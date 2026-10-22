from __future__ import annotations

import asyncio
import ipaddress
import logging
import socket
import time
from urllib.parse import urljoin, urlsplit

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import Settings
from ..core.urls import normalize_url
from ..models import Bookmark
from ..models.category import utcnow_iso

logger = logging.getLogger(__name__)

_check_lock = asyncio.Lock()
MAX_REDIRECTS = 5
REDIRECT_CODES = {301, 302, 303, 307, 308}
HEAD_FALLBACK_CODES = {403, 405, 501}
USER_AGENT = "Mozilla/5.0 (compatible; BookmarkHub/1.0)"


async def _ensure_public_target(url: str, allow_private: bool) -> None:
    parsed = urlsplit(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError("unsupported url")

    if allow_private:
        return

    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    loop = asyncio.get_running_loop()
    try:
        infos = await loop.getaddrinfo(
            parsed.hostname, port, type=socket.SOCK_STREAM
        )
    except socket.gaierror as exc:
        raise ValueError(f"dns resolution failed: {exc}") from exc

    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if not ip.is_global:
            raise ValueError(f"target address is not public: {ip}")


async def _probe_once(
    client: httpx.AsyncClient, method: str, url: str
) -> tuple[int, str | None]:
    if method == "GET":
        async with client.stream("GET", url, follow_redirects=False) as response:
            return response.status_code, response.headers.get("location")
    response = await client.request(method, url, follow_redirects=False)
    return response.status_code, response.headers.get("location")


async def _probe(
    client: httpx.AsyncClient,
    url: str,
    method: str,
    settings: Settings,
) -> int:
    current = url
    for _ in range(MAX_REDIRECTS + 1):
        await _ensure_public_target(current, settings.check_allow_private)
        status, location = await _probe_once(client, method, current)
        if status in REDIRECT_CODES and location:
            current = urljoin(current, location)
            continue
        return status
    raise ValueError("too many redirects")


async def check_one(
    client: httpx.AsyncClient, url: str, settings: Settings
) -> dict:
    started = time.perf_counter()
    try:
        status_code = await _probe(client, url, "HEAD", settings)
        if status_code in HEAD_FALLBACK_CODES:
            status_code = await _probe(client, url, "GET", settings)

        response_ms = int((time.perf_counter() - started) * 1000)
        healthy = 200 <= status_code < 400
        return {
            "status": "ok" if healthy else "error",
            "http_status": status_code,
            "response_ms": response_ms,
            "last_error": None if healthy else f"HTTP {status_code}",
        }
    except httpx.TimeoutException:
        return {
            "status": "timeout",
            "http_status": None,
            "response_ms": int((time.perf_counter() - started) * 1000),
            "last_error": "request timeout",
        }
    except Exception as exc:  # noqa: BLE001 - network errors are data, not crashes
        return {
            "status": "error",
            "http_status": None,
            "response_ms": int((time.perf_counter() - started) * 1000),
            "last_error": str(exc)[:500],
        }


async def check_many(urls: list[str], settings: Settings) -> list[dict]:
    if not urls:
        return []

    timeout = httpx.Timeout(settings.check_timeout_seconds)
    concurrency = max(1, settings.check_concurrency)
    limits = httpx.Limits(
        max_connections=max(2, concurrency),
        max_keepalive_connections=concurrency,
    )
    headers = {"User-Agent": USER_AGENT}

    async with httpx.AsyncClient(
        timeout=timeout, limits=limits, headers=headers
    ) as client:
        semaphore = asyncio.Semaphore(concurrency)

        async def run(url: str) -> dict:
            async with semaphore:
                result = await check_one(client, url, settings)
                return {"url": url, **result}

        return list(await asyncio.gather(*(run(url) for url in urls)))


def _apply_result(bookmark: Bookmark, result: dict) -> None:
    bookmark.status = result["status"]
    bookmark.http_status = result["http_status"]
    bookmark.response_ms = result["response_ms"]
    bookmark.last_error = result["last_error"]
    bookmark.last_checked_at = utcnow_iso()


def _summarize(results: list[dict], duration_ms: int) -> dict:
    return {
        "checked": len(results),
        "ok": sum(1 for item in results if item["status"] == "ok"),
        "error": sum(1 for item in results if item["status"] == "error"),
        "timeout": sum(1 for item in results if item["status"] == "timeout"),
        "duration_ms": duration_ms,
        "items": results,
    }


async def check_all(db: AsyncSession, settings: Settings) -> dict:
    async with _check_lock:
        started = time.perf_counter()
        bookmarks = list(
            (await db.execute(select(Bookmark))).scalars().all()
        )
        results = await check_many([item.url for item in bookmarks], settings)
        by_url = {item.url: item for item in bookmarks}
        for result in results:
            bookmark = by_url.get(result["url"])
            if bookmark is not None:
                _apply_result(bookmark, result)
        await db.commit()
        duration_ms = int((time.perf_counter() - started) * 1000)
        logger.info(
            "connectivity check finished: %s bookmarks in %sms",
            len(results),
            duration_ms,
        )
        return _summarize(results, duration_ms)


async def check_urls(
    db: AsyncSession, urls: list[str], settings: Settings
) -> dict:
    async with _check_lock:
        started = time.perf_counter()
        valid_urls: list[str] = []
        invalid_results: list[dict] = []

        for raw in urls:
            try:
                normalized = normalize_url(raw)
                if normalized not in valid_urls:
                    valid_urls.append(normalized)
            except ValueError as exc:
                invalid_results.append(
                    {
                        "url": raw,
                        "status": "error",
                        "http_status": None,
                        "response_ms": 0,
                        "last_error": str(exc),
                    }
                )

        bookmarks = list(
            (
                await db.execute(
                    select(Bookmark).where(Bookmark.url.in_(valid_urls))
                )
            )
            .scalars()
            .all()
        ) if valid_urls else []
        by_url = {item.url: item for item in bookmarks}

        results = await check_many(valid_urls, settings)
        for result in results:
            bookmark = by_url.get(result["url"])
            if bookmark is not None:
                _apply_result(bookmark, result)

        await db.commit()
        all_results = results + invalid_results
        duration_ms = int((time.perf_counter() - started) * 1000)
        return _summarize(all_results, duration_ms)


async def check_bookmark(
    db: AsyncSession, bookmark: Bookmark, settings: Settings
) -> dict:
    async with _check_lock:
        results = await check_many([bookmark.url], settings)
        result = results[0]
        _apply_result(bookmark, result)
        await db.commit()
        return result


async def run_full_check(sessionmaker, settings: Settings) -> None:
    async with sessionmaker() as session:
        await check_all(session, settings)
