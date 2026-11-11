# Autonomous Multi-Agent TikTok Affiliate System (AMAS) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Xây dựng hệ sinh thái Multi-Agent tự động hóa tiếp thị liên kết (TikTok Affiliate) chuyên sâu cho 2 ngách Thời Trang Nữ và Đồ Gia Dụng Thông Minh, sử dụng **AliasMode** (trình duyệt ẩn danh mã nguồn mở, 0 chi phí) kết hợp **Human Behavioral Biometrics Engine** (mô phỏng sinh trắc học người thật nghiêm ngặt), tối ưu hóa tỷ lệ chuyển đổi cao với giọng điệu tự nhiên, điều khiển toàn diện qua Telegram Bot.

**Architecture:** Hệ thống sử dụng kiến trúc Niche-Specialist Multi-Agent kết hợp cơ sở dữ liệu PostgreSQL (`asyncpg`), Redis Queue và **AliasMode Anti-Detect Browser** (kết nối Playwright qua CDP). Hai Agent chuyên gia (`FashionScoutAgent`, `HomeLifeScoutAgent`) săn tìm sản phẩm và video viral qua Kalodata + TikTok Scraper; người dùng duyệt 1 chạm qua Telegram Topics; Agent 2 tái sản xuất video tự nhiên kèm giọng đọc `edge-tts` & phụ đề `FFmpeg`; **Agent 3 (Smart Publisher)** điều khiển AliasMode qua bộ mô phỏng sinh trắc học (`human_behavior.py`: lướt dạo feed 3-5 phút, gõ phím ngẫu nhiên có micro-pauses và lỗi typo, cuộn chuột quán tính, còi báo động Captcha); Agent 5 quét và trả lời bình luận theo ngữ cảnh Persona để kích thích chốt đơn giỏ hàng vàng; Agent 4 (Hermes) giám sát tiến trình và tiếp nhận lệnh điều khiển trực tiếp từ Telegram.

**Tech Stack:** Python 3.11+, PostgreSQL 16+, SQLAlchemy 2.0 (Async), `asyncpg`, Redis, `aiogram` 3.x, `yt-dlp`, `faster-whisper`, `edge-tts`, `FFmpeg`, `playwright`, **AliasMode** (Camoufox / Chromium CDP), Google Gemini API (`google-genai`).

**Spec:** `/Users/tuanlva/Folder/workSpace/affiliate/SYSTEM_SPEC.md`

## Global Constraints

- **Python Version:** 3.11+ bắt buộc, sử dụng `asyncio` toàn phần cho I/O (database, web scraping, Telegram bot).
- **Database Engine:** PostgreSQL với `SQLAlchemy 2.0` async session (`asyncpg`) và `JSONB` cho metadata động.
- **Anti-Detect & Biometrics Engine:**
  - Trình duyệt: **AliasMode** (Local API & CDP endpoint).
  - Hành vi sinh trắc học: Bắt buộc đi qua `HumanBehaviorService` (cuộn quán tính, tốc độ gõ 80-220ms, micro-pauses 0.6-1.4s, tỷ lệ gõ nhầm sửa lại 3%, lướt feed ngẫu nhiên 3-5 phút trước khi vào trang đăng bài).
  - An toàn Captcha: Gặp Captcha lập tức dừng lại và chụp màn hình gửi Telegram cho Admin xử lý bằng tay, tuyệt đối không cho bot giải bừa.
- **Natural Conversational Language (Giọng điệu người thật, chống "mùi AI"):**
  - Tuyệt đối cấm các câu máy móc: *"Xin chào quý khách"*, *"Tôi là trợ lý AI"*, *"Sản phẩm này rất tốt và tiện ích"*.
  - Bắt buộc dùng xưng hô gần gũi đúng thị hiếu TikTok Việt Nam: *"Chị em ơi"*, *"Bà nào bụng dưới to bơi hết vào đây"*, *"Từ ngày tậu cái này việc nhà nhàn hẳn"*, *"Chị bấm ngay góc trái nhận mã freeship nha"*.
- **Chính sách TikTok Shop Việt Nam:**
  - Tự động lọc bỏ hoàn toàn các từ khóa hàng nhái (Zara, Chanel, Gucci, rep 1:1, super fake).
  - Tự động lọc bỏ các cam kết y khoa/quảng cáo quá đà (trị dứt điểm 100%, vĩnh viễn không bám bẩn).
- **Human-in-the-Loop:** Không tự ý xuất bản nếu chưa có sự phê duyệt qua nút bấm trên Telegram (trừ khi bật chế độ auto-pilot tường minh).

## Review Focus

1. **Phát hiện Captcha trên TikTok:** Khi xuất hiện iframe hoặc popup Captcha xác minh, hệ thống phải kích hoạt ngay cảnh báo Telegram và chuyển trạng thái kênh sang `captcha_blocked`, không được tiếp tục click.
2. **Hành vi gõ phím phi tự nhiên:** Đảm bảo toàn bộ thao tác nhập caption đều có độ trễ ngẫu nhiên và micro-pauses, cấm hoàn toàn `page.fill()` trực tiếp vào trường text của TikTok Studio.
3. **Quá trình Warm-up kênh mới:** Kênh có trạng thái `warming` chỉ được phép chạy phiên lướt feed xem video tạo lịch sử trust, từ chối mọi yêu cầu đăng bài affiliate cho đến khi chuyển sang `ready_to_post`.
4. **Kalodata API Token Missing/Expired:** Khi token rỗng hoặc 401, bot phải thông báo hướng dẫn lấy token rõ ràng tại `~/.kalopilot/token`.
5. **Ghi đồng thời Database:** Khi Telegram callback xảy ra đúng lúc Scraper lưu hàng loạt sản phẩm, phiên làm việc `AsyncSession` phải cô lập độc lập, không gây tranh chấp lock.

---

### Task 1: Scaffolding, File Môi Trường, Cấu hình trung tâm & Database Schema

**Files:**
- Create: `.env.example`
- Create: `scripts/get_telegram_ids.py`
- Create: `config.yaml`
- Create: `src/core/config.py`
- Create: `src/database/session.py`
- Create: `src/database/models.py`
- Create: `src/core/tone_validator.py`
- Test: `tests/test_config.py`
- Test: `tests/test_database.py`

**Interfaces:**
- Consumes: Environment variables (`DATABASE_URL`, `REDIS_URL`, `TELEGRAM_BOT_TOKEN`, `GEMINI_API_KEY`, `ALIASMODE_API_URL`).
- Produces: `get_db() -> AsyncGenerator[AsyncSession, None]`, `AppConfig`, `NicheConfig`, `Base`, `ToneValidator.validate(text: str) -> bool`.

- [ ] **Step 1: Viết test kiểm tra nạp cấu hình và khởi tạo ORM models**

```python
# tests/test_config.py
import pytest
from src.core.config import load_config

def test_load_config_niches_and_browser():
    config = load_config("config.yaml")
    assert len(config.niches) == 2
    assert config.browser.provider == "aliasmode"
    niche_ids = [n.niche_id for n in config.niches]
    assert "thoi_trang_nu" in niche_ids
    assert "do_gia_dung" in niche_ids
```

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

- [ ] **Step 2: Chạy test để xác nhận lỗi vì chưa có mã nguồn**

Run: `pytest tests/test_config.py tests/test_database.py -v`  
Expected: FAIL

- [ ] **Step 3: Tạo `.env.example` và `scripts/get_telegram_ids.py`**

Tạo file mẫu môi trường đầy đủ chú thích tiếng Việt cho Telegram Bot Token, Admin ID, Topics ID, PostgreSQL, Redis và AliasMode API URL (`http://127.0.0.1:50325`). Cài đặt script tự động bắt User ID và Topic ID khi nhắn tin cho Bot.

- [ ] **Step 4: Tạo `config.yaml` và cài đặt `src/core/config.py`**

Cấu hình 2 ngách Thời Trang Nữ và Đồ Gia Dụng kèm Persona chi tiết, bộ từ cấm, tiêu chuẩn giá và cấu hình `browser.provider: "aliasmode"`. Cài đặt Pydantic model trong `src/core/config.py`.

- [ ] **Step 5: Cài đặt `src/database/models.py` và `src/database/session.py`**

Cài đặt các bảng `Niche`, `Channel` (có `browser_provider`, `browser_profile_id`, `lifecycle_status`), `Competitor`, `Product`, `VideoJob`, `VideoComment`, `Metric` sử dụng SQLAlchemy 2.0 `DeclarativeBase` và kiểu `JSONB`.

- [ ] **Step 6: Cài đặt `src/core/tone_validator.py` (Bộ lọc chống mùi AI)**

Cài đặt hàm kiểm tra văn bản tiếng Việt: phát hiện và loại bỏ các mẫu câu rập khuôn máy móc, ép giọng điệu tự nhiên đời thường của KOC TikTok.

- [ ] **Step 7: Chạy lại test để đảm bảo PASS**

Run: `pytest tests/test_config.py tests/test_database.py -v`  
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add .env.example scripts/ config.yaml src/core/ src/database/ tests/
git commit -m "feat(core): setup config with aliasmode, database models, and tone validator"
```

---

### Task 2: Base Scout Infrastructure & Kalodata + Scraper Service

**Files:**
- Create: `src/services/kalodata_client.py`
- Create: `src/services/tiktok_scraper.py`
- Create: `src/agents/base_scout.py`
- Test: `tests/test_kalodata_client.py`
- Test: `tests/test_tiktok_scraper.py`

**Interfaces:**
- Consumes: `~/.kalopilot/token` hoặc `KALOPILOT_TOKEN`, URL kênh TikTok.
- Produces: 
  - `KalodataClient.get_top_products(category_id: str, limit: int) -> List[Dict]`
  - `TikTokScraper.get_recent_videos(channel_url: str, limit: int) -> List[TikTokVideoMeta]`
  - `TikTokScraper.extract_anchor_product(video_url: str) -> Optional[Dict]`
  - `BaseScoutAgent.discover_candidates(niche_id: str) -> List[ProductCandidate]`

- [ ] **Step 1: Viết test cho `KalodataClient` và `TikTokScraper`**
- [ ] **Step 2: Chạy test để xác nhận FAIL**
- [ ] **Step 3: Cài đặt `KalodataClient` tích hợp async submit & poll**
- [ ] **Step 4: Cài đặt `TikTokScraper` sử dụng `yt-dlp` bóc metadata và giỏ hàng**
- [ ] **Step 5: Cài đặt `BaseScoutAgent` lọc sơ bộ theo ngưỡng giá & hoa hồng**
- [ ] **Step 6: Chạy lại test để đảm bảo PASS**
- [ ] **Step 7: Commit**

```bash
git add src/services/ src/agents/base_scout.py tests/
git commit -m "feat(scout): implement Kalodata client and TikTok scraper service"
```

---

### Task 3: Triển khai 2 Niche Specialist Agents (`FashionScout` & `HomeLifeScout`)

**Files:**
- Create: `src/agents/fashion_scout.py`
- Create: `src/agents/homelife_scout.py`
- Create: `src/core/prompt_templates.py`
- Test: `tests/test_specialist_scouts.py`

**Interfaces:**
- Consumes: `ProductCandidate`, `BaseScoutAgent`, Gemini API.
- Produces: 
  - `FashionScoutAgent.evaluate_product(item: Dict) -> SpecialistEvaluation`
  - `HomeLifeScoutAgent.evaluate_product(item: Dict) -> SpecialistEvaluation`

- [ ] **Step 1: Viết test cho thuật toán chấm điểm chuyên ngành và bộ lọc vi phạm**
- [ ] **Step 2: Chạy test xác nhận FAIL**
- [ ] **Step 3: Cài đặt `FashionScoutAgent` (hack dáng, che khuyết điểm, loại trừ hàng nhái)**
- [ ] **Step 4: Cài đặt `HomeLifeScoutAgent` (giải phóng sức lao động, Before/After 3s)**
- [ ] **Step 5: Xây dựng Prompt LLM chuyên gia trong `src/core/prompt_templates.py`**
- [ ] **Step 6: Chạy test đảm bảo PASS**
- [ ] **Step 7: Commit**

```bash
git add src/agents/fashion_scout.py src/agents/homelife_scout.py src/core/prompt_templates.py tests/
git commit -m "feat(scout): implement Fashion and HomeLife specialist agents"
```

---

### Task 4: Telegram Command Center & Phê duyệt 1 chạm (Human-in-the-Loop)

**Files:**
- Create: `src/bot/telegram_bot.py`
- Create: `src/bot/keyboards.py`
- Create: `src/bot/handlers.py`
- Test: `tests/test_telegram_bot.py`

**Interfaces:**
- Consumes: `aiogram 3.x`, `TELEGRAM_BOT_TOKEN`, `ADMIN_TELEGRAM_ID`.
- Produces: 
  - `send_product_card(niche_id: str, evaluation: SpecialistEvaluation)`
  - Command handlers: `/test_scout`, `/test_video`, `/test_reply`, `/status`, `/menu`, `/create_channel`, `/warmup`.
  - Callback query handler: `approve_product:<product_id>`, `reject_product:<product_id>`.

- [ ] **Step 1: Viết test cho cấu trúc tin nhắn và phím bấm Telegram**
- [ ] **Step 2: Chạy test xác nhận FAIL**
- [ ] **Step 3: Cài đặt `format_product_message` và `keyboards.py`**
- [ ] **Step 4: Cài đặt `telegram_bot.py` và `handlers.py` với Forum Topics**
- [ ] **Step 5: Chạy test đảm bảo PASS**
- [ ] **Step 6: Commit**

```bash
git add src/bot/ tests/test_telegram_bot.py
git commit -m "feat(telegram): implement command center and approval handlers"
```

---

### Task 5: Video Remixing & Content Engine (Ngôn ngữ tự nhiên, lách thuật toán TikTok)

**Files:**
- Create: `src/services/video_downloader.py`
- Create: `src/services/audio_transcriber.py`
- Create: `src/services/script_generator.py`
- Create: `src/services/tts_service.py`
- Create: `src/services/video_processor.py`
- Create: `src/agents/video_studio.py`
- Test: `tests/test_script_generator.py`
- Test: `tests/test_tts_service.py`
- Test: `tests/test_video_processor.py`

**Interfaces:**
- Consumes: URL video đối thủ, kịch bản gốc, Persona cấu hình.
- Produces: `VideoStudioAgent.produce_video(job_id: str) -> str (mp4_path)`.

- [ ] **Step 1: Viết test cho Script Generator & TTS Service**
- [ ] **Step 2: Chạy test xác nhận FAIL**
- [ ] **Step 3: Cài đặt `video_downloader.py` & `audio_transcriber.py` (Whisper)**
- [ ] **Step 4: Cài đặt `script_generator.py` với công thức Hook 3s người thật và CTA giỏ hàng vàng**
- [ ] **Step 5: Cài đặt `tts_service.py` (`edge-tts`) & `video_processor.py` (FFmpeg lách bản quyền)**
- [ ] **Step 6: Cài đặt `video_studio.py` ghép nối pipeline hoàn chỉnh**
- [ ] **Step 7: Chạy test đảm bảo PASS**
- [ ] **Step 8: Commit**

```bash
git add src/services/ src/agents/video_studio.py tests/
git commit -m "feat(studio): implement high-conversion natural video remix pipeline"
```

---

### Task 6: Human Behavioral Biometrics Engine & Smart Publisher với AliasMode (Agent 3)

**Files:**
- Create: `src/services/browser_adapter.py`
- Create: `src/services/human_behavior.py`
- Create: `src/agents/smart_publisher.py`
- Test: `tests/test_browser_adapter.py`
- Test: `tests/test_human_behavior.py`
- Test: `tests/test_smart_publisher.py`

**Interfaces:**
- Consumes: AliasMode Local API, Playwright, Proxy config, Telegram Bot (để cảnh báo Captcha).
- Produces: 
  - `BrowserAdapter.create_profile(name: str, proxy: Optional[str]) -> str (profile_id)`
  - `BrowserAdapter.start_browser(profile_id: str) -> str (cdp_endpoint)`
  - `HumanBehaviorService.human_scroll(page: Page, steps: int = 5) -> None`
  - `HumanBehaviorService.human_type(page: Page, selector: str, text: str, typo_rate: float = 0.03) -> None`
  - `HumanBehaviorService.warmup_feed_session(page: Page, duration_seconds: int = 180) -> None`
  - `HumanBehaviorService.detect_and_handle_captcha(page: Page) -> bool`
  - `SmartPublisher.publish_video(job_id: str) -> PublishResult`

- [ ] **Step 1: Viết test cho `HumanBehaviorService` và `BrowserAdapter`**

```python
# tests/test_human_behavior.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.services.human_behavior import HumanBehaviorService

@pytest.mark.asyncio
async def test_human_type_simulation():
    page = MagicMock()
    page.keyboard = MagicMock()
    page.keyboard.press = AsyncMock()
    page.wait_for_selector = AsyncMock()
    page.click = AsyncMock()
    
    service = HumanBehaviorService()
    # Test typing with typo simulation and backspace
    typed_keys = []
    async def mock_press(key):
        typed_keys.append(key)
    page.keyboard.press.side_effect = mock_press
    
    await service.human_type(page, "#caption_input", "Váy xinh", typo_rate=0.0)
    assert len(typed_keys) == len("Váy xinh")
```

- [ ] **Step 2: Chạy test xác nhận FAIL**

Run: `pytest tests/test_human_behavior.py tests/test_browser_adapter.py -v`  
Expected: FAIL

- [ ] **Step 3: Cài đặt `src/services/browser_adapter.py`**

Quản lý profile trên AliasMode qua Local API, khởi động trình duyệt và trả về CDP WebSocket endpoint.

- [ ] **Step 4: Cài đặt `src/services/human_behavior.py` (Biometrics Engine)**

Cài đặt 5 kỹ thuật:
1. `human_scroll`: cuộn chuột từng nấc có gia tốc và rung giật ngược nhẹ.
2. `human_type`: tốc độ gõ biến thiên 80–220ms, micro-pauses 0.6–1.4s, gõ nhầm 3% rồi nhấn Backspace sửa lại.
3. `human_move_and_click`: di chuột theo đường cong Bezier, hover trước khi bấm.
4. `warmup_feed_session`: lướt trang chủ TikTok 3–5 phút, xem 3–5 video trước khi đăng.
5. `detect_and_handle_captcha`: bắt sự kiện Captcha, chụp ảnh màn hình và bắn còi báo động về Telegram.

- [ ] **Step 5: Cài đặt `SmartPublisher` (Agent 3)**

Kết hợp `BrowserAdapter` và `HumanBehaviorService` để thực hiện toàn bộ quy trình upload video, gõ caption, hashtag và gắn Product Anchor trong Showcase.

- [ ] **Step 6: Chạy test đảm bảo PASS**

Run: `pytest tests/test_browser_adapter.py tests/test_human_behavior.py tests/test_smart_publisher.py -v`  
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/services/browser_adapter.py src/services/human_behavior.py src/agents/smart_publisher.py tests/
git commit -m "feat(publisher): implement human behavioral biometrics engine and AliasMode publisher"
```

---

### Task 7: Comment Engagement & Conversion Agent (Agent 5)

**Files:**
- Create: `src/agents/comment_agent.py`
- Create: `src/services/comment_scanner.py`
- Test: `tests/test_comment_agent.py`

**Interfaces:**
- Consumes: Comment text, Persona config, Product info.
- Produces: 
  - `CommentAgent.classify_intent(comment: str) -> CommentIntent`
  - `CommentAgent.generate_reply(comment: str, product_meta: Dict, persona: PersonaConfig) -> str`

- [ ] **Step 1: Viết test cho bộ phân loại ý định bình luận và sinh câu trả lời tư vấn**
- [ ] **Step 2: Chạy test xác nhận FAIL**
- [ ] **Step 3: Cài đặt `comment_agent.py`**
- [ ] **Step 4: Chạy test đảm bảo PASS**
- [ ] **Step 5: Commit**

```bash
git add src/agents/comment_agent.py src/services/comment_scanner.py tests/test_comment_agent.py
git commit -m "feat(engagement): implement natural comment conversion agent"
```

---

### Task 8: Hermes Orchestrator, CLI Runner & E2E Dry-run

**Files:**
- Create: `src/agents/hermes_orchestrator.py`
- Create: `main.py`
- Create: `tests/test_e2e_dryrun.py`
- Create: `README.md`
- Test: `tests/test_hermes_flow.py`
- Test: `tests/test_e2e_dryrun.py`

**Interfaces:**
- Consumes: LangGraph, Telegram Handlers, Database, All Agents.
- Produces: 
  - `HermesOrchestrator.run_pipeline_step(step_name: str, payload: Dict)`
  - `main.py` CLI runner for bot & background schedulers.

- [ ] **Step 1: Viết test cho luồng State Graph của Hermes và kịch bản E2E Dry-run**
- [ ] **Step 2: Chạy test xác nhận FAIL**
- [ ] **Step 3: Cài đặt `hermes_orchestrator.py` với LangGraph**
- [ ] **Step 4: Cài đặt `main.py` kết nối Bot Telegram, hỗ trợ các lệnh `/test_scout`, `/test_video`, `/test_reply`, `/create_channel`, `/warmup`**
- [ ] **Step 5: Viết `README.md` hướng dẫn cấu hình `.env`, khởi động AliasMode và chạy hệ thống**
- [ ] **Step 6: Chạy toàn bộ test suite đảm bảo 100% PASS**

Run: `pytest tests/ -v`  
Expected: 100% PASS

- [ ] **Step 7: Commit**

```bash
git add src/agents/hermes_orchestrator.py main.py tests/ README.md
git commit -m "feat(orchestrator): implement master Hermes orchestrator and complete test suite"
```
