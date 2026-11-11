# Project: AMAS v1.4.0 (Autonomous Multi-Agent TikTok Affiliate System)

## Architecture
AMAS v1.4.0 is an autonomous, event-driven multi-agent system executing product scouting, AI video generation, human-like automated publishing, and customer comment conversion across two pilot niches: Women's Fashion (`thoi_trang_nu`) and Home Utilities (`do_gia_dung`).

```
[Kalodata / TikTok Scraper]
            │ (Raw Products)
            ▼
[Base & Specialist Scouts (Fashion & HomeLife)]
            │ (SpecialistEvaluation)
            ▼
[Telegram Command Center] ◄── [Human-in-the-Loop 1-Tap Approval]
            │ (Approved Job)
            ▼
[Video Remix Studio (Whisper + edge-tts + FFmpeg)]
            │ (Rendered MP4)
            ▼
[Smart Publisher (AliasMode CDP + Human Biometrics Engine)]
            │ (Published Video)
            ▼
[Comment Engagement Agent (Intent Classification + KOC Response)]
            ▲
            │ (State Coordination)
[Hermes LangGraph Orchestrator]
```

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| F01 | Central Config Loader | Pydantic configuration loader for .env and config.yaml (niches, browser, telegram, redis, db) | M1 | SYSTEM_SPEC § 1, Plan Task 1 |
| F02 | Async DB Engine & Session | Async SQLAlchemy sessionmaker with asyncpg (PostgreSQL) and SQLite test compatibility | M1 | SYSTEM_SPEC § 2, Plan Task 1 |
| F03 | Domain Data Models | 7 core models: Niche, Channel, Competitor, Product, VideoJob, VideoComment, Metric | M1 | SYSTEM_SPEC § 5, Plan Task 1 |
| F04 | Anti-Robotic ToneValidator | Rule-based & regex validator banning AI cliches, counterfeit brands, and exaggerated claims | M1 | Plan Task 1, ORIGINAL_REQUEST § R2 |
| F05 | Kalodata Async Client | Async client submitting queries and polling viral products from Kalodata Pilot API | M2 | Plan Task 2, kalopilot/SKILL.md |
| F06 | TikTok Scraper & Metadata | yt-dlp based metadata and anchor product extractor | M2 | Plan Task 2 |
| F07 | Base Scout Agent | Filtering raw candidates by pricing and commission thresholds | M2 | Plan Task 2 |
| F08 | Fashion Scout Agent | Women's fashion specialist evaluating body hacks and banning fake brands (Zara, Chanel) | M3 | Plan Task 3, ORIGINAL_REQUEST § R1 |
| F09 | HomeLife Scout Agent | Home utilities specialist evaluating 3s Before/After hooks and labor-saving utility | M3 | Plan Task 3, ORIGINAL_REQUEST § R1 |
| F10 | Forum Topic Routing | Routing notifications to dedicated Telegram forum topics (#thoi-trang-nu, #do-gia-dung) | M4 | Plan Task 4, ORIGINAL_REQUEST § R5 |
| F11 | 1-Tap Approval Keyboards | Inline buttons for Human-in-the-Loop review (approve_product / reject_product) | M4 | Plan Task 4, ORIGINAL_REQUEST § R5 |
| F12 | Bot Command Center | Bot commands (/test_scout, /test_video, /test_reply, /status, /create_channel, /warmup) | M4 | Plan Task 4, ORIGINAL_REQUEST § R5 |
| F13 | Video Downloader | Clean watermark-free source video downloader | M5 | Plan Task 5, ORIGINAL_REQUEST § R2 |
| F14 | Audio Transcriber | Whisper speech-to-text audio transcriber | M5 | Plan Task 5, ORIGINAL_REQUEST § R2 |
| F15 | KOC Script Generator | Viral script rewriter with Hook 3s and yellow cart CTA | M5 | Plan Task 5, ORIGINAL_REQUEST § R2 |
| F16 | Natural TTS Service | edge-tts Vietnamese speech synthesis (vi-VN-HoaiMyNeural) | M5 | Plan Task 5, ORIGINAL_REQUEST § R2 |
| F17 | Video Processor | FFmpeg copyright evasion remuxer (speed, crop, BGM -20dB, burn subtitles) | M5 | Plan Task 5, ORIGINAL_REQUEST § R2 |
| F18 | Video Studio Agent | End-to-end video production pipeline coordinator | M5 | Plan Task 5, ORIGINAL_REQUEST § R2 |
| F19 | AliasMode Browser Adapter | Anti-detect browser profile manager and Playwright CDP connector | M6 | Plan Task 6, ORIGINAL_REQUEST § R3 |
| F20 | Inertial Human Scrolling | Mouse wheel scrolling with acceleration curve and reverse overshoot | M6 | Plan Task 6, SYSTEM_SPEC § 3.1 |
| F21 | Biometric Typing Simulation | Keystroke delays 80-220ms, micro-pauses 0.6-1.4s, 3% typo with Backspace correction | M6 | Plan Task 6, SYSTEM_SPEC § 3.2 |
| F22 | Bezier Mouse Movement | Non-linear cubic Bezier mouse curves with jitter | M6 | Plan Task 6, SYSTEM_SPEC § 3.3 |
| F23 | Pre-posting Feed Warmup | 3-5 minute feed browsing session before uploading | M6 | Plan Task 6, SYSTEM_SPEC § 3.4 |
| F24 | Emergency Captcha Guard | Immediate abort, screenshot to screenshots/, Telegram alert on Captcha | M6 | Plan Task 6, SYSTEM_SPEC § 3.5 |
| F25 | Smart Publisher Agent | Automated video upload and showcase anchor attachment guard | M6 | Plan Task 6, ORIGINAL_REQUEST § R3 |
| F26 | Video Comment Scanner | Scrapes recent comments from published videos | M7 | Plan Task 7, ORIGINAL_REQUEST § R6 |
| F27 | Intent & KOC Reply Agent | Classifies comment intent and generates KOC conversion replies | M7 | Plan Task 7, ORIGINAL_REQUEST § R6 |
| F28 | Hermes State Coordinator | LangGraph StateGraph connecting multi-agent workflow | M8 | Plan Task 8, ORIGINAL_REQUEST § R7 |
| F29 | CLI Runner & Daemon | Entrypoint CLI supporting bot, scout, dry-run, and daemon modes | M8 | Plan Task 8, ORIGINAL_REQUEST § R7 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Scaffolding, Config & Database Schema | F01, F02, F03, F04, git init, requirements.txt, conftest.py | none | DONE |
| M2 | Base Scout & Scraper Service | F05, F06, F07 | M1 | DONE |
| M3 | Specialist Scout Agents (Fashion & HomeLife) | F08, F09 | M2 | DONE |
| M4 | Telegram Command Center & 1-Tap Approval | F10, F11, F12 | M1, M3 | DONE |
| M5 | Video Remix & Content Engine | F13, F14, F15, F16, F17, F18 | M1, M4 | DONE |
| M6 | Biometrics Engine & Smart Publisher | F19, F20, F21, F22, F23, F24, F25 | M1, M5 | DONE |
| M7 | Comment Engagement & Conversion Agent | F26, F27 | M1, M6 | DONE |
| M8 | Hermes Orchestrator & E2E Integration | F28, F29 | M1..M7 | DONE |
| M-Final | Final Milestone: 100% E2E Test Suite & Hardening | Phase 1 (Tiers 1-4 E2E Pass: 61/61) + Full Regression (490/490) | M8, TEST_READY.md | DONE |

## Interface Contracts

### 1. Core Config & DB ↔ All Agents
- `load_config(path: str = "config.yaml") -> AppConfig`
- `get_async_engine(database_url: str)`: Returns async engine with `@compiles(JSONB, "sqlite")` hook for SQLite test compatibility.
- `get_db() -> AsyncGenerator[AsyncSession, None]`: Context manager for isolated DB transactions.
- `ToneValidator.validate(text: str) -> bool`: Pure validator, returns False if text contains banned robotic or counterfeit phrases.

### 2. Scout Pipeline ↔ Telegram Command Center
- `KalodataClient.get_top_products(category_id: str, limit: int) -> List[Dict]`
- `TikTokScraper.download_video_metadata(video_url: str) -> TikTokVideoMeta`
- `FashionScoutAgent.evaluate_product(item: Dict) -> SpecialistEvaluation`
- `HomeLifeScoutAgent.evaluate_product(item: Dict) -> SpecialistEvaluation`
- `SpecialistEvaluation`: dataclass (`product_id`, `niche_id`, `passed_filter: bool`, `score: float`, `hook_angle: str`, `target_audience: str`, `pros: List[str]`, `cons: List[str]`, `viral_factor: str`, `rejection_reason: Optional[str]`)

### 3. Telegram Bot ↔ Video Studio Pipeline
- Inline Callback: `approve_product:<id>` -> Updates `Product.status = 'approved'`, triggers `VideoStudioAgent.produce_video(job_id)`.
- Inline Callback: `reject_product:<id>` -> Updates `Product.status = 'rejected'`.

### 4. Video Studio ↔ Smart Publisher
- `VideoStudioAgent.produce_video(job_id: str) -> str`: Returns path to processed MP4 file, updates `VideoJob.status = 'rendered'`.
- `SmartPublisher.publish_video(job_id: str) -> PublishResult`: Verifies `Channel.lifecycle_status != 'warming'`, runs feed warmup, uploads video, attaches Showcase anchor.

### 5. Smart Publisher ↔ Telegram Alarm
- `detect_and_handle_captcha(page: Page) -> bool`: If captcha detected, captures screenshot to `screenshots/captcha_<timestamp>.png`, sends emergency alert via Telegram Bot, updates `Channel.lifecycle_status = 'captcha_blocked'`.

### 6. Comment Agent ↔ Database & Channel
- `CommentAgent.classify_intent(comment: str) -> CommentIntent` (`ask_price`, `ask_material_usage`, `complaint`, `other`)
- `CommentAgent.generate_reply(comment: str, product_meta: Dict, persona: Dict) -> str`: Generates KOC reply passing `ToneValidator.validate()`.

### 7. Hermes Orchestrator ↔ CLI
- `HermesOrchestrator.build_state_graph() -> CompiledStateGraph`
- `main.py --mode [bot|scout|dry-run|daemon]`

## Code Layout
```
/Users/tuanlva/Folder/workSpace/affiliate/
├── .env.example
├── config.yaml
├── main.py
├── README.md
├── scripts/
│   └── get_telegram_ids.py
├── src/
│   ├── core/
│   │   ├── config.py
│   │   ├── prompt_templates.py
│   │   └── tone_validator.py
│   ├── database/
│   │   ├── models.py
│   │   └── session.py
│   ├── services/
│   │   ├── kalodata_client.py
│   │   ├── tiktok_scraper.py
│   │   ├── video_downloader.py
│   │   ├── audio_transcriber.py
│   │   ├── script_generator.py
│   │   ├── tts_service.py
│   │   ├── video_processor.py
│   │   ├── browser_adapter.py
│   │   ├── human_behavior.py
│   │   └── comment_scanner.py
│   ├── agents/
│   │   ├── base_scout.py
│   │   ├── fashion_scout.py
│   │   ├── homelife_scout.py
│   │   ├── video_studio.py
│   │   ├── smart_publisher.py
│   │   ├── comment_agent.py
│   │   └── hermes_orchestrator.py
│   └── bot/
│       ├── telegram_bot.py
│       ├── keyboards.py
│       └── handlers.py
└── tests/
    ├── conftest.py
    ├── test_config.py
    ├── test_database.py
    ├── test_kalodata_client.py
    ├── test_tiktok_scraper.py
    ├── test_specialist_scouts.py
    ├── test_telegram_bot.py
    ├── test_script_generator.py
    ├── test_tts_service.py
    ├── test_video_processor.py
    ├── test_browser_adapter.py
    ├── test_human_behavior.py
    ├── test_smart_publisher.py
    ├── test_comment_agent.py
    ├── test_hermes_flow.py
    └── test_e2e_dryrun.py
```
