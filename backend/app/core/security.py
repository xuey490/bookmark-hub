from __future__ import annotations

import secrets

from fastapi import Depends, Header, HTTPException

from .config import Settings, get_settings


async def require_token(
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> None:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="missing token")
    token = authorization[7:].strip()
    if (
        not token
        or not settings.api_token
        or not secrets.compare_digest(token, settings.api_token)
    ):
        raise HTTPException(status_code=401, detail="invalid token")
