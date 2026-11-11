"""Comprehensive Test Suite for Comment Engagement & Conversion Agent (Feature F26 & F27).

Covers:
1. CommentScanner offline/mock scraping, live API parsing, error handling, and database persistence (F26).
2. CommentIntent classification across all 4 categories, Vietnamese slang, homographs, false-positive guards, and priority (F27).
3. KOC Reply Generation for Fashion (Hoài My) with Yellow Cart CTA and body-hack focus.
4. KOC Reply Generation for Home Utilities (Nam Minh) with Yellow Cart CTA and labor-saving focus.
5. 100% ToneValidator compliance guarantee on all generated responses.
6. Title sanitization against counterfeit brands and policy violations.
7. SQLAlchemy VideoComment database persistence and lifecycle management.
8. LLM integration and automatic fallback resilience.
"""

from datetime import datetime, timezone
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch
import aiohttp
import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.agents.comment_agent import CommentAgent, CommentIntent
from src.core.tone_validator import ToneValidator
from src.database.models import Base, Channel, Niche, Product, VideoComment, VideoJob
from src.services.comment_scanner import (
    CommentRateLimitError,
    CommentScanner,
    CommentScannerError,
    CommentScannerTimeoutError,
    InvalidVideoIdError,
    VideoNotFoundError,
)


# ==============================================================================
# Fixtures
# ==============================================================================

@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Hermetic isolated AsyncSession for comment agent tests."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
def sample_fashion_product():
    return {
        "product_id": "fash_dress_001",
        "niche_id": "thoi_trang_nu",
        "title": "Váy hoa nhí dáng xòe chiết eo hack dáng đỉnh cao",
        "price": 189000.0,
        "commission_rate": 0.15,
        "sales_30d": 3500,
        "revenue_30d": 661500000.0,
        "product_url": "https://shop.tiktok.com/view/product/fash_dress_001",
    }


@pytest.fixture
def sample_homelife_product():
    return {
        "product_id": "home_mop_001",
        "niche_id": "do_gia_dung",
        "title": "Cây lau nhà tự vắt xoay 360 độ đa năng thông minh",
        "price": 149000.0,
        "commission_rate": 0.18,
        "sales_30d": 5200,
        "revenue_30d": 774800000.0,
        "product_url": "https://shop.tiktok.com/view/product/home_mop_001",
    }


@pytest.fixture
def sample_dirty_product():
    return {
        "product_id": "dirty_prod_999",
        "niche_id": "thoi_trang_nu",
        "title": "Váy Zara rep 1:1 siêu xịn tốt nhất thị trường vĩnh viễn không hỏng",
        "price": 250000.0,
    }


# ==============================================================================
# 1. CommentScanner Contract & Functionality (F26)
# ==============================================================================

class TestCommentScanner:
    """Tests for CommentScanner service scraping and output contract."""

    @pytest.mark.asyncio
    async def test_scan_comments_f26_contract(self):
        scanner = CommentScanner()
        comments = await scanner.scan_comments("tt_pub_101", limit=5)
        assert len(comments) >= 3
        for c in comments:
            assert "comment_id" in c
            assert "text" in c
            assert "user" in c
            assert "timestamp" in c
            assert "author_name" in c
            assert "author_id" in c
            assert "like_count" in c
            assert "reply_count" in c
            assert isinstance(c["comment_id"], str)
            assert isinstance(c["text"], str)
            assert len(c["text"].strip()) > 0

    @pytest.mark.asyncio
    async def test_scan_comments_limit_partitions(self):
        scanner = CommentScanner(mock_mode=True)
        assert len(await scanner.scan_comments("vid_1", limit=1)) == 1
        assert len(await scanner.scan_comments("vid_1", limit=3)) == 3
        assert len(await scanner.scan_comments("vid_1", limit=0)) == 0
        assert len(await scanner.scan_comments("vid_1", limit=-5)) == 0

    @pytest.mark.asyncio
    async def test_scan_comments_url_extraction(self):
        scanner = CommentScanner(mock_mode=True)
        url = "https://www.tiktok.com/@koc_fashion/video/7123456789?is_from_webapp=1"
        comments = await scanner.scan_comments(url, limit=2)
        assert len(comments) == 2
        assert "7123456789" in comments[0]["comment_id"]

    @pytest.mark.asyncio
    async def test_scan_comments_invalid_ids(self):
        scanner = CommentScanner()
        for bad_id in ["", "   ", None, 12345, []]:
            with pytest.raises((InvalidVideoIdError, ValueError)):
                await scanner.scan_comments(bad_id)

    @pytest.mark.asyncio
    async def test_scan_comments_mock_deterministic(self):
        scanner = CommentScanner(mock_mode=True)
        c1 = await scanner.scan_comments("vid_stable", limit=3)
        c2 = await scanner.scan_comments("vid_stable", limit=3)
        assert [c["comment_id"] for c in c1] == [c["comment_id"] for c in c2]
        assert [c["text"] for c in c1] == [c["text"] for c in c2]

    @pytest.mark.asyncio
    async def test_scan_comments_live_api_success(self):
        fake_payload = {
            "status_code": 0,
            "comments": [
                {
                    "cid": "7001",
                    "text": "Váy đẹp quá shop ơi",
                    "create_time": 1715000000,
                    "digg_count": 5,
                    "reply_comment_total": 1,
                    "user": {"unique_id": "lan_anh", "nickname": "Lan Anh", "uid": "u1"},
                }
            ],
        }

        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value=fake_payload)
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.get.return_value = mock_resp

        scanner = CommentScanner(mock_mode=False, session=mock_session)
        res = await scanner.scan_comments("7123456789", limit=5)
        assert len(res) == 1
        assert res[0]["comment_id"] == "7001"
        assert res[0]["text"] == "Váy đẹp quá shop ơi"
        assert res[0]["user"] == "lan_anh"
        assert res[0]["author_name"] == "Lan Anh"

    @pytest.mark.asyncio
    async def test_scan_comments_live_rate_limit(self):
        mock_resp = AsyncMock()
        mock_resp.status = 429
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.get.return_value = mock_resp

        scanner = CommentScanner(
            mock_mode=False,
            session=mock_session,
            max_retries=1,
            rate_limit_delay=0.01,
            fallback_to_mock=False,
        )
        with pytest.raises(CommentRateLimitError):
            await scanner.scan_comments("vid_rate_limit", limit=5)

    @pytest.mark.asyncio
    async def test_scan_comments_live_rate_limit_fallback(self):
        mock_resp = AsyncMock()
        mock_resp.status = 429
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.get.return_value = mock_resp

        scanner = CommentScanner(
            mock_mode=False,
            session=mock_session,
            max_retries=1,
            rate_limit_delay=0.01,
            fallback_to_mock=True,
        )
        comments = await scanner.scan_comments("vid_rate_limit_fallback", limit=3)
        assert len(comments) == 3
        assert "c_vid_rate_limit_fallback_1" in comments[0]["comment_id"]

    @pytest.mark.asyncio
    async def test_scan_comments_timeout(self):
        mock_session = MagicMock()
        mock_session.get.side_effect = aiohttp.ServerTimeoutError("Request timed out")

        scanner = CommentScanner(
            mock_mode=False,
            session=mock_session,
            max_retries=0,
            timeout=0.01,
            fallback_to_mock=False,
        )
        with pytest.raises((CommentScannerTimeoutError, TimeoutError, CommentScannerError)):
            await scanner.scan_comments("vid_timeout", limit=5)

    @pytest.mark.asyncio
    async def test_sync_comments_to_db_idempotency(self, db_session):
        niche = Niche(niche_id="niche_fash", name="Thời trang", description="Váy")
        channel = Channel(
            channel_id="chan_fash_01",
            niche_id="niche_fash",
            browser_profile_id="prof_01",
        )
        db_session.add_all([niche, channel])
        await db_session.commit()

        scanner = CommentScanner(mock_mode=True)
        initial_comments = await scanner.scan_comments("tt_pub_101", limit=2)

        # First sync
        synced = await scanner.sync_comments_to_db(
            "tt_pub_101", "chan_fash_01", initial_comments, db_session
        )
        await db_session.commit()
        assert len(synced) == 2

        # Update first comment to 'replied'
        synced[0].reply_status = "replied"
        synced[0].reply_text = "Dạ chào chị yêu nè!"
        await db_session.commit()

        # Second sync with 3 comments (2 existing + 1 new)
        updated_comments = await scanner.scan_comments("tt_pub_101", limit=3)
        synced2 = await scanner.sync_comments_to_db(
            "tt_pub_101", "chan_fash_01", updated_comments, db_session
        )
        await db_session.commit()
        assert len(synced2) == 3

        # Verify idempotency: existing row was not overwritten back to 'pending'
        rows = (
            await db_session.execute(
                select(VideoComment).where(VideoComment.video_id == "tt_pub_101")
            )
        ).scalars().all()
        assert len(rows) == 3
        first_row = next(r for r in rows if r.comment_id == initial_comments[0]["comment_id"])
        assert first_row.reply_status == "replied"
        assert first_row.reply_text == "Dạ chào chị yêu nè!"

    @pytest.mark.asyncio
    async def test_sync_comments_to_db_intra_batch_dups(self, db_session):
        niche = Niche(niche_id="niche_dup", name="Dup Niche", description="Test")
        channel = Channel(
            channel_id="chan_dup_01",
            niche_id="niche_dup",
            browser_profile_id="prof_dup",
        )
        db_session.add_all([niche, channel])
        await db_session.commit()

        scanner = CommentScanner(mock_mode=True)
        raw_comments = [
            {"comment_id": "c_dup_1", "text": "Comment 1", "user": "user1"},
            {"comment_id": "c_dup_1", "text": "Comment 1 duplicate", "user": "user1"},
            {"comment_id": "c_dup_2", "text": "Comment 2", "user": "user2"},
        ]
        synced = await scanner.sync_comments_to_db(
            "vid_dup", "chan_dup_01", raw_comments, db_session
        )
        await db_session.commit()
        assert len(synced) == 3  # 2 unique records mapped across 3 items
        rows = (
            await db_session.execute(
                select(VideoComment).where(VideoComment.video_id == "vid_dup")
            )
        ).scalars().all()
        assert len(rows) == 2

    @pytest.mark.asyncio
    async def test_sync_comments_to_db_invalid_channel(self, db_session):
        scanner = CommentScanner()
        with pytest.raises(ValueError):
            await scanner.sync_comments_to_db("vid_1", "", [{"comment_id": "c1"}], db_session)


# ==============================================================================
# 2. Intent Classification Tests (F27)
# ==============================================================================

class TestCommentIntentClassification:
    """Tests for CommentAgent.classify_intent accuracy, slang handling, and homographs."""

    @pytest.fixture
    def agent(self):
        return CommentAgent()

    def test_tier1_contract_comments(self, agent):
        assert agent.classify_intent("Váy này giá bao nhiêu vậy shop?") == CommentIntent.ASK_PRICE
        assert agent.classify_intent("Bụng 75cm mặc size nào vừa ạ?") == CommentIntent.ASK_MATERIAL_USAGE
        assert agent.classify_intent("Giao hàng lâu quá shop ơi!") == CommentIntent.COMPLAINT
        assert agent.classify_intent("Tuyệt vời") == CommentIntent.OTHER

    @pytest.mark.parametrize("comment,expected", [
        # ASK_PRICE: Vietnamese slang & unaccented
        ("Váy này bao tiền thế?", CommentIntent.ASK_PRICE),
        ("nhiu xien vay shop", CommentIntent.ASK_PRICE),
        ("gia bn sop", CommentIntent.ASK_PRICE),
        ("inbox gia giup minh", CommentIntent.ASK_PRICE),
        ("ro gia the nao shop", CommentIntent.ASK_PRICE),
        ("bao nhieu a", CommentIntent.ASK_PRICE),
        ("cai gia de do nay bao tien", CommentIntent.ASK_PRICE),
        ("mấy củ vậy", CommentIntent.ASK_PRICE),
        ("mấy đồng shop ơi", CommentIntent.ASK_PRICE),

        # ASK_MATERIAL_USAGE: Sizing, body, fabric & appliance
        ("m7 60kg mặc sz gì", CommentIntent.ASK_MATERIAL_USAGE),
        ("55 cân vừa k shop", CommentIntent.ASK_MATERIAL_USAGE),
        ("bung 75 mac vua k", CommentIntent.ASK_MATERIAL_USAGE),
        ("chat vai dui hay cotton vay", CommentIntent.ASK_MATERIAL_USAGE),
        ("cay lau nha thong minh nay dung the nao", CommentIntent.ASK_MATERIAL_USAGE),
        ("cai gia treo nay lap kieu gi", CommentIntent.ASK_MATERIAL_USAGE),
        ("váy này mặc vừa khum shop", CommentIntent.ASK_MATERIAL_USAGE),
        ("chất co giãn hong shop", CommentIntent.ASK_MATERIAL_USAGE),
        ("cao 1m58 nang 48kg mac size nao", CommentIntent.ASK_MATERIAL_USAGE),
        ("chan vay dai den dau the", CommentIntent.ASK_MATERIAL_USAGE),

        # COMPLAINT: Shipping, defects, scam, returns
        ("hang loi rach roi doi tra the nao", CommentIntent.COMPLAINT),
        ("shop lua dao a", CommentIntent.COMPLAINT),
        ("dat 2 tuan ma chua nhan duoc hang", CommentIntent.COMPLAINT),
        ("giao sai mau roi shop oi", CommentIntent.COMPLAINT),
        ("vai xau khong giong hinh", CommentIntent.COMPLAINT),
        ("ship lau qua shop oi", CommentIntent.COMPLAINT),
        ("hang ko giong video", CommentIntent.COMPLAINT),

        # OTHER: False-positive guards, compliments, noise
        ("gia nhu e biet shop som hon", CommentIntent.OTHER),
        ("danh gia 5 sao cho shop nhe", CommentIntent.OTHER),
        ("vay dep gia re qua shop oi", CommentIntent.OTHER),
        ("chấm", CommentIntent.OTHER),
        ("haha cute qua", CommentIntent.OTHER),
        ("", CommentIntent.OTHER),
        ("   ", CommentIntent.OTHER),
        ("...", CommentIntent.OTHER),
        ("🥰🥰🥰", CommentIntent.OTHER),

        # Milestone 7 Remediation: Teen code & slang price inquiries
        ("bnhiu z sop", CommentIntent.ASK_PRICE),
        ("rổ rá", CommentIntent.ASK_PRICE),
        ("bn z shop", CommentIntent.ASK_PRICE),
        ("bnhieu vậy", CommentIntent.ASK_PRICE),
        ("bnhieu?", CommentIntent.ASK_PRICE),
        ("bnhiu?", CommentIntent.ASK_PRICE),

        # Milestone 7 Remediation: Fabric defects and price dissatisfaction complaints
        ("vải xấu quá mà giá đắt", CommentIntent.COMPLAINT),
        ("chất vải xấu mà giá đắt thế", CommentIntent.COMPLAINT),
        ("chất xấu như giẻ lau", CommentIntent.COMPLAINT),
        ("vải đểu thế mà bán 200k", CommentIntent.COMPLAINT),
        ("hàng xấu vải mỏng tang", CommentIntent.COMPLAINT),
        ("đắt wa ko giống video", CommentIntent.COMPLAINT),
        ("gia dat qua shop oi", CommentIntent.COMPLAINT),

        # Milestone 7 Remediation: Homograph protection (wear vs expensive, order vs expensive, courtesy bn)
        ("ao nay mac qua dep", CommentIntent.OTHER),
        ("minh dat qua mang", CommentIntent.OTHER),
        ("cảm ơn bn ạ", CommentIntent.OTHER),
    ])
    def test_partition_cases(self, agent, comment, expected):
        assert agent.classify_intent(comment) == expected

    def test_complaint_trumps_price(self, agent):
        comment = "Hàng giao chậm quá mà giá thì đắt, phục vụ tệ thật sự"
        assert agent.classify_intent(comment) == CommentIntent.COMPLAINT

    def test_complaint_trumps_material(self, agent):
        comment = "Vải rách nát rồi shop ơi, hàng lỗi không mặc được"
        assert agent.classify_intent(comment) == CommentIntent.COMPLAINT

    def test_m7_empirical_failures_resolved(self, agent):
        """Explicit regression assertion for all 9 empirical failures found by m7_challenger."""
        empirical_cases = {
            "bnhiu z sop": CommentIntent.ASK_PRICE,
            "rổ rá": CommentIntent.ASK_PRICE,
            "bn z shop": CommentIntent.ASK_PRICE,
            "bnhieu vậy": CommentIntent.ASK_PRICE,
            "vải xấu quá mà giá đắt": CommentIntent.COMPLAINT,
            "chất vải xấu mà giá đắt thế": CommentIntent.COMPLAINT,
            "chất xấu như giẻ lau": CommentIntent.COMPLAINT,
            "vải đểu thế mà bán 200k": CommentIntent.COMPLAINT,
            "hàng xấu vải mỏng tang": CommentIntent.COMPLAINT,
        }
        for comment, expected in empirical_cases.items():
            actual = agent.classify_intent(comment)
            assert actual == expected, f"Failed on '{comment}': expected {expected}, got {actual}"



# ==============================================================================
# 3. KOC Reply Generation: Fashion (Hoài My)
# ==============================================================================

class TestGenerateReplyFashion:
    """Tests KOC reply generation under Hoài My persona."""

    @pytest.fixture
    def agent(self):
        return CommentAgent()

    def test_fashion_ask_price_reply(self, agent, sample_fashion_product):
        reply = agent.generate_reply(
            "Váy này bao tiền thế shop?",
            sample_fashion_product,
            persona={"niche_id": "thoi_trang_nu"},
        )
        assert "189,000" in reply or "189" in reply
        assert any(cta in reply.lower() for cta in ["giỏ hàng", "freeship", "góc trái"])
        assert any(kw in reply.lower() for kw in ["chị em ơi", "mấy bà", "chị yêu", "nha"])
        assert ToneValidator.validate(reply) is True

    def test_fashion_ask_material_reply(self, agent, sample_fashion_product):
        reply = agent.generate_reply(
            "Bụng 75cm mặc có che được mỡ thừa không shop?",
            sample_fashion_product,
            persona={"name": "Hoài My"},
        )
        assert any(kw in reply.lower() for kw in ["bụng", "tôn dáng", "hack eo", "mát", "đũi", "size"])
        assert any(cta in reply.lower() for cta in ["giỏ hàng", "góc trái", "bảng"])
        assert ToneValidator.validate(reply) is True

    def test_fashion_complaint_reply(self, agent, sample_fashion_product):
        reply = agent.generate_reply(
            "Giao hàng chậm quá, chờ cả tuần rồi!",
            sample_fashion_product,
            persona={"niche_id": "thoi_trang_nu"},
        )
        assert any(kw in reply.lower() for kw in ["xin lỗi", "thông cảm", "nhắn tin", "hỗ trợ"])
        assert "giỏ hàng" not in reply.lower()  # Complaint should not push sales
        assert ToneValidator.validate(reply) is True

    def test_fashion_other_reply(self, agent, sample_fashion_product):
        reply = agent.generate_reply(
            "Mẫu mặc xinh xỉu luôn á!",
            sample_fashion_product,
            persona={"niche_id": "thoi_trang_nu"},
        )
        assert any(kw in reply.lower() for kw in ["cảm ơn", "mấy bà", "giỏ hàng", "yêu"])
        assert ToneValidator.validate(reply) is True


# ==============================================================================
# 4. KOC Reply Generation: Home Utilities (Nam Minh)
# ==============================================================================

class TestGenerateReplyHomeLife:
    """Tests KOC reply generation under Nam Minh persona."""

    @pytest.fixture
    def agent(self):
        return CommentAgent()

    def test_homelife_ask_price_reply(self, agent, sample_homelife_product):
        reply = agent.generate_reply(
            "Cây lau nhà này giá bao nhiêu vậy bác?",
            sample_homelife_product,
            persona={"niche_id": "do_gia_dung"},
        )
        assert "149,000" in reply or "149" in reply
        assert any(cta in reply.lower() for cta in ["giỏ hàng", "freeship", "góc trái"])
        assert any(kw in reply.lower() for kw in ["các bác", "bác ơi", "nhàn"])
        assert ToneValidator.validate(reply) is True

    def test_homelife_ask_material_reply(self, agent, sample_homelife_product):
        reply = agent.generate_reply(
            "Cây lau này có bền không và dùng có tốn sức không shop?",
            sample_homelife_product,
            persona={"name": "Nam Minh"},
        )
        assert any(kw in reply.lower() for kw in ["nhàn", "3s", "bền", "tiện", "inox", "abs"])
        assert any(cta in reply.lower() for cta in ["giỏ hàng", "góc trái"])
        assert ToneValidator.validate(reply) is True

    def test_homelife_complaint_reply(self, agent, sample_homelife_product):
        reply = agent.generate_reply(
            "Hàng bị trầy xước lúc nhận hàng rồi shop ơi!",
            sample_homelife_product,
            persona={"niche_id": "do_gia_dung"},
        )
        assert any(kw in reply.lower() for kw in ["xin lỗi", "thông cảm", "nhắn tin", "xử lý"])
        assert ToneValidator.validate(reply) is True

    def test_homelife_other_reply(self, agent, sample_homelife_product):
        reply = agent.generate_reply(
            "Video hướng dẫn lau nhà hay quá bác!",
            sample_homelife_product,
            persona={"niche_id": "do_gia_dung"},
        )
        assert any(kw in reply.lower() for kw in ["cảm ơn", "các bác", "nhàn", "giỏ hàng"])
        assert ToneValidator.validate(reply) is True


# ==============================================================================
# 5. ToneValidator Guarantee & Dirty Title Sanitization
# ==============================================================================

class TestToneValidatorGuarantee:
    """Verifies 100% compliance with ToneValidator and brand policy."""

    @pytest.fixture
    def agent(self):
        return CommentAgent()

    def test_100_percent_matrix_tone_compliance(
        self, agent, sample_fashion_product, sample_homelife_product
    ):
        test_comments = [
            "Giá bao nhiêu shop ơi?",
            "Có size cho người 60kg không?",
            "Vải gì vậy?",
            "Giao hàng lâu quá!",
            "Hàng lỗi rồi",
            "Mẫu xinh quá",
            "Chấm hóng link",
            "Có freeship không shop?",
        ]
        products = [sample_fashion_product, sample_homelife_product]
        personas = [
            {"niche_id": "thoi_trang_nu"},
            {"niche_id": "do_gia_dung"},
            {},
        ]

        for p in products:
            for pers in personas:
                for c in test_comments:
                    reply = agent.generate_reply(c, p, pers)
                    assert len(reply.strip()) > 0
                    assert ToneValidator.validate(reply) is True, f"Failed on comment '{c}': {reply}"

    def test_dirty_product_title_sanitization_in_reply(self, agent, sample_dirty_product):
        reply = agent.generate_reply(
            "Váy này giá thế nào em?",
            sample_dirty_product,
            persona={"niche_id": "thoi_trang_nu"},
        )
        assert ToneValidator.validate(reply) is True
        for banned in ["zara", "rep 1:1", "tốt nhất thị trường", "vĩnh viễn không hỏng"]:
            assert banned not in reply.lower()


# ==============================================================================
# 6. Database Integration with VideoComment ORM
# ==============================================================================

class TestDatabaseIntegration:
    """Tests end-to-end database persistence of VideoComment entities."""

    @pytest.mark.asyncio
    async def test_video_comment_lifecycle_in_database(
        self, db_session, sample_fashion_product
    ):
        # 1. Setup prerequisite records
        niche = Niche(niche_id="thoi_trang_nu", name="Thời trang nữ")
        channel = Channel(
            channel_id="chan_test_01",
            niche_id=niche.niche_id,
            browser_profile_id="prof_01",
            lifecycle_status="ready_to_post",
        )
        product = Product(
            product_id=sample_fashion_product["product_id"],
            niche_id=niche.niche_id,
            title=sample_fashion_product["title"],
            price=sample_fashion_product["price"],
            commission_rate=sample_fashion_product["commission_rate"],
            product_url=sample_fashion_product["product_url"],
        )
        job = VideoJob(
            job_id="job_live_01",
            channel_id=channel.channel_id,
            product_id=product.product_id,
            niche_id=niche.niche_id,
            status="published",
        )
        db_session.add_all([niche, channel, product, job])
        await db_session.commit()

        # 2. Simulate incoming comment
        raw_comment = {
            "comment_id": "comm_rec_101",
            "channel_id": channel.channel_id,
            "video_id": "tt_pub_live_01",
            "author_id": "user_buyer_99",
            "author_name": "Ngọc Trinh",
            "comment_text": "Váy này giá bao nhiêu và có freeship không shop?",
        }

        # 3. Process via CommentAgent
        agent = CommentAgent()
        intent = agent.classify_intent(raw_comment["comment_text"])
        reply = agent.generate_reply(
            raw_comment["comment_text"],
            sample_fashion_product,
            persona={"niche_id": "thoi_trang_nu"},
        )

        comment_record = VideoComment(
            comment_id=raw_comment["comment_id"],
            channel_id=raw_comment["channel_id"],
            video_id=raw_comment["video_id"],
            author_id=raw_comment["author_id"],
            author_name=raw_comment["author_name"],
            comment_text=raw_comment["comment_text"],
            intent=intent.value,
            reply_text=reply,
            reply_status="replied",
            replied_at=datetime.now(timezone.utc),
        )
        db_session.add(comment_record)
        await db_session.commit()

        # 4. Verify persistence
        stmt = select(VideoComment).where(VideoComment.comment_id == "comm_rec_101")
        result = await db_session.execute(stmt)
        persisted = result.scalar_one_or_none()

        assert persisted is not None
        assert persisted.intent == "ask_price"
        assert persisted.reply_status == "replied"
        assert "189,000" in persisted.reply_text or "189" in persisted.reply_text
        assert persisted.replied_at is not None
        assert ToneValidator.validate(persisted.reply_text) is True


# ==============================================================================
# 7. LLM Integration and Fallback Resilience
# ==============================================================================

class TestLLMIntegrationAndFallback:
    """Verifies behavior when LLM is available or produces invalid tone."""

    def test_generate_reply_with_mock_llm_success(self, sample_fashion_product):
        mock_llm = MagicMock()
        mock_llm.generate.return_value = (
            "Chị em ơi, em váy này đang sale hời ở giỏ hàng vàng góc trái nè, bấm nhận mã freeship nha!"
        )
        agent = CommentAgent(llm_client=mock_llm)
        reply = agent.generate_reply("Bao tiền thế?", sample_fashion_product, {})

        assert "freeship" in reply.lower()
        assert ToneValidator.validate(reply) is True
        mock_llm.generate.assert_called_once()

    def test_generate_reply_llm_robotic_fallback_to_template(self, sample_fashion_product):
        mock_llm = MagicMock()
        # Mock LLM generates banned robotic cliche
        mock_llm.generate.return_value = (
            "Kính chào quý khách, sản phẩm này rất tốt và tiện ích, sự lựa chọn hoàn hảo của bạn."
        )
        agent = CommentAgent(llm_client=mock_llm)
        reply = agent.generate_reply("Váy này giá bao nhiêu?", sample_fashion_product, {})

        # Should detect robotic cliche, reject it, and fall back to clean template
        assert "kính chào quý khách" not in reply.lower()
        assert "sự lựa chọn hoàn hảo" not in reply.lower()
        assert "189,000" in reply or "189" in reply
        assert ToneValidator.validate(reply) is True
