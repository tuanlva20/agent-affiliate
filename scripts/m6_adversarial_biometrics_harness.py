#!/usr/bin/env python3
"""Empirical Adversarial Stress Harness for Milestone 6 Biometrics Engine.

AMAS v1.4.0 — Target Feature:
- Feature F20-F24: Human Behavioral Biometrics Engine (`src/services/human_behavior.py`)

Mandate Attack Vectors:
1. Typing Jitter & Timing Distribution:
   - Sample 500 keystrokes and verify all delays strictly fall within [0.08, 0.22] seconds (80ms - 220ms).
   - Statistical spread verification (dynamic variance vs deterministic delay).
2. Micro-Pause Timing Distribution:
   - Sample 100 pause points and verify delays strictly fall within [0.60, 1.40] seconds.
   - Punctuation boundaries (. , ! ? ; \\n) and hashtag triggers (#).
3. Typo Rate & Backspace Integrity:
   - typo_rate = 0.0: verify ZERO 'Backspace' presses across 50 diverse strings.
   - typo_rate = 1.0: verify EVERY character generates an incorrect key followed by 'Backspace' and then the correct key.
   - typo_rate = 0.03: over 1,000 characters, verify empirical typo count is reasonably bounded (between 1.0% and 6.0%).
   - Editor buffer reconstruction oracle (100% data integrity after Backspaces).
4. String Boundary & Unicode Torture:
   - Empty string "" (clean no-op, no clicks/keystrokes).
   - String of pure spaces "     " (space keystrokes preserved).
   - Pure Vietnamese diacritics "àáảãạăắằẳẵặâấầẩẫậ" (accent preservation and typo recovery).
   - Multi-line text with mixed punctuation and hashtags.
   - Unicode emojis "👗✨🔥🛒" (grapheme preservation).
5. Scroll Torture (Inertial Scrolling & Overshoot Dynamics):
   - steps = 0, steps = -5: verify safe rejection with ValueError, preventing negative loops.
   - steps = 100: verify wheel call count >= 100, verify presence of reverse overshoot ticks (delta_y < 0).
   - Acceleration curve verification (velocity increases over steps).
6. Captcha Alert Torture & Degradation Resilience:
   - Mock page where is_visible raises unexpected error: safe error catch and log, no unhandled crash.
   - Captcha detected: verify screenshot file is actually created in screenshots/ directory, verify Telegram message text contains "CẢNH BÁO CAPTCHA".
   - Bot object with no send_message or invalid admin_id: verify graceful degradation without unhandled crash.
7. Bezier Curve Mathematical Invariants:
   - Boundary tests (zero distance, negative coords).
   - Finite numerical validation without NaN or Inf.
"""

from __future__ import annotations

import asyncio
import math
import os
from pathlib import Path
import random
import shutil
import string
import sys
import tempfile
import time
from typing import Any, Callable, Dict, List, Optional, Tuple
from unittest.mock import AsyncMock, MagicMock, patch

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.services.human_behavior import (
    HumanBehaviorService,
    compute_cubic_bezier_point,
    generate_bezier_trajectory,
    TIKTOK_CAPTCHA_SELECTORS,
    QWERTY_ADJACENT,
)


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


def simulate_editor_buffer(pressed_keys: List[str]) -> str:
    """Simulate editor text buffer state by interpreting typed keys and Backspaces."""
    buffer: List[str] = []
    for key in pressed_keys:
        if key == "Backspace":
            if buffer:
                buffer.pop()
        else:
            buffer.append(key)
    return "".join(buffer)


# ==============================================================================
# Suite 1: Typing Jitter & Timing Distribution (500 Keystrokes)
# ==============================================================================
async def test_suite_1_typing_jitter_distribution() -> TestResult:
    res = TestResult("Suite 1: Typing Jitter & Timing Distribution (500 Keystrokes)")
    service = HumanBehaviorService()

    recorded_sleeps: List[float] = []

    async def fast_sleep(duration: float) -> None:
        recorded_sleeps.append(duration)

    page = MagicMock()
    page.keyboard = MagicMock()
    page.keyboard.press = AsyncMock()

    # Generate 500 alphanumeric characters with no sentence boundary or hashtag
    # Every keystroke must take the normal keystroke delay branch: [0.08, 0.22]
    alphabet_500 = ("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789" * 10)[:500]

    with patch("asyncio.sleep", side_effect=fast_sleep):
        await service.human_type(page, selector="", text=alphabet_500, typo_rate=0.0)

    # 1. Total samples count
    if len(recorded_sleeps) == 500:
        res.record_pass()
    else:
        res.record_fail(f"Expected 500 keystroke sleep samples, got {len(recorded_sleeps)}")

    # 2. Strict delay bounds verification [0.08, 0.22]
    out_of_bounds = [d for d in recorded_sleeps if d < 0.08 or d > 0.22]
    if not out_of_bounds:
        res.record_pass()
    else:
        res.record_fail(
            f"Found {len(out_of_bounds)} keystroke delays outside [0.08, 0.22]s: "
            f"min={min(out_of_bounds):.4f}, max={max(out_of_bounds):.4f}"
        )

    # 3. Dynamic variance check (must not be fixed or deterministic)
    if len(recorded_sleeps) >= 10:
        min_d = min(recorded_sleeps)
        max_d = max(recorded_sleeps)
        spread = max_d - min_d
        # Expected spread across 500 uniform samples in [0.08, 0.22] is close to 0.14
        if spread >= 0.10:
            res.record_pass()
        else:
            res.record_fail(f"Keystroke delay spread too narrow ({spread:.4f}s), lacks realistic human jitter")

        # Mean check (theoretical mean = 0.150s)
        mean_d = sum(recorded_sleeps) / len(recorded_sleeps)
        if 0.140 <= mean_d <= 0.160:
            res.record_pass()
        else:
            res.record_fail(f"Keystroke delay mean ({mean_d:.4f}s) deviated significantly from expected 0.150s")

    return res


# ==============================================================================
# Suite 2: Micro-Pause Timing Distribution (100 Pause Points)
# ==============================================================================
async def test_suite_2_micro_pause_distribution() -> TestResult:
    res = TestResult("Suite 2: Micro-Pause Timing Distribution (100 Pause Points)")
    service = HumanBehaviorService()

    recorded_pauses: List[float] = []

    async def fast_sleep(duration: float) -> None:
        recorded_pauses.append(duration)

    page = MagicMock()
    page.keyboard = MagicMock()
    page.keyboard.press = AsyncMock()

    # Punctuation characters triggering micro-pauses: {".", ",", "!", "?", ";", "\n"}
    # Construct 100 pause triggers
    pause_chars = [".", ",", "!", "?", ";", "\n"] * 17  # 102 chars
    pause_text = "".join(pause_chars[:100])

    with patch("asyncio.sleep", side_effect=fast_sleep):
        await service.human_type(page, selector="", text=pause_text, typo_rate=0.0)

    # 1. Total samples count
    if len(recorded_pauses) == 100:
        res.record_pass()
    else:
        res.record_fail(f"Expected 100 pause sleep samples, got {len(recorded_pauses)}")

    # 2. Strict delay bounds verification [0.60, 1.40]
    out_of_bounds = [p for p in recorded_pauses if p < 0.60 or p > 1.40]
    if not out_of_bounds:
        res.record_pass()
    else:
        res.record_fail(
            f"Found {len(out_of_bounds)} micro-pauses outside [0.60, 1.40]s: "
            f"min={min(out_of_bounds):.4f}, max={max(out_of_bounds):.4f}"
        )

    # 3. Dynamic variance check
    if len(recorded_pauses) >= 10:
        min_p = min(recorded_pauses)
        max_p = max(recorded_pauses)
        spread = max_p - min_p
        # Theoretical range is 0.80s (0.6 to 1.4)
        if spread >= 0.50:
            res.record_pass()
        else:
            res.record_fail(f"Micro-pause spread too narrow ({spread:.4f}s), lacks human thinking variability")

        # Mean check (theoretical mean = 1.00s)
        mean_p = sum(recorded_pauses) / len(recorded_pauses)
        if 0.90 <= mean_p <= 1.10:
            res.record_pass()
        else:
            res.record_fail(f"Micro-pause mean ({mean_p:.4f}s) deviated from expected 1.00s")

    # 4. Hashtag pre-pause check: space before '#' and '#' itself
    hashtag_sleeps: List[float] = []

    async def record_hashtag_sleeps(duration: float) -> None:
        hashtag_sleeps.append(duration)

    with patch("asyncio.sleep", side_effect=record_hashtag_sleeps):
        # In "a #b", 'a' is normal, ' ' is before '#', '#' is hashtag
        await service.human_type(page, selector="", text="a #b", typo_rate=0.0)

    # hashtag_sleeps:
    # idx 0: 'a' -> normal delay [0.08, 0.22]
    # idx 1: ' ' (is_before_hashtag=True) -> pause [0.60, 1.40]
    # idx 2: '#' (char=='#') -> pause [0.60, 1.40]
    # idx 3: 'b' -> normal delay [0.08, 0.22]
    if len(hashtag_sleeps) == 4:
        res.record_pass()
        if 0.60 <= hashtag_sleeps[1] <= 1.40 and 0.60 <= hashtag_sleeps[2] <= 1.40:
            res.record_pass()
        else:
            res.record_fail(
                f"Hashtag pauses incorrect: pause_before={hashtag_sleeps[1]:.3f}s, pause_hash={hashtag_sleeps[2]:.3f}s"
            )
    else:
        res.record_fail(f"Expected 4 sleep calls for 'a #b', got {len(hashtag_sleeps)}")

    return res


# ==============================================================================
# Suite 3: Typo Rate & Backspace Integrity
# ==============================================================================
async def test_suite_3_typo_rate_and_backspace_integrity() -> TestResult:
    res = TestResult("Suite 3: Typo Rate & Backspace Integrity")
    service = HumanBehaviorService()

    async def noop_sleep(d: float) -> None:
        pass

    # --------------------------------------------------------------------------
    # Subtest 3.1: typo_rate = 0.0 across 50 strings
    # --------------------------------------------------------------------------
    strings_50 = [
        f"Test string {i}: Váy xinh công sở dáng xòe #fashion_{i}! Siêu đẹp."
        for i in range(50)
    ]
    all_zero_backspaces = True
    total_keys_0 = 0

    with patch("asyncio.sleep", side_effect=noop_sleep):
        for s in strings_50:
            page = MagicMock()
            pressed: List[str] = []

            async def rec_press(k: str) -> None:
                pressed.append(k)

            page.keyboard = MagicMock()
            page.keyboard.press = AsyncMock(side_effect=rec_press)

            await service.human_type(page, selector="", text=s, typo_rate=0.0)
            total_keys_0 += len(pressed)

            if "Backspace" in pressed or len(pressed) != len(s):
                all_zero_backspaces = False
                res.record_fail(f"typo_rate=0.0 produced Backspaces or wrong length in: '{s}'")
                break

    if all_zero_backspaces and total_keys_0 > 0:
        res.record_pass()
    else:
        res.record_fail("Zero-typo verification failed across 50 strings")

    # --------------------------------------------------------------------------
    # Subtest 3.2: typo_rate = 1.0 (EVERY char generates wrong_char -> Backspace -> correct_char)
    # --------------------------------------------------------------------------
    test_chars_str = "AMASv140_Biometrics"
    page_1 = MagicMock()
    pressed_1: List[str] = []

    async def rec_press_1(k: str) -> None:
        pressed_1.append(k)

    page_1.keyboard = MagicMock()
    page_1.keyboard.press = AsyncMock(side_effect=rec_press_1)

    with patch("asyncio.sleep", side_effect=noop_sleep):
        await service.human_type(page_1, selector="", text=test_chars_str, typo_rate=1.0)

    # For length L, pressed keys must be 3 * L
    expected_len = len(test_chars_str) * 3
    if len(pressed_1) == expected_len:
        res.record_pass()
    else:
        res.record_fail(f"typo_rate=1.0 expected {expected_len} keypresses, got {len(pressed_1)}")

    # Verify every 3-step sequence: [wrong_char, "Backspace", correct_char]
    all_triplets_valid = True
    for idx, expected_char in enumerate(test_chars_str):
        wrong_k = pressed_1[idx * 3]
        bs_k = pressed_1[idx * 3 + 1]
        correct_k = pressed_1[idx * 3 + 2]

        if wrong_k == expected_char:
            all_triplets_valid = False
            res.record_fail(f"Char '{expected_char}' typo was identical to target key")
            break
        if bs_k != "Backspace":
            all_triplets_valid = False
            res.record_fail(f"Char '{expected_char}' lacked Backspace correction, got '{bs_k}'")
            break
        if correct_k != expected_char:
            all_triplets_valid = False
            res.record_fail(f"Char '{expected_char}' final typed key was wrong: '{correct_k}'")
            break

    if all_triplets_valid:
        res.record_pass()

    # Verify editor buffer reconstruction after 100% typos
    reconstructed_1 = simulate_editor_buffer(pressed_1)
    if reconstructed_1 == test_chars_str:
        res.record_pass()
    else:
        res.record_fail(f"Buffer reconstruction failed: expected '{test_chars_str}', got '{reconstructed_1}'")

    # --------------------------------------------------------------------------
    # Subtest 3.3: typo_rate = 0.03 empirical bound over 1,000 characters
    # --------------------------------------------------------------------------
    # 1,000 characters of natural text
    base_snippet = "Váy lụa thêu hoa cao cấp phong cách Hàn Quốc thời thượng 2026. "
    text_1000 = (base_snippet * (1000 // len(base_snippet) + 1))[:1000]

    page_003 = MagicMock()
    pressed_003: List[str] = []

    async def rec_press_003(k: str) -> None:
        pressed_003.append(k)

    page_003.keyboard = MagicMock()
    page_003.keyboard.press = AsyncMock(side_effect=rec_press_003)

    with patch("asyncio.sleep", side_effect=noop_sleep):
        await service.human_type(page_003, selector="", text=text_1000, typo_rate=0.03)

    typo_count = pressed_003.count("Backspace")
    empirical_rate = typo_count / 1000.0

    # Bounded between 1.0% (10 typos) and 6.0% (60 typos)
    if 10 <= typo_count <= 60:
        res.record_pass()
    else:
        res.record_fail(
            f"Empirical typo count {typo_count}/1000 ({empirical_rate*100:.2f}%) out of expected [1.0%, 6.0%]"
        )

    # Verify 100% integrity of reconstructed buffer for typo_rate=0.03
    reconstructed_003 = simulate_editor_buffer(pressed_003)
    if reconstructed_003 == text_1000:
        res.record_pass()
    else:
        res.record_fail(f"Buffer reconstruction failed under 3% typo rate! Length diff: {len(reconstructed_003)} vs 1000")

    return res


# ==============================================================================
# Suite 4: String Boundary & Unicode Torture
# ==============================================================================
async def test_suite_4_string_boundary_torture() -> TestResult:
    res = TestResult("Suite 4: String Boundary & Unicode Torture")
    service = HumanBehaviorService()

    async def noop_sleep(d: float) -> None:
        pass

    torture_cases: List[Tuple[str, str]] = [
        ("Empty string", ""),
        ("Pure spaces", "     "),
        ("Pure Vietnamese diacritics", "àáảãạăắằẳẵặâấầẩẫậ"),
        (
            "Multi-line with mixed punctuation and hashtags",
            "Hook 3s! Đẹp mê ly? Bấm ngay #thoitrang #xuhuong\nLink giỏ hàng.",
        ),
        ("Unicode emojis", "👗✨🔥🛒"),
        ("Mixed diacritics & emojis", "Váy xinh 👗 xịn sò ✨ săn ngay 🔥 giỏ hàng 🛒"),
    ]

    for label, target_str in torture_cases:
        page = MagicMock()
        pressed: List[str] = []

        async def rec_press(k: str) -> None:
            pressed.append(k)

        page.click = AsyncMock()
        page.keyboard = MagicMock()
        page.keyboard.press = AsyncMock(side_effect=rec_press)

        with patch("asyncio.sleep", side_effect=noop_sleep):
            try:
                await service.human_type(page, selector="#input_box", text=target_str, typo_rate=0.03)

                if target_str == "":
                    # Empty string should not click or type
                    if page.click.call_count == 0 and len(pressed) == 0:
                        res.record_pass()
                    else:
                        res.record_fail("Empty string called click or typed characters")
                else:
                    # Non-empty strings must click input and preserve buffer integrity
                    page.click.assert_awaited_once_with("#input_box")
                    reconstructed = simulate_editor_buffer(pressed)
                    if reconstructed == target_str:
                        res.record_pass()
                    else:
                        res.record_fail(
                            f"Torture case '{label}' reconstruction failed. Expected: {repr(target_str)}, Got: {repr(reconstructed)}"
                        )
            except Exception as e:
                res.record_fail(f"Torture case '{label}' raised unexpected exception: {e}")

    # Pure Vietnamese diacritics under forced 100% typo rate
    vn_diacritics = "àáảãạăắằẳẵặâấầẩẫậ"
    page_vn = MagicMock()
    pressed_vn: List[str] = []

    async def rec_press_vn(k: str) -> None:
        pressed_vn.append(k)

    page_vn.keyboard = MagicMock()
    page_vn.keyboard.press = AsyncMock(side_effect=rec_press_vn)

    with patch("asyncio.sleep", side_effect=noop_sleep):
        await service.human_type(page_vn, selector="", text=vn_diacritics, typo_rate=1.0)

    reconstructed_vn = simulate_editor_buffer(pressed_vn)
    if reconstructed_vn == vn_diacritics:
        res.record_pass()
    else:
        res.record_fail("Vietnamese diacritics 100% typo reconstruction failed")

    return res


# ==============================================================================
# Suite 5: Scroll Torture (Inertial Scrolling & Overshoot Dynamics)
# ==============================================================================
async def test_suite_5_scroll_torture() -> TestResult:
    res = TestResult("Suite 5: Scroll Torture (Inertial Scrolling & Overshoot)")
    service = HumanBehaviorService()

    async def noop_sleep(d: float) -> None:
        pass

    # --------------------------------------------------------------------------
    # Subtest 5.1: steps <= 0 must be safely rejected with ValueError
    # --------------------------------------------------------------------------
    page_invalid = MagicMock()

    # steps = 0
    try:
        await service.human_scroll(page_invalid, steps=0)
        res.record_fail("steps=0 did not raise ValueError")
    except ValueError as e:
        if "positive integer" in str(e):
            res.record_pass()
        else:
            res.record_fail(f"steps=0 raised ValueError with unexpected message: {e}")
    except Exception as e:
        res.record_fail(f"steps=0 raised unexpected exception: {type(e).__name__}: {e}")

    # steps = -5
    try:
        await service.human_scroll(page_invalid, steps=-5)
        res.record_fail("steps=-5 did not raise ValueError")
    except ValueError as e:
        if "positive integer" in str(e):
            res.record_pass()
        else:
            res.record_fail(f"steps=-5 raised ValueError with unexpected message: {e}")
    except Exception as e:
        res.record_fail(f"steps=-5 raised unexpected exception: {type(e).__name__}: {e}")

    # --------------------------------------------------------------------------
    # Subtest 5.2: steps = 100 wheel call count >= 100 & reverse overshoot ticks
    # --------------------------------------------------------------------------
    page_100 = MagicMock()
    page_100.mouse = MagicMock()
    wheel_calls: List[Tuple[int, int]] = []

    async def rec_wheel(dx: int, dy: int) -> None:
        wheel_calls.append((dx, dy))

    page_100.mouse.wheel = AsyncMock(side_effect=rec_wheel)

    with patch("asyncio.sleep", side_effect=noop_sleep):
        await service.human_scroll(page_100, steps=100)

    # 1. Total wheel calls must be >= 100 (steps + reverse rollback ticks)
    if len(wheel_calls) >= 100:
        res.record_pass()
    else:
        res.record_fail(f"Expected wheel calls >= 100, got {len(wheel_calls)}")

    # 2. Count forward ticks (dy > 0)
    forward_ticks = [dy for _, dy in wheel_calls if dy > 0]
    if len(forward_ticks) == 100:
        res.record_pass()
    else:
        res.record_fail(f"Expected 100 forward ticks, got {len(forward_ticks)}")

    # 3. Presence of reverse overshoot ticks (dy < 0)
    reverse_ticks = [dy for _, dy in wheel_calls if dy < 0]
    # Because i % 3 == 0 triggers on index 0, 3, 6, ..., 99 (34 indices), reverse count >= 34
    if len(reverse_ticks) >= 34:
        res.record_pass()
    else:
        res.record_fail(f"Expected at least 34 reverse overshoot ticks, got {len(reverse_ticks)}")

    # 4. Acceleration curve: forward deltas should increase over time
    first_10_mean = sum(forward_ticks[:10]) / 10.0
    last_10_mean = sum(forward_ticks[-10:]) / 10.0
    if last_10_mean > first_10_mean + 1000:  # delta increases by i * 20 -> ~1800 diff
        res.record_pass()
    else:
        res.record_fail(
            f"Acceleration verification failed: first 10 avg={first_10_mean:.1f}, last 10 avg={last_10_mean:.1f}"
        )

    # 5. Page missing mouse or wheel handles safely
    empty_page = object()
    try:
        with patch("asyncio.sleep", side_effect=noop_sleep):
            await service.human_scroll(empty_page, steps=3)
        res.record_pass()
    except Exception as e:
        res.record_fail(f"Scroll on page without mouse raised: {e}")

    return res


# ==============================================================================
# Suite 6: Captcha Alert Torture & Degradation Resilience
# ==============================================================================
async def test_suite_6_captcha_alert_torture() -> TestResult:
    res = TestResult("Suite 6: Captcha Alert Torture & Degradation Resilience")
    service = HumanBehaviorService()

    # --------------------------------------------------------------------------
    # Subtest 6.1: Mock page where is_visible raises unexpected error
    # --------------------------------------------------------------------------
    page_err = MagicMock()
    page_err.is_visible = AsyncMock(side_effect=RuntimeError("CDP connection destroyed unexpectedly"))
    page_err.url = "https://www.tiktok.com/@koc_fashion"

    try:
        detected = await service.detect_and_handle_captcha(page_err)
        if detected is False:
            res.record_pass()
        else:
            res.record_fail(f"Expected detected=False when is_visible throws, got {detected}")
    except Exception as e:
        res.record_fail(f"detect_and_handle_captcha did not catch page.is_visible error: {e}")

    # --------------------------------------------------------------------------
    # Subtest 6.2: Captcha detected -> verify screenshot file created & Telegram alert text
    # --------------------------------------------------------------------------
    test_screenshot_dir = tempfile.mkdtemp(prefix="amas_captcha_test_")
    test_screenshot_path = os.path.join(test_screenshot_dir, "captcha_alert.png")

    page_cpt = MagicMock()
    # Return True on first selector
    page_cpt.is_visible = AsyncMock(return_value=True)

    # Simulate realistic Playwright screenshot behavior (writes file to path)
    async def mock_screenshot(path: Optional[str] = None) -> None:
        if path:
            with open(path, "wb") as f:
                f.write(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + b"\x00" * 50)

    page_cpt.screenshot = AsyncMock(side_effect=mock_screenshot)

    bot = MagicMock()
    bot.admin_id = 99887766
    sent_alerts: List[Dict[str, Any]] = []

    async def mock_send(chat_id: Any, text: str) -> None:
        sent_alerts.append({"chat_id": chat_id, "text": text})

    bot.send_message = AsyncMock(side_effect=mock_send)

    try:
        detected = await service.detect_and_handle_captcha(
            page_cpt,
            telegram_bot=bot,
            channel_id="FASHION_01",
            screenshot_path=test_screenshot_path,
        )

        if detected is True:
            res.record_pass()
        else:
            res.record_fail("Expected detected=True when captcha selector visible")

        # Verify screenshot file was created on disk
        if os.path.exists(test_screenshot_path) and os.path.getsize(test_screenshot_path) > 0:
            res.record_pass()
        else:
            res.record_fail(f"Screenshot file not created at: {test_screenshot_path}")

        # Verify Telegram message contains required text tokens
        if len(sent_alerts) == 1:
            res.record_pass()
            msg_text = sent_alerts[0]["text"]
            if "CẢNH BÁO CAPTCHA" in msg_text:
                res.record_pass()
            else:
                res.record_fail(f"Telegram alert missing 'CẢNH BÁO CAPTCHA': {msg_text}")

            if "KÊNH FASHION_01" in msg_text:
                res.record_pass()
            else:
                res.record_fail(f"Telegram alert missing channel id: {msg_text}")
        else:
            res.record_fail(f"Expected 1 Telegram alert, got {len(sent_alerts)}")

    finally:
        shutil.rmtree(test_screenshot_dir, ignore_errors=True)

    # --------------------------------------------------------------------------
    # Subtest 6.3: Bot object with no send_message or invalid admin_id -> graceful degradation
    # --------------------------------------------------------------------------
    page_dummy = MagicMock()
    page_dummy.is_visible = AsyncMock(return_value=True)
    page_dummy.screenshot = AsyncMock()

    # Plain object with no Telegram methods
    empty_bot = object()
    try:
        detected_empty = await service.detect_and_handle_captcha(page_dummy, telegram_bot=empty_bot)
        if detected_empty is True:
            res.record_pass()
        else:
            res.record_fail("Degradation check failed on empty bot object")
    except Exception as e:
        res.record_fail(f"Empty bot object caused unhandled crash: {e}")

    # Bot with failing send_message
    broken_bot = MagicMock()
    broken_bot.admin_id = "not_an_int"
    broken_bot.send_message = AsyncMock(side_effect=Exception("Telegram Gateway Connection Refused"))

    try:
        detected_broken = await service.detect_and_handle_captcha(page_dummy, telegram_bot=broken_bot)
        if detected_broken is True:
            res.record_pass()
        else:
            res.record_fail("Degradation check failed on broken bot object")
    except Exception as e:
        res.record_fail(f"Broken bot object caused unhandled crash: {e}")

    # --------------------------------------------------------------------------
    # Subtest 6.4: URL-based Captcha detection fallback
    # --------------------------------------------------------------------------
    page_url_cpt = MagicMock()
    page_url_cpt.is_visible = AsyncMock(return_value=False)
    page_url_cpt.url = "https://www.tiktok.com/verify/captcha?lang=vi"
    page_url_cpt.screenshot = AsyncMock()

    detected_url = await service.detect_and_handle_captcha(page_url_cpt, telegram_bot=None)
    if detected_url is True:
        res.record_pass()
    else:
        res.record_fail("URL fallback failed to detect captcha URL")

    return res


# ==============================================================================
# Suite 7: Bezier Curve Mathematical Invariants
# ==============================================================================
async def test_suite_7_bezier_curve_invariants() -> TestResult:
    res = TestResult("Suite 7: Bezier Curve Mathematical Invariants")

    # 1. Zero-distance movement
    try:
        pts_zero = generate_bezier_trajectory(start=(300.0, 300.0), end=(300.0, 300.0), steps=10, jitter_px=1.0)
        if len(pts_zero) == 11:
            res.record_pass()
        else:
            res.record_fail(f"Zero-distance trajectory length expected 11, got {len(pts_zero)}")
    except Exception as e:
        res.record_fail(f"Zero-distance trajectory raised exception: {e}")

    # 2. Extreme coordinates (negative to high positive)
    try:
        pts_extreme = generate_bezier_trajectory(
            start=(-500.0, -200.0), end=(3840.0, 2160.0), steps=40, jitter_px=2.5
        )
        if len(pts_extreme) == 41:
            res.record_pass()
        else:
            res.record_fail(f"Extreme trajectory length expected 41, got {len(pts_extreme)}")

        # Verify all coordinates are finite numbers (no NaN or Inf)
        all_finite = all(
            math.isfinite(x) and math.isfinite(y) for x, y in pts_extreme
        )
        if all_finite:
            res.record_pass()
        else:
            res.record_fail("Trajectory contains NaN or Inf coordinates")

        # Verify start point close to start and end point close to end
        if abs(pts_extreme[0][0] - (-500.0)) <= 10.0 and abs(pts_extreme[-1][0] - 3840.0) <= 10.0:
            res.record_pass()
        else:
            res.record_fail("Boundary endpoints drifted beyond jitter tolerance")
    except Exception as e:
        res.record_fail(f"Extreme trajectory raised exception: {e}")

    # 3. Cubic Bezier point evaluation at t=0 and t=1
    p0 = (10.0, 20.0)
    p1 = (50.0, 80.0)
    p2 = (120.0, 160.0)
    p3 = (200.0, 300.0)
    pt_start = compute_cubic_bezier_point(p0, p1, p2, p3, 0.0)
    pt_end = compute_cubic_bezier_point(p0, p1, p2, p3, 1.0)

    if math.isclose(pt_start[0], 10.0) and math.isclose(pt_start[1], 20.0):
        res.record_pass()
    else:
        res.record_fail(f"Bezier t=0 math failed: expected {p0}, got {pt_start}")

    if math.isclose(pt_end[0], 200.0) and math.isclose(pt_end[1], 300.0):
        res.record_pass()
    else:
        res.record_fail(f"Bezier t=1 math failed: expected {p3}, got {pt_end}")

    return res


# ==============================================================================
# Main Runner
# ==============================================================================
async def run_all_adversarial_tests() -> Tuple[int, int, List[TestResult]]:
    print("=" * 80)
    print("🚀 AMAS v1.4.0 — Adversarial Stress Test Harness: Human Behavioral Biometrics")
    print("Target: src/services/human_behavior.py (Features F20 to F24)")
    print("=" * 80)

    start_time = time.perf_counter()
    suites: List[TestResult] = []

    s1 = await test_suite_1_typing_jitter_distribution()
    suites.append(s1)

    s2 = await test_suite_2_micro_pause_distribution()
    suites.append(s2)

    s3 = await test_suite_3_typo_rate_and_backspace_integrity()
    suites.append(s3)

    s4 = await test_suite_4_string_boundary_torture()
    suites.append(s4)

    s5 = await test_suite_5_scroll_torture()
    suites.append(s5)

    s6 = await test_suite_6_captcha_alert_torture()
    suites.append(s6)

    s7 = await test_suite_7_bezier_curve_invariants()
    suites.append(s7)

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
    if total_failed == 0:
        print("VERDICT: APPROVE (Biometrics Engine passes all adversarial stress vectors)")
    else:
        print("VERDICT: REQUEST_CHANGES (Regressions or vulnerabilities identified)")
    print("=" * 80)

    return total_passed, total_failed, suites


if __name__ == "__main__":
    passed, failed, suite_list = asyncio.run(run_all_adversarial_tests())
    sys.exit(0 if failed == 0 else 1)
