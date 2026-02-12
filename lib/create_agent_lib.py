"""Autonomous agent creation flow (no user prompts)."""

import time
from typing import Optional

from console_compat import Console

from blockchain import BlockchainService
from constants import AGENT_CLASSES


DEFAULT_NAME_POOL = [
    "Mike",
    "Andrew",
    "Alex",
    "Sam",
    "Chris",
    "Jordan",
    "Taylor",
    "Casey",
    "Riley",
    "Morgan",
    "Avery",
    "Jamie",
]


def _pick_class(chain: BlockchainService) -> dict:
    class_id = int(getattr(chain.config, "auto_create_class_id", -1))
    if 0 <= class_id < len(AGENT_CLASSES):
        return AGENT_CLASSES[class_id]

    # Heuristic: strongest overall base stats, then offense bias, then lowest id.
    return max(
        AGENT_CLASSES,
        key=lambda c: (
            c["str"] + c["agi"] + c["vit"] + c["int"],
            c["str"] + c["agi"],
            -c["id"],
        ),
    )


def _default_bonus_stats(chosen_class: dict) -> list[str]:
    stat_order = [
        ("strength", int(chosen_class["str"])),
        ("agility", int(chosen_class["agi"])),
        ("vitality", int(chosen_class["vit"])),
        ("intelligence", int(chosen_class["int"])),
    ]
    stat_order.sort(key=lambda x: x[1], reverse=True)
    return [stat_order[0][0], stat_order[1][0]]


def _safe_symbol(name: str) -> str:
    cleaned = "".join(ch for ch in name.upper() if ch.isalpha())
    if not cleaned:
        return "AGENT"
    if len(cleaned) < 3:
        cleaned = (cleaned + "AGENT")[:5]
    return cleaned[:5]


def _safe_name(name: str) -> str:
    cleaned = "".join(ch for ch in name.strip() if ch.isalpha())
    if not cleaned:
        return "Mike"
    return cleaned[:18].capitalize()


def _name_candidates(chain: BlockchainService) -> list[str]:
    prefix = _safe_name(str(getattr(chain.config, "auto_create_name_prefix", "")).strip())
    wallet = chain.wallet.lower()
    seed = int(wallet[-6:], 16) if len(wallet) >= 6 else 0
    ordered_pool = DEFAULT_NAME_POOL[seed % len(DEFAULT_NAME_POOL):] + DEFAULT_NAME_POOL[: seed % len(DEFAULT_NAME_POOL)]
    wallet_letters = "".join(ch for ch in wallet if ch in "abcdef")
    suffix_letters = (wallet_letters[-2:] or "aa").capitalize()

    cands = []
    if prefix and prefix.lower() not in {"agent", "micro"}:
        cands.append(prefix)
    cands.extend(ordered_pool[:8])
    cands.extend([f"{n}{suffix_letters[0]}" for n in ordered_pool[:6]])

    deduped = []
    seen = set()
    for raw in cands:
        name = _safe_name(raw)
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(name)
    return deduped[:12]


def _candidate_pairs(chain: BlockchainService) -> list[tuple[str, str]]:
    wallet_letters = "".join(ch for ch in chain.wallet.lower() if ch in "abcdef")
    salt1 = (wallet_letters[-1:] or "x")
    salt2 = (wallet_letters[-2:] or "zz")

    pairs = []
    seen = set()
    for name in _name_candidates(chain):
        symbols = [
            _safe_symbol(name),
            _safe_symbol(f"{name}{salt1}"),
            _safe_symbol(f"{name}{salt2}"),
        ]
        for symbol in symbols:
            key = f"{name.lower()}::{symbol}"
            if key in seen:
                continue
            seen.add(key)
            pairs.append((name, symbol))
    return pairs[:16]


def interactive_create_agent(
    chain: BlockchainService,
    console: Optional[Console] = None,
) -> Optional[int]:
    """Create a new agent automatically. Returns new token_id or None."""
    if console is None:
        console = Console()

    chosen_class = _pick_class(chain)
    class_id = int(chosen_class["id"])
    mask = str(chosen_class["personality"])

    # Personality: moderate default aligned to class bit mask
    personality = [2 if bit == "1" else -2 for bit in mask]
    bonus_stats = _default_bonus_stats(chosen_class)

    pairs = _candidate_pairs(chain)
    name, symbol = pairs[0]

    initial_buy_micro = max(0, int(getattr(chain.config, "auto_create_initial_buy_micro", 0)))
    initial_buy_wei = initial_buy_micro * 10**18

    console.print("[bold cyan]Autonomous agent creation enabled[/bold cyan]")
    console.print(
        f"Class: {chosen_class['name']} (#{class_id}) | "
        f"Personality mask: {mask} | "
        f"Bonus stats: {bonus_stats[0]}, {bonus_stats[1]}"
    )
    console.print(f"Name: {name} | Symbol: {symbol} | Initial buy: {initial_buy_micro} MICRO")

    try:
        mint_fee = chain.get_mint_fee()
        total_approve = mint_fee + initial_buy_wei
        micro_balance = chain.get_micro_balance()
        console.print(
            f"Mint fee: {mint_fee / 10**18:.1f} MICRO | "
            f"Total approval: {total_approve / 10**18:.1f} MICRO | "
            f"Balance: {micro_balance / 10**18:.1f} MICRO"
        )

        if micro_balance < total_approve:
            console.print(
                f"[yellow]Insufficient MICRO for createAgent "
                f"({micro_balance / 10**18:.1f} < {total_approve / 10**18:.1f}).[/yellow]"
            )
            return None

        if total_approve > 0:
            console.print("Approving MICRO for factory...")
            approve_tx = chain.approve_token(chain.config.factory_contract, total_approve)
            chain.wait_for_tx(approve_tx)

        for cand_name, cand_symbol in pairs:
            console.print(f"Sending createAgent transaction (name: {cand_name}, symbol: {cand_symbol})...")
            try:
                tx_hash = chain.create_agent(
                    name=cand_name,
                    symbol=cand_symbol,
                    personality_mask=mask,
                    drive=personality[0],
                    logic=personality[1],
                    adaptability=personality[2],
                    sociality=personality[3],
                    agent_name=cand_name,
                    bonus_stat1=bonus_stats[0],
                    bonus_stat2=bonus_stats[1],
                    buy_amount=initial_buy_wei,
                )
                console.print(f"Create tx: {tx_hash}")
                chain.wait_for_tx(tx_hash)
                console.print("[bold green]Agent created successfully[/bold green]")
                break
            except Exception as e:
                console.print(
                    f"[yellow]Create attempt failed with {cand_name}/{cand_symbol}: {e}[/yellow]"
                )
        else:
            return None

        token_ids = chain.get_owned_agents()
        if not token_ids:
            for _ in range(12):
                time.sleep(5)
                token_ids = chain.get_owned_agents()
                if token_ids:
                    break
        if not token_ids:
            return None
        new_id = max(token_ids)
        info = chain.get_agent_info(new_id)
        console.print(f"Token ID: {new_id} | Name: {info.name} | Class: {info.agent_class}")
        return new_id
    except Exception as e:
        console.print(f"[red]Agent creation failed: {e}[/red]")
        return None
