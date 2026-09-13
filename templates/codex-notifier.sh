#!/usr/bin/env bash
# ==============================================================================
# Codex CLI / 长耗时任务通用完成通知脚本 (v4.0)
# 用法:
#   ./templates/codex-notifier.sh "任务描述" 命令参数...
# 示例:
#   ./templates/codex-notifier.sh "代码重构与验证" pytest tests/
# ==============================================================================
set -u

TASK_NAME="${1:-任务}"
shift || true

START_TIME=$(date +%s)
echo "[Codex Runner] 开始执行: ${TASK_NAME}..."

# 执行传入的命令
"$@"
EXIT_CODE=$?

DURATION=$(( $(date +%s) - START_TIME ))

if [[ ${EXIT_CODE} -eq 0 ]]; then
    MSG="Codex ${TASK_NAME}执行成功，耗时${DURATION}秒。"
    EVENT_FLAGS=("--event" "task_complete" "--style" "cheerful")
else
    MSG="警告：Codex ${TASK_NAME}执行失败，退出码为${EXIT_CODE}。"
    EVENT_FLAGS=("--event" "warning" "--style" "urgent")
fi

# 异步触发语音提醒，绝不阻塞主脚本退出
if command -v agent-voice &>/dev/null; then
    agent-voice "${EVENT_FLAGS[@]}" "${MSG}" &
elif [[ -x "${HOME}/.local/bin/agent-voice" ]]; then
    "${HOME}/.local/bin/agent-voice" "${EVENT_FLAGS[@]}" "${MSG}" &
fi

exit ${EXIT_CODE}
