"""Unit tests for Scene Analyzer Service (Phase 2.1a / AMAS-3)."""

from pathlib import Path
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.database.models import Base, MotionAsset
from src.services.scene_analyzer import (
    SceneAnalysisResult,
    SceneAnalyzerService,
    VideoInputError,
    VideoSegment,
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
        yield session

    await engine.dispose()


class TestSceneAnalyzerService:
    """Verifies 4-part scene decomposition, metadata parsing, and DB persistence."""

    @pytest.mark.asyncio
    async def test_invalid_input_rejected(self, tmp_path):
        service = SceneAnalyzerService(output_dir=tmp_path, mock_mode=True)
        with pytest.raises(VideoInputError):
            await service.analyze_and_segment("")

        with pytest.raises(VideoInputError):
            await service.analyze_and_segment(None)  # type: ignore

        with pytest.raises(VideoInputError):
            await service.analyze_and_segment(str(tmp_path / "non_existent.mp4"))

    @pytest.mark.asyncio
    async def test_analyze_video_url_mock(self, tmp_path):
        service = SceneAnalyzerService(output_dir=tmp_path, mock_mode=True)
        url = "https://tiktok.com/@competitor/video/712345"

        result = await service.analyze_and_segment(url, cut_clips=True)

        assert isinstance(result, SceneAnalysisResult)
        assert result.asset_id.startswith("asset_")
        assert result.source_url == url
        assert len(result.segments) == 4

        segment_names = [s.name for s in result.segments]
        assert segment_names == ["hook", "problem", "demo", "cta"]

        # Validate Hook is ~3s
        hook = result.segments[0]
        assert hook.name == "hook"
        assert hook.start_sec == 0.0
        assert hook.end_sec == 3.0
        assert hook.duration == 3.0
        assert hook.clip_path is not None
        assert Path(hook.clip_path).exists()

        # Validate result dictionary conversion
        res_dict = result.to_dict()
        assert "segments" in res_dict
        assert len(res_dict["segments"]) == 4

    @pytest.mark.asyncio
    async def test_analyze_local_video_and_db_save(self, tmp_path, async_session):
        service = SceneAnalyzerService(output_dir=tmp_path, mock_mode=True)

        # Create dummy local mp4 file
        local_video = tmp_path / "sample_competitor.mp4"
        local_video.write_bytes(b"FAKE_MP4_HEADER_DATA")

        custom_asset_id = "test_asset_001"
        result = await service.analyze_and_segment(
            str(local_video),
            save_to_db=True,
            session=async_session,
            cut_clips=False,
            asset_id=custom_asset_id,
        )

        assert result.asset_id == custom_asset_id
        assert result.video_path == str(local_video.resolve())
        assert result.total_duration > 0

        # Query DB to verify persistence
        saved_asset = await async_session.get(MotionAsset, custom_asset_id)
        assert saved_asset is not None
        assert saved_asset.asset_id == custom_asset_id
        assert saved_asset.source_type == "competitor_video"
        assert saved_asset.duration == result.total_duration
        assert "segments" in saved_asset.motion_features
        assert len(saved_asset.motion_features["segments"]) == 4
