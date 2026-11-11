# DISPATCH — m4_challenger_2
Role: Concurrency & Callback Race Condition Adversarial Challenger for Milestone 4
Workspace: /Users/tuanlva/Folder/workSpace/affiliate
Milestone: M4 (Task 4: Telegram Command Center & 1-Tap Approval)
Working directory: /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m4_challenger_2/
Parent Conversation ID: f5177315-7404-4813-b8ba-56081885cdd4

Your task:
Viết và thực thi một test harness đối nghịch độc lập (`scripts/m4_adversarial_callback_harness.py`) để kiểm tra:
1. Double-click & race condition hammer: Gửi 50-100 concurrent callbacks (`approve_product:X` và `reject_product:X`) cùng lúc, kiểm tra xem trạng thái DB có bị corrupt, duplicate VideoJob có bị tạo, hay xảy ra deadlock.
2. Malformed callback data: Callback rỗng, thiếu ID, ID không tồn tại trong DB, ID là chuỗi độc hại.
3. Queue failure resilience: Giả lập lỗi Redis / crash queue, kiểm tra hệ thống có xử lý an toàn và phản hồi callback thích hợp hay không.
4. Đưa ra phán quyết rõ ràng: APPROVE hoặc REQUEST_CHANGES kèm báo cáo handoff.md 5 thành phần.


## 2026-11-10T10:36:16Z
You are m4_challenger_2, Concurrency & Callback Race Condition Adversarial Challenger for Milestone 4 (Telegram Command Center & 1-Tap Approval).
Your working directory is: /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m4_challenger_2/
The original request file is: /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/ORIGINAL_REQUEST.md
The dispatch file is: /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m4_challenger_2/DISPATCH.md
The worker's handoff is at: /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/worker_m4_1/handoff.md
The project scope is in: /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/PROJECT.md

Read ORIGINAL_REQUEST.md, DISPATCH.md, and worker_m4_1/handoff.md.
Your mission is to perform rigorous adversarial stress-testing against Telegram callbacks and queue integration:
1. Write an empirical stress test harness script at `/Users/tuanlva/Folder/workSpace/affiliate/scripts/m4_adversarial_callback_harness.py`:
   - Concurrency & Race Conditions: Launch 50–100 simultaneous concurrent callback executions (`asyncio.gather`) approving and rejecting the same product. Verify database integrity, check that no duplicate `VideoJob` rows are created, and confirm that there are zero deadlocks or unhandled exceptions.
   - Idempotency Hammer: Fire repeated approval calls on an already approved product, and repeated rejection calls on an already rejected product.
   - Malformed Callback Data: Test empty data (`""`), missing prefix (`"prod_123"`), missing product ID (`"approve_product:"`), non-existent product IDs, SQL injection in product ID (`"approve_product:' OR 1=1--"`), non-ASCII/binary product IDs.
   - Queue Resilience: Test behavior when Redis is unavailable, when Redis raises unexpected connection errors, and verify fallback capture.
2. Execute the harness via shell: `python3 scripts/m4_adversarial_callback_harness.py`.
3. Verify that 100% of callback and concurrency edge cases pass safely.
4. Write your comprehensive 5-component handoff report (Observation, Logic Chain, Caveats, Conclusion, Verification Method) to `/Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m4_challenger_2/handoff.md`.
5. State your explicit verdict: APPROVE or REQUEST_CHANGES.
Send a message back to parent orchestrator with your verdict and artifact path when done.
