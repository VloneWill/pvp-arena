"""Leaderboard: top users by wins."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import User, Match

router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])


@router.get("")
def get_leaderboard(
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    Top users by wins. Sort: wins DESC, level DESC, username ASC.
    Returns rank, user_id, username, class_name, level, wins, losses.
    """
    finished = db.query(Match).filter(Match.status == "finished", Match.winner_id.isnot(None)).all()
    wins_map = {}
    losses_map = {}
    for m in finished:
        w = m.winner_id
        loser = m.player2_id if w == m.player1_id else m.player1_id
        wins_map[w] = wins_map.get(w, 0) + 1
        losses_map[loser] = losses_map.get(loser, 0) + 1
    all_ids = set(wins_map.keys()) | set(losses_map.keys())
    if not all_ids:
        return []
    users = {u.id: u for u in db.query(User).filter(User.id.in_(all_ids)).all()}
    rows = []
    for uid in all_ids:
        u = users.get(uid)
        if u:
            rows.append((u, wins_map.get(uid, 0), losses_map.get(uid, 0)))
    rows.sort(key=lambda x: (-x[1], -x[0].level, x[0].username))
    return [
        {
            "rank": rank,
            "user_id": user.id,
            "username": user.username,
            "class_name": user.class_name or "unknown",
            "level": user.level,
            "wins": wins,
            "losses": losses,
        }
        for rank, (user, wins, losses) in enumerate(rows[:limit], start=1)
    ]
