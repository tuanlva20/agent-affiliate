## 2026-11-10T15:00:56Z

You are m6_explorer_2, an exploration agent investigating HumanBehaviorService for Milestone 6 (Task 6: Human Behavioral Biometrics Engine & Smart Publisher).

Working directory: /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m6_explorer_2/
Read ORIGINAL_REQUEST.md first: /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/ORIGINAL_REQUEST.md
Also read:
- /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/PROJECT.md
- /Users/tuanlva/Folder/workSpace/affiliate/SYSTEM_SPEC.md (Section 3: Quy chuẩn mô phỏng hành vi sinh trắc học)
- /Users/tuanlva/Folder/workSpace/affiliate/docs/superpowers/plans/2026-11-10-autonomous-affiliate-system.md (Task 6)
- /Users/tuanlva/Folder/workSpace/affiliate/tests/e2e/test_tier1_features.py (F20, F21, F22, F23, F24)

Your Focus:
1. Detailed algorithm & implementation design for `HumanBehaviorService` (`src/services/human_behavior.py`):
   - `human_scroll(page: Page, steps: int = 5) -> None`:
     * Mouse wheel scrolling with acceleration curve (variable delta_y, small pauses).
     * Occasional reverse overshoot (10%-20% rollback scroll) to mimic human overscroll.
   - `human_type(page: Page, selector: str, text: str, typo_rate: float = 0.03) -> None`:
     * Keystroke delay randomly sampled in 80ms - 220ms (0.08s - 0.22s).
     * Typo simulation: with probability `typo_rate`, type an adjacent/random wrong key, pause 300ms, press 'Backspace', pause, then type correct char.
     * Micro-pauses: 0.6s - 1.4s at sentence boundaries or before hashtag (#).
   - `human_move_and_click(page: Page, selector: str) -> None`:
     * Hover over selector, natural delay 200ms - 400ms, then click (or mousedown -> delay -> mouseup).
   - `warmup_feed_session(page: Page, duration_seconds: int = 180) -> bool`:
     * Navigate to https://www.tiktok.com, browse feed, scroll through 3-5 videos, simulate watching, optional random like.
   - `detect_and_handle_captcha(page: Page, telegram_bot: Optional[Any] = None) -> bool`:
     * Check selectors for Captcha (sec-cpt-container, captcha-verify-container, slide verify, etc., or `is_visible`).
     * If detected: IMMEDIATELY halt operations, take screenshot saved to `screenshots/captcha_<timestamp>.png` (ensure `screenshots/` exists), send emergency alert via Telegram Bot (with alert text containing "CẢNH BÁO CAPTCHA" and channel info), return True.
2. Test Strategy for `tests/test_human_behavior.py`:
   - Unit tests mocking Playwright Page, Mouse, Keyboard.
   - Test `human_scroll` call counts and delta variations.
   - Test `human_type` with `typo_rate=0.0` (exact length) and `typo_rate=1.0` (guaranteed Backspace).
   - Test `human_move_and_click` hover before click.
   - Test `warmup_feed_session` timing and navigation.
   - Test `detect_and_handle_captcha` detecting visible captcha, creating screenshot, and sending Telegram message.

Deliverables:
- Write comprehensive blueprint and analysis to `/Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m6_explorer_2/handoff.md`.
- Include exact code structure, mathematical timing formulas, mock patterns, and unit tests.
- DO NOT edit or create any source code outside your directory.
- Send a completion message back when done.
