"""
Simple turn-based combat logic
"""
import random
from sqlalchemy.orm import Session
from app.db.models import Match


# Combat constants
BASE_ATTACK_DAMAGE = (10, 20)  # min, max damage
DEFEND_DAMAGE_REDUCTION = 0.5  # 50% damage reduction
HEAL_AMOUNT = 15
DOUBLE_ATTACK_MULTIPLIER = 2.0


def initialize_match(match: Match) -> None:
    """Initialize a match for combat - set first turn"""
    if match.current_turn is None:
        match.current_turn = match.player1_id
        match.turn_number = 1
        match.player1_health = 100
        match.player2_health = 100
        match.player1_defending = False
        match.player2_defending = False
        match.player1_ability_effect = None
        match.player2_ability_effect = None


def process_attack(match: Match, attacker_id: int, defender_id: int) -> dict:
    """Process an attack action"""
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


def process_defend(match: Match, player_id: int) -> dict:
    """Process a defend action"""
    is_player1 = player_id == match.player1_id
    if is_player1:
        match.player1_defending = True
    else:
        match.player2_defending = True
    
    return {
        "action": "defend",
        "message": "Defending - next attack will deal 50% less damage",
    }


def process_heal(match: Match, player_id: int) -> dict:
    """Process a heal ability"""
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


def process_double_attack_ability(match: Match, player_id: int) -> dict:
    """Process double attack ability - next attack does 2x damage"""
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
    """Advance to the next turn"""
    match.turn_number += 1
    # Switch turns
    if match.current_turn == match.player1_id:
        match.current_turn = match.player2_id
    else:
        match.current_turn = match.player1_id


def check_match_end(match: Match) -> int | None:
    """Check if match has ended, return winner_id or None"""
    if match.player1_health <= 0:
        match.status = "finished"
        return match.player2_id
    elif match.player2_health <= 0:
        match.status = "finished"
        return match.player1_id
    return None
