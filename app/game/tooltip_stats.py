"""
Computed tooltip stats for actions and effects. Single source of truth for numeric values
shown in the UI. Used by the game-state endpoint to attach player1_action_tooltips / player2_action_tooltips.
"""
from typing import Any, Dict, List

from app.game.classes import get_attack_damage_range, get_heal_amount
from app.game.abilities import ABILITY_DEFS, get_ability, get_cooldown_turns


# Defend is always 50% reduction for 1 hit
DEFEND_REDUCTION_PCT = 50


def _scale_damage(min_dmg: int, max_dmg: int, multiplier: float) -> tuple:
    return (int(min_dmg * multiplier), int(max_dmg * multiplier))


def compute_action_tooltips(
    class_name: str,
    level: int,
    cooldowns: Dict[str, int],
) -> Dict[str, Dict[str, Any]]:
    """
    Compute tooltip stats for all actions available to a player.
    Uses a fake User-like object with class_name and level for get_attack_damage_range / get_heal_amount.
    Returns dict: action_id -> { damage_min, damage_max, heal_amount, shield_amount, duration, ... }.
    """
    class _FakeUser:
        def __init__(self, cn, lvl):
            self.class_name = cn
            self.level = lvl
    fake_user = _FakeUser(class_name, level) if class_name else None
    attack_min, attack_max = get_attack_damage_range(fake_user) if fake_user else (10, 20)
    heal_base = get_heal_amount(fake_user) if fake_user else 15

    out = {}

    # Attack (basic)
    out["attack"] = {
        "damage_min": attack_min,
        "damage_max": attack_max,
        "summary": f"Deal {attack_min}-{attack_max} damage.",
        "cooldown_total": 0,
        "cooldown_remaining": 0,
    }

    # Defend
    out["defend"] = {
        "reduction_pct": DEFEND_REDUCTION_PCT,
        "duration": 1,
        "summary": f"Next attack against you reduced by {DEFEND_REDUCTION_PCT}%.",
        "cooldown_total": 0,
        "cooldown_remaining": 0,
    }

    # Heal
    out["heal"] = {
        "heal_amount": heal_base,
        "summary": f"Heal for {heal_base} HP.",
        "cooldown_total": 0,
        "cooldown_remaining": 0,
    }

    abilities = ABILITY_DEFS.get(class_name, [])
    for ab in abilities:
        aid = ab.get("id", "")
        cd_total = get_cooldown_turns(ab)
        cd_remaining = cooldowns.get(aid, 0)

        entry = {
            "cooldown_total": cd_total,
            "cooldown_remaining": cd_remaining,
        }

        if ab.get("type") == "attack":
            mult = ab.get("damage_multiplier", 1.0)
            dmin, dmax = _scale_damage(attack_min, attack_max, mult)
            entry["damage_min"] = dmin
            entry["damage_max"] = dmax
            summary_parts = [f"Deal {dmin}-{dmax} damage."]
            if ab.get("effect") and ab.get("effect_target") == "enemy":
                dur = ab.get("duration", 0)
                dot = ab.get("damage_per_tick", 0)
                chill_pct = ab.get("chill_damage_taken_pct")
                if dot:
                    summary_parts.append(f"Apply {dot} DoT/turn for {dur} turns.")
                elif chill_pct is not None:
                    pct = int((chill_pct or 0) * 100)
                    summary_parts.append(f"Apply Chill: target takes {pct}% more damage until end of your next turn.")
                else:
                    summary_parts.append(f"Apply debuff until end of your next turn.")
            if aid == "execute":
                thresh = int((ab.get("low_hp_threshold", 0.35) or 0) * 100)
                bonus = ab.get("bonus_multiplier", 1.6)
                bmin, bmax = _scale_damage(attack_min, attack_max, bonus)
                summary_parts.append(f"Below {thresh}% HP: {bmin}-{bmax} damage.")
            if aid == "backstab" and ab.get("effect_if_not_defending"):
                dot = ab.get("effect_if_not_defending_damage_per_tick", 5)
                dur = ab.get("effect_if_not_defending_duration", 2)
                summary_parts.append(f"If target not defending: apply Bleed {dot}/turn for {dur} turns.")
            if aid == "shadowstep" and ab.get("effect_also_self"):
                summary_parts.append("Grants Evasion (next hit avoided) to self.")
            entry["summary"] = " ".join(summary_parts)

        elif ab.get("type") == "heal":
            mult = ab.get("heal_multiplier", 1.0)
            h = int(heal_base * mult)
            entry["heal_amount"] = h
            entry["summary"] = f"Heal for {h} HP."

        elif ab.get("type") == "defend":
            entry["reduction_pct"] = DEFEND_REDUCTION_PCT
            entry["duration"] = 1
            entry["summary"] = f"Next attack reduced by {DEFEND_REDUCTION_PCT}%."

        elif ab.get("type") == "effect":
            hits = ab.get("hits_left")
            dur = ab.get("duration", 1)
            if hits is not None:
                if ab.get("reduction_pct") is not None and ab.get("reflect_pct") is not None:
                    red = int((ab["reduction_pct"] or 0) * 100)
                    ref = int((ab["reflect_pct"] or 0) * 100)
                    entry["reduction_pct"] = red
                    entry["reflect_pct"] = ref
                    entry["hits_left"] = hits
                    entry["summary"] = f"Next {hits} incoming hit(s) reduced by {red}%; reflect {ref}% of reduced amount. Expires end of your next turn if unused."
                elif ab.get("avoid_pct") is not None:
                    pct = int((ab["avoid_pct"] or 0) * 100)
                    entry["avoid_pct"] = pct
                    entry["summary"] = f"Avoid {pct}% of next incoming hit. Expires end of your next turn if unused."
                else:
                    entry["summary"] = "Next incoming hit. Expires end of your next turn if unused."
            else:
                entry["duration"] = dur
                if ab.get("absorb_flat") is not None:
                    entry["shield_amount"] = ab["absorb_flat"]
                    entry["summary"] = f"Absorb up to {ab['absorb_flat']} damage until end of your next turn."
                elif ab.get("reflect_pct") is not None:
                    pct = int((ab["reflect_pct"] or 0) * 100)
                    entry["reflect_pct"] = pct
                    entry["summary"] = f"Reflect {pct}% of damage dealt until end of your next turn."
                elif ab.get("avoid_pct") is not None:
                    pct = int((ab["avoid_pct"] or 0) * 100)
                    entry["avoid_pct"] = pct
                    entry["summary"] = f"Avoid {pct}% of next attack until end of your next turn."
                elif ab.get("damage_per_tick") is not None and ab.get("effect_target") == "enemy":
                    dot = ab["damage_per_tick"]
                    entry["damage_per_tick"] = dot
                    entry["summary"] = f"Apply {dot} damage/turn for {dur} turn(s)."
                elif ab.get("id") == "shapeshift":
                    dmg_boost = int((ab.get("damage_boost_pct") or 0) * 100)
                    def_boost = int((ab.get("defense_boost_pct") or 0) * 100)
                    heal_boost = int((ab.get("heal_boost_pct") or 0) * 100)
                    entry["damage_boost_pct"] = dmg_boost
                    entry["defense_boost_pct"] = def_boost
                    entry["heal_boost_pct"] = heal_boost
                    entry["summary"] = f"+{dmg_boost}% damage, +{def_boost}% damage reduction, +{heal_boost}% healing until end of your next turn."
                elif ab.get("id") == "battle_shout":
                    flat = ab.get("flat_damage_bonus", 5)
                    red = int((ab.get("damage_reduction_pct") or 0) * 100)
                    entry["flat_damage_bonus"] = flat
                    entry["damage_reduction_pct"] = red
                    entry["summary"] = f"+{flat} flat damage to attacks, +{red}% damage reduction until end of your next turn."
                else:
                    entry["summary"] = f"Buff until end of your next turn."

        out[aid] = entry

    return out


def compute_effect_tooltip(effect: Dict[str, Any]) -> Dict[str, Any]:
    """
    Given an effect dict (name, turns_left, hits_left, value, damage_per_tick, reflect_pct, avoid_pct, etc.),
    return tooltip fields for the UI.
    """
    name = effect.get("name", "unknown")
    turns = effect.get("turns_left", 0)
    hits = effect.get("hits_left")
    out = {"name": name, "turns_left": turns}

    if effect.get("flat_damage_bonus") is not None and effect.get("damage_reduction_pct") is not None:
        flat = effect["flat_damage_bonus"]
        red = int((effect["damage_reduction_pct"] or 0) * 100)
        out["flat_damage_bonus"] = flat
        out["damage_reduction_pct"] = red
        out["summary"] = f"+{flat} flat damage, +{red}% damage reduction until end of your next turn."
    elif hits is not None:
        if effect.get("reduction_pct") is not None and effect.get("reflect_pct") is not None:
            red = int((effect["reduction_pct"] or 0) * 100)
            ref = int((effect["reflect_pct"] or 0) * 100)
            out["reduction_pct"] = red
            out["reflect_pct"] = ref
            out["hits_left"] = hits
            out["summary"] = f"Next {hits} incoming hit(s) reduced by {red}%; reflect {ref}% of reduced amount. Does not expire if unused."
        elif effect.get("avoid_pct") is not None:
            pct = int((effect["avoid_pct"] or 0) * 100)
            out["avoid_pct"] = pct
            out["summary"] = f"Avoids {pct}% of next incoming hit. Does not expire if unused."
        else:
            out["summary"] = "Does not expire if unused."
    elif effect.get("damage_taken_pct") is not None:
        pct = int((effect["damage_taken_pct"] or 0) * 100)
        out["summary"] = f"Target takes {pct}% more damage until end of your next turn. {turns} turn(s) left."
    elif effect.get("value") is not None:
        out["shield_amount"] = effect["value"]
        out["summary"] = f"Absorbs up to {effect['value']} damage until end of your next turn. {turns} turn(s) left."
    elif effect.get("damage_per_tick"):
        out["damage_per_tick"] = effect["damage_per_tick"]
        out["summary"] = f"{effect['damage_per_tick']} damage/turn. {turns} turn(s) left."
    elif effect.get("reflect_pct") is not None:
        pct = int((effect["reflect_pct"] or 0) * 100)
        out["reflect_pct"] = pct
        out["summary"] = f"Reflects {pct}% damage until end of your next turn. {turns} turn(s) left."
    elif effect.get("avoid_pct") is not None:
        pct = int((effect["avoid_pct"] or 0) * 100)
        out["avoid_pct"] = pct
        out["summary"] = f"Avoids {pct}% of next attack until end of your next turn. {turns} turn(s) left."
    elif name == "shapeshift":
        # Use ability def for shapeshift numbers
        for class_abilities in ABILITY_DEFS.values():
            for ab in class_abilities:
                if ab.get("id") == "shapeshift":
                    out["damage_boost_pct"] = int((ab.get("damage_boost_pct") or 0) * 100)
                    out["defense_boost_pct"] = int((ab.get("defense_boost_pct") or 0) * 100)
                    out["heal_boost_pct"] = int((ab.get("heal_boost_pct") or 0) * 100)
                    out["summary"] = f"+{out['damage_boost_pct']}% damage, +{out['defense_boost_pct']}% reduction, +{out['heal_boost_pct']}% healing until end of your next turn. {turns} turn(s) left."
                    return out
        out["summary"] = f"Transform. {turns} turn(s) left."
    else:
        out["summary"] = f"{turns} turn(s) left."

    return out
