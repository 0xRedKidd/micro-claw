---
name: micromolt-player
description: >
  Autonomous MicroFun gameplay on Base Sepolia — PvE boss fights,
  leveling, equipment, agent creation. Say "play microfun" to start.
user-invocable: true
tags: ["gaming", "automation", "web3", "microfun", "pve"]
metadata:
  author: FairFlows
  version: "0.3.0"
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
allowed-tools: Bash(python3:*) Read Write
---

# MicroMolt Player Skill

Autonomous gameplay bot for **MicroFun** — a blockchain RPG on Base Sepolia where AI agents fight PvE bosses, earn XP, level up, collect loot, and equip gear. All on-chain.

## CRITICAL: Skill Directory

This skill's root directory is wherever this SKILL.md file lives. All paths below are relative to that directory. Before running ANY command, `cd` into the skill directory first. Find it with:

```bash
SKILL_DIR="$(dirname "$(find /root -name 'SKILL.md' -path '*/micro-claw/*' 2>/dev/null | head -1)")"
echo "$SKILL_DIR"
```

ALL commands below assume you are inside `$SKILL_DIR`. Always `cd "$SKILL_DIR"` before running anything.

## CRITICAL: Install Dependencies First

Before any Python command will work, install the dependencies. Do this ONCE after cloning:

```bash
cd "$SKILL_DIR" && pip install -r requirements.txt
```

If `pip` is not available, use `pip3`. Do NOT create wrapper shell scripts. Do NOT create a venv unless the user asks. The Python scripts in this repo are ready to run as-is.

## When to Activate This Skill

Activate this skill when the user says anything like:

- "play microfun" / "play micromolt" / "start microfun"
- "play microfun pve" / "run pve" / "fight bosses"
- "microfun status" / "check my agent" / "what level am I"
- "create a microfun agent" / "make me an agent"
- "run microfun loop" / "auto-play microfun" / "grind microfun"
- "level up my agent" / "equip my agent"
- Any mention of "microfun", "micromolt", or "micro agent" in a gaming context

**Arena/PvP is not yet available.** If the user asks for "pvp", "arena", or "play microfun pvp", say: "Arena mode is coming soon — only PvE is available right now. Want me to run PvE instead?"

## First-Run Setup (MUST DO BEFORE ANY COMMAND)

**Before running any gameplay command**, check if `.env` exists in the skill directory:

```bash
cd "$SKILL_DIR" && test -f .env && echo "CONFIG_EXISTS" || echo "CONFIG_MISSING"
```

### If output is CONFIG_MISSING:

Ask the user for config values IN THE CHAT. Do NOT tell them to SSH in or edit files manually. Do NOT create shell scripts. Ask these 3 questions one at a time:

1. "I need to set up MicroMolt first (one-time only). What is your Base Sepolia wallet private key? (starts with 0x — I'll store it securely and never display it)"
2. "What is your Base Sepolia RPC URL? (e.g. Alchemy or Infura URL). Say 'default' to use the free public RPC."
3. "Do you have an OpenAI API key for smarter boss fights? (optional — say 'skip' to use template actions instead)"

After collecting answers, write the `.env` file directly. Replace `<PRIVATE_KEY>`, `<RPC_URL>`, and `<OPENAI_KEY>` with the user's actual values:

```bash
cd "$SKILL_DIR" && cat > .env << 'ENVEOF'
MICROMOLT_PRIVATE_KEY=<PRIVATE_KEY>
MICROMOLT_RPC_URL=<RPC_URL>
MICROMOLT_PVE_BACKEND_URL=ws://209.38.216.229:8000/ws/
MICROMOLT_OPENAI_API_KEY=<OPENAI_KEY>
MICROMOLT_OPENAI_MODEL=gpt-4o
MICROMOLT_MODE=continuous
MICROMOLT_PREFERRED_ZONE=auto
MICROMOLT_LOOP_DELAY=5
MICROMOLT_AUTO_CREATE_CLASS_ID=-1
MICROMOLT_AUTO_CREATE_INITIAL_BUY_MICRO=0
MICROMOLT_AUTO_CREATE_NAME_PREFIX=Agent
MICROMOLT_AUTO_MINT_MIN_MICRO=10000
ENVEOF
```

Defaults if user says "default" or "skip":
- RPC_URL default: `https://sepolia.base.org`
- OPENAI_KEY default: leave empty (bot uses template actions)

After writing, say: "Setup complete! Your config is saved — you won't need to enter this again. Let me check your status..."

Then immediately run the `status` command to verify connectivity.

### If output is CONFIG_EXISTS:

Skip setup entirely. Never re-ask for env vars. Proceed directly to the command.

## Intent Routing

Match the user's request to a command:

| User says | Command to run |
|---|---|
| "play microfun" / "start" / "run" / "fight" | `run-once` |
| "play microfun pve" / "boss fight" / "pve" | `run-once` |
| "auto play" / "grind" / "loop" / "keep playing" | `run-loop` (ask how many runs, default 5) |
| "status" / "check agent" / "what level" / "balance" | `status` |
| "create agent" / "make agent" / "new agent" | `create-agent` |
| "play microfun pvp" / "arena" / "pvp" | Say arena coming soon, offer PvE |

## Commands

**IMPORTANT: Every command must be run from the skill directory.** Always prefix with `cd "$SKILL_DIR" &&`.

### status

```bash
cd "$SKILL_DIR" && python3 scripts/micromolt_openclaw.py status
```

Shows wallet, agent stats, balances, available zones. Run this first to verify everything works.

### run-once

```bash
cd "$SKILL_DIR" && python3 scripts/micromolt_openclaw.py run-once
```

One full cycle: level up → equip best gear → burn junk → PvE boss fight. Fully autonomous, no user input needed during execution.

### run-loop

```bash
cd "$SKILL_DIR" && python3 scripts/micromolt_openclaw.py run-loop --max-runs 5
```

Continuous cycles. Stops after `--max-runs`. Omit the flag for unlimited. When user asks to "grind", ask: "How many runs? (default: 5, or say 'unlimited')"

### create-agent

```bash
cd "$SKILL_DIR" && python3 scripts/micromolt_openclaw.py create-agent
```

Creates a new agent if wallet owns none. Auto-picks best class, generates name, handles MICRO approval + factory call.

## How Each Cycle Works

1. **Level up** — If XP threshold met, allocates +1 to agent's best stat
2. **Equip** — Scans inventory, equips highest stat bonus item per slot
3. **Burn** — Burns excess items (keeps 1 each) for XP
4. **PvE** — If energy > 0 and MICRO covers zone fee:
   - WebSocket auth → zone selection → MICRO payment
   - 3 personality-driven phases (autonomous)
   - 3-round boss fight with AI or template actions
   - Loot seed generated automatically

## Presenting Results to the User

After each command, read the terminal output and summarize it conversationally. Do NOT dump raw output. Examples:

- **status**: "Your agent Mike #12 is a level 5 Market Bruiser with 880/1330 XP and 3 energy. Balance: 9850 MICRO. You can enter Airdrop Zone and Pending TX Zone."
- **run-once success**: "Nice fight! Your agent beat the Airdrop Phantom scoring 78/100. Gained 120 XP and picked up an uncommon weapon."
- **run-once no energy**: "Your agent is out of energy right now. It regenerates over time — try again later."
- **run-loop done**: "Finished 5 runs! Your agent went from level 3 to 7 and collected 3 items."
- **error**: Explain what went wrong in plain language. Don't just paste the traceback.

## Error Handling

| Error | What to tell the user |
|---|---|
| "No agents found" | "You don't have an agent yet. Want me to create one?" |
| "No energy" | "Your agent is out of energy. It'll regenerate — try again later." |
| "Insufficient MICRO" | "MICRO balance too low for zone fees. The bot will try to mint some." |
| "429 Too Many Requests" | "RPC rate limited — the bot retries automatically. If this keeps happening, try a different RPC." |
| "Transaction failed" | "On-chain transaction reverted. Let me check your agent's current status." Then run `status`. |
| WebSocket / connection errors | "The PvE server might be down. Try again in a few minutes." |
| ModuleNotFoundError | Dependencies not installed. Run: `cd "$SKILL_DIR" && pip install -r requirements.txt` |

## DO NOT

- Do NOT create wrapper shell scripts (setup.sh, play.sh, etc.). The Python scripts handle everything.
- Do NOT tell the user to SSH into the server or manually edit files.
- Do NOT create a virtual environment unless the user specifically asks.
- Do NOT display, log, or echo private keys. Ever. Not even partially.
- Do NOT re-ask for env vars if `.env` already exists.
- Do NOT run commands outside the skill directory.

## Configuration Reference

All config lives in `.env` inside the skill directory. Contract addresses and zone fees are hardcoded in `lib/constants.py` — users never touch those.

**Required (collected during first-run setup):**

| Variable | Description |
|---|---|
| `MICROMOLT_PRIVATE_KEY` | Wallet private key (never displayed) |
| `MICROMOLT_RPC_URL` | Base Sepolia RPC (default: `https://sepolia.base.org`) |
| `MICROMOLT_PVE_BACKEND_URL` | PvE server (default: `ws://209.38.216.229:8000/ws/`) |

**Optional (user can edit .env later):**

| Variable | Default | Description |
|---|---|---|
| `MICROMOLT_OPENAI_API_KEY` | (none) | AI boss actions; templates without it |
| `MICROMOLT_OPENAI_MODEL` | `gpt-4o` | OpenAI model for combat |
| `MICROMOLT_PREFERRED_ZONE` | `auto` | Zone key or `auto` for highest |
| `MICROMOLT_LOOP_DELAY` | `5` | Seconds between loop cycles |
| `MICROMOLT_AUTO_CREATE_CLASS_ID` | `-1` | Class ID (-1 = auto-pick) |
| `MICROMOLT_AUTO_MINT_MIN_MICRO` | `10000` | Auto-mint if below this |
