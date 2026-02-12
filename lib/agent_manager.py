"""Agent housekeeping — level up, equip best items, burn for XP."""

from typing import Optional

from console_compat import Console

from blockchain import AgentInfo, BlockchainService
from config_openclaw import Settings
from constants import (
    LEVEL_REQUIREMENTS,
    TRAIT_GATE_LEVELS,
    EQUIPMENT_SLOTS,
    SLOT_IDS,
)


def try_level_up(
    chain: BlockchainService,
    agent: AgentInfo,
    console: Optional[Console] = None,
) -> bool:
    """Check if agent can level up, and do it. Returns True if leveled up."""
    next_level = agent.level + 1
    if next_level not in LEVEL_REQUIREMENTS:
        return False

    required_xp = LEVEL_REQUIREMENTS[next_level]
    if agent.exp < required_xp:
        return False

    # Check trait gate
    trait_id = 0
    if next_level in TRAIT_GATE_LEVELS:
        needed, options = chain.get_next_level_trait_options(agent.token_id)
        if needed:
            if not options:
                if console:
                    console.log(
                        f"[yellow]Level {next_level} requires a trait but none available — "
                        f"skipping level-up[/yellow]"
                    )
                return False
            trait_id = options[0]  # Pick first available trait
            if console:
                console.log(f"Using trait #{trait_id} for level gate")

    stat_name = agent.best_stat_name
    if console:
        console.log(
            f"Leveling up to {next_level} (+1 {stat_name})..."
        )

    try:
        tx_hash = chain.level_up(agent.token_id, stat_name, trait_id)
        chain.wait_for_tx(tx_hash)
        if console:
            console.log(f"[green]Leveled up to {next_level}![/green] (tx: {tx_hash[:10]}...)")
        return True
    except Exception as e:
        if console:
            console.log(f"[red]Level-up failed: {e}[/red]")
        return False


def try_equip_best(
    chain: BlockchainService,
    config: Settings,
    agent: AgentInfo,
    console: Optional[Console] = None,
) -> bool:
    """Check inventory and equip better items if available. Returns True if anything changed."""
    changed = False
    slot_contracts = {
        "weapon": config.weapons_contract,
        "armor": config.armors_contract,
        "software": config.softwares_contract,
        "cpu": config.cpus_contract,
    }
    equipped_map = {
        "weapon": agent.equipped_weapon,
        "armor": agent.equipped_armor,
        "software": agent.equipped_software,
        "cpu": agent.equipped_cpu,
    }

    for slot in EQUIPMENT_SLOTS:
        contract_addr = slot_contracts[slot]
        current_id = equipped_map[slot]

        # Get current equipped item's stat bonus (0 if nothing equipped)
        current_bonus = 0
        if current_id > 0:
            try:
                current_bonus = chain.get_item_stat(slot, current_id)
            except Exception:
                pass

        # Scan common item IDs (1-50) for better options
        best_id = current_id
        best_bonus = current_bonus
        for item_id in range(1, 51):
            try:
                balance = chain.get_item_balance(slot, item_id)
                if balance <= 0:
                    continue
                # Check level range
                min_lvl, max_lvl = chain.get_item_level_range(slot, item_id)
                if agent.level < min_lvl or agent.level > max_lvl:
                    continue
                bonus = chain.get_item_stat(slot, item_id)
                if bonus > best_bonus:
                    best_bonus = bonus
                    best_id = item_id
            except Exception:
                continue

        if best_id != current_id and best_id > 0:
            try:
                # Ensure ERC1155 approval
                chain.ensure_erc1155_approval(slot)

                # Unequip current if needed
                if current_id > 0:
                    tx = chain.unequip_item(agent.token_id, contract_addr)
                    chain.wait_for_tx(tx)

                # Equip new item
                tx = chain.equip_item(agent.token_id, contract_addr, best_id)
                chain.wait_for_tx(tx)
                changed = True
                if console:
                    console.log(
                        f"[green]Equipped {slot} #{best_id} "
                        f"(+{best_bonus} stat bonus)[/green]"
                    )
            except Exception as e:
                if console:
                    console.log(f"[yellow]Equip {slot} #{best_id} failed: {e}[/yellow]")

    return changed


def try_burn_items(
    chain: BlockchainService,
    config: Settings,
    agent: AgentInfo,
    console: Optional[Console] = None,
) -> bool:
    """Burn excess common items for XP. Returns True if anything was burned."""
    burned = False

    for slot, slot_id in SLOT_IDS.items():
        for item_id in range(1, 21):
            try:
                balance = chain.get_item_balance(slot, item_id)
                # Keep 1, burn the rest
                if balance <= 1:
                    continue
                burn_amount = balance - 1

                chain.ensure_erc1155_approval(slot)
                tx = chain.burn_items_for_xp(
                    agent.token_id, slot_id, item_id, burn_amount
                )
                chain.wait_for_tx(tx)
                burned = True
                if console:
                    console.log(
                        f"[green]Burned {burn_amount}x {slot} #{item_id} for XP[/green]"
                    )
            except Exception:
                continue

    return burned
