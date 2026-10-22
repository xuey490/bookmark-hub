from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
async def client(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    monkeypatch.setenv("BK_DATA_DIR", str(data_dir))
    monkeypatch.setenv(
        "BK_DATABASE_URL",
        f"sqlite+aiosqlite:///{(tmp_path / 'test.db').as_posix()}",
    )
    monkeypatch.setenv("BK_API_TOKEN", "test-token")
    monkeypatch.setenv("BK_CHECK_INTERVAL_HOURS", "0")
    monkeypatch.setenv("BK_CHECK_ALLOW_PRIVATE", "true")
    monkeypatch.setenv("BK_PRINT_TOKEN", "false")
    monkeypatch.setenv("BK_WEB_DIST", str(tmp_path / "no-dist"))
    # 不依赖开发者本地的 backend/.env：显式关闭演示模式，
    # 否则本地 .env 里写了 BK_ENABLED_DEMO=true 会让所有写接口用例变 403。
    monkeypatch.setenv("BK_ENABLED_DEMO", "false")

    from app.core.config import get_settings

    get_settings.cache_clear()

    from app.main import create_app

    app = create_app()
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as http_client:
            http_client.headers["Authorization"] = "Bearer test-token"
            yield http_client

    get_settings.cache_clear()
