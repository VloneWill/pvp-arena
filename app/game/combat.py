"""
Turn-based combat logic with class-based stats and data-driven abilities.
Uses app.game.abilities for definitions; no giant if/else chains.
"""
import random
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.db.models import Match, User
from app.game.classes import (
    get_max_hp,
    get_attack_damage_range,
    get_heal_amount,
    award_match_xp,
)
from app.game.abilities import get_ability, get_cooldown_turns


# Combat constants
DEFEND_DAMAGE_REDUCTION = 0.5  # 50% damage reduction
TURN_DURATION_SECONDS = 30


def _now_utc() -> datetime:
    """Current time in UTC for turn timers."""
    return datetime.now(timezone.utc)


def _set_turn_timers(match: Match, now: Optional[datetime] = None) -> None:
    """Set turn_started_at and turn_expires_at for the current turn."""
    if now is None:
        now = _now_utc()
    match.turn_started_at = now
    match.turn_expires_at = now + timedelta(seconds=TURN_DURATION_SECONDS)


def apply_turn_timeout_if_needed(match: Match, now: Optional[datetime] = None) -> None:
    """
    If the match is active and the current turn has expired, switch turn to the
    other player and reset turn timers. No match history or forfeit; turn switch only.
    Caller must commit the session after this if changes were made.
    """
    if match.status != "active":
        return
    if now is None:
        now = _now_utc()
    if match.turn_expires_at is None:
        _set_turn_timers(match, now)
        return
    expires = match.turn_expires_at
    if getattr(expires, "tzinfo", None) is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if now <= expires:
        return
    # Expired: switch turn and reset timers
    if match.current_turn == match.player1_id:
        match.current_turn = match.player2_id
    else:
        match.current_turn = match.player1_id
    _set_turn_timers(match, now)


#create the invalid action error class
class InvalidActionError(ValueError):
    """Base error for invalid combat actions."""


#create the match not active error class
class MatchNotActiveError(InvalidActionError):
    """Raised when trying to perform an action on a match that is not active."""


#create the check match active function
def _check_match_active(match: Match) -> None:
    """Check if match is active, raise MatchNotActiveError if not."""
    if match.status != "active":
        raise MatchNotActiveError(f"Match is not active (status: {match.status})")


#create the check actor valid and alive function
def _check_actor_valid_and_alive(match: Match, actor_id: int) -> None:
    """Ensure actor is one of the players and not dead."""
    if actor_id not in (match.player1_id, match.player2_id):
        raise InvalidActionError("Actor must be one of the match players")

    if actor_id == match.player1_id and match.player1_health <= 0:
        raise InvalidActionError("Dead player cannot act")
    if actor_id == match.player2_id and match.player2_health <= 0:
        raise InvalidActionError("Dead player cannot act")


def _get_user_for_player(match: Match, player_id: int, db: Session) -> Optional[User]:
    """Get User object for a player in the match."""
    return db.query(User).filter(User.id == player_id).first()


def _add_combat_log_event(match: Match, event: Dict[str, Any], db: Session) -> None:
    """Add a combat log event with usernames."""
    if match.combat_log is None:
        match.combat_log = []  # type: ignore[assignment]
    
    # Ensure event has usernames
    if "actor_id" in event and "actor_username" not in event:
        actor = _get_user_for_player(match, event["actor_id"], db)
        event["actor_username"] = actor.username if actor else f"Player {event['actor_id']}"
    
    if "target_id" in event and "target_username" not in event:
        target = _get_user_for_player(match, event["target_id"], db)
        event["target_username"] = target.username if target else f"Player {event['target_id']}"
    
    if "attacker_id" in event and "attacker_username" not in event:
        attacker = _get_user_for_player(match, event["attacker_id"], db)
        event["attacker_username"] = attacker.username if attacker else f"Player {event['attacker_id']}"
    
    if "defender_id" in event and "defender_username" not in event:
        defender = _get_user_for_player(match, event["defender_id"], db)
        event["defender_username"] = defender.username if defender else f"Player {event['defender_id']}"
    
    match.combat_log.append(event)
    flag_modified(match, "combat_log")


def _get_cooldowns(match: Match, player_id: int) -> Dict[str, int]:
    """Return per-ability cooldowns for player (mutable dict)."""
    is_p1 = player_id == match.player1_id
    cooldowns = getattr(match, "player1_cooldowns", None) if is_p1 else getattr(match, "player2_cooldowns", None)
    if cooldowns is None:
        cooldowns = {}
        if is_p1:
            match.player1_cooldowns = cooldowns
        else:
            match.player2_cooldowns = cooldowns
    return cooldowns


def _get_effects(match: Match, player_id: int) -> List[Dict[str, Any]]:
    """Return active effects for player (mutable list)."""
    is_p1 = player_id == match.player1_id
    effects = getattr(match, "player1_effects", None) if is_p1 else getattr(match, "player2_effects", None)
    if effects is None:
        effects = []
        if is_p1:
            match.player1_effects = effects
        else:
            match.player2_effects = effects
    return effects


def _check_ability_cooldown_for_id(match: Match, player_id: int, ability_id: str) -> None:
    """Check if the given ability is on cooldown for this player."""
    cooldowns = _get_cooldowns(match, player_id)
    remaining = cooldowns.get(ability_id, 0)
    if remaining > 0:
        raise InvalidActionError(f"{ability_id} is on cooldown for {remaining} more turn(s)")


def _set_ability_cooldown_for_id(match: Match, player_id: int, ability_id: str, turns: int) -> None:
    """Set cooldown for an ability after use."""
    cooldowns = _get_cooldowns(match, player_id)
    cooldowns[ability_id] = turns
    is_p1 = player_id == match.player1_id
    flag_modified(match, "player1_cooldowns" if is_p1 else "player2_cooldowns")


def _tick_cooldowns_for_player(match: Match, player_id: int) -> None:
    """Decrement all cooldowns for the player who just ended their turn."""
    cooldowns = _get_cooldowns(match, player_id)
    for k in list(cooldowns.keys()):
        if cooldowns[k] > 0:
            cooldowns[k] -= 1
            if cooldowns[k] <= 0:
                del cooldowns[k]
    is_p1 = player_id == match.player1_id
    flag_modified(match, "player1_cooldowns" if is_p1 else "player2_cooldowns")


def _expire_effects_when_source_ends_turn(match: Match, player_ending_turn_id: int) -> None:
    """
    When the player who applied effects (source) ends their turn, decrement remaining_turns_until_expiry
    and remove effects that have expired. Effects last until end of caster's next turn (so Chill on B
    applied by A stays until A ends their next turn, giving A one more hit with Chill).
    DoT effects (turns_left + damage_per_tick) are NOT expired here; they tick in _apply_dot_ticks.
    """
    for player_id in (match.player1_id, match.player2_id):
        effects = _get_effects(match, player_id)
        to_remove = []
        for i, e in enumerate(effects):
            source_id = e.get("source_id")
            if source_id is None or source_id != player_ending_turn_id:
                continue
            # DoT effects expire by turns_left in _apply_dot_ticks, not here
            if e.get("damage_per_tick") and e.get("turns_left") is not None:
                continue
            # Hit-based effects (Shield Wall, Evade) never expire by turn; they last until consumed by hits
            if e.get("hits_left") is not None:
                continue
            remaining = e.get("remaining_turns_until_expiry")
            if remaining is None:
                to_remove.append(i)
                continue
            remaining -= 1
            e["remaining_turns_until_expiry"] = remaining
            e["turns_left"] = remaining
            if remaining <= 0:
                to_remove.append(i)
        for i in reversed(to_remove):
            effects.pop(i)
        is_p1 = player_id == match.player1_id
        flag_modified(match, "player1_effects" if is_p1 else "player2_effects")


def _consume_effect(match: Match, player_id: int, effect_name: str) -> Optional[Dict[str, Any]]:
    """Remove first effect with given name from player; return it or None."""
    effects = _get_effects(match, player_id)
    for i, e in enumerate(effects):
        if e.get("name") == effect_name:
            consumed = effects.pop(i)
            is_p1 = player_id == match.player1_id
            flag_modified(match, "player1_effects" if is_p1 else "player2_effects")
            return consumed
    return None

def _decrement_effect_hits_and_maybe_consume(match: Match, player_id: int, effect_name: str) -> bool:
    """Decrement hits_left on first effect with this name; remove if <= 0. Return True if effect was removed."""
    effects = _get_effects(match, player_id)
    for i, e in enumerate(effects):
        if e.get("name") != effect_name:
            continue
        hits = e.get("hits_left", 1)
        hits -= 1
        if hits <= 0:
            effects.pop(i)
        else:
            e["hits_left"] = hits
        is_p1 = player_id == match.player1_id
        flag_modified(match, "player1_effects" if is_p1 else "player2_effects")
        return hits <= 0
    return False


def _has_effect(match: Match, player_id: int, effect_name: str) -> bool:
    """Return True if player has an active effect with the given name."""
    effects = _get_effects(match, player_id)
    return any(e.get("name") == effect_name for e in effects)


def _get_effect_params(match: Match, player_id: int, effect_name: str) -> Optional[Dict[str, Any]]:
    """Return first effect dict with given name (for reading value/params)."""
    effects = _get_effects(match, player_id)
    for e in effects:
        if e.get("name") == effect_name:
            return e
    return None


def _check_ability_cooldown(match: Match, player_id: int) -> None:
    """Legacy: check single ability cooldown (for backward compat)."""
    cooldowns = _get_cooldowns(match, player_id)
    if any(v > 0 for v in cooldowns.values()):
        raise InvalidActionError("Ability is on cooldown")


#create the initialize match function
def initialize_match(match: Match, db: Session) -> None:
    """
    Initialize a match for combat.

    - Sets both players to full health based on their class/level.
    - Clears all defensive and ability flags.
    - Sets the current turn to player1 and turn_number to 1 (if not already set).
    - Ensures health is exactly equal to max_hp (no old defaults leak in).
    """
    if match.current_turn is None:
        match.current_turn = match.player1_id
        match.turn_number = 1
        _set_turn_timers(match)

        # Get players and compute max HP (single source of truth)
        p1 = _get_user_for_player(match, match.player1_id, db)
        p2 = _get_user_for_player(match, match.player2_id, db)
        
        # Compute max HP consistently
        p1_max_hp = get_max_hp(p1) if p1 else 100
        p2_max_hp = get_max_hp(p2) if p2 else 100
        
        # Set health to exactly max_hp (no old defaults, no inconsistencies)
        match.player1_health = p1_max_hp
        match.player2_health = p2_max_hp
        
        match.player1_defending = False
        match.player2_defending = False
        match.player1_ability_cooldown = 0
        match.player2_ability_cooldown = 0
        match.player1_ability_effect = None
        match.player2_ability_effect = None
        match.player1_cooldowns = getattr(match, "player1_cooldowns", None) or {}
        match.player2_cooldowns = getattr(match, "player2_cooldowns", None) or {}
        match.player1_effects = getattr(match, "player1_effects", None) or []
        match.player2_effects = getattr(match, "player2_effects", None) or []
        match.combat_log = []  # type: ignore[assignment]


def _apply_dot_ticks(match: Match, player_id: int, db: Session) -> None:
    """
    At start of turn: apply DoT damage to the given player for each effect that has damage_per_tick.
    Decrement turns_left and remove effect when 0. Emit combat log entries for each tick.
    """
    effects = _get_effects(match, player_id)
    is_p1 = player_id == match.player1_id
    to_remove = []
    for i, e in enumerate(effects):
        dmg_per_tick = e.get("damage_per_tick", 0)
        if dmg_per_tick <= 0:
            continue
        effect_name = e.get("name", "unknown")
        turns_left = e.get("turns_left", 1)
        current_hp = match.player1_health if is_p1 else match.player2_health
        actual_damage = min(dmg_per_tick, current_hp)
        if actual_damage > 0:
            if is_p1:
                match.player1_health = max(0, match.player1_health - actual_damage)
            else:
                match.player2_health = max(0, match.player2_health - actual_damage)
            log_event = {
                "action_type": "dot_tick",
                "action_key": effect_name,
                "target_id": player_id,
                "effect": effect_name,
                "damage": actual_damage,
                "turns_left": turns_left,
            }
            _add_combat_log_event(match, log_event, db)
        e["turns_left"] = turns_left - 1
        if e["turns_left"] <= 0:
            to_remove.append(i)
    for i in reversed(to_remove):
        effects.pop(i)
    if to_remove:
        flag_modified(match, "player1_effects" if is_p1 else "player2_effects")


#create the process attack function
def process_attack(match: Match, attacker_id: int, defender_id: int, db: Session, ability_multiplier: float = 1.0) -> Dict[str, Any]:
    """
    Process a basic attack action (no turn validation here).
    Applies defender effects: evade (avoid/reduce), arcane_shield (absorb), then damage, then thorns (reflect).
    Emits full combat log: raw/primary damage, damage_absorbed, damage_reflected, evade_avoided.
    """
    _check_match_active(match)
    _check_actor_valid_and_alive(match, attacker_id)

    if attacker_id == defender_id:
        raise InvalidActionError("Cannot attack yourself")

    is_player1_att = attacker_id == match.player1_id
    defender_defending = match.player2_defending if is_player1_att else match.player1_defending

    attacker = _get_user_for_player(match, attacker_id, db)
    min_dmg, max_dmg = get_attack_damage_range(attacker) if attacker else (10, 20)
    damage = random.randint(min_dmg, max_dmg)
    damage = int(damage * ability_multiplier)

    damage_bonus_battle_shout = 0
    damage_bonus_chill = 0
    damage_bonus_shapeshift = 0
    damage_reduced_defend = 0
    damage_reduced_battle_shout = 0
    damage_reduced_shapeshift = 0

    if defender_defending:
        damage_before_defend = damage
        damage = int(damage * (1 - DEFEND_DAMAGE_REDUCTION))
        damage_reduced_defend = damage_before_defend - damage
        if is_player1_att:
            match.player2_defending = False
        else:
            match.player1_defending = False

    # Shapeshift: attacker deals more damage
    if _has_effect(match, attacker_id, "shapeshift"):
        sh = _get_effect_params(match, attacker_id, "shapeshift")
        boost_pct = sh.get("damage_boost_pct", 0.22) if sh else 0.22
        damage_before = damage
        damage = int(damage * (1 + boost_pct))
        damage_bonus_shapeshift = damage - damage_before

    # Battle Shout (War Cry): attacker gains +flat damage
    if _has_effect(match, attacker_id, "battle_shout"):
        bs_params = _get_effect_params(match, attacker_id, "battle_shout")
        flat_bonus = bs_params.get("flat_damage_bonus", 5) if bs_params else 5
        damage += flat_bonus
        damage_bonus_battle_shout = flat_bonus

    # Battle Shout (War Cry): defender takes less damage
    if _has_effect(match, defender_id, "battle_shout"):
        bs_params = _get_effect_params(match, defender_id, "battle_shout")
        red_pct = bs_params.get("damage_reduction_pct", 0.20) if bs_params else 0.20
        damage_before = damage
        damage = int(damage * (1 - red_pct))
        damage_reduced_battle_shout = damage_before - damage

    # Shapeshift: defender takes less damage
    if _has_effect(match, defender_id, "shapeshift"):
        sh = _get_effect_params(match, defender_id, "shapeshift")
        def_pct = sh.get("defense_boost_pct", 0.25) if sh else 0.25
        damage_before = damage
        damage = int(damage * (1 - def_pct))
        damage_reduced_shapeshift = damage_before - damage

    damage_absorbed = 0
    damage_reflected = 0
    evaded = False
    damage_reduced_shield_wall = 0
    damage_reflected_shield_wall = 0
    damage_reflected_thorns = 0
    damage_absorbed_arcane_shield = 0

    # Shield Wall: next incoming hit reduced by 50%, then reflect 20% of reduced amount to attacker; consumed on hit
    if _has_effect(match, defender_id, "shield_wall"):
        shw = _get_effect_params(match, defender_id, "shield_wall")
        reduction_pct = shw.get("reduction_pct", 0.50) if shw else 0.50
        reflect_pct = shw.get("reflect_pct", 0.20) if shw else 0.20
        reduced_amount = int(damage * reduction_pct)
        damage = damage - reduced_amount
        damage_reduced_shield_wall = reduced_amount
        _decrement_effect_hits_and_maybe_consume(match, defender_id, "shield_wall")
        counter_reflect = int(reduced_amount * reflect_pct)
        if counter_reflect > 0:
            if is_player1_att:
                match.player1_health = max(0, match.player1_health - counter_reflect)
            else:
                match.player2_health = max(0, match.player2_health - counter_reflect)
            damage_reflected += counter_reflect
            damage_reflected_shield_wall = counter_reflect
            log_sw = {
                "action_type": "damage_reflected",
                "action_key": "shield_wall",
                "defender_id": defender_id,
                "attacker_id": attacker_id,
                "effect": "shield_wall",
                "amount": counter_reflect,
            }
            _add_combat_log_event(match, log_sw, db)

    # Evade: next hit avoided/reduced; consumed on hit (hits_left, not turns)
    if _has_effect(match, defender_id, "evade"):
        ev = _get_effect_params(match, defender_id, "evade")
        avoid_pct = ev.get("avoid_pct", 1.0) if ev else 1.0
        damage = int(damage * (1 - avoid_pct))
        _consume_effect(match, defender_id, "evade")
        evaded = True
        log_evade = {
            "action_type": "evade_avoided",
            "action_key": "evade",
            "defender_id": defender_id,
            "attacker_id": attacker_id,
        }
        _add_combat_log_event(match, log_evade, db)

    # Chill: target takes more damage (e.g. 15%); consumed on next hit
    if damage > 0 and _has_effect(match, defender_id, "chill"):
        chill_params = _get_effect_params(match, defender_id, "chill")
        chill_pct = chill_params.get("damage_taken_pct", 0.15) if chill_params else 0.15
        damage_before_chill = damage
        damage = int(damage * (1 + chill_pct))
        damage_bonus_chill = damage - damage_before_chill
        _consume_effect(match, defender_id, "chill")

    if damage > 0 and _has_effect(match, defender_id, "arcane_shield"):
        sh = _get_effect_params(match, defender_id, "arcane_shield")
        absorb_cap = sh.get("value", 18) if sh else 18
        absorb = min(absorb_cap, damage)
        damage -= absorb
        damage_absorbed += absorb
        damage_absorbed_arcane_shield = absorb
        _consume_effect(match, defender_id, "arcane_shield")
        log_absorb = {
            "action_type": "damage_absorbed",
            "action_key": "arcane_shield",
            "defender_id": defender_id,
            "attacker_id": attacker_id,
            "effect": "arcane_shield",
            "amount": absorb,
        }
        _add_combat_log_event(match, log_absorb, db)

    damage_dealt = max(0, damage)
    if damage_dealt > 0:
        if is_player1_att:
            match.player2_health = max(0, match.player2_health - damage_dealt)
        else:
            match.player1_health = max(0, match.player1_health - damage_dealt)

    if damage_dealt > 0 and _has_effect(match, defender_id, "thorns"):
        th = _get_effect_params(match, defender_id, "thorns")
        reflect_pct = th.get("reflect_pct", 0.25) if th else 0.25
        damage_reflected = int(damage_dealt * reflect_pct)
        damage_reflected_thorns = damage_reflected
        if damage_reflected > 0:
            if is_player1_att:
                match.player1_health = max(0, match.player1_health - damage_reflected)
            else:
                match.player2_health = max(0, match.player2_health - damage_reflected)
            log_reflect = {
                "action_type": "damage_reflected",
                "action_key": "thorns",
                "defender_id": defender_id,
                "attacker_id": attacker_id,
                "effect": "thorns",
                "amount": damage_reflected,
            }
            _add_combat_log_event(match, log_reflect, db)

    result = {
        "action": "attack",
        "damage": damage_dealt,
        "defended": defender_defending,
        "damage_absorbed": damage_absorbed,
        "damage_reflected": damage_reflected,
        "evaded": evaded,
        "target_health": match.player2_health if is_player1_att else match.player1_health,
        "attacker_id": attacker_id,
        "defender_id": defender_id,
    }

    log_event = {
        "action_type": "attack",
        "action_key": "attack",
        "attacker_id": attacker_id,
        "defender_id": defender_id,
        "damage": damage_dealt,
        "defended": defender_defending,
    }
    if damage_bonus_battle_shout > 0:
        log_event["damage_bonus_battle_shout"] = damage_bonus_battle_shout
    if damage_bonus_chill > 0:
        log_event["damage_bonus_chill"] = damage_bonus_chill
    if damage_bonus_shapeshift > 0:
        log_event["damage_bonus_shapeshift"] = damage_bonus_shapeshift
    if damage_reduced_defend > 0:
        log_event["damage_reduced_defend"] = damage_reduced_defend
    if damage_reduced_battle_shout > 0:
        log_event["damage_reduced_battle_shout"] = damage_reduced_battle_shout
    if damage_reduced_shapeshift > 0:
        log_event["damage_reduced_shapeshift"] = damage_reduced_shapeshift
    if damage_reduced_shield_wall > 0:
        log_event["damage_reduced_shield_wall"] = damage_reduced_shield_wall
    if damage_reflected_shield_wall > 0:
        log_event["damage_reflected_shield_wall"] = damage_reflected_shield_wall
    if damage_reflected_thorns > 0:
        log_event["damage_reflected_thorns"] = damage_reflected_thorns
    if damage_absorbed_arcane_shield > 0:
        log_event["damage_absorbed_arcane_shield"] = damage_absorbed_arcane_shield
    if evaded:
        log_event["evaded"] = True
    _add_combat_log_event(match, log_event, db)

    return result


#create the process defend function
def process_defend(match: Match, player_id: int, db: Session) -> Dict[str, Any]:
    """
    Process a defend action (no turn validation here).

    Marks the given player as defending so the next incoming attack deals
    reduced damage. Returns a small status dict describing the action.
    """
    _check_match_active(match)
    _check_actor_valid_and_alive(match, player_id)
    is_player1 = player_id == match.player1_id
    if is_player1:
        match.player1_defending = True
    else:
        match.player2_defending = True
    
    result = {
        "action": "defend",
        "message": "Defending - next attack will be reduced by 50%",
        "actor_id": player_id,
    }
    
    # Add to combat log
    log_event = {
        "action_type": "defend",
        "action_key": "defend",
        "actor_id": player_id,
    }
    _add_combat_log_event(match, log_event, db)

    return result


#create the process heal function
def process_heal(match: Match, player_id: int, db: Session, ability_multiplier: float = 1.0) -> Dict[str, Any]:
    """
    Process a heal ability (no turn validation here).

    Heals the given player by a class-based amount, capped at max HP.
    Shapeshift (heal_boost_pct) increases healing; the bonus is reflected in combat log.
    """
    _check_match_active(match)
    _check_actor_valid_and_alive(match, player_id)
    is_player1 = player_id == match.player1_id

    # Get player's class-based heal amount and max HP
    player = _get_user_for_player(match, player_id, db)
    heal_amount = get_heal_amount(player) if player else 15
    max_hp = get_max_hp(player) if player else 100

    # Apply ability multiplier (for class abilities)
    heal_amount = int(heal_amount * ability_multiplier)
    heal_bonus_shapeshift = 0
    if _has_effect(match, player_id, "shapeshift"):
        sh = _get_effect_params(match, player_id, "shapeshift")
        boost_pct = sh.get("heal_boost_pct", 0.20) if sh else 0.20
        heal_bonus_shapeshift = int(heal_amount * boost_pct)
        heal_amount += heal_bonus_shapeshift

    current_health = match.player1_health if is_player1 else match.player2_health
    new_health = min(max_hp, current_health + heal_amount)
    healed = new_health - current_health

    if is_player1:
        match.player1_health = new_health
    else:
        match.player2_health = new_health

    result = {
        "action": "heal",
        "healed": healed,
        "new_health": new_health,
        "actor_id": player_id,
    }
    if heal_bonus_shapeshift > 0:
        result["heal_bonus_shapeshift"] = heal_bonus_shapeshift

    # Add to combat log (include buff breakdown for formatter)
    log_event = {
        "action_type": "heal",
        "action_key": "heal",
        "actor_id": player_id,
        "healed": healed,
    }
    if heal_bonus_shapeshift > 0:
        log_event["heal_bonus_shapeshift"] = heal_bonus_shapeshift
    _add_combat_log_event(match, log_event, db)

    return result


#create the process ability function (data-driven)
def process_ability(match: Match, player_id: int, ability_id: str, db: Session) -> Dict[str, Any]:
    """
    Process a named ability from abilities.py. Checks cooldown, applies effect (attack/heal/defend/effect).
    Turn is not advanced here; caller (CombatEngine) does that after check_match_end.
    """
    _check_match_active(match)
    _check_actor_valid_and_alive(match, player_id)
    
    player = _get_user_for_player(match, player_id, db)
    if not player or not player.class_name:
        raise InvalidActionError("Player must have a class to use abilities")
    
    ab = get_ability(player.class_name, ability_id)
    if not ab:
        raise InvalidActionError(f"Unknown ability: {ability_id} for class {player.class_name}")
    
    _check_ability_cooldown_for_id(match, player_id, ability_id)
    
    is_player1 = player_id == match.player1_id
    opponent_id = match.player2_id if is_player1 else match.player1_id
    ab_type = ab.get("type", "attack")
    cooldown_turns = get_cooldown_turns(ab)
    
    if ab_type == "attack":
        mult = ab.get("damage_multiplier", 1.0)
        if ability_id == "execute":
            defender_hp = match.player2_health if is_player1 else match.player1_health
            defender_user = _get_user_for_player(match, opponent_id, db)
            defender_max = get_max_hp(defender_user) if defender_user else 100
            if defender_max > 0 and (defender_hp / defender_max) <= ab.get("low_hp_threshold", 0.35):
                mult = ab.get("bonus_multiplier", 1.6)
            else:
                mult = ab.get("damage_multiplier", 1.2)
        result = process_attack(match, player_id, opponent_id, db, mult)
        result["action"] = ability_id
        result["message"] = f"{ab.get('name', ability_id)} dealt {result['damage']} damage!"
        if match.combat_log:
            match.combat_log[-1]["action_type"] = ability_id
            match.combat_log[-1]["action_key"] = ability_id
        # Backstab: if target was not defending, apply Bleed
        if ability_id == "backstab" and ab.get("effect_if_not_defending") and not result.get("defended", False):
            eff_name = ab["effect_if_not_defending"]
            duration = ab.get("effect_if_not_defending_duration", 2)
            dot = ab.get("effect_if_not_defending_damage_per_tick", 5)
            target_effects = _get_effects(match, opponent_id)
            eff_dict = {"name": eff_name, "turns_left": duration, "damage_per_tick": dot, "source_id": player_id}
            target_effects.append(eff_dict)
            flag_modified(match, "player1_effects" if not is_player1 else "player2_effects")
            log_eff = {
                "action_type": "effect_applied",
                "action_key": ability_id,
                "actor_id": player_id,
                "target_id": opponent_id,
                "effect": eff_name,
                "duration": duration,
            }
            _add_combat_log_event(match, log_eff, db)
        # Shadowstep: also grant Evasion (next hit) to self
        if ability_id == "shadowstep" and ab.get("effect_also_self"):
            eff_name = ab["effect_also_self"]
            self_effects = _get_effects(match, player_id)
            eff_dict = {"name": eff_name, "hits_left": ab.get("effect_also_self_hits_left", 1), "source_id": player_id, "remaining_turns_until_expiry": 2}
            if ab.get("effect_also_self_avoid_pct") is not None:
                eff_dict["avoid_pct"] = ab["effect_also_self_avoid_pct"]
            self_effects.append(eff_dict)
            flag_modified(match, "player1_effects" if is_player1 else "player2_effects")

            log_evade_self = {
                "action_type": "effect_applied",
                "action_key": "shadowstep",
                "actor_id": player_id,
                "target_id": player_id,
                "effect": eff_name,
                "hits_left": ab.get("effect_also_self_hits_left", 1),
            }
            _add_combat_log_event(match, log_evade_self, db)
        # Attack abilities that apply a DoT/debuff (e.g. fireball -> burn, ice_bolt -> chill)
        if ab.get("effect") and ab.get("effect_target") == "enemy" and ab.get("duration"):
            eff_name = ab["effect"]
            duration = ab["duration"]
            target_effects = _get_effects(match, opponent_id)
            eff_dict = {"name": eff_name, "turns_left": duration, "source_id": player_id}
            if ab.get("damage_per_tick"):
                eff_dict["damage_per_tick"] = ab["damage_per_tick"]
            if ab.get("chill_damage_taken_pct") is not None:
                eff_dict["damage_taken_pct"] = ab["chill_damage_taken_pct"]
            # Chill (and similar debuffs) last until end of caster's next turn so caster can benefit
            if not ab.get("damage_per_tick"):
                eff_dict["remaining_turns_until_expiry"] = (duration or 1) + 1
            target_effects.append(eff_dict)
            flag_modified(match, "player1_effects" if not is_player1 else "player2_effects")
            log_eff = {
                "action_type": "effect_applied",
                "action_key": ability_id,
                "actor_id": player_id,
                "target_id": opponent_id,
                "effect": eff_name,
                "duration": duration,
            }
            _add_combat_log_event(match, log_eff, db)
    elif ab_type == "heal":
        mult = ab.get("heal_multiplier", 1.0)
        result = process_heal(match, player_id, db, mult)
        result["action"] = ability_id
        result["message"] = f"{ab.get('name', ability_id)} healed for {result['healed']} HP!"
        if match.combat_log:
            match.combat_log[-1]["action_type"] = ability_id
            match.combat_log[-1]["action_key"] = ability_id
    elif ab_type == "defend":
        result = process_defend(match, player_id, db)
        result["action"] = ability_id
        result["message"] = f"{ab.get('name', ability_id)} - blocking!"
        if match.combat_log:
            match.combat_log[-1]["action_type"] = ability_id
            match.combat_log[-1]["action_key"] = ability_id
    elif ab_type == "effect":
        effect_name = ab.get("effect", ability_id)
        effect_target = ab.get("effect_target", "self")
        target_id = opponent_id if effect_target == "enemy" else player_id
        effects = _get_effects(match, target_id)
        eff_dict = {"name": effect_name, "source_id": player_id}
        if ab.get("hits_left") is not None:
            eff_dict["hits_left"] = ab["hits_left"]
            # Hit-based effects (Shield Wall, Evade) do not expire by turn; they last until consumed by hits
        else:
            duration = ab.get("duration", 1)
            # DoT effects (poison) use turns_left only; non-DoT use remaining_turns_until_expiry
            if ab.get("damage_per_tick") is not None:
                eff_dict["turns_left"] = duration
            else:
                eff_dict["turns_left"] = duration  # for display
                eff_dict["remaining_turns_until_expiry"] = (duration or 1) + 1
        if ab.get("absorb_flat") is not None:
            eff_dict["value"] = ab["absorb_flat"]
        if ab.get("reflect_pct") is not None:
            eff_dict["reflect_pct"] = ab["reflect_pct"]
        if ab.get("reduction_pct") is not None:
            eff_dict["reduction_pct"] = ab["reduction_pct"]
        if ab.get("damage_per_tick") is not None:
            eff_dict["damage_per_tick"] = ab["damage_per_tick"]
        if ab.get("avoid_pct") is not None:
            eff_dict["avoid_pct"] = ab["avoid_pct"]
        if ab.get("flat_damage_bonus") is not None:
            eff_dict["flat_damage_bonus"] = ab["flat_damage_bonus"]
        if ab.get("damage_reduction_pct") is not None:
            eff_dict["damage_reduction_pct"] = ab["damage_reduction_pct"]
        if ab.get("damage_boost_pct") is not None:
            eff_dict["damage_boost_pct"] = ab["damage_boost_pct"]
        if ab.get("defense_boost_pct") is not None:
            eff_dict["defense_boost_pct"] = ab["defense_boost_pct"]
        if ab.get("heal_boost_pct") is not None:
            eff_dict["heal_boost_pct"] = ab["heal_boost_pct"]
        effects.append(eff_dict)
        flag_modified(match, "player1_effects" if target_id == match.player1_id else "player2_effects")
        duration = eff_dict.get("turns_left", 1)
        result = {
            "action": ability_id,
            "message": f"{ab.get('name', ability_id)} applied!",
            "actor_id": player_id,
            "effect": effect_name,
            "duration": duration,
        }
        log_event = {
            "action_type": "effect_applied",
            "action_key": ability_id,
            "actor_id": player_id,
            "target_id": target_id,
            "effect": effect_name,
            "duration": duration,
        }
        if eff_dict.get("hits_left") is not None:
            log_event["hits_left"] = eff_dict["hits_left"]
        _add_combat_log_event(match, log_event, db)
    else:
        raise InvalidActionError(f"Unsupported ability type: {ab_type}")
    
    _set_ability_cooldown_for_id(match, player_id, ability_id, cooldown_turns)
    return result


def process_class_ability(match: Match, player_id: int, db: Session, ability_id: Optional[str] = None) -> Dict[str, Any]:
    """Legacy: process class ability by id (e.g. power_strike, fireball). If ability_id is None, not used."""
    if ability_id:
        return process_ability(match, player_id, ability_id, db)
    raise InvalidActionError("Ability id required")


#create the advance turn function
def advance_turn(match: Match) -> None:
    """
    Advance to the next turn. Cooldowns and effects tick at end-of-turn for the player who just acted.
    """
    player_ending_turn = match.current_turn
    match.turn_number += 1
    
    # Tick cooldowns for the player whose turn just ended
    _tick_cooldowns_for_player(match, player_ending_turn)
    # Expire duration-based effects when caster ends their turn (Chill/Shapeshift/etc. last until end of caster's next turn)
    _expire_effects_when_source_ends_turn(match, player_ending_turn)
    
    # Legacy single-ability cooldown tick
    if player_ending_turn == match.player1_id and match.player1_ability_cooldown > 0:
        match.player1_ability_cooldown -= 1
    elif player_ending_turn == match.player2_id and match.player2_ability_cooldown > 0:
        match.player2_ability_cooldown -= 1
    
    # Switch turns
    if match.current_turn == match.player1_id:
        match.current_turn = match.player2_id
    else:
        match.current_turn = match.player1_id
    _set_turn_timers(match)


#create the check match end function
def check_match_end(match: Match, db: Session) -> Optional[int]:
    """
    Check if the match has ended.

    If either player has health <= 0, marks the match as finished, sets winner_id,
    awards XP, and returns the winner's user ID. Otherwise returns None.
    """
    if match.player1_health <= 0:
        match.status = "finished"
        match.winner_id = match.player2_id
        award_match_xp(match, db)
        return match.player2_id
    elif match.player2_health <= 0:
        match.status = "finished"
        match.winner_id = match.player1_id
        award_match_xp(match, db)
        return match.player1_id
    return None


#create the check turn function
def _check_turn(match: Match, actor_id: int) -> None:
    """Ensure it's the actor's turn."""
    if match.current_turn is None:
        raise InvalidActionError("Current turn is not set on match")

    if actor_id != match.current_turn:
        raise InvalidActionError("It is not this player's turn")


#create the combat engine class
class CombatEngine:
    """
    Higher-level combat engine that enforces:
    - match is active
    - actor is a valid, alive player
    - actor plays only on their turn
    - turn advances automatically after a valid action
    """

    def __init__(self, db: Session):
        self.db = db

    #create the attack method
    def attack(self, match: Match, attacker_id: int, defender_id: int) -> Dict[str, Any]:
        _check_match_active(match)
        _check_actor_valid_and_alive(match, attacker_id)
        _check_turn(match, attacker_id)

        _apply_dot_ticks(match, match.current_turn, self.db)
        winner_id = check_match_end(match, self.db)
        if winner_id is not None:
            return {"winner_id": winner_id, "action": "attack", "damage": 0, "defended": False, "target_health": 0, "attacker_id": attacker_id, "defender_id": defender_id}

        result = process_attack(match, attacker_id, defender_id, self.db)

        winner_id = check_match_end(match, self.db)
        if winner_id is None:
            advance_turn(match)

        return {"winner_id": winner_id, **result}

    #create the defend method
    def defend(self, match: Match, player_id: int) -> Dict[str, Any]:
        _check_match_active(match)
        _check_actor_valid_and_alive(match, player_id)
        _check_turn(match, player_id)

        _apply_dot_ticks(match, match.current_turn, self.db)
        winner_id = check_match_end(match, self.db)
        if winner_id is not None:
            return {"winner_id": winner_id, "action": "defend", "message": "Defending", "actor_id": player_id}

        result = process_defend(match, player_id, self.db)

        winner_id = check_match_end(match, self.db)
        if winner_id is None:
            advance_turn(match)

        return {"winner_id": winner_id, **result}

    #create the heal method
    def heal(self, match: Match, player_id: int) -> Dict[str, Any]:
        _check_match_active(match)
        _check_actor_valid_and_alive(match, player_id)
        _check_turn(match, player_id)

        _apply_dot_ticks(match, match.current_turn, self.db)
        winner_id = check_match_end(match, self.db)
        if winner_id is not None:
            return {"winner_id": winner_id, "action": "heal", "healed": 0, "new_health": 0, "actor_id": player_id}

        result = process_heal(match, player_id, self.db)

        winner_id = check_match_end(match, self.db)
        if winner_id is None:
            advance_turn(match)

        return {"winner_id": winner_id, **result}

    #create the class ability method (by ability id, e.g. power_strike, fireball)
    def class_ability(self, match: Match, player_id: int, ability_id: str) -> Dict[str, Any]:
        _check_match_active(match)
        _check_actor_valid_and_alive(match, player_id)
        _check_turn(match, player_id)

        _apply_dot_ticks(match, match.current_turn, self.db)
        winner_id = check_match_end(match, self.db)
        if winner_id is not None:
            return {"winner_id": winner_id, "action": ability_id, "message": "", "actor_id": player_id}

        result = process_ability(match, player_id, ability_id, self.db)

        winner_id = check_match_end(match, self.db)
        if winner_id is None:
            advance_turn(match)

        return {"winner_id": winner_id, **result}


# Note: engine instance must be created per-request with db session
# See matches.py for usage
