<img src="docs/media/hero-browser.png" alt="Jev-in-the-Loop: Browser — The first module. More to come." width="100%" />

# Jev-in-the-Loop: Browser

### Codex 负责思考，Jev 负责操作。

搜索酒店、挑选房型、打开预订页。那些原本需要你来回点击的步骤，现在可以从 Codex 里的一句话开始。

**Jev-in-the-Loop: Browser** 把 Jev 的快速网页操作带进你已经在用的 Codex。Codex 理解任务、准备输入，Jev 选择网页操作，插件在本地 Chrome 中执行。

**已有 Codex，再接上 Jev 就够了。** 不用另外配置文本生成模型，也不用再申请一份 OpenRouter 或其他文本模型 API Key。

[开始使用](#开始使用) · [安装指南](https://github.com/Tongyun1/Jev-in-the-Loop/blob/main/plugins/jev-browser-plugin/README.md#安装到-codex) · [参与开发](https://github.com/Tongyun1/Jev-in-the-Loop/blob/main/CONTRIBUTING.md)

## 从一句话，到你要的页面

> 帮我找云南昆明的酒店，10 月 13 日入住，14 日退房，2 位成人。
> 选好房型，打开预订填写页，留给我确认。

更换目的地、搜索酒店、查看详情、选择房型——这是我们已经在携程跑通的流程。最后停在预订填写页，把下一步交回给你。

不必把需求拆成“点击这里，再点击那里”。说清楚想做什么，让操作接着发生。

## 少一点点击，多一点完成

**不再多接一套模型。**

搜索词、目的地、日期由 Codex 准备，Jev 根据页面选择操作与输入。你继续使用现有的 Codex，只需为插件配置 TypeSafe API Key。

**在熟悉的 Codex 里用。**

装成插件，直接交代任务。不用另开一个工作台，也不用切换到另一套助手。

**把连续操作连起来。**

搜索、选择、滚动、导航，在一次插件调用中推进。Jev 根据当前网页选择下一步，让重复的网页操作交给执行循环。

**做到你指定的位置。**

打开视频结果页，进入酒店预订页，或保留页面继续查看。你决定目标，也决定在哪里接手。

## 给它一个任务

找学习资料：

```text
用 Jev 在 B 站搜索高等数学教学视频，保留搜索结果页。
```

准备一次出行：

```text
用 Jev 在携程找昆明酒店，10 月 13–14 日，1 间房、2 位成人。
打开一家酒店，选好房型，停在预订填写页，不提交订单。
```

从一件你经常需要手动完成的网页任务开始。

## 开始使用

准备好 **Codex、Chrome** 和你的 **TypeSafe API Key**。本地运行环境由 **uv** 管理，包括插件所需的 Python 和依赖。

```sh
git clone https://github.com/Tongyun1/Jev-in-the-Loop.git
cd Jev-in-the-Loop/plugins/jev-browser-plugin
```

按照 [安装指南](https://github.com/Tongyun1/Jev-in-the-Loop/blob/main/plugins/jev-browser-plugin/README.md#安装到-codex) 完成密钥配置、Chrome 连接和插件安装，然后在 Codex 新任务中说：**“用 Jev……”**

## Browser，只是开始

网页里藏着太多重复劳动。Browser 是 **Jev-in-the-Loop** 的第一站：让 Jev 从理解一个页面，走向完成一段真实工作。

接下来，我们想把这件事带到更多值得自动化的场景。

有想让它接手的任务？[告诉我们](https://github.com/Tongyun1/Jev-in-the-Loop/issues)。喜欢这个方向？点个 **Star**，一起看下一步。

---

[开发指南](https://github.com/Tongyun1/Jev-in-the-Loop/blob/main/CONTRIBUTING.md) · [安全与隐私](https://github.com/Tongyun1/Jev-in-the-Loop/blob/main/SECURITY.md) · [MIT License](https://github.com/Tongyun1/Jev-in-the-Loop/blob/main/LICENSE)

基于 [browser-use/jev-ultrafast](https://github.com/browser-use/jev-ultrafast) 构建，感谢上游项目。详见 [第三方声明](https://github.com/Tongyun1/Jev-in-the-Loop/blob/main/THIRD_PARTY_NOTICES.md)。
