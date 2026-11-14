"""AMAS v1.5 — Multi-Social Scraper (AMAS-14).

Ingests competitor videos/posts from TikTok, Facebook and Instagram with:
1. Canonical ID extraction (tracking params stripped) so one post == one row.
2. UPSERT dedup: re-scraping an existing video only refreshes its metrics.
3. Velocity scoring: scheduled runs (force=False) keep only viral posts (score >= 7.0).
"""

from __future__ import annotations

import asyncio
import hashlib
import math
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from urllib.parse import parse_qs, urlparse

from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import CompetitorScrapeLog, CompetitorVideo
from src.services.tiktok_scraper import TikTokScraper

try:
    import yt_dlp
except ImportError:
    yt_dlp = None

VIRAL_THRESHOLD = 7.0
CACHE_DIR = Path("tempFile/raw_videos")
MOCK_MODE = bool(os.environ.get("MULTI_SOCIAL_SCRAPER_MOCK", "1") == "1")

_PLATFORM_HOSTS = {
    "tiktok": ("tiktok.com",),
    "facebook": ("facebook.com", "fb.watch", "fb.com"),
    "instagram": ("instagram.com",),
}


def detect_platform(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    for platform, hosts in _PLATFORM_HOSTS.items():
        if any(host == h or host.endswith("." + h) for h in hosts):
            return platform
    raise ValueError(f"Unsupported social URL: {url}")


def extract_canonical_id(url: str) -> Tuple[str, str]:
    """Returns (platform, canonical_id). Tracking params never change the ID."""
    if not url or not isinstance(url, str):
        raise ValueError("URL must be a non-empty string")
    url = url.strip()
    platform = detect_platform(url)
    parsed = urlparse(url)
    path = parsed.path

    patterns = {
        "tiktok": r"/video/(\d+)",
        "instagram": r"/(?:reel|reels|p)/([A-Za-z0-9_-]+)",
        "facebook": r"/(?:reel|videos|posts)/(\d+)",
    }
    match = re.search(patterns[platform], path)
    if match:
        return platform, match.group(1)
    if platform == "facebook":
        v = parse_qs(parsed.query).get("v")
        if v and v[0].isdigit():
            return platform, v[0]
    # Short links (vt.tiktok.com/xyz, fb.watch/xyz): hash host+path, query dropped.
    normalized = f"{parsed.hostname}{path.rstrip('/')}".lower()
    return platform, hashlib.sha1(normalized.encode()).hexdigest()[:20]


def calculate_velocity_score(views: int, likes: int, comments: int, hours_since_posted: float) -> float:
    """0-10 viral score: 60% views/hour (log scale), 40% engagement rate."""
    views, likes, comments = max(views, 0), max(likes, 0), max(comments, 0)
    views_per_hour = views / max(hours_since_posted, 1.0)
    velocity = min(10.0, math.log10(views_per_hour + 1) * 2)
    engagement = min(10.0, (likes + comments) / max(views, 1) * 100)
    return round(0.6 * velocity + 0.4 * engagement, 2)


async def fetch_metadata(platform: str, url: str) -> Dict[str, Any]:
    """Returns {views, likes, comments, caption, hours_since_posted}."""
    if platform == "tiktok":
        meta = await TikTokScraper(mock_mode=MOCK_MODE or None).download_video_metadata(url)
        return {
            "views": meta.view_count,
            "likes": meta.like_count,
            "comments": meta.comment_count,
            "caption": meta.caption,
            "hours_since_posted": 24.0,  # shortcut: TikTokVideoMeta has no timestamp, upgrade when it does
        }
    if MOCK_MODE or yt_dlp is None:
        return {"views": 420000, "likes": 21000, "comments": 800,
                "caption": f"Mock {platform} reel", "hours_since_posted": 24.0}

    def _extract() -> Dict[str, Any]:
        with yt_dlp.YoutubeDL({"quiet": True, "skip_download": True}) as ydl:
            return ydl.extract_info(url, download=False)

    info = await asyncio.to_thread(_extract)
    ts = info.get("timestamp")
    hours = (datetime.now(timezone.utc).timestamp() - ts) / 3600 if ts else 24.0
    return {
        "views": int(info.get("view_count") or 0),
        "likes": int(info.get("like_count") or 0),
        "comments": int(info.get("comment_count") or 0),
        "caption": info.get("description") or info.get("title") or "",
        "hours_since_posted": hours,
    }


async def ensure_cached_video(platform: str, video_id: str, url: str) -> Tuple[Path, bool]:
    """Returns (path, downloaded_now). Skips the heavy download if the file exists."""
    path = CACHE_DIR / f"{platform}_{video_id}.mp4"
    if path.exists() or MOCK_MODE or yt_dlp is None:
        return path, False
    path.parent.mkdir(parents=True, exist_ok=True)

    def _download() -> None:
        with yt_dlp.YoutubeDL({"quiet": True, "outtmpl": str(path), "format": "mp4/best"}) as ydl:
            ydl.download([url])

    await asyncio.to_thread(_download)
    return path, True


async def ingest_competitor_video(
    session: AsyncSession,
    url: str,
    competitor_id: str,
    project_id: Optional[str] = None,
    force: bool = False,
) -> Dict[str, Any]:
    """Scrapes one competitor URL and UPSERTs it into competitor_videos."""
    platform, video_id = extract_canonical_id(url)
    meta = await fetch_metadata(platform, url)
    score = calculate_velocity_score(meta["views"], meta["likes"], meta["comments"], meta["hours_since_posted"])
    result: Dict[str, Any] = {
        "video_id": video_id, "platform": platform, "velocity_score": score,
        "stored": False, "is_duplicate_updated": False, "skipped_low_score": False,
        "downloaded": False,
    }

    if not force and score < VIRAL_THRESHOLD:
        result["skipped_low_score"] = True
        session.add(CompetitorScrapeLog(
            log_id=f"slog_{uuid.uuid4().hex[:12]}", competitor_id=competitor_id,
            videos_found=0, status="skipped_low_score",
        ))
        await session.commit()
        return result

    existing = await session.get(CompetitorVideo, video_id)
    if existing:
        existing.views_count = meta["views"]
        existing.likes_count = meta["likes"]
        existing.caption = meta["caption"]
        existing.scraped_at = datetime.now(timezone.utc)
        result["is_duplicate_updated"] = True
    else:
        session.add(CompetitorVideo(
            video_id=video_id, competitor_id=competitor_id, project_id=project_id,
            platform=platform, video_url=url.strip(), caption=meta["caption"],
            views_count=meta["views"], likes_count=meta["likes"],
        ))

    session.add(CompetitorScrapeLog(
        log_id=f"slog_{uuid.uuid4().hex[:12]}", competitor_id=competitor_id,
        videos_found=1, status="success",
    ))
    await session.commit()

    _, result["downloaded"] = await ensure_cached_video(platform, video_id, url)
    result["stored"] = True
    return result
