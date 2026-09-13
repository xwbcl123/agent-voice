#!/usr/bin/env python3
"""Unit and regression test suite for agent-voice v4.0.0
Tests registry discovery, validation rules, security boundaries, style resolution,
speed/gain bounding, v3 backward compatibility, and runtime capability probes.
"""
from importlib.machinery import SourceFileLoader
import os
from pathlib import Path
import sys
import tempfile
import unittest
import wave

AGENT_VOICE_SCRIPT = Path(__file__).resolve().parent.parent / "agent-voice"
av = SourceFileLoader("agent_voice", str(AGENT_VOICE_SCRIPT)).load_module()


class TestVoiceSecurity(unittest.TestCase):
    def test_voice_id_security_regex(self):
        valid_ids = ["default", "sol-like", "martin-primary", "sentinel-calm", "voice123"]
        for vid in valid_ids:
            self.assertTrue(av.validate_voice_id(vid), f"Expected {vid} to be valid")

        invalid_ids = [
            "../escape", "/etc/passwd", "sol/like", "voice name with space",
            "voice!", "default..", "..", "", "a" * 65, "Upper-Case"
        ]
        for vid in invalid_ids:
            self.assertFalse(av.validate_voice_id(vid), f"Expected {vid} to be invalid")

    def test_text_sanitization(self):
        raw = "Hello\x00\x08World!\n\t"
        cleaned = av.sanitize_text(raw, max_chars=10)
        self.assertEqual(cleaned, "HelloWorld")


class TestStyleRegistryAndResolution(unittest.TestCase):
    def test_styles_parser(self):
        styles = av.load_styles()
        self.assertIn("neutral", styles)
        self.assertIn("warm", styles)
        self.assertIn("serious", styles)
        self.assertIn("urgent", styles)
        self.assertEqual(styles["neutral"]["speed"], 1.0)

    def test_unknown_style_fallback(self):
        # Unknown style should fall back to neutral
        res = av.resolve_voice_and_style(text="测试文本", requested_style="unknown-style-123")
        self.assertEqual(res["style"], "neutral")
        self.assertIsNotNone(res["instruction"])

    def test_instruction_length_limit(self):
        long_instruct = "请" * 500
        res = av.resolve_voice_and_style(text="测试文本", raw_instruct=long_instruct)
        self.assertLessEqual(len(res["instruction"]), av.MAX_INSTRUCTION_CHARS)

    def test_instruction_language_selection(self):
        style_prof = av.get_style_profile("warm")
        self.assertIsNotNone(style_prof)
        prompt_zh = av.select_instruction_prompt(style_prof, "今天天气真好")
        self.assertIn("温暖", prompt_zh)

        prompt_en = av.select_instruction_prompt(style_prof, "System operational check completed.")
        self.assertIn("warmly", prompt_en)

    def test_speed_gain_bounds(self):
        res_fast = av.resolve_voice_and_style(text="测试", requested_speed=2.5)
        self.assertEqual(res_fast["speed"], av.MAX_SPEED)

        res_slow = av.resolve_voice_and_style(text="测试", requested_speed=0.1)
        self.assertEqual(res_slow["speed"], av.MIN_SPEED)

        res_loud = av.resolve_voice_and_style(text="测试", requested_gain=10.0)
        self.assertEqual(res_loud["gain_db"], av.MAX_GAIN_DB)

        res_quiet = av.resolve_voice_and_style(text="测试", requested_gain=-25.0)
        self.assertEqual(res_quiet["gain_db"], av.MIN_GAIN_DB)


class TestEventRoutingAndCompatibility(unittest.TestCase):
    def test_v3_scalar_compatibility(self):
        prof = av.resolve_voice_for_event("permission", None)
        self.assertIsNotNone(prof)
        self.assertEqual(prof["id"], "sentinel-calm")

    def test_precedence_explicit_overrides_event(self):
        res = av.resolve_voice_and_style(
            text="测试文本",
            requested_voice="martin-primary",
            requested_style="cheerful",
            event="permission"
        )
        self.assertEqual(res["voice"], "martin-primary")
        self.assertEqual(res["style"], "cheerful")

    def test_raw_instruct_overrides_style(self):
        custom_prompt = "请用极度平静的声音说话。"
        res = av.resolve_voice_and_style(
            text="测试文本",
            requested_style="warm",
            raw_instruct=custom_prompt
        )
        self.assertEqual(res["style"], "raw_instruct")
        self.assertEqual(res["instruction"], custom_prompt)

    def test_dry_run_flag(self):
        res = av.resolve_voice_and_style(text="测试文本", requested_voice="martin-primary", requested_style="warm")
        self.assertEqual(res["voice"], "martin-primary")
        self.assertEqual(res["style"], "warm")
        self.assertIn(res["runtime_mode"], ("instruct2", "zero-shot"))


class TestProfileValidation(unittest.TestCase):
    def test_valid_profile(self):
        prof = av.get_voice_profile("default")
        self.assertIsNotNone(prof)
        code, issues = av.validate_single_profile(prof)
        self.assertEqual(code, 0)

    def test_missing_wav(self):
        fake_prof = {
            "id": "fake",
            "wav": Path("/tmp/non-existent-12345.wav"),
            "txt": Path("/tmp/non-existent-12345.txt"),
            "transcript": "Hello",
            "meta": {}
        }
        code, issues = av.validate_single_profile(fake_prof)
        self.assertEqual(code, 2)
        self.assertTrue(any("reference.wav 文件不存在" in i for i in issues))

    def test_empty_transcript(self):
        prof = av.get_voice_profile("default")
        fake_prof = dict(prof)
        fake_prof["transcript"] = ""
        code, issues = av.validate_single_profile(fake_prof)
        self.assertEqual(code, 2)
        self.assertTrue(any("转录文本为空" in i for i in issues))


class TestRuntimeDoctor(unittest.TestCase):
    def test_doctor_probe(self):
        caps = av.probe_runtime_capabilities()
        self.assertTrue(caps["speech_cli"])
        self.assertTrue(caps["cosyvoice"])
        self.assertTrue(caps["cloning"])
        self.assertTrue(caps["instruct2"])
        self.assertTrue(caps["speed_control"])
        self.assertTrue(caps["gain_control"])


if __name__ == "__main__":
    unittest.main()
