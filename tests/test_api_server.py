"""Unit & integration tests for FastAPI Server (Phase 2.3 / AMAS-7)."""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.api.deps import get_db
from src.api.main import app
from src.database.models import (
    Base,
    Channel,
    Competitor,
    CompetitorVideo,
    Niche,
    Product,
    Proxy,
    VideoComment,
    VideoJob,
)


@pytest.fixture
async def test_db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as session:
        # Prepopulate test entities
        niche = Niche(niche_id="niche_api", name="Tech", description="Gadgets")
        channel = Channel(
            channel_id="chan_api_01",
            niche_id="niche_api",
            browser_profile_id="prof_api_01",
            platform="facebook",
            lifecycle_status="ready_to_post",
            platform_metadata={"affiliate_link_placement": "first_comment"},
        )
        product = Product(
            product_id="prod_api_01",
            niche_id="niche_api",
            title="Bàn phím cơ không dây",
            price=890000.0,
            product_url="https://shopee.vn/p/kb01",
        )
        job = VideoJob(
            job_id="job_api_01",
            product_id="prod_api_01",
            niche_id="niche_api",
            channel_id="chan_api_01",
            status="rendered",
            output_video_path="/tmp/test_rendered.mp4",
        )
        proxy = Proxy(
            proxy_id="px_api_01",
            proxy_url="http://127.0.0.1:8080",
            protocol="http",
            status="alive",
            assigned_count=0,
        )
        comment = VideoComment(
            comment_id="cmt_api_01",
            channel_id="chan_api_01",
            video_id="vid_01",
            author_id="user_123",
            comment_text="Cho xin giá với shop ơi?",
            intent="ask_price",
        )
        competitor = Competitor(
            competitor_id="comp_01",
            niche_id="niche_api",
            username="tech_reviewer",
            profile_url="https://tiktok.com/@tech_reviewer",
        )
        comp_video = CompetitorVideo(
            video_id="cv_api_01",
            competitor_id="comp_01",
            video_url="https://tiktok.com/@tech_reviewer/video/123",
            caption="Bàn phím xịn giá rẻ",
            views_count=50000,
            likes_count=4200,
        )
        session.add_all([niche, channel, product, job, proxy, comment, competitor, comp_video])
        await session.commit()
        yield session

    await engine.dispose()


@pytest.fixture
async def client(test_db_session):
    async def override_get_db():
        yield test_db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


class TestAPIServer:
    """Verifies all REST API routes and SSE endpoints."""

    @pytest.mark.asyncio
    async def test_health_check(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    @pytest.mark.asyncio
    async def test_studio_preprocess(self, client):
        resp = await client.post(
            "/api/studio/preprocess",
            json={"video_url_or_path": "https://tiktok.com/@test/video/123", "cut_clips": False},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "segments" in data
        assert len(data["segments"]) == 4

    @pytest.mark.asyncio
    async def test_studio_motion_assets(self, client):
        resp = await client.get("/api/studio/motion-assets")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    @pytest.mark.asyncio
    async def test_studio_generate(self, client, tmp_path):
        dummy_img = tmp_path / "model.png"
        dummy_img.write_bytes(b"MODEL_IMG")

        resp = await client.post(
            "/api/studio/generate",
            json={
                "product_id": "prod_api_01",
                "niche_id": "niche_api",
                "channel_id": "chan_api_01",
                "character_image_url": str(dummy_img),
                "script": "Áo cực đẹp bấm giỏ hàng ngay!",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "rendered"
        assert "output_video_path" in data

    @pytest.mark.asyncio
    async def test_studio_sse_stream(self, client):
        resp = await client.get("/api/studio/jobs/job_api_01/stream")
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]
        body = resp.text
        assert "data:" in body
        assert "completed" in body

    @pytest.mark.asyncio
    async def test_channels_endpoints(self, client):
        # List channels
        list_res = await client.get("/api/channels/")
        assert list_res.status_code == 200
        assert len(list_res.json()) >= 1

        # Warmup
        warmup_res = await client.post(
            "/api/channels/chan_api_01/warmup",
            json={"duration_minutes": 2},
        )
        assert warmup_res.status_code == 200
        assert "new_lifecycle_status" in warmup_res.json()

        # Unlock
        unlock_res = await client.post("/api/channels/chan_api_01/unlock")
        assert unlock_res.status_code == 200
        assert unlock_res.json()["lifecycle_status"] == "ready_to_post"

        # Publish
        pub_res = await client.post(
            "/api/channels/chan_api_01/publish",
            json={"job_id": "job_api_01", "caption": "Bàn phím siêu hot!", "affiliate_url": "https://shopee.vn/aff/kb"},
        )
        assert pub_res.status_code == 200
        assert pub_res.json()["success"] is True

    @pytest.mark.asyncio
    async def test_proxies_endpoints(self, client):
        # List
        res = await client.get("/api/proxies/")
        assert res.status_code == 200
        assert len(res.json()) >= 1

        # Check proxy
        check_res = await client.post("/api/proxies/px_api_01/check")
        assert check_res.status_code == 200
        assert check_res.json()["status"] == "alive"

        # Rotate proxy
        rotate_res = await client.post("/api/proxies/rotate/chan_api_01")
        assert rotate_res.status_code == 200
        assert rotate_res.json()["assigned_proxy_id"] == "px_api_01"

    @pytest.mark.asyncio
    async def test_history_endpoints(self, client):
        # Publishes
        pub_res = await client.get("/api/history/publishes")
        assert pub_res.status_code == 200

        # Comments
        cmt_res = await client.get("/api/history/comments")
        assert cmt_res.status_code == 200
        assert len(cmt_res.json()) >= 1

        # Reply
        reply_res = await client.post(
            "/api/history/comments/cmt_api_01/reply",
            json={"reply_text": "Dạ em gửi link giỏ hàng góc trái video bạn nhé!"},
        )
        assert reply_res.status_code == 200
        assert reply_res.json()["reply_status"] == "replied"

        # Competitor videos
        comp_res = await client.get("/api/history/competitor-videos")
        assert comp_res.status_code == 200
        assert len(comp_res.json()) >= 1
