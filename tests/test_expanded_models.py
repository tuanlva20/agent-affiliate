"""Unit tests for newly expanded database models (AMAS-2)."""

import pytest
import pytest_asyncio
from datetime import datetime, timezone
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.models import (
    Base,
    Channel,
    VideoJob,
    Proxy,
    MotionAsset,
    PublishLog,
    CompetitorScrapeLog,
    CompetitorVideo,
    Niche,
    Product,
    Competitor,
)
from src.database.session import get_async_engine, get_session_factory

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
async def test_expanded_models_crud(db_session: AsyncSession):
    # 1. Niche & Channel with new platform fields
    niche = Niche(niche_id="test_niche", name="Test Niche")
    db_session.add(niche)
    await db_session.flush()

    channel = Channel(
        channel_id="chan_fb_01",
        niche_id="test_niche",
        browser_profile_id="prof_01",
        platform="facebook",
        account_type="fanpage",
        platform_metadata={"page_id": "123456", "affiliate_link_placement": "first_comment"},
        lifecycle_status="ready_to_post",
    )
    db_session.add(channel)
    await db_session.flush()

    # 2. Proxy model
    proxy = Proxy(
        proxy_id="proxy_01",
        proxy_url="http://user:pass@1.2.3.4:8080",
        protocol="http",
        status="live",
        assigned_count=1,
    )
    db_session.add(proxy)

    # 3. Product & VideoJob with segments_data
    product = Product(
        product_id="prod_01",
        niche_id="test_niche",
        title="Sản phẩm thử nghiệm",
        price=199000.0,
        product_url="https://shop.tiktok.com/prod_01",
    )
    db_session.add(product)
    await db_session.flush()

    video_job = VideoJob(
        job_id="job_01",
        product_id="prod_01",
        niche_id="test_niche",
        channel_id="chan_fb_01",
        motion_mode="replicate_motion_control",
        character_image_url="https://example.com/character.png",
        product_image_url="https://example.com/product.png",
        segments_data={"hook": "test hook", "cta": "test cta"},
    )
    db_session.add(video_job)
    await db_session.flush()

    # 4. MotionAsset
    motion = MotionAsset(
        asset_id="motion_01",
        source_type="competitor_video",
        source_url="https://tiktok.com/@comp/video/1",
        duration=15.5,
        is_official=True,
    )
    db_session.add(motion)

    # 5. PublishLog
    pub_log = PublishLog(
        log_id="pub_01",
        job_id="job_01",
        channel_id="chan_fb_01",
        platform="facebook",
        published_video_id="fb_vid_123",
        published_url="https://facebook.com/reel/123",
        status="published",
        published_at=datetime.now(timezone.utc),
    )
    db_session.add(pub_log)

    # 6. Competitor & Scrape Logs
    comp = Competitor(
        competitor_id="comp_01",
        niche_id="test_niche",
        username="rival_shop",
        profile_url="https://tiktok.com/@rival_shop",
    )
    db_session.add(comp)
    await db_session.flush()

    scrape_log = CompetitorScrapeLog(
        log_id="scrape_01",
        competitor_id="comp_01",
        videos_found=5,
        status="success",
    )
    comp_video = CompetitorVideo(
        video_id="vid_comp_01",
        competitor_id="comp_01",
        video_url="https://tiktok.com/@rival_shop/video/100",
        views_count=15000,
        likes_count=1200,
    )
    db_session.add_all([scrape_log, comp_video])
    await db_session.commit()

    # Query back & verify persistence
    ch = await db_session.get(Channel, "chan_fb_01")
    assert ch.platform == "facebook"
    assert ch.account_type == "fanpage"
    assert ch.platform_metadata["page_id"] == "123456"

    p = await db_session.get(Proxy, "proxy_01")
    assert p.status == "live"
    assert p.assigned_count == 1

    vj = await db_session.get(VideoJob, "job_01")
    assert vj.motion_mode == "replicate_motion_control"
    assert vj.segments_data["hook"] == "test hook"

    pl = await db_session.get(PublishLog, "pub_01")
    assert pl.status == "published"
    assert pl.published_video_id == "fb_vid_123"

    cv = await db_session.get(CompetitorVideo, "vid_comp_01")
    assert cv.views_count == 15000
