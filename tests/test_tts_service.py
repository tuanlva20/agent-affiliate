"""Unit tests for Natural TTS Service (Feature F16)."""

import os
from pathlib import Path
import pytest
from unittest.mock import AsyncMock, patch

from src.services.tts_service import TTSService


class TestTTSServiceContract:
    """Verifies interface contract with Tier 1 and VideoStudioAgent."""

    @pytest.mark.asyncio
    async def test_tts_synthesize_defaults(self, tmp_path):
        tts = TTSService(storage_dir=str(tmp_path / "audio"), offline_mode=True)
        audio = await tts.synthesize("Chị em ơi, chiếc váy này xinh xỉu luôn á!")
        assert os.path.exists(audio)
        assert audio.endswith(".mp3")
        assert os.path.getsize(audio) > 0

    @pytest.mark.asyncio
    async def test_tts_synthesize_hoai_my_voice(self, tmp_path):
        tts = TTSService(storage_dir=str(tmp_path / "audio"), offline_mode=True)
        audio = await tts.synthesize(
            "Chị em ơi, dáng này hack chân đỉnh chóp luôn á!",
            voice="vi-VN-HoaiMyNeural",
        )
        assert os.path.exists(audio)
        assert audio.endswith(".mp3")

    @pytest.mark.asyncio
    async def test_tts_synthesize_nam_minh_voice(self, tmp_path):
        tts = TTSService(storage_dir=str(tmp_path / "audio"), offline_mode=True)
        audio = await tts.synthesize(
            "Các bác ơi, 3 giây sạch bóng kin kít việc nhà nhàn hẳn!",
            voice="vi-VN-NamMinhNeural",
        )
        assert os.path.exists(audio)
        assert audio.endswith(".mp3")

    @pytest.mark.asyncio
    async def test_tts_custom_output_path(self, tmp_path):
        custom_out = tmp_path / "custom_folder" / "voice_01.mp3"
        tts = TTSService(offline_mode=True)
        audio = await tts.synthesize("Xin chào các bạn", output_path=str(custom_out))
        assert audio == str(custom_out)
        assert os.path.exists(custom_out)


class TestTTSValidationAndErrors:
    """Verifies edge cases, empty input handling, and fallback resilience."""

    @pytest.mark.asyncio
    async def test_tts_empty_string_raises_value_error(self):
        tts = TTSService(offline_mode=True)
        with pytest.raises(ValueError, match="TTS text cannot be empty"):
            await tts.synthesize("")

    @pytest.mark.asyncio
    async def test_tts_whitespace_raises_value_error(self):
        tts = TTSService(offline_mode=True)
        with pytest.raises(ValueError, match="TTS text cannot be empty"):
            await tts.synthesize("   \n\t  ")

    @pytest.mark.asyncio
    async def test_tts_none_raises_value_error(self):
        tts = TTSService(offline_mode=True)
        with pytest.raises(ValueError, match="TTS text cannot be empty"):
            await tts.synthesize(None)  # type: ignore

    @pytest.mark.asyncio
    async def test_tts_unsupported_voice_falls_back_to_default(self, tmp_path):
        tts = TTSService(storage_dir=str(tmp_path / "audio"), offline_mode=True)
        audio = await tts.synthesize("Test giọng lạ", voice="unknown-voice-id")
        assert os.path.exists(audio)

    def test_get_audio_duration_heuristic(self, tmp_path):
        tts = TTSService()
        dummy_audio = tmp_path / "test.mp3"
        dummy_audio.touch()

        # Vietnamese text: 15 words -> ~5.0 seconds
        text = "Chị em ơi đây là chiếc váy hoa nhí cực kỳ tôn dáng che khuyết điểm bụng"
        dur = tts.get_audio_duration(str(dummy_audio), text=text)
        assert 3.0 <= dur <= 8.0

        # Empty text fallback
        dur_empty = tts.get_audio_duration(str(dummy_audio))
        assert dur_empty > 0.0

    @pytest.mark.asyncio
    async def test_tts_offline_fallback_valid_mp3_header(self, tmp_path):
        tts = TTSService(storage_dir=str(tmp_path / "audio"), offline_mode=True)
        out_file = tmp_path / "offline.mp3"
        await tts.synthesize("Kịch bản thử nghiệm ngoại tuyến", output_path=str(out_file))

        assert out_file.exists()
        header = out_file.read_bytes()[:4]
        # MP3 sync frame prefix: 0xff 0xfb
        assert header.startswith(b"\xff\xfb")
