from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.errors import ok
from ..core.security import require_token
from ..db.session import get_db
from ..models import Bookmark, Category, Tag

router = APIRouter(
    prefix="/api/stats",
    tags=["stats"],
    dependencies=[Depends(require_token)],
)


@router.get("")
async def get_stats(db: AsyncSession = Depends(get_db)) -> dict:
    rows = (
        await db.execute(
            select(Bookmark.status, func.count(Bookmark.id)).group_by(
                Bookmark.status
            )
        )
    ).all()
    counts = {"unknown": 0, "ok": 0, "error": 0, "timeout": 0}
    for status, count in rows:
        if status in counts:
            counts[status] = count

    categories = int(
        await db.scalar(select(func.count(Category.id))) or 0
    )
    tags = int(await db.scalar(select(func.count(Tag.id))) or 0)
    last_check_at = await db.scalar(select(func.max(Bookmark.last_checked_at)))

    return ok(
        {
            "total": sum(counts.values()),
            **counts,
            "categories": categories,
            "tags": tags,
            "last_check_at": last_check_at,
        }
    )
