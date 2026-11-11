"""Unit tests for Human Behavioral Biometrics Engine (Milestone 6, Task 6, Features F20-F24)."""

from __future__ import annotations

import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.human_behavior import (
    HumanBehaviorService,
    compute_cubic_bezier_point,
    generate_bezier_trajectory,
)


class TestHumanScroll:
    """Tests for Feature F20: Inertial Human Scrolling."""

    @pytest.mark.asyncio
    async def test_human_scroll_call_count_and_positive_steps(self):
        page = MagicMock()
        page.mouse = MagicMock()
        page.mouse.wheel = AsyncMock()

        service = HumanBehaviorService()
        await service.human_scroll(page, steps=4)

        # Call count must be >= steps because of reverse overshoot ticks
        assert page.mouse.wheel.call_count >= 4

    @pytest.mark.asyncio
    async def test_human_scroll_variable_acceleration_and_overshoot(self):
        page = MagicMock()
        page.mouse = MagicMock()
        recorded_deltas = []

        async def record_wheel(x, y):
            recorded_deltas.append(y)

        page.mouse.wheel = AsyncMock(side_effect=record_wheel)

        service = HumanBehaviorService()
        await service.human_scroll(page, steps=6)

        # 1. Delta_y must not all be identical (acceleration curve)
        forward_deltas = [d for d in recorded_deltas if d > 0]
        assert len(set(forward_deltas)) > 1

        # 2. Reverse overshoot must have produced at least one negative delta_y
        negative_deltas = [d for d in recorded_deltas if d < 0]
        assert len(negative_deltas) >= 1

    @pytest.mark.asyncio
    async def test_human_scroll_invalid_steps_raises_value_error(self):
        page = MagicMock()
        service = HumanBehaviorService()

        with pytest.raises(ValueError, match="positive integer"):
            await service.human_scroll(page, steps=0)

        with pytest.raises(ValueError, match="positive integer"):
            await service.human_scroll(page, steps=-3)


class TestHumanType:
    """Tests for Feature F21: Biometric Typing Simulation."""

    @pytest.mark.asyncio
    async def test_human_type_zero_typo_rate(self):
        page = MagicMock()
        page.click = AsyncMock()
        page.keyboard = MagicMock()
        pressed_keys = []

        async def record_press(key):
            pressed_keys.append(key)

        page.keyboard.press = AsyncMock(side_effect=record_press)

        service = HumanBehaviorService()
        text = "Váy xinh công sở"
        await service.human_type(page, "#caption_input", text, typo_rate=0.0)

        page.click.assert_awaited_once_with("#caption_input")
        assert len(pressed_keys) == len(text)
        assert "".join(pressed_keys) == text
        assert "Backspace" not in pressed_keys

    @pytest.mark.asyncio
    async def test_human_type_forced_typo_with_backspace(self):
        page = MagicMock()
        page.click = AsyncMock()
        page.keyboard = MagicMock()
        pressed_keys = []

        async def record_press(key):
            pressed_keys.append(key)

        page.keyboard.press = AsyncMock(side_effect=record_press)

        service = HumanBehaviorService()
        # Force typo on every character
        await service.human_type(page, "#caption_input", "Váy", typo_rate=1.0)

        assert "Backspace" in pressed_keys
        assert "V" in pressed_keys
        assert "á" in pressed_keys
        assert "y" in pressed_keys
        # Because every character triggers a typo, Backspace count equals string length
        assert pressed_keys.count("Backspace") == len("Váy")

    @pytest.mark.asyncio
    async def test_human_type_micro_pauses_on_punctuation_and_hashtag(self):
        page = MagicMock()
        page.click = AsyncMock()
        page.keyboard = MagicMock()
        page.keyboard.press = AsyncMock()

        service = HumanBehaviorService()
        sleep_durations = []

        async def mock_sleep(seconds):
            sleep_durations.append(seconds)

        with patch("asyncio.sleep", side_effect=mock_sleep):
            await service.human_type(page, "#caption_input", "A. #B", typo_rate=0.0)

        # Pauses for '.' and '#' must be in [0.6, 1.4]
        long_pauses = [d for d in sleep_durations if d >= 0.55]
        assert len(long_pauses) >= 2

    @pytest.mark.asyncio
    async def test_human_type_empty_text(self):
        page = MagicMock()
        page.click = AsyncMock()
        page.keyboard = MagicMock()
        page.keyboard.press = AsyncMock()

        service = HumanBehaviorService()
        await service.human_type(page, "#caption_input", "", typo_rate=0.0)
        page.click.assert_not_called()
        page.keyboard.press.assert_not_called()


class TestHumanMoveAndClick:
    """Tests for Feature F22: Bezier Mouse Movement & Hover Before Click."""

    @pytest.mark.asyncio
    async def test_human_move_and_click_hover_then_click(self):
        page = MagicMock()
        call_sequence = []

        async def mock_hover(sel):
            call_sequence.append(("hover", sel))

        async def mock_click(sel):
            call_sequence.append(("click", sel))

        page.hover = AsyncMock(side_effect=mock_hover)
        page.click = AsyncMock(side_effect=mock_click)

        service = HumanBehaviorService()
        await service.human_move_and_click(page, "button#upload")

        page.hover.assert_awaited_once_with("button#upload")
        page.click.assert_awaited_once_with("button#upload")
        assert call_sequence == [("hover", "button#upload"), ("click", "button#upload")]

    def test_bezier_trajectory_math(self):
        start = (100.0, 100.0)
        end = (500.0, 400.0)
        points = generate_bezier_trajectory(start, end, steps=10, jitter_px=2.0)
        assert len(points) == 11
        # First point near start, last point near end
        assert abs(points[0][0] - start[0]) < 10
        assert abs(points[-1][0] - end[0]) < 10


class TestWarmupFeedSession:
    """Tests for Feature F23: Pre-posting Feed Warmup Session."""

    @pytest.mark.asyncio
    async def test_warmup_feed_session_navigation_and_scrolling(self):
        page = MagicMock()
        page.goto = AsyncMock()
        page.mouse = MagicMock()
        page.mouse.wheel = AsyncMock()

        service = HumanBehaviorService()
        success = await service.warmup_feed_session(page, duration_seconds=1)

        assert success is True
        page.goto.assert_awaited_once_with("https://www.tiktok.com")
        assert page.mouse.wheel.call_count >= 1

    @pytest.mark.asyncio
    async def test_warmup_feed_session_genuine_timing_180s(self):
        """Verify duration_seconds=180 results in genuine 180s sleep without artificial caps."""
        page = MagicMock()
        page.goto = AsyncMock()
        page.mouse = MagicMock()
        page.mouse.wheel = AsyncMock()

        service = HumanBehaviorService()
        recorded_sleeps = []

        async def mock_sleep(seconds):
            recorded_sleeps.append(seconds)

        with patch("asyncio.sleep", side_effect=mock_sleep):
            success = await service.warmup_feed_session(page, duration_seconds=180, time_scale=1.0)

        assert success is True
        # Filter for video watch sleeps (duration_seconds / video_count, which is in [36.0, 60.0])
        video_watch_sleeps = [s for s in recorded_sleeps if s >= 30.0]
        assert len(video_watch_sleeps) in (3, 4, 5)
        # Sum of video watch sleeps must equal 180s exactly
        assert abs(sum(video_watch_sleeps) - 180.0) < 1e-4
        # Verify no 0.5s artificial cap is present
        assert all(s > 0.5 for s in video_watch_sleeps)

    @pytest.mark.asyncio
    async def test_warmup_feed_session_time_scale(self):
        """Verify time_scale parameter correctly scales sleep durations for fast testing."""
        page = MagicMock()
        page.goto = AsyncMock()
        page.mouse = MagicMock()
        page.mouse.wheel = AsyncMock()

        service = HumanBehaviorService()
        recorded_sleeps = []

        async def mock_sleep(seconds):
            recorded_sleeps.append(seconds)

        with patch("asyncio.sleep", side_effect=mock_sleep):
            success = await service.warmup_feed_session(page, duration_seconds=180, time_scale=0.1)

        assert success is True
        video_watch_sleeps = [s for s in recorded_sleeps if s >= 3.0]
        assert len(video_watch_sleeps) in (3, 4, 5)
        assert abs(sum(video_watch_sleeps) - 18.0) < 1e-4

    @pytest.mark.asyncio
    async def test_warmup_feed_session_fast_mode(self):
        """Verify fast_mode=True scales timing to 0.01 factor."""
        page = MagicMock()
        page.goto = AsyncMock()
        page.mouse = MagicMock()
        page.mouse.wheel = AsyncMock()

        service = HumanBehaviorService()
        recorded_sleeps = []

        async def mock_sleep(seconds):
            recorded_sleeps.append(seconds)

        with patch("asyncio.sleep", side_effect=mock_sleep):
            success = await service.warmup_feed_session(page, duration_seconds=180, fast_mode=True)

        assert success is True
        video_watch_sleeps = [s for s in recorded_sleeps if s >= 0.30]
        assert len(video_watch_sleeps) in (3, 4, 5)
        assert abs(sum(video_watch_sleeps) - 1.8) < 1e-4

    @pytest.mark.asyncio
    async def test_warmup_feed_session_validation(self):
        """Verify ValueError is raised for negative duration or time_scale."""
        page = MagicMock()
        service = HumanBehaviorService()

        with pytest.raises(ValueError, match="duration_seconds"):
            await service.warmup_feed_session(page, duration_seconds=-10)

        with pytest.raises(ValueError, match="time_scale"):
            await service.warmup_feed_session(page, duration_seconds=10, time_scale=-0.5)

    @pytest.mark.asyncio
    async def test_warmup_feed_session_zero_duration(self):
        """Verify zero duration skips warmup cleanly."""
        page = MagicMock()
        page.goto = AsyncMock()
        service = HumanBehaviorService()

        success = await service.warmup_feed_session(page, duration_seconds=0)
        assert success is True
        page.goto.assert_not_called()

    def test_no_sleep_cap_in_human_behavior_source(self):
        import src.services.human_behavior as hb

        with open(hb.__file__, "r", encoding="utf-8") as f:
            content = f.read()

        assert "min(watch_per_video, 0.5)" not in content, "Found forbidden sleep cap in human_behavior.py"


class TestDetectAndHandleCaptcha:
    """Tests for Feature F24: Emergency Captcha Guard."""

    @pytest.mark.asyncio
    async def test_detect_and_handle_captcha_when_present(self):
        page = MagicMock()
        page.is_visible = AsyncMock(return_value=True)
        page.screenshot = AsyncMock()

        bot = MagicMock()
        bot.admin_id = 987654321
        sent_messages = []

        async def mock_send(chat_id, text):
            sent_messages.append({"chat_id": chat_id, "text": text})

        bot.send_message = AsyncMock(side_effect=mock_send)
        bot.sent_messages = sent_messages

        service = HumanBehaviorService()
        detected = await service.detect_and_handle_captcha(page, telegram_bot=bot)

        assert detected is True
        page.screenshot.assert_awaited_once_with(path="screenshots/captcha_detected.png")
        assert len(sent_messages) == 1
        assert "CẢNH BÁO CAPTCHA" in sent_messages[0]["text"]
        assert "🚨 [CẢNH BÁO CAPTCHA TIKTOK" in sent_messages[0]["text"]

    @pytest.mark.asyncio
    async def test_detect_and_handle_captcha_when_absent(self):
        page = MagicMock()
        page.is_visible = AsyncMock(return_value=False)
        page.url = "https://www.tiktok.com/@me"
        page.screenshot = AsyncMock()

        bot = MagicMock()
        bot.send_message = AsyncMock()

        service = HumanBehaviorService()
        detected = await service.detect_and_handle_captcha(page, telegram_bot=bot)

        assert detected is False
        page.screenshot.assert_not_called()
        bot.send_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_detect_and_handle_captcha_without_bot(self):
        page = MagicMock()
        page.is_visible = AsyncMock(return_value=True)
        page.screenshot = AsyncMock()

        service = HumanBehaviorService()
        detected = await service.detect_and_handle_captcha(page, telegram_bot=None)

        assert detected is True
        page.screenshot.assert_awaited_once()
