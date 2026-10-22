from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.errors import ApiError, ok
from ..core.security import require_token
from ..db.session import get_db
from ..models import Bookmark, Category
from ..schemas.category import CategoryCreate, CategoryUpdate

router = APIRouter(
    prefix="/api/categories",
    tags=["categories"],
    dependencies=[Depends(require_token)],
)


def _category_dict(category: Category, bookmark_count: int = 0) -> dict:
    return {
        "id": category.id,
        "name": category.name,
        "bookmark_count": bookmark_count,
        "created_at": category.created_at,
    }


@router.get("")
async def list_categories(db: AsyncSession = Depends(get_db)) -> dict:
    rows = (
        await db.execute(
            select(Category, func.count(Bookmark.id))
            .outerjoin(Bookmark, Bookmark.category_id == Category.id)
            .group_by(Category.id)
            .order_by(Category.name.asc())
        )
    ).all()
    return ok([_category_dict(category, count) for category, count in rows])


@router.post("", status_code=201)
async def create_category(
    payload: CategoryCreate, db: AsyncSession = Depends(get_db)
) -> dict:
    existing = await db.scalar(select(Category.id).where(Category.name == payload.name))
    if existing is not None:
        raise ApiError(409, "category already exists")

    category = Category(name=payload.name)
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return ok(_category_dict(category, 0))


@router.put("/{category_id}")
async def update_category(
    category_id: int,
    payload: CategoryUpdate,
    db: AsyncSession = Depends(get_db),
) -> dict:
    category = await db.get(Category, category_id)
    if category is None:
        raise ApiError(404, "category not found")

    duplicate = await db.scalar(
        select(Category.id).where(
            Category.name == payload.name, Category.id != category_id
        )
    )
    if duplicate is not None:
        raise ApiError(409, "category already exists")

    category.name = payload.name
    await db.commit()
    await db.refresh(category)
    count = (
        await db.scalar(
            select(func.count(Bookmark.id)).where(
                Bookmark.category_id == category_id
            )
        )
        or 0
    )
    return ok(_category_dict(category, count))


@router.delete("/{category_id}")
async def delete_category(
    category_id: int, db: AsyncSession = Depends(get_db)
) -> dict:
    category = await db.get(Category, category_id)
    if category is None:
        raise ApiError(404, "category not found")

    await db.delete(category)
    await db.commit()
    return ok({"deleted": True})
