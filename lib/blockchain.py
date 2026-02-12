"""On-chain interface — read agent data, send transactions, sign messages."""

import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from eth_account import Account
from eth_account.messages import encode_defunct
from web3 import Web3

from config_openclaw import Settings
from constants import STAT_NAMES, STAT_PRIMARY, PERSONALITY_TRAITS, EQUIPMENT_SLOTS


def _load_abi(name: str) -> list:
    abi_dir = os.path.join(os.path.dirname(__file__), "..", "abis")
    with open(os.path.join(abi_dir, f"{name}.json")) as f:
        return json.load(f)


@dataclass
class AgentInfo:
    token_id: int = 0
    name: str = ""
    agent_class: str = ""
    level: int = 1
    exp: int = 0
    energy: int = 0
    # Base stats (without equipment)
    strength: int = 0
    agility: int = 0
    vitality: int = 0
    intelligence: int = 0
    # Personality
    drive: int = 0
    logic: int = 0
    adaptability: int = 0
    sociality: int = 0
    # Equipment
    equipped_weapon: int = 0
    equipped_armor: int = 0
    equipped_software: int = 0
    equipped_cpu: int = 0

    @property
    def personality_dict(self) -> Dict[str, int]:
        return {
            "drive": self.drive,
            "logic": self.logic,
            "adaptability": self.adaptability,
            "sociality": self.sociality,
        }

    @property
    def stats_dict(self) -> Dict[str, int]:
        return {
            "strength": self.strength,
            "agility": self.agility,
            "vitality": self.vitality,
            "intelligence": self.intelligence,
        }

    @property
    def best_stat_name(self) -> str:
        stats = self.stats_dict
        return max(stats, key=stats.get)

    @property
    def best_stat_primary(self) -> bytes:
        """bytes32 short name for arena choosePrimary (e.g. b'STR')."""
        return STAT_PRIMARY[self.best_stat_name]


class BlockchainService:
    def __init__(self, config: Settings):
        self.config = config
        self.w3 = Web3(Web3.HTTPProvider(config.rpc_url))
        if not self.w3.is_connected():
            raise RuntimeError(f"Cannot connect to RPC: {config.rpc_url}")

        self.account = Account.from_key(config.private_key)
        self.wallet = self.account.address

        # Load contracts
        self.agents = self.w3.eth.contract(
            address=self.w3.to_checksum_address(config.agents_contract),
            abi=_load_abi("agents"),
        )
        self.factory = self.w3.eth.contract(
            address=self.w3.to_checksum_address(config.factory_contract),
            abi=_load_abi("factory"),
        )
        self.micro_token = self.w3.eth.contract(
            address=self.w3.to_checksum_address(config.micro_token_contract),
            abi=_load_abi("erc20"),
        )
        # Equipment contracts (ERC1155)
        self.equipment_contracts = {
            "weapon": self.w3.eth.contract(
                address=self.w3.to_checksum_address(config.weapons_contract),
                abi=_load_abi("erc1155"),
            ),
            "armor": self.w3.eth.contract(
                address=self.w3.to_checksum_address(config.armors_contract),
                abi=_load_abi("erc1155"),
            ),
            "software": self.w3.eth.contract(
                address=self.w3.to_checksum_address(config.softwares_contract),
                abi=_load_abi("erc1155"),
            ),
            "cpu": self.w3.eth.contract(
                address=self.w3.to_checksum_address(config.cpus_contract),
                abi=_load_abi("erc1155"),
            ),
        }

    # ── Utility ───────────────────────────────────────────────────

    def _send_tx(self, func, value: int = 0) -> str:
        """Build, sign, send a transaction and return the tx hash hex."""
        # Estimate gas from the function call first. Building with a low fixed gas
        # can cause estimate to fail and silently underfund complex transactions.
        try:
            gas_est = int(func.estimate_gas({"from": self.wallet, "value": value}))
            gas_limit = min(max(int(gas_est * 1.25), 300_000), 8_000_000)
        except Exception:
            gas_limit = 2_000_000

        nonce = self.w3.eth.get_transaction_count(self.wallet, "pending")
        tx = func.build_transaction({
            "from": self.wallet,
            "nonce": nonce,
            "chainId": self.w3.eth.chain_id,
            "gas": gas_limit,
            "gasPrice": self.w3.eth.gas_price,
            "value": value,
        })
        signed = self.w3.eth.account.sign_transaction(tx, self.config.private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        h = tx_hash.hex()
        return h if h.startswith("0x") else f"0x{h}"

    def wait_for_tx(self, tx_hash: str, timeout: int = 120) -> dict:
        """Wait for transaction receipt. Accepts hex string with or without 0x."""
        if isinstance(tx_hash, str) and not tx_hash.startswith("0x"):
            tx_hash = f"0x{tx_hash}"
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=timeout)
        if receipt["status"] != 1:
            try:
                tx = self.w3.eth.get_transaction(tx_hash)
                gas_used = int(receipt.get("gasUsed", 0))
                gas_limit = int(tx.get("gas", 0))
                raise RuntimeError(
                    f"Transaction failed: {tx_hash} (gas used {gas_used}/{gas_limit})"
                )
            except Exception:
                raise RuntimeError(f"Transaction failed: {tx_hash}")
        return receipt

    def sign_message(self, nonce: str) -> str:
        """EIP-191 sign a nonce string. Returns 0x-prefixed hex."""
        message = encode_defunct(text=nonce)
        signed = self.w3.eth.account.sign_message(message, private_key=self.config.private_key)
        sig_hex = signed.signature.hex()
        return sig_hex if sig_hex.startswith("0x") else f"0x{sig_hex}"

    # ── Read: Agent Discovery ─────────────────────────────────────

    def get_owned_agents(self) -> List[int]:
        """Get all token IDs owned by the wallet."""
        checksum = self.w3.to_checksum_address(self.wallet)
        balance = self.agents.functions.balanceOf(checksum).call()
        return [
            self.agents.functions.tokenOfOwnerByIndex(checksum, i).call()
            for i in range(balance)
        ]

    def get_agent_info(self, token_id: int) -> AgentInfo:
        """Fetch full agent info from chain."""
        info = AgentInfo(token_id=token_id)

        info.name = self.agents.functions.nameOf(token_id).call()
        info.agent_class = self.agents.functions.classOf(token_id).call()
        info.level = self.agents.functions.getLevel(token_id).call()
        info.exp = self.agents.functions.getExp(token_id).call()
        info.energy = self.agents.functions.getEnergy(token_id).call()

        # Core stats (without equipment): [agility, strength, vitality, intelligence, energy]
        core = self.agents.functions.getCoreStats(token_id).call()
        info.agility = int(core[0])
        info.strength = int(core[1])
        info.vitality = int(core[2])
        info.intelligence = int(core[3])

        # Personality: [drive, logic, adaptability, sociality]
        p = self.agents.functions.getPersonality(token_id).call()
        info.drive = int(p[0])
        info.logic = int(p[1])
        info.adaptability = int(p[2])
        info.sociality = int(p[3])

        # Equipment
        info.equipped_weapon = self.agents.functions.equippedWeapon(token_id).call()
        info.equipped_armor = self.agents.functions.equippedArmor(token_id).call()
        info.equipped_software = self.agents.functions.equippedSoftware(token_id).call()
        info.equipped_cpu = self.agents.functions.equippedCPU(token_id).call()

        return info

    # ── Read: Balances ────────────────────────────────────────────

    def get_micro_balance(self) -> int:
        """MICRO token balance in wei."""
        return self.micro_token.functions.balanceOf(
            self.w3.to_checksum_address(self.wallet)
        ).call()

    def get_eth_balance(self) -> int:
        """ETH balance in wei."""
        return self.w3.eth.get_balance(self.w3.to_checksum_address(self.wallet))

    # ── Read: Equipment Inventory ─────────────────────────────────

    def get_item_balance(self, slot: str, item_id: int) -> int:
        """Check how many of a specific item the wallet holds."""
        contract = self.equipment_contracts[slot]
        return contract.functions.balanceOf(
            self.w3.to_checksum_address(self.wallet), item_id
        ).call()

    def get_item_level_range(self, slot: str, item_id: int) -> tuple:
        """Get (minLevel, maxLevel) for an item."""
        contract = self.equipment_contracts[slot]
        result = contract.functions.levelRange(item_id).call()
        return (int(result[0]), int(result[1]))

    def get_item_stat(self, slot: str, item_id: int) -> int:
        """Get the stat bonus for an item."""
        contract = self.equipment_contracts[slot]
        return contract.functions.stat(item_id).call()

    # ── Read: Curve ───────────────────────────────────────────────

    def is_curve_ended(self, curve_address: str) -> bool:
        """Check if an agent's bonding curve has graduated."""
        curve = self.w3.eth.contract(
            address=self.w3.to_checksum_address(curve_address),
            abi=_load_abi("curve"),
        )
        return curve.functions.curveEnded().call()

    # ── Write: Token Operations ───────────────────────────────────

    def approve_token(self, spender: str, amount: int) -> str:
        """Approve MICRO token spending."""
        func = self.micro_token.functions.approve(
            self.w3.to_checksum_address(spender), amount
        )
        return self._send_tx(func)

    def transfer_micro(self, to: str, amount: int) -> str:
        """Transfer MICRO tokens (e.g. zone fee payment)."""
        func = self.micro_token.functions.transfer(
            self.w3.to_checksum_address(to), amount
        )
        return self._send_tx(func)

    def mint_micro(self, to: str, amount: int) -> str:
        """Mint MICRO tokens (testnet/dev token contracts with public mint)."""
        if amount <= 0:
            raise ValueError("Mint amount must be positive")
        func = self.micro_token.functions.mint(
            self.w3.to_checksum_address(to), int(amount)
        )
        return self._send_tx(func)

    # ── Write: Agent Management ───────────────────────────────────

    def level_up(self, token_id: int, stat_name: str, trait_id: int = 0) -> str:
        """Level up an agent, allocating a point to stat_name (e.g. 'strength')."""
        func = self.agents.functions.levelUp(token_id, stat_name, trait_id)
        return self._send_tx(func)

    def equip_item(self, agent_id: int, item_contract: str, item_id: int) -> str:
        """Equip an item to an agent."""
        func = self.agents.functions.equip(
            agent_id, self.w3.to_checksum_address(item_contract), item_id
        )
        return self._send_tx(func)

    def unequip_item(self, agent_id: int, item_contract: str) -> str:
        """Unequip an item from an agent."""
        func = self.agents.functions.unequip(
            agent_id, self.w3.to_checksum_address(item_contract)
        )
        return self._send_tx(func)

    def burn_items_for_xp(self, agent_id: int, slot: int, item_id: int, amount: int) -> str:
        """Burn items for XP."""
        func = self.agents.functions.burnItemsForXP(agent_id, slot, item_id, amount)
        return self._send_tx(func)

    # ── Write: Factory ────────────────────────────────────────────

    def get_mint_fee(self) -> int:
        return self.factory.functions.mintFee().call()

    def create_agent(
        self,
        name: str,
        symbol: str,
        personality_mask: str,
        drive: int,
        logic: int,
        adaptability: int,
        sociality: int,
        agent_name: str,
        bonus_stat1: str,
        bonus_stat2: str,
        buy_amount: int = 0,
        blueprint_token_id: int = 0,
    ) -> str:
        """Create a new agent via factory. Mint fee is paid in MICRO (must approve first)."""
        func = self.factory.functions.createAgent(
            self.w3.to_checksum_address(self.wallet),  # _minter
            name,              # curveName
            symbol,            # curveSymbol
            personality_mask,  # personalityMask
            drive,
            logic,
            adaptability,
            sociality,
            agent_name,        # agentName
            bonus_stat1,       # bonusStat1 (e.g. "strength")
            bonus_stat2,       # bonusStat2 (e.g. "agility")
            buy_amount,
            blueprint_token_id,
        )
        return self._send_tx(func)

    # ── Trait Checks ──────────────────────────────────────────────

    def get_next_level_trait_options(self, token_id: int) -> tuple:
        """Returns (needed: bool, options: list[int])."""
        result = self.agents.functions.getNextLevelTraitOptions(token_id).call()
        return (result[0], list(result[1]))

    def ensure_erc1155_approval(self, slot: str) -> None:
        """Ensure the agents contract is approved to move ERC1155 items."""
        contract = self.equipment_contracts[slot]
        approved = contract.functions.isApprovedForAll(
            self.w3.to_checksum_address(self.wallet),
            self.w3.to_checksum_address(self.config.agents_contract),
        ).call()
        if not approved:
            func = contract.functions.setApprovalForAll(
                self.w3.to_checksum_address(self.config.agents_contract), True
            )
            tx_hash = self._send_tx(func)
            self.wait_for_tx(tx_hash)
