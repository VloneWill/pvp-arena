from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func, Boolean
from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


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
    player1_ability_effect = Column(String(50), nullable=True)  # e.g., "double_attack", "none"
    player2_ability_effect = Column(String(50), nullable=True)