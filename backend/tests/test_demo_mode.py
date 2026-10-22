from __future__ import annotations

from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient


@asynccontextmanager
async def _demo_app(tmp_path, monkeypatch, extra_env: dict[str, str] | None = None):
    """构造一个启用 BK_ENABLED_DEMO 的独立应用实例。"""
    env = {
        "BK_DATA_DIR": str(tmp_path / "data"),
        "BK_DATABASE_URL": f"sqlite+aiosqlite:///{(tmp_path / 'demo.db').as_posix()}",
        "BK_API_TOKEN": "demo-token",
        "BK_CHECK_INTERVAL_HOURS": "0",
        "BK_ENABLED_DEMO": "true",
        "BK_PRINT_TOKEN": "false",
        "BK_WEB_DIST": str(tmp_path / "no-dist"),
        # 显式给出默认值，避免被开发者本地 backend/.env 干扰
        "BK_DEMO_ALLOW_VISIT": "true",
        "BK_DEMO_WRITE_ALLOWLIST": "",
    }
    env.update(extra_env or {})
    for key, value in env.items():
        monkeypatch.setenv(key, value)

    from app.core.config import get_settings

    get_settings.cache_clear()

    from app.main import create_app

    app = create_app()
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as http_client:
            http_client.headers["Authorization"] = "Bearer demo-token"
            yield SimpleNamespace(app=app, client=http_client)

    get_settings.cache_clear()


@pytest.fixture
async def demo_client(tmp_path, monkeypatch):
    async with _demo_app(tmp_path, monkeypatch) as ctx:
        yield ctx.client


@pytest.fixture
async def demo_ctx(tmp_path, monkeypatch):
    """需要同时拿到 app（用来直接落库）的用例使用。"""
    async with _demo_app(tmp_path, monkeypatch) as ctx:
        yield ctx


async def _insert_bookmark(app, url: str = "https://example.com") -> int:
    """演示模式无法通过 API 建书签，这里直接写库。"""
    from app.models import Bookmark

    sessionmaker = app.state.sessionmaker
    async with sessionmaker() as session:
        bookmark = Bookmark(url=url, title="example")
        session.add(bookmark)
        await session.commit()
        await session.refresh(bookmark)
        return bookmark.id


async def test_demo_mode_allows_reads(demo_client):
    for url in ("/health", "/api/bookmarks", "/api/categories", "/api/stats"):
        response = await demo_client.get(url)
        assert response.status_code == 200, f"GET {url} -> {response.status_code}"
        assert response.json()["code"] == 0


async def test_demo_mode_blocks_writes(demo_client):
    cases = [
        ("POST", "/api/bookmarks", {"url": "https://example.com"}),
        ("PUT", "/api/bookmarks/1", {"url": "https://example.com"}),
        ("PATCH", "/api/bookmarks/1", {"title": "x"}),
        ("DELETE", "/api/bookmarks/1", None),
        ("POST", "/api/bookmarks/batch-delete", {"ids": [1]}),
        ("POST", "/api/bookmarks/1/check", None),
        ("POST", "/api/categories", {"name": "demo"}),
        ("PUT", "/api/categories/1", {"name": "demo"}),
        ("DELETE", "/api/categories/1", None),
        ("POST", "/api/check/urls", {}),
        ("POST", "/api/bookmarks/import", {"bookmarks": []}),
        ("PUT", "/api/token", {"token": "hacked"}),
        ("POST", "/api/token/reset", None),
    ]

    for method, url, payload in cases:
        response = await demo_client.request(method, url, json=payload)
        assert response.status_code == 403, f"{method} {url} -> {response.status_code}"
        body = response.json()
        assert body["code"] == 403
        assert "演示模式" in body["message"]
        # 报错里带上被拦的请求，前端 toast 与 journalctl 都能直接定位
        assert f"{method} {url}" in body["message"]


async def test_demo_mode_allows_visit_tracking(demo_ctx):
    """白名单：记录访问（访问次数 + 上次访问时间）在演示模式下仍然生效。"""
    bookmark_id = await _insert_bookmark(demo_ctx.app)

    first = await demo_ctx.client.post(f"/api/bookmarks/{bookmark_id}/visit")
    assert first.status_code == 200, first.text
    data = first.json()["data"]
    assert data["visit_count"] == 1
    assert data["last_visited_at"]

    second = await demo_ctx.client.post(f"/api/bookmarks/{bookmark_id}/visit")
    assert second.status_code == 200
    assert second.json()["data"]["visit_count"] == 2


async def test_demo_mode_visit_still_requires_token(demo_ctx):
    """放行写接口不等于放行鉴权。"""
    bookmark_id = await _insert_bookmark(demo_ctx.app)
    demo_ctx.client.headers.pop("Authorization")
    response = await demo_ctx.client.post(f"/api/bookmarks/{bookmark_id}/visit")
    assert response.status_code == 401


async def test_demo_mode_still_requires_token(demo_client):
    demo_client.headers.pop("Authorization")
    response = await demo_client.get("/api/bookmarks")
    assert response.status_code == 401


async def test_demo_mode_does_not_touch_data(demo_client):
    """写请求被拦截后，列表数量保持不变。"""
    before = (await demo_client.get("/api/bookmarks")).json()["data"]["total"]
    await demo_client.post("/api/bookmarks", json={"url": "https://blocked.test"})
    after = (await demo_client.get("/api/bookmarks")).json()["data"]["total"]
    assert before == after == 0


async def test_demo_allow_visit_can_be_disabled(tmp_path, monkeypatch):
    """BK_DEMO_ALLOW_VISIT=false 时访问统计也被拦，回到彻底只读。"""
    async with _demo_app(
        tmp_path, monkeypatch, {"BK_DEMO_ALLOW_VISIT": "false"}
    ) as ctx:
        bookmark_id = await _insert_bookmark(ctx.app)
        response = await ctx.client.post(f"/api/bookmarks/{bookmark_id}/visit")
        assert response.status_code == 403


async def test_demo_allow_visit_survives_broken_regex(tmp_path, monkeypatch):
    """回归：systemd EnvironmentFile 会吃掉反斜杠（\\d -> d+），

    访问统计必须靠布尔开关放行，不能被坏掉的正则连累。
    """
    async with _demo_app(
        tmp_path, monkeypatch, {"BK_DEMO_WRITE_ALLOWLIST": "^/api/bookmarks/d+/visit$"}
    ) as ctx:
        bookmark_id = await _insert_bookmark(ctx.app)
        response = await ctx.client.post(f"/api/bookmarks/{bookmark_id}/visit")
        assert response.status_code == 200, response.text


async def test_demo_allowlist_extra_endpoint(tmp_path, monkeypatch):
    """额外白名单可以再放行别的接口（例如连通性检测）。"""
    async with _demo_app(
        tmp_path,
        monkeypatch,
        {"BK_DEMO_WRITE_ALLOWLIST": r"^/api/bookmarks/\d+/check$"},
    ) as ctx:
        bookmark_id = await _insert_bookmark(ctx.app)
        # 白名单命中的接口不再被 403（会去真发请求，结果可能是 ok/error，但不是 403）
        response = await ctx.client.post(f"/api/bookmarks/{bookmark_id}/check")
        assert response.status_code != 403, response.text
        # 未命中的写接口仍然被拦
        blocked = await ctx.client.put("/api/token", json={"token": "x"})
        assert blocked.status_code == 403


async def test_demo_allowlist_ignores_invalid_regex(tmp_path, monkeypatch):
    """非法正则只告警，不影响启动，也不会意外放行。"""
    async with _demo_app(
        tmp_path, monkeypatch, {"BK_DEMO_WRITE_ALLOWLIST": "([bad"}
    ) as ctx:
        response = await ctx.client.put("/api/token", json={"token": "x"})
        assert response.status_code == 403
