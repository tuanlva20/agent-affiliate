"""Unit tests for SmartPublisher Agent (Milestone 6, Task 6, Feature F25)."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from pathlib import Path
from typing import AsyncGenerator
import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.agents.smart_publisher import PublishResult, SmartPublisher
from src.database.models import Base, Channel, Niche, Product, VideoJob


@pytest.fixture(autouse=True)
def ensure_temp_video_files():
    """Ensures standard temporary video paths exist on disk so os.path.exists succeeds genuinely."""
    paths = [Path("/tmp/vid.mp4"), Path("/tmp/video.mp4"), Path("/tmp/mock.mp4")]
    created = []
    for p in paths:
        if not p.exists():
            try:
                p.touch()
                created.append(p)
            except OSError:
                pass
    yield
    for p in created:
        try:
            p.unlink(missing_ok=True)
        except OSError:
            pass


@pytest_asyncio.fixture
async def async_db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


# ---------------------------------------------------------------------------
# 1. PublishResult Dataclass Tests
# ---------------------------------------------------------------------------

def test_publish_result_defaults():
    res = PublishResult(success=True, video_id="tt_pub_101", channel_status="cooldown")
    assert res.success is True
    assert res.video_id == "tt_pub_101"
    assert res.channel_status == "cooldown"
    assert res.published_url == "https://www.tiktok.com/@channel/video/tt_pub_101"
    assert res.error is None
    assert isinstance(res.metadata, dict)


def test_publish_result_failure_repr():
    res = PublishResult(
        success=False,
        channel_status="warming",
        error="Cannot publish: channel is in warming stage (nuôi nick); affiliate posting not permitted.",
    )
    assert res.success is False
    assert res.video_id is None
    assert res.published_url is None
    assert res.channel_status == "warming"
    assert "warming stage" in res.error


# ---------------------------------------------------------------------------
# 2. Lifecycle Guard Tests (Dict Representation)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_lifecycle_guard_warming_dict():
    mock_browser = MagicMock()
    mock_browser.start_browser = AsyncMock()
    publisher = SmartPublisher(browser_adapter=mock_browser, human_behavior=MagicMock())

    channel = {"channel_id": "c1", "lifecycle_status": "warming"}
    res = await publisher.publish_video("job_1", channel, "/tmp/vid.mp4", "Caption", {})

    assert res.success is False
    assert res.channel_status == "warming"
    assert "warming stage" in res.error
    # Must NOT start browser
    mock_browser.start_browser.assert_not_called()


@pytest.mark.asyncio
async def test_lifecycle_guard_captcha_blocked_dict():
    mock_browser = MagicMock()
    mock_browser.start_browser = AsyncMock()
    publisher = SmartPublisher(browser_adapter=mock_browser, human_behavior=MagicMock())

    channel = {"channel_id": "c2", "lifecycle_status": "captcha_blocked"}
    res = await publisher.publish_video("job_2", channel, "/tmp/vid.mp4", "Caption", {})

    assert res.success is False
    assert res.channel_status == "captcha_blocked"
    assert "blocked by Captcha" in res.error
    assert "captcha blocked" in res.error.lower()
    mock_browser.start_browser.assert_not_called()


@pytest.mark.asyncio
async def test_lifecycle_guard_cooldown_dict():
    mock_browser = MagicMock()
    mock_browser.start_browser = AsyncMock()
    publisher = SmartPublisher(browser_adapter=mock_browser, human_behavior=MagicMock())

    channel = {"channel_id": "c3", "lifecycle_status": "cooldown"}
    res = await publisher.publish_video("job_3", channel, "/tmp/vid.mp4", "Caption", {})

    assert res.success is False
    assert res.channel_status == "cooldown"
    assert "cooldown stage" in res.error
    mock_browser.start_browser.assert_not_called()


# ---------------------------------------------------------------------------
# 3. Lifecycle Guard Tests (ORM Model Channel)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_lifecycle_guard_warming_orm():
    publisher = SmartPublisher(MagicMock(), MagicMock())
    orm_channel = Channel(
        channel_id="c_orm_1",
        niche_id="thoi_trang_nu",
        browser_profile_id="prof_orm_1",
        lifecycle_status="warming",
    )
    res = await publisher.publish_video("job_orm", orm_channel, "/tmp/vid.mp4", "Caption", {})
    assert res.success is False
    assert res.channel_status == "warming"
    assert "warming stage" in res.error


@pytest.mark.asyncio
async def test_lifecycle_guard_captcha_blocked_orm():
    publisher = SmartPublisher(MagicMock(), MagicMock())
    orm_channel = Channel(
        channel_id="c_orm_2",
        niche_id="thoi_trang_nu",
        browser_profile_id="prof_orm_2",
        lifecycle_status="captcha_blocked",
    )
    res = await publisher.publish_video("job_orm_2", orm_channel, "/tmp/vid.mp4", "Caption", {})
    assert res.success is False
    assert res.channel_status == "captcha_blocked"
    assert "blocked by Captcha" in res.error


# ---------------------------------------------------------------------------
# 4. Error Handling Tests (Missing File & Browser Failure)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_error_missing_video_path():
    publisher = SmartPublisher(MagicMock(), MagicMock())
    ready_channel = {"channel_id": "c_ready", "lifecycle_status": "ready_to_post"}

    # Case 1: Empty path
    res1 = await publisher.publish_video("job_fail_1", ready_channel, "", "Caption", {})
    assert res1.success is False
    assert "missing video file path" in res1.error

    # Case 2: Non-existent file on disk (and not /tmp/vid.mp4)
    res2 = await publisher.publish_video(
        "job_fail_2", ready_channel, "/nonexistent/invalid_file.mp4", "Caption", {}
    )
    assert res2.success is False
    assert "video file not found" in res2.error


@pytest.mark.asyncio
async def test_error_browser_start_failure():
    mock_browser = MagicMock()
    mock_browser.start_browser = AsyncMock(side_effect=RuntimeError("CDP connection refused on port 50325"))
    publisher = SmartPublisher(mock_browser, MagicMock())

    ready_channel = {"channel_id": "c_ready", "lifecycle_status": "ready_to_post"}
    res = await publisher.publish_video("job_err_browser", ready_channel, "/tmp/vid.mp4", "Caption", {})

    assert res.success is False
    assert res.channel_status == "ready_to_post"  # Status remains ready_to_post
    assert "Browser start failure" in res.error


# ---------------------------------------------------------------------------
# 5. Captcha Mid-Flight Interception
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_mid_flight_captcha_detection():
    mock_browser = MagicMock()
    mock_browser.start_browser = AsyncMock(return_value="ws://127.0.0.1:50325/devtools/browser/p1")
    mock_page = MagicMock()
    mock_browser.connect_over_cdp = AsyncMock(return_value=(MagicMock(), MagicMock(), mock_page))
    mock_browser.stop_browser = AsyncMock(return_value=True)

    mock_human = MagicMock()
    mock_human.warmup_feed_session = AsyncMock()
    # Captcha detected!
    mock_human.detect_and_handle_captcha = AsyncMock(return_value=True)

    publisher = SmartPublisher(mock_browser, mock_human)
    channel = {"channel_id": "c_mid", "lifecycle_status": "ready_to_post"}

    res = await publisher.publish_video("job_captcha", channel, "/tmp/vid.mp4", "Caption", {})

    assert res.success is False
    assert res.channel_status == "captcha_blocked"
    assert channel["lifecycle_status"] == "captcha_blocked"
    assert "Captcha" in res.error
    mock_browser.connect_over_cdp.assert_awaited_once_with("ws://127.0.0.1:50325/devtools/browser/p1")


# ---------------------------------------------------------------------------
# 6. Successful Publishing & Product Anchor Attachment
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_successful_publish_with_anchor():
    mock_browser = MagicMock()
    mock_browser.start_browser = AsyncMock(return_value="ws://127.0.0.1:50325/devtools/browser/prof_123")

    mock_human = MagicMock()
    mock_human.warmup_feed_session = AsyncMock(return_value=True)
    mock_human.detect_and_handle_captcha = AsyncMock(return_value=False)
    mock_human.human_type = AsyncMock()

    mock_page = MagicMock()
    mock_page.goto = AsyncMock()
    mock_page.click = AsyncMock()
    mock_page.set_input_files = AsyncMock()

    publisher = SmartPublisher(mock_browser, mock_human)
    channel = {"channel_id": "c_success", "lifecycle_status": "ready_to_post"}
    anchor = {"product_id": "prod_dress_999", "title": "Đầm hoa Vintage"}

    res = await publisher.publish_video(
        job_id="job_999",
        channel=channel,
        video_path="/tmp/vid.mp4",
        caption="Váy xinh mặc đi tiệc cực tôn dáng #fashion",
        product_anchor=anchor,
        page=mock_page,
    )

    assert res.success is True
    assert res.video_id == "tt_pub_job_999"
    assert res.channel_status == "cooldown"
    assert channel["lifecycle_status"] == "cooldown"
    assert channel["last_posted_at"] is not None
    assert res.metadata["has_product_anchor"] is True
    assert res.metadata["anchor"]["product_id"] == "prod_dress_999"

    # Verify human_type was called for caption and anchor search
    assert mock_human.human_type.call_count >= 2


# ---------------------------------------------------------------------------
# 7. Database Integration Test with AsyncSession
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_publish_video_with_database_session(async_db_session):
    # Setup test DB records
    niche = Niche(niche_id="thoi_trang_nu_pub", name="Thời trang nữ Pub")
    async_db_session.add(niche)

    channel = Channel(
        channel_id="ch_db_pub_1",
        niche_id="thoi_trang_nu_pub",
        browser_profile_id="prof_db_pub_1",
        lifecycle_status="ready_to_post",
    )
    async_db_session.add(channel)

    prod = Product(
        product_id="prod_db_pub_1",
        niche_id="thoi_trang_nu_pub",
        title="Váy maxi đi biển",
        price=250000.0,
        commission_rate=0.15,
        rating=4.9,
        product_url="https://tiktok.com/@shop/product/prod_db_pub_1",
    )
    async_db_session.add(prod)

    job = VideoJob(
        job_id="job_db_pub_1",
        product_id="prod_db_pub_1",
        niche_id="thoi_trang_nu_pub",
        channel_id="ch_db_pub_1",
        status="rendered",
    )
    async_db_session.add(job)
    await async_db_session.commit()

    mock_browser = MagicMock()
    mock_browser.start_browser = AsyncMock(return_value="ws://127.0.0.1:50325/devtools/browser/prof_db_pub_1")
    mock_page = MagicMock()
    mock_page.goto = AsyncMock()
    mock_page.click = AsyncMock()
    mock_page.set_input_files = AsyncMock()
    mock_browser.connect_over_cdp = AsyncMock(return_value=(MagicMock(), MagicMock(), mock_page))
    mock_browser.stop_browser = AsyncMock(return_value=True)

    mock_human = MagicMock()
    mock_human.warmup_feed_session = AsyncMock(return_value=True)
    mock_human.detect_and_handle_captcha = AsyncMock(return_value=False)
    mock_human.human_type = AsyncMock()

    publisher = SmartPublisher(mock_browser, mock_human)

    res = await publisher.publish_video(
        job_id="job_db_pub_1",
        channel=channel,
        video_path="/tmp/vid.mp4",
        caption="Review váy hoa nhí",
        product_anchor={"product_id": "p123"},
        db_session=async_db_session,
    )

    assert res.success is True
    assert res.channel_status == "cooldown"
    assert channel.lifecycle_status == "cooldown"
    assert channel.last_posted_at is not None

    mock_browser.connect_over_cdp.assert_awaited_once_with("ws://127.0.0.1:50325/devtools/browser/prof_db_pub_1")
    mock_human.warmup_feed_session.assert_awaited_once_with(mock_page, duration_seconds=180, time_scale=1.0, fast_mode=False)
    mock_browser.stop_browser.assert_awaited_once_with("prof_db_pub_1")

    # Check updated VideoJob status in database
    stmt = select(VideoJob).where(VideoJob.job_id == "job_db_pub_1")
    exec_res = await async_db_session.execute(stmt)
    updated_job = exec_res.scalar_one()
    assert updated_job.status == "published"


def test_no_mock_imports_in_smart_publisher_source():
    import src.agents.smart_publisher as sp

    with open(sp.__file__, "r", encoding="utf-8") as f:
        content = f.read()

    assert "unittest.mock" not in content, "Found forbidden unittest.mock in smart_publisher.py"
    assert "MagicMock" not in content, "Found forbidden MagicMock in smart_publisher.py"
    assert "is_mock_path" not in content, "Found forbidden is_mock_path in smart_publisher.py"

