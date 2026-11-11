# Remediation Blueprint Report — HumanBehaviorService Timing Integrity (Milestone 6)

**Agent**: `m6_remedy_explorer_2`  
**Target File**: `src/services/human_behavior.py`  
**Violation Remediated**: Audit Finding 4 — Fake Timing & Dummy Sleep Bypass (`min(watch_per_video, 0.5)`) in `warmup_feed_session`  
**Standard**: `SYSTEM_SPEC.md § 3.4`, `ORIGINAL_REQUEST.md Task 6` ("Kịch bản warmup_feed_session lướt feed ngẫu nhiên đúng thời gian quy định")

---

## 1. Observation

Direct empirical evidence gathered from codebase inspection and tool executions:

### Observation 1.1: Dummy Sleep Cap in `src/services/human_behavior.py`
In `src/services/human_behavior.py`, lines 275–280:
```python
        video_count = random.randint(3, 5)
        watch_per_video = max(0.01, duration_seconds / max(1, video_count))

        for _ in range(video_count):
            await asyncio.sleep(min(watch_per_video, 0.5))
```
- Tool output from `grep_search`:
  `{"File":"/Users/tuanlva/Folder/workSpace/affiliate/src/services/human_behavior.py","LineNumber":279,"LineContent":"            await asyncio.sleep(min(watch_per_video, 0.5))"}`
- When `duration_seconds=180` (default 3-minute warm-up session), `watch_per_video` is `180 / 4 = 45.0` seconds.
- However, `min(watch_per_video, 0.5)` forces `asyncio.sleep(0.5)` on every loop iteration.
- Total elapsed sleep time for a designated 180s warmup session is only `video_count * 0.5` = **1.5 to 2.5 seconds**, cutting the warm-up session down by ~98.6%.

### Observation 1.2: Current Unit Test Baseline in `tests/test_human_behavior.py`
In `tests/test_human_behavior.py`, lines 181–198:
```python
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
```
- In `test_warmup_feed_session_navigation_and_scrolling`, `duration_seconds=1` was already passed as an explicit test argument.
- With `video_count = 4`, `1 / 4 = 0.25s`, which is already `< 0.5s`.
- The artificial cap `min(watch_per_video, 0.5)` was completely unnecessary to keep this existing test fast, but it silently crippled real production executions where `duration_seconds >= 180`.

### Observation 1.3: Companion Bypass in `src/agents/smart_publisher.py`
In `src/agents/smart_publisher.py`, lines 232–238:
```python
        warmup_duration = 0 if active_page else 180
        if self.config and hasattr(self.config, "browser"):
            warmup_duration = getattr(self.config.browser, "warmup_duration_seconds", warmup_duration)
        warmup_duration = kwargs.get("warmup_duration", warmup_duration)

        if warmup_duration > 0 and hasattr(self.human_behavior, "warmup_feed_session"):
            await self.human_behavior.warmup_feed_session(p, duration_seconds=warmup_duration)
```
- Line 232 introduced `warmup_duration = 0 if active_page else 180`, which was flagged in the audit as a test-specific bypass flag because `SmartPublisher` tests inject `active_page`.

---

## 2. Logic Chain

1. **Requirement Definition**:
   - `ORIGINAL_REQUEST.md Task 6` requires: *"Kịch bản warmup_feed_session lướt feed ngẫu nhiên đúng thời gian quy định"*.
   - `SYSTEM_SPEC.md § 3.4` dictates a genuine 3–5 minute feed browsing session (`180s` to `300s`) before posting to emulate authentic human biometrics and warm up TikTok session cookies.
2. **Defect Deduction**:
   - The expression `min(watch_per_video, 0.5)` in `src/services/human_behavior.py:279` unconditionally caps each video watch sleep to 500 milliseconds.
   - For a requested 180-second session, the system logs `Starting pre-posting feed warmup session (180s)...` but exits after ~2.4 seconds.
   - This directly violates the rule against "Dummy sleep bypasses or fake timing logic" established in development integrity rules.
3. **Architectural Solution Formulation**:
   - The calculation of per-video watch duration must be authentic:
     $$\text{watch\_per\_video} = \frac{\text{duration\_seconds}}{\max(1, \text{video\_count})}$$
   - When running in production (`time_scale = 1.0`), the system must sleep for the full `watch_per_video` (e.g. 45.0s per video across 4 videos = 180.0s).
   - To accommodate rapid test execution without introducing deceptive caps or test bypass flags in production logic:
     a. Provide an explicit `time_scale: float = 1.0` parameter at both class instantiation (`HumanBehaviorService(time_scale=...)`) and method invocation (`warmup_feed_session(..., time_scale=...)`).
     b. Provide a convenience `fast_mode: bool = False` parameter (setting effective `time_scale = 0.001` if enabled without explicit `time_scale`).
     c. Retain support for explicit small `duration_seconds` (e.g. `1` or `2` seconds), which naturally sleep for genuine 1.0s or 2.0s without any time scaling.
     d. In unit tests testing 180s logic, either pass `time_scale=0.001` / `fast_mode=True` or patch `asyncio.sleep` to assert that sleep durations sum exactly to 180.0s.
4. **Validation Logic**:
   - If `duration_seconds < 0` or `time_scale < 0`, raise `ValueError`.
   - If `duration_seconds == 0`, log and return `True` immediately without unnecessary network or DOM calls.

---

## 3. Caveats

1. **Scoping**: This remediation specifically targets `src/services/human_behavior.py` and its test suite `tests/test_human_behavior.py`. Accompanying adjustments in `src/agents/smart_publisher.py` (removing `warmup_duration = 0 if active_page else 180`) must be executed in coordination with the SmartPublisher remediation agent (`m6_remedy_explorer_1` / implementer).
2. **Playwright Mocking in Unit Tests**: Playwright page interactions (`goto`, `mouse.wheel`, `keyboard.press`) in unit tests remain mock-driven via standard `unittest.mock.MagicMock` inside test files (which is standard and compliant with audit rules; only production code in `src/` must not import or instantiate `unittest.mock`).
3. **No Other Fake Sleeps**: All other sleep calls in `src/services/human_behavior.py` (inertial wheel delays of 10–40ms, typo backspace pauses of 100–350ms, and biometric keypress intervals of 80–220ms with 0.6–1.4s sentence pauses) conform exactly to `SYSTEM_SPEC.md § 3.4` and were verified by the forensic auditor as authentic biometrics.

---

## 4. Conclusion & Actionable Remedy Blueprint

### 4.1 Production Code Replacement for `src/services/human_behavior.py`

#### Change 1: Class Initialization with `time_scale` Support
In `src/services/human_behavior.py`, update class `HumanBehaviorService` (beginning around line 120) to add `__init__`:

```python
class HumanBehaviorService:
    """Biometrics Engine simulating genuine human interaction on Playwright pages."""

    def __init__(self, time_scale: float = 1.0) -> None:
        """Initialize HumanBehaviorService biometrics engine.

        Args:
            time_scale: Global timing acceleration factor (default 1.0 for authentic biometrics).
                Values < 1.0 accelerate timing for testing or simulated environments.

        Raises:
            ValueError: If time_scale is negative.
        """
        if time_scale < 0:
            raise ValueError("time_scale must be non-negative (>= 0.0)")
        self.time_scale = time_scale

    @staticmethod
    async def _safe_await(result: Any) -> Any:
        """Helper to await coroutines while handling synchronous mocks transparently."""
        if inspect.isawaitable(result):
            return await result
        return result
```

#### Change 2: Genuine Timing in `warmup_feed_session` (Lines 255–290)
Replace `warmup_feed_session` in `src/services/human_behavior.py` with the following genuine timing implementation:

```python
    # --------------------------------------------------------------------------
    # F23: Pre-posting Feed Warmup Session
    # --------------------------------------------------------------------------
    async def warmup_feed_session(
        self,
        page: Any,
        duration_seconds: int = 180,
        time_scale: Optional[float] = None,
        fast_mode: bool = False,
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
            fast_mode: Convenience flag; if True, applies an accelerated scale factor (0.001)
                unless an explicit time_scale is specified. Default is False.

        Returns:
            True upon successful completion.

        Raises:
            ValueError: If duration_seconds < 0 or effective time_scale < 0.
        """
        if duration_seconds < 0:
            raise ValueError("duration_seconds must be a non-negative integer (>= 0)")

        if time_scale is not None:
            effective_scale = time_scale
        elif fast_mode:
            effective_scale = 0.001
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
```

---

### 4.2 Comprehensive Unit Test Enhancements for `tests/test_human_behavior.py`

Replace class `TestWarmupFeedSession` in `tests/test_human_behavior.py` (lines 181–198) with:

```python
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
        """Verify fast_mode=True scales timing to 0.001 factor."""
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
        video_watch_sleeps = [s for s in recorded_sleeps if s >= 0.03]
        assert len(video_watch_sleeps) in (3, 4, 5)
        assert abs(sum(video_watch_sleeps) - 0.18) < 1e-4

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
```

---

### 4.3 Integration Guidance for `SmartPublisher` Remediation

In `src/agents/smart_publisher.py`:
- Remove `warmup_duration = 0 if active_page else 180`.
- In production, set default `warmup_duration = 180` (or retrieve from `config.browser.warmup_duration_seconds`).
- When calling `warmup_feed_session`:
  ```python
  warmup_duration = 180
  if self.config and hasattr(self.config, "browser"):
      warmup_duration = getattr(self.config.browser, "warmup_duration_seconds", warmup_duration)
  warmup_duration = kwargs.get("warmup_duration", warmup_duration)

  if warmup_duration > 0 and hasattr(self.human_behavior, "warmup_feed_session"):
      time_scale = kwargs.get("time_scale", getattr(self.human_behavior, "time_scale", 1.0))
      await self.human_behavior.warmup_feed_session(
          p, duration_seconds=warmup_duration, time_scale=time_scale
      )
  ```
- In unit tests for `SmartPublisher`, tests mock `warmup_feed_session` via `mock_human.warmup_feed_session = AsyncMock()`, which avoids real sleeps while ensuring production code executes real sleeps when deployed.

---

## 5. Verification Method

To independently verify the implementation after application:

### Step 5.1: Verify Absence of `min(watch_per_video, 0.5)`
Run ripgrep to ensure zero occurrences of the artificial cap:
```bash
grep -rn "min(watch_per_video, 0.5)" src/
```
*Expected Result*: Zero matches.

### Step 5.2: Execute Unit Tests
Run the human behavior unit test suite:
```bash
pytest tests/test_human_behavior.py -v
```
*Expected Result*: All 18 tests pass with exit code 0.

### Step 5.3: Verify Genuine Timing Assertions
Run the specific warmup test cases:
```bash
pytest tests/test_human_behavior.py -k "TestWarmupFeedSession" -v
```
*Expected Result*:
- `test_warmup_feed_session_navigation_and_scrolling`: PASSED
- `test_warmup_feed_session_genuine_timing_180s`: PASSED (confirms sum of video watch sleeps == 180.0s)
- `test_warmup_feed_session_time_scale`: PASSED (confirms time_scale=0.1 yields sum == 18.0s)
- `test_warmup_feed_session_fast_mode`: PASSED (confirms fast_mode yields sum == 0.18s)
- `test_warmup_feed_session_validation`: PASSED (confirms ValueError on negative inputs)
- `test_warmup_feed_session_zero_duration`: PASSED (confirms instant clean exit)

### Step 5.4: Execute Full Regression Suite
Run all repository tests to ensure zero regressions:
```bash
pytest tests/ -v
```
*Expected Result*: All tests pass (>= 385 tests).

### Invalidation Conditions
This remediation blueprint is invalidated if:
1. An artificial cap (e.g. `min(..., X)`) is reintroduced into sleep duration calculations.
2. Production code silently bypasses warmup when `duration_seconds > 0` and `time_scale == 1.0`.
3. Test suite hangs or takes > 30 seconds due to un-mocked or unscaled 180-second sleeps during general test runs.
