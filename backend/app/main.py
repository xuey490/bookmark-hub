from __future__ import annotations

import logging
import re
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .core.config import get_settings
from .core.errors import ApiError, envelope, install_exception_handlers, ok
from .core.logging import print_startup_banner, setup_logging
from .db.base import Base
from .db.init_db import init_models
from .db.session import create_engine_and_session
from .routers import (
    bookmarks,
    categories,
    checks,
    import_export,
    stats,
    tags,
    token_admin,
)
from .tasks.scheduler import start_scheduler

logger = logging.getLogger(__name__)

# 只读方法：演示模式下放行
_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})

# 演示模式下「记录访问」的固定路径（访问次数 + 上次访问时间）。
# 用布尔开关控制而不是让用户写正则，避免 \d 被 systemd/.env 的转义吃掉。
_VISIT_PATH = re.compile(r"^/api/bookmarks/\d+/visit$")


def _compile_allowlist(raw: str) -> tuple[re.Pattern[str], ...]:
    """把逗号分隔的正则字符串编译成列表，非法正则只告警不中断启动。"""
    patterns: list[re.Pattern[str]] = []
    for item in (raw or "").split(","):
        item = item.strip()
        if not item:
            continue
        try:
            patterns.append(re.compile(item))
        except re.error as exc:
            logger.warning("忽略无效的演示模式白名单正则 %r：%s", item, exc)
    return tuple(patterns)


def _is_demo_allowlisted(
    path: str, patterns: tuple[re.Pattern[str], ...], allow_visit: bool
) -> bool:
    if allow_visit and _VISIT_PATH.search(path):
        return True
    return any(pattern.search(path) for pattern in patterns)


def create_app() -> FastAPI:
    settings = get_settings()
    setup_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        settings.ensure_dirs()
        engine, sessionmaker = create_engine_and_session(
            settings.resolved_database_url()
        )
        app.state.engine = engine
        app.state.sessionmaker = sessionmaker
        app.state.settings = settings

        await init_models(engine)
        scheduler = start_scheduler(app, sessionmaker, settings)
        print_startup_banner(settings, periodic_check=scheduler is not None)

        try:
            yield
        finally:
            if scheduler is not None:
                scheduler.shutdown(wait=False)
            await engine.dispose()

    app = FastAPI(
        title=settings.app_name,
        version=settings.version,
        lifespan=lifespan,
    )

    # 演示模式（只读）守卫。
    # 必须注册在 CORSMiddleware 之前，这样它位于 CORS 内层：
    # 被拦截的 403 响应仍会经过 CORS 中间件补上跨域头，前端才能读到错误信息。
    demo_allowlist = _compile_allowlist(settings.demo_write_allowlist)
    if settings.enabled_demo:
        # 启动时打一行，journalctl 里能直接确认配置是否按预期加载
        logger.info(
            "演示模式已开启：记录访问=%s，额外白名单=%s",
            "允许" if settings.demo_allow_visit else "禁止",
            [p.pattern for p in demo_allowlist] or "无",
        )

    @app.middleware("http")
    async def demo_readonly_guard(request: Request, call_next):
        if settings.enabled_demo and request.method not in _SAFE_METHODS:
            # 白名单内的接口（默认是「记录访问」）仍放行，其余写操作一律 403
            if not _is_demo_allowlisted(
                request.url.path, demo_allowlist, settings.demo_allow_visit
            ):
                # 打一条日志：排查时 journalctl 里能直接看到被拦的路径与当前配置
                logger.info(
                    "演示模式拦截 %s %s（记录访问=%s，额外白名单=%s）",
                    request.method,
                    request.url.path,
                    settings.demo_allow_visit,
                    settings.demo_write_allowlist or "空",
                )
                return JSONResponse(
                    status_code=403,
                    content=envelope(
                        403,
                        "演示模式：仅允许浏览，写操作已禁用"
                        f"（{request.method} {request.url.path}）",
                    ),
                )
        return await call_next(request)

    origins = [item.strip() for item in settings.cors_origins.split(",") if item.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins or ["*"],
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=False,
    )

    install_exception_handlers(app)

    @app.middleware("http")
    async def log_requests(request, call_next):
        started = time.perf_counter()
        response = await call_next(request)
        elapsed = (time.perf_counter() - started) * 1000
        logger.info(
            "%s %s -> %s %.1fms",
            request.method,
            request.url.path,
            response.status_code,
            elapsed,
        )
        return response

    # import/export routes must be registered before /{bookmark_id}
    app.include_router(import_export.router)
    app.include_router(categories.router)
    app.include_router(tags.router)
    app.include_router(stats.router)
    app.include_router(checks.router)
    app.include_router(bookmarks.router)
    app.include_router(token_admin.router)

    @app.get("/health")
    async def health() -> dict:
        return ok({"status": "ok", "version": settings.version})

    @app.api_route(
        "/api/{path:path}",
        methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        include_in_schema=False,
    )
    async def api_not_found(path: str) -> dict:
        raise ApiError(404, "not found")

    app.mount(
        "/media/screenshots",
        StaticFiles(directory=str(settings.data_dir / "screenshots")),
        name="media",
    )

    if settings.web_dist.exists():
        app.mount(
            "/",
            StaticFiles(directory=str(settings.web_dist), html=True),
            name="web",
        )
    else:
        @app.get("/", include_in_schema=False)
        async def index() -> dict:
            return {
                "name": settings.app_name,
                "message": "Frontend is not built yet. Run `npm run build` in web/.",
            }

    return app


app = create_app()
