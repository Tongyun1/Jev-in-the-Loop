# Jev-in-the-Loop

[![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)](plugins/jev-browser-plugin/pyproject.toml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Status: Alpha](https://img.shields.io/badge/Status-Alpha-orange)](plugins/jev-browser-plugin/pyproject.toml)
[![Codex plugin](https://img.shields.io/badge/Codex-Plugin-111827)](plugins/jev-browser-plugin/README_ZH.md)

[English](README.md) · **简体中文**

<img src="docs/media/hero-project.gif" alt="Jev-in-the-Loop — 让决策更快，让任务更进一步" width="100%" />

### 让需要 LLM 决策的任务，更快一步。

**Jev-in-the-Loop 致力于研究如何用 Jev 加速各类需要 LLM 做决策的任务。** 从选择下一步操作，到推进一段工作流，我们探索把 Jev 引入决策循环，让智能体从理解意图更快地走向完成任务。

**哪些决策可以交给 Jev，让整个任务更快完成？** 每个模块探索一种答案。Browser 是第一个，更多模块将从接下来探索的任务与决策循环中生长出来。

[Browser 模块](#jev-in-the-loop-browser) · [项目方向](#project-direction) · [参与开发](https://github.com/Tongyun1/Jev-in-the-Loop/blob/main/CONTRIBUTING.md)

## Jev-in-the-Loop: Browser

<p align="center">
  <img src="docs/media/hero-browser.png" alt="Jev-in-the-Loop: Browser — Codex 插件，项目的首个模块" width="75%" />
</p>

**一个让浏览器操作超高速运行的 Codex 插件。** Browser 是 Jev-in-the-Loop 的首个模块。安装到 Codex 后，直接交代任务：Codex 理解目标、准备输入，Jev 快速选择下一步操作，插件在本地 Chrome 中执行。从搜索到打开目标页面，让点击、输入与跳转连贯推进。

**Codex 懂你的任务，Jev 加快每一步。** 给你熟悉的助手接上高速浏览器决策循环。沿用现有 Codex，再配置一个 TypeSafe API Key，就完成了模型侧的准备，无需另接文本生成服务。

[观看演示](#浏览器演示) · [开始使用](#开始使用) · [安装指南](plugins/jev-browser-plugin/README_ZH.md#安装到-codex)

### 浏览器演示

#### 一句话，走到酒店预订页

> 帮我找北京的酒店，2026 年 11 月 11 日入住，12 日退房，2 位成人。
> 选好房型，打开预订填写页，留给我确认。

更换目的地、搜索酒店、查看详情、选择房型。让连续的点击一气呵成，最后停在预订填写页，等你接手。

<img src="docs/media/demo-hotel.gif" alt="携程搜索北京酒店并打开预订页，3 倍速播放，计时器显示录屏经过时间" width="100%" />

[观看北京酒店演示（MP4）](https://github.com/user-attachments/assets/50a78ed3-9fbb-4434-a969-86b6bebd6e88) · **3 倍速播放** · 计时器显示录屏经过时间。

#### 从想学什么，到打开课程

> 在 B 站用英文搜索 Stanford CS336，打开第一个视频。

输入关键词、提交搜索、打开课程。从一个学习念头，到眼前的视频页面。

<img src="docs/media/demo-course.gif" alt="B 站搜索 Stanford CS336 并打开第一个视频：原速播放" width="100%" />

[观看原 MP4](https://github.com/user-attachments/assets/0a7e59a4-65af-4f65-9d15-17ac95641864) · **原速播放** · 计时器显示录屏经过时间。

不必把需求拆成“点击这里，再点击那里”。说清楚想做什么，让操作接着发生。

### ⚡ 少一点点击，多一点完成

**理解交给 Codex，快速决策交给 Jev。**

Codex 把需求变成计划，准备好要输入的文字；Jev 在一次 TypeSafe 请求里选出下一步操作、目标和输入内容。让你正在用的助手与快速决策模型各展所长，无需额外的文本模型 API Key。

**给现有工作流，直接加速。**

装成 Codex 插件，在对话里说出目标，看它在本地 Chrome 中推进。浏览器操作自然成为当前任务的一部分，从交代需求到接手页面，都在熟悉的工作流里。

**一次交代，连续推进。**

搜索、选择、输入、跳转，多个阶段在一次插件调用中接连完成。执行循环读取当前页面、检查进度、推进下一步；暂停的会话也能带着已有阶段与标签页进度继续。

**交到你手上，也是任务的一部分。**

直接说你要的结果：打开就能看的课程、等待你审核的表单、可以继续探索的页面。把目标和停点一起交代，让自动操作的终点，恰好成为你下一步的起点。

### 💬 给它一个任务

找学习资料：

```text
用 Jev 在 B 站用英文搜索 Stanford CS336，打开第一个视频。
```

准备一次出行：

```text
用 Jev 在携程找北京酒店，2026 年 11 月 11–12 日，1 间房、2 位成人。
打开一家酒店，选好房型，停在预订填写页，不提交订单。
```

从一件你经常需要手动完成的网页任务开始。

### 开始使用

将 **Browser 插件安装到 Codex**：准备好 **Codex、Chrome** 和你的 **TypeSafe API Key**。本地运行环境由 **uv** 管理，包括插件所需的 Python 和依赖。

```sh
git clone https://github.com/Tongyun1/Jev-in-the-Loop.git
cd Jev-in-the-Loop/plugins/jev-browser-plugin
```

按照 [安装指南](plugins/jev-browser-plugin/README_ZH.md#安装到-codex) 完成密钥配置、Chrome 连接和插件安装，然后在 Codex 新任务中说：**“用 Jev……”**

<a id="project-direction"></a>

## 🔬 把 Jev 带进更多决策循环

浏览器是第一个实践场景，不是项目的边界。我们希望继续探索工具选择、工作流分支等需要 LLM 决策的环节，研究 Jev 在哪里能发挥作用，以及如何与现有智能体协作。

从真实任务出发，用可复现的实验检验速度与完成质量，再把有效的方法做成可用的模块。

有想让它接手的任务？[告诉我们](https://github.com/Tongyun1/Jev-in-the-Loop/issues)。喜欢这个方向？点个 **Star**，一起看下一步。

---

[开发指南](https://github.com/Tongyun1/Jev-in-the-Loop/blob/main/CONTRIBUTING.md) · [安全与隐私](https://github.com/Tongyun1/Jev-in-the-Loop/blob/main/SECURITY.md) · [MIT License](https://github.com/Tongyun1/Jev-in-the-Loop/blob/main/LICENSE)

Browser 模块基于 [browser-use/jev-ultrafast](https://github.com/browser-use/jev-ultrafast) 构建，感谢上游项目。详见 [第三方声明](https://github.com/Tongyun1/Jev-in-the-Loop/blob/main/THIRD_PARTY_NOTICES.md)。
