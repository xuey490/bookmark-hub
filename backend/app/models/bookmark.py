from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Column, ForeignKey, Integer, String, Table, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db.base import Base
from .category import utcnow_iso

if TYPE_CHECKING:
    from .category import Category
    from .tag import Tag


bookmark_tags = Table(
    "bookmark_tags",
    Base.metadata,
    Column(
        "bookmark_id",
        Integer,
        ForeignKey("bookmarks.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "tag_id",
        Integer,
        ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Bookmark(Base):
    __tablename__ = "bookmarks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    url: Mapped[str] = mapped_column(
        String(2048), unique=True, nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    category_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    cover_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    screenshot_path: Mapped[str | None] = mapped_column(String(500), nullable=True)

    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="unknown", index=True
    )
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_checked_at: Mapped[str | None] = mapped_column(
        String(32), nullable=True, index=True
    )
    visit_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    last_visited_at: Mapped[str | None] = mapped_column(
        String(32), nullable=True
    )

    created_at: Mapped[str] = mapped_column(
        String(32), default=utcnow_iso, nullable=False, index=True
    )
    updated_at: Mapped[str] = mapped_column(
        String(32), default=utcnow_iso, onupdate=utcnow_iso, nullable=False
    )

    category: Mapped["Category | None"] = relationship(
        back_populates="bookmarks", lazy="selectin"
    )
    tags: Mapped[list["Tag"]] = relationship(
        secondary=bookmark_tags,
        back_populates="bookmarks",
        lazy="selectin",
        order_by="Tag.name",
    )
