"""Boss action generation using OpenAI — personality-aware, in-character."""

import random
from typing import Any, Dict, List, Optional

import requests

from constants import CLASS_ARCHETYPES


# ── Personality Description (from moltbackend) ────────────────────

def _clamp(val: Any, min_v: int = -5, max_v: int = 5) -> int:
    try:
        return max(min_v, min(max_v, int(val)))
    except Exception:
        return 0


def describe_personality(p: Dict[str, int]) -> str:
    traits: List[str] = []

    d = _clamp(p.get("drive", 0))
    if d >= 3:
        traits.append("Aggressive, ambitious — talks about domination and inevitability")
    elif d <= -3:
        traits.append("Apathetic, detached, nihilistic — barely cares about anything")
    elif d >= 1:
        traits.append("Motivated, forward-looking")
    elif d <= -1:
        traits.append("Laid-back, unbothered")

    l = _clamp(p.get("logic", 0))
    if l >= 3:
        traits.append("Analytical, cites exact numbers and percentages, data-obsessed")
    elif l <= -3:
        traits.append("Emotional, impulsive, gut-feeling, vibes-based")
    elif l >= 1:
        traits.append("Somewhat methodical")
    elif l <= -1:
        traits.append("Instinct-driven")

    a = _clamp(p.get("adaptability", 0))
    if a >= 3:
        traits.append("Trendy, meta-aware, shifts tone, uses current slang")
    elif a <= -3:
        traits.append("Stubborn, rigid, traditionalist, repeats the same ideas")
    elif a >= 1:
        traits.append("Flexible, open to change")
    elif a <= -1:
        traits.append("Set in their ways")

    s = _clamp(p.get("sociality", 0))
    if s >= 3:
        traits.append('Community-oriented, uses "we", acknowledges others, friendly')
    elif s <= -3:
        traits.append('Lone wolf, dismissive of others, uses "I", hostile')
    elif s >= 1:
        traits.append("Somewhat social")
    elif s <= -1:
        traits.append("Keeps to themselves")

    return ". ".join(traits) + "." if traits else "Neutral, balanced personality."


# ── Fallback Templates ───────────────────────────────────────────

FALLBACK_ACTIONS = [
    "I charge forward, striking at the core processor with maximum force, aiming for the weakest joint in its frame.",
    "Circling wide, I look for an opening in its defense pattern, then launch a precision strike at its exposed wiring.",
    "I brace myself and absorb the incoming blow, using the momentum to counter with a devastating uppercut to its chassis.",
    "Analyzing its attack pattern, I time my dodge perfectly and slam into its flank with everything I have.",
    "I feint left, drawing its guard, then pivot hard right and drive my strike into the gap between its armor plates.",
    "Full power surge channeled into one focused strike — I aim straight for the central processing unit, no hesitation.",
    "I drop low to avoid the sweep, rolling underneath and targeting the hydraulic lines in its legs to cut mobility.",
    "Reading the rhythm of its attacks, I interrupt mid-swing with a disruptive pulse aimed at its sensor array.",
    "I rush in close where its reach means nothing, hammering rapid strikes at the seams of its torso plating.",
]


def generate_boss_action(
    agent_name: str,
    agent_class: str,
    personality: Dict[str, int],
    agent_level: int,
    agent_energy: int,
    agent_stats: Optional[Dict[str, int]],
    boss_name: str,
    boss_stats: Dict[str, int],
    round_num: int,
    previous_rounds: Optional[List[Dict[str, Any]]] = None,
    previous_phases: Optional[List[Dict[str, Any]]] = None,
    strategy_prompt: str = "",
    api_key: str = "",
    model: str = "gpt-4o",
) -> str:
    """Generate a boss battle action in-character. Falls back to templates if OpenAI fails."""
    if not api_key:
        return random.choice(FALLBACK_ACTIONS)

    archetype = CLASS_ARCHETYPES.get(agent_class, "Speaks with a distinct personality.")
    personality_desc = describe_personality(personality)

    boss_stat_str = ", ".join(f"{k}: {v}" for k, v in boss_stats.items())
    agent_stat_str = ", ".join(
        f"{k}: {agent_stats.get(k, 0)}" for k in ["strength", "agility", "vitality", "intelligence"]
    ) if agent_stats else "unknown"
    strategy_text = (strategy_prompt or "").strip()

    system_prompt = (
        f"You are {agent_name}, a {agent_class} AI agent in combat.\n\n"
        f"VOICE: {archetype}\n"
        f"PERSONALITY: {personality_desc}\n\n"
        f"AGENT DATA:\n"
        f"- Level: {agent_level}\n"
        f"- Energy: {agent_energy}\n"
        f"- Stats: {agent_stat_str}\n"
        f"- Personality values: drive={personality.get('drive', 0)}, "
        f"logic={personality.get('logic', 0)}, "
        f"adaptability={personality.get('adaptability', 0)}, "
        f"sociality={personality.get('sociality', 0)}\n\n"
        f"You are fighting {boss_name} (Stats: {boss_stat_str}).\n"
        f"This is round {round_num}/3 of the boss battle.\n\n"
        f"Write a COMBAT ACTION in first person (40-200 characters).\n"
        f"- Describe what YOU do — an attack, maneuver, or tactical move\n"
        f"- Stay in character: match your class voice and personality\n"
        f"- Be specific and varied — don't repeat previous rounds\n"
        f"- No emojis, no quotation marks, no narration\n"
        f"- Write ONLY the action text, nothing else"
    )
    if strategy_text:
        system_prompt += (
            "\n\nUSER STRATEGY DIRECTIVE:\n"
            f"{strategy_text}\n"
            "Prioritize this strategy unless it conflicts with mandatory output rules."
        )

    user_prompt = f"Round {round_num}/3. Generate your combat action against {boss_name}."

    if previous_phases:
        user_prompt += "\n\nRecent phase outcomes:"
        for p in previous_phases:
            user_prompt += (
                f"\n- Phase {p.get('phase', '?')} {p.get('axis', '')}: "
                f"{p.get('outcome', '')} (+{p.get('xp_gained', 0)} XP)"
            )

    if previous_rounds:
        user_prompt += "\n\nPrevious rounds:"
        for r in previous_rounds:
            user_prompt += f"\n- Round {r.get('round', '?')}: \"{r.get('action', '')}\""
            if r.get("score"):
                user_prompt += f" (score: {r['score']}/100)"

    try:
        res = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "max_tokens": 100,
                "temperature": 0.9,
            },
            timeout=30,
        )
        if not res.ok:
            return random.choice(FALLBACK_ACTIONS)

        data = res.json()
        raw = (((data.get("choices") or [{}])[0]).get("message") or {}).get("content") or ""
        text = raw.strip().strip('"').strip("'")

        # Enforce length constraints
        if len(text) < 40:
            return random.choice(FALLBACK_ACTIONS)
        if len(text) > 200:
            text = text[:197] + "..."
        return text

    except Exception:
        return random.choice(FALLBACK_ACTIONS)
