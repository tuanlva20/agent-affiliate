"""AMAS v1.4.0 — Comment Scanner Service (Feature F26).

Extracts recent comments from published TikTok videos using dual-mode execution:
1. High-fidelity deterministic mock mode for hermetic CI/CD testing.
2. Live TikTok Web API extraction with timeout, rate limit handling, and exponential backoff.
3. Idempotent database synchronization into SQLAlchemy VideoComment ORM models.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import logging
import os
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import aiohttp
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import VideoComment

logger = logging.getLogger("amas.services.comment_scanner")


# ==============================================================================
# Exceptions
# ==============================================================================

class CommentScannerError(Exception):
    """Base exception for all CommentScanner operations."""
    pass


class InvalidVideoIdError(ValueError, CommentScannerError):
    """Raised when video_id is empty, non-string, or malformed."""
    pass


class CommentScannerTimeoutError(TimeoutError, CommentScannerError):
    """Raised when comment extraction exceeds configured timeout."""
    pass


class CommentRateLimitError(CommentScannerError):
    """Raised when TikTok rate limits or returns HTTP 429 / 10101."""
    pass


class VideoNotFoundError(CommentScannerError):
    """Raised when video does not exist or comments are disabled."""
    pass


# ==============================================================================
# Helper Functions
# ==============================================================================

def extract_video_id(video_input: str) -> str:
    """Extracts clean video ID from raw video ID or full TikTok URL.

    Handles:
    - "tt_pub_101" -> "tt_pub_101"
    - "7123456789" -> "7123456789"
    - "https://www.tiktok.com/@koc_fashion/video/7123456789" -> "7123456789"
    - "https://www.tiktok.com/@koc/video/7123456789?is_from_webapp=1" -> "7123456789"
    """
    if not isinstance(video_input, str):
        raise InvalidVideoIdError(f"Video ID must be a string, got {type(video_input).__name__}")

    cleaned = video_input.strip()
    if not cleaned:
        raise InvalidVideoIdError("Video ID cannot be empty or whitespace")

    if "tiktok.com" in cleaned or cleaned.startswith(("http://", "https://")):
        parsed = urlparse(cleaned)
        path_parts = [p for p in parsed.path.split("/") if p]
        if "video" in path_parts:
            idx = path_parts.index("video")
            if idx + 1 < len(path_parts):
                return path_parts[idx + 1].split("?")[0]
        if path_parts:
            return path_parts[-1].split("?")[0]

    return cleaned


def parse_timestamp(val: Any) -> datetime:
    """Converts diverse timestamp formats to timezone-aware UTC datetime."""
    if val is None:
        return datetime.now(timezone.utc)
    if isinstance(val, datetime):
        if val.tzinfo is None:
            return val.replace(tzinfo=timezone.utc)
        return val.astimezone(timezone.utc)
    if isinstance(val, (int, float)):
        try:
            return datetime.fromtimestamp(val, tz=timezone.utc)
        except Exception:
            return datetime.now(timezone.utc)
    if isinstance(val, str):
        val_str = val.strip()
        if not val_str:
            return datetime.now(timezone.utc)
        try:
            iso_str = val_str.replace("Z", "+00:00")
            dt = datetime.fromisoformat(iso_str)
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except Exception:
            pass
        try:
            epoch = float(val_str)
            return datetime.fromtimestamp(epoch, tz=timezone.utc)
        except Exception:
            pass
    return datetime.now(timezone.utc)


# ==============================================================================
# Realistic Vietnamese Mock Comment Pool
# ==============================================================================

MOCK_COMMENT_POOL: List[Dict[str, Any]] = [
    {
        "text": "Váy này giá bao nhiêu vậy shop? Có freeship về Hà Nội không ạ?",
        "user": "lan_anh_99",
        "author_name": "Lan Anh",
        "author_id": "usr_lan_anh_99",
        "like_count": 14,
    },
    {
        "text": "Bụng 75cm mặc size nào vừa ạ? Chất vải có co giãn tốt không shop?",
        "user": "thanh_hang_vt",
        "author_name": "Thanh Hằng",
        "author_id": "usr_thanh_hang_vt",
        "like_count": 9,
    },
    {
        "text": "Giao hàng lâu quá shop ơi! Đặt từ tuần trước mà chưa thấy đơn giao tới.",
        "user": "user_bad_01",
        "author_name": "Minh Quân",
        "author_id": "usr_user_bad_01",
        "like_count": 2,
    },
    {
        "text": "Váy mặc lên form xinh dã man luôn ấy, vải mát rượi hack eo cực đỉnh!",
        "user": "thanh_truc_88",
        "author_name": "Thanh Trúc",
        "author_id": "usr_thanh_truc_88",
        "like_count": 31,
    },
    {
        "text": "Nồi chiên này có chống dính tốt không bác ơi, nướng gà nguyên con vừa không?",
        "user": "hoang_nam_hn",
        "author_name": "Hoàng Nam",
        "author_id": "usr_hoang_nam_hn",
        "like_count": 7,
    },
    {
        "text": "Cho mình xin giá và bảng size chi tiết với ạ!",
        "user": "mai_huong_hp",
        "author_name": "Mai Hương",
        "author_id": "usr_mai_huong_hp",
        "like_count": 5,
    },
]


# ==============================================================================
# CommentScanner Service
# ==============================================================================

class CommentScanner:
    """Asynchronous comment scanner extracting recent comments from TikTok videos.

    Supports dual-mode execution:
    - High-fidelity offline mock mode for hermetic CI/CD testing.
    - Live TikTok Web API / scraping with retry, rate limit handling, and timeout guard.
    - Idempotent database synchronization into SQLAlchemy VideoComment models.
    """

    DEFAULT_USER_AGENT: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )

    def __init__(
        self,
        mock_mode: Optional[bool] = None,
        timeout: float = 15.0,
        rate_limit_delay: float = 0.5,
        max_retries: int = 2,
        fallback_to_mock: bool = False,
        session: Optional[aiohttp.ClientSession] = None,
        browser_adapter: Optional[Any] = None,
    ) -> None:
        self.timeout = timeout
        self.rate_limit_delay = rate_limit_delay
        self.max_retries = max_retries
        self.fallback_to_mock = fallback_to_mock
        self._custom_session = session
        self.browser_adapter = browser_adapter

        if mock_mode is not None:
            self.mock_mode = mock_mode
        else:
            env_val = os.getenv("COMMENT_SCANNER_MOCK", "").lower()
            if env_val in ("0", "false", "no"):
                self.mock_mode = False
            else:
                self.mock_mode = True

    async def scan_comments(self, video_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Scans recent comments for a given video ID or TikTok URL.

        Args:
            video_id: TikTok video identifier or URL (e.g. "tt_pub_101", "7123456789").
            limit: Maximum number of comments to return (default 10).

        Returns:
            List of comment dictionaries containing comment_id, text, user,
            author_name, author_id, timestamp, like_count, reply_count.

        Raises:
            InvalidVideoIdError: If video_id is empty or invalid.
            CommentScannerTimeoutError: If live request exceeds timeout.
            CommentRateLimitError: If TikTok rate limits the scanner.
        """
        clean_id = extract_video_id(video_id)
        if limit <= 0:
            return []

        if self.mock_mode:
            return self._mock_comments(clean_id, limit)

        try:
            return await self._extract_via_tiktok_api(clean_id, limit)
        except Exception as exc:
            if self.fallback_to_mock:
                logger.warning(
                    "Live comment extraction failed (%s); falling back to mock comments for %s",
                    exc,
                    clean_id,
                )
                return self._mock_comments(clean_id, limit)
            raise

    def _mock_comments(self, video_id: str, limit: int) -> List[Dict[str, Any]]:
        """Generates deterministic mock comments for offline testing."""
        comments: List[Dict[str, Any]] = []
        for i in range(limit):
            sample = MOCK_COMMENT_POOL[i % len(MOCK_COMMENT_POOL)]
            cid = f"c_{video_id}_{i + 1}"
            minute = (20 + i) % 60
            comments.append({
                "comment_id": cid,
                "text": sample["text"],
                "user": sample["user"],
                "author_name": sample["author_name"],
                "author_id": sample["author_id"],
                "timestamp": f"2026-11-10T14:{minute:02d}:00Z",
                "like_count": sample["like_count"],
                "reply_count": 0,
            })
        return comments

    async def _extract_via_tiktok_api(self, video_id: str, limit: int) -> List[Dict[str, Any]]:
        """Live extraction from TikTok Web Comment API with retries and rate limit checks."""
        endpoint = (
            f"https://www.tiktok.com/api/comment/list/"
            f"?aid=1988&aweme_id={video_id}&count={min(limit, 50)}&cursor=0"
        )
        headers = {
            "User-Agent": self.DEFAULT_USER_AGENT,
            "Referer": "https://www.tiktok.com/",
            "Accept": "application/json, text/plain, */*",
        }

        session = self._custom_session or aiohttp.ClientSession()
        close_session = self._custom_session is None

        try:
            for attempt in range(self.max_retries + 1):
                try:
                    async with asyncio.timeout(self.timeout):
                        async with session.get(endpoint, headers=headers) as resp:
                            if resp.status == 429:
                                if attempt < self.max_retries:
                                    await asyncio.sleep(self.rate_limit_delay * (2 ** attempt))
                                    continue
                                raise CommentRateLimitError(
                                    f"Rate limited by TikTok API for video {video_id}"
                                )

                            if resp.status == 404:
                                raise VideoNotFoundError(
                                    f"Video {video_id} not found or comments disabled"
                                )

                            if resp.status != 200:
                                raise CommentScannerError(
                                    f"TikTok API returned HTTP {resp.status} for video {video_id}"
                                )

                            payload = await resp.json(content_type=None)
                            if not isinstance(payload, dict):
                                return []

                            status_code = payload.get("status_code", 0)
                            if status_code != 0:
                                status_msg = str(payload.get("status_msg", "API error"))
                                if "rate" in status_msg.lower() or status_code in (10101, 10102):
                                    raise CommentRateLimitError(f"TikTok rate limit: {status_msg}")
                                raise CommentScannerError(
                                    f"TikTok API error ({status_code}): {status_msg}"
                                )

                            raw_comments = payload.get("comments") or []
                            results: List[Dict[str, Any]] = []
                            for rc in raw_comments[:limit]:
                                user_obj = rc.get("user") or {}
                                cid = str(rc.get("cid") or rc.get("id") or f"c_{video_id}_{len(results) + 1}")
                                user_handle = str(
                                    user_obj.get("unique_id")
                                    or user_obj.get("short_id")
                                    or "user_unknown"
                                )
                                author_name = str(user_obj.get("nickname") or user_handle)
                                author_id = str(user_obj.get("uid") or user_handle)
                                create_time = rc.get("create_time")
                                ts_str = (
                                    datetime.fromtimestamp(create_time, tz=timezone.utc).isoformat()
                                    if create_time
                                    else datetime.now(timezone.utc).isoformat()
                                )
                                results.append({
                                    "comment_id": cid,
                                    "text": str(rc.get("text") or ""),
                                    "user": user_handle,
                                    "author_name": author_name,
                                    "author_id": author_id,
                                    "timestamp": ts_str,
                                    "like_count": int(rc.get("digg_count") or 0),
                                    "reply_count": int(rc.get("reply_comment_total") or 0),
                                })
                            return results
                except (asyncio.TimeoutError, TimeoutError, aiohttp.ServerTimeoutError) as exc:
                    if attempt < self.max_retries:
                        await asyncio.sleep(self.rate_limit_delay)
                        continue
                    raise CommentScannerTimeoutError(
                        f"Comment scan timed out after {self.timeout}s for video {video_id}"
                    ) from exc
        finally:
            if close_session:
                await session.close()
        return []

    async def sync_comments_to_db(
        self,
        video_id: str,
        channel_id: str,
        comments: List[Dict[str, Any]],
        session: AsyncSession,
    ) -> List[VideoComment]:
        """Synchronizes scanned comments into SQLAlchemy VideoComment records idempotently.

        Args:
            video_id: Target video ID.
            channel_id: Foreign key ID of the channel owning the video.
            comments: List of comment dicts (from scan_comments).
            session: Active SQLAlchemy AsyncSession.

        Returns:
            List of VideoComment ORM objects corresponding to the comments.
        """
        clean_vid = extract_video_id(video_id)[:100]
        if not isinstance(channel_id, str) or not channel_id.strip():
            raise ValueError("channel_id must be a non-empty string")
        clean_cid = channel_id.strip()[:50]

        if not comments:
            return []

        # 1. Collect valid comment IDs
        clean_cids = [
            str(c.get("comment_id") or "").strip()[:50]
            for c in comments
            if c.get("comment_id")
        ]
        if not clean_cids:
            return []

        # 2. Query existing records in DB to guarantee idempotency
        stmt = select(VideoComment).where(VideoComment.comment_id.in_(clean_cids))
        result = await session.execute(stmt)
        existing_map: Dict[str, VideoComment] = {
            vc.comment_id: vc for vc in result.scalars().all()
        }

        synced_records: List[VideoComment] = []

        for c in comments:
            cid = str(c.get("comment_id") or "").strip()[:50]
            if not cid:
                continue

            if cid in existing_map:
                # Existing record preserved (status & existing intent/replies maintained)
                synced_records.append(existing_map[cid])
            else:
                user_handle = str(c.get("user") or c.get("author_name") or "unknown_user")[:100]
                author_id = str(c.get("author_id") or user_handle)[:100]
                author_name = str(c.get("author_name") or user_handle)[:100]
                text = str(c.get("text") or c.get("comment_text") or "")
                ts = parse_timestamp(c.get("timestamp"))

                new_record = VideoComment(
                    comment_id=cid,
                    channel_id=clean_cid,
                    video_id=clean_vid,
                    author_id=author_id,
                    author_name=author_name,
                    comment_text=text,
                    intent=c.get("intent"),
                    reply_text=c.get("reply_text"),
                    reply_status=c.get("reply_status", "pending"),
                    created_at=ts,
                )
                session.add(new_record)
                existing_map[cid] = new_record  # Prevent duplicate within same batch
                synced_records.append(new_record)

        await session.flush()
        return synced_records
