# Agent Voice & CosyVoice 技术文档体系 (Knowledge Base)

> 🔗 代码与资产仓库：[agent-voice](../README.md) · 上层架构：Apple Silicon CosyVoice 3.0 MLX TTS 基础设施

本目录收纳 CosyVoice 3.0 MLX 与 Agent Voice 本地语音体系的全套技术调研、底层部署、架构演进 Spec、音色录制指南与 v4.0 韵律风格控制规范，构建了完整的理论 ➔ 部署 ➔ 音色 ➔ 风格 ➔ 实操的知识拓扑链路。

---

## 1. 知识体系逻辑拓扑图 (Knowledge Topology)

```
┌────────────────────────────────────────────────────────────────────────┐
│ 1. 理论与技术全景 (Theory & Engineering Foundations)                   │
│    20260913_apple-silicon-speech-agent-handbook_v1.md                  │
│    状态: 【已实现 (Implemented)】 苹果架构解构、零驻留内存模型与进程隔离 │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ 指导技术选型与 CLI 架构
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ 2. 底层部署与环境基准 (Runtime Deployment & Benchmarks)                │
│    20260913_cosyvoice3-mlx-macos-deployment-guide_v1.md                │
│    状态: 【已实现 (Implemented)】 speech-swift + 8-bit MLX 推理栈实测通过│
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ 提供底层 TTS 引擎与管道支持
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ 3. 多音色演进工程规范 (v3 Evolution Engineering Spec)                  │
│    20260913_agent-voice-v3-functional-evolution-spec_v1.md             │
│    状态: 【已全量实现 (Implemented)】 Voice Registry、事件路由、多音色部署│
└──────────────────┬─────────────────────────────────┬───────────────────┘
                   │                                 │
                   │ 约束声学指标与格式               │ 扩展正交风格控制
                   ▼                                 ▼
┌───────────────────────────────────────┐ ┌──────────────────────────────┐
│ 4. 音色录制与采集指南 (User Guide)   │ │ 5. 韵律风格控制规范 (v4 Spec)│
│    20260913_agent-voice-reference-    │ │    20260913_agent-voice-     │
│      voice-recording-guide_v1.md      │ │      v4-instructive-style-   │
│    状态: 【用户操作参考 (Active)】     │ │      control-spec_v1.md      │
│    指导 Martin 录制原声与样本资产校验 │ │    状态: 【已实现 (Done)】   │
└───────────────────────────────────────┘ └──────────────┬───────────────┘
                                                         │
                                                         ▼
                                          ┌──────────────────────────────┐
                                          │ 6. 生产运行工具与交付库      │
                                          │    ../agent-voice (v4.0.0)   │
                                          │    ../styles.yml (风格注册表)│
                                          │    ../voices/ (音色库)       │
                                          │    ../setup.sh (跨机一键部署)│
                                          │    状态: 【生产可用 (Ready)】│
                                          └──────────────────────────────┘
```

---

## 2. 文档实现状态与职责矩阵 (Implementation Status Matrix)

| 序号 | 核心文档 | 文档定位 | 状态划分 | 现阶段实现范围与职责说明 |
| :--- | :--- | :--- | :--- | :--- |
| **01** | [Apple Silicon 语音智能体手册](./20260913_apple-silicon-speech-agent-handbook_v1.md) | 架构选型手册 | **✅ 已实现**<br>`(Implemented)` | **已落地**：Apple Silicon MLX 架构选型、零常驻内存 (Zero Resident RAM) 单次瞬态执行、内核 `flock` 互斥与进程生命周期安全回收机制已全量在 `agent-voice` 生产包装器中运行。 |
| **02** | [CosyVoice 3 部署实战指南](./20260913_cosyvoice3-mlx-macos-deployment-guide_v1.md) | 运行时部署指南 | **✅ 已实现**<br>`(Implemented)` | **已落地**：`/opt/homebrew/bin/speech` (v0.0.27)、`CosyVoice3-0.5B-MLX-8bit` 模型加载、24kHz 单声道参考样本与 `afplay` 播放管道已全链路打通并经高阶评审验收（退出码 0，RTF 1.34）。 |
| **03** | [Agent Voice 功能演进 Spec](./20260913_agent-voice-v3-functional-evolution-spec_v1.md) | 工程实现规范 | **✅ 已全量实现**<br>`(Implemented)` | **已全量落地**：多音色注册表（`voices/<id>/`）、`voice.yml` Schema、全局事件路由（`--event` & `config.yml`）、全套 CLI 子命令（`voices`/`validate`/`normalize`/`audition`）及单元测试就绪。Martin 专属音色 (`martin-primary`) 与哨兵音色 (`sentinel-calm`) 均已上线。 |
| **04** | [Reference Voice 录制采集指南](./20260913_agent-voice-reference-voice-recording-guide_v1.md) | 用户操作参考 | **📖 用户操作参考**<br>`(User Reference)` | **长期操作标准**：非代码类规范。为录制个人原声、从 ChatGPT/ElevenLabs 获取 AI 音色切片提供标准流程。详述 4~8s 干净单人句、24kHz Mono 16-bit PCM 转码及文本 100% 字对字对齐铁律。 |
| **05** | [Agent Voice v4 风格控制 Spec](./20260913_agent-voice-v4-instructive-style-control-spec_v1.md) | 进阶工程规范 | **✅ 已实现**<br>`(Implemented)` | **已全量落地**：引入 CosyVoice instruct2 风格控制、`styles.yml` 10 大标准风格注册表、Voice × Style 正交路由、`doctor` 运行时探针、`benchmark` 性能套件、`--speed` 语速与 `--gain` 增益解耦控制，15/15 测试全通。 |

---

## 3. 五阶逻辑演化与推进路径

### 第一阶：架构解构 (Theory)
- **核心文档**：[Apple Silicon 语音智能体手册](./20260913_apple-silicon-speech-agent-handbook_v1.md)
- **逻辑价值**：阐明了为什么在 16GB/32GB Unified Memory 机器上不能跑常驻 Daemon，论证了 CLI 按需瞬态执行的合理性，为整个本地语音系统确立了“低内存、不阻塞、严密互斥”的底层设计原则。

### 第二阶：环境筑基 (Runtime)
- **核心文档**：[CosyVoice 3 部署实战指南](./20260913_cosyvoice3-mlx-macos-deployment-guide_v1.md)
- **逻辑价值**：排除了虚构的 Python FastAPI 路由假设，确立了基于 upstream `speech-swift` 官方二进制的正确部署路径与量化选型，为多智能体提供了稳定离线的 TTS 推理基石。

### 第三阶：多音色演进 (Multi-Voice Identity)
- **核心文档**：[Agent Voice 功能演进 Spec](./20260913_agent-voice-v3-functional-evolution-spec_v1.md)
- **逻辑价值**：打破了“单一声音播报所有事件”的局限，提出了“事件语义 ➔ 声音身份 ➔ TTS 引擎”的三层解耦架构，建立了 `voices/` 注册表与资产门禁校验体系。

### 第四阶：声音定制与入库 (Voice Assets)
- **核心文档**：[Reference Voice 录制采集指南](./20260913_agent-voice-reference-voice-recording-guide_v1.md)
- **逻辑价值**：连接人类真实声音与模型的关键纽带。指导采集并交付了专属音色 (`martin-primary`) 与哨兵音色 (`sentinel-calm`)。

### 第五阶：风格解耦与自然韵律 (Instructive Prosody Control)
- **核心文档**：[Agent Voice v4 风格控制 Spec](./20260913_agent-voice-v4-instructive-style-control-spec_v1.md)
- **逻辑价值**：解耦“谁在说 (Voice Identity)”与“怎么说 (Delivery Style)”。无需为同一音色克隆不同情绪模型，通过 CosyVoice instruct2 实现自然语言语调控制，搭配语速和播放增益解耦调节，赋能全量智能体 Fleet。

---

## 4. 关键代码与资产导航

- **统一入口 CLI**：[`../agent-voice`](../agent-voice) (v4.0.0, Python 3)
- **风格注册表**：[`../styles.yml`](../styles.yml)（包含 `neutral`, `warm`, `cheerful`, `calm`, `serious`, `urgent`, `curious`, `concise`, `narrator`, `soft`）
- **多音色注册表**：[`../voices/`](../voices/)（包含 `default`, `martin-primary`, `sentinel-calm`）
- **全局路由配置**：[`../config.yml`](../config.yml)
- **自动化测试套件**：[`../tests/test_agent_voice.py`](../tests/test_agent_voice.py) (15 项单元测试)
- **跨机一键安装脚本**：[`../setup.sh`](../setup.sh)
