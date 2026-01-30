"""
Class-based stats and progression system.
"""
from typing import Dict, Tuple
from app.db.models import User, Match


# Class base stats (at level 1)
# Balanced for competitive play:
# - Warrior: Tanky, moderate damage, weaker burst
# - Mage: Squishy, highest burst ability
# - Druid: Mid HP, best sustain/healing
# - Rogue: High tempo/burst, lower HP than warrior, evasion/utility
CLASS_STATS = {
    "warrior": {
        "base_hp": 130,  # Highest HP pool
        "hp_per_level": 14,  # Good scaling
        "base_attack_min": 11,
        "base_attack_max": 20,
        "attack_per_level": 2,
        "base_heal": 11,
        "heal_per_level": 1,
    },
    "mage": {
        "base_hp": 75,  # Lowest HP pool
        "hp_per_level": 7,
        "base_attack_min": 16,
        "base_attack_max": 25,
        "attack_per_level": 3,
        "base_heal": 9,
        "heal_per_level": 1,
    },
    "druid": {
        "base_hp": 105,  # Mid HP pool
        "hp_per_level": 11,
        "base_attack_min": 10,
        "base_attack_max": 19,
        "attack_per_level": 2,
        "base_heal": 15,  # Best base heal
        "heal_per_level": 2,
    },
    "rogue": {
        "base_hp": 90,  # Lower than warrior, evasion-focused
        "hp_per_level": 9,
        "base_attack_min": 14,  # High tempo burst
        "base_attack_max": 24,
        "attack_per_level": 3,
        "base_heal": 8,
        "heal_per_level": 1,
    },
}


def get_max_hp(user: User) -> int:
    """Calculate max HP based on class and level."""
    if not user.class_name:
        return 100  # Fallback for legacy users
    stats = CLASS_STATS.get(user.class_name, CLASS_STATS["warrior"])
    return stats["base_hp"] + (stats["hp_per_level"] * (user.level - 1))


def get_attack_damage_range(user: User) -> Tuple[int, int]:
    """Calculate attack damage range based on class and level."""
    if not user.class_name:
        return (10, 20)  # Fallback
    stats = CLASS_STATS.get(user.class_name, CLASS_STATS["warrior"])
    min_dmg = stats["base_attack_min"] + (stats["attack_per_level"] * (user.level - 1))
    max_dmg = stats["base_attack_max"] + (stats["attack_per_level"] * (user.level - 1))
    return (min_dmg, max_dmg)


def get_heal_amount(user: User) -> int:
    """Calculate heal amount based on class and level."""
    if not user.class_name:
        return 15  # Fallback
    stats = CLASS_STATS.get(user.class_name, CLASS_STATS["warrior"])
    return stats["base_heal"] + (stats["heal_per_level"] * (user.level - 1))


def get_xp_needed_for_level(level: int) -> int:
    """XP required to gain one level (flat 100 per level)."""
    return 100


def award_xp(user: User, amount: int, db) -> Dict[str, int]:
    """
    Award XP to a user and handle leveling.
    Returns dict with new_xp, new_level, levels_gained.
    """
    user.xp += amount
    levels_gained = 0
    original_level = user.level
    
    # Level up loop
    while True:
        xp_needed = get_xp_needed_for_level(user.level)
        if user.xp >= xp_needed:
            user.xp -= xp_needed
            user.level += 1
            levels_gained += 1
        else:
            break
    
    db.commit()
    db.refresh(user)
    
    return {
        "xp_awarded": amount,
        "new_xp": user.xp,
        "new_level": user.level,
        "levels_gained": levels_gained,
        "original_level": original_level,
    }


def award_match_xp(match: Match, db) -> None:
    """
    Award XP to both players when a match ends.
    Winner gets 50 XP, loser gets 20 XP.
    Only awards once (checks xp_awarded flag).
    """
    if match.xp_awarded or match.status != "finished" or not match.winner_id:
        return
    
    # Skip XP award if db is None (for unit tests)
    if db is None:
        return
    
    from app.db.models import User
    
    winner = db.query(User).filter(User.id == match.winner_id).first()
    loser_id = match.player2_id if match.winner_id == match.player1_id else match.player1_id
    loser = db.query(User).filter(User.id == loser_id).first()
    
    if winner:
        award_xp(winner, 50, db)
    if loser:
        award_xp(loser, 20, db)
    
    match.xp_awarded = True
    db.commit()
