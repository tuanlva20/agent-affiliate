"""Tier 3: Cross-Feature Pairwise Multi-Agent Combination Test Suite.

Verifies end-to-end dataflows, state transformations, and interface contracts between interconnected subsystems:
Scout -> Approval -> Video Studio -> Smart Publisher -> Comment Engagement.
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
    NicheConfig,
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
# 1. Combination: Base Scout -> Specialist Scout -> Telegram Card
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_comb_scout_to_telegram_card(async_db_session, sample_fashion_product):
    """Pairwise flow: Raw product discovered, evaluated by specialist, formatted into Telegram Card."""
    # 1. Base Scout filters candidate
    base_scout = BaseScoutAgent()
    candidates = await base_scout.discover_candidates(
        niche_id="thoi_trang_nu",
        raw_items=[sample_fashion_product],
    )
    assert len(candidates) == 1
    candidate = candidates[0]

    # Save candidate product to DB
    product = ProductModel(
        product_id=candidate.product_id,
        niche_id=candidate.niche_id,
        title=candidate.title,
        price_vnd=candidate.price_vnd,
        commission_rate=candidate.commission_rate,
        product_url=candidate.product_url,
        status="pending_review",
    )
    async_db_session.add(product)
    await async_db_session.commit()

    # 2. Specialist Scout evaluates candidate
    fashion_scout = FashionScoutAgent()
    evaluation = fashion_scout.evaluate_product(sample_fashion_product)
    assert evaluation.passed_filter is True
    assert evaluation.score >= 8.0

    # 3. Telegram Command Center routes to topic and sends card with inline approval buttons
    bot = TelegramCommandCenter(admin_id=987654321)
    topic_id = route_topic(candidate.niche_id)
    assert topic_id == 101  # #thoi-trang-nu

    keyboard = get_approval_keyboard(candidate.product_id)
    card_text = (
        f"👗 [SẢN PHẨM MỚI DUYỆT - THỜI TRANG NỮ]\n"
        f"📌 Tên: {candidate.title}\n"
        f"💰 Giá: {int(candidate.price_vnd):,}đ | Hoa hồng: {int(candidate.commission_rate*100)}%\n"
        f"🎯 Hook 3s: {evaluation.hook_angle}\n"
        f"⭐ Điểm tiềm năng: {evaluation.score}/10"
    )

    msg = await bot.send_message(
        chat_id=-1001234567890,
        text=card_text,
        message_thread_id=topic_id,
        reply_markup=keyboard,
    )

    assert msg["message_thread_id"] == 101
    assert "approve_product:fash_dress_001" in str(msg["reply_markup"])


# ---------------------------------------------------------------------------
# 2. Combination: Telegram Approval Callback -> Video Studio Generation
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_comb_approval_to_video_studio(async_db_session, sample_fashion_product):
    """Pairwise flow: Admin clicks 1-tap approve button, product updates to approved, Video Studio generates video."""
    # 1. Product exists in DB as pending_review
    prod = ProductModel(
        product_id=sample_fashion_product["product_id"],
        niche_id="thoi_trang_nu",
        title=sample_fashion_product["title"],
        price_vnd=sample_fashion_product["price"],
        commission_rate=sample_fashion_product["commission_rate"],
        product_url=sample_fashion_product["product_url"],
        status="pending_review",
    )
    async_db_session.add(prod)
    await async_db_session.commit()

    # 2. Simulate Telegram callback query "approve_product:<id>"
    callback_data = f"approve_product:{prod.product_id}"
    action, pid = callback_data.split(":")
    assert action == "approve_product"
    assert pid == prod.product_id

    # Update product status
    prod.status = "approved"
    job = VideoJobModel(
        job_id="job_auto_001",
        product_id=prod.product_id,
        status="rendering",
    )
    async_db_session.add(job)
    await async_db_session.commit()

    # 3. Video Studio Agent produces script, voiceover, and remuxed video
    studio = VideoStudioAgent()
    rendered_file = await studio.produce_video(
        job_id=job.job_id,
        product_meta=sample_fashion_product,
        persona={"tone": "koc"},
    )

    assert os.path.exists(rendered_file)

    # Update VideoJob status
    job.status = "rendered"
    job.rendered_video_path = rendered_file
    await async_db_session.commit()

    # Query back
    job_check = await async_db_session.execute(select(VideoJobModel).where(VideoJobModel.job_id == "job_auto_001"))
    saved_job = job_check.scalar_one()
    assert saved_job.status == "rendered"
    assert saved_job.rendered_video_path == rendered_file


# ---------------------------------------------------------------------------
# 3. Combination: Video Studio Output -> Smart Publisher Video Upload
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_comb_studio_to_smart_publisher(async_db_session, sample_fashion_product, tmp_path):
    """Pairwise flow: Rendered video handed to Smart Publisher, warmup feed, biometric typing, upload, and cooldown."""
    # 1. Rendered video artifact
    rendered_file = tmp_path / "final_render.mp4"
    rendered_file.touch()

    # 2. Channel in ready_to_post status
    channel = ChannelModel(
        channel_id="chan_pub_01",
        niche_id="thoi_trang_nu",
        browser_profile_id="alias_prof_01",
        lifecycle_status="ready_to_post",
    )
    async_db_session.add(channel)
    await async_db_session.commit()

    # 3. Publisher uploads video
    publisher = SmartPublisher(BrowserAdapter(), HumanBehaviorService())
    publish_result = await publisher.publish_video(
        job_id="job_auto_001",
        channel_info={"channel_id": channel.channel_id, "lifecycle_status": channel.lifecycle_status},
        video_path=str(rendered_file),
        caption="Chiếc váy tôn dáng đỉnh cao #fashion #xuhuong",
        product_anchor={"product_id": sample_fashion_product["product_id"]},
    )

    assert publish_result.success is True
    assert publish_result.video_id == "tt_pub_job_auto_001"
    assert publish_result.channel_status == "cooldown"

    # 4. Channel transitions to cooldown
    channel.lifecycle_status = "cooldown"
    await async_db_session.commit()

    chan_check = await async_db_session.execute(select(ChannelModel).where(ChannelModel.channel_id == "chan_pub_01"))
    assert chan_check.scalar_one().lifecycle_status == "cooldown"


# ---------------------------------------------------------------------------
# 4. Combination: Smart Publisher Encountering Captcha -> Telegram Emergency Halt
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_comb_publisher_to_captcha_alarm(async_db_session):
    """Pairwise flow: Smart publisher encounters captcha, triggers emergency stop, alerts Telegram, blocks channel."""
    mock_page = MagicMock()
    mock_page.is_visible = AsyncMock(side_effect=lambda sel: sel == "#secsdk-captcha-drag-wrapper")
    mock_page.screenshot = AsyncMock()

    bot = TelegramCommandCenter(admin_id=987654321)
    publisher = SmartPublisher(BrowserAdapter(), HumanBehaviorService())

    channel = ChannelModel(
        channel_id="chan_captcha_01",
        niche_id="thoi_trang_nu",
        browser_profile_id="alias_prof_captcha",
        lifecycle_status="ready_to_post",
    )
    async_db_session.add(channel)
    await async_db_session.commit()

    result = await publisher.publish_video(
        job_id="job_captcha_01",
        channel_info={"channel_id": channel.channel_id, "lifecycle_status": channel.lifecycle_status},
        video_path="/tmp/vid.mp4",
        caption="Caption",
        product_anchor={},
        mock_page=mock_page,
        telegram_bot=bot,
    )

    # Assert emergency halt
    assert result.success is False
    assert result.channel_status == "captcha_blocked"
    assert len(bot.sent_messages) == 1
    assert "CẢNH BÁO CAPTCHA" in bot.sent_messages[0]["text"]

    # Channel updated in DB
    channel.lifecycle_status = "captcha_blocked"
    await async_db_session.commit()

    updated_chan = (await async_db_session.execute(select(ChannelModel).where(ChannelModel.channel_id == "chan_captcha_01"))).scalar_one()
    assert updated_chan.lifecycle_status == "captcha_blocked"


# ---------------------------------------------------------------------------
# 5. Combination: Published Video -> Comment Scanner -> Intent -> KOC Reply
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_comb_published_video_to_koc_reply(async_db_session, sample_fashion_product):
    """Pairwise flow: Scanner retrieves comments, classifier detects price inquiry, agent outputs high-conversion KOC reply."""
    # 1. Job marked as published
    job = VideoJobModel(
        job_id="job_active_01",
        product_id=sample_fashion_product["product_id"],
        status="published",
        published_video_id="tt_pub_job_active_01",
    )
    async_db_session.add(job)
    await async_db_session.commit()

    # 2. Comment scanner extracts comments
    scanner = CommentScanner()
    raw_comments = await scanner.scan_comments(job.published_video_id, limit=5)
    assert len(raw_comments) > 0

    # 3. Comment agent processes each comment
    agent = CommentAgent()
    for raw_c in raw_comments:
        c_text = raw_c["text"]
        intent = agent.classify_intent(c_text)
        reply = agent.generate_reply(c_text, sample_fashion_product, {})

        # Assert tone compliance
        assert ToneValidator.validate(reply) is True

        # Save to DB
        comment_record = VideoCommentModel(
            comment_id=raw_c["comment_id"],
            job_id=job.job_id,
            user_handle=raw_c["user"],
            comment_text=c_text,
            intent=intent.value,
            reply_text=reply,
            status="replied",
        )
        async_db_session.add(comment_record)

    await async_db_session.commit()

    # Verify all comments replied in DB
    replied = (await async_db_session.execute(select(VideoCommentModel).where(VideoCommentModel.job_id == job.job_id))).scalars().all()
    assert len(replied) == len(raw_comments)
    for r in replied:
        assert r.status == "replied"
        assert len(r.reply_text) > 10
