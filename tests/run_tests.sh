#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "=== 运行 agent-voice v4.0 单元与回归测试套件 ==="
python3 "${SCRIPT_DIR}/test_agent_voice.py" -v
echo ""
echo "=== 运行 CLI 核心命令回归检查 ==="
"${SCRIPT_DIR}/../agent-voice" voices
"${SCRIPT_DIR}/../agent-voice" voice show default
"${SCRIPT_DIR}/../agent-voice" voice validate --all
"${SCRIPT_DIR}/../agent-voice" styles
"${SCRIPT_DIR}/../agent-voice" style show warm
"${SCRIPT_DIR}/../agent-voice" doctor
"${SCRIPT_DIR}/../agent-voice" --voice martin-primary --style warm --dry-run "回归测试文本"
echo "🎉 所有测试全部通过！"
