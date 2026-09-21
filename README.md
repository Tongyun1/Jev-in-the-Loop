# Jev-in-the-Loop

把 Jev 放进实际工作的执行循环，让自然语言任务连接到可操作、可核验的结果。

**Jev-in-the-Loop: Browser** 是项目的第一个模块：一个面向 Codex 的实验性浏览器插件，
由 Jev 选择网页操作，通过 Browser Harness 与本地 Chrome 执行，并根据调用者提供的条件核验结果。

Browser 是起点。后续模块将围绕更多有实际价值的工作场景逐步扩展；当前仓库仅提供 Browser。

## Jev-in-the-Loop: Browser

- 在公开网页上连续搜索、导航和准备表单。
- 使用域名范围、停止条件与操作预算约束任务。
- 使用可检查的网页条件判断完成；支持保留结果页和暂停后继续。
- 以 Codex 插件形式运行，无需单独的应用窗口。

例如：“搜索一个高等数学教学视频，并保留结果页”；或“比较三家酒店，停在提交订单之前”。
网站内容和交互会变化，Alpha 版本不保证所有网站成功，也没有固定倍数的速度承诺。

开始使用请阅读 [Browser 安装与使用说明](plugins/jev-browser-plugin/README.md)。
需要支持本地 MCP 插件的 Codex、uv / Python 3.12+、本机 Chrome 远程调试，以及自己的 TypeSafe API Key。
源码托管于 [GitHub](https://github.com/Tongyun1/Jev-in-the-Loop)。当前提供源码与本地安装方式，尚未提供公共 marketplace 安装入口。

## 仓库结构

```text
Jev-in-the-Loop/
├── README.md
├── CONTRIBUTING.md
├── SECURITY.md
├── LICENSE
├── THIRD_PARTY_NOTICES.md
├── docs/                    # 项目结构与发布说明
├── scripts/                 # 整仓源码打包
├── .github/workflows/       # 离线 CI
└── plugins/
    └── jev-browser-plugin/  # Jev-in-the-Loop: Browser，自包含插件
        ├── .codex-plugin/
        ├── .mcp.json
        ├── skills/
        ├── src/jev_browser/
        ├── tests/
        ├── scripts/
        ├── pyproject.toml
        └── uv.lock
```

总仓库不是插件包；安装时选择 `plugins/jev-browser-plugin/`。
显示名称为 `Jev-in-the-Loop: Browser`，现有插件 ID `jev-browser-plugin`、Python 模块 `jev_browser`
和 MCP 工具名保持兼容。

## 开发

```sh
cd plugins/jev-browser-plugin
uv sync --locked --all-groups --no-editable
uv run ruff check .
JEV_TEST_CHROME=0 uv run pytest -q
uv build
```

测试默认不连接真实 Chrome、不调用付费模型。贡献与验证见 [CONTRIBUTING.md](CONTRIBUTING.md)，
目录约定见 [项目结构](docs/STRUCTURE.md)，打包见 [发布说明](docs/RELEASING.md)。

## 数据与许可

网页可见文本、任务目标和提供的输入会发送给 TypeSafe；只用于公开、非敏感网页。
具体限制见 [SECURITY.md](SECURITY.md)。

采用 MIT 许可。Browser 的执行实现派生自
[browser-use/jev-ultrafast](https://github.com/browser-use/jev-ultrafast)，保留其版权和许可证。
详见 [第三方声明](THIRD_PARTY_NOTICES.md)。本项目并非 TypeSafe、Browser Use 或 OpenAI 的官方项目。
