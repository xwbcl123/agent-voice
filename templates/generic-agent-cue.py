#!/usr/bin/env python3
"""Generic Agent Voice Cue Helper (v4.0)
Provides a clean, non-blocking Python function for any Python-based agent,
script, or background job to trigger local CosyVoice TTS notifications
with optional voice identity, delivery style, and event-driven routing.
"""
from __future__ import annotations
import os
from pathlib import Path
import subprocess
import sys

AGENT_VOICE_BIN = Path.home() / ".local/bin/agent-voice"


def speak(
    text: str,
    style: str | None = None,
    voice: str | None = None,
    event: str | None = None,
    speed: float | None = None,
    gain: float | None = None,
    non_blocking: bool = True,
) -> bool:
    """Trigger agent-voice notification.

    Args:
        text: Speech text (recommended < 50 Chinese chars).
        style: Instruction style (e.g., 'neutral', 'warm', 'cheerful', 'urgent').
        voice: Voice identity (e.g., 'default', 'martin-primary', 'sentinel-calm').
        event: Event semantic type (e.g., 'task_complete', 'warning', 'permission').
        speed: Speed multiplier (0.75x ~ 1.25x).
        gain: Gain adjustment in dB (-12dB ~ +3dB).
        non_blocking: If True, dispatches detached background process.

    Returns:
        bool: True if dispatched, False if binary not found or empty text.
    """
    cmd = []
    if AGENT_VOICE_BIN.is_file() and os.access(AGENT_VOICE_BIN, os.X_OK):
        cmd.append(str(AGENT_VOICE_BIN))
    else:
        # Fallback to PATH lookup
        import shutil
        found = shutil.which("agent-voice")
        if found:
            cmd.append(found)
        else:
            return False

    clean_text = text.strip()
    if not clean_text:
        return False

    if event:
        cmd.extend(["--event", event])
    if voice:
        cmd.extend(["--voice", voice])
    if style:
        cmd.extend(["--style", style])
    if speed is not None:
        cmd.extend(["--speed", str(speed)])
    if gain is not None:
        cmd.extend(["--gain", str(gain)])

    cmd.append(clean_text)

    if non_blocking:
        subprocess.Popen(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
            start_new_session=True,
            shell=False,
        )
    else:
        subprocess.run(
            cmd,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    return True


if __name__ == "__main__":
    msg = sys.argv[1] if len(sys.argv) > 1 else "测试智能体语音通知。"
    success = speak(msg, style="warm", non_blocking=False)
    sys.exit(0 if success else 1)
