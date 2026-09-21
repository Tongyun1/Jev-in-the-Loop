# Jev-in-the-Loop: Browser

**Jev-in-the-Loop** 的首个模块，当前为 Alpha。Browser 是项目的起点，后续将逐步扩展更多工作场景。
技术标识 `jev-browser-plugin`、Python 包 `jev_browser` 和现有 MCP 工具名保持兼容。

这是 **Codex 插件**，不是独立 App。用户在 Codex 中描述任务，Codex 按技能说明准备参数，
插件的本地 MCP 后端用 Jev + Browser Harness/CDP 在 Chrome 中连续执行操作并核验结果。
无需独立窗口或单独启动 App，也不依赖作者的聊天记录。Python/uv 是插件内部运行时依赖。

实现派生自 [browser-use/jev-ultrafast](https://github.com/browser-use/jev-ultrafast)，保留 MIT
许可证与上游版权声明；不是 Browser Use、TypeSafe 或 OpenAI 的官方插件。

**当前为实验性 Alpha 候选。** 真实网站存在成功与失败记录，不保证任意网站成功，不发布
“固定快几倍”的结论。发布整理只做离线验证，未重新跑真实网站。

## 安装到 Codex

### 前置条件

- 支持插件及本地 MCP 的 Codex；仅 macOS 曾做真实浏览器验证，其他平台未验证。
- [uv](https://docs.astral.sh/uv/getting-started/installation/)：管理插件所需的 Python 3.12+ 和依赖；正常联网且允许自动下载时，无需另行手动安装 Python。
- 本机 Chrome 与用户手动允许的 Remote debugging。仅限本机，不公开调试端口。
- 自己的 TypeSafe API Key，调用可能产生费用。无需额外 OpenAI/browser-use 模型 API Key。

### 首次配置

在仓库外创建 `~/.config/jev-browser/config.env`，按 `.env.example` 填入自己的
`TYPESAFE_API_KEY`，可选 `TYPESAFE_MODEL`（默认 `jev-1.13.0`）。将权限限制为仅当前用户。
不要把真实密钥写进本仓库、README、聊天或 GitHub issue。

配置优先级：进程环境变量 > `JEV_ENV_FILE` 指定的绝对路径文件 > 上述固定用户配置文件。
不会搜索当前工作目录的 `.env`，不会读取其他项目的配置。修改配置后重启插件 MCP 服务。

### 插件安装入口

当前目录 `plugins/jev-browser-plugin/` 就是插件包（不是总仓库根目录）：
`.codex-plugin/plugin.json` 是清单，`.mcp.json` 启动本地服务，
`skills/jev-browser/` 指导 Codex 调用。运行时源码、锁文件均包含在包内，无需引用作者的目录。

源码仓库：[Tongyun1/Jev-in-the-Loop](https://github.com/Tongyun1/Jev-in-the-Loop)。
克隆后进入 `plugins/jev-browser-plugin/` 按下方步骤安装；目前尚未提供公共 marketplace 安装入口。
把源码上传 GitHub 不等于已经注册了 Codex marketplace。公开发布时还需要指定实际仓库与
marketplace 安装入口；不要将不存在的地址作为安装命令。

本地开发安装可在 Codex 中要求“使用 plugin-creator，将此目录安装为个人 Codex 插件”。
提供的辅助命令如下（依赖该 Codex 安装提供的 plugin-creator helpers，只是开发工具）：

下列命令均在 `plugins/jev-browser-plugin/` 内运行。

```sh
uv sync --locked --all-groups --no-editable
uv run python scripts/install_local.py
```

该脚本通过 Codex 的个人 marketplace helper 注册并安装，不直接改写 Codex 配置。
若 helper 不可用，脚本会明确退出，不会悄悄把插件当独立 App 运行。
运行后在 Codex 新任务中加载插件。插件由 Codex 自动启动，普通使用无需运行 Python 命令。
首次启动可能需要下载依赖；受限/离线环境应在插件安装目录预先 `uv sync --locked --no-dev`。

安装后的插件运行**不依赖这些开发 helper**，只需要包内文件、uv、配置和 Chrome 连接。
`JEV_RUNTIME_ROOT` 只作为开发者可选覆盖；默认从启动脚本位置定位插件包。

## 使用与默认设置

示例请求：“用 Jev 在 Wikipedia 搜索哥德尔不完备性定理，打开条目后核验标题。”
需要把结果留在 Chrome 时加上“保留结果标签页”；需要订单准备时说清楚“资料页停止，不提交”。

|设置|默认值与含义|
|---|---|
|浏览器|可见 Chrome；不使用 Safari|
|视口|实际窗口尺寸，不强制缩成 1120×780|
|`keep_open`|`false`：退出时关闭本次创建的标签页，避免累积|
|保留/继续|显式 `keep_open: true`；暂停后 `jev_resume` 复用同一会话|
|固定尺寸|仅显式 `viewport: {"width": 1120, "height": 780}` 时使用|
|操作预算|默认40次，最多60次；150秒为软时间预算|
|模型|`jev-1.13.0`，通过环境/配置文件可改|

每个新任务创建专用页，不复用用户已有页；同一任务暂停后使用 resume，不要循环创建新任务。
仅管理本次拥有的页。不清理之前遗留的页，不自动覆盖保留的结果。运行时请勿在专用页填写内容。
网站同时弹出多个子页会停止，特殊新页不保证能追踪；不承诺绝无遗留标签。

## 工具和任务证据

- `jev_run`：一次调用完成有预算的多步任务。
- `jev_resume`：补充安全文本后继续暂停会话，不改变原域名和停止条件。
- `jev_release`：释放暂停会话内存，不关闭标签；不是取消正在执行的操作。
- `jev_health`：只检查配置/依赖，不连接 Chrome；`browser_connected: null` 表示未检查。

调用者提供 `url`、`goal`、安全的 `text_values`，可配置 `allowed_domains`、`stop_before`、
`stages`、`success_when` 和 `stop_when`。具体参数与通用例子见
[技能说明](skills/jev-browser/SKILL.md)。默认仅允许起始 hostname 及其子域名。

完成条件必须包含 URL、控件状态或精确文本证据；仅有文本子串或点击历史会被拒绝。
`match: "line"` 可匹配完整的页面文本行，例如 `Guest details`，避免将 `Guest Reviews`
误认为住客信息页。仍需根据实际页面选择有区分度的条件，不能仅凭通用词判断完成。
执行器记录“页面状态→动作→结果状态”，重复走过的路径会从当前候选项中排除，
包括弹窗打开/关闭的往返循环；改变人数等有效状态变化不受影响。装饰性文字变化不算进展。
观察层为可识别的加减控件提供分组名称和当前值，不将数字或外层容器误作操作按钮。

`done` 表示调用者定义的本地条件通过，不是模型自己声称完成。没有完成证据则返回
`unverified`；缺文本/不能推进返回 `needs_text`/`blocked`；命中边界返回 `safety_stop`。
错误可能代表动作状态不确定，不自动重试。`keep_open: false` 不支持暂停后继续。
显式保留的暂停会话仅存在当前服务进程，闲置30分钟过期、最多16个，重启即失效。

## 隐私与限制

目标、提供的文本、网页可见文本与控件状态会发送到 TypeSafe。只用于公开、非敏感页面。
登录/支付/敏感字段拦截是启发式规则，不是完整 DLP 或安全保证，详见 [SECURITY.md](SECURITY.md)。
建议单独的 Chrome 配置文件。插件不会自动打开远程调试、批准权限或填写密钥。

已知限制包括重复填写导致停滞、CDP/IPC超时、动态网页加载和标签页变化；跨域 iframe、
封闭 Shadow DOM、画布、拖拽和文件上传不保证支持。历史 B站和携程多轮测试均出现过失败。

## 开发与源码发布

```sh
uv sync --locked --all-groups --no-editable
uv run ruff check .
JEV_TEST_CHROME=0 uv run pytest -q
uv build
uv run python scripts/package_release.py
```

默认测试不启动 Chrome、不调用付费模型。真实 Chrome 测试必须显式设 `JEV_TEST_CHROME=1`；
不要在未获授权时运行。`scripts/probe.py --request` 和 `record_run.py` 也是真实/付费运行。

发布脚本用允许清单导出源码 ZIP 和 SHA-256 清单，不包含 `.venv`、真实 `.env`、截图、日志、
缓存、旧构建包或本机安装配置。不要直接压缩整个工作目录。检查步骤见
[发布检查表](docs/RELEASING.md)。源码仓库与独立的 GitHub Release 安装包分别管理。

项目使用 MIT；上游来源及许可完整保留在 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
