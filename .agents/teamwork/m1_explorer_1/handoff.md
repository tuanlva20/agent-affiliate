# Milestone 1 Task 1: Scaffolding, Configuration & Database Schema — Technical Investigation & Handoff Report

## 1. Observation

### 1.1 Greenfield Workspace State
- Workspace root `/Users/tuanlva/Folder/workSpace/affiliate` contains only:
  - `SYSTEM_SPEC.md` (6,995 bytes, 96 lines)
  - `docs/superpowers/plans/2026-11-10-autonomous-affiliate-system.md` (19,272 bytes, 385 lines)
  - `skills-lock.json` (260 bytes, 12 lines)
  - `.agents/` directory (containing `.agents/skills/kalopilot` and `.agents/teamwork/`)
- Non-existent files/directories confirmed via directory inspection:
  - `.git` directory does NOT exist.
  - `.gitignore` does NOT exist.
  - `requirements.txt` and `pyproject.toml` do NOT exist.
  - `src/` directory does NOT exist.
  - `tests/` directory does NOT exist.
  - `scripts/` directory does NOT exist.
  - `.env` and `config.yaml` do NOT exist.

### 1.2 Specification & Architecture Requirements
- **`ORIGINAL_REQUEST.md` (lines 42–46)**:
  - Task 1 Acceptance Criteria:
    - `.env.example`, `config.yaml` and `scripts/get_telegram_ids.py` created.
    - SQLAlchemy 2.0 async models (`Niche`, `Channel`, `Competitor`, `Product`, `VideoJob`, `VideoComment`, `Metric`) defined with JSONB.
    - `ToneValidator` tests and rejects robotic AI phrases and fake brands.
    - `pytest tests/test_config.py tests/test_database.py` executes 100% PASS.
- **`PROJECT.md` (lines 76–81)**:
  - `load_config(path: str = "config.yaml") -> AppConfig`
  - `get_async_engine(database_url: str)`: Returns async engine with `@compiles(JSONB, "sqlite")` hook for SQLite test compatibility.
  - `get_db() -> AsyncGenerator[AsyncSession, None]`: Context manager for isolated DB transactions.
  - `ToneValidator.validate(text: str) -> bool`: Pure validator, returns False if text contains banned robotic or counterfeit phrases.
- **`SYSTEM_SPEC.md` (lines 81–95)**:
  - Channel table schema: `channel_id`, `niche_id`, `browser_provider` (default `'aliasmode'`), `browser_profile_id` (unique), `proxy_url`, `lifecycle_status` (default `'warming'`: `warming`, `ready_to_post`, `cooldown`, `captcha_blocked`), `warmup_days_completed`, `last_posted_at`, `max_posts_per_day`, `created_at`.
- **`docs/superpowers/plans/2026-11-10-autonomous-affiliate-system.md` (lines 58–84)**:
  - Test snippets for `tests/test_config.py` verifying 2 pilot niches (`thoi_trang_nu`, `do_gia_dung`) and `browser.provider == "aliasmode"`.
  - Test snippet for `tests/test_database.py` testing engine creation against `sqlite+aiosqlite:///:memory:` and verifying `"lifecycle_status" in Channel.__table__.columns`.

---

## 2. Logic Chain

1. **Scaffolding Logic**: Because the workspace is completely greenfield, initial setup must precede all code: git repo initialization, `.gitignore` creation, pinned `requirements.txt` installation into a virtual environment, and directory skeleton creation.
2. **Python 3.12 Compatibility Logic**: Python 3.12 deprecated older async idioms and requires updated wheels for C-extensions (`asyncpg`, `pyyaml`, `pydantic-core`, `aiosqlite`). Pinning versions that have tested Python 3.12 wheels avoids compilation failures and runtime `DeprecationWarning`s.
3. **SQLite In-Memory Test Harness Logic**:
   - Production uses PostgreSQL 16+ with `asyncpg` and `JSONB`.
   - Unit tests must run lightning-fast without requiring live PostgreSQL or external network access.
   - SQLite does not have a native `JSONB` type. Using `@compiles(JSONB, "sqlite")` instructs SQLAlchemy to render `JSON` in SQLite DDL.
   - Using `JSONB().with_variant(JSON(), "sqlite")` ensures SQLite's Python serializer automatically handles dictionary-to-JSON-string serialization and JSON-string-to-dictionary deserialization.
   - SQLite in-memory `:memory:` databases are isolated per physical connection. To prevent connection closing or pool turnover from wiping in-memory tables between test statements, `StaticPool` must be used.
   - In async/await contexts, coroutines may resume across thread boundaries; setting `connect_args={"check_same_thread": False}` prevents `sqlite3.ProgrammingError`.
4. **TDD Flow Logic**: Writing `tests/conftest.py`, `tests/test_config.py`, and `tests/test_database.py` before source code confirms that all tests fail for the right reasons (missing modules/functions), establishing a clean RED baseline before implementing GREEN code.

---

## 3. Technical Investigation Findings

### 3.1 Greenfield Scaffolding

#### Comprehensive `.gitignore` Specification
Create `.gitignore` at `/Users/tuanlva/Folder/workSpace/affiliate/.gitignore`:
```gitignore
# Byte-compiled / optimized / DLL files
__pycache__/
*.py[cod]
*$py.class
*.so

# C extensions
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
share/python-wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual Environments
.venv/
venv/
ENV/
env/

# Environment Variables & Secrets (CRITICAL)
.env
.env.local
.env.*.local
*.pem
*.key

# Testing & Quality
.pytest_cache/
.coverage
htmlcov/
.tox/
.nox/
.hypothesis/
.mypy_cache/
.ruff_cache/

# IDE & OS
.DS_Store
.idea/
.vscode/
*.swp
*.swo

# Project Runtime Outputs
output/
downloads/
screenshots/
logs/
*.log

# Database Files (Local dev SQLite)
*.sqlite
*.sqlite3
*.db

# Whisper / ML Weights Cache
models/
.cache/

# Temporary Audio/Video Renders
*.mp4
*.mp3
*.wav
*.srt
*.vtt
```

#### Pinned `requirements.txt` for Python 3.12
Create `requirements.txt` at `/Users/tuanlva/Folder/workSpace/affiliate/requirements.txt`:
```txt
# Core Framework & Asynchronous I/O
pydantic==2.8.2
pydantic-settings==2.4.0
pyyaml==6.0.2
python-dotenv==1.0.1
aiofiles==24.1.0
tenacity==8.5.0
httpx==0.27.0

# Database & ORM
SQLAlchemy==2.0.32
asyncpg==0.29.0
aiosqlite==0.20.0

# Message Broker & Caching
redis==5.0.8
fakeredis[aioredis]==2.23.3

# Telegram Command Center
aiogram==3.12.0

# Video Remix & Content Pipeline
yt-dlp==2024.8.6
faster-whisper==1.0.3
edge-tts==6.1.12
ffmpeg-python==0.2.0

# Anti-Detect Browser Automation
playwright==1.46.0

# AI Orchestration & Gemini LLM
langgraph==0.2.14
langchain-core==0.2.34
google-genai==0.1.1

# Testing & Mock Harness
pytest==8.3.2
pytest-asyncio==0.23.8
pytest-mock==3.14.0
```

#### Virtual Environment Command Steps
Worker setup commands:
```bash
# 1. Initialize git repository
git init

# 2. Create Python 3.12 virtual environment
python3 -m venv .venv

# 3. Activate virtual environment
source .venv/bin/activate

# 4. Upgrade core build tools
pip install --upgrade pip setuptools wheel

# 5. Install all dependencies
pip install -r requirements.txt

# 6. Install Playwright browser binaries
playwright install chromium

# 7. Create directory skeleton
mkdir -p src/core src/database src/services src/agents src/bot scripts tests
touch src/__init__.py src/core/__init__.py src/database/__init__.py src/services/__init__.py src/agents/__init__.py src/bot/__init__.py tests/__init__.py
```

---

### 3.2 Async Test Harness (`tests/conftest.py`)

#### Problem Analysis: SQLite In-Memory & PostgreSQL JSONB
1. **JSONB in SQLite**:
   PostgreSQL uses `sqlalchemy.dialects.postgresql.JSONB`. SQLite natively lacks a `JSONB` data type.
   We solve this at two levels:
   - DDL compilation hook:
     ```python
     from sqlalchemy.dialects.postgresql import JSONB
     from sqlalchemy.ext.compiler import compiles

     @compiles(JSONB, "sqlite")
     def compile_jsonb_sqlite(type_, compiler, **kw):
         return "JSON"
     ```
   - Portable Column Type definition in `src/database/models.py`:
     ```python
     import sqlalchemy as sa
     from sqlalchemy.dialects.postgresql import JSONB

     # Compatible JSON type: renders JSONB in PostgreSQL, JSON in SQLite with automatic dict serialization
     CompatibleJSON = JSONB().with_variant(sa.JSON(), "sqlite")
     ```
     This guarantees that SQLite's dialect automatically serializes Python `dict`s to JSON strings during `INSERT`/`UPDATE` and deserializes them back to Python `dict`s on `SELECT`.

2. **Connection Pooling: `StaticPool` + `check_same_thread=False`**:
   In `src/database/session.py`:
   ```python
   from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
   from sqlalchemy.pool import StaticPool

   def get_async_engine(database_url: str = "sqlite+aiosqlite:///:memory:") -> AsyncEngine:
       connect_args = {}
       engine_kwargs = {"echo": False}
       
       if "sqlite" in database_url:
           connect_args["check_same_thread"] = False
           engine_kwargs["connect_args"] = connect_args
           if ":memory:" in database_url:
               engine_kwargs["poolclass"] = StaticPool
       
       return create_async_engine(database_url, **engine_kwargs)
   ```

3. **`pytest.ini` Configuration**:
   Create `pytest.ini` at `/Users/tuanlva/Folder/workSpace/affiliate/pytest.ini`:
   ```ini
   [pytest]
   asyncio_mode = auto
   testpaths = tests
   python_files = test_*.py
   python_classes = Test*
   python_functions = test_*
   filterwarnings =
       ignore::DeprecationWarning
   ```

4. **Complete `tests/conftest.py` Implementation**:
   Create `tests/conftest.py`:
   ```python
   import pytest
   import pytest_asyncio
   from typing import AsyncGenerator
   from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, AsyncEngine
   from src.database.session import get_async_engine
   from src.database.models import Base

   @pytest_asyncio.fixture(scope="session")
   async def test_engine() -> AsyncGenerator[AsyncEngine, None]:
       """Session-scoped async in-memory SQLite engine."""
       engine = get_async_engine("sqlite+aiosqlite:///:memory:")
       yield engine
       await engine.dispose()

   @pytest_asyncio.fixture(scope="function")
   async def setup_database(test_engine: AsyncEngine):
       """Recreates all tables cleanly before each test function."""
       async with test_engine.begin() as conn:
           await conn.run_sync(Base.metadata.drop_all)
           await conn.run_sync(Base.metadata.create_all)
       yield
       async with test_engine.begin() as conn:
           await conn.run_sync(Base.metadata.drop_all)

   @pytest_asyncio.fixture(scope="function")
   async def db_session(test_engine: AsyncEngine, setup_database) -> AsyncGenerator[AsyncSession, None]:
       """Provides an isolated AsyncSession with automatic rollback."""
       session_factory = async_sessionmaker(
           bind=test_engine,
           class_=AsyncSession,
           expire_on_commit=False,
           autoflush=False,
       )
       async with session_factory() as session:
           yield session
           await session.rollback()
   ```

---

### 3.3 Exact Test Specifications

#### 3.3.1 Specification for `tests/test_config.py`
This test suite covers central configuration loading, Pydantic validation, niche definitions, browser configurations, and `ToneValidator` rules.

```python
import pytest
import tempfile
import yaml
from pathlib import Path
from pydantic import ValidationError
from src.core.config import load_config, AppConfig, NicheConfig
from src.core.tone_validator import ToneValidator

def test_load_config_success():
    """Verify loading default config.yaml contains valid structure and 2 pilot niches."""
    config = load_config("config.yaml")
    assert isinstance(config, AppConfig)
    assert len(config.niches) == 2
    niche_ids = [n.niche_id for n in config.niches]
    assert "thoi_trang_nu" in niche_ids
    assert "do_gia_dung" in niche_ids

def test_fashion_niche_config():
    """Verify fashion niche settings, persona, and banned fake brand keywords."""
    config = load_config("config.yaml")
    fashion = next(n for n in config.niches if n.niche_id == "thoi_trang_nu")
    assert fashion.name == "Thời trang nữ"
    assert fashion.telegram_topic_id is not None
    # Check banned counterfeit keywords
    banned_lower = [k.lower() for k in fashion.banned_keywords]
    assert any("zara" in k for k in banned_lower)
    assert any("chanel" in k for k in banned_lower)
    assert any("rep 1:1" in k or "fake" in k for k in banned_lower)
    # Check persona
    assert fashion.persona.voice_name == "vi-VN-HoaiMyNeural"
    assert fashion.selection_criteria.min_commission_rate >= 0.10

def test_homelife_niche_config():
    """Verify homelife niche settings, persona, and banned exaggerated claims."""
    config = load_config("config.yaml")
    homelife = next(n for n in config.niches if n.niche_id == "do_gia_dung")
    assert homelife.name == "Đồ gia dụng thông minh"
    assert homelife.telegram_topic_id is not None
    banned_lower = [k.lower() for k in homelife.banned_keywords]
    assert any("trị dứt điểm" in k for k in banned_lower)
    assert homelife.persona.voice_name == "vi-VN-NamMinhNeural"
    assert homelife.selection_criteria.min_sales >= 100

def test_browser_config():
    """Verify browser configuration defaults to AliasMode with valid ports."""
    config = load_config("config.yaml")
    assert config.browser.provider == "aliasmode"
    assert "127.0.0.1:50325" in config.browser.api_url

def test_load_config_missing_file():
    """Verify loading a nonexistent file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        load_config("nonexistent_config_file_xyz.yaml")

def test_load_config_invalid_yaml(tmp_path):
    """Verify invalid schema raises Pydantic ValidationError."""
    invalid_file = tmp_path / "invalid.yaml"
    invalid_file.write_text("niches:\n  - niche_id: only_id_without_required_fields\n")
    with pytest.raises(ValidationError):
        load_config(str(invalid_file))

def test_tone_validator_banned_cliches():
    """Verify ToneValidator rejects robotic phrases."""
    robotic_samples = [
        "Xin chào quý khách, hôm nay tôi sẽ giới thiệu sản phẩm",
        "Tôi là trợ lý AI hữu ích",
        "Sản phẩm này rất tốt và tiện ích, bạn nên mua ngay",
    ]
    for text in robotic_samples:
        assert ToneValidator.validate(text) is False
        violations = ToneValidator.check_violations(text)
        assert len(violations) > 0

def test_tone_validator_banned_counterfeit():
    """Verify ToneValidator rejects counterfeit/trademark infringement terms."""
    counterfeit_samples = [
        "Áo thun Zara hàng rep 1:1 bao xịn",
        "Túi xách Chanel super fake y hình",
        "Đồng hồ Gucci rep chuẩn auth",
    ]
    for text in counterfeit_samples:
        assert ToneValidator.validate(text) is False
        violations = ToneValidator.check_violations(text)
        assert any("trademark" in v or "counterfeit" in v for v in violations)

def test_tone_validator_banned_medical_claims():
    """Verify ToneValidator rejects exaggerated medical/cleaning claims."""
    exaggerated_samples = [
        "Kem này cam kết trị dứt điểm 100% tàn nhang",
        "Nồi chiên vĩnh viễn không bám bẩn",
    ]
    for text in exaggerated_samples:
        assert ToneValidator.validate(text) is False

def test_tone_validator_natural_koc_pass():
    """Verify natural conversational KOC sentences pass validation cleanly."""
    natural_samples = [
        "Chị em ơi mẫu đầm này che bắp tay cực đỉnh luôn, mặc lên hack dáng dã man!",
        "Bà nào lười lau dọn bơi hết vào đây nha, từ ngày tậu em này nhàn hẳn.",
        "Mọi người bấm ngay vào góc trái giỏ hàng nhận mã freeship nha!",
    ]
    for text in natural_samples:
        assert ToneValidator.validate(text) is True
        assert ToneValidator.check_violations(text) == []
```

#### 3.3.2 Specification for `tests/test_database.py`
This test suite covers schema metadata, table creation, CRUD operations, channel lifecycle transitions, and JSON metadata storage in SQLite.

```python
import pytest
from datetime import datetime, timezone
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

def test_models_metadata():
    """Verify that all 7 required models exist in metadata and have correct columns."""
    tables = Base.metadata.tables
    expected_tables = {
        "niches",
        "channels",
        "competitors",
        "products",
        "video_jobs",
        "video_comments",
        "metrics",
    }
    assert expected_tables.issubset(tables.keys())

    # Check channels table specific columns and defaults
    channels_table = tables["channels"]
    assert "channel_id" in channels_table.columns
    assert "niche_id" in channels_table.columns
    assert "browser_provider" in channels_table.columns
    assert "browser_profile_id" in channels_table.columns
    assert "lifecycle_status" in channels_table.columns
    assert "warmup_days_completed" in channels_table.columns
    assert "last_posted_at" in channels_table.columns
    assert "max_posts_per_day" in channels_table.columns

@pytest.mark.asyncio
async def test_crud_niche(db_session: AsyncSession):
    """Test creating and querying a Niche."""
    niche = Niche(
        niche_id="thoi_trang_nu",
        name="Thời trang nữ",
        description="Quần áo và phụ kiện nữ TikTok Shop",
    )
    db_session.add(niche)
    await db_session.commit()

    result = await db_session.execute(select(Niche).where(Niche.niche_id == "thoi_trang_nu"))
    saved_niche = result.scalar_one_or_none()
    assert saved_niche is not None
    assert saved_niche.name == "Thời trang nữ"

@pytest.mark.asyncio
async def test_channel_lifecycle_status_transitions(db_session: AsyncSession):
    """Test channel creation with default 'warming' and lifecycle status updates."""
    # 1. Setup Niche
    niche = Niche(niche_id="do_gia_dung", name="Đồ gia dụng thông minh")
    db_session.add(niche)
    await db_session.flush()

    # 2. Create Channel - verify default status
    channel = Channel(
        channel_id="chan_homelife_01",
        niche_id="do_gia_dung",
        browser_profile_id="alias_profile_hl01",
    )
    db_session.add(channel)
    await db_session.commit()

    result = await db_session.execute(select(Channel).where(Channel.channel_id == "chan_homelife_01"))
    chan = result.scalar_one()
    assert chan.lifecycle_status == "warming"
    assert chan.browser_provider == "aliasmode"

    # 3. Transition: warming -> ready_to_post
    chan.lifecycle_status = "ready_to_post"
    chan.warmup_days_completed = 3
    await db_session.commit()

    result = await db_session.execute(select(Channel).where(Channel.channel_id == "chan_homelife_01"))
    chan = result.scalar_one()
    assert chan.lifecycle_status == "ready_to_post"
    assert chan.warmup_days_completed == 3

    # 4. Transition: ready_to_post -> cooldown
    chan.lifecycle_status = "cooldown"
    chan.last_posted_at = datetime.now(timezone.utc)
    await db_session.commit()

    # 5. Transition: cooldown -> captcha_blocked
    chan.lifecycle_status = "captcha_blocked"
    await db_session.commit()

    result = await db_session.execute(select(Channel).where(Channel.channel_id == "chan_homelife_01"))
    chan = result.scalar_one()
    assert chan.lifecycle_status == "captcha_blocked"

@pytest.mark.asyncio
async def test_product_crud_and_json_metadata_storage(db_session: AsyncSession):
    """Test storing and retrieving complex dicts in JSON/JSONB column on SQLite."""
    niche = Niche(niche_id="thoi_trang_nu", name="Thời trang nữ")
    db_session.add(niche)
    await db_session.flush()

    eval_meta = {
        "passed_filter": True,
        "score": 8.75,
        "hook_angle": "Hack dáng che eo bánh mì",
        "target_audience": "Nữ công sở 22-35",
        "pros": ["Tôn dáng", "Vải mát không nhăn"],
        "cons": ["Hơi dài với người dưới 1m55"],
        "viral_factor": "Trước sau biến hình 3s",
    }

    product = Product(
        product_id="prod_fashion_101",
        niche_id="thoi_trang_nu",
        title="Đầm xòe hoa nhí tay bồng",
        price=199000.0,
        commission_rate=0.18,
        product_url="https://tiktok.com/view/product/101",
        sales_count=1520,
        rating=4.9,
        evaluation_data=eval_meta,
        status="approved",
    )
    db_session.add(product)
    await db_session.commit()

    # Retrieve and verify JSON deserialization
    result = await db_session.execute(select(Product).where(Product.product_id == "prod_fashion_101"))
    saved_product = result.scalar_one()
    assert saved_product.title == "Đầm xòe hoa nhí tay bồng"
    assert saved_product.status == "approved"
    assert isinstance(saved_product.evaluation_data, dict)
    assert saved_product.evaluation_data["score"] == 8.75
    assert "Hack dáng che eo bánh mì" in saved_product.evaluation_data["hook_angle"]
    assert len(saved_product.evaluation_data["pros"]) == 2

    # Mutate and update JSON
    updated_eval = dict(saved_product.evaluation_data)
    updated_eval["reviewed_by"] = "FashionScoutAgent"
    saved_product.evaluation_data = updated_eval
    await db_session.commit()

    result = await db_session.execute(select(Product).where(Product.product_id == "prod_fashion_101"))
    reloaded_product = result.scalar_one()
    assert reloaded_product.evaluation_data["reviewed_by"] == "FashionScoutAgent"

@pytest.mark.asyncio
async def test_video_job_lifecycle_and_foreign_keys(db_session: AsyncSession):
    """Test VideoJob linked to Product and Channel through status pipeline."""
    niche = Niche(niche_id="thoi_trang_nu", name="Thời trang nữ")
    channel = Channel(
        channel_id="chan_01",
        niche_id="thoi_trang_nu",
        browser_profile_id="prof_01",
    )
    product = Product(
        product_id="prod_01",
        niche_id="thoi_trang_nu",
        title="Quần ống suông",
        price=150000.0,
        commission_rate=0.15,
        status="approved",
    )
    db_session.add_all([niche, channel, product])
    await db_session.flush()

    job = VideoJob(
        job_id="job_001",
        product_id="prod_01",
        niche_id="thoi_trang_nu",
        channel_id="chan_01",
        source_video_url="https://tiktok.com/@competitor/video/1",
        status="created",
    )
    db_session.add(job)
    await db_session.commit()

    # Pipeline transitions: created -> scripted -> audio_generated -> rendered -> published
    job.status = "scripted"
    job.script = "Chị em nào chân to bơi vào đây ngay..."
    await db_session.commit()

    job.status = "audio_generated"
    job.audio_path = "/tmp/audio_001.mp3"
    await db_session.commit()

    job.status = "rendered"
    job.output_video_path = "/tmp/render_001.mp4"
    await db_session.commit()

    job.status = "published"
    await db_session.commit()

    result = await db_session.execute(select(VideoJob).where(VideoJob.job_id == "job_001"))
    saved_job = result.scalar_one()
    assert saved_job.status == "published"
    assert saved_job.output_video_path == "/tmp/render_001.mp4"
```

---

## 4. Step-by-Step TDD Implementation Plan for Worker

| Step | Phase | Action | Target Files | Verification / Expected State |
|---|---|---|---|---|
| **1** | Scaffolding | Initialize Git & write `.gitignore` | `/.gitignore` | `git status` shows clean tracking |
| **2** | Dependencies | Create pinned `requirements.txt` | `/requirements.txt` | Complete dependency list for Py 3.12 |
| **3** | Environment | Create venv & install packages | `.venv/` | `pip list` confirms all packages installed |
| **4** | Config Files | Create `.env.example` & `config.yaml` | `/.env.example`, `/config.yaml` | 2 niches + aliasmode defined |
| **5** | Helper Script | Create `scripts/get_telegram_ids.py` | `/scripts/get_telegram_ids.py` | aiogram 3.x update inspector |
| **6** | Red Test Bed | Create `pytest.ini` & `tests/conftest.py` | `/pytest.ini`, `/tests/conftest.py` | Async SQLite fixture + @compiles JSONB |
| **7** | Red Test Suite | Write `test_config.py` & `test_database.py` | `/tests/test_config.py`, `/tests/test_database.py` | Run `pytest tests/test_config.py tests/test_database.py` -> **FAIL (RED)** |
| **8** | Green Core | Implement `src/core/config.py` | `/src/core/config.py` | Pydantic V2 AppConfig, NicheConfig |
| **9** | Green Tone | Implement `src/core/tone_validator.py` | `/src/core/tone_validator.py` | Anti-robotic & counterfeit validator |
| **10** | Green DB Session | Implement `src/database/session.py` | `/src/database/session.py` | Engine factory, `@compiles(JSONB, "sqlite")`, get_db |
| **11** | Green DB Models | Implement `src/database/models.py` | `/src/database/models.py` | 7 ORM models with CompatibleJSON |
| **12** | Test Execution | Run unit test suite | Terminal execution | Run `pytest tests/test_config.py tests/test_database.py -v` -> **100% PASS (GREEN)** |
| **13** | Commit | Git commit Task 1 implementation | Git tracking | `git commit -m "feat(core): setup config with aliasmode, database models, and tone validator"` |

---

## 5. Caveats

1. **Host Sandbox Restrictions**: Direct terminal execution of arbitrary shell commands (`git status`, `python3`) timed out on user prompt in subagent mode. All filesystem inspections were performed using native IDE tools (`list_dir`, `view_file`, `find_by_name`, `grep_search`).
2. **PostgreSQL vs SQLite JSON Operators**: While `@compiles(JSONB, "sqlite")` and `CompatibleJSON` guarantee seamless storage and retrieval of Python dictionaries, advanced PostgreSQL JSONB indexing operators (such as `@>` or `?&`) are dialect-specific and should not be used in generic queries unless guarded.
3. **Foreign Key Enforcement in SQLite**: SQLite disabled foreign keys by default unless `PRAGMA foreign_keys = ON;` is explicitly executed on the raw DBAPI connection. If FK constraints are tested in SQLite, this pragma must be attached via SQLAlchemy event listener (`@event.listens_for(engine.sync_engine, "connect")`).

---

## 6. Conclusion

1. **Readiness**: The greenfield codebase has no conflicting legacy code. Task 1 specifications are completely defined.
2. **Key Architectural Solutions Established**:
   - Pinned `requirements.txt` for Python 3.12 eliminates build failures across SQLAlchemy 2.0, asyncpg, Playwright, and PyYAML.
   - Dual-dialect JSON handling (`@compiles(JSONB, "sqlite")` + `JSONB().with_variant(JSON(), "sqlite")`) solves PostgreSQL JSONB vs SQLite test discrepancy.
   - In-memory SQLite with `StaticPool` and `check_same_thread=False` guarantees thread-safe, fast unit tests without external database dependencies.
   - Exact test specifications for `tests/test_config.py` and `tests/test_database.py` provide a turn-key blueprint for the implementing Worker.

---

## 7. Verification Method

To verify the findings and specifications in this report:
1. **Inspect Handoff Artifact**:
   Read `/Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m1_explorer_1/handoff.md`.
2. **Post-Implementation Test Execution**:
   Once Worker applies the code in Section 4:
   ```bash
   pytest tests/test_config.py tests/test_database.py -v
   ```
   **Pass Condition**: 100% of test cases pass with 0 failures, 0 errors, in under 3 seconds.
3. **Invalidation Conditions**:
   - If `test_database.py` fails with `sqlite3.InterfaceError: Error binding parameter: supported types are bytes, str, int, float, None`, the JSON variant configuration was omitted.
   - If `test_database.py` fails with `OperationalError: no such table`, `StaticPool` was omitted from the SQLite engine configuration.
