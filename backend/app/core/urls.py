from __future__ import annotations

from urllib.parse import urlsplit, urlunsplit

MAX_URL_LENGTH = 2048


def normalize_url(raw: str) -> str:
    value = (raw or "").strip()
    if not value:
        raise ValueError("url is required")
    if len(value) > MAX_URL_LENGTH:
        raise ValueError("url is too long")

    parsed = urlsplit(value)
    if not parsed.scheme:
        value = "https://" + value
        parsed = urlsplit(value)

    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError("only http/https urls are supported")
    if not parsed.hostname:
        raise ValueError("url host is required")

    return urlunsplit(
        (parsed.scheme, parsed.netloc, parsed.path, parsed.query, parsed.fragment)
    )


def fallback_title(url: str) -> str:
    try:
        parsed = urlsplit(url)
        return parsed.hostname or url
    except ValueError:
        return url
