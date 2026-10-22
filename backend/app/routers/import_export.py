from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.errors import ApiError, ok
from ..core.security import require_token
from ..db.session import get_db
from ..models import Bookmark, Category
from ..services.export_service import export_html, export_json
from ..services.import_parser import items_from_payload, parse_file
from ..services.import_service import import_items

router = APIRouter(
    prefix="/api/bookmarks",
    tags=["import-export"],
    dependencies=[Depends(require_token)],
)

MAX_IMPORT_BYTES = 10 * 1024 * 1024


@router.get("/export")
async def export_bookmarks(
    format: Literal["json", "html"] = Query(default="json"),
    db: AsyncSession = Depends(get_db),
) -> Response:
    bookmarks = list(
        (
            await db.execute(
                select(Bookmark).order_by(Bookmark.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
    categories = list(
        (await db.execute(select(Category.name).order_by(Category.name)))
        .scalars()
        .all()
    )
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")

    if format == "html":
        content = export_html(bookmarks)
        filename = f"bookmarks-{stamp}.html"
        media_type = "text/html; charset=utf-8"
    else:
        content = export_json(bookmarks, categories)
        filename = f"bookmarks-{stamp}.json"
        media_type = "application/json"

    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        },
    )


@router.post("/import")
async def import_bookmarks(
    request: Request,
    mode: str = Query(default="skip"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if mode not in ("skip", "update"):
        raise ApiError(400, "mode must be skip or update")

    content_type = request.headers.get("content-type", "")
    parse_errors: list[dict] = []

    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        upload = form.get("file")
        if upload is None or not hasattr(upload, "read"):
            raise ApiError(400, "file is required")
        filename = getattr(upload, "filename", "") or ""
        raw = await upload.read()
        if len(raw) > MAX_IMPORT_BYTES:
            raise ApiError(413, "file is too large")
        form_mode = form.get("mode")
        if form_mode:
            mode = str(form_mode)
            if mode not in ("skip", "update"):
                raise ApiError(400, "mode must be skip or update")
        try:
            items, parse_errors = parse_file(raw, filename)
        except Exception as exc:  # noqa: BLE001 - report parse problems as 400
            raise ApiError(400, f"failed to parse file: {exc}") from exc
    elif content_type.startswith("application/json"):
        try:
            payload = await request.json()
        except Exception as exc:  # noqa: BLE001
            raise ApiError(400, "invalid json body") from exc
        if isinstance(payload, dict) and payload.get("mode"):
            mode = str(payload["mode"])
            if mode not in ("skip", "update"):
                raise ApiError(400, "mode must be skip or update")
        try:
            items, parse_errors = items_from_payload(payload)
        except Exception as exc:  # noqa: BLE001
            raise ApiError(400, f"failed to parse payload: {exc}") from exc
    else:
        raise ApiError(415, "unsupported content type")

    stats = await import_items(db, items, mode)
    if parse_errors:
        stats["failed"] += len(parse_errors)
        stats["errors"] = (parse_errors + stats["errors"])[:50]
    return ok(stats)
