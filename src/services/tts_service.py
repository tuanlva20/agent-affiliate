"""AMAS v1.4.0 — Natural TTS Service (Feature F16).

Integrates edge-tts for Vietnamese speech synthesis with offline and mock fallbacks.
Supported voices:
- vi-VN-HoaiMyNeural: Female KOC Persona (Fashion)
- vi-VN-NamMinhNeural: Male KOC Persona (Home Utilities)
"""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
import tempfile
from typing import Any, Dict, Optional

logger = logging.getLogger("amas.services.tts")

# Minimal valid MPEG Layer 3 audio frame for offline/mock fallback
_MOCK_MP3_FRAME = b"\xff\xfb\x90\x00" + b"\x00" * 414


class TTSService:
    """Vietnamese Text-to-Speech synthesis service."""

    SUPPORTED_VOICES: Dict[str, str] = {
        "vi-VN-HoaiMyNeural": "Hoài My (Female, Fashion KOC)",
        "vi-VN-NamMinhNeural": "Nam Minh (Male, Home Utilities KOC)",
    }
    DEFAULT_VOICE = "vi-VN-HoaiMyNeural"

    def __init__(
        self,
        default_voice: str = DEFAULT_VOICE,
        storage_dir: str = "storage/audio",
        offline_mode: bool = False,
    ) -> None:
        self.default_voice = (
            default_voice if default_voice in self.SUPPORTED_VOICES else self.DEFAULT_VOICE
        )
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.offline_mode = offline_mode

    async def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        output_path: Optional[str] = None,
        rate: str = "+0%",
        volume: str = "+0%",
        pitch: str = "+0Hz",
        max_retries: int = 3,
    ) -> str:
        """Synthesizes natural Vietnamese voiceover into an MP3 file.

        Raises:
            ValueError: If text is empty or whitespace only.
        """
        if not text or not isinstance(text, str) or not text.strip():
            raise ValueError("TTS text cannot be empty")

        selected_voice = voice or self.default_voice
        if selected_voice not in self.SUPPORTED_VOICES:
            logger.warning(
                f"Voice {selected_voice} not officially recognized; using {self.DEFAULT_VOICE}"
            )
            selected_voice = self.DEFAULT_VOICE

        if output_path:
            dest = Path(output_path)
            dest.parent.mkdir(parents=True, exist_ok=True)
        else:
            fd, tmp = tempfile.mkstemp(prefix="tts_", suffix=".mp3", dir=str(self.storage_dir))
            os.close(fd)
            dest = Path(tmp)

        # 1. Offline Mode Check
        if self.offline_mode:
            return self._generate_fallback_mp3(dest)

        # 2. edge-tts Attempt with Retry
        try:
            import edge_tts  # type: ignore

            for attempt in range(1, max_retries + 1):
                try:
                    communicate = edge_tts.Communicate(
                        text=text.strip(),
                        voice=selected_voice,
                        rate=rate,
                        volume=volume,
                        pitch=pitch,
                    )
                    await communicate.save(str(dest))
                    if dest.exists() and dest.stat().st_size > 0:
                        return str(dest)
                except Exception as ex:
                    logger.warning(f"edge-tts attempt {attempt}/{max_retries} failed: {ex}")
                    if attempt < max_retries:
                        await asyncio.sleep(1.0 * attempt)
                    else:
                        raise ex
        except Exception as e:
            logger.warning(f"edge-tts unavailable or failed ({e}); invoking offline fallback")
            return self._generate_fallback_mp3(dest)

        return str(dest)

    def _generate_fallback_mp3(self, dest: Path) -> str:
        """Writes valid mock MP3 data to ensure downstream processes do not fail."""
        try:
            dest.write_bytes(_MOCK_MP3_FRAME)
        except Exception:
            dest.touch()
        return str(dest)

    def get_audio_duration(self, audio_path: str, text: Optional[str] = None) -> float:
        """Estimates or detects audio duration in seconds."""
        # 1. Heuristic from text if provided (Vietnamese conversational pace: ~3.0 words/sec)
        if text and text.strip():
            words = len(text.strip().split())
            return max(1.0, round(words / 3.0, 2))

        # 2. Check file size heuristic
        if os.path.exists(audio_path):
            size = os.path.getsize(audio_path)
            if size > 1024:
                # 128 kbps = 16 KB/sec
                return max(1.0, round(size / 16000.0, 2))

        return 3.0
