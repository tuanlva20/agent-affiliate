# BRIEFING — 2026-11-10T15:08:30Z

## Mission
Investigate and design the HumanBehaviorService and its test strategy for Milestone 6 (Task 6: Human Behavioral Biometrics Engine & Smart Publisher).

## 🔒 My Identity
- Archetype: explorer
- Roles: investigation, synthesis
- Working directory: /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m6_explorer_2/
- Original parent: f5177315-7404-4813-b8ba-56081885cdd4
- Milestone: Milestone 6 (Task 6)

## 🔒 Key Constraints
- Read-only investigation — do NOT implement
- Write only to `/Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m6_explorer_2/`
- No source code edits or creation outside our working directory

## Current Parent
- Conversation ID: f5177315-7404-4813-b8ba-56081885cdd4
- Updated: 2026-11-10T15:08:30Z

## Investigation State
- **Explored paths**:
  - `ORIGINAL_REQUEST.md`, `PROJECT.md`, `SYSTEM_SPEC.md` § 3
  - `docs/superpowers/plans/2026-11-10-autonomous-affiliate-system.md` (Task 6)
  - `tests/e2e/test_tier1_features.py` (F20, F21, F22, F23, F24)
  - `tests/e2e/conftest.py` (HumanBehaviorService contract mock)
  - `src/bot/telegram_bot.py` and `src/bot/formatters.py`
  - `tests/e2e/test_tier2_boundaries.py` (Captcha screenshot assertions)
- **Key findings**:
  - `human_scroll`: Needs variable acceleration delta ($\Delta y = 150 + 20 \cdot i + \text{jitter}$), small pauses (40-150ms), and 15-20% reverse overscroll bounce ($\Delta y < 0$). Must support both async coroutines and sync mocks.
  - `human_type`: Keystrokes delayed 80-220ms. Micro-pauses (0.6-1.4s) on sentence boundaries and before hashtags (#). Typo simulation with `typo_rate` (default 0.03, forced in test to 1.0) types adjacent/wrong key, waits 300ms, presses Backspace, waits, then types correct char.
  - `human_move_and_click`: Must await `page.hover(selector)` first, pause 200-400ms, then await `page.click(selector)` to satisfy exact assertions in `test_f22_bezier_mouse_movement`.
  - `warmup_feed_session`: Must navigate to `https://www.tiktok.com`, browse feed, watch 3-5 videos with proportional delay, scroll between them, and return `True`.
  - `detect_and_handle_captcha`: Must inspect multiple captcha selectors, halt immediately, create screenshot directory `screenshots/` and capture to `screenshots/captcha_<timestamp>.png` (with default alias/fallback to `"screenshots/captcha_detected.png"`), trigger Telegram emergency alarm containing "CẢNH BÁO CAPTCHA", and return `True`.
- **Unexplored areas**: None, all interfaces and test requirements mapped.

## Key Decisions Made
- Architecture design of `HumanBehaviorService` structured as clean modular methods with optional coordinate-based Bezier math helpers.
- Full test plan with 100% deterministic mocking patterns (mocking time/sleep/random where needed).
- Full compatibility with existing Tier 1 (`test_tier1_features.py`), Tier 2 (`test_tier2_boundaries.py`), and dedicated unit tests (`tests/test_human_behavior.py`).

## Artifact Index
- DISPATCH.md — Parent dispatch instructions
- BRIEFING.md — Persistent context & state
- progress.md — Heartbeat & execution checklist
- handoff.md — Comprehensive 5-component blueprint deliverable
