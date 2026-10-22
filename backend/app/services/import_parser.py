from __future__ import annotations

import json
from typing import Any

from bs4 import BeautifulSoup
from pydantic import ValidationError

from ..schemas.bookmark import ImportItem


def items_from_payload(payload: Any) -> tuple[list[ImportItem], list[dict]]:
    if isinstance(payload, list):
        raw_items = payload
    elif isinstance(payload, dict):
        raw_items = payload.get("items")
        if raw_items is None:
            raw_items = payload.get("bookmarks")
        if raw_items is None and "url" in payload:
            raw_items = [payload]
        if raw_items is None:
            raw_items = []
    else:
        raise ValueError("unsupported json structure")

    items: list[ImportItem] = []
    errors: list[dict] = []
    for raw in raw_items:
        if not isinstance(raw, dict) or not raw.get("url"):
            continue
        category = raw.get("category") or raw.get("category_name")
        if isinstance(category, dict):
            category = category.get("name")
        tags = raw.get("tags") or []
        if isinstance(tags, str):
            tags = [piece.strip() for piece in tags.split(",") if piece.strip()]
        try:
            items.append(
                ImportItem(
                    url=str(raw["url"]),
                    title=str(raw.get("title") or "")[:500],
                    category=str(category)[:30] if category else None,
                    tags=tags,
                )
            )
        except (ValidationError, ValueError, TypeError) as exc:
            errors.append({"url": str(raw.get("url")), "reason": str(exc)[:300]})
    return items, errors


def items_from_html(content: str) -> tuple[list[ImportItem], list[dict]]:
    soup = BeautifulSoup(content, "html.parser")
    items: list[ImportItem] = []
    errors: list[dict] = []
    for anchor in soup.find_all("a", href=True):
        raw_tags = anchor.get("tags") or ""
        tags = [piece.strip() for piece in raw_tags.split(",") if piece.strip()]
        title = anchor.get_text(strip=True) or ""
        try:
            items.append(
                ImportItem(
                    url=str(anchor["href"]),
                    title=title[:500],
                    tags=tags,
                )
            )
        except (ValidationError, ValueError, TypeError) as exc:
            errors.append(
                {"url": str(anchor.get("href")), "reason": str(exc)[:300]}
            )
    return items, errors


def parse_file(content: bytes, filename: str = "") -> tuple[list[ImportItem], list[dict]]:
    text = content.decode("utf-8", errors="replace")
    stripped = text.lstrip()
    looks_like_json = filename.lower().endswith(".json") or stripped.startswith(
        ("{", "[")
    )
    if looks_like_json:
        return items_from_payload(json.loads(text))
    return items_from_html(text)
