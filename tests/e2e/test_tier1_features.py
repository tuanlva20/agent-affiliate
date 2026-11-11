"""Tier 1: Comprehensive Feature Isolation Test Suite (F01 to F29).

Verifies every AMAS v1.4.0 capability independently against requirements and interface contracts.
"""

import os
import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy import select

from tests.e2e.conftest import (
    AppConfig,
    AudioTranscriber,
    BaseScoutAgent,
    BrowserAdapter,
    ChannelModel,
    CommentAgent,
    CommentIntent,
    CommentScanner,
    CompetitorModel,
    FashionScoutAgent,
    HomeLifeScoutAgent,
    HumanBehaviorService,
    KalodataClient,
    MetricModel,
    NicheConfig,
    NicheModel,
    ProductCandidate,
    ProductModel,
    ScriptGenerator,
    SmartPublisher,
    SpecialistEvaluation,
    TTSService,
    TelegramCommandCenter,
    TikTokScraper,
    TikTokVideoMeta,
    ToneValidator,
    VideoCommentModel,
    VideoDownloader,
    VideoJobModel,
    VideoProcessor,
    VideoStudioAgent,
    get_approval_keyboard,
    load_config,
    route_topic,
    run_cli,
    HermesOrchestrator,
)


# ---------------------------------------------------------------------------
# F01: Central Config Loader
# ---------------------------------------------------------------------------
def test_f01_config_loader(sample_config_yaml):
    """F01: Validates that configuration loads properly and maps all subsystems."""
    config = load_config(str(sample_config_yaml))
    assert isinstance(config, AppConfig)
    assert config.app_name == "AMAS"
    assert config.version == "1.4.0"
    assert len(config.niches) == 2

    niche_ids = [n.niche_id for n in config.niches]
    assert "thoi_trang_nu" in niche_ids
    assert "do_gia_dung" in niche_ids

    assert config.browser.provider == "aliasmode"
    assert config.telegram.admin_id == 987654321
    assert config.telegram.forum_topics["thoi_trang_nu"] == 101


# ---------------------------------------------------------------------------
# F02: Async DB Engine & Session
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_f02_async_db_engine_session(async_db_session):
    """F02: Validates async DB engine creation and transactional session."""
    niche = NicheModel(niche_id="test_niche", name="Ngách Thử Nghiệm", description="Test Description")
    async_db_session.add(niche)
    await async_db_session.commit()

    result = await async_db_session.execute(select(NicheModel).where(NicheModel.niche_id == "test_niche"))
    fetched = result.scalar_one_or_none()
    assert fetched is not None
    assert fetched.name == "Ngách Thử Nghiệm"


# ---------------------------------------------------------------------------
# F03: Domain Data Models (7 Core Models)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_f03_domain_models(async_db_session):
    """F03: Validates all 7 domain models with foreign keys and lifecycle attributes."""
    # 1. Niche
    niche = NicheModel(niche_id="thoi_trang_nu", name="Thời Trang Nữ")
    async_db_session.add(niche)

    # 2. Channel
    channel = ChannelModel(
        channel_id="chan_fashion_01",
        niche_id="thoi_trang_nu",
        browser_provider="aliasmode",
        browser_profile_id="alias_prof_01",
        lifecycle_status="warming",
        warmup_days_completed=1,
    )
    async_db_session.add(channel)

    # 3. Competitor
    competitor = CompetitorModel(
        competitor_id="comp_01",
        niche_id="thoi_trang_nu",
        handle="@koc_hang_dau",
        profile_url="https://tiktok.com/@koc_hang_dau",
        avg_views=150000.0,
    )
    async_db_session.add(competitor)

    # 4. Product
    product = ProductModel(
        product_id="prod_dress_01",
        niche_id="thoi_trang_nu",
        title="Váy Chữ A Hack Dáng",
        price_vnd=199000.0,
        commission_rate=0.15,
        product_url="https://shop.tiktok.com/p/01",
        raw_data={"rating": 4.9, "sold": 3000},
    )
    async_db_session.add(product)

    # 5. VideoJob
    job = VideoJobModel(
        job_id="job_01",
        product_id="prod_dress_01",
        channel_id="chan_fashion_01",
        status="queued",
    )
    async_db_session.add(job)

    # 6. VideoComment
    comment = VideoCommentModel(
        comment_id="comm_01",
        job_id="job_01",
        user_handle="@buyer_girl",
        comment_text="Váy này có size L không chị?",
        intent="ask_material_usage",
    )
    async_db_session.add(comment)

    # 7. Metric
    metric = MetricModel(
        metric_id="met_01",
        job_id="job_01",
        views=1000,
        likes=50,
        clicks_yellow_cart=12,
    )
    async_db_session.add(metric)

    await async_db_session.commit()

    # Query back and verify relations
    job_res = await async_db_session.execute(select(VideoJobModel).where(VideoJobModel.job_id == "job_01"))
    fetched_job = job_res.scalar_one()
    assert fetched_job.product_id == "prod_dress_01"
    assert fetched_job.status == "queued"


# ---------------------------------------------------------------------------
# F04: Anti-Robotic ToneValidator
# ---------------------------------------------------------------------------
def test_f04_anti_robotic_tone_validator():
    """F04: Validates strict rejection of AI cliches, fakes, and exaggerated medical claims."""
    # Natural KOC speeches -> MUST PASS
    assert ToneValidator.validate("Chị em ơi, chiếc váy này mặc tôn dáng cực kỳ luôn!") is True
    assert ToneValidator.validate("Bà nào bụng dưới to bơi hết vào đây nhận mã freeship nha!") is True
    assert ToneValidator.validate("Từ ngày tậu cái này việc nhà nhàn hẳn, 3s là sạch bóng.") is True

    # AI cliches -> MUST FAIL
    assert ToneValidator.validate("Xin chào quý khách, tôi là trợ lý AI.") is False
    assert ToneValidator.validate("Sản phẩm này rất tốt và tiện ích cho người tiêu dùng.") is False
    assert ToneValidator.validate("Chúc quý khách một ngày tốt lành và hạnh phúc.") is False

    # Counterfeit fakes -> MUST FAIL
    assert ToneValidator.validate("Váy phong cách Zara cao cấp cực sang chảnh") is False
    assert ToneValidator.validate("Túi xách Chanel rep 1:1 siêu đẹp") is False
    assert ToneValidator.validate("Giày Gucci super fake chuẩn từng đường chỉ") is False

    # Exaggerated medical/claims -> MUST FAIL
    assert ToneValidator.validate("Kem bôi trị dứt điểm 100% tàn nhang sau 3 ngày") is False
    assert ToneValidator.validate("Vĩnh viễn không bám bẩn với công nghệ nano") is False

    # Empty text -> MUST FAIL
    assert ToneValidator.validate("") is False
    assert ToneValidator.validate("   ") is False


# ---------------------------------------------------------------------------
# F05: Kalodata Async Client
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_f05_kalodata_async_client():
    """F05: Validates async Kalodata client returns viral products with metrics."""
    client = KalodataClient(token="valid_test_token")
    products = await client.get_top_products(category_id="thoi_trang_nu", limit=5)
    assert len(products) == 5
    for item in products:
        assert "product_id" in item
        assert "price" in item
        assert "commission_rate" in item
        assert item["price"] > 0
        assert item["commission_rate"] > 0.0


# ---------------------------------------------------------------------------
# F06: TikTok Scraper & Metadata
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_f06_tiktok_scraper_metadata():
    """F06: Validates video metadata and anchor product extractor."""
    scraper = TikTokScraper()
    meta = await scraper.download_video_metadata("https://www.tiktok.com/@koc_fashion/video/7123456789")
    assert isinstance(meta, TikTokVideoMeta)
    assert meta.video_id == "7123456789"
    assert meta.view_count > 0
    assert meta.anchor_product_id is not None
    assert "hack dáng" in meta.caption.lower()


# ---------------------------------------------------------------------------
# F07: Base Scout Agent
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_f07_base_scout_agent():
    """F07: Validates preliminary filtering by price and commission thresholds."""
    agent = BaseScoutAgent()
    raw_items = [
        {"product_id": "p1", "title": "Valid item", "price": 150000.0, "commission_rate": 0.15, "sales_30d": 500},
        {"product_id": "p2", "title": "Too cheap", "price": 20000.0, "commission_rate": 0.20, "sales_30d": 100},
        {"product_id": "p3", "title": "Low commission", "price": 200000.0, "commission_rate": 0.05, "sales_30d": 100},
    ]
    candidates = await agent.discover_candidates(niche_id="thoi_trang_nu", raw_items=raw_items)
    assert len(candidates) == 1
    assert candidates[0].product_id == "p1"
    assert candidates[0].price_vnd == 150000.0


# ---------------------------------------------------------------------------
# F08: Fashion Scout Agent
# ---------------------------------------------------------------------------
def test_f08_fashion_scout_agent(sample_fashion_product, sample_counterfeit_product=None):
    """F08: Validates specialist fashion scoring and trademark violation blocking."""
    scout = FashionScoutAgent()

    # Valid body-hack fashion item
    eval_result = scout.evaluate_product(sample_fashion_product)
    assert isinstance(eval_result, SpecialistEvaluation)
    assert eval_result.passed_filter is True
    assert eval_result.score >= 8.0
    assert "bụng" in eval_result.hook_angle.lower() or "eo" in eval_result.hook_angle.lower()

    # Counterfeit fake brand item -> MUST BE REJECTED
    fake_item = {
        "product_id": "fash_fake_01",
        "title": "Váy Chanel rep 1:1 siêu cấp",
        "price": 250000.0,
        "commission_rate": 0.20,
    }
    fake_eval = scout.evaluate_product(fake_item)
    assert fake_eval.passed_filter is False
    assert fake_eval.score == 0.0
    assert "trademark" in fake_eval.rejection_reason.lower() or "policy" in fake_eval.rejection_reason.lower()


# ---------------------------------------------------------------------------
# F09: HomeLife Scout Agent
# ---------------------------------------------------------------------------
def test_f09_homelife_scout_agent(sample_homelife_product):
    """F09: Validates specialist home utilities scoring and Before/After 3s hook detection."""
    scout = HomeLifeScoutAgent()

    eval_result = scout.evaluate_product(sample_homelife_product)
    assert isinstance(eval_result, SpecialistEvaluation)
    assert eval_result.passed_filter is True
    assert eval_result.score >= 8.5
    assert "3s" in eval_result.hook_angle or "nhàn" in eval_result.hook_angle

    # Exaggerated medical claim item -> MUST BE REJECTED
    exag_item = {
        "product_id": "home_fake_01",
        "title": "Chai xịt nano vĩnh viễn không bám bẩn",
        "price": 120000.0,
        "commission_rate": 0.15,
    }
    exag_eval = scout.evaluate_product(exag_item)
    assert exag_eval.passed_filter is False
    assert "exaggerated" in exag_eval.rejection_reason.lower() or "policy" in exag_eval.rejection_reason.lower()


# ---------------------------------------------------------------------------
# F10: Forum Topic Routing
# ---------------------------------------------------------------------------
def test_f10_forum_topic_routing():
    """F10: Validates routing of niche events to dedicated Telegram topics."""
    assert route_topic("thoi_trang_nu") == 101
    assert route_topic("do_gia_dung") == 102
    assert route_topic("unknown_niche") == 100


# ---------------------------------------------------------------------------
# F11: 1-Tap Approval Keyboards
# ---------------------------------------------------------------------------
def test_f11_1tap_approval_keyboards():
    """F11: Validates inline keyboard formatting for Human-in-the-Loop review."""
    kb = get_approval_keyboard("prod_123")
    buttons = kb["inline_keyboard"][0]
    assert len(buttons) == 2
    assert buttons[0]["callback_data"] == "approve_product:prod_123"
    assert buttons[1]["callback_data"] == "reject_product:prod_123"


# ---------------------------------------------------------------------------
# F12: Bot Command Center
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_f12_bot_command_center():
    """F12: Validates bot command dispatcher and security guard."""
    bot = TelegramCommandCenter(admin_id=987654321)

    # Authorized admin commands
    assert "trinh sát" in (await bot.handle_command("/test_scout", 987654321, "thoi_trang_nu"))
    assert "pipeline" in (await bot.handle_command("/test_video", 987654321))
    assert "Comment Agent" in (await bot.handle_command("/test_reply", 987654321))
    assert "đang hoạt động" in (await bot.handle_command("/status", 987654321))
    assert "warming" in (await bot.handle_command("/create_channel", 987654321, "koc_02"))
    assert "lướt feed dạo" in (await bot.handle_command("/warmup", 987654321))

    # Unauthorized non-admin command -> MUST BE DENIED
    denied = await bot.handle_command("/test_scout", user_id=111222333)
    assert "Quyền truy cập bị từ chối" in denied


# ---------------------------------------------------------------------------
# F13: Video Downloader
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_f13_video_downloader():
    """F13: Validates source video downloader."""
    downloader = VideoDownloader()
    path = await downloader.download_video("https://tiktok.com/@competitor/video/712345")
    assert os.path.exists(path)
    assert path.endswith(".mp4")


# ---------------------------------------------------------------------------
# F14: Audio Transcriber
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_f14_audio_transcriber(tmp_path):
    """F14: Validates speech-to-text audio transcriber."""
    media = tmp_path / "sample.mp4"
    media.touch()
    transcriber = AudioTranscriber()
    transcript = await transcriber.transcribe(str(media))
    assert isinstance(transcript, str)
    assert len(transcript) > 10


# ---------------------------------------------------------------------------
# F15: KOC Script Generator
# ---------------------------------------------------------------------------
def test_f15_koc_script_generator(sample_fashion_product):
    """F15: Validates natural KOC viral script generation with Hook 3s and yellow cart CTA."""
    gen = ScriptGenerator()
    script = gen.generate_script(sample_fashion_product, {"tone": "koc"})
    assert "hook_3s" in script
    assert "cta_yellow_cart" in script
    assert "caption" in script
    # Verify no robotic AI smells
    assert ToneValidator.validate(script["full_voiceover"]) is True


# ---------------------------------------------------------------------------
# F16: Natural TTS Service
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_f16_natural_tts_service():
    """F16: Validates Vietnamese natural speech synthesis."""
    tts = TTSService()
    audio = await tts.synthesize("Chị em ơi, chiếc váy này xinh xỉu luôn á!", voice="vi-VN-HoaiMyNeural")
    assert os.path.exists(audio)
    assert audio.endswith(".mp3")


# ---------------------------------------------------------------------------
# F17: Video Processor
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_f17_video_processor(tmp_path):
    """F17: Validates FFmpeg copyright evasion remuxer."""
    video = tmp_path / "raw.mp4"
    audio = tmp_path / "voice.mp3"
    out = tmp_path / "remixed.mp4"
    video.touch()
    audio.touch()

    proc = VideoProcessor()
    res = await proc.remix_video(str(video), str(audio), str(out))
    assert os.path.exists(res)


# ---------------------------------------------------------------------------
# F18: Video Studio Agent
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_f18_video_studio_agent(sample_fashion_product):
    """F18: Validates end-to-end studio video production coordinator."""
    studio = VideoStudioAgent()
    final_video = await studio.produce_video(
        job_id="job_e2e_01",
        product_meta=sample_fashion_product,
        persona={"tone": "friendly"},
    )
    assert os.path.exists(final_video)
    assert "job_e2e_01" in final_video


# ---------------------------------------------------------------------------
# F19: AliasMode Browser Adapter
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_f19_aliasmode_browser_adapter():
    """F19: Validates profile management and CDP connection via AliasMode."""
    adapter = BrowserAdapter(api_url="http://127.0.0.1:50325")
    pid = await adapter.create_profile("fashion_koc_01", proxy="http://user:pass@1.2.3.4:8080")
    assert pid.startswith("alias_prof_")

    cdp_url = await adapter.start_browser(pid)
    assert cdp_url.startswith("ws://127.0.0.1:50325/devtools/browser/")


# ---------------------------------------------------------------------------
# F20: Inertial Human Scrolling
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_f20_inertial_human_scrolling():
    """F20: Validates wheel scroll with variable acceleration and overshoot."""
    mock_page = MagicMock()
    mock_page.mouse = MagicMock()
    mock_page.mouse.wheel = AsyncMock()

    service = HumanBehaviorService()
    await service.human_scroll(mock_page, steps=4)
    assert mock_page.mouse.wheel.call_count >= 4


# ---------------------------------------------------------------------------
# F21: Biometric Typing Simulation
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_f21_biometric_typing_simulation():
    """F21: Validates biometric keystroke delay and typo with backspace correction."""
    mock_page = MagicMock()
    mock_page.click = AsyncMock()
    mock_page.keyboard = MagicMock()
    pressed_keys = []

    async def record_press(key):
        pressed_keys.append(key)

    mock_page.keyboard.press = AsyncMock(side_effect=record_press)

    service = HumanBehaviorService()
    # Force typo rate = 1.0 to ensure typo and Backspace are triggered
    await service.human_type(mock_page, "#caption_input", "Váy", typo_rate=1.0)
    assert "Backspace" in pressed_keys
    assert "V" in pressed_keys
    assert "á" in pressed_keys
    assert "y" in pressed_keys


# ---------------------------------------------------------------------------
# F22: Bezier Mouse Movement
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_f22_bezier_mouse_movement():
    """F22: Validates smooth mouse hover before click."""
    mock_page = MagicMock()
    mock_page.hover = AsyncMock()
    mock_page.click = AsyncMock()

    service = HumanBehaviorService()
    await service.human_move_and_click(mock_page, "button#upload")
    mock_page.hover.assert_awaited_once_with("button#upload")
    mock_page.click.assert_awaited_once_with("button#upload")


# ---------------------------------------------------------------------------
# F23: Pre-posting Feed Warmup
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_f23_pre_posting_feed_warmup():
    """F23: Validates 3-5 minute feed browsing session before upload."""
    mock_page = MagicMock()
    mock_page.goto = AsyncMock()
    mock_page.mouse = MagicMock()
    mock_page.mouse.wheel = AsyncMock()

    service = HumanBehaviorService()
    success = await service.warmup_feed_session(mock_page, duration_seconds=5)
    assert success is True
    mock_page.goto.assert_awaited_once_with("https://www.tiktok.com")


# ---------------------------------------------------------------------------
# F24: Emergency Captcha Guard
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_f24_emergency_captcha_guard(tmp_path):
    """F24: Validates immediate abort, screenshot, and Telegram alarm on Captcha."""
    mock_page = MagicMock()
    mock_page.is_visible = AsyncMock(return_value=True)  # Captcha visible
    mock_page.screenshot = AsyncMock()

    bot = TelegramCommandCenter(admin_id=987654321)
    service = HumanBehaviorService()

    caught = await service.detect_and_handle_captcha(mock_page, telegram_bot=bot)
    assert caught is True
    mock_page.screenshot.assert_awaited_once()
    assert len(bot.sent_messages) == 1
    assert "CẢNH BÁO CAPTCHA" in bot.sent_messages[0]["text"]


# ---------------------------------------------------------------------------
# F25: Smart Publisher Agent
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_f25_smart_publisher_agent():
    """F25: Validates video publication with channel lifecycle guard and anchor link."""
    publisher = SmartPublisher(BrowserAdapter(), HumanBehaviorService())

    # Case 1: Channel in 'warming' -> MUST BE BLOCKED
    warming_channel = {"channel_id": "c1", "lifecycle_status": "warming"}
    res1 = await publisher.publish_video("job_1", warming_channel, "/tmp/vid.mp4", "Caption", {})
    assert res1.success is False
    assert res1.channel_status == "warming"
    assert "warming stage" in res1.error

    # Case 2: Channel in 'ready_to_post' -> SUCCESSFUL PUBLISH
    ready_channel = {"channel_id": "c2", "lifecycle_status": "ready_to_post"}
    res2 = await publisher.publish_video("job_2", ready_channel, "/tmp/vid.mp4", "Caption", {"product_id": "p1"})
    assert res2.success is True
    assert res2.video_id == "tt_pub_job_2"
    assert res2.channel_status == "cooldown"


# ---------------------------------------------------------------------------
# F26: Video Comment Scanner
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_f26_video_comment_scanner():
    """F26: Validates scraping recent comments from published videos."""
    scanner = CommentScanner()
    comments = await scanner.scan_comments("tt_pub_101", limit=5)
    assert len(comments) >= 3
    for c in comments:
        assert "comment_id" in c
        assert "text" in c
        assert "user" in c


# ---------------------------------------------------------------------------
# F27: Intent & KOC Reply Agent
# ---------------------------------------------------------------------------
def test_f27_intent_and_koc_reply_agent(sample_fashion_product):
    """F27: Validates comment intent classification and natural KOC reply generation."""
    agent = CommentAgent()

    # Intent classification
    assert agent.classify_intent("Váy này giá bao nhiêu vậy shop?") == CommentIntent.ASK_PRICE
    assert agent.classify_intent("Bụng 75cm mặc size nào vừa ạ?") == CommentIntent.ASK_MATERIAL_USAGE
    assert agent.classify_intent("Giao hàng lâu quá shop ơi!") == CommentIntent.COMPLAINT
    assert agent.classify_intent("Tuyệt vời") == CommentIntent.OTHER

    # Reply generation
    price_reply = agent.generate_reply("Váy này bao tiền thế?", sample_fashion_product, {})
    assert "189,000" in price_reply or "189" in price_reply
    assert "giỏ hàng" in price_reply.lower() or "freeship" in price_reply.lower()
    assert ToneValidator.validate(price_reply) is True


# ---------------------------------------------------------------------------
# F28: Hermes State Coordinator
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_f28_hermes_state_coordinator(sample_app_config):
    """F28: Validates LangGraph state transitions and multi-agent coordination."""
    hermes = HermesOrchestrator(sample_app_config)
    graph = hermes.build_state_graph()
    assert "scout_products" in graph
    assert "specialist_eval" in graph["scout_products"]
    assert "smart_publish" in graph["video_render"]

    # Step execution
    step_res = await hermes.run_pipeline_step("scout", {"niche_id": "thoi_trang_nu"})
    assert step_res["status"] == "success"
    assert step_res["count"] > 0


# ---------------------------------------------------------------------------
# F29: CLI Runner & Daemon
# ---------------------------------------------------------------------------
def test_f29_cli_runner_and_daemon():
    """F29: Validates CLI runner command line options and exit codes."""
    assert run_cli(["--help"]) == 0
    assert run_cli(["--mode", "dry-run"]) == 0
    assert run_cli(["--mode", "bot"]) == 0
    assert run_cli(["--mode", "scout"]) == 0
    assert run_cli(["--mode", "daemon"]) == 0
    assert run_cli(["--mode", "invalid_mode"]) == 1
    assert run_cli(["--mode"]) == 2
