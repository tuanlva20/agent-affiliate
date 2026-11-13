"""Unit tests for ProxyManagerService and FacebookPublisher (Phase 2.2 / AMAS-6)."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.database.models import Base, Channel, Niche, Product, Proxy, PublishLog, VideoJob
from src.services.facebook_publisher import (
    ChannelBlockedError,
    FacebookPublisher,
    FacebookPublisherError,
)
from src.services.proxy_manager import ProxyManagerError, ProxyManagerService


@pytest.fixture
async def async_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session_factory = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session_factory() as session:
        niche = Niche(niche_id="niche_fb", name="Fashion", description="Fashion")
        channel = Channel(
            channel_id="chan_fb_01",
            niche_id="niche_fb",
            browser_profile_id="prof_01",
            platform="facebook",
            account_type="fanpage",
            platform_metadata={"page_id": "123", "affiliate_link_placement": "first_comment"},
            lifecycle_status="ready_to_post",
        )
        product = Product(
            product_id="prod_fb_01",
            niche_id="niche_fb",
            title="Đầm dạ hội sang trọng",
            price=399000.0,
            product_url="https://shopee.vn/p/01",
        )
        job = VideoJob(
            job_id="job_fb_01",
            product_id="prod_fb_01",
            niche_id="niche_fb",
            channel_id="chan_fb_01",
            output_video_path="/tmp/rendered_fb_video.mp4",
            status="rendered",
        )
        session.add_all([niche, channel, product, job])
        await session.flush()
        yield session

    await engine.dispose()


class TestProxyManagerService:
    """Verifies proxy health check, assignment, and rotation."""

    @pytest.mark.asyncio
    async def test_proxy_health_and_update(self, async_session):
        service = ProxyManagerService(mock_mode=True)

        proxy_live = Proxy(
            proxy_id="px_live",
            proxy_url="http://user:pass@1.2.3.4:8080",
            protocol="http",
            status="unchecked",
        )
        proxy_dead = Proxy(
            proxy_id="px_dead",
            proxy_url="http://user:pass@5.6.7.8:9999",
            protocol="http",
            status="unchecked",
        )
        async_session.add_all([proxy_live, proxy_dead])
        await async_session.flush()

        # Update live proxy
        updated_live = await service.update_proxy_status(async_session, "px_live")
        assert updated_live.status == "alive"
        assert updated_live.last_checked_at is not None

        # Update dead proxy
        updated_dead = await service.update_proxy_status(async_session, "px_dead")
        assert updated_dead.status == "dead"

    @pytest.mark.asyncio
    async def test_proxy_assignment_and_rotation(self, async_session):
        service = ProxyManagerService(mock_mode=True)

        p1 = Proxy(proxy_id="p1", proxy_url="http://10.0.0.1:8080", protocol="http", status="alive", assigned_count=5)
        p2 = Proxy(proxy_id="p2", proxy_url="http://10.0.0.2:8080", protocol="http", status="alive", assigned_count=1)
        async_session.add_all([p1, p2])
        await async_session.flush()

        # Assign p1
        await service.assign_proxy_to_channel(async_session, "chan_fb_01", "p1")
        current_p = await service.get_channel_proxy(async_session, "chan_fb_01")
        assert current_p is not None
        assert current_p.proxy_id == "p1"

        # Rotate proxy -> should pick p2 (assigned_count 1 < 6)
        rotated = await service.rotate_proxy_for_channel(async_session, "chan_fb_01")
        assert rotated is not None
        assert rotated.proxy_id == "p2"


class TestFacebookPublisher:
    """Verifies Reels publishing, first-comment attachment, and warmup/captcha controls."""

    @pytest.mark.asyncio
    async def test_publish_reel_success(self, async_session):
        publisher = FacebookPublisher(mock_mode=True)
        res = await publisher.publish_reel(
            session=async_session,
            channel_id="chan_fb_01",
            job_id="job_fb_01",
            caption="Mẫu đầm siêu hack dáng!",
            affiliate_url="https://shopee.vn/aff/dam123",
        )
        assert res.success is True
        assert res.post_id is not None
        assert res.comment_status == "posted"

        channel = await async_session.get(Channel, "chan_fb_01")
        assert channel.lifecycle_status == "cooldown"

    @pytest.mark.asyncio
    async def test_publish_blocked_on_captcha(self, async_session):
        publisher = FacebookPublisher(mock_mode=True)
        channel = await async_session.get(Channel, "chan_fb_01")
        channel.lifecycle_status = "captcha_blocked"
        await async_session.flush()

        with pytest.raises(ChannelBlockedError):
            await publisher.publish_reel(
                session=async_session,
                channel_id="chan_fb_01",
                job_id="job_fb_01",
                caption="Mẫu đầm",
            )

    @pytest.mark.asyncio
    async def test_warmup_and_captcha_unlock(self, async_session):
        publisher = FacebookPublisher(mock_mode=True)
        channel = await async_session.get(Channel, "chan_fb_01")
        channel.lifecycle_status = "warming"
        await async_session.flush()

        # Warmup session
        warmup_res = await publisher.warmup_feed_session(async_session, "chan_fb_01", duration_minutes=3)
        assert warmup_res["new_lifecycle_status"] == "ready_to_post"

        # Captcha unlock
        channel.lifecycle_status = "captcha_blocked"
        await async_session.flush()

        unlocked = await publisher.unlock_captcha(async_session, "chan_fb_01")
        assert unlocked.lifecycle_status == "ready_to_post"
