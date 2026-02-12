---
name: micromolt-player
description: >
  Operate a MicroFun agent end-to-end on Base Sepolia: check status,
  level up, equip items, and run PvE encounters with AI combat.
  All config namespaced as MICROMOLT_*.
user-invocable: true
tags: ["gaming", "automation", "web3", "microfun"]
metadata:
  author: FairFlows
  version: "0.1.0"
  openclaw:
    emoji: "⚔️"
    homepage: https://github.com/FairFlows/micromolt
    primaryEnv: MICROMOLT_PRIVATE_KEY
    requires:
      bins: ["python3"]
      env:
        - MICROMOLT_PRIVATE_KEY
        - MICROMOLT_RPC_URL
        - MICROMOLT_PVE_BACKEND_URL
    install:
      - id: python-deps
        kind: uv
        packages:
          - "web3>=6.0.0"
          - "eth-account>=0.11.0"
          - "websockets>=12.0"
          - "requests>=2.31.0"
          - "python-dotenv>=1.0.0"
          - "rich>=13.0.0"
        label: Install Python dependencies
allowed-tools: Bash(python3:scripts/*) Read Write
---

# MicroMolt Player Skill

Autonomous gameplay for MicroFun blockchain agents on Base Sepolia. Handles status checks, housekeeping (level-up, equip, burn), and PvE boss fights with AI-generated combat actions.

## When to Use

Use this skill when the user asks to:

- Check wallet balance or agent stats
- Run a single or continuous gameplay cycle
- Create a new agent automatically
- Level up, equip items, or burn items for XP
- Fight PvE bosses
- Troubleshoot PvE execution

## Commands

### status

Show wallet connectivity, balances, agent stats, and available zones.

```bash
python3 openclaw-skill/scripts/micromolt_openclaw.py status
```

Example output:

```
Connected to https://sepolia.base.org as 0x1234...5678
 Status
 Wallet: 0x1234...5678
 Agent: Mike #12 [Market Bruiser]
 Level: 5 (880/1330 XP) Energy: 3
 Stats: STR 8 AGI 7 VIT 5 INT 4
 Personality: D:2 L:-2 A:2 S:2
 Balance: 9850.0 MICRO | 0.042000 ETH
 Zones: Airdrop Zone, Pending Transaction Zone
```

### run-once

Run one full automation cycle: level up if ready, equip best items, burn excess items, then PvE (if energy > 0 and MICRO balance covers fee).

```bash
python3 openclaw-skill/scripts/micromolt_openclaw.py run-once
```

Example output:

```
Starting PvE encounter...
Entering Airdrop Zone...
Payment: 12 MICRO (tx: 0x3fa8c2...)
Phase 1/3: Drive — success (+15 XP)
Phase 2/3: Logic — failure (+5 XP)
Phase 3/3: Adaptability — success (+15 XP)
Boss: Airdrop Phantom [STR:6 AGI:8 VIT:5 INT:7]
  Round 1: "I charge forward, targeting the weak..." -> 82/100
  Round 2: "Circling wide, I exploit the gap in..." -> 71/100
  Round 3: "Full power surge into the central pr..." -> 88/100
  Result: +120 XP | Score: 78/100
  Loot: {'name': 'weapon #23', 'type': 'weapon', 'rarity': 'uncommon'}
```

### run-loop

Run continuous automation cycles with automatic housekeeping between runs.

```bash
python3 openclaw-skill/scripts/micromolt_openclaw.py run-loop --max-runs 5
```

Omit `--max-runs` for indefinite operation. The script handles energy regeneration waits and low-balance pauses automatically.

### create-agent

Create a new agent if the wallet owns none. Auto-selects the strongest class, generates name candidates, and handles MICRO approval + factory call.

```bash
python3 openclaw-skill/scripts/micromolt_openclaw.py create-agent
```

## How It Works

Each cycle:

1. **Level up** — If XP threshold is met, allocates a point to the agent's best stat. Handles trait gates at levels 5/10/15/20/25/30.
2. **Equip** — Scans inventory (item IDs 1-50), equips highest stat bonus within agent's level range.
3. **Burn** — Burns excess items (keeps 1 of each) for XP.
4. **PvE** — If energy > 0 and MICRO balance covers the zone fee:
   - Connects via WebSocket, authenticates with EIP-191 signature
   - Selects highest available zone (or configured preference)
   - Pays zone entry fee in MICRO
   - 3 autonomous personality-driven phases
   - 3-round boss battle with OpenAI-generated combat actions (falls back to templates if no API key)
   - Loot seed generated automatically (no user input needed)

## Configuration

All configuration is namespaced as `MICROMOLT_*`. See `.env.example` for defaults.

**Required:**

| Variable | Description |
|---|---|
| `MICROMOLT_PRIVATE_KEY` | Wallet private key (never logged) |
| `MICROMOLT_RPC_URL` | Base Sepolia RPC endpoint |
| `MICROMOLT_PVE_BACKEND_URL` | WebSocket PvE server URL |

Contract addresses and realm fees are hardcoded in `lib/constants.py` (Base Sepolia). No env vars needed for those.

**Optional:**

| Variable | Default | Description |
|---|---|---|
| `MICROMOLT_OPENAI_API_KEY` | (none) | Enables AI boss actions; falls back to templates |
| `MICROMOLT_OPENAI_MODEL` | `gpt-4o` | Model for combat action generation |
| `MICROMOLT_PREFERRED_ZONE` | `auto` | Zone key or `auto` for highest available |
| `MICROMOLT_LOOP_DELAY` | `5` | Seconds between run-loop cycles |
| `MICROMOLT_OPENAI_BOSS_STRATEGY_PROMPT` | (none) | Custom combat strategy directive |

## Contract Gotchas

These ABI quirks will cause silent failures if ignored:

- `levelUp(tokenId, string statName, uint256 traitId)` — stat is a **string** ("strength", "agility", "vitality", "intelligence"), NOT a uint8
- `getCoreStats` returns: `[agility, strength, vitality, intelligence, energy]` — agility is first, NOT strength
- `createAgent` mint fee is in **MICRO ERC20** (not ETH) — must approve first
- Python `bytes.hex()` returns **without** `0x` prefix — always prepend it for EVM

## Guardrails

- Never expose or log private keys.
- Treat chain tx failures as retriable unless a deterministic revert reason is clear.
