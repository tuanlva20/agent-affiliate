# DISPATCH — m4_remedy_explorer_2
Role: Callback Validation & DB Integrity Remediation Explorer
Workspace: /Users/tuanlva/Folder/workSpace/affiliate
Milestone: M4 (Iteration 2 Remediation)
Working directory: /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m4_remedy_explorer_2/
Parent Conversation ID: f5177315-7404-4813-b8ba-56081885cdd4

Previous Failure Context:
- m4_challenger_2 executed `scripts/m4_adversarial_callback_harness.py` with 4 critical failures:
  1. `approve_product:` (empty product_id) returns `success=True` and pushes corrupted job `job_` with empty `product_id` to video queue.
  2. `reject_product:` (empty product_id) returns `success=True`.
  3. `approve_product:prod_ghost_404` (non-existent product in DB) with active session returns `success=True` and pushes to video queue despite 0 records in DB, causing DB-Queue desynchronization.
  4. `reject_product:prod_ghost_404` with DB session returns `success=True` for non-existent product.

Your task:
Nghiên cứu và thiết kế giải pháp khắc phục trong `src/bot/handlers.py` (`execute_callback`):
1. Thiết kế validation chặt chẽ cho `product_id`: không cho phép rỗng/chỉ chứa whitespace. Trả về `{"success": False, "error": "malformed_callback", "message": "Dữ liệu callback không hợp lệ: thiếu mã sản phẩm."}`.
2. Thiết kế logic kiểm tra sự tồn tại của `Product` trong database khi `session is not None`: nếu `product is None`, không cập nhật DB, không tạo `VideoJob`, không đẩy vào `video_queue`, và trả về `{"success": False, "error": "product_not_found", "message": f"Sản phẩm {product_id} không tồn tại trong hệ thống."}`.
3. Đảm bảo chạy `python3 scripts/m4_adversarial_callback_harness.py` đạt 40/40 assertions PASS (100%).
4. Viết báo cáo phân tích chiến lược remediation chi tiết tại handoff.md.


## 2026-11-10T10:48:08Z
You are m4_remedy_explorer_2, Callback Validation & DB Integrity Remediation Explorer for Milestone 4 (Iteration 2).
Your working directory is: /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m4_remedy_explorer_2/
The original request file is: /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/ORIGINAL_REQUEST.md
The dispatch file is: /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m4_remedy_explorer_2/DISPATCH.md
The project scope is in: /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/PROJECT.md
The failure reports are in:
- /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m4_challenger_2/handoff.md
- /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m4_reviewer_1/handoff.md

Read ORIGINAL_REQUEST.md, DISPATCH.md, and the failure handoff reports.
Analyze `src/bot/handlers.py` (`execute_callback`), `scripts/m4_adversarial_callback_harness.py`, and database models (`src/database/models.py`).
Design the exact remediation fix:
1. Handling empty `product_id`: `if not product_id:` -> return `{"success": False, "error": "malformed_callback", "message": "Dữ liệu callback không hợp lệ: thiếu mã sản phẩm."}` for both approve and reject.
2. Checking `Product` existence in database when `session is not None`: if `product is None`, return `{"success": False, "error": "product_not_found", "message": f"Sản phẩm {product_id} không tồn tại trong hệ thống."}`, preventing state desync and phantom jobs in Redis queue.
3. Verification with `scripts/m4_adversarial_callback_harness.py` ensuring 40/40 assertions pass (100%).
4. Provide concrete, exact code changes in your handoff report.
Write your report to `/Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m4_remedy_explorer_2/handoff.md`.
Send a message back to parent orchestrator when done.
