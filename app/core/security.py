#imports for the security
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

#imports for the settings
from app.core.config import settings

#create the bearer scheme
bearer_scheme = HTTPBearer()

#create the hash password function
def hash_password(password: str) -> str:
    pw_bytes = password.encode("utf-8")

    # bcrypt hard limit
    if len(pw_bytes) > 72:
        raise ValueError("Password too long (bcrypt max is 72 bytes)")

    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pw_bytes, salt).decode("utf-8")

#create the verify password function
def verify_password(password: str, password_hash: str) -> bool:
    pw_bytes = password.encode("utf-8")
    return bcrypt.checkpw(pw_bytes, password_hash.encode("utf-8"))

#create the create access token function
def create_access_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_alg)

#create the get current user id function
def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> int:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_alg])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return int(user_id)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
