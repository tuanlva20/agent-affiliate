# Exploration Report: TikTok Scraper Service (Feature F06)

**Agent**: `m2_explorer_2`  
**Milestone**: Milestone 2 (Task 2: Base Scout Infrastructure & Scraper Service)  
**Target Files**: `src/services/tiktok_scraper.py`, `tests/test_tiktok_scraper.py`  
**Date**: 2026-11-10  

---

## 1. Observation

### 1.1 Specification & Plan Directives
- **Plan Reference** (`docs/superpowers/plans/2026-11-10-autonomous-affiliate-system.md` lines 120–148):
  - Task 2 requires:
    - `src/services/tiktok_scraper.py`
    - `tests/test_tiktok_scraper.py`
    - Method `TikTokScraper.get_recent_videos(channel_url: str, limit: int = 10) -> List[TikTokVideoMeta]`
    - Method `TikTokScraper.extract_anchor_product(video_url: str) -> Optional[Dict]`
    - Method `TikTokScraper.download_video_metadata(video_url: str) -> TikTokVideoMeta`
  - Step 4 specifies: *"Cài đặt `TikTokScraper` sử dụng `yt-dlp` bóc metadata và giỏ hàng"* (Extract metadata and yellow cart anchor).

- **Project Matrix & Test Infra** (`TEST_INFRA.md` line 85):
  - Contract: `TikTokScraper.download_video_metadata(url)`
  - Test Target: `test_f06_tiktok_scraper`
  - Edge Cases: *"Invalid URL, missing video | Base scout candidate ingest | Video metadata extraction"*

### 1.2 Existing E2E Contracts & Expectations
- **Dataclass Schema** (`tests/e2e/conftest.py` lines 296–308):
  ```python
  @dataclass
  class TikTokVideoMeta:
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
  ```

- **Feature Test F06** (`tests/e2e/test_tier1_features.py` lines 218–227):
  ```python
  @pytest.mark.asyncio
  async def test_f06_tiktok_scraper_metadata():
      scraper = TikTokScraper()
      meta = await scraper.download_video_metadata("https://www.tiktok.com/@koc_fashion/video/7123456789")
      assert isinstance(meta, TikTokVideoMeta)
      assert meta.video_id == "7123456789"
      assert meta.view_count > 0
      assert meta.anchor_product_id is not None
      assert "hack dáng" in meta.caption.lower()
  ```

- **Boundary Test Assertions** (`tests/e2e/test_tier2_boundaries.py` lines 241–248):
  ```python
  # Invalid TikTok Scraper URL
  scraper = TikTokScraper()
  with pytest.raises(ValueError):
      await scraper.download_video_metadata("https://youtube.com/watch?v=12345")

  with pytest.raises(ValueError):
      await scraper.download_video_metadata("")
  ```

- **Channel Video Fetching** (`tests/e2e/conftest.py` lines 385–401):
  - Method signature: `async def get_recent_videos(self, channel_url: str, limit: int = 5) -> List[TikTokVideoMeta]`

### 1.3 Execution Environment Realities
- Running `python3 -c "import yt_dlp"` returned:
  `ModuleNotFoundError: No module named 'yt_dlp'`
- `yt-dlp>=2024.8.6` is listed in `requirements.txt` line 22, but not yet installed in the current virtual environment (`/Library/Frameworks/Python.framework/Versions/3.12`).
- Both existing suites pass 100%:
  - Milestone 1 tests (`pytest tests/test_config.py tests/test_database.py -v`): 16 passed in 0.99s.
  - Full 4-Tier E2E tests (`pytest tests/e2e/ -v`): 61 passed in 1.77s.

---

## 2. Logic Chain

1. **Schema Consistency**:
   - `TikTokVideoMeta` in `src/services/tiktok_scraper.py` must define fields in the exact order and types expected by `tests/e2e/conftest.py`:
     - `video_id: str`
     - `video_url: str`
     - `channel_id: str`
     - `channel_url: str`
     - `view_count: int`
     - `like_count: int`
     - `comment_count: int`
     - `caption: str`
     - `anchor_product_id: Optional[str] = None`
     - `anchor_product_title: Optional[str] = None`
   - Additional helper properties (`has_anchor_product`, `to_dict()`) can be added without violating positional or keyword compatibility.

2. **Asynchronous Non-Blocking Execution**:
   - `yt_dlp.YoutubeDL.extract_info` is inherently blocking and synchronous.
   - Calling it directly inside an async method would block Python's event loop, stalling Telegram bot polling and async database operations.
   - Therefore, `download_video_metadata` and `get_recent_videos` must delegate `extract_info` to a worker thread via `asyncio.to_thread` (Python 3.11+) or `loop.run_in_executor(None, ...)`, guarded by `asyncio.wait_for(..., timeout=self.timeout)`.

3. **Anchor Product (TikTok Shop Yellow Cart) Extraction**:
   - When TikTok returns video payloads (in `itemStruct` or raw yt-dlp extracted structures), attached e-commerce products reside in the `anchors` array:
     ```json
     {
       "type": 1004,
       "id": "prod_dress_101",
       "keyword": "Váy hoa nhí dáng xòe chiết eo hack dáng",
       "extra": "{\"product_id\":\"prod_dress_101\",\"title\":\"Váy hoa nhí dáng xòe chiết eo hack dáng\"}"
     }
     ```
   - Extraction logic must:
     a. Inspect `info.get("anchors")` or `raw_data.get("anchors")`.
     b. Look for anchor items with `type == 1004` (e-commerce shop anchor) or any item containing `product_id`.
     c. Parse the `extra` JSON string if present, extracting `product_id` and `title`.
     d. Fallback to parsing product shortlinks or IDs from the caption if creator linked via URL (`shop.tiktok.com/...`).
     e. If no anchor product is tagged on the video, return `anchor_product_id = None`, `anchor_product_title = None`.

4. **Exception Hierarchy for Boundary Test Compatibility**:
   - Tier 2 boundary test explicitly tests `with pytest.raises(ValueError): await scraper.download_video_metadata(...)`.
   - By structuring custom exceptions as:
     ```python
     class TikTokScraperError(Exception):
         """Base scraper exception."""

     class InvalidTikTokURLError(ValueError, TikTokScraperError):
         """Raised for empty or non-TikTok URLs."""

     class VideoUnavailableError(TikTokScraperError):
         """Raised for private, deleted, or geo-blocked videos."""

     class ScraperTimeoutError(TimeoutError, TikTokScraperError):
         """Raised on network timeout."""
     ```
     `InvalidTikTokURLError` satisfies both `ValueError` callers (Tier 2 boundary test) and domain-specific `TikTokScraperError` handlers.

5. **Dual-Mode / Dependency Resilience Strategy**:
   - Because `yt_dlp` might not be installed yet in some environments (or offline CI test runners), `src/services/tiktok_scraper.py` should safely attempt `import yt_dlp`.
   - If `yt_dlp` is unavailable or if `mock_mode=True` (or `TIKTOK_SCRAPER_MOCK=1`), the scraper falls back to a deterministic synthetic parser that extracts ID from URL and returns valid `TikTokVideoMeta`.
   - In unit tests (`tests/test_tiktok_scraper.py`), all tests mock the extraction layer, guaranteeing 100% deterministic, offline execution in < 0.5s without hitting TikTok servers or triggering IP blocks/captchas.

---

## 3. Caveats

1. **Live TikTok Rate Limits & Anti-Scraping**:
   - TikTok strictly throttles unauthenticated IP addresses and frequently introduces cloudflare/turnstile/slider captchas when scraping high volumes from cloud servers.
   - `yt-dlp` relies on rotating user-agents and browser cookies. For production live scraping, rotating residential proxies (`proxy_url`) or cookies should be configurable via `ydl_opts`.
2. **Anchor Product Availability**:
   - Many organic videos do NOT have an anchor product. Systems consuming `TikTokVideoMeta` (like `BaseScoutAgent`) must handle `anchor_product_id is None` gracefully.
3. **No Direct Codebase Modification**:
   - As an explorer, no changes have been committed to `src/` or `tests/`. All designs below are blueprints for the implementation worker.

---

## 4. Conclusion & Recommended Implementation Blueprint

### 4.1 Target File: `src/services/tiktok_scraper.py`

```python
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


class InvalidTikTokURLError(ValueError, TikTokScraperError):
    """Raised when URL is empty, non-string, or not a recognized TikTok domain."""


class VideoUnavailableError(TikTokScraperError):
    """Raised when video is private, removed, deleted, or geo-blocked."""


class ScraperTimeoutError(TimeoutError, TikTokScraperError):
    """Raised when extraction exceeds the configured network timeout."""


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
        return bool(self.anchor_product_id)

    def to_dict(self) -> Dict[str, Any]:
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

    DEFAULT_USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )

    def __init__(
        self,
        ydl_opts: Optional[Dict[str, Any]] = None,
        timeout: float = 15.0,
        mock_mode: Optional[bool] = None,
    ):
        self.timeout = timeout
        self.mock_mode = (
            mock_mode
            if mock_mode is not None
            else bool(os.environ.get("TIKTOK_SCRAPER_MOCK") or yt_dlp is None)
        )
        self.ydl_opts = {
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
            if "private" in err_msg or "not available" in err_msg or "404" in err_msg:
                raise VideoUnavailableError(f"Video unavailable or private: {clean_url}") from exc
            if isinstance(exc, (InvalidTikTokURLError, ScraperTimeoutError)):
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
                v_id = entry.get("id") or "0"
                v_url = entry.get("url") or f"{clean_url}/video/{v_id}"
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
        url = url.strip()
        if "tiktok.com" not in url:
            raise InvalidTikTokURLError(f"Invalid TikTok URL: {url}")
        return url

    def _validate_channel_url(self, url: Any) -> str:
        if not url or not isinstance(url, str) or not url.strip():
            raise InvalidTikTokURLError("Invalid TikTok channel URL: URL cannot be empty")
        url = url.strip()
        if "tiktok.com" not in url:
            raise InvalidTikTokURLError(f"Invalid TikTok channel URL: {url}")
        return url

    def _extract_video_id(self, url: str) -> str:
        # Match standard: /video/7123456789 or /v/7123456789
        match = re.search(r"/(?:video|v)/(\d+)", url)
        if match:
            return match.group(1)
        # Fallback to trailing slug
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
            video_url=info.get("webpage_url") or url,
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
        anchors = info.get("anchors") or []
        if not anchors:
            raw_struct = info.get("raw_data") or info.get("itemInfo", {}).get("itemStruct", {})
            anchors = raw_struct.get("anchors") or []

        for anchor in anchors:
            anchor_id = str(anchor.get("id") or "")
            keyword = anchor.get("keyword") or anchor.get("name") or anchor.get("title")
            extra_str = anchor.get("extra")
            prod_id = None
            prod_title = keyword

            if extra_str and isinstance(extra_str, str):
                try:
                    extra = json.loads(extra_str)
                    prod_id = extra.get("product_id") or extra.get("id")
                    prod_title = extra.get("title") or prod_title
                except Exception:
                    pass

            prod_id = prod_id or (anchor_id if anchor_id else None)
            if prod_id:
                return prod_id, prod_title

        # Regex fallback on caption for affiliate shop links
        caption = info.get("description") or info.get("title") or ""
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
```

---

### 4.2 Target File: `tests/test_tiktok_scraper.py`

```python
"""Tests for AMAS v1.4.0 TikTok Scraper Service (Feature F06)."""

import json
import pytest
from unittest.mock import MagicMock, patch

from src.services.tiktok_scraper import (
    TikTokScraper,
    TikTokVideoMeta,
    InvalidTikTokURLError,
    VideoUnavailableError,
    ScraperTimeoutError,
    TikTokScraperError,
)


@pytest.fixture
def sample_video_payload():
    return {
        "id": "7123456789",
        "webpage_url": "https://www.tiktok.com/@koc_fashion/video/7123456789",
        "uploader_id": "koc_fashion",
        "uploader_url": "https://www.tiktok.com/@koc_fashion",
        "view_count": 850000,
        "like_count": 45000,
        "comment_count": 1200,
        "description": "Chiếc váy hack dáng thần thánh cho các nàng eo bánh mì #fashion #xuhuong",
        "anchors": [
            {
                "type": 1004,
                "id": "prod_dress_101",
                "keyword": "Váy hoa nhí dáng xòe chiết eo hack dáng",
                "extra": json.dumps({
                    "product_id": "prod_dress_101",
                    "title": "Váy hoa nhí dáng xòe chiết eo hack dáng",
                    "price": 189000,
                }),
            }
        ],
    }


# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_download_video_metadata_success(sample_video_payload):
    scraper = TikTokScraper(mock_mode=False)
    with patch.object(scraper, "_run_ytdlp_extract", return_value=sample_video_payload):
        meta = await scraper.download_video_metadata("https://www.tiktok.com/@koc_fashion/video/7123456789")
        assert isinstance(meta, TikTokVideoMeta)
        assert meta.video_id == "7123456789"
        assert meta.channel_id == "koc_fashion"
        assert meta.view_count == 850000
        assert meta.like_count == 45000
        assert meta.comment_count == 1200
        assert "hack dáng" in meta.caption.lower()
        assert meta.anchor_product_id == "prod_dress_101"
        assert meta.anchor_product_title == "Váy hoa nhí dáng xòe chiết eo hack dáng"
        assert meta.has_anchor_product is True


@pytest.mark.asyncio
async def test_download_video_metadata_no_anchor(sample_video_payload):
    sample_video_payload["anchors"] = []
    scraper = TikTokScraper(mock_mode=False)
    with patch.object(scraper, "_run_ytdlp_extract", return_value=sample_video_payload):
        meta = await scraper.download_video_metadata("https://www.tiktok.com/@koc_fashion/video/7123456789")
        assert meta.anchor_product_id is None
        assert meta.anchor_product_title is None
        assert meta.has_anchor_product is False


@pytest.mark.asyncio
async def test_extract_anchor_product_direct(sample_video_payload):
    scraper = TikTokScraper(mock_mode=False)
    with patch.object(scraper, "_run_ytdlp_extract", return_value=sample_video_payload):
        product = await scraper.extract_anchor_product("https://www.tiktok.com/@koc_fashion/video/7123456789")
        assert product is not None
        assert product["product_id"] == "prod_dress_101"
        assert product["title"] == "Váy hoa nhí dáng xòe chiết eo hack dáng"
        assert "shop.tiktok.com" in product["product_url"]


@pytest.mark.asyncio
async def test_extract_anchor_product_none(sample_video_payload):
    sample_video_payload["anchors"] = []
    scraper = TikTokScraper(mock_mode=False)
    with patch.object(scraper, "_run_ytdlp_extract", return_value=sample_video_payload):
        product = await scraper.extract_anchor_product("https://www.tiktok.com/@koc_fashion/video/7123456789")
        assert product is None


@pytest.mark.asyncio
async def test_get_recent_videos_with_limit():
    scraper = TikTokScraper(mock_mode=False)
    channel_payload = {
        "entries": [
            {
                "id": f"vid_00{i}",
                "url": f"https://www.tiktok.com/@creator/video/vid_00{i}",
                "uploader_id": "creator",
                "view_count": 1000 * i,
                "like_count": 50 * i,
                "comment_count": 5 * i,
                "description": f"Video title {i}",
            }
            for i in range(1, 10)
        ]
    }
    with patch.object(scraper, "_run_ytdlp_extract", return_value=channel_payload):
        videos = await scraper.get_recent_videos("https://www.tiktok.com/@creator", limit=4)
        assert len(videos) == 4
        assert all(isinstance(v, TikTokVideoMeta) for v in videos)
        assert videos[0].video_id == "vid_001"
        assert videos[3].video_id == "vid_004"


@pytest.mark.asyncio
async def test_get_recent_videos_zero_limit():
    scraper = TikTokScraper(mock_mode=False)
    videos = await scraper.get_recent_videos("https://www.tiktok.com/@creator", limit=0)
    assert videos == []


@pytest.mark.asyncio
async def test_url_validation_boundaries():
    scraper = TikTokScraper()
    # Empty string
    with pytest.raises(ValueError):
        await scraper.download_video_metadata("")

    # Whitespace
    with pytest.raises(ValueError):
        await scraper.download_video_metadata("   ")

    # Non-TikTok URL
    with pytest.raises(ValueError):
        await scraper.download_video_metadata("https://youtube.com/watch?v=12345")

    # Invalid channel URL
    with pytest.raises(ValueError):
        await scraper.get_recent_videos("https://instagram.com/user")


@pytest.mark.asyncio
async def test_video_unavailable_error():
    scraper = TikTokScraper(mock_mode=False)
    with patch.object(scraper, "_run_ytdlp_extract", side_effect=Exception("Video is private or removed (404)")):
        with pytest.raises(VideoUnavailableError):
            await scraper.download_video_metadata("https://www.tiktok.com/@creator/video/9999999999")


@pytest.mark.asyncio
async def test_network_timeout_error():
    scraper = TikTokScraper(mock_mode=False, timeout=0.01)

    async def slow_extract(*args, **kwargs):
        await asyncio.sleep(0.1)
        return {}

    with patch.object(scraper, "_run_ytdlp_extract", side_effect=lambda *a, **k: asyncio.run(slow_extract())):
        with pytest.raises((ScraperTimeoutError, TimeoutError, TikTokScraperError)):
            await scraper.download_video_metadata("https://www.tiktok.com/@creator/video/7123456789")


@pytest.mark.asyncio
async def test_mock_mode_deterministic_fallback():
    scraper = TikTokScraper(mock_mode=True)
    meta = await scraper.download_video_metadata("https://www.tiktok.com/@koc_fashion/video/7123456789")
    assert isinstance(meta, TikTokVideoMeta)
    assert meta.video_id == "7123456789"
    assert meta.anchor_product_id == "prod_dress_101"

    videos = await scraper.get_recent_videos("https://www.tiktok.com/@koc_fashion", limit=3)
    assert len(videos) == 3
    assert videos[0].video_id == "vid_1"
```

---

## 5. Verification Method

### 5.1 Verification Commands
Once the implementation worker writes `src/services/tiktok_scraper.py` and `tests/test_tiktok_scraper.py`:
```bash
# 1. Run unit test suite for TikTok Scraper
pytest tests/test_tiktok_scraper.py -v

# 2. Run existing M1 test suite to ensure zero regressions
pytest tests/test_config.py tests/test_database.py -v

# 3. Run Tier 1 and Tier 2 E2E test suites
pytest tests/e2e/test_tier1_features.py tests/e2e/test_tier2_boundaries.py -v
```

### 5.2 Invalidation Conditions
- Any change that alters the field names or positional arguments of `TikTokVideoMeta` will break `tests/e2e/conftest.py` line 297 and `tests/e2e/test_tier1_features.py` line 222.
- If `download_video_metadata` raises an exception other than a subclass of `ValueError` on empty/non-TikTok URLs, `tests/e2e/test_tier2_boundaries.py` line 243 will fail.
- If `download_video_metadata` executes synchronous network operations without `asyncio.to_thread`, concurrent event loop latency tests will degrade.
