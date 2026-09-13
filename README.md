# Agent Voice

> 🎙️ **Apple Silicon CosyVoice 3.0 MLX 本地零常驻语音基础设施与自然韵律控制引擎**  
> High-fidelity, zero-resident-RAM local TTS & instructive prosody control infrastructure for AI agent fleets on macOS Apple Silicon.

[![Platform](https://img.shields.io/badge/Platform-macOS%20Apple%20Silicon-black?style=flat-square&logo=apple)](https://apple.com)
[![Engine](https://img.shields.io/badge/Engine-CosyVoice%203.0%20(MLX%208--bit)-blue?style=flat-square)](https://github.com/soniqo/speech-swift)
[![RAM](https://img.shields.io/badge/Resident%20RAM-0%20MB-brightgreen?style=flat-square)]()
[![Version](https://img.shields.io/badge/CLI-v4.0.0-orange?style=flat-square)]()
[![Tests](https://img.shields.io/badge/Tests-15%2F15%20Passing-success?style=flat-square)]()
[![License](https://img.shields.io/badge/License-MIT-purple?style=flat-square)]()

[English](#english-overview) · [中文文档](#中文说明) · [Agent 接入指南](#3-智能体接入指南-agent-fleet-integration) · [CLI 命令大全](#5-cli-命令与调用参考) · [风格矩阵](#4-10-大开箱即用交付风格-styles-registry)

---

## 中文说明

### 1. 它解决什么问题 (Why Agent Voice?)

现代 AI 智能体（如 **Claude Code**, **OpenAI Codex**, **Antigravity CLI**, **Cursor Agent** 等）在终端中自主执行长时间的重构、构建、测试与研究任务。但在交互反馈上面临核心痛点：

1. **常驻内存吞噬 (RAM Bloat)**：传统本地 TTS 通常依赖常驻的 Python FastAPI 或 PyTorch 服务，持续占用 4GB ~ 8GB 统一内存，在 16GB/32GB Mac 上极易引发内存挤压与系统卡顿；
2. **云端 API 高延迟与隐私泄露**：调用商业云端 TTS 增加外部依赖与网络延迟，且代码片段与敏感任务摘要存在外泄风险；
3. **机械死板的播音腔 (Flat Robotic Tone)**：传统零样本克隆 TTS 无论面对“危险权限请求”还是“测试成功”，音调完全一致，缺乏根据任务情境变化的语感与情绪；
4. **终端阻塞与竞态轰炸 (Process Blocking & Audio Collision)**：多个并行 Agent 或连续输出可能造成播放进程重叠轰炸或锁死 Agent 执行流。

**`agent-voice`** 专为 macOS Apple Silicon 深度定制，提供 **0 MB 常驻内存**、**Voice × Style 正交解耦**、**内核级别文件锁非阻塞调度**的工业级本地语音基础设施。

---

### 2. 核心架构与设计原则 (Architecture)

```text
 ┌────────────────────────────────────────────────────────────────────────┐
 │                      AI Agent Fleet (Claude / Codex / Antigravity)     │
 └───────────────────────────────────┬────────────────────────────────────┘
                                     │ CLI Invocation / Event Trigger
                                     ▼
 ┌────────────────────────────────────────────────────────────────────────┐
 │ agent-voice CLI (v4.0.0 Dispatcher)                                    │
 │                                                                        │
 │   ┌───────────────────────────┐    ┌────────────────────────────────┐  │
 │   │  Voice Registry (谁在说)  │ ✖  │ Style Registry (怎么说)        │  │
 │   │  - default (基准通用)     │    │ - neutral   - serious  - warm  │  │
 │   │  - martin-primary (本人)  │    │ - cheerful  - urgent   - calm  │  │
 │   │  - sentinel-calm (哨兵)   │    │ - curious   - concise  - soft  │  │
 │   └─────────────┬─────────────┘    └────────────────┬───────────────┘  │
 │                 │                                   │                  │
 │                 └─────────────────┬─────────────────┘                  │
 │                                   │                                    │
 │           ┌───────────────────────▼──────────────────────────┐         │
 │           │ Event-Driven Router & Parameter Bounding         │         │
 │           │ - Speed (0.75x ~ 1.25x)  Gain (-12dB ~ +3dB)     │         │
 │           │ - Kernel flock Busy-Drop (非阻塞忙碌丢弃)        │         │
 │           └───────────────────────┬──────────────────────────┘         │
 └───────────────────────────────────┼────────────────────────────────────┘
                                     │
                                     ▼
 ┌────────────────────────────────────────────────────────────────────────┐
 │ Underlying Runtime: /opt/homebrew/bin/speech (upstream speech-swift)   │
 │ Model: CosyVoice3-0.5B-MLX-8bit (Apple Silicon Neural Engine / GPU)    │
 │ Execution: 瞬态加载 ➔ 推理 (RTF ~1.3) ➔ afplay 原生 CoreAudio ➔ 立即退出│
 │ 常态驻留内存: 0 MB                                                     │
 └────────────────────────────────────────────────────────────────────────┘
```

#### 关键工程特性
- **Voice × Style 正交控制**：声音生物学特征（Voice Identity）与语气/韵律指令（Delivery Style）完全解耦，同一个参考音频即可演绎 10 种以上情绪。
- **零常驻内存 (Zero Resident RAM)**：无守护进程、无常驻端口。利用 Apple Silicon 统一内存带宽实现秒级冷启动，推理播放后显存与内存立即 100% 归还系统。
- **内核 `flock` 非阻塞互斥 (Lockless Busy Dropping)**：当一段播报正在进行时，新触发的低优先级通知立即静默丢弃，绝不挂起主线程，绝不产生声音混叠叠加。
- **声学门禁自动化校验**：内置 `voice validate`，自动化验证 24kHz 单声道 16-bit PCM 标准、时长窗口（3~10s）、字词级别转录文本匹配度。

---

### 3. 极速安装与部署 (Quickstart)

#### 3.1 前置要求 (Prerequisites)
- **硬件**：Mac 设备配备 Apple Silicon 芯片（M1 / M2 / M3 / M4 系列）
- **操作系统**：macOS 14.0 (Sonoma) 或 macOS 15.0+ (Sequoia)
- **包管理器**：Homebrew (`brew`)

#### 3.2 一键部署
在终端中克隆本仓库并执行部署脚本：

```bash
# 1. 克隆代码仓库
git clone git@github.com:xwbcl123/agent-voice.git ~/Code/agent-voice
cd ~/Code/agent-voice

# 2. 运行一键配置安装脚本
./setup.sh
```

`setup.sh` 脚本将自动完成以下操作：
1. 校验 Apple Silicon (`arm64`) 系统架构；
2. 自动安装或更新底层 Swift 推理工具：`brew install soniqo/speech/speech`；
3. 将配置模板与 10 大风格库发布至 `~/.config/agent-voice/`；
4. 将多音色资产库同步至 `~/.local/share/agent-voice/voices/`；
5. 将 CLI 链接至 `~/.local/bin/agent-voice` 并配置执行权限；
6. 自动执行 `doctor` 运行时探针检测与多音色声学门禁校验；
7. 播放温和问候测试音，验证系统全链路就绪。

> 💡 **提示**：请确保 `~/.local/bin` 已加入 PATH：
> ```bash
> echo 'export PATH="${HOME}/.local/bin:${PATH}"' >> ~/.zshrc && source ~/.zshrc
> ```

---

### 4. 10 大开箱即用交付风格 (Styles Registry)

所有风格配置于 `~/.config/agent-voice/styles.yml`，由 CosyVoice 3.0 的自然语言 Instruct 机制动态驱动：

| 风格 ID (`--style`) | 语气特征 (Tone & Prosody) | 预设语速 | 增益 | 适用场景 (Use Cases) |
| :--- | :--- | :---: | :---: | :--- |
| **`neutral`** ⭐ | 自然、清晰、平衡、适度停顿 | 1.00x | +0 dB | 默认日常工作汇报、通用编码轮次总结 |
| **`warm`** | 温暖、自然、令人安心、轻柔清晰 | 0.95x | +0 dB | 个人反思日记、晚间收尾、轻度提醒 |
| **`cheerful`** | 轻松、友好、带笑意、自然活力 | 1.03x | +0 dB | 任务成功达成、所有测试通过、高光交付 |
| **`calm`** | 平静、沉着、稳定、放慢节奏 | 0.92x | +0 dB | 深度聚焦思考、架构设计、排错分析 |
| **`serious`** | 认真、沉稳、克制、突出关键信息 | 0.96x | +0 dB | 权限提升确认、敏感配置修改、关键门禁 |
| **`urgent`** | 坚定、紧迫、节奏快、清晰不破音 | 1.08x | +1 dB | 运行时异常、构建失败、服务超时、错误警告 |
| **`curious`** | 明亮、好奇、富有探索感 | 1.02x | +0 dB | 调研发现、新模式洞察、知识库探索 |
| **`concise`** | 简洁、直接、极少冗余停顿 | 1.07x | +0 dB | 极短状态同步、CLI 脚本快速确认 |
| **`narrator`** | 温暖、沉稳、叙事感、层次分明 | 0.92x | +0 dB | 播客长篇阅读、长篇复盘报告、系统总结 |
| **`soft`** | 贴近、轻柔、完整发声不漏气 | 0.96x | -1 dB | 深夜免打扰模式、低分贝私密通知 |

---

### 5. CLI 命令与调用参考

```bash
# -------------------------------------------------------------
# 1. 基础合成与风格控制
# -------------------------------------------------------------
# 默认音色与标准风格
agent-voice "任务执行完毕，代码已提交。"

# 指定预设风格 (-s / --style)
agent-voice --style warm "辛苦了，今天的计划已全部闭环。"
agent-voice -s urgent "警告：测试套件发现 2 处破坏性变更！"
agent-voice -s cheerful "所有 15 项集成测试均顺利通过！"

# 指定音色与风格组合 (-v / --voice)
agent-voice -v sentinel-calm -s serious "检测到 Git 强制推送操作，请核验。"
agent-voice -v martin-primary -s curious "在开源库中发现了一种更加优雅的锁机制。"

# 调节语速与回放响度 (--speed: 0.75~1.25, --gain: -12~+3 dB)
agent-voice --speed 1.15 --gain 1.5 "快速提醒：数据同步完成。"

# 自定义任意自然语言指令播报 (--instruct)
agent-voice --instruct "请用兴奋且带有惊喜感的语气说话，语速加快" "发现了一个巨大的性能优化突破点！"

# -------------------------------------------------------------
# 2. 事件语义自动路由 (--event)
# -------------------------------------------------------------
# 触发 permission 事件：自动路由至 sentinel-calm 音色 + serious 风格
agent-voice --event permission "需要执行高危文件删除，请确认。"

# 触发 warning 事件：自动路由至 sentinel-calm 音色 + urgent 风格
agent-voice --event warning "端口 8080 连接超时，正在重试。"

# 触发 task_complete 事件：自动路由至 default 音色 + cheerful 风格
agent-voice --event task_complete "架构演进已全部就绪并归档。"

# 参数模拟仿真 (--dry-run: 不合成音频、不消耗算力，输出解析决策)
agent-voice --event permission --dry-run "请确认继续执行"

# -------------------------------------------------------------
# 3. 注册表管理、资产校验与系统诊断
# -------------------------------------------------------------
# 查看可用音色列表
agent-voice voices

# 查看指定音色详细信息
agent-voice voice show martin-primary

# 校验所有已注册音色的声学标准 (格式、采样率、声道、对齐)
agent-voice voice validate --all

# 查看可用风格列表与自然语言 Prompt
agent-voice styles
agent-voice style show warm

# 运行底层探针与兼容性诊断
agent-voice doctor

# 运行基准性能评测 (RTF、延迟与各风格生成指标)
agent-voice benchmark --voice default --styles neutral,warm,urgent --runs 1
```

---

### 6. 智能体接入指南 (Agent Fleet Integration)

本仓库提供标准化配置模板（位于 `templates/`），可无缝植入主流 AI 终端助手。

#### 6.1 Claude Code 接入 (Stop Hook + Dynamic Summary)
通过 Claude Code 的 Stop Hook 机制，在 Agent 回合结束时自动提取总结并语音播报：

1. **安装提取脚本**（`setup.sh` 已默认部署至 `~/.local/bin/claude-stop-summary.py`）；
2. **在 `~/.claude/settings.json` 中配置 Hook**：
   ```json
   {
     "hooks": {
       "Stop": [
         {
           "hooks": [
             {
               "type": "command",
               "command": "python3 ~/.local/bin/claude-stop-summary.py || true"
             }
           ]
         }
       ]
     }
   }
   ```
3. **在 `~/.claude/CLAUDE.md` 添加提示词规则**：
   ```markdown
   - **Voice Summary Protocol**: 在回复末尾附上一行定制口语化核心总结：
     `<!-- VOICE: 一句话口语化总结，50字以内 -->`。该标签不影响正文，但会被本地 TTS 朗读。
   ```

#### 6.2 OpenAI Codex CLI 接入
包装长耗时任务，执行结束根据退出状态自动以不同风格播报：
```bash
# 复制包装脚本
cp templates/codex-notifier.sh ~/.local/bin/codex-notifier && chmod +x ~/.local/bin/codex-notifier

# 使用包装器执行命令
codex-notifier "单元测试套件" pytest tests/
```

#### 6.3 Antigravity CLI / Cursor Agent 接入
在智能体工作流脚本或集成钩子中调用 `antigravity-hook.sh`：
```bash
~/.local/bin/antigravity-hook.sh "多智能体评审已完成，代码准备合入。" cheerful task_complete
```

#### 6.4 Python SDK 与自定义 Agent 接入
将 `templates/generic-agent-cue.py` 引入你的 Python 项目：
```python
from generic_agent_cue import speak

# 非阻塞异步播报
speak("数据清洗已完成，共处理 10,000 条记录。", style="cheerful")

# 权限警告播报
speak("检测到配置漂移，需要人工介入。", style="urgent", event="warning")
```

---

### 7. 自定义音色采集与录制指南 (Voice Enrollment)

想要添加自己或团队成员的声音？只需在 `voices/<voice-id>/` 放置声学样本：

1. **创建音色目录**：
   ```bash
   mkdir -p ~/.local/share/agent-voice/voices/my-voice
   ```
2. **录制参考音频 (`reference.wav`)**：
   - 寻找安静环境，朗读一段 4 ~ 8 秒的自然中文短句；
   - 格式要求：**24,000 Hz, 单声道 (Mono), 16-bit PCM WAV**；
   - 可使用 ffmpeg 转码：
     ```bash
     ffmpeg -i raw.m4a -ac 1 -ar 24000 -c:a pcm_s16le reference.wav
     ```
3. **编写参考文本 (`reference.txt`)**：
   - 文本内容必须与录音发音 **100% 逐字完全匹配**，不得遗漏或多字。
4. **编写元数据 (`voice.yml`)**：
   ```yaml
   id: my-voice
   name: "My Custom Voice"
   version: "1.0.0"
   status: "approved"
   description: "Custom primary voice for daily coding summaries"
   acoustics:
     sample_rate: 24000
     channels: 1
     sample_format: "s16le"
     duration_seconds: 5.2
   tags: ["custom", "warm", "personal"]
   ```
5. **门禁校验**：
   ```bash
   agent-voice voice validate my-voice
   ```

---

### 8. 性能基准测试 (Performance Benchmarks)

实测环境：**Apple Mac mini (M4, 24GB Unified Memory, macOS 15.3)**

| 指标 (Metric) | 测量值 (Measurement) | 说明 (Note) |
| :--- | :--- | :--- |
| **常态驻留内存 (Resident RAM)** | **0 MB** | 无 Daemon，无后台 Python 进程 |
| **推理峰值显存 (Peak VRAM)** | **~1.1 GB** | 8-bit 量化 CosyVoice 瞬态执行 |
| **冷启动到首包延迟 (TTFB)** | **~1.8 s** | 包含模型权重读取与 MLX 初始化 |
| **实时因子 (Real-Time Factor, RTF)** | **~1.25 ~ 1.35** | 10 秒语音约 13 秒生成完毕 |
| **并发保护行为 (Concurrency)** | **Non-blocking Busy-Drop** | 内核文件锁，冲突时 0 毫秒丢弃 |
| **单元测试覆盖** | **15/15 Passed (0.3s)** | 路由、风格、安全性、边界全覆盖 |

---

## English Overview

**`agent-voice`** is a high-fidelity local text-to-speech (TTS) and instructive prosody control system designed for autonomous AI agent fleets operating on macOS Apple Silicon.

- **0 MB Resident RAM**: Unlike conventional TTS servers running long-lived FastAPI/PyTorch daemons, `agent-voice` operates on transient MLX CLI invocations. Memory is immediately released back to macOS upon playback.
- **Voice × Style Orthogonal Control**: Voice identity (acoustics/timbre) is cleanly separated from delivery style (emotion/prosody). A single reference audio can render neutral notifications, cheerful achievements, calm debugging cues, or urgent error alerts.
- **Zero Process Blocking**: Uses kernel-level `flock` with busy-dropping. If an announcement is already playing, subsequent low-priority notifications are dropped silently rather than blocking agent turn loops.
- **10 Built-in Delivery Styles**: Neutral, warm, cheerful, calm, serious, urgent, curious, concise, narrator, and soft.

---

## 9. 目录结构与资产布局 (Directory Structure)

```
agent-voice/
├── README.md                  # 官方说明文档 (本文档)
├── setup.sh                   # 一键安装与跨机部署脚本
├── agent-voice                # 统一核心 CLI 入口 (Python 3, v4.0.0)
├── claude-stop-summary.py     # Claude Code Stop Hook 动态摘要提取脚本
├── config.yml                 # 默认配置与事件路由表 (Voice × Style 对象映射)
├── styles.yml                 # 10 大标准交付风格注册表
├── reference.wav              # 向后兼容的 baseline 24kHz 参考音频
├── reference.txt              # 向后兼容的 baseline 参考文本
├── .gitignore                 # Git 忽略配置
├── voices/                    # 多音色注册表 (Voice Registry)
│   ├── default/               # 通用基准高保真音色
│   ├── martin-primary/        # Martin 个人定制专属原声音色
│   └── sentinel-calm/         # 权限确认与警报专有哨兵音色
├── templates/                 # Agent Fleet 接入模板与脚本
│   ├── claude-settings.json   # Claude Code settings.json 配置片段
│   ├── claude-prompt.md       # Claude Code 提示词规范
│   ├── codex-notifier.sh      # OpenAI Codex CLI 包装器
│   ├── antigravity-hook.sh    # Antigravity CLI / Cursor 钩子
│   └── generic-agent-cue.py   # 通用 Python Agent 调用辅助模块
├── tests/                     # 单元与回归自动化测试套件
│   ├── test_agent_voice.py    # 15 项单元测试
│   └── run_tests.sh           # 测试运行脚本
└── docs/                      # 集中式架构与规范技术文档库
    ├── README.md              # 文档体系总览与知识拓扑
    ├── 20260913_apple-silicon-speech-agent-handbook_v1.md
    ├── 20260913_cosyvoice3-mlx-macos-deployment-guide_v1.md
    ├── 20260913_agent-voice-v3-functional-evolution-spec_v1.md
    ├── 20260913_agent-voice-reference-voice-recording-guide_v1.md
    └── 20260913_agent-voice-v4-instructive-style-control-spec_v1.md
```

---

## 10. 贡献与许可 (License)

本项目采用 [MIT License](LICENSE) 开源许可。欢迎提交 Issue 或 PR 扩展更多声音风格与智能体适配器。
