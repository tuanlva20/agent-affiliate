# Adversarial Stress Testing Handoff Report: Milestone 4 (Concurrency & Callback Race Conditions)

**Agent ID**: `m4_challenger_2`  
**Milestone**: Milestone 4 (Task 4: Telegram Command Center & 1-Tap Approval)  
**Assigned Roles**: critic, specialist  
**Working Directory**: `/Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m4_challenger_2/`  
**Date**: 2026-11-10T10:45:00Z  
**Handoff Type**: Hard Handoff  
**VERDICT**: **REQUEST_CHANGES**  

---

## 1. Observation

### 1.1 Empirical Adversarial Harness Execution
A dedicated adversarial challenge harness was constructed and executed at `scripts/m4_adversarial_callback_harness.py`:
- **Command**: `python3 scripts/m4_adversarial_callback_harness.py`
- **Exit Code**: `1` (FAIL)
- **Summary**: `36/40 assertions passed (90.0%). Total Failures: 4`

#### Verbatim Execution Log:
```
================================================================================
AMAS v1.4.0 — Milestone 4 Callback & Concurrency Adversarial Harness
================================================================================

▶ Challenge 1: Concurrency & Race Conditions: PASS
  Tests: 13 | Passed: 13 | Failed: 0 | Pass Rate: 100.0%

▶ Challenge 2: Idempotency Hammer: PASS
  Tests: 8 | Passed: 8 | Failed: 0 | Pass Rate: 100.0%

▶ Challenge 3: Malformed Callback & Ghost Product Injection: FAIL (4 issues)
  Tests: 12 | Passed: 8 | Failed: 4 | Pass Rate: 66.7%
  Top Failure Details (up to 5):
    ❌ [3.4 Missing Product ID on Approve] Expected rejection of empty product_id, but callback SUCCEEDED with job payload: {'job_id': 'job_', 'product_id': '', 'niche_id': 'thoi_trang_nu', 'status': 'pending', 'action': 'produce_video'}
    ❌ [3.5 Missing Product ID on Reject] Expected rejection of empty product_id, but callback SUCCEEDED: {'success': True, 'action': 'reject_product', 'product_id': '', 'message': '❌ Đã từ chối sản phẩm .'}
    ❌ [3.6 Ghost Product Approval] Non-existent product was marked success=True (DB VideoJob exists: False, Pushed to queue: True)
    ❌ [3.7 Ghost Product Rejection] Non-existent product rejection reported success=True: {'success': True, 'action': 'reject_product', 'product_id': 'prod_ghost_404', 'message': '❌ Đã từ chối sản phẩm prod_ghost_404.'}

▶ Challenge 4: Queue Failure Resilience & Fallback Integrity: PASS
  Tests: 7 | Passed: 7 | Failed: 0 | Pass Rate: 100.0%

================================================================================
SUMMARY: 36/40 assertions passed (90.0%). Total Failures: 4
================================================================================
```

### 1.2 Code Inspection Observations (`src/bot/handlers.py`)

#### Observation 1.2.1: Missing `product_id` Validation (`src/bot/handlers.py:134-144`)
Lines 134–144 state:
```python
    if not callback_data or ":" not in callback_data:
        return {
            "success": False,
            "error": "malformed_callback",
            "message": "Dữ liệu callback không hợp lệ.",
        }

    action, product_id = callback_data.split(":", 1)
    action = action.strip()
    product_id = product_id.strip()
```
- The code verifies that `callback_data` contains a colon (`":" in callback_data`), but never checks whether `product_id` is empty (`not product_id`).
- When `callback_data="approve_product:"`, `action="approve_product"` and `product_id=""`.
- The handler proceeds to execute approval on an empty string identifier, setting `job_id="job_"` and pushing `{"job_id": "job_", "product_id": "", ...}` to the video queue.
- When `callback_data="reject_product:"`, the handler returns `{"success": True, "action": "reject_product", "product_id": "", "message": "❌ Đã từ chối sản phẩm ."}`.

#### Observation 1.2.2: Ghost Product Approval & DB-Queue Desynchronization (`src/bot/handlers.py:146-187`)
Lines 146–187 state:
```python
    if action == "approve_product":
        job_id = f"job_{product_id}"
        niche_id = "thoi_trang_nu"
        if session:
            stmt = select(Product).where(Product.product_id == product_id)
            res = await session.execute(stmt)
            product = res.scalars().first()
            if product:
                product.status = "approved"
                niche_id = product.niche_id

                # Idempotency check: don't create duplicate VideoJob
                stmt_job = select(VideoJob).where(VideoJob.product_id == product_id)
                res_job = await session.execute(stmt_job)
                existing_job = res_job.scalars().first()
                if existing_job is None:
                    new_job = VideoJob(
                        job_id=job_id,
                        product_id=product_id,
                        niche_id=niche_id,
                        status="pending",
                    )
                    session.add(new_job)
                else:
                    existing_job.status = "pending"
                    job_id = existing_job.job_id
                await session.commit()

        payload = {
            "job_id": job_id,
            "product_id": product_id,
            "niche_id": niche_id,
            "status": "pending",
            "action": "produce_video",
        }
        await push_to_video_queue(payload)
        return {
            "success": True,
            "action": "approve_product",
            "product_id": product_id,
            "job": payload,
            "message": f"✅ Đã duyệt sản phẩm {product_id}. Đang chuyển sang Video Studio!",
        }
```
- When an active `session` is passed and `product_id="prod_ghost_404"` (which does NOT exist in the `products` table):
  1. `product = res.scalars().first()` returns `None`.
  2. The entire `if product:` block is skipped. Consequently, no `Product` record is updated and **no `VideoJob` row is created in the database**.
  3. Execution continues unconditionally to line 180: `await push_to_video_queue(payload)`.
  4. A payload with `job_id="job_prod_ghost_404"` and `product_id="prod_ghost_404"` is dispatched to Redis / fallback queue.
  5. Line 181 reports `success=True` to the Telegram admin with `"✅ Đã duyệt sản phẩm prod_ghost_404. Đang chuyển sang Video Studio!"`.
- **Result**: The database and the video queue are left in an inconsistent/desynchronized state. Downstream Video Studio will receive a queue task for a non-existent product, leading to subsequent unhandled errors in Milestone 5.
- Similarly, on rejection (`reject_product`), line 193 queries `product`, and if `product is None`, the block is skipped but line 197 unconditionally returns `success=True`.

### 1.3 Observations on Robust / Passing Vectors

1. **Concurrency & Race Conditions (Challenge 1: 13/13 Passed)**:
   - 50 concurrent `approve_product` calls on the same product executed with 0 unhandled exceptions, 0 deadlocks, resulting in `Product.status == "approved"` and strictly 1 `VideoJob` row in the database.
   - 50 concurrent `reject_product` calls executed with 0 unhandled exceptions, resulting in `Product.status == "rejected"` and 0 `VideoJob` rows.
   - 100 simultaneous mixed callbacks (50 approvals + 50 rejections) with randomized jitter completed cleanly with <=1 `VideoJob` row and zero database corruption.
   - Multi-product concurrency (10 products x 5 concurrent callbacks) created exactly 10 `VideoJobs` (1 per product).

2. **Idempotency Hammer (Challenge 2: 8/8 Passed)**:
   - 25 repeated sequential approvals on an approved product returned `success=True` and preserved the exact same `job_id` without creating duplicate `VideoJob` rows.
   - 25 repeated sequential rejections returned `success=True` and created 0 `VideoJob` rows.
   - Rapid state churn sequence (A -> R -> A -> R -> A) transitioned cleanly between states with zero dangling jobs and exactly 1 active `VideoJob` at completion.

3. **Queue Resilience & Fallback (Challenge 4: 7/7 Passed)**:
   - Unreachable Redis port, invalid DNS host, and malformed URL scheme were cleanly caught and diverted to `_IN_MEMORY_VIDEO_QUEUE` without raising unhandled exceptions.
   - High-throughput fallback under broker outage captured 100/100 jobs in memory with 0 lost jobs.
   - 100% of captured jobs conformed to the payload schema (`job_id`, `product_id`, `niche_id`, `status='pending'`, `action='produce_video'`).

4. **Existing Regression Test Suites**:
   - `pytest tests/test_telegram_bot.py -v`: 51 passed in 5.97s.
   - `pytest tests/e2e/ -v`: 61 passed in 1.42s.
   - `pytest tests/ -v`: 255 passed in 9.68s.

---

## 2. Logic Chain

1. **Logic of Missing Product ID (Vulnerability V1)**:
   - *Observation*: `execute_callback("approve_product:")` returns `success=True`, `job_id="job_"`, `product_id=""`.
   - *Reasoning*: A valid Telegram callback for 1-tap review requires both an action and a target entity ID (`<action>:<product_id>`). If `<product_id>` is blank or empty whitespace, the callback cannot be bound to any physical or domain product.
   - *Inference*: Allowing callbacks with empty product IDs to succeed and pushing empty `job_` tasks to the video queue is an unhandled boundary defect. Lines 141–144 must validate `if not product_id: return {"success": False, "error": "malformed_callback", "message": "Mã sản phẩm không hợp lệ."}`.

2. **Logic of Ghost Product Approval & DB-Queue Desync (Vulnerability V2)**:
   - *Observation*: `execute_callback("approve_product:prod_ghost_404", session=s)` returns `success=True` and pushes to queue, while DB has 0 `VideoJob` records and no `Product` record.
   - *Reasoning*: The purpose of Human-in-the-Loop review is to approve an *existing* scouted product found in the database. When an active database session is supplied, approving a product ID that does not exist in `products` cannot update any product and cannot generate a valid `VideoJob`.
   - *Inference*: Pushing a job to the queue when the database record is missing breaks transactional consistency between Telegram approvals, PostgreSQL/SQLite, and the Redis job queue. If `session is not None` and `product is None`, the handler must abort queue dispatch and return `{"success": False, "error": "product_not_found", "message": f"Sản phẩm {product_id} không tồn tại trong hệ thống."}`. Similarly, rejection of a non-existent product should return `{"success": False, "error": "product_not_found"}`.

3. **Logic of Verdict**:
   - While concurrency serialization and Redis fallback mechanisms are excellently architected, the callback handler fails 4 edge case tests in Challenge 3 involving malformed product IDs and phantom product injection.
   - As an empirical challenger, finding reproducible bugs that compromise queue integrity and state consistency requires a verdict of **REQUEST_CHANGES**.

---

## 3. Caveats

1. **Session-less Testing (Mock Mode)**:
   - When `session=None` (pure offline dispatcher mode), the handler does not have database access to verify product existence. However, missing/empty product ID (`approve_product:`) can and should still be validated even when `session=None`.
2. **Redis Cluster vs In-Memory Fallback**:
   - Challenge 4 tested broker unavailability and connection error handling via fallback to `_IN_MEMORY_VIDEO_QUEUE`. Live Redis cluster failover was not tested due to lack of a live Redis cluster in the local test environment.
3. **No Code Modification Constraint**:
   - In accordance with the system constraints (`Review-only — do NOT modify implementation code`), no source code files in `src/` were edited. A remedy worker must apply the recommended fixes.

---

## 4. Conclusion

- **VERDICT**: **REQUEST_CHANGES**
- **Summary**:
  - Concurrency handling (50–100 simultaneous requests with `asyncio.gather`), double-click idempotency, and Redis queue outage fallback are robust and passed 100%.
  - However, **4 critical edge case failures** were discovered in `src/bot/handlers.py`:
    1. Empty product IDs (`"approve_product:"`, `"reject_product:"`) succeed and queue corrupt jobs.
    2. Approving non-existent products (`"approve_product:prod_ghost_404"`) with a DB session succeeds and pushes phantom jobs to the queue, creating state desynchronization between the database and Redis queue.
- **Actionable Remediation Required**:
  In `src/bot/handlers.py` (`execute_callback`):
  1. Add empty `product_id` check immediately after splitting:
     ```python
     if not product_id:
         return {
             "success": False,
             "error": "malformed_callback",
             "message": "Dữ liệu callback không hợp lệ: thiếu mã sản phẩm.",
         }
     ```
  2. When `session is not None`, verify `Product` existence before approving or queuing:
     ```python
     if session:
         stmt = select(Product).where(Product.product_id == product_id)
         res = await session.execute(stmt)
         product = res.scalars().first()
         if not product:
             return {
                 "success": False,
                 "error": "product_not_found",
                 "message": f"Sản phẩm {product_id} không tồn tại trong hệ thống.",
             }
         # proceed to update status and VideoJob
     ```

---

## 5. Verification Method

To independently reproduce these findings and verify the failures:

1. **Run Dedicated Adversarial Callback Harness**:
   ```bash
   python3 scripts/m4_adversarial_callback_harness.py
   ```
   *Expected Result*: Exits with code `1`, displaying 4 failures in Challenge 3:
   - `[3.4 Missing Product ID on Approve]`
   - `[3.5 Missing Product ID on Reject]`
   - `[3.6 Ghost Product Approval]`
   - `[3.7 Ghost Product Rejection]`

2. **Run Existing Test Suites**:
   ```bash
   pytest tests/test_telegram_bot.py -v
   pytest tests/e2e/ -v
   ```
   *Expected Result*: All 51 bot tests and 61 E2E tests pass.

3. **Invalidation Conditions**:
   - The findings are invalidated if `execute_callback("approve_product:")` safely returns `success=False` with `error="malformed_callback"`.
   - The findings are invalidated if `execute_callback("approve_product:prod_ghost_404", session=session)` safely returns `success=False` with `error="product_not_found"` and does not push phantom jobs to `video_queue`.
