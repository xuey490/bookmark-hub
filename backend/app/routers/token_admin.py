from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends

from ..core.config import Settings, get_settings
from ..core.errors import ok
from ..core.security import require_token
from ..schemas.token import TokenUpdate

router = APIRouter(
    prefix="/api/token",
    tags=["token"],
    dependencies=[Depends(require_token)],
)


def _persist_token(settings: Settings, token: str) -> None:
    token_file = settings.data_dir / "api_token.txt"
    token_file.parent.mkdir(parents=True, exist_ok=True)
    token_file.write_text(token, encoding="utf-8")
    token_file.chmod(0o600)
    settings.api_token = token


@router.put("")
async def update_token(
    payload: TokenUpdate,
    settings: Settings = Depends(get_settings),
) -> dict:
    _persist_token(settings, payload.token)
    return ok({"token": payload.token})


@router.post("/reset")
async def reset_token(
    settings: Settings = Depends(get_settings),
) -> dict:
    token = secrets.token_urlsafe(32)
    _persist_token(settings, token)
    return ok({"token": token})
