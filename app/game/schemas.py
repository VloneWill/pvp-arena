#imports for the schemas
from pydantic import BaseModel, ConfigDict
from typing import Literal


#create the match out schema
class MatchOut(BaseModel):
    id: int
    player1_id: int
    player2_id: int
    status: str
    winner_id: int | None = None

    model_config = ConfigDict(from_attributes=True)


#create the match history item schema (enriched with opponent info and result)
class MatchHistoryItem(BaseModel):
    id: int
    status: str
    winner_id: int | None = None
    result: str  # "WIN" or "LOSS" relative to requesting user
    opponent: dict  # {username, class_name, level}
    created_at: str | None = None


#create the queue status out schema
class QueueStatusOut(BaseModel):
    in_queue: bool
    position: int | None
    queue_size: int


#create the match end request schema
class MatchEndRequest(BaseModel):
    status: Literal["finished", "canceled"]


#create the action request schema
class ActionRequest(BaseModel):
    action: Literal["attack", "defend", "heal", "power_strike", "arcane_blast", "rejuvenate"]


#create the combat log event schema
class CombatLogEvent(BaseModel):
    action_type: str
    actor_id: int | None = None
    attacker_id: int | None = None
    defender_id: int | None = None
    target_id: int | None = None
    actor_username: str | None = None
    attacker_username: str | None = None
    defender_username: str | None = None
    target_username: str | None = None
    damage: int | None = None
    healed: int | None = None
    defended: bool | None = None


#create the player stats schema
class PlayerStats(BaseModel):
    level: int
    xp: int
    class_name: str


#create the game state out schema
class GameStateOut(BaseModel):
    match_id: int
    player1_id: int
    player2_id: int
    player1_health: int
    player2_health: int
    player1_max_hp: int  # Canonical max HP for player1
    player2_max_hp: int  # Canonical max HP for player2
    current_turn: int | None
    turn_number: int
    player1_defending: bool
    player2_defending: bool
    player1_ability_effect: str | None
    player2_ability_effect: str | None
    player1_ability_cooldown: int = 0
    player2_ability_cooldown: int = 0
    status: str
    winner_id: int | None = None
    combat_log: list[CombatLogEvent] = []
    player1_stats: PlayerStats | None = None
    player2_stats: PlayerStats | None = None

    model_config = ConfigDict(from_attributes=True)
