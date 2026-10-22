from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.urls import fallback_title
from ..models import Bookmark, Category, Tag
from ..schemas.bookmark import ImportItem


async def import_items(
    db: AsyncSession, items: list[ImportItem], mode: str = "skip"
) -> dict:
    categories = {
        category.name: category
        for category in (await db.execute(select(Category))).scalars().all()
    }
    tags = {
        tag.name.lower(): tag
        for tag in (await db.execute(select(Tag))).scalars().all()
    }

    urls = [item.url for item in items]
    existing_list = (
        (await db.execute(select(Bookmark).where(Bookmark.url.in_(urls))))
        .scalars()
        .all()
        if urls
        else []
    )
    existing = {bookmark.url: bookmark for bookmark in existing_list}

    imported = updated = skipped = failed = 0
    errors: list[dict] = []

    def get_category(name: str | None) -> Category | None:
        if not name:
            return None
        category = categories.get(name)
        if category is None:
            category = Category(name=name)
            db.add(category)
            categories[name] = category
        return category

    def get_tags(names: list[str]) -> list[Tag]:
        result: list[Tag] = []
        for name in names:
            key = name.lower()
            tag = tags.get(key)
            if tag is None:
                tag = Tag(name=name)
                db.add(tag)
                tags[key] = tag
            result.append(tag)
        return result

    for item in items:
        try:
            bookmark = existing.get(item.url)
            if bookmark is not None:
                if mode != "update":
                    skipped += 1
                    continue
                if item.title.strip():
                    bookmark.title = item.title.strip()
                if item.category:
                    bookmark.category = get_category(item.category.strip())
                if item.tags:
                    bookmark.tags = get_tags(item.tags)
                updated += 1
                continue

            bookmark = Bookmark(
                url=item.url,
                title=item.title.strip() or fallback_title(item.url),
                category=get_category(item.category.strip() if item.category else None),
                tags=get_tags(item.tags),
            )
            db.add(bookmark)
            existing[item.url] = bookmark
            imported += 1
        except Exception as exc:  # noqa: BLE001 - one bad row must not stop import
            failed += 1
            if len(errors) < 50:
                errors.append({"url": item.url, "reason": str(exc)[:300]})

    await db.commit()
    return {
        "imported": imported,
        "updated": updated,
        "skipped": skipped,
        "failed": failed,
        "errors": errors,
    }
