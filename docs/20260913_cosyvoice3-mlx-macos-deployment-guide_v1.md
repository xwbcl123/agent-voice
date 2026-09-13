---
title: "CosyVoice 3.0 MLX on Apple Silicon — Agentic 本地语音通知部署指南"
jd_id: "41.10"
type: "note"
doc_role: "deployment_guide"
status: "active"
implementation_status: "implemented"
stage_summary: "已实现：/opt/homebrew/bin/speech + 8-bit 模型与 24kHz 单声道参考音频全链路打通，实测退出码 0，内存按需单次释放"
created: "2026-09-13 19:55"
updated: "2026-09-13 22:12"
version: "1.1.0"
previous_version: "1.0.0"
target_platform:
  - "macOS 15+"
  - "Apple Silicon (M-series)"
primary_runtime: "soniqo/speech-swift + CosyVoiceTTS"
model: "aufklarer/CosyVoice3-0.5B-MLX-8bit"
model_base: "FunAudioLLM/Fun-CosyVoice3-0.5B-2512"
license: "Apache-2.0"
change_type: "Corrective / Breaking"
breaking_changes:
  - "移除虚构的 Python run_mlx_inference() 路径"
  - "主部署路径由 Python FastAPI placeholder 改为 speech-swift/CosyVoiceTTS"
  - "移除未经验证的 <200ms TTFT、0.2–0.4 RTF、<8W、~1.2GB runtime RAM 等 SLA 宣称"
  - "移除 <happy>/<calm>/<serious> 作为 CosyVoice 3 官方控制语法的假设"
  - "Claude Code 项目级设置路径修正为 .claude/settings.json"
  - "Stop hook 不再使用 matcher；任务完成与轮次结束语义分离"
verification_baseline: "Fact-checked against upstream/model-card sources available on September 13, 2026"
parent: "[[README|docs/README]]"
package_root: "[[../README|agent-voice 交付件仓库]]"
system_doc: "[[00-09_System-Meta/01.02_system-docs-lib/tool-cosyvoice-tts|tool-cosyvoice-tts]]"
links:
  - "[[20260913_apple-silicon-speech-agent-handbook_v1|前置理论：Apple Silicon 语音引擎手册]]"
  - "[[20260913_agent-voice-v3-functional-evolution-spec_v1|演进规范：Agent Voice v3.0 功能演进 Spec]]"
  - "[[20260913_agent-voice-reference-voice-recording-guide_v1|操作参考：Reference Voice 录制与采集指南]]"
tags:
  - "topic/apple-silicon"
  - "topic/speech"
  - "topic/tts"
  - "topic/mlx"
  - "topic/cosyvoice"
  - "topic/claude-code"
  - "topic/codex"
  - "topic/ai-agents"
aliases:
  - "CosyVoice 3.0 MLX on Apple Silicon — Agentic 本地语音通知部署指南"
  - "CosyVoice 3.0 (MLX 4-bit) on Apple Silicon — Agentic 本地语音通知部署指南"
---


# CosyVoice 3.0 (MLX 4-bit) on Apple Silicon
## Agentic 本地语音通知部署指南 v1.1.0

> [!NOTE] 知识体系关联与实现状态
> - **文档定位**：底层运行时部署指南 (Runtime Deployment Guide)
> - **实现状态**：**已实现 (Implemented / Active)**。底层 `soniqo/speech-swift` CLI、`aufklarer/CosyVoice3-0.5B-MLX-8bit` 权重、参考音频与 afplay 播放管道均已全链路部署并通过实机验收。
> - **知识链路**：[[20260913_apple-silicon-speech-agent-handbook_v1|架构手册]] ➔ **部署指南 (本文)** ➔ 为 [[20260913_agent-voice-v3-functional-evolution-spec_v1|v3 功能演进 Spec]] 提供底层运行时底座。

> **目标**：在 Apple Silicon Mac 上，用真实可运行的 CosyVoice 3 MLX runtime，为 Claude Code / Codex / Cursor 等 Agent 工作流提供本地语音通知。
>
> **设计原则**：先保证 **真实可运行、可验证、可回滚**，再优化为 warm daemon 和低延迟。
>
> **重要说明**：本指南不把“模型权重存在”与“Python MLX runtime 存在”等同。当前主路径使用已经实现 CosyVoiceTTS 推理的 `speech-swift`。

---

# 0. Version Change Summary

## v1.0.0 → v1.1.0

| Area | v1.0.0 | v1.1.0 |
|---|---|---|
| MLX runtime | 假设 `mlx` + Python 即可推理 | 使用已有 `speech-swift / CosyVoiceTTS` |
| `server.py` | placeholder，实际不加载模型 | 从主路径移除 |
| LLM | 4-bit | 4-bit |
| DiT Flow | 误写 FP16 | **int4** |
| HiFi-GAN / HiFT bundle | 误写 FP16 | **fp32** |
| S3 tokenizer | 未列出 | **bf16，zero-shot cloning 必需** |
| Bundle size | ~1.2 GB | 仓库约 **1.26 GB**；不等于 runtime RAM |
| Emotion control | 假设 `<happy>` 等 | 不再假设；仅使用 runtime 明确支持的控制 |
| Voice cloning | 未定义 reference profile | 明确 `reference.wav + transcript` |
| CLI JSON | quoting 有 bug | 不再通过手拼 JSON |
| Claude settings | `.claude.json` | `.claude/settings.json` |
| Stop hook | `matcher: .*` | Stop 不使用 matcher |
| Performance | 声称固定 SLA | 改为必须本机 benchmark |
| Privacy | “100% 绝对隐私” | 改为“模型缓存完成后可离线推理” |
| Status | Production Guide | **Production Candidate**，需通过 DoD Gate |

---

# 1. Why：为什么仍然选择 CosyVoice 3 + MLX？

对于 AI Coding Agent，本地语音通知的真正价值不是“让电脑会说话”，而是降低异步工作流中的注意力切换：

```text
Agent 执行
   ↓
编译 / 测试 / Sub-Agent
   ↓
用户去做其他事情
   ↓
生命周期事件触发
   ↓
本地 TTS 播报
```

这个场景适合本地 TTS，原因主要有三个：

1. **隐私边界清晰**
   - 模型文件缓存完成后，可在断网环境执行本地推理。
   - Agent 任务摘要无需发送到第三方 TTS API。

2. **成本结构稳定**
   - 无按字符、Token 或调用次数计费。

3. **Apple Silicon 适配良好**
   - MLX 面向 Apple Silicon Unified Memory。
   - `speech-swift` 已实现 CosyVoiceTTS 的 Apple Silicon 推理路径。

但本指南不会把这些优势夸大成未经验证的性能 SLA。

---

# 2. Fact-Checked Model Architecture

目标模型：

```text
aufklarer/CosyVoice3-0.5B-MLX-4bit
```

其模型卡当前描述的 bundle 结构为：

| Component | Architecture / Precision | Approx. logical size |
|---|---|---:|
| LLM | Qwen2.5-0.5B, int4 | ~388 MB |
| DiT Flow Matching | 22-layer DiT, int4 | ~186 MB |
| HiFi-GAN / HiFT-related vocoder weights | fp32 | ~79 MB |
| S3-Tokenizer-v3 | Conformer/FSMN/FSQ, bf16 | ~462 MB |
| Total logical bundle | mixed precision | ~1.1 GB |
| HF repository footprint | — | ~1.26 GB |

> **注意**：磁盘模型大小 ≠ runtime resident memory。  
> Runtime memory 必须在你的具体 Mac 上实测。

Zero-shot voice cloning pipeline 可以抽象为：

```text
Text ----------------------┐
                           ├──> Qwen2.5 LLM ──> speech tokens
Reference transcript ------┘                         │
                                                     ▼
Reference WAV ──> S3-Tokenizer ──> prompt tokens ──> DiT Flow ──> Mel
                                                     │
                                                     ▼
                                               Vocoder / HiFT
                                                     │
                                                     ▼
                                                 PCM Audio
```

---

# 3. Supported Deployment Architecture

## 3.1 v1.1 推荐架构

```text
┌───────────────────────────────────────────────┐
│ Claude Code / Codex / Cursor / Shell          │
└──────────────────────┬────────────────────────┘
                       │ lifecycle event
                       ▼
┌───────────────────────────────────────────────┐
│ agent-voice                                   │
│ - normalize text                              │
│ - truncate / deduplicate                      │
│ - lock / queue                                │
│ - map event → message                         │
└──────────────────────┬────────────────────────┘
                       │ local process call
                       ▼
┌───────────────────────────────────────────────┐
│ speech-swift CLI                              │
│ `speech speak --engine cosyvoice ...`         │
└──────────────────────┬────────────────────────┘
                       │
                       ▼
┌───────────────────────────────────────────────┐
│ CosyVoiceTTS                                  │
│ - Qwen2.5 int4                                │
│ - DiT int4                                    │
│ - S3 tokenizer bf16                           │
│ - vocoder fp32                                │
└──────────────────────┬────────────────────────┘
                       │
                       ▼
                WAV → macOS `afplay`
```

### 为什么 v1.1 不以 FastAPI daemon 为默认？

因为模型权重本身并不提供 Python MLX inference API。

v1.0 中的：

```python
run_mlx_inference(...)
```

没有真实实现。

v1.1 选择已经存在的 runtime，首先保证：

```text
Text → real model inference → WAV → speaker
```

是闭环。

---

# 4. Requirements

## 4.1 Hardware

- Apple Silicon Mac：
  - M1 / M2 / M3 / M4 / M5 及更新 M 系列全谱系 (含 Base, Pro, Max, Ultra)
- 建议至少：
  - 16 GB unified memory
- 足够模型缓存空间：
  - 至少预留 3–5 GB，包含模型、临时 WAV、工具缓存

> 16 GB 是工程建议值，不是模型官方硬性最低要求。

## 4.2 Software

推荐：

```text
macOS 15+
native ARM Homebrew (/opt/homebrew)
Swift 6+
Xcode 16+ / Metal Toolchain
```

检查当前架构：

```bash
uname -m
```

期望：

```text
arm64
```

检查 Homebrew：

```bash
which brew
```

推荐：

```text
/opt/homebrew/bin/brew
```

如果显示：

```text
/usr/local/bin/brew
```

请先确认是不是 Rosetta/x86 Homebrew。

---

# 5. Install Runtime

## 5.1 安装 speech-swift CLI

优先使用 Homebrew：

```bash
brew install speech
```

验证：

```bash
speech --help
```

如果 Homebrew formula 在你的环境中不可用，可从源码构建：

```bash
git clone https://github.com/soniqo/speech-swift.git
cd speech-swift

make build
```

如果遇到：

```text
Failed to load the default metallib
```

先安装 Metal Toolchain：

```bash
xcodebuild -downloadComponent MetalToolchain
```

然后重新：

```bash
make build
```

---

# 6. First Real Inference Test

这一阶段的目标只有一个：

> **不要接 Agent。先证明真实 CosyVoice inference 能产生非静音 WAV。**

创建工作目录：

```bash
mkdir -p ~/.local/share/agent-voice
mkdir -p ~/.cache/agent-voice
```

准备一段 reference audio，例如：

```text
~/.local/share/agent-voice/reference.wav
```

推荐：

- 单人
- 环境安静
- 3–10 秒
- 无背景音乐
- 无混响或尽量少混响
- 内容对应一个准确 transcript

保存 transcript：

```bash
cat > ~/.local/share/agent-voice/reference.txt <<'EOF'
这是参考音频中实际说出的内容。
EOF
```

进行第一次 synthesis：

```bash
REF="$HOME/.local/share/agent-voice/reference.wav"
REF_TEXT="$(cat "$HOME/.local/share/agent-voice/reference.txt")"

speech speak \
  "Agent 语音系统测试成功。" \
  --engine cosyvoice \
  --voice-sample "$REF" \
  --cosy-reference-transcript "$REF_TEXT" \
  -o "$HOME/.cache/agent-voice/test.wav"
```

播放：

```bash
afplay "$HOME/.cache/agent-voice/test.wav"
```

---

# 7. Acceptance Test A：确认不是“假成功”

执行：

```bash
test -s "$HOME/.cache/agent-voice/test.wav" \
  && echo "PASS: WAV exists and is non-empty" \
  || echo "FAIL"
```

查看文件：

```bash
file "$HOME/.cache/agent-voice/test.wav"
ls -lh "$HOME/.cache/agent-voice/test.wav"
```

可选，用 ffprobe：

```bash
brew install ffmpeg
ffprobe "$HOME/.cache/agent-voice/test.wav"
```

**DoD：**

- [ ] 命令退出码为 0
- [ ] WAV 文件存在
- [ ] WAV 文件非 0 byte
- [ ] 能听到目标文本
- [ ] 声音不是纯静音/噪声
- [ ] reference voice 相似度可接受

只有通过这里，才进入 Agent 集成。

---

# 8. agent-voice Wrapper

不要让每个 Agent 自己拼复杂的 CosyVoice 命令。

创建：

```text
~/.local/bin/agent-voice
```

内容：

```bash
#!/usr/bin/env bash
set -euo pipefail

VOICE_HOME="${AGENT_VOICE_HOME:-$HOME/.local/share/agent-voice}"
CACHE_DIR="${AGENT_VOICE_CACHE:-$HOME/.cache/agent-voice}"

REF_WAV="$VOICE_HOME/reference.wav"
REF_TXT="$VOICE_HOME/reference.txt"

mkdir -p "$CACHE_DIR"

RAW_TEXT="${1:-Agent 本轮处理结束。}"

# 去掉换行，限制最大输入长度。
# 不在 shell 中处理 JSON，也不假设 emotion tag 语法。
CLEAN_TEXT="$(
  printf '%s' "$RAW_TEXT" \
    | tr '\r\n' '  ' \
    | sed -E 's/[[:space:]]+/ /g' \
    | cut -c 1-300
)"

if [[ -z "${CLEAN_TEXT// /}" ]]; then
  exit 0
fi

if [[ ! -f "$REF_WAV" ]]; then
  echo "agent-voice: reference WAV missing: $REF_WAV" >&2
  exit 2
fi

if [[ ! -f "$REF_TXT" ]]; then
  echo "agent-voice: reference transcript missing: $REF_TXT" >&2
  exit 2
fi

REF_TEXT="$(cat "$REF_TXT")"

# 防止多个 Agent 同时争抢声卡 / 同时加载模型。
LOCKDIR="$CACHE_DIR/lock"

if ! mkdir "$LOCKDIR" 2>/dev/null; then
  # Notification 场景优先避免叠音。
  exit 0
fi

cleanup() {
  rm -rf "$LOCKDIR"
}
trap cleanup EXIT INT TERM

OUT="$CACHE_DIR/notification-$$.wav"

speech speak \
  "$CLEAN_TEXT" \
  --engine cosyvoice \
  --voice-sample "$REF_WAV" \
  --cosy-reference-transcript "$REF_TEXT" \
  -o "$OUT"

afplay "$OUT"

rm -f "$OUT"
```

授权：

```bash
chmod +x ~/.local/bin/agent-voice
```

确认 PATH：

```bash
command -v agent-voice
```

测试：

```bash
agent-voice "测试完成，现在可以连接 Agent 生命周期事件。"
```

---

# 9. 为什么 v1.1 不使用 `<happy>` / `<serious>`

不要默认这样做：

```text
<happy>Hello
<serious>Hello
<calm>Hello
```

除非你正在使用的 runtime 文档明确支持这些 tag。

CosyVoice 3 能力层面支持 instruction / style / fine-grained control，但不同 runtime 的控制接口并不等价。

因此 v1.1 的默认原则：

```text
Capability supported by model
        ≠
Arbitrary syntax supported by runtime
```

在 notification 场景中，先使用稳定的：

```text
text + reference voice
```

情感控制作为后续增强项。

---

# 10. Claude Code Integration

## 10.1 配置文件

用户级：

```text
~/.claude/settings.json
```

项目级：

```text
<repo>/.claude/settings.json
```

本地项目覆盖：

```text
<repo>/.claude/settings.local.json
```

不要把项目 hook 写到：

```text
.claude.json
```

---

## 10.2 Stop：播报“本轮结束”，而不是“任务完成”

`Stop` 的语义是：

> Claude 结束当前 response / turn。

它不等价于：

> 整个任务一定完成。

配置示例：

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "$HOME/.local/bin/agent-voice \"Claude 本轮处理结束。\""
          }
        ]
      }
    ]
  }
}
```

### 为什么没有 matcher？

`Stop` 不依赖 matcher 做过滤，因此不加入：

```json
"matcher": ".*"
```

---

## 10.3 Notification：只播报需要用户注意的事件

如果你的 Claude Code 版本支持具体 notification matcher，优先使用精确事件，例如 permission prompt，而不是：

```text
.*
```

目标语义：

```text
Claude 需要你的权限确认。
```

而不是把所有 notification 都播出来。

> Hook schema 可能随 Claude Code 版本变化。应用前运行当前版本的官方 hook 验证/诊断命令，并以当前官方文档为准。

---

# 11. Codex Integration

Codex 的 hook 能力和配置 schema 会随版本演进。

因此 v1.1 不复制未经当前环境验证的固定 `config.toml` 片段，而采用：

```text
Codex lifecycle event
        ↓
command hook
        ↓
~/.local/bin/agent-voice "Codex 本轮处理结束。"
```

原则与 Claude 相同：

1. hook 只负责事件触发；
2. TTS 逻辑全部封装在 `agent-voice`；
3. 不在 Codex 配置中复制模型参数；
4. “response ended”和“task completed”使用不同播报文本。

在当前 Codex 版本中配置前，先检查：

```bash
codex --help
```

以及当前官方 hooks 文档。

---

# 12. Cursor / Generic CLI Integration

任何能够执行 shell command 的工具都可以接：

```bash
~/.local/bin/agent-voice "任务需要你的注意。"
```

这就是 wrapper 的价值：

```text
Agent-specific lifecycle
           ↓
  generic shell command
           ↓
      agent-voice
           ↓
       CosyVoice
```

模型实现和 Agent 实现彼此解耦。

---

# 13. Offline / Privacy Validation

模型第一次使用通常需要下载，因此：

```text
首次安装/下载 ≠ air-gapped
```

模型和依赖缓存完成之后，再测试离线能力。

## Test

先正常运行一次：

```bash
agent-voice "缓存预热测试。"
```

然后关闭 Wi-Fi：

```bash
networksetup -setairportpower en0 off
```

再次：

```bash
agent-voice "这是离线语音测试。"
```

成功后才能写：

> “该部署在模型与依赖缓存完成后支持离线本地推理。”

不要写：

> “100% 绝对隐私”

除非你另外完成：

- outbound traffic capture
- dependency audit
- telemetry audit
- process/network inspection

可以使用：

```bash
nettop
lsof -i
tcpdump
```

进行验证。

恢复 Wi-Fi：

```bash
networksetup -setairportpower en0 on
```

> 某些 Mac 的 Wi-Fi interface 不一定是 `en0`。如有需要先用 `networksetup -listallhardwareports` 确认。

---

# 14. Concurrency Protection

Agent workflow 最大的实际风险之一是同时完成多个任务。

错误情况：

```text
Claude Stop ----┐
Codex Stop -----┼──> TTS simultaneously
Sub-Agent ------┘
```

可能出现：

- 多段音频叠播
- 多次模型加载
- memory spike
- 声卡争抢

v1.1 wrapper 使用：

```bash
mkdir "$LOCKDIR"
```

作为最小互斥锁。

它的策略是：

> **Busy 时丢弃新通知。**

这对于 notification 是合理的 MVP 策略。

后续可以升级为：

```text
SQLite queue
FIFO
launchd daemon
Swift actor queue
```

---

# 15. Crash / Failure Behavior

语音通知不能影响 Agent 主任务。

因此原则是：

```text
Agent correctness > notification delivery
```

建议 Agent hook 在调用时使用容错包装：

```bash
$HOME/.local/bin/agent-voice "Claude 本轮处理结束。" || true
```

这样即使：

- 模型损坏
- speech CLI crash
- WAV 无法播放
- CoreAudio unavailable

也不会让 Agent lifecycle 本身失败。

---

# 16. Benchmark：禁止猜性能

不要直接声称：

```text
TTFT <200 ms
RTF 0.2–0.4
RAM ~1.2 GB
Power <8 W
```

这些数据必须绑定：

- Mac model
- SoC
- RAM
- macOS version
- speech-swift version
- model revision
- reference audio
- text corpus
- cold/warm state

---

## 16.1 基础 latency benchmark

```bash
/usr/bin/time -lp \
  agent-voice "这是一次本地语音性能测试。"
```

至少重复：

```text
n = 10
```

记录：

```text
cold start
warm filesystem
p50
p95
```

---

## 16.2 Model cache / runtime memory

可辅助使用：

```bash
ps -o pid,rss,command -ax | grep speech
```

更深入：

```bash
vmmap <PID>
```

如果 CLI 在推理完成后立刻退出，需要在后续 persistent-daemon 版本中测量峰值 RSS。

---

## 16.3 Power

可选：

```bash
sudo powermetrics
```

只报告真实观测结果。

---

# 17. Warm Daemon：v1.2 候选优化

如果实测发现每次：

```bash
speech speak ...
```

启动 latency 太大，可以升级成 persistent runtime。

推荐下一步不是重新发明 Python inference，而是：

```text
Swift service
  ↓
import CosyVoiceTTS
  ↓
model = fromPretrained() once
  ↓
keep resident
  ↓
Unix domain socket / localhost HTTP
```

目标架构：

```text
Agent
  ↓
agent-voice
  ↓
Unix Socket
  ↓
VoiceDaemon (Swift)
  ├── CosyVoiceTTS resident
  ├── voice profile cache
  ├── serial queue
  └── AVFoundation playback
```

这个版本才能合理测试：

```text
warm TTFA
resident RSS
queue latency
```

---

# 18. Persistent Voice Profile Optimization

Zero-shot cloning需要：

```text
reference WAV
+
reference transcript
```

如果 runtime API 支持 profile extraction，可将：

```text
S3 tokenizer output
prompt tokens
prompt features
speaker-related conditioning
```

缓存起来。

这样无需每次 notification 都重新处理 reference audio。

这是 warm daemon 最大的优化点之一。

---

# 19. launchd：只在真正拥有 daemon 后使用

v1.0 把一个没有模型加载能力的 Python server 配成：

```xml
<key>KeepAlive</key>
<true/>
```

会制造“服务活着 = TTS 可用”的错觉。

v1.1 的原则：

> **没有真实 persistent inference service，就不要部署 fake daemon。**

当 v1.2 Swift VoiceDaemon 完成后，再创建：

```text
~/Library/LaunchAgents/com.local.agent-voice.plist
```

届时至少需要：

```text
RunAtLoad
KeepAlive
ThrottleInterval
StandardOutPath
StandardErrorPath
WorkingDirectory
```

并提供：

```text
/health
or
socket ping
```

---

# 20. Health Check Contract for Future Daemon

未来 daemon 的 `/health` 不应只返回 HTTP 200。

正确 health contract：

```json
{
  "status": "ready",
  "model_loaded": true,
  "voice_profile_loaded": true,
  "audio_output_available": true,
  "queue_depth": 0
}
```

只有：

```text
model_loaded=true
```

才允许标记为 ready。

---

# 21. Security Boundaries

即使是 localhost service，也需要明确威胁模型。

如果未来开放：

```text
127.0.0.1:9880
```

至少考虑：

- max text length
- request timeout
- queue length
- malformed input
- rate limit
- local untrusted process abuse
- log redaction

如果只需要本机 Agent，优先：

```text
Unix domain socket
```

而不是 TCP port。

---

# 22. Logging

日志不能默认保存完整敏感 Agent 内容。

推荐：

```text
timestamp
event type
character count
duration
result
error code
```

不要默认记录：

```text
full source code
secret
prompt content
vulnerability details
credentials
```

例如：

```text
2026-09-13T19:00:00+02:00 event=claude_stop chars=21 result=ok duration_ms=...
```

---

# 23. Troubleshooting

| Symptom | Likely cause | Action |
|---|---|---|
| `speech: command not found` | CLI 未安装 / PATH | `brew install speech`; 检查 PATH |
| Rosetta architecture | x86 Homebrew | 使用 native ARM Homebrew |
| `Failed to load default metallib` | Metal library/toolchain 缺失 | 安装 Metal Toolchain，重新 build |
| 首次运行很慢 | 模型首次下载/缓存 | 等待模型缓存完成后再 benchmark |
| cloning 相似度差 | reference 差 / transcript 不准 | 换 3–10 秒干净 reference，逐字校准 transcript |
| 多个通知叠音 | concurrency | 使用 lock / queue |
| Agent hook 卡住 | TTS 同步运行 | 根据需要 background 执行或 daemon 化 |
| 离线失败 | 模型未全部缓存 | 联网预热并确认缓存 |
| 输出 WAV 为 0 byte | inference 失败 | 检查 CLI stderr / model cache |
| Hook 配置不生效 | Agent schema/version 变化 | 用当前官方 docs 校验 |

---

# 24. Definition of Done — Production Gate

在把这份指南从：

```text
Production Candidate
```

升级为：

```text
Production
```

之前，至少完成以下测试。

## Gate 1 — Real inference

- [ ] CosyVoice 实际生成 WAV
- [ ] 音频非静音
- [ ] 中文可懂度正常
- [ ] reference voice cloning 可接受

## Gate 2 — Agent E2E

- [ ] Claude Stop → voice
- [ ] Claude permission notification → voice
- [ ] Codex lifecycle → voice
- [ ] TTS failure 不影响 Agent

## Gate 3 — Concurrency

连续触发：

```text
20 events
```

验证：

- [ ] 不 crash
- [ ] 不叠音
- [ ] 不出现失控 memory spike

## Gate 4 — Offline

- [ ] Wi-Fi OFF 后可正常 synthesis
- [ ] 无隐藏 cloud fallback

## Gate 5 — Performance

记录：

- [ ] cold latency
- [ ] warm latency
- [ ] p50
- [ ] p95
- [ ] disk size
- [ ] peak memory
- [ ] hardware/software version

## Gate 6 — Restart / Recovery

- [ ] CoreAudio 暂时不可用时不会破坏 Agent
- [ ] 模型缓存损坏有清晰报错
- [ ] wrapper lock 不会永久残留

---

# 25. Recommended Roadmap

## v1.1 — Reproducible Baseline

```text
speech-swift
+ CosyVoiceTTS
+ agent-voice
+ Claude/Codex hooks
```

目标：

> **先真实跑通。**

## v1.2 — Warm Voice Daemon

```text
Swift daemon
+ resident model
+ cached voice profile
+ serial queue
+ UDS
```

目标：

> **降低重复模型启动成本。**

## v1.3 — Adaptive Notification Layer

加入：

```text
event priority
deduplication
summary
quiet hours
different voice/style by event
```

目标：

> **从 TTS 工具升级为 Agent auditory interface。**

---

# 26. Final Architecture Principle

这套系统最重要的不是 CosyVoice 本身，而是职责分离：

```text
Agent
 │
 │ event
 ▼
Notification Policy
 │
 │ normalized intent
 ▼
Voice Dispatcher
 │
 │ stable interface
 ▼
TTS Runtime
 │
 ▼
Audio
```

因此：

- Claude Code 变了，不需要改 TTS；
- Codex 变了，不需要改模型；
- CosyVoice runtime 变了，不需要改 Agent hook；
- 未来换 Qwen3-TTS / Kokoro，只替换 runtime adapter。

这才是 Agentic voice notification 值得长期维护的工程结构。

---

# 27. References

## Upstream / Model

1. CosyVoice upstream  
   https://github.com/FunAudioLLM/CosyVoice

2. CosyVoice3 MLX 4-bit model  
   https://huggingface.co/aufklarer/CosyVoice3-0.5B-MLX-4bit

3. speech-swift / CosyVoiceTTS runtime  
   https://github.com/soniqo/speech-swift

4. Apple MLX  
   https://github.com/ml-explore/mlx

## Agent Hooks

5. Claude Code Hooks  
   https://code.claude.com/docs/en/hooks-guide

6. OpenAI Codex documentation  
   https://developers.openai.com/codex/

---

# Appendix A — Minimal Smoke Test

```bash
#!/usr/bin/env bash
set -euo pipefail

REF="$HOME/.local/share/agent-voice/reference.wav"
REF_TEXT="$(cat "$HOME/.local/share/agent-voice/reference.txt")"
OUT="/tmp/cosyvoice-smoke.wav"

speech speak \
  "这是 CosyVoice 三的本地部署验证。" \
  --engine cosyvoice \
  --voice-sample "$REF" \
  --cosy-reference-transcript "$REF_TEXT" \
  -o "$OUT"

test -s "$OUT"

afplay "$OUT"

echo "PASS: real inference + non-empty WAV + playback path completed"
```

---

# Appendix B — v1.1 Known Limitations

1. CLI baseline 可能存在重复加载模型的 latency。
2. 本版本没有承诺 `<200ms` TTFT。
3. 本版本没有声明固定 RTF。
4. 本版本没有声明固定 runtime RAM。
5. 本版本没有声明固定功耗。
6. Agent hook schema 可能随 Claude Code / Codex 更新而变化。
7. 情感控制语法必须以所使用 runtime 的当前文档为准。
8. 若要求低延迟常驻服务，应进入 v1.2 Swift daemon 工程，而不是恢复 v1.0 的 placeholder Python server。

---

**Version verdict:** `v1.1.0 — Production Candidate / Reproducible Baseline`

只有在本机完成第 24 节 DoD 后，建议将 metadata 改为：

```yaml
STATUS: "Production"
```

---

# Appendix C — 本机实操部署与性能实测记录 (2026-09-13)

### 1. 运行时与模型变体修正
- **运行时**: `speech` (soniqo/speech-swift) v0.0.27 (Homebrew native ARM: `/opt/homebrew/bin/speech`)
- **上游硬性限制**: `speech-swift` v0.0.27 要求 `CosyVoice LLM bundles must be 8-bit quantized or 16-bit/bf16 plain Linear.`。尝试加载 4-bit 权重会报错 `modelLoadFailed`。
- **实测生效模型**: `aufklarer/CosyVoice3-0.5B-MLX-8bit`（LLM 8-bit group_size 64 + DiT Flow + CAM++ 192-dim speaker encoder）。
- **封装命令**: `/Users/martin/.local/bin/agent-voice`（内置 `--cosyvoice-variant "${COSYVOICE_VARIANT:-8bit}"` 与文件锁排队机制）。

### 2. 本机环境基准
- **OS**: macOS (arm64, Apple Silicon)
- **Swift**: 6.4 (swiftlang-6.4.0.34.1)
- **Reference Voice**: `~/.local/share/agent-voice/reference.wav` (24kHz 16-bit PCM WAV) + `reference.txt`

### 3. 性能基准实测 (`/usr/bin/time -lp`)
- **测试文本**: "这是一次本地语音性能测试。" (音频时长 2.20s)
- **纯推理耗时**: 1.52s
- **RTF (Real-Time Factor)**: **0.69**
- **最大驻留内存 (Max RSS)**: **1,306,722,304 bytes (~1.24 GB)**
- **总端到端耗时**: 7.08s（包含 cold/warm 进程拉起、模型缓存加载、CAM++ 特征提取、MLX 推理、WAV 写入、`afplay` 完整播放 2.20s 及锁清理）

### 4. Agent 接入生效状态
- **Claude Code**: 已在 `~/.claude/settings.json` 中配置 `Stop` hook 调用 `agent-voice` 并附带 `|| true` 容错隔离保护。
