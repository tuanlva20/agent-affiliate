"""Tier 2: Boundary, Adversarial, and Corner Case Test Suite.

Stress-tests AMAS v1.4.0 resilience against malformed inputs, extreme bounds, counterfeit trademarks,
captcha interrupts, authentication failures, rate limits, and SQL/XSS injections.
"""

import asyncio
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
    FashionScoutAgent,
    HomeLifeScoutAgent,
    HumanBehaviorService,
    KalodataClient,
    NicheConfig,
    ProductModel,
    SmartPublisher,
    SpecialistEvaluation,
    TTSService,
    TelegramCommandCenter,
    TikTokScraper,
    ToneValidator,
    VideoJobModel,
    load_config,
    run_cli,
)


# ---------------------------------------------------------------------------
# 1. Empty, Malformed, and Whitespace Inputs
# ---------------------------------------------------------------------------
def test_boundary_empty_and_whitespace_inputs(tmp_path):
    """Stress test empty config, blank titles, and whitespace handling."""
    # Empty config file
    empty_cfg = tmp_path / "empty.yaml"
    empty_cfg.write_text("", encoding="utf-8")
    cfg = load_config(str(empty_cfg))
    assert isinstance(cfg, AppConfig)
    assert len(cfg.niches) == 0

    # Non-existent config
    with pytest.raises(FileNotFoundError):
        load_config("/path/to/non_existent_config.yaml")

    # ToneValidator on whitespace and empty
    assert ToneValidator.validate("") is False
    assert ToneValidator.validate("   ") is False
    assert ToneValidator.validate("\n\t\r") is False


# ---------------------------------------------------------------------------
# 2. Extreme Pricing & Commission Outliers
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_boundary_extreme_pricing_and_commissions():
    """Validates boundary filtering on zero, negative, and excessive prices/commissions."""
    scout = BaseScoutAgent()
    fashion_scout = FashionScoutAgent()
    homelife_scout = HomeLifeScoutAgent()

    test_items = [
        {"product_id": "p_zero", "title": "Váy hoa", "price": 0.0, "commission_rate": 0.15},
        {"product_id": "p_negative", "title": "Cây lau nhà", "price": -50000.0, "commission_rate": 0.20},
        {"product_id": "p_extreme_high", "title": "Váy kim cương", "price": 99999999999.0, "commission_rate": 0.15},
        {"product_id": "p_comm_zero", "title": "Váy xinh", "price": 199000.0, "commission_rate": 0.0},
        {"product_id": "p_comm_excessive", "title": "Chổi quét", "price": 120000.0, "commission_rate": 1.50},
    ]

    # Base scout filtering
    candidates = await scout.discover_candidates("thoi_trang_nu", test_items)
    for c in candidates:
        assert c.price_vnd >= 50000.0
        assert 0.0 < c.commission_rate <= 1.0


# ---------------------------------------------------------------------------
# 3. Counterfeit Brand & Trademark Matrix (Zero-Tolerance)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "suspicious_title",
    [
        "Váy tiểu thư Zara chuẩn auth",
        "Set đồ thiết kế phong cách Chanel sang chảnh",
        "Túi xách nữ Gucci da xịn",
        "Áo sơ mi Dior thêu hoa cao cấp",
        "Ví cầm tay Louis Vuitton thời thượng",
        "Khăn lụa Hermes mềm mịn",
        "Đầm suông form rộng rep 1:1 y hình",
        "Áo khoác dạ tweed super fake loại 1",
        "Váy thiết kế hang fake xuất xịn",
        "Giày búp bê nhái thương hiệu lớn",
    ],
)
def test_boundary_counterfeit_trademark_matrix(suspicious_title):
    """Enforces absolute rejection of counterfeit brands across validator and fashion scout."""
    # ToneValidator check
    assert ToneValidator.validate(suspicious_title) is False

    # FashionScoutAgent check
    scout = FashionScoutAgent()
    evaluation = scout.evaluate_product({
        "product_id": "test_fake",
        "title": suspicious_title,
        "price": 220000.0,
        "commission_rate": 0.18,
    })
    assert evaluation.passed_filter is False
    assert evaluation.score == 0.0
    assert "trademark" in evaluation.rejection_reason.lower() or "policy" in evaluation.rejection_reason.lower()


# ---------------------------------------------------------------------------
# 4. Exaggerated Medical & Functional Claims Matrix
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "exaggerated_title",
    [
        "Serum bôi trị dứt điểm 100% mụn thâm",
        "Chai xịt phủ nano vĩnh viễn không bám bẩn",
        "Nước lau sàn cam kết chữa khỏi nấm mốc",
        "Thuốc thảo mộc 100% hết bệnh xương khớp",
        "Dung dịch chữa dứt điểm vết ố vàng trọn đời",
    ],
)
def test_boundary_exaggerated_claims_matrix(exaggerated_title):
    """Enforces zero tolerance against exaggerated medical/utility claims."""
    # ToneValidator check
    assert ToneValidator.validate(exaggerated_title) is False

    # HomeLifeScoutAgent check
    scout = HomeLifeScoutAgent()
    evaluation = scout.evaluate_product({
        "product_id": "test_exag",
        "title": exaggerated_title,
        "price": 95000.0,
        "commission_rate": 0.15,
    })
    assert evaluation.passed_filter is False
    assert evaluation.score == 0.0


# ---------------------------------------------------------------------------
# 5. Captcha Emergency Handling & Channel Lockdown
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_boundary_captcha_emergency_handling():
    """Validates that Captcha appearance instantly stops publisher and transitions channel to captcha_blocked."""
    mock_page = MagicMock()
    # Simulate slider captcha appearance
    mock_page.is_visible = AsyncMock(side_effect=lambda sel: sel == "#secsdk-captcha-drag-wrapper")
    mock_page.screenshot = AsyncMock()

    bot = TelegramCommandCenter(admin_id=987654321)
    publisher = SmartPublisher(BrowserAdapter(), HumanBehaviorService())

    channel_info = {
        "channel_id": "chan_fashion_01",
        "lifecycle_status": "ready_to_post",
    }

    result = await publisher.publish_video(
        job_id="job_captcha_test",
        channel_info=channel_info,
        video_path="/tmp/video.mp4",
        caption="Caption test",
        product_anchor={"product_id": "p1"},
        mock_page=mock_page,
        telegram_bot=bot,
    )

    # 1. Publishing must fail immediately
    assert result.success is False
    assert result.channel_status == "captcha_blocked"
    assert "Captcha" in result.error

    # 2. Screenshot must have been taken
    mock_page.screenshot.assert_awaited_once_with(path="screenshots/captcha_detected.png")

    # 3. Telegram alert must be dispatched
    assert len(bot.sent_messages) == 1
    assert "🚨 [CẢNH BÁO CAPTCHA TIKTOK]" in bot.sent_messages[0]["text"]

    # 4. Subsequent publish calls on this blocked channel must be rejected without navigation
    blocked_res = await publisher.publish_video(
        job_id="job_subsequent",
        channel_info={"channel_id": "chan_fashion_01", "lifecycle_status": "captcha_blocked"},
        video_path="/tmp/video.mp4",
        caption="Subsequent caption",
        product_anchor={},
    )
    assert blocked_res.success is False
    assert "blocked by Captcha" in blocked_res.error


# ---------------------------------------------------------------------------
# 6. Channel Lifecycle State Boundary Guards
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "invalid_status,expected_error_substr",
    [
        ("warming", "warming stage"),
        ("captcha_blocked", "blocked by Captcha"),
    ],
)
@pytest.mark.asyncio
async def test_boundary_channel_lifecycle_states(invalid_status, expected_error_substr):
    """Guards against unlawful posting on warming or blocked channels."""
    publisher = SmartPublisher(BrowserAdapter(), HumanBehaviorService())
    res = await publisher.publish_video(
        job_id="job_status_guard",
        channel_info={"channel_id": "c_guard", "lifecycle_status": invalid_status},
        video_path="/tmp/mock.mp4",
        caption="Test",
        product_anchor={},
    )
    assert res.success is False
    assert expected_error_substr in res.error


# ---------------------------------------------------------------------------
# 7. Network Timeouts and Auth Expiration Errors
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_boundary_network_timeouts_and_auth_errors():
    """Validates graceful error handling during Kalodata token expiration and scraper failures."""
    # Expired token in Kalodata client
    client = KalodataClient(token="expired_token")
    with pytest.raises(PermissionError) as exc_info:
        await client.get_top_products("thoi_trang_nu")
    assert "~/.kalopilot/token" in str(exc_info.value)

    # Invalid TikTok Scraper URL
    scraper = TikTokScraper()
    with pytest.raises(ValueError):
        await scraper.download_video_metadata("https://youtube.com/watch?v=12345")

    with pytest.raises(ValueError):
        await scraper.download_video_metadata("")

    # Browser profile not found
    adapter = BrowserAdapter()
    with pytest.raises(KeyError):
        await adapter.start_browser("non_existent_profile_id")


# ---------------------------------------------------------------------------
# 8. SQL Injection & XSS Escaping Integrity
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_boundary_sql_and_xss_injections(async_db_session):
    """Verifies that malicious payloads do not break database integrity or crash validation."""
    malicious_inputs = [
        "'; DROP TABLE products; --",
        "' OR '1'='1",
        "<script>alert('XSS')</script>",
        "🎉 🚀 \x00\x08 \u202eRTL_OVERRIDE",
    ]

    for payload in malicious_inputs:
        # DB insertion test with parameterization
        prod = ProductModel(
            product_id=f"prod_inject_{abs(hash(payload))}",
            niche_id="thoi_trang_nu",
            title=payload,
            price_vnd=150000.0,
            commission_rate=0.15,
            product_url="https://shop.tiktok.com",
            raw_data={"payload": payload},
        )
        async_db_session.add(prod)
        await async_db_session.commit()

        # Query back
        res = await async_db_session.execute(select(ProductModel).where(ProductModel.product_id == prod.product_id))
        fetched = res.scalar_one()
        assert fetched.title == payload

    # Tables must still exist
    products_count = await async_db_session.execute(select(ProductModel))
    assert len(products_count.scalars().all()) == len(malicious_inputs)


# ---------------------------------------------------------------------------
# 9. Concurrency & High Volume Burst Loads
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_boundary_burst_concurrency_load(async_db_session):
    """Stress tests concurrent DB writes and bot command bursts."""
    # 20 concurrent product insertions
    async def insert_product(idx: int):
        p = ProductModel(
            product_id=f"burst_prod_{idx}",
            niche_id="thoi_trang_nu",
            title=f"Burst Item {idx}",
            price_vnd=100000.0 + idx,
            commission_rate=0.10,
            product_url="https://tiktok.com",
        )
        async_db_session.add(p)

    tasks = [insert_product(i) for i in range(25)]
    await asyncio.gather(*tasks)
    await async_db_session.commit()

    res = await async_db_session.execute(select(ProductModel))
    all_products = res.scalars().all()
    assert len(all_products) >= 25
