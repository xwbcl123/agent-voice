#!/usr/bin/env python3
"""Claude Code Stop Hook Dynamic Voice Summary Extractor (v1.7.0)
Architecture: Bounded Stream Assembly -> CommonMark Fence & Quote Filtering -> Strict Line Tags -> Multi-Line Section Summary -> Polite Closing Filter -> Isolated Detached Async Dispatch
"""
from __future__ import annotations
import fcntl
import json
import os
from pathlib import Path
import re
import select
import subprocess
import sys
import time

AGENT_VOICE_BIN = "/Users/martin/.local/bin/agent-voice"
LOG_FILE = Path("/tmp/claude-stop-summary.log")
DEFAULT_FALLBACK = "Claude 本轮处理结束。"
MAX_INPUT_BYTES = 256 * 1024
MAX_SUMMARY_CHARS = 55

POLITE_CLOSINGS = re.compile(
    r"^(?:您还需要|需要查询|请问还有|如果有任何|如果需要|随时告诉我|请随时|是否需要|还需要|需要我|请问需要).*?[？?]?$",
    re.IGNORECASE
)

def log_debug(msg: str) -> None:
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
    except Exception:
        pass

def strip_control_and_ansi(text: str) -> str:
    text = re.sub(r"\x1b\].*?(?:\x07|\x1b\\)", " ", text) # OSC
    text = re.sub(r"\x1b\[[0-9;?]*[a-zA-Z]", " ", text)   # CSI
    text = re.sub(r"\x1b.", " ", text)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", " ", text)
    return text

def strip_fences_and_quotes(raw: str) -> str:
    lines = raw.splitlines()
    out = []
    fence_char = None
    fence_len = 0
    for line in lines:
        stripped = line.strip()
        if fence_char is None:
            m = re.match(r"^(`{3,}|~{3,})(.*)$", stripped)
            if m:
                fence_char = m.group(1)[0]
                fence_len = len(m.group(1))
                continue
        else:
            # CommonMark: closing fence MUST consist only of the fence character and whitespace
            m = re.match(r"^(`{3,}|~{3,})\s*$", stripped)
            if m and m.group(1)[0] == fence_char and len(m.group(1)) >= fence_len:
                fence_char = None
                fence_len = 0
                continue
            # Still inside code block
            continue

        # Skip blockquote lines
        if stripped.startswith(">"):
            continue

        out.append(line)
    return "\n".join(out)

def extract_tag_content(line: str) -> str | None:
    line = line.strip()
    # 1. HTML comment format: <!-- VOICE: content -->
    m_html = re.match(r"^<!--\s*VOICE:\s*(.*?)\s*-->$", line, re.IGNORECASE)
    if m_html:
        content = m_html.group(1)
        if "-->" not in content and "<!--" not in content:
            return content
        return None

    # 2. XML tag format: <voice>content</voice>
    m_xml = re.match(r"^<voice>\s*(.*?)\s*</voice>$", line, re.IGNORECASE)
    if m_xml:
        content = m_xml.group(1)
        if "<" not in content and ">" not in content:
            return content
        return None

    # 3. Bracket format: [VOICE: content]
    m_brk = re.match(r"^\[VOICE:\s*(.*?)\s*\]$", line, re.IGNORECASE)
    if m_brk:
        content = m_brk.group(1)
        if "[" not in content and "]" not in content:
            return content
        return None

    # 4. Prefix format: [VOICE]: content
    m_pref = re.match(r"^\[VOICE\]:\s*(.*?)$", line, re.IGNORECASE)
    if m_pref:
        return m_pref.group(1)

    return None

def sanitize_and_bound_speech(text: str, max_chars: int = MAX_SUMMARY_CHARS) -> str:
    text = strip_control_and_ansi(text)
    text = re.sub(r"[\U00010000-\U0010ffff]", " ", text) # Strip emojis
    text = re.sub(r"https?://\S+", " ", text)
    # Match real absolute/relative path preceded by space or start of line
    text = re.sub(r"(?:\b[a-zA-Z]:[\\/]|(?<=\s)/(?:[a-zA-Z0-9._-]+/)+[a-zA-Z0-9._-]*)", " ", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"[#*_~|]", " ", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"^[0-9]+[.)、\s]+", "", text) # Strip leading list bullet numbers
    text = re.sub(r"^[-*•]\s+", "", text)         # Strip leading bullet dash
    text = re.sub(r"\s+", " ", text).strip()

    if len(text) <= max_chars:
        return text

    # Oversize candidate: cannot safely prove semantic preservation,
    # strictly return empty string to trigger fallback
    return ""

def extract_section_summary(lines: list[str]) -> str | None:
    heading_re = re.compile(
        r"^(?:#+\s*|[*_]{2}\s*).*?(?:最终结论|核心结论|结论|Summary|诊断结论|总结)",
        re.IGNORECASE
    )
    for idx, line in enumerate(lines):
        if heading_re.match(line):
            # Check if content is on the same line: e.g. "## 结论：已部署完成"
            inline_m = re.match(r"^(?:#+\s*|[*_]{2}\s*).*?(?:最终结论|核心结论|结论|Summary|诊断结论|总结)[：:\s]+(.+)$", line, re.IGNORECASE)
            if inline_m:
                content = inline_m.group(1).strip()
                if content and not content.startswith("("):
                    cand = sanitize_and_bound_speech(content)
                    if len(cand) >= 4:
                        return cand

            # Look at candidate lines right under this heading
            for sub_line in lines[idx + 1:]:
                if re.match(r"^#+\s+", sub_line):
                    break
                if re.match(r"^[-*=_]{3,}$", sub_line):
                    continue
                cand = sanitize_and_bound_speech(sub_line)
                if len(cand) >= 4:
                    return cand
    return None

def extract_summary(raw_text: str) -> str:
    if not raw_text or not raw_text.strip():
        log_debug("extract_summary: empty raw_text -> fallback")
        return DEFAULT_FALLBACK
    cleaned = strip_fences_and_quotes(raw_text).strip()
    if not cleaned:
        log_debug("extract_summary: empty after cleaning -> fallback")
        return DEFAULT_FALLBACK
    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    if not lines:
        log_debug("extract_summary: no lines -> fallback")
        return DEFAULT_FALLBACK

    # 1. Trailing explicit tag: must be strictly on the last non-empty line
    last_line = lines[-1]
    tag_content = extract_tag_content(last_line)
    if tag_content is not None:
        cand = sanitize_and_bound_speech(tag_content)
        if len(cand) >= 4:
            log_debug(f"Strategy: explicit_tag -> {cand!r}")
            return cand
        log_debug("Strategy: explicit_tag failed bounds -> fallback")
        return DEFAULT_FALLBACK

    # 2. Section matching (最终结论, 核心结论, Summary, 总结, etc.)
    sec_cand = extract_section_summary(lines)
    if sec_cand:
        log_debug(f"Strategy: section_heading -> {sec_cand!r}")
        return sec_cand

    # 3. Last substantive line (skipping closing polite questions)
    for line in reversed(lines):
        if re.match(r"^[-*=_]{3,}$", line):
            continue
        if POLITE_CLOSINGS.match(line):
            continue
        cand = sanitize_and_bound_speech(line)
        if len(cand) >= 6:
            log_debug(f"Strategy: substantive_line -> {cand!r}")
            return cand
        log_debug("Strategy: substantive_line oversize -> fallback")
        return DEFAULT_FALLBACK

    log_debug("Strategy: default_fallback")
    return DEFAULT_FALLBACK

def read_last_assistant_message(input_data: dict) -> str:
    last_msg = input_data.get("last_assistant_message")
    if not last_msg:
        return ""
    if isinstance(last_msg, str):
        return last_msg
    if isinstance(last_msg, list):
        parts = [b.get("text", "") for b in last_msg if isinstance(b, dict) and b.get("type") == "text"]
        return " ".join(parts).strip()
    if isinstance(last_msg, dict) and last_msg.get("type") == "text":
        return last_msg.get("text", "")
    return ""

def read_stdin_with_deadline(timeout_s: float = 0.20) -> str:
    deadline = time.monotonic() + timeout_s
    chunks = []
    total_bytes = 0
    fd = sys.stdin.fileno()
    try:
        flags = fcntl.fcntl(fd, fcntl.F_GETFL)
        fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
    except Exception:
        pass

    while True:
        rem = deadline - time.monotonic()
        if rem <= 0:
            break
        try:
            rlist, _, _ = select.select([fd], [], [], max(0.0, rem))
        except Exception:
            break
        if not rlist:
            break
        try:
            chunk = os.read(fd, 8192)
            if not chunk:
                break
            total_bytes += len(chunk)
            if total_bytes > MAX_INPUT_BYTES:
                return ""
            chunks.append(chunk)
        except (BlockingIOError, OSError):
            break
    return b"".join(chunks).decode("utf-8", errors="replace")

def dispatch_voice_async(text: str) -> None:
    if not os.path.isfile(AGENT_VOICE_BIN):
        return
    try:
        log_debug(f"Dispatching to agent-voice: {text!r}")
        subprocess.Popen(
            [AGENT_VOICE_BIN, text],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
            start_new_session=True,
            shell=False
        )
    except Exception as exc:
        log_debug(f"Dispatch exception: {exc}")

def main() -> None:
    try:
        raw_in = read_stdin_with_deadline(timeout_s=0.20).strip()
        if not raw_in:
            log_debug("Empty stdin -> fallback")
            dispatch_voice_async(DEFAULT_FALLBACK)
            return

        try:
            data = json.loads(raw_in)
        except Exception as exc:
            log_debug(f"JSON parse error: {exc} -> fallback")
            dispatch_voice_async(DEFAULT_FALLBACK)
            return

        raw_text = read_last_assistant_message(data)
        log_debug(f"Parsed last_assistant_message (length {len(raw_text)})")
        summary = extract_summary(raw_text)
        dispatch_voice_async(summary)
    except Exception as exc:
        log_debug(f"Main exception: {exc} -> fallback")
        try:
            dispatch_voice_async(DEFAULT_FALLBACK)
        except Exception:
            pass

if __name__ == "__main__":
    main()
