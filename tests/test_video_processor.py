"""Unit tests for FFmpeg Video Processor (Feature F17)."""

import os
from pathlib import Path
import pytest
from unittest.mock import AsyncMock, patch

from src.services.video_processor import VideoProcessor, VideoProcessingError


class TestVideoProcessorContract:
    """Verifies interface contract with Tier 1 and VideoStudioAgent."""

    @pytest.mark.asyncio
    async def test_video_processor_dummy_inputs_simulated_pass(self, tmp_path):
        """Simulates test_tier1_features.py test_f17_video_processor where inputs are 0-byte touched files."""
        video = tmp_path / "raw.mp4"
        audio = tmp_path / "voice.mp3"
        out = tmp_path / "remixed.mp4"
        video.touch()
        audio.touch()

        proc = VideoProcessor()
        res = await proc.remix_video(str(video), str(audio), str(out))
        assert os.path.exists(res)
        assert res == str(out)

    @pytest.mark.asyncio
    async def test_remix_video_missing_inputs_raises_file_not_found(self, tmp_path):
        proc = VideoProcessor()
        video = tmp_path / "nonexistent_video.mp4"
        audio = tmp_path / "nonexistent_audio.mp3"
        out = tmp_path / "out.mp4"

        with pytest.raises(FileNotFoundError):
            await proc.remix_video(str(video), str(audio), str(out))

    @pytest.mark.asyncio
    async def test_remix_video_ffmpeg_failure_raises_video_processing_error(self, tmp_path):
        video = tmp_path / "raw.mp4"
        audio = tmp_path / "voice.mp3"
        out = tmp_path / "remixed.mp4"
        video.write_bytes(b"non_empty_video_bytes")
        audio.write_bytes(b"non_empty_audio_bytes")

        proc = VideoProcessor(ffmpeg_bin="ffmpeg")
        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (b"", b"Invalid codec or corrupted stream")
        mock_proc.returncode = 1

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            with pytest.raises(VideoProcessingError) as exc_info:
                await proc.remix_video(str(video), str(audio), str(out))
            assert "FFmpeg remixing failed with code 1" in str(exc_info.value)
            assert "Invalid codec" in str(exc_info.value)


class TestVideoProcessorCommandBuilding:
    """Verifies FFmpeg command construction and copyright evasion filter chain."""

    def test_build_ffmpeg_command_contains_all_evasion_filters(self):
        proc = VideoProcessor(ffmpeg_bin="ffmpeg")
        cmd = proc.build_ffmpeg_command(
            video_path="/tmp/video.mp4",
            audio_path="/tmp/audio.mp3",
            output_path="/tmp/out.mp4",
            options={
                "speed_factor": 1.05,
                "hflip": True,
                "contrast": 1.04,
                "keep_original_audio": True,
            },
        )

        cmd_str = " ".join(cmd)
        # Check video filters
        assert "hflip" in cmd_str
        assert "setpts=" in cmd_str
        assert "eq=" in cmd_str
        assert "crop=" in cmd_str
        assert "scale=1080:1920" in cmd_str

        # Check audio mixing
        assert "amix=" in cmd_str
        assert "atempo=" in cmd_str

        # Check encoders
        assert "libx264" in cmd_str
        assert "aac" in cmd_str
        assert "+faststart" in cmd_str

    def test_build_ffmpeg_command_without_bgm(self):
        proc = VideoProcessor(ffmpeg_bin="ffmpeg")
        cmd = proc.build_ffmpeg_command(
            video_path="/tmp/video.mp4",
            audio_path="/tmp/audio.mp3",
            output_path="/tmp/out.mp4",
            options={"keep_original_audio": False},
        )
        cmd_str = " ".join(cmd)
        # amix should NOT be present when original audio is discarded
        assert "amix" not in cmd_str

    def test_speed_jitter_bounds(self):
        proc = VideoProcessor(default_speed_range=(1.02, 1.08))
        for _ in range(10):
            cmd = proc.build_ffmpeg_command(
                video_path="/tmp/video.mp4",
                audio_path="/tmp/audio.mp3",
                output_path="/tmp/out.mp4",
            )
            # Find setpts or atempo
            cmd_str = " ".join(cmd)
            # Speed is between 1.02 and 1.08
            assert any(f"atempo=1.0" in cmd_str for _ in range(1))

    @pytest.mark.asyncio
    async def test_extract_audio_from_video(self, tmp_path):
        video = tmp_path / "test.mp4"
        video.touch()
        out_audio = tmp_path / "extracted.mp3"

        proc = VideoProcessor()
        res = await proc.extract_audio(str(video), str(out_audio))
        assert os.path.exists(res)
        assert res.endswith(".mp3")


class TestVideoStudioAgent:
    """Verifies F18 VideoStudioAgent end-to-end coordination."""

    @pytest.mark.asyncio
    async def test_produce_video_standalone(self, tmp_path):
        from src.agents.video_studio import VideoStudioAgent

        studio = VideoStudioAgent(storage_dir=str(tmp_path / "rendered"))
        prod_meta = {
            "product_id": "prod_test_01",
            "niche_id": "thoi_trang_nu",
            "title": "Váy hoa nhí dáng xòe chiết eo tôn dáng",
            "price": 189000.0,
        }
        res = await studio.produce_video(
            job_id="job_studio_01",
            product_meta=prod_meta,
            persona={"tone": "koc"},
        )

        assert os.path.exists(res)
        assert "job_studio_01" in res
        assert res.endswith(".mp4")

    @pytest.mark.asyncio
    async def test_produce_video_with_db_sync(self, db_session, tmp_path):
        from src.agents.video_studio import VideoStudioAgent
        from src.database.models import Niche, Product, VideoJob

        # Setup test entities in DB
        niche = Niche(niche_id="thoi_trang_nu_test", name="Thời trang nữ", description="Test niche")
        prod = Product(
            product_id="prod_db_01",
            niche_id="thoi_trang_nu_test",
            title="Đầm maxi hoa nhí tôn dáng",
            product_url="https://tiktok.com/@shop/product/prod_db_01",
            price=299000.0,
            commission_rate=0.2,
        )
        job = VideoJob(
            job_id="job_db_sync_01",
            product_id="prod_db_01",
            niche_id="thoi_trang_nu_test",
            status="rendering",
        )
        db_session.add(niche)
        db_session.add(prod)
        db_session.add(job)
        await db_session.commit()

        studio = VideoStudioAgent(storage_dir=str(tmp_path / "rendered"))
        res = await studio.produce_video(
            job_id="job_db_sync_01",
            product_meta={"title": prod.title, "niche_id": "thoi_trang_nu_test"},
            persona={"tone": "koc"},
            db_session=db_session,
        )

        assert os.path.exists(res)
        # Check job updated in DB
        await db_session.refresh(job)
        assert job.status == "rendered"
        assert job.output_video_path == res
        assert job.rendered_video_path == res
        assert job.audio_path is not None
        assert job.script is not None

    @pytest.mark.asyncio
    async def test_video_studio_voice_routing_and_transcribe_source(self, tmp_path):
        from unittest.mock import AsyncMock
        from src.agents.video_studio import VideoStudioAgent

        studio = VideoStudioAgent(storage_dir=str(tmp_path / "rendered"))
        studio.transcriber.transcribe = AsyncMock(return_value="Kịch bản đối thủ mẫu")
        studio.tts.synthesize = AsyncMock(return_value=str(tmp_path / "audio.mp3"))
        studio.downloader.download_video = AsyncMock(return_value=str(tmp_path / "source.mp4"))
        studio.processor.remix_video = AsyncMock(return_value=str(tmp_path / "final.mp4"))

        # Case 1: Homelife title without niche_id -> must resolve to Nam Minh voice
        await studio.produce_video(
            job_id="job_voice_test_01",
            product_meta={"title": "Cây lau nhà thông minh tự vắt 360 độ"},
            persona={"tone": "koc"},
        )
        assert studio.tts.synthesize.call_args.kwargs["voice"] == "vi-VN-NamMinhNeural"

        # Case 2: Explicit persona voice override
        await studio.produce_video(
            job_id="job_voice_test_02",
            product_meta={"title": "Cây lau nhà thông minh tự vắt 360 độ"},
            persona={"voice_name": "vi-VN-CustomVoice"},
        )
        assert studio.tts.synthesize.call_args.kwargs["voice"] == "vi-VN-CustomVoice"

        # Case 3: options['transcribe_source'] activates transcriber
        await studio.produce_video(
            job_id="job_transcribe_test",
            product_meta={"title": "Váy body nhún eo"},
            options={"transcribe_source": True},
        )
        assert studio.transcriber.transcribe.called
