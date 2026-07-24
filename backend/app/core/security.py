import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
import bcrypt
import jwt
from fastapi import Header, HTTPException, Request, Response, status, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import User

JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
ACCESS_TOKEN_TTL_MINUTES = int(os.getenv("ACCESS_TOKEN_TTL_MINUTES", "15"))
REFRESH_TOKEN_TTL_DAYS = int(os.getenv("REFRESH_TOKEN_TTL_DAYS", "7"))
ACCESS_COOKIE_NAME = "access_token"
REFRESH_COOKIE_NAME = "refresh_token"
COOKIE_SAME_SITE = "lax"
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "true").lower() == "true"
COOKIE_HTTP_ONLY = True
_refresh_token_store: dict[str, int] = {}


def _create_token(subject: int, token_type: str, ttl: timedelta,extra: dict | None = None) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + ttl).timestamp()),
        "jti": str(uuid.uuid4()),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def create_access_token(user_id: int, role: str) -> str:
    return _create_token(user_id, "access", timedelta(minutes=ACCESS_TOKEN_TTL_MINUTES),extra={"role": role})


def create_refresh_token(user_id: int) -> str:
    return _create_token(user_id, "refresh", timedelta(days=REFRESH_TOKEN_TTL_DAYS))


def _decode_token(token: str, expected_type: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token") from exc

    if payload.get("type") != expected_type:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    return payload


def set_session_cookies(response: Response, user_id: int, role: str) -> tuple[str, str]:
    access_token = create_access_token(user_id, role)
    refresh_token = create_refresh_token(user_id)
    refresh_payload = _decode_token(refresh_token, "refresh")

    _refresh_token_store[refresh_payload["jti"]] = user_id

    response.set_cookie(
        key=ACCESS_COOKIE_NAME,
        value=access_token,
        httponly=COOKIE_HTTP_ONLY,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAME_SITE,
        path="/",
    )
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        httponly=COOKIE_HTTP_ONLY,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAME_SITE,
        path="/",
    )
    return access_token, refresh_token


def clear_session_cookies(response: Response) -> None:
    response.delete_cookie(ACCESS_COOKIE_NAME, path="/")
    response.delete_cookie(REFRESH_COOKIE_NAME, path="/")


def get_current_user(request: Request) -> dict[str, Any]:
    access_token = request.cookies.get(ACCESS_COOKIE_NAME)
    if not access_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    payload = _decode_token(access_token, "access")
    return payload

def get_current_user_db(
    payload: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    user = db.query(User).filter(User.id == payload["sub"]).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user

def rotate_refresh_token(response: Response, refresh_token: str) -> tuple[str, str]:
    payload = _decode_token(refresh_token, "refresh")
    jti = payload.get("jti")
    if not jti or _refresh_token_store.get(jti) is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token revoked")

    _refresh_token_store.pop(jti, None)
    user_id = payload.get("sub")
    if not isinstance(user_id, int):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    return set_session_cookies(response, user_id)
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))

def require_admin(payload: dict = Depends(get_current_user)) -> None:
    if (payload.get("role") or "").lower() != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can list users",
        )
    return None