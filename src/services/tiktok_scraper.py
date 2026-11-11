"""AMAS v1.4.0 — TikTok Scraper & Metadata Extraction Service (Feature F06).

Extracts video metrics, captions, channel information, and linked anchor products (TikTok Shop)
using yt-dlp with non-blocking async execution and fallback offline simulation.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Optional yt-dlp import for resilient test environments
try:
    import yt_dlp
except ImportError:
    yt_dlp = None


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class TikTokScraperError(Exception):
    """Base exception for all TikTok Scraper operations."""
    pass


class InvalidTikTokURLError(ValueError, TikTokScraperError):
    """Raised when URL is empty, non-string, or not a recognized TikTok domain.

    Inherits from ValueError for contract compatibility with existing boundary tests.
    """
    pass


class VideoUnavailableError(TikTokScraperError):
    """Raised when video is private, removed, deleted, or geo-blocked."""
    pass


class ScraperTimeoutError(TimeoutError, TikTokScraperError):
    """Raised when extraction exceeds the configured network timeout."""
    pass


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class TikTokVideoMeta:
    """Standardized metadata representation of a TikTok video."""

    video_id: str
    video_url: str
    channel_id: str
    channel_url: str
    view_count: int
    like_count: int
    comment_count: int
    caption: str
    anchor_product_id: Optional[str] = None
    anchor_product_title: Optional[str] = None

    @property
    def has_anchor_product(self) -> bool:
        """Returns True if the video contains an attached yellow cart anchor product."""
        return bool(self.anchor_product_id)

    def to_dict(self) -> Dict[str, Any]:
        """Converts metadata to a standard dictionary."""
        return {
            "video_id": self.video_id,
            "video_url": self.video_url,
            "channel_id": self.channel_id,
            "channel_url": self.channel_url,
            "view_count": self.view_count,
            "like_count": self.like_count,
            "comment_count": self.comment_count,
            "caption": self.caption,
            "anchor_product_id": self.anchor_product_id,
            "anchor_product_title": self.anchor_product_title,
        }


# ---------------------------------------------------------------------------
# Service Implementation
# ---------------------------------------------------------------------------

class TikTokScraper:
    """Asynchronous TikTok scraper extracting video metadata and TikTok Shop anchors."""

    DEFAULT_USER_AGENT: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )

    def __init__(
        self,
        ydl_opts: Optional[Dict[str, Any]] = None,
        timeout: float = 15.0,
        mock_mode: Optional[bool] = None,
    ) -> None:
        self.timeout = timeout
        self.mock_mode = (
            mock_mode
            if mock_mode is not None
            else bool(os.environ.get("TIKTOK_SCRAPER_MOCK") or yt_dlp is None)
        )
        self.ydl_opts: Dict[str, Any] = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
            "skip_download": True,
            "socket_timeout": int(timeout),
            "http_headers": {
                "User-Agent": self.DEFAULT_USER_AGENT,
            },
        }
        if ydl_opts:
            self.ydl_opts.update(ydl_opts)

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    async def download_video_metadata(self, video_url: str) -> TikTokVideoMeta:
        """Extracts complete metadata and anchor product from a TikTok video URL."""
        clean_url = self._validate_video_url(video_url)
        video_id = self._extract_video_id(clean_url)

        if self.mock_mode:
            return self._mock_video_metadata(clean_url, video_id)

        try:
            info = await asyncio.wait_for(
                asyncio.to_thread(self._run_ytdlp_extract, clean_url),
                timeout=self.timeout,
            )
            return self._parse_video_meta(info, clean_url, video_id)
        except asyncio.TimeoutError as exc:
            raise ScraperTimeoutError(f"Scraper timed out after {self.timeout}s for {clean_url}") from exc
        except Exception as exc:
            err_msg = str(exc).lower()
            if "private" in err_msg or "not available" in err_msg or "404" in err_msg or "removed" in err_msg:
                raise VideoUnavailableError(f"Video unavailable or private: {clean_url}") from exc
            if isinstance(exc, (InvalidTikTokURLError, ScraperTimeoutError, VideoUnavailableError)):
                raise
            raise TikTokScraperError(f"Scraper failed for {clean_url}: {exc}") from exc

    async def extract_anchor_product(self, video_url: str) -> Optional[Dict[str, Any]]:
        """Extracts linked TikTok Shop product information from a video URL."""
        meta = await self.download_video_metadata(video_url)
        if not meta.anchor_product_id:
            return None
        return {
            "product_id": meta.anchor_product_id,
            "title": meta.anchor_product_title or "",
            "product_url": f"https://shop.tiktok.com/view/product/{meta.anchor_product_id}",
        }

    async def get_recent_videos(self, channel_url: str, limit: int = 10) -> List[TikTokVideoMeta]:
        """Extracts recent video metadata list from a creator/channel profile URL."""
        clean_url = self._validate_channel_url(channel_url)
        if limit <= 0:
            return []

        if self.mock_mode:
            return self._mock_channel_videos(clean_url, limit)

        opts = dict(self.ydl_opts)
        opts["playlistend"] = limit
        opts["extract_flat"] = True

        try:
            info = await asyncio.wait_for(
                asyncio.to_thread(self._run_ytdlp_extract, clean_url, opts),
                timeout=self.timeout * 2,
            )
            entries = info.get("entries") or []
            results: List[TikTokVideoMeta] = []
            for entry in entries[:limit]:
                v_id = str(entry.get("id") or "0")
                v_url = str(entry.get("url") or f"{clean_url}/video/{v_id}")
                results.append(self._parse_video_meta(entry, v_url, v_id))
            return results
        except asyncio.TimeoutError as exc:
            raise ScraperTimeoutError(f"Channel scraping timed out for {clean_url}") from exc
        except Exception as exc:
            if isinstance(exc, (InvalidTikTokURLError, ScraperTimeoutError)):
                raise
            raise TikTokScraperError(f"Channel extraction failed for {clean_url}: {exc}") from exc

    # -----------------------------------------------------------------------
    # Internal Helpers
    # -----------------------------------------------------------------------

    def _run_ytdlp_extract(self, url: str, custom_opts: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Runs synchronous yt-dlp extraction in worker thread."""
        opts = custom_opts or self.ydl_opts
        if yt_dlp is None:
            raise RuntimeError("yt_dlp module is not installed")
        with yt_dlp.YoutubeDL(opts) as ydl:
            return ydl.extract_info(url, download=False)

    def _validate_video_url(self, url: Any) -> str:
        if not url or not isinstance(url, str) or not url.strip():
            raise InvalidTikTokURLError("Invalid TikTok URL: URL cannot be empty")
        url_clean = url.strip()
        try:
            parsed = urlparse(url_clean)
        except Exception as exc:
            raise InvalidTikTokURLError(f"Invalid TikTok URL: {url_clean}") from exc

        if parsed.scheme.lower() not in ("http", "https"):
            raise InvalidTikTokURLError(f"Invalid TikTok URL scheme '{parsed.scheme}': {url_clean}")

        host = (parsed.hostname or "").lower()
        if not (host == "tiktok.com" or host.endswith(".tiktok.com")):
            raise InvalidTikTokURLError(f"Invalid TikTok domain '{host}': {url_clean}")

        return url_clean

    def _validate_channel_url(self, url: Any) -> str:
        if not url or not isinstance(url, str) or not url.strip():
            raise InvalidTikTokURLError("Invalid TikTok channel URL: URL cannot be empty")
        url_clean = url.strip()
        try:
            parsed = urlparse(url_clean)
        except Exception as exc:
            raise InvalidTikTokURLError(f"Invalid TikTok channel URL: {url_clean}") from exc

        if parsed.scheme.lower() not in ("http", "https"):
            raise InvalidTikTokURLError(f"Invalid TikTok channel URL scheme '{parsed.scheme}': {url_clean}")

        host = (parsed.hostname or "").lower()
        if not (host == "tiktok.com" or host.endswith(".tiktok.com")):
            raise InvalidTikTokURLError(f"Invalid TikTok channel domain '{host}': {url_clean}")

        return url_clean

    def _extract_video_id(self, url: str) -> str:
        match = re.search(r"/(?:video|v)/(\d+)", url)
        if match:
            return match.group(1)
        slug = url.rstrip("/").split("/")[-1].split("?")[0]
        return slug or "0"

    def _parse_video_meta(self, info: Dict[str, Any], url: str, fallback_id: str) -> TikTokVideoMeta:
        vid_id = str(info.get("id") or fallback_id)
        channel_id = str(info.get("uploader_id") or info.get("channel_id") or "unknown_creator")
        channel_url = str(info.get("uploader_url") or f"https://www.tiktok.com/@{channel_id}")
        caption = str(info.get("description") or info.get("title") or "")
        view_count = int(info.get("view_count") or 0)
        like_count = int(info.get("like_count") or 0)
        comment_count = int(info.get("comment_count") or 0)

        anchor_id, anchor_title = self._extract_anchor_from_info(info)

        return TikTokVideoMeta(
            video_id=vid_id,
            video_url=str(info.get("webpage_url") or url),
            channel_id=channel_id,
            channel_url=channel_url,
            view_count=view_count,
            like_count=like_count,
            comment_count=comment_count,
            caption=caption,
            anchor_product_id=anchor_id,
            anchor_product_title=anchor_title,
        )

    def _extract_anchor_from_info(self, info: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
        if not isinstance(info, dict):
            return None, None

        anchors = info.get("anchors") or []
        if not anchors:
            raw_struct = info.get("raw_data")
            if not isinstance(raw_struct, dict):
                item_info = info.get("itemInfo")
                if isinstance(item_info, dict):
                    raw_struct = item_info.get("itemStruct")
                else:
                    raw_struct = None
            if isinstance(raw_struct, dict):
                anchors = raw_struct.get("anchors") or []

        if not isinstance(anchors, list):
            anchors = []

        SHOPPING_ANCHOR_TYPES = {1004, 1005}
        NON_SHOPPING_ANCHOR_TYPES = {28, 1002, 1003, 1006}

        for anchor in anchors:
            if not isinstance(anchor, dict):
                continue

            anchor_type = anchor.get("type")
            if anchor_type is not None:
                try:
                    anchor_type = int(anchor_type)
                except (ValueError, TypeError):
                    anchor_type = None

            if anchor_type in NON_SHOPPING_ANCHOR_TYPES:
                continue

            extra = anchor.get("extra")
            extra_data: Optional[Dict[str, Any]] = None
            if isinstance(extra, dict):
                extra_data = extra
            elif isinstance(extra, str) and extra.strip():
                try:
                    parsed = json.loads(extra)
                    if isinstance(parsed, dict):
                        extra_data = parsed
                except Exception:
                    pass

            is_shopping_anchor = False
            if anchor_type in SHOPPING_ANCHOR_TYPES:
                is_shopping_anchor = True
            elif extra_data and any(k in extra_data for k in ("product_id", "promotion_id", "price", "shop_id")):
                is_shopping_anchor = True

            if not is_shopping_anchor and anchor_type is not None:
                continue

            anchor_id = str(anchor.get("id") or "").strip()
            keyword = str(anchor.get("keyword") or anchor.get("name") or anchor.get("title") or "").strip()
            prod_id = None
            prod_title = keyword or None

            if extra_data:
                pid_extra = extra_data.get("product_id") or extra_data.get("id")
                if pid_extra:
                    prod_id = str(pid_extra).strip()
                title_extra = extra_data.get("title") or extra_data.get("name")
                if title_extra:
                    prod_title = str(title_extra).strip()

            prod_id = prod_id or (anchor_id if anchor_id else None)
            if prod_id:
                return str(prod_id), prod_title

        # Regex fallback on caption for affiliate shop links
        caption = str(info.get("description") or info.get("title") or "")
        match = re.search(r"shop\.tiktok\.com/(?:view/)?product/([A-Za-z0-9_]+)", caption)
        if match:
            return match.group(1), None

        return None, None

    def _mock_video_metadata(self, video_url: str, video_id: str) -> TikTokVideoMeta:
        return TikTokVideoMeta(
            video_id=video_id,
            video_url=video_url,
            channel_id="chan_koc_01",
            channel_url="https://www.tiktok.com/@koc_fashion",
            view_count=850000,
            like_count=45000,
            comment_count=1200,
            caption="Chiếc váy hack dáng thần thánh cho các nàng eo bánh mì #fashion #xuhuong",
            anchor_product_id="prod_dress_101",
            anchor_product_title="Váy hoa nhí dáng xòe chiết eo hack dáng",
        )

    def _mock_channel_videos(self, channel_url: str, limit: int) -> List[TikTokVideoMeta]:
        return [
            TikTokVideoMeta(
                video_id=f"vid_{i+1}",
                video_url=f"{channel_url}/video/700000{i+1}",
                channel_id="chan_test",
                channel_url=channel_url,
                view_count=100000 * (i + 1),
                like_count=5000 * (i + 1),
                comment_count=200 * (i + 1),
                caption=f"Video sample {i+1} viral review",
                anchor_product_id=f"prod_{i+1}",
                anchor_product_title=f"Sample Product {i+1}",
            )
            for i in range(limit)
        ]
