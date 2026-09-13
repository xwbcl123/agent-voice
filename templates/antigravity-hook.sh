#!/usr/bin/env bash
# ==============================================================================
# Antigravity CLI / Cursor / 通用终端 Agent 语音提示钩子 (v4.0)
# 用法:
#   antigravity-hook.sh "多智能体评审已结束，交付已批准。" [style] [event]
# 示例:
#   antigravity-hook.sh "构建完成" cheerful task_complete
# ==============================================================================
set -euo pipefail

MESSAGE="${1:-Antigravity 任务已执行完毕。}"
STYLE="${2:-neutral}"
EVENT="${3:-task_complete}"

AGENT_VOICE_BIN="${HOME}/.local/bin/agent-voice"

if [[ -x "${AGENT_VOICE_BIN}" ]]; then
    nohup "${AGENT_VOICE_BIN}" --style "${STYLE}" --event "${EVENT}" "${MESSAGE}" >/dev/null 2>&1 &
elif command -v agent-voice &>/dev/null; then
    nohup agent-voice --style "${STYLE}" --event "${EVENT}" "${MESSAGE}" >/dev/null 2>&1 &
else
    echo "⚠️ agent-voice 未安装或不可执行" >&2
fi
