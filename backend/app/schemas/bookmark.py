from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from ..core.urls import normalize_url

MAX_TAGS = 10
MAX_TAG_LENGTH = 20


def clean_tags(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for raw in values:
        if raw is None:
            continue
        for piece in str(raw).split(","):
            tag = piece.strip().lstrip("#").strip()
            if not tag:
                continue
            if len(tag) > MAX_TAG_LENGTH:
                raise ValueError(f"tag is longer than {MAX_TAG_LENGTH} characters")
            key = tag.lower()
            if key in seen:
                continue
            seen.add(key)
            result.append(tag)
    if len(result) > MAX_TAGS:
        raise ValueError(f"at most {MAX_TAGS} tags are allowed")
    return result


class BookmarkCreate(BaseModel):
    url: str = Field(min_length=1, max_length=2048)
    title: str = Field(default="", max_length=500)
    category_id: int | None = None
    tags: list[str] = Field(default_factory=list)

    @field_validator("url")
    @classmethod
    def _normalize_url(cls, value: str) -> str:
        return normalize_url(value)

    @field_validator("tags")
    @classmethod
    def _clean_tags(cls, value: list[str]) -> list[str]:
        return clean_tags(value)


class BookmarkUpdate(BaseModel):
    url: str | None = Field(default=None, max_length=2048)
    title: str | None = Field(default=None, max_length=500)
    category_id: int | None = None
    tags: list[str] | None = None

    @field_validator("url")
    @classmethod
    def _normalize_url(cls, value: str | None) -> str | None:
        return normalize_url(value) if value is not None else None

    @field_validator("tags")
    @classmethod
    def _clean_tags(cls, value: list[str] | None) -> list[str] | None:
        return clean_tags(value) if value is not None else None


class BookmarkBatchDelete(BaseModel):
    ids: list[int] = Field(min_length=1, max_length=500)

    @field_validator("ids")
    @classmethod
    def _clean_ids(cls, values: list[int]) -> list[int]:
        unique = list(dict.fromkeys(values))
        if any(value <= 0 for value in unique):
            raise ValueError("bookmark ids must be positive integers")
        return unique


class ImportItem(BaseModel):
    url: str = Field(min_length=1, max_length=2048)
    title: str = Field(default="", max_length=500)
    category: str | None = Field(default=None, max_length=30)
    tags: list[str] = Field(default_factory=list)

    @field_validator("url")
    @classmethod
    def _normalize_url(cls, value: str) -> str:
        return normalize_url(value)

    @field_validator("tags")
    @classmethod
    def _clean_tags(cls, value: list[str]) -> list[str]:
        return clean_tags(value)


class ImportRequest(BaseModel):
    mode: str = "skip"
    items: list[ImportItem] = Field(default_factory=list)
