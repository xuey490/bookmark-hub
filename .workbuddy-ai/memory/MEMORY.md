# Bookmark Hub 项目长期记忆

## 协作约定

- **前端 UI 改动不需要截图验证**：只要 `npx vue-tsc --noEmit` 与 `npm run build` 跑通即可，用户会自己刷新页面测试。不要为此启动浏览器自动化。
- 依赖统一走 uv：`uv sync` / `uv run`，以 `pyproject.toml` + `uv.lock` 为准；`requirements.txt` 仅作参考保留，但改动依赖时需同步一行，保持两者一致。
- Python 固定 3.13：`.python-version` 写 `3.13`，本地 `.venv` 用系统解释器创建（`uv sync --python <系统 python 路径>`），避免依赖 WorkBuddy 私有 binaries。
- 文档 `docs/开发文档.md` 是改动的首要依据，行为变更后同步更新对应章节。

## 已知技术事实

- 入口：`app/main.py` 末尾已 `app = create_app()`，启动用 `app.main:app`；工厂模式必须写 `app.main:create_app --factory`（`main:create_app` 会报 `Could not import module "main"`）。
- 后端命令须在 `backend/` 目录执行；在项目根目录需加 `--app-dir backend`。
- 顶栏 `.app-header` 实际渲染为深色（antd `Layout.Header` 默认 `#001529` 会覆盖 `styles.css` 里的 `background`），文字/图标必须用浅色，否则不可见。
- 前端 hash 路由；Token 桌面端存 `localStorage`，H5 存 `sessionStorage`，key 均为 `bookmark_hub_token`。
- 侧边栏用 `position: sticky` + `height: 100vh` + `align-self: flex-start` 固定，折叠按钮放在顶栏（`:trigger="null"` 关闭自带 trigger）。
- 分页：后端 API 默认 `page_size=20`，Web 端与 H5 前端默认传 10。
