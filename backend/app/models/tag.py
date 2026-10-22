from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db.base import Base
from .bookmark import bookmark_tags
from .category import utcnow_iso

if TYPE_CHECKING:
    from .bookmark import Bookmark


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    created_at: Mapped[str] = mapped_column(String(32), default=utcnow_iso, nullable=False)

    bookmarks: Mapped[list["Bookmark"]] = relationship(
        secondary=bookmark_tags, back_populates="tags"
    )
