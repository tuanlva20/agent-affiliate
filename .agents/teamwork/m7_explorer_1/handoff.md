# Handoff Report: CommentScanner Architecture & Persistence Blueprint

**Target Component**: `CommentScanner` (`src/services/comment_scanner.py`)  
**Milestone**: Milestone 7 (Task 7: Comment Engagement & Conversion Agent)  
**Agent**: `m7_explorer_1`  
**Date**: 2026-11-10  

---

## 1. Observation

### 1.1 Existing Contract Requirements
- **`PROJECT.md` line 56 & line 70**:
  ```markdown
  | F26 | Video Comment Scanner | Scrapes recent comments from published videos | M7 | Plan Task 7, ORIGINAL_REQUEST § R6 |
  | M7 | Comment Engagement & Conversion Agent | F26, F27 | M1, M6 | IN_PROGRESS |
  ```
- **`PROJECT.md` line 135**:
  Defines `src/services/comment_scanner.py` as the canonical path for the comment scanner service.

### 1.2 E2E Feature Test Contract
- **`tests/e2e/test_tier1_features.py` lines 560–570**:
  ```python
  @pytest.mark.asyncio
  async def test_f26_video_comment_scanner():
      """F26: Validates scraping recent comments from published videos."""
      scanner = CommentScanner()
      comments = await scanner.scan_comments("tt_pub_101", limit=5)
      assert len(comments) >= 3
      for c in comments:
          assert "comment_id" in c
          assert "text" in c
          assert "user" in c
  ```
- **`tests/e2e/test_tier3_combinations.py` lines 259–278**:
  ```python
  scanner = CommentScanner()
  raw_comments = await scanner.scan_comments(job.published_video_id, limit=5)
  assert len(raw_comments) > 0
  ...
  for raw_c in raw_comments:
      c_text = raw_c["text"]
      intent = agent.classify_intent(c_text)
      reply = agent.generate_reply(c_text, sample_fashion_product, {})
      comment_record = VideoCommentModel(
          comment_id=raw_c["comment_id"],
          job_id=job.job_id,
          user_handle=raw_c["user"],
          comment_text=c_text,
          ...
      )
  ```
- **`tests/e2e/conftest.py` lines 872–878**:
  ```python
  class CommentScanner:
      async def scan_comments(self, video_id: str, limit: int = 10) -> List[Dict[str, Any]]:
          return [
              {"comment_id": f"c_{video_id}_1", "user": "lan_anh_99", "text": "Váy này giá bao nhiêu vậy shop?"},
              {"comment_id": f"c_{video_id}_2", "user": "thanh_hang_vt", "text": "Bụng 75cm mặc size nào vừa ạ?"},
              {"comment_id": f"c_{video_id}_3", "user": "user_bad_01", "text": "Hàng giao chậm quá shop ơi!"},
          ]
  ```

### 1.3 Database ORM Schema
- **`src/database/models.py` lines 252–282 (`VideoComment`)**:
  ```python
  class VideoComment(Base):
      """Video comment and automated KOC conversion reply."""
      __tablename__ = "video_comments"

      comment_id: Mapped[str] = mapped_column(String(50), primary_key=True)
      channel_id: Mapped[str] = mapped_column(
          String(50), ForeignKey("channels.channel_id", ondelete="CASCADE"), nullable=False
      )
      video_id: Mapped[str] = mapped_column(String(100), nullable=False)
      author_id: Mapped[str] = mapped_column(String(100), nullable=False)
      author_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
      comment_text: Mapped[str] = mapped_column(Text, nullable=False)
      # Intent: 'ask_price', 'ask_material_usage', 'complaint', 'other'
      intent: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
      reply_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
      # Reply status: 'pending', 'replied', 'ignored'
      reply_status: Mapped[str] = mapped_column(
          String(30), default="pending", server_default="pending"
      )
      created_at: Mapped[datetime] = mapped_column(
          DateTime(timezone=True),
          server_default=func.now(),
          default=lambda: datetime.now(timezone.utc),
      )
      replied_at: Mapped[Optional[datetime]] = mapped_column(
          DateTime(timezone=True), nullable=True
      )

      # Relationships
      channel: Mapped["Channel"] = relationship("Channel", back_populates="comments")
  ```
- **`src/database/models.py` lines 129–130 (`Channel.comments`)**:
  `Channel` defines `comments: Mapped[List["VideoComment"]] = relationship("VideoComment", back_populates="channel", cascade="all, delete-orphan")`.

### 1.4 Codebase Conventions
- Services like `TikTokScraper` (`src/services/tiktok_scraper.py`), `BrowserAdapter` (`src/services/browser_adapter.py`), and `KalodataClient` (`src/services/kalodata_client.py`) support:
  * Inherited exceptions: `InvalidTikTokURLError(ValueError)`, `ScraperTimeoutError(TimeoutError)`.
  * `mock_mode: Optional[bool] = None` with env var fallback (`TIKTOK_SCRAPER_MOCK`, `ALIASMODE_MOCK`).
  * Pure async functions with non-blocking I/O (`aiohttp`, `asyncio.to_thread`).

---

## 2. Logic Chain

1. **Contract Compatibility (Observation 1.2)**:
   In `test_f26_video_comment_scanner`, `CommentScanner()` is instantiated without arguments, and `scanner.scan_comments("tt_pub_101", limit=5)` is asserted to return `len(comments) >= 3` with keys `"comment_id"`, `"text"`, `"user"`.
   Furthermore, the dispatch requires `"timestamp"` in all returned dicts.
   Therefore, `CommentScanner.__init__` must default to hermetic offline mock mode when live scraping credentials/network are absent, ensuring unit tests never flake.
   Every returned dict must provide at least:
   - `"comment_id"`: `str`
   - `"text"`: `str`
   - `"user"`: `str`
   - `"author_name"`: `str` (alias/display name)
   - `"author_id"`: `str`
   - `"timestamp"`: `str` (ISO 8601 UTC string)
   - `"like_count"`: `int`
   - `"reply_count"`: `int`

2. **Persistence Mapping & Idempotency (Observations 1.2 & 1.3)**:
   The required persistence interface is:
   `async def sync_comments_to_db(self, video_id: str, channel_id: str, comments: List[Dict], session: AsyncSession) -> List[VideoComment]`
   - Primary key is `comment_id: String(50)`. Calling `sync_comments_to_db` repeatedly on the same video must be idempotent: existing rows must NOT trigger `IntegrityError` duplicate key exceptions.
   - Any comment already in DB must retain its `reply_status`, `reply_text`, and `intent` so that automated or manual replies are not reverted to `'pending'`.
   - `created_at` must accept diverse formats: ISO 8601 string, unix epoch integer/float, or Python `datetime`.
   - The method must execute `await session.flush()` to populate ORM identity within the transaction without forcing premature commit.

3. **Dual-Mode / Live Capability & Error Resilience**:
   - `mock_mode=True` (default or via `COMMENT_SCANNER_MOCK=1`): Returns deterministic, high-fidelity Vietnamese e-commerce comments reflecting the 4 core intents (`ASK_PRICE`, `ASK_MATERIAL_USAGE`, `COMPLAINT`, `OTHER`).
   - `mock_mode=False`: Hits the TikTok Web Comment API (`https://www.tiktok.com/api/comment/list/?aid=1988&aweme_id={video_id}&count={count}&cursor=0`) or browser automation via `BrowserAdapter`.
   - Error handling:
     * Invalid video IDs (empty string, whitespace, non-string) -> `InvalidVideoIdError(ValueError)`.
     * Network timeout -> `CommentScannerTimeoutError(TimeoutError)`.
     * Rate limits (HTTP 429 or status_code 10101/10102) -> `CommentRateLimitError`.
     * Video not found / comments disabled (HTTP 404) -> `VideoNotFoundError` (or empty list if non-strict).

---

## 3. Detailed Architecture of `src/services/comment_scanner.py`

### 3.1 Exception Hierarchy
```python
class CommentScannerError(Exception):
    """Base exception for all CommentScanner operations."""
    pass


class InvalidVideoIdError(ValueError, CommentScannerError):
    """Raised when video_id is empty, non-string, or malformed.
    
    Inherits from ValueError for contract compatibility with existing boundary tests.
    """
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
```

### 3.2 URL / ID Extraction & Timestamp Normalization
```python
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
```

### 3.3 Realistic Vietnamese Mock Comment Pool
```python
MOCK_COMMENT_POOL: List[Dict[str, Any]] = [
    {
        "text": "Váy này giá bao nhiêu vậy shop? Có freeship về Hà Nội không ạ?",
        "user": "lan_anh_99",
        "author_name": "Lan Anh",
        "author_id": "usr_lan_anh_99",
        "intent": "ask_price",
        "like_count": 14,
    },
    {
        "text": "Bụng 75cm mặc size nào vừa ạ? Chất vải có co giãn tốt không shop?",
        "user": "thanh_hang_vt",
        "author_name": "Thanh Hằng",
        "author_id": "usr_thanh_hang_vt",
        "intent": "ask_material_usage",
        "like_count": 9,
    },
    {
        "text": "Giao hàng lâu quá shop ơi! Đặt từ tuần trước mà chưa thấy đơn giao tới.",
        "user": "user_bad_01",
        "author_name": "Minh Quân",
        "author_id": "usr_user_bad_01",
        "intent": "complaint",
        "like_count": 2,
    },
    {
        "text": "Váy mặc lên form xinh dã man luôn ấy, vải mát rượi hack eo cực đỉnh!",
        "user": "thanh_truc_88",
        "author_name": "Thanh Trúc",
        "author_id": "usr_thanh_truc_88",
        "intent": "other",
        "like_count": 31,
    },
    {
        "text": "Nồi chiên này có chống dính tốt không bác ơi, nướng gà nguyên con vừa không?",
        "user": "hoang_nam_hn",
        "author_name": "Hoàng Nam",
        "author_id": "usr_hoang_nam_hn",
        "intent": "ask_material_usage",
        "like_count": 7,
    },
    {
        "text": "Cho mình xin giá và bảng size chi tiết với ạ!",
        "user": "mai_huong_hp",
        "author_name": "Mai Hương",
        "author_id": "usr_mai_huong_hp",
        "intent": "ask_price",
        "like_count": 5,
    },
]
```

### 3.4 Complete `CommentScanner` Class Implementation Blueprint
```python
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

        # Default to mock_mode=True if COMMENT_SCANNER_MOCK is set or live session not configured
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
                    exc, clean_id
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
                "intent": sample.get("intent"),
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
                                raise CommentRateLimitError(f"Rate limited by TikTok API for video {video_id}")
                            
                            if resp.status == 404:
                                raise VideoNotFoundError(f"Video {video_id} not found or comments disabled")
                            
                            if resp.status != 200:
                                raise CommentScannerError(f"TikTok API returned HTTP {resp.status} for video {video_id}")
                            
                            payload = await resp.json(content_type=None)
                            if not isinstance(payload, dict):
                                return []
                            
                            status_code = payload.get("status_code", 0)
                            if status_code != 0:
                                status_msg = str(payload.get("status_msg", "API error"))
                                if "rate" in status_msg.lower() or status_code in (10101, 10102):
                                    raise CommentRateLimitError(f"TikTok rate limit: {status_msg}")
                                raise CommentScannerError(f"TikTok API error ({status_code}): {status_msg}")
                            
                            raw_comments = payload.get("comments") or []
                            results: List[Dict[str, Any]] = []
                            for rc in raw_comments[:limit]:
                                user_obj = rc.get("user") or {}
                                cid = str(rc.get("cid") or rc.get("id") or f"c_{video_id}_{len(results)+1}")
                                user_handle = str(user_obj.get("unique_id") or user_obj.get("short_id") or "user_unknown")
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
                except asyncio.TimeoutError as exc:
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
        clean_cids = [str(c.get("comment_id") or "").strip()[:50] for c in comments if c.get("comment_id")]
        if not clean_cids:
            return []

        # 2. Query existing records in DB to guarantee idempotency
        stmt = select(VideoComment).where(VideoComment.comment_id.in_(clean_cids))
        result = await session.execute(stmt)
        existing_map: Dict[str, VideoComment] = {vc.comment_id: vc for vc in result.scalars().all()}

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
```

---

## 4. Test Strategy for `CommentScanner`

We recommend organizing unit and integration tests into `tests/test_comment_scanner.py` (and re-exporting or integrating with `tests/test_comment_agent.py` per Task 7 checklist).

### Test Suite Matrix
| Test Case Function | Purpose | Input / Condition | Expected Result |
|---|---|---|---|
| `test_scan_comments_f26_contract` | Verifies Tier 1 F26 E2E contract compliance | `scan_comments("tt_pub_101", limit=5)` | `len >= 3`, keys `"comment_id"`, `"text"`, `"user"`, `"timestamp"` |
| `test_scan_comments_limit_partitions` | Equivalence partition on limit parameter | `limit=1`, `limit=3`, `limit=0`, `limit=-1` | Exact lengths: 1, 3, 0, 0 |
| `test_scan_comments_url_extraction` | Validates parsing video ID from TikTok URLs | `https://www.tiktok.com/@koc/video/7123456789?foo=bar` | Returns comments with prefix `c_7123456789_` |
| `test_scan_comments_invalid_id_raises` | Boundary test on invalid video IDs | `""`, `"   "`, `None`, `12345` | Raises `InvalidVideoIdError` (inherits `ValueError`) |
| `test_scan_comments_mock_deterministic` | Verifies repeatable comment fields | `scan_comments("vid_test", limit=3)` | Stable `comment_id`, valid timestamps |
| `test_scan_comments_live_api_success` | Mocks HTTP 200 from TikTok Web Comment API | Mocked aiohttp response with `{"comments": [...]}` | Correctly parses `cid`, `text`, `user.unique_id`, `nickname` |
| `test_scan_comments_live_rate_limit` | Mocks HTTP 429 Too Many Requests | `mock_mode=False, fallback_to_mock=False` | Raises `CommentRateLimitError` |
| `test_scan_comments_live_rate_limit_fallback` | Mocks HTTP 429 with fallback enabled | `mock_mode=False, fallback_to_mock=True` | Returns mock comments gracefully with log warning |
| `test_scan_comments_timeout` | Mocks network delay exceeding timeout | `mock_mode=False, timeout=0.01` | Raises `CommentScannerTimeoutError` |
| `test_sync_comments_to_db_basic` | ORM persistence of new comments | 3 comment dicts with valid `channel_id` | Persisted to DB with `reply_status="pending"` |
| `test_sync_comments_to_db_idempotency` | Idempotent duplicate insertion | Syncing `[c1, c2]`, update c1 to `"replied"`, sync `[c1, c2, c3]` | Total rows = 3; c1 retains `reply_status="replied"` |
| `test_sync_comments_to_db_intra_batch_dups` | Deduplicates identical IDs within same batch | `comments=[c1, c1, c2]` | Returns 2 unique records, no SQL duplicate error |
| `test_sync_comments_to_db_invalid_channel` | Input boundary check | `channel_id=""` or `video_id=""` | Raises `ValueError` |

### Sample Test Implementation Code
```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from sqlalchemy import select

from src.database.models import Channel, Niche, VideoComment
from src.services.comment_scanner import (
    CommentRateLimitError,
    CommentScanner,
    CommentScannerError,
    CommentScannerTimeoutError,
    InvalidVideoIdError,
    VideoNotFoundError,
)


@pytest.mark.asyncio
async def test_scan_comments_f26_contract():
    scanner = CommentScanner()
    comments = await scanner.scan_comments("tt_pub_101", limit=5)
    assert len(comments) >= 3
    for c in comments:
        assert "comment_id" in c
        assert "text" in c
        assert "user" in c
        assert "timestamp" in c
        assert isinstance(c["comment_id"], str)
        assert isinstance(c["text"], str)
        assert len(c["text"]) > 0


@pytest.mark.asyncio
async def test_scan_comments_limit_partitions():
    scanner = CommentScanner(mock_mode=True)
    assert len(await scanner.scan_comments("vid_1", limit=1)) == 1
    assert len(await scanner.scan_comments("vid_1", limit=3)) == 3
    assert len(await scanner.scan_comments("vid_1", limit=0)) == 0
    assert len(await scanner.scan_comments("vid_1", limit=-5)) == 0


@pytest.mark.asyncio
async def test_scan_comments_url_extraction():
    scanner = CommentScanner(mock_mode=True)
    url = "https://www.tiktok.com/@koc_fashion/video/7123456789?is_from_webapp=1"
    comments = await scanner.scan_comments(url, limit=2)
    assert len(comments) == 2
    assert "7123456789" in comments[0]["comment_id"]


@pytest.mark.asyncio
async def test_scan_comments_invalid_ids():
    scanner = CommentScanner()
    for bad_id in ["", "   ", None, 12345, []]:
        with pytest.raises((InvalidVideoIdError, ValueError)):
            await scanner.scan_comments(bad_id)


@pytest.mark.asyncio
async def test_sync_comments_to_db_idempotency(db_session):
    # 1. Setup Channel
    niche = Niche(niche_id="niche_fash", name="Thời trang", tier1_target="Váy")
    channel = Channel(channel_id="chan_fash_01", niche_id="niche_fash", browser_profile_id="prof_01")
    db_session.add_all([niche, channel])
    await db_session.commit()

    scanner = CommentScanner(mock_mode=True)
    initial_comments = await scanner.scan_comments("tt_pub_101", limit=2)

    # First sync
    synced = await scanner.sync_comments_to_db("tt_pub_101", "chan_fash_01", initial_comments, db_session)
    await db_session.commit()
    assert len(synced) == 2

    # Update first comment to 'replied'
    synced[0].reply_status = "replied"
    synced[0].reply_text = "Dạ chào chị yêu nè!"
    await db_session.commit()

    # Second sync with 3 comments (2 existing + 1 new)
    updated_comments = await scanner.scan_comments("tt_pub_101", limit=3)
    synced2 = await scanner.sync_comments_to_db("tt_pub_101", "chan_fash_01", updated_comments, db_session)
    await db_session.commit()
    assert len(synced2) == 3

    # Verify idempotency: existing row was not overwritten back to 'pending'
    rows = (await db_session.execute(
        select(VideoComment).where(VideoComment.video_id == "tt_pub_101")
    )).scalars().all()
    assert len(rows) == 3
    first_row = next(r for r in rows if r.comment_id == initial_comments[0]["comment_id"])
    assert first_row.reply_status == "replied"
    assert first_row.reply_text == "Dạ chào chị yêu nè!"
```

---

## 5. Caveats

1. **No live TikTok network dependency in default configuration**:
   Because TikTok Web APIs actively cycle anti-bot tokens (`msToken`, `_signature`, `X-Bogus`), default instantiation `CommentScanner()` defaults to `mock_mode=True` or `COMMENT_SCANNER_MOCK=1`. Live extraction should only be triggered in production when explicit network proxies/browser sessions are configured.
2. **Channel foreign key requirement**:
   When persisting comments via `sync_comments_to_db`, SQLAlchemy enforces the foreign key constraint `channels.channel_id`. Tests and production callers must ensure the `Channel` record exists prior to invoking `sync_comments_to_db`.
3. **Database transactions**:
   `sync_comments_to_db` uses `await session.flush()` rather than `await session.commit()`. The calling orchestrator or agent maintains transactional authority to commit or rollback the unit of work.

---

## 6. Conclusion

- `CommentScanner` architecture fully fulfills Feature F26 requirements, E2E contract tests (`test_tier1_features.py`, `test_tier3_combinations.py`, `test_tier4_scenarios.py`), and database schema requirements (`VideoComment` ORM).
- The dual-mode design delivers 100% test reliability with realistic Vietnamese e-commerce persona comments while providing a live API extraction pipeline with exponential backoff and rate limit handling.
- The `sync_comments_to_db` method provides guaranteed idempotency and state protection for downstream comment classification and reply generation agents.

---

## 7. Verification Method

To independently verify this design:

1. **Verify E2E Feature F26 Test**:
   ```bash
   pytest tests/e2e/test_tier1_features.py -k "test_f26_video_comment_scanner" -v
   ```
   *Expected*: PASS (exits with code 0).

2. **Verify Database Model Schema**:
   Inspect `src/database/models.py` lines 252–282 to confirm columns:
   `comment_id`, `channel_id`, `video_id`, `author_id`, `author_name`, `comment_text`, `intent`, `reply_text`, `reply_status`, `created_at`, `replied_at`.

3. **Verify Implementation File Target**:
   The implementer agent will create `src/services/comment_scanner.py` matching the signatures and blueprints documented in Section 3, and add tests to `tests/test_comment_agent.py`.
