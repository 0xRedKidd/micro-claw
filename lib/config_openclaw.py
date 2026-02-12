"""OpenClaw-adapted config — reads MICROMOLT_* env vars for namespace isolation."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

from constants import CONTRACTS, REALM_FEES


def _env(name: str, default: str | None = None, required: bool = False) -> str:
    value = os.getenv(name, default)
    if value is None or value == "":
        if required:
            raise ValueError(f"Missing required environment variable: {name}")
        return ""
    return str(value)


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return int(value)


@dataclass
class Settings:
    # Wallet
    private_key: str
    rpc_url: str

    # PvE Backend
    pve_backend_url: str

    # OpenAI
    openai_api_key: str
    openai_model: str
    openai_boss_strategy_prompt: str

    # Mode
    mode: str
    preferred_zone: str

    # Contract Addresses (from constants, not env)
    agents_contract: str
    factory_contract: str
    neuro_token_contract: str
    micro_token_contract: str
    weapons_contract: str
    armors_contract: str
    softwares_contract: str
    cpus_contract: str
    payment_address: str

    # Loop delay
    loop_delay: int

    # Realm Entry Fees (MICRO)
    realm_fee_airdrop: float
    realm_fee_pending_tx: float
    realm_fee_rugville: float
    realm_fee_snipebot: float
    realm_fee_ponzi: float
    realm_fee_failed_launch: float

    # Autonomous creation controls
    auto_create_class_id: int
    auto_create_initial_buy_micro: int
    auto_create_name_prefix: str
    auto_mint_min_micro: int

    def realm_fee_micro(self, zone_key: str) -> float:
        zone_fee_map = {
            "airdrop_zone": self.realm_fee_airdrop,
            "pending_tx_zone": self.realm_fee_pending_tx,
            "rugville_zone": self.realm_fee_rugville,
            "snipebot_zone": self.realm_fee_snipebot,
            "ponzi_zone": self.realm_fee_ponzi,
            "failed_launch_zone": self.realm_fee_failed_launch,
        }
        return float(zone_fee_map.get(zone_key, self.realm_fee_airdrop))

    def realm_fee_wei(self, zone_key: str) -> int:
        return int(self.realm_fee_micro(zone_key) * 10**18)

    @property
    def min_realm_fee_wei(self) -> int:
        min_micro = min(
            self.realm_fee_airdrop,
            self.realm_fee_pending_tx,
            self.realm_fee_rugville,
            self.realm_fee_snipebot,
            self.realm_fee_ponzi,
            self.realm_fee_failed_launch,
        )
        return int(min_micro * 10**18)


def load_config() -> Settings:
    # Always find .env relative to the skill root, not cwd
    _skill_root = os.path.join(os.path.dirname(__file__), "..")
    _dotenv_path = os.path.join(_skill_root, ".env")
    load_dotenv(_dotenv_path)

    return Settings(
        private_key=_env("MICROMOLT_PRIVATE_KEY", required=True),
        rpc_url=_env("MICROMOLT_RPC_URL", "https://sepolia.base.org"),
        pve_backend_url=_env("MICROMOLT_PVE_BACKEND_URL", "ws://localhost:8787"),
        openai_api_key=_env("MICROMOLT_OPENAI_API_KEY", ""),
        openai_model=_env("MICROMOLT_OPENAI_MODEL", "gpt-4o"),
        openai_boss_strategy_prompt=_env("MICROMOLT_OPENAI_BOSS_STRATEGY_PROMPT", ""),
        mode=_env("MICROMOLT_MODE", "continuous"),
        preferred_zone=_env("MICROMOLT_PREFERRED_ZONE", "auto"),
        # Contract addresses from constants (same for all users)
        agents_contract=CONTRACTS["agents"],
        factory_contract=CONTRACTS["factory"],
        neuro_token_contract=CONTRACTS["neuro_token"],
        micro_token_contract=CONTRACTS["micro_token"],
        weapons_contract=CONTRACTS["weapons"],
        armors_contract=CONTRACTS["armors"],
        softwares_contract=CONTRACTS["softwares"],
        cpus_contract=CONTRACTS["cpus"],
        payment_address=CONTRACTS["payment"],
        loop_delay=_env_int("MICROMOLT_LOOP_DELAY", 5),
        # Realm fees from constants
        realm_fee_airdrop=REALM_FEES["airdrop_zone"],
        realm_fee_pending_tx=REALM_FEES["pending_tx_zone"],
        realm_fee_rugville=REALM_FEES["rugville_zone"],
        realm_fee_snipebot=REALM_FEES["snipebot_zone"],
        realm_fee_ponzi=REALM_FEES["ponzi_zone"],
        realm_fee_failed_launch=REALM_FEES["failed_launch_zone"],
        auto_create_class_id=_env_int("MICROMOLT_AUTO_CREATE_CLASS_ID", -1),
        auto_create_initial_buy_micro=_env_int("MICROMOLT_AUTO_CREATE_INITIAL_BUY_MICRO", 0),
        auto_create_name_prefix=_env("MICROMOLT_AUTO_CREATE_NAME_PREFIX", "Agent"),
        auto_mint_min_micro=_env_int("MICROMOLT_AUTO_MINT_MIN_MICRO", 10000),
    )
