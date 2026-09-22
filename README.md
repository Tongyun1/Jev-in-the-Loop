# Living Melody（原 music-mvp）· Jev 氛围旋律续写

这是一个浏览器原型：用户用虚拟钢琴输入动机，用文字描述意境。每两个小节 Jev 先判断当前意境的情绪档案、动机发展、音符数量与节奏，再从该情绪允许的旋律及调内和弦候选中作选择；界面用 Three.js 球体表现声音和情绪。没有 API key 时，服务端返回带有明确来源标识的本地音乐规则。

## 运行

```bash
cd living-melody
python3 server.py
```

访问 `http://127.0.0.1:8787`。浏览器首次播放需要点击“开始续写”。

服务端会自动读取相邻的 `../jev-ultrafast/.env`。也可以显式传入环境变量（环境变量优先）：

```bash
cd living-melody
TYPESAFE_API_KEY=你的官方key python3 server.py
```

密钥只在本地 Python 进程内使用，不会发送给浏览器。

## 选型结论

| 项目 | 调研发现 | 是否作为原型基础 |
| --- | --- | --- |
| [Tone.js](https://github.com/Tonejs/Tone.js) | 浏览器音频时钟、合成器和多音调度成熟，MIT | 是，负责精确出声 |
| [Tonal](https://github.com/tonaljs/tonal) | JavaScript 调式、和弦与音程工具 | 后续接入；首版 C 大调用固定标度减少依赖 |
| [OpenArranger](https://github.com/realsigmamusic/openarranger) | 浏览器自动伴奏，节奏分段按整小节、半小节或四分之一小节量化切换，MIT | 作为第二阶段“伴奏自由切换”的结构参考，不直接 fork |
| [Contrapunk](https://github.com/contrapunk-audio/contrapunk) | 实时 MIDI 和声/编配，含浏览器、桌面和 DAW 表面，MIT | 未来 MIDI 键盘阶段参考；Rust/WASM 规模超过首版 |
| [RockDice](https://github.com/surikov/rockdice) | 约 200 个可转调 riff，分 drums/bass/lead/pad 四层，GPL-3.0 | 很适合验证“有限伴奏候选”，但不直接复用 GPL 代码或素材 |
| [ACCompanion](https://github.com/CPJKU/accompanion) | 严谨的实时跟谱伴奏研究系统，需要 MIDI 和特定 MusicXML 乐谱 | 不适合自由即兴的网页 MVP |
| [AccoMontage2](https://github.com/billyblu2000/AccoMontage2) | 离线全曲和声/编配，依赖数据包和 PyTorch | 适合以后离线生成完整伴奏，不适合每小节实时选择 |

结论是手动抽取：保留 OpenArranger 的量化切换与可编辑样式数据理念，采用 Tone.js 的浏览器音频时钟，并在两者之间放入 Jev 的有限候选决策。这样既能实时，也保留每一次选择的概率、回退和可解释性。

每次请求只保留最近四小节、最多 32 个压缩音符事件，以及八小节的短句 ID 历史。明确的当前情绪由本地规则规划节奏，不调用 `/plan`；无法归类的描述才调用一次 `/plan`，并按当前场景缓存规划。`/decision` 仍由 Jev 在完整两小节旋律与和弦候选中选择，同时判断视觉状态。服务端只向模型发送候选音符计划一次，候选说明仅出现在问题选项中，避免重复上下文。`context_chars` 是请求 JSON 字符数，不是模型 token 用量或账单金额。

页面使用 [Three.js](https://github.com/mrdoob/three.js) 的球体、双层 GLSL 材质、粒子和环形光晕。Jev 的视觉选择控制色相、形变、运动和亮度；播放音符触发球体脉冲。当前意境中若明确出现“雨夜”“愤怒”“变亮”等词，页面会优先采用对应色调，防止过早出现后续场景的颜色，并在来源栏标出“意境校色”。方案参考了 MIT 许可的 [summer-orb](https://github.com/lbxa/summer-orb) 与 [audio_reactive_visualizer](https://github.com/gztes/audio_reactive_visualizer) 的架构，球体着色器和页面布局在本项目内重写。视觉情绪与旋律在同一次 `/decision` 请求中决定。明确情绪下每两个小节调用一次 Jev；120 BPM 时约每 4 秒一次，即持续播放约 15 次/分钟。

球体还会读取最近四小节的音符密度：密度升高时，核心体积、表面细节、粒子尺寸与光环会逐步增强；密度降低时会缓慢收回。颜色、运动、亮度和形状目标也在 WebGL 帧循环中以不同速度插值，避免每次 Jev 结果返回时出现刷新或重置感。控制区提供独立的“主旋律”和“和弦铺底”音量；铺底本身有较低预设音量，默认会让旋律保持在前景。

旋律候选不再围绕最后一个音做固定级进：`static/melody.js` 从用户动机抽取音程，生成回声、倒影、逆行、模进、问答、跳进、留白、装饰和句尾等计划，并在生成时约束相邻音的八度位置。Jev 选择后，前端会保存**被评估的原始播放计划**，到小节边界直接演奏它。以前的实现会在播放时重新生成候选，导致模型评估的音符与听到的音符可能不同。

`static/harmony.js` 依据当前情绪档案提供调内和弦根音与 triad、add9 或 diatonic seventh；候选排序参考上一和弦的根音。Jev 同时选和弦和基础转位；客户端参考上一和弦选择移动较小的配音。铺底音色可选择 Pad、暖色合成、Bell、Organ；参数取自 `gesture-synth` 的预设思路，并在本项目用 Tone.js 重写。

创作描述可以写成 `平静→开心`。前四小节的当前意境为“平静”，后四小节为“开心”；完整描述只表示长线走向，不再让开头词锁定后半段的情绪。术语见 `CONTEXT.md`。

旋律、和声与意境规划回归检查：`node --experimental-default-type=module tests/melody.test.mjs`、`node --experimental-default-type=module tests/harmony.test.mjs` 和 `node --experimental-default-type=module tests/direction.test.mjs`。

离线采样工具：`node --experimental-default-type=module tools/sample.mjs "雨夜，克制，慢慢变亮" 40`。这是旧版单小节采样链，与当前两阶段实时播放链不同；仅供比较历史重复率，用于统计重复率、候选利用率与强拍和弦对齐率；采样结论记录在 `MELODY_SAMPLING_REPORT.md`。

2026-09-21 已用 `jev-ultrafast/.env` 中的官方 `apikey_` 密钥完成真实接口验证：请求成功返回 `source=Jev`、候选概率、`motif_keep` 和 `density`；密钥没有写入本项目文件，也没有发送到浏览器。

## 当前边界

- 麦克风入口暂时移除；用户用虚拟钢琴输入动机。
- 全部 24 个大小调可选；Jev 回答 `key_shift`（保持/关系/同主音/下属/属方向），四小节边界执行。键盘只给当前音阶的七个音加高八度主音；例如 C 小调会显示 Eb、Ab、Bb，C 大调不会被自动塞入这些音。所有自动旋律与和弦都在当前调内，转调边界的候选提前按目标调生成。
- 节奏库含均分八分、附点、切分、十六分点缀四族；Jev 为两小节分别选族和 2–8 个起音；加入按句式变化的连奏、断奏、长音和强弱拍力度。决策卡显示音符时间线、当前演奏音、调性、情绪及节奏，球体随每颗音的力度与时值伸缩。
- 当前铺底只做调内和弦和四种基础配音；下一阶段可把候选扩展成 drums、bass、pad 的 groove，并仍由 Jev 在小节边界选择。
