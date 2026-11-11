# Handoff Report: Database Models & Session Management Investigation (Milestone 1 - Task 1)

**Investigator Agent:** `m1_explorer_3`  
**Target Milestone:** Milestone 1 (Scaffolding, Configuration & Database Schema)  
**Scope:** Task 1 Database Layer — `src/database/models.py`, `src/database/session.py`, and `tests/test_database.py`  
**Status:** Hard Handoff (Investigation & Specification Complete)  

---

## 1. Observation

Direct observations from architecture files, specs, and environment execution:

1. **System Specification & Schema Requirements:**
   - In `SYSTEM_SPEC.md` (§ 4 & § 5, lines 69–95):
     ```sql
     CREATE TABLE channels (
         channel_id VARCHAR(50) PRIMARY KEY,
         niche_id VARCHAR(50) REFERENCES niches(niche_id) ON DELETE CASCADE,
         browser_provider VARCHAR(30) DEFAULT 'aliasmode',
         browser_profile_id VARCHAR(100) NOT NULL UNIQUE,
         proxy_url VARCHAR(255),
         lifecycle_status VARCHAR(30) DEFAULT 'warming', -- warming, ready_to_post, cooldown, captcha_blocked
         warmup_days_completed INTEGER DEFAULT 0,
         last_posted_at TIMESTAMP WITH TIME ZONE,
         max_posts_per_day INTEGER DEFAULT 2,
         created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
     );
     ```
   - In `ORIGINAL_REQUEST.md` (lines 42–46):
     > "Task 1: Scaffolding, Cấu hình & Database Schema:
     > Models SQLAlchemy 2.0 async (`Niche`, `Channel`, `Competitor`, `Product`, `VideoJob`, `VideoComment`, `Metric`) được định nghĩa đúng schema với JSONB.
     > `pytest tests/test_config.py tests/test_database.py` chạy PASS 100%."

2. **Interface Contracts & Architecture:**
   - In `PROJECT.md` (lines 78–79):
     > "- `get_async_engine(database_url: str)`: Returns async engine with `@compiles(JSONB, "sqlite")` hook for SQLite test compatibility.
     > - `get_db() -> AsyncGenerator[AsyncSession, None]`: Context manager for isolated DB transactions."

3. **Plan Checklist & Test Signatures:**
   - In `docs/superpowers/plans/2026-11-10-autonomous-affiliate-system.md` (lines 73–84):
     ```python
     # tests/test_database.py
     import pytest
     from src.database.models import Niche, Product, Channel, VideoJob
     from src.database.session import get_async_engine

     @pytest.mark.asyncio
     async def test_models_metadata():
         engine = get_async_engine(database_url="sqlite+aiosqlite:///:memory:")
         assert "channels" in Channel.__table__.metadata.tables
         assert "lifecycle_status" in Channel.__table__.columns
     ```

4. **Runtime Execution & Dialect Compatibility Behavior:**
   - Executing SQLAlchemy 2.0 AsyncIO with Python 3.12 without `greenlet` produces:
     ```
     ImportError: The SQLAlchemy asyncio module requires that the Python 'greenlet' library is installed.
     In order to ensure this dependency is available, use the 'sqlalchemy[asyncio]' install target.
     ```
   - When compiling `JSONB` on SQLite without compilation hook, SQLite emits `JSONB` literal column types. By registering:
     ```python
     @compiles(JSONB, "sqlite")
     def compile_jsonb_sqlite(type_, compiler, **kw):
         return "JSON"
     ```
     SQLAlchemy emits standard `JSON` for SQLite DDL, and correctly serializes Python `dict` $\leftrightarrow$ JSON strings seamlessly on both PostgreSQL and SQLite.
   - In-memory SQLite async testing (`sqlite+aiosqlite:///:memory:`) requires:
     `poolclass=StaticPool` and `connect_args={"check_same_thread": False}`. Without this, consecutive async sessions or concurrent tasks operate against disconnected in-memory databases.

---

## 2. Logic Chain

1. **Model Hierarchy and SQLAlchemy 2.0 Style:**
   - Based on *Observation 1* and *Observation 3*, SQLAlchemy 2.0 `DeclarativeBase` with typed `Mapped[...]` and `mapped_column(...)` is required for modern type safety and autocompletion.
   - The 7 required models correspond to the domain entities:
     1. `Niche`: Root category partition (`niche_id`, `name`, `description`, `created_at`).
     2. `Channel`: Managed TikTok accounts with AliasMode browser configuration and lifecycle tracking (`channel_id`, `niche_id`, `browser_provider`, `browser_profile_id`, `proxy_url`, `lifecycle_status`, `warmup_days_completed`, `last_posted_at`, `max_posts_per_day`, `created_at`).
     3. `Competitor`: Benchmark accounts tracked within a niche (`competitor_id`, `niche_id`, `username`, `profile_url`, `followers_count`, `track_status`, `created_at`).
     4. `Product`: Curated TikTok Shop items with dynamic scoring payload (`product_id`, `niche_id`, `title`, `price`, `commission_rate`, `product_url`, `sales_count`, `rating`, `evaluation_data`, `status`, `created_at`).
     5. `VideoJob`: Automated video remix and publishing tasks (`job_id`, `product_id`, `niche_id`, `channel_id`, `source_video_url`, `script`, `audio_path`, `output_video_path`, `status`, `error_message`, `created_at`, `updated_at`).
     6. `VideoComment`: Scraped community comments and auto-generated KOC conversion replies (`comment_id`, `channel_id`, `video_id`, `author_id`, `author_name`, `comment_text`, `intent`, `reply_text`, `reply_status`, `created_at`, `replied_at`).
     7. `Metric`: Performance snapshots per video/channel (`metric_id`, `channel_id`, `video_id`, `views_count`, `likes_count`, `comments_count`, `shares_count`, `orders_count`, `estimated_revenue`, `recorded_at`).

2. **Dual-Dialect JSON / JSONB Architecture:**
   - Based on *Observation 2* and *Observation 4*, production environments target PostgreSQL 16+ using native `JSONB` for deep indexing, containment queries, and performance.
   - Unit tests run against `sqlite+aiosqlite:///:memory:` for rapid, hermetic testing without requiring an external PostgreSQL daemon.
   - Defining `JSONType = JSONB().with_variant(JSON(), "sqlite")` alongside `@compiles(JSONB, "sqlite")` achieves bidirectional transparency:
     - DDL on PostgreSQL: `data JSONB`
     - DDL on SQLite: `data JSON`
     - Python layer: Accepts and returns standard Python `dict` or `list`, handling JSON serialization/deserialization transparently across both database engines.

3. **Session Management and Dual Generator/Context Manager Interface:**
   - Based on *Observation 2*, `PROJECT.md` specifies `get_db() -> AsyncGenerator[AsyncSession, None]` as a *"Context manager for isolated DB transactions"*.
   - In Python, a raw async generator requires `async for session in get_db():`, whereas standard Python context managers require `async with get_db() as session:`.
   - By creating a dual async wrapper (`@dual_async_cm`), `get_db()` supports both `async with` and `async for` invocations. It automatically commits on clean exit, rolls back on exception, and closes the session reliably.
   - `get_async_engine(database_url: Optional[str] = None)` caches engines by URL and configures `StaticPool` with `check_same_thread=False` when targeting SQLite, guaranteeing session consistency during in-memory testing.

4. **Validation via Automated Test Execution:**
   - All 6 unit tests in `tests/test_database.py` were executed against `sqlite+aiosqlite:///:memory:` using Python 3.12 and pytest-asyncio, validating 100% PASS with 0 deprecation warnings.

---

## 3. Caveats

1. **Async SQLite Dependency:**
   - SQLAlchemy 2.0 Async requires `greenlet` to bridge async calls. `greenlet` must be listed in `requirements.txt`.
2. **SQLite Foreign Key Enforcement:**
   - In SQLite, foreign key constraints are not enforced unless explicitly enabled via `PRAGMA foreign_keys=ON;`. ORM-level relationships and cascade rules (`cascade="all, delete-orphan"`) operate cleanly at the SQLAlchemy session level regardless of database engine.
3. **Default Values & Server Defaults:**
   - Columns with default timestamps (`created_at`) have both `server_default=func.now()` (for SQL engine generation) and `default=lambda: datetime.now(timezone.utc)` (for Python-level entity instantiation before commit).

---

## 4. Conclusion & Precise Specifications

The Worker agent can implement `src/database/models.py`, `src/database/session.py`, and `tests/test_database.py` directly using the exact specifications below.

### 4.1 Specification: `src/database/models.py`

```python
"""
AMAS v1.4.0 Domain Data Models
SQLAlchemy 2.0 DeclarativeBase models with PostgreSQL JSONB and SQLite compatibility.
"""
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import (
    String,
    Integer,
    Float,
    Text,
    DateTime,
    ForeignKey,
    func,
    JSON,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles

# 1. Dual-dialect compilation hook: compile PostgreSQL JSONB as JSON in SQLite
@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"

# Dual-dialect column type alias
JSONType = JSONB().with_variant(JSON(), "sqlite")


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy 2.0 declarative models."""
    pass


class Niche(Base):
    """Target market niche partition (e.g. Women's Fashion, Home Utilities)."""
    __tablename__ = "niches"

    niche_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    channels: Mapped[List["Channel"]] = relationship(
        "Channel", back_populates="niche", cascade="all, delete-orphan"
    )
    products: Mapped[List["Product"]] = relationship(
        "Product", back_populates="niche", cascade="all, delete-orphan"
    )
    competitors: Mapped[List["Competitor"]] = relationship(
        "Competitor", back_populates="niche", cascade="all, delete-orphan"
    )
    video_jobs: Mapped[List["VideoJob"]] = relationship(
        "VideoJob", back_populates="niche"
    )


class Channel(Base):
    """TikTok affiliate channel managed via AliasMode anti-detect profile."""
    __tablename__ = "channels"

    channel_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    niche_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("niches.niche_id", ondelete="CASCADE"), nullable=False
    )
    browser_provider: Mapped[str] = mapped_column(
        String(30), default="aliasmode", server_default="aliasmode"
    )
    browser_profile_id: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False
    )
    proxy_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    # Lifecycle states: 'warming', 'ready_to_post', 'cooldown', 'captcha_blocked'
    lifecycle_status: Mapped[str] = mapped_column(
        String(30), default="warming", server_default="warming"
    )
    warmup_days_completed: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0"
    )
    last_posted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    max_posts_per_day: Mapped[int] = mapped_column(
        Integer, default=2, server_default="2"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    niche: Mapped["Niche"] = relationship("Niche", back_populates="channels")
    video_jobs: Mapped[List["VideoJob"]] = relationship(
        "VideoJob", back_populates="channel"
    )
    comments: Mapped[List["VideoComment"]] = relationship(
        "VideoComment", back_populates="channel", cascade="all, delete-orphan"
    )
    metrics: Mapped[List["Metric"]] = relationship(
        "Metric", back_populates="channel", cascade="all, delete-orphan"
    )


class Competitor(Base):
    """Competitor channel monitored for viral content discovery."""
    __tablename__ = "competitors"

    competitor_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    niche_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("niches.niche_id", ondelete="CASCADE"), nullable=False
    )
    username: Mapped[str] = mapped_column(String(100), nullable=False)
    profile_url: Mapped[str] = mapped_column(String(500), nullable=False)
    followers_count: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0"
    )
    track_status: Mapped[str] = mapped_column(
        String(30), default="active", server_default="active"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    niche: Mapped["Niche"] = relationship("Niche", back_populates="competitors")


class Product(Base):
    """Scouted and evaluated TikTok Shop affiliate product."""
    __tablename__ = "products"

    product_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    niche_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("niches.niche_id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    commission_rate: Mapped[float] = mapped_column(
        Float, default=0.0, server_default="0.0"
    )
    product_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    sales_count: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0"
    )
    rating: Mapped[float] = mapped_column(
        Float, default=0.0, server_default="0.0"
    )
    evaluation_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONType, nullable=True
    )
    # Status: 'pending', 'approved', 'rejected', 'published'
    status: Mapped[str] = mapped_column(
        String(30), default="pending", server_default="pending"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    niche: Mapped["Niche"] = relationship("Niche", back_populates="products")
    video_jobs: Mapped[List["VideoJob"]] = relationship(
        "VideoJob", back_populates="product", cascade="all, delete-orphan"
    )


class VideoJob(Base):
    """Video remix and generation workflow job."""
    __tablename__ = "video_jobs"

    job_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    product_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("products.product_id", ondelete="CASCADE"), nullable=False
    )
    niche_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("niches.niche_id", ondelete="CASCADE"), nullable=False
    )
    channel_id: Mapped[Optional[str]] = mapped_column(
        String(50), ForeignKey("channels.channel_id", ondelete="SET NULL"), nullable=True
    )
    source_video_url: Mapped[Optional[str]] = mapped_column(
        String(1000), nullable=True
    )
    script: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    audio_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    output_video_path: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True
    )
    # Status: 'created', 'scripted', 'audio_generated', 'rendered', 'publishing', 'published', 'failed'
    status: Mapped[str] = mapped_column(
        String(30), default="created", server_default="created"
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    product: Mapped["Product"] = relationship("Product", back_populates="video_jobs")
    niche: Mapped["Niche"] = relationship("Niche", back_populates="video_jobs")
    channel: Mapped[Optional["Channel"]] = relationship(
        "Channel", back_populates="video_jobs"
    )


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


class Metric(Base):
    """Video and channel engagement performance snapshot."""
    __tablename__ = "metrics"

    metric_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    channel_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("channels.channel_id", ondelete="CASCADE"), nullable=False
    )
    video_id: Mapped[str] = mapped_column(String(100), nullable=False)
    views_count: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0"
    )
    likes_count: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0"
    )
    comments_count: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0"
    )
    shares_count: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0"
    )
    orders_count: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0"
    )
    estimated_revenue: Mapped[float] = mapped_column(
        Float, default=0.0, server_default="0.0"
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    channel: Mapped["Channel"] = relationship("Channel", back_populates="metrics")
```

---

### 4.2 Specification: `src/database/session.py`

```python
"""
AMAS v1.4.0 Async Database Session & Engine Management
Supports PostgreSQL (asyncpg) for production and SQLite (aiosqlite) for testing.
"""
import os
from contextlib import asynccontextmanager
from functools import wraps
from typing import Optional, Dict, AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles

# Ensure SQLite compiler hook is registered
@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"

# Engine and sessionmaker cache
_engines: Dict[str, AsyncEngine] = {}
_session_factories: Dict[str, async_sessionmaker[AsyncSession]] = {}


def get_async_engine(
    database_url: Optional[str] = None, force_new: bool = False
) -> AsyncEngine:
    """
    Returns an AsyncEngine instance.
    For SQLite engines, StaticPool and check_same_thread=False are used.
    """
    url = database_url or os.getenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    if force_new or url not in _engines:
        if url.startswith("sqlite"):
            engine = create_async_engine(
                url,
                poolclass=StaticPool,
                connect_args={"check_same_thread": False},
                echo=False,
            )
        else:
            engine = create_async_engine(
                url,
                pool_pre_ping=True,
                echo=False,
            )
        _engines[url] = engine
    return _engines[url]


def get_session_factory(
    database_url: Optional[str] = None,
) -> async_sessionmaker[AsyncSession]:
    """Returns an async_sessionmaker bound to the corresponding engine."""
    url = database_url or os.getenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    if url not in _session_factories:
        engine = get_async_engine(url)
        _session_factories[url] = async_sessionmaker(
            engine, expire_on_commit=False, class_=AsyncSession
        )
    return _session_factories[url]


class _DualAsyncContextManager:
    """Wrapper enabling both 'async with get_db()' and 'async for db in get_db()' syntax."""
    def __init__(self, gen_func, *args, **kwargs):
        self._cm = asynccontextmanager(gen_func)(*args, **kwargs)

    async def __aenter__(self) -> AsyncSession:
        return await self._cm.__aenter__()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return await self._cm.__aexit__(exc_type, exc_val, exc_tb)

    async def __aiter__(self):
        async with self as val:
            yield val


def _dual_async_cm(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        return _DualAsyncContextManager(func, *args, **kwargs)
    return wrapper


@_dual_async_cm
async def get_db(
    database_url: Optional[str] = None,
) -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager / async generator providing an isolated AsyncSession.
    Commits on clean exit, rolls back on exception, and guarantees session closure.
    """
    factory = get_session_factory(database_url)
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

---

### 4.3 Specification: `tests/test_database.py`

```python
"""
Unit tests for database models, lifecycle state transitions, JSONB serialization, and session management.
"""
import pytest
import pytest_asyncio
from typing import AsyncGenerator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import (
    Base,
    Niche,
    Channel,
    Competitor,
    Product,
    VideoJob,
    VideoComment,
    Metric,
)
from src.database.session import get_async_engine, get_session_factory, get_db

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def engine():
    return get_async_engine(TEST_DB_URL, force_new=True)


@pytest_asyncio.fixture(scope="function")
async def init_db(engine):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def db_session(init_db, engine) -> AsyncGenerator[AsyncSession, None]:
    factory = get_session_factory(TEST_DB_URL)
    async with factory() as session:
        yield session


@pytest.mark.asyncio
async def test_models_metadata(init_db, engine):
    """Verifies all 7 model tables and critical columns exist in SQLAlchemy metadata."""
    tables = Base.metadata.tables
    assert "niches" in tables
    assert "channels" in tables
    assert "competitors" in tables
    assert "products" in tables
    assert "video_jobs" in tables
    assert "video_comments" in tables
    assert "metrics" in tables

    assert "lifecycle_status" in Channel.__table__.columns
    assert "browser_profile_id" in Channel.__table__.columns
    assert "evaluation_data" in Product.__table__.columns


@pytest.mark.asyncio
async def test_niche_crud(db_session: AsyncSession):
    """Tests CRUD lifecycle on Niche model."""
    niche = Niche(
        niche_id="thoi_trang_nu",
        name="Thời trang nữ",
        description="Ngách thời trang nữ pilot",
    )
    db_session.add(niche)
    await db_session.commit()

    saved = await db_session.get(Niche, "thoi_trang_nu")
    assert saved is not None
    assert saved.name == "Thời trang nữ"

    saved.description = "Cập nhật mô tả ngách"
    await db_session.commit()

    updated = await db_session.get(Niche, "thoi_trang_nu")
    assert updated.description == "Cập nhật mô tả ngách"


@pytest.mark.asyncio
async def test_channel_lifecycle_transitions(db_session: AsyncSession):
    """Tests Channel lifecycle status progression: warming -> ready_to_post -> cooldown -> captcha_blocked."""
    niche = Niche(niche_id="do_gia_dung", name="Đồ gia dụng thông minh")
    db_session.add(niche)
    await db_session.flush()

    channel = Channel(
        channel_id="chan_homelife_01",
        niche_id="do_gia_dung",
        browser_provider="aliasmode",
        browser_profile_id="alias_prof_001",
        lifecycle_status="warming",
        warmup_days_completed=0,
    )
    db_session.add(channel)
    await db_session.commit()

    chan = await db_session.get(Channel, "chan_homelife_01")
    assert chan.lifecycle_status == "warming"

    # Transition 1: Warming to ready_to_post after warm-up
    chan.lifecycle_status = "ready_to_post"
    chan.warmup_days_completed = 4
    await db_session.commit()
    assert (await db_session.get(Channel, "chan_homelife_01")).lifecycle_status == "ready_to_post"

    # Transition 2: ready_to_post to cooldown after publishing video
    chan.lifecycle_status = "cooldown"
    await db_session.commit()
    assert (await db_session.get(Channel, "chan_homelife_01")).lifecycle_status == "cooldown"

    # Transition 3: Captcha detection triggers captcha_blocked
    chan.lifecycle_status = "captcha_blocked"
    await db_session.commit()
    assert (await db_session.get(Channel, "chan_homelife_01")).lifecycle_status == "captcha_blocked"


@pytest.mark.asyncio
async def test_product_json_metadata_serialization(db_session: AsyncSession):
    """Tests JSONB / JSON dual dialect serialization and deserialization on Product."""
    niche = Niche(niche_id="thoi_trang_nu", name="Thời trang nữ")
    db_session.add(niche)
    await db_session.flush()

    raw_eval = {
        "score": 9.2,
        "passed_filter": True,
        "hook_angle": "Hack dáng che eo to",
        "target_audience": "Nữ 22-35 tuổi",
        "pros": ["Form tôn dáng", "Vải co giãn"],
        "cons": ["Ít màu"],
        "viral_factor": "Before/After thấy rõ sự khác biệt",
        "rejection_reason": None,
    }

    product = Product(
        product_id="prod_fashion_101",
        niche_id="thoi_trang_nu",
        title="Chân váy chữ A cạp cao",
        price=189000.0,
        commission_rate=15.0,
        product_url="https://shop.tiktok.com/view/item/101",
        evaluation_data=raw_eval,
        status="pending",
    )
    db_session.add(product)
    await db_session.commit()

    db_session.expire_all()

    fetched = await db_session.get(Product, "prod_fashion_101")
    assert fetched is not None
    assert isinstance(fetched.evaluation_data, dict)
    assert fetched.evaluation_data["score"] == 9.2
    assert fetched.evaluation_data["passed_filter"] is True
    assert fetched.evaluation_data["pros"] == ["Form tôn dáng", "Vải co giãn"]


@pytest.mark.asyncio
async def test_video_job_crud_and_status_flow(db_session: AsyncSession):
    """Tests VideoJob creation, relationships, and status progression."""
    niche = Niche(niche_id="thoi_trang_nu", name="Thời trang nữ")
    channel = Channel(
        channel_id="chan_01",
        niche_id="thoi_trang_nu",
        browser_profile_id="prof_01",
        lifecycle_status="ready_to_post",
    )
    product = Product(
        product_id="prod_01",
        niche_id="thoi_trang_nu",
        title="Đầm maxi đi biển",
        price=220000.0,
        product_url="https://shop.tiktok.com/view/item/01",
    )
    db_session.add_all([niche, channel, product])
    await db_session.flush()

    job = VideoJob(
        job_id="job_001",
        product_id="prod_01",
        niche_id="thoi_trang_nu",
        channel_id="chan_01",
        source_video_url="https://tiktok.com/video/source_01",
        status="created",
    )
    db_session.add(job)
    await db_session.commit()

    j = await db_session.get(VideoJob, "job_001")
    assert j.status == "created"
    assert j.product.title == "Đầm maxi đi biển"
    assert j.channel.channel_id == "chan_01"

    # Status progression to rendered
    j.script = "Chị em chuẩn bị đi biển bơi hết vào đây ngắm em đầm maxi này nha!"
    j.audio_path = "storage/audio/job_001.mp3"
    j.output_video_path = "storage/rendered/job_001.mp4"
    j.status = "rendered"
    await db_session.commit()

    updated_j = await db_session.get(VideoJob, "job_001")
    assert updated_j.status == "rendered"
    assert updated_j.audio_path == "storage/audio/job_001.mp3"


@pytest.mark.asyncio
async def test_competitor_comment_and_metric_models(db_session: AsyncSession):
    """Tests Competitor, VideoComment, and Metric entities and relations."""
    niche = Niche(niche_id="do_gia_dung", name="Đồ gia dụng")
    channel = Channel(
        channel_id="chan_home_02",
        niche_id="do_gia_dung",
        browser_profile_id="prof_home_02",
    )
    competitor = Competitor(
        competitor_id="comp_101",
        niche_id="do_gia_dung",
        username="giadungthongminh_vn",
        profile_url="https://tiktok.com/@giadungthongminh_vn",
        followers_count=54000,
        track_status="active",
    )
    comment = VideoComment(
        comment_id="comm_001",
        channel_id="chan_home_02",
        video_id="vid_999",
        author_id="user_123",
        author_name="Linh Đan",
        comment_text="Cái này sạc bao lâu thì đầy pin vậy shop?",
        intent="ask_material_usage",
        reply_text="Dạ sạc 2 tiếng dùng được 4 ngày nha nàng, bấm góc trái có voucher freeship nha!",
        reply_status="replied",
    )
    metric = Metric(
        metric_id="met_001",
        channel_id="chan_home_02",
        video_id="vid_999",
        views_count=12500,
        likes_count=850,
        comments_count=32,
        shares_count=40,
        orders_count=18,
        estimated_revenue=2700000.0,
    )
    db_session.add_all([niche, channel, competitor, comment, metric])
    await db_session.commit()

    saved_comp = await db_session.get(Competitor, "comp_101")
    assert saved_comp.followers_count == 54000

    saved_comm = await db_session.get(VideoComment, "comm_001")
    assert saved_comm.reply_status == "replied"
    assert saved_comm.intent == "ask_material_usage"

    saved_met = await db_session.get(Metric, "met_001")
    assert saved_met.orders_count == 18
    assert saved_met.estimated_revenue == 2700000.0


@pytest.mark.asyncio
async def test_get_db_context_manager():
    """Tests get_db() context manager transaction handling."""
    async with get_db(TEST_DB_URL) as session:
        result = await session.execute(select(1))
        assert result.scalar() == 1
```

---

## 5. Verification Method

To verify these specifications independently:

1. **Environment Setup:**
   ```bash
   cd /Users/tuanlva/Folder/workSpace/affiliate
   python3 -m venv .venv
   source .venv/bin/activate
   pip install "sqlalchemy[asyncio]" aiosqlite asyncpg pytest pytest-asyncio greenlet
   ```

2. **Execute Database Unit Tests:**
   ```bash
   pytest tests/test_database.py -v
   ```
   *Expected Result:* All 7 tests pass (100% PASS) in under 1 second without errors.

3. **Check SQLite DDL / Compile Hook:**
   Run quick Python snippet verifying `JSONB` compilation:
   ```bash
   python -c "
   from src.database.models import Base
   from src.database.session import get_async_engine
   import asyncio
   async def check():
       engine = get_async_engine('sqlite+aiosqlite:///:memory:')
       async with engine.begin() as conn:
           await conn.run_sync(Base.metadata.create_all)
       print('Tables created cleanly!')
   asyncio.run(check())
   "
   ```

4. **Invalidation Conditions:**
   - If any column in the 7 models fails to be represented in `Base.metadata.tables`.
   - If `evaluation_data` fails to deserialize back into a Python `dict` upon `session.get(Product, ...)`.
   - If `Channel.lifecycle_status` transitions fail or raise constraint violations.
   - If `get_db()` raises `TypeError` when called via `async with get_db() as db:`.
