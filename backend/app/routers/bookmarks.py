from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..core.config import Settings, get_settings
from ..core.errors import ApiError, ok
from ..core.security import require_token
from ..core.urls import fallback_title
from ..db.session import get_db
from ..models import Bookmark, Category, Tag
from ..models.category import utcnow_iso
from ..schemas.bookmark import BookmarkBatchDelete, BookmarkCreate, BookmarkUpdate
from ..services.check_service import check_bookmark
from ..services.serializers import bookmark_to_dict

router = APIRouter(
    prefix="/api/bookmarks",
    tags=["bookmarks"],
    dependencies=[Depends(require_token)],
)

STATUS_VALUES = ("unknown", "ok", "error", "timeout")


async def _get_bookmark(db: AsyncSession, bookmark_id: int) -> Bookmark:
    bookmark = await db.scalar(
        select(Bookmark)
        .where(Bookmark.id == bookmark_id)
        .options(
            selectinload(Bookmark.category),
            selectinload(Bookmark.tags),
        )
    )
    if bookmark is None:
        raise ApiError(404, "bookmark not found")
    return bookmark


async def _get_category(
    db: AsyncSession, category_id: int | None
) -> Category | None:
    if category_id is None:
        return None
    category = await db.get(Category, category_id)
    if category is None:
        raise ApiError(400, "category not found")
    return category


async def _resolve_tags(db: AsyncSession, names: list[str]) -> list[Tag]:
    if not names:
        return []
    existing = (
        (await db.execute(select(Tag).where(Tag.name.in_(names))))
        .scalars()
        .all()
    )
    by_name = {tag.name.lower(): tag for tag in existing}
    result: list[Tag] = []
    for name in names:
        key = name.lower()
        tag = by_name.get(key)
        if tag is None:
            tag = Tag(name=name)
            db.add(tag)
            by_name[key] = tag
        result.append(tag)
    return result


@router.get("")
async def list_bookmarks(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    q: str | None = Query(default=None, max_length=200),
    category_id: int | None = Query(default=None),
    tag: str | None = Query(default=None, max_length=20),
    status: Literal["unknown", "ok", "error", "timeout"] | None = Query(
        default=None
    ),
    sort: Literal["created_at_desc", "updated_at_desc", "title_asc"] = Query(
        default="created_at_desc"
    ),
    db: AsyncSession = Depends(get_db),
) -> dict:
    conditions = []
    if q and q.strip():
        keyword = q.strip()
        conditions.append(
            or_(
                Bookmark.title.contains(keyword, autoescape=True),
                Bookmark.url.contains(keyword, autoescape=True),
            )
        )
    if category_id is not None:
        conditions.append(Bookmark.category_id == category_id)
    if status is not None:
        conditions.append(Bookmark.status == status)

    count_stmt = select(func.count(func.distinct(Bookmark.id))).select_from(
        Bookmark
    )
    if tag:
        count_stmt = count_stmt.join(Bookmark.tags).where(Tag.name == tag)
    if conditions:
        count_stmt = count_stmt.where(*conditions)
    total = int(await db.scalar(count_stmt) or 0)

    stmt = select(Bookmark).options(
        selectinload(Bookmark.category), selectinload(Bookmark.tags)
    )
    if tag:
        stmt = stmt.join(Bookmark.tags).where(Tag.name == tag)
    if conditions:
        stmt = stmt.where(*conditions)

    if sort == "title_asc":
        stmt = stmt.order_by(func.lower(Bookmark.title).asc(), Bookmark.id.desc())
    elif sort == "updated_at_desc":
        stmt = stmt.order_by(Bookmark.updated_at.desc(), Bookmark.id.desc())
    else:
        stmt = stmt.order_by(Bookmark.created_at.desc(), Bookmark.id.desc())

    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    items = (await db.execute(stmt)).scalars().unique().all()
    pages = (total + page_size - 1) // page_size if total else 0

    return ok(
        {
            "items": [bookmark_to_dict(item) for item in items],
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": pages,
        }
    )


@router.post("", status_code=201)
async def create_bookmark(
    payload: BookmarkCreate, db: AsyncSession = Depends(get_db)
) -> dict:
    existing_id = await db.scalar(
        select(Bookmark.id).where(Bookmark.url == payload.url)
    )
    if existing_id is not None:
        raise ApiError(
            409, "bookmark already exists", {"id": existing_id}
        )

    category = await _get_category(db, payload.category_id)
    tags = await _resolve_tags(db, payload.tags)
    bookmark = Bookmark(
        url=payload.url,
        title=payload.title.strip() or fallback_title(payload.url),
        category=category,
        tags=tags,
    )
    db.add(bookmark)
    await db.commit()
    await db.refresh(bookmark)
    return ok(bookmark_to_dict(bookmark))


@router.post("/batch-delete")
async def batch_delete_bookmarks(
    payload: BookmarkBatchDelete, db: AsyncSession = Depends(get_db)
) -> dict:
    result = await db.execute(
        delete(Bookmark).where(Bookmark.id.in_(payload.ids))
    )
    await db.commit()
    return ok({"deleted": max(0, result.rowcount or 0)})


@router.get("/{bookmark_id}")
async def get_bookmark(
    bookmark_id: int, db: AsyncSession = Depends(get_db)
) -> dict:
    bookmark = await _get_bookmark(db, bookmark_id)
    return ok(bookmark_to_dict(bookmark))


@router.put("/{bookmark_id}")
async def update_bookmark(
    bookmark_id: int,
    payload: BookmarkUpdate,
    db: AsyncSession = Depends(get_db),
) -> dict:
    bookmark = await _get_bookmark(db, bookmark_id)
    fields = payload.model_fields_set

    if "url" in fields and payload.url is not None:
        if payload.url != bookmark.url:
            duplicate = await db.scalar(
                select(Bookmark.id).where(
                    Bookmark.url == payload.url, Bookmark.id != bookmark_id
                )
            )
            if duplicate is not None:
                raise ApiError(
                    409, "bookmark already exists", {"id": duplicate}
                )
            bookmark.url = payload.url
            bookmark.status = "unknown"
            bookmark.http_status = None
            bookmark.response_ms = None
            bookmark.last_error = None
            bookmark.last_checked_at = None

    if "title" in fields and payload.title is not None:
        bookmark.title = payload.title.strip() or fallback_title(bookmark.url)

    if "category_id" in fields:
        bookmark.category = await _get_category(db, payload.category_id)

    if "tags" in fields and payload.tags is not None:
        bookmark.tags = await _resolve_tags(db, payload.tags)

    bookmark.updated_at = utcnow_iso()
    await db.commit()
    return ok(bookmark_to_dict(bookmark))


@router.delete("/{bookmark_id}")
async def delete_bookmark(
    bookmark_id: int, db: AsyncSession = Depends(get_db)
) -> dict:
    bookmark = await _get_bookmark(db, bookmark_id)
    await db.delete(bookmark)
    await db.commit()
    return ok({"deleted": True})


@router.post("/{bookmark_id}/check")
async def check_bookmark_endpoint(
    bookmark_id: int,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    bookmark = await _get_bookmark(db, bookmark_id)
    await check_bookmark(db, bookmark, settings)
    return ok(bookmark_to_dict(bookmark))


@router.post("/{bookmark_id}/visit")
async def record_bookmark_visit(
    bookmark_id: int, db: AsyncSession = Depends(get_db)
) -> dict:
    result = await db.execute(
        update(Bookmark)
        .where(Bookmark.id == bookmark_id)
        .values(
            visit_count=Bookmark.visit_count + 1,
            last_visited_at=utcnow_iso(),
        )
    )
    if not result.rowcount:
        raise ApiError(404, "bookmark not found")

    await db.commit()
    bookmark = await _get_bookmark(db, bookmark_id)
    return ok(bookmark_to_dict(bookmark))
