# Bookmark Hub Chrome Extension

Manifest V3 插件，无需构建，直接在 Chrome 加载。

## 安装

### 方式一：加载已解压目录（推荐，Chrome 唯一稳定可用方式）

1. 打开 `chrome://extensions`；
2. 开启右上角「开发者模式」；
3. 「加载已解压的扩展程序」→ 选择本目录；
4. 点击工具栏图标，填写服务器地址（如 `http://127.0.0.1:8000`）和 Token；
5. 「测试连接」→「保存配置」；
6. 打开任意网页，右下角出现收藏按钮。

### 方式二：解压 zip 后加载

把 `release/bookmark-hub-extension-1.0.0.zip` 解压到任意固定目录，然后按方式一选择该目录。

### 方式三：命令行加载（免手动点击）

先完全退出 Chrome，再执行：

```powershell
& "C:\Users\<用户名>\AppData\Local\Google\Chrome\Application\chrome.exe" --load-extension="<解压后的目录绝对路径>"
```

### 关于 .crx 拖拽安装

`release/bookmark-hub-extension-1.0.0.crx` 已生成，但 **Chrome 稳定版自 2018 年起禁止安装商店外的扩展**，把 crx 拖进 `chrome://extensions` 会被拦截并提示「无法从该网站添加应用、扩展程序和用户脚本」。只有在配置了 `ExtensionInstallSources` / `ExtensionInstallAllowlist` 企业策略的环境下才会放行。日常使用请走方式一或方式三。

## 打包

在项目根目录用本机 Chrome 重新打包（版本号改 `manifest.json` 的 `version` 后执行）：

```powershell
& "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe" --pack-extension="<项目根>\extension" --no-message-box
```

会在项目根目录生成 `extension.crx` 与 `extension.pem`。**`.pem` 是私钥，必须妥善保存**：扩展 ID 由它派生，后续升级必须用同一私钥签名，否则会被识别成另一个扩展。

- 扩展 ID：`bekdpbmgmcmepdeididacbmgienhikml`
- zip 打包（解压后加载）：

```powershell
Compress-Archive -Path "extension\*" -DestinationPath "release\bookmark-hub-extension-1.0.0.zip" -Force
```


## 功能

- 网页右下角悬浮按钮（Shadow DOM 隔离样式，可拖动、可关闭）
- 收藏弹窗：自动填充标题/URL，选择分类、输入标签，`Ctrl/⌘ + Enter` 保存
- 设置页：服务器地址、Token、按钮开关、连接测试、打开 H5 收藏夹
- 新标签页：最近 12 条收藏 + 搜索入口（`chrome_url_overrides.newtab`），点击卡片记录访问次数

## 权限说明

| 权限 | 用途 |
|---|---|
| `storage` | 保存服务器地址、Token、按钮位置与开关 |
| `host_permissions` (`http/https`) | 注入收藏按钮；background 代理跨域 API 请求 |

插件不会向任何第三方发送数据，所有请求只发往用户填写的服务器地址。

## 说明

- 所有 API 请求由 `background.js` 发出，避免 HTTPS 页面请求 HTTP 后端时的混合内容拦截；
- 服务端必须是 HTTP 或 HTTPS，推荐生产环境使用 HTTPS；
- 不需要新标签页功能时，删除 `manifest.json` 中的 `chrome_url_overrides` 后重新加载插件。
