from datetime import datetime, timedelta, timezone
from jose import jwt
import bcrypt

from app.core.config import settings


def hash_password(password: str) -> str:
    pw_bytes = password.encode("utf-8")

    # bcrypt hard limit
    if len(pw_bytes) > 72:
        raise ValueError("Password too long (bcrypt max is 72 bytes)")

    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pw_bytes, salt).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    pw_bytes = password.encode("utf-8")
    return bcrypt.checkpw(pw_bytes, password_hash.encode("utf-8"))


def create_access_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_alg)
