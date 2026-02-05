"""
Centralized combat log message builder. Renders structured events to human-readable
strings with consistent grammar and tense. All damage/result lines use past tense;
ongoing states use present continuous. Action name (action_key) is always included.
"""

from typing import Any, Dict, Optional


# Human-readable action labels (snake_case -> display)
ACTION_LABELS = {
    "attack": "Basic Attack",
    "defend": "Defend",
    "heal": "Heal",
    "power_strike": "Power Strike",
    "shield_wall": "Shield Wall",
    "execute": "Execute",
    "battle_shout": "Battle Shout",
    "fireball": "Fireball",
    "ice_bolt": "Ice Bolt",
    "arcane_shield": "Arcane Shield",
    "meteor": "Meteor",
    "regrowth": "Regrowth",
    "thorns": "Thorns",
    "shapeshift": "Shapeshift",
    "nature_wrath": "Nature Wrath",
    "backstab": "Backstab",
    "evade": "Evade",
    "poison": "Poison",
    "shadowstep": "Shadowstep",
    "shadowstep_buff": "Shadowstep",
    "bleed": "Bleed",
    "chill": "Chill",
    "dot_tick": "DoT",
    "damage_absorbed": "Absorb",
    "damage_reflected": "Reflect",
    "evade_avoided": "Evade",
    "effect_applied": "Effect",
    "effect_expired": "Effect",
}


def _label(action_key: str) -> str:
    """Return human-readable action/effect name."""
    return ACTION_LABELS.get(action_key, action_key.replace("_", " ").title())


def format_combat_log_message(
    event: Dict[str, Any],
    viewer_id: Optional[int],
    actor_username: str,
    target_username: Optional[str] = None,
    attacker_username: Optional[str] = None,
    defender_username: Optional[str] = None,
) -> str:
    """
    Render a single combat log event to a string for the given viewer.
    - viewer_id: the player reading the log (for "You" vs username).
    - Usernames are already resolved (actor_username, target_username, etc.).
    Grammar: past tense for results (damage, heal, applied); present continuous for ongoing (blocking).
    Action name is always included via action_key.
    """
    action_type = event.get("action_type", "")
    action_key = event.get("action_key", action_type)
    label = _label(action_key)

    def _you_or(name: str, id_val: Optional[int]) -> str:
        if id_val is not None and viewer_id is not None and id_val == viewer_id:
            return "You"
        return name or "Unknown"

    # ---- Attack / damage dealt ----
    if action_type == "attack" or (
        event.get("damage") is not None
        and (event.get("attacker_id") is not None or event.get("defender_id") is not None)
    ):
        att_id = event.get("attacker_id")
        def_id = event.get("defender_id")
        att_name = _you_or(attacker_username or "", att_id)
        def_name = _you_or(defender_username or "", def_id)
        dmg = event.get("damage", 0)
        defended = event.get("defended", False)
        parts = [f"{att_name} dealt {dmg} damage to {def_name} with {label}."]
        if event.get("damage_bonus_shapeshift", 0) > 0:
            parts.append(f" Increased by {event['damage_bonus_shapeshift']} for Shapeshift.")
        if event.get("damage_bonus_battle_shout", 0) > 0:
            parts.append(f" Increased by {event['damage_bonus_battle_shout']} for Battle Shout.")
        if event.get("damage_bonus_chill", 0) > 0:
            parts.append(f" Increased by {event['damage_bonus_chill']} for Chill.")
        if event.get("damage_reduced_defend", 0) > 0:
            parts.append(f" Reduced by {event['damage_reduced_defend']} (blocked).")
        elif defended:
            parts.append(" (blocked, reduced damage)")
        if event.get("damage_reduced_battle_shout", 0) > 0:
            parts.append(f" Reduced by {event['damage_reduced_battle_shout']} (Battle Shout).")
        if event.get("damage_reduced_shapeshift", 0) > 0:
            parts.append(f" Reduced by {event['damage_reduced_shapeshift']} (Shapeshift).")
        if event.get("damage_reduced_shield_wall", 0) > 0:
            parts.append(f" Reduced by {event['damage_reduced_shield_wall']} (Shield Wall).")
        if event.get("damage_reflected_shield_wall", 0) > 0:
            parts.append(f" Reflected {event['damage_reflected_shield_wall']} to attacker (Shield Wall).")
        if event.get("damage_absorbed_arcane_shield", 0) > 0:
            parts.append(f" Absorbed {event['damage_absorbed_arcane_shield']} (Arcane Shield).")
        if event.get("damage_reflected_thorns", 0) > 0:
            parts.append(f" Reflected {event['damage_reflected_thorns']} to attacker (Thorns).")
        if event.get("evaded", False):
            parts.append(" Evaded.")
        return "".join(parts)

    # ---- Heal ----
    if event.get("healed") is not None and event.get("actor_id") is not None:
        actor_id = event.get("actor_id")
        actor_name = _you_or(actor_username or "", actor_id)
        healed = event.get("healed", 0)
        msg = f"{actor_name} healed {healed} HP with {label}."
        if event.get("heal_bonus_shapeshift", 0) > 0:
            msg += f" Increased by {event['heal_bonus_shapeshift']} for Shapeshift."
        return msg

    # ---- Defend (past: used; effect described) ----
    if action_type == "defend":
        actor_id = event.get("actor_id")
        actor_name = _you_or(actor_username or "", actor_id)
        return f"{actor_name} used {label}. Next incoming hit will be reduced by 50%."

    # ---- DoT tick (past tense: took damage from effect) ----
    if action_type == "dot_tick":
        target_id = event.get("target_id")
        target_name = _you_or(target_username or "", target_id)
        effect_name = _label(event.get("effect", "unknown"))
        dmg = event.get("damage", 0)
        turns = event.get("turns_left", 0)
        t = "turn" if turns == 1 else "turns"
        return f"{target_name} took {dmg} {effect_name} damage ({turns} {t} remaining)."

    # ---- Damage absorbed ----
    if action_type == "damage_absorbed":
        effect_name = _label(event.get("effect", "unknown"))
        amount = event.get("amount", 0)
        def_id = event.get("defender_id")
        def_name = _you_or(defender_username or "", def_id)
        return f"{effect_name} reduced damage to {def_name} by {amount}."

    # ---- Damage reflected ----
    if action_type == "damage_reflected":
        def_id = event.get("defender_id")
        att_id = event.get("attacker_id")
        def_name = _you_or(defender_username or "", def_id)
        att_name = _you_or(attacker_username or "", att_id)
        effect_name = _label(event.get("effect", "thorns"))
        amount = event.get("amount", 0)
        # Never "You's" — use "Your" for viewer-owned effects
        possessive = "Your" if (viewer_id is not None and def_id == viewer_id) else f"{def_name}'s"
        return f"{possessive} {effect_name} reflected {amount} damage to {att_name}."

    # ---- Evade (attack avoided) ----
    if action_type == "evade_avoided":
        def_id = event.get("defender_id")
        def_name = _you_or(defender_username or "", def_id)
        return f"{def_name} evaded the attack."

    # ---- Effect applied ----
    if action_type == "effect_applied":
        actor_id = event.get("actor_id")
        actor_name = _you_or(actor_username or "", actor_id)
        target_id = event.get("target_id")
        target_name = _you_or(target_username or "", target_id)
        effect_name = _label(event.get("effect", "unknown"))
        duration = event.get("duration", 1)
        hits = event.get("hits_left")
        if hits is not None:
            if hits == 1:
                return f"{actor_name} used {label}. {effect_name} will apply to the next incoming hit (does not expire if unused)."
            else:
                return f"{actor_name} used {label}. {effect_name} will apply to the next {hits} incoming hit(s) (does not expire if unused)."
        if event.get("effect") == "battle_shout":
            return f"{actor_name} used {label}. +flat damage and damage reduction until end of your next turn."
        return f"{actor_name} applied {effect_name} to {target_name}."

    # ---- Effect expired ----
    if action_type == "effect_expired":
        target_id = event.get("target_id")
        target_name = _you_or(target_username or "", target_id)
        effect_name = _label(event.get("effect", "unknown"))
        return f"{effect_name} on {target_name} expired."

    # ---- Generic fallback ----
    actor_id = event.get("actor_id") or event.get("attacker_id")
    actor_name = _you_or(actor_username or "", actor_id)
    return f"{actor_name} used {label}."


def get_tone_for_event(event: Dict[str, Any]) -> str:
    """Return tone for display: damage, heal, defend, buff, neutral."""
    action_type = event.get("action_type", "")
    if action_type in ("dot_tick", "damage_reflected") or event.get("damage") is not None:
        return "damage"
    if event.get("healed") is not None:
        return "heal"
    if action_type == "defend":
        return "defend"
    if action_type in ("damage_absorbed", "evade_avoided", "effect_applied", "effect_expired"):
        return "buff"
    return "neutral"


def build_display_entry(
    event: Dict[str, Any],
    viewer_id: Optional[int],
) -> Dict[str, Any]:
    """
    Build a single combat_log_display entry: { message, tone, is_my_action }.
    Event must already have *_username fields set.
    """
    actor_id = event.get("actor_id") or event.get("attacker_id")
    is_my_action = viewer_id is not None and actor_id == viewer_id

    message = format_combat_log_message(
        event,
        viewer_id=viewer_id,
        actor_username=event.get("actor_username") or "",
        target_username=event.get("target_username"),
        attacker_username=event.get("attacker_username"),
        defender_username=event.get("defender_username"),
    )
    tone = get_tone_for_event(event)
    return {"message": message, "tone": tone, "is_my_action": is_my_action}
