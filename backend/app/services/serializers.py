from __future__ import annotations

from ..models import Bookmark


def bookmark_to_dict(bookmark: Bookmark) -> dict:
    category = None
    if bookmark.category is not None:
        category = {"id": bookmark.category.id, "name": bookmark.category.name}

    tags = sorted((tag.name for tag in bookmark.tags), key=str.lower)
    screenshot_url = None
    if bookmark.screenshot_path:
        relative = bookmark.screenshot_path.lstrip("/")
        if relative.startswith("screenshots/"):
            relative = relative[len("screenshots/") :]
        screenshot_url = f"/media/screenshots/{relative}"

    return {
        "id": bookmark.id,
        "url": bookmark.url,
        "title": bookmark.title,
        "category": category,
        "tags": tags,
        "status": bookmark.status,
        "http_status": bookmark.http_status,
        "response_ms": bookmark.response_ms,
        "last_error": bookmark.last_error,
        "last_checked_at": bookmark.last_checked_at,
        "visit_count": bookmark.visit_count,
        "last_visited_at": bookmark.last_visited_at,
        "description": bookmark.description,
        "cover_url": bookmark.cover_url,
        "screenshot_url": screenshot_url,
        "created_at": bookmark.created_at,
        "updated_at": bookmark.updated_at,
    }
