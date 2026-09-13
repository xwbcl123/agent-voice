---
title: "Agent Voice Reference Voice 录制与采集指南"
jd_id: "41.10"
type: "note"
doc_role: "user_operational_guide"
status: "active"
implementation_status: "user_reference"
stage_summary: "用户使用参考：指导 Martin 录制专属个人音色或采集 AI 音色切片，提供标准参数、清洗脚本与 100% 文本对齐铁律"
version: "1.0.0"
target_system: "agent-voice (v3.0.0) + CosyVoice 3 MLX"
updated: "2026-09-13 22:12"
parent: "[[README|docs/README]]"
package_root: "[[../README|agent-voice 交付件仓库]]"
system_doc: "[[00-09_System-Meta/01.02_system-docs-lib/tool-cosyvoice-tts|tool-cosyvoice-tts]]"
links:
  - "[[20260913_agent-voice-v3-functional-evolution-spec_v1|上级规范：Agent Voice v3.0 功能演进 Spec]]"
  - "[[20260913_cosyvoice3-mlx-macos-deployment-guide_v1|底层环境：CosyVoice 3 部署指南]]"
  - "[[../voices/martin-primary/voice.yml|目标落点：Martin 专属音色 Profile]]"
---

# Agent Voice — Reference Voice 录制与采集指南 v1.0.0

> [!TIP] 知识体系关联与实现状态
> - **文档定位**：用户操作与采集参考指南 (User Operational Reference)
> - **实现状态**：**用户使用参考 (User Reference / Active)**。本文为非代码类实操指南，用于指导 Martin 录制个人原声或采集 AI 音色，标准长期有效。
> - **知识链路**：受 [[20260913_agent-voice-v3-functional-evolution-spec_v1|功能演进 Spec]] 声学门禁约束 ➔ **录音指南 (本文)** ➔ 输出音频直接注入 [[../voices/martin-primary/voice.yml|voices/martin-primary/]] ➔ 经 `agent-voice voice validate` 验证上线。

> **用途**：为本地 `agent-voice + CosyVoice 3` 准备高质量 reference voice。
>
> **适用场景**：个人学习、音色比较、本地 TTS 实验、Agent auditory UX 研究。
>
> **核心原则**：**可听 ≠ 可复制，可复制 ≠ 可分发，可分发 ≠ 可商用。**

---

# 1. 最终要得到什么？

每个 voice profile：

```text
voice-id/
├── reference.wav
├── reference.txt
└── voice.yml
```

`reference.wav`：目标声音短样本。

`reference.txt`：与音频实际内容严格一致的 transcript。

---

# 2. 推荐技术规格

| Item | 推荐 |
|---|---|
| Duration | **4–8 秒** |
| Minimum | 3 秒 |
| Maximum | 10–12 秒以内 |
| Format | WAV |
| Codec | PCM 16-bit |
| Sample Rate | 24 kHz |
| Channels | Mono |
| Speaker | 单人 |
| Background Music | 无 |
| Reverb | 尽量低 |
| Noise | 尽量低 |
| Transcript | 字词严格一致 |

标准化：

```bash
ffmpeg -y   -i input_audio   -ar 24000   -ac 1   -c:a pcm_s16le   reference.wav
```

---

# 3. 好 Reference 的判断标准

好：

```text
一个人
+ 一句话
+ 自然语速
+ 稳定音量
+ 明确语气
+ 无音乐
+ 无其他说话人
+ 无明显混响
```

差：

```text
背景音乐很大
哭喊
多人叠话
笑声盖住文字
手机外放后二次录音
远距离混响
过度压缩
```

---

# 4. Reference 不是越长越好

这里是 CosyVoice zero-shot conditioning，不是训练一个新模型。

因此：

```text
5 秒非常干净
```

通常优于：

```text
30 秒混杂、带音乐、多情绪
```

ElevenLabs 自己训练 Instant/Professional Voice Clone 需要更长素材，这是不同机制。

---

# 5. 建议台词

中文：

```text
系统检查已经完成，所有后台任务运行正常，现在可以继续下一步操作。
```

英文：

```text
The system check is complete, and all background tasks are running normally.
```

中英混合：

```text
Claude Code 已完成 review，所有 unit tests passed，可以继续下一步。
```

---

# 6. Source A — 自己录自己的声音

最推荐。

建议：

1. 安静房间；
2. 关闭风扇；
3. 手机距嘴 20–30 cm；
4. 正常音量；
5. 不刻意播音腔；
6. 连录三遍；
7. 选最自然的一遍。

导出后：

```bash
ffmpeg -y   -i my_voice.m4a   -ar 24000   -ac 1   -c:a pcm_s16le   reference.wav
```

---

# 7. Source B — 经本人同意的朋友/家人

建议记录：

```yaml
source:
  type: consented_person
  consent: verbal
  usage: personal_experiment
  redistributable: false
```

“同意个人实验”不自动等于：

```text
可公开发布
可商业化
可上传公开 Voice Library
```

---

# 8. Source C — ChatGPT Voice / Live

ChatGPT Voice 当前提供自然语音会话；具体可用 voice 可能随客户端和产品更新而变化。

推荐方法：

> 在正常使用界面里，让 Voice 模式朗读你自己提供的测试句，再录制可听输出用于私人实验。

例如：

```text
The system check is complete, and all background tasks are running normally.
```

或：

```text
任务执行完成，所有测试已经通过。
```

优先采用平台/系统允许的录屏或音频录制。

不要：

- 提取 app 内部 voice asset；
- 绕过访问控制；
- 抓取隐藏接口；
- 把样本误称为 OpenAI 官方可分发 voice pack。

转码：

```bash
ffmpeg -y   -i chatgpt_capture.m4a   -ar 24000   -ac 1   -c:a pcm_s16le   reference.wav
```

建议 profile 命名：

```text
relaxed-neutral-01
calm-direct-01
bright-curious-01
```

而不是直接绑定服务官方名称。

---

# 9. Source D — Gemini Live

Google 当前支持在 Gemini App 中选择不同 voice；可用数量会随语言变化，voice setting 会用于 Gemini Live 等语音响应。

采集原则同上：

```text
正常使用
→ 让 Gemini 朗读自定义句
→ 录制可听输出
→ 裁切
→ transcript
→ 转成 reference.wav
```

不要提取 APK/app 内部资产，也不要绕过平台访问控制。

A/B 测试时，让所有候选 voice 说同一句。

---

# 10. Source E — ElevenLabs

可考虑：

```text
Voice Library
Voice Design
Instant Voice Clone
Professional Voice Clone
```

对于 `agent-voice`，寻找音色审美方向最适合：

```text
Voice Library / Voice Design
```

推荐：

1. 选候选 voice；
2. 用统一 audition 台词生成短音频；
3. 下载你被允许下载/使用的生成结果；
4. 裁到 4–8 秒；
5. 转为标准 reference；
6. 记录来源。

```yaml
source:
  type: licensed_voice
  provider: ElevenLabs
  source_label: "Voice Library candidate"
  usage: personal_experiment
  redistributable: false
```

注意：

ElevenLabs 官方对其 Instant Voice Clone 通常建议约 1–2 分钟高质量音频；Professional Voice Clone 使用更长训练素材。

这和本地 CosyVoice 的 4–8 秒 reference 不是一回事。

---

# 11. Source F — 第三方影视作品

本节只针对：

> **你合法访问的电影、电视剧、纪录片、播客等内容，用于个人本地学习、声学研究和非公开实验。**

它不代表你拥有：

- 演员/角色声音权；
- 公开发布 clone 的权利；
- 商用权；
- 冒充权；
- 绕过 DRM 的权利。

---

# 12. 影视片段如何选

理想：

```text
单人讲话
+ 4–8 秒
+ 无配乐
+ 无环境噪音
+ 无插话
+ 无哭喊
+ 无电话滤镜
```

最适合：

```text
安静室内近景对白
采访
旁白
安静对话
```

不适合：

```text
动作戏
酒吧
战场
汽车
背景音乐
多人争吵
```

---

# 13. 从合法本地媒体文件裁片

如果你有一个可合法处理的本地媒体文件：

```bash
ffmpeg   -ss 00:42:13.500   -i movie.mkv   -t 00:00:06.000   -vn   -ac 1   -ar 24000   -c:a pcm_s16le   reference.wav
```

不要用本指南绕过 DRM 或访问控制。

---

# 14. 有背景音乐怎么办？

第一选择：

> **换片段。**

Source separation 后，即便听感还行，残留的：

```text
音乐谐波
room tone
artifact
reverb
```

仍可能污染 reference。

轻微背景时可做有限处理：

```bash
ffmpeg   -i raw.wav   -af "highpass=f=70,lowpass=f=12000"   cleaned.wav
```

---

# 15. Audio Cleanup

去头尾静音：

```bash
ffmpeg   -i input.wav   -af silenceremove=start_periods=1:start_threshold=-45dB:stop_periods=1:stop_threshold=-45dB   trimmed.wav
```

谨慎：过强会切掉 `s/f/h/breath` 等弱音。

Normalize：

```bash
ffmpeg   -i trimmed.wav   -af loudnorm   normalized.wav
```

最终：

```bash
ffmpeg -y   -i normalized.wav   -ar 24000   -ac 1   -c:a pcm_s16le   reference.wav
```

---

# 16. Transcript 是关键

必须写音频**实际**说的内容。

音频：

```text
Well, I think we're ready to go.
```

正确：

```text
Well, I think we're ready to go.
```

不要改写成：

```text
I think we are ready to go.
```

---

# 17. 字幕只作为起点

字幕可能：

- 展开缩写；
- 省略口头语；
- 改断句；
- 做翻译；
- 做 closed-caption 描述。

正确流程：

```text
subtitle
   ↓
manual listen
   ↓
exact transcript
```

---

# 18. Reference 与目标语言

Reference 与生成语言可以不同：

```text
English reference
        ↓
Chinese output
```

但跨语言稳定度不一定相同。

每个 candidate 建议测试：

```text
Chinese
English
Mixed
```

---

# 19. Audition Test Set

中文完成：

```text
任务执行完成，所有测试已经通过。
```

中文权限：

```text
Claude 正在等待你的权限确认。
```

中文错误：

```text
构建失败，请检查最新日志。
```

Mixed：

```text
Codex review finished，三个 integration tests failed。
```

Summary：

```text
本轮代码审查已经完成，共发现三个问题，其中一个需要立即处理。
```

---

# 20. Listening Score

| Dimension | Weight |
|---|---:|
| Naturalness | 20% |
| Intelligibility | 20% |
| Low Fatigue | 20% |
| Chinese/English | 15% |
| Short Sentence | 15% |
| Persona Fit | 10% |

Agent voice 要特别重视：

> **Low Fatigue**

第一次惊艳 ≠ 一天听 30 次仍舒服。

---

# 21. Persona 设计

建议按：

```text
calm
direct
warm
bright
curious
authoritative
low-fatigue
editorial
```

而不是只按性别分类。

推荐角色：

```text
Primary  -> relaxed + intelligent
Sentinel -> calm + authoritative
Muse     -> bright + curious
Narrator -> warm + editorial
```

---

# 22. voice.yml 示例

```yaml
schema_version: 1

id: relaxed-neutral-01
name: Relaxed Neutral 01
version: 1.0.0

description: >
  Relaxed and clear general-purpose Agent voice.

language:
  primary: en
  supported:
    - en
    - zh
    - mixed

style:
  energy: medium
  warmth: medium
  authority: medium
  pace: medium
  expressiveness: restrained
  fatigue: low

reference:
  wav: reference.wav
  transcript: reference.txt

source:
  type: ai_generated
  provider: null
  source_label: null
  usage: personal_experiment
  redistributable: false
```

---

# 23. Source Classification

```text
self_recorded
consented_person
ai_generated
licensed_voice
third_party_media_experiment
unknown
```

影视样本：

```yaml
source:
  type: third_party_media_experiment
  usage: personal_experiment
  redistributable: false
```

---

# 24. Git / 分发

如果 source 是：

```text
电影
电视剧
演员
AI 平台专有 voice
第三方个人
```

不要把原始 `reference.wav` 随代码公开分发。

建议 `.gitignore`：

```text
voices/*/reference.wav
voices/*/source-original.*
```

---

# 25. 命名

私人本地可以保留来源备注。

公开 profile 建议：

```text
warm-narrator-01
calm-direct-02
```

避免使用公众人物、演员或平台官方 voice 名字作为公开 voice pack 名称。

---

# 26. 不用于欺骗

不要把克隆音色用于：

- 冒充本人；
- 冒充客服；
- 冒充同事/家人；
- 社工；
- 欺骗式电话；
- 伪造证据；
- 让他人误以为是真人录音。

---

# 27. 推荐 Workflow

```text
发现喜欢的声音
   ↓
确认来源/用途边界
   ↓
选择 4–8s 干净单人句
   ↓
录制/合法导出
   ↓
裁切
   ↓
人工 transcript
   ↓
24k mono PCM
   ↓
voice.yml
   ↓
agent-voice validate
   ↓
audition
   ↓
评分
   ↓
approved / reject
```

---

# 28. 保留原始来源

```text
voice-id/
├── source-original.m4a
├── reference.wav
├── reference.txt
└── voice.yml
```

版权/授权敏感时：

```text
source-original.*
```

只本地保存，不进 Git/cloud sync。

---

# 29. Promotion Gate

- [ ] reference 4–8 sec
- [ ] clean single speaker
- [ ] transcript exact
- [ ] 24kHz mono PCM
- [ ] 中文测试通过
- [ ] 英文测试通过
- [ ] mixed 测试通过
- [ ] low-fatigue >= 4
- [ ] total score >= 4.0
- [ ] source metadata complete
- [ ] redistribution status 明确

---

# 30. Source Summary

| Source | 推荐度 | 权利清晰度 | 质量潜力 | 备注 |
|---|---:|---:|---:|---|
| 自己录音 | ★★★★★ | ★★★★★ | ★★★★☆ | 最推荐 |
| 经同意朋友/家人 | ★★★★☆ | ★★★★☆ | ★★★★☆ | 保留 consent |
| ChatGPT Voice | ★★★★☆ | ★★☆☆☆ | ★★★★★ | 个人实验；勿提取内部资源 |
| Gemini Live | ★★★★☆ | ★★☆☆☆ | ★★★★★ | 同上 |
| ElevenLabs licensed/library | ★★★★★ | ★★★★☆ | ★★★★★ | 按 voice 条款 |
| 影视作品片段 | ★★★☆☆ | ★☆☆☆☆ | ★★★★☆ | 仅个人实验，勿分发 |
| 随机社交媒体人声 | ★★☆☆☆ | ★☆☆☆☆ | ★★☆☆☆ | 噪声与授权风险高 |

---

# 31. Naming Convention

```text
relaxed-neutral-01
calm-direct-01
sentinel-calm-01
bright-curious-01
warm-narrator-01
```

---

# 32. Checklist

采集前：

- [ ] 我知道来源
- [ ] 我理解用途边界
- [ ] 我不会绕过 DRM
- [ ] 我不会公开分发未获授权样本

音频：

- [ ] 单人
- [ ] 4–8 秒
- [ ] 无音乐
- [ ] 无重叠
- [ ] 无明显混响
- [ ] 自然语气

处理：

- [ ] WAV
- [ ] 24 kHz
- [ ] mono
- [ ] PCM 16-bit
- [ ] transcript 精确

验证：

- [ ] 中文
- [ ] 英文
- [ ] mixed
- [ ] short notification
- [ ] low-fatigue

---

# 33. Current External Reference Notes

截至 September 13, 2026：

- ChatGPT Voice 官方仍将 Voice/Live 定义为自然语音会话能力，具体 voice 选项可能随版本变化。
- Gemini 官方允许用户选择 voice，并说明此设置会用于 Gemini Live；可用数量会因语言变化。
- ElevenLabs 提供 Voice Library、Voice Design、Instant Voice Cloning、Professional Voice Cloning。
- ElevenLabs 官方强调：单 speaker、低噪声、低混响和一致的录音风格对 voice cloning 很关键。

平台规则会变化，因此采集前应重新查看当前 ToS 与 voice 使用说明。

---

# 34. References

OpenAI — ChatGPT Voice  
https://help.openai.com/en/articles/20001274

Google — Change Gemini's voice  
https://support.google.com/gemini/answer/15277943

Google — Gemini Live Help  
https://support.google.com/gemini/answer/15274899

ElevenLabs — Voice Cloning  
https://elevenlabs.io/docs/eleven-creative/voices/voice-cloning

ElevenLabs — Instant Voice Cloning  
https://elevenlabs.io/docs/eleven-creative/voices/voice-cloning/instant-voice-cloning

ElevenLabs — Voice Library  
https://elevenlabs.io/docs/eleven-creative/voices/voice-library

---

# Final Principle

最好的 Agent voice，不一定是最“像真人”的声音。

真正长期好用的标准：

```text
清晰
+ 低疲劳
+ 易区分
+ 中英稳定
+ 不抢注意力
+ 来源边界清楚
```

把声音当作 Agent UX 的一部分，而不是单纯“克隆一个好听的声音”。
