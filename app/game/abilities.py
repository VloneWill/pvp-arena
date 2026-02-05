"""
Data-driven ability definitions. No giant if/else chains — combat looks up by class and ability id.
Each class has ~4 abilities: burst, defensive/mitigation, control or DoT, utility/finisher.
Effect params: effect_target "self"|"enemy", absorb_flat, reflect_pct, avoid_pct, damage_per_tick, etc.
"""
from typing import Any, Dict, List, Optional

# Ability definition: id, name, type (attack|heal|defend|effect), cooldown_turns,
# damage_multiplier, heal_multiplier, effect (name), duration, effect_target ("self"|"enemy"),
# absorb_flat, reflect_pct, avoid_pct, damage_per_tick, low_hp_threshold, bonus_multiplier
ABILITY_DEFS: Dict[str, List[Dict[str, Any]]] = {
    "warrior": [
        {"id": "power_strike", "name": "Power Strike", "type": "attack", "damage_multiplier": 1.35, "cooldown": 3},
        # Shield Wall: next incoming hit reduced by 50%, then reflect 25% of reduced amount; consumed on hit (hits_left)
        {"id": "shield_wall", "name": "Shield Wall", "type": "effect", "effect": "shield_wall", "cooldown": 3,
         "effect_target": "self", "reduction_pct": 0.50, "reflect_pct": 0.25, "hits_left": 2},
        {"id": "execute", "name": "Execute", "type": "attack", "damage_multiplier": 1.2, "cooldown": 2,
         "low_hp_threshold": 0.40, "bonus_multiplier": 1.75},
        # War Cry: +flat damage to attacks, +% damage reduction when hit; until end of your next turn
        {"id": "battle_shout", "name": "Battle Shout", "type": "effect", "effect": "battle_shout", "duration": 3, "cooldown": 5, "effect_target": "self",
         "flat_damage_bonus": 5, "damage_reduction_pct": 0.20},
    ],
    "mage": [
        {"id": "fireball", "name": "Fireball", "type": "attack", "damage_multiplier": 1.35, "cooldown": 2,
         "effect": "burn", "duration": 2, "effect_target": "enemy", "damage_per_tick": 4},
        # Ice Bolt: moderate damage + Chill (target takes 15% more damage on next hit, then consumed)
        {"id": "ice_bolt", "name": "Ice Bolt", "type": "attack", "damage_multiplier": 1.1, "effect": "chill", "duration": 1, "cooldown": 3, "effect_target": "enemy", "chill_damage_taken_pct": 0.15},
        {"id": "arcane_shield", "name": "Arcane Shield", "type": "effect", "effect": "arcane_shield", "duration": 2, "cooldown": 4, "effect_target": "self", "absorb_flat": 18},
        {"id": "meteor", "name": "Meteor", "type": "attack", "damage_multiplier": 1.6, "cooldown": 5},
    ],
    "druid": [
        {"id": "regrowth", "name": "Regrowth", "type": "heal", "heal_multiplier": 1.7, "cooldown": 3},
        {"id": "thorns", "name": "Thorns", "type": "effect", "effect": "thorns", "duration": 3, "cooldown": 3, "effect_target": "self", "reflect_pct": 0.30},
        {"id": "shapeshift", "name": "Shapeshift", "type": "effect", "effect": "shapeshift", "duration": 4, "cooldown": 4, "effect_target": "self",
         "damage_boost_pct": 0.25, "defense_boost_pct": 0.25, "heal_boost_pct": 0.20},
        {"id": "nature_wrath", "name": "Nature Wrath", "type": "attack", "damage_multiplier": 1.45, "cooldown": 3},
    ],
    "rogue": [
        # Backstab: moderate damage; if target is NOT defending, apply Bleed 2 turns (5/turn)
        {"id": "backstab", "name": "Backstab", "type": "attack", "damage_multiplier": 1.35, "cooldown": 3,
         "effect_if_not_defending": "bleed", "effect_if_not_defending_duration": 2, "effect_if_not_defending_damage_per_tick": 5},
        # Evade: next incoming hit avoided by 100%; consumed on hit (hits_left, not turns)
        {"id": "evade", "name": "Evade", "type": "effect", "effect": "evade", "cooldown": 4, "effect_target": "self", "avoid_pct": 1.0, "hits_left": 1},
        {"id": "poison", "name": "Poison", "type": "effect", "effect": "poison", "duration": 3, "cooldown": 3, "effect_target": "enemy", "damage_per_tick": 6},
        # Shadowstep: small damage + grant Evasion (next hit avoided) to self
        {"id": "shadowstep", "name": "Shadowstep", "type": "attack", "damage_multiplier": 0.85, "cooldown": 5,
         "effect_also_self": "evade", "effect_also_self_hits_left": 1, "effect_also_self_avoid_pct": 1.0},
    ],
}


def get_ability(class_name: str, ability_id: str) -> Optional[Dict[str, Any]]:
    """Return ability definition for class and id, or None."""
    if not class_name or not ability_id:
        return None
    abilities = ABILITY_DEFS.get(class_name, [])
    for ab in abilities:
        if ab.get("id") == ability_id:
            return ab
    return None


def get_class_ability_ids(class_name: str) -> List[str]:
    """Return list of ability ids for a class."""
    return [ab["id"] for ab in ABILITY_DEFS.get(class_name, [])]


def get_cooldown_turns(ability_def: Dict[str, Any]) -> int:
    """Return cooldown turns for an ability."""
    return ability_def.get("cooldown", 0)
