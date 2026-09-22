# Jev · Living Melody

**让一句旋律，长成一片氛围。**

弹几个音，写下「雨夜、克制、慢慢变亮」这样的描述，网页会接着演奏。你可以在播放中继续弹琴或修改描述；旋律、和弦与球体的颜色和形状会随下一段音乐变化。

![实时旋律续写演示：球体随音乐改变形状和颜色](docs/demo.gif)

## 你可以怎么玩

- **给旋律一个起点**：点击调内八键，或按 `A S D F G H J K` 输入短动机。
- **用文字改变方向**：描述氛围，也可以写「平静 → 开心」让音乐逐段转变。
- **看见每次选择**：页面展示下一段的音符、乐句候选、和声及决策来源；三维球体随音乐运动。

当前版本是**两小节一段的实时续写原型**。它先依据描述确定演奏范围并生成可播放的候选乐句，再由 [Jev](https://docs.typesafe.ai/primitives) 从候选中选择。Jev 连接不可用时，会明确标注并使用本地音乐规则继续播放。

## 本地运行

需要 Python 3。浏览器首次加载 [Tone.js](https://github.com/Tonejs/Tone.js) 和 [Three.js](https://github.com/mrdoob/three.js) 时需要联网；球体需要 WebGL。

```bash
git clone https://github.com/LuXZ1z/Jev-Living-Melody.git
cd Jev-Living-Melody
python3 server.py
```

打开 <http://127.0.0.1:8787>，弹出几个音，点击「开始续写」。没有可用密钥时，页面会使用本地规则演示；接入 Jev 可这样启动：

```bash
TYPESAFE_API_KEY=你的密钥 python3 server.py
```

密钥仅由本地 Python 服务读取，不会发送给浏览器。按 `Ctrl+C` 停止服务。

## 想了解实现？

前端使用 Tone.js 播放、Three.js 绘制球体；`static/melody.js` 生成调内乐句候选，`static/harmony.js` 安排和声，`server.py` 调用 Jev 并处理本地回退。技术细节见[决策设计](JEV_DECISION_DESIGN.md)、[节奏设计](RHYTHM_DIRECTOR.md)和[旋律采样报告](MELODY_SAMPLING_REPORT.md)。
