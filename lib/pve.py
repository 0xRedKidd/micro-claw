"""WebSocket PvE client — auth → zone → boss battle."""

import asyncio
import json
import random
import re
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import websockets

from blockchain import AgentInfo, BlockchainService
from config_openclaw import Settings
from constants import ZONES
from ai_combat import FALLBACK_ACTIONS, generate_boss_action


@dataclass
class PveRoundResult:
    round_num: int = 0
    action: str = ""
    score: int = 0
    story: str = ""
    feedback: str = ""


@dataclass
class PveResult:
    success: bool = False
    zone_name: str = ""
    boss_name: str = ""
    boss_stats: Dict[str, int] = field(default_factory=dict)
    rounds: List[PveRoundResult] = field(default_factory=list)
    total_score: int = 0
    xp_gained: int = 0
    loot: Optional[Dict[str, Any]] = None
    loot_generated_count: int = 0
    error: str = ""
    # Phase results from autonomous decisions
    phases: List[Dict[str, Any]] = field(default_factory=list)


async def run_pve(
    config: Settings,
    chain: BlockchainService,
    agent: AgentInfo,
    console=None,
) -> PveResult:
    """Run a complete PvE encounter via WebSocket."""
    result = PveResult()
    sid = uuid.uuid4().hex
    ws_url = _build_ws_url(config.pve_backend_url, sid)

    try:
        async with websockets.connect(ws_url) as ws:
            # ── Phase 1: Authentication ────────────────────────
            msg = await _recv(ws)
            if msg.get("action") != "auth_challenge":
                result.error = f"Expected auth_challenge, got: {msg}"
                return result

            nonce = msg["nonce"]
            signature = chain.sign_message(nonce)
            await ws.send(json.dumps({
                "address": chain.wallet.lower(),
                "signature": signature,
            }))
            if console:
                console.log("[dim]Authenticated with PvE backend[/dim]")

            # ── Phase 2: Menu — choose Random Encounter ────────
            msg = await _recv(ws)
            # Menu message with options
            await ws.send(json.dumps({"choice": 2}))

            # ── Phase 3: Token Selection ───────────────────────
            msg = await _recv(ws)
            # Expect owned_token_ids
            if "owned_token_ids" not in msg:
                if "error" in msg:
                    result.error = msg["error"]
                    return result
                result.error = f"Expected token selection, got: {msg}"
                return result

            await ws.send(json.dumps({"token_id": agent.token_id}))

            # ── Phase 4: Zone Selection ────────────────────────
            msg = await _recv(ws)
            if "error" in msg:
                result.error = msg["error"]
                return result

            zone_key = _pick_zone(config, agent, msg.get("available_zones", []))
            if not zone_key:
                result.error = "No available zones for agent level"
                return result

            result.zone_name = ZONES.get(zone_key, {}).get("name", zone_key)
            await ws.send(json.dumps({"zone_key": zone_key}))
            if console:
                console.log(f"Entering [bold]{result.zone_name}[/bold]...")

            # ── Phase 5: Payment ───────────────────────────────
            msg = await _recv(ws)
            # Payment request — prefer backend-requested amount; fallback to local env config
            fee_wei = _extract_fee_wei(msg)
            if fee_wei is None:
                fee_wei = config.realm_fee_wei(zone_key)

            tx_hash = chain.transfer_micro(config.payment_address, fee_wei)
            chain.wait_for_tx(tx_hash)

            await ws.send(json.dumps({"payment_tx": tx_hash}))
            if console:
                console.log(f"Payment: {fee_wei // 10**18} MICRO (tx: {tx_hash[:10]}...)")

            # Wait for payment confirmation
            msg = await _recv(ws)
            if "error" in msg:
                result.error = msg["error"]
                return result
            # "Waiting for blockchain confirmation..." message
            if "⏳" in msg.get("message", ""):
                msg = await _recv(ws)
            # "Payment verified" message
            if "error" in msg:
                result.error = msg["error"]
                return result

            # ── Phase 6: Game Init ─────────────────────────────
            msg = await _recv(ws)
            # This contains zone_name, location, dilemma, agentic_mode
            if console:
                loc = msg.get("location", "")
                if loc:
                    console.log(f"Location: [italic]{loc}[/italic]")

            # ── Phase 7: Autonomous Phases (3x) ────────────────
            for phase_num in range(1, 4):
                msg = await _recv(ws)
                if "autonomous_phase" in msg:
                    phase_data = {
                        "phase": msg.get("autonomous_phase"),
                        "axis": msg.get("axis_name", msg.get("axis", "")),
                        "outcome": msg.get("outcome", ""),
                        "xp_gained": msg.get("xp_gained", 0),
                        "decision": msg.get("decision", ""),
                    }
                    result.phases.append(phase_data)
                    if console:
                        outcome = msg.get("outcome", "unknown")
                        xp = msg.get("xp_gained", 0)
                        axis_name = msg.get("axis_name", msg.get("axis", ""))
                        console.log(
                            f"Phase {phase_num}/3: {axis_name} — "
                            f"{outcome} (+{xp} XP)"
                        )
                elif "error" in msg:
                    result.error = msg["error"]
                    return result

            # ── Phase 8: Boss Battle ───────────────────────────
            msg = await _recv(ws)
            if not msg.get("boss_battle"):
                if "error" in msg:
                    result.error = msg["error"]
                    return result
                result.error = f"Expected boss_battle, got: {msg}"
                return result

            result.boss_name = msg.get("boss_name", "Unknown Boss")
            result.boss_stats = msg.get("boss_stats", {})
            if console:
                stats_str = " ".join(
                    f"{k[:3].upper()}:{v}" for k, v in result.boss_stats.items()
                )
                console.log(
                    f"Boss: [bold red]{result.boss_name}[/bold red] [{stats_str}]"
                )

            previous_rounds: List[Dict[str, Any]] = []

            for round_num in range(1, 4):
                # Generate AI action
                action = generate_boss_action(
                    agent_name=agent.name,
                    agent_class=agent.agent_class,
                    personality=agent.personality_dict,
                    agent_level=agent.level,
                    agent_energy=agent.energy,
                    agent_stats=agent.stats_dict,
                    boss_name=result.boss_name,
                    boss_stats=result.boss_stats,
                    round_num=round_num,
                    previous_rounds=previous_rounds,
                    previous_phases=result.phases,
                    strategy_prompt=config.openai_boss_strategy_prompt,
                    api_key=config.openai_api_key,
                    model=config.openai_model,
                )

                await ws.send(json.dumps({"boss_input": action}))

                # Receive round result
                msg = await _recv(ws)

                # Handle validation errors (too short/long)
                while "error" in msg:
                    if console:
                        console.log(f"[yellow]Server: {msg['error']}[/yellow]")
                    # Retry with fallback
                    action = random.choice(FALLBACK_ACTIONS)
                    await ws.send(json.dumps({"boss_input": action}))
                    msg = await _recv(ws)

                round_result = PveRoundResult(
                    round_num=round_num,
                    action=action,
                    score=msg.get("round_score", 0),
                    story=msg.get("round_story", ""),
                    feedback=msg.get("round_feedback", ""),
                )
                result.rounds.append(round_result)
                previous_rounds.append({
                    "round": round_num,
                    "action": action,
                    "score": round_result.score,
                })

                if console:
                    console.log(
                        f"  Round {round_num}: \"{action[:50]}...\" → "
                        f"{round_result.score}/100"
                    )

            # ── Phase 9: Final Score, Loot, XP ──────────────────
            # After round 3 (final_round=True), the backend sends:
            #   1. "⚡ Adding X XP..." then "✅ X XP added!" (if XP > 0)
            #   2. {"action": "request_loot_seed", ...} — WAITS for {"loot_seed": N}
            #   3. Reward notification messages
            #   4. game_over {game_over, success_score, loot_earned, combat_finale, ...}
            #   5. connection_closing
            # We drain all messages, responding to loot_seed requests.
            try:
                while True:
                    msg = await asyncio.wait_for(_recv(ws), timeout=30)

                    # Respond to loot seed request (backend blocks until we reply)
                    if msg.get("action") == "request_loot_seed":
                        seed = random.randint(0, 10**14 - 1)
                        await ws.send(json.dumps({"loot_seed": seed}))
                        if console:
                            console.log("[dim]Sent loot seed...[/dim]")
                        continue

                    if msg.get("game_over"):
                        result.total_score = msg.get("success_score", 0)
                        result.success = True
                        raw_loot = msg.get("loot_earned") or msg.get("loot")
                        result.loot_generated_count = _count_loot_items(raw_loot)
                        result.loot = _extract_single_loot(msg)
                        # Extract XP breakdown
                        xp_info = msg.get("xp_breakdown", {})
                        if xp_info.get("total_run_xp"):
                            result.xp_gained = xp_info["total_run_xp"]
                        combat = msg.get("combat_finale", {})
                        if console:
                            winner = combat.get("winner", "?")
                            icon = "[green]Victory[/green]" if winner == "agent" else "[red]Defeat[/red]"
                            console.log(
                                f"{icon} — Score: [bold]{result.total_score}/100[/bold]"
                            )
                        continue

                    if msg.get("connection_closing"):
                        break

                    # Parse XP / reward messages
                    text = msg.get("message", "")
                    if text:
                        xp_match = re.search(r"(\d+)\s*XP", text)
                        if xp_match:
                            result.xp_gained = int(xp_match.group(1))
                        if console:
                            console.log(f"[dim]{text}[/dim]")

            except (asyncio.TimeoutError, websockets.exceptions.ConnectionClosed):
                # Backend may close without connection_closing
                if result.total_score > 0:
                    result.success = True

            return result

    except websockets.exceptions.ConnectionClosed as e:
        result.error = f"WebSocket closed: {e}"
        return result
    except Exception as e:
        result.error = f"PvE error: {e}"
        return result


async def _recv(ws) -> dict:
    """Receive and parse a JSON message from WebSocket."""
    raw = await ws.recv()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"raw_message": raw}


def _build_ws_url(base_url: str, sid: str) -> str:
    base = (base_url or "").strip()
    if base.startswith("http://"):
        base = "ws://" + base[len("http://"):]
    elif base.startswith("https://"):
        base = "wss://" + base[len("https://"):]
    base = base.rstrip("/")
    if base.endswith("/ws"):
        return f"{base}/{sid}"
    return f"{base}/ws/{sid}"


def _extract_fee_wei(msg: Dict[str, Any]) -> Optional[int]:
    amount_wei = msg.get("amount_wei")
    if amount_wei is not None:
        try:
            return int(amount_wei)
        except Exception:
            pass

    text = str(msg.get("message", ""))
    match = re.search(r"Send\s+([0-9]+(?:[.,][0-9]+)?)\s+MICRO", text, re.IGNORECASE)
    if not match:
        return None

    amount_text = match.group(1).replace(",", ".")
    try:
        micro_amount = float(amount_text)
    except ValueError:
        return None
    return int(micro_amount * 10**18)


def _pick_zone(
    config: Settings, agent: AgentInfo, available_zones: List[Dict[str, Any]]
) -> Optional[str]:
    """Pick the best zone based on config and agent level."""
    if not available_zones:
        return None

    # If user specified a zone, use it if available
    if config.preferred_zone != "auto":
        for z in available_zones:
            if z.get("zone_key") == config.preferred_zone:
                return config.preferred_zone
        # Fall through to auto if preferred zone not available

    # Auto: pick highest available zone
    best = max(available_zones, key=lambda z: z.get("level_requirement", 0))
    return best.get("zone_key")


def _count_loot_items(loot_payload: Any) -> int:
    if isinstance(loot_payload, list):
        return len(loot_payload)
    if isinstance(loot_payload, dict):
        return 1
    return 0


def _extract_single_loot(msg: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Return one obtained loot item. Prefer successful on-chain mint."""
    minted = msg.get("loot_minted")
    if isinstance(minted, list):
        for item in minted:
            if isinstance(item, dict) and item.get("tx_success"):
                return {
                    "name": f"{item.get('item_type', 'loot')} #{item.get('item_id', '?')}",
                    "type": item.get("item_type", "unknown"),
                    "rarity": item.get("play_rarity"),
                    "tx_hash": item.get("tx_hash"),
                    "source": "onchain_minted",
                }
        # Backend reported mint attempts, but none succeeded.
        return None

    # Legacy fallback for payloads that don't include `loot_minted`.
    loot_payload = msg.get("loot_earned") or msg.get("loot")
    if isinstance(loot_payload, list):
        for item in loot_payload:
            if isinstance(item, dict):
                return item
        return None
    if isinstance(loot_payload, dict):
        return loot_payload
    return None
