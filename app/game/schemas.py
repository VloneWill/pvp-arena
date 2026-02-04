#imports for the schemas
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import Literal


#create the match out schema
class MatchOut(BaseModel):
    id: int
    player1_id: int
    player2_id: int
    status: str
    winner_id: int | None = None
    current_turn: int | None = None
    turn_expires_at: datetime | None = None  # serialized as ISO in JSON

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
# Supports: { "action": "attack" }, { "action": "defend" }, { "action": "heal" },
# { "action": "ability", "ability": "fireball" }, or legacy { "action": "power_strike" } (treated as ability id).
class ActionRequest(BaseModel):
    action: str  # "attack" | "defend" | "heal" | "ability" | or any ability id (e.g. power_strike, fireball)
    ability: str | None = None  # required when action is "ability", e.g. "fireball"


#create the combat log event schema
class CombatLogEvent(BaseModel):
    action_type: str
    action_key: str | None = None  # canonical action name for display, e.g. "attack", "power_strike"
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
    effect: str | None = None
    amount: int | None = None
    duration: int | None = None
    turns_left: int | None = None
    # Buff breakdown for combat log display
    heal_bonus_shapeshift: int | None = None
    damage_bonus_shapeshift: int | None = None
    damage_bonus_battle_shout: int | None = None
    damage_bonus_chill: int | None = None
    damage_reduced_defend: int | None = None
    damage_reduced_battle_shout: int | None = None
    damage_reduced_shapeshift: int | None = None
    damage_reduced_shield_wall: int | None = None
    damage_reflected_shield_wall: int | None = None
    damage_absorbed_arcane_shield: int | None = None
    damage_reflected_thorns: int | None = None
    evaded: bool | None = None

    model_config = ConfigDict(extra="allow")  # allow other event fields from combat


class CombatLogDisplayEntry(BaseModel):
    """Pre-rendered combat log line for the requesting user (correct grammar + perspective)."""
    message: str
    tone: str  # "damage" | "heal" | "defend" | "buff" | "neutral"
    is_my_action: bool


#create the player stats schema
class PlayerStats(BaseModel):
    level: int
    xp: int
    class_name: str


# Per-action computed tooltip stats (damage_min/max, heal_amount, shield_amount, duration, etc.)
class ActionTooltipStats(BaseModel):
    damage_min: int | None = None
    damage_max: int | None = None
    heal_amount: int | None = None
    shield_amount: int | None = None
    reduction_pct: int | None = None
    reflect_pct: int | None = None
    avoid_pct: int | None = None
    damage_per_tick: int | None = None
    damage_boost_pct: int | None = None
    defense_boost_pct: int | None = None
    duration: int | None = None
    cooldown_total: int = 0
    cooldown_remaining: int = 0
    summary: str = ""

    model_config = ConfigDict(extra="allow")  # allow extra fields from backend


#create the game state out schema
class GameStateOut(BaseModel):
    match_id: int
    player1_id: int
    player2_id: int
    player1_health: int
    player2_health: int
    player1_max_hp: int
    player2_max_hp: int
    current_turn: int | None
    turn_number: int
    player1_defending: bool
    player2_defending: bool
    player1_ability_effect: str | None = None
    player2_ability_effect: str | None = None
    player1_ability_cooldown: int = 0
    player2_ability_cooldown: int = 0
    player1_cooldowns: dict = {}
    player2_cooldowns: dict = {}
    player1_effects: list = []
    player2_effects: list = []
    status: str
    winner_id: int | None = None
    combat_log: list[CombatLogEvent] = []
    combat_log_display: list[CombatLogDisplayEntry] = []  # server-rendered messages for viewer
    player1_stats: PlayerStats | None = None
    player2_stats: PlayerStats | None = None
    player1_action_tooltips: dict = {}  # action_id -> ActionTooltipStats-like dict
    player2_action_tooltips: dict = {}
    turn_expires_at: datetime | None = None  # serialized as ISO for turn timer
    server_time: str | None = None  # ISO timestamp for clock drift adjustment

    model_config = ConfigDict(from_attributes=True)
