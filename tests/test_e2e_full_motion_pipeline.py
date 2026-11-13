"""End-to-End (E2E) Integration Tests for AMAS Full Motion Control Pipeline (Phase 4 / AMAS-11).

Executes the complete lifecycle:
1. Ingest competitor video -> Deconstruct 4 segments (Hook 3s, Problem, Demo, CTA) via SceneAnalyzerService.
2. Render 4 clips via MotionControlEngine (Replicate API simulation) + dub Vietnamese KOC audio.
3. Apply HybridSwapPipeline (<= 1.000đ/video) for face swap substitution & anti-AI detection evasion.
4. Manage & rotate proxy via ProxyManagerService.
5. Publish to multi-channel (Facebook Reels / TikTok) via FacebookPublisher with first-comment affiliate placement.
6. Verify audit logging and lifecycle transitions in database.
"""

from pathlib import Path
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.database.models import (
    Base,
    Channel,
    MotionAsset,
    Niche,
    Product,
    Proxy,
    PublishLog,
    VideoJob,
)
from src.services.facebook_publisher import FacebookPublisher
from src.services.hybrid_swap_pipeline import HybridSwapPipeline
from src.services.motion_control_engine import MotionControlEngine
from src.services.proxy_manager import ProxyManagerService
from src.services.scene_analyzer import SceneAnalyzerService


@pytest.fixture
async def e2e_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as session:
        # Prepopulate foundation domain entities
        niche = Niche(niche_id="niche_e2e", name="Fashion KOC", description="Women's Apparel")
        channel = Channel(
            channel_id="chan_e2e_01",
            niche_id="niche_e2e",
            browser_profile_id="prof_e2e_01",
            platform="facebook",
            account_type="fanpage",
            lifecycle_status="ready_to_post",
            platform_metadata={
                "page_id": "fb_page_99",
                "affiliate_link_placement": "first_comment",
            },
        )
        product = Product(
            product_id="prod_e2e_01",
            niche_id="niche_e2e",
            title="Đầm dạ hội đuôi cá tôn dáng",
            price=350000.0,
            product_url="https://shopee.vn/dam-da-hoi",
        )
        proxy1 = Proxy(
            proxy_id="px_e2e_01",
            proxy_url="http://103.142.12.8:8080",
            protocol="http",
            status="alive",
            assigned_count=1,
        )
        proxy2 = Proxy(
            proxy_id="px_e2e_02",
            proxy_url="http://103.142.12.50:8080",
            protocol="http",
            status="alive",
            assigned_count=0,
        )
        session.add_all([niche, channel, product, proxy1, proxy2])
        await session.commit()
        yield session

    await engine.dispose()


class TestE2EFullMotionPipeline:
    """Verifies end-to-end integration across all pipeline components."""

    @pytest.mark.asyncio
    async def test_complete_e2e_workflow(self, e2e_session, tmp_path):
        # -------------------------------------------------------------
        # STEP 1: Deconstruct competitor video into 4 functional segments
        # -------------------------------------------------------------
        scene_analyzer = SceneAnalyzerService(output_dir=tmp_path / "scenes", mock_mode=True)
        competitor_url = "https://www.tiktok.com/@competitor/video/73912345678"

        scene_result = await scene_analyzer.analyze_and_segment(
            video_url_or_path=competitor_url,
            save_to_db=True,
            session=e2e_session,
            cut_clips=True,
            asset_id="asset_e2e_001",
        )

        assert scene_result.asset_id == "asset_e2e_001"
        assert len(scene_result.segments) == 4
        assert [s.name for s in scene_result.segments] == ["hook", "problem", "demo", "cta"]
        assert scene_result.segments[0].duration == 3.0

        # Verify MotionAsset saved to DB
        saved_asset = await e2e_session.get(MotionAsset, "asset_e2e_001")
        assert saved_asset is not None
        assert "segments" in saved_asset.motion_features

        # -------------------------------------------------------------
        # STEP 2: Motion Control generation (Replicate API simulation)
        # -------------------------------------------------------------
        char_img = tmp_path / "hoaimy_face.png"
        char_img.write_bytes(b"HOAIMY_FACE_DATA")

        job_id = "job_e2e_kling_01"
        job = VideoJob(
            job_id=job_id,
            product_id="prod_e2e_01",
            niche_id="niche_e2e",
            channel_id="chan_e2e_01",
            status="created",
        )
        e2e_session.add(job)
        await e2e_session.flush()

        motion_engine = MotionControlEngine(storage_dir=tmp_path / "motion", mock_mode=True)
        job_result = await motion_engine.process_job(
            job_id=job_id,
            character_image_path=str(char_img),
            script="Chào mọi người, mẫu đầm này che bụng cực đỉnh nha!",
            segments_data=[s.to_dict() for s in scene_result.segments],
            session=e2e_session,
        )

        assert job_result["status"] == "rendered"
        assert job_result["motion_mode"] == "kling_motion"
        assert Path(job_result["output_video_path"]).exists()

        # -------------------------------------------------------------
        # STEP 3: Hybrid Swap (<= 1.000đ/video) substitution & Anti-AI evasion
        # -------------------------------------------------------------
        hybrid_pipeline = HybridSwapPipeline(output_dir=tmp_path / "hybrid", mock_mode=True)
        assert hybrid_pipeline.estimate_cost_vnd(30.0) <= 1000

        hybrid_job_id = "job_e2e_hybrid_01"
        hybrid_job = VideoJob(
            job_id=hybrid_job_id,
            product_id="prod_e2e_01",
            niche_id="niche_e2e",
            channel_id="chan_e2e_01",
            status="created",
        )
        e2e_session.add(hybrid_job)
        await e2e_session.flush()

        hybrid_result = await hybrid_pipeline.process_hybrid_job(
            job_id=hybrid_job_id,
            source_video_path=job_result["output_video_path"],
            face_image_path=str(char_img),
            session=e2e_session,
        )

        assert hybrid_result["status"] == "rendered"
        assert hybrid_result["motion_mode"] == "hybrid_swap"
        assert hybrid_result["estimated_cost_vnd"] <= 1000
        assert Path(hybrid_result["output_video_path"]).exists()

        # -------------------------------------------------------------
        # STEP 4: Proxy Health Check and Channel Proxy Rotation
        # -------------------------------------------------------------
        proxy_manager = ProxyManagerService(mock_mode=True)
        rotated_proxy = await proxy_manager.rotate_proxy_for_channel(e2e_session, "chan_e2e_01")
        assert rotated_proxy is not None
        assert rotated_proxy.proxy_id == "px_e2e_02"

        # -------------------------------------------------------------
        # STEP 5: Facebook Reels Publishing with First-Comment Link
        # -------------------------------------------------------------
        publisher = FacebookPublisher(mock_mode=True)
        pub_result = await publisher.publish_reel(
            session=e2e_session,
            channel_id="chan_e2e_01",
            job_id=job_id,
            caption="Chiếc đầm hack dáng đi tiệc siêu sang #affiliate #thoitrang",
            affiliate_url="https://shopee.vn/aff/dam-da-hoi",
        )

        assert pub_result.success is True
        assert pub_result.post_id is not None
        assert pub_result.comment_status == "posted"

        # Channel moved to cooldown
        channel = await e2e_session.get(Channel, "chan_e2e_01")
        assert channel.lifecycle_status == "cooldown"

        # -------------------------------------------------------------
        # STEP 6: Verify Audit Trail in PublishLog
        # -------------------------------------------------------------
        stmt_log = select(PublishLog).where(PublishLog.job_id == job_id)
        res_log = await e2e_session.execute(stmt_log)
        publish_log = res_log.scalars().first()

        assert publish_log is not None
        assert publish_log.status == "published"
        assert publish_log.channel_id == "chan_e2e_01"
        assert publish_log.platform == "facebook"
        assert publish_log.published_video_id == pub_result.post_id
