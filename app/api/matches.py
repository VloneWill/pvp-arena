from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.security import get_current_user_id
from app.db.database import get_db
from app.db.models import Match
from app.game.schemas import MatchOut, MatchEndRequest, ActionRequest, GameStateOut
from app.game.combat import (
    initialize_match,
    process_attack,
    process_defend,
    process_heal,
    process_double_attack_ability,
    advance_turn,
    check_match_end,
)

router = APIRouter(prefix="/matches", tags=["matches"])


@router.get("/{match_id}", response_model=MatchOut)
def get_match(
    match_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    if user_id not in (match.player1_id, match.player2_id):
        raise HTTPException(status_code=403, detail="Not your match")

    return match


@router.post("/{match_id}/end", response_model=MatchOut)
def end_match(
    match_id: int,
    payload: MatchEndRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    if user_id not in (match.player1_id, match.player2_id):
        raise HTTPException(status_code=403, detail="Not your match")

    if match.status != "active":
        raise HTTPException(status_code=409, detail="Match is not active")

    match.status = payload.status
    db.commit()
    db.refresh(match)
    return match


@router.get("/{match_id}/state", response_model=GameStateOut)
def get_game_state(
    match_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    if user_id not in (match.player1_id, match.player2_id):
        raise HTTPException(status_code=403, detail="Not your match")

    # Initialize match if not already initialized
    if match.current_turn is None:
        initialize_match(match)
        db.commit()
        db.refresh(match)

    # Check for winner
    winner_id = None
    if match.status == "active":
        winner_id = check_match_end(match)
        if winner_id:
            db.commit()
            db.refresh(match)

    return GameStateOut(
        match_id=match.id,
        player1_id=match.player1_id,
        player2_id=match.player2_id,
        player1_health=match.player1_health,
        player2_health=match.player2_health,
        current_turn=match.current_turn,
        turn_number=match.turn_number,
        player1_defending=match.player1_defending,
        player2_defending=match.player2_defending,
        player1_ability_effect=match.player1_ability_effect,
        player2_ability_effect=match.player2_ability_effect,
        status=match.status,
        winner_id=winner_id,
    )


@router.post("/{match_id}/action")
def take_action(
    match_id: int,
    payload: ActionRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    if user_id not in (match.player1_id, match.player2_id):
        raise HTTPException(status_code=403, detail="Not your match")

    if match.status != "active":
        raise HTTPException(status_code=409, detail="Match is not active")

    # Initialize match if not already initialized
    if match.current_turn is None:
        initialize_match(match)

    # Check if it's the user's turn
    if match.current_turn != user_id:
        raise HTTPException(status_code=409, detail="Not your turn")

    # Process the action
    is_player1 = user_id == match.player1_id
    opponent_id = match.player2_id if is_player1 else match.player1_id
    result = {}

    if payload.action == "attack":
        result = process_attack(match, user_id, opponent_id)
    elif payload.action == "defend":
        result = process_defend(match, user_id)
    elif payload.action == "heal":
        result = process_heal(match, user_id)
    elif payload.action == "double_attack":
        result = process_double_attack_ability(match, user_id)

    # Check if match ended
    winner_id = check_match_end(match)

    # Advance turn (unless match ended)
    if winner_id is None:
        advance_turn(match)

    db.commit()
    db.refresh(match)

    return {
        "action": payload.action,
        "result": result,
        "game_state": GameStateOut(
            match_id=match.id,
            player1_id=match.player1_id,
            player2_id=match.player2_id,
            player1_health=match.player1_health,
            player2_health=match.player2_health,
            current_turn=match.current_turn,
            turn_number=match.turn_number,
            player1_defending=match.player1_defending,
            player2_defending=match.player2_defending,
            player1_ability_effect=match.player1_ability_effect,
            player2_ability_effect=match.player2_ability_effect,
            status=match.status,
            winner_id=winner_id,
        ),
    }
