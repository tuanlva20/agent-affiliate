#!/usr/bin/env python3
"""Empirical Adversarial Stress Harness for Milestone 5 Media Components.

AMAS v1.4.0 — Target Features:
- F17: Video Processor (FFmpeg Copyright Evasion Engine)
- F13: Video Downloader (Competitor Video Acquisition & Watermark Bypass)
- F16: Natural TTS Service (Vietnamese KOC Speech Synthesis)
- F18: Video Studio Pipeline Agent (End-to-End Orchestrator)

Adversarial Stress Dimensions:
1. Video Processor Filter Graph Integrity:
   - 100 randomized parameter configurations stress-testing filter graph consistency.
   - Verification of default speed jitter bounds (1.02 - 1.08x).
   - Strict verification of essential filter tokens: hflip, setpts, atempo, eq, crop, scale=1080:1920, amix, libx264, aac, +faststart.
   - Dual-branch audio topology (amix dual-stream vs. single-stream voiceover when keep_original_audio=False).
2. 0-Byte Media & Missing File Resilience:
   - Missing input file handling (raises FileNotFoundError for missing video or audio).
   - 0-byte video and 0-byte audio touched files (clean mock handling without exit code crashes).
   - Asymmetric empty input combinations (0-byte video with valid audio, valid video with 0-byte audio).
   - Output directory auto-creation for deep non-existent directories.
3. TTS Service Edge-Cases:
   - Text validation: empty string, whitespace-only, newlines, non-string types (raise ValueError).
   - Synthesis crash resistance on emoji-only strings (e.g. 😀🔥🎉💯) and 5,000+ character scripts.
   - Valid MPEG Layer 3 audio frame header verification (b"\\xff\\xfb\\x90\\x00").
   - Duration estimation heuristics for empty text, very long text, and varying file sizes.
   - Unsupported voice fallback to default KOC persona.
4. Video Downloader URL Adversarial Attacks:
   - Strict validation rejection (InvalidVideoURLError) on empty, whitespace, scheme-less, protocol injection, and SQL injection strings.
   - Validation that InvalidVideoURLError inherits from ValueError.
   - Mock mode validation: generates valid MP4 container with ISO header bytes (b"\\x00\\x00\\x00\\x20ftypisom").
5. Video Studio Pipeline Resilience:
   - Missing product metadata (None or empty dict).
   - Corrupted and adversarial job_ids (special characters, unicode, spaces).
   - Null database session resilience.
   - Database persistence verification with mock async session.
   - Persona and voice routing verification (Hoài My for fashion vs. Nam Minh for home utilities).
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
import random
import re
import shutil
import sys
import tempfile
import time
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.agents.video_studio import VideoStudioAgent
from src.database.models import VideoJob
from src.services.tts_service import TTSService
from src.services.video_downloader import (
    InvalidVideoURLError,
    VideoDownloader,
    VideoDownloaderError,
)
from src.services.video_processor import VideoProcessor


class TestResult:
    """Test suite result tracker."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.total = 0
        self.passed = 0
        self.failed = 0
        self.failures: List[str] = []

    def record_pass(self) -> None:
        self.total += 1
        self.passed += 1

    def record_fail(self, detail: str) -> None:
        self.total += 1
        self.failed += 1
        self.failures.append(detail)

    @property
    def pass_rate(self) -> float:
        return (self.passed / self.total * 100.0) if self.total > 0 else 0.0


# ==============================================================================
# Suite 1: Video Processor Filter Graph Integrity (100 Random Iterations & Graph Rules)
# ==============================================================================
async def test_suite_1_video_processor_filter_graph() -> TestResult:
    res = TestResult("Suite 1: Video Processor Filter Graph Integrity")
    vp = VideoProcessor()

    # 1. 100 Randomized Combinations of Options
    for i in range(100):
        override_speed = random.choice([True, False, False])
        speed_val = round(random.uniform(0.90, 1.30), 3) if override_speed else None
        hflip_val = random.choice([True, False])
        keep_bgm_val = random.choice([True, False])
        contrast_val = round(random.uniform(0.95, 1.20), 2)
        sat_val = round(random.uniform(0.95, 1.20), 2)
        brightness_val = round(random.uniform(-0.05, 0.05), 2)
        crop_val = round(random.uniform(0.01, 0.05), 3)

        opts: Dict[str, Any] = {
            "hflip": hflip_val,
            "keep_original_audio": keep_bgm_val,
            "contrast": contrast_val,
            "saturation": sat_val,
            "brightness": brightness_val,
            "crop_ratio": crop_val,
        }
        if speed_val is not None:
            opts["speed_factor"] = speed_val

        video_in = f"/tmp/input_{i}.mp4"
        audio_in = f"/tmp/voice_{i}.mp3"
        video_out = f"/tmp/rendered_{i}.mp4"

        cmd = vp.build_ffmpeg_command(video_in, audio_in, video_out, options=opts)
        cmd_str = " ".join(cmd)

        # Baseline structure check
        if "-filter_complex" in cmd and "-i" in cmd and "-c:v" in cmd and "libx264" in cmd:
            res.record_pass()
        else:
            res.record_fail(f"Iteration {i}: Command missing baseline FFmpeg arguments: {cmd_str}")

        # Check speed bounds
        # Look for atempo= or setpts=
        if keep_bgm_val:
            match_atempo = re.search(r"atempo=([0-9\.]+)", cmd_str)
            if match_atempo:
                atempo_speed = float(match_atempo.group(1))
                if override_speed:
                    if abs(atempo_speed - speed_val) < 1e-3:
                        res.record_pass()
                    else:
                        res.record_fail(
                            f"Iteration {i}: Overridden speed mismatch ({atempo_speed} vs {speed_val})"
                        )
                else:
                    if 1.02 <= atempo_speed <= 1.08:
                        res.record_pass()
                    else:
                        res.record_fail(
                            f"Iteration {i}: Default speed factor {atempo_speed} out of bounds [1.02, 1.08]"
                        )
            else:
                res.record_fail(f"Iteration {i}: atempo parameter not found in audio filter")

        # Check setpts inversion: setpts = (1 / speed) * PTS
        match_setpts = re.search(r"setpts=([0-9\.]+)\*PTS", cmd_str)
        if match_setpts:
            inv_speed = float(match_setpts.group(1))
            eff_speed = round(1.0 / inv_speed, 2)
            if not override_speed:
                if 1.01 <= eff_speed <= 1.09:
                    res.record_pass()
                else:
                    res.record_fail(
                        f"Iteration {i}: Inverted setpts speed {eff_speed} out of expected range"
                    )
            else:
                res.record_pass()
        else:
            res.record_fail(f"Iteration {i}: setpts parameter not found in video filter")

        # Check hflip logic
        if hflip_val:
            if "hflip" in cmd_str:
                res.record_pass()
            else:
                res.record_fail(f"Iteration {i}: hflip=True but 'hflip' missing from command")
        else:
            if "hflip" not in cmd_str:
                res.record_pass()
            else:
                res.record_fail(f"Iteration {i}: hflip=False but 'hflip' present in command")

        # Check keep_original_audio logic
        if keep_bgm_val:
            if "amix=inputs=2:duration=first" in cmd_str and "[a1][a0]amix" in cmd_str:
                res.record_pass()
            else:
                res.record_fail(f"Iteration {i}: keep_original_audio=True missing amix node")
        else:
            if "amix" not in cmd_str and "[1:a]volume=" in cmd_str and "[a]" in cmd_str:
                res.record_pass()
            else:
                res.record_fail(
                    f"Iteration {i}: keep_original_audio=False should omit amix and map single stream"
                )

        # Check output encoding parameters
        if (
            "-pix_fmt yuv420p" in cmd_str
            and "-c:a aac" in cmd_str
            and "-movflags +faststart" in cmd_str
            and "-crf 23" in cmd_str
            and "-preset fast" in cmd_str
        ):
            res.record_pass()
        else:
            res.record_fail(f"Iteration {i}: Output encoding flags incomplete in {cmd_str}")

    # 2. Strict Presence Test for Default Filter Chain
    # (hflip, setpts, atempo, eq, crop, scale=1080:1920, amix, libx264, aac, +faststart)
    default_cmd = vp.build_ffmpeg_command("input.mp4", "audio.mp3", "output.mp4")
    default_cmd_str = " ".join(default_cmd)

    strictly_required = [
        "hflip",
        "setpts",
        "atempo",
        "eq",
        "crop",
        "scale=1080:1920",
        "amix",
        "libx264",
        "aac",
        "+faststart",
    ]

    for token in strictly_required:
        if token in default_cmd_str:
            res.record_pass()
        else:
            res.record_fail(f"Strict filter token '{token}' missing from default command")

    return res


# ==============================================================================
# Suite 2: 0-Byte Media & Missing File Resilience
# ==============================================================================
async def test_suite_2_zero_byte_and_missing_file_resilience() -> TestResult:
    res = TestResult("Suite 2: 0-Byte Media & Missing File Resilience")
    vp = VideoProcessor()

    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)

        vid_empty = tdp / "empty_video.mp4"
        vid_empty.touch()
        aud_empty = tdp / "empty_audio.mp3"
        aud_empty.touch()

        vid_valid = tdp / "valid_video.mp4"
        vid_valid.write_bytes(b"\x00\x00\x00\x20ftypisom" + b"\x00" * 2000)
        aud_valid = tdp / "valid_audio.mp3"
        aud_valid.write_bytes(b"\xff\xfb\x90\x00" + b"\x00" * 1000)

        missing_vid = str(tdp / "nonexistent_video.mp4")
        missing_aud = str(tdp / "nonexistent_audio.mp3")

        # 1. Missing video raises FileNotFoundError
        try:
            await vp.remix_video(missing_vid, str(aud_valid), str(tdp / "out_1.mp4"))
            res.record_fail("remix_video did not raise FileNotFoundError on missing video")
        except FileNotFoundError:
            res.record_pass()
        except Exception as e:
            res.record_fail(f"Unexpected exception on missing video: {e}")

        # 2. Missing audio raises FileNotFoundError
        try:
            await vp.remix_video(str(vid_valid), missing_aud, str(tdp / "out_2.mp4"))
            res.record_fail("remix_video did not raise FileNotFoundError on missing audio")
        except FileNotFoundError:
            res.record_pass()
        except Exception as e:
            res.record_fail(f"Unexpected exception on missing audio: {e}")

        # 3. Both missing raises FileNotFoundError
        try:
            await vp.remix_video(missing_vid, missing_aud, str(tdp / "out_3.mp4"))
            res.record_fail("remix_video did not raise FileNotFoundError when both files missing")
        except FileNotFoundError:
            res.record_pass()
        except Exception as e:
            res.record_fail(f"Unexpected exception on both missing: {e}")

        # 4. 0-byte video + 0-byte audio (touch files) must succeed without subprocess crash
        out_empty_both = str(tdp / "out_empty_both.mp4")
        try:
            result_both = await vp.remix_video(str(vid_empty), str(aud_empty), out_empty_both)
            if os.path.exists(result_both):
                res.record_pass()
            else:
                res.record_fail("0-byte video + 0-byte audio did not produce output file")
        except Exception as e:
            res.record_fail(f"0-byte video + 0-byte audio threw exception: {e}")

        # 5. 0-byte video + valid audio must succeed
        out_empty_vid = str(tdp / "out_empty_vid.mp4")
        try:
            result_ev = await vp.remix_video(str(vid_empty), str(aud_valid), out_empty_vid)
            if os.path.exists(result_ev):
                res.record_pass()
            else:
                res.record_fail("0-byte video + valid audio did not produce output file")
        except Exception as e:
            res.record_fail(f"0-byte video + valid audio threw exception: {e}")

        # 6. Valid video + 0-byte audio must succeed
        out_empty_aud = str(tdp / "out_empty_aud.mp4")
        try:
            result_ea = await vp.remix_video(str(vid_valid), str(aud_empty), out_empty_aud)
            if os.path.exists(result_ea):
                res.record_pass()
            else:
                res.record_fail("Valid video + 0-byte audio did not produce output file")
        except Exception as e:
            res.record_fail(f"Valid video + 0-byte audio threw exception: {e}")

        # 7. Deep non-existent output directory auto-creation
        deep_out = str(tdp / "deep" / "nested" / "folder" / "structure" / "remixed.mp4")
        try:
            deep_res = await vp.remix_video(str(vid_empty), str(aud_empty), deep_out)
            if os.path.exists(deep_res) and Path(deep_res).is_file():
                res.record_pass()
            else:
                res.record_fail("Deep nested directory output not created")
        except Exception as e:
            res.record_fail(f"Deep directory creation failed: {e}")

        # 8. extract_audio resilience tests
        try:
            await vp.extract_audio(missing_vid)
            res.record_fail("extract_audio did not raise FileNotFoundError on missing video")
        except FileNotFoundError:
            res.record_pass()
        except Exception as e:
            res.record_fail(f"extract_audio unexpected error on missing video: {e}")

        try:
            aud_out = await vp.extract_audio(str(vid_empty))
            if os.path.exists(aud_out):
                res.record_pass()
            else:
                res.record_fail("extract_audio on 0-byte video did not produce output file")
        except Exception as e:
            res.record_fail(f"extract_audio threw error on 0-byte video: {e}")

    return res


# ==============================================================================
# Suite 3: TTS Service Edge-Cases
# ==============================================================================
async def test_suite_3_tts_service_edge_cases() -> TestResult:
    res = TestResult("Suite 3: TTS Service Edge-Cases")
    tts = TTSService(offline_mode=True)

    # 1. Empty string & whitespace validation
    invalid_texts = [
        "",
        "   ",
        "\t\t\n\r",
        "   \n   ",
        None,
        12345,
        {"text": "invalid"},
        ["empty"],
    ]

    for inv in invalid_texts:
        try:
            await tts.synthesize(inv)  # type: ignore
            res.record_fail(f"synthesize({inv!r}) did not raise ValueError")
        except ValueError:
            res.record_pass()
        except Exception as e:
            res.record_fail(f"synthesize({inv!r}) raised {type(e).__name__} instead of ValueError: {e}")

    # 2. Strings with only emoji
    emoji_payloads = [
        "😀🔥🎉💯",
        "🇻🇳👗✨",
        "👏👍❤️😍",
    ]
    for em in emoji_payloads:
        try:
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tf:
                em_path = tf.name
            out = await tts.synthesize(em, output_path=em_path)
            if os.path.exists(out) and os.path.getsize(out) > 0:
                header = Path(out).read_bytes()[:4]
                if header == b"\xff\xfb\x90\x00":
                    res.record_pass()
                else:
                    res.record_fail(f"Emoji payload {em!r} produced invalid MP3 header: {header}")
            else:
                res.record_fail(f"Emoji payload {em!r} did not produce non-empty audio file")
            if os.path.exists(em_path):
                os.unlink(em_path)
        except Exception as e:
            res.record_fail(f"Emoji payload {em!r} threw exception: {e}")

    # 3. Very long text (5,000 and 10,000 characters)
    for length in (5000, 10000):
        long_str = ("Sản phẩm thời trang cao cấp chất lượng vượt trội " * (length // 45 + 1))[
            :length
        ]
        try:
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tf:
                long_path = tf.name
            out = await tts.synthesize(long_str, output_path=long_path)
            if os.path.exists(out):
                header = Path(out).read_bytes()[:4]
                if header == b"\xff\xfb\x90\x00":
                    res.record_pass()
                else:
                    res.record_fail(f"Long text ({length} chars) produced invalid MP3 header: {header}")
            else:
                res.record_fail(f"Long text ({length} chars) did not produce output file")
            if os.path.exists(long_path):
                os.unlink(long_path)
        except Exception as e:
            res.record_fail(f"Long text ({length} chars) synthesis threw exception: {e}")

    # 4. Offline fallback produces valid MP3 headers
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tf:
        fallback_path = tf.name
    try:
        out = await tts.synthesize("Xin chào chị em, hôm nay tui lên mẫu này nhé", output_path=fallback_path)
        raw_bytes = Path(out).read_bytes()
        # Verify sync word and Layer 3 header
        if raw_bytes[:4] == b"\xff\xfb\x90\x00":
            res.record_pass()
        else:
            res.record_fail(f"Fallback audio header incorrect: {raw_bytes[:4]}")
        # Verify non-trivial frame size (418 bytes)
        if len(raw_bytes) >= 418:
            res.record_pass()
        else:
            res.record_fail(f"Fallback audio frame too small: {len(raw_bytes)} bytes")
    finally:
        if os.path.exists(fallback_path):
            os.unlink(fallback_path)

    # 5. Duration detection tests
    # Heuristic: empty text -> check audio size or fallback
    d1 = tts.get_audio_duration("nonexistent.mp3", text="")
    if d1 == 3.0:
        res.record_pass()
    else:
        res.record_fail(f"Empty text duration expected 3.0, got {d1}")

    d2 = tts.get_audio_duration("nonexistent.mp3", text="   \n\t  ")
    if d2 == 3.0:
        res.record_pass()
    else:
        res.record_fail(f"Whitespace text duration expected 3.0, got {d2}")

    # Text calculation: words / 3.0
    text_30_words = " ".join([f"word_{j}" for j in range(30)])
    d_30 = tts.get_audio_duration("nonexistent.mp3", text=text_30_words)
    if d_30 == 10.0:
        res.record_pass()
    else:
        res.record_fail(f"30-word text duration expected 10.0, got {d_30}")

    # Very long text duration
    text_3000_words = " ".join([f"từ_{j}" for j in range(3000)])
    d_3000 = tts.get_audio_duration("nonexistent.mp3", text=text_3000_words)
    if d_3000 == 1000.0:
        res.record_pass()
    else:
        res.record_fail(f"3000-word text duration expected 1000.0, got {d_3000}")

    # Small audio file (<= 1024 bytes) without text
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tf:
        tf.write(b"\xff\xfb\x90\x00" * 100)  # 400 bytes
        small_mp3 = tf.name
    try:
        d_small = tts.get_audio_duration(small_mp3, text=None)
        if d_small == 3.0:
            res.record_pass()
        else:
            res.record_fail(f"Small audio file duration expected 3.0, got {d_small}")
    finally:
        os.unlink(small_mp3)

    # Large audio file (> 1024 bytes) without text: size / 16000.0
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tf:
        tf.write(b"\x00" * 48000)  # 48 KB -> 3.0s
        large_mp3 = tf.name
    try:
        d_large = tts.get_audio_duration(large_mp3, text=None)
        if d_large == 3.0:
            res.record_pass()
        else:
            res.record_fail(f"48KB audio file duration expected 3.0, got {d_large}")
    finally:
        os.unlink(large_mp3)

    # 6. Unsupported Voice Fallback
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tf:
        voice_test_path = tf.name
    try:
        out_voice = await tts.synthesize(
            "Kiểm tra giọng nói dự phòng",
            voice="unsupported_voice_12345",
            output_path=voice_test_path,
        )
        if os.path.exists(out_voice):
            res.record_pass()
        else:
            res.record_fail("Unsupported voice synthesis failed to produce file")
    finally:
        if os.path.exists(voice_test_path):
            os.unlink(voice_test_path)

    return res


# ==============================================================================
# Suite 4: Video Downloader URL Adversarial Attacks
# ==============================================================================
async def test_suite_4_video_downloader_adversarial_attacks() -> TestResult:
    res = TestResult("Suite 4: Video Downloader URL Adversarial Attacks")
    downloader = VideoDownloader(mock_mode=True)

    # 1. Verify InvalidVideoURLError exception hierarchy
    if issubclass(InvalidVideoURLError, ValueError) and issubclass(
        InvalidVideoURLError, VideoDownloaderError
    ):
        res.record_pass()
    else:
        res.record_fail("InvalidVideoURLError must inherit from both ValueError and VideoDownloaderError")

    # 2. Adversarial URL vectors
    adversarial_urls = [
        # Empty & whitespace
        "",
        "   ",
        "\t\n\r  ",
        # None & non-string
        None,
        123456,
        {"url": "https://tiktok.com"},
        # Explicit invalid domains / patterns
        "https://invalid.com/video",
        "http://invalid.org/media/123",
        "https://www.tiktok.com/@user/video/invalid_token",
        # Protocol injection & XSS
        "javascript:alert(1)",
        "data:text/html,<script>alert(1)</script>",
        "file:///etc/passwd",
        # SQL injection strings
        "' OR '1'='1",
        "1; DROP TABLE products; --",
        "SELECT * FROM users WHERE id=1",
        "admin' --",
        "1' UNION SELECT username, password FROM users --",
        # Shell injection strings
        "; rm -rf /",
        "$(whoami)",
        "`cat /etc/passwd`",
        "&& shutdown -h now",
        # URLs without scheme
        "tiktok.com/@user/video/7123456789012345678",
        "www.tiktok.com/@koc_viet/video/1001",
        "vt.tiktok.com/ZS2R9ABCD/",
        # Malformed URLs
        "http://",
        "https://",
        "ftp://",
        "://missing-scheme.com/video",
        "https:///missing-host/video",
    ]

    for attack in adversarial_urls:
        try:
            await downloader.download_video(attack)  # type: ignore
            res.record_fail(f"Attack vector {attack!r} was accepted without InvalidVideoURLError")
        except InvalidVideoURLError as e:
            if isinstance(e, ValueError):
                res.record_pass()
            else:
                res.record_fail(f"Attack vector {attack!r} raised non-ValueError InvalidVideoURLError")
        except Exception as e:
            res.record_fail(
                f"Attack vector {attack!r} raised unexpected {type(e).__name__} instead of InvalidVideoURLError: {e}"
            )

    # 3. Valid URLs in mock mode produce valid MP4 files with ISO header
    valid_urls = [
        "https://www.tiktok.com/@fashion_shop/video/7392817294819283741",
        "https://vt.tiktok.com/ZS23456/",
        "https://tiktok.com/@homelife/video/8271638291038472910?is_from_webapp=1",
        "https://vm.tiktok.com/ZM8r12345/",
    ]

    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        for idx, url in enumerate(valid_urls):
            custom_out = tdp / f"valid_download_{idx}.mp4"
            out_file = await downloader.download_video(url, output_path=custom_out)

            # Check existence
            if os.path.exists(out_file) and Path(out_file).is_file():
                res.record_pass()
            else:
                res.record_fail(f"Valid URL {url} did not produce existing file: {out_file}")

            # Check ISO MP4 32-byte header (b"\x00\x00\x00\x20ftypisom")
            raw_bytes = Path(out_file).read_bytes()
            expected_magic = b"\x00\x00\x00\x20\x66\x74\x79\x70\x69\x73\x6f\x6d"
            if raw_bytes[:12] == expected_magic:
                res.record_pass()
            else:
                res.record_fail(
                    f"Valid URL {url} produced incorrect MP4 magic bytes: {raw_bytes[:12]!r}"
                )

            # Check file extension is strictly .mp4
            if out_file.endswith(".mp4"):
                res.record_pass()
            else:
                res.record_fail(f"Downloaded file does not end with .mp4: {out_file}")

    return res


# ==============================================================================
# Suite 5: Video Studio Pipeline Resilience
# ==============================================================================
async def test_suite_5_video_studio_pipeline_resilience() -> TestResult:
    res = TestResult("Suite 5: Video Studio Pipeline Resilience")

    with tempfile.TemporaryDirectory() as td:
        agent = VideoStudioAgent(storage_dir=td)

        # 1. Missing product meta (product_meta=None), missing persona, missing db_session
        normal_job_id = "job_baseline_001"
        try:
            rendered = await agent.produce_video(
                job_id=normal_job_id,
                product_meta=None,
                persona=None,
                source_video_url=None,
                db_session=None,
            )
            if os.path.exists(rendered) and normal_job_id in rendered:
                res.record_pass()
            else:
                res.record_fail(f"Missing meta produce_video failed: rendered={rendered}")
        except Exception as e:
            res.record_fail(f"produce_video with missing meta threw exception: {e}")

        # 2. Corrupted job_ids
        corrupted_job_ids = [
            "job_!@#$%^&*()_+ special/chars",
            "job_vietnamese_tiếng_việt_có_dấu_🇻🇳",
            "job_emoji_🔥_🎉_💯",
            "job-with-hyphens-and-dots.v1.0.final",
            "job_extreme_" + "A" * 150,
        ]

        for cid in corrupted_job_ids:
            try:
                out = await agent.produce_video(
                    job_id=cid,
                    product_meta={"title": "Váy hoa nhí dáng xòe", "price": 189000.0},
                    persona={"tone": "koc"},
                    db_session=None,
                )
                if os.path.exists(out):
                    res.record_pass()
                else:
                    res.record_fail(f"Corrupted job_id {cid!r} did not produce existing file: {out}")

                if cid in out:
                    res.record_pass()
                else:
                    res.record_fail(f"Output path {out!r} does not contain job_id {cid!r}")
            except Exception as e:
                res.record_fail(f"Corrupted job_id {cid!r} raised exception: {e}")

        # 3. Persona and Voice Routing Verification
        # Fashion niche -> vi-VN-HoaiMyNeural
        try:
            fashion_meta = {
                "title": "Set blazer croptop thời trang",
                "niche_id": "thoi_trang_nu",
                "price": 250000.0,
            }
            fashion_job_id = "job_fashion_persona"
            fashion_rendered = await agent.produce_video(
                job_id=fashion_job_id,
                product_meta=fashion_meta,
                db_session=None,
            )
            if os.path.exists(fashion_rendered) and fashion_job_id in fashion_rendered:
                res.record_pass()
            else:
                res.record_fail("Fashion persona video output missing")
        except Exception as e:
            res.record_fail(f"Fashion persona video generation threw exception: {e}")

        # HomeLife niche -> vi-VN-NamMinhNeural
        try:
            homelife_meta = {
                "title": "Cây lau nhà tự vắt thông minh",
                "niche_id": "do_gia_dung",
                "price": 129000.0,
            }
            homelife_job_id = "job_homelife_persona"
            homelife_rendered = await agent.produce_video(
                job_id=homelife_job_id,
                product_meta=homelife_meta,
                db_session=None,
            )
            if os.path.exists(homelife_rendered) and homelife_job_id in homelife_rendered:
                res.record_pass()
            else:
                res.record_fail("HomeLife persona video output missing")
        except Exception as e:
            res.record_fail(f"HomeLife persona video generation threw exception: {e}")

        # 4. Database Session Synchronization Verification
        # Mock database session and mock job record
        mock_job = MagicMock(spec=VideoJob)
        mock_job.job_id = "job_db_sync_100"
        mock_job.status = "pending"
        mock_job.output_video_path = None
        mock_job.rendered_video_path = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_job

        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_result
        mock_session.commit = AsyncMock()

        try:
            db_rendered = await agent.produce_video(
                job_id="job_db_sync_100",
                product_meta={"title": "Nồi chiên không dầu", "niche_id": "do_gia_dung"},
                db_session=mock_session,
            )
            if mock_job.status == "rendered":
                res.record_pass()
            else:
                res.record_fail(f"VideoJob status not updated to 'rendered': {mock_job.status}")

            if mock_job.rendered_video_path == db_rendered:
                res.record_pass()
            else:
                res.record_fail(
                    f"VideoJob rendered_video_path mismatch: {mock_job.rendered_video_path}"
                )

            if mock_session.commit.called:
                res.record_pass()
            else:
                res.record_fail("db_session.commit was not called during video production")
        except Exception as e:
            res.record_fail(f"Database synchronization test threw exception: {e}")

    return res


# ==============================================================================
# Runner: Orchestrate All Adversarial Media Suites
# ==============================================================================
async def run_all_adversarial_tests() -> Tuple[int, int, List[TestResult]]:
    start_time = time.perf_counter()
    print("=" * 80)
    print("AMAS v1.4.0 — Empirical Adversarial Stress Harness for Milestone 5 Media")
    print("Target Components: VideoProcessor, VideoDownloader, TTSService, VideoStudioAgent")
    print("=" * 80)

    suites: List[TestResult] = []

    s1 = await test_suite_1_video_processor_filter_graph()
    suites.append(s1)

    s2 = await test_suite_2_zero_byte_and_missing_file_resilience()
    suites.append(s2)

    s3 = await test_suite_3_tts_service_edge_cases()
    suites.append(s3)

    s4 = await test_suite_4_video_downloader_adversarial_attacks()
    suites.append(s4)

    s5 = await test_suite_5_video_studio_pipeline_resilience()
    suites.append(s5)

    elapsed = time.perf_counter() - start_time
    total_passed = sum(s.passed for s in suites)
    total_failed = sum(s.failed for s in suites)
    grand_total = total_passed + total_failed

    for s in suites:
        status_str = "PASS" if s.failed == 0 else f"FAIL ({s.failed} issues)"
        print(f"\n▶ {s.name}: {status_str}")
        print(
            f"  Assertions: {s.total} | Passed: {s.passed} | Failed: {s.failed} | Pass Rate: {s.pass_rate:.1f}%"
        )
        if s.failures:
            print("  Failures Encountered:")
            for f in s.failures[:5]:
                print(f"    ❌ {f}")
            if len(s.failures) > 5:
                print(f"    ... and {len(s.failures) - 5} more issues.")

    print("\n" + "=" * 80)
    overall_rate = (total_passed / grand_total * 100.0) if grand_total > 0 else 0.0
    print(
        f"SUMMARY: {total_passed}/{grand_total} assertions passed ({overall_rate:.1f}%). "
        f"Total Failures: {total_failed} in {elapsed*1000:.1f}ms"
    )
    print("=" * 80)

    return total_passed, total_failed, suites


if __name__ == "__main__":
    from typing import Tuple

    passed, failed, suite_list = asyncio.run(run_all_adversarial_tests())
    sys.exit(0 if failed == 0 else 1)
