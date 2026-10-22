from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db.base import Base

if TYPE_CHECKING:
    from .bookmark import Bookmark


def utcnow_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, index=True)
    created_at: Mapped[str] = mapped_column(String(32), default=utcnow_iso, nullable=False)
    updated_at: Mapped[str] = mapped_column(
        String(32), default=utcnow_iso, onupdate=utcnow_iso, nullable=False
    )

    bookmarks: Mapped[list["Bookmark"]] = relationship(back_populates="category")
