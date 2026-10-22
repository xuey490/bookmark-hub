from __future__ import annotations

import io
from pathlib import Path
from types import SimpleNamespace

from app.core.logging import print_startup_banner


def _settings(print_token: bool):
    return SimpleNamespace(
        version="1.0.0",
        print_token=print_token,
        api_token="test-token-value",
        check_interval_hours=6,
        data_dir=Path("/tmp/bookmark-test"),
    )


def test_startup_banner_prints_token():
    buffer = io.StringIO()
    print_startup_banner(_settings(True), periodic_check=True, stream=buffer)
    output = buffer.getvalue()
    assert "test-token-value" in output
    assert "Bookmark Hub" in output
    assert "每 6 小时" in output


def test_startup_banner_can_hide_token():
    buffer = io.StringIO()
    print_startup_banner(_settings(False), periodic_check=False, stream=buffer)
    output = buffer.getvalue()
    assert "test-token-value" not in output
    assert "已隐藏" in output
    assert "已关闭" in output
