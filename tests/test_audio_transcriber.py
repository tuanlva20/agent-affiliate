"""Unit tests for Audio Transcriber Service (Feature F14)."""

import os
from pathlib import Path
import pytest

from src.services.audio_transcriber import (
    AudioTranscriber,
    AudioTranscriberError,
    MediaNotFoundError,
)


class TestAudioTranscriber:
    """Verifies F14 Audio Transcriber contracts and behavior."""

    @pytest.mark.asyncio
    async def test_transcribe_missing_file_raises_not_found(self):
        transcriber = AudioTranscriber(mock_mode=True)
        with pytest.raises(FileNotFoundError):
            await transcriber.transcribe("/nonexistent/path/sample.mp4")

    @pytest.mark.asyncio
    async def test_transcribe_dummy_sample_success(self, tmp_path):
        media = tmp_path / "sample.mp4"
        media.touch()

        transcriber = AudioTranscriber(mock_mode=True)
        transcript = await transcriber.transcribe(str(media))

        assert isinstance(transcript, str)
        assert len(transcript) > 10
        # Vietnamese KOC text
        assert any(w in transcript.lower() for w in ["chào", "chiếc", "bụng", "giỏ hàng", "chị em", "các bác"])

    @pytest.mark.asyncio
    async def test_transcribe_with_timestamps(self, tmp_path):
        media = tmp_path / "sample.mp4"
        media.touch()

        transcriber = AudioTranscriber(mock_mode=True)
        segments = await transcriber.transcribe_with_timestamps(str(media))

        assert isinstance(segments, list)
        assert len(segments) > 0
        for seg in segments:
            assert "start" in seg
            assert "end" in seg
            assert "text" in seg

    @pytest.mark.asyncio
    async def test_extract_audio_missing_media_raises_error(self):
        transcriber = AudioTranscriber(mock_mode=True)
        with pytest.raises(FileNotFoundError):
            await transcriber.extract_audio("/nonexistent/video.mp4")

    @pytest.mark.asyncio
    async def test_extract_audio_success_mock(self, tmp_path):
        media = tmp_path / "video.mp4"
        media.touch()
        out_wav = tmp_path / "audio.wav"

        transcriber = AudioTranscriber(mock_mode=True)
        res = await transcriber.extract_audio(str(media), output_wav_path=str(out_wav))

        assert os.path.exists(res)
        assert res.endswith(".wav")

    @pytest.mark.asyncio
    async def test_extract_audio_default_tempfile_creation(self, tmp_path):
        media = tmp_path / "video.mp4"
        media.touch()

        transcriber = AudioTranscriber(mock_mode=True)
        res = await transcriber.extract_audio(str(media))

        assert os.path.exists(res)
        assert res.endswith(".wav")
        try:
            os.remove(res)
        except OSError:
            pass
