from __future__ import annotations

import secrets
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = "Bookmark Hub"
    version: str = "1.0.0"
    data_dir: Path = BASE_DIR / "data"
    database_url: str = ""
    api_token: str = ""
    print_token: bool = True
    check_interval_hours: float = 6
    check_timeout_seconds: float = 10
    check_concurrency: int = 8
    check_allow_private: bool = False
    check_on_startup: bool = False
    # 演示模式：为 True 时系统只读，所有写操作（POST/PUT/PATCH/DELETE）返回 403
    enabled_demo: bool = False
    # 演示模式下是否仍允许「记录访问」（POST /api/bookmarks/{id}/visit）。
    # 前端点开书签时会调它，累加访问次数并更新上次访问时间；这类统计写入不改书签内容。
    # 用布尔开关而不是正则，是为了不受 .env / systemd 对反斜杠的转义影响。
    # 想彻底只读就设为 false。
    demo_allow_visit: bool = True
    # 额外放行的写接口，逗号分隔的正则（按路径匹配），一般留空。
    # 需要时例如：BK_DEMO_WRITE_ALLOWLIST=^/api/bookmarks/\d+/check$
    # 注意：这个值含反斜杠，若 unit 里用了 EnvironmentFile，systemd 会吃掉 \ 变成 d+，
    # 导致正则失效 —— 所以默认不依赖它，常用开关是上面的 demo_allow_visit。
    demo_write_allowlist: str = ""
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    log_level: str = "INFO"
    web_dist: Path = BASE_DIR.parent / "web" / "dist"

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_prefix="BK_",
        extra="ignore",
    )

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / "screenshots").mkdir(parents=True, exist_ok=True)

    def resolved_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        return f"sqlite+aiosqlite:///{(self.data_dir / 'bookmarks.db').as_posix()}"


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_dirs()
    settings.api_token = settings.api_token.strip()

    if not settings.api_token:
        token_file = settings.data_dir / "api_token.txt"
        token = ""
        if token_file.exists():
            token = token_file.read_text(encoding="utf-8").strip()

        if not token:
            token = secrets.token_urlsafe(32)
            token_file.write_text(token, encoding="utf-8")
            token_file.chmod(0o600)

        settings.api_token = token

    return settings
