"""Static constants for MicroFun agent classes, zones, level requirements, and personality."""

from typing import Dict, List, Any

# ── 16 Agent Classes ──────────────────────────────────────────────
# id, name, personality mask (4-bit DLAS), base stats
AGENT_CLASSES: List[Dict[str, Any]] = [
    {"id": 0,  "name": "Market Bruiser",     "personality": "1011", "str": 3, "agi": 2, "vit": 2, "int": 1},
    {"id": 1,  "name": "Fast Liquidator",    "personality": "1111", "str": 1, "agi": 3, "vit": 2, "int": 2},
    {"id": 2,  "name": "Chain Analyst",      "personality": "0101", "str": 1, "agi": 1, "vit": 2, "int": 4},
    {"id": 3,  "name": "Front-Run Scout",    "personality": "0000", "str": 2, "agi": 3, "vit": 2, "int": 1},
    {"id": 4,  "name": "Liquidity Tank",     "personality": "0001", "str": 3, "agi": 1, "vit": 3, "int": 1},
    {"id": 5,  "name": "Market Tactician",   "personality": "0111", "str": 1, "agi": 2, "vit": 2, "int": 3},
    {"id": 6,  "name": "Protocol Enforcer",  "personality": "1000", "str": 2, "agi": 3, "vit": 2, "int": 1},
    {"id": 7,  "name": "Balanced Holder",    "personality": "1001", "str": 2, "agi": 2, "vit": 2, "int": 2},
    {"id": 8,  "name": "Speed Hacker",       "personality": "1110", "str": 1, "agi": 4, "vit": 1, "int": 2},
    {"id": 9,  "name": "Candlebreaker",      "personality": "1100", "str": 3, "agi": 3, "vit": 1, "int": 1},
    {"id": 10, "name": "Frontline Holder",   "personality": "1101", "str": 2, "agi": 2, "vit": 3, "int": 1},
    {"id": 11, "name": "Chain Survivor",     "personality": "0010", "str": 2, "agi": 2, "vit": 3, "int": 1},
    {"id": 12, "name": "Liquidity Assassin", "personality": "0110", "str": 3, "agi": 3, "vit": 1, "int": 1},
    {"id": 13, "name": "Consensus Keeper",   "personality": "0100", "str": 1, "agi": 1, "vit": 3, "int": 3},
    {"id": 14, "name": "Bagholder Tank",     "personality": "0011", "str": 2, "agi": 1, "vit": 4, "int": 1},
    {"id": 15, "name": "Scalp Raider",       "personality": "1010", "str": 3, "agi": 2, "vit": 2, "int": 1},
]

CLASS_BY_ID: Dict[int, Dict[str, Any]] = {c["id"]: c for c in AGENT_CLASSES}
CLASS_BY_NAME: Dict[str, Dict[str, Any]] = {c["name"]: c for c in AGENT_CLASSES}

# ── Level XP Requirements (levels 2-31) ──────────────────────────
LEVEL_REQUIREMENTS: Dict[int, int] = {
    2: 120, 3: 280, 4: 530, 5: 880, 6: 1330, 7: 1930, 8: 2730,
    9: 3730, 10: 4980, 11: 6580, 12: 8580, 13: 11080, 14: 14180,
    15: 17980, 16: 22580, 17: 28080, 18: 34580, 19: 42380, 20: 51580,
    21: 62380, 22: 74980, 23: 89480, 24: 105980, 25: 124680, 26: 145680,
    27: 169180, 28: 195180, 29: 223980, 30: 255480, 31: 290480,
}

# Trait gate levels — must have a trait equipped to level past these
TRAIT_GATE_LEVELS = {5, 10, 15, 20, 25, 30}

# ── 6 Zones ───────────────────────────────────────────────────────
ZONES: Dict[str, Dict[str, Any]] = {
    "airdrop_zone":       {"name": "Airdrop Zone",          "level_req": 1,  "fee_micro": 100, "realm_id": 1},
    "pending_tx_zone":    {"name": "Pending Transaction Zone", "level_req": 5,  "fee_micro": 100, "realm_id": 2},
    "rugville_zone":      {"name": "Rugville Zone",         "level_req": 10, "fee_micro": 100, "realm_id": 3},
    "snipebot_zone":      {"name": "SnipeBot Zone",         "level_req": 15, "fee_micro": 100, "realm_id": 4},
    "ponzi_zone":         {"name": "Ponzi Zone",            "level_req": 20, "fee_micro": 100, "realm_id": 5},
    "failed_launch_zone": {"name": "Failed Launchpad Zone", "level_req": 25, "fee_micro": 100, "realm_id": 6},
}

ZONE_FEE_WEI = 100 * 10**18  # 100 MICRO with 18 decimals

# ── Personality ───────────────────────────────────────────────────
# Trait names in contract order
PERSONALITY_TRAITS = ["drive", "logic", "adaptability", "sociality"]

# Stat names in contract order
STAT_NAMES = ["agility", "strength", "vitality", "intelligence"]

# For choosePrimary (arena) — bytes32 short names
STAT_PRIMARY: dict = {
    "strength": b"STR",
    "agility": b"AGI",
    "vitality": b"VIT",
    "intelligence": b"INT",
}

# For burnItemsForXP — Slot enum: None=0, Weapon=1, Armor=2, Software=3, CPU=4, Trait=5
SLOT_IDS = {"weapon": 1, "armor": 2, "software": 3, "cpu": 4}

# ── Class Archetypes (voice for AI prompts) ───────────────────────
CLASS_ARCHETYPES: Dict[str, str] = {
    "Market Bruiser": "Blunt, confrontational. Short punchy declarations. Sees everything as a fight.",
    "Fast Liquidator": "Quick-witted, impatient. Talks about speed and efficiency. Hates waiting.",
    "Chain Analyst": "Cerebral, detached. Obsessed with data and patterns. Speaks like a research note.",
    "Front-Run Scout": "Sneaky, cryptic. Hints rather than states. Always implies being one step ahead.",
    "Liquidity Tank": "Stoic, immovable. Slow heavy statements. Endurance is everything.",
    "Market Tactician": "Strategic, calculated. Frames everything as moves on a board. Thinks long-term.",
    "Protocol Enforcer": "Authoritative, rigid. Speaks in rules and absolutes. Black and white thinking.",
    "Balanced Holder": "Measured, pragmatic. Even-tempered. Never too excited, never too worried.",
    "Speed Hacker": "Hyperactive, fragmented speech. Skips words. Talks fast, thinks faster.",
    "Candlebreaker": "Volatile, intense. Raw energy. Lives for the moment of impact.",
    "Frontline Holder": "Loyal, steady. Talks about holding the line and protecting positions.",
    "Chain Survivor": "Weathered, cautious. Speaks from experience. Has seen things go wrong before.",
    "Liquidity Assassin": "Cold, precise. Few words, maximum impact. Treats everything as a target.",
    "Consensus Keeper": "Diplomatic, thoughtful. Seeks harmony. References the bigger picture.",
    "Bagholder Tank": "Stubborn, defiant. Never sells. Grim determination. Diamond hands mentality.",
    "Scalp Raider": "Restless, opportunistic. Always hunting the next trade. Short attention span.",
}

# ── Equipment Slot Names ──────────────────────────────────────────
EQUIPMENT_SLOTS = ["weapon", "armor", "software", "cpu"]

# ── Contract Addresses (Base Sepolia) ────────────────────────────
CONTRACTS = {
    "agents":       "0x13c43f2f8124fd760ef491cbf78492d1592aaee9",
    "factory":      "0x836fcb0167240b4cbb8d01f76686613681b6256d",
    "neuro_token":  "0x8f8206a18d2c22eb29a9e5985d221e21f4ec6a63",
    "micro_token":  "0x8f8206a18d2c22eb29a9e5985d221e21f4ec6a63",
    "weapons":      "0x93b99dbe9e9f4ea3f240728998cf0ec904d45ff5",
    "armors":       "0x4b15d16360810645638dffe775f16a534215af80",
    "softwares":    "0xa022553946dc91b91f596f1de3248e4f4be39961",
    "cpus":         "0xb9bf1fe4dc5c7a804d2bcaa40b4a15955c6324c0",
    "payment":      "0x05638C8ac42D3aCed7A292c52aE847ea4A5bD6B7",
}

# ── Realm Entry Fees (MICRO, human-readable) ─────────────────────
REALM_FEES: Dict[str, float] = {
    "airdrop_zone":       12,
    "pending_tx_zone":    24,
    "rugville_zone":      36,
    "snipebot_zone":      58,
    "ponzi_zone":         92,
    "failed_launch_zone": 144,
}
