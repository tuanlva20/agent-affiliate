## 2026-11-10T10:25:02Z

You are worker_m4_1, implementing Milestone 4 (Task 4: Telegram Command Center & 1-Tap Approval) following strict TDD.

Working directory: /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/worker_m4_1/
Write ownership:
- `src/bot/` (all files: `__init__.py`, `keyboards.py`, `formatters.py`, `handlers.py`, `telegram_bot.py`)
- `tests/test_telegram_bot.py`
- `.agents/teamwork/worker_m4_1/`

You MUST read:
- ORIGINAL_REQUEST.md at /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/ORIGINAL_REQUEST.md
- PROJECT.md at /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/PROJECT.md
- SYSTEM_SPEC.md at /Users/tuanlva/Folder/workSpace/affiliate/SYSTEM_SPEC.md
- docs/superpowers/plans/2026-11-10-autonomous-affiliate-system.md (Task 4)
- m4_explorer_1 handoff at /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m4_explorer_1/handoff.md
- m4_explorer_2 handoff at /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m4_explorer_2/handoff.md
- m4_explorer_3 handoff at /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m4_explorer_3/handoff.md
- tests/e2e/test_tier1_features.py (lines 300-340 for F10, F11, F12 contracts)

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Detailed Tasks:
1. TDD Step 1 (RED Phase):
   - Author `tests/test_telegram_bot.py` covering:
     * F10 Forum Topic Routing: `route_topic` mapping (`thoi_trang_nu` -> 101, `do_gia_dung` -> 102, `dashboard_tong` / unknown -> 100)
     * F11 1-Tap Approval Keyboards: `get_approval_keyboard("prod_123")` dual subscripting (`kb["inline_keyboard"][0]`) and button callbacks (`approve_product:prod_123`, `reject_product:prod_123`)
     * F12 Bot Command Center: Authorized admin commands (`/test_scout`, `/test_video`, `/test_reply`, `/status`, `/create_channel`, `/warmup`) and unauthorized non-admin rejection ("⛔ Quyền truy cập bị từ chối: Bạn không phải Admin!")
     * Card formatting: `format_product_card` across Fashion & HomeLife candidates, ensuring ToneValidator passes
     * Callback processing: `approve_product` (Product status -> 'approved', VideoJob created with status 'pending', pushed to queue, message updated) and `reject_product` (Product status -> 'rejected', message updated)
     * Offline mock mode execution: ensure `TelegramCommandCenter` runs cleanly without real Telegram tokens or live network calls
   - Execute `pytest tests/test_telegram_bot.py -v` to confirm RED phase failure.

2. TDD Step 2 (GREEN Phase):
   - Implement:
     * `src/bot/keyboards.py`: `CompatibleInlineKeyboardMarkup`, `CompatibleInlineKeyboardButton`, `get_approval_keyboard`, `get_main_menu_keyboard`
     * `src/bot/formatters.py`: `format_product_card`, `format_captcha_alert`
     * `src/bot/handlers.py`: callback handlers (`approve_product`, `reject_product`), queue pusher (`push_to_video_queue` with in-memory fallback), aiogram router setup (`setup_bot_routers`)
     * `src/bot/telegram_bot.py`: `TelegramCommandCenter`, `route_topic`, `MessageDict`
     * `src/bot/__init__.py`: Clean re-exports
   - Execute `pytest tests/test_telegram_bot.py -v` to confirm GREEN phase pass.

3. TDD Step 3 (Verification Phase):
   - Run and document verbatim output of:
     * `pytest tests/test_telegram_bot.py -v` (100% PASS)
     * `pytest tests/e2e/ -v` (100% PASS)
     * `pytest tests/ -v` (100% PASS across entire workspace)
     * `python3 scripts/m1_stress_harness.py` (100% PASS)
     * `python3 scripts/m2_stress_harness.py` (100% PASS)
     * `python3 scripts/m2_kalodata_stress_harness.py` (100% PASS)
     * `python3 scripts/m3_fashion_adversarial_harness.py` (100% PASS)
     * `python3 scripts/m3_homelife_adversarial_harness.py` (100% PASS)
