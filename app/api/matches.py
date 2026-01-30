#imports for the matches router
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional, List

from app.core.security import get_current_user_id
from app.db.database import get_db
from app.db.models import Match
#imports for the schemas
from app.game.schemas import MatchOut, MatchEndRequest, ActionRequest, GameStateOut, CombatLogDisplayEntry
from app.game.combat_log import build_display_entry
#imports for the combat
from app.game.combat import (
    initialize_match,
    check_match_end,
    CombatEngine,
    InvalidActionError,
    MatchNotActiveError,
)
#create the matches router
router = APIRouter(prefix="/matches", tags=["matches"])


#create the get match history endpoint (MUST be before /{match_id} route)
@router.get("/history")
def match_history(
    limit: int = 25,
    offset: int = 0,
    status: Optional[str] = None,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    from app.game.schemas import MatchHistoryItem
    from app.db.models import User
    
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
    
    # Enrich matches with opponent info and result
    history_items = []
    for match in matches:
        # Determine opponent
        opponent_id = match.player2_id if match.player1_id == user_id else match.player1_id
        opponent = db.query(User).filter(User.id == opponent_id).first()
        
        # Determine result
        if match.status == "finished" and match.winner_id:
            result = "WIN" if match.winner_id == user_id else "LOSS"
        elif match.status == "canceled":
            result = "CANCELED"
        else:
            result = "ACTIVE"
        
        # Build opponent info (class_name is required)
        opponent_info = {
            "username": opponent.username if opponent else f"Player {opponent_id}",
            "class_name": opponent.class_name if opponent and opponent.class_name else "unknown",
            "level": opponent.level if opponent else None,
        }
        
        history_items.append({
            "id": match.id,
            "status": match.status,
            "winner_id": match.winner_id,
            "result": result,
            "opponent": opponent_info,
            "created_at": match.created_at.isoformat() if match.created_at else None,
        })
    
    return history_items


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
    check_match_end(match, db)
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
        initialize_match(match, db)
        db.commit()
        db.refresh(match)

    # Check for winner
    if match.status == "active":
        winner_id = check_match_end(match, db)
        if winner_id:
            db.commit()
            db.refresh(match)

    # Ensure combat_log is initialized
    if match.combat_log is None:
        match.combat_log = []
    
    # Fetch player stats for both players
    from app.db.models import User
    from app.game.classes import get_max_hp
    p1 = db.query(User).filter(User.id == match.player1_id).first()
    p2 = db.query(User).filter(User.id == match.player2_id).first()
    
    from app.game.schemas import PlayerStats
    p1_stats = PlayerStats(level=p1.level, xp=p1.xp, class_name=p1.class_name) if p1 else None
    p2_stats = PlayerStats(level=p2.level, xp=p2.xp, class_name=p2.class_name) if p2 else None
    
    # Compute max HP consistently (single source of truth)
    p1_max_hp = get_max_hp(p1) if p1 else 100
    p2_max_hp = get_max_hp(p2) if p2 else 100
    
    # Clamp health values to never exceed max_hp (defensive guarantee)
    p1_health = min(match.player1_health, p1_max_hp)
    p2_health = min(match.player2_health, p2_max_hp)
    
    p1_cooldowns = getattr(match, "player1_cooldowns", None) or {}
    p2_cooldowns = getattr(match, "player2_cooldowns", None) or {}
    p1_effects = getattr(match, "player1_effects", None) or []
    p2_effects = getattr(match, "player2_effects", None) or []

    from app.game.tooltip_stats import compute_action_tooltips
    p1_class = p1.class_name if p1 else None
    p2_class = p2.class_name if p2 else None
    p1_level = p1.level if p1 else 1
    p2_level = p2.level if p2 else 1
    p1_action_tooltips = compute_action_tooltips(p1_class, p1_level, p1_cooldowns) if p1_class else {}
    p2_action_tooltips = compute_action_tooltips(p2_class, p2_level, p2_cooldowns) if p2_class else {}

    combat_log_events = match.combat_log or []
    combat_log_display_list = [
        CombatLogDisplayEntry(**build_display_entry(ev, user_id))
        for ev in combat_log_events
    ]

    return GameStateOut(
        match_id=match.id,
        player1_id=match.player1_id,
        player2_id=match.player2_id,
        player1_health=p1_health,
        player2_health=p2_health,
        player1_max_hp=p1_max_hp,
        player2_max_hp=p2_max_hp,
        current_turn=match.current_turn,
        turn_number=match.turn_number,
        player1_defending=match.player1_defending,
        player2_defending=match.player2_defending,
        player1_ability_effect=match.player1_ability_effect,
        player2_ability_effect=match.player2_ability_effect,
        player1_ability_cooldown=match.player1_ability_cooldown,
        player2_ability_cooldown=match.player2_ability_cooldown,
        player1_cooldowns=p1_cooldowns,
        player2_cooldowns=p2_cooldowns,
        player1_effects=p1_effects,
        player2_effects=p2_effects,
        status=match.status,
        winner_id=match.winner_id,
        combat_log=match.combat_log or [],
        combat_log_display=combat_log_display_list,
        player1_stats=p1_stats,
        player2_stats=p2_stats,
        player1_action_tooltips=p1_action_tooltips,
        player2_action_tooltips=p2_action_tooltips,
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
        initialize_match(match, db)

    is_player1 = user_id == match.player1_id
    opponent_id = match.player2_id if is_player1 else match.player1_id

    action_type = payload.action
    ability_id = payload.ability
    if action_type == "ability" and not ability_id:
        raise HTTPException(status_code=400, detail="ability is required when action is 'ability'")
    if action_type not in ("attack", "defend", "heal", "ability"):
        ability_id = action_type
        action_type = "ability"

    engine = CombatEngine(db)
    try:
        if action_type == "attack":
            result = engine.attack(match, attacker_id=user_id, defender_id=opponent_id)
            result["attacker_id"] = user_id
            result["defender_id"] = opponent_id
        elif action_type == "defend":
            result = engine.defend(match, player_id=user_id)
            result["actor_id"] = user_id
            result["opponent_id"] = opponent_id
        elif action_type == "heal":
            result = engine.heal(match, player_id=user_id)
            result["actor_id"] = user_id
            result["opponent_id"] = opponent_id
        else:
            result = engine.class_ability(match, player_id=user_id, ability_id=ability_id)
            result["actor_id"] = user_id
            result["opponent_id"] = opponent_id
    except MatchNotActiveError as exc:
        # Match is no longer active
        raise HTTPException(status_code=409, detail=str(exc))
    except InvalidActionError as exc:
        # Invalid turn, actor, or action
        raise HTTPException(status_code=400, detail=str(exc))

    db.commit()
    db.refresh(match)

    # Ensure combat_log is initialized
    if match.combat_log is None:
        match.combat_log = []

    # Fetch player stats for both players
    from app.db.models import User
    from app.game.classes import get_max_hp
    p1 = db.query(User).filter(User.id == match.player1_id).first()
    p2 = db.query(User).filter(User.id == match.player2_id).first()
    
    from app.game.schemas import PlayerStats
    p1_stats = PlayerStats(level=p1.level, xp=p1.xp, class_name=p1.class_name) if p1 else None
    p2_stats = PlayerStats(level=p2.level, xp=p2.xp, class_name=p2.class_name) if p2 else None

    # Compute max HP consistently (single source of truth)
    p1_max_hp = get_max_hp(p1) if p1 else 100
    p2_max_hp = get_max_hp(p2) if p2 else 100
    
    # Clamp health values to never exceed max_hp (defensive guarantee)
    p1_health = min(match.player1_health, p1_max_hp)
    p2_health = min(match.player2_health, p2_max_hp)

    from app.game.tooltip_stats import compute_action_tooltips
    p1_class = p1.class_name if p1 else None
    p2_class = p2.class_name if p2 else None
    p1_level = p1.level if p1 else 1
    p2_level = p2.level if p2 else 1
    p1_cooldowns = getattr(match, "player1_cooldowns", None) or {}
    p2_cooldowns = getattr(match, "player2_cooldowns", None) or {}
    p1_action_tooltips = compute_action_tooltips(p1_class, p1_level, p1_cooldowns) if p1_class else {}
    p2_action_tooltips = compute_action_tooltips(p2_class, p2_level, p2_cooldowns) if p2_class else {}
    combat_log_after = match.combat_log or []
    combat_log_display_after = [
        CombatLogDisplayEntry(**build_display_entry(ev, user_id))
        for ev in combat_log_after
    ]

    action_display = ability_id or result.get("action", action_type)
    return {
        "action": action_display,
        "result": result,
        "game_state": GameStateOut(
            match_id=match.id,
            player1_id=match.player1_id,
            player2_id=match.player2_id,
            player1_health=p1_health,
            player2_health=p2_health,
            player1_max_hp=p1_max_hp,
            player2_max_hp=p2_max_hp,
            current_turn=match.current_turn,
            turn_number=match.turn_number,
            player1_defending=match.player1_defending,
            player2_defending=match.player2_defending,
            player1_ability_effect=match.player1_ability_effect,
            player2_ability_effect=match.player2_ability_effect,
            player1_ability_cooldown=match.player1_ability_cooldown,
            player2_ability_cooldown=match.player2_ability_cooldown,
            player1_cooldowns=p1_cooldowns,
            player2_cooldowns=p2_cooldowns,
            player1_effects=getattr(match, "player1_effects", None) or [],
            player2_effects=getattr(match, "player2_effects", None) or [],
            status=match.status,
            winner_id=match.winner_id,
            combat_log=combat_log_after,
            combat_log_display=combat_log_display_after,
            player1_stats=p1_stats,
            player2_stats=p2_stats,
            player1_action_tooltips=p1_action_tooltips,
            player2_action_tooltips=p2_action_tooltips,
        ),
    }
