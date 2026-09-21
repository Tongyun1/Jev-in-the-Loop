# Jev-in-the-Loop: Browser

[English](README.md) · **简体中文** · [观看演示](https://github.com/Tongyun1/Jev-in-the-Loop/blob/main/README_ZH.md#浏览器演示)

**一个让浏览器操作超高速运行的 Codex 插件。** 说清楚任务，让 Jev 连续操作，在你指定的页面接手。

## 安装到 Codex

以下流程适用于 **macOS**。准备好**支持插件的 Codex 及其 CLI**、**Chrome**、[**uv**](https://docs.astral.sh/uv/getting-started/installation/) 和 [**TypeSafe API Key**](https://docs.typesafe.ai/introduction)。Python 和依赖交给 uv 管理，文本准备交给你现有的 Codex。

### 1. 下载并启动安装向导

```sh
git clone https://github.com/Tongyun1/Jev-in-the-Loop.git
cd Jev-in-the-Loop/plugins/jev-browser-plugin
uv run --locked --no-dev --no-editable python scripts/setup.py
```

已经克隆过仓库？直接进入插件目录即可。如果拿到的是维护者提供的
`jev-browser-plugin-<版本>-codex.zip`，解压后进入
`Jev-in-the-Loop/plugins/jev-browser-plugin`，运行相同的 `uv run` 命令即可。

### 2. 按提示完成配置

在终端的隐藏输入提示中粘贴 TypeSafe API Key，然后打开 Chrome，按提示完成连接。
向导会自动准备 Python 和运行依赖，以私有权限保存密钥，并将插件安装到 Codex。
已有密钥会直接复用。Jev 调用由 TypeSafe 计费，无需另外配置文本模型 API Key。

### 3. 开始使用

在 Codex 中**新建任务**，启用插件后说：

```text
用 Jev 在 B 站用英文搜索 Stanford CS336。
打开第一个视频，保留页面。
```

Codex 会自动启动插件。之后，直接交代想完成的任务就好。

Codex 会将插件复制到自己的缓存目录。请保留解压或克隆的文件夹以便更新。
如果 CLI 不认识 `codex plugin`，请先更新 Codex。普通用户无需使用开发脚本 `scripts/install_local.py`。

## 按你的方式用

- **保留结果：**“把页面留着。”
- **准备预订：**“选好房型，停在预订填写页，不提交订单。”
- **继续暂停的任务：**让 Codex 恢复已有的 Jev 会话。

操作在本地 Chrome 执行；任务与网页可见内容会发送给 TypeSafe，请用于公开、非敏感页面。[隐私说明](SECURITY.md)。

---

[安装排错](docs/USAGE.md#setup-help) · [配置与工具](docs/USAGE.md) · [开发说明](docs/RELEASING.md) · [MIT 与来源声明](THIRD_PARTY_NOTICES.md)
