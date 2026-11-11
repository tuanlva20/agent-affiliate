## 2026-11-10T15:26:24Z
[Message] timestamp=2026-11-10T15:26:24Z sender=f5177315-7404-4813-b8ba-56081885cdd4 priority=MESSAGE_PRIORITY_HIGH content=You are m6_challenger_1, an adversarial verifier for Milestone 6 (Task 6: Human Behavioral Biometrics Engine & Smart Publisher với AliasMode).

Working directory: /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m6_challenger_1/
Read ORIGINAL_REQUEST.md first: /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/ORIGINAL_REQUEST.md
Also read:
- /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/PROJECT.md
- /Users/tuanlva/Folder/workSpace/affiliate/SYSTEM_SPEC.md (Section 3: Quy chuẩn mô phỏng hành vi sinh trắc học)
- Implementation: /Users/tuanlva/Folder/workSpace/affiliate/src/services/human_behavior.py
- Tests: /Users/tuanlva/Folder/workSpace/affiliate/tests/test_human_behavior.py

Your Mandate — Adversarial Stress Testing of Biometrics Engine:
1. Write a standalone adversarial stress test harness: `scripts/m6_adversarial_biometrics_harness.py`.
2. Attack vectors to stress test:
   - Typing jitter & timing distribution: Sample 500 keystrokes and verify all delays strictly fall within [0.08, 0.22] seconds (80ms - 220ms).
   - Micro-pause distribution: Sample 100 pause points and verify delays strictly fall within [0.6, 1.4] seconds.
   - Typo rate & Backspace integrity:
     * `typo_rate = 0.0`: verify ZERO 'Backspace' presses across 50 strings.
     * `typo_rate = 1.0`: verify EVERY character generates an incorrect key followed by 'Backspace' and then the correct key.
     * `typo_rate = 0.03`: over 1000 characters, verify empirical typo count is reasonably bounded (between 1% and 6%).
   - String boundary torture:
     * Empty string `""`
     * String of pure spaces `"     "`
     * Pure Vietnamese diacritics `"àáảãạăắằẳẵặâấầẩẫậ"`
     * Multi-line text with mixed punctuation and hashtags `"Hook 3s! Đẹp mê ly? Bấm ngay #thoitrang #xuhuong\nLink giỏ hàng."`
     * Unicode emojis `"👗✨🔥🛒"`
   - Scroll torture:
     * `steps = 0`, `steps = -5`: does it reject or handle safely without crashing?
     * `steps = 100`: verify wheel call count >= 100, verify presence of reverse overshoot ticks.
   - Captcha alert torture:
     * Mock page where `is_visible` raises unexpected error: does it catch or log safely?
     * Captcha detected: verify screenshot file is actually created in `screenshots/` directory, verify Telegram message text contains `"CẢNH BÁO CAPTCHA"`.
     * Bot object with no `send_message` or invalid admin_id: verify graceful degradation without unhandled crash.
3. Execute the harness: `python3 scripts/m6_adversarial_biometrics_harness.py`.
4. Report:
   - Document number of test cases passed, failure count, execution output.
   - If ANY assertion fails, issue `REQUEST_CHANGES` with exact reproducible evidence.
   - If ALL assertions pass, issue `APPROVE`.
   - Write `/Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m6_challenger_1/handoff.md`.
   - Send message back to parent with verdict.
