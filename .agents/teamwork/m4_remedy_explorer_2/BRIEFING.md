# BRIEFING — 2026-11-10T10:56:00Z

## Mission
Analyze callback validation and DB integrity failures in `src/bot/handlers.py`, and design the remediation strategy to ensure 100% pass on adversarial harness.

## 🔒 My Identity
- Archetype: explorer
- Roles: Callback Validation & DB Integrity Remediation Explorer
- Working directory: /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m4_remedy_explorer_2/
- Original parent: f5177315-7404-4813-b8ba-56081885cdd4
- Milestone: M4 Iteration 2 Remediation

## 🔒 Key Constraints
- Read-only investigation — do NOT modify source code files in src/ directly (propose exact changes in handoff)
- Working directory strictly inside `.agents/teamwork/m4_remedy_explorer_2/`
- Ensure 40/40 assertions pass on `scripts/m4_adversarial_callback_harness.py`
- Thorough evidence chain and 5-component handoff report

## Current Parent
- Conversation ID: f5177315-7404-4813-b8ba-56081885cdd4
- Updated: not yet

## Investigation State
- **Explored paths**:
  - `src/bot/handlers.py` (lines 120-209: `execute_callback`)
  - `scripts/m4_adversarial_callback_harness.py` (Challenge 3: assertions 3.4, 3.5, 3.6, 3.7)
  - `scripts/m4_adversarial_security_harness.py` (callback boundary & idempotency tests)
  - `scripts/m4_bot_stress_harness.py` (Category 5: DB state machine & queue atomicity)
  - `src/database/models.py` (Product, VideoJob relationships and FK constraints)
  - `tests/test_telegram_bot.py` (test_bot_instance_handle_callback_delegation and callback tests)
  - `tests/e2e/test_tier3_combinations.py` (approval combinations)
- **Key findings**:
  1. Empty `product_id` vulnerability: `callback_data.split(":", 1)` resulted in empty `product_id` that bypassed checks, created `job_`, and pushed corrupted tasks to queue.
  2. Ghost product injection vulnerability: `if product:` block skipped DB writes on non-existent `product_id`, but queue push was outside `if product:` block, causing state desynchronization and phantom jobs.
  3. Hidden test dependency: `test_bot_instance_handle_callback_delegation` in `tests/test_telegram_bot.py:559` passed previously only because of the ghost product bug (it tested with unseeded `prod_via_center`). Remediation must seed `Product` in that test.
  4. Verified empirical remediation: Patched `execute_callback` achieved 40/40 (100%) PASS on adversarial harness, 189/189 (100%) on security harness, 42/42 (100%) on bot stress harness, and 51/51 on unit test suite.
- **Unexplored areas**:
  - aiogram 3.x router registration (handled in parallel by m4_remedy_explorer_1)
  - admin_id type coercion and group `@bot` syntax (handled in parallel by m4_remedy_explorer_3)

## Key Decisions Made
- Validated empty `product_id` immediately post-split: `if not product_id:` returns `{"success": False, "error": "malformed_callback", "message": "Dữ liệu callback không hợp lệ: thiếu mã sản phẩm."}`.
- Enforced strict database existence check when `session is not None`: if `product is None`, abort queue push and return `{"success": False, "error": "product_not_found", "message": f"Sản phẩm {product_id} không tồn tại trong hệ thống."}` for both `approve_product` and `reject_product`.
- Produced patch files `handlers_callback_validation.patch` and `test_callback_validation.patch` in agent directory for implementer worker.

## Artifact Index
- DISPATCH.md — Dispatch instructions from orchestrator
- handlers_callback_validation.patch — Patch file for `src/bot/handlers.py`
- test_callback_validation.patch — Patch file for `tests/test_telegram_bot.py`
- progress.md — Liveness heartbeat
- handoff.md — Comprehensive 5-component remediation report
