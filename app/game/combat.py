"""
Turn-based combat logic with class-based stats and abilities.
"""
import random
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.db.models import Match, User
from app.game.classes import (
    get_max_hp,
    get_attack_damage_range,
    get_heal_amount,
    award_match_xp,
)


# Combat constants
DEFEND_DAMAGE_REDUCTION = 0.5  # 50% damage reduction
ABILITY_COOLDOWN = 3  # Turns before ability can be used again

# Class ability multipliers
# Balanced so Mage has highest burst, Warrior has moderate burst, Druid has best sustain
WARRIOR_POWER_STRIKE_MULTIPLIER = 1.2  # 20% more damage (weaker than Arcane Blast)
MAGE_ARCANE_BLAST_MULTIPLIER = 1.5  # 50% more damage (strongest burst)
DRUID_REJUVENATE_MULTIPLIER = 1.5  # 50% more heal (best sustain)


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
        match.combat_log = []
    
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
    # Flag the JSON column as modified so SQLAlchemy detects the change
    flag_modified(match, "combat_log")


def _check_ability_cooldown(match: Match, player_id: int) -> None:
    """Check if player's ability is on cooldown."""
    is_player1 = player_id == match.player1_id
    cooldown = match.player1_ability_cooldown if is_player1 else match.player2_ability_cooldown
    if cooldown > 0:
        raise InvalidActionError(f"Ability is on cooldown for {cooldown} more turn(s)")


def _set_ability_cooldown(match: Match, player_id: int) -> None:
    """Set ability cooldown after use."""
    is_player1 = player_id == match.player1_id
    if is_player1:
        match.player1_ability_cooldown = ABILITY_COOLDOWN
    else:
        match.player2_ability_cooldown = ABILITY_COOLDOWN


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
        match.combat_log = []  # Initialize empty combat log


#create the process attack function
def process_attack(match: Match, attacker_id: int, defender_id: int, db: Session, ability_multiplier: float = 1.0) -> Dict[str, Any]:
    """
    Process a basic attack action (no turn validation here).

    Validates that the match is active, the attacker is a valid, alive player,
    and that the attacker is not targeting themselves. Applies class-based damage
    and defense modifiers, updates health, and returns a summary dict.
    """
    _check_match_active(match)
    _check_actor_valid_and_alive(match, attacker_id)

    if attacker_id == defender_id:
        raise InvalidActionError("Cannot attack yourself")

    is_player1 = attacker_id == match.player1_id
    defender_defending = match.player2_defending if is_player1 else match.player1_defending
    
    # Get attacker's class-based damage range
    attacker = _get_user_for_player(match, attacker_id, db)
    min_dmg, max_dmg = get_attack_damage_range(attacker) if attacker else (10, 20)
    
    # Calculate base damage
    damage = random.randint(min_dmg, max_dmg)
    
    # Apply ability multiplier (for class abilities)
    damage = int(damage * ability_multiplier)
    
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
    
    result = {
        "action": "attack",
        "damage": damage,
        "defended": defender_defending,
        "target_health": match.player2_health if is_player1 else match.player1_health,
        "attacker_id": attacker_id,
        "defender_id": defender_id,
    }
    
    # Add to combat log
    log_event = {
        "action_type": "attack",
        "attacker_id": attacker_id,
        "defender_id": defender_id,
        "damage": damage,
        "defended": defender_defending,
    }
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
        "actor_id": player_id,
    }
    _add_combat_log_event(match, log_event, db)
    
    return result


#create the process heal function
def process_heal(match: Match, player_id: int, db: Session, ability_multiplier: float = 1.0) -> Dict[str, Any]:
    """
    Process a heal ability (no turn validation here).

    Heals the given player by a class-based amount, capped at max HP.
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
    
    # Add to combat log
    log_event = {
        "action_type": "heal",
        "actor_id": player_id,
        "healed": healed,
    }
    _add_combat_log_event(match, log_event, db)
    
    return result


#create the process class ability function
def process_class_ability(match: Match, player_id: int, db: Session) -> Dict[str, Any]:
    """
    Process a class-specific ability (Power Strike, Arcane Blast, or Rejuvenate).
    Checks cooldown and applies appropriate effect.
    """
    _check_match_active(match)
    _check_actor_valid_and_alive(match, player_id)
    _check_ability_cooldown(match, player_id)
    
    player = _get_user_for_player(match, player_id, db)
    if not player or not player.class_name:
        raise InvalidActionError("Player must have a class to use abilities")
    
    is_player1 = player_id == match.player1_id
    opponent_id = match.player2_id if is_player1 else match.player1_id
    
    class_name = player.class_name
    
    if class_name == "warrior":
        # Power Strike: High damage attack
        result = process_attack(match, player_id, opponent_id, db, WARRIOR_POWER_STRIKE_MULTIPLIER)
        result["action"] = "power_strike"
        result["message"] = f"Power Strike dealt {result['damage']} damage!"
        # Update combat log event (already added by process_attack, just update action_type)
        if match.combat_log:
            match.combat_log[-1]["action_type"] = "power_strike"
    elif class_name == "mage":
        # Arcane Blast: Very high damage attack
        result = process_attack(match, player_id, opponent_id, db, MAGE_ARCANE_BLAST_MULTIPLIER)
        result["action"] = "arcane_blast"
        result["message"] = f"Arcane Blast dealt {result['damage']} damage!"
        # Update combat log event (already added by process_attack, just update action_type)
        if match.combat_log:
            match.combat_log[-1]["action_type"] = "arcane_blast"
    elif class_name == "druid":
        # Rejuvenate: Strong heal
        result = process_heal(match, player_id, db, DRUID_REJUVENATE_MULTIPLIER)
        result["action"] = "rejuvenate"
        result["message"] = f"Rejuvenate healed for {result['healed']} HP!"
        # Update combat log event (already added by process_heal, just update action_type)
        if match.combat_log:
            match.combat_log[-1]["action_type"] = "rejuvenate"
    else:
        raise InvalidActionError(f"Unknown class: {class_name}")
    
    # Set cooldown
    _set_ability_cooldown(match, player_id)
    
    return result


#create the advance turn function
def advance_turn(match: Match) -> None:
    """
    Advance to the next turn.

    Increments the turn counter, flips `current_turn` to the other player,
    and decrements ability cooldown ONLY for the player whose turn just ended.
    """
    # Get the player whose turn is ending (before we switch)
    player_ending_turn = match.current_turn
    
    match.turn_number += 1
    
    # Decrement cooldown ONLY for the player whose turn just ended
    if player_ending_turn == match.player1_id:
        if match.player1_ability_cooldown > 0:
            match.player1_ability_cooldown -= 1
    elif player_ending_turn == match.player2_id:
        if match.player2_ability_cooldown > 0:
            match.player2_ability_cooldown -= 1
    
    # Switch turns
    if match.current_turn == match.player1_id:
        match.current_turn = match.player2_id
    else:
        match.current_turn = match.player1_id


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

        result = process_heal(match, player_id, self.db)

        winner_id = check_match_end(match, self.db)
        if winner_id is None:
            advance_turn(match)

        return {"winner_id": winner_id, **result}

    #create the class ability method
    def class_ability(self, match: Match, player_id: int) -> Dict[str, Any]:
        _check_match_active(match)
        _check_actor_valid_and_alive(match, player_id)
        _check_turn(match, player_id)

        result = process_class_ability(match, player_id, self.db)

        winner_id = check_match_end(match, self.db)
        if winner_id is None:
            advance_turn(match)

        return {"winner_id": winner_id, **result}


# Note: engine instance must be created per-request with db session
# See matches.py for usage
