#!/usr/bin/env python3
"""AMAS v1.4.0 — Milestone 4 Adversarial Stress Harness: Callback & Concurrency Hammer.

Tests:
1. Challenge 1: Concurrency & Race Conditions (50 concurrent approvals, 50 concurrent rejections,
   100 mixed callbacks race condition on same product, multi-product concurrent callbacks).
   Verifies: DB integrity, no duplicate VideoJob rows, 0 deadlocks, 0 unhandled exceptions.
2. Challenge 2: Idempotency Hammer (repeated approvals, repeated rejections, rapid state churn).
   Verifies: deterministic state, single VideoJob retention, no duplicate rows.
3. Challenge 3: Malformed Callback & Ghost Product Injection (empty data, missing separator,
   missing product ID, non-existent product IDs with DB session, SQL injection vectors, binary/Unicode).
   Verifies: safe handling, no SQL injection, proper validation against ghost jobs.
4. Challenge 4: Queue Failure Resilience & Fallback Integrity (unreachable Redis, invalid host,
   malformed scheme, high-concurrency fallback capture, payload contract schema).
   Verifies: 100% fallback reliability, zero dropped jobs, payload schema compliance.
"""

from __future__ import annotations

import asyncio
import json
import os
import random
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.handlers import (
    ADMIN_DENIED_MESSAGE,
    _IN_MEMORY_VIDEO_QUEUE,
    execute_callback,
    push_to_video_queue,
)
from src.bot.telegram_bot import TelegramCommandCenter
from src.database.models import Base, Niche, Product, VideoJob
from src.database.session import get_async_engine, get_db, get_session_factory

TEST_ADMIN_ID = 987654321
HARNESS_DB_URL = "sqlite+aiosqlite:///:memory:"


class TestResult:
    """Accumulates pass/fail metrics for each challenge suite."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.total = 0
        self.passed = 0
        self.failed = 0
        self.failures: List[str] = []

    def record_pass(self) -> None:
        self.total += 1
        self.passed += 1

    def record_fail(self, detail: str) -> None:
        self.total += 1
        self.failed += 1
        self.failures.append(detail)

    @property
    def pass_rate(self) -> float:
        return (self.passed / self.total * 100.0) if self.total > 0 else 0.0


async def setup_harness_db(db_url: str = HARNESS_DB_URL) -> None:
    """Initialize clean database tables and seed pilot niches."""
    engine = get_async_engine(db_url, force_new=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with get_db(db_url) as s:
        for nid, name in [
            ("thoi_trang_nu", "Thời trang nữ"),
            ("do_gia_dung", "Đồ gia dụng thông minh"),
        ]:
            existing = await s.get(Niche, nid)
            if not existing:
                s.add(Niche(niche_id=nid, name=name))
        await s.commit()


async def seed_product(
    product_id: str,
    niche_id: str = "thoi_trang_nu",
    title: str = "Test Product",
    price: float = 250000.0,
    status: str = "pending",
    db_url: str = HARNESS_DB_URL,
) -> None:
    """Helper to seed a test product."""
    async with get_db(db_url) as s:
        existing = await s.get(Product, product_id)
        if not existing:
            s.add(
                Product(
                    product_id=product_id,
                    niche_id=niche_id,
                    title=title,
                    price=price,
                    commission_rate=0.15,
                    product_url=f"https://tiktok.com/@shop/{product_id}",
                    status=status,
                )
            )
            await s.commit()


# ==============================================================================
# Challenge 1: Concurrency & Race Conditions
# ==============================================================================

async def challenge_1_concurrency_and_race_conditions(db_url: str = HARNESS_DB_URL) -> TestResult:
    """Stress-test concurrent callbacks on identical and multiple products."""
    result = TestResult("Challenge 1: Concurrency & Race Conditions")

    # --------------------------------------------------------------------------
    # Sub-test 1.1: 50 concurrent approvals on same product
    # --------------------------------------------------------------------------
    prod_id_1 = "prod_race_approve_50"
    await seed_product(prod_id_1, db_url=db_url)

    async def run_approve(i: int):
        async with get_db(db_url) as s:
            return await execute_callback(
                f"approve_product:{prod_id_1}",
                user_id=TEST_ADMIN_ID,
                admin_id=TEST_ADMIN_ID,
                session=s,
            )

    tasks_1 = [run_approve(i) for i in range(50)]
    t0 = time.perf_counter()
    res_1 = await asyncio.gather(*tasks_1, return_exceptions=True)
    t_elapsed = time.perf_counter() - t0

    exceptions_1 = [r for r in res_1 if isinstance(r, Exception)]
    if not exceptions_1:
        result.record_pass()
    else:
        result.record_fail(f"[1.1 Concurrent 50 Approvals] Raised {len(exceptions_1)} exceptions: {exceptions_1[0]}")

    all_success_1 = all(isinstance(r, dict) and r.get("success") is True for r in res_1)
    if all_success_1:
        result.record_pass()
    else:
        result.record_fail("[1.1 Concurrent 50 Approvals] Not all responses had success=True")

    async with get_db(db_url) as s:
        p1 = (await s.execute(select(Product).where(Product.product_id == prod_id_1))).scalar_one()
        jobs_1 = (await s.execute(select(VideoJob).where(VideoJob.product_id == prod_id_1))).scalars().all()

    if p1.status == "approved":
        result.record_pass()
    else:
        result.record_fail(f"[1.1 Concurrent 50 Approvals] Product status expected 'approved', got '{p1.status}'")

    if len(jobs_1) == 1:
        result.record_pass()
    else:
        result.record_fail(f"[1.1 Concurrent 50 Approvals] Expected strictly 1 VideoJob row, got {len(jobs_1)} (DUPLICATE JOB DETECTED)")

    # --------------------------------------------------------------------------
    # Sub-test 1.2: 50 concurrent rejections on same product
    # --------------------------------------------------------------------------
    prod_id_2 = "prod_race_reject_50"
    await seed_product(prod_id_2, db_url=db_url)

    async def run_reject(i: int):
        async with get_db(db_url) as s:
            return await execute_callback(
                f"reject_product:{prod_id_2}",
                user_id=TEST_ADMIN_ID,
                admin_id=TEST_ADMIN_ID,
                session=s,
            )

    tasks_2 = [run_reject(i) for i in range(50)]
    res_2 = await asyncio.gather(*tasks_2, return_exceptions=True)

    exceptions_2 = [r for r in res_2 if isinstance(r, Exception)]
    if not exceptions_2:
        result.record_pass()
    else:
        result.record_fail(f"[1.2 Concurrent 50 Rejections] Raised {len(exceptions_2)} exceptions: {exceptions_2[0]}")

    async with get_db(db_url) as s:
        p2 = (await s.execute(select(Product).where(Product.product_id == prod_id_2))).scalar_one()
        jobs_2 = (await s.execute(select(VideoJob).where(VideoJob.product_id == prod_id_2))).scalars().all()

    if p2.status == "rejected":
        result.record_pass()
    else:
        result.record_fail(f"[1.2 Concurrent 50 Rejections] Product status expected 'rejected', got '{p2.status}'")

    if len(jobs_2) == 0:
        result.record_pass()
    else:
        result.record_fail(f"[1.2 Concurrent 50 Rejections] Expected 0 VideoJob rows, got {len(jobs_2)}")

    # --------------------------------------------------------------------------
    # Sub-test 1.3: 100 simultaneous mixed callbacks (50 approvals + 50 rejections)
    # --------------------------------------------------------------------------
    prod_id_3 = "prod_race_mixed_100"
    await seed_product(prod_id_3, db_url=db_url)

    async def run_mixed(action: str):
        await asyncio.sleep(random.uniform(0.0005, 0.005))
        async with get_db(db_url) as s:
            return await execute_callback(
                f"{action}:{prod_id_3}",
                user_id=TEST_ADMIN_ID,
                admin_id=TEST_ADMIN_ID,
                session=s,
            )

    mixed_actions = ["approve_product"] * 50 + ["reject_product"] * 50
    random.shuffle(mixed_actions)
    tasks_3 = [run_mixed(act) for act in mixed_actions]

    t0_mixed = time.perf_counter()
    res_3 = await asyncio.gather(*tasks_3, return_exceptions=True)
    t_elapsed_mixed = time.perf_counter() - t0_mixed

    exceptions_3 = [r for r in res_3 if isinstance(r, Exception)]
    if not exceptions_3:
        result.record_pass()
    else:
        result.record_fail(f"[1.3 Mixed 100 Callbacks] Raised {len(exceptions_3)} exceptions: {exceptions_3[0]}")

    # No deadlocks check (100 callbacks must resolve within 10s)
    if t_elapsed_mixed < 10.0:
        result.record_pass()
    else:
        result.record_fail(f"[1.3 Mixed 100 Callbacks] High latency / near deadlock: took {t_elapsed_mixed:.2f}s")

    async with get_db(db_url) as s:
        p3 = (await s.execute(select(Product).where(Product.product_id == prod_id_3))).scalar_one()
        jobs_3 = (await s.execute(select(VideoJob).where(VideoJob.product_id == prod_id_3))).scalars().all()

    if p3.status in ("approved", "rejected"):
        result.record_pass()
    else:
        result.record_fail(f"[1.3 Mixed 100 Callbacks] Invalid corrupted status '{p3.status}'")

    if len(jobs_3) <= 1:
        result.record_pass()
    else:
        result.record_fail(f"[1.3 Mixed 100 Callbacks] Duplicate VideoJobs created: {len(jobs_3)}")

    # --------------------------------------------------------------------------
    # Sub-test 1.4: Multi-Product Concurrency (10 products x 5 concurrent approvals)
    # --------------------------------------------------------------------------
    multi_prods = [f"prod_multi_{i}" for i in range(10)]
    for pid in multi_prods:
        await seed_product(pid, db_url=db_url)

    async def run_multi(pid: str):
        async with get_db(db_url) as s:
            return await execute_callback(
                f"approve_product:{pid}",
                user_id=TEST_ADMIN_ID,
                admin_id=TEST_ADMIN_ID,
                session=s,
            )

    multi_tasks = [run_multi(pid) for pid in multi_prods for _ in range(5)]
    random.shuffle(multi_tasks)
    res_4 = await asyncio.gather(*multi_tasks, return_exceptions=True)

    exceptions_4 = [r for r in res_4 if isinstance(r, Exception)]
    if not exceptions_4:
        result.record_pass()
    else:
        result.record_fail(f"[1.4 Multi-Product Concurrency] Raised {len(exceptions_4)} exceptions: {exceptions_4[0]}")

    async with get_db(db_url) as s:
        multi_jobs = (await s.execute(select(VideoJob).where(VideoJob.product_id.in_(multi_prods)))).scalars().all()

    if len(multi_jobs) == 10:
        result.record_pass()
    else:
        result.record_fail(f"[1.4 Multi-Product Concurrency] Expected exactly 10 VideoJobs (1 per product), got {len(multi_jobs)}")

    return result


# ==============================================================================
# Challenge 2: Idempotency Hammer
# ==============================================================================

async def challenge_2_idempotency_hammer(db_url: str = HARNESS_DB_URL) -> TestResult:
    """Stress-test repeated duplicate calls and alternating status transitions."""
    result = TestResult("Challenge 2: Idempotency Hammer")

    # --------------------------------------------------------------------------
    # Sub-test 2.1: 25 sequential repeated approvals
    # --------------------------------------------------------------------------
    pid_1 = "prod_idem_approve_25"
    await seed_product(pid_1, db_url=db_url)

    first_job_id = None
    all_ok = True
    for seq in range(25):
        async with get_db(db_url) as s:
            res = await execute_callback(
                f"approve_product:{pid_1}",
                user_id=TEST_ADMIN_ID,
                admin_id=TEST_ADMIN_ID,
                session=s,
            )
            if not res.get("success"):
                all_ok = False
            cur_job_id = res.get("job", {}).get("job_id")
            if seq == 0:
                first_job_id = cur_job_id
            elif cur_job_id != first_job_id:
                result.record_fail(f"[2.1 Repeated Approvals] Job ID mutated on call {seq}: {cur_job_id} != {first_job_id}")

    if all_ok:
        result.record_pass()
    else:
        result.record_fail("[2.1 Repeated Approvals] Some approval calls returned success=False")

    async with get_db(db_url) as s:
        p1 = (await s.execute(select(Product).where(Product.product_id == pid_1))).scalar_one()
        jobs_1 = (await s.execute(select(VideoJob).where(VideoJob.product_id == pid_1))).scalars().all()

    if p1.status == "approved":
        result.record_pass()
    else:
        result.record_fail(f"[2.1 Repeated Approvals] Expected status 'approved', got '{p1.status}'")

    if len(jobs_1) == 1:
        result.record_pass()
    else:
        result.record_fail(f"[2.1 Repeated Approvals] VideoJob duplicated: expected 1, got {len(jobs_1)}")

    # --------------------------------------------------------------------------
    # Sub-test 2.2: 25 sequential repeated rejections
    # --------------------------------------------------------------------------
    pid_2 = "prod_idem_reject_25"
    await seed_product(pid_2, db_url=db_url)

    all_reject_ok = True
    for _ in range(25):
        async with get_db(db_url) as s:
            res = await execute_callback(
                f"reject_product:{pid_2}",
                user_id=TEST_ADMIN_ID,
                admin_id=TEST_ADMIN_ID,
                session=s,
            )
            if not res.get("success"):
                all_reject_ok = False

    if all_reject_ok:
        result.record_pass()
    else:
        result.record_fail("[2.2 Repeated Rejections] Some rejection calls returned success=False")

    async with get_db(db_url) as s:
        p2 = (await s.execute(select(Product).where(Product.product_id == pid_2))).scalar_one()
        jobs_2 = (await s.execute(select(VideoJob).where(VideoJob.product_id == pid_2))).scalars().all()

    if p2.status == "rejected":
        result.record_pass()
    else:
        result.record_fail(f"[2.2 Repeated Rejections] Expected status 'rejected', got '{p2.status}'")

    if len(jobs_2) == 0:
        result.record_pass()
    else:
        result.record_fail(f"[2.2 Repeated Rejections] Expected 0 VideoJobs, got {len(jobs_2)}")

    # --------------------------------------------------------------------------
    # Sub-test 2.3: Rapid State Churn (A -> R -> A -> R -> A)
    # --------------------------------------------------------------------------
    pid_3 = "prod_idem_churn_5"
    await seed_product(pid_3, db_url=db_url)

    transitions = [
        ("approve_product", "approved"),
        ("reject_product", "rejected"),
        ("approve_product", "approved"),
        ("reject_product", "rejected"),
        ("approve_product", "approved"),
    ]

    transition_ok = True
    for action, expected_status in transitions:
        async with get_db(db_url) as s:
            await execute_callback(
                f"{action}:{pid_3}",
                user_id=TEST_ADMIN_ID,
                admin_id=TEST_ADMIN_ID,
                session=s,
            )
        async with get_db(db_url) as s:
            p3 = (await s.execute(select(Product).where(Product.product_id == pid_3))).scalar_one()
            if p3.status != expected_status:
                transition_ok = False
                result.record_fail(f"[2.3 State Churn] After {action}, expected status '{expected_status}', got '{p3.status}'")

    if transition_ok:
        result.record_pass()

    async with get_db(db_url) as s:
        jobs_3 = (await s.execute(select(VideoJob).where(VideoJob.product_id == pid_3))).scalars().all()

    if len(jobs_3) == 1:
        result.record_pass()
    else:
        result.record_fail(f"[2.3 State Churn] Expected strictly 1 VideoJob row after churn, got {len(jobs_3)}")

    return result


# ==============================================================================
# Challenge 3: Malformed Callback & Ghost Product Injection
# ==============================================================================

async def challenge_3_malformed_and_ghost_callbacks(db_url: str = HARNESS_DB_URL) -> TestResult:
    """Test malformed inputs, missing identifiers, non-existent products, and injections."""
    result = TestResult("Challenge 3: Malformed Callback & Ghost Product Injection")

    # 3.1 Empty callback data
    res_empty = await execute_callback("", TEST_ADMIN_ID, TEST_ADMIN_ID, session=None)
    if res_empty.get("success") is False and res_empty.get("error") == "malformed_callback":
        result.record_pass()
    else:
        result.record_fail(f"[3.1 Empty Data] Expected error='malformed_callback', got {res_empty}")

    # 3.2 Missing action separator / no colon
    res_no_colon = await execute_callback("prod_only_without_prefix", TEST_ADMIN_ID, TEST_ADMIN_ID, session=None)
    if res_no_colon.get("success") is False and res_no_colon.get("error") == "malformed_callback":
        result.record_pass()
    else:
        result.record_fail(f"[3.2 No Colon] Expected error='malformed_callback', got {res_no_colon}")

    # 3.3 Missing action prefix (":prod_123")
    res_no_action = await execute_callback(":prod_123", TEST_ADMIN_ID, TEST_ADMIN_ID, session=None)
    if res_no_action.get("success") is False:
        result.record_pass()
    else:
        result.record_fail(f"[3.3 No Action Prefix] Expected success=False, got {res_no_action}")

    # 3.4 Missing product ID on approval ("approve_product:")
    res_no_prod_approve = await execute_callback("approve_product:", TEST_ADMIN_ID, TEST_ADMIN_ID, session=None)
    if res_no_prod_approve.get("success") is False:
        result.record_pass()
    else:
        result.record_fail(
            f"[3.4 Missing Product ID on Approve] Expected rejection of empty product_id, but callback SUCCEEDED with job payload: {res_no_prod_approve.get('job')}"
        )

    # 3.5 Missing product ID on rejection ("reject_product:")
    res_no_prod_reject = await execute_callback("reject_product:", TEST_ADMIN_ID, TEST_ADMIN_ID, session=None)
    if res_no_prod_reject.get("success") is False:
        result.record_pass()
    else:
        result.record_fail(
            f"[3.5 Missing Product ID on Reject] Expected rejection of empty product_id, but callback SUCCEEDED: {res_no_prod_reject}"
        )

    # 3.6 Non-existent product ID with active DB session ("approve_product:prod_ghost_404")
    # When DB session is provided, approving a non-existent product must NOT report success
    # and must NOT push a ghost job to the queue while DB has no corresponding product/job.
    queue_len_before = len(_IN_MEMORY_VIDEO_QUEUE)
    async with get_db(db_url) as s:
        res_ghost = await execute_callback("approve_product:prod_ghost_404", TEST_ADMIN_ID, TEST_ADMIN_ID, session=s)

    async with get_db(db_url) as s:
        ghost_job = (await s.execute(select(VideoJob).where(VideoJob.product_id == "prod_ghost_404"))).scalars().first()

    # Vulnerability check: Did it report success=True despite product not existing?
    if res_ghost.get("success") is False:
        result.record_pass()
    else:
        queue_len_after = len(_IN_MEMORY_VIDEO_QUEUE)
        pushed_ghost = queue_len_after > queue_len_before
        result.record_fail(
            f"[3.6 Ghost Product Approval] Non-existent product was marked success=True (DB VideoJob exists: {ghost_job is not None}, Pushed to queue: {pushed_ghost})"
        )

    # 3.7 Non-existent product on rejection with active DB session
    async with get_db(db_url) as s:
        res_ghost_reject = await execute_callback("reject_product:prod_ghost_404", TEST_ADMIN_ID, TEST_ADMIN_ID, session=s)
    if res_ghost_reject.get("success") is False:
        result.record_pass()
    else:
        result.record_fail(
            f"[3.7 Ghost Product Rejection] Non-existent product rejection reported success=True: {res_ghost_reject}"
        )

    # 3.8 SQL Injection in product ID (' OR 1=1--)
    sql_injection_payload = "approve_product:' OR 1=1--"
    injection_safe = True
    try:
        async with get_db(db_url) as s:
            await execute_callback(sql_injection_payload, TEST_ADMIN_ID, TEST_ADMIN_ID, session=s)
    except Exception as e:
        injection_safe = False
        result.record_fail(f"[3.8 SQL Injection] Query crashed with exception: {e}")

    if injection_safe:
        # Verify table integrity: products table is intact and not corrupted
        async with get_db(db_url) as s:
            all_prods = (await s.execute(select(Product))).scalars().all()
            if len(all_prods) > 0:
                result.record_pass()
            else:
                result.record_fail("[3.8 SQL Injection] Products table was emptied or corrupted!")

    # 3.9 Destructive SQL injection attempt ('; DROP TABLE products;--)
    sql_drop_payload = "approve_product:'; DROP TABLE products;--"
    drop_safe = True
    try:
        async with get_db(db_url) as s:
            await execute_callback(sql_drop_payload, TEST_ADMIN_ID, TEST_ADMIN_ID, session=s)
    except Exception as e:
        # Expected if SQLite rejects multi-statement strings, not a problem as long as DB is safe
        pass

    async with get_db(db_url) as s:
        try:
            check_prods = (await s.execute(select(Product))).scalars().all()
            result.record_pass()
        except Exception as e:
            result.record_fail(f"[3.9 SQL Drop Injection] Table products was dropped or compromised: {e}")

    # 3.10 Non-ASCII, Unicode emojis, and null bytes in product ID
    unicode_payload = "approve_product:👗_đầm_hoa_nhí_2026_✨"
    try:
        async with get_db(db_url) as s:
            res_uni = await execute_callback(unicode_payload, TEST_ADMIN_ID, TEST_ADMIN_ID, session=s)
        result.record_pass()
    except Exception as e:
        result.record_fail(f"[3.10 Unicode Payload] Crashed on Unicode emoji product ID: {e}")

    binary_payload = "approve_product:\x00\xff\xfe\x01"
    try:
        async with get_db(db_url) as s:
            res_bin = await execute_callback(binary_payload, TEST_ADMIN_ID, TEST_ADMIN_ID, session=s)
        result.record_pass()
    except Exception as e:
        result.record_fail(f"[3.10 Binary Payload] Crashed on binary null byte product ID: {e}")

    # 3.11 Massive length product ID (5,000 characters)
    massive_payload = "approve_product:" + ("A" * 5000)
    try:
        async with get_db(db_url) as s:
            res_mass = await execute_callback(massive_payload, TEST_ADMIN_ID, TEST_ADMIN_ID, session=s)
        result.record_pass()
    except Exception as e:
        result.record_fail(f"[3.11 Massive Payload] Crashed on 5000-char product ID: {e}")

    return result


# ==============================================================================
# Challenge 4: Queue Failure Resilience & Fallback Integrity
# ==============================================================================

async def challenge_4_queue_resilience_and_fallback() -> TestResult:
    """Stress-test Redis queue downtime, connection errors, and high-concurrency fallback."""
    result = TestResult("Challenge 4: Queue Failure Resilience & Fallback Integrity")

    _IN_MEMORY_VIDEO_QUEUE.clear()

    # 4.1 Unreachable port / connection refused
    payload_1 = {
        "job_id": "job_queue_unreachable",
        "product_id": "prod_q1",
        "niche_id": "thoi_trang_nu",
        "status": "pending",
        "action": "produce_video",
    }
    pushed_1 = await push_to_video_queue(payload_1, redis_url="redis://127.0.0.1:59999/0")
    if pushed_1 is False:
        result.record_pass()
    else:
        result.record_fail("[4.1 Unreachable Port] Expected push_to_video_queue to return False on unreachable port")

    if payload_1 in _IN_MEMORY_VIDEO_QUEUE:
        result.record_pass()
    else:
        result.record_fail("[4.1 Unreachable Port] Payload not captured in _IN_MEMORY_VIDEO_QUEUE fallback")

    # 4.2 Non-existent hostname (DNS failure)
    payload_2 = {
        "job_id": "job_queue_dns_fail",
        "product_id": "prod_q2",
        "niche_id": "do_gia_dung",
        "status": "pending",
        "action": "produce_video",
    }
    pushed_2 = await push_to_video_queue(payload_2, redis_url="redis://nonexistent-cluster-host-999.local:6379/0")
    if pushed_2 is False and payload_2 in _IN_MEMORY_VIDEO_QUEUE:
        result.record_pass()
    else:
        result.record_fail("[4.2 DNS Failure] Fallback failed for non-existent hostname")

    # 4.3 Malformed URL scheme
    payload_3 = {
        "job_id": "job_queue_bad_scheme",
        "product_id": "prod_q3",
        "niche_id": "thoi_trang_nu",
        "status": "pending",
        "action": "produce_video",
    }
    try:
        pushed_3 = await push_to_video_queue(payload_3, redis_url="invalid_scheme://127.0.0.1:6379")
        if pushed_3 is False and payload_3 in _IN_MEMORY_VIDEO_QUEUE:
            result.record_pass()
        else:
            result.record_fail("[4.3 Malformed Scheme] Did not capture payload in fallback on malformed scheme")
    except Exception as e:
        result.record_fail(f"[4.3 Malformed Scheme] push_to_video_queue raised unhandled exception: {e}")

    # 4.4 High-concurrency fallback under broker outage (100 concurrent pushes)
    _IN_MEMORY_VIDEO_QUEUE.clear()
    concurrent_payloads = [
        {
            "job_id": f"job_concurrent_q_{i}",
            "product_id": f"prod_cq_{i}",
            "niche_id": "thoi_trang_nu" if i % 2 == 0 else "do_gia_dung",
            "status": "pending",
            "action": "produce_video",
        }
        for i in range(100)
    ]

    async def push_item(item: Dict[str, Any]):
        return await push_to_video_queue(item, redis_url="redis://127.0.0.1:59999/0")

    t0_q = time.perf_counter()
    push_results = await asyncio.gather(*(push_item(p) for p in concurrent_payloads), return_exceptions=True)
    t_elapsed_q = time.perf_counter() - t0_q

    q_exceptions = [r for r in push_results if isinstance(r, Exception)]
    if not q_exceptions:
        result.record_pass()
    else:
        result.record_fail(f"[4.4 High-Concurrency Fallback] Raised {len(q_exceptions)} exceptions: {q_exceptions[0]}")

    if len(_IN_MEMORY_VIDEO_QUEUE) == 100:
        result.record_pass()
    else:
        result.record_fail(f"[4.4 High-Concurrency Fallback] Expected 100 items captured in memory, got {len(_IN_MEMORY_VIDEO_QUEUE)}")

    # 4.5 Payload schema contract verification
    schema_ok = True
    required_keys = {"job_id", "product_id", "niche_id", "status", "action"}
    for idx, item in enumerate(_IN_MEMORY_VIDEO_QUEUE):
        if not required_keys.issubset(item.keys()):
            schema_ok = False
            result.record_fail(f"[4.5 Payload Schema] Item {idx} missing required keys: {required_keys - set(item.keys())}")
            break
        if item["status"] != "pending" or item["action"] != "produce_video":
            schema_ok = False
            result.record_fail(f"[4.5 Payload Schema] Item {idx} invalid status/action: status={item['status']}, action={item['action']}")
            break

    if schema_ok:
        result.record_pass()

    return result


# ==============================================================================
# Runner & Main
# ==============================================================================

async def run_all_adversarial_tests() -> int:
    """Executes the full suite of adversarial stress tests and prints formatted summary."""
    print("=" * 80)
    print("AMAS v1.4.0 — Milestone 4 Callback & Concurrency Adversarial Harness")
    print("=" * 80)

    await setup_harness_db(HARNESS_DB_URL)

    test_suites = [
        challenge_1_concurrency_and_race_conditions,
        challenge_2_idempotency_hammer,
        challenge_3_malformed_and_ghost_callbacks,
        challenge_4_queue_resilience_and_fallback,
    ]

    total_passed = 0
    total_failed = 0
    suite_results: List[TestResult] = []

    for suite_fn in test_suites:
        res = await suite_fn()
        suite_results.append(res)
        total_passed += res.passed
        total_failed += res.failed

        status_str = "PASS" if res.failed == 0 else f"FAIL ({res.failed} issues)"
        print(f"\n▶ {res.name}: {status_str}")
        print(f"  Tests: {res.total} | Passed: {res.passed} | Failed: {res.failed} | Pass Rate: {res.pass_rate:.1f}%")
        if res.failures:
            print("  Top Failure Details (up to 5):")
            for f in res.failures[:5]:
                print(f"    ❌ {f}")
            if len(res.failures) > 5:
                print(f"    ... and {len(res.failures) - 5} more failures.")

    print("\n" + "=" * 80)
    grand_total = total_passed + total_failed
    overall_rate = (total_passed / grand_total * 100.0) if grand_total > 0 else 0.0
    print(f"SUMMARY: {total_passed}/{grand_total} assertions passed ({overall_rate:.1f}%). Total Failures: {total_failed}")
    print("=" * 80)

    return total_failed


if __name__ == "__main__":
    failed_count = asyncio.run(run_all_adversarial_tests())
    sys.exit(0 if failed_count == 0 else 1)
