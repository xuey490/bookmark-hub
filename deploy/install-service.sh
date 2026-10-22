#!/usr/bin/env bash
#
# Bookmark Hub systemd 服务安装脚本
#
# 用法：
#   sudo ./deploy/install-service.sh                # 自动识别项目根目录，运行用户 bookmark
#   sudo ./deploy/install-service.sh /opt/bookmark-hub bookmark
#
# 注意：本脚本需在 Linux 上执行。若从 Windows 拷贝过来出现
#       "bad interpreter: /usr/bin/env bash^M"，先执行：
#       sed -i 's/\r$//' deploy/install-service.sh
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(cd "${1:-$(dirname "$SCRIPT_DIR")}" && pwd)"
RUN_USER="${2:-bookmark}"
SERVICE_NAME="bookmark-hub"
UNIT_PATH="/etc/systemd/system/${SERVICE_NAME}.service"
BACKEND_DIR="${APP_DIR}/backend"
VENV_DIR="${BACKEND_DIR}/.venv"
VENV_PYTHON="${VENV_DIR}/bin/python"
UV_PYTHON_DIR="${APP_DIR}/.uv-python"

red()  { printf '\033[31m%s\033[0m\n' "$*" >&2; }
green(){ printf '\033[32m%s\033[0m\n' "$*"; }
warn() { printf '\033[33m%s\033[0m\n' "$*"; }

if [[ "${EUID}" -ne 0 ]]; then
    red "请用 root 执行：sudo $0 $*"
    exit 1
fi

if [[ ! -f "${BACKEND_DIR}/app/main.py" ]]; then
    red "找不到后端代码：${BACKEND_DIR}/app/main.py"
    echo "请把参数指向项目根目录（包含 backend/ 的那一层）" >&2
    exit 1
fi

# ---------------------------------------------------------------- 1. 运行用户
if ! id "$RUN_USER" >/dev/null 2>&1; then
    useradd --system --home-dir "$APP_DIR" --shell /usr/sbin/nologin "$RUN_USER"
    echo "已创建系统用户：$RUN_USER"
else
    echo "运行用户已存在：$RUN_USER"
fi

# ------------------------------------------------- 2. 以服务用户身份检查可执行
# systemd 报 203/EXEC 基本只有三种原因：
#   a) 文件没有可执行位
#   b) 文件存在，但它的 shebang 解释器（如 /root/.local/share/uv/python/.../python3.13）
#      对服务用户不可读/不可执行 —— root 用 uv 装 Python 时最常踩
#   c) 路径上某一级目录服务用户没有 x（进入）权限
run_as_run_user() {
    if command -v runuser >/dev/null 2>&1; then
        runuser -u "$RUN_USER" -- "$@" 2>/dev/null
    else
        su -s /bin/sh "$RUN_USER" -c "$(printf '%q ' "$@")" 2>/dev/null
    fi
}

can_exec_as_run_user() {
    run_as_run_user test -x "$1"
}

print_perm_chain() {
    local target="$1"
    echo "--- 权限链（namei -l ${target}）---" >&2
    namei -l "$target" >&2 || true
}

ensure_venv() {
    if [[ -x "${VENV_PYTHON}" ]]; then
        return 0
    fi
    warn "未找到 ${VENV_PYTHON}，尝试创建虚拟环境……"
    mkdir -p "${UV_PYTHON_DIR}"
    if command -v uv >/dev/null 2>&1; then
        # 关键：把 uv 托管的 Python 装到项目内，避免落在 /root/.local/share/uv（700）下
        ( cd "$BACKEND_DIR" && \
          UV_PYTHON_INSTALL_DIR="${UV_PYTHON_DIR}" \
          uv sync --frozen )
    else
        local sys_py
        sys_py="$(command -v python3.13 || command -v python3 || true)"
        if [[ -z "$sys_py" ]]; then
            red "系统里既没有 uv 也没有 python3，无法创建虚拟环境"
            exit 1
        fi
        "$sys_py" -m venv "${VENV_DIR}"
        "${VENV_DIR}/bin/python" -m pip install -q -r "${BACKEND_DIR}/requirements.txt"
    fi
}

ensure_venv

if [[ ! -x "${VENV_PYTHON}" ]]; then
    red "虚拟环境创建失败：${VENV_PYTHON} 不存在或不可执行"
    exit 1
fi

# 补上可执行位（从 Windows 拷贝或解压丢权限时很常见）
chmod +x "${VENV_DIR}/bin/"* 2>/dev/null || true

# 解析 venv 里 python 指向的真实解释器（uv 创建时是软链，指向托管 Python）
PY_REAL="$(readlink -f "${VENV_PYTHON}" 2>/dev/null || echo "${VENV_PYTHON}")"
echo "venv 解释器：${VENV_PYTHON}"
echo "  实际指向 ：${PY_REAL}"

if ! can_exec_as_run_user "${PY_REAL}"; then
    red "❌ 服务用户 ${RUN_USER} 无法执行解释器：${PY_REAL}"
    echo
    echo "这是 systemd 报 status=203/EXEC / Permission denied 的最常见原因：" >&2
    echo "  root 执行 uv sync 时，uv 把 Python 装到了 /root/.local/share/uv/ 下，" >&2
    echo "  而 /root 目录权限是 700，${RUN_USER} 用户根本进不去。" >&2
    echo
    print_perm_chain "${PY_REAL}"
    echo
    echo "修复方式（把 uv 托管的 Python 改到项目内，然后重建虚拟环境）：" >&2
    echo "  sudo $SCRIPT_DIR/fix-python-env.sh ${APP_DIR} ${RUN_USER}" >&2
    echo "  —— 该脚本会自动诊断权限链、重建 venv 并重启服务" >&2
    echo
    echo "也可以手动做：" >&2
    echo "  cd ${BACKEND_DIR}" >&2
    echo "  rm -rf .venv" >&2
    echo "  UV_PYTHON_INSTALL_DIR=${UV_PYTHON_DIR} uv sync --frozen" >&2
    echo "  sudo $0 ${APP_DIR} ${RUN_USER}" >&2
    echo
    echo "或者直接用系统自带的 Python 3.13 建 venv（不经过 uv 下载）：" >&2
    echo "  cd ${BACKEND_DIR} && rm -rf .venv" >&2
    echo "  /usr/bin/python3.13 -m venv .venv && .venv/bin/pip install -r requirements.txt" >&2
    exit 1
fi

# uvicorn 模块本身也要能 import，否则启动会变成 ModuleNotFoundError
if ! run_as_run_user "${VENV_PYTHON}" -c "import uvicorn, fastapi" ; then
    red "❌ 服务用户 ${RUN_USER} 无法导入 uvicorn / fastapi"
    echo "请先安装依赖：" >&2
    echo "  cd ${BACKEND_DIR}" >&2
    echo "  UV_PYTHON_INSTALL_DIR=${UV_PYTHON_DIR} uv sync --frozen" >&2
    exit 1
fi

# ---------------------------------------------------------------- 3. 配置文件
if [[ ! -f "${BACKEND_DIR}/.env" && -f "${BACKEND_DIR}/.env.example" ]]; then
    cp "${BACKEND_DIR}/.env.example" "${BACKEND_DIR}/.env"
    echo "已从 .env.example 生成 .env"
    warn "  示例里 BK_ENABLED_DEMO=true 表示只读演示模式，需要正常读写请改成 false"
fi

# ------------------------------------------------------------ 4. 目录与权限
# 服务用户需要：可读代码、可写 data 目录；路径上每一级目录都要有 x 权限
chmod a+x "$APP_DIR" "${BACKEND_DIR}" 2>/dev/null || true
chown -R "${RUN_USER}:${RUN_USER}" "${BACKEND_DIR}"
mkdir -p "${BACKEND_DIR}/data/screenshots"
chown -R "${RUN_USER}:${RUN_USER}" "${BACKEND_DIR}/data"
chmod 750 "${BACKEND_DIR}/data"
if [[ -f "${BACKEND_DIR}/data/api_token.txt" ]]; then
    chmod 600 "${BACKEND_DIR}/data/api_token.txt"
fi

# -------------------------------------------------------------- 5. 写入 unit
cat > "$UNIT_PATH" <<EOF
[Unit]
Description=Bookmark Hub (FastAPI + SQLite)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${RUN_USER}
Group=${RUN_USER}
WorkingDirectory=${BACKEND_DIR}
# 不用 EnvironmentFile：应用自己通过 pydantic-settings 读 ${BACKEND_DIR}/.env。
# 若再加 EnvironmentFile，systemd 会以更高优先级的进程环境变量注入，
# 且会处理反斜杠转义（\d -> d+），让 BK_DEMO_WRITE_ALLOWLIST 之类的正则静默失效。
Environment=PYTHONUNBUFFERED=1
# 用 venv 内的解释器执行模块，不依赖 bin/uvicorn 脚本的可执行位，
# 也绕开 shebang 指向的 Python 对服务用户不可达时出现的 203/EXEC。
ExecStart=${VENV_PYTHON} -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
Restart=always
RestartSec=3
TimeoutStopSec=20
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

echo "已写入：${UNIT_PATH}"

# ------------------------------------------------------------ 6. 启用并启动
systemctl daemon-reload
systemctl enable "$SERVICE_NAME" >/dev/null
systemctl restart "$SERVICE_NAME"
sleep 2

if systemctl is-active --quiet "$SERVICE_NAME"; then
    green "✅ ${SERVICE_NAME} 已启动并设为开机自启"
else
    red "❌ 启动失败，最近日志："
    journalctl -u "$SERVICE_NAME" -n 40 --no-pager >&2 || true
    echo >&2
    print_perm_chain "${VENV_PYTHON}"
    echo >&2
    echo "排查建议：" >&2
    echo "  1) 手动以服务用户跑一遍，能直接看到真实报错：" >&2
    echo "     sudo -u ${RUN_USER} ${VENV_PYTHON} -m uvicorn app.main:app --host 127.0.0.1 --port 8000" >&2
    echo "  2) 若是 Permission denied，看上面的权限链，缺 x 的那一级就是元凶" >&2
    echo "  3) 若是 ModuleNotFoundError，重新执行 uv sync --frozen" >&2
    exit 1
fi

echo
systemctl --no-pager --full status "$SERVICE_NAME" | head -n 12 || true
echo
echo "常用命令："
echo "  systemctl restart ${SERVICE_NAME}      # 重启"
echo "  systemctl stop ${SERVICE_NAME}         # 停止"
echo "  systemctl disable ${SERVICE_NAME}      # 取消开机自启"
echo "  journalctl -u ${SERVICE_NAME} -f       # 跟踪日志"
echo "  cat ${BACKEND_DIR}/data/api_token.txt  # 查看登录 Token"
