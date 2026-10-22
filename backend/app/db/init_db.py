from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine

from .base import Base


async def init_models(engine: AsyncEngine) -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

        # create_all() does not add columns to an existing SQLite table.
        result = await connection.exec_driver_sql(
            "PRAGMA table_info(bookmarks)"
        )
        columns = {row[1] for row in result.fetchall()}
        if "visit_count" not in columns:
            await connection.exec_driver_sql(
                "ALTER TABLE bookmarks "
                "ADD COLUMN visit_count INTEGER NOT NULL DEFAULT 0"
            )
        if "last_visited_at" not in columns:
            await connection.exec_driver_sql(
                "ALTER TABLE bookmarks "
                "ADD COLUMN last_visited_at VARCHAR(32)"
            )
