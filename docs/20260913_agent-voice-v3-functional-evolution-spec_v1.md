---
title: "Agent Voice Functional Evolution Specification (v3.0)"
jd_id: "41.10"
type: "note"
doc_role: "engineering_specification"
status: "in_progress"
implementation_status: "partially_implemented"
stage_summary: "核心已实现 / 扩展演进中：多音色注册表、voice.yml、事件路由表、完整 CLI 子命令体系（voices/validate/normalize/audition）及 7/7 单元测试已上线；待接入 Martin 专属新录音并完成终审"
spec_version: "1.0.0"
target_product: "agent-voice"
current_baseline: "v3.0.0 (Code Released)"
target_release: "v3.x"
updated: "2026-09-13 22:12"
parent: "[[README|docs/README]]"
package_root: "[[../README|agent-voice 交付件仓库]]"
system_doc: "[[00-09_System-Meta/01.02_system-docs-lib/tool-cosyvoice-tts|tool-cosyvoice-tts]]"
links:
  - "[[20260913_cosyvoice3-mlx-macos-deployment-guide_v1|前置底座：CosyVoice 3 部署指南]]"
  - "[[20260913_apple-silicon-speech-agent-handbook_v1|前置理论：Apple Silicon 语音引擎手册]]"
  - "[[20260913_agent-voice-reference-voice-recording-guide_v1|配套指南：Reference Voice 录制与采集指南]]"
  - "[[../agent-voice|代码实现：agent-voice (v3.0.0)]]"
---

# Agent Voice — 功能演进 Spec v1.0.0

> [!IMPORTANT] 知识体系关联与实现状态
> - **文档定位**：工程架构实现规范 (Engineering Specification)
> - **实现状态**：**核心功能已全部实现，部分扩展持续演进 (Core Implemented / Extensions In Progress)**。
>   - ✅ **已实现落地**：多音色注册表 (`voices/`)、`voice.yml` 元数据、全局路由表 (`~/.config/agent-voice/config.yml`)、CLI 核心子命令（`voices`、`voice show`、`voice validate`、`voice normalize`、`audition`、`migrate`）、安全边界校验与单元测试；
>   - ⏳ **待执行/待实现**：Martin 提供个人新录音后对 `voices/martin-primary/` 的真实音色替换与 Promotion 门禁评审；未来高级扩展（时段路由、静音模式等）。
> - **知识链路**：[[20260913_cosyvoice3-mlx-macos-deployment-guide_v1|部署指南]] ➔ **演进 Spec (本文)** ➔ 约束 [[20260913_agent-voice-reference-voice-recording-guide_v1|录音采集规范]] ➔ 驱动生产代码 `agent-voice` (v3.0.0)。

> **目标**：把当前单一 `reference.wav + reference.txt` 的本地语音通知工具，演进成一个可维护、可扩展、可审计的 **Agent Auditory Interface**：支持多音色注册、按事件自动路由、音色试听/评分、跨设备同步和安全降级。
>
> 本文面向实现 Agent（Claude Code / Codex / Cursor / Antigravity 等），强调 Requirement → Spec → Design → Task → Test → DoD。

---

# 1. Background

当前 `agent-voice v2.1.0` 已具备：

- Apple Silicon + CosyVoice 3 MLX 本地 TTS；
- `agent-voice "<text>"` 统一 CLI；
- 单一 `reference.wav + reference.txt` 音色克隆；
- kernel/file-lock 级并发序列化；
- Claude Code Stop Hook、Codex wrapper、Generic Agent 接口；
- 跨设备 `setup.sh` 部署；
- 非 daemon、零常驻内存设计。

当前限制：

```text
Single Voice
   ↓
All Events
   ↓
Same Auditory Identity
```

随着 Agent 数量增加，会出现三个问题：

1. **事件不可听觉区分**：完成、警告、权限确认、研究发现都用同一种声音；
2. **音色资产不可管理**：更换 `reference.wav` 等于全局替换；
3. **缺乏可比较机制**：没有 audition、评分和质量门槛。

---

# 2. Product Vision

目标架构：

```text
Agent Event
   │
   ▼
Event Normalizer
   │
   ▼
Voice Policy / Router
   │
   ├── task_complete ───> cove-like
   ├── permission ───────> sentinel-calm
   ├── research ─────────> vale-like
   └── default ──────────> sol-like
   │
   ▼
Voice Registry
   │
   ▼
CosyVoice Runtime
   │
   ▼
Audio Playback
```

核心理念：

> **事件语义与声音身份分离，声音身份与底层 TTS runtime 分离。**

---

# 3. Goals

## G1 — 多音色注册

支持多个独立 voice profile：

```text
voices/
├── sol-like/
├── cove-like/
├── sentinel-calm/
└── narrator-warm/
```

每个 profile 是自包含资产。

## G2 — CLI 统一

```bash
agent-voice "任务完成。"
agent-voice --voice sol-like "任务完成。"
agent-voice -v sentinel-calm "需要权限确认。"
agent-voice voices
agent-voice voice show sol-like
```

## G3 — Event Routing

```bash
agent-voice --event permission "Claude 需要你的确认。"
```

由配置决定：

```text
permission -> sentinel-calm
```

## G4 — Audition

```bash
agent-voice audition sol-like
agent-voice audition --all
```

## G5 — Quality / Safety

每个 profile 必须满足：

- reference 音频存在；
- transcript 存在；
- 音频可解析；
- 时长、采样率和通道满足规范或可自动规范化；
- transcript 非空；
- metadata 可解析；
- profile ID 唯一；
- 来源与使用边界可记录。

---

# 4. Non-Goals

v3.x 不负责：

- 训练新的 TTS foundation model；
- 自动破解/抓取第三方平台私有音频资产；
- 绕过 DRM；
- 创建公众人物或第三方人物的公开可分发 impersonation voice pack；
- 替代用户确认授权、版权或平台 ToS；
- 保证任意 reference 都能实现高保真克隆。

---

# 5. Directory Layout

推荐结构：

```text
agent-voice/
├── README.md
├── setup.sh
├── agent-voice
├── voices/
│   ├── sol-like/
│   │   ├── reference.wav
│   │   ├── reference.txt
│   │   └── voice.yml
│   ├── sentinel-calm/
│   │   ├── reference.wav
│   │   ├── reference.txt
│   │   └── voice.yml
│   └── narrator-warm/
│       ├── reference.wav
│       ├── reference.txt
│       └── voice.yml
├── auditions/
├── templates/
└── tests/
```

运行时：

```text
~/.local/share/agent-voice/
├── voices/
├── config.yml
└── cache/
```

---

# 6. Voice Profile Schema

`voices/<voice-id>/voice.yml`

```yaml
schema_version: 1

id: sol-like
name: Sol-like
version: 1.0.0

description: >
  Relaxed, intelligent, warm-neutral voice for everyday agent notifications.

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

use_cases:
  - default
  - coding
  - completion

tags:
  - relaxed
  - neutral
  - clear
  - low-fatigue

quality:
  status: approved
  naturalness: 4
  intelligibility: 5
  bilingual: 4
  low_fatigue: 5
  short_prompt: 5
  persona_fit: 4
```

---

# 7. Source Metadata

`source.type` 枚举：

```text
self_recorded
consented_person
ai_generated
licensed_voice
third_party_media_experiment
unknown
```

规则：

- `third_party_media_experiment` 默认：
  ```yaml
  redistributable: false
  usage: personal_experiment
  ```
- `unknown` 不允许进入 `approved`。
- `consented_person` 建议保留 consent note/reference。
- AI 平台生成音色应记录 provider 和 acquisition date。

---

# 8. Global Config

`~/.config/agent-voice/config.yml`

```yaml
default_voice: sol-like

routing:
  default: sol-like
  task_complete: cove-like
  permission: sentinel-calm
  warning: sentinel-calm
  error: sentinel-calm
  research: vale-like
  summary: narrator-warm

behavior:
  busy_policy: drop
  max_chars: 300
  playback: afplay
  log_full_text: false

audition:
  corpus: default
```

---

# 9. CLI Specification

## 9.1 Backward-compatible

```bash
agent-voice "文本"
```

## 9.2 Explicit voice

```bash
agent-voice --voice sol-like "文本"
agent-voice -v sol-like "文本"
```

## 9.3 Event routing

```bash
agent-voice --event permission "Claude 需要你的权限确认。"
```

## 9.4 List voices

```bash
agent-voice voices
```

示例输出：

```text
ID              STATUS     STYLE
sol-like        approved   relaxed / neutral / low-fatigue
cove-like       approved   composed / direct
sentinel-calm   approved   calm / authoritative
vale-like       candidate  bright / curious
```

## 9.5 Show voice

```bash
agent-voice voice show sol-like
```

## 9.6 Validate

```bash
agent-voice voice validate sol-like
agent-voice voice validate --all
```

退出码：

```text
0  valid
1  validation warning
2  invalid
```

## 9.7 Audition

```bash
agent-voice audition sol-like
agent-voice audition --all
agent-voice audition sol-like --corpus mixed
```

---

# 10. Audition Corpus

```yaml
completion_zh:
  text: "任务执行完成，所有测试已经通过。"

permission_zh:
  text: "Claude 正在等待你的权限确认。"

error_zh:
  text: "构建失败，请检查最新日志。"

mixed:
  text: "Codex review finished，三个 integration tests failed。"

summary:
  text: "本轮代码审查已经完成，共发现三个问题，其中一个需要立即处理。"
```

输出：

```text
auditions/<voice-id>/
├── completion_zh.wav
├── permission_zh.wav
├── error_zh.wav
├── mixed.wav
└── summary.wav
```

---

# 11. Voice Quality Score

| Dimension | Weight |
|---|---:|
| Naturalness | 20% |
| Intelligibility | 20% |
| Low Fatigue | 20% |
| Bilingual / Code-switching | 15% |
| Short Notification Performance | 15% |
| Persona Fit | 10% |

状态：

```text
candidate  < 3.5
review     3.5–3.99
approved   >= 4.0
```

---

# 12. Reference Validation

最低验证：

```text
WAV exists
transcript exists
metadata exists
duration >= 3s
duration <= 12s
channels == 1 after normalization
sample rate normalized to 24kHz
PCM 16-bit output available
transcript non-empty
```

推荐质量：

```text
4–8 sec
mono
24 kHz
pcm_s16le
single speaker
no music
low reverb
low noise
natural prosody
accurate transcript
```

---

# 13. Normalize Command

```bash
agent-voice voice normalize sol-like
```

等价逻辑：

```bash
ffmpeg -y   -i input   -ar 24000   -ac 1   -c:a pcm_s16le   reference.wav
```

---

# 14. Event Taxonomy

```text
default
task_complete
turn_complete
permission
warning
error
research
summary
background_done
```

原则：

- `turn_complete` ≠ `task_complete`
- warning/error 不默认使用过度激烈声音
- 权限事件要求高辨识度但低焦虑
- summary 可以允许更长、更温暖 narration style

---

# 15. Suggested Voice Roles

### Primary
```text
Role: 日常 coding notification
Style: relaxed + intelligent + low fatigue
```

### Sentinel
```text
Role: permission / warning / error
Style: calm + authoritative + clear
```

### Muse
```text
Role: research / discovery / creative result
Style: bright + curious + light
```

### Narrator
```text
Role: daily summary / long-form review
Style: warm + editorial
```

---

# 16. Concurrency

保持现有：

```text
busy_policy = drop
```

MVP：file lock / flock。

未来可选：

```text
drop
latest
queue
```

---

# 17. Logging

默认禁止记录完整 Agent 内容。

允许：

```text
timestamp
event
voice_id
text_length
duration_ms
result
exit_code
```

---

# 18. Failure Policy

TTS 永远不能影响 Agent 主任务。

```bash
agent-voice --event task_complete "任务完成。" || true
```

Fallback：

```text
requested voice missing
   ↓
default voice
   ↓
system voice (optional)
   ↓
silent failure + log
```

---

# 19. Migration from v2.1

当前：

```text
reference.wav
reference.txt
```

迁移：

```text
voices/default/reference.wav
voices/default/reference.txt
voices/default/voice.yml
```

新增：

```bash
agent-voice migrate
```

---

# 20. Tests

## Unit
1. metadata parser
2. invalid YAML
3. missing reference
4. missing transcript
5. unknown voice
6. default fallback
7. event routing
8. path traversal rejection
9. invalid ID
10. score calculation

## Integration
1. explicit voice → WAV
2. event route → expected voice
3. busy lock → second request dropped
4. invalid voice → default fallback
5. offline inference
6. Chinese
7. English
8. mixed Chinese/English

## Regression

```bash
agent-voice "hello"
```

必须继续成功。

---

# 21. Security

Voice ID：

```regex
^[a-z0-9][a-z0-9-]{0,63}$
```

禁止：

```text
../
absolute path
shell interpolation
```

Profile metadata 不能执行 command。

subprocess 使用 argv array，避免 `shell=True`。

---

# 22. Definition of Done

- [ ] legacy CLI compatible
- [ ] >= 3 voice profiles
- [ ] `voices`
- [ ] `voice show`
- [ ] `voice validate`
- [ ] `audition`
- [ ] explicit `--voice`
- [ ] event `--event`
- [ ] routing config
- [ ] fallback behavior
- [ ] migration
- [ ] unit tests
- [ ] integration tests
- [ ] offline test
- [ ] no full-text logging by default
- [ ] README updated

---

# 23. Implementation Phases

## Phase 1 — Registry
```text
voice.yml
profile discovery
validation
--voice
```

## Phase 2 — Routing
```text
config.yml
--event
fallback
```

## Phase 3 — Audition
```text
audition corpus
batch synthesis
score metadata
```

## Phase 4 — UX
```text
voice list/show
migration
documentation
```

---

# 24. Acceptance Examples

```bash
agent-voice voices
agent-voice --voice sol-like "任务完成。"
agent-voice --event permission "Claude 正在等待确认。"
agent-voice audition sol-like
agent-voice voice validate --all
```

---

# 25. Future Extensions

- per-Agent voice
- time-of-day routing
- quiet hours
- automatic summary compression
- voice preference profiles
- dynamic speaking rate
- instruction/style conditioning
- Swift warm daemon
- UDS service
- auditory earcons + TTS
- voice pack import/export with provenance

---

# Final Design Principle

```text
Agent
  ↓
Semantic Event
  ↓
Voice Policy
  ↓
Voice Identity
  ↓
TTS Runtime
  ↓
Audio
```

任何一层替换都不应迫使其他层重写。

**Spec verdict:** `Ready for implementation planning`
