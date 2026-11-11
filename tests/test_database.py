"""Unit tests for database models, lifecycle state transitions, JSONB serialization, and session management."""

import pytest
import pytest_asyncio
from typing import AsyncGenerator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import (
    Base,
    Niche,
    Channel,
    Competitor,
    Product,
    VideoJob,
    VideoComment,
    Metric,
)
from src.database.session import get_async_engine, get_session_factory, get_db

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def engine():
    return get_async_engine(TEST_DB_URL, force_new=True)


@pytest_asyncio.fixture(scope="function")
async def init_db(engine):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def db_session(init_db, engine) -> AsyncGenerator[AsyncSession, None]:
    factory = get_session_factory(TEST_DB_URL)
    async with factory() as session:
        yield session


@pytest.mark.asyncio
async def test_models_metadata(init_db, engine):
    """Verifies all 7 model tables and critical columns exist in SQLAlchemy metadata."""
    tables = Base.metadata.tables
    assert "niches" in tables
    assert "channels" in tables
    assert "competitors" in tables
    assert "products" in tables
    assert "video_jobs" in tables
    assert "video_comments" in tables
    assert "metrics" in tables

    assert "lifecycle_status" in Channel.__table__.columns
    assert "browser_profile_id" in Channel.__table__.columns
    assert "evaluation_data" in Product.__table__.columns


@pytest.mark.asyncio
async def test_niche_crud(db_session: AsyncSession):
    """Tests CRUD lifecycle on Niche model."""
    niche = Niche(
        niche_id="thoi_trang_nu",
        name="Thời trang nữ",
        description="Ngách thời trang nữ pilot",
    )
    db_session.add(niche)
    await db_session.commit()

    saved = await db_session.get(Niche, "thoi_trang_nu")
    assert saved is not None
    assert saved.name == "Thời trang nữ"

    saved.description = "Cập nhật mô tả ngách"
    await db_session.commit()

    updated = await db_session.get(Niche, "thoi_trang_nu")
    assert updated.description == "Cập nhật mô tả ngách"


@pytest.mark.asyncio
async def test_channel_lifecycle_transitions(db_session: AsyncSession):
    """Tests Channel lifecycle status progression: warming -> ready_to_post -> cooldown -> captcha_blocked."""
    niche = Niche(niche_id="do_gia_dung", name="Đồ gia dụng thông minh")
    db_session.add(niche)
    await db_session.flush()

    channel = Channel(
        channel_id="chan_homelife_01",
        niche_id="do_gia_dung",
        browser_provider="aliasmode",
        browser_profile_id="alias_prof_001",
        lifecycle_status="warming",
        warmup_days_completed=0,
    )
    db_session.add(channel)
    await db_session.commit()

    chan = await db_session.get(Channel, "chan_homelife_01")
    assert chan.lifecycle_status == "warming"

    # Transition 1: Warming to ready_to_post after warm-up
    chan.lifecycle_status = "ready_to_post"
    chan.warmup_days_completed = 4
    await db_session.commit()
    assert (await db_session.get(Channel, "chan_homelife_01")).lifecycle_status == "ready_to_post"

    # Transition 2: ready_to_post to cooldown after publishing video
    chan.lifecycle_status = "cooldown"
    await db_session.commit()
    assert (await db_session.get(Channel, "chan_homelife_01")).lifecycle_status == "cooldown"

    # Transition 3: Captcha detection triggers captcha_blocked
    chan.lifecycle_status = "captcha_blocked"
    await db_session.commit()
    assert (await db_session.get(Channel, "chan_homelife_01")).lifecycle_status == "captcha_blocked"


@pytest.mark.asyncio
async def test_product_json_metadata_serialization(db_session: AsyncSession):
    """Tests JSONB / JSON dual dialect serialization and deserialization on Product."""
    niche = Niche(niche_id="thoi_trang_nu", name="Thời trang nữ")
    db_session.add(niche)
    await db_session.flush()

    raw_eval = {
        "score": 9.2,
        "passed_filter": True,
        "hook_angle": "Hack dáng che eo to",
        "target_audience": "Nữ 22-35 tuổi",
        "pros": ["Form tôn dáng", "Vải co giãn"],
        "cons": ["Ít màu"],
        "viral_factor": "Before/After thấy rõ sự khác biệt",
        "rejection_reason": None,
    }

    product = Product(
        product_id="prod_fashion_101",
        niche_id="thoi_trang_nu",
        title="Chân váy chữ A cạp cao",
        price=189000.0,
        commission_rate=15.0,
        product_url="https://shop.tiktok.com/view/item/101",
        evaluation_data=raw_eval,
        status="pending",
    )
    db_session.add(product)
    await db_session.commit()

    db_session.expire_all()

    fetched = await db_session.get(Product, "prod_fashion_101")
    assert fetched is not None
    assert isinstance(fetched.evaluation_data, dict)
    assert fetched.evaluation_data["score"] == 9.2
    assert fetched.evaluation_data["passed_filter"] is True
    assert fetched.evaluation_data["pros"] == ["Form tôn dáng", "Vải co giãn"]


@pytest.mark.asyncio
async def test_video_job_crud_and_status_flow(db_session: AsyncSession):
    """Tests VideoJob creation, relationships, and status progression."""
    niche = Niche(niche_id="thoi_trang_nu", name="Thời trang nữ")
    channel = Channel(
        channel_id="chan_01",
        niche_id="thoi_trang_nu",
        browser_profile_id="prof_01",
        lifecycle_status="ready_to_post",
    )
    product = Product(
        product_id="prod_01",
        niche_id="thoi_trang_nu",
        title="Đầm maxi đi biển",
        price=220000.0,
        product_url="https://shop.tiktok.com/view/item/01",
    )
    db_session.add_all([niche, channel, product])
    await db_session.flush()

    job = VideoJob(
        job_id="job_001",
        product_id="prod_01",
        niche_id="thoi_trang_nu",
        channel_id="chan_01",
        source_video_url="https://tiktok.com/video/source_01",
        status="created",
    )
    db_session.add(job)
    await db_session.commit()

    j = await db_session.get(VideoJob, "job_001")
    assert j.status == "created"
    assert j.product.title == "Đầm maxi đi biển"
    assert j.channel.channel_id == "chan_01"

    # Status progression to rendered
    j.script = "Chị em chuẩn bị đi biển bơi hết vào đây ngắm em đầm maxi này nha!"
    j.audio_path = "storage/audio/job_001.mp3"
    j.output_video_path = "storage/rendered/job_001.mp4"
    j.status = "rendered"
    await db_session.commit()

    updated_j = await db_session.get(VideoJob, "job_001")
    assert updated_j.status == "rendered"
    assert updated_j.audio_path == "storage/audio/job_001.mp3"


@pytest.mark.asyncio
async def test_competitor_comment_and_metric_models(db_session: AsyncSession):
    """Tests Competitor, VideoComment, and Metric entities and relations."""
    niche = Niche(niche_id="do_gia_dung", name="Đồ gia dụng")
    channel = Channel(
        channel_id="chan_home_02",
        niche_id="do_gia_dung",
        browser_profile_id="prof_home_02",
    )
    competitor = Competitor(
        competitor_id="comp_101",
        niche_id="do_gia_dung",
        username="giadungthongminh_vn",
        profile_url="https://tiktok.com/@giadungthongminh_vn",
        followers_count=54000,
        track_status="active",
    )
    comment = VideoComment(
        comment_id="comm_001",
        channel_id="chan_home_02",
        video_id="vid_999",
        author_id="user_123",
        author_name="Linh Đan",
        comment_text="Cái này sạc bao lâu thì đầy pin vậy shop?",
        intent="ask_material_usage",
        reply_text="Dạ sạc 2 tiếng dùng được 4 ngày nha nàng, bấm góc trái có voucher freeship nha!",
        reply_status="replied",
    )
    metric = Metric(
        metric_id="met_001",
        channel_id="chan_home_02",
        video_id="vid_999",
        views_count=12500,
        likes_count=850,
        comments_count=32,
        shares_count=40,
        orders_count=18,
        estimated_revenue=2700000.0,
    )
    db_session.add_all([niche, channel, competitor, comment, metric])
    await db_session.commit()

    saved_comp = await db_session.get(Competitor, "comp_101")
    assert saved_comp.followers_count == 54000

    saved_comm = await db_session.get(VideoComment, "comm_001")
    assert saved_comm.reply_status == "replied"
    assert saved_comm.intent == "ask_material_usage"

    saved_met = await db_session.get(Metric, "met_001")
    assert saved_met.orders_count == 18
    assert saved_met.estimated_revenue == 2700000.0


@pytest.mark.asyncio
async def test_get_db_context_manager():
    """Tests get_db() context manager transaction handling."""
    async with get_db(TEST_DB_URL) as session:
        result = await session.execute(select(1))
        assert result.scalar() == 1


@pytest.mark.asyncio
async def test_video_job_rendered_video_path_synonym_query(db_session: AsyncSession):
    """Verifies VideoJob.rendered_video_path synonym attribute and ORM query compilation."""
    niche = Niche(niche_id="thoi_trang_nu_synonym", name="Thời trang nữ")
    product = Product(
        product_id="prod_synonym_01",
        niche_id="thoi_trang_nu_synonym",
        title="Váy xếp ly công sở",
        price=210000.0,
        product_url="https://shop.tiktok.com/view/item/synonym_01",
    )
    # 1. Constructor instantiation with rendered_video_path kwarg
    job = VideoJob(
        job_id="job_synonym_001",
        product_id="prod_synonym_01",
        niche_id="thoi_trang_nu_synonym",
        rendered_video_path="storage/rendered/synonym_init.mp4",
        status="created",
    )
    db_session.add_all([niche, product, job])
    await db_session.commit()

    # 2. Verify attribute getter and setter reflection
    assert job.output_video_path == "storage/rendered/synonym_init.mp4"
    assert job.rendered_video_path == "storage/rendered/synonym_init.mp4"

    job.rendered_video_path = "storage/rendered/synonym_updated.mp4"
    await db_session.commit()
    assert job.output_video_path == "storage/rendered/synonym_updated.mp4"

    # 3. Query via select with where clause on synonym (must NOT compile to WHERE false)
    stmt = select(VideoJob).where(
        VideoJob.rendered_video_path == "storage/rendered/synonym_updated.mp4"
    )
    res = await db_session.execute(stmt)
    matched_job = res.scalar_one_or_none()
    assert matched_job is not None
    assert matched_job.job_id == "job_synonym_001"
    assert matched_job.output_video_path == "storage/rendered/synonym_updated.mp4"
