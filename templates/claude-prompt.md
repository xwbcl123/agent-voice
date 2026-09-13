<!-- Add this to ~/.claude/CLAUDE.md to instruct Claude Code to append voice summary tags -->
- **Voice Summary Protocol**: 在回复末尾（最后一行），附上一行专门为本地 TTS 语音播报定制的简明核心总结标签：`<!-- VOICE: <一句话口语化总结，50字以内> -->`。该标签为 HTML 注释，不影响正文排版，但会被 Stop Hook 优先朗读。
