"""
Simple turn-based combat logic.

This module exposes both low-level functions (used by tests) and a higher-level
CombatEngine that enforces turn rules and match state.
"""
import random
from typing import Any, Dict, Optional

from app.db.models import Match


# Combat constants
BASE_ATTACK_DAMAGE = (10, 20)  # min, max damage
DEFEND_DAMAGE_REDUCTION = 0.5  # 50% damage reduction
HEAL_AMOUNT = 15
DOUBLE_ATTACK_MULTIPLIER = 2.0


class InvalidActionError(ValueError):
    """Base error for invalid combat actions."""


class MatchNotActiveError(InvalidActionError):
    """Raised when trying to perform an action on a match that is not active."""


def _check_match_active(match: Match) -> None:
    """Check if match is active, raise MatchNotActiveError if not."""
    if match.status != "active":
        raise MatchNotActiveError(f"Match is not active (status: {match.status})")


def _check_actor_valid_and_alive(match: Match, actor_id: int) -> None:
    """Ensure actor is one of the players and not dead."""
    if actor_id not in (match.player1_id, match.player2_id):
        raise InvalidActionError("Actor must be one of the match players")

    if actor_id == match.player1_id and match.player1_health <= 0:
        raise InvalidActionError("Dead player cannot act")
    if actor_id == match.player2_id and match.player2_health <= 0:
        raise InvalidActionError("Dead player cannot act")


def initialize_match(match: Match) -> None:
    """
    Initialize a match for combat.

    - Sets both players to full health.
    - Clears all defensive and ability flags.
    - Sets the current turn to player1 and turn_number to 1 (if not already set).
    """
    if match.current_turn is None:
        match.current_turn = match.player1_id
        match.turn_number = 1
        match.player1_health = 100
        match.player2_health = 100
        match.player1_defending = False
        match.player2_defending = False
        match.player1_ability_effect = None
        match.player2_ability_effect = None


def process_attack(match: Match, attacker_id: int, defender_id: int) -> Dict[str, Any]:
    """
    Process a basic attack action (no turn validation here).

    Validates that the match is active, the attacker is a valid, alive player,
    and that the attacker is not targeting themselves. Applies ability and
    defense modifiers, updates health, and returns a summary dict:

    {
        "action": "attack",
        "damage": int,
        "defended": bool,
        "target_health": int,
    }
    """
    _check_match_active(match)
    _check_actor_valid_and_alive(match, attacker_id)

    if attacker_id == defender_id:
        raise InvalidActionError("Cannot attack yourself")

    is_player1 = attacker_id == match.player1_id
    defender_defending = match.player2_defending if is_player1 else match.player1_defending
    
    # Calculate base damage
    min_dmg, max_dmg = BASE_ATTACK_DAMAGE
    damage = random.randint(min_dmg, max_dmg)
    
    # Apply ability effects
    ability_effect = match.player1_ability_effect if is_player1 else match.player2_ability_effect
    if ability_effect == "double_attack":
        damage = int(damage * DOUBLE_ATTACK_MULTIPLIER)
        # Clear ability effect after use
        if is_player1:
            match.player1_ability_effect = None
        else:
            match.player2_ability_effect = None
    
    # Apply defense
    if defender_defending:
        damage = int(damage * (1 - DEFEND_DAMAGE_REDUCTION))
        # Clear defense after being hit
        if is_player1:
            match.player2_defending = False
        else:
            match.player1_defending = False
    
    # Apply damage
    if is_player1:
        match.player2_health = max(0, match.player2_health - damage)
    else:
        match.player1_health = max(0, match.player1_health - damage)
    
    return {
        "action": "attack",
        "damage": damage,
        "defended": defender_defending,
        "target_health": match.player2_health if is_player1 else match.player1_health,
    }


def process_defend(match: Match, player_id: int) -> Dict[str, Any]:
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
    
    return {
        "action": "defend",
        "message": "Defending - next attack will deal 50% less damage",
    }


def process_heal(match: Match, player_id: int) -> Dict[str, Any]:
    """
    Process a heal ability (no turn validation here).

    Heals the given player by a fixed amount, capped at 100 HP. Returns a
    dict with details about how much was healed and the new health.
    """
    _check_match_active(match)
    _check_actor_valid_and_alive(match, player_id)
    is_player1 = player_id == match.player1_id
    current_health = match.player1_health if is_player1 else match.player2_health
    new_health = min(100, current_health + HEAL_AMOUNT)
    healed = new_health - current_health
    
    if is_player1:
        match.player1_health = new_health
    else:
        match.player2_health = new_health
    
    return {
        "action": "heal",
        "healed": healed,
        "new_health": new_health,
    }


def process_double_attack_ability(match: Match, player_id: int) -> Dict[str, Any]:
    """
    Process the double-attack ability (no turn validation here).

    Marks the player so that their *next* attack deals double damage. The
    effect is consumed on use. Returns a dict describing the applied buff.
    """
    _check_match_active(match)
    _check_actor_valid_and_alive(match, player_id)
    is_player1 = player_id == match.player1_id
    if is_player1:
        match.player1_ability_effect = "double_attack"
    else:
        match.player2_ability_effect = "double_attack"
    
    return {
        "action": "double_attack",
        "message": "Next attack will deal double damage",
    }


def advance_turn(match: Match) -> None:
    """
    Advance to the next turn.

    Increments the turn counter and flips `current_turn` to the other player.
    """
    match.turn_number += 1
    # Switch turns
    if match.current_turn == match.player1_id:
        match.current_turn = match.player2_id
    else:
        match.current_turn = match.player1_id


def check_match_end(match: Match) -> Optional[int]:
    """
    Check if the match has ended.

    If either player has health <= 0, marks the match as finished and returns
    the winner's user ID. Otherwise returns None.
    """
    if match.player1_health <= 0:
        match.status = "finished"
        return match.player2_id
    elif match.player2_health <= 0:
        match.status = "finished"
        return match.player1_id
    return None


def _check_turn(match: Match, actor_id: int) -> None:
    """Ensure it's the actor's turn."""
    if match.current_turn is None:
        # If no turn set, treat as invalid usage of engine.
        raise InvalidActionError("Current turn is not set on match")

    if actor_id != match.current_turn:
        raise InvalidActionError("It is not this player's turn")


class CombatEngine:
    """
    Higher-level combat engine that enforces:
    - match is active
    - actor is a valid, alive player
    - actor plays only on their turn
    - turn advances automatically after a valid action
    """

    def attack(self, match: Match, attacker_id: int, defender_id: int) -> Dict[str, Any]:
        _check_match_active(match)
        _check_actor_valid_and_alive(match, attacker_id)
        _check_turn(match, attacker_id)

        result = process_attack(match, attacker_id, defender_id)

        winner_id = check_match_end(match)
        if winner_id is None:
            advance_turn(match)

        return {"winner_id": winner_id, **result}

    def defend(self, match: Match, player_id: int) -> Dict[str, Any]:
        _check_match_active(match)
        _check_actor_valid_and_alive(match, player_id)
        _check_turn(match, player_id)

        result = process_defend(match, player_id)

        winner_id = check_match_end(match)
        if winner_id is None:
            advance_turn(match)

        return {"winner_id": winner_id, **result}

    def heal(self, match: Match, player_id: int) -> Dict[str, Any]:
        _check_match_active(match)
        _check_actor_valid_and_alive(match, player_id)
        _check_turn(match, player_id)

        result = process_heal(match, player_id)

        winner_id = check_match_end(match)
        if winner_id is None:
            advance_turn(match)

        return {"winner_id": winner_id, **result}

    def double_attack(self, match: Match, player_id: int) -> Dict[str, Any]:
        _check_match_active(match)
        _check_actor_valid_and_alive(match, player_id)
        _check_turn(match, player_id)

        result = process_double_attack_ability(match, player_id)

        winner_id = check_match_end(match)
        if winner_id is None:
            advance_turn(match)

        return {"winner_id": winner_id, **result}


# Convenient shared engine instance
engine: CombatEngine = CombatEngine()
