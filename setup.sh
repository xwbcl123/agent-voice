#!/usr/bin/env bash
# ==============================================================================
# agent-voice v4.0 一键配置与跨设备同步安装脚本 (macOS Apple Silicon)
# 适用于: Mac mini / MacBook Pro / 其他 Apple Silicon Mac
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DEST="${HOME}/.local/bin"
SHARE_DEST="${HOME}/.local/share/agent-voice"
CONFIG_DEST="${HOME}/.config/agent-voice"

echo "=== [1/6] 检查系统架构与环境 ==="
if [[ "$(uname -s)" != "Darwin" ]]; then
    echo "❌ 错误: 本系统不是 macOS。CosyVoice 3.0 MLX 仅支持 macOS Apple Silicon。" >&2
    exit 1
fi

ARCH="$(uname -m)"
if [[ "${ARCH}" != "arm64" ]]; then
    echo "❌ 错误: 当前架构为 ${ARCH}，CosyVoice MLX 依赖 Apple Silicon (arm64)。" >&2
    exit 1
fi
echo "✅ 架构检查通过: Apple Silicon (${ARCH})"

echo "=== [2/6] 检查 Homebrew 与 speech 二进制 ==="
if ! command -v /opt/homebrew/bin/speech &>/dev/null; then
    echo "⚠️ 未在 /opt/homebrew/bin/speech 找到 speech 工具。"
    echo "正在尝试检查 Homebrew..."
    if command -v brew &>/dev/null; then
        echo "正在执行: brew install soniqo/speech/speech"
        brew install soniqo/speech/speech
    else
        echo "❌ 错误: 请先安装 Homebrew 或手动安装 speech: https://github.com/soniqo/speech-swift" >&2
        exit 1
    fi
fi
echo "✅ speech 底层二进制已就绪: $(/opt/homebrew/bin/speech --version 2>/dev/null || echo 'OK')"

echo "=== [3/6] 部署配置文件、风格库与多音色注册表 ==="
mkdir -p "${CONFIG_DEST}"
if [[ ! -f "${CONFIG_DEST}/config.yml" ]]; then
    cp -f "${SCRIPT_DIR}/config.yml" "${CONFIG_DEST}/config.yml"
    echo "✅ 默认配置文件已生成: ${CONFIG_DEST}/config.yml"
else
    echo "ℹ️ 保留现有配置文件: ${CONFIG_DEST}/config.yml"
fi

if [[ ! -f "${CONFIG_DEST}/styles.yml" ]]; then
    cp -f "${SCRIPT_DIR}/styles.yml" "${CONFIG_DEST}/styles.yml"
    echo "✅ 默认风格注册表已生成: ${CONFIG_DEST}/styles.yml"
else
    echo "ℹ️ 保留现有风格注册表: ${CONFIG_DEST}/styles.yml"
fi

mkdir -p "${SHARE_DEST}/voices"
cp -Rf "${SCRIPT_DIR}/voices/"* "${SHARE_DEST}/voices/"
cp -f "${SCRIPT_DIR}/reference.wav" "${SHARE_DEST}/reference.wav" 2>/dev/null || true
cp -f "${SCRIPT_DIR}/reference.txt" "${SHARE_DEST}/reference.txt" 2>/dev/null || true
echo "✅ 多音色注册表与参考音频已部署至: ${SHARE_DEST}/voices/"

echo "=== [4/6] 部署 CLI 工具并赋予执行权限 ==="
mkdir -p "${BIN_DEST}"
cp -f "${SCRIPT_DIR}/agent-voice" "${BIN_DEST}/agent-voice"
cp -f "${SCRIPT_DIR}/claude-stop-summary.py" "${BIN_DEST}/claude-stop-summary.py"
chmod +x "${BIN_DEST}/agent-voice" "${BIN_DEST}/claude-stop-summary.py"
echo "✅ CLI 工具已部署至: ${BIN_DEST}/"

# 确保 ~/.local/bin 在 PATH 中
if [[ ":${PATH}:" != *":${BIN_DEST}:"* ]]; then
    echo "ℹ️ 提示: ${BIN_DEST} 不在当前 PATH 中，建议将其加入 ~/.zshrc:"
    echo "    export PATH=\"\${HOME}/.local/bin:\${PATH}\""
fi

echo "=== [5/6] 运行时能力探测与声学门禁校验 ==="
"${BIN_DEST}/agent-voice" doctor
"${BIN_DEST}/agent-voice" voice validate --all || true

echo "=== [6/6] 语音合成可用性验证 ==="
if [[ "${1:-}" != "--skip-test" ]]; then
    echo "正在播放就绪测试音频 (风格: warm)..."
    "${BIN_DEST}/agent-voice" --style warm "智能体语音基础设施 v4.0 升级配置完成。" || true
else
    echo "已跳过就绪测试。"
fi

echo ""
echo "🎉 安装与升级完成！当前可用音色列表:"
"${BIN_DEST}/agent-voice" voices
echo ""
echo "当前可用风格列表:"
"${BIN_DEST}/agent-voice" styles
echo ""
echo "=============================================================================="
