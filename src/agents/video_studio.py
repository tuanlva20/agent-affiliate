"""AMAS v1.4.0 — Video Studio Pipeline Agent (Feature F18).

Coordinates the end-to-end video remix pipeline:
Product / VideoJob -> ScriptGenerator -> TTSService -> VideoDownloader -> VideoProcessor (FFmpeg)
Updates VideoJob.status = 'rendered' and saves output_video_path / rendered_video_path.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
import tempfile
from typing import Any, Dict, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.tone_validator import ToneValidator
from src.database.models import VideoJob
from src.services.audio_transcriber import AudioTranscriber
from src.services.script_generator import ScriptGenerator
from src.services.tts_service import TTSService
from src.services.video_downloader import VideoDownloader
from src.services.video_processor import VideoProcessor

logger = logging.getLogger("amas.agents.video_studio")


class VideoStudioAgent:
    """Coordinator of the end-to-end automated video remix studio (Feature F18).

    Orchestrates the multi-step production pipeline:
    1. ScriptGenerator: Generates persona-aligned, ToneValidator-compliant KOC scripts.
    2. TTSService: Synthesizes high-fidelity Vietnamese voiceover with resolved persona voice.
    3. VideoDownloader: Acquires benchmark/competitor source videos.
    4. AudioTranscriber: Extracts audio and transcribes competitor scripts for inspiration/analysis
       (invoked on source video when options={'transcribe_source': True}).
    5. VideoProcessor: Remuxes video with FFmpeg copyright evasion transformations.
    6. Database: Synchronizes job state and outputs in VideoJob.
    """

    def __init__(
        self,
        downloader: Optional[VideoDownloader] = None,
        transcriber: Optional[AudioTranscriber] = None,
        script_generator: Optional[ScriptGenerator] = None,
        tts_service: Optional[TTSService] = None,
        processor: Optional[VideoProcessor] = None,
        storage_dir: str = "storage/rendered",
    ) -> None:
        self.downloader = downloader or VideoDownloader()
        self.transcriber = transcriber or AudioTranscriber()
        self.script_gen = script_generator or ScriptGenerator()
        self.tts = tts_service or TTSService()
        self.processor = processor or VideoProcessor()
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    async def produce_video(
        self,
        job_id: str,
        product_meta: Optional[Dict[str, Any]] = None,
        persona: Optional[Dict[str, Any]] = None,
        source_video_url: Optional[str] = None,
        db_session: Optional[AsyncSession] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Executes full studio remix pipeline for a job.

        Args:
            job_id: Unique identifier for the video rendering job.
            product_meta: Product metadata (title, niche_id, price, etc.).
            persona: Persona configuration (optional explicit voice_name/voice_id or tone).
            source_video_url: Benchmark TikTok URL to download and remix.
            db_session: Optional AsyncSession to persist rendered status and file paths.
            options: Rendering and pipeline options, e.g.:
                - 'transcribe_source': bool, run AudioTranscriber on source video.
                - FFmpeg evasion options passed to VideoProcessor.remix_video.

        Returns:
            Absolute path to final rendered remix video.
        """
        meta = product_meta or {"title": "Sản phẩm xu hướng", "price": 199000.0}
        pers = persona or {"tone": "koc"}

        # 1. Generate KOC Script first so persona and certified voice are resolved
        script_data = self.script_gen.generate_script(meta, pers)
        if hasattr(script_data, "get"):
            full_voiceover = script_data.get("full_voiceover", "")
            script_voice = script_data.get("voice_id")
        else:
            full_voiceover = getattr(script_data, "full_voiceover", "")
            script_voice = getattr(script_data, "voice_id", None)

        # Determine voice name: explicit persona voice -> script_data voice_id -> niche check fallback
        voice = None
        if isinstance(pers, dict):
            voice = pers.get("voice_name") or pers.get("voice_id")
        if not voice:
            voice = script_voice
        if not voice:
            niche_id = str(meta.get("niche_id", "") if isinstance(meta, dict) else getattr(meta, "niche_id", ""))
            voice = "vi-VN-NamMinhNeural" if "do_gia_dung" in niche_id else "vi-VN-HoaiMyNeural"

        # 2. Synthesize TTS Audio
        audio_file = await self.tts.synthesize(full_voiceover, voice=voice)

        # 3. Video Acquisition (Download)
        url = (
            source_video_url
            or meta.get("source_video_url")
            or "https://tiktok.com/@competitor/video/1001"
        )
        raw_video = await self.downloader.download_video(url)

        # Optional competitor audio transcription / research extraction (Feature F14)
        if options and options.get("transcribe_source"):
            try:
                transcription = await self.transcriber.transcribe(raw_video)
                logger.info(
                    "Source video %s transcribed successfully (%d chars) for competitor analysis.",
                    raw_video,
                    len(transcription),
                )
            except Exception as exc:
                logger.warning("Optional competitor transcription skipped: %s", exc)

        # 4. Remux with FFmpeg Copyright Evasion
        rendered_file = str(self.storage_dir / f"remixed_{job_id}_final.mp4")
        await self.processor.remix_video(raw_video, audio_file, rendered_file, options=options)

        # 5. Database Synchronization (if session provided)
        if db_session:
            stmt = select(VideoJob).where(VideoJob.job_id == job_id)
            res = await db_session.execute(stmt)
            job = res.scalar_one_or_none()
            if job:
                job.status = "rendered"
                job.output_video_path = rendered_file
                job.rendered_video_path = rendered_file
                job.audio_path = audio_file
                job.script = full_voiceover
                await db_session.commit()

        return rendered_file
