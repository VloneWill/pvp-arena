#imports for the auth router
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import Literal
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password, create_access_token, get_current_user_id
from app.db.database import get_db
from app.db.models import User

router = APIRouter(prefix="/auth", tags=["auth"])


#create the register request schema
class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=72)
    class_name: Literal["warrior", "mage", "druid", "rogue"] = Field(..., description="Player class: warrior, mage, druid, or rogue (locked after registration)")


#create the login request schema
class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=72)


#create the token response schema
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


#create the register endpoint
@router.post("/register", status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    # class_name is already validated by Pydantic Literal, so no need for manual validation
    
    existing = db.query(User).filter(User.username == payload.username).first()
    if existing:
        raise HTTPException(status_code=409, detail="Username already exists")

    try:
        pw_hash = hash_password(payload.password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    user = User(
        username=payload.username, 
        password_hash=pw_hash,
        class_name=payload.class_name,
        level=1,
        xp=0
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return {"id": user.id, "username": user.username, "class_name": user.class_name, "level": user.level, "xp": user.xp}


#create the login endpoint
@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

    token = create_access_token(subject=str(user.id))
    return TokenResponse(access_token=token)


#create the me endpoint
@router.get("/me")
def me(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "id": user.id, 
        "username": user.username,
        "class_name": user.class_name,
        "level": user.level,
        "xp": user.xp
    }


#create the get user by id endpoint
@router.get("/user/{user_id}")
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
):
    """Get user info by ID (for looking up opponent usernames)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "id": user.id, 
        "username": user.username,
        "class_name": user.class_name,
        "level": user.level,
        "xp": user.xp
    }
