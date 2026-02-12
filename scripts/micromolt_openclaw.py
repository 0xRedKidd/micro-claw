#!/usr/bin/env python3
"""OpenClaw runner for MicroMolt gameplay automation."""

import argparse
import asyncio
import os
import sys
import time
from typing import Optional

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LIB_DIR = os.path.join(BASE_DIR, "lib")
if LIB_DIR not in sys.path:
    sys.path.insert(0, LIB_DIR)

from console_compat import Console, Panel, Table
from config_openclaw import load_config, Settings
from blockchain import BlockchainService, AgentInfo
from constants import ZONES, LEVEL_REQUIREMENTS
from agent_manager import try_level_up, try_equip_best, try_burn_items
from create_agent_lib import interactive_create_agent
from pve import run_pve


console = Console()


def display_banner() -> None:
    console.print(
        Panel(
            "[bold cyan]MicroMolt OpenClaw Skill[/bold cyan] — Autonomous MicroFun Agent",
            border_style="cyan",
        )
    )


def display_dashboard(chain: BlockchainService, agent: AgentInfo) -> None:
    next_level = agent.level + 1
    xp_needed = LEVEL_REQUIREMENTS.get(next_level, 0)
    xp_str = f"{agent.exp}/{xp_needed} XP" if xp_needed else f"{agent.exp} XP (MAX)"

    micro_bal = chain.get_micro_balance()
    eth_bal = chain.get_eth_balance()

    available = [z["name"] for _, z in ZONES.items() if agent.level >= z["level_req"]]

    dashboard = (
        f"[dim]Wallet:[/dim] {chain.wallet[:6]}...{chain.wallet[-4:]}\n"
        f"[dim]Agent:[/dim] [bold]{agent.name}[/bold] #{agent.token_id} [dim][{agent.agent_class}][/dim]\n"
        f"[dim]Level:[/dim] {agent.level} ({xp_str}) Energy: {agent.energy}\n"
        f"[dim]Stats:[/dim] STR {agent.strength} AGI {agent.agility} VIT {agent.vitality} INT {agent.intelligence}\n"
        f"[dim]Personality:[/dim] D:{agent.drive} L:{agent.logic} A:{agent.adaptability} S:{agent.sociality}\n"
        f"[dim]Balance:[/dim] {micro_bal / 10**18:.1f} MICRO | {eth_bal / 10**18:.6f} ETH\n"
        f"[dim]Zones:[/dim] {', '.join(available) if available else 'None'}"
    )
    console.print(Panel(dashboard, title="Status", border_style="cyan"))


def pick_agent(chain: BlockchainService, token_ids: list[int]) -> int:
    if len(token_ids) == 1:
        return token_ids[0]

    table = Table(title="Owned Agents")
    table.add_column("Token ID", style="bold")
    table.add_column("Name")
    table.add_column("Class")
    table.add_column("Level", justify="center")

    scored: list[tuple[int, int, int]] = []
    for token_id in token_ids:
        try:
            info = chain.get_agent_info(token_id)
            table.add_row(str(token_id), info.name, info.agent_class, str(info.level))
            scored.append((token_id, int(info.level), int(info.energy)))
        except Exception:
            table.add_row(str(token_id), "?", "?", "?")
            scored.append((token_id, 0, 0))

    console.print(table)
    best = max(scored, key=lambda x: (x[1], x[2], x[0]))
    console.print(f"[dim]Selected token {best[0]} (level {best[1]}, energy {best[2]})[/dim]")
    return best[0]


def has_micro_for_fee(chain: BlockchainService, config: Settings) -> bool:
    return chain.get_micro_balance() >= config.min_realm_fee_wei


def ensure_starting_micro_balance(chain: BlockchainService, config: Settings) -> bool:
    target_micro = max(0, int(config.auto_mint_min_micro))
    target_wei = target_micro * 10**18
    current_wei = chain.get_micro_balance()

    if current_wei >= target_wei:
        return True

    missing_wei = target_wei - current_wei
    console.print(
        f"[yellow]MICRO balance low ({current_wei / 10**18:.1f}); minting {missing_wei / 10**18:.1f} MICRO...[/yellow]"
    )
    try:
        tx_hash = chain.mint_micro(chain.wallet, missing_wei)
        chain.wait_for_tx(tx_hash)
    except Exception as exc:
        console.print(f"[red]Startup MICRO mint failed: {exc}[/red]")
        return False

    updated = current_wei
    for _ in range(12):
        updated = chain.get_micro_balance()
        if updated >= target_wei:
            break
        time.sleep(5)

    if updated < target_wei:
        console.print(
            f"[red]Startup MICRO mint incomplete ({updated / 10**18:.1f} < {target_micro}).[/red]"
        )
        return False

    console.print(f"[green]MICRO balance ready: {updated / 10**18:.1f} MICRO[/green]")
    return True


def display_pve_result(result) -> None:
    if not result.success:
        console.print(f"[red]PvE Error: {result.error}[/red]")
        return

    lines = []
    for phase in result.phases:
        lines.append(
            f"  Phase {phase.get('phase', '?')}/3: {phase.get('axis', '')} — "
            f"{phase.get('outcome', '')} (+{phase.get('xp_gained', 0)} XP)"
        )

    for round_result in result.rounds:
        action_short = round_result.action[:45] + "..." if len(round_result.action) > 45 else round_result.action
        lines.append(f"  Round {round_result.round_num}: \"{action_short}\" -> {round_result.score}/100")

    lines.append(f"  Result: +{result.xp_gained} XP | Score: {result.total_score}/100")
    if result.loot:
        lines.append(f"  Loot: {result.loot}")
    elif getattr(result, "loot_generated_count", 0) > 0:
        lines.append(
            f"  Loot note: backend generated {result.loot_generated_count} item(s), "
            "but no on-chain loot mint succeeded"
        )

    console.print(
        Panel(
            "\n".join(lines),
            title=f"[bold]{result.zone_name}[/bold] — {result.boss_name}",
            border_style="green",
        )
    )


def ensure_agent(chain: BlockchainService) -> int:
    while True:
        token_ids = chain.get_owned_agents()
        if token_ids:
            return pick_agent(chain, token_ids)

        console.print("[yellow]No agents found for this wallet. Auto-create is enabled.[/yellow]")
        new_id = interactive_create_agent(chain, console)
        if new_id is not None:
            return new_id

        console.print("[dim]Auto-create not completed. Retrying in 60s...[/dim]")
        time.sleep(60)


async def run_cycle(chain: BlockchainService, config: Settings, token_id: int) -> None:
    agent = chain.get_agent_info(token_id)

    leveled = True
    while leveled:
        agent = chain.get_agent_info(token_id)
        leveled = try_level_up(chain, agent, console)

    try_equip_best(chain, config, agent, console)
    try_burn_items(chain, config, agent, console)

    agent = chain.get_agent_info(token_id)

    if agent.energy > 0 and has_micro_for_fee(chain, config):
        console.print("[bold]Starting PvE encounter...[/bold]")
        result = await run_pve(config, chain, agent, console)
        display_pve_result(result)
        return

    if agent.energy <= 0:
        console.print(f"[yellow]No energy ({agent.energy}); waiting for regeneration.[/yellow]")
    elif not has_micro_for_fee(chain, config):
        micro_bal = chain.get_micro_balance() / 10**18
        min_fee = config.min_realm_fee_wei / 10**18
        console.print(f"[yellow]Insufficient MICRO ({micro_bal:.1f}); need at least {min_fee:g}.[/yellow]")


def connect() -> tuple[Settings, BlockchainService]:
    config = load_config()
    chain = BlockchainService(config)
    return config, chain


def cmd_status() -> int:
    config, chain = connect()
    console.print(f"[green]Connected[/green] to {config.rpc_url} as {chain.wallet[:6]}...{chain.wallet[-4:]}")
    token_id = ensure_agent(chain)
    agent = chain.get_agent_info(token_id)
    display_dashboard(chain, agent)
    return 0


def cmd_create_agent() -> int:
    _, chain = connect()
    created = interactive_create_agent(chain, console)
    if created is None:
        console.print("[red]Agent creation failed.[/red]")
        return 1
    console.print(f"[green]Created agent token #{created}[/green]")
    return 0


async def _run_once_async() -> int:
    config, chain = connect()
    display_banner()
    console.print(f"[green]Connected[/green] to {config.rpc_url} as {chain.wallet[:6]}...{chain.wallet[-4:]}")

    if not ensure_starting_micro_balance(chain, config):
        return 1

    token_id = ensure_agent(chain)
    display_dashboard(chain, chain.get_agent_info(token_id))
    await run_cycle(chain, config, token_id)
    return 0


def cmd_run_once() -> int:
    return asyncio.run(_run_once_async())


async def _run_loop_async(max_runs: Optional[int] = None) -> int:
    config, chain = connect()
    display_banner()
    console.print(f"[green]Connected[/green] to {config.rpc_url} as {chain.wallet[:6]}...{chain.wallet[-4:]}")

    if not ensure_starting_micro_balance(chain, config):
        return 1

    token_id = ensure_agent(chain)
    display_dashboard(chain, chain.get_agent_info(token_id))

    run_count = 0
    while True:
        run_count += 1
        console.rule(f"[dim]Run #{run_count}[/dim]")
        await run_cycle(chain, config, token_id)

        if max_runs is not None and run_count >= max_runs:
            break

        console.print(f"[dim]Next run in {config.loop_delay}s...[/dim]")
        await asyncio.sleep(config.loop_delay)

    return 0


def cmd_run_loop(max_runs: Optional[int] = None) -> int:
    return asyncio.run(_run_loop_async(max_runs))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="MicroMolt OpenClaw skill runner")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="Show wallet/agent status")
    sub.add_parser("create-agent", help="Create an agent if none exists")
    sub.add_parser("run-once", help="Run one full automation cycle")

    loop_parser = sub.add_parser("run-loop", help="Run continuous automation")
    loop_parser.add_argument("--max-runs", type=int, default=None, help="Optional stop after N cycles")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        if args.command == "status":
            return cmd_status()
        if args.command == "create-agent":
            return cmd_create_agent()
        if args.command == "run-once":
            return cmd_run_once()
        if args.command == "run-loop":
            return cmd_run_loop(max_runs=args.max_runs)
        parser.error(f"Unknown command: {args.command}")
        return 2
    except KeyboardInterrupt:
        console.print("\n[dim]Interrupted.[/dim]")
        return 130
    except Exception as exc:
        console.print(f"[red]Fatal error: {exc}[/red]")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
