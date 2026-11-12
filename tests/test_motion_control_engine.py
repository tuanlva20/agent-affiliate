"""Unit tests for Motion Control Engine (Phase 2.1b / AMAS-4)."""

import os
from pathlib import Path
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.database.models import Base, Channel, Niche, Product, VideoJob
from src.services.motion_control_engine import (
    MissingResourceError,
    MotionControlEngine,
    MotionControlError,
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
        # Prepopulate required parent records for VideoJob foreign keys
        niche = Niche(niche_id="niche_01", name="Fashion", description="Fashion niche")
        channel = Channel(
            channel_id="chan_01",
            niche_id="niche_01",
            browser_profile_id="prof_01",
            platform="tiktok",
            lifecycle_status="ready_to_post",
        )
        product = Product(
            product_id="prod_01",
            niche_id="niche_01",
            title="Áo thun phong cách",
            price=150000.0,
            product_url="https://shop.tiktok.com/p/01",
        )
        session.add_all([niche, channel, product])
        await session.flush()
        yield session

    await engine.dispose()


class TestMotionControlEngine:
    """Verifies segment generation, assembling, and VideoJob processing."""

    @pytest.mark.asyncio
    async def test_missing_character_image_raises_error(self, tmp_path):
        engine = MotionControlEngine(storage_dir=tmp_path, mock_mode=True)
        with pytest.raises(MissingResourceError):
            await engine.generate_segment_clip(
                character_image_path=str(tmp_path / "non_existent.jpg"),
                motion_reference_path="",
                prompt="test prompt",
                segment_name="hook",
            )

    @pytest.mark.asyncio
    async def test_empty_assemble_clips_raises_error(self, tmp_path):
        engine = MotionControlEngine(storage_dir=tmp_path, mock_mode=True)
        with pytest.raises(MotionControlError):
            await engine.assemble_full_video(
                segment_clip_paths=[],
                voiceover_audio_path=str(tmp_path / "audio.mp3"),
                output_path=str(tmp_path / "out.mp4"),
            )

    @pytest.mark.asyncio
    async def test_generate_segment_clip_mock(self, tmp_path):
        engine = MotionControlEngine(storage_dir=tmp_path, mock_mode=True)

        char_img = tmp_path / "model.png"
        char_img.write_bytes(b"MODEL_PNG_DATA")

        clip_path = await engine.generate_segment_clip(
            character_image_path=str(char_img),
            motion_reference_path="",
            prompt="smiling model in dress",
            segment_name="hook",
        )

        assert os.path.exists(clip_path)
        assert Path(clip_path).stat().st_size > 0

    @pytest.mark.asyncio
    async def test_full_video_job_processing(self, tmp_path, async_session):
        engine = MotionControlEngine(storage_dir=tmp_path, mock_mode=True)

        char_img = tmp_path / "avatar.png"
        char_img.write_bytes(b"AVATAR_IMAGE_DATA")

        prod_img = tmp_path / "product.png"
        prod_img.write_bytes(b"PRODUCT_IMAGE_DATA")

        # Create VideoJob in DB
        job_id = "job_motion_001"
        job = VideoJob(
            job_id=job_id,
            product_id="prod_01",
            niche_id="niche_01",
            channel_id="chan_01",
            status="created",
        )
        async_session.add(job)
        await async_session.flush()

        result = await engine.process_job(
            job_id=job_id,
            character_image_path=str(char_img),
            product_image_path=str(prod_img),
            script="Chào bạn, đây là mẫu áo váy mới nhất!",
            session=async_session,
        )

        assert result["job_id"] == job_id
        assert result["status"] == "rendered"
        assert result["motion_mode"] == "kling_motion"
        assert os.path.exists(result["output_video_path"])
        assert os.path.exists(result["audio_path"])
        assert len(result["segment_clips"]) == 4

        # Verify DB updated
        updated_job = await async_session.get(VideoJob, job_id)
        assert updated_job is not None
        assert updated_job.status == "rendered"
        assert updated_job.motion_mode == "kling_motion"
        assert updated_job.output_video_path == result["output_video_path"]
        assert updated_job.audio_path == result["audio_path"]
        assert updated_job.segments_data is not None
        assert len(updated_job.segments_data["clips"]) == 4
