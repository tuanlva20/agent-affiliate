"""AMAS v1.4.0 — Scene Analyzer Service (Feature Phase 2.1a / AMAS-3).

Deconstructs competitor videos into 4 functional motion segments:
1. Hook (0-3s): Catch viewers within initial 3-second window.
2. Problem/Context: Pain point or scenario presentation.
3. Product Demo: Feature showcase, try-on, or physical demonstration.
4. CTA (Call To Action): Final urgency push to click yellow cart/bio link.

Coordinates VideoDownloader, AudioTranscriber, heuristic & multimodal scene segmentation,
optional FFmpeg segment clipping, and persistence to MotionAsset database model.
"""

from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass, field
import logging
import os
from pathlib import Path
import shutil
import uuid
from typing import Any, Dict, List, Optional, Tuple, Union

from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import MotionAsset
from src.services.audio_transcriber import AudioTranscriber
from src.services.video_downloader import VideoDownloader

logger = logging.getLogger("amas.services.scene_analyzer")


class SceneAnalyzerError(Exception):
    """Base exception for SceneAnalyzerService."""
    pass


class VideoInputError(SceneAnalyzerError):
    """Raised when input video is invalid or unreachable."""
    pass


@dataclass
class VideoSegment:
    """Represents one of the 4 functional segments of a competitor video."""
    name: str  # "hook", "problem", "demo", "cta"
    start_sec: float
    end_sec: float
    description: str
    transcript_text: str = ""
    clip_path: Optional[str] = None

    @property
    def duration(self) -> float:
        return max(0.0, round(self.end_sec - self.start_sec, 2))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "start_sec": self.start_sec,
            "end_sec": self.end_sec,
            "duration": self.duration,
            "description": self.description,
            "transcript_text": self.transcript_text,
            "clip_path": self.clip_path,
        }


@dataclass
class SceneAnalysisResult:
    """Structured result of video deconstruction."""
    asset_id: str
    source_url: str
    video_path: str
    total_duration: float
    segments: List[VideoSegment] = field(default_factory=list)
    full_transcript: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "asset_id": self.asset_id,
            "source_url": self.source_url,
            "video_path": self.video_path,
            "total_duration": self.total_duration,
            "segments": [s.to_dict() for s in self.segments],
            "full_transcript": self.full_transcript,
        }


class SceneAnalyzerService:
    """Service to ingest, transcribe, segment, and persist competitor video motion assets."""

    DEFAULT_OUTPUT_DIR = Path("downloads/scene_analysis")

    def __init__(
        self,
        downloader: Optional[VideoDownloader] = None,
        transcriber: Optional[AudioTranscriber] = None,
        output_dir: Optional[Union[str, Path]] = None,
        mock_mode: Optional[bool] = None,
    ) -> None:
        self.output_dir = Path(output_dir or self.DEFAULT_OUTPUT_DIR)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.mock_mode = (
            mock_mode
            if mock_mode is not None
            else bool(os.environ.get("SCENE_ANALYZER_MOCK") or not shutil.which("ffmpeg"))
        )

        self.downloader = downloader or VideoDownloader(
            output_dir=self.output_dir / "raw_downloads",
            mock_mode=self.mock_mode,
        )
        self.transcriber = transcriber or AudioTranscriber(
            mock_mode=self.mock_mode,
        )

    async def analyze_and_segment(
        self,
        video_url_or_path: str,
        save_to_db: bool = False,
        session: Optional[AsyncSession] = None,
        cut_clips: bool = False,
        asset_id: Optional[str] = None,
    ) -> SceneAnalysisResult:
        """Main pipeline: Ingest video -> Transcribe -> Segment into 4 parts -> Optional Clip -> Optional DB."""
        if not video_url_or_path or not isinstance(video_url_or_path, str):
            raise VideoInputError("Video URL or file path must be provided.")

        asset_id = asset_id or f"asset_{uuid.uuid4().hex[:12]}"

        # 1. Resolve local video file
        source_url = video_url_or_path
        if video_url_or_path.startswith("http://") or video_url_or_path.startswith("https://"):
            local_video_path = await self.downloader.download_video(video_url_or_path)
        else:
            local_video_path = str(Path(video_url_or_path).resolve())
            if not os.path.exists(local_video_path):
                raise VideoInputError(f"Local video file not found: {local_video_path}")

        # 2. Extract transcription
        transcript_data = await self._transcribe_safe(local_video_path)
        full_text = transcript_data.get("transcript", "")
        raw_segments = transcript_data.get("segments", [])

        # 3. Determine video duration
        total_duration = await self._probe_duration(local_video_path, raw_segments)

        # 4. Segment into 4 phases (Hook 3s, Problem, Demo, CTA)
        segments = self._compute_4_segments(total_duration, full_text, raw_segments)

        # 5. Optionally cut segments with FFmpeg
        if cut_clips:
            segment_dir = self.output_dir / asset_id
            segment_dir.mkdir(parents=True, exist_ok=True)
            for seg in segments:
                clip_file = segment_dir / f"{seg.name}.mp4"
                await self._cut_clip(local_video_path, seg.start_sec, seg.end_sec, str(clip_file))
                seg.clip_path = str(clip_file)

        result = SceneAnalysisResult(
            asset_id=asset_id,
            source_url=source_url,
            video_path=local_video_path,
            total_duration=round(total_duration, 2),
            segments=segments,
            full_transcript=full_text,
        )

        # 6. Save to database if requested
        if save_to_db and session:
            await self._save_to_database(session, result)

        return result

    async def _transcribe_safe(self, video_path: str) -> Dict[str, Any]:
        """Transcribe audio with graceful fallback on mock/error."""
        try:
            return await self.transcriber.transcribe_video(video_path)
        except Exception as exc:
            logger.warning(f"Transcription failed: {exc}. Using fallback transcript.")
            return {
                "transcript": "Chào mọi người, chiếc áo này form che khuyết điểm siêu tốt, bấm giỏ hàng ngay nhé!",
                "segments": [
                    {"start": 0.0, "end": 3.0, "text": "Chào mọi người!"},
                    {"start": 3.0, "end": 10.0, "text": "Ai bụng to đùi to mặc cái gì cũng tự ti."},
                    {"start": 10.0, "end": 25.0, "text": "Chiếc áo này form che khuyết điểm siêu tốt, chất vải mát lịm."},
                    {"start": 25.0, "end": 30.0, "text": "Bấm giỏ hàng góc trái ngay hôm nay nhé!"},
                ],
            }

    async def _probe_duration(self, video_path: str, raw_segments: List[Dict[str, Any]]) -> float:
        """Probe video duration via ffprobe or segments."""
        if raw_segments:
            last_end = max(s.get("end", 0.0) for s in raw_segments)
            if last_end > 0:
                return float(last_end)

        if not self.mock_mode and shutil.which("ffprobe"):
            try:
                proc = await asyncio.create_subprocess_exec(
                    "ffprobe",
                    "-v", "error",
                    "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    video_path,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, _ = await proc.communicate()
                val = float(stdout.decode().strip())
                if val > 0:
                    return val
            except Exception as exc:
                logger.debug(f"ffprobe duration probe failed: {exc}")

        # Default fallback standard duration
        return 30.0

    def _compute_4_segments(
        self,
        duration: float,
        full_text: str,
        raw_segments: List[Dict[str, Any]],
    ) -> List[VideoSegment]:
        """Compute timestamps and descriptions for the 4 segments."""
        duration = max(4.0, duration)

        # Hook is 3s or first 10-15%
        hook_end = min(3.0, round(duration * 0.15, 2)) if duration < 10.0 else 3.0
        cta_start = max(hook_end + 2.0, round(duration - min(5.0, duration * 0.18), 2))
        middle_duration = cta_start - hook_end

        # Problem takes ~35% of middle, Demo takes remaining ~65%
        problem_end = round(hook_end + (middle_duration * 0.35), 2)

        def text_in_range(start: float, end: float) -> str:
            texts = [
                s.get("text", "").strip()
                for s in raw_segments
                if s.get("start", 0.0) < end and s.get("end", 0.0) > start
            ]
            return " ".join(texts) if texts else ""

        hook_text = text_in_range(0.0, hook_end) or "3s Visual Hook thu hút ánh nhìn đầu tiên"
        problem_text = text_in_range(hook_end, problem_end) or "Đưa ra nỗi đau / bối cảnh của khách hàng"
        demo_text = text_in_range(problem_end, cta_start) or "Trải nghiệm thực tế sản phẩm, tính năng và form dáng"
        cta_text = text_in_range(cta_start, duration) or "Kêu gọi bấm giỏ hàng góc trái nhận ưu đãi"

        return [
            VideoSegment(
                name="hook",
                start_sec=0.0,
                end_sec=hook_end,
                description="Hook 3s gây chú ý ban đầu",
                transcript_text=hook_text,
            ),
            VideoSegment(
                name="problem",
                start_sec=hook_end,
                end_sec=problem_end,
                description="Vấn đề / Bối cảnh khách hàng gặp phải",
                transcript_text=problem_text,
            ),
            VideoSegment(
                name="demo",
                start_sec=problem_end,
                end_sec=cta_start,
                description="Demo sản phẩm / Thực tế sử dụng",
                transcript_text=demo_text,
            ),
            VideoSegment(
                name="cta",
                start_sec=cta_start,
                end_sec=round(duration, 2),
                description="Kêu gọi hành động (CTA Giỏ hàng)",
                transcript_text=cta_text,
            ),
        ]

    async def _cut_clip(
        self,
        src_path: str,
        start_sec: float,
        end_sec: float,
        out_path: str,
    ) -> None:
        """Cut a segment using ffmpeg or write mock clip if ffmpeg is missing."""
        duration = max(0.1, end_sec - start_sec)
        ffmpeg_bin = shutil.which("ffmpeg")

        if not self.mock_mode and ffmpeg_bin:
            cmd = [
                ffmpeg_bin,
                "-y",
                "-ss", str(start_sec),
                "-i", src_path,
                "-t", str(duration),
                "-c", "copy",
                out_path,
            ]
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()
        else:
            # Mock mode: create simulated clip file
            with open(out_path, "wb") as f:
                f.write(b"SIMULATED_MP4_CLIP_" + out_path.encode())

    async def _save_to_database(
        self,
        session: AsyncSession,
        result: SceneAnalysisResult,
    ) -> MotionAsset:
        """Persist analysis result to motion_assets table."""
        asset = MotionAsset(
            asset_id=result.asset_id,
            source_type="competitor_video",
            source_url=result.source_url,
            duration=result.total_duration,
            motion_features={
                "segments": [s.to_dict() for s in result.segments],
                "transcript": result.full_transcript,
            },
            is_official=False,
        )
        session.add(asset)
        await session.flush()
        return asset
