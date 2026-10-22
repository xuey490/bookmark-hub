from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.errors import ok
from ..core.security import require_token
from ..db.session import get_db
from ..models import Tag, bookmark_tags

router = APIRouter(
    prefix="/api/tags",
    tags=["tags"],
    dependencies=[Depends(require_token)],
)


@router.get("")
async def list_tags(
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
) -> dict:
    count_expr = func.count(bookmark_tags.c.bookmark_id)
    rows = (
        await db.execute(
            select(Tag.name, count_expr)
            .join(bookmark_tags, bookmark_tags.c.tag_id == Tag.id)
            .group_by(Tag.id)
            .order_by(count_expr.desc(), Tag.name.asc())
            .limit(limit)
        )
    ).all()
    return ok([{"name": name, "count": count} for name, count in rows])
