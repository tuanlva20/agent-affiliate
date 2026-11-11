## 2026-11-10T15:11:10Z
You are worker_m6_1, a versatile implementation worker assigned to Milestone 6 (Task 6: Human Behavioral Biometrics Engine & Smart Publisher với AliasMode).

Working directory: /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/worker_m6_1/
Read ORIGINAL_REQUEST.md first: /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/ORIGINAL_REQUEST.md

Also read the detailed Explorer architectural blueprints before writing code:
- /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m6_explorer_1/handoff.md (BrowserAdapter Architecture & Test Blueprint)
- /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m6_explorer_2/handoff.md (HumanBehaviorService Biometrics Engine & Test Blueprint)
- /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m6_explorer_3/handoff.md (SmartPublisher Lifecycle & Test Blueprint)
- /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/PROJECT.md
- /Users/tuanlva/Folder/workSpace/affiliate/SYSTEM_SPEC.md (Section 3: Quy chuẩn mô phỏng hành vi sinh trắc học; Section 4: Trạng thái vòng đời kênh)
- /Users/tuanlva/Folder/workSpace/affiliate/tests/e2e/test_tier1_features.py (F19-F25)
- /Users/tuanlva/Folder/workSpace/affiliate/tests/e2e/test_tier2_boundaries.py (KeyError boundary on missing profile)

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

File Write Boundaries:
You own exclusively:
- `src/services/browser_adapter.py`
- `src/services/human_behavior.py`
- `src/agents/smart_publisher.py`
- `tests/test_browser_adapter.py`
- `tests/test_human_behavior.py`
- `tests/test_smart_publisher.py`
(If needed for module exports, you may touch `src/services/__init__.py` and `src/agents/__init__.py`).
Do NOT modify unrelated files.

Implementation Requirements:

1. `src/services/browser_adapter.py` (Feature F19):
   - Dual-mode execution:
     * `mock_mode=True` (default in dev/test when live AliasMode API is not running): in-memory dictionary `self.profiles`, generates `alias_prof_{N}` IDs and `ws://127.0.0.1:50325/devtools/browser/{profile_id}` endpoints.
     * `mock_mode=False`: async HTTP calls via `aiohttp.ClientSession` to `http://127.0.0.1:50325`.
   - Exception Hierarchy with multiple inheritance:
     * `BrowserAdapterError(Exception)`
     * `BrowserProfileNotFoundError(KeyError, BrowserAdapterError)` -> Crucial: MUST inherit from `KeyError` to satisfy `test_tier2_boundaries.py:251` (`with pytest.raises(KeyError)`).
     * `BrowserProxyError(ValueError, BrowserAdapterError)`
     * `BrowserConnectionError(ConnectionError, BrowserAdapterError)`
     * `BrowserTimeoutError(TimeoutError, BrowserAdapterError)`
     * `BrowserAPIError(BrowserAdapterError)`
   - Methods:
     * `create_profile(name: str, proxy: Optional[str] = None) -> str`: parses proxy if present, returns `profile_id`.
     * `start_browser(profile_id: str) -> str`: starts profile, returns CDP WebSocket URL. Raises `BrowserProfileNotFoundError` if not found.
     * `stop_browser(profile_id: str) -> bool`: stops profile. Raises `BrowserProfileNotFoundError` if not found.
     * `delete_profile(profile_id: str) -> bool`: removes profile.
     * `open_session(profile_id: str)`: async context manager for starting and stopping browser safely.
     * `connect_over_cdp(cdp_url: str)`: helper to connect Playwright over CDP if playwright is available.

2. `src/services/human_behavior.py` (Features F20-F24):
   - `human_scroll(page: Page, steps: int = 5) -> None`:
     * Scroll using `page.mouse.wheel(0, delta_y)` across multiple steps.
     * Variable acceleration curve (delta_y variation with small pauses).
     * Occasional reverse overshoot (10%-20% rollback scroll) to mimic human overscroll.
     * Must call `page.mouse.wheel` >= `steps` times to satisfy `test_f20`.
   - `human_type(page: Page, selector: str, text: str, typo_rate: float = 0.03) -> None`:
     * Clicks or focuses selector (`await page.click(selector)`).
     * Character-by-character typing with delay between 80ms and 220ms (0.08s - 0.22s).
     * Typo simulation: with probability `typo_rate`, presses a wrong key, sleeps ~300ms, presses 'Backspace', sleeps, then types correct character.
     * Micro-pauses: 0.6s - 1.4s at sentence boundaries (`.`, `!`, `?`, `\n`) or before `#`.
     * When `typo_rate == 0.0`, typed keys count equals text length. When `typo_rate == 1.0`, 'Backspace' is guaranteed to be pressed.
   - `human_move_and_click(page: Page, selector: str) -> None`:
     * Hovers over selector (`await page.hover(selector)`).
     * Natural delay 200ms - 400ms before click.
     * Clicks selector (`await page.click(selector)`).
     * Satisfies `test_f22` assertions (`mock_page.hover.assert_awaited_once_with(...)`, `mock_page.click.assert_awaited_once_with(...)`).
   - `warmup_feed_session(page: Page, duration_seconds: int = 180) -> bool`:
     * Navigates to `https://www.tiktok.com` (`await page.goto("https://www.tiktok.com")`).
     * Loops feed browsing with `human_scroll`, pauses between videos, optional random like.
     * Returns `True`. Satisfies `test_f23`.
   - `detect_and_handle_captcha(page: Page, telegram_bot: Optional[Any] = None) -> bool`:
     * Checks if Captcha elements are visible on page (checks known selectors like `sec-cpt-container`, `captcha-verify-container`, etc. or calls `await page.is_visible(...)`).
     * If visible / detected:
       - Immediately aborts/halts bot operations.
       - Creates `screenshots/` directory if not present.
       - Calls `await page.screenshot(path=...)` saving to `screenshots/captcha_<timestamp>.png`.
       - If `telegram_bot` provided (supports bot with `send_message` or `admin_id` and `sent_messages`), sends emergency alert message containing text `"CẢNH BÁO CAPTCHA"` and instructions.
       - Returns `True`. If no captcha detected, returns `False`.
       - Satisfies `test_f24`.

3. `src/agents/smart_publisher.py` (Feature F25):
   - `PublishResult` dataclass:
     * `success: bool`
     * `video_id: Optional[str] = None`
     * `published_url: Optional[str] = None`
     * `channel_status: str = ""`
     * `error: Optional[str] = None`
     * `metadata: Dict[str, Any] = field(default_factory=dict)`
     * `__post_init__`: if `video_id` and not `published_url`, set `published_url = f"https://www.tiktok.com/@channel/video/{video_id}"`.
   - `SmartPublisher`:
     * `__init__(self, browser_adapter: Optional[BrowserAdapter] = None, human_behavior: Optional[HumanBehaviorService] = None, config: Optional[AppConfig] = None, **kwargs)`
     * Supports `human_svc` keyword argument alias.
     * `publish_video(self, job_id: str, channel: Union[Dict, Channel], video_path: str, caption: str, product_anchor: Optional[Dict] = None, db_session: Optional[AsyncSession] = None) -> PublishResult`:
       - Dual representation handling: read/set attributes on both dict and SQLAlchemy `Channel` ORM instance.
       - Channel lifecycle guard:
         * If `lifecycle_status == 'warming'`: return `PublishResult(success=False, channel_status="warming", error="Cannot publish: channel is in warming stage (nuôi nick); affiliate posting not permitted.")` (must contain substring `"warming stage"`).
         * If `lifecycle_status == 'captcha_blocked'`: return `PublishResult(success=False, channel_status="captcha_blocked", error="Cannot publish: channel is captcha blocked. Manual resolution required.")`.
         * If `lifecycle_status == 'cooldown'`: verify if cooldown period has elapsed.
         * If `lifecycle_status == 'ready_to_post'`:
           - If `video_path` does not exist on disk, check if it's a test environment or return error unless mock/test mode. Note: in `test_f25`, `/tmp/vid.mp4` might not exist on disk, so in mock/test mode or if file doesn't exist, proceed gracefully or treat as test payload!
           - Execute publication steps: starts browser via `browser_adapter.start_browser(profile_id)`, checks captcha via `human_behavior.detect_and_handle_captcha`. If captcha encountered mid-flight: update channel status to `captcha_blocked`, commit db_session if present, return `PublishResult(success=False, channel_status="captcha_blocked", error="Captcha detected during upload")`.
           - Types caption via `human_behavior.human_type`.
           - Attaches product anchor if `product_anchor` provided.
           - On success: updates channel `lifecycle_status = 'cooldown'`, sets `last_posted_at = datetime.now(timezone.utc)`, commits db_session if present, returns `PublishResult(success=True, video_id=f"tt_pub_{job_id}", channel_status="cooldown")`.

4. Strict TDD Process:
   - Step 1: Write `tests/test_browser_adapter.py`, `tests/test_human_behavior.py`, `tests/test_smart_publisher.py` with comprehensive test cases.
   - Step 2: Run pytest to verify tests FAIL (RED phase).
   - Step 3: Implement `src/services/browser_adapter.py`, `src/services/human_behavior.py`, `src/agents/smart_publisher.py` (GREEN phase).
   - Step 4: Run pytest on unit tests and E2E tests (`pytest tests/test_browser_adapter.py tests/test_human_behavior.py tests/test_smart_publisher.py tests/e2e/test_tier1_features.py -v`).
   - Step 5: Run full test suite: `pytest tests/ -v`.
   - Step 6: Write handoff report in `.agents/teamwork/worker_m6_1/handoff.md` with verbatim test execution logs.
   - Step 7: Send completion message back to parent orchestrator.
