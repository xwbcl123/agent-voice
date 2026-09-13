---
title: "Agent Voice 4.0 — Instructive Prosody & Style Control Specification"
jd_id: "41.10"
type: "note"
doc_role: "engineering_specification"
status: "active"
implementation_status: "in_progress"
stage_summary: "v4.0 核心演进：引入 CosyVoice instruct2 风格控制体系、Instruction Profile Registry (styles.yml)、Voice × Style 正交路由、Runtime 探针 (doctor) 与速率/增益解耦控制"
spec_version: "1.1.0"
product_version: "4.0.0"
baseline_product: "agent-voice v3.0.0"
updated: "2026-09-13 22:55"
parent: "[[README|docs/README]]"
package_root: "[[../README|agent-voice 交付件仓库]]"
system_doc: "[[00-09_System-Meta/01.02_system-docs-lib/tool-cosyvoice-tts|tool-cosyvoice-tts]]"
links:
  - "[[20260913_agent-voice-v3-functional-evolution-spec_v1|前序基线：Agent Voice v3.0 功能演进 Spec]]"
  - "[[20260913_cosyvoice3-mlx-macos-deployment-guide_v1|底层底座：CosyVoice 3 部署指南]]"
  - "[[20260913_agent-voice-reference-voice-recording-guide_v1|配套指南：Reference Voice 录制与采集指南]]"
  - "[[../agent-voice|代码实现：agent-voice (v4.0.0)]]"
---

# Agent Voice 4.0
## Instructive Prosody & Style Control Spec v1.1.0

> **目标**：在已经落地的 Agent Voice v3.0 基础上，引入 CosyVoice instruct2 风格控制，使 Voice Identity 与 Delivery Style 成为两个独立维度。
>
> v4.0 不重新实现 v3.0 已完成的 Voice Registry、事件路由、资产校验、Audition、部署和测试能力，而是在这些能力之上增加：
>
> ```text
> 谁在说  → Voice
> 怎么说  → Style / Instruction
> 说多快  → Speed
> 播多响  → Playback Gain
> 说什么  → Text
> ```

---

# 1. Baseline: v3.0 Already Implemented

根据当前 v3.0 实现，以下能力视为既有基线，不属于 v4 重做范围：

- 多音色注册表 `voices/<voice-id>/`
- `voice.yml` 元数据
- `agent-voice -v/--voice`
- `agent-voice -e/--event`
- `agent-voice voices`
- `voice show`
- `voice validate`
- `voice normalize`
- `audition`
- `config.yml` 事件路由
- backward compatibility：
  ```bash
  agent-voice "text"
  ```
- file-lock / busy-drop concurrency
- zero-resident non-daemon architecture
- setup.sh 跨设备安装
- test suite 与质量门禁

v4.0 的设计必须复用这些能力。

---

# 2. Why v4.0

v3.0 已解决：

```text
Event → Voice
```

但仍未解决：

```text
同一个 Voice
如何以不同情绪、语速、强调方式说话
```

v4.0 的目标是：

```text
Event
  ├── Voice Identity
  └── Delivery Style
```

例如：

```yaml
permission:
  voice: sentinel-calm
  style: serious
```

而不是为同一个 voice 创建：

```text
sentinel-calm
sentinel-warm
sentinel-serious
sentinel-urgent
```

---

# 3. Performance and Memory Impact

## 3.1 Expected Memory Impact

Instruct2 通常复用同一套：

```text
Tokenizer
LLM
Flow / DiT
Vocoder
```

不会为 instruction 再加载一套模型。

新增内存主要来自：

- instruction token buffer
- prompt embeddings
- 少量额外 KV cache
- style-conditioning 中间张量

因此对短 instruction 来说，预期内存增量相对于模型权重和生成张量较小。

但 v4.0 不允许在未 benchmark 前写死：

```text
0 MB overhead
1% overhead
```

### Release target

在相同 voice、text、输出音频长度条件下：

```text
Peak RSS with instruct
---------------------- <= 1.10
Peak RSS zero-shot
```

即建议目标：

> instruct 模式峰值内存增量不超过 10%。

这是验收门槛，不是预先宣称的事实。

---

## 3.2 Expected Latency Impact

固定新增成本主要是：

```text
instruction tokenization
+
extra prompt prefill
```

通常较小。

更明显的总耗时差异往往来自 style 本身：

- `calm`：说得更慢、停顿更多
- `narrator`：音频可能更长
- `urgent`：可能更短、更快
- `cheerful`：prosody variation 增加

所以必须同时报告：

```text
wall-clock latency
audio duration
RTF
```

不能只比较总耗时。

### Release target

对 neutral profile：

```text
p50 instruct overhead <= 15%
```

同样是建议验收目标。

---

# 4. Product Model

```text
Agent Event
    │
    ▼
v3 Event Router
    │
    ├── Voice ID
    └── Style ID
          │
          ▼
Instruction Profile Registry
          │
          ▼
Runtime Adapter
          │
          ├── reference.wav
          ├── reference.txt
          ├── instruction prompt
          ├── optional speed
          └── output WAV
```

---

# 5. New v4 Components

v4.0 只新增四个核心组件：

1. **Instruction Profile Registry**
2. **Voice × Style Resolver**
3. **Runtime Capability Probe**
4. **Instruct Benchmark Harness**

推荐新增目录：

```text
agent-voice/
├── styles/
│   ├── neutral.yml
│   ├── warm.yml
│   ├── cheerful.yml
│   ├── calm.yml
│   ├── serious.yml
│   ├── urgent.yml
│   ├── curious.yml
│   ├── concise.yml
│   ├── narrator.yml
│   └── soft.yml
├── tests/
│   ├── test_styles.py
│   ├── test_instruct_routing.py
│   └── test_runtime_capabilities.py
└── benchmarks/
    └── instruct-benchmark.yml
```

也允许把 profile 合并进单个：

```text
styles.yml
```

MVP 建议先单文件，后续再拆分。

---

# 6. CLI Additions

## 6.1 Style Profile

```bash
agent-voice --style warm "欢迎回来。"
agent-voice -s serious "需要你的确认。"
```

## 6.2 Explicit Alias

```bash
agent-voice --instruct-profile warm "欢迎回来。"
```

`--style` 是推荐短接口。

## 6.3 Raw Instruction

Expert mode：

```bash
agent-voice \
  --instruct "请用温暖、自然、令人安心的语气说话，语速略慢。" \
  "今天的工作已经完成。"
```

## 6.4 Voice + Style

```bash
agent-voice \
  --voice martin-primary \
  --style cheerful \
  "任务顺利完成。"
```

## 6.5 Event Routing

```bash
agent-voice --event permission "Claude 正在等待确认。"
```

v4 允许 event 同时解析：

```text
voice = sentinel-calm
style = serious
```

## 6.6 Dry Run

```bash
agent-voice \
  --voice martin-primary \
  --style warm \
  --dry-run \
  "测试文本"
```

示例输出：

```yaml
voice: martin-primary
style: warm
instruction_language: zh
speed: 0.95
gain_db: 0
runtime_mode: instruct2
fallback: none
```

---

# 7. Argument Precedence

Style：

```text
--instruct
    >
--style / --instruct-profile
    >
event route style
    >
voice default style
    >
global default style
```

Voice：

```text
--voice
    >
event route voice
    >
global default voice
```

Speed：

```text
--speed
    >
style profile speed
    >
global default speed
```

Gain：

```text
--gain
    >
style/event gain
    >
global gain
```

---

# 8. Updated config.yml Schema

v3 scalar route：

```yaml
routing:
  permission: sentinel-calm
```

v4 object route：

```yaml
routing:
  permission:
    voice: sentinel-calm
    style: serious
```

完整示例：

```yaml
default_voice: default
default_style: neutral

routing:
  default:
    voice: default
    style: neutral

  task_complete:
    voice: default
    style: cheerful

  turn_complete:
    voice: default
    style: concise

  permission:
    voice: sentinel-calm
    style: serious

  warning:
    voice: sentinel-calm
    style: urgent

  error:
    voice: sentinel-calm
    style: serious

  research:
    voice: default
    style: curious

  summary:
    voice: martin-primary
    style: narrator

  background_done:
    voice: default
    style: concise

behavior:
  busy_policy: drop
  max_chars: 300
  playback: afplay
  log_full_text: false
  max_instruction_chars: 400
  require_instruct: false
  default_instruction_language: auto
```

---

# 9. Backward-Compatible Route Parser

v4 必须同时接受：

```yaml
permission: sentinel-calm
```

和：

```yaml
permission:
  voice: sentinel-calm
  style: serious
```

解析规则：

```text
scalar string
    → voice=<value>, style=default_style

object
    → voice=<voice>, style=<style>
```

这样 setup.sh 无需强制一次性迁移所有用户配置。

---

# 10. Default Instruction Profiles

推荐存储：

```text
~/.config/agent-voice/styles.yml
```

```yaml
schema_version: 1

profiles:

  neutral:
    name: Neutral
    description: Balanced default delivery for everyday use.
    instruction_zh: >
      请用自然、清晰、平衡的语气说话，保持正常语速和适度停顿，
      不要刻意夸张情绪。
    instruction_en: >
      Speak naturally and clearly with balanced emotion,
      normal pacing, and moderate pauses. Avoid exaggerated delivery.
    speed: 1.00
    gain_db: 0
    tags: [default, balanced, low-fatigue]

  warm:
    name: Warm
    description: Warm, reassuring and low-fatigue.
    instruction_zh: >
      请用温暖、自然、令人安心的语气说话，语速略慢，
      保持轻柔但清晰，不要耳语。
    instruction_en: >
      Speak warmly, naturally and reassuringly,
      slightly slower than normal. Keep the voice gentle but clear,
      without whispering.
    speed: 0.95
    gain_db: 0
    tags: [warm, reassuring, calm]

  cheerful:
    name: Cheerful
    description: Friendly and subtly upbeat.
    instruction_zh: >
      请用轻松、友好、略带笑意的语气说话，保持自然活力，
      不要过度兴奋，也不要喊叫。
    instruction_en: >
      Speak in a friendly, cheerful tone with a subtle smile
      and natural energy. Do not sound theatrical or shout.
    speed: 1.03
    gain_db: 0
    tags: [happy, friendly, completion]

  calm:
    name: Calm
    description: Calm, composed and steady.
    instruction_zh: >
      请用平静、沉着、稳定的语气说话，适当放慢节奏，
      使用自然停顿，并保持发音清晰。
    instruction_en: >
      Speak calmly, steadily and with composure.
      Use slightly slower pacing, natural pauses, and clear articulation.
    speed: 0.92
    gain_db: 0
    tags: [calm, composed, focus]

  serious:
    name: Serious
    description: Controlled, authoritative and clear.
    instruction_zh: >
      请用认真、沉稳、克制而清晰的语气说话，
      突出关键信息，但不要制造恐慌或显得生硬。
    instruction_en: >
      Speak seriously, clearly and with controlled authority.
      Emphasize important information without sounding alarming or harsh.
    speed: 0.96
    gain_db: 0
    tags: [serious, permission, important]

  urgent:
    name: Urgent
    description: Firm and attention-catching without shouting.
    instruction_zh: >
      请用明确、坚定、稍显紧迫的语气说话，节奏略快，
      清楚突出需要立即关注的信息，但不要喊叫。
    instruction_en: >
      Speak clearly and firmly with moderate urgency
      and slightly faster pacing. Highlight what needs immediate attention,
      but do not shout.
    speed: 1.08
    gain_db: 1
    tags: [urgent, warning, error]

  curious:
    name: Curious
    description: Bright, interested and exploratory.
    instruction_zh: >
      请用明亮、好奇、富有探索感的语气说话，
      保持自然轻快，并在关键发现处给予适度强调。
    instruction_en: >
      Speak in a bright, curious and exploratory tone.
      Keep the delivery naturally light and gently emphasize key discoveries.
    speed: 1.02
    gain_db: 0
    tags: [research, discovery, insight]

  concise:
    name: Concise
    description: Direct and efficient notification delivery.
    instruction_zh: >
      请用简洁、直接、清晰的方式说话，减少不必要的停顿，
      保持自然语气，不要显得急躁。
    instruction_en: >
      Speak concisely, directly and clearly,
      with minimal unnecessary pauses while remaining natural and unhurried.
    speed: 1.07
    gain_db: 0
    tags: [short, efficient, notification]

  narrator:
    name: Narrator
    description: Warm editorial narration for longer summaries.
    instruction_zh: >
      请用温暖、沉稳、有叙事感的语气说话，
      保持流畅节奏和自然层次，在段落转折处适当停顿。
    instruction_en: >
      Speak with a warm, grounded editorial narration style.
      Maintain a flowing rhythm, natural phrasing,
      and gentle pauses at transitions.
    speed: 0.92
    gain_db: 0
    tags: [summary, long-form, editorial]

  soft:
    name: Soft
    description: Gentle delivery, separate from playback volume.
    instruction_zh: >
      请用较轻柔、贴近而清晰的语气说话，
      保持完整发声，不要变成耳语。
    instruction_en: >
      Speak softly, closely and clearly,
      while maintaining full vocal support and avoiding a whisper.
    speed: 0.96
    gain_db: -1
    tags: [soft, private, evening]
```

---

# 11. Instruction Language Selection

默认规则：

```text
Mostly Chinese target text
    → instruction_zh

Mostly English target text
    → instruction_en

Mixed text
    → configurable default
```

建议：

```yaml
default_instruction_language: auto
mixed_instruction_language: zh
```

Instruction 不得拼入播报正文。

错误：

```text
请用温暖语气说。任务完成。
```

正确：

```text
instruction channel = 请用温暖语气说。
tts text            = 任务完成。
```

---

# 12. Raw --instruct Safety

`--instruct` 为 Expert Mode。

默认限制：

```text
max_instruction_chars = 400
recommended <= 180
```

不得把未经信任的 LLM 输出直接传入：

```bash
agent-voice --instruct "$UNTRUSTED_OUTPUT" "..."
```

原因：

- prompt 可过长
- 可能出现指令覆盖
- 增加 latency
- 输出不可预测
- 可能破坏 style consistency

默认日志只记录：

```text
instruction_length
style_id
```

不记录完整 instruction。

---

# 13. Runtime Capability Probe

新增：

```bash
agent-voice doctor
```

检查：

```text
speech CLI
CosyVoice engine
voice cloning
instruct2
speed
output WAV
emotion/style support
```

示例：

```yaml
runtime:
  speech_cli: true
  cosyvoice: true
  cloning: true
  instruct2: true
  speed: true
  output_file: true
```

如果 instruct2 不支持：

```text
requested style
    ↓
warn once
    ↓
fallback to v3 zero-shot
```

严格模式：

```bash
agent-voice --require-instruct -s warm "..."
```

不支持时返回非零。

---

# 14. Runtime Adapter Contract

```python
synthesize(
    text: str,
    voice_profile: VoiceProfile,
    instruction: str | None,
    speed: float | None,
    output_path: Path,
) -> SynthesisResult
```

必须保证：

- instruction 通过 runtime 的 style/instruct2 channel；
- 不能拼接到 text；
- 不让用户手写 runtime special token；
- subprocess 使用 argv array；
- 不使用 `shell=True`。

---

# 15. Speed Policy

两种控制：

```text
Instruction pacing
→ 自然节奏、停顿、表达方式

Numeric speed
→ 相对可预测的整体速度
```

建议范围：

```text
0.75 <= speed <= 1.25
```

Profile 可给默认 speed；显式 `--speed` 覆盖。

---

# 16. Pitch Policy

v4 不提供模型级：

```bash
--pitch +2
```

原因：

- natural-language instruction 可表达“稍高、明亮”或“稍低、温暖”；
- 但这不等于确定性的 semitone shift。

未来如需精确 pitch：

```text
generated WAV
    ↓
DSP post-processing
```

独立设计为：

```bash
--post-pitch-semitones
```

不纳入 v4 MVP。

---

# 17. Playback Gain Policy

必须区分：

```text
soft style
→ 发声方式

gain -4 dB
→ 最终播放电平
```

新增：

```bash
agent-voice --gain -4 "..."
```

允许范围建议：

```text
-12 dB to +3 dB
```

---

# 18. Voice Profile Compatibility

现有 `voice.yml` 可选增加：

```yaml
delivery:
  default_style: neutral
  recommended_styles:
    - neutral
    - warm
    - cheerful
  blocked_styles:
    - urgent
```

如果 style 被 blocked：

```text
fallback to default_style
```

并输出 warning。

该字段为可选，旧 profile 无需修改。

---

# 19. Benchmark Harness

新增：

```bash
agent-voice benchmark \
  --voice martin-primary \
  --styles zero-shot,neutral,warm,serious \
  --runs 10
```

记录：

```csv
voice,style,run,wall_ms,audio_ms,rtf,peak_rss_mb
```

必须固定：

- text
- reference
- machine
- runtime version
- model revision

比较：

```text
zero-shot
neutral
warm
cheerful
serious
urgent
```

---

# 20. Quality Evaluation

| Dimension | Weight |
|---|---:|
| Instruction adherence | 25% |
| Naturalness | 20% |
| Voice identity retention | 20% |
| Intelligibility | 15% |
| Low fatigue | 10% |
| Repeatability | 10% |

关键风险：

```text
Style adherence ↑
Speaker identity ↓
```

因此不能只判断“情绪像不像”，还要检查是否仍像原 voice。

---

# 21. Tests

## Unit

1. styles.yml parser
2. unknown style
3. instruction length limit
4. precedence
5. Chinese/English prompt selection
6. speed bounds
7. gain bounds
8. scalar v3 route compatibility
9. v4 object route
10. blocked style fallback
11. capability fallback

## Integration

1. v3 legacy command
2. explicit voice + neutral
3. explicit voice + warm
4. event → voice + style
5. raw instruct
6. Chinese target
7. English target
8. mixed target
9. unsupported instruct fallback
10. require-instruct failure
11. busy-drop behavior unchanged

## Regression

以下 v3 命令必须全部继续通过：

```bash
agent-voice "text"
agent-voice -v default "text"
agent-voice --event permission "text"
agent-voice voices
agent-voice voice show default
agent-voice voice validate --all
agent-voice audition default
```

---

# 22. Migration

新增：

```bash
agent-voice migrate --to 4
```

动作：

1. 备份 `config.yml`
2. 创建 `styles.yml`
3. 增加 `default_style: neutral`
4. 可选把 scalar route 升级成 object route
5. 不修改 `voices/`
6. 不修改 reference assets
7. 生成 migration report
8. 运行 tests

由于 parser 支持 v3 scalar route，migration 可以渐进执行。

---

# 23. setup.sh Changes

v4 setup.sh 新增：

- 安装 `styles.yml`
- 保留用户自定义 profile
- 执行 `agent-voice doctor`
- 执行 style schema validation
- 运行 v3 regression tests
- 运行一个 instruct smoke test
- instruct 不可用时打印 fallback 状态，不删除 v3 能力

---

# 24. Implementation Tasks

| Task | Priority | Status |
|---|---:|---|
| Capability probe | P0 | Backlog |
| Style schema/parser | P0 | Backlog |
| `--style` | P0 | Backlog |
| Raw `--instruct` | P0 | Backlog |
| Voice × Style resolver | P0 | Backlog |
| v3/v4 route compatibility | P0 | Backlog |
| Runtime adapter instruct2 | P0 | Backlog |
| Style tests | P0 | Backlog |
| `--dry-run` | P1 | Backlog |
| Numeric speed | P1 | Backlog |
| Playback gain | P1 | Backlog |
| Benchmark command | P1 | Backlog |
| Migration command | P1 | Backlog |
| Voice/style compatibility metadata | P2 | Backlog |
| Reference-conditioning cache | P2 | Future |
| Warm daemon | P2 | Future |

---

# 25. Definition of Done

## Functional

- [ ] v3 CLI regression passes
- [ ] `--style neutral`
- [ ] `--style warm`
- [ ] `--style cheerful`
- [ ] `--style calm`
- [ ] `--style serious`
- [ ] `--style urgent`
- [ ] `--style curious`
- [ ] `--style concise`
- [ ] `--style narrator`
- [ ] `--style soft`
- [ ] raw `--instruct`
- [ ] event route resolves voice + style
- [ ] scalar v3 routes remain valid
- [ ] capability fallback works
- [ ] `--require-instruct` works
- [ ] `--dry-run` works

## Performance

- [ ] zero-shot baseline recorded
- [ ] instruct peak RSS measured
- [ ] RTF measured
- [ ] audio duration measured
- [ ] p50/p95 reported
- [ ] no unsupported SLA claims

## Quality

- [ ] instruction adherence evaluated
- [ ] voice identity retention evaluated
- [ ] Chinese profiles tested
- [ ] English profiles tested
- [ ] mixed text tested
- [ ] low-fatigue review completed

## Security

- [ ] max instruction length enforced
- [ ] raw instruction absent from default logs
- [ ] no shell interpolation
- [ ] existing voice ID validation unchanged
- [ ] untrusted Agent output not auto-used as instruction

---

# 26. Recommended Delivery Phases

## Phase 1 — Instruct MVP

```text
styles.yml
--style
runtime instruct2 adapter
neutral/warm/serious
tests
```

## Phase 2 — Routing

```text
voice + style object routes
v3 scalar compatibility
migration
```

## Phase 3 — Control Surface

```text
--instruct
--speed
--gain
--dry-run
doctor
```

## Phase 4 — Evaluation

```text
benchmark
quality score
voice identity regression
audition by style
```

---

# 27. Acceptance Examples

```bash
agent-voice \
  --voice martin-primary \
  --style warm \
  "今天的工作已经完成。"
```

```bash
agent-voice \
  --event permission \
  "Claude 正在等待你的确认。"
```

```bash
agent-voice \
  --instruct "请用明亮、好奇、自然轻快的语气说话。" \
  "我们发现了一个值得继续研究的新方向。"
```

```bash
agent-voice \
  --style narrator \
  --speed 0.90 \
  "下面是今天的完整工作总结。"
```

---

# Final Architecture

```text
Agent / User
     │
     ▼
Existing v3 Event Router
     │
     ├── Voice ID
     └── Style ID
            │
            ▼
Instruction Profile Registry
            │
            ▼
CosyVoice Instruct2 Adapter
            │
            ├── Voice Reference
            ├── Instruction
            ├── Speed
            └── Text
            │
            ▼
          Audio
```

**Spec verdict:** `Ready for implementation planning against the implemented v3.0 baseline`
