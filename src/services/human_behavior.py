"""AMAS v1.4.0 — Human Behavioral Biometrics Engine (Features F20 to F24).

Implements realistic human simulation on top of Playwright:
- F20: Inertia mouse wheel scrolling with dynamic acceleration and reverse rollback.
- F21: Biometric keystroke delays (80-220ms), micro-pauses (0.6-1.4s), and typo simulation with Backspace correction.
- F22: Non-linear Bezier mouse movement with jitter and pre-click hover.
- F23: Pre-posting feed warm-up session on tiktok.com (3-5 minutes, watching & scrolling).
- F24: Emergency Captcha Guard (immediate halt, screenshot capture, and Telegram alarm).
"""

from __future__ import annotations

import asyncio
import inspect
import logging
import math
import os
import random
import string
import time
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("amas.services.human_behavior")

# Known TikTok Captcha DOM selectors (F24)
TIKTOK_CAPTCHA_SELECTORS: List[str] = [
    "#secsdk-captcha-drag-wrapper",
    ".captcha_verify_container",
    ".sec-cpt-container",
    "[data-testid='captcha-verify-container']",
    ".captcha-verify-container",
    "#captcha_container",
    ".slide-verify",
    "div[class*='captcha']",
]

# Common QWERTY keyboard adjacent keys for realistic typo simulation
QWERTY_ADJACENT: Dict[str, str] = {
    "a": "qwsz",
    "b": "vghn",
    "c": "xdfv",
    "d": "ersfxc",
    "e": "wsdr",
    "f": "rtgdvc",
    "g": "tyhfvb",
    "h": "yujgbn",
    "i": "ujko",
    "j": "uikmnh",
    "k": "ijlm",
    "l": "okp",
    "m": "njk",
    "n": "bhjm",
    "o": "iklp",
    "p": "ol",
    "q": "wa",
    "r": "edft",
    "s": "wedxza",
    "t": "rfgy",
    "u": "yhji",
    "v": "cfgb",
    "w": "qase",
    "x": "zsdc",
    "y": "tghu",
    "z": "asx",
}


def compute_cubic_bezier_point(
    p0: Tuple[float, float],
    p1: Tuple[float, float],
    p2: Tuple[float, float],
    p3: Tuple[float, float],
    t: float,
) -> Tuple[float, float]:
    """Calculate (x, y) point along a cubic Bezier curve at parameter t in [0, 1]."""
    u = 1.0 - t
    tt = t * t
    uu = u * u
    uuu = uu * u
    ttt = tt * t

    x = uuu * p0[0] + 3 * uu * t * p1[0] + 3 * u * tt * p2[0] + ttt * p3[0]
    y = uuu * p0[1] + 3 * uu * t * p1[1] + 3 * u * tt * p2[1] + ttt * p3[1]
    return (x, y)


def generate_bezier_trajectory(
    start: Tuple[float, float],
    end: Tuple[float, float],
    steps: int = 20,
    jitter_px: float = 2.0,
) -> List[Tuple[float, float]]:
    """Generate non-linear trajectory with acceleration and random jitter (Feature F22)."""
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    dist = math.hypot(dx, dy)

    deviation = min(100.0, dist * 0.3)
    p1 = (
        start[0] + dx * 0.25 + random.uniform(-deviation, deviation),
        start[1] + dy * 0.25 + random.uniform(-deviation, deviation),
    )
    p2 = (
        start[0] + dx * 0.75 + random.uniform(-deviation, deviation),
        start[1] + dy * 0.75 + random.uniform(-deviation, deviation),
    )

    points: List[Tuple[float, float]] = []
    for step in range(steps + 1):
        t = step / max(1, steps)
        ease_t = 3 * (t**2) - 2 * (t**3)
        bx, by = compute_cubic_bezier_point(start, p1, p2, end, ease_t)
        jitter_x = random.uniform(-jitter_px, jitter_px)
        jitter_y = random.uniform(-jitter_px, jitter_px)
        points.append((round(bx + jitter_x, 2), round(by + jitter_y, 2)))
    return points


class HumanBehaviorService:
    """Biometrics Engine simulating genuine human interaction on Playwright pages."""

    def __init__(self, time_scale: float = 1.0, fast_mode: bool = False) -> None:
        """Initialize HumanBehaviorService biometrics engine.

        Args:
            time_scale: Global timing acceleration factor (default 1.0 for authentic biometrics).
                Values < 1.0 accelerate timing for testing or simulated environments.
            fast_mode: Convenience flag; if True, applies an accelerated scale factor (0.01)
                unless an explicit time_scale is specified. Default is False.

        Raises:
            ValueError: If time_scale is negative.
        """
        if time_scale < 0:
            raise ValueError("time_scale must be non-negative (>= 0.0)")
        self.fast_mode = fast_mode
        self.time_scale = time_scale

    @staticmethod
    async def _safe_await(result: Any) -> Any:
        """Helper to await coroutines while handling synchronous mocks transparently."""
        if inspect.isawaitable(result):
            return await result
        return result

    # --------------------------------------------------------------------------
    # F20: Inertial Human Scrolling
    # --------------------------------------------------------------------------
    async def human_scroll(self, page: Any, steps: int = 5) -> None:
        """Scroll mouse wheel with acceleration curve and reverse rollback overshoot.

        Args:
            page: Playwright Page instance or mock.
            steps: Number of forward scroll steps (must be > 0).

        Raises:
            ValueError: If steps <= 0.
        """
        if steps <= 0:
            raise ValueError("Steps must be a positive integer (> 0)")

        mouse = getattr(page, "mouse", None)
        has_wheel = mouse is not None and hasattr(mouse, "wheel")

        for i in range(steps):
            delta_y = int(150 + (i * 20) + random.uniform(-10, 10))
            if has_wheel:
                res = mouse.wheel(0, delta_y)
                await self._safe_await(res)

            # Small inter-tick pause (10ms - 40ms in test-friendly range)
            await asyncio.sleep(random.uniform(0.01, 0.04))

            # Reverse overshoot (10% - 20% rollback scroll) to mimic human overscroll
            # Triggers on index 0 or every 3 steps (or ~20% probability)
            if i % 3 == 0 or random.random() < 0.20:
                rollback_ratio = random.uniform(0.10, 0.20)
                rollback_delta = -int(delta_y * rollback_ratio)
                if rollback_delta >= 0:
                    rollback_delta = -30
                if has_wheel:
                    res_bounce = mouse.wheel(0, rollback_delta)
                    await self._safe_await(res_bounce)
                await asyncio.sleep(random.uniform(0.01, 0.04))

    # --------------------------------------------------------------------------
    # F21: Biometric Typing Simulation
    # --------------------------------------------------------------------------
    async def human_type(
        self,
        page: Any,
        selector: str,
        text: str,
        typo_rate: float = 0.03,
    ) -> None:
        """Biometric typing with variable delay (80-220ms), micro-pauses, and typo correction.

        Args:
            page: Playwright Page instance or mock.
            selector: CSS selector of the text input/textarea.
            text: Text to be typed.
            typo_rate: Probability of typo per character (default 0.03 = 3%).
        """
        if not text:
            return

        if selector and hasattr(page, "click"):
            click_res = page.click(selector)
            await self._safe_await(click_res)
            await asyncio.sleep(random.uniform(0.02, 0.05))

        keyboard = getattr(page, "keyboard", None)
        has_press = keyboard is not None and hasattr(keyboard, "press")

        for idx, char in enumerate(text):
            is_sentence_boundary = char in {".", ",", "!", "?", ";", "\n"}
            is_before_hashtag = (idx + 1 < len(text) and text[idx + 1] == "#") or char == "#"

            # 1. Typo simulation
            should_typo = (typo_rate >= 1.0) or (typo_rate > 0.0 and random.random() < typo_rate)
            if should_typo and has_press:
                lower_char = char.lower()
                candidates = QWERTY_ADJACENT.get(lower_char, string.ascii_lowercase)
                wrong_char = random.choice(candidates) if candidates else "x"
                if wrong_char == char:
                    wrong_char = "z" if char != "z" else "q"

                p_wrong = keyboard.press(wrong_char)
                await self._safe_await(p_wrong)
                await asyncio.sleep(random.uniform(0.25, 0.35))

                p_bs = keyboard.press("Backspace")
                await self._safe_await(p_bs)
                await asyncio.sleep(random.uniform(0.10, 0.20))

            # 2. Type intended character
            if has_press:
                p_correct = keyboard.press(char)
                await self._safe_await(p_correct)

            # 3. Post-keystroke timing
            if is_sentence_boundary or is_before_hashtag:
                pause = random.uniform(0.60, 1.40)
                await asyncio.sleep(pause)
            else:
                delay = random.uniform(0.08, 0.22)
                await asyncio.sleep(delay)

    # --------------------------------------------------------------------------
    # F22: Bezier Mouse Movement & Pre-click Hover
    # --------------------------------------------------------------------------
    async def human_move_and_click(self, page: Any, selector: str) -> None:
        """Hover over element with natural delay before clicking (Feature F22).

        Args:
            page: Playwright Page instance or mock.
            selector: Target element CSS selector.
        """
        if hasattr(page, "hover"):
            hover_res = page.hover(selector)
            await self._safe_await(hover_res)

        await asyncio.sleep(random.uniform(0.20, 0.40))

        if hasattr(page, "click"):
            click_res = page.click(selector)
            await self._safe_await(click_res)

    # --------------------------------------------------------------------------
    # F23: Pre-posting Feed Warmup Session
    # --------------------------------------------------------------------------
    async def warmup_feed_session(
        self,
        page: Any,
        duration_seconds: int = 180,
        time_scale: Optional[float] = None,
        fast_mode: Optional[bool] = None,
    ) -> bool:
        """Browse tiktok.com feed for designated duration before publishing (Feature F23).

        Simulates authentic human browsing behavior prior to video upload:
        - Navigates to tiktok.com homepage
        - Divides duration_seconds authentically across 3 to 5 random videos
        - Watches each video for (duration_seconds / video_count) seconds
        - Randomly engages with like ('l' key) and scrolls between videos with inertial acceleration.

        Args:
            page: Playwright Page instance or mock.
            duration_seconds: Total warmup session length in seconds (default 180s = 3 mins).
            time_scale: Optional multiplier for sleep intervals (default None, uses self.time_scale;
                set to 1.0 for authentic real-time simulation, or < 1.0 in fast test harnesses).
            fast_mode: Optional flag; if True, applies an accelerated scale factor (0.01)
                unless an explicit time_scale is specified. Defaults to None (uses self.fast_mode).

        Returns:
            True upon successful completion.

        Raises:
            ValueError: If duration_seconds < 0 or effective time_scale < 0.
        """
        if duration_seconds < 0:
            raise ValueError("duration_seconds must be a non-negative integer (>= 0)")

        is_fast = fast_mode if fast_mode is not None else self.fast_mode

        if time_scale is not None:
            effective_scale = time_scale
        elif is_fast:
            effective_scale = 0.01
        else:
            effective_scale = self.time_scale

        if effective_scale < 0:
            raise ValueError("time_scale must be non-negative (>= 0.0)")

        if duration_seconds == 0:
            logger.info("Feed warmup session skipped (duration_seconds=0).")
            return True

        logger.info(
            f"Starting pre-posting feed warmup session "
            f"({duration_seconds}s target, time_scale={effective_scale})..."
        )

        if hasattr(page, "goto"):
            goto_res = page.goto("https://www.tiktok.com")
            await self._safe_await(goto_res)

        video_count = random.randint(3, 5)
        watch_per_video = duration_seconds / max(1, video_count)

        for _ in range(video_count):
            sleep_duration = watch_per_video * effective_scale
            if sleep_duration > 0:
                await asyncio.sleep(sleep_duration)

            if random.random() < 0.25 and hasattr(page, "keyboard") and hasattr(page.keyboard, "press"):
                press_res = page.keyboard.press("l")
                await self._safe_await(press_res)
                await asyncio.sleep(0.01 * effective_scale)

            await self.human_scroll(page, steps=random.randint(2, 4))

        logger.info("Feed warmup session completed successfully.")
        return True

    # --------------------------------------------------------------------------
    # F24: Emergency Captcha Guard
    # --------------------------------------------------------------------------
    async def detect_and_handle_captcha(
        self,
        page: Any,
        telegram_bot: Optional[Any] = None,
        channel_id: str = "",
        screenshot_path: Optional[str] = None,
    ) -> bool:
        """Inspect page for Captcha challenges, halt operations, screenshot, and alert Telegram.

        Args:
            page: Playwright Page instance or mock.
            telegram_bot: Optional TelegramCommandCenter instance or bot mock.
            channel_id: Identifier of the active channel for alert context.
            screenshot_path: Custom path to save screenshot (defaults to 'screenshots/captcha_detected.png').

        Returns:
            True if Captcha was detected and emergency procedures executed, False otherwise.
        """
        is_captcha = False

        if hasattr(page, "is_visible"):
            for sel in TIKTOK_CAPTCHA_SELECTORS:
                try:
                    res = page.is_visible(sel)
                    visible = await self._safe_await(res)
                    if visible is True:
                        is_captcha = True
                        logger.warning(f"TikTok Captcha detected via selector: {sel}")
                        break
                except Exception as e:
                    logger.debug(f"Selector check for {sel} threw: {e}")

        if not is_captcha and hasattr(page, "url"):
            current_url = getattr(page, "url", "")
            if isinstance(current_url, str) and (
                "captcha" in current_url.lower() or "verify" in current_url.lower()
            ):
                is_captcha = True

        if not is_captcha:
            return False

        logger.critical("EMERGENCY CAPTCHA GUARD TRIGGERED! Halting all automated publisher actions.")

        final_screenshot_path = screenshot_path or "screenshots/captcha_detected.png"
        parent_dir = os.path.dirname(final_screenshot_path) or "screenshots"
        os.makedirs(parent_dir, exist_ok=True)

        if hasattr(page, "screenshot"):
            try:
                s_res = page.screenshot(path=final_screenshot_path)
                await self._safe_await(s_res)
                logger.info(f"Emergency Captcha screenshot saved to: {final_screenshot_path}")
            except Exception as e:
                logger.error(f"Failed to capture Captcha screenshot: {e}")

        if telegram_bot:
            try:
                chan_str = f" - KÊNH {channel_id}" if channel_id else ""
                alert_text = (
                    f"🚨 [CẢNH BÁO CAPTCHA TIKTOK{chan_str}]\n"
                    f"Phát hiện màn hình yêu cầu xác minh danh tính. Bot đã tạm dừng an toàn!\n"
                    f"👉 Vui lòng mở trình duyệt giải bằng tay trong vòng 5 phút."
                )
                if hasattr(telegram_bot, "send_message"):
                    admin_id = getattr(telegram_bot, "admin_id", 987654321)
                    await self._safe_await(telegram_bot.send_message(chat_id=admin_id, text=alert_text))
                elif hasattr(telegram_bot, "send_captcha_alert"):
                    await self._safe_await(
                        telegram_bot.send_captcha_alert(
                            channel_id=channel_id,
                            screenshot_path=final_screenshot_path,
                        )
                    )
            except Exception as e:
                logger.error(f"Failed to dispatch Telegram emergency alert: {e}")

        return True
