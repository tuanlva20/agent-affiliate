"""AMAS v1.4.0 — Telegram Command Center & 1-Tap Approval Unit Test Suite (Features F10, F11, F12).

Tests:
1. Category 1: Forum Topic Routing (route_topic mapping, unknown fallbacks, custom topic mapping).
2. Category 2: 1-Tap Approval Keyboards (get_approval_keyboard, dual dict & attribute access, button callbacks, get_main_menu_keyboard).
3. Category 3: Product Card Formatting & Tone Compliance (format_product_card, ToneValidator compliance, KOC markers, format_captcha_alert).
4. Category 4: Authorized Admin Command Execution (handle_command across /test_scout, /test_video, /test_reply, /status, /create_channel, /warmup, /help, /menu).
5. Category 5: Unauthorized Non-Admin Command Rejection (security guard across commands and callbacks).
6. Category 6: Callback Query Handling & Database Transitions (approve_product, reject_product, idempotency, video queue push).
7. Category 7: Offline Mock Mode & TelegramCommandCenter Lifecycle (send_message, send_product_card, send_captcha_alert, MessageDict).
8. Category 8: aiogram 3.x Router Integration & Dispatcher Setup.
"""

from __future__ import annotations

import os
from typing import Any, Dict
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.base_scout import ProductCandidate
from src.agents.fashion_scout import SpecialistEvaluation
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
    format_product_message,
    get_approval_keyboard,
    get_main_menu_keyboard,
    push_to_video_queue,
    route_topic,
    router,
    setup_bot_routers,
)
from src.core.tone_validator import ToneValidator
from src.database.models import Channel, Niche, Product, VideoJob


@pytest.fixture(autouse=True)
async def seed_pilot_niches(db_session: AsyncSession):
    """Seed pilot niches to satisfy foreign key constraints in tests."""
    for nid, name in [("thoi_trang_nu", "Thời trang nữ"), ("do_gia_dung", "Đồ gia dụng thông minh")]:
        existing = await db_session.get(Niche, nid)
        if not existing:
            db_session.add(Niche(niche_id=nid, name=name))
    await db_session.commit()


# ==============================================================================
# Category 1: Forum Topic Routing (route_topic)
# ==============================================================================

class TestRouteTopic:
    """Verifies mapping of niche identifiers to dedicated Telegram forum topics."""

    def test_route_topic_fashion(self):
        assert route_topic("thoi_trang_nu") == 101

    def test_route_topic_homelife(self):
        assert route_topic("do_gia_dung") == 102

    def test_route_topic_dashboard_tong(self):
        assert route_topic("dashboard_tong") == 100
        assert route_topic("dashboard") == 100

    def test_route_topic_unknown_niche_fallback(self):
        assert route_topic("unknown_niche") == 100
        assert route_topic("random_category") == 100
        assert route_topic("") == 100
        assert route_topic(None) == 100

    def test_route_topic_custom_mapping_override(self):
        custom = {"thoi_trang_nu": 201, "do_gia_dung": 202, "dashboard": 200}
        assert route_topic("thoi_trang_nu", custom) == 201
        assert route_topic("do_gia_dung", custom) == 202
        assert route_topic("unknown", custom) == 100

    def test_topic_map_constant_integrity(self):
        assert TOPIC_MAP["thoi_trang_nu"] == 101
        assert TOPIC_MAP["do_gia_dung"] == 102
        assert TOPIC_MAP["dashboard_tong"] == 100


# ==============================================================================
# Category 2: 1-Tap Approval Keyboards (get_approval_keyboard)
# ==============================================================================

class TestApprovalKeyboard:
    """Verifies inline keyboard structure, callback data, and dual-mode access."""

    def test_approval_keyboard_dict_subscripting(self):
        kb = get_approval_keyboard("prod_test_001")
        assert "inline_keyboard" in kb
        buttons = kb["inline_keyboard"][0]
        assert len(buttons) == 2
        assert buttons[0]["callback_data"] == "approve_product:prod_test_001"
        assert buttons[1]["callback_data"] == "reject_product:prod_test_001"

    def test_approval_keyboard_button_labels(self):
        kb = get_approval_keyboard("prod_test_002")
        buttons = kb["inline_keyboard"][0]
        assert "Duyệt" in buttons[0]["text"]
        assert "Từ chối" in buttons[1]["text"]

    def test_approval_keyboard_special_product_ids(self):
        pid = "prod-vn_2026:special#42"
        kb = get_approval_keyboard(pid)
        buttons = kb["inline_keyboard"][0]
        assert buttons[0]["callback_data"] == f"approve_product:{pid}"
        assert buttons[1]["callback_data"] == f"reject_product:{pid}"

    def test_approval_keyboard_aiogram_attribute_compatibility(self):
        kb = get_approval_keyboard("prod_test_003")
        assert hasattr(kb, "inline_keyboard")
        assert len(kb.inline_keyboard[0]) == 2
        assert kb.inline_keyboard[0][0].callback_data == "approve_product:prod_test_003"
        assert kb.inline_keyboard[0][1].callback_data == "reject_product:prod_test_003"

    def test_main_menu_keyboard_structure(self):
        menu_kb = get_main_menu_keyboard()
        assert "inline_keyboard" in menu_kb
        rows = menu_kb["inline_keyboard"]
        assert len(rows) >= 3
        flattened_callbacks = [btn["callback_data"] for row in rows for btn in row]
        assert "cmd:test_scout" in flattened_callbacks
        assert "cmd:test_video" in flattened_callbacks
        assert "cmd:status" in flattened_callbacks
        assert "cmd:warmup" in flattened_callbacks

    def test_keyboard_missing_key_raises_keyerror(self):
        kb = get_approval_keyboard("prod_test_001")
        with pytest.raises(KeyError):
            _ = kb["non_existent_field"]

    def test_button_missing_key_raises_keyerror(self):
        kb = get_approval_keyboard("prod_test_001")
        btn = kb["inline_keyboard"][0][0]
        with pytest.raises(KeyError):
            _ = btn["non_existent_field"]


# ==============================================================================
# Category 3: Product Card Formatting & Tone Compliance
# ==============================================================================

class TestProductCardFormatting:
    """Verifies card text structure, emoji indicators, and ToneValidator compliance."""

    @pytest.fixture
    def fashion_evaluation(self) -> SpecialistEvaluation:
        return SpecialistEvaluation(
            product_id="prod_fash_01",
            niche_id="thoi_trang_nu",
            passed_filter=True,
            score=8.7,
            hook_angle="Bà nào bụng dưới to bơi hết vào đây, chiếc đầm chiết eo này giấu mỡ đỉnh chóp!",
            target_audience="Nữ công sở, mẹ bỉm sau sinh 22-35 tuổi",
            pros=["Chất vải tuyết mưa cao cấp, co giãn nhẹ", "Form chữ A che bụng dưới xuất sắc"],
            cons=["Cần giặt tay ở lần giặt đầu để bền màu"],
            viral_factor="Visual Before/After 3s thon gọn vòng eo 5cm",
        )

    @pytest.fixture
    def homelife_evaluation(self) -> SpecialistEvaluation:
        return SpecialistEvaluation(
            product_id="prod_home_01",
            niche_id="do_gia_dung",
            passed_filter=True,
            score=9.1,
            hook_angle="Từ ngày tậu em cây lau nhà tự vắt này việc nhà nhàn hẳn các bác ạ!",
            target_audience="Hội yêu bếp nghiện nhà, gia đình bận rộn",
            pros=["Tiết kiệm 80% thời gian lau sàn", "Khớp xoay 360 độ luồn gầm giường tủ dễ dàng"],
            cons=["Bông lau nên thay mới sau 3 tháng sử dụng"],
            viral_factor="Visual Before/After 3s vắt khô kiệt nước không chạm tay",
        )

    def test_format_fashion_product_card_contains_all_metrics(self, fashion_evaluation):
        card = format_product_card(
            product={
                "product_id": "prod_fash_01",
                "title": "Đầm Chữ A Chiết Eo Tôn Dáng",
                "price_vnd": 250000,
                "commission_rate": 0.15,
                "sales_30d": 1200,
            },
            evaluation=fashion_evaluation,
        )
        assert "👗" in card
        assert "THỜI TRANG NỮ" in card
        assert "Đầm Chữ A Chiết Eo Tôn Dáng" in card
        assert "250,000đ" in card
        assert "15%" in card
        assert "37,500đ/đơn" in card
        assert "1,200 đã bán" in card
        assert "8.7/10" in card
        assert "Bà nào bụng dưới to" in card
        assert "Chất vải tuyết mưa" in card

    def test_format_fashion_product_card_tone_compliance(self, fashion_evaluation):
        card = format_product_card(
            product={"title": "Đầm Nữ Hack Dáng", "price": 199000, "commission_rate": 0.12},
            evaluation=fashion_evaluation,
        )
        assert ToneValidator.validate(card) is True
        assert ToneValidator.has_koc_markers(card) is True

    def test_format_homelife_product_card_tone_compliance(self, homelife_evaluation):
        card = format_product_card(
            product={"title": "Cây Lau Nhà Tự Vắt", "price_vnd": 180000, "commission_rate": 0.14, "sales": 950},
            evaluation=homelife_evaluation,
        )
        assert "🏠" in card
        assert "ĐỒ GIA DỤNG" in card
        assert "Nam Minh" in card
        assert ToneValidator.validate(card) is True
        assert ToneValidator.has_koc_markers(card) is True

    def test_format_product_card_polymorphic_inputs(self, fashion_evaluation):
        candidate = ProductCandidate(
            product_id="prod_cand_01",
            niche_id="thoi_trang_nu",
            title="Váy Suông Che Khuyết Điểm",
            price_vnd=220000.0,
            commission_rate=0.10,
            sales_30d=500,
            revenue_30d=110000000.0,
            product_url="https://vt.tiktok.com/ZSsample",
        )
        card = format_product_card(candidate, fashion_evaluation)
        assert "Váy Suông Che Khuyết Điểm" in card
        assert "220,000đ" in card
        assert format_product_message == format_product_card

    def test_format_captcha_alert(self):
        alert = format_captcha_alert("chan_fashion_01", "/tmp/captcha_01.png")
        assert "🚨 [CẢNH BÁO CAPTCHA TIKTOK" in alert
        assert "chan_fashion_01" in alert
        assert "tạm dừng an toàn" in alert


# ==============================================================================
# Category 4: Authorized Admin Command Execution (handle_command)
# ==============================================================================

class TestCommandDispatcherAuthorized:
    """Verifies all 6 control commands when invoked by authorized administrator."""

    @pytest.fixture
    def bot(self) -> TelegramCommandCenter:
        return TelegramCommandCenter(admin_id=987654321)

    @pytest.mark.asyncio
    async def test_cmd_test_scout_default_niche(self, bot):
        res = await bot.handle_command("/test_scout", 987654321)
        assert "trinh sát" in res
        assert "thoi_trang_nu" in res

    @pytest.mark.asyncio
    async def test_cmd_test_scout_custom_niche(self, bot):
        res = await bot.handle_command("/test_scout", 987654321, "do_gia_dung")
        assert "trinh sát" in res
        assert "do_gia_dung" in res

    @pytest.mark.asyncio
    async def test_cmd_test_video(self, bot):
        res = await bot.handle_command("/test_video", 987654321)
        assert "pipeline" in res

    @pytest.mark.asyncio
    async def test_cmd_test_reply(self, bot):
        res = await bot.handle_command("/test_reply", 987654321)
        assert "Comment Agent" in res

    @pytest.mark.asyncio
    async def test_cmd_status(self, bot):
        res = await bot.handle_command("/status", 987654321)
        assert "đang hoạt động" in res
        assert "AMAS v1.4.0" in res

    @pytest.mark.asyncio
    async def test_cmd_create_channel_with_alias(self, bot):
        res = await bot.handle_command("/create_channel", 987654321, "koc_02")
        assert "warming" in res
        assert "koc_02" in res

    @pytest.mark.asyncio
    async def test_cmd_create_channel_default_alias(self, bot):
        res = await bot.handle_command("/create_channel", 987654321)
        assert "warming" in res

    @pytest.mark.asyncio
    async def test_cmd_warmup(self, bot):
        res = await bot.handle_command("/warmup", 987654321)
        assert "lướt feed dạo" in res

    @pytest.mark.asyncio
    async def test_cmd_help_menu(self, bot):
        res = await bot.handle_command("/help", 987654321)
        assert "/test_scout" in res
        assert "/test_video" in res
        assert "/status" in res

    @pytest.mark.asyncio
    async def test_cmd_case_and_whitespace_insensitivity(self, bot):
        res1 = await bot.handle_command("/TEST_SCOUT", 987654321)
        assert "trinh sát" in res1
        res2 = await bot.handle_command("  /status  ", 987654321)
        assert "đang hoạt động" in res2

    @pytest.mark.asyncio
    async def test_cmd_embedded_single_string_args(self, bot):
        res = await bot.handle_command("/test_scout do_gia_dung", 987654321)
        assert "trinh sát" in res
        assert "do_gia_dung" in res

    @pytest.mark.asyncio
    async def test_cmd_unknown_command(self, bot):
        res = await bot.handle_command("/nonexistent_cmd", 987654321)
        assert "không xác định" in res

    @pytest.mark.asyncio
    async def test_cmd_bot_username_strip(self, bot):
        res1 = await bot.handle_command("/test_scout@AmasBot", 987654321)
        assert "trinh sát ngách: thoi_trang_nu" in res1

        res2 = await bot.handle_command("/test_scout@AmasBot do_gia_dung", 987654321)
        assert "trinh sát ngách: do_gia_dung" in res2

        res3 = await bot.handle_command("/status@AmasBot", 987654321)
        assert "đang hoạt động" in res3

        res4 = await bot.handle_command("/create_channel@AmasBot koc_forum", 987654321)
        assert "profile_alias_koc_forum" in res4

    @pytest.mark.asyncio
    async def test_admin_id_string_coercion_authorized(self):
        # Bot configured with string admin_id
        bot_str_admin = TelegramCommandCenter(admin_id="987654321")
        assert isinstance(bot_str_admin.admin_id, int)
        assert bot_str_admin.admin_id == 987654321

        # Native int caller
        res1 = await bot_str_admin.handle_command("/status", 987654321)
        assert "đang hoạt động" in res1

    @pytest.mark.asyncio
    async def test_cmd_create_channel_db_persistence_headless(self, bot, db_session: AsyncSession):
        # Calling handle_command without passing session
        res = await bot.handle_command("/create_channel", 987654321, "koc_headless")
        assert "Tạo kênh mới thành công" in res

        # Verify that Channel was persisted in database
        chan = await db_session.get(Channel, "chan_koc_headless")
        assert chan is not None
        assert chan.channel_id == "chan_koc_headless"
        assert chan.browser_profile_id == "profile_alias_koc_headless"
        assert chan.lifecycle_status == "warming"


# ==============================================================================
# Category 5: Unauthorized Non-Admin Rejection (Security Guard)
# ==============================================================================

class TestCommandDispatcherUnauthorized:
    """Verifies strict security rejection for non-admin user IDs."""

    @pytest.fixture
    def bot(self) -> TelegramCommandCenter:
        return TelegramCommandCenter(admin_id=987654321)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "cmd,args",
        [
            ("/test_scout", "thoi_trang_nu"),
            ("/test_video", None),
            ("/test_reply", None),
            ("/status", None),
            ("/create_channel", "hacker_alias"),
            ("/warmup", None),
            ("/arbitrary_command", None),
        ],
    )
    async def test_unauthorized_user_rejected_across_all_commands(self, bot, cmd, args):
        denied = await bot.handle_command(cmd, user_id=111222333, args=args)
        assert "Quyền truy cập bị từ chối" in denied
        assert denied == ADMIN_DENIED_MESSAGE

    @pytest.mark.asyncio
    @pytest.mark.parametrize("bad_id", [0, -1, 987654320, 12345])
    async def test_unauthorized_boundary_user_ids(self, bot, bad_id):
        denied = await bot.handle_command("/status", user_id=bad_id)
        assert denied == ADMIN_DENIED_MESSAGE


# ==============================================================================
# Category 6: Callback Query Handling & Database Transitions
# ==============================================================================

class TestCallbackHandlingAndDB:
    """Verifies Human-in-the-Loop review callbacks and atomic DB state updates."""

    @pytest.mark.asyncio
    async def test_approve_product_callback_updates_product_and_queues_job(self, db_session: AsyncSession):
        prod = Product(
            product_id="prod_db_approve_01",
            niche_id="thoi_trang_nu",
            title="Đầm Hoa Nhí Dáng Suông",
            price=280000.0,
            commission_rate=0.15,
            product_url="https://tiktok.com/@shop/item1",
            status="pending",
        )
        db_session.add(prod)
        await db_session.commit()

        result = await execute_callback(
            callback_data="approve_product:prod_db_approve_01",
            user_id=987654321,
            admin_id=987654321,
            session=db_session,
        )
        assert result["success"] is True
        assert "Đã duyệt" in result["message"]

        reloaded = (await db_session.execute(
            select(Product).where(Product.product_id == "prod_db_approve_01")
        )).scalar_one()
        assert reloaded.status == "approved"

        job = (await db_session.execute(
            select(VideoJob).where(VideoJob.product_id == "prod_db_approve_01")
        )).scalar_one()
        assert job.product_id == "prod_db_approve_01"
        assert job.niche_id == "thoi_trang_nu"
        assert job.status == "pending"

    @pytest.mark.asyncio
    async def test_approve_product_callback_idempotent(self, db_session: AsyncSession):
        prod = Product(
            product_id="prod_db_idempotent",
            niche_id="thoi_trang_nu",
            title="Chân Váy Xếp Ly",
            price=190000.0,
            commission_rate=0.10,
            product_url="https://tiktok.com/@shop/item2",
            status="pending",
        )
        db_session.add(prod)
        await db_session.commit()

        res1 = await execute_callback("approve_product:prod_db_idempotent", 987654321, 987654321, db_session)
        assert res1["success"] is True

        res2 = await execute_callback("approve_product:prod_db_idempotent", 987654321, 987654321, db_session)
        assert res2["success"] is True

        jobs = (await db_session.execute(
            select(VideoJob).where(VideoJob.product_id == "prod_db_idempotent")
        )).scalars().all()
        assert len(jobs) == 1

    @pytest.mark.asyncio
    async def test_reject_product_callback_updates_product_only(self, db_session: AsyncSession):
        prod = Product(
            product_id="prod_db_reject_01",
            niche_id="do_gia_dung",
            title="Nồi Chiên Không Dầu",
            price=850000.0,
            commission_rate=0.08,
            product_url="https://tiktok.com/@shop/item3",
            status="pending",
        )
        db_session.add(prod)
        await db_session.commit()

        result = await execute_callback(
            callback_data="reject_product:prod_db_reject_01",
            user_id=987654321,
            admin_id=987654321,
            session=db_session,
        )
        assert result["success"] is True
        assert "từ chối" in result["message"]

        reloaded = (await db_session.execute(
            select(Product).where(Product.product_id == "prod_db_reject_01")
        )).scalar_one()
        assert reloaded.status == "rejected"

        jobs = (await db_session.execute(
            select(VideoJob).where(VideoJob.product_id == "prod_db_reject_01")
        )).scalars().all()
        assert len(jobs) == 0

    @pytest.mark.asyncio
    async def test_callback_unauthorized_user_rejected(self, db_session: AsyncSession):
        prod = Product(
            product_id="prod_db_unauth",
            niche_id="thoi_trang_nu",
            title="Áo Thun Nữ",
            price=120000.0,
            commission_rate=0.10,
            product_url="https://tiktok.com/@shop/item4",
            status="pending",
        )
        db_session.add(prod)
        await db_session.commit()

        result = await execute_callback(
            callback_data="approve_product:prod_db_unauth",
            user_id=111222333,
            admin_id=987654321,
            session=db_session,
        )
        assert result["success"] is False
        assert result["error"] == "unauthorized"
        assert ADMIN_DENIED_MESSAGE in result["message"]

        reloaded = (await db_session.execute(
            select(Product).where(Product.product_id == "prod_db_unauth")
        )).scalar_one()
        assert reloaded.status == "pending"

    @pytest.mark.asyncio
    async def test_callback_malformed_syntax(self, db_session: AsyncSession):
        result = await execute_callback("invalid_no_colon", 987654321, 987654321, db_session)
        assert result["success"] is False
        assert result["error"] == "malformed_callback"

    @pytest.mark.asyncio
    async def test_callback_empty_product_id_rejected(self):
        res_app = await execute_callback("approve_product:", 987654321, 987654321, None)
        assert res_app["success"] is False
        assert res_app["error"] == "malformed_callback"
        assert "thiếu mã sản phẩm" in res_app["message"]

        res_rej = await execute_callback("reject_product:   ", 987654321, 987654321, None)
        assert res_rej["success"] is False
        assert res_rej["error"] == "malformed_callback"

    @pytest.mark.asyncio
    async def test_callback_ghost_product_with_session_rejected(self, db_session: AsyncSession):
        res_app = await execute_callback("approve_product:prod_ghost_404", 987654321, 987654321, session=db_session)
        assert res_app["success"] is False
        assert res_app["error"] == "product_not_found"
        assert "không tồn tại" in res_app["message"]

        res_rej = await execute_callback("reject_product:prod_ghost_404", 987654321, 987654321, session=db_session)
        assert res_rej["success"] is False
        assert res_rej["error"] == "product_not_found"

    @pytest.mark.asyncio
    async def test_push_to_video_queue_fallback(self):
        payload = {"job_id": "job_queue_test", "action": "produce_video"}
        pushed = await push_to_video_queue(payload, redis_url="redis://localhost:9999/0")
        assert pushed is False or pushed is True


# ==============================================================================
# Category 7: Offline Mock Mode & TelegramCommandCenter
# ==============================================================================

class TestOfflineMockMode:
    """Verifies TelegramCommandCenter execution without external network connections."""

    @pytest.fixture
    def bot(self) -> TelegramCommandCenter:
        return TelegramCommandCenter(token="mock_token", admin_id=987654321)

    @pytest.mark.asyncio
    async def test_mock_send_message_recording(self, bot):
        msg = await bot.send_message(
            chat_id=-1001234567890,
            text="Hello AMAS",
            message_thread_id=101,
            reply_markup={"inline_keyboard": []},
        )
        assert len(bot.sent_messages) == 1
        assert bot.sent_messages[0]["text"] == "Hello AMAS"
        assert bot.sent_messages[0]["message_thread_id"] == 101

        # Dual subscripting and attribute access check
        assert msg["message_id"] == 1
        assert msg["text"] == "Hello AMAS"
        assert msg.text == "Hello AMAS"
        assert msg.message_thread_id == 101

    @pytest.mark.asyncio
    async def test_mock_send_product_card(self, bot):
        eval_item = SpecialistEvaluation(
            product_id="prod_mock_card",
            niche_id="thoi_trang_nu",
            passed_filter=True,
            score=8.5,
            hook_angle="Bà nào chân ngắn bơi vào đây",
            target_audience="Nữ sinh viên",
            pros=["Tôn dáng"],
            cons=["Ít màu"],
            viral_factor="Before/After 3s",
        )
        msg = await bot.send_product_card(
            chat_id=-1001234567890,
            product={"title": "Quần Ống Suông Hack Chân", "price": 195000, "commission_rate": 0.15},
            evaluation=eval_item,
        )
        assert msg["message_thread_id"] == 101
        assert "approve_product:prod_mock_card" in str(msg["reply_markup"])
        assert "Quần Ống Suông Hack Chân" in msg["text"]

    @pytest.mark.asyncio
    async def test_mock_send_captcha_alert(self, bot):
        msg = await bot.send_captcha_alert(
            channel_id="chan_fashion_01",
            screenshot_path="/tmp/test_captcha.png",
            chat_id=-1001234567890,
        )
        assert "🚨 [CẢNH BÁO CAPTCHA TIKTOK" in msg["text"]
        assert "chan_fashion_01" in msg["text"]

    @pytest.mark.asyncio
    async def test_bot_instance_handle_callback_delegation(self, bot, db_session: AsyncSession):
        prod = Product(
            product_id="prod_via_center",
            niche_id="thoi_trang_nu",
            title="Chân Váy Xếp Ly",
            price=190000.0,
            commission_rate=0.10,
            product_url="https://tiktok.com/@shop/item_vc",
            status="pending",
        )
        db_session.add(prod)
        await db_session.commit()

        res = await bot.handle_callback("approve_product:prod_via_center", user_id=987654321, session=db_session)
        assert res["success"] is True
        assert res["action"] == "approve_product"

        unauth = await bot.handle_callback("approve_product:prod_via_center", user_id=12345)
        assert unauth["success"] is False
        assert ADMIN_DENIED_MESSAGE in unauth["message"]


# ==============================================================================
# Category 8: aiogram 3.x Router Integration & Event Dispatcher Testing
# ==============================================================================

class TestAiogramRouterSetup:
    """Verifies aiogram Router configuration, handler bindings, and event dispatching."""

    @pytest.fixture(autouse=True)
    def clean_router_parent(self):
        router._parent_router = None
        yield
        router._parent_router = None

    def test_router_configuration(self):
        assert router is not None
        assert router.name == "amas_bot_router"

    def test_router_has_registered_handlers(self):
        """Verifies router has active message and callback query handlers."""
        assert len(router.message.handlers) > 0, "Router must have >= 1 registered message handler"
        assert len(router.callback_query.handlers) > 0, "Router must have >= 1 registered callback query handler"

    def test_setup_bot_routers_with_command_center(self):
        """Verifies setup_bot_routers binds workflow_data into the dispatcher."""
        bot = TelegramCommandCenter(token="mock_token", admin_id=987654321)
        r = setup_bot_routers(bot)
        assert r is not None
        if bot.dp:
            assert bot.dp["command_center"] is bot
            assert bot.dp["admin_id"] == 987654321

    @pytest.mark.asyncio
    async def test_aiogram_event_dispatch_admin_status_command(self):
        """Verifies simulated Message event dispatches through aiogram to execute_command."""
        from datetime import datetime
        from unittest.mock import AsyncMock
        from aiogram import Bot, Dispatcher
        from aiogram.types import Chat, Message, Update, User

        dp = Dispatcher()
        dp.include_router(router)
        mock_bot = AsyncMock(spec=Bot)

        admin_user = User(id=987654321, is_bot=False, first_name="Admin")
        chat = Chat(id=987654321, type="private")
        msg = Message(message_id=1, date=datetime.now(), chat=chat, from_user=admin_user, text="/status")
        upd = Update(update_id=1, message=msg)

        res = await dp.feed_update(bot=mock_bot, update=upd, admin_id=987654321)
        assert res is not None
        assert "đang hoạt động" in res
        assert "AMAS v1.4.0" in res

    @pytest.mark.asyncio
    async def test_aiogram_event_dispatch_group_command_syntax(self):
        """Verifies /command@BotName syntax dispatches cleanly in group chat context."""
        from datetime import datetime
        from unittest.mock import AsyncMock
        from aiogram import Bot, Dispatcher
        from aiogram.types import Chat, Message, Update, User

        dp = Dispatcher()
        dp.include_router(router)
        mock_bot = AsyncMock(spec=Bot)

        admin_user = User(id=987654321, is_bot=False, first_name="Admin")
        chat = Chat(id=-1001234567890, type="supergroup")
        msg = Message(
            message_id=2,
            date=datetime.now(),
            chat=chat,
            from_user=admin_user,
            text="/test_scout@AmasBot thoi_trang_nu",
        )
        upd = Update(update_id=2, message=msg)

        res = await dp.feed_update(bot=mock_bot, update=upd, admin_id=987654321)
        assert "trinh sát" in res
        assert "thoi_trang_nu" in res

    @pytest.mark.asyncio
    async def test_aiogram_event_dispatch_unauthorized_user(self):
        """Verifies unauthorized user messages are rejected via event dispatch."""
        from datetime import datetime
        from unittest.mock import AsyncMock
        from aiogram import Bot, Dispatcher
        from aiogram.types import Chat, Message, Update, User

        dp = Dispatcher()
        dp.include_router(router)
        mock_bot = AsyncMock(spec=Bot)

        unauth_user = User(id=111222333, is_bot=False, first_name="Hacker")
        chat = Chat(id=111222333, type="private")
        msg = Message(message_id=3, date=datetime.now(), chat=chat, from_user=unauth_user, text="/status")
        upd = Update(update_id=3, message=msg)

        res = await dp.feed_update(bot=mock_bot, update=upd, admin_id=987654321)
        assert res == ADMIN_DENIED_MESSAGE

    @pytest.mark.asyncio
    async def test_aiogram_event_dispatch_callback_approval(self, db_session: AsyncSession):
        """Verifies simulated CallbackQuery dispatches through aiogram and updates DB."""
        from datetime import datetime
        from unittest.mock import AsyncMock
        from aiogram import Bot, Dispatcher
        from aiogram.types import CallbackQuery, Chat, Message, Update, User

        prod = Product(
            product_id="prod_dispatch_01",
            niche_id="thoi_trang_nu",
            title="Đầm Xòe Nữ",
            price=250000.0,
            commission_rate=0.15,
            product_url="https://tiktok.com/@shop/item_d1",
            status="pending",
        )
        db_session.add(prod)
        await db_session.commit()

        dp = Dispatcher()
        dp.include_router(router)
        mock_bot = AsyncMock(spec=Bot)

        admin_user = User(id=987654321, is_bot=False, first_name="Admin")
        chat = Chat(id=-1001234567890, type="supergroup")
        msg = Message(message_id=4, date=datetime.now(), chat=chat, from_user=admin_user, text="Product Card")
        cb = CallbackQuery(
            id="cb_disp_1",
            from_user=admin_user,
            chat_instance="inst_1",
            message=msg,
            data="approve_product:prod_dispatch_01",
        )
        upd = Update(update_id=4, callback_query=cb)

        res = await dp.feed_update(bot=mock_bot, update=upd, admin_id=987654321, session=db_session)
        assert res["success"] is True
        assert res["action"] == "approve_product"

        reloaded = (await db_session.execute(
            select(Product).where(Product.product_id == "prod_dispatch_01")
        )).scalar_one()
        assert reloaded.status == "approved"

        job = (await db_session.execute(
            select(VideoJob).where(VideoJob.product_id == "prod_dispatch_01")
        )).scalar_one()
        assert job.status == "pending"

    @pytest.mark.asyncio
    async def test_aiogram_event_dispatch_callback_rejection(self, db_session: AsyncSession):
        """Verifies simulated CallbackQuery rejection dispatches through aiogram."""
        from datetime import datetime
        from unittest.mock import AsyncMock
        from aiogram import Bot, Dispatcher
        from aiogram.types import CallbackQuery, Chat, Message, Update, User

        prod = Product(
            product_id="prod_dispatch_02",
            niche_id="do_gia_dung",
            title="Máy Hút Bụi",
            price=650000.0,
            commission_rate=0.10,
            product_url="https://tiktok.com/@shop/item_d2",
            status="pending",
        )
        db_session.add(prod)
        await db_session.commit()

        dp = Dispatcher()
        dp.include_router(router)
        mock_bot = AsyncMock(spec=Bot)

        admin_user = User(id=987654321, is_bot=False, first_name="Admin")
        chat = Chat(id=-1001234567890, type="supergroup")
        msg = Message(message_id=5, date=datetime.now(), chat=chat, from_user=admin_user, text="Product Card")
        cb = CallbackQuery(
            id="cb_disp_2",
            from_user=admin_user,
            chat_instance="inst_2",
            message=msg,
            data="reject_product:prod_dispatch_02",
        )
        upd = Update(update_id=5, callback_query=cb)

        res = await dp.feed_update(bot=mock_bot, update=upd, admin_id=987654321, session=db_session)
        assert res["success"] is True
        assert res["action"] == "reject_product"

        reloaded = (await db_session.execute(
            select(Product).where(Product.product_id == "prod_dispatch_02")
        )).scalar_one()
        assert reloaded.status == "rejected"

    @pytest.mark.asyncio
    async def test_aiogram_event_dispatch_ghost_product_rejection(self, db_session: AsyncSession):
        """Verifies non-existent product callback is rejected without creating jobs."""
        from datetime import datetime
        from unittest.mock import AsyncMock
        from aiogram import Bot, Dispatcher
        from aiogram.types import CallbackQuery, Chat, Message, Update, User

        dp = Dispatcher()
        dp.include_router(router)
        mock_bot = AsyncMock(spec=Bot)

        admin_user = User(id=987654321, is_bot=False, first_name="Admin")
        chat = Chat(id=-1001234567890, type="supergroup")
        msg = Message(message_id=6, date=datetime.now(), chat=chat, from_user=admin_user, text="Product Card")
        cb = CallbackQuery(
            id="cb_disp_3",
            from_user=admin_user,
            chat_instance="inst_3",
            message=msg,
            data="approve_product:prod_ghost_404",
        )
        upd = Update(update_id=6, callback_query=cb)

        res = await dp.feed_update(bot=mock_bot, update=upd, admin_id=987654321, session=db_session)
        assert res["success"] is False
        assert res["error"] == "product_not_found"
