# Survey Phase Investigation Report: Runtime Environment & External Integrations for AMAS v1.4.0

**Working Directory:** `/Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/explorer_integrations_1/`  
**Date:** 2026-11-10T07:13:00Z  
**Author:** teamwork_explorer  

---

## 1. Observation

### 1.1 Python Runtime & Active Environment
- Command: `which python; which python3; python3 --version; echo "VIRTUAL_ENV: $VIRTUAL_ENV"`
  - Result:
    - `python`: Not found in `$PATH`.
    - `python3`: `/Library/Frameworks/Python.framework/Versions/3.12/bin/python3` (Python 3.12.2).
    - `VIRTUAL_ENV`: Empty (no virtualenv currently activated).
    - `pip`: Version 24.0 located at `/Library/Frameworks/Python.framework/Versions/3.12/lib/python3.12/site-packages/pip`.
- Command: `python3 -m pip list`
  - Output shows 29 global packages: `aiodns 3.2.0`, `aiohttp 3.9.3`, `openpyxl 3.1.5`, `pandas 2.2.1`, `pillow 12.3.0`, `requests 2.31.0`, etc.
  - Crucial packages for AMAS **MISSING** from global environment: `SQLAlchemy`, `asyncpg`, `aiosqlite`, `redis`, `fakeredis`, `aiogram`, `yt-dlp`, `faster-whisper`, `edge-tts`, `playwright`, `camoufox`, `langgraph`, `google-genai`, `pytest`, `pytest-asyncio`, `pytest-mock`, `pydantic`, `pyyaml`.

### 1.2 Availability of External CLI Tools & daemons
- Commands tested across system paths:
  | Tool | Path / Status | Version / Details |
  |---|---|---|
  | `ffmpeg` | **NOT FOUND** | Not in `$PATH` or `/usr/local/bin/brew` formula list |
  | `ffprobe` | **NOT FOUND** | Not in `$PATH` |
  | `docker` | `/usr/local/bin/docker` | Docker version 29.4.0, build 9d7ad9f |
  | `sqlite3` | `/usr/bin/sqlite3` | SQLite 3.43.2 (macOS system binary) |
  | `psql` | **NOT FOUND** | Not in host `$PATH` (available inside Docker container) |
  | `redis-cli` | **NOT FOUND** | Not in host `$PATH` |
  | `brew` | `/usr/local/bin/brew` | Homebrew package manager installed |

### 1.3 Running Services & Network Ports
- Command: `lsof -i :5432` / `docker ps`
  - Result: Port 5432 is active and listening:
    ```
    COMMAND   PID   USER   FD   TYPE   DEVICE   SIZE/OFF   NODE   NAME
    com.docke 2398  tuanlva 158u IPv6  ...      0t0        TCP    *:postgresql (LISTEN)
    ```
  - Docker container details:
    - Name: `local-postgres`
    - Image: `pgvector/pgvector:pg16`
    - Container ID: `6aa0218cdcc1`
    - Status: Up 33+ hours, port `0.0.0.0:5432->5432/tcp`
    - Environment variables: `POSTGRES_DB=ai_kb`, `POSTGRES_USER=fillform`, `POSTGRES_PASSWORD=admin@`, PostgreSQL version `16.14`.
    - Exec verified: `docker exec local-postgres psql -U fillform -d ai_kb -c "SELECT version();"` successfully returned `PostgreSQL 16.14`.
- Command: `lsof -i :6379`
  - Result: Port 6379 is NOT listening. No Redis daemon currently running.
- Command: `lsof -i :50325` / `lsof -i :50400`
  - Result: Port 50325 / 50400 is NOT listening. AliasMode daemon not running in background.

### 1.4 Kalodata & TikTok Scraper Assets
- Path: `~/.kalopilot/`
  - `~/.kalopilot/token` exists (64 bytes, mode 600).
  - `~/.kalopilot/task_id` exists (32 bytes).
- Skill documentation: `/Users/tuanlva/Folder/workSpace/affiliate/.agents/skills/kalopilot/SKILL.md`
  - Documents async submit & poll API:
    - `POST https://www.kalodata.com/api/pilot/skill/ext/v1/chat/async/submit`
    - `GET https://www.kalodata.com/api/pilot/skill/ext/v1/chat/async/result?task_id=<id>`
    - Header: `Authorization: Bearer <token>`
    - Response envelope: `{ success: true, data: { task_id, status, text, report, report_url } }`.

### 1.5 AliasMode & Camoufox Integration Specs
- Documentation and specs confirmed:
  - AliasMode provides an **AdsPower-compatible Local API** on loopback (`http://127.0.0.1:50325` or `http://127.0.0.1:50400`).
  - Endpoints:
    - `POST /api/v1/user/create` (creates profile with proxy, fingerprint config).
    - `GET /api/v1/browser/start?user_id=<profile_id>` (returns `{code: 0, data: {ws: {puppeteer: "ws://..."}}}`).
    - `GET /api/v1/browser/stop?user_id=<profile_id>`
    - `GET /api/v1/browser/active?user_id=<profile_id>`
  - CDP connection: Playwright connects via `await playwright.chromium.connect_over_cdp(ws_endpoint)`.

---

## 2. Logic Chain

```
Observation 1.1: Python 3.12.2 present, but project dependencies missing in global env.
  └── Logic Step 1: The system must operate within a dedicated virtualenv (e.g. `.venv`) to isolate requirements and ensure consistent builds across machines.

Observation 1.2: `ffmpeg` & `ffprobe` binaries are not in PATH.
  └── Logic Step 2: Live video processing requires `brew install ffmpeg`. However, CI and unit tests CANNOT assume `ffmpeg` is installed. VideoProcessor unit tests MUST mock `asyncio.create_subprocess_exec` / `subprocess.run` to verify CLI command structure, filter graph syntax, and exit-code handling without invoking the real binary.

Observation 1.3: Docker PostgreSQL 16 is already running on port 5432; SQLite 3.43.2 is installed locally.
  └── Logic Step 3: 
      - The plan specifies `sqlite+aiosqlite:///:memory:` for unit tests (e.g., Task 1 `test_database.py`), while production uses PostgreSQL with `JSONB`.
      - In SQLAlchemy 2.0, referencing PostgreSQL dialect `JSONB` directly in models causes `CompileError: Compiler <sqlite.dialect.SQLiteTypeCompiler> can't render element of type JSONB` when compiling against SQLite.
      - Therefore, models or the database layer must use `@compiles(JSONB, "sqlite")` to compile `JSONB` as `JSON` on SQLite, or define `JSON().with_variant(JSONB, "postgresql")`.
      - In SQLite in-memory, `StaticPool` and `connect_args={"check_same_thread": False}` must be configured to preserve tables across async transactions.
      - For end-to-end integration or migration tests, the running Docker PostgreSQL container (`fillform:admin@localhost:5432/ai_kb`) can be utilized directly.

Observation 1.3 & Plan: Redis is required for job queuing, but no local redis server is running.
  └── Logic Step 4:
      - For 100% test pass rate in CI/local test suite, `fakeredis[asyncio]` provides a zero-dependency in-memory mock of Redis.
      - For live execution, Docker is available (`docker run -d --name local-redis -p 6379:6379 redis:7-alpine`).

Observation 1.4: Kalodata client uses HTTP async submit/poll with external token; TikTok scraping relies on `yt-dlp`.
  └── Logic Step 5:
      - Unit tests for `KalodataClient` and `TikTokScraper` must not perform outbound HTTP calls or rely on third-party rate limits.
      - Mocking `aiohttp.ClientSession` (using `aioresponses` or `unittest.mock.AsyncMock`) allows deterministic testing of submission, polling states (`submitted`, `running`, `completed`, `error`), and token error handling (401 / missing token).
      - Mocking `yt-dlp` returns static metadata for fashion and homelife videos.

Observation 1.5: AliasMode & Playwright CDP biometrics.
  └── Logic Step 6:
      - Live execution expects AliasMode running on `127.0.0.1:50325`.
      - In automated tests, Playwright `Page`, `Keyboard`, and `Mouse` can be mocked with `AsyncMock`.
      - `HumanBehaviorService` algorithms (Bezier curve interpolation, 80-220ms typing jitter, 3% typo with backspace, 0.6-1.4s micro-pauses, inertia scroll acceleration, and captcha selector detection) are algorithmic functions that can be tested with 100% test coverage using mocked Playwright primitives.
```

---

## 3. Caveats

1. **Host Environment Modification Restraint:** Under our read-only survey guidelines, we did not run `python3 -m venv .venv` or `brew install ffmpeg`. The implementation agent will need to initialize `.venv` and install the dependency manifest (`requirements.txt`).
2. **Docker PostgreSQL Existing Database:** The running container `local-postgres` has database `ai_kb` used by another project. The implementation agent should either create a separate database (e.g. `affiliate_db` / `amas_db`) inside this container (`docker exec local-postgres psql -U fillform -d ai_kb -c "CREATE DATABASE amas_db;"`) or rely on SQLite in-memory for all automated tests.
3. **AliasMode Daemon in Headless CI:** AliasMode is a desktop GUI antidetect browser application. In headless Linux CI environments, AliasMode desktop cannot run natively without Xvfb or a mock server. Therefore, testing `BrowserAdapter` via an AdsPower API mock server (or HTTP mocking) is essential for CI portability.

---

## 4. Conclusion & Strategic Recommendations

### 4.1 Dependency & Environment Setup Blueprint
The implementation phase must immediately create `.venv` and install the following pinned dependency stack:

```text
# requirements.txt
python-dotenv>=1.0.0
pydantic>=2.6.0
pydantic-settings>=2.0.0
pyyaml>=6.0.1
sqlalchemy>=2.0.25
asyncpg>=0.29.0
aiosqlite>=0.20.0
redis>=5.0.1
fakeredis[asyncio]>=2.21.0
aiogram>=3.4.1
yt-dlp>=2024.3.10
edge-tts>=6.1.10
faster-whisper>=1.0.0
playwright>=1.42.0
langgraph>=0.0.30
langchain-core>=0.1.30
google-genai>=0.1.1
aiohttp>=3.9.3

# Testing dependencies
pytest>=8.0.2
pytest-asyncio>=0.23.5
pytest-mock>=3.12.0
aioresponses>=0.7.6
```

### 4.2 SQLite & PostgreSQL `JSONB` Compatibility Solution
To satisfy Task 1's requirement (`get_async_engine(database_url="sqlite+aiosqlite:///:memory:")`) while maintaining full PostgreSQL `JSONB` production schema:
1. In `src/database/session.py`, implement dialect compilation hook:
   ```python
   from sqlalchemy.dialects.postgresql import JSONB
   from sqlalchemy.ext.compiler import compiles
   from sqlalchemy.pool import StaticPool
   from sqlalchemy.ext.asyncio import create_async_engine

   @compiles(JSONB, "sqlite")
   def compile_jsonb_sqlite(type_, compiler, **kw):
       return "JSON"

   def get_async_engine(database_url: str):
       if "sqlite" in database_url:
           return create_async_engine(
               database_url,
               poolclass=StaticPool,
               connect_args={"check_same_thread": False}
           )
       return create_async_engine(database_url, pool_pre_ping=True)
   ```
2. In `src/database/models.py`, fields can use `JSONB` directly (or `JSON().with_variant(JSONB, "postgresql")`), guaranteeing 100% portability.

### 4.3 External Integration & Mocking Matrix for 100% Pass Rate

| Subsystem | External Dependency | Live Behavior | Test/Mock Strategy (100% Isolated) |
|---|---|---|---|
| **Database** | PostgreSQL 16 (`asyncpg`) | Connects to `localhost:5432/amas_db` | `sqlite+aiosqlite:///:memory:` with `@compiles(JSONB, 'sqlite')` |
| **Broker/Queue** | Redis (`localhost:6379`) | Job scheduling, delay queues | `fakeredis.aioredis.FakeRedis()` injected via fixture |
| **Telegram Bot** | Telegram Bot API (`aiogram 3.x`) | Sends cards with topics (`message_thread_id`), handles callbacks | Mock `Bot`, `Message`, `CallbackQuery` with `AsyncMock`. Test formatters & keyboards as pure deterministic unit tests |
| **Kalodata API** | `https://www.kalodata.com` | Async submit + poll, reads `~/.kalopilot/token` | Mock `aiohttp.ClientSession` using `aioresponses` or monkeypatch. Inject fixture JSON for Fashion & HomeLife products |
| **TikTok Scraper**| `yt-dlp` CLI / Python lib | Scrapes video metadata & creator showcase | Mock `yt_dlp.YoutubeDL.extract_info` to return pre-canned video & product metadata dictionaries |
| **Voice Synthesis**| `edge-tts` (Microsoft Cloud) | Streams Vietnamese neural TTS to MP3 | Mock `edge_tts.Communicate.save()` to write mock bytes / touch file |
| **Audio Transcription**| `faster-whisper` | Downloads and loads Whisper model weights | Mock `faster_whisper.WhisperModel.transcribe()` returning simulated segments `[{"text": "...", "start": 0, "end": 2}]` |
| **Video Remixing**| `ffmpeg` & `ffprobe` CLI | Executes complex filter graph (`setpts`, `atempo`, `crop`, `eq`) | Mock `asyncio.create_subprocess_exec` to capture CLI args, verify copyright evasion filter string, simulate exit code 0 |
| **Anti-Detect / CDP**| AliasMode Local API (`127.0.0.1:50325`) | Creates profile, starts browser, returns CDP WS endpoint | Mock HTTP responses for `/api/v1/user/create` and `/api/v1/browser/start` |
| **Biometrics Engine**| Playwright CDP session | Controls mouse Bezier, typing delays, captcha detection | Mock `page.keyboard.press`, `page.mouse.wheel`, `page.screenshot` with `AsyncMock`. Assert statistical properties (typing speed, typo count, backspaces, micro-pauses) |

---

## 5. Verification Method

To independently verify the observations and conclusions in this report:

1. **Verify Python & Pip:**
   ```bash
   /Library/Frameworks/Python.framework/Versions/3.12/bin/python3 --version
   ```
   *Expected:* `Python 3.12.2`

2. **Verify Docker PostgreSQL Container:**
   ```bash
   docker ps --filter "name=local-postgres" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
   docker exec local-postgres psql -U fillform -d ai_kb -c "SELECT version();"
   ```
   *Expected:* PostgreSQL 16.14 running on port 5432.

3. **Verify Kalopilot Token Existence:**
   ```bash
   [ -s ~/.kalopilot/token ] && echo "Token present, length: $(wc -c < ~/.kalopilot/token) bytes"
   ```
   *Expected:* Token present, 64 bytes.

4. **Verify FFmpeg / CLI absence:**
   ```bash
   which ffmpeg || echo "ffmpeg missing as expected"
   which redis-cli || echo "redis-cli missing as expected"
   ```

5. **Test Invalidation Conditions:**
   - If `ffmpeg` or `redis-server` are installed globally or in brew, live execution can use them directly without docker/mocking.
   - If SQLite in-memory tests fail on `JSONB`, verify that `@compiles(JSONB, 'sqlite')` is included in the test execution path.
