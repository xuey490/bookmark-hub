后端 backend/
- FastAPI + SQLAlchemy 2 async + SQLite（WAL）
- 启动自动生成 Token，写入 data/api_token.txt（权限 600）；空 Token 无法通过鉴权
- 书签/分类/标签完整 CRUD、分页、搜索、筛选、排序
- 标签聚合计数、统计接口
- 连通性检测：单条复检、批量复检、APScheduler 定时巡检
- SSRF 防护：默认禁止内网/回环地址、重定向逐跳校验、超时与并发限制
- JSON + Netscape HTML 导入导出
- 统一 {code, message, data} 响应
- 安全修复：/media 只挂载 screenshots/，不会暴露 Token 文件和数据库

Web web/
- Vue 3 + ant-design-vue 4.2.6 + Vite 8.2.0
- 书签列表、分类管理、标签聚合、统计面板
- Token 输入/失效重设、401 自动清理
- 导入导出弹窗、异常状态标签、手动检测
- H5 页面：/#/h5?token=xxx，支持搜索、编辑、删除
- 新标签页搜索可通过 &q= 直接打开 H5

Chrome 插件 extension/
- Manifest V3，无需构建
- 悬浮收藏按钮（Shadow DOM、可拖动、可关闭）
- 收藏弹窗：标题/分类/标签，Ctrl/⌘ + Enter 保存
- 所有请求经 background.js 代理，规避混合内容/CORS
- 设置页：服务器地址、Token、连接测试、开关
- 接管新标签页，展示最近 12 条收藏
- 已生成 16/48/128 PNG 图标


文档与部署
- README.md：启动、插件安装、API 速览、部署、限制
- docs/开发文档.md：已更新到 v1.0，含实现状态和差异说明（1954 行）
- deploy/：systemd、Nginx HTTPS、SQLite 备份脚本
- scripts/make_icons.py

验证结果

- 后端测试：9 passed
- 前端：npm run build 成功，vue-tsc --noEmit 无报错
- 真实服务冒烟测试：
- /health、/、/docs、/openapi.json 均 200
- 未授权请求返回 401
- 真实检测 https://example.com/ 返回 ok / HTTP 200
- /media/api_token.txt、/media/bookmarks.db 均 404
- 插件 JS、manifest、图标均校验通过

立即运行

cd /mnt/dde_data/home/cyl/Desktop/url/backend
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
cat data/api_token.txt
浏览器打开 http://127.0.0.1:8000，输入 Token。
插件安装：chrome://extensions → 开发者模式 → 加载已解压的扩展程序 → 选择 extension/，服务器填 http://127.0.0.1:8000。
H5 临时访问：
http://127.0.0.1:8000/#/h5?token=你的Token

当前边界
- 网页摘要/封面/截图属于 v1.2，字段已预留，本次未实现
- HTML 导入可导入书签和标签，但不保留浏览器文件夹分类
- 前端全量引入 ant-design-vue，构建产物 gzip 约 491KB，有 chunk 体积警告但不影响功能
- 插件交互和页面视觉效果需在 Chrome 中实际加载确认；当前环境未做浏览器自动化视觉测试