# Codex 插件 Alpha 发布检查表

1. 运行离线检查与构建；不要把这些结果写成真实网站回归通过。
2. 运行 `scripts/package_release.py`，检查 ZIP 内的 `SOURCE_MANIFEST.json`。输出若已存在会拒绝覆盖；
   用新的 `--output` 文件名。源码压缩包是 GitHub 上传候选，不是独立 App 安装包。
3. 确认没有密钥、Cookie、用户日志/截图、私有路径、缓存及历史构建。公开演示必须单独脱敏。
4. 保留 LICENSE 和 THIRD_PARTY_NOTICES；依赖自己的发行包也有许可证，应随其发行方式保留。
5. 由维护者指定实际 GitHub 仓库、作者署名及 Codex marketplace 分发方式。当前未配置公共入口；
   不声称上传仓库后即可直接 `codex plugin add owner/repo`（该命令安装 marketplace 中的插件）。
6. 公开说明 Alpha 状态、macOS 验证范围、TypeSafe 费用与数据发送、Chrome remote debugging要求。
7. 新版本安装到 Codex 后在新任务加载。CI只覆盖离线逻辑；全新机器安装和真实浏览器体验需另行验收。

开发安装脚本使用本机 Codex helper，但最终插件包不依赖 helper 或作者源码目录。
允许保留用户明确配置的 `JEV_ENV_FILE` 路径；这些本机设置不应复制到公开源码。

固定视口和自动关闭标签的改动已有离线回归目标，尚未完成真实 Chrome 的新一轮验证。
历史功能测试有成功也有失败，不把旧的成功截图或带异常恢复的耗时作为性能保证。
