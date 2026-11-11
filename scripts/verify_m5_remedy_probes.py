#!/usr/bin/env python3
"""Targeted Empirical Verification Probe for Milestone 5 Remediation.

Specific verification checks for:
1. VideoDownloader URL validation:
   - Legitimate @invalid_user handles pass.
   - Host spoofing, path attacks, non-video paths raise InvalidVideoURLError.
2. VideoProcessor VideoProcessingError & Mock Mode:
   - Non-zero returncode on non-empty files raises VideoProcessingError (no silent 0-byte file created).
   - 0-byte dummy test files succeed in simulated mock mode.
   - extract_audio error handling.
3. mktemp audit across src/.
4. VideoJob.rendered_video_path SQLAlchemy synonym query compilation.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import AsyncMock, patch
from sqlalchemy import select

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.database.models import VideoJob
from src.services.video_downloader import (
    InvalidVideoURLError,
    VideoDownloader,
    VideoDownloaderError,
)
from src.services.video_processor import VideoProcessingError, VideoProcessor


def test_url_validation() -> None:
    print("Testing URL Validation in VideoDownloader...")
    downloader = VideoDownloader(mock_mode=True)

    # 1. Required test: Legitimate handle with "invalid" in username
    target_legit = "https://www.tiktok.com/@invalid_user/video/712345"
    try:
        validated = downloader._validate_url(target_legit)
        assert validated == target_legit, f"Expected {target_legit}, got {validated}"
        print(f"  [PASS] Legitimate URL passed: {target_legit}")
    except Exception as exc:
        raise AssertionError(f"Legitimate URL {target_legit} was rejected: {exc}")

    # Additional legitimate handles
    legit_urls = [
        "https://www.tiktok.com/@invalid/video/123456789",
        "https://www.tiktok.com/@user_invalid_koc/video/987654321",
        "https://m.tiktok.com/v/123456789",
        "https://vt.tiktok.com/ZS23456/",
        "https://vm.tiktok.com/ZM8r12345/",
        "https://www.douyin.com/video/7123456789",
    ]
    for url in legit_urls:
        validated = downloader._validate_url(url)
        assert validated == url, f"Expected {url}, got {validated}"
        print(f"  [PASS] Additional legit URL passed: {url}")

    # 2. Required attack URLs: Must raise InvalidVideoURLError
    attack_urls = [
        ("https://malicious.com/exploit.exe", "External malicious domain"),
        ("https://tiktok.com.attacker.com/video/1", "Domain spoofing / subdomain hijacking"),
        ("https://tiktok.com/@creator_only", "Non-video profile path"),
    ]

    for attack_url, desc in attack_urls:
        try:
            downloader._validate_url(attack_url)
            raise AssertionError(f"Attack URL {attack_url} ({desc}) should have failed but PASSED!")
        except InvalidVideoURLError as e:
            print(f"  [PASS] Correctly rejected ({desc}): {attack_url} -> {type(e).__name__}: {e}")
        except Exception as e:
            raise AssertionError(
                f"Attack URL {attack_url} raised {type(e).__name__} instead of InvalidVideoURLError: {e}"
            )

    # Additional adversarial attacks
    extra_attacks = [
        "https://attacker.tiktok.com.evil.com/video/123",
        "ftp://www.tiktok.com/@user/video/123",
        "https://www.tiktok.com/@user/video/",
        "https://vt.tiktok.com/",
        "https://www.douyin.com/@creator",
    ]
    for attack in extra_attacks:
        try:
            downloader._validate_url(attack)
            raise AssertionError(f"Extra attack URL {attack} should have failed but PASSED!")
        except InvalidVideoURLError:
            print(f"  [PASS] Extra attack correctly rejected: {attack}")


async def test_video_processor_resilience() -> None:
    print("\nTesting VideoProcessor VideoProcessingError & Mock Mode...")
    vp = VideoProcessor()

    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)

        # 1. 0-byte dummy test files must succeed in simulated mock mode
        zero_vid = tdp / "zero_vid.mp4"
        zero_vid.touch()
        zero_aud = tdp / "zero_aud.mp3"
        zero_aud.touch()
        out_mock = tdp / "mock_out.mp4"

        res_mock = await vp.remix_video(str(zero_vid), str(zero_aud), str(out_mock))
        assert os.path.exists(res_mock), "0-byte dummy input failed to produce output"
        assert res_mock == str(out_mock)
        print("  [PASS] 0-byte dummy files succeeded in simulated mock mode.")

        # 2. Non-zero FFmpeg returncode on non-empty files must raise VideoProcessingError
        # Create non-empty test files
        real_vid = tdp / "real_vid.mp4"
        real_vid.write_bytes(b"\x00\x00\x00\x20ftypisom" + b"\x00" * 1024)
        real_aud = tdp / "real_aud.mp3"
        real_aud.write_bytes(b"\xff\xfb\x90\x00" + b"\x00" * 512)
        out_fail = tdp / "fail_out.mp4"

        # Mock asyncio.create_subprocess_exec to simulate FFmpeg exit code 1 with stderr
        mock_proc = AsyncMock()
        mock_proc.returncode = 1
        mock_proc.communicate.return_value = (b"", b"FFmpeg error: Invalid data found when processing input")

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            try:
                # Force ffmpeg_bin to exist so it doesn't shortcut mock mode
                vp_with_ffmpeg = VideoProcessor(ffmpeg_bin="/usr/bin/ffmpeg")
                await vp_with_ffmpeg.remix_video(str(real_vid), str(real_aud), str(out_fail))
                raise AssertionError("remix_video did not raise VideoProcessingError on exitcode 1!")
            except VideoProcessingError as e:
                assert "failed with code 1" in str(e), f"Unexpected message: {e}"
                assert not out_fail.exists(), "F-02 defect present: fail_out.mp4 was touched despite error!"
                print(f"  [PASS] Non-zero FFmpeg returncode raised VideoProcessingError: {e}")
                print("  [PASS] Verified out_fail was NOT touched (no 0-byte corrupted file created).")

        # 3. extract_audio non-zero returncode on non-empty file must raise VideoProcessingError
        out_aud_fail = tdp / "fail_audio.mp3"
        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            try:
                vp_with_ffmpeg = VideoProcessor(ffmpeg_bin="/usr/bin/ffmpeg")
                await vp_with_ffmpeg.extract_audio(str(real_vid), str(out_aud_fail))
                raise AssertionError("extract_audio did not raise VideoProcessingError on exitcode 1!")
            except VideoProcessingError as e:
                assert "failed with code 1" in str(e)
                print(f"  [PASS] extract_audio non-zero returncode raised VideoProcessingError: {e}")


def test_mktemp_absence() -> None:
    print("\nAuditing absence of tempfile.mktemp in src/...")
    cmd = ["git", "grep", "mktemp", "src/"]
    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True)
    if result.returncode == 0 and result.stdout.strip():
        raise AssertionError(f"Found forbidden tempfile.mktemp usage in src/:\n{result.stdout}")
    print("  [PASS] Zero occurrences of tempfile.mktemp in src/.")


def test_database_rendered_video_path_synonym() -> None:
    print("\nTesting VideoJob.rendered_video_path SQLAlchemy synonym...")
    stmt = select(VideoJob).where(VideoJob.rendered_video_path == "/path/to/test.mp4")
    compiled_sql = str(stmt.compile())
    print(f"  Compiled SQL: {compiled_sql}")
    assert "video_jobs.output_video_path = :output_video_path_1" in compiled_sql or (
        "video_jobs.output_video_path" in compiled_sql and "WHERE" in compiled_sql
    ), f"Unexpected compiled SQL: {compiled_sql}"
    assert "WHERE false" not in compiled_sql.lower(), "Query compiled to WHERE false!"
    print("  [PASS] VideoJob.rendered_video_path correctly targets output_video_path column.")


async def main() -> None:
    print("=" * 80)
    print("Milestone 5 Remediation Empirical Probe Runner")
    print("=" * 80)
    test_url_validation()
    await test_video_processor_resilience()
    test_mktemp_absence()
    test_database_rendered_video_path_synonym()
    print("=" * 80)
    print("ALL SPECIFIC RE-VERIFICATION PROBES PASSED 100%!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
