# AMAS v1.4.0 Specification Survey & Feature Catalog

> **Author**: Specification Miner (`spec_miner_survey_1`)  
> **Date**: 2026-11-10  
> **Target System**: Autonomous Multi-Agent TikTok Affiliate System (AMAS v1.4.0)  
> **Primary References**:
> - `/Users/tuanlva/Folder/workSpace/affiliate/SYSTEM_SPEC.md`
> - `/Users/tuanlva/Folder/workSpace/affiliate/docs/superpowers/plans/2026-11-10-autonomous-affiliate-system.md`
> - `/Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/ORIGINAL_REQUEST.md`
> - `/Users/tuanlva/Folder/workSpace/affiliate/.agents/skills/kalopilot/SKILL.md`

---

## 1. Observation

### 1.1 Specification Sources & Scope

From `SYSTEM_SPEC.md` (lines 4-10):
> "Version: 1.4.0"  
> "Database: PostgreSQL (with JSONB & SQLAlchemy Async) | Broker: Redis"  
> "Anti-Detect Engine: AliasMode + Human Behavioral Biometrics Engine (human_behavior.py)"  
> "Target Niches (Pilot): 1. Thời trang nữ (Women's Fashion) | 2. Đồ gia dụng thông minh (Home Utilities)"  
> "Core Framework: Python 3.11+, LangGraph, Playwright, AliasMode, aiogram (Telegram)"

From `2026-11-10-autonomous-affiliate-system.md` (lines 5-10, 15-27):
> "Python Version: 3.11+ bắt buộc, sử dụng asyncio toàn phần cho I/O (database, web scraping, Telegram bot)."  
> "Database Engine: PostgreSQL với SQLAlchemy 2.0 async session (asyncpg) và JSONB cho metadata động."  
> "Anti-Detect & Biometrics Engine: Trình duyệt AliasMode (Local API & CDP endpoint). Hành vi sinh trắc học bắt buộc qua HumanBehaviorService."  
> "Natural Conversational Language: Tuyệt đối cấm các câu máy móc... Bắt buộc dùng xưng hô gần gũi đúng thị hiếu TikTok Việt Nam."  
> "Chính sách TikTok Shop Việt Nam: Tự động lọc bỏ từ khóa hàng nhái và cam kết y khoa/quảng cáo quá đà."

From `SYSTEM_SPEC.md` (lines 83-95) - Channel Schema:
> ```sql
> CREATE TABLE channels (
>     channel_id VARCHAR(50) PRIMARY KEY,
>     niche_id VARCHAR(50) REFERENCES niches(niche_id) ON DELETE CASCADE,
>     browser_provider VARCHAR(30) DEFAULT 'aliasmode',
>     browser_profile_id VARCHAR(100) NOT NULL UNIQUE,
>     proxy_url VARCHAR(255),
>     lifecycle_status VARCHAR(30) DEFAULT 'warming', -- warming, ready_to_post, cooldown, captcha_blocked
>     warmup_days_completed INTEGER DEFAULT 0,
>     last_posted_at TIMESTAMP WITH TIME ZONE,
>     max_posts_per_day INTEGER DEFAULT 2,
>     created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
> );
> ```

From `.agents/skills/kalopilot/SKILL.md` (lines 45-48):
> `POST https://www.kalodata.com/api/pilot/skill/ext/v1/chat/async/submit`  
> `GET  https://www.kalodata.com/api/pilot/skill/ext/v1/chat/async/result?task_id=<id>`  
> Token stored at `~/.kalopilot/token` or via `KALOPILOT_TOKEN`.

---

### 1.2 Features Discovered

| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|----------|---------|-------------|--------|---------|----------------|----------------|
| F01 | Core / Config | Central Configuration Loader | Loads `config.yaml` and `.env` into validated Pydantic models with 2 pilot niches, browser config, Redis, and Telegram configs. | File path (`config.yaml`), Environment variables | `AppConfig` instance (with `niches`, `browser`, `database`, `telegram`) | Raises `ValidationError` or `FileNotFoundError` if required keys are missing. | Plan § Task 1, lines 61-70, 94-97 |
| F02 | Core / Database | Async SQLAlchemy Engine & Session | Async PostgreSQL engine using `asyncpg` with fallback/variant support for SQLite `aiosqlite` during testing. | Database URL string | `AsyncEngine`, `async_sessionmaker[AsyncSession]`, async generator `get_db()` | Raises DB connection error or invalid URI exception. | Plan § Task 1, lines 73-83, 98-101 |
| F03 | Core / Database | AMAS Domain Data Models | Defines 7 core models (`Niche`, `Channel`, `Competitor`, `Product`, `VideoJob`, `VideoComment`, `Metric`) with JSONB fields. | DeclarativeBase schemas | SQLAlchemy ORM Model Classes | Raises `IntegrityError` on unique/FK violations. | Plan § Task 1, lines 73-83, 98-101; SYSTEM_SPEC § 5 |
| F04 | Core / Tone | Anti-Robotic Tone Validator | Enforces natural Vietnamese KOC phrasing, rejects robotic AI speech, drops counterfeit brands, and rejects extreme claims. | Text string (`caption`, `script`, `reply`) | `Tuple[bool, List[str]]` or `bool` (pass/fail with violation reasons) | Returns `False` and lists forbidden phrases; does not crash. | Plan § Global Constraints, Task 1, lines 102-105 |
| F05 | Scout / Kalodata | Async Kalodata API Client | Submits queries and polls results from Kalodata Pilot API for top viral products. | Query string, optional `task_id`, `category_id`, limit | List of raw product dictionaries, task completion status | Raises clear missing-token prompt pointing to `~/.kalopilot/token` on 401/empty token. | Plan § Task 2, lines 130-132; kalopilot/SKILL.md |
| F06 | Scout / Scraper | TikTok Scraper & Metadata Extractor | Uses `yt-dlp` to extract video statistics (views, likes, comments, shares), descriptions, and anchor product link without watermark. | TikTok channel/video URL | `TikTokVideoMeta` dataclass/dict | Returns empty/None or raises `ScraperException` on network/selector failure. | Plan § Task 2, lines 133-134, 140 |
| F07 | Scout / Base | Base Scout Agent | Discovers candidate products and filters candidates by pricing thresholds, commission rates, and sales velocity. | `niche_id: str` | `List[ProductCandidate]` | Logs warning and returns empty list if no candidates meet minimum thresholds. | Plan § Task 2, lines 135-136, 141 |
| F08 | Scout / Specialist | Fashion Scout Agent | Specialist for Women's Fashion: evaluates body-flattering ("hack dáng"), flaw-concealing, trends; strictly rejects fake brands (Zara, Chanel, Gucci, rep 1:1). | `ProductCandidate` or product dict | `SpecialistEvaluation` (score, passed_filter, hook_angle, pros, cons, rejection_reason) | Rejects with explicit `rejection_reason` on trademark violation. | Plan § Task 3, lines 154-177 |
| F09 | Scout / Specialist | HomeLife Scout Agent | Specialist for Home Utilities: evaluates labor-saving utility ("giải phóng sức lao động"), 3s Before/After visual hooks; rejects extreme claims. | `ProductCandidate` or product dict | `SpecialistEvaluation` (score, passed_filter, hook_angle, pros, cons, rejection_reason) | Rejects with explicit `rejection_reason` on extreme claims violation. | Plan § Task 3, lines 154-177 |
| F10 | Bot / Dispatcher | Telegram Forum Topic Routing | Routes notifications and cards to dedicated forum topics (`#thoi-trang-nu`, `#do-gia-dung`, `#dashboard-tong`). | Message, Thread ID | Telegram Message sent to specified `message_thread_id` | Catches `TelegramAPIError`, falls back to general topic or logs error. | Plan § Task 4, lines 189-195, 199 |
| F11 | Bot / UI | 1-Tap Approval Inline Keyboard | Generates inline buttons for human-in-the-loop review: `Approve` (`approve_product:<id>`), `Reject` (`reject_product:<id>`), and `View Original Video`. | `product_id`, `video_url` | `InlineKeyboardMarkup` | Ignores invalid callback data format. | Plan § Task 4, lines 184-187, 194 |
| F12 | Bot / Commands | Command Center Handlers | Implements bot commands: `/test_scout`, `/test_video`, `/test_reply`, `/status`, `/menu`, `/create_channel`, `/warmup`. | Command message + arguments | Telegram response message / triggered background action | Sends syntax help message if arguments are missing/malformed. | Plan § Task 4, lines 193-195 |
| F13 | Video / Ingestion | Watermark-Free Downloader | Downloads original source video from competitor TikTok post using `yt-dlp`. | Video URL, target directory | Local MP4 file path | Raises `DownloadError` if video is deleted or inaccessible. | Plan § Task 5, lines 213, 229 |
| F14 | Video / Audio | Audio Transcriber | Transcribes source video spoken audio to text and timestamps using Whisper / `faster-whisper`. | Video/Audio file path | Plain text transcript and segment timestamps | Returns fallback text or raises transcription error if file corrupted. | Plan § Task 5, lines 214, 229 |
| F15 | Video / Script | KOC Script Generator | Rewrites viral script according to Hook 3s, problem-solution body, KOC colloquial tone, and yellow cart CTA. | Original transcript, product metadata, niche config | Structured script dict (`hook`, `body`, `cta`, `full_script`, `subtitles`) | Regenerates or sanitizes if `ToneValidator` detects robotic phrases. | Plan § Task 5, lines 215, 230 |
| F16 | Video / Voice | Natural TTS Service | Synthesizes Vietnamese speech using `edge-tts` (voices: `vi-VN-HoaiMyNeural` or `vi-VN-NamMinhNeural`). | Vietnamese text, voice name, rate, output path | Local MP3/WAV audio file path | Raises TTS error if network fails or voice unavailable. | Plan § Task 5, lines 216, 231 |
| F17 | Video / Remix | FFmpeg Algorithm Evasion Processor | Remuxes video: strips original audio, embeds new voiceover + BGM at -20dB, applies 1.02-1.05x speed, 2-3% crop, subtle color shift, and subtitles. | Raw MP4, Audio MP3, output path, options | Processed MP4 file path | Raises `FFmpegError` with stderr if command fails. | Plan § Task 5, lines 217, 231 |
| F18 | Video / Studio | Video Studio Agent | Pipeline orchestrator coordinating download, transcribe, script generation, TTS, and FFmpeg processing into a finalized `VideoJob`. | `job_id: str` | Final MP4 file path; updates `VideoJob.status = 'rendered'` | Sets `VideoJob.status = 'failed'` and logs error message. | Plan § Task 5, lines 218, 232 |
| F19 | Browser / CDP | AliasMode Browser Adapter | Interacts with AliasMode Local API (`http://127.0.0.1:50325`) to create/start anti-detect profiles and connects Playwright via CDP endpoint. | Profile ID or name, optional proxy URL | Playwright `BrowserContext`, `Page`, CDP endpoint | Raises connection error if AliasMode API daemon is not running. | Plan § Task 6, lines 246, 256-257, 297-299 |
| F20 | Biometrics | Inertial Human Scrolling | Simulates mouse wheel ticks with variable acceleration/deceleration and 10-20% reverse overshoot. Never uses `window.scrollTo()`. | `page: Page`, `steps: int`, `direction: str` | Async completion | Falls back safely if element cannot be scrolled. | Plan § Task 6, lines 258, 303; SYSTEM_SPEC § 3.1 |
| F21 | Biometrics | Biometric Typing Simulation | Types keystrokes with 80-220ms random delay, micro-pauses 0.6-1.4s at sentence ends/hashtags, and 3% typo rate with Backspace correction. | `page: Page`, `selector: str`, `text: str`, `typo_rate: float` | Async completion | Clicks selector and types key by key; never calls `page.fill()`. | Plan § Task 6, lines 259, 273-289, 304; SYSTEM_SPEC § 3.2 |
| F22 | Biometrics | Non-linear Bezier Mouse Movement | Moves cursor along cubic Bezier curve with acceleration and $\pm 2$px jitter, hovering 200-400ms before clicking. | `page: Page`, `selector: str` or coordinates | Async completion | Retries or throws element not found exception. | Plan § Task 6, lines 305; SYSTEM_SPEC § 3.3 |
| F23 | Biometrics | Pre-posting Feed Warmup Session | Navigates to `tiktok.com`, scrolls and watches 3-5 videos for 3-5 minutes (watching >= 60% duration), randomly likes 1 video. | `page: Page`, `duration_seconds: int = 180` | Async completion | Gracefully recovers if video fails to play; continues session. | Plan § Task 6, lines 260, 306; SYSTEM_SPEC § 3.4 |
| F24 | Biometrics / Safety | Emergency Captcha Guard | Detects verification sliders/puzzle iframes. Immediately STOPS actions, takes screenshot, sounds Telegram alarm, and sets channel to `captcha_blocked`. | `page: Page` | `bool` (True if captcha found) | Returns `True` and aborts all execution. Bot never attempts to solve. | Plan § Task 6, lines 261, 307; SYSTEM_SPEC § 3.5 |
| F25 | Publisher / Core | Smart Publisher Agent | Manages publishing workflow: checks channel lifecycle, runs warmup, navigates Creator Center, uploads MP4, types metadata, and attaches Showcase anchor. | `job_id: str` | `PublishResult` (`success`, `video_url`, `captcha_triggered`, `error`) | Sets channel to `cooldown` on success; `captcha_blocked` on captcha. Rejects if channel is in `warming` state. | Plan § Task 6, lines 262, 309-312 |
| F26 | Engagement / Scanner | Video Comment Scanner | Scans recent comments on published channel videos. | `channel_id: str`, `video_id: str` | List of comment dicts (`author`, `comment_text`, `comment_id`) | Logs warning and returns empty list if video not accessible. | Plan § Task 7, lines 331, 335 |
| F27 | Engagement / Agent | Intent Classification & KOC Reply Agent | Classifies comment intent (`ASK_PRICE`, `ASK_MATERIAL_USAGE`, `COMPLAINT`, `OTHER`) and crafts KOC response guiding to yellow cart. | `comment: str`, `product_meta: Dict`, `persona: PersonaConfig` | `CommentIntent` enum and reply text string | Validates reply via `ToneValidator`; falls back to default friendly prompt if validation fails. | Plan § Task 7, lines 330, 337-339 |
| F28 | Orchestrator | Hermes LangGraph State Coordinator | Manages multi-agent execution pipeline via LangGraph StateGraph (Scout -> Approval -> Video -> Publish -> Engagement). | `step_name: str`, `payload: Dict` or state | Updated pipeline state dict | Catches node exceptions, sets error state, and alerts Telegram Admin. | Plan § Task 8, lines 356, 365-366, 371 |
| F29 | System / Runner | CLI Runner & Background Daemon | Main entrypoint supporting `--mode bot`, `--mode scout`, `--mode dry-run`, and `--mode daemon` for scheduled jobs. | CLI arguments (`sys.argv`) | Process exit code (0 on success) | Handles `SIGINT`/`SIGTERM` gracefully, closes database pool and browser connections. | Plan § Task 8, lines 357, 367, 372 |

---

### 1.3 Edge Cases & Strict Constraints

| # | Feature | Input / Trigger | Observed & Required Behavior | Source Reference |
|---|---------|-----------------|------------------------------|------------------|
| E01 | ToneValidator | Input contains AI cliches (e.g. "Xin chào quý khách", "Tôi là trợ lý AI", "Sản phẩm này rất tốt và tiện ích") | `ToneValidator.validate()` returns `False` and lists matching robotic phrases. Script or reply must be rejected or rewritten. | Plan lines 22, 102-104 |
| E02 | ToneValidator & Scout | Input contains counterfeit trademarks ("Zara", "Chanel", "Gucci", "Dior", "rep 1:1", "super fake") | `FashionScoutAgent` rejects candidate product with `passed_filter=False` and reason `"counterfeit_trademark_detected"`. ToneValidator blocks published captions. | Plan lines 25, 168 |
| E03 | ToneValidator & Scout | Input contains false medical or exaggerated claims ("trị dứt điểm 100%", "vĩnh viễn không bám bẩn") | `HomeLifeScoutAgent` rejects candidate product. Script generator blocks text. | Plan lines 26, 169 |
| E04 | SmartPublisher | Channel has lifecycle status `warming` and receives an affiliate publishing job | SmartPublisher refuses to publish affiliate video (`success=False`, `error="Channel in warming status cannot post affiliate videos"`). Only warmup feed sessions are permitted. | Plan line 33; SYSTEM_SPEC lines 72-73 |
| E05 | SmartPublisher | Channel has lifecycle status `cooldown` with `last_posted_at` < 4 hours ago | Publisher rejects post until cooldown window (4–6 hours) has elapsed to protect channel reputation. | SYSTEM_SPEC line 74 |
| E06 | HumanBehaviorService | Captcha iframe, slider, or puzzle popup appears during upload or feed browse | `detect_and_handle_captcha` immediately aborts all browser actions, takes a screenshot to `screenshots/captcha_<timestamp>.png`, fires an emergency alert to Telegram, and updates Channel to `captcha_blocked`. Never attempts programmatic solving. | Plan lines 20, 31, 307; SYSTEM_SPEC lines 60-66 |
| E07 | HumanBehaviorService | Text input to TikTok Studio caption field | MUST use `human_type` with 80-220ms randomized delay, 3% typo simulation (types wrong char, waits 300ms, Backspace, types correct char), and 0.6-1.4s micro-pauses at punctuation/hashtags. Absolute prohibition on `page.fill()`. | Plan lines 19, 32, 280-289 |
| E08 | KalodataClient | Missing `~/.kalopilot/token` or HTTP 401 Unauthorized from Kalodata API | Client raises an informative exception guiding the user to visit `https://kalodata.com/pilot` -> OpenClaw integration -> copy Current Account Token to `~/.kalopilot/token`. | Plan line 34; kalopilot/SKILL.md lines 12-26 |
| E09 | Database / Concurrency | Telegram callback query triggers simultaneously while Scraper bulk-saves products | `get_db()` provides an isolated `AsyncSession` per transaction/task. Independent sessions avoid lock contention in PostgreSQL. | Plan line 35 |
| E10 | Database / Testing | SQLAlchemy `JSONB` type compiled under SQLite in test suite (`sqlite+aiosqlite:///:memory:`) | In SQLite, PostgreSQL `JSONB` raises compilation error unless implemented as `sa.JSON().with_variant(JSONB, "postgresql")` or handled polymorphically. Model definitions must be cross-compatible with SQLite for test execution. | Plan lines 78-83 |
| E11 | Telegram Bot | Admin sends message without specifying topic, or Telegram API returns thread not found | System falls back to default general chat or logs thread ID error without dropping the notification. | Plan lines 199 |
| E12 | ScriptGenerator | Gemini API returns response lacking Hook 3s or yellow cart CTA | Validator detects missing KOC elements and triggers a retry or injects mandatory standard KOC CTA: *"Chị em bấm ngay góc trái nhận mã freeship nha!"*. | Plan lines 23, 230 |

---

## 2. Logic Chain

```
[SYSTEM_SPEC.md & ORIGINAL_REQUEST.md Requirements]
       │
       ▼
[Task 1: Core Configuration & Database Schema]
  ├── .env.example & config.yaml (Niches: thoi_trang_nu, do_gia_dung; Browser: aliasmode)
  ├── SQLAlchemy 2.0 Async Models (Niche, Channel, Competitor, Product, VideoJob, VideoComment, Metric)
  └── ToneValidator (Bans robotic phrases & counterfeit/medical claims, enforces KOC markers)
       │
       ▼
[Task 2 & 3: Scout & Niche Intelligence Pipeline]
  ├── KalodataClient (async submit + poll, ~/.kalopilot/token auth)
  ├── TikTokScraper (yt-dlp metadata & anchor extractor)
  ├── BaseScoutAgent (pricing & commission threshold filter)
  └── Specialist Scout Agents:
        ├── FashionScoutAgent (hack dáng, che khuyết điểm, chống hàng nhái)
        └── HomeLifeScoutAgent (giải phóng sức lao động, Before/After 3s, chống cam kết quá đà)
       │
       ▼
[Task 4: Telegram Bot Command Center (Human-in-the-Loop)]
  ├── Forum Topic Dispatching (#thoi-trang-nu, #do-gia-dung, #dashboard-tong)
  ├── 1-Tap Inline Keyboard (approve_product:<id>, reject_product:<id>)
  └── Bot Commands (/test_scout, /test_video, /test_reply, /status, /create_channel, /warmup)
       │
       ▼ (On Approval)
[Task 5: Video Remixing & Content Engine]
  ├── VideoDownloader (watermark-free source video)
  ├── AudioTranscriber (faster-whisper transcription)
  ├── ScriptGenerator (Hook 3s, KOC persona, CTA giỏ hàng vàng)
  ├── TTSService (edge-tts Vietnamese neural voices: vi-VN-HoaiMyNeural)
  └── VideoProcessor (FFmpeg 1.03x speed, subtle crop, BGM -20dB, burn subtitles)
       │
       ▼
[Task 6: Human Behavioral Biometrics Engine & Smart Publisher]
  ├── AliasMode Browser Adapter (CDP WebSocket connection to local port 50325)
  ├── HumanBehaviorService (Inertial scroll, 80-220ms typing, 3% typo + backspace, 0.6-1.4s micro-pauses, Bezier curves)
  ├── Channel Lifecycle Guard (warming vs ready_to_post vs cooldown vs captcha_blocked)
  └── Emergency Captcha Guard (Immediate stop, screenshot to screenshots/, Telegram alert)
       │
       ▼
[Task 7: Comment Engagement & Conversion Agent]
  ├── CommentScanner (scans video comments on TikTok)
  ├── Intent Classifier (ASK_PRICE, ASK_MATERIAL_USAGE, COMPLAINT, OTHER)
  └── KOC Reply Generator (guides customer to yellow cart icon with ToneValidator verification)
       │
       ▼
[Task 8: Hermes Orchestrator, CLI Runner & E2E Dry-run]
  ├── LangGraph StateGraph coordination
  ├── main.py CLI runner (--mode bot, --mode scout, --mode dry-run, --mode daemon)
  └── 100% Comprehensive Test Suite (pytest tests/ -v)
```

1. **Task 1 Foundation**: Without async database models and `ToneValidator`, none of the downstream agents can persist state or ensure compliance with TikTok Vietnam natural tone requirements.
2. **Tasks 2 & 3 Specialization**: The two niches (Women's Fashion and Home Utilities) have radically different evaluation criteria:
   - Fashion requires body-shape hacks and zero tolerance for fake brands (`Zara`, `Chanel`, `Gucci`).
   - Home Utilities requires labor-saving utility and instant Before/After visual proof within 3s.
3. **Task 4 Control Plane**: Human-in-the-Loop approval is strictly required before any video production or publishing occurs. The Telegram forum topic structure ensures clean separation between the two niches.
4. **Task 5 Production**: Once approved, video generation re-creates the asset using natural Vietnamese voices (`edge-tts`) and transforms video hashes via FFmpeg to avoid duplicate content penalties.
5. **Task 6 Anti-Detection**: Automated publishers are instantly banned if they display robotic traits. AliasMode combined with `human_behavior.py` (biometric typing, 3% typo rate, micro-pauses, warmup sessions) mimics a human creator. The Captcha guard ensures no automated solving triggers a permanent ban.
6. **Task 7 Conversion**: Publishing is only half the battle; closing sales requires responding to comments with helpful advice and explicit instructions to click the yellow cart on the bottom-left.
7. **Task 8 Orchestration**: Hermes links all agents into a unified State Graph, with `main.py` enabling both CLI dry-run verification and 24/7 autonomous daemon operation.

---

## 3. Concrete Architectural Specification & Interfaces

### 3.1 Module & File Hierarchy

```
affiliate/
├── .env.example
├── config.yaml
├── main.py
├── README.md
├── scripts/
│   └── get_telegram_ids.py
├── src/
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py             # Pydantic AppConfig, NicheConfig, BrowserConfig
│   │   ├── prompt_templates.py   # Specialized LLM prompts (Gemini API)
│   │   └── tone_validator.py     # Anti-robotic rules & brand policy validator
│   ├── database/
│   │   ├── __init__.py
│   │   ├── models.py             # SQLAlchemy 2.0 ORM (7 tables, cross-dialect JSON)
│   │   └── session.py            # Async engine, sessionmaker, get_db generator
│   ├── services/
│   │   ├── __init__.py
│   │   ├── kalodata_client.py    # Kalopilot async submit & poll client
│   │   ├── tiktok_scraper.py     # yt-dlp metadata extractor
│   │   ├── video_downloader.py   # Clean video downloader
│   │   ├── audio_transcriber.py  # Whisper transcriber
│   │   ├── script_generator.py   # Hook 3s + KOC script generator
│   │   ├── tts_service.py        # edge-tts async voice synthesizer
│   │   ├── video_processor.py    # FFmpeg transforms & remuxer
│   │   ├── browser_adapter.py    # AliasMode Local API & CDP connector
│   │   ├── human_behavior.py     # Biometric scrolling, typing, bezier, captcha
│   │   └── comment_scanner.py    # TikTok video comment scraper
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base_scout.py         # Base scout filtering logic
│   │   ├── fashion_scout.py      # FashionScoutAgent
│   │   ├── homelife_scout.py     # HomeLifeScoutAgent
│   │   ├── video_studio.py       # VideoStudioAgent
│   │   ├── smart_publisher.py    # SmartPublisher agent
│   │   ├── comment_agent.py      # CommentAgent (intent & reply)
│   │   └── hermes_orchestrator.py# LangGraph StateGraph coordinator
│   └── bot/
│       ├── __init__.py
│       ├── telegram_bot.py       # aiogram 3.x Bot instance & setup
│       ├── keyboards.py          # Inline keyboards for approval & alerts
│       └── handlers.py           # Commands & callback query handlers
└── tests/
    ├── conftest.py               # Shared mock fixtures (DB, Telegram, Playwright, API)
    ├── test_config.py            # Task 1 tests
    ├── test_database.py          # Task 1 tests
    ├── test_kalodata_client.py   # Task 2 tests
    ├── test_tiktok_scraper.py    # Task 2 tests
    ├── test_specialist_scouts.py # Task 3 tests
    ├── test_telegram_bot.py      # Task 4 tests
    ├── test_script_generator.py  # Task 5 tests
    ├── test_tts_service.py       # Task 5 tests
    ├── test_video_processor.py   # Task 5 tests
    ├── test_browser_adapter.py   # Task 6 tests
    ├── test_human_behavior.py    # Task 6 tests
    ├── test_smart_publisher.py   # Task 6 tests
    ├── test_comment_agent.py     # Task 7 tests
    ├── test_hermes_flow.py       # Task 8 tests
    └── test_e2e_dryrun.py        # Task 8 tests
```

---

### 3.2 Exact Class Signatures & Data Contracts

#### 1. Configuration & Core
```python
# src/core/config.py
class BrowserConfig(BaseModel):
    provider: str = "aliasmode"
    api_url: str = "http://127.0.0.1:50325"
    headless: bool = False

class NicheConfig(BaseModel):
    niche_id: str
    name: str
    telegram_topic_id: Optional[int] = None
    min_price: float = 50000.0
    min_commission_rate: float = 0.10
    banned_keywords: List[str] = Field(default_factory=list)
    persona: Dict[str, Any] = Field(default_factory=dict)

class AppConfig(BaseModel):
    environment: str = "development"
    database_url: str
    redis_url: str
    telegram_bot_token: str
    admin_telegram_id: int
    gemini_api_key: Optional[str] = None
    browser: BrowserConfig
    niches: List[NicheConfig]

def load_config(path: str = "config.yaml") -> AppConfig: ...
```

```python
# src/core/tone_validator.py
class ToneValidator:
    BANNED_ROBOTIC_PHRASES: List[str] = [
        "xin chào quý khách", "tôi là trợ lý ai", "sản phẩm này rất tốt và tiện ích",
        "kính thưa quý vị", "chúng tôi xin giới thiệu", "rất mong nhận được sự ủng hộ",
        "hãy liên hệ với chúng tôi", "đây là một giải pháp hoàn hảo"
    ]
    BANNED_COUNTERFEIT_KEYWORDS: List[str] = [
        "zara", "chanel", "gucci", "dior", "louis vuitton", "rep 1:1", "super fake", "fake 1:1"
    ]
    BANNED_EXTREME_CLAIMS: List[str] = [
        "trị dứt điểm 100%", "vĩnh viễn không bám bẩn", "cam kết khỏi 100%", "hoàn toàn không tái phát"
    ]
    MANDATORY_KOC_CUES: List[str] = [
        "chị em", "bà nào", "tậu", "giỏ hàng", "mã freeship", "góc trái", "bấm ngay", "mê", "ưng"
    ]

    @classmethod
    def validate(cls, text: str) -> bool: ...
    @classmethod
    def check_violations(cls, text: str) -> List[str]: ...
```

#### 2. Database Models (Cross-Dialect JSON)
```python
# src/database/models.py
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, Float, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.dialects.postgresql import JSONB

# Compatible with SQLite in tests and PostgreSQL in production
JSON_TYPE = JSON().with_variant(JSONB, "postgresql")

class Base(DeclarativeBase):
    pass

class Niche(Base):
    __tablename__ = "niches"
    niche_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

class Channel(Base):
    __tablename__ = "channels"
    channel_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    niche_id: Mapped[str] = mapped_column(ForeignKey("niches.niche_id", ondelete="CASCADE"))
    browser_provider: Mapped[str] = mapped_column(String(30), default="aliasmode")
    browser_profile_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    proxy_url: Mapped[Optional[str]] = mapped_column(String(255))
    lifecycle_status: Mapped[str] = mapped_column(String(30), default="warming") # warming, ready_to_post, cooldown, captcha_blocked
    warmup_days_completed: Mapped[int] = mapped_column(Integer, default=0)
    last_posted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    max_posts_per_day: Mapped[int] = mapped_column(Integer, default=2)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

class Product(Base):
    __tablename__ = "products"
    product_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    niche_id: Mapped[str] = mapped_column(ForeignKey("niches.niche_id"))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    commission_rate: Mapped[float] = mapped_column(Float, default=0.1)
    product_url: Mapped[str] = mapped_column(Text, nullable=False)
    sales_count: Mapped[int] = mapped_column(Integer, default=0)
    rating: Mapped[float] = mapped_column(Float, default=5.0)
    evaluation_data: Mapped[Dict[str, Any]] = mapped_column(JSON_TYPE, default=dict)
    status: Mapped[str] = mapped_column(String(30), default="pending") # pending, approved, rejected, published
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

class VideoJob(Base):
    __tablename__ = "video_jobs"
    job_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.product_id"))
    niche_id: Mapped[str] = mapped_column(ForeignKey("niches.niche_id"))
    channel_id: Mapped[Optional[str]] = mapped_column(ForeignKey("channels.channel_id"))
    source_video_url: Mapped[str] = mapped_column(Text, nullable=False)
    script: Mapped[Optional[str]] = mapped_column(Text)
    audio_path: Mapped[Optional[str]] = mapped_column(String(255))
    output_video_path: Mapped[Optional[str]] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(30), default="created") # created, scripted, audio_generated, rendered, publishing, published, failed
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
```

#### 3. Scout & Scraper Services
```python
# src/services/kalodata_client.py
class KalodataClient:
    SUBMIT_URL = "https://www.kalodata.com/api/pilot/skill/ext/v1/chat/async/submit"
    RESULT_URL = "https://www.kalodata.com/api/pilot/skill/ext/v1/chat/async/result"

    def __init__(self, token: Optional[str] = None): ...
    def get_token(self) -> str: ... # checks ~/.kalopilot/token or env
    async def submit_query(self, query: str, task_id: Optional[str] = None) -> str: ...
    async def poll_result(self, task_id: str, poll_interval: float = 2.0, max_attempts: int = 15) -> Dict[str, Any]: ...
    async def get_top_products(self, category_id: str, limit: int = 10) -> List[Dict[str, Any]]: ...

# src/services/tiktok_scraper.py
@dataclass
class TikTokVideoMeta:
    video_id: str
    video_url: str
    title: str
    author: str
    views: int
    likes: int
    comments: int
    shares: int
    anchor_product: Optional[Dict[str, Any]]
    download_url: Optional[str]
    description: str

class TikTokScraper:
    async def get_recent_videos(self, channel_url: str, limit: int = 5) -> List[TikTokVideoMeta]: ...
    async def extract_anchor_product(self, video_url: str) -> Optional[Dict[str, Any]]: ...
    async def download_video_metadata(self, video_url: str) -> TikTokVideoMeta: ...
```

#### 4. Specialist Scouts
```python
# src/agents/fashion_scout.py & homelife_scout.py
@dataclass
class SpecialistEvaluation:
    product_id: str
    niche_id: str
    passed_filter: bool
    score: float # 0 - 100
    hook_angle: str
    target_audience: str
    pros: List[str]
    cons: List[str]
    viral_factor: str
    rejection_reason: Optional[str] = None

class FashionScoutAgent:
    async def evaluate_product(self, item: Dict[str, Any]) -> SpecialistEvaluation: ...

class HomeLifeScoutAgent:
    async def evaluate_product(self, item: Dict[str, Any]) -> SpecialistEvaluation: ...
```

#### 5. Telegram Bot
```python
# src/bot/telegram_bot.py & handlers.py
class TelegramCommandCenter:
    def __init__(self, bot: Bot, dp: Dispatcher, config: AppConfig): ...
    async def start(self): ...
    async def send_product_card(self, niche_id: str, evaluation: SpecialistEvaluation, product: Product) -> Message: ...
    async def send_captcha_alarm(self, channel_id: str, screenshot_path: str) -> Message: ...
```

#### 6. Video Studio Pipeline
```python
# src/services/script_generator.py
class ScriptGenerator:
    async def generate_remix_script(self, original_transcript: str, product_meta: Dict[str, Any], niche: str) -> Dict[str, Any]:
        """Returns {'hook': str, 'body': str, 'cta': str, 'full_script': str, 'subtitles': List[Dict]}"""

# src/services/tts_service.py
class TTSService:
    async def generate_speech(self, text: str, output_path: str, voice: str = "vi-VN-HoaiMyNeural", rate: str = "+0%") -> str: ...

# src/services/video_processor.py
class VideoProcessor:
    async def process_video(self, raw_video_path: str, audio_path: str, output_path: str, options: Optional[Dict[str, Any]] = None) -> str: ...

# src/agents/video_studio.py
class VideoStudioAgent:
    async def produce_video(self, job_id: str) -> str: ...
```

#### 7. Biometrics Engine & Smart Publisher
```python
# src/services/browser_adapter.py
class BrowserAdapter:
    def __init__(self, api_url: str = "http://127.0.0.1:50325"): ...
    async def create_profile(self, name: str, proxy: Optional[str] = None) -> str: ...
    async def start_browser(self, profile_id: str) -> Tuple[BrowserContext, Page, str]: ...
    async def stop_browser(self, profile_id: str) -> None: ...

# src/services/human_behavior.py
class HumanBehaviorService:
    async def human_scroll(self, page: Page, steps: int = 5, direction: str = "down") -> None: ...
    async def human_type(self, page: Page, selector: str, text: str, typo_rate: float = 0.03) -> None: ...
    async def human_move_and_click(self, page: Page, selector: str) -> None: ...
    async def warmup_feed_session(self, page: Page, duration_seconds: int = 180) -> None: ...
    async def detect_and_handle_captcha(self, page: Page) -> bool: ...

# src/agents/smart_publisher.py
@dataclass
class PublishResult:
    success: bool
    video_url: Optional[str] = None
    captcha_triggered: bool = False
    error: Optional[str] = None

class SmartPublisher:
    async def publish_video(self, job_id: str) -> PublishResult: ...
```

#### 8. Comment Engagement & Hermes Orchestrator
```python
# src/agents/comment_agent.py
class CommentIntent(str, Enum):
    ASK_PRICE = "ask_price"
    ASK_MATERIAL_USAGE = "ask_material_usage"
    COMPLAINT = "complaint"
    OTHER = "other"

class CommentAgent:
    def classify_intent(self, comment: str) -> CommentIntent: ...
    async def generate_reply(self, comment: str, product_meta: Dict[str, Any], persona: Optional[Dict[str, Any]] = None) -> str: ...
    async def process_pending_comments(self) -> int: ...

# src/agents/hermes_orchestrator.py
class HermesOrchestrator:
    def build_state_graph(self) -> CompiledStateGraph: ...
    async def run_pipeline_step(self, step_name: str, payload: Dict[str, Any]) -> Dict[str, Any]: ...
```

---

## 4. Acceptance Criteria & Test Fixtures Strategy (TDD)

### Task-by-Task Acceptance Matrix

| Task | Test File | Key Mock Fixtures Required | Acceptance Criteria |
|------|-----------|----------------------------|---------------------|
| **Task 1** | `tests/test_config.py`<br/>`tests/test_database.py` | - In-memory SQLite async engine (`sqlite+aiosqlite:///:memory:`)<br/>- Sample `config.yaml` with 2 niches | - `load_config()` successfully parses 2 niches and aliasmode browser provider.<br/>- SQLAlchemy models instantiate, tables exist in metadata, `lifecycle_status` column is present on `Channel`.<br/>- `ToneValidator.validate()` catches all AI robotic phrases and bans fake brands. |
| **Task 2** | `tests/test_kalodata_client.py`<br/>`tests/test_tiktok_scraper.py` | - Mock `aiohttp.ClientSession` for submit and poll endpoints<br/>- Mock `yt_dlp.YoutubeDL` extract_info return payload | - `KalodataClient` handles submit & poll workflow; handles missing token gracefully.<br/>- `TikTokScraper` extracts `TikTokVideoMeta` with views, author, anchor product without network calls.<br/>- `BaseScoutAgent` filters out products below price / commission thresholds. |
| **Task 3** | `tests/test_specialist_scouts.py` | - Mock Gemini API client (`google.genai` / AsyncMock)<br/>- Sample Fashion candidates (Zara fake vs Unbranded shapewear)<br/>- Sample HomeLife candidates (Labor-saving vs False medical claim) | - `FashionScoutAgent` flags and rejects "Zara", "rep 1:1" items; passes body-flattering items.<br/>- `HomeLifeScoutAgent` rejects "trị dứt điểm 100%"; approves Before/After cleaning gadget.<br/>- Outputs structured `SpecialistEvaluation` with scores 0-100. |
| **Task 4** | `tests/test_telegram_bot.py` | - Mock `aiogram.Bot` with AsyncMock `send_message`, `send_photo`<br/>- Mock `aiogram.types.CallbackQuery` and `Message` | - Product cards are formatted with topic thread ID and inline buttons.<br/>- `approve_product:<id>` callback transitions product status to approved.<br/>- Commands `/test_scout`, `/test_video`, `/test_reply`, `/status`, `/warmup` invoke corresponding service methods. |
| **Task 5** | `tests/test_script_generator.py`<br/>`tests/test_tts_service.py`<br/>`tests/test_video_processor.py` | - Mock `edge_tts.Communicate.save`<br/>- Mock `asyncio.create_subprocess_exec` for FFmpeg execution<br/>- Sample transcripts and product metadata | - `ScriptGenerator` produces Hook 3s + KOC body + yellow cart CTA passing `ToneValidator`.<br/>- `TTSService` generates speech with `vi-VN-HoaiMyNeural`.<br/>- `VideoProcessor` runs FFmpeg with speed, crop, and BGM flags without crashing. |
| **Task 6** | `tests/test_browser_adapter.py`<br/>`tests/test_human_behavior.py`<br/>`tests/test_smart_publisher.py` | - Mock Playwright `Page`, `BrowserContext`, `Keyboard`<br/>- Mock AliasMode API responses (`/api/profile/create`, `/api/profile/start`) | - `human_type` simulates 80-220ms delays, micro-pauses, and 3% typo with Backspace.<br/>- `warmup_feed_session` simulates random browsing for configured duration.<br/>- `detect_and_handle_captcha` detects captcha element, halts, triggers screenshot and Telegram alert.<br/>- `SmartPublisher` forbids posting for channels in `warming` state. |
| **Task 7** | `tests/test_comment_agent.py` | - Mock `CommentScanner` output<br/>- Test comment strings for price, material, complaints | - Correctly classifies comment intent into `ASK_PRICE`, `ASK_MATERIAL_USAGE`, `COMPLAINT`.<br/>- Generates natural KOC reply directing buyer to the bottom-left yellow shopping cart.<br/>- Passes `ToneValidator` check. |
| **Task 8** | `tests/test_hermes_flow.py`<br/>`tests/test_e2e_dryrun.py` | - End-to-end mocked pipeline state graph<br/>- Mock CLI args for `main.py` | - LangGraph StateGraph executes nodes in sequence with conditional branches.<br/>- `main.py --mode dry-run` completes E2E flow with exit code 0.<br/>- Entire test suite `pytest tests/ -v` executes 100% PASS. |

---

## 5. Caveats

1. **PostgreSQL vs SQLite In-Memory Testing**: In production, `asyncpg` and PostgreSQL `JSONB` are used. In tests, SQLite is used for high-speed, zero-dependency CI runs. Models MUST use `JSON().with_variant(JSONB, "postgresql")` to prevent SQLite compile errors.
2. **AliasMode Local Service**: AliasMode operates as an external desktop app exposing port `50325`. During unit tests, all HTTP requests to this port and Playwright CDP WebSocket endpoints must be mocked using `aioresponses` or `unittest.mock.AsyncMock`.
3. **Kalopilot Token**: The production token is expected at `~/.kalopilot/token`. Unit tests must mock the Kalodata client network calls completely so tests run without real tokens or credit consumption.
4. **FFmpeg Binary**: `ffmpeg` and `ffprobe` are expected on the host machine. In CI or test environments where FFmpeg might be missing, subprocess calls must be mocked to test command string building without failing on process execution.
5. **Edge-TTS Network**: `edge-tts` communicates with Microsoft's speech service. Tests must mock `Communicate` to avoid external network dependency during testing.

---

## 6. Conclusion

The specification for **AMAS v1.4.0** across `SYSTEM_SPEC.md`, `ORIGINAL_REQUEST.md`, and `docs/superpowers/plans/2026-11-10-autonomous-affiliate-system.md` is complete, coherent, and highly detailed. 

Every task from Task 1 through Task 8 has clearly defined file paths, module boundaries, database schemas, Pydantic contracts, and strict anti-detect / KOC tone constraints. The testing strategy using mock fixtures allows 100% TDD pass rate on greenfield setup before live external service connection.

The implementation team can proceed directly to execute Task 1 through Task 8 following the TDD methodology defined in the plan.

---

## 7. Verification Method

To independently verify the completeness and accuracy of this survey:

1. **Verify Interface & Model Coverage**:
   Inspect `tests/test_config.py` and `tests/test_database.py` against Section 3.1 & 3.2. Ensure all 7 models (`Niche`, `Channel`, `Competitor`, `Product`, `VideoJob`, `VideoComment`, `Metric`) and their column names match `SYSTEM_SPEC.md` § 5.
2. **Verify Biometrics Rigor**:
   Inspect `src/services/human_behavior.py` against `SYSTEM_SPEC.md` § 3 to verify the 5 biometric rules (inertia scroll, 80-220ms typing with 3% typos and backspace, Bezier curves, warmup session, emergency captcha stop).
3. **Verify Test Execution Plan**:
   Execute `pytest tests/ -v` once tasks are scaffolded to verify that each task's test file fails before implementation and passes after implementation.
