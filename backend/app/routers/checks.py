from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import Settings, get_settings
from ..core.errors import ok
from ..core.security import require_token
from ..db.session import get_db
from ..schemas.check import CheckRequest
from ..services.check_service import check_all, check_urls

router = APIRouter(
    prefix="/api/check",
    tags=["checks"],
    dependencies=[Depends(require_token)],
)


@router.post("/urls")
async def run_checks(
    payload: CheckRequest,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    if payload.urls:
        summary = await check_urls(db, payload.urls, settings)
    else:
        summary = await check_all(db, settings)
    return ok(summary)
