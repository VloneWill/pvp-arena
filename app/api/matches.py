#imports for the matches router
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional, List

from app.core.security import get_current_user_id
from app.db.database import get_db
from app.db.models import Match
#imports for the schemas
from app.game.schemas import MatchOut, MatchEndRequest, ActionRequest, GameStateOut
#imports for the combat
from app.game.combat import (
    initialize_match,
    check_match_end,
    engine,
    InvalidActionError,
    MatchNotActiveError,
)
#create the matches router
router = APIRouter(prefix="/matches", tags=["matches"])


#create the get match history endpoint (MUST be before /{match_id} route)
@router.get("/history", response_model=List[MatchOut])
def match_history(
    limit: int = 25,
    offset: int = 0,
    status: Optional[str] = None,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    q = db.query(Match).filter(
        or_(Match.player1_id == user_id, Match.player2_id == user_id)
    )

    if status is not None:
        q = q.filter(Match.status == status)

    matches = (
        q.order_by(Match.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return matches


#create the get match endpoint
@router.get("/{match_id}", response_model=MatchOut)
def get_match(
    match_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    #get the match from the database
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    #check if the user is in the match
    if user_id not in (match.player1_id, match.player2_id):
        raise HTTPException(status_code=403, detail="Not your match")

    #return the match
    return match


#create the end match endpoint
@router.post("/{match_id}/end", response_model=MatchOut)
def end_match(
    match_id: int,
    payload: MatchEndRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    #get the match from the database
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    #check if the user is in the match
    if user_id not in (match.player1_id, match.player2_id):
        raise HTTPException(status_code=403, detail="Not your match")

    #check if the match is active
    if match.status != "active":
        raise HTTPException(status_code=409, detail="Match is not active")

    #update the match status
    match.status = payload.status
    db.commit()
    db.refresh(match)
    return match


#create the forfeit match endpoint
@router.post("/{match_id}/forfeit", response_model=MatchOut)
def forfeit_match(
    match_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Forfeit an active match - opponent wins."""
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    if user_id not in (match.player1_id, match.player2_id):
        raise HTTPException(status_code=403, detail="Not your match")

    if match.status != "active":
        raise HTTPException(status_code=409, detail="Match is not active")

    # Set opponent as winner by setting forfeiting player's health to 0
    if user_id == match.player1_id:
        match.player1_health = 0
    else:
        match.player2_health = 0
    
    # Check match end to properly set winner
    from app.game.combat import check_match_end
    check_match_end(match)
    db.commit()
    db.refresh(match)
    return match


#create the get game state endpoint
@router.get("/{match_id}/state", response_model=GameStateOut)
def get_game_state(
    match_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    #get the match from the database
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    if user_id not in (match.player1_id, match.player2_id):
        raise HTTPException(status_code=403, detail="Not your match")

    # Initialize match if not already initialized (only if match hasn't started)
    if match.current_turn is None and match.turn_number == 0:
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

#create the take action endpoint
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

    # Initialize match if not already initialized (only if match hasn't started)
    if match.current_turn is None and match.turn_number == 0:
        initialize_match(match)

    is_player1 = user_id == match.player1_id
    opponent_id = match.player2_id if is_player1 else match.player1_id

    try:
        if payload.action == "attack":
            result = engine.attack(match, attacker_id=user_id, defender_id=opponent_id)
            result["attacker_id"] = user_id
            result["defender_id"] = opponent_id
        elif payload.action == "defend":
            result = engine.defend(match, player_id=user_id)
            result["actor_id"] = user_id
            result["opponent_id"] = opponent_id
        elif payload.action == "heal":
            result = engine.heal(match, player_id=user_id)
            result["actor_id"] = user_id
            result["opponent_id"] = opponent_id
        elif payload.action == "double_attack":
            result = engine.double_attack(match, player_id=user_id)
            result["attacker_id"] = user_id
            result["defender_id"] = opponent_id
        else:
            raise InvalidActionError(f"Unknown action: {payload.action}")
    except MatchNotActiveError as exc:
        # Match is no longer active
        raise HTTPException(status_code=409, detail=str(exc))
    except InvalidActionError as exc:
        # Invalid turn, actor, or action
        raise HTTPException(status_code=400, detail=str(exc))

    db.commit()
    db.refresh(match)

    winner_id = result.get("winner_id")

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
