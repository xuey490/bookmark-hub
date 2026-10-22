# Bookmark Hub · 自托管网络书签

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

FastAPI + SQLite + Vue 3 / ant-design-vue 4 + Chrome Extension 实现的个人网络书签系统。网页一键收藏、分类标签、远程访问、定时连通性检测、导入导出、新标签页最近收藏。

完整设计见 [`docs/开发文档.md`](docs/开发文档.md)。

## 已实现功能

- Chrome 插件：网页悬浮收藏按钮（可拖动、可关闭）、收藏弹窗（标题/分类/标签）、配置页、接管新标签页
- 后端：书签/分类/标签 CRUD、分页搜索筛选、标签聚合、统计
- 鉴权：服务端启动自动生成 32 字节 Token，全部 API 走 `Authorization: Bearer <token>`
- 连通性检测：APScheduler 定时巡检 + 单条/全量手动检测，异常/超时标记，SSRF 防护
- Web 管理端：书签列表（支持多选批量删除、访问次数/上次访问记录）、分类管理、标签聚合、统计概览
- Token 设置页：设置自定义 Token 或重置服务端 Token
- H5 临时访问：`/#/h5?token=xxx`，移动端适配
- 导入导出：JSON（含分类标签）、Netscape HTML（可导入 Chrome）
- 测试：pytest 覆盖鉴权、CRUD、标签、批量删除、导入导出、连通性检测

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | Python 3.13、FastAPI、SQLAlchemy 2（async）、aiosqlite、httpx、APScheduler |
| 依赖管理 | uv（`backend/pyproject.toml` + `uv.lock`） |
| 前端 | Vue 3、ant-design-vue 4.2、Vite 8.2、vue-router、axios、dayjs |
| 插件 | Chrome Extension Manifest V3（原生 JS） |
| 数据库 | SQLite（WAL 模式） |

## 目录结构

```text
url/
├─ backend/            # FastAPI 服务、pyproject.toml/uv.lock、测试、数据目录
├─ web/                # Vue 管理端与 H5
├─ extension/          # Chrome 插件（无需构建）
├─ deploy/             # systemd / Nginx / 备份示例
├─ docs/开发文档.md
├─ scripts/make_icons.py
├─ LICENSE             # MIT 许可证
└─ README.md
```

## 快速开始

### 1. 启动后端

两种方式任选其一，依赖内容一致（`requirements.txt` 与 `pyproject.toml` 保持同步）。

#### 方式 A：uv（推荐）

依赖由 `uv` 管理（`backend/pyproject.toml` + `uv.lock`）：

```bash
cd backend
uv sync                     # 首次会创建 .venv 并安装全部依赖（含 pytest 等 dev 组）
cp .env.example .env        # 可选，按需修改
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Windows / Linux / macOS 命令一致，无需手动创建或激活虚拟环境。

Python 版本由 `backend/.python-version`（`3.13`）和 `pyproject.toml` 的 `requires-python = ">=3.13"` 固定；`uv sync` 会自动选用本机 3.13 解释器，缺失时按需下载。

#### 方式 B：传统 venv + pip（不使用 uv）

Linux / macOS：

```bash
cd backend
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env        # 可选，按需修改
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Windows PowerShell：

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1          # 若提示执行策略受限：Set-ExecutionPolicy -Scope Process Bypass
python -m pip install -r requirements.txt
copy .env.example .env                # 可选，按需修改
.\.venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Windows CMD：

```bat
cd backend
python -m venv .venv
.venv\Scripts\activate.bat
python -m pip install -r requirements.txt
copy .env.example .env
.venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

也可以用 `uv venv` 只创建环境、再用 pip 装依赖（`--seed` 会顺带装上 pip，否则 venv 里没有 pip）：

```bash
cd backend
uv venv --python 3.13 --seed
source .venv/bin/activate             # Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

> **启动目标写法**：`app.main:app` 直接使用 `app/main.py` 里已实例化的 `app`，最省事。
> 若要用工厂模式，必须带包名：`app.main:create_app --factory`（写成 `main:create_app` 会报 `Could not import module "main"`）。
> 开发时加 `--reload`，生产不要加。
>
> 以上命令都要在 **`backend/` 目录**下执行。若想在项目根目录启动，用：
>
> ```powershell
> .\backend\.venv\Scripts\python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --app-dir backend
> ```

首次启动会生成 Token：

```bash
cat data/api_token.txt
```

登录 Web 管理端后，可在左侧「Token 设置」中设置自定义 Token，或重置服务端 Token（旧 Token 会立即失效）。

接口文档：<http://127.0.0.1:8000/docs>  
健康检查：<http://127.0.0.1:8000/health>

### 2. 构建前端

```bash
cd web
npm install
npm run build
```

构建产物在 `web/dist`。后端启动时会自动托管该目录；如果后端已经在运行，构建后重启一次即可。

开发模式（前端热更新）：

```bash
# 终端 1：后端
cd backend && uv run uvicorn app.main:app --reload --port 8000

# 终端 2：前端
cd web && npm run dev
```

访问 <http://127.0.0.1:5173>，输入 Token 即可。

### 3. 安装 Chrome 插件

1. Chrome 打开 `chrome://extensions`；
2. 打开右上角「开发者模式」；
3. 点击「加载已解压的扩展程序」，选择 `extension/` 目录；
4. 点击工具栏 Bookmark Hub 图标，填写服务器地址（如 `http://127.0.0.1:8000`）和 Token；
5. 点「测试连接」→「保存配置」；
6. 打开任意网页，右下角出现蓝色收藏按钮。

> 插件会接管新标签页，展示最近 12 条收藏；不需要时可在 `extension/manifest.json` 中删除 `chrome_url_overrides` 后重新加载。

### 4. H5 临时访问

任意电脑浏览器打开：

```text
http://服务器地址:8000/#/h5?token=你的Token
```

Token 只保存在当前标签页的 `sessionStorage`，地址栏参数会被清除。

## API 速览

```bash
TOKEN=$(cat backend/data/api_token.txt)
BASE=http://127.0.0.1:8000

curl -H "Authorization: Bearer $TOKEN" "$BASE/api/bookmarks?page=1&page_size=10"
curl -H "Authorization: Bearer $TOKEN" "$BASE/api/categories"
curl -H "Authorization: Bearer $TOKEN" "$BASE/api/tags"
curl -H "Authorization: Bearer $TOKEN" "$BASE/api/stats"

# 手动检测全部
curl -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{}' "$BASE/api/check/urls"

# 导出
curl -H "Authorization: Bearer $TOKEN" "$BASE/api/bookmarks/export?format=json" -o bookmarks.json
```

完整接口、请求/响应示例见 `docs/开发文档.md` 第 5 章，或运行后访问 `/docs`。

## 配置项

| 环境变量 | 默认值 | 说明 |
|---|---|---|
| `BK_DATA_DIR` | `backend/data` | 数据目录（DB、Token、截图） |
| `BK_DATABASE_URL` | `sqlite+aiosqlite:///./data/bookmarks.db` | 数据库连接串 |
| `BK_API_TOKEN` | 空 | 留空则启动时生成并写入 `data/api_token.txt` |
| `BK_PRINT_TOKEN` | `true` | 启动时在控制台彩色打印 Token；生产环境建议 `false` |
| `BK_CHECK_INTERVAL_HOURS` | `6` | 自动检测间隔，`0` 关闭 |
| `BK_CHECK_TIMEOUT_SECONDS` | `10` | 单次探测超时 |
| `BK_CHECK_CONCURRENCY` | `8` | 探测并发数 |
| `BK_CHECK_ALLOW_PRIVATE` | `false` | 是否允许探测内网地址（默认禁止，防 SSRF） |
| `BK_CHECK_ON_STARTUP` | `false` | 启动 30 秒后跑一次检测 |
| `BK_ENABLED_DEMO` | `false` | 演示模式，`true` 时仅允许浏览，所有写操作返回 403 |
| `BK_DEMO_ALLOW_VISIT` | `true` | 演示模式下是否仍允许「记录访问」（`POST /api/bookmarks/{id}/visit`）；`false` 则彻底只读 |
| `BK_DEMO_WRITE_ALLOWLIST` | 空 | 演示模式下**额外**放行的写接口（逗号分隔正则），一般留空 |
| `BK_CORS_ORIGINS` | `http://localhost:5173,...` | 开发跨域来源 |
| `BK_WEB_DIST` | `../web/dist` | 前端构建目录 |

> **演示模式**：`BK_ENABLED_DEMO=true` 时所有 POST/PUT/PATCH/DELETE 返回 403，但「记录访问」（`POST /api/bookmarks/{id}/visit`）默认放行 —— 否则点开书签时访问次数和上次访问时间不会更新。这类统计写入不改书签内容，留着体验更完整。
>
> - 想**彻底只读**：`BK_DEMO_ALLOW_VISIT=false`
> - 想**再放行别的接口**（例如连通性检测），用正则追加：
>
> ```ini
> BK_DEMO_WRITE_ALLOWLIST=^/api/bookmarks/\d+/check$
> ```
>
> ⚠️ 这个正则含反斜杠，**不要**让 systemd 的 `EnvironmentFile` 去解析它（systemd 会把 `\d` 变成 `d+`，正则静默失效）。本项目 unit 刻意不加 `EnvironmentFile`，由 pydantic-settings 自己读 `backend/.env`，所以写在这里是安全的。

## 测试

```bash
cd backend
uv run pytest -q
```

传统 venv（已激活）：

```bash
cd backend
python -m pytest -q
# Windows 未激活时：.\.venv\Scripts\python -m pytest -q
```

当前 14 个用例覆盖：Token 鉴权与重置、分类/书签 CRUD、重复 URL、标签替换、分类删除置空、分页与筛选、批量删除、访问统计、导入导出往返、HTML 导入、连通性 ok/timeout/error。

## 部署

服务器上首次部署在 `backend/` 执行 `uv sync --frozen`（严格按 `uv.lock` 安装，保证与本地一致）；若使用传统方式则执行 `python -m pip install -r requirements.txt`。之后可用 `uv run uvicorn ...` 启动，或按 systemd 里的写法 `.venv/bin/python -m uvicorn ...` 启动（两者指向同一个 venv）。

> 用 `root` 装依赖时记得加 `UV_PYTHON_INSTALL_DIR=/opt/bookmark-hub/.uv-python`，否则 uv 会把 Python 下到 `/root/.local/share/uv/`，非 root 服务用户无法执行，systemd 直接 `203/EXEC`。

参考 `deploy/`：

- `bookmark-hub.service`：systemd 服务
- `nginx.conf`：全量反向代理（前端也由后端托管，配置最简单）
- `nginx-static.conf`：静态直出（Nginx 直接读 dist，推荐生产使用）
- `backup.sh`：SQLite `VACUUM INTO` 每日备份

### 前端两种托管方式

| | 方式一：Nginx 静态直出（推荐） | 方式二：后端托管 + 全量反代 |
|---|---|---|
| 前端位置 | 任意目录，由 Nginx `root` 指向 | 任意目录，由 `BK_WEB_DIST` 指向 |
| 静态请求 | Nginx 直接读磁盘，可加缓存与 gzip | 经 Uvicorn 返回 |
| 配置文件 | `deploy/nginx-static.conf` | `deploy/nginx.conf` |
| 适用场景 | 生产、有缓存/CDN 需求 | 单机快速部署、内网 |

#### 方式一：Nginx 直接托管 dist

```bash
cd web && npm run build

sudo mkdir -p /var/www/bookmark-hub/web
sudo cp -r dist/* /var/www/bookmark-hub/web/
sudo chown -R www-data:www-data /var/www/bookmark-hub/web   # 发行版不同可能是 nginx 用户
```

然后复制 `deploy/nginx-static.conf`，改 `server_name`、证书路径、`root`、`/media/screenshots/` 的 `alias`，执行 `sudo nginx -t && sudo systemctl reload nginx`。

这种方式下后端**不需要** dist：把 `BK_WEB_DIST` 指向一个不存在的路径即可，后端会自动跳过静态挂载，只提供 `/api`、`/media`、`/docs`。

#### 方式二：dist 迁到任意目录，由后端托管

```bash
sudo mkdir -p /srv/bookmark-web
sudo cp -r web/dist/* /srv/bookmark-web/
```

在 `backend/.env` 指定绝对路径，重启后端生效：

```ini
BK_WEB_DIST=/srv/bookmark-web
```

再用 `deploy/nginx.conf` 全量反代即可，Nginx 只负责 TLS 和转发。

### 常驻服务（systemd）

`deploy/bookmark-hub.service` 是 unit 模板，`deploy/install-service.sh` 可以一键装好；`deploy/fix-python-env.sh` 用于修复 `203/EXEC` 这类解释器不可执行的问题。

#### 一键安装

```bash
# 先把项目放到 /opt/bookmark-hub（或任意目录），并装好依赖
cd /opt/bookmark-hub/backend

# ⚠️ root 安装时务必指定 UV_PYTHON_INSTALL_DIR：
# 默认 uv 会把 Python 下载到 /root/.local/share/uv/（该目录 700），
# 服务用户 bookmark 进不去，systemd 会报 203/EXEC Permission denied。
UV_PYTHON_INSTALL_DIR=/opt/bookmark-hub/.uv-python uv sync --frozen

sudo bash /opt/bookmark-hub/deploy/install-service.sh                      # 自动识别项目根目录
sudo bash /opt/bookmark-hub/deploy/install-service.sh /opt/bookmark-hub    # 或显式指定
```

脚本会依次完成：创建系统用户 `bookmark` → **预检解释器对服务用户是否可执行** → 修正 `data/` 权限 → 写入 `/etc/systemd/system/bookmark-hub.service` → `enable --now` → 打印状态。

#### 手动安装

```bash
# 1. 创建运行用户（系统用户，无登录 shell）
sudo useradd --system --home-dir /opt/bookmark-hub --shell /usr/sbin/nologin bookmark

# 2. 安装依赖（ExecStart 用 venv 里的 python 执行 -m uvicorn，venv 必须存在）
cd /opt/bookmark-hub/backend
UV_PYTHON_INSTALL_DIR=/opt/bookmark-hub/.uv-python uv sync --frozen
chmod +x .venv/bin/*

# 3. 按实际路径修改 unit 里的 User / Group / WorkingDirectory 三项
sudo vi /opt/bookmark-hub/deploy/bookmark-hub.service

# 4. 安装并启动
sudo cp /opt/bookmark-hub/deploy/bookmark-hub.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now bookmark-hub

# 5. 验证
systemctl status bookmark-hub
journalctl -u bookmark-hub -f
curl http://127.0.0.1:8000/health
```

#### 常用运维命令

```bash
systemctl restart bookmark-hub      # 改完 .env 或代码后重启
systemctl stop bookmark-hub
systemctl disable bookmark-hub      # 取消开机自启
journalctl -u bookmark-hub -n 100 --no-pager
journalctl -u bookmark-hub -f       # 跟踪日志
```

#### 几个容易踩的点

- **不要加 `EnvironmentFile`**：应用已经通过 pydantic-settings 自己读 `backend/.env`。再加 `EnvironmentFile` 会让 systemd 先解析一遍并以「进程环境变量」注入（优先级高于 `.env`），而且 systemd 会处理反斜杠转义 —— 像 `BK_DEMO_WRITE_ALLOWLIST=^/api/bookmarks/\d+/visit$` 会被改成 `d+`，正则静默失效、接口照旧 403，非常难查。
- **`PYTHONUNBUFFERED=1` 不能省**：否则 Python 输出被缓冲，`journalctl -f` 里看不到实时日志。
- **`WorkingDirectory` 必须是 `backend/`**：`app` 包导入和 `.env` 里的 `./data` 相对路径都基于它。
- **ExecStart 不要写 `uv run`**：systemd 的 PATH 里通常没有 uv；用 `.venv/bin/python -m uvicorn` 最稳。
- **`status=203/EXEC` / `Permission denied`**：几乎都是 venv 里的 `python` 指向了服务用户访问不到的路径。`root` 跑 `uv sync` 时 uv 默认把 Python 装到 `/root/.local/share/uv/`（`/root` 是 700），`bookmark` 用户进不去，于是连解释器都 exec 不了。**注意换 `python -m uvicorn` 并不能绕过这一层**，因为连 python 自己都起不来。一条命令修：

  ```bash
  sudo /opt/bookmark-hub/deploy/fix-python-env.sh
  ```

  它会打印权限链、把旧 venv 改名备份、用系统 Python 或项目内托管 Python 重建、放开权限并重启服务。手动做法：

  ```bash
  # ① 把 uv 托管的 Python 装到项目内（推荐）
  cd /opt/bookmark-hub/backend && rm -rf .venv
  UV_PYTHON_INSTALL_DIR=/opt/bookmark-hub/.uv-python uv sync --frozen

  # ② 直接用系统 Python 建 venv，完全绕开 uv 下载
  /usr/bin/python3.13 -m venv .venv && .venv/bin/pip install -r requirements.txt

  # ③ 临时放开（不推荐，会削弱 root 目录隔离）
  chmod 755 /root /root/.local/share /root/.local/share/uv
  ```

  排查命令：`readlink -f .venv/bin/python` 看真实解释器，`namei -l <该路径>` 看哪一级目录缺 `x` 权限。
- **改完 `.env` 必须 `systemctl restart`**，systemd 不会自动重载配置。
- **端口冲突**：默认只监听 `127.0.0.1:8000` 由 Nginx 对外；若被占用，`systemctl status` 会显示 `address already in use`。
- **数据目录权限**：服务用户必须能写 `backend/data`，否则 SQLite 报 `unable to open database file`。
- 从 Windows 拷贝脚本过去若报 `bad interpreter: /usr/bin/env bash^M`，执行 `sed -i 's/\r$//' deploy/install-service.sh` 转成 LF。

### 路径与缓存注意事项

- 前端 `vite base` 是 `/`，**只能部署在域名根路径**（`https://bookmark.example.com/`）。若要挂在子路径（如 `/bookmark/`），需在 `vite.config.ts` 设 `base: '/bookmark/'` 后重新构建，Nginx 的 `location` 同步调整。
- 前端是 hash 路由（`/#/bookmarks`），服务器只需返回 `index.html`，不需要 history fallback；`nginx-static.conf` 保留 `try_files` 只是为将来切换路由模式留余地。
- `index.html` 不要缓存，`/assets/` 可以长缓存（文件名带内容 hash）。
- `/media/` 只能 alias 到 `data/screenshots/`，**不要 alias 到 `data/`**，否则 `api_token.txt`、`bookmarks.db` 会变成可下载文件。
- CentOS / RHEL 等 SELinux 环境需放行静态目录：`chcon -R -t httpd_sys_content_t /var/www/bookmark-hub/web`。

生产环境要点：

1. **必须使用 HTTPS**：HTTPS 页面中的插件若请求 HTTP 后端，会被混合内容策略拦截；
2. Uvicorn 固定 `--workers 1`（SQLite 单写者）；量大再迁 PostgreSQL；
3. 不要以 root 运行服务；Token 文件权限为 `600`；
4. 启动横幅默认彩色打印 Token，方便本地登录；正式环境建议设置 `BK_PRINT_TOKEN=false`，并限制日志访问权限；
5. 检测服务默认禁止访问内网/回环地址，避免 SSRF；
6. 定期备份 `backend/data/bookmarks.db`。

## 已知限制 / 后续计划

- 暂无网页摘要、封面、截图（数据表字段已预留，v1.2 实现）；
- 单用户单 Token，无多租户；
- 前端整体引入 ant-design-vue，首屏包约 1.5MB（gzip ~490KB），后续可按需引入优化；
- 标签筛选暂为单标签精确匹配，后续支持多标签 AND/OR；
- SQLite 单实例部署，检测任务与 API 共用进程。

## License

本项目基于 [MIT License](LICENSE) 开源发布。

```
MIT License

Copyright (c) 2026 xuey490

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

简单说：你可以自由使用、修改、分发、商用本项目，只需保留版权声明与许可声明；软件按「现状」提供，不附带任何担保。

### 第三方许可

本项目依赖的第三方组件遵循各自的许可证，主要是 MIT、Apache-2.0、BSD 与 MPL-2.0，详见 `web/package-lock.json` 与 `backend/uv.lock`。分发时请一并保留这些组件的许可声明。
