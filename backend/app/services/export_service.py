from __future__ import annotations

import html
import json
from collections import OrderedDict
from datetime import datetime, timezone

from ..models import Bookmark, Category


def _bookmark_payload(bookmark: Bookmark) -> dict:
    return {
        "url": bookmark.url,
        "title": bookmark.title,
        "category": bookmark.category.name if bookmark.category else None,
        "tags": sorted((tag.name for tag in bookmark.tags), key=str.lower),
        "created_at": bookmark.created_at,
    }


def export_json(bookmarks: list[Bookmark], categories: list[str]) -> str:
    payload = {
        "version": 1,
        "exported_at": datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
        "categories": sorted(categories),
        "bookmarks": [_bookmark_payload(bookmark) for bookmark in bookmarks],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def export_html(bookmarks: list[Bookmark]) -> str:
    groups: "OrderedDict[str | None, list[Bookmark]]" = OrderedDict()
    for bookmark in bookmarks:
        key = bookmark.category.name if bookmark.category else None
        groups.setdefault(key, []).append(bookmark)

    lines = [
        "<!DOCTYPE NETSCAPE-Bookmark-file-1>",
        "<!-- This is an automatically generated file. -->",
        '<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">',
        "<TITLE>Bookmarks</TITLE>",
        "<H1>Bookmarks</H1>",
        "<DL><p>",
    ]

    def write_links(items: list[Bookmark], indent: str) -> None:
        for bookmark in items:
            tags = ",".join(tag.name for tag in bookmark.tags)
            tag_attr = f' TAGS="{html.escape(tags, quote=True)}"' if tags else ""
            lines.append(
                f'{indent}<DT><A HREF="{html.escape(bookmark.url, quote=True)}"'
                f"{tag_attr}>{html.escape(bookmark.title)}</A>"
            )

    for category_name, items in groups.items():
        if category_name is None:
            write_links(items, "    ")
            continue
        lines.append(f"    <DT><H3>{html.escape(category_name)}</H3>")
        lines.append("    <DL><p>")
        write_links(items, "        ")
        lines.append("    </DL><p>")

    lines.append("</DL><p>")
    return "\n".join(lines) + "\n"
