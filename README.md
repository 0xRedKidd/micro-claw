# MicroMolt OpenClaw Skill

OpenClaw skill package to automate MicroFun gameplay for a configured wallet.

## What This Includes

- Namespaced config via `MICROMOLT_*` environment variables
- On-chain actions (agent discovery, level-up, equip, burn, mint)
- PvE WebSocket flow with optional OpenAI boss-input generation
- Runner commands for `status`, `run-once`, and `run-loop`

## Setup

```bash
cd openclaw-skill
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edit .env values
```

## Runner Usage

```bash
python scripts/micromolt_openclaw.py status
python scripts/micromolt_openclaw.py run-once
python scripts/micromolt_openclaw.py run-loop --max-runs 3
python scripts/micromolt_openclaw.py create-agent
```

## OpenClaw Usage

- Install this folder as a skill (or copy into your OpenClaw skills directory).
- Invoke via natural language, or trigger commands using the runner above.

## Notes

- OpenAI is optional; if no API key is set, boss actions fall back to local templates.
- Loot display is strict to successful on-chain mint results.
