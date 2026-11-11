"""AMAS v1.4.0 — TikTok Scraper Unit Test Suite (Feature F06).

Tests video metadata downloading, yellow cart anchor extraction, channel scanning,
URL boundary validation, and offline fallback resilience.
"""

from __future__ import annotations

import asyncio
import json
from unittest.mock import MagicMock, patch

import pytest

from src.services.tiktok_scraper import (
    InvalidTikTokURLError,
    ScraperTimeoutError,
    TikTokScraper,
    TikTokScraperError,
    TikTokVideoMeta,
    VideoUnavailableError,
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
# 1. Video Metadata Extraction Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_tiktok_scraper_download_video_metadata(sample_video_payload):
    scraper = TikTokScraper(mock_mode=False)
    with patch.object(scraper, "_run_ytdlp_extract", return_value=sample_video_payload):
        meta = await scraper.download_video_metadata("https://www.tiktok.com/@koc_fashion/video/7123456789")

    assert isinstance(meta, TikTokVideoMeta)
    assert meta.video_id == "7123456789"
    assert meta.video_url == "https://www.tiktok.com/@koc_fashion/video/7123456789"
    assert meta.channel_id == "koc_fashion"
    assert meta.view_count == 850000
    assert meta.like_count == 45000
    assert meta.comment_count == 1200
    assert "hack dáng" in meta.caption.lower()
    assert meta.anchor_product_id == "prod_dress_101"
    assert meta.anchor_product_title == "Váy hoa nhí dáng xòe chiết eo hack dáng"
    assert meta.has_anchor_product is True

    # Test serialization
    as_dict = meta.to_dict()
    assert as_dict["video_id"] == "7123456789"
    assert as_dict["anchor_product_id"] == "prod_dress_101"


@pytest.mark.asyncio
async def test_tiktok_scraper_no_anchor(sample_video_payload):
    sample_video_payload["anchors"] = []
    scraper = TikTokScraper(mock_mode=False)
    with patch.object(scraper, "_run_ytdlp_extract", return_value=sample_video_payload):
        meta = await scraper.download_video_metadata("https://www.tiktok.com/@koc_fashion/video/7123456789")

    assert meta.anchor_product_id is None
    assert meta.anchor_product_title is None
    assert meta.has_anchor_product is False


# ---------------------------------------------------------------------------
# 2. Yellow Cart Anchor Extraction Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_tiktok_scraper_extract_anchor_product(sample_video_payload):
    scraper = TikTokScraper(mock_mode=False)
    with patch.object(scraper, "_run_ytdlp_extract", return_value=sample_video_payload):
        product = await scraper.extract_anchor_product("https://www.tiktok.com/@koc_fashion/video/7123456789")

    assert product is not None
    assert product["product_id"] == "prod_dress_101"
    assert product["title"] == "Váy hoa nhí dáng xòe chiết eo hack dáng"
    assert "shop.tiktok.com" in product["product_url"]

    # When no anchor
    sample_video_payload["anchors"] = []
    with patch.object(scraper, "_run_ytdlp_extract", return_value=sample_video_payload):
        none_prod = await scraper.extract_anchor_product("https://www.tiktok.com/@koc_fashion/video/7123456789")
        assert none_prod is None


# ---------------------------------------------------------------------------
# 3. Channel Video Batch Scanning Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_tiktok_scraper_get_recent_videos():
    scraper = TikTokScraper(mock_mode=False)
    channel_payload = {
        "entries": [
            {
                "id": f"712345600{i}",
                "url": f"https://www.tiktok.com/@fashion_channel/video/712345600{i}",
                "uploader_id": "fashion_channel",
                "uploader_url": "https://www.tiktok.com/@fashion_channel",
                "view_count": 50000 * i,
                "like_count": 2000 * i,
                "comment_count": 100 * i,
                "description": f"Fashion outfit review {i}",
            }
            for i in range(1, 8)
        ]
    }
    with patch.object(scraper, "_run_ytdlp_extract", return_value=channel_payload):
        videos = await scraper.get_recent_videos("https://www.tiktok.com/@fashion_channel", limit=5)

    assert isinstance(videos, list)
    assert len(videos) == 5
    for item in videos:
        assert isinstance(item, TikTokVideoMeta)
        assert item.channel_id == "fashion_channel"
        assert item.view_count > 0

    # Test limit=0 returns empty list
    videos_empty = await scraper.get_recent_videos("https://www.tiktok.com/@fashion_channel", limit=0)
    assert videos_empty == []


# ---------------------------------------------------------------------------
# 4. URL Validation Boundary Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_tiktok_scraper_invalid_urls():
    scraper = TikTokScraper()

    # Empty string
    with pytest.raises(ValueError):
        await scraper.download_video_metadata("")

    # Whitespace only
    with pytest.raises(ValueError):
        await scraper.download_video_metadata("   \n\t")

    # Non-string input
    with pytest.raises(ValueError):
        await scraper.download_video_metadata(None)  # type: ignore

    # Non-tiktok URL
    with pytest.raises(ValueError):
        await scraper.download_video_metadata("https://youtube.com/watch?v=12345")

    with pytest.raises(ValueError):
        await scraper.download_video_metadata("https://facebook.com/reel/12345")

    # Attacker domain spoofing and schemes
    with pytest.raises(ValueError):
        await scraper.download_video_metadata("https://tiktok.com.attacker.com/video/123")

    with pytest.raises(ValueError):
        await scraper.download_video_metadata("https://not-tiktok.com/video/123")

    with pytest.raises(ValueError):
        await scraper.download_video_metadata("javascript:alert('tiktok.com')")

    with pytest.raises(ValueError):
        await scraper.download_video_metadata("file:///etc/passwd#tiktok.com")

    # Invalid channel URL
    with pytest.raises(ValueError):
        await scraper.get_recent_videos("https://instagram.com/user")


def test_tiktok_scraper_anchor_edge_cases():
    scraper = TikTokScraper(mock_mode=False)

    # 1. itemInfo: None and string
    pid, title = scraper._extract_anchor_from_info({"id": "v1", "itemInfo": None})
    assert pid is None and title is None

    pid, title = scraper._extract_anchor_from_info({"id": "v2", "itemInfo": "not_a_dict"})
    assert pid is None and title is None

    # 2. Non-shopping anchor type 28 (POI location)
    poi_info = {
        "id": "v3",
        "anchors": [{"type": 28, "id": "poi_999", "keyword": "Hồ Gươm", "extra": ""}],
    }
    pid, title = scraper._extract_anchor_from_info(poi_info)
    assert pid is None and title is None

    # 3. Anchor with extra already a parsed dict
    dict_extra_info = {
        "id": "v4",
        "anchors": [{
            "id": "anc_1",
            "extra": {"product_id": "p_parsed_123", "title": "Áo Sơ Mi"},
        }],
    }
    pid, title = scraper._extract_anchor_from_info(dict_extra_info)
    assert pid == "p_parsed_123"
    assert title == "Áo Sơ Mi"


# ---------------------------------------------------------------------------
# 5. Offline Fallback & Mock Mode Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_tiktok_scraper_offline_fallback():
    scraper = TikTokScraper(mock_mode=True)
    meta = await scraper.download_video_metadata("https://www.tiktok.com/@koc_fashion/video/7123456789")

    assert isinstance(meta, TikTokVideoMeta)
    assert meta.video_id == "7123456789"
    assert meta.channel_id == "chan_koc_01"
    assert meta.view_count > 0
    assert meta.anchor_product_id == "prod_dress_101"
    assert "hack dáng" in meta.caption.lower()

    # Channel scanning in offline mock mode
    videos = await scraper.get_recent_videos("https://www.tiktok.com/@koc_fashion", limit=3)
    assert len(videos) == 3
    assert videos[0].video_id == "vid_1"


# ---------------------------------------------------------------------------
# 6. Error Conditions (Unavailable & Timeout)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_tiktok_scraper_video_unavailable():
    scraper = TikTokScraper(mock_mode=False)
    with patch.object(scraper, "_run_ytdlp_extract", side_effect=Exception("HTTP Error 404: Not Found")):
        with pytest.raises(VideoUnavailableError):
            await scraper.download_video_metadata("https://www.tiktok.com/@creator/video/9999999999")


@pytest.mark.asyncio
async def test_tiktok_scraper_timeout():
    scraper = TikTokScraper(mock_mode=False, timeout=0.01)

    async def slow_extract(*args, **kwargs):
        await asyncio.sleep(0.1)
        return {}

    with patch.object(scraper, "_run_ytdlp_extract", side_effect=lambda *a, **k: asyncio.run(slow_extract())):
        with pytest.raises((ScraperTimeoutError, TimeoutError, TikTokScraperError)):
            await scraper.download_video_metadata("https://www.tiktok.com/@creator/video/7123456789")
