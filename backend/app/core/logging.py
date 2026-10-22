from __future__ import annotations

import logging
import os
import sys
from typing import TextIO

from rich import box
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .config import Settings

# uvicorn 在加载 app 前会用自己的彩色 formatter 配置这些 logger，
# 这里统一换成 RichHandler，避免原始 ANSI 码在不支持 VT 的终端里显示成 "[32m"。
_UVICORN_LOGGERS = ("uvicorn", "uvicorn.error", "uvicorn.access")

_ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004

_vt_supported: bool | None = None


def _enable_windows_vt() -> bool:
    """在 Windows 控制台开启 ANSI 转义解析。

    cmd.exe / 传统 conhost 默认不解析 ANSI，会把 ``\\033[32m`` 显示成 ``[32m``。
    该函数对 stdout / stderr 打开 ENABLE_VIRTUAL_TERMINAL_PROCESSING；
    Windows Terminal、Git Bash、Linux/macOS 本身已支持，调用无副作用。
    """
    if os.name != "nt":
        return True
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        enabled = False
        for std_handle in (-11, -12):  # STD_OUTPUT_HANDLE / STD_ERROR_HANDLE
            handle = kernel32.GetStdHandle(std_handle)
            if handle in (0, -1):
                continue
            mode = ctypes.c_uint32()
            if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
                continue
            if mode.value & _ENABLE_VIRTUAL_TERMINAL_PROCESSING:
                enabled = True
                continue
            if kernel32.SetConsoleMode(
                handle, mode.value | _ENABLE_VIRTUAL_TERMINAL_PROCESSING
            ):
                enabled = True
        return enabled
    except Exception:  # noqa: BLE001 - 拿不到控制台就退回无色输出
        return False


def _vt_ok() -> bool:
    """缓存 VT 探测结果，避免每次创建 Console 都调用一次 win32 API。"""
    global _vt_supported
    if _vt_supported is None:
        _vt_supported = _enable_windows_vt()
    return _vt_supported


def _force_color() -> bool:
    return os.environ.get("FORCE_COLOR", "").lower() in ("1", "true", "yes")


def _no_color() -> bool:
    return os.environ.get("NO_COLOR") is not None


def _make_console(stream: TextIO | None = None, *, stderr: bool = False) -> Console:
    target = stream if stream is not None else (sys.stderr if stderr else sys.stdout)
    forced = _force_color()
    # rich 在 Windows 上默认 legacy_windows=True，会绕开 ANSI 直接调用 win32
    # 控制台 API：一旦输出被重定向或终端未按预期处理，颜色就会丢失。
    # 既然已主动打开 VT，这里显式关闭 legacy 模式；VT 开启失败则交回 rich 自行降级。
    legacy_windows = None
    if os.name == "nt":
        # 显式要求彩色时直接走 ANSI；否则以 VT 是否真正开启为准。
        legacy_windows = False if forced or _vt_ok() else None

    return Console(
        file=target,
        force_terminal=True if forced else None,
        # rich 遇到 TERM=dumb 会强制无色，即使 force_terminal=True；
        # 显式指定色彩系统，保证 FORCE_COLOR=1 时一定带颜色。
        color_system="standard" if forced else "auto",
        no_color=True if _no_color() else None,
        legacy_windows=legacy_windows,
        highlight=False,
        markup=False,
        emoji=False,
    )


def setup_logging(level: str = "INFO") -> None:
    """配置全局日志：Rich 彩色输出，并接管 uvicorn / apscheduler 的日志。

    颜色仅在终端下启用；输出重定向到文件或 systemd journal 时自动退化为纯文本，
    不会留下 ANSI 转义码。``NO_COLOR`` / ``FORCE_COLOR`` 环境变量可强制开关。
    """
    _enable_windows_vt()

    console = _make_console(stderr=True)
    handler = RichHandler(
        console=console,
        show_path=False,
        show_level=True,
        show_time=True,
        log_time_format="%H:%M:%S",
        markup=False,
        rich_tracebacks=True,
    )
    handler.setFormatter(logging.Formatter("%(name)s: %(message)s"))

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        handlers=[handler],
        force=True,
    )

    # uvicorn 的 LOGGING_CONFIG 在导入 app 之前就已生效，必须显式替换其 handler，
    # 否则 "Started server process" 等日志仍会带原始 ANSI 码。
    for name in _UVICORN_LOGGERS:
        logger = logging.getLogger(name)
        logger.handlers = [handler]
        logger.propagate = False


def _token_text(token: str) -> Text:
    return Text(f" {token} ", style="bold black on bright_yellow")


def print_startup_banner(
    settings: Settings,
    periodic_check: bool,
    stream: TextIO | None = None,
) -> None:
    """打印启动信息。

    终端下渲染为彩色面板（标题、状态、Token 高亮）；
    非终端环境（systemd、重定向、测试）输出不带任何转义码的纯文本。
    设置 ``BK_PRINT_TOKEN=false`` 可隐藏 Token 值。
    """
    output = stream if stream is not None else sys.stdout
    _enable_windows_vt()
    console = _make_console(output)

    interval = (
        f"每 {settings.check_interval_hours:g} 小时"
        if periodic_check
        else "已关闭"
    )
    token_file = settings.data_dir / "api_token.txt"

    if not console.is_terminal:
        lines = [
            f"Bookmark Hub v{settings.version}",
            "✓ 数据库已连接",
            f"✓ 连通性检测：{interval}",
            "➜ Web 管理端：/",
            "➜ 接口文档：/docs",
        ]
        if settings.print_token:
            lines.append(f"登录 Token：{settings.api_token}")
            lines.append(
                "提示：Token 等同于密码，请勿泄露；"
                "生产环境可设置 BK_PRINT_TOKEN=false 关闭本行输出。"
            )
        else:
            lines.append("登录 Token：已隐藏（BK_PRINT_TOKEN=false）")
            lines.append(f"➜ Token 文件：{token_file}")
        print("\n".join(lines), file=output, flush=True)
        return

    table = Table.grid(padding=(0, 2))
    table.add_column(justify="left", no_wrap=True)
    table.add_column(justify="left", overflow="fold")

    ok_style = "bold green"
    link_style = "bold blue"
    label_style = "bold bright_yellow"

    table.add_row(Text("✓", style=ok_style), Text("数据库已连接"))
    table.add_row(Text("✓", style=ok_style), Text(f"连通性检测：{interval}"))
    table.add_row(Text("➜", style=link_style), Text("Web 管理端：/"))
    table.add_row(Text("➜", style=link_style), Text("接口文档：/docs"))

    if settings.print_token:
        table.add_row(
            Text("登录 Token", style=label_style),
            _token_text(settings.api_token),
        )
        table.add_row(
            Text("提示", style=label_style),
            Text(
                "Token 等同于密码，请勿泄露；"
                "生产环境可设置 BK_PRINT_TOKEN=false 关闭本行输出。",
                style="dim",
            ),
        )
    else:
        table.add_row(
            Text("登录 Token", style=label_style),
            Text("已隐藏（BK_PRINT_TOKEN=false）", style="dim"),
        )
        table.add_row(
            Text("➜", style=link_style),
            Text(f"Token 文件：{token_file}"),
        )

    console.print(
        Panel(
            table,
            title=Text.assemble(
                ("Bookmark Hub", "bold cyan"),
                (f" v{settings.version}", "dim"),
            ),
            border_style="cyan",
            box=box.ROUNDED,
            padding=(0, 2),
            expand=False,
        )
    )
