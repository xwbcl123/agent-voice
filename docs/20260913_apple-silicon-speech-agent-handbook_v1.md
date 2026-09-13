---
title: "Apple Silicon 原生语音引擎与 Agentic 自动化工程实践手册"
jd_id: "41.10"
type: "note"
doc_role: "architecture_handbook"
status: "active"
implementation_status: "implemented"
stage_summary: "已实现：Apple Silicon MLX 架构选型、零驻留内存 (Zero Resident RAM) 与 flock 互斥保护已全链路落地至 agent-voice CLI 生产环境"
created: "2026-09-13 00:03"
updated: "2026-09-13 22:12"
tags:
  - "topic/apple-silicon"
  - "topic/speech"
  - "topic/asr"
  - "topic/tts"
  - "topic/mcp"
  - "topic/claude-code"
  - "topic/codex"
  - "topic/ai-agents"
parent: "[[README|docs/README]]"
package_root: "[[../README|agent-voice 交付件仓库]]"
system_doc: "[[00-09_System-Meta/01.02_system-docs-lib/tool-cosyvoice-tts|tool-cosyvoice-tts]]"
links:
  - "[[20260913_cosyvoice3-mlx-macos-deployment-guide_v1|下一步：CosyVoice 3.0 MLX 部署指南]]"
  - "[[20260913_agent-voice-v3-functional-evolution-spec_v1|演进规范：Agent Voice v3.0 功能演进 Spec]]"
  - "[[20260913_agent-voice-reference-voice-recording-guide_v1|操作参考：Reference Voice 录制与采集指南]]"
---

# Apple Silicon 原生语音引擎与 Agentic 自动化工程实践手册

> [!NOTE] 知识体系关联与实现状态
> - **文档定位**：技术选型与架构手册 (Architecture Handbook)
> - **实现状态**：**已实现 (Implemented / Active)**。文中论证的 Apple Silicon MLX 零常驻内存选型、Swift 二进制桥接与非阻塞文件锁机制已全部在 `agent-voice` (v3.0.0) 生产包装器中落地。
> - **知识链路**：[[README|docs/README]] ➔ **架构手册 (本文)** ➔ 指导 [[20260913_cosyvoice3-mlx-macos-deployment-guide_v1|CosyVoice 3 部署实战]] ➔ 驱动 [[20260913_agent-voice-v3-functional-evolution-spec_v1|v3 功能演进 Spec]]。

> **硬件基准**：Apple Silicon（M 系列架构，如 M5 / 32GB 统一内存）  
> **核心目标**：解构 macOS 原生与开源语音能力边界，搭建零云端依赖、零隐私泄露、轻量且高响应的本地语音回路，并深度集成至 Claude Code / Codex / Cursor 等 AI Coding Agent 工作流中。

---

## 1. 概念澄清与技术选型辨析

在评估端侧语音处理方案前，需理清核心工具的底层驱动与运行拓扑：

| 方案                | 分类     | 驱动后端                                                 | 网络状态           | 隐私合规        | 适用场景与局限                                        |
| :---------------- | :----- | :--------------------------------------------------- | :------------- | :---------- | :--------------------------------------------- |
| **`edge-tts`**    | 云端包装器  | 微软 Azure Neural TTS 逆向接口 (Edge Read Aloud WebSocket) | **强依赖联网**      | ❌ 文本发送至微软云端 | 临时批量生成有声读物；有 403 限流与被封禁风险。                     |
| **`Kokoro-ONNX`** | 本地 TTS | ONNX Runtime (CPU/ANE/CoreML)                        | **纯离线**        | ✔️ 100% 本地  | 极速响应（82M 参数）、内存占用极低 (<500MB)、英文极佳，中文尚可，缺乏声音克隆。 |
| **`CosyVoice`**   | 本地 TTS | PyTorch MPS / MLX (阿里开源)                             | **纯离线**        | ✔️ 100% 本地  | 3~5秒极速声音克隆、中文表现力顶级；M 系列芯片统一内存推荐跑 MLX/MPS 导出版。  |
| **macOS `say`**   | 原生 TTS | macOS 内置 `AVFoundation` / `NSSpeechSynthesizer`      | **纯离线**        | ✔️ 100% 本地  | 系统预装、0 依赖、极低资源开销；适合系统级通知广播。                    |
| **macOS `hear`**  | 原生 ASR | macOS 内置 `Speech.framework` (SFSpeechRecognizer)     | **纯离线** (`-d`) | ✔️ 100% 本地  | 专为对称 `say` 开发的 CLI；调用苹果神经引擎（ANE）进行离线听写。        |

---

## 2. Apple 原生语音“双子星”：`say` 与 `hear`

macOS 体系下天然存在一组满足 Unix 管道哲学（Text Stream）的对称组合：
       [ 文本流 / Text ]
      ▲                │
      │ (hear)         ▼ (say)
 [ 麦克风/音频 ]      [ 扬声器/声音 ]

### 2.1 文本转语音：`say` (系统内置)
- **核心命令示例**：
  
```bash
  # 查验系统已安装的声音资源
  say -v '?' | grep zh_CN
  
  # 基础中文播报（推荐系统自带的 Ting-Ting，语速通常建议 180-200）
  say -v Ting-Ting -r 190 "任务已完成，所有测试均已通过。"
  
  # 导出为高质量独立音频文件
  say -v Ting-Ting "音频内容" -o output.m4a
```

### 2.2 语音识别：`hear` (开源生态补充)

macOS 拥有强大的底层语音识别引擎（即系统按快捷键呼出的“听写”能力），但并未提供开箱即用的 CLI 工具。开源项目 **`hear`**（by sveinbjornt）补齐了这一闭环。

- **安装**：

  Bash

```
  brew tap sveinbjornt/hear [https://github.com/sveinbjornt/hear](https://github.com/sveinbjornt/hear)
  brew install sveinbjornt/hear/hear
```

- **核心命令示例**：

  Bash

  ```
  # 实时拾取麦克风并在终端输出转录文字（指定中文）
  hear -l zh-CN -m

  # 强制本地 Apple Neural Engine 离线转录（-d），处理音频文件
  hear -d -l zh-CN -i ./input.m4a > result.txt
  ```

- **管道闭环体验**（“鹦鹉学舌”极简链路）：

  Bash

  ```
  hear -l zh-CN | say -v Ting-Ting
  ```

## 3. 将 ASR 包装为 Agent 的 Model Context Protocol (MCP)

若需让 Claude Desktop、Cursor 或具备 Agentic 特性的工作流调用 Apple 原生语音识别，可使用 `FastMCP` 将 `hear` 封装为标准协议服务。

### 3.1 Python 实现 (`apple_speech_mcp.py`)


  ```Python
import os
import subprocess
from fastmcp import FastMCP

mcp = FastMCP("Apple-Native-ASR")

@mcp.tool()
def transcribe_local_audio(audio_path: str, lang: str = "zh-CN") -> str:
    """
    使用 Apple Silicon 原生 Speech Engine (ANE 离线模式) 转录本地音频文件。
    :param audio_path: 音频文件绝对路径 (支持 wav, m4a, mp3 等)
    :param lang: 识别语言代码 (默认 'zh-CN', 可选 'en-US')
    :return: 转录后的纯文本字符串
    """
    if not os.path.exists(audio_path):
        return f"错误: 目标音频文件不存在: {audio_path}"

    try:
        cmd = ["hear", "-d", "-l", lang, "-i", audio_path]
        proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return proc.stdout.strip()
    except subprocess.CalledProcessError as err:
        return f"ASR 识别执行异常: {err.stderr}"
    except FileNotFoundError:
        return "环境错误: 未检测到 hear 命令，请先运行 `brew install sveinbjornt/hear/hear`。"

if __name__ == "__main__":
    mcp.run()
  ```

### 3.2 客户端配置 (`claude_desktop_config.json`)

```JSON
{
  "mcpServers": {
    "apple-native-asr": {
      "command": "python3",
      "args": ["/Users/YOUR_USER/.local/bin/apple_speech_mcp.py"]
    }
  }
}
```

## 4. 深度集成：AI Coding Agent (Claude Code / Codex) 语音生命周期播报

长耗时任务（如大型项目重构、自动化跑测试、漏洞扫描）时，开发者通常会切换到其他窗口。通过为 Agent 挂载生命周期 **Hook**，可实现**免视线驻留、任务完毕语音主动交付**。

### 4.1 通用异步通知脚本 (`~/.local/bin/agent_notify.sh`)

该脚本具备文本去 Markdown 标记、截断保底、系统音效提示与非阻塞运行特性。


```Bash
#!/usr/bin/env bash
# ==============================================================================
# Agent 状态语音播报脚本
# 用法: ./agent_notify.sh [状态: success|failed|waiting] [播报摘要文本]
# ==============================================================================

STATUS="${1:-success}"
RAW_MSG="${2:-Claude Code 任务已完成，请检查结果。}"

# 1. 过滤 Markdown 字符 (*, #, `, _, >, 代码块标记)，防止朗读念出标点符号
CLEAN_MSG=$(echo "$RAW_MSG" | sed -E 's/[*#`_~>]//g' | tr '\n' ' ' | sed -E 's/ +/ /g')

# 2. 截取前 100 字符，避免朗读冗长正文
SPEECH_TEXT=$(echo "$CLEAN_MSG" | cut -c 1-100)

# 3. 伴随音效设计与语音朗读
case "$STATUS" in
  "waiting")
    # 遇到权限申请或需要交互输入时
    afplay /System/Library/Sounds/Glass.aiff &
    say -v Ting-Ting -r 190 "请注意，终端需要您的确认。" &
    ;;
  "failed")
    afplay /System/Library/Sounds/Basso.aiff &
    say -v Ting-Ting -r 190 "警告，执行遇到异常终止。" &
    ;;
  *)
    # 正常完成
    afplay /System/Library/Sounds/Hero.aiff &
    say -v Ting-Ting -r 190 "$SPEECH_TEXT" &
    ;;
esac
```

赋予执行权限：

```Bash
chmod +x ~/.local/bin/agent_notify.sh
```

### 4.2 接入方式 A：Claude Code 官方原生 Hooks

Claude Code 拥有完整的生命周期事件体系（如 `Stop`, `SubagentStop`, `Notification` 等）。在项目根目录或全局 `~/.claude/settings.json` 中配置：
          

```JSON
{
  "hooks": {
    "Stop": [
      {
        "matcher": ".*",
        "hooks": [
          {
            "type": "command",
            "command": "~/.local/bin/agent_notify.sh success \"Claude 任务已结束，代码已完成修改。\""
          }
        ]
      }
    ],
    "Notification": [
      {
        "matcher": ".*",
        "hooks": [
          {
            "type": "command",
            "command": "~/.local/bin/agent_notify.sh waiting"
          }
        ]
      }
    ]
  }
}
```

### 4.3 接入方式 B：Codex / 命令行 Agent 终端 Wrapper

针对没有内置丰富 Hook 或跨多款 CLI Agent（如 Codex、Gemini CLI）的场景，采用 Shell 进程监听 Wrapper 是最干净的零侵入方案。

在 `~/.zshrc` 或 `~/.bashrc` 中增加封装函数：

```Bash
# 封装自定义终端 Agent
function codex-watch() {
    echo "🤖 启动 Codex 任务监听中..."
    codex "$@"
    local EXIT_CODE=$?

    if [ $EXIT_CODE -eq 0 ]; then
        ~/.local/bin/agent_notify.sh success "Codex 执行完毕，终端已就绪。"
    else
        ~/.local/bin/agent_notify.sh failed "Codex 异常退出，退出码 $EXIT_CODE。"
    fi
    return $EXIT_CODE
}
```

### 4.4 进阶技巧：动态广播提取（Dynamic Broadcast）

在项目的 `.clauderc`、`CLAUDE.md` 或全局指令中加入提示词规范：

> **Prompt 附加约定**：
>
> "在所有工作流最终执行结束前，在回答的最后一行单独输出格式为 `[VOICE]: <15字以内的口头完成简述>` 的一句话。"

编写解析脚本过滤最后一行的 `[VOICE]:` 内容并直接传入 `say`，即可实现让 Agent 用自然口语告诉你它刚才具体完成了什么工作（例如：*“已修复三个类型报错，所有单元测试通过”*）。

```
<ElicitationsGroup message="如需进一步优化或实操测试，可从以下方向继续：">
  <Elicitation label="调试 Claude Code Hook 接收 stdin JSON 数据的解析脚本" query="请给出一个能够解析 Claude Code Hook 传入的 stdin JSON 数据并提取输出文本的 Python/Bash 脚本。"/>
  <Elicitation label="配置 macOS 快捷指令实现一键全局语音输入与转录" query="如何利用 macOS 快捷指令（Shortcuts）结合 hear 命令实现一个全局呼出的语音输入听写挂件？"/>
</ElicitationsGroup>
```