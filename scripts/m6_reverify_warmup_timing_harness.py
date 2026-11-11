#!/usr/bin/env python3
"""AMAS v1.4.0 — Empirical Challenger Re-verification Harness for Milestone 6.

Deep Stress Testing & Verification for:
- warmup_feed_session time_scale and fast_mode behaviors
- Wall-clock genuine sleep vs accelerated sleep
- Sleep cap absence (180s & 300s durations)
- Configuration precedence matrix (class level vs call level)
- Boundary and error handling
"""

from __future__ import annotations

import asyncio
import math
import sys
import time
from pathlib import Path
from typing import List, Tuple
from unittest.mock import AsyncMock, MagicMock, patch

# Ensure project root in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.services.human_behavior import HumanBehaviorService


class ReverifyReport:
    def __init__(self, name: str) -> None:
        self.name = name
        self.assertions = 0
        self.passed = 0
        self.failed = 0
        self.errors: List[str] = []

    def check(self, condition: bool, description: str) -> None:
        self.assertions += 1
        if condition:
            self.passed += 1
        else:
            self.failed += 1
            self.errors.append(description)
            print(f"  ❌ FAIL: {description}")


async def test_fast_mode_and_time_scale_wall_clock(report: ReverifyReport) -> None:
    print("\n--- Test Suite 1: Wall-Clock Timing Verification (No Sleep Mocking) ---")
    page = MagicMock()
    page.goto = AsyncMock()
    page.mouse = MagicMock()
    page.mouse.wheel = AsyncMock()
    page.keyboard = MagicMock()
    page.keyboard.press = AsyncMock()

    # 1. fast_mode=True with 1s duration
    service_fast = HumanBehaviorService(fast_mode=True)
    t0 = time.perf_counter()
    res1 = await service_fast.warmup_feed_session(page, duration_seconds=1)
    t1 = time.perf_counter()
    elapsed1 = t1 - t0
    report.check(res1 is True, "warmup_feed_session returns True with fast_mode=True")
    report.check(
        elapsed1 < 0.6,
        f"fast_mode=True (1s) finishes fast in real wall-clock time (< 0.6s, actual: {elapsed1:.3f}s)",
    )

    # 2. time_scale=0.01 with 1s duration
    service_normal = HumanBehaviorService(fast_mode=False, time_scale=1.0)
    t0 = time.perf_counter()
    res2 = await service_normal.warmup_feed_session(page, duration_seconds=1, time_scale=0.01)
    t1 = time.perf_counter()
    elapsed2 = t1 - t0
    report.check(res2 is True, "warmup_feed_session returns True with time_scale=0.01")
    report.check(
        elapsed2 < 0.6,
        f"time_scale=0.01 (1s) finishes fast in real wall-clock time (< 0.6s, actual: {elapsed2:.3f}s)",
    )

    # 3. Genuine real sleep: fast_mode=False and time_scale=1.0 with duration_seconds=1
    # Genuine sleep must take >= 1.0s in real wall-clock time!
    t0 = time.perf_counter()
    res3 = await service_normal.warmup_feed_session(page, duration_seconds=1)
    t1 = time.perf_counter()
    elapsed3 = t1 - t0
    report.check(res3 is True, "warmup_feed_session returns True with authentic 1.0 scale")
    report.check(
        elapsed3 >= 1.0,
        f"Authentic scale=1.0 (1s) MUST sleep >= 1.0s in wall-clock time (actual: {elapsed3:.3f}s)",
    )


async def test_timing_intercept_oracle(report: ReverifyReport) -> None:
    print("\n--- Test Suite 2: Intercepted Sleep Durations & Capping Invariants ---")
    page = MagicMock()
    page.goto = AsyncMock()
    page.mouse = MagicMock()
    page.mouse.wheel = AsyncMock()
    page.keyboard = MagicMock()
    page.keyboard.press = AsyncMock()

    service = HumanBehaviorService(time_scale=1.0, fast_mode=False)

    # 1. 180 seconds genuine duration (3 minutes)
    recorded_sleeps: List[float] = []

    async def intercept_sleep(secs: float):
        recorded_sleeps.append(secs)

    with patch("asyncio.sleep", side_effect=intercept_sleep):
        await service.warmup_feed_session(page, duration_seconds=180, time_scale=1.0)

    # Video watch sleeps are significantly larger than scroll sleeps (which are 0.01-0.04s)
    video_sleeps = [s for s in recorded_sleeps if s > 1.0]
    report.check(
        len(video_sleeps) in (3, 4, 5),
        f"Video count strictly in [3, 5], got {len(video_sleeps)}",
    )
    total_video_sleep = sum(video_sleeps)
    report.check(
        math.isclose(total_video_sleep, 180.0, rel_tol=1e-5),
        f"Total video watch sleep for 180s duration must equal 180.0s (got {total_video_sleep:.4f}s)",
    )
    # Check that individual video sleeps are NOT capped to 0.5s
    for idx, vs in enumerate(video_sleeps):
        report.check(
            vs >= 36.0,
            f"Video {idx+1} sleep {vs:.2f}s is uncapped (must be >= 36.0s for 180s total across max 5 videos)",
        )

    # 2. 300 seconds genuine duration (5 minutes)
    recorded_sleeps.clear()
    with patch("asyncio.sleep", side_effect=intercept_sleep):
        await service.warmup_feed_session(page, duration_seconds=300, time_scale=1.0)

    video_sleeps_300 = [s for s in recorded_sleeps if s > 1.0]
    report.check(
        len(video_sleeps_300) in (3, 4, 5),
        f"Video count for 300s strictly in [3, 5], got {len(video_sleeps_300)}",
    )
    total_video_sleep_300 = sum(video_sleeps_300)
    report.check(
        math.isclose(total_video_sleep_300, 300.0, rel_tol=1e-5),
        f"Total video watch sleep for 300s duration must equal 300.0s (got {total_video_sleep_300:.4f}s)",
    )
    for idx, vs in enumerate(video_sleeps_300):
        report.check(
            vs >= 60.0,
            f"Video {idx+1} sleep {vs:.2f}s is uncapped (must be >= 60.0s for 300s total across max 5 videos)",
        )


async def test_precedence_and_matrix(report: ReverifyReport) -> None:
    print("\n--- Test Suite 3: Configuration Precedence Matrix ---")
    page = MagicMock()
    page.goto = AsyncMock()
    page.mouse = MagicMock()
    page.mouse.wheel = AsyncMock()

    recorded: List[float] = []

    async def intercept(s: float):
        recorded.append(s)

    # Matrix Case 1: default init -> scale 1.0
    s1 = HumanBehaviorService()
    recorded.clear()
    with patch("asyncio.sleep", side_effect=intercept):
        await s1.warmup_feed_session(page, duration_seconds=100)
    v1 = [s for s in recorded if s > 1.0]
    report.check(
        math.isclose(sum(v1), 100.0, rel_tol=1e-5),
        f"Default instance uses scale 1.0: sum = {sum(v1):.2f}s (expected 100.0s)",
    )

    # Matrix Case 2: init time_scale=0.5 -> scale 0.5
    s2 = HumanBehaviorService(time_scale=0.5)
    recorded.clear()
    with patch("asyncio.sleep", side_effect=intercept):
        await s2.warmup_feed_session(page, duration_seconds=100)
    v2 = [s for s in recorded if s > 1.0]
    report.check(
        math.isclose(sum(v2), 50.0, rel_tol=1e-5),
        f"Instance time_scale=0.5 scales sum = {sum(v2):.2f}s (expected 50.0s)",
    )

    # Matrix Case 3: init fast_mode=True -> scale 0.01
    s3 = HumanBehaviorService(fast_mode=True)
    recorded.clear()
    with patch("asyncio.sleep", side_effect=intercept):
        await s3.warmup_feed_session(page, duration_seconds=100)
    v3 = [s for s in recorded if s >= 0.15]
    report.check(
        math.isclose(sum(v3), 1.0, rel_tol=1e-5),
        f"Instance fast_mode=True scales sum = {sum(v3):.2f}s (expected 1.0s)",
    )

    # Matrix Case 4: init fast_mode=False, call override fast_mode=True
    s4 = HumanBehaviorService(fast_mode=False)
    recorded.clear()
    with patch("asyncio.sleep", side_effect=intercept):
        await s4.warmup_feed_session(page, duration_seconds=100, fast_mode=True)
    v4 = [s for s in recorded if s >= 0.15]
    report.check(
        math.isclose(sum(v4), 1.0, rel_tol=1e-5),
        f"Call-level fast_mode=True overrides instance fast_mode=False: sum = {sum(v4):.2f}s (expected 1.0s)",
    )

    # Matrix Case 5: init fast_mode=True, call override fast_mode=False
    s5 = HumanBehaviorService(fast_mode=True, time_scale=1.0)
    recorded.clear()
    with patch("asyncio.sleep", side_effect=intercept):
        await s5.warmup_feed_session(page, duration_seconds=100, fast_mode=False)
    v5 = [s for s in recorded if s > 1.0]
    report.check(
        math.isclose(sum(v5), 100.0, rel_tol=1e-5),
        f"Call-level fast_mode=False overrides instance fast_mode=True: sum = {sum(v5):.2f}s (expected 100.0s)",
    )

    # Matrix Case 6: call provides both time_scale and fast_mode: time_scale takes precedence
    s6 = HumanBehaviorService()
    recorded.clear()
    with patch("asyncio.sleep", side_effect=intercept):
        await s6.warmup_feed_session(page, duration_seconds=100, time_scale=0.05, fast_mode=True)
    v6 = [s for s in recorded if s >= 0.5]
    report.check(
        math.isclose(sum(v6), 5.0, rel_tol=1e-5),
        f"Explicit time_scale=0.05 takes precedence over fast_mode=True: sum = {sum(v6):.2f}s (expected 5.0s)",
    )


async def test_boundary_and_validation(report: ReverifyReport) -> None:
    print("\n--- Test Suite 4: Boundary Invariants & Exception Guardrails ---")
    page = MagicMock()
    page.goto = AsyncMock()

    service = HumanBehaviorService()

    # 1. Negative duration_seconds
    try:
        await service.warmup_feed_session(page, duration_seconds=-1)
        report.check(False, "Negative duration_seconds=-1 must raise ValueError")
    except ValueError as e:
        report.check("duration_seconds" in str(e), f"Negative duration_seconds raises ValueError: {e}")

    # 2. Negative call time_scale
    try:
        await service.warmup_feed_session(page, duration_seconds=10, time_scale=-0.1)
        report.check(False, "Negative time_scale must raise ValueError")
    except ValueError as e:
        report.check("time_scale" in str(e), f"Negative call time_scale raises ValueError: {e}")

    # 3. Negative init time_scale
    try:
        HumanBehaviorService(time_scale=-1.0)
        report.check(False, "Negative init time_scale must raise ValueError")
    except ValueError as e:
        report.check("time_scale" in str(e), f"Negative init time_scale raises ValueError: {e}")

    # 4. Zero duration skips without goto
    page_zero = MagicMock()
    page_zero.goto = AsyncMock()
    res_zero = await service.warmup_feed_session(page_zero, duration_seconds=0)
    report.check(res_zero is True, "duration_seconds=0 returns True")
    page_zero.goto.assert_not_called()
    report.check(True, "duration_seconds=0 cleanly bypasses navigation and video loop")

    # 5. time_scale = 0.0 (instantaneous execution)
    page_instant = MagicMock()
    page_instant.goto = AsyncMock()
    page_instant.mouse = MagicMock()
    page_instant.mouse.wheel = AsyncMock()
    res_instant = await service.warmup_feed_session(
        page_instant, duration_seconds=180, time_scale=0.0
    )
    report.check(res_instant is True, "time_scale=0.0 executes and returns True")


async def main() -> int:
    print("=" * 80)
    print("🔬 EMPIRICAL CHALLENGER: Milestone 6 Timing & Scalability Re-verification")
    print("=" * 80)

    report = ReverifyReport("M6 Warmup Timing & Scalability Challenger Suite")

    await test_fast_mode_and_time_scale_wall_clock(report)
    await test_timing_intercept_oracle(report)
    await test_precedence_and_matrix(report)
    await test_boundary_and_validation(report)

    print("\n" + "=" * 80)
    print(f"SUMMARY: {report.passed}/{report.assertions} passed ({(report.passed/report.assertions)*100:.1f}%)")
    print(f"Failures: {report.failed}")
    if report.failed == 0:
        print("VERDICT: APPROVE (Timing and scaling behavior empirically verified)")
    else:
        print("VERDICT: REQUEST_CHANGES")
        for err in report.errors:
            print(f"  - {err}")
    print("=" * 80)

    return 0 if report.failed == 0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
