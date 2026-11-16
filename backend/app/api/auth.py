"""Invite-code -> bearer token auth (docs/design.md § API contract, § Privacy and safety).

A short-lived JWT (HS256, signed with JWT_SECRET) is issued in exchange
for the shared invite code, and required on every endpoint except
POST /api/auth, via the `require_token` dependency.
"""

from __future__ import annotations

import time
import uuid

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import Settings, get_settings

TOKEN_TTL_SECONDS = 7 * 24 * 60 * 60  # 7 days — a group of friends, not a bank

_bearer_scheme = HTTPBearer(auto_error=False)


def _signing_key(settings: Settings) -> str:
    """Refuse to sign or verify with an empty key.

    PyJWT happily HMACs with b"" — an unset JWT_SECRET wouldn't fail
    loudly, it would just make every token forgeable by anyone who
    guesses the key is empty. Fail fast instead.
    """
    if not settings.jwt_secret:
        raise RuntimeError("JWT_SECRET is not set — see .env.example")
    return settings.jwt_secret


def issue_token(settings: Settings) -> str:
    now = int(time.time())
    payload = {"iat": now, "exp": now + TOKEN_TTL_SECONDS, "jti": uuid.uuid4().hex}
    return jwt.encode(payload, _signing_key(settings), algorithm="HS256")


def require_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    settings: Settings = Depends(get_settings),
) -> None:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Missing bearer token")
    try:
        jwt.decode(credentials.credentials, _signing_key(settings), algorithms=["HS256"])
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc
