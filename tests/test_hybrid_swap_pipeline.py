"""Unit tests for Hybrid Swap & Anti-AI Detection Pipeline (Phase 2.1d / AMAS-12)."""

import os
from pathlib import Path
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.database.models import Base, Channel, Niche, Product, VideoJob
from src.services.hybrid_swap_pipeline import (
    AntiAIDetectionConfig,
    FaceSwapConfig,
    HybridSwapError,
    HybridSwapPipeline,
)


@pytest.fixture
async def async_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session_factory = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session_factory() as session:
        niche = Niche(niche_id="niche_02", name="Home & Living", description="Home accessories")
        channel = Channel(
            channel_id="chan_02",
            niche_id="niche_02",
            browser_profile_id="prof_02",
            platform="facebook",
            lifecycle_status="ready_to_post",
        )
        product = Product(
            product_id="prod_02",
            niche_id="niche_02",
            title="Kệ đa năng thông minh",
            price=220000.0,
            product_url="https://shop.tiktok.com/p/02",
        )
        session.add_all([niche, channel, product])
        await session.flush()
        yield session

    await engine.dispose()


class TestHybridSwapPipeline:
    """Verifies cost-efficiency, anti-AI evasion, and end-to-end hybrid job execution."""

    def test_cost_estimation_under_1000_vnd(self):
        pipeline = HybridSwapPipeline(mock_mode=True)
        assert pipeline.estimate_cost_vnd(30.0) <= 1000
        assert pipeline.estimate_cost_vnd(60.0) <= 1000
        assert pipeline.estimate_cost_vnd(15.0) <= 1000

    @pytest.mark.asyncio
    async def test_missing_source_video_raises_error(self, tmp_path):
        pipeline = HybridSwapPipeline(output_dir=tmp_path, mock_mode=True)
        with pytest.raises(HybridSwapError):
            await pipeline.swap_face_and_restore(
                source_video_path=str(tmp_path / "non_existent.mp4"),
                face_image_path=str(tmp_path / "face.jpg"),
            )

    @pytest.mark.asyncio
    async def test_face_swap_mock(self, tmp_path):
        pipeline = HybridSwapPipeline(output_dir=tmp_path, mock_mode=True)
        src_video = tmp_path / "competitor.mp4"
        src_video.write_bytes(b"VIDEO_FRAMES")
        face_img = tmp_path / "target_face.png"
        face_img.write_bytes(b"FACE_DATA")

        out_path = await pipeline.swap_face_and_restore(
            str(src_video),
            str(face_img),
            config=FaceSwapConfig(engine="insightface", restoration_model="codeformer"),
        )
        assert os.path.exists(out_path)
        assert Path(out_path).stat().st_size > 0

    @pytest.mark.asyncio
    async def test_anti_ai_evasion_mock(self, tmp_path):
        pipeline = HybridSwapPipeline(output_dir=tmp_path, mock_mode=True)
        in_video = tmp_path / "swapped.mp4"
        in_video.write_bytes(b"SWAPPED_VIDEO")
        voiceover = tmp_path / "tts.mp3"
        voiceover.write_bytes(b"MP3_VOICEOVER")
        out_evasion = tmp_path / "evaded.mp4"

        res_path = await pipeline.apply_anti_ai_evasion(
            str(in_video),
            str(voiceover),
            str(out_evasion),
            config=AntiAIDetectionConfig(add_noise_grain=True, speed_factor=1.05),
        )
        assert res_path == str(out_evasion)
        assert os.path.exists(out_evasion)

    @pytest.mark.asyncio
    async def test_full_hybrid_job_processing(self, tmp_path, async_session):
        pipeline = HybridSwapPipeline(output_dir=tmp_path, mock_mode=True)

        src_video = tmp_path / "source.mp4"
        src_video.write_bytes(b"SOURCE_VIDEO")
        face_img = tmp_path / "face.jpg"
        face_img.write_bytes(b"FACE_IMAGE")

        job_id = "job_hybrid_001"
        job = VideoJob(
            job_id=job_id,
            product_id="prod_02",
            niche_id="niche_02",
            channel_id="chan_02",
            status="created",
        )
        async_session.add(job)
        await async_session.flush()

        result = await pipeline.process_hybrid_job(
            job_id=job_id,
            source_video_path=str(src_video),
            face_image_path=str(face_img),
            script="Chào bạn, mẫu kệ bếp đa năng giải quyết bừa bộn cực tốt!",
            session=async_session,
        )

        assert result["job_id"] == job_id
        assert result["status"] == "rendered"
        assert result["motion_mode"] == "hybrid_swap"
        assert result["estimated_cost_vnd"] <= 1000
        assert os.path.exists(result["output_video_path"])
        assert os.path.exists(result["audio_path"])

        # Check DB update
        updated_job = await async_session.get(VideoJob, job_id)
        assert updated_job is not None
        assert updated_job.status == "rendered"
        assert updated_job.motion_mode == "hybrid_swap"
        assert updated_job.output_video_path == result["output_video_path"]
