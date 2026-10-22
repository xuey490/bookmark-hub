#!/usr/bin/env bash
#
# 修复 systemd 报 status=203/EXEC（Permission denied）
#
# 症状：
#   Failed to execute /opt/bookmark-hub/backend/.venv/bin/python: Permission denied
#   Main process exited, code=exited, status=203/EXEC
#
# 原因：
#   root 执行 uv sync 时，uv 把 Python 下载到 /root/.local/share/uv/python/...，
#   而 /root 目录权限是 700。服务用户（如 bookmark）无法穿过 /root，
#   于是连 .venv/bin/python 这个软链都 exec 不了 —— 换成
#   `python -m uvicorn` 也救不回来，因为连 python 自己都起不来。
#
# 本脚本会：诊断权限链 → 把旧 venv 改名备份 → 用「系统 Python 或项目内托管 Python」
#          重建 venv → 放开读/执行权限 → 重启服务。
#
# 用法：
#   sudo ./deploy/fix-python-env.sh                    # 自动识别项目根，用户 bookmark
#   sudo ./deploy/fix-python-env.sh /opt/bookmark-hub bookmark
#
# 若从 Windows 拷贝过来报 bad interpreter，先 sed -i 's/\r$//' deploy/fix-python-env.sh
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(cd "${1:-$(dirname "$SCRIPT_DIR")}" && pwd)"
RUN_USER="${2:-bookmark}"
BACKEND_DIR="${APP_DIR}/backend"
VENV_DIR="${BACKEND_DIR}/.venv"
VENV_PYTHON="${VENV_DIR}/bin/python"
UV_PYTHON_DIR="${APP_DIR}/.uv-python"
SERVICE_NAME="bookmark-hub"
UNIT_PATH="/etc/systemd/system/${SERVICE_NAME}.service"

red()   { printf '\033[31m%s\033[0m\n' "$*" >&2; }
green() { printf '\033[32m%s\033[0m\n' "$*"; }
warn()  { printf '\033[33m%s\033[0m\n' "$*"; }

[[ "${EUID}" -eq 0 ]] || { red "请用 root 执行：sudo $0 $*"; exit 1; }
[[ -f "${BACKEND_DIR}/app/main.py" ]] || { red "找不到 ${BACKEND_DIR}/app/main.py"; exit 1; }
id "$RUN_USER" >/dev/null 2>&1 || { red "用户不存在：${RUN_USER}"; exit 1; }

run_as_run_user() {
    if command -v runuser >/dev/null 2>&1; then
        runuser -u "$RUN_USER" -- "$@" 2>/dev/null
    else
        su -s /bin/sh "$RUN_USER" -c "$(printf '%q ' "$@")" 2>/dev/null
    fi
}

real_python() {
    readlink -f "${VENV_PYTHON}" 2>/dev/null || echo "${VENV_PYTHON}"
}

interpreter_ok() {
    [[ -e "${VENV_PYTHON}" ]] || return 1
    run_as_run_user test -x "$(real_python)"
}

diagnose() {
    echo "---- 诊断 ----"
    if [[ -e "${VENV_PYTHON}" || -L "${VENV_PYTHON}" ]]; then
        ls -l "${VENV_PYTHON}" || true
        local real
        real="$(real_python)"
        echo "真实解释器：${real}"
        echo "权限链："
        namei -l "${real}" 2>/dev/null || true
    else
        echo "未找到 ${VENV_PYTHON}"
    fi
    echo "--------------"
}

py_version() {
    "$1" -c 'import sys;print("%d.%d" % sys.version_info[:2])' 2>/dev/null || echo "0.0"
}

# 比较 "3.13" >= "3.13"，避免 [[ "3.9" > "3.13" ]] 这种字符串比较的坑
ver_ge() {
    local a_major="${1%%.*}" a_minor="${1#*.}" b_major="${2%%.*}" b_minor="${2#*.}"
    (( a_major > b_major || (a_major == b_major && a_minor >= b_minor) ))
}

# ---------------------------------------------------------------- 已正常则退出
if interpreter_ok; then
    green "✅ ${RUN_USER} 已能执行 venv 解释器，无需修复"
    echo "   $(real_python)"
    exit 0
fi

warn "服务用户 ${RUN_USER} 无法执行 venv 解释器，开始重建"
diagnose

# ---------------------------------------------------- 旧 venv 改名备份（不直接删）
if [[ -d "${VENV_DIR}" ]]; then
    rm -rf "${VENV_DIR}.broken"
    mv "${VENV_DIR}" "${VENV_DIR}.broken"
    echo "旧 venv 已重命名为 ${VENV_DIR}.broken（确认服务正常后可 rm -rf 删除）"
fi

# ------------------------------------------- 选解释器：优先系统 3.13，其次 uv
SYS_PY=""
for candidate in /usr/bin/python3.13 /usr/local/bin/python3.13 \
                 /usr/bin/python3 /usr/local/bin/python3; do
    if [[ -x "$candidate" ]]; then SYS_PY="$candidate"; break; fi
done

SYS_VER="0.0"
[[ -n "${SYS_PY}" ]] && SYS_VER="$(py_version "${SYS_PY}")"

BUILD_MODE=""
if [[ -n "${SYS_PY}" ]] && ver_ge "${SYS_VER}" "3.13"; then
    BUILD_MODE="system"
elif command -v uv >/dev/null 2>&1; then
    BUILD_MODE="uv"
elif [[ -n "${SYS_PY}" ]]; then
    BUILD_MODE="system"
    warn "系统 Python 是 ${SYS_VER}（项目声明 >=3.13），仍尝试用 requirements.txt 安装"
else
    red "既没有可用的系统 python3，也没有 uv，无法重建虚拟环境"
    exit 1
fi

if [[ "${BUILD_MODE}" == "system" ]]; then
    echo "用系统解释器建 venv：${SYS_PY} (Python ${SYS_VER})"
    "${SYS_PY}" -m venv "${VENV_DIR}"
    "${VENV_PYTHON}" -m pip install -q --upgrade pip
    echo "安装依赖（requirements.txt）……"
    "${VENV_PYTHON}" -m pip install -q -r "${BACKEND_DIR}/requirements.txt"
else
    echo "用 uv 建 venv，托管 Python 装到 ${UV_PYTHON_DIR}（项目内，服务用户可访问）"
    mkdir -p "${UV_PYTHON_DIR}"
    ( cd "${BACKEND_DIR}" && \
      UV_PYTHON_INSTALL_DIR="${UV_PYTHON_DIR}" \
      uv sync --frozen )
fi

# -------------------------------------------------------------- 权限收尾
chmod +x "${VENV_DIR}/bin/"* 2>/dev/null || true
chmod -R a+rX "${VENV_DIR}" 2>/dev/null || true
if [[ -d "${UV_PYTHON_DIR}" ]]; then
    chmod -R a+rX "${UV_PYTHON_DIR}" 2>/dev/null || true
fi
chmod a+x "${APP_DIR}" "${BACKEND_DIR}" 2>/dev/null || true

echo
if ! interpreter_ok; then
    red "❌ 重建后仍然不可执行，请把下面的权限链贴给维护者"
    diagnose
    exit 1
fi

green "✅ 重建完成，${RUN_USER} 现在可以执行解释器：$(real_python)"

if ! run_as_run_user "$(real_python)" -c "import uvicorn, fastapi"; then
    red "❌ 依赖导入失败（uvicorn / fastapi）"
    exit 1
fi
echo "依赖导入 OK"

# -------------------------------------------------------------- 重启服务
if [[ -f "${UNIT_PATH}" ]]; then
    echo "重启 ${SERVICE_NAME} ……"
    systemctl daemon-reload
    systemctl restart "${SERVICE_NAME}"
    sleep 2
    if systemctl is-active --quiet "${SERVICE_NAME}"; then
        green "✅ ${SERVICE_NAME} 已正常运行"
        systemctl --no-pager --full status "${SERVICE_NAME}" | head -n 8 || true
    else
        red "❌ 服务仍启动失败，最近日志："
        journalctl -u "${SERVICE_NAME}" -n 40 --no-pager || true
        exit 1
    fi
else
    warn "未找到 ${UNIT_PATH}，跳过重启；可执行 deploy/install-service.sh 安装服务"
fi
