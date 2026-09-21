# Jev-in-the-Loop: Browser

[English](README.md) · **简体中文** · [观看演示](https://github.com/Tongyun1/Jev-in-the-Loop/blob/main/README_ZH.md#浏览器演示)

**一个让浏览器操作超高速运行的 Codex 插件。** 说清楚任务，让 Jev 连续操作，在你指定的页面接手。

## 安装到 Codex

以下是 **macOS 源码安装流程**。准备好 **Codex 及其 CLI 和 plugin-creator helpers**、**Chrome**、[**uv**](https://docs.astral.sh/uv/getting-started/installation/) 和 [**TypeSafe API Key**](https://docs.typesafe.ai/introduction)。Python 和依赖交给 uv 管理，文本准备交给你现有的 Codex。

### 1. 下载插件

```sh
git clone https://github.com/Tongyun1/Jev-in-the-Loop.git
cd Jev-in-the-Loop/plugins/jev-browser-plugin
uv sync --locked --all-groups --no-editable
```

已经克隆过仓库？直接进入插件目录即可。

### 2. 填入 Jev 密钥

```sh
mkdir -p ~/.config/jev-browser
cp -n .env.example ~/.config/jev-browser/config.env
chmod 600 ~/.config/jev-browser/config.env
open -e ~/.config/jev-browser/config.env
```

在打开的文件里填好 `TYPESAFE_API_KEY=`，保存。密钥只保留在本地。Jev 调用由 TypeSafe 计费，无需另外配置文本模型 API Key。

### 3. 连接 Chrome，安装插件

打开 Chrome，然后运行：

```sh
uv run browser-harness --doctor
```

按提示完成连接，并在 Chrome 中允许本地远程调试。然后安装：

```sh
uv run python scripts/install_local.py
```

### 4. 开始使用

在 Codex 中**新建任务**，启用插件后说：

```text
用 Jev 在 B 站用英文搜索 Stanford CS336。
打开第一个视频，保留页面。
```

Codex 会自动启动插件。之后，直接交代想完成的任务就好。

## 按你的方式用

- **保留结果：**“把页面留着。”
- **准备预订：**“选好房型，停在预订填写页，不提交订单。”
- **继续暂停的任务：**让 Codex 恢复已有的 Jev 会话。

操作在本地 Chrome 执行；任务与网页可见内容会发送给 TypeSafe，请用于公开、非敏感页面。[隐私说明](SECURITY.md)。

---

[安装排错](docs/USAGE.md#setup-help) · [配置与工具](docs/USAGE.md) · [开发说明](docs/RELEASING.md) · [MIT 与来源声明](THIRD_PARTY_NOTICES.md)
