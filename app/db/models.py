from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func, Boolean, JSON
from sqlalchemy.ext.mutable import MutableList, MutableDict
from .database import Base

# Mutable JSON types so in-place changes (append, __setitem__) are persisted
_JSON_LIST = MutableList.as_mutable(JSON())
_JSON_DICT = MutableDict.as_mutable(JSON())


#create the user model
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    class_name = Column(String(20), nullable=True)  # "warrior", "mage", "druid", "rogue"
    level = Column(Integer, nullable=False, default=1)
    xp = Column(Integer, nullable=False, default=0)


#create the match model
class Match(Base):
    __tablename__ = "matches"

    id = Column(Integer, primary_key=True, index=True)

    player1_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    player2_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    status = Column(String(20), nullable=False, default="active")  # active, finished, canceled
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Game state
    player1_health = Column(Integer, nullable=False, default=100)
    player2_health = Column(Integer, nullable=False, default=100)
    current_turn = Column(Integer, ForeignKey("users.id"), nullable=True)
    turn_number = Column(Integer, nullable=False, default=0)
    player1_defending = Column(Boolean, nullable=False, default=False)
    player2_defending = Column(Boolean, nullable=False, default=False)
    player1_ability_effect = Column(String(50), nullable=True)  # Legacy, kept for migration
    player2_ability_effect = Column(String(50), nullable=True)
    player1_ability_cooldown = Column(Integer, nullable=False, default=0)  # Legacy single-ability CD
    player2_ability_cooldown = Column(Integer, nullable=False, default=0)
    # Per-ability cooldowns: {"power_strike": 2, "shield_wall": 0, ...}
    player1_cooldowns = Column(_JSON_DICT, nullable=False, default=lambda: {})
    player2_cooldowns = Column(_JSON_DICT, nullable=False, default=lambda: {})
    # Active effects: [{"name": "thorns", "turns_left": 2}, ...]
    player1_effects = Column(_JSON_LIST, nullable=False, default=lambda: [])
    player2_effects = Column(_JSON_LIST, nullable=False, default=lambda: [])
    winner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    xp_awarded = Column(Boolean, nullable=False, default=False)
    combat_log = Column(_JSON_LIST, nullable=False, default=lambda: [])