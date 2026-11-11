# Autonomous Multi-Agent TikTok Affiliate System (AMAS v1.4.0)
# E2E Test Infrastructure & Test Plan Specification

> **Document:** `TEST_INFRA.md`  
> **Status:** Active / Authoritative Test Architecture  
> **Target Version:** AMAS v1.4.0  
> **Test Framework:** Pytest 9.x + `pytest-asyncio`  

---

## 1. Testing Philosophy & Core Principles

The End-to-End (E2E) testing track for AMAS v1.4.0 adheres to four immutable engineering principles:

1. **Opaque-Box & Requirement-Driven**:
   Tests are derived strictly from user requirements in `ORIGINAL_REQUEST.md`, architectural specifications in `SYSTEM_SPEC.md`, and the Feature Inventory in `PROJECT.md`. Tests evaluate system behavior, input-output transformations, and interface contracts rather than white-box private state.

2. **Independence & Hermetic Execution**:
   Tests are fully self-contained. No live third-party external credentials (e.g. live TikTok logins, paid Kalodata API keys, or active Telegram bot tokens) are required to execute the test suite. External boundaries (Kalodata Pilot API, TikTok Scraper CDP, AliasMode Browser API, Telegram Bot API, FFmpeg binary, and Faster-Whisper) are mediated by high-fidelity contract adapters and mock fixtures that emulate exact network and protocol behaviors.

3. **Progressive Testability**:
   The E2E test harness is designed to execute cleanly across all development phases. When real modules in `src/` are present, tests dynamically interface with them; when modules are under construction or when simulating external integration failure modes, contract adapters ensure deterministic verification of system state graphs and business rules.

4. **Adversarial Verification & Zero-Flake Guarantee**:
   The suite aggressively validates boundary conditions: counterfeit product keywords, robotic tone cliches, extreme pricing anomalies, anti-detect browser captcha interrupts, rate limits, network timeouts, and concurrent database lock isolation.

---

## 2. 4-Tier Test Architecture

```
tests/e2e/
├── conftest.py                   # Central fixtures, mock adapters, in-memory DB, sample payloads
├── test_tier1_features.py        # Tier 1: Isolated capability tests for F01 through F29
├── test_tier2_boundaries.py      # Tier 2: Boundary, stress, adversarial, and edge cases
├── test_tier3_combinations.py    # Tier 3: Pairwise multi-agent pipeline transitions
└── test_tier4_scenarios.py       # Tier 4: Full lifecycle real-world campaign simulations
```

### Tier 1: Feature Isolation (F01 – F29)
Verifies that each atomic capability works according to its specification:
- **Core (F01–F04)**: Config loading, async DB session, models schema, tone validator.
- **Scout (F05–F09)**: Kalodata async client, TikTok scraper, base scout, fashion scout, homelife scout.
- **Telegram Command Center (F10–F12)**: Forum topic routing, 1-tap inline buttons, command handlers.
- **Video Studio (F13–F18)**: Video downloader, audio transcriber, KOC script generator, TTS synthesis, FFmpeg evasion, video studio agent.
- **Smart Publisher & Biometrics (F19–F25)**: AliasMode adapter, inertial scrolling, biometric typing, Bezier cursor curves, feed warmup, captcha guard, publisher agent.
- **Comment Engagement (F26–F27)**: Comment scanner, intent classification & KOC conversion reply.
- **Orchestration & CLI (F28–F29)**: Hermes LangGraph state graph, CLI runner (`--mode`).

### Tier 2: Boundary & Corner Cases
Stress-tests resilience against malformed, malicious, or extreme environmental conditions:
- Empty strings, unicode control characters, and SQL injection strings in captions and comments.
- Extreme pricing (0 VND, negative, billions) and 0% / 100% commission rates.
- Trademark infringement (Chanel, Gucci, Zara, "rep 1:1", "super fake") and exaggerated claims ("trị dứt điểm 100%").
- Immediate Captcha detection, emergency Telegram alert dispatch, and channel lock.
- Network timeouts, HTTP 401 token expirations, and browser CDP disconnects.
- Concurrency and transaction isolation under burst load.

### Tier 3: Pairwise Multi-Agent Combinations
Tests the handoffs between interconnected agents:
- **Combination 1**: Base Scout $\rightarrow$ Specialist Scout (Fashion/HomeLife) data handoff.
- **Combination 2**: Specialist Scout Evaluation $\rightarrow$ Telegram Command Center Card formatting $\rightarrow$ Inline Callback (`approve_product`).
- **Combination 3**: Approved Product $\rightarrow$ Video Studio (Script $\rightarrow$ TTS $\rightarrow$ Processor) $\rightarrow$ Rendered Output.
- **Combination 4**: Rendered Video $\rightarrow$ Smart Publisher (Warmup $\rightarrow$ Biometric Typing $\rightarrow$ Anchor Link).
- **Combination 5**: Published Video $\rightarrow$ Comment Scanner $\rightarrow$ Intent Classification $\rightarrow$ KOC Reply Generation.

### Tier 4: Realistic End-to-End Scenarios
Executes complete business workflows simulating full production runs:
- **Scenario A (Fashion Viral Dress Campaign)**: Sourcing viral dress on Kalodata, specialist evaluation, Telegram approval, KOC script generation with Hook 3s, synthetic rendering, human publisher warmup, and post.
- **Scenario B (HomeLife Smart Cleaner Campaign)**: Before/After 3s hook video generation, labor-saving utility scoring, Telegram 1-tap approval, render, and automated upload.
- **Scenario C (Emergency Captcha Halt & Alert)**: Live upload simulation encounters TikTok slider captcha; Publisher immediately aborts, takes screenshot, dispatches urgent Telegram alert, and sets channel state to `captcha_blocked`.
- **Scenario D (Comment Conversion into Yellow Cart Sales)**: Inbound comments ("giá bao nhiêu shop", "chất vải gì thế", "giao hàng lâu") classified by intent and converted to friendly KOC replies directing buyers to the yellow cart.

---

## 3. Feature Inventory Coverage Matrix (F01 – F29)

| Feature ID | Feature Name | Primary Contract / Interface | Tier 1 Test | Tier 2 Boundary | Tier 3 Interaction | Tier 4 Scenario |
|:----------:|:-------------|:-----------------------------|:-----------:|:---------------:|:------------------:|:---------------:|
| **F01** | Central Config Loader | `load_config(path: str) -> AppConfig` | `test_f01_config_loader` | Empty/malformed YAML | Scout/Bot config flow | Fashion & HomeLife campaigns |
| **F02** | Async DB Engine & Session | `get_async_engine()`, `get_db()` | `test_f02_database_session` | Concurrency & rollback | DB transaction in pipeline | Channel state updates |
| **F03** | Domain Data Models | `Niche`, `Channel`, `Product`, `VideoJob`, `VideoComment` | `test_f03_domain_models` | Constraint violations | Cross-table relationships | Full lifecycle DB persistence |
| **F04** | Anti-Robotic ToneValidator | `ToneValidator.validate(text: str) -> bool` | `test_f04_tone_validator` | AI cliches, counterfeit fakes | Script & comment validation | KOC conversion replies |
| **F05** | Kalodata Async Client | `KalodataClient.get_top_products(category_id, limit)` | `test_f05_kalodata_client` | 401 token, empty results | Scout pipeline input | Sourcing viral products |
| **F06** | TikTok Scraper & Metadata | `TikTokScraper.download_video_metadata(url)` | `test_f06_tiktok_scraper` | Invalid URL, missing video | Base scout candidate ingest | Video metadata extraction |
| **F07** | Base Scout Agent | `BaseScoutAgent.discover_candidates(niche_id)` | `test_f07_base_scout` | Price bounds, 0 commission | Output to Specialist Scouts | Initial candidate discovery |
| **F08** | Fashion Scout Agent | `FashionScoutAgent.evaluate_product(item)` | `test_f08_fashion_scout` | Fake brands, body hacks | Specialist -> Telegram card | Fashion Dress Campaign |
| **F09** | HomeLife Scout Agent | `HomeLifeScoutAgent.evaluate_product(item)` | `test_f09_homelife_scout` | Exaggerated claims, Before/After | Specialist -> Telegram card | Smart Cleaner Campaign |
| **F10** | Forum Topic Routing | `route_topic(niche_id: str) -> int` | `test_f10_topic_routing` | Unknown niche ID fallback | Telegram card delivery | Topic-specific notification |
| **F11** | 1-Tap Approval Keyboards | `get_approval_keyboard(product_id: str)` | `test_f11_approval_keyboards` | Malformed product IDs | Bot callback -> Studio trigger | Human-in-the-Loop review |
| **F12** | Bot Command Center | Bot command dispatch (`/test_scout`, etc.) | `test_f12_bot_command_center` | Unauthorized user, bad args | Admin command invocation | End-to-end command dry-run |
| **F13** | Video Downloader | `VideoDownloader.download_video(url)` | `test_f13_video_downloader` | 404, corrupted stream | Downloader -> Whisper | Sourcing clean competitor video |
| **F14** | Audio Transcriber | `AudioTranscriber.transcribe(audio_path)` | `test_f14_audio_transcriber` | Silent audio, noise | Transcriber -> Script Gen | Competitor script extraction |
| **F15** | KOC Script Generator | `ScriptGenerator.generate_script(meta, persona)` | `test_f15_script_generator` | Missing hooks, long captions | Script -> TTS & ToneValidator | Viral KOC script rewrite |
| **F16** | Natural TTS Service | `TTSService.synthesize(text, voice)` | `test_f16_tts_service` | Empty text, special chars | TTS audio -> FFmpeg remux | Vietnamese voice synthesis |
| **F17** | Video Processor | `VideoProcessor.remix_video(...)` | `test_f17_video_processor` | Codec mismatch, bad aspect | Studio pipeline integration | Evasion remuxing (crop/speed/BGM) |
| **F18** | Video Studio Agent | `VideoStudioAgent.produce_video(job_id)` | `test_f18_video_studio_agent` | Pipeline step crash recovery | Job status: ready -> rendered | Complete video production |
| **F19** | AliasMode Browser Adapter | `BrowserAdapter.start_browser(profile_id)` | `test_f19_browser_adapter` | Connection refused, timeout | Browser lifecycle management | Headless/CDP session launch |
| **F20** | Inertial Human Scrolling | `HumanBehaviorService.human_scroll(page, steps)` | `test_f20_human_scrolling` | Negative steps, zero distance | Pre-posting feed session | Natural feed browsing |
| **F21** | Biometric Typing Sim | `HumanBehaviorService.human_type(page, sel, text)`| `test_f21_biometric_typing` | High typo rate, empty string | Caption entry during upload | Studio caption typing |
| **F22** | Bezier Mouse Movement | `HumanBehaviorService.human_move_and_click(page)` | `test_f22_bezier_mouse` | Off-screen target bounds | Navigation to Creator Center | Upload button click |
| **F23** | Pre-posting Feed Warmup | `HumanBehaviorService.warmup_feed_session(...)` | `test_f23_feed_warmup` | Interrupted session | Warmup prior to upload | 3-5 min feed browsing |
| **F24** | Emergency Captcha Guard | `detect_and_handle_captcha(page)` | `test_f24_captcha_guard` | Captcha frame detection | Publisher abort -> Telegram alarm | Captcha emergency halt scenario |
| **F25** | Smart Publisher Agent | `SmartPublisher.publish_video(job_id)` | `test_f25_smart_publisher` | Channel in 'warming' status | Studio output -> Published video | Complete upload & anchor tag |
| **F26** | Video Comment Scanner | `CommentScanner.scan_comments(video_id)` | `test_f26_comment_scanner` | Zero comments, deleted video | Video -> Comment pipeline | Comment harvesting |
| **F27** | Intent & KOC Reply Agent | `CommentAgent.classify_intent()`, `generate_reply()` | `test_f27_comment_agent` | Unclear query, toxic input | Scanner -> Reply generation | Comment conversion to cart |
| **F28** | Hermes State Coordinator | `HermesOrchestrator.build_state_graph()` | `test_f28_hermes_state` | Invalid transition, cycle | Multi-agent state machine | Complete autonomous graph |
| **F29** | CLI Runner & Daemon | `main.py --mode [bot|scout|dry-run|daemon]` | `test_f29_cli_runner` | Unknown args, exit codes | CLI invocation | System startup & dry-run |

---

## 4. Test Execution & Quality Gates

### Execution Command
```bash
pytest tests/e2e/ -v --tb=short
```

### Coverage Thresholds
- **Tier 1 Feature Pass Rate**: 100% (29/29 features verified).
- **Tier 2 Boundary Pass Rate**: 100% (Zero unhandled exceptions; expected validation rejections).
- **Tier 3 Combination Pass Rate**: 100% (All multi-agent handoffs validated).
- **Tier 4 Scenario Pass Rate**: 100% (All 4 end-to-end production simulations successful).
- **Flakiness Threshold**: 0% (Hermetic execution via deterministic seed and contract mocks).
