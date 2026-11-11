"""AMAS v1.4.0 — Video Downloader Service (Feature F13).

Downloads watermark-free TikTok competitor videos using yt-dlp with async execution,
configurable storage management, and offline simulation fallback.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse

logger = logging.getLogger("amas.services.video_downloader")

try:
    import yt_dlp
except ImportError:
    yt_dlp = None


class VideoDownloaderError(Exception):
    """Base exception for VideoDownloader."""
    pass


class InvalidVideoURLError(ValueError, VideoDownloaderError):
    """Raised when URL is empty, invalid, or malformed."""
    pass


class VideoNotFoundError(VideoDownloaderError):
    """Raised when video is 404, removed, or private."""
    pass


class VideoDownloadTimeoutError(TimeoutError, VideoDownloaderError):
    """Raised when video download times out."""
    pass


class VideoDownloader:
    """Asynchronous video downloader with watermark-free stream extraction."""

    DEFAULT_OUTPUT_DIR = Path("downloads/raw_videos")
    DEFAULT_TIMEOUT = 30.0

    ALLOWED_DOMAINS = frozenset({
        "tiktok.com",
        "www.tiktok.com",
        "vm.tiktok.com",
        "vt.tiktok.com",
        "m.tiktok.com",
        "douyin.com",
        "www.douyin.com",
    })
    SHORTLINK_DOMAINS = frozenset({
        "vm.tiktok.com",
        "vt.tiktok.com",
    })

    def __init__(
        self,
        output_dir: Optional[str | Path] = None,
        timeout: float = DEFAULT_TIMEOUT,
        mock_mode: Optional[bool] = None,
        ydl_opts: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.output_dir = Path(output_dir or self.DEFAULT_OUTPUT_DIR)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout
        self.mock_mode = (
            mock_mode
            if mock_mode is not None
            else bool(os.environ.get("VIDEO_DOWNLOADER_MOCK") or yt_dlp is None)
        )
        self.ydl_opts: Dict[str, Any] = {
            "format": "best[ext=mp4]/bestvideo[ext=mp4]+bestaudio[ext=m4a]/best",
            "quiet": True,
            "no_warnings": True,
            "nocheckcertificate": True,
            "socket_timeout": int(timeout),
        }
        if ydl_opts:
            self.ydl_opts.update(ydl_opts)

    def _validate_url(self, url: str) -> str:
        if not url or not isinstance(url, str):
            raise InvalidVideoURLError("Video URL must be a non-empty string.")
        clean_url = url.strip()
        if not clean_url:
            raise InvalidVideoURLError("Video URL cannot be empty.")

        try:
            parsed = urlparse(clean_url)
        except Exception as exc:
            raise InvalidVideoURLError(f"Malformed video URL: {url}") from exc

        if not parsed.scheme or parsed.scheme.lower() not in ("http", "https"):
            raise InvalidVideoURLError(f"Malformed video URL: {url}")

        host = (parsed.hostname or "").lower()
        if not host or host not in self.ALLOWED_DOMAINS:
            raise InvalidVideoURLError(f"Unsupported video domain: {host}")

        path = parsed.path or ""
        if host in self.SHORTLINK_DOMAINS:
            if not re.search(r"^/[a-zA-Z0-9_-]+/?$", path) or path in ("", "/"):
                raise InvalidVideoURLError(f"URL does not point to a valid video stream: {clean_url}")
        else:
            if not re.search(r"/(?:video|v)/(\d+)", path):
                raise InvalidVideoURLError(f"URL does not point to a valid video stream: {clean_url}")

        return clean_url

    def _extract_video_id(self, url: str) -> str:
        match = re.search(r"/(?:video|v)/(\d+)", url)
        if match:
            return match.group(1)
        sanitized = re.sub(r"[^a-zA-Z0-9_-]", "_", url.split("?")[0].rstrip("/").split("/")[-1])
        return sanitized or "video_download"

    def _mock_download(self, url: str, dest_path: Path) -> str:
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        # Minimal valid ISO Base Media File Format (MP4) 32-byte header
        mp4_magic = (
            b"\x00\x00\x00\x20\x66\x74\x79\x70\x69\x73\x6f\x6d"
            b"\x00\x00\x02\x00\x69\x73\x6f\x6d\x69\x73\x6f\x32"
            b"\x61\x76\x63\x31\x6d\x70\x34\x31"
        )
        with open(dest_path, "wb") as f:
            f.write(mp4_magic)
        return str(dest_path.resolve())

    def _run_ytdlp_download(self, url: str, dest_path: Path, opts: Dict[str, Any]) -> str:
        if yt_dlp is None:
            raise VideoDownloaderError("yt-dlp is not installed")
        local_opts = dict(opts)
        local_opts["outtmpl"] = str(dest_path)
        with yt_dlp.YoutubeDL(local_opts) as ydl:
            retcode = ydl.download([url])
            if retcode != 0:
                raise VideoDownloaderError(f"yt-dlp download failed with exit code {retcode}")
        return str(dest_path.resolve())

    async def download_video(
        self,
        url: str,
        output_path: Optional[str | Path] = None,
        timeout: Optional[float] = None,
    ) -> str:
        """Downloads a TikTok video to a local MP4 file."""
        clean_url = self._validate_url(url)
        effective_timeout = timeout or self.timeout

        if output_path:
            dest = Path(output_path)
        else:
            vid_id = self._extract_video_id(clean_url)
            dest = self.output_dir / f"{vid_id}.mp4"

        # Ensure destination ends with .mp4
        if not str(dest).endswith(".mp4"):
            dest = dest.with_suffix(".mp4")

        dest.parent.mkdir(parents=True, exist_ok=True)

        if self.mock_mode:
            return self._mock_download(clean_url, dest)

        try:
            return await asyncio.wait_for(
                asyncio.to_thread(self._run_ytdlp_download, clean_url, dest, self.ydl_opts),
                timeout=effective_timeout,
            )
        except asyncio.TimeoutError as exc:
            raise VideoDownloadTimeoutError(
                f"Download timed out after {effective_timeout}s for {clean_url}"
            ) from exc
        except Exception as exc:
            err_msg = str(exc).lower()
            if "404" in err_msg or "not found" in err_msg or "unavailable" in err_msg:
                raise VideoNotFoundError(f"Video not found or unavailable: {clean_url}") from exc
            if isinstance(exc, (InvalidVideoURLError, VideoDownloadTimeoutError, VideoNotFoundError)):
                raise
            raise VideoDownloaderError(f"Download failed for {clean_url}: {exc}") from exc
