from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI

from ..core.config import Settings
from ..services.check_service import run_full_check

logger = logging.getLogger(__name__)


def start_scheduler(
    app: FastAPI, sessionmaker, settings: Settings
) -> AsyncIOScheduler | None:
    if settings.check_interval_hours <= 0:
        logger.info("periodic connectivity check disabled")
        return None

    scheduler = AsyncIOScheduler(timezone="UTC")

    async def job() -> None:
        try:
            await run_full_check(sessionmaker, settings)
        except Exception:  # noqa: BLE001 - keep scheduler alive
            logger.exception("scheduled connectivity check failed")

    scheduler.add_job(
        job,
        trigger="interval",
        hours=settings.check_interval_hours,
        id="connectivity-check",
        max_instances=1,
        coalesce=True,
        replace_existing=True,
    )

    if settings.check_on_startup:
        scheduler.add_job(
            job,
            trigger="date",
            run_date=datetime.now(timezone.utc) + timedelta(seconds=30),
            id="startup-connectivity-check",
        )

    scheduler.start()
    logger.info(
        "connectivity scheduler started, interval=%s hours",
        settings.check_interval_hours,
    )
    return scheduler
