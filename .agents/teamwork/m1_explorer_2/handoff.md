# Technical Investigation Report: Milestone 1 (Task 1: Configuration, Scripts & ToneValidator)

## 1. Observation

### 1.1 Requirements & Repository State
1. **Repository State**:
   - Workspace `/Users/tuanlva/Folder/workSpace/affiliate` is currently greenfield with only `.agents/`, `SYSTEM_SPEC.md`, `docs/`, and `skills-lock.json`.
   - Python environment is verified as **Python 3.12.2** (`python3 --version`).
   - Root configuration files (`.env.example`, `config.yaml`), scripts (`scripts/get_telegram_ids.py`), source modules (`src/core/config.py`, `src/core/tone_validator.py`), and test suites (`tests/test_config.py`) do not yet exist.

2. **Project Specification Citations**:
   - `ORIGINAL_REQUEST.md` (Lines 42–47):
     ```markdown
     ### Task 1: Scaffolding, Cấu hình & Database Schema
     - [ ] File `.env.example`, `config.yaml` và `scripts/get_telegram_ids.py` được tạo đầy đủ.
     - [ ] `ToneValidator` kiểm tra và chặn được các mẫu câu rập khuôn AI.
     - [ ] `pytest tests/test_config.py tests/test_database.py` chạy PASS 100%.
     ```
   - `ORIGINAL_REQUEST.md` (Lines 21–27):
     - Anti-robotic requirement: *"Tuyệt đối cấm các câu máy móc: 'Xin chào quý khách', 'Tôi là trợ lý AI', 'Sản phẩm này rất tốt và tiện ích'. Bắt buộc dùng xưng hô gần gũi đúng thị hiếu TikTok Việt Nam: 'Chị em ơi', 'Bà nào bụng dưới to bơi hết vào đây', 'Từ ngày tậu cái này việc nhà nhàn hẳn', 'Chị bấm ngay góc trái nhận mã freeship nha'."*
     - TikTok Shop Policy requirement: *"Tự động lọc bỏ hoàn toàn các từ khóa hàng nhái (Zara, Chanel, Gucci, rep 1:1, super fake). Tự động lọc bỏ các cam kết y khoa/quảng cáo quá đà (trị dứt điểm 100%, vĩnh viễn không bám bẩn)."*
   - `PROJECT.md` (Lines 76–80):
     - `load_config(path: str = "config.yaml") -> AppConfig`
     - `ToneValidator.validate(text: str) -> bool`: Pure validator, returns False if text contains banned robotic or counterfeit phrases.
   - `SYSTEM_SPEC.md` (Lines 43–67):
     - Biometrics Engine requirements: typing delay 80–220ms, typo rate 3% with backspace recovery, micro-pauses 0.6–1.4s, warmup feed 3–5 minutes, scroll inertia with reverse overshoot.
     - Captcha emergency alarm to Telegram.

---

## 2. Logic Chain

1. **Configuration Hierarchy & Precedence**:
   - `config.yaml` serves as the centralized source of structured configuration (niche definitions, persona templates, default browser biometrics parameters, thresholds).
   - `.env` / Environment variables serve as runtime credentials and host overrides (`POSTGRES_URL`, `DATABASE_URL`, `REDIS_URL`, `TELEGRAM_BOT_TOKEN`, `ADMIN_TELEGRAM_ID`, `TELEGRAM_FORUM_CHAT_ID`, `GEMINI_API_KEY`, `BROWSER_API_URL`, `BROWSER_WS_URL`).
   - `src/core/config.py` loads YAML first, merges environment variables with highest precedence, and validates the entire tree via Pydantic V2 models (`AppConfig`, `BrowserConfig`, `NicheConfig`, `PersonaConfig`, etc.).

2. **Telegram Forum Topic & ID Discovery**:
   - AMAS routes niche notifications to dedicated Telegram forum topics (`#thoi-trang-nu`, `#do-gia-dung`, `#dashboard-tong`).
   - Telegram Bot API 6.0+ sends `message_thread_id` inside `types.Message` when running in a Supergroup with Forum Topics enabled.
   - `scripts/get_telegram_ids.py` must use `aiogram` 3.x to inspect updates in real-time, print formatted IDs (Chat ID, Topic ID, User ID), and provide a direct copy-paste cheat sheet for `.env` and `config.yaml`.

3. **ToneValidator Design**:
   - Pure regex/keyword matching guarantees determinism, zero API latency, and 0 cost for every generated script and comment.
   - Unicode normalization (`unicodedata.normalize('NFC', text)`) is required before matching to ensure Vietnamese composed/decomposed diacritics are matched consistently.
   - Word boundaries (`\b`) and case-insensitive matching (`re.IGNORECASE`) prevent false positives on substrings (e.g. acronym `LV` must not match inside `silver` or Vietnamese words like `lưu`, `lực`).
   - Three distinct violation categories:
     1. `ROBOTIC_CLICHE`: AI greetings, bot self-identification, corporate essay marketing fillers.
     2. `COUNTERFEIT_KEYWORD`: Trademark violations (Zara, Chanel, Gucci, Dior, LV, Hermes, Nike, Adidas) and counterfeit slangs (`rep 1:1`, `super fake`, `chuẩn auth`, `tuồn auth`).
     3. `EXAGGERATED_CLAIM`: Medical cures (`trị dứt điểm 100%`, `khỏi hẳn sau 7 ngày`, `thần dược`) and absolute impossibility claims (`vĩnh viễn không bám bẩn`, `100% không bao giờ hỏng`).
   - A complementary method `has_koc_markers(text: str) -> bool` checks for authentic Vietnamese KOC colloquial openers, slang, and cart CTA cues.

---

## 3. Caveats

1. **Rule-Based Regex vs LLM Semantic Evaluation**:
   - `ToneValidator` operates on deterministic regex rules for immediate filtering. Highly disguised robotic phrasing or subtle sarcasm may bypass regex; however, this deterministic layer is the essential fast filter before/after Gemini generation.
2. **Vietnamese Word Boundaries**:
   - While Python 3.12 `\b` works well with Unicode alphanumeric characters, phrases containing punctuation (like `rep 1:1` or `100%`) must have custom boundary regex (e.g. `(?:\s|^|[^\w])rep\s*1\s*[:\/\-]\s*1(?:\s|$|[^\w])`) to prevent edge-case mismatches.
3. **Pydantic V2 Dependency**:
   - Code is designed strictly for Pydantic V2 (`pydantic>=2.7.0`). In Pydantic V2, `ConfigDict` and `field_validator` replace V1's inner `class Config` and `@validator`.

---

## 4. Conclusion & Complete Specifications

Below are the exact, copy-paste ready implementations for the Worker to build.

### 4.1 Specification: `.env.example`
Path: `/Users/tuanlva/Folder/workSpace/affiliate/.env.example`

```dotenv
# ==============================================================================
# AMAS v1.4.0 — Environment Variables Configuration Template
# Sao chép file này thành .env và điền các giá trị thực tế trước khi khởi chạy.
# ==============================================================================

# --- 1. MÔI TRƯỜNG HỆ THỐNG ---
ENVIRONMENT=development
LOG_LEVEL=INFO

# --- 2. CƠ SỞ DỮ LIỆU & BROKER ---
# Kết nối PostgreSQL (Yêu cầu asyncpg driver cho SQLAlchemy 2.0 Async)
POSTGRES_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/affiliate_db
# Dự phòng / Alias tương thích
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/affiliate_db

# Kết nối Redis (Dùng cho hàng đợi tác vụ và rate limiting)
REDIS_URL=redis://localhost:6379/0

# --- 3. TELEGRAM COMMAND CENTER ---
# Token Telegram Bot lấy từ @BotFather
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGhIJKlmNoPQRsTUVwxyZ_EXAMPLE

# Telegram User ID của Admin nhận thông báo khẩn cấp (như Captcha alarm)
# Chạy `python scripts/get_telegram_ids.py` và nhắn tin cho Bot để lấy ID này
ADMIN_TELEGRAM_ID=123456789

# Telegram Chat ID của Supergroup / Forum Group chứa các Topics của 2 ngách
# Chạy `python scripts/get_telegram_ids.py` trong nhóm để lấy ID này (thường bắt đầu bằng -100...)
TELEGRAM_FORUM_CHAT_ID=-1001234567890

# --- 4. GOOGLE GEMINI AI ---
# API Key của Google Gemini cho các Agent chuyên gia & viết kịch bản
GEMINI_API_KEY=AIzaSyD-EXAMPLE-GEMINI-KEY-HERE
GEMINI_MODEL=gemini-2.5-flash

# --- 5. BROWSER ANTI-DETECT & CDP ---
# REST API của trình duyệt AliasMode nội bộ
BROWSER_API_URL=http://127.0.0.1:50325

# WebSocket CDP Endpoint (Để trống nếu lấy động qua AliasMode API)
BROWSER_WS_URL=

# --- 6. SCOUT & KALODATA TOKEN ---
# Token truy cập Kalodata API (Mặc định hệ thống tự đọc tại ~/.kalopilot/token nếu để trống)
KALOPILOT_TOKEN=
```

---

### 4.2 Specification: `config.yaml`
Path: `/Users/tuanlva/Folder/workSpace/affiliate/config.yaml`

```yaml
app_name: "AMAS"
version: "1.4.0"
environment: "development"

# ==============================================================================
# CẤU HÌNH TRÌNH DUYỆT ẨN DANH (ALIASMODE) & BIOMETRICS ENGINE
# ==============================================================================
browser:
  provider: "aliasmode" # aliasmode | playwright_standalone | camoufox
  api_url: "http://127.0.0.1:50325"
  ws_url: null
  headless: false
  timeout_ms: 30000
  warmup_duration_seconds: 180 # 3 phút lướt feed dạo trước khi đăng
  behavior:
    typing_min_delay_ms: 80
    typing_max_delay_ms: 220
    typo_rate: 0.03 # 3% gõ nhầm và bấm backspace sửa lại
    backspace_delay_ms: 300
    micro_pause_min_s: 0.6
    micro_pause_max_s: 1.4
    scroll_steps: 5
    scroll_reverse_ratio: 0.15 # 15% xác suất cuộn ngược quán tính

# ==============================================================================
# CẤU HÌNH TELEGRAM BOT & TOPIC ROUTING
# ==============================================================================
telegram:
  bot_token: "" # Ghi đè bởi biến môi trường TELEGRAM_BOT_TOKEN
  admin_id: 0   # Ghi đè bởi biến môi trường ADMIN_TELEGRAM_ID
  forum_chat_id: null # Ghi đè bởi biến môi trường TELEGRAM_FORUM_CHAT_ID
  topic_ids:
    thoi_trang_nu: 2 # Message thread ID cho topic Thời trang nữ
    do_gia_dung: 4   # Message thread ID cho topic Đồ gia dụng
    dashboard: 1     # Message thread ID cho topic Tổng quan

# ==============================================================================
# CẤU HÌNH DATABASE & REDIS
# ==============================================================================
database:
  url: "postgresql+asyncpg://postgres:postgres@localhost:5432/affiliate_db"
  pool_size: 10
  max_overflow: 20
  echo: false

redis:
  url: "redis://localhost:6379/0"

# ==============================================================================
# 2 NGÁCH THÍ ĐIỂM (PILOT NICHES)
# ==============================================================================
niches:
  - niche_id: "thoi_trang_nu"
    name: "Thời trang nữ"
    telegram_topic_id: 2
    categories:
      - "women_clothing"
      - "vay_dam"
      - "ao_nu"
      - "quan_nu"
      - "set_do_nu"
    topics:
      - "phối đồ"
      - "hack dáng"
      - "che khuyết điểm bắp tay chân to"
      - "váy đi tiệc sang chảnh"
      - "outfit công sở trẻ trung"
    thresholds:
      min_price: 99000.0
      max_price: 650000.0
      min_commission_rate: 0.10 # Tối thiểu 10%
      min_sales_7d: 100
      min_rating: 4.5
      min_evaluation_score: 7.0 # Thang điểm 10 từ FashionScoutAgent
    persona:
      role: "KOC Thời trang nữ Gen Z / Millennial"
      tone: "Thân mật, hào hứng, xưng chị em/các bà/tui, am hiểu chất vải và form dáng tôn dáng, cởi mở chân thật"
      sample_greetings:
        - "Chị em ơi"
        - "Mấy bà ơi"
        - "Bà nào bụng dưới to bơi hết vào đây nha"
        - "Team chân ngắn đâu rồi bơi vào nhận đồ đẹp nè"
      sample_hooks:
        - "Mặc cái này lên eo thon gọn hẳn 5 phân không cần nịt bụng"
        - "Váy hack dáng đỉnh nhất tui từng thử trong năm nay"
        - "Đừng mua mẫu váy này nếu sợ bị đồng nghiệp hỏi xin link liên tục"
      sample_ctas:
        - "Bấm ngay góc trái nhận mã freeship nha"
        - "Link tui để ở giỏ hàng góc trái nè"
        - "Săn ngay mã giảm giá ở giỏ hàng vàng nha mấy bà"
    banned_keywords:
      - "zara"
      - "chanel"
      - "gucci"
      - "dior"
      - "louis vuitton"
      - "lv"
      - "hermes"
      - "nike"
      - "adidas"
      - "rep 1:1"
      - "rep 1 1"
      - "super fake"
      - "hàng rep"
      - "like auth"
      - "chuẩn auth"
      - "tuồn auth"

  - niche_id: "do_gia_dung"
    name: "Đồ gia dụng thông minh"
    telegram_topic_id: 4
    categories:
      - "home_appliances"
      - "do_nha_bep"
      - "dung_cu_ve_sinh_thong_minh"
      - "tien_ich_gia_dinh"
    topics:
      - "tiện ích nhà bếp"
      - "vệ sinh nhà cửa nhàn tênh"
      - "before-after làm sạch siêu đỉnh"
      - "tiết kiệm thời gian cho mẹ bỉm"
      - "đồ gia dụng thông minh giá rẻ"
    thresholds:
      min_price: 49000.0
      max_price: 1200000.0
      min_commission_rate: 0.12 # Tối thiểu 12%
      min_sales_7d: 80
      min_rating: 4.6
      min_evaluation_score: 7.0 # Thang điểm 10 từ HomeLifeScoutAgent
    persona:
      role: "KOC Đồ gia dụng thông minh / Yêu bếp nghiện nhà"
      tone: "Thực tế, gần gũi, xưng các bác/mấy bà/tui, chú trọng giải phóng sức lao động, nhấn mạnh Before/After 3s"
      sample_greetings:
        - "Các bác ơi"
        - "Bà nào ngại dọn nhà bơi vào đây"
        - "Chân ái cho hội lười dọn dẹp đây rồi"
        - "Từ ngày tậu em này việc nhà nhàn hẳn"
      sample_hooks:
        - "Bỏ ngay mấy cái giẻ lau cũ đi, dùng cái này nhàn tênh"
        - "3 giây sạch bóng kin kít không tốn một giọt mồ hôi"
        - "Cứ tưởng vô dụng mà đỉnh không tưởng các bác ạ"
      sample_ctas:
        - "Chị em bấm vào giỏ hàng góc trái nhận ưu đãi nha"
        - "Đang có mã giảm 20k ở giỏ hàng vàng kìa các bác"
        - "Link mua chính hãng ở góc trái màn hình nha"
    banned_keywords:
      - "trị dứt điểm 100%"
      - "vĩnh viễn không bám bẩn"
      - "vĩnh viễn không hỏng"
      - "100% không bao giờ hỏng"
      - "thần dược"
      - "bảo hành trọn đời không hỏng"
```

---

### 4.3 Specification: `scripts/get_telegram_ids.py`
Path: `/Users/tuanlva/Folder/workSpace/affiliate/scripts/get_telegram_ids.py`

```python
#!/usr/bin/env python3
"""AMAS Helper: Inspect Telegram bot updates to extract Chat ID, User ID, and Topic (Thread) IDs."""

import argparse
import asyncio
import os
import sys
from pathlib import Path
from typing import Optional

# Tự động nạp .env nếu có
try:
    from dotenv import load_dotenv

    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass

from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart


def parse_args():
    parser = argparse.ArgumentParser(
        description="Lấy Telegram Chat ID, User ID và Topic Message Thread ID cho hệ thống AMAS."
    )
    parser.add_argument(
        "--token",
        type=str,
        default=os.getenv("TELEGRAM_BOT_TOKEN"),
        help="Telegram Bot Token (nếu không truyền sẽ đọc từ biến môi trường TELEGRAM_BOT_TOKEN)",
    )
    return parser.parse_args()


async def main():
    args = parse_args()
    token = args.token

    if not token or "EXAMPLE" in token:
        print("\n❌ LỖI: Chưa có TELEGRAM_BOT_TOKEN hợp lệ!")
        print("👉 Vui lòng cấu hình TELEGRAM_BOT_TOKEN trong file .env hoặc chạy:")
        print("   python scripts/get_telegram_ids.py --token <BOT_TOKEN>\n")
        sys.exit(1)

    bot = Bot(token=token)
    dp = Dispatcher()

    try:
        bot_info = await bot.get_me()
        print("\n" + "=" * 65)
        print(f"🤖 AMAS Telegram ID Discovery Service")
        print(f"   Bot Username: @{bot_info.username}")
        print(f"   Bot Name:     {bot_info.full_name}")
        print("=" * 65)
        print("📌 HƯỚNG DẪN:")
        print("1. Nhắn bất kỳ tin nhắn nào cho Bot trong Chat riêng -> Lấy ADMIN_TELEGRAM_ID.")
        print("2. Thêm Bot vào Supergroup (đã bật Topics), nhắn tin trong từng Topic:")
        print("   -> Lấy TELEGRAM_FORUM_CHAT_ID và message_thread_id tương ứng.")
        print("3. Nhấn Ctrl+C để kết thúc khi đã ghi lại đủ ID.")
        print("=" * 65 + "\n")
    except Exception as e:
        print(f"\n❌ Lỗi xác thực Bot Token: {e}\n")
        await bot.session.close()
        sys.exit(1)

    @dp.message()
    async def handle_incoming_message(message: types.Message):
        chat = message.chat
        user = message.from_user
        thread_id = message.message_thread_id
        text = message.text or message.caption or "<Non-text update>"

        print("-" * 65)
        print("📩 NHẬN TIN NHẮN MỚI TỪ TELEGRAM:")
        print(f"   Chat ID:           {chat.id}")
        print(f"   Chat Title:        {chat.title or 'Private Chat (Direct Message)'}")
        print(f"   Chat Type:         {chat.type}")
        if user:
            print(f"   From User:         {user.full_name} (@{user.username}) [ID: {user.id}]")
        print(f"   Message Thread ID: {thread_id}  <-- DÙNG CHO telegram_topic_id")
        print(f"   Nội dung tin nhắn: {text[:80]}")
        print("-" * 65)
        print("📋 GỢI Ý CẤU HÌNH:")
        if chat.type == "private" and user:
            print(f"   .env -> ADMIN_TELEGRAM_ID={user.id}")
        else:
            print(f"   .env -> TELEGRAM_FORUM_CHAT_ID={chat.id}")
            if thread_id:
                print(f"   config.yaml -> topic_ids: <niche_key>: {thread_id}")
        print("-" * 65 + "\n")

        # Gửi phản hồi lại Telegram xác nhận
        try:
            reply_text = (
                f"✅ <b>AMAS Helper ghi nhận ID:</b>\n"
                f"• Chat ID: <code>{chat.id}</code>\n"
                f"• User ID: <code>{user.id if user else 'N/A'}</code>\n"
                f"• Thread / Topic ID: <code>{thread_id or 'General (1)'}</code>"
            )
            await message.reply(reply_text, parse_mode="HTML")
        except Exception:
            pass

    try:
        await dp.start_polling(bot)
    except (KeyboardInterrupt, SystemExit):
        print("\n👋 Đã dừng lắng nghe Telegram updates.")
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
```

---

### 4.4 Specification: `src/core/config.py`
Path: `/Users/tuanlva/Folder/workSpace/affiliate/src/core/config.py`

```python
"""AMAS v1.4.0 — Core Configuration Loader with Pydantic V2 and Environment Variable Overrides."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator


class BrowserBehaviorConfig(BaseModel):
    """Cấu hình mô phỏng sinh trắc học người thật cho trình duyệt."""

    model_config = ConfigDict(extra="ignore")

    typing_min_delay_ms: int = Field(default=80, ge=10, le=1000)
    typing_max_delay_ms: int = Field(default=220, ge=10, le=2000)
    typo_rate: float = Field(default=0.03, ge=0.0, le=0.5)
    backspace_delay_ms: int = Field(default=300, ge=50, le=2000)
    micro_pause_min_s: float = Field(default=0.6, ge=0.1, le=10.0)
    micro_pause_max_s: float = Field(default=1.4, ge=0.1, le=10.0)
    scroll_steps: int = Field(default=5, ge=1, le=50)
    scroll_reverse_ratio: float = Field(default=0.15, ge=0.0, le=0.5)


class BrowserConfig(BaseModel):
    """Cấu hình AliasMode / Anti-detect browser."""

    model_config = ConfigDict(extra="ignore")

    provider: str = Field(default="aliasmode")
    api_url: str = Field(default="http://127.0.0.1:50325")
    ws_url: Optional[str] = Field(default=None)
    headless: bool = Field(default=False)
    timeout_ms: int = Field(default=30000, ge=1000)
    warmup_duration_seconds: int = Field(default=180, ge=0)
    behavior: BrowserBehaviorConfig = Field(default_factory=BrowserBehaviorConfig)


class PersonaConfig(BaseModel):
    """Đặc trưng Persona KOC cho từng ngách."""

    model_config = ConfigDict(extra="ignore")

    role: str
    tone: str
    sample_greetings: List[str] = Field(default_factory=list)
    sample_hooks: List[str] = Field(default_factory=list)
    sample_ctas: List[str] = Field(default_factory=list)


class FilterThresholds(BaseModel):
    """Ngưỡng lọc sản phẩm cho BaseScout và SpecialistScout."""

    model_config = ConfigDict(extra="ignore")

    min_price: float = Field(default=0.0, ge=0.0)
    max_price: float = Field(default=10000000.0, ge=0.0)
    min_commission_rate: float = Field(default=0.05, ge=0.0, le=1.0)
    min_sales_7d: int = Field(default=10, ge=0)
    min_rating: float = Field(default=4.0, ge=0.0, le=5.0)
    min_evaluation_score: float = Field(default=7.0, ge=0.0, le=10.0)


class NicheConfig(BaseModel):
    """Cấu hình chi tiết cho 1 ngách thí điểm."""

    model_config = ConfigDict(extra="ignore")

    niche_id: str
    name: str
    telegram_topic_id: Optional[int] = Field(default=None)
    categories: List[str] = Field(default_factory=list)
    topics: List[str] = Field(default_factory=list)
    thresholds: FilterThresholds = Field(default_factory=FilterThresholds)
    persona: PersonaConfig
    banned_keywords: List[str] = Field(default_factory=list)


class TelegramConfig(BaseModel):
    """Cấu hình Telegram Bot Command Center."""

    model_config = ConfigDict(extra="ignore")

    bot_token: str = Field(default="")
    admin_id: int = Field(default=0)
    forum_chat_id: Optional[int] = Field(default=None)
    topic_ids: Dict[str, int] = Field(default_factory=dict)


class DatabaseConfig(BaseModel):
    """Cấu hình cơ sở dữ liệu PostgreSQL / asyncpg."""

    model_config = ConfigDict(extra="ignore")

    url: str = Field(default="postgresql+asyncpg://postgres:postgres@localhost:5432/affiliate_db")
    pool_size: int = Field(default=10, ge=1)
    max_overflow: int = Field(default=20, ge=0)
    echo: bool = Field(default=False)


class RedisConfig(BaseModel):
    """Cấu hình Redis queue."""

    model_config = ConfigDict(extra="ignore")

    url: str = Field(default="redis://localhost:6379/0")


class AppConfig(BaseModel):
    """Cấu hình trung tâm toàn hệ thống AMAS."""

    model_config = ConfigDict(extra="ignore")

    app_name: str = Field(default="AMAS")
    version: str = Field(default="1.4.0")
    environment: str = Field(default="development")
    gemini_api_key: Optional[str] = Field(default=None)
    gemini_model: str = Field(default="gemini-2.5-flash")
    browser: BrowserConfig = Field(default_factory=BrowserConfig)
    telegram: TelegramConfig = Field(default_factory=TelegramConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    niches: List[NicheConfig] = Field(default_factory=list)

    def get_niche(self, niche_id: str) -> Optional[NicheConfig]:
        """Tìm cấu hình ngách theo niche_id."""
        for n in self.niches:
            if n.niche_id == niche_id:
                return n
        return None


def _apply_env_overrides(raw_data: Dict[str, Any]) -> Dict[str, Any]:
    """Ghi đè giá trị cấu hình bằng các biến môi trường nếu có."""
    # Database URL: ưu tiên POSTGRES_URL sau đó DATABASE_URL
    db_url = os.getenv("POSTGRES_URL") or os.getenv("DATABASE_URL")
    if db_url:
        raw_data.setdefault("database", {})["url"] = db_url

    # Redis URL
    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        raw_data.setdefault("redis", {})["url"] = redis_url

    # Telegram Bot Token & Admin ID & Forum Chat ID
    tg_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if tg_token:
        raw_data.setdefault("telegram", {})["bot_token"] = tg_token

    tg_admin = os.getenv("ADMIN_TELEGRAM_ID")
    if tg_admin:
        try:
            raw_data.setdefault("telegram", {})["admin_id"] = int(tg_admin)
        except ValueError:
            pass

    tg_forum = os.getenv("TELEGRAM_FORUM_CHAT_ID")
    if tg_forum:
        try:
            raw_data.setdefault("telegram", {})["forum_chat_id"] = int(tg_forum)
        except ValueError:
            pass

    # Gemini
    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key:
        raw_data["gemini_api_key"] = gemini_key

    gemini_model = os.getenv("GEMINI_MODEL")
    if gemini_model:
        raw_data["gemini_model"] = gemini_model

    # Browser
    browser_api = os.getenv("BROWSER_API_URL")
    if browser_api:
        raw_data.setdefault("browser", {})["api_url"] = browser_api

    browser_ws = os.getenv("BROWSER_WS_URL")
    if browser_ws:
        raw_data.setdefault("browser", {})["ws_url"] = browser_ws

    # Environment
    env = os.getenv("ENVIRONMENT")
    if env:
        raw_data["environment"] = env

    return raw_data


def load_config(path: str = "config.yaml") -> AppConfig:
    """Nạp file cấu hình YAML và áp dụng ghi đè từ biến môi trường.

    Raises:
        FileNotFoundError: Nếu file YAML không tồn tại.
        pydantic.ValidationError: Nếu cấu trúc dữ liệu không hợp lệ.
    """
    config_file = Path(path)
    if not config_file.exists():
        raise FileNotFoundError(f"Không tìm thấy file cấu hình tại: {path}")

    with open(config_file, "r", encoding="utf-8") as f:
        raw_data = yaml.safe_load(f) or {}

    raw_data = _apply_env_overrides(raw_data)
    return AppConfig.model_validate(raw_data)
```

---

### 4.5 Specification: `src/core/tone_validator.py`
Path: `/Users/tuanlva/Folder/workSpace/affiliate/src/core/tone_validator.py`

```python
"""AMAS v1.4.0 — Anti-Robotic, Policy & Brand Tone Validator.

Kiểm tra và ngăn chặn:
1. Mùi bot, văn phong máy móc rập khuôn AI (Robotic Clichés).
2. Từ khóa nhãn hiệu vi phạm sở hữu trí tuệ / hàng nhái (Counterfeit Brands).
3. Cam kết y tế / quảng cáo quá đà vi phạm chính sách TikTok Shop (Exaggerated Claims).
4. Xác minh sự hiện diện của các dấu hiệu KOC tự nhiên (KOC Markers).
"""

from __future__ import annotations

import re
import unicodedata
from typing import List, Tuple


class ToneValidator:
    """Bộ kiểm tra tuân thủ giọng điệu KOC và chính sách TikTok Shop."""

    # Nhóm 1: Mẫu câu máy móc / Mùi bot AI (Banned Robotic Clichés)
    ROBOTIC_PATTERNS: List[Tuple[str, str]] = [
        (r"\bxin chào quý khách\b", "xin chào quý khách"),
        (r"\bchào mừng quý khách\b", "chào mừng quý khách"),
        (r"\bkính chào quý khách\b", "kính chào quý khách"),
        (r"\brất hân hạnh được phục vụ\b", "rất hân hạnh được phục vụ"),
        (r"\btôi là trợ lý (ảo|ai)\b", "tôi là trợ lý ảo/AI"),
        (r"\btôi là (ai|chatgpt|mô hình ngôn ngữ)\b", "tôi là AI/mô hình ngôn ngữ"),
        (r"\bnhư một trợ lý ai\b", "như một trợ lý AI"),
        (r"\bsản phẩm này rất tốt và tiện ích\b", "sản phẩm này rất tốt và tiện ích"),
        (r"\bsản phẩm (này )?rất tuyệt vời\b", "sản phẩm rất tuyệt vời"),
        (r"\bđáp ứng mọi nhu cầu( của bạn)?\b", "đáp ứng mọi nhu cầu"),
        (r"\bsự lựa chọn hoàn hảo\b", "sự lựa chọn hoàn hảo"),
        (r"\bgiải pháp hoàn hảo\b", "giải pháp hoàn hảo"),
        (r"\bđừng bỏ lỡ cơ hội này\b", "đừng bỏ lỡ cơ hội này"),
        (r"\bhãy nhanh tay sở hữu\b", "hãy nhanh tay sở hữu"),
        (r"\bsở hữu ngay hôm nay\b", "sở hữu ngay hôm nay"),
        (r"\bcảm ơn quý khách đã tin tưởng\b", "cảm ơn quý khách đã tin tưởng"),
        (r"\bchúc quý khách một ngày tốt lành\b", "chúc quý khách một ngày tốt lành"),
        (r"\bmọi thắc mắc xin vui lòng liên hệ\b", "mọi thắc mắc xin vui lòng liên hệ"),
        (r"\btrân trọng cảm ơn\b", "trân trọng cảm ơn"),
    ]

    # Nhóm 2: Từ khóa nhãn hiệu hàng nhái / vi phạm bản quyền (Counterfeit Keywords)
    COUNTERFEIT_PATTERNS: List[Tuple[str, str]] = [
        (r"(?:\b|^|\s)rep\s*(1\s*[:\/\-]\s*1|1\s*1)(?:\b|$|\s)", "rep 1:1"),
        (r"\bsuper\s*fake\b", "super fake"),
        (r"\bhàng\s*(fake|rep|f1)\b", "hàng fake/rep/f1"),
        (r"\b(like|chuẩn|tuồn)\s*auth\b", "like/chuẩn/tuồn auth"),
        (r"\bhàng\s*tuồn\b", "hàng tuồn"),
        (r"\bvnxk\s*chuẩn\s*auth\b", "vnxk chuẩn auth"),
        (r"\bcheck\s*code\s*auth\b", "check code auth"),
        (r"\bzara\b", "Zara"),
        (r"\bchanel\b", "Chanel"),
        (r"\bgucci\b", "Gucci"),
        (r"\bdior\b", "Dior"),
        (r"\blouis\s*vuitton\b", "Louis Vuitton"),
        (r"(?:\b|^|\s)lv(?:\b|$|\s)", "LV"),
        (r"\bherm[eè]s\b", "Hermes"),
        (r"\bprada\b", "Prada"),
        (r"\bbalenciaga\b", "Balenciaga"),
        (r"\brolex\b", "Rolex"),
        (r"\bnike\b", "Nike"),
        (r"\badidas\b", "Adidas"),
    ]

    # Nhóm 3: Cam kết y tế / quảng cáo quá đà (Exaggerated Claims)
    EXAGGERATED_PATTERNS: List[Tuple[str, str]] = [
        (r"\btrị dứt điểm(\s*100%)?\b", "trị dứt điểm 100%"),
        (r"\bchữa khỏi hoàn toàn\b", "chữa khỏi hoàn toàn"),
        (r"\bđặc trị( dứt điểm| tận gốc)?\b", "đặc trị"),
        (r"\bcam kết khỏi( bệnh)?( 100%)?\b", "cam kết khỏi bệnh 100%"),
        (r"\bkhỏi hẳn sau\b", "khỏi hẳn sau"),
        (r"\bthần dược\b", "thần dược"),
        (r"\bthuốc trị\b", "thuốc trị"),
        (r"\bvĩnh viễn không bám bẩn\b", "vĩnh viễn không bám bẩn"),
        (r"\bvĩnh viễn không hỏng\b", "vĩnh viễn không hỏng"),
        (r"\b100% không bao giờ hỏng\b", "100% không bao giờ hỏng"),
        (r"\bvĩnh viễn không (rỉ|gỉ) sét\b", "vĩnh viễn không rỉ sét"),
        (r"\btốt nhất thị trường\b", "tốt nhất thị trường"),
        (r"\bsố 1 (thế giới|việt nam)\b", "số 1 thế giới/việt nam"),
        (r"\bduy nhất trên thị trường\b", "duy nhất trên thị trường"),
    ]

    # Nhóm 4: Dấu hiệu văn phong KOC tự nhiên (KOC Markers)
    KOC_MARKER_PATTERNS: List[str] = [
        r"\b(chị em ơi|mấy bà ơi|các bà ơi|bà nào|chị nào|mấy bác ơi|các bác ơi|bà con ơi|team chân ngắn|team bụng mỡ)\b",
        r"\b(nhàn hẳn|nhàn tênh|mê chữ ê kéo dài|chân ái|đỉnh chóp|hack dáng|che khuyết điểm|bụng dưới to|bắp tay to)\b",
        r"\b(giỏ hàng góc trái|góc trái màn hình|bấm ngay góc trái|giỏ hàng vàng|mã freeship|săn sale|săn voucher)\b",
    ]

    @classmethod
    def _normalize(cls, text: str) -> str:
        """Chuẩn hóa Unicode NFC và chữ thường."""
        if not text:
            return ""
        return unicodedata.normalize("NFC", text).lower()

    @classmethod
    def check_violations(cls, text: str) -> List[str]:
        """Trả về danh sách chi tiết các vi phạm có trong văn bản."""
        if not text:
            return []

        norm_text = cls._normalize(text)
        violations: List[str] = []

        # Kiểm tra Robotic Clichés
        for pattern, label in cls.ROBOTIC_PATTERNS:
            if re.search(pattern, norm_text, re.IGNORECASE):
                violations.append(f"ROBOTIC_CLICHE: '{label}'")

        # Kiểm tra Counterfeit Keywords
        for pattern, label in cls.COUNTERFEIT_PATTERNS:
            if re.search(pattern, norm_text, re.IGNORECASE):
                violations.append(f"COUNTERFEIT_KEYWORD: '{label}'")

        # Kiểm tra Exaggerated Claims
        for pattern, label in cls.EXAGGERATED_PATTERNS:
            if re.search(pattern, norm_text, re.IGNORECASE):
                violations.append(f"EXAGGERATED_CLAIM: '{label}'")

        return violations

    @classmethod
    def validate(cls, text: str) -> bool:
        """Trả về True nếu văn bản sạch, không chứa bất kỳ vi phạm nào."""
        return len(cls.check_violations(text)) == 0

    @classmethod
    def has_koc_markers(cls, text: str) -> bool:
        """Kiểm tra văn bản có chứa ít nhất 1 dấu hiệu KOC tự nhiên hay không."""
        if not text:
            return False
        norm_text = cls._normalize(text)
        for pattern in cls.KOC_MARKER_PATTERNS:
            if re.search(pattern, norm_text, re.IGNORECASE):
                return True
        return False
```

---

### 4.6 Specification: `tests/test_config.py`
Path: `/Users/tuanlva/Folder/workSpace/affiliate/tests/test_config.py`

```python
"""Unit tests for Central Configuration Loader and ToneValidator."""

import os
from pathlib import Path
import pytest
from pydantic import ValidationError

from src.core.config import AppConfig, load_config
from src.core.tone_validator import ToneValidator


# ==============================================================================
# 1. CONFIGURATION LOADER TESTS
# ==============================================================================

def test_load_config_niches_and_browser():
    """Kiểm tra đọc file config.yaml gốc của dự án."""
    config = load_config("config.yaml")

    # Kiểm tra cấu hình browser
    assert config.browser.provider == "aliasmode"
    assert config.browser.api_url == "http://127.0.0.1:50325"
    assert config.browser.headless is False
    assert config.browser.behavior.typing_min_delay_ms == 80
    assert config.browser.behavior.typing_max_delay_ms == 220
    assert config.browser.behavior.typo_rate == 0.03
    assert config.browser.behavior.micro_pause_min_s == 0.6
    assert config.browser.behavior.micro_pause_max_s == 1.4

    # Kiểm tra 2 ngách thí điểm
    assert len(config.niches) == 2
    niche_ids = [n.niche_id for n in config.niches]
    assert "thoi_trang_nu" in niche_ids
    assert "do_gia_dung" in niche_ids

    # Kiểm tra chi tiết ngách Thời trang nữ
    fashion = config.get_niche("thoi_trang_nu")
    assert fashion is not None
    assert fashion.telegram_topic_id == 2
    assert fashion.thresholds.min_price == 99000.0
    assert fashion.thresholds.min_commission_rate == 0.10
    assert len(fashion.persona.sample_greetings) > 0
    assert len(fashion.banned_keywords) > 0

    # Kiểm tra chi tiết ngách Đồ gia dụng
    homelife = config.get_niche("do_gia_dung")
    assert homelife is not None
    assert homelife.telegram_topic_id == 4
    assert homelife.thresholds.min_price == 49000.0
    assert homelife.thresholds.min_commission_rate == 0.12


def test_load_config_env_overrides(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Kiểm tra cơ chế ưu tiên ghi đè bằng biến môi trường."""
    sample_yaml = tmp_path / "custom_config.yaml"
    sample_yaml.write_text(
        """
app_name: "AMAS_CUSTOM"
browser:
  provider: "aliasmode"
  api_url: "http://127.0.0.1:50325"
niches:
  - niche_id: "thoi_trang_nu"
    name: "Thời trang nữ"
    persona:
      role: "KOC"
      tone: "Tự nhiên"
""",
        encoding="utf-8",
    )

    # Đặt các biến môi trường ghi đè
    monkeypatch.setenv("POSTGRES_URL", "postgresql+asyncpg://user:pass@remote:5432/db")
    monkeypatch.setenv("REDIS_URL", "redis://remote-redis:6379/1")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "mock_bot_token_123")
    monkeypatch.setenv("ADMIN_TELEGRAM_ID", "987654321")
    monkeypatch.setenv("TELEGRAM_FORUM_CHAT_ID", "-1009876543210")
    monkeypatch.setenv("GEMINI_API_KEY", "mock_gemini_key_456")
    monkeypatch.setenv("BROWSER_API_URL", "http://aliasmode-host:50325")
    monkeypatch.setenv("ENVIRONMENT", "staging")

    config = load_config(str(sample_yaml))

    assert config.database.url == "postgresql+asyncpg://user:pass@remote:5432/db"
    assert config.redis.url == "redis://remote-redis:6379/1"
    assert config.telegram.bot_token == "mock_bot_token_123"
    assert config.telegram.admin_id == 987654321
    assert config.telegram.forum_chat_id == -1009876543210
    assert config.gemini_api_key == "mock_gemini_key_456"
    assert config.browser.api_url == "http://aliasmode-host:50325"
    assert config.environment == "staging"


def test_load_config_missing_file():
    """Kiểm tra bắn lỗi FileNotFoundError khi đường dẫn file không tồn tại."""
    with pytest.raises(FileNotFoundError):
        load_config("non_existent_config.yaml")


def test_load_config_invalid_schema(tmp_path: Path):
    """Kiểm tra bắn lỗi ValidationError khi dữ liệu sai quy chuẩn Pydantic."""
    broken_yaml = tmp_path / "broken_config.yaml"
    broken_yaml.write_text(
        """
browser:
  behavior:
    typo_rate: 1.5 # Vượt quá le=0.5
niches:
  - niche_id: "thoi_trang_nu"
    # Thiếu trường name và persona bắt buộc
""",
        encoding="utf-8",
    )

    with pytest.raises(ValidationError):
        load_config(str(broken_yaml))


# ==============================================================================
# 2. TONE VALIDATOR TESTS
# ==============================================================================

def test_tone_validator_valid_natural_koc():
    """Văn bản KOC đời thường chuẩn giọng người thật phải vượt qua kiểm tra."""
    fashion_sample = (
        "Chị em ơi, bà nào bụng dưới to bơi hết vào đây nha! "
        "Em váy chữ A này hack dáng đỉnh chóp luôn, mặc lên nhìn thon hẳn 5 phân. "
        "Bấm ngay góc trái nhận mã freeship nha các bà!"
    )
    assert ToneValidator.validate(fashion_sample) is True
    assert ToneValidator.check_violations(fashion_sample) == []
    assert ToneValidator.has_koc_markers(fashion_sample) is True

    homelife_sample = (
        "Các bác ơi, từ ngày tậu em máy này việc nhà nhàn hẳn luôn á. "
        "3 giây sạch bóng kin kít không tốn sức. "
        "Link tui để ở giỏ hàng góc trái nè!"
    )
    assert ToneValidator.validate(homelife_sample) is True
    assert ToneValidator.check_violations(homelife_sample) == []
    assert ToneValidator.has_koc_markers(homelife_sample) is True


def test_tone_validator_blocks_robotic_cliches():
    """Ngăn chặn các mẫu câu bot máy móc."""
    robotic_samples = [
        "Xin chào quý khách, tôi là trợ lý AI.",
        "Sản phẩm này rất tốt và tiện ích, đáp ứng mọi nhu cầu của bạn.",
        "Sự lựa chọn hoàn hảo cho mọi gia đình. Hãy nhanh tay sở hữu!",
        "Cảm ơn quý khách đã tin tưởng, chúc quý khách một ngày tốt lành.",
    ]
    for sample in robotic_samples:
        assert ToneValidator.validate(sample) is False
        violations = ToneValidator.check_violations(sample)
        assert any("ROBOTIC_CLICHE" in v for v in violations)


def test_tone_validator_blocks_counterfeit_trademarks():
    """Ngăn chặn từ khóa nhái thương hiệu lớn và tiếng lóng hàng giả."""
    counterfeit_samples = [
        ("Váy Zara thiết kế tôn dáng", "Zara"),
        ("Túi Chanel rep 1:1 bao nét", "Chanel"),
        ("Giày Gucci super fake chuẩn auth", "Gucci"),
        ("Áo thun Dior hàng tuồn vnxk", "Dior"),
        ("Ví nữ LV hàng rep đẹp mê", "LV"),
        ("Giày Nike rep 1 1 siêu cấp", "Nike"),
    ]
    for text, brand in counterfeit_samples:
        assert ToneValidator.validate(text) is False
        violations = ToneValidator.check_violations(text)
        assert any("COUNTERFEIT_KEYWORD" in v for v in violations), f"Failed for {text}"


def test_tone_validator_blocks_exaggerated_claims():
    """Ngăn chặn cam kết y tế và quảng cáo quá đà."""
    exaggerated_samples = [
        "Cam kết trị dứt điểm 100% mụn thâm sau 7 ngày",
        "Chảo chống dính vĩnh viễn không bám bẩn, 100% không bao giờ hỏng",
        "Sản phẩm tốt nhất thị trường số 1 việt nam",
        "Thần dược chữa khỏi hoàn toàn chứng mất ngủ",
    ]
    for sample in exaggerated_samples:
        assert ToneValidator.validate(sample) is False
        violations = ToneValidator.check_violations(sample)
        assert any("EXAGGERATED_CLAIM" in v for v in violations)


def test_tone_validator_word_boundaries_no_false_positives():
    """Kiểm tra từ biên (Word Boundaries) để không bắt nhầm các từ tiếng Việt hợp lệ."""
    valid_vietnamese_texts = [
        "Lực lượng lao động trẻ trung",      # Không bắt nhầm 'lv'
        "Lưu ý khi giặt váy lụa",            # Không bắt nhầm 'lv'
        "Quản lý việc nhà nhàn tênh",        # Không bắt nhầm 'lv'
        "Uống một ly trà sữa mát lạnh",      # Không bắt nhầm 'lv'
        "Quần áo thời trang phong cách",    # Không bắt nhầm 'rep' hay 'f1'
    ]
    for text in valid_vietnamese_texts:
        violations = ToneValidator.check_violations(text)
        assert violations == [], f"False positive in: '{text}', violations: {violations}"
        assert ToneValidator.validate(text) is True
```

---

## 5. Verification Method

### 5.1 Verification Commands
Once the Worker creates the code files from these specifications, execute:
```bash
# 1. Chạy toàn bộ test cấu hình và ToneValidator
pytest tests/test_config.py -v

# 2. Kiểm tra syntax của script Telegram helper
python3 -m py_compile scripts/get_telegram_ids.py
python3 scripts/get_telegram_ids.py --help
```

### 5.2 Pass Criteria
1. `tests/test_config.py`: 8/8 tests pass with 0 warnings/failures.
2. `config.yaml`: Successfully parsed and validated by `load_config()`.
3. `ToneValidator`: Correctly flags 100% of tested robotic, counterfeit, and exaggerated texts, while passing authentic KOC sentences with 0 false positives on common Vietnamese words.
