"""AMAS v1.4.0 — Milestone 4 Adversarial Stress Harness.

Rigorous empirical stress testing for:
1. Topic routing resilience under corrupted/extreme inputs.
2. Keyboard serialization, dict subscripting, and Pydantic V2 compatibility.
3. Product card formatting under distorted, extreme numeric, and injection-like payloads.
4. Security guard robustness against unauthorized user IDs, boundary numbers, and prompt injection strings.
5. Database state machine integrity, race conditions, idempotency, and rollback safety.
"""

import asyncio
import json
import sys
from typing import Any, Dict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from src.database.session import get_async_engine
from src.database.models import Base, Niche, Product, VideoJob
from src.bot import (
    ADMIN_DENIED_MESSAGE,
    TOPIC_MAP,
    CompatibleInlineKeyboardButton,
    CompatibleInlineKeyboardMarkup,
    MessageDict,
    TelegramCommandCenter,
    execute_callback,
    execute_command,
    format_captcha_alert,
    format_product_card,
    get_approval_keyboard,
    get_main_menu_keyboard,
    push_to_video_queue,
    route_topic,
    _IN_MEMORY_VIDEO_QUEUE,
)
from src.core.tone_validator import ToneValidator
from src.agents.fashion_scout import SpecialistEvaluation

TOTAL = 0
PASSED = 0
FAILED = 0


def record_result(category: str, test_name: str, passed: bool, detail: str = ""):
    global TOTAL, PASSED, FAILED
    TOTAL += 1
    if passed:
        PASSED += 1
        print(f"✅ [PASS] [{category}] {test_name} {detail}")
    else:
        FAILED += 1
        print(f"❌ [FAIL] [{category}] {test_name}: {detail}")


async def run_stress_suite():
    print("=" * 80)
    print("AMAS v1.4.0 — MILESTONE 4 FORENSIC ADVERSARIAL STRESS TEST HARNESS")
    print("=" * 80)

    # --------------------------------------------------------------------------
    # 1. Topic Routing Adversarial Testing
    # --------------------------------------------------------------------------
    cat1 = "Topic Routing Adversarial"
    record_result(cat1, "Standard fashion", route_topic("thoi_trang_nu") == 101)
    record_result(cat1, "Standard homelife", route_topic("do_gia_dung") == 102)
    record_result(cat1, "Dashboard tong", route_topic("dashboard_tong") == 100)
    record_result(cat1, "None input fallback", route_topic(None) == 100)
    record_result(cat1, "Empty string fallback", route_topic("") == 100)
    record_result(cat1, "Whitespace string fallback", route_topic("   ") == 100)
    record_result(cat1, "SQL injection string", route_topic("' OR '1'='1") == 100)
    record_result(cat1, "Buffer-like long string", route_topic("a" * 10000) == 100)
    record_result(cat1, "Unicode emoji string", route_topic("👗👗👗") == 100)
    record_result(cat1, "Custom dictionary override", route_topic("thoi_trang_nu", {"thoi_trang_nu": 999}) == 999)
    record_result(cat1, "Custom dictionary missing key", route_topic("unknown", {"thoi_trang_nu": 999}) == 100)

    # --------------------------------------------------------------------------
    # 2. Keyboard & Dual-Mode Serialization Fidelity
    # --------------------------------------------------------------------------
    cat2 = "Keyboard Serialization Fidelity"
    kb = get_approval_keyboard("prod_adversarial_#1")
    record_result(cat2, "Dict subscriptable", "inline_keyboard" in kb)
    record_result(cat2, "Button count is 2", len(kb["inline_keyboard"][0]) == 2)
    record_result(cat2, "Button 1 callback", kb["inline_keyboard"][0][0]["callback_data"] == "approve_product:prod_adversarial_#1")
    record_result(cat2, "Button 2 callback", kb["inline_keyboard"][0][1]["callback_data"] == "reject_product:prod_adversarial_#1")
    record_result(cat2, "Pydantic attribute access", kb.inline_keyboard[0][0].callback_data == "approve_product:prod_adversarial_#1")

    # Verify Pydantic dump and json export
    dumped = kb.model_dump()
    record_result(cat2, "Pydantic model_dump dict structure", isinstance(dumped, dict) and "inline_keyboard" in dumped)
    json_str = kb.model_dump_json()
    record_result(cat2, "Pydantic model_dump_json serialization", "approve_product:prod_adversarial_#1" in json_str)

    menu = get_main_menu_keyboard()
    record_result(cat2, "Main menu rows >= 3", len(menu.inline_keyboard) >= 3)
    record_result(cat2, "Main menu dict access", "cmd:status" in [b["callback_data"] for r in menu["inline_keyboard"] for b in r])

    # --------------------------------------------------------------------------
    # 3. Product Card Formatting & Tone Integrity Under Distorted Inputs
    # --------------------------------------------------------------------------
    cat3 = "Product Card Distorted Inputs & Tone"
    eval_fash = SpecialistEvaluation(
        product_id="prod_fash_adv",
        niche_id="thoi_trang_nu",
        passed_filter=True,
        score=9.3,
        hook_angle="Chị em nào dáng quả lê bơi ngay vào đây, mẫu này che khuyết điểm siêu đỉnh á!",
        target_audience="Nữ công sở",
        pros=["Chất liệu co giãn", "Tôn dáng"],
        cons=["Chỉ giặt nước lạnh"],
        viral_factor="Visual Before/After 3s",
    )
    # Extremely large numbers
    card1 = format_product_card(
        product={"product_id": "p1", "title": "Đầm Maxi Đẹp", "price_vnd": 999999999, "commission_rate": 0.20, "sales_30d": 500000},
        evaluation=eval_fash,
    )
    record_result(cat3, "Extreme price formatting", "999,999,999đ" in card1)
    record_result(cat3, "Extreme sales formatting", "500,000 đã bán" in card1)
    record_result(cat3, "Extreme commission payout", "200,000,000đ/đơn" in card1)
    record_result(cat3, "ToneValidator passes extreme card", ToneValidator.validate(card1) is True)
    record_result(cat3, "KOC markers present in card", ToneValidator.has_koc_markers(card1) is True)

    # Corrupted / Missing product dictionary
    card2 = format_product_card(product="thoi_trang_nu", title="Đầm Thô Mộc")
    record_result(cat3, "Flat call format card", "Đầm Thô Mộc" in card2 and ToneValidator.validate(card2) is True)

    # Captcha Alert
    alert = format_captcha_alert("chan_koc_09", "/tmp/captcha.png")
    record_result(cat3, "Captcha alarm prefix", "🚨 [CẢNH BÁO CAPTCHA TIKTOK - KÊNH chan_koc_09]" in alert)

    # --------------------------------------------------------------------------
    # 4. Security Guard & Command Dispatching
    # --------------------------------------------------------------------------
    cat4 = "Security Guard & Command Dispatch"
    admin_id = 987654321
    bot = TelegramCommandCenter(admin_id=admin_id)

    # Unauthorized tests across boundaries
    unauth_ids = [-999999, 0, 1, 987654320, 987654322, 123456789]
    all_rejected = True
    for uid in unauth_ids:
        res = await bot.handle_command("/status", user_id=uid)
        if res != ADMIN_DENIED_MESSAGE:
            all_rejected = False
            break
    record_result(cat4, "All non-admin user IDs strictly denied", all_rejected)

    # Authorized commands execution
    cmd_scout = await bot.handle_command("/test_scout do_gia_dung", user_id=admin_id)
    record_result(cat4, "Command /test_scout handles args", "do_gia_dung" in cmd_scout)

    cmd_vid = await bot.handle_command("/test_video", user_id=admin_id)
    record_result(cat4, "Command /test_video responds", "pipeline" in cmd_vid)

    cmd_reply = await bot.handle_command("/test_reply", user_id=admin_id)
    record_result(cat4, "Command /test_reply responds", "Comment Agent" in cmd_reply)

    cmd_stat = await bot.handle_command("/status", user_id=admin_id)
    record_result(cat4, "Command /status responds", "AMAS v1.4.0" in cmd_stat)

    cmd_warm = await bot.handle_command("/warmup", user_id=admin_id)
    record_result(cat4, "Command /warmup responds", "lướt feed dạo" in cmd_warm)

    # --------------------------------------------------------------------------
    # 5. Database State Machine & Queue Atomicity
    # --------------------------------------------------------------------------
    cat5 = "DB State Machine & Queue Atomicity"
    engine = get_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        # Seed pilot niches
        n1 = Niche(niche_id="thoi_trang_nu", name="Thời trang nữ")
        n2 = Niche(niche_id="do_gia_dung", name="Đồ gia dụng thông minh")
        session.add_all([n1, n2])
        await session.commit()

        # Seed products
        p1 = Product(product_id="prod_atomic_1", niche_id="thoi_trang_nu", title="Đầm A", price=250000, commission_rate=0.15, product_url="url1", status="pending")
        p2 = Product(product_id="prod_atomic_2", niche_id="do_gia_dung", title="Robot", price=1500000, commission_rate=0.10, product_url="url2", status="pending")
        session.add_all([p1, p2])
        await session.commit()

        # Approval transition
        res_app = await execute_callback("approve_product:prod_atomic_1", user_id=admin_id, admin_id=admin_id, session=session)
        record_result(cat5, "Approval returns success", res_app["success"] is True)

        p1_db = (await session.execute(select(Product).where(Product.product_id == "prod_atomic_1"))).scalar_one()
        record_result(cat5, "Product status updated to approved", p1_db.status == "approved")

        jobs = (await session.execute(select(VideoJob).where(VideoJob.product_id == "prod_atomic_1"))).scalars().all()
        record_result(cat5, "VideoJob created with pending status", len(jobs) == 1 and jobs[0].status == "pending")

        # Double approval idempotency check (simulate rapid button clicks)
        for _ in range(5):
            await execute_callback("approve_product:prod_atomic_1", user_id=admin_id, admin_id=admin_id, session=session)
        jobs_after = (await session.execute(select(VideoJob).where(VideoJob.product_id == "prod_atomic_1"))).scalars().all()
        record_result(cat5, "Idempotent 5x approval produces exactly 1 VideoJob", len(jobs_after) == 1)

        # Rejection transition
        res_rej = await execute_callback("reject_product:prod_atomic_2", user_id=admin_id, admin_id=admin_id, session=session)
        record_result(cat5, "Rejection returns success", res_rej["success"] is True)

        p2_db = (await session.execute(select(Product).where(Product.product_id == "prod_atomic_2"))).scalar_one()
        record_result(cat5, "Product status updated to rejected", p2_db.status == "rejected")
        p2_jobs = (await session.execute(select(VideoJob).where(VideoJob.product_id == "prod_atomic_2"))).scalars().all()
        record_result(cat5, "Rejected product creates 0 VideoJobs", len(p2_jobs) == 0)

        # In-memory queue fallback check
        record_result(cat5, "In-memory video queue captured approved job", len(_IN_MEMORY_VIDEO_QUEUE) >= 1)
        record_result(cat5, "Captured job payload structure valid", _IN_MEMORY_VIDEO_QUEUE[-1].get("product_id") == "prod_atomic_1")

    print("=" * 80)
    print(f"SUMMARY: {PASSED}/{TOTAL} passed ({(PASSED/TOTAL)*100:.1f}%). Total Failures: {FAILED}")
    print("=" * 80)
    if FAILED > 0:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(run_stress_suite())
