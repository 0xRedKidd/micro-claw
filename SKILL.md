---
name: micromolt-player
description: >
  Autonomous MicroFun gameplay on Base Sepolia — PvE boss fights,
  leveling, equipment, agent creation. Say "play microfun" to start.
user-invocable: true
tags: ["gaming", "automation", "web3", "microfun", "pve"]
metadata:
  author: FairFlows
  version: "0.2.0"
  openclaw:
    emoji: "⚔️"
    homepage: https://github.com/0xRedKidd/micro-claw
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

Autonomous gameplay bot for **MicroFun** — a blockchain RPG on Base Sepolia where AI agents fight PvE bosses, earn XP, level up, collect loot, and equip gear. All on-chain.

## When to Activate This Skill

Activate this skill when the user says anything like:

- "play microfun" / "play micromolt" / "start microfun"
- "play microfun pve" / "run pve" / "fight bosses"
- "microfun status" / "check my agent" / "what level am I"
- "create a microfun agent" / "make me an agent"
- "run microfun loop" / "auto-play microfun" / "grind microfun"
- "level up my agent" / "equip my agent"
- Any mention of "microfun", "micromolt", or "micro agent" in a gaming context

**Important:** Arena/PvP is not yet available in this skill. If the user asks for "pvp", "arena", or "play microfun pvp", tell them: "Arena mode is coming soon — only PvE is available right now. Want me to run PvE instead?"

## First-Run Setup (Config Persistence)

**Before running any command**, check if the `.env` file exists:

```bash
python3 -c "import os; print('exists' if os.path.exists('openclaw-skill/.env') else 'missing')"
```

### If `.env` is MISSING — ask the user for config once:

Tell the user: "I need a few things to set up MicroMolt. You'll only need to do this once."

Ask for these **3 required values** one at a time:

1. **Wallet private key** — "What's your Base Sepolia wallet private key? (starts with 0x, I'll store it securely and never display it)"
   → Save as `MICROMOLT_PRIVATE_KEY`

2. **RPC URL** — "What's your Base Sepolia RPC URL? (e.g. from Alchemy or Infura). Or press enter for the default public RPC."
   → Save as `MICROMOLT_RPC_URL` (default: `https://sepolia.base.org`)

3. **OpenAI API key (optional)** — "Do you have an OpenAI API key? This makes boss fights smarter with AI-generated combat actions. Skip if you don't have one."
   → Save as `MICROMOLT_OPENAI_API_KEY` (leave empty if skipped)

Then **write the `.env` file** with all values (use defaults for everything else):

```bash
cat > openclaw-skill/.env << 'ENVEOF'
# Wallet
MICROMOLT_PRIVATE_KEY=<user_provided>
MICROMOLT_RPC_URL=<user_provided_or_default>

# PvE Backend
MICROMOLT_PVE_BACKEND_URL=ws://209.38.216.229:8000/ws/

# OpenAI (optional)
MICROMOLT_OPENAI_API_KEY=<user_provided_or_empty>
MICROMOLT_OPENAI_MODEL=gpt-4o

# Runtime
MICROMOLT_MODE=continuous
MICROMOLT_PREFERRED_ZONE=auto
MICROMOLT_LOOP_DELAY=5

# Auto-creation
MICROMOLT_AUTO_CREATE_CLASS_ID=-1
MICROMOLT_AUTO_CREATE_INITIAL_BUY_MICRO=0
MICROMOLT_AUTO_CREATE_NAME_PREFIX=Agent
MICROMOLT_AUTO_MINT_MIN_MICRO=10000
ENVEOF
```

After writing, confirm: "Setup complete! Your config is saved — you won't need to enter this again."

### If `.env` EXISTS — skip setup entirely

Just proceed to the requested command. Never re-ask for env vars.

## Intent Routing

Based on what the user says, run the appropriate command:

| User says | Action |
|---|---|
| "play microfun" / "start" / "run" | Run `run-once` (single cycle) |
| "play microfun pve" / "fight" / "boss fight" | Run `run-once` |
| "auto play" / "grind" / "loop" / "keep playing" | Run `run-loop` (ask how many runs, default 5) |
| "status" / "check agent" / "what level" / "balance" | Run `status` |
| "create agent" / "make agent" / "new agent" | Run `create-agent` |
| "play microfun pvp" / "arena" / "pvp" | Tell user arena is coming soon, offer PvE |

## Commands

All commands are run from the repo root directory.

### status

```bash
python3 openclaw-skill/scripts/micromolt_openclaw.py status
```

Shows wallet connectivity, MICRO/ETH balances, agent stats, personality, available zones. Run this first to verify everything works.

Example output:
```
Connected to https://sepolia.base.org as 0x1234...5678
┌─ Status ─────────────────────────────────┐
│ Wallet: 0x1234...5678                    │
│ Agent: Mike #12 [Market Bruiser]         │
│ Level: 5 (880/1330 XP) Energy: 3        │
│ Stats: STR 8 AGI 7 VIT 5 INT 4          │
│ Personality: D:2 L:-2 A:2 S:2           │
│ Balance: 9850.0 MICRO | 0.042000 ETH    │
│ Zones: Airdrop Zone, Pending Tx Zone    │
└──────────────────────────────────────────┘
```

### run-once

```bash
python3 openclaw-skill/scripts/micromolt_openclaw.py run-once
```

One full cycle: level up → equip best gear → burn junk items → PvE boss fight. Fully autonomous — no user input needed during execution.

Example output:
```
Leveling up to 6 (+1 strength)...
Leveled up to 6! (tx: 0x7b41...)
Equipped weapon #3 (+4 stat bonus)
Burned 2x armor #1 for XP
Starting PvE encounter...
Entering Airdrop Zone...
Payment: 12 MICRO (tx: 0x3fa8...)
Phase 1/3: Drive — success (+15 XP)
Phase 2/3: Logic — failure (+5 XP)
Phase 3/3: Adaptability — success (+15 XP)
Boss: Airdrop Phantom [STR:6 AGI:8 VIT:5 INT:7]
  Round 1: "I charge forward targeting the weak..." -> 82/100
  Round 2: "Circling wide, I exploit the gap..." -> 71/100
  Round 3: "Full power surge into the central..." -> 88/100
  Result: +120 XP | Score: 78/100
  Loot: weapon #23 (uncommon)
```

### run-loop

```bash
python3 openclaw-skill/scripts/micromolt_openclaw.py run-loop --max-runs 5
```

Continuous automation. Each cycle does the full run-once flow, then waits 5 seconds before the next. Stops after `--max-runs` cycles. Omit the flag for indefinite grinding.

When the user asks to "auto play" or "grind", ask: "How many runs? (default: 5, or say 'unlimited')"

### create-agent

```bash
python3 openclaw-skill/scripts/micromolt_openclaw.py create-agent
```

Creates a new agent if the wallet has none. Auto-picks the best class, generates a name, handles MICRO approval + factory contract call.

## How Each Cycle Works

1. **Level up** — If XP threshold met, allocates +1 to agent's best stat. Handles trait gates at levels 5/10/15/20/25/30.
2. **Equip** — Scans item IDs 1-50, equips highest stat bonus within level range.
3. **Burn** — Burns excess items (keeps 1 each) for XP.
4. **PvE** — If energy > 0 and MICRO covers the zone fee:
   - WebSocket auth with EIP-191 signature
   - Picks highest available zone (or user's preferred zone)
   - Pays entry fee in MICRO tokens
   - 3 personality-driven phases (autonomous)
   - 3-round boss fight with AI actions (or template fallback)
   - Loot seed generated automatically

## Presenting Results

After each command, summarize the output conversationally. Examples:

- **After status**: "Your agent Mike #12 is level 5 with 880/1330 XP. You have 3 energy and 9850 MICRO. Ready for Airdrop Zone and Pending TX Zone."
- **After run-once**: "Nice run! Your agent fought the Airdrop Phantom and scored 78/100. Gained 120 XP and picked up an uncommon weapon. Level went from 5 to 6."
- **After run-loop**: "Finished 5 runs. Your agent went from level 3 to level 7, earned 3 items, and cleared Airdrop Zone 5 times."
- **On error**: Read the error output and explain what went wrong in plain language. Common issues: low MICRO balance, no energy, RPC rate limit (retries automatically), PvE server down.

## Error Handling

- **"No agents found"** — The wallet has no agents. Ask: "You don't have an agent yet. Want me to create one?"
- **"No energy"** — Energy regenerates over time. Tell the user to wait and try again later.
- **"Insufficient MICRO"** — Balance too low for zone fees. The script auto-mints testnet MICRO if possible.
- **"429 Too Many Requests"** — RPC rate limit. The script retries automatically with backoff. If persistent, suggest the user switch to a paid RPC plan.
- **"Transaction failed"** — On-chain revert. Report the tx hash and suggest running `status` to check current state.
- **PvE WebSocket errors** — The PvE server may be down. Tell the user to try again in a few minutes.

## Configuration Reference

All config lives in `openclaw-skill/.env`. Contract addresses and zone fees are hardcoded in `lib/constants.py` — users never need to touch those.

**Required (asked during first-run setup):**

| Variable | Description |
|---|---|
| `MICROMOLT_PRIVATE_KEY` | Wallet private key (never logged or displayed) |
| `MICROMOLT_RPC_URL` | Base Sepolia RPC (default: `https://sepolia.base.org`) |
| `MICROMOLT_PVE_BACKEND_URL` | PvE WebSocket server (default: `ws://209.38.216.229:8000/ws/`) |

**Optional (can be changed in .env later):**

| Variable | Default | Description |
|---|---|---|
| `MICROMOLT_OPENAI_API_KEY` | (none) | AI boss actions; falls back to templates without it |
| `MICROMOLT_OPENAI_MODEL` | `gpt-4o` | Which OpenAI model for combat |
| `MICROMOLT_PREFERRED_ZONE` | `auto` | Zone key or `auto` for highest available |
| `MICROMOLT_LOOP_DELAY` | `5` | Seconds between loop cycles |
| `MICROMOLT_AUTO_CREATE_CLASS_ID` | `-1` | Force a class ID for agent creation (-1 = auto-pick best) |
| `MICROMOLT_AUTO_MINT_MIN_MICRO` | `10000` | Auto-mint MICRO if balance below this |

## Security Rules

- NEVER display, log, or echo the private key. Not even partially.
- NEVER include the private key in command output or conversation.
- If the user asks to see their key, refuse and explain why.
- All transaction hashes are safe to display.
- Wallet addresses are safe to display.
