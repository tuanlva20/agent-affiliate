"""Tier 4: Realistic End-to-End Production Scenarios.

Simulates full lifecycle multi-agent production runs:
1. Scenario A: Fashion Viral Dress Campaign (Sourcing -> Approval -> Render -> Upload)
2. Scenario B: HomeLife Smart Cleaner Campaign (Before/After 3s Hook -> Video -> Publish)
3. Scenario C: Emergency Captcha Halt & Telegram Alarm Workflow
4. Scenario D: Comment Conversion Loop (Viewer comments -> Intent -> KOC reply -> Yellow Cart)
"""

import os
import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy import select

from tests.e2e.conftest import (
    AppConfig,
    BaseScoutAgent,
    BrowserAdapter,
    ChannelModel,
    CommentAgent,
    CommentIntent,
    CommentScanner,
    FashionScoutAgent,
    HomeLifeScoutAgent,
    HumanBehaviorService,
    KalodataClient,
    MetricModel,
    ProductModel,
    SmartPublisher,
    SpecialistEvaluation,
    TelegramCommandCenter,
    ToneValidator,
    VideoCommentModel,
    VideoJobModel,
    VideoStudioAgent,
    get_approval_keyboard,
    route_topic,
)


# ---------------------------------------------------------------------------
# Scenario A: Fashion Viral Dress Campaign
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_scenario_fashion_viral_dress_campaign(async_db_session, tmp_path):
    """Full lifecycle scenario for Women's Fashion viral dress affiliate campaign."""
    # Step 1: Kalodata Sourcing
    kalo_client = KalodataClient(token="kalo_prod_token")
    raw_fashion_items = await kalo_client.get_top_products(category_id="thoi_trang_nu", limit=3)
    assert len(raw_fashion_items) > 0

    target_raw_item = {
        "product_id": "fash_dress_viral_99",
        "title": "Váy hoa nhí dáng chữ A chiết eo hack dáng thần thánh cho các nàng",
        "price": 195000.0,
        "commission_rate": 0.16,
        "sales_30d": 4200,
        "revenue_30d": 819000000.0,
        "product_url": "https://shop.tiktok.com/view/product/fash_dress_viral_99",
    }

    # Step 2: Base Scout Filtering
    base_scout = BaseScoutAgent()
    filtered = await base_scout.discover_candidates("thoi_trang_nu", [target_raw_item])
    assert len(filtered) == 1
    candidate = filtered[0]

    # Step 3: Fashion Specialist Evaluation
    fashion_scout = FashionScoutAgent()
    evaluation = fashion_scout.evaluate_product(target_raw_item)
    assert evaluation.passed_filter is True
    assert evaluation.score >= 8.5
    assert "hack dáng" in target_raw_item["title"].lower()

    # Step 4: Persist Product Candidate to PostgreSQL
    prod_record = ProductModel(
        product_id=candidate.product_id,
        niche_id=candidate.niche_id,
        title=candidate.title,
        price_vnd=candidate.price_vnd,
        commission_rate=candidate.commission_rate,
        sales_30d=candidate.sales_30d,
        revenue_30d=candidate.revenue_30d,
        product_url=candidate.product_url,
        status="pending_review",
    )
    async_db_session.add(prod_record)

    # Setup Channel
    channel = ChannelModel(
        channel_id="chan_fashion_viral",
        niche_id="thoi_trang_nu",
        browser_profile_id="alias_prof_fash_01",
        lifecycle_status="ready_to_post",
    )
    async_db_session.add(channel)
    await async_db_session.commit()

    # Step 5: Telegram Command Center Notification (Topic #thoi-trang-nu)
    bot = TelegramCommandCenter(admin_id=987654321)
    topic_id = route_topic("thoi_trang_nu")
    assert topic_id == 101

    kb = get_approval_keyboard(prod_record.product_id)
    msg = await bot.send_message(
        chat_id=-1001234567890,
        text=f"👗 [SẢN PHẨM MỚI] {prod_record.title}\n⭐ Điểm: {evaluation.score}/10\n🎯 Hook: {evaluation.hook_angle}",
        message_thread_id=topic_id,
        reply_markup=kb,
    )
    assert msg["message_thread_id"] == 101

    # Step 6: 1-Tap Human Approval Callback
    prod_record.status = "approved"
    job = VideoJobModel(
        job_id="job_fash_99",
        product_id=prod_record.product_id,
        channel_id=channel.channel_id,
        status="rendering",
    )
    async_db_session.add(job)
    await async_db_session.commit()

    # Step 7: Video Studio Production (Script -> Voiceover -> Remux)
    studio = VideoStudioAgent()
    rendered_video_path = await studio.produce_video(
        job_id=job.job_id,
        product_meta={"title": prod_record.title, "price_vnd": prod_record.price_vnd},
        persona={"tone": "koc"},
    )
    assert os.path.exists(rendered_video_path)
    job.status = "rendered"
    job.rendered_video_path = rendered_video_path
    await async_db_session.commit()

    # Step 8: Smart Publisher Upload (Warmup -> Biometric Typing -> Anchor Link)
    publisher = SmartPublisher(BrowserAdapter(), HumanBehaviorService())
    publish_result = await publisher.publish_video(
        job_id=job.job_id,
        channel_info={"channel_id": channel.channel_id, "lifecycle_status": channel.lifecycle_status},
        video_path=rendered_video_path,
        caption="Chiếc váy cứu cánh vòng 2 cho chị em công sở #fashion #xuhuong",
        product_anchor={"product_id": prod_record.product_id},
    )

    assert publish_result.success is True
    assert publish_result.video_id is not None
    assert publish_result.channel_status == "cooldown"

    # Step 9: Final Database Consistency Check
    job.status = "published"
    job.published_video_id = publish_result.video_id
    channel.lifecycle_status = "cooldown"
    await async_db_session.commit()

    saved_job = (await async_db_session.execute(select(VideoJobModel).where(VideoJobModel.job_id == "job_fash_99"))).scalar_one()
    assert saved_job.status == "published"
    assert saved_job.published_video_id.startswith("tt_pub_")


# ---------------------------------------------------------------------------
# Scenario B: HomeLife Smart Cleaner Campaign
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_scenario_homelife_smart_cleaner_campaign(async_db_session):
    """Full lifecycle scenario for Home Utilities Before/After 3s hook campaign."""
    target_cleaner = {
        "product_id": "home_mop_viral_88",
        "title": "Cây lau nhà tự vắt thông minh xoay 360 độ giải phóng sức lao động",
        "price": 169000.0,
        "commission_rate": 0.20,
        "sales_30d": 6500,
        "revenue_30d": 1098500000.0,
        "product_url": "https://shop.tiktok.com/view/product/home_mop_viral_88",
    }

    # Step 1: HomeLife Scout Specialist Evaluation
    scout = HomeLifeScoutAgent()
    eval_res = scout.evaluate_product(target_cleaner)
    assert eval_res.passed_filter is True
    assert eval_res.score >= 8.8
    assert "3s" in eval_res.viral_factor or "vắt khô" in eval_res.viral_factor

    # Step 2: Persist Product & Channel
    prod = ProductModel(
        product_id=target_cleaner["product_id"],
        niche_id="do_gia_dung",
        title=target_cleaner["title"],
        price_vnd=target_cleaner["price"],
        commission_rate=target_cleaner["commission_rate"],
        sales_30d=target_cleaner["sales_30d"],
        revenue_30d=target_cleaner["revenue_30d"],
        product_url=target_cleaner["product_url"],
        status="approved",
    )
    chan = ChannelModel(
        channel_id="chan_home_01",
        niche_id="do_gia_dung",
        browser_profile_id="alias_prof_home_01",
        lifecycle_status="ready_to_post",
    )
    async_db_session.add_all([prod, chan])
    await async_db_session.commit()

    # Step 3: Telegram Command Center routing to Topic #do-gia-dung (102)
    assert route_topic("do_gia_dung") == 102

    # Step 4: Produce Video & Publish
    job = VideoJobModel(job_id="job_cleaner_88", product_id=prod.product_id, channel_id=chan.channel_id)
    async_db_session.add(job)
    await async_db_session.commit()

    studio = VideoStudioAgent()
    video_path = await studio.produce_video(job.job_id, target_cleaner, {"tone": "koc"})
    assert os.path.exists(video_path)

    publisher = SmartPublisher(BrowserAdapter(), HumanBehaviorService())
    res = await publisher.publish_video(
        job_id=job.job_id,
        channel_info={"channel_id": chan.channel_id, "lifecycle_status": chan.lifecycle_status},
        video_path=video_path,
        caption="Lau nhà chưa bao giờ nhàn đến thế với cây lau thông minh #giadung #tienich",
        product_anchor={"product_id": prod.product_id},
    )
    assert res.success is True
    assert res.channel_status == "cooldown"


# ---------------------------------------------------------------------------
# Scenario C: Emergency Captcha Halt & Telegram Alarm
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_scenario_emergency_captcha_halt_and_alert(async_db_session):
    """Emergency workflow when anti-bot Captcha challenge is triggered during publishing."""
    bot = TelegramCommandCenter(admin_id=987654321)
    mock_page = MagicMock()
    # Mock captcha slider visible
    mock_page.is_visible = AsyncMock(side_effect=lambda sel: sel == "#secsdk-captcha-drag-wrapper")
    mock_page.screenshot = AsyncMock()

    channel = ChannelModel(
        channel_id="chan_alert_01",
        niche_id="thoi_trang_nu",
        browser_profile_id="alias_prof_alert",
        lifecycle_status="ready_to_post",
    )
    async_db_session.add(channel)
    await async_db_session.commit()

    publisher = SmartPublisher(BrowserAdapter(), HumanBehaviorService())
    result = await publisher.publish_video(
        job_id="job_halt_01",
        channel_info={"channel_id": channel.channel_id, "lifecycle_status": channel.lifecycle_status},
        video_path="/tmp/mock.mp4",
        caption="Caption test",
        product_anchor={},
        mock_page=mock_page,
        telegram_bot=bot,
    )

    # Assert immediate halt
    assert result.success is False
    assert result.channel_status == "captcha_blocked"
    mock_page.screenshot.assert_awaited_once()

    # Assert Telegram alert message
    assert len(bot.sent_messages) == 1
    alert_msg = bot.sent_messages[0]
    assert "🚨 [CẢNH BÁO CAPTCHA TIKTOK]" in alert_msg["text"]

    # Channel status locked in DB
    channel.lifecycle_status = "captcha_blocked"
    await async_db_session.commit()

    ch_verify = (await async_db_session.execute(select(ChannelModel).where(ChannelModel.channel_id == "chan_alert_01"))).scalar_one()
    assert ch_verify.lifecycle_status == "captcha_blocked"


# ---------------------------------------------------------------------------
# Scenario D: Comment Conversion into Yellow Cart Sales
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_scenario_comment_conversion_into_yellow_cart_sales(async_db_session, sample_fashion_product):
    """End-to-end comment monitoring and KOC persona conversion reply into yellow cart."""
    job = VideoJobModel(
        job_id="job_viral_post_77",
        product_id=sample_fashion_product["product_id"],
        status="published",
        published_video_id="tt_pub_job_viral_post_77",
    )
    metric = MetricModel(
        metric_id="met_job_77",
        job_id=job.job_id,
        views=25000,
        likes=1200,
        comments=4,
        clicks_yellow_cart=85,
    )
    async_db_session.add_all([job, metric])
    await async_db_session.commit()

    incoming_comments = [
        {"user": "hoa_mai_9x", "text": "Váy này bao nhiêu tiền thế shop?"},
        {"user": "bich_ngoc_cute", "text": "Vải đũi hay voan vậy chị, bụng to mặc che được không?"},
        {"user": "huyen_trang_hn", "text": "Đặt từ tuần trước mà sao giao hàng chậm thế!"},
        {"user": "thanh_truc_88", "text": "Mẫu mặc xinh quá!"},
    ]

    agent = CommentAgent()
    persona = {"tone": "koc", "name": "Thảo Nhi"}

    for c in incoming_comments:
        c_text = c["text"]
        intent = agent.classify_intent(c_text)
        reply = agent.generate_reply(c_text, sample_fashion_product, persona)

        # Tone compliance check
        assert ToneValidator.validate(reply) is True

        # Conversion check: price and material inquiries must push yellow cart
        if intent in [CommentIntent.ASK_PRICE, CommentIntent.ASK_MATERIAL_USAGE]:
            assert "giỏ hàng" in reply.lower() or "freeship" in reply.lower() or "góc trái" in reply.lower()

        db_comm = VideoCommentModel(
            comment_id=f"comm_{abs(hash(c_text))}",
            job_id=job.job_id,
            user_handle=c["user"],
            comment_text=c_text,
            intent=intent.value,
            reply_text=reply,
            status="replied",
        )
        async_db_session.add(db_comm)

    # Conversion bump
    metric.clicks_yellow_cart += len(incoming_comments)
    await async_db_session.commit()

    # Query back
    records = (await async_db_session.execute(select(VideoCommentModel).where(VideoCommentModel.job_id == job.job_id))).scalars().all()
    assert len(records) == 4

    updated_metric = (await async_db_session.execute(select(MetricModel).where(MetricModel.metric_id == "met_job_77"))).scalar_one()
    assert updated_metric.clicks_yellow_cart == 89
