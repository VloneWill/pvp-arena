from pydantic import BaseModel, ConfigDict
from typing import Literal


class MatchOut(BaseModel):
    id: int
    player1_id: int
    player2_id: int
    status: str

    model_config = ConfigDict(from_attributes=True)


class QueueStatusOut(BaseModel):
    in_queue: bool
    position: int | None
    queue_size: int


class MatchEndRequest(BaseModel):
    status: Literal["finished", "canceled"]


class ActionRequest(BaseModel):
    action: Literal["attack", "defend", "heal", "double_attack"]


class GameStateOut(BaseModel):
    match_id: int
    player1_id: int
    player2_id: int
    player1_health: int
    player2_health: int
    current_turn: int | None
    turn_number: int
    player1_defending: bool
    player2_defending: bool
    player1_ability_effect: str | None
    player2_ability_effect: str | None
    status: str
    winner_id: int | None = None

    model_config = ConfigDict(from_attributes=True)
