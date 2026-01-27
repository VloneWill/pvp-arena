#imports for the matchmaking router
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

#imports for the security
from app.core.security import get_current_user_id
from app.db.database import get_db
from app.db.models import Match
from app.game.engine import queue
from app.game.schemas import MatchOut, QueueStatusOut
from app.game.combat import initialize_match

#create the matchmaking router
router = APIRouter(prefix="/matchmaking", tags=["matchmaking"])


#create the join queue endpoint
@router.post("/join")
def join_queue(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    # Check if user already has an active match
    active_match = db.query(Match).filter(
        (Match.player1_id == user_id) | (Match.player2_id == user_id),
        Match.status == "active"
    ).first()
    
    if active_match:
        # Remove from queue if they're in it
        queue.leave(user_id)
        return {"status": "matched", "match": MatchOut.model_validate(active_match)}

    queue.join(user_id)

    pair = queue.pop_pair()
    if pair is None:
        pos = queue.position(user_id)
        return {"status": "waiting", "position": pos, "queue_size": queue.size()}

    p1, p2 = pair
    match = Match(player1_id=p1, player2_id=p2, status="active")
    db.add(match)
    db.commit()
    db.refresh(match)
    initialize_match(match)
    db.commit()
    db.refresh(match)

    return {"status": "matched", "match": MatchOut.model_validate(match)}


#create the leave queue endpoint
@router.post("/leave")
def leave_queue(
    user_id: int = Depends(get_current_user_id),
):
    queue.leave(user_id)
    return {"status": "left"}


#create the status endpoint
@router.get("/status", response_model=QueueStatusOut)
def status(
    user_id: int = Depends(get_current_user_id),
):
    pos = queue.position(user_id)
    return QueueStatusOut(
        in_queue=pos is not None,
        position=pos,
        queue_size=queue.size(),
    )
