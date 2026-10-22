from __future__ import annotations

from pydantic import BaseModel


class CheckRequest(BaseModel):
    urls: list[str] | None = None
