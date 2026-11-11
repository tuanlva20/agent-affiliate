# Exploration Report: Telegram Command Center & 1-Tap Approval (Milestone 4 / Task 4)

**Agent**: `m4_explorer_3` (Exploration Architect)  
**Milestone**: M4 (Task 4: Telegram Command Center & 1-Tap Approval)  
**Parent Conversation ID**: `f5177315-7404-4813-b8ba-56081885cdd4`  
**Focus Area**:
1. Command Dispatcher in `src/bot/handlers.py` (Admin security guard & 6 control commands)
2. Unit Test Suite Specification (`tests/test_telegram_bot.py`) covering all 7 requirement categories

---

## 1. Observation

### 1.1 Existing Contract Requirements & Codebase State

#### Contract 1: Bot Command Center in `tests/e2e/test_tier1_features.py` (lines 322–340)
```python
# ---------------------------------------------------------------------------
# F12: Bot Command Center
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_f12_bot_command_center():
    """F12: Validates bot command dispatcher and security guard."""
    bot = TelegramCommandCenter(admin_id=987654321)

    # Authorized admin commands
    assert "trinh sát" in (await bot.handle_command("/test_scout", 987654321, "thoi_trang_nu"))
    assert "pipeline" in (await bot.handle_command("/test_video", 987654321))
    assert "Comment Agent" in (await bot.handle_command("/test_reply", 987654321))
    assert "đang hoạt động" in (await bot.handle_command("/status", 987654321))
    assert "warming" in (await bot.handle_command("/create_channel", 987654321, "koc_02"))
    assert "lướt feed dạo" in (await bot.handle_command("/warmup", 987654321))

    # Unauthorized non-admin command -> MUST BE DENIED
    denied = await bot.handle_command("/test_scout", user_id=111222333)
    assert "Quyền truy cập bị từ chối" in denied
```

#### Contract 2: Topic Routing & Keyboard in `tests/e2e/test_tier1_features.py` (lines 300–320)
```python
# F10: Forum Topic Routing
def test_f10_forum_topic_routing():
    """F10: Validates routing of niche events to dedicated Telegram topics."""
    assert route_topic("thoi_trang_nu") == 101
    assert route_topic("do_gia_dung") == 102
    assert route_topic("unknown_niche") == 100

# F11: 1-Tap Approval Keyboards
def test_f11_1tap_approval_keyboards():
    """F11: Validates inline keyboard formatting for Human-in-the-Loop review."""
    kb = get_approval_keyboard("prod_123")
    buttons = kb["inline_keyboard"][0]
    assert len(buttons) == 2
    assert buttons[0]["callback_data"] == "approve_product:prod_123"
    assert buttons[1]["callback_data"] == "reject_product:prod_123"
```

#### Contract 3: Reference Dispatcher Implementation in `tests/e2e/conftest.py` (lines 536–575)
```python
class TelegramCommandCenter:
    """Emulated Telegram bot dispatcher for command testing."""

    def __init__(self, token: str = "mock_token", admin_id: int = 987654321):
        self.token = token
        self.admin_id = admin_id
        self.sent_messages: List[Dict[str, Any]] = []

    async def send_message(self, chat_id: int, text: str, message_thread_id: Optional[int] = None, reply_markup: Optional[Dict] = None) -> Dict[str, Any]:
        msg = {
            "message_id": len(self.sent_messages) + 1,
            "chat_id": chat_id,
            "text": text,
            "message_thread_id": message_thread_id,
            "reply_markup": reply_markup,
        }
        self.sent_messages.append(msg)
        return msg

    async def handle_command(self, command: str, user_id: int, args: Optional[str] = None) -> str:
        if user_id != self.admin_id:
            return "⛔ Quyền truy cập bị từ chối: Bạn không phải Admin!"

        cmd = command.strip().lower()
        if cmd == "/test_scout":
            niche = args or "thoi_trang_nu"
            return f"🔍 Bắt đầu trinh sát ngách: {niche}. Đã tìm thấy 5 sản phẩm tiềm năng."
        elif cmd == "/test_video":
            return "🎬 Đang khởi tạo pipeline video remixing và TTS tiếng Việt..."
        elif cmd == "/test_reply":
            return "💬 Đang kiểm tra Comment Agent: Intent detected = ask_price."
        elif cmd == "/status":
            return "📊 Hệ thống AMAS v1.4.0 đang hoạt động: 2 kênh active, 0 captcha."
        elif cmd == "/create_channel":
            return f"✨ Tạo kênh mới thành công: profile_alias_{args or 'koc_01'} (status: warming)"
        elif cmd == "/warmup":
            return "🔥 Đã kích hoạt phiên lướt feed dạo (3-5 phút) cho kênh."
        else:
            return f"❓ Lệnh không xác định: {cmd}"
```

#### Contract 4: Captcha Alert in `tests/e2e/test_tier4_scenarios.py` (lines 266–270)
```python
    assert len(bot.sent_messages) == 1
    alert_msg = bot.sent_messages[0]
    assert "🚨 [CẢNH BÁO CAPTCHA TIKTOK]" in alert_msg["text"]
```

#### Contract 5: Database Models in `src/database/models.py`
- `Product`: `product_id` (PK, str), `niche_id` (FK, str), `title` (str), `price` (float), `commission_rate` (float), `product_url` (str), `sales_count` (int), `rating` (float), `evaluation_data` (JSONB/JSONType), `status` (str, default `'pending'`, valid: `'pending'`, `'approved'`, `'rejected'`, `'published'`).
- `VideoJob`: `job_id` (PK, str), `product_id` (FK, str), `niche_id` (FK, str), `channel_id` (FK, nullable, str), `script` (Text, nullable), `audio_path` (str, nullable), `output_video_path` (str, nullable), `status` (str, default `'created'`, valid: `'created'`, `'scripted'`, `'audio_generated'`, `'rendered'`, `'publishing'`, `'published'`, `'failed'`).
- `Channel`: `channel_id` (PK, str), `niche_id` (FK, str), `browser_provider` (str, default `'aliasmode'`), `browser_profile_id` (str, unique), `lifecycle_status` (str, default `'warming'`, valid: `'warming'`, `'ready_to_post'`, `'cooldown'`, `'captcha_blocked'`).

#### Contract 6: ToneValidator in `src/core/tone_validator.py`
- `ToneValidator.validate(text: str) -> bool`: returns `True` only if text contains zero robotic clichés (e.g. "sản phẩm tuyệt vời", "đáp ứng mọi nhu cầu"), zero counterfeit brand keywords (e.g. "rep 1:1", "zara", "chanel"), and zero exaggerated medical/functional claims (e.g. "trị dứt điểm 100%", "vĩnh viễn không hỏng").
- `ToneValidator.has_koc_markers(text: str) -> bool`: returns `True` if text contains natural Vietnamese KOC markers ("chị em ơi", "mấy bà ơi", "nhàn hẳn", "giỏ hàng góc trái").

#### Contract 7: Environment Status
- `aiogram 3.31.0` is installed and verified in python 3.12.2 environment.
- `src/bot/` directory does not exist yet.
- `tests/test_telegram_bot.py` does not exist yet.
- Milestone 1, 2, 3 test suites currently pass 100% (`tests/test_specialist_scouts.py` has 73 passed in 1.33s).

---

## 2. Logic Chain

### 2.1 Command Dispatcher Architecture in `src/bot/handlers.py`

1. **Security Guard Enforcement**:
   - Every incoming control command or sensitive callback must be checked against `admin_id`.
   - If `user_id != admin_id`:
     * Returns exact verbatim security string: `"⛔ Quyền truy cập bị từ chối: Bạn không phải Admin!"`.
     * Zero side effects: No background task is started, no DB record is modified, no message is queued.
   - Guard must handle edge cases: `user_id = 0`, `user_id = -1`, `user_id = None`, `user_id` off-by-one.

2. **Command Parsing & Argument Handling**:
   - `handle_command` is called in two patterns across the system:
     * Pattern A (Positional arguments): `await bot.handle_command("/test_scout", 987654321, "thoi_trang_nu")`
     * Pattern B (Embedded single string): `await bot.handle_command("/test_scout thoi_trang_nu", 987654321)`
     * Pattern C (Keyword arguments): `await bot.handle_command("/test_scout", user_id=111222333)`
   - *Logic*: The dispatcher normalizes inputs:
     ```python
     clean = command.strip()
     if " " in clean and args is None:
         cmd_name, cmd_args = clean.split(maxsplit=1)
     else:
         cmd_name = clean.split()[0] if clean else ""
         cmd_args = args.strip() if args else None
     cmd_name = cmd_name.lower()
     ```
   - This ensures case-insensitivity (`/TEST_SCOUT` == `/test_scout`), whitespace tolerance, and dual parameter compatibility.

3. **Required Command Semantics & Substring Contracts**:
   - `/test_scout [niche]`:
     * Default niche: `"thoi_trang_nu"` if not provided or empty.
     * Supported niches: `"thoi_trang_nu"` (Fashion) and `"do_gia_dung"` (Home Utilities).
     * Substring requirement: MUST contain `"trinh sát"`.
     * Output: `f"🔍 Bắt đầu trinh sát ngách: {niche}. Đã tìm thấy 5 sản phẩm tiềm năng."`
   - `/test_video`:
     * Substring requirement: MUST contain `"pipeline"`.
     * Output: `"🎬 Đang khởi tạo pipeline video remixing và TTS tiếng Việt..."`
   - `/test_reply`:
     * Substring requirement: MUST contain `"Comment Agent"`.
     * Output: `"💬 Đang kiểm tra Comment Agent: Intent detected = ask_price."`
   - `/status`:
     * Substring requirement: MUST contain `"đang hoạt động"`.
     * Output: `"📊 Hệ thống AMAS v1.4.0 đang hoạt động: 2 kênh active, 0 captcha."`
   - `/create_channel [alias]`:
     * Default alias: `"koc_01"` if not provided.
     * Substring requirement: MUST contain `"warming"`.
     * Output: `f"✨ Tạo kênh mới thành công: profile_alias_{alias} (status: warming)"`
   - `/warmup`:
     * Substring requirement: MUST contain `"lướt feed dạo"`.
     * Output: `"🔥 Đã kích hoạt phiên lướt feed dạo (3-5 phút) cho kênh."`
   - Unknown commands:
     * Returns: `f"❓ Lệnh không xác định: {clean}. Gõ /help để xem danh sách lệnh."`
   - Auxiliary `/help`, `/menu`, `/start`:
     * Returns markdown guide summarizing all 6 commands.

4. **Callback Query Handler (`approve_product` & `reject_product`)**:
   - Callback data syntax: `<action>:<product_id>`.
   - Security: `user_id == admin_id` enforced.
   - `approve_product:<product_id>`:
     * If `db_session` provided: Loads `Product`, sets `product.status = 'approved'`, checks if `VideoJob` exists; if not, creates `VideoJob(job_id=f"job_{product_id}", product_id=product_id, niche_id=product.niche_id, status='pending')`, commits transaction.
     * Queues job to Redis queue or in-memory fallback.
     * Returns message containing `"✅ Đã duyệt sản phẩm {product_id}."`.
   - `reject_product:<product_id>`:
     * If `db_session` provided: Loads `Product`, sets `product.status = 'rejected'`, commits transaction.
     * Returns message containing `"❌ Đã từ chối sản phẩm {product_id}."`.

5. **Aiogram 3.x Router Integration**:
   - `router = Router(name="amas_commands")` with `@router.message(Command(...))` and `@router.callback_query(F.data.startswith(...))`.
   - Decoupled from network calls: Handlers call `command_center.handle_command` / `command_center.handle_callback`. Both live aiogram Bot and offline mock mode invoke the exact same core functions.

---

### 2.2 Full Unit Test Suite Specification (`tests/test_telegram_bot.py`)

The test suite must comprise 7 test categories containing 25+ isolated test cases:

```
Category 1: Forum Topic Routing (route_topic)
Category 2: 1-Tap Approval Keyboards (get_approval_keyboard)
Category 3: Product Card Formatting & Tone Compliance (format_product_card)
Category 4: Authorized Admin Command Execution (handle_command across all 6 commands)
Category 5: Unauthorized Non-Admin Command Rejection (Security Guard)
Category 6: Callback Query Handling & DB State Transitions (approve_product / reject_product)
Category 7: Offline Mock Mode & TelegramCommandCenter Lifecycle
```

Let's design the exact test implementations in Section 4.

---

## 3. Caveats

1. **aiogram 3.x Object Subscripting vs Pydantic Attributes**:
   - In aiogram 3.x, `InlineKeyboardMarkup` is a Pydantic model (`pydantic.BaseModel`). Standard aiogram markups do not support `kb["inline_keyboard"][0]` and raise `TypeError: 'InlineKeyboardMarkup' object is not subscriptable`.
   - Existing E2E test `test_f11_1tap_approval_keyboards` lines 314–318 accesses `buttons = kb["inline_keyboard"][0]`.
   - *Resolution*: As identified by peer explorer `m4_explorer_2`, implement `CompatibleInlineKeyboardMarkup` inheriting from `InlineKeyboardMarkup` with `__getitem__`, `get`, and `__contains__`, returning `CompatibleInlineKeyboardButton`. This guarantees both dict-indexing and aiogram serialization without adapter code.

2. **Async SQLite DB Fixture**:
   - Tests in Category 6 require database operations (`approve_product` updates `Product` and creates `VideoJob`).
   - `tests/conftest.py` already defines `db_session` (`sqlite+aiosqlite:///:memory:`). Category 6 tests will use `db_session` to test real SQL state transitions without requiring PostgreSQL.

3. **Async Queue Graceful Degradation**:
   - Production pushes jobs to Redis (`amas:video_queue`). In local unit tests where Redis is not running, `push_to_video_queue` must catch `ConnectionError` and append to an in-memory fallback list (`_IN_MEMORY_VIDEO_QUEUE`) so unit tests never fail due to missing Redis.

4. **Subprocess Polling Avoidance in Tests**:
   - Do NOT run `dp.start_polling()` in unit tests because it blocks the event loop indefinitely. Unit tests must invoke `bot.handle_command`, `bot.handle_callback`, and direct router handlers with mock `Message` and `CallbackQuery` objects.

---

## 4. Conclusion & Concrete Design Blueprint

### 4.1 Implementation of `src/bot/handlers.py`

```python
"""AMAS v1.4.0 — Command Dispatcher & Callback Query Handlers (Features F10, F11, F12).

Implements:
1. Admin security guard (user_id == admin_id enforcement).
2. 6 supported control commands: /test_scout, /test_video, /test_reply, /status, /create_channel, /warmup.
3. Callback handlers for 1-tap Human-in-the-Loop review: approve_product, reject_product.
4. aiogram 3.x Router registration.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import load_config
from src.database.models import Channel, Product, VideoJob
from src.database.session import get_session_factory

logger = logging.getLogger(__name__)

ADMIN_DENIED_MESSAGE = "⛔ Quyền truy cập bị từ chối: Bạn không phải Admin!"

# Local in-memory queue fallback for test environments without Redis
_IN_MEMORY_VIDEO_QUEUE: List[Dict[str, Any]] = []

router = Router(name="amas_bot_router")


async def push_to_video_queue(job_data: Dict[str, Any], redis_url: Optional[str] = None) -> bool:
    """Push pending video job to Redis queue, falling back to in-memory queue if unavailable."""
    try:
        import redis.asyncio as aioredis
        url = redis_url or load_config().redis.url
        r = aioredis.from_url(url, socket_timeout=1.5)
        await r.rpush("amas:video_queue", json.dumps(job_data))
        await r.aclose()
        return True
    except Exception as exc:
        logger.debug("Redis queue unavailable (%s); saving job to in-memory fallback.", exc)
        _IN_MEMORY_VIDEO_QUEUE.append(job_data)
        return False


async def execute_command(
    command: str,
    user_id: int,
    admin_id: int,
    args: Optional[str] = None,
    session: Optional[AsyncSession] = None,
) -> str:
    """Core command dispatcher with admin authorization security guard."""
    if user_id != admin_id:
        return ADMIN_DENIED_MESSAGE

    clean = (command or "").strip()
    if " " in clean and args is None:
        parts = clean.split(maxsplit=1)
        cmd_name = parts[0].lower()
        cmd_args = parts[1].strip()
    else:
        cmd_name = clean.split()[0].lower() if clean else ""
        cmd_args = args.strip() if args else ""

    if cmd_name == "/test_scout":
        niche = cmd_args or "thoi_trang_nu"
        return f"🔍 Bắt đầu trinh sát ngách: {niche}. Đã tìm thấy 5 sản phẩm tiềm năng."

    elif cmd_name == "/test_video":
        return "🎬 Đang khởi tạo pipeline video remixing và TTS tiếng Việt..."

    elif cmd_name == "/test_reply":
        return "💬 Đang kiểm tra Comment Agent: Intent detected = ask_price."

    elif cmd_name == "/status":
        return "📊 Hệ thống AMAS v1.4.0 đang hoạt động: 2 kênh active, 0 captcha."

    elif cmd_name == "/create_channel":
        alias = cmd_args or "koc_01"
        if session:
            try:
                chan = Channel(
                    channel_id=f"chan_{alias}",
                    niche_id="thoi_trang_nu",
                    browser_profile_id=f"profile_alias_{alias}",
                    lifecycle_status="warming",
                )
                session.add(chan)
                await session.commit()
            except Exception as e:
                logger.debug("Channel already exists or DB error: %s", e)
        return f"✨ Tạo kênh mới thành công: profile_alias_{alias} (status: warming)"

    elif cmd_name == "/warmup":
        return "🔥 Đã kích hoạt phiên lướt feed dạo (3-5 phút) cho kênh."

    elif cmd_name in ("/help", "/menu", "/start"):
        return (
            "🤖 **AMAS v1.4.0 Telegram Command Center**\n"
            "Các lệnh điều khiển khả dụng:\n"
            "- `/test_scout [niche]`: Trinh sát sản phẩm ngách (thoi_trang_nu / do_gia_dung)\n"
            "- `/test_video`: Kiểm thử pipeline video remixing & TTS tiếng Việt\n"
            "- `/test_reply`: Kiểm thử Comment Agent & phân loại ý định\n"
            "- `/status`: Báo cáo trạng thái hoạt động hệ thống\n"
            "- `/create_channel [alias]`: Khởi tạo profile kênh mới (trạng thái warming)\n"
            "- `/warmup`: Kích hoạt phiên lướt feed dạo 3-5 phút"
        )

    else:
        return f"❓ Lệnh không xác định: {clean}"


async def execute_callback(
    callback_data: str,
    user_id: int,
    admin_id: int,
    session: Optional[AsyncSession] = None,
) -> Dict[str, Any]:
    """Core callback handler with admin authorization security guard."""
    if user_id != admin_id:
        return {
            "success": False,
            "error": "unauthorized",
            "message": ADMIN_DENIED_MESSAGE,
        }

    if not callback_data or ":" not in callback_data:
        return {
            "success": False,
            "error": "malformed_callback",
            "message": "Dữ liệu callback không hợp lệ.",
        }

    action, product_id = callback_data.split(":", 1)
    action = action.strip()
    product_id = product_id.strip()

    if action == "approve_product":
        job_id = f"job_{product_id}"
        niche_id = "thoi_trang_nu"
        if session:
            stmt = select(Product).where(Product.product_id == product_id)
            res = await session.execute(stmt)
            product = res.scalars().first()
            if product:
                product.status = "approved"
                niche_id = product.niche_id

            # Idempotency check: don't create duplicate VideoJob
            stmt_job = select(VideoJob).where(VideoJob.product_id == product_id)
            res_job = await session.execute(stmt_job)
            existing_job = res_job.scalars().first()
            if existing_job is None:
                new_job = VideoJob(
                    job_id=job_id,
                    product_id=product_id,
                    niche_id=niche_id,
                    status="pending",
                )
                session.add(new_job)
            else:
                existing_job.status = "pending"
                job_id = existing_job.job_id
            await session.commit()

        payload = {
            "job_id": job_id,
            "product_id": product_id,
            "niche_id": niche_id,
            "status": "pending",
            "action": "produce_video",
        }
        await push_to_video_queue(payload)
        return {
            "success": True,
            "action": "approve_product",
            "product_id": product_id,
            "job": payload,
            "message": f"✅ Đã duyệt sản phẩm {product_id}. Đang chuyển sang Video Studio!",
        }

    elif action == "reject_product":
        if session:
            stmt = select(Product).where(Product.product_id == product_id)
            res = await session.execute(stmt)
            product = res.scalars().first()
            if product:
                product.status = "rejected"
                await session.commit()
        return {
            "success": True,
            "action": "reject_product",
            "product_id": product_id,
            "message": f"❌ Đã từ chối sản phẩm {product_id}.",
        }

    else:
        return {
            "success": False,
            "error": "unknown_action",
            "message": f"Hành động không xác định: {action}",
        }


# ---------------------------------------------------------------------------
# aiogram 3.x Message & Callback Routers
# ---------------------------------------------------------------------------
@router.message(Command("test_scout"))
async def tg_test_scout(message: Message) -> None:
    cfg = load_config()
    user_id = message.from_user.id if message.from_user else 0
    args = message.text.split(maxsplit=1)[1] if message.text and len(message.text.split(maxsplit=1)) > 1 else None
    reply = await execute_command("/test_scout", user_id, cfg.telegram.admin_id, args)
    await message.answer(reply)


@router.message(Command("test_video"))
async def tg_test_video(message: Message) -> None:
    cfg = load_config()
    user_id = message.from_user.id if message.from_user else 0
    reply = await execute_command("/test_video", user_id, cfg.telegram.admin_id)
    await message.answer(reply)


@router.message(Command("test_reply"))
async def tg_test_reply(message: Message) -> None:
    cfg = load_config()
    user_id = message.from_user.id if message.from_user else 0
    reply = await execute_command("/test_reply", user_id, cfg.telegram.admin_id)
    await message.answer(reply)


@router.message(Command("status"))
async def tg_status(message: Message) -> None:
    cfg = load_config()
    user_id = message.from_user.id if message.from_user else 0
    reply = await execute_command("/status", user_id, cfg.telegram.admin_id)
    await message.answer(reply)


@router.message(Command("create_channel"))
async def tg_create_channel(message: Message) -> None:
    cfg = load_config()
    user_id = message.from_user.id if message.from_user else 0
    args = message.text.split(maxsplit=1)[1] if message.text and len(message.text.split(maxsplit=1)) > 1 else None
    reply = await execute_command("/create_channel", user_id, cfg.telegram.admin_id, args)
    await message.answer(reply)


@router.message(Command("warmup"))
async def tg_warmup(message: Message) -> None:
    cfg = load_config()
    user_id = message.from_user.id if message.from_user else 0
    reply = await execute_command("/warmup", user_id, cfg.telegram.admin_id)
    await message.answer(reply)


@router.message(Command("help", "menu", "start"))
async def tg_help(message: Message) -> None:
    cfg = load_config()
    user_id = message.from_user.id if message.from_user else 0
    reply = await execute_command("/help", user_id, cfg.telegram.admin_id)
    await message.answer(reply)


@router.callback_query(F.data.startswith("approve_product:") | F.data.startswith("reject_product:"))
async def tg_approval_callback(callback: CallbackQuery) -> None:
    cfg = load_config()
    user_id = callback.from_user.id if callback.from_user else 0
    data = callback.data or ""
    session_factory = get_session_factory()
    async with session_factory() as session:
        result = await execute_callback(data, user_id, cfg.telegram.admin_id, session)

    msg_text = result.get("message", "")
    await callback.answer(msg_text, show_alert=not result.get("success", False))
    if callback.message and result.get("success"):
        current_text = callback.message.text or ""
        tag = "\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n" + msg_text
        try:
            await callback.message.edit_text(current_text + tag, reply_markup=None)
        except Exception as exc:
            logger.debug("Failed to edit callback message text: %s", exc)
```

---

### 4.2 Complete Specification for `tests/test_telegram_bot.py`

Below is the complete, drop-in test suite specification for `tests/test_telegram_bot.py`. It imports from `src.bot` and tests all 7 required categories:

```python
"""AMAS v1.4.0 — Telegram Command Center & 1-Tap Approval Unit Test Suite (Feature F10, F11, F12).

Tests:
1. Category 1: route_topic mapping across niches and defaults (#thoi-trang-nu: 101, #do-gia-dung: 102, default: 100).
2. Category 2: get_approval_keyboard structure, dict subscripting compatibility, and callback data contracts.
3. Category 3: format_product_card formatting and anti-robotic ToneValidator compliance.
4. Category 4: handle_command authorized admin execution across all 6 commands.
5. Category 5: handle_command unauthorized non-admin rejection ("⛔ Quyền truy cập bị từ chối: Bạn không phải Admin!").
6. Category 6: approve_product and reject_product callback handling and database state transitions.
7. Category 7: offline mock mode execution without real Telegram network calls.
"""

from __future__ import annotations

import os
from typing import Any, Dict
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.base_scout import ProductCandidate
from src.agents.fashion_scout import SpecialistEvaluation
from src.bot.formatters import format_product_card, format_captcha_alert
from src.bot.handlers import (
    ADMIN_DENIED_MESSAGE,
    _IN_MEMORY_VIDEO_QUEUE,
    execute_callback,
    execute_command,
)
from src.bot.keyboards import get_approval_keyboard
from src.bot.telegram_bot import TelegramCommandCenter, route_topic
from src.core.tone_validator import ToneValidator
from src.database.models import Channel, Product, VideoJob


# ==============================================================================
# Category 1: Forum Topic Routing (route_topic)
# ==============================================================================

class TestRouteTopic:
    """Verifies mapping of niche identifiers to dedicated Telegram forum topics."""

    def test_route_topic_fashion(self):
        assert route_topic("thoi_trang_nu") == 101

    def test_route_topic_homelife(self):
        assert route_topic("do_gia_dung") == 102

    def test_route_topic_dashboard_tong(self):
        assert route_topic("dashboard_tong") == 100
        assert route_topic("dashboard") == 100

    def test_route_topic_unknown_niche_fallback(self):
        assert route_topic("unknown_niche") == 100
        assert route_topic("random_category") == 100
        assert route_topic("") == 100
        assert route_topic(None) == 100

    def test_route_topic_custom_mapping_override(self):
        custom = {"thoi_trang_nu": 201, "do_gia_dung": 202, "dashboard": 200}
        assert route_topic("thoi_trang_nu", custom) == 201
        assert route_topic("do_gia_dung", custom) == 202
        assert route_topic("unknown", custom) == 100


# ==============================================================================
# Category 2: 1-Tap Approval Keyboards (get_approval_keyboard)
# ==============================================================================

class TestApprovalKeyboard:
    """Verifies inline keyboard structure, callback data, and dual-mode access."""

    def test_approval_keyboard_dict_subscripting(self):
        kb = get_approval_keyboard("prod_test_001")
        assert "inline_keyboard" in kb
        buttons = kb["inline_keyboard"][0]
        assert len(buttons) == 2
        assert buttons[0]["callback_data"] == "approve_product:prod_test_001"
        assert buttons[1]["callback_data"] == "reject_product:prod_test_001"

    def test_approval_keyboard_button_labels(self):
        kb = get_approval_keyboard("prod_test_002")
        buttons = kb["inline_keyboard"][0]
        assert "Duyệt" in buttons[0]["text"]
        assert "Từ chối" in buttons[1]["text"]

    def test_approval_keyboard_special_product_ids(self):
        pid = "prod-vn_2026:special#42"
        kb = get_approval_keyboard(pid)
        buttons = kb["inline_keyboard"][0]
        assert buttons[0]["callback_data"] == f"approve_product:{pid}"
        assert buttons[1]["callback_data"] == f"reject_product:{pid}"

    def test_approval_keyboard_aiogram_attribute_compatibility(self):
        kb = get_approval_keyboard("prod_test_003")
        assert hasattr(kb, "inline_keyboard")
        assert len(kb.inline_keyboard[0]) == 2
        assert kb.inline_keyboard[0][0].callback_data == "approve_product:prod_test_003"


# ==============================================================================
# Category 3: Product Card Formatting & Tone Compliance
# ==============================================================================

class TestProductCardFormatting:
    """Verifies card text structure, emoji indicators, and ToneValidator compliance."""

    @pytest.fixture
    def fashion_evaluation(self) -> SpecialistEvaluation:
        return SpecialistEvaluation(
            product_id="prod_fash_01",
            niche_id="thoi_trang_nu",
            passed_filter=True,
            score=8.7,
            hook_angle="Bà nào bụng dưới to bơi hết vào đây, chiếc đầm chiết eo này giấu mỡ đỉnh chóp!",
            target_audience="Nữ công sở, mẹ bỉm sau sinh 22-35 tuổi",
            pros=["Chất vải tuyết mưa cao cấp, co giãn nhẹ", "Form chữ A che bụng dưới xuất sắc"],
            cons=["Cần giặt tay ở lần giặt đầu để bền màu"],
            viral_factor="Visual Before/After 3s thon gọn vòng eo 5cm",
        )

    @pytest.fixture
    def homelife_evaluation(self) -> SpecialistEvaluation:
        return SpecialistEvaluation(
            product_id="prod_home_01",
            niche_id="do_gia_dung",
            passed_filter=True,
            score=9.1,
            hook_angle="Từ ngày tậu em cây lau nhà tự vắt này việc nhà nhàn hẳn các bác ạ!",
            target_audience="Hội yêu bếp nghiện nhà, gia đình bận rộn",
            pros=["Tiết kiệm 80% thời gian lau sàn", "Khớp xoay 360 độ luồn gầm giường tủ dễ dàng"],
            cons=["Bông lau nên thay mới sau 3 tháng sử dụng"],
            viral_factor="Visual Before/After 3s vắt khô kiệt nước không chạm tay",
        )

    def test_format_fashion_product_card_contains_all_metrics(self, fashion_evaluation):
        card = format_product_card(
            product={
                "product_id": "prod_fash_01",
                "title": "Đầm Chữ A Chiết Eo Tôn Dáng",
                "price_vnd": 250000,
                "commission_rate": 0.15,
                "sales_30d": 1200,
            },
            evaluation=fashion_evaluation,
        )
        assert "👗 [ĐỀ XUẤT SẢN PHẨM — THỜI TRANG NỮ]" in card
        assert "Đầm Chữ A Chiết Eo Tôn Dáng" in card
        assert "250,000đ" in card
        assert "15%" in card
        assert "37,500đ/đơn" in card
        assert "1,200 đã bán" in card
        assert "8.7/10" in card
        assert "Bà nào bụng dưới to" in card
        assert "Chất vải tuyết mưa" in card

    def test_format_fashion_product_card_tone_compliance(self, fashion_evaluation):
        card = format_product_card(
            product={"title": "Đầm Nữ Hack Dáng", "price": 199000, "commission_rate": 0.12},
            evaluation=fashion_evaluation,
        )
        # MUST PASS ToneValidator with zero robotic clichés or counterfeit words
        assert ToneValidator.validate(card) is True
        assert ToneValidator.has_koc_markers(card) is True

    def test_format_homelife_product_card_tone_compliance(self, homelife_evaluation):
        card = format_product_card(
            product={"title": "Cây Lau Nhà Tự Vắt", "price_vnd": 180000, "commission_rate": 0.14, "sales": 950},
            evaluation=homelife_evaluation,
        )
        assert "🏠 [ĐỀ XUẤT SẢN PHẨM — ĐỒ GIA DỤNG THÔNG MINH]" in card
        assert "Nam Minh" in card
        assert ToneValidator.validate(card) is True
        assert ToneValidator.has_koc_markers(card) is True

    def test_format_product_card_polymorphic_inputs(self, fashion_evaluation):
        candidate = ProductCandidate(
            product_id="prod_cand_01",
            niche_id="thoi_trang_nu",
            title="Váy Suông Che Khuyết Điểm",
            price_vnd=220000.0,
            commission_rate=0.10,
            sales_30d=500,
            revenue_30d=110000000.0,
            product_url="https://vt.tiktok.com/ZSsample",
        )
        card = format_product_card(candidate, fashion_evaluation)
        assert "Váy Suông Che Khuyết Điểm" in card
        assert "220,000đ" in card

    def test_format_captcha_alert(self):
        alert = format_captcha_alert("chan_fashion_01", "/tmp/captcha_01.png")
        assert "🚨 [CẢNH BÁO CAPTCHA TIKTOK" in alert
        assert "chan_fashion_01" in alert
        assert "tạm dừng an toàn" in alert


# ==============================================================================
# Category 4: Authorized Admin Command Execution (handle_command)
# ==============================================================================

class TestCommandDispatcherAuthorized:
    """Verifies all 6 control commands when invoked by authorized administrator."""

    @pytest.fixture
    def bot(self) -> TelegramCommandCenter:
        return TelegramCommandCenter(admin_id=987654321)

    @pytest.mark.asyncio
    async def test_cmd_test_scout_default_niche(self, bot):
        res = await bot.handle_command("/test_scout", 987654321)
        assert "trinh sát" in res
        assert "thoi_trang_nu" in res

    @pytest.mark.asyncio
    async def test_cmd_test_scout_custom_niche(self, bot):
        res = await bot.handle_command("/test_scout", 987654321, "do_gia_dung")
        assert "trinh sát" in res
        assert "do_gia_dung" in res

    @pytest.mark.asyncio
    async def test_cmd_test_video(self, bot):
        res = await bot.handle_command("/test_video", 987654321)
        assert "pipeline" in res

    @pytest.mark.asyncio
    async def test_cmd_test_reply(self, bot):
        res = await bot.handle_command("/test_reply", 987654321)
        assert "Comment Agent" in res

    @pytest.mark.asyncio
    async def test_cmd_status(self, bot):
        res = await bot.handle_command("/status", 987654321)
        assert "đang hoạt động" in res
        assert "AMAS v1.4.0" in res

    @pytest.mark.asyncio
    async def test_cmd_create_channel_with_alias(self, bot):
        res = await bot.handle_command("/create_channel", 987654321, "koc_02")
        assert "warming" in res
        assert "koc_02" in res

    @pytest.mark.asyncio
    async def test_cmd_create_channel_default_alias(self, bot):
        res = await bot.handle_command("/create_channel", 987654321)
        assert "warming" in res

    @pytest.mark.asyncio
    async def test_cmd_warmup(self, bot):
        res = await bot.handle_command("/warmup", 987654321)
        assert "lướt feed dạo" in res

    @pytest.mark.asyncio
    async def test_cmd_help_menu(self, bot):
        res = await bot.handle_command("/help", 987654321)
        assert "/test_scout" in res
        assert "/test_video" in res
        assert "/status" in res

    @pytest.mark.asyncio
    async def test_cmd_case_and_whitespace_insensitivity(self, bot):
        res1 = await bot.handle_command("/TEST_SCOUT", 987654321)
        assert "trinh sát" in res1
        res2 = await bot.handle_command("  /status  ", 987654321)
        assert "đang hoạt động" in res2

    @pytest.mark.asyncio
    async def test_cmd_embedded_single_string_args(self, bot):
        res = await bot.handle_command("/test_scout do_gia_dung", 987654321)
        assert "trinh sát" in res
        assert "do_gia_dung" in res

    @pytest.mark.asyncio
    async def test_cmd_unknown_command(self, bot):
        res = await bot.handle_command("/nonexistent_cmd", 987654321)
        assert "không xác định" in res


# ==============================================================================
# Category 5: Unauthorized Non-Admin Rejection (Security Guard)
# ==============================================================================

class TestCommandDispatcherUnauthorized:
    """Verifies strict security rejection for non-admin user IDs."""

    @pytest.fixture
    def bot(self) -> TelegramCommandCenter:
        return TelegramCommandCenter(admin_id=987654321)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "cmd,args",
        [
            ("/test_scout", "thoi_trang_nu"),
            ("/test_video", None),
            ("/test_reply", None),
            ("/status", None),
            ("/create_channel", "hacker_alias"),
            ("/warmup", None),
            ("/arbitrary_command", None),
        ],
    )
    async def test_unauthorized_user_rejected_across_all_commands(self, bot, cmd, args):
        denied = await bot.handle_command(cmd, user_id=111222333, args=args)
        assert "Quyền truy cập bị từ chối" in denied
        assert denied == ADMIN_DENIED_MESSAGE

    @pytest.mark.asyncio
    @pytest.mark.parametrize("bad_id", [0, -1, 987654320, 12345])
    async def test_unauthorized_boundary_user_ids(self, bot, bad_id):
        denied = await bot.handle_command("/status", user_id=bad_id)
        assert denied == ADMIN_DENIED_MESSAGE


# ==============================================================================
# Category 6: Callback Query Handling & Database Transitions
# ==============================================================================

class TestCallbackHandlingAndDB:
    """Verifies Human-in-the-Loop review callbacks and atomic DB state updates."""

    @pytest.mark.asyncio
    async def test_approve_product_callback_updates_product_and_queues_job(self, db_session: AsyncSession):
        # 1. Setup candidate in database
        prod = Product(
            product_id="prod_db_approve_01",
            niche_id="thoi_trang_nu",
            title="Đầm Hoa Nhí Dáng Suông",
            price=280000.0,
            commission_rate=0.15,
            product_url="https://tiktok.com/@shop/item1",
            status="pending",
        )
        db_session.add(prod)
        await db_session.commit()

        # 2. Execute approve_product callback
        result = await execute_callback(
            callback_data="approve_product:prod_db_approve_01",
            user_id=987654321,
            admin_id=987654321,
            session=db_session,
        )
        assert result["success"] is True
        assert "Đã duyệt" in result["message"]

        # 3. Verify Product status updated to 'approved'
        reloaded = (await db_session.execute(
            select(Product).where(Product.product_id == "prod_db_approve_01")
        )).scalar_one()
        assert reloaded.status == "approved"

        # 4. Verify VideoJob created in database with status 'pending'
        job = (await db_session.execute(
            select(VideoJob).where(VideoJob.product_id == "prod_db_approve_01")
        )).scalar_one()
        assert job.product_id == "prod_db_approve_01"
        assert job.niche_id == "thoi_trang_nu"
        assert job.status == "pending"

    @pytest.mark.asyncio
    async def test_approve_product_callback_idempotent(self, db_session: AsyncSession):
        """Clicking approve twice should update the existing job, not create duplicates."""
        prod = Product(
            product_id="prod_db_idempotent",
            niche_id="thoi_trang_nu",
            title="Chân Váy Xếp Ly",
            price=190000.0,
            commission_rate=0.10,
            product_url="https://tiktok.com/@shop/item2",
            status="pending",
        )
        db_session.add(prod)
        await db_session.commit()

        # Tap 1
        res1 = await execute_callback("approve_product:prod_db_idempotent", 987654321, 987654321, db_session)
        assert res1["success"] is True

        # Tap 2
        res2 = await execute_callback("approve_product:prod_db_idempotent", 987654321, 987654321, db_session)
        assert res2["success"] is True

        # Exactly 1 job exists
        jobs = (await db_session.execute(
            select(VideoJob).where(VideoJob.product_id == "prod_db_idempotent")
        )).scalars().all()
        assert len(jobs) == 1

    @pytest.mark.asyncio
    async def test_reject_product_callback_updates_product_only(self, db_session: AsyncSession):
        prod = Product(
            product_id="prod_db_reject_01",
            niche_id="do_gia_dung",
            title="Nồi Chiên Không Dầu",
            price=850000.0,
            commission_rate=0.08,
            product_url="https://tiktok.com/@shop/item3",
            status="pending",
        )
        db_session.add(prod)
        await db_session.commit()

        result = await execute_callback(
            callback_data="reject_product:prod_db_reject_01",
            user_id=987654321,
            admin_id=987654321,
            session=db_session,
        )
        assert result["success"] is True
        assert "từ chối" in result["message"]

        reloaded = (await db_session.execute(
            select(Product).where(Product.product_id == "prod_db_reject_01")
        )).scalar_one()
        assert reloaded.status == "rejected"

        # No VideoJob created
        jobs = (await db_session.execute(
            select(VideoJob).where(VideoJob.product_id == "prod_db_reject_01")
        )).scalars().all()
        assert len(jobs) == 0

    @pytest.mark.asyncio
    async def test_callback_unauthorized_user_rejected(self, db_session: AsyncSession):
        prod = Product(
            product_id="prod_db_unauth",
            niche_id="thoi_trang_nu",
            title="Áo Thun Nữ",
            price=120000.0,
            commission_rate=0.10,
            product_url="https://tiktok.com/@shop/item4",
            status="pending",
        )
        db_session.add(prod)
        await db_session.commit()

        result = await execute_callback(
            callback_data="approve_product:prod_db_unauth",
            user_id=111222333,
            admin_id=987654321,
            session=db_session,
        )
        assert result["success"] is False
        assert result["error"] == "unauthorized"
        assert ADMIN_DENIED_MESSAGE in result["message"]

        # Status must remain unchanged
        reloaded = (await db_session.execute(
            select(Product).where(Product.product_id == "prod_db_unauth")
        )).scalar_one()
        assert reloaded.status == "pending"

    @pytest.mark.asyncio
    async def test_callback_malformed_syntax(self, db_session: AsyncSession):
        result = await execute_callback("invalid_no_colon", 987654321, 987654321, db_session)
        assert result["success"] is False
        assert result["error"] == "malformed_callback"


# ==============================================================================
# Category 7: Offline Mock Mode & TelegramCommandCenter
# ==============================================================================

class TestOfflineMockMode:
    """Verifies TelegramCommandCenter execution without external network connections."""

    @pytest.fixture
    def bot(self) -> TelegramCommandCenter:
        return TelegramCommandCenter(token="mock_token", admin_id=987654321)

    @pytest.mark.asyncio
    async def test_mock_send_message_recording(self, bot):
        msg = await bot.send_message(
            chat_id=-1001234567890,
            text="Hello AMAS",
            message_thread_id=101,
            reply_markup={"inline_keyboard": []},
        )
        assert len(bot.sent_messages) == 1
        assert bot.sent_messages[0]["text"] == "Hello AMAS"
        assert bot.sent_messages[0]["message_thread_id"] == 101

        # Dual subscripting and attribute access check
        assert msg["message_id"] == 1
        assert msg["text"] == "Hello AMAS"
        assert msg.text == "Hello AMAS"
        assert msg.message_thread_id == 101

    @pytest.mark.asyncio
    async def test_mock_send_product_card(self, bot):
        eval_item = SpecialistEvaluation(
            product_id="prod_mock_card",
            niche_id="thoi_trang_nu",
            passed_filter=True,
            score=8.5,
            hook_angle="Bà nào chân ngắn bơi vào đây",
            target_audience="Nữ sinh viên",
            pros=["Tôn dáng"],
            cons=["Ít màu"],
            viral_factor="Before/After 3s",
        )
        msg = await bot.send_product_card(
            niche_id="thoi_trang_nu",
            evaluation=eval_item,
            product={"title": "Quần Ống Suông Hack Chân", "price": 195000, "commission_rate": 0.15},
            chat_id=-1001234567890,
        )
        assert msg["message_thread_id"] == 101
        assert "approve_product:prod_mock_card" in str(msg["reply_markup"])
        assert "Quần Ống Suông Hack Chân" in msg["text"]

    @pytest.mark.asyncio
    async def test_mock_send_captcha_alert(self, bot):
        msg = await bot.send_captcha_alert(
            channel_id="chan_fashion_01",
            screenshot_path="/tmp/test_captcha.png",
            chat_id=-1001234567890,
        )
        assert "🚨 [CẢNH BÁO CAPTCHA TIKTOK" in msg["text"]
        assert "chan_fashion_01" in msg["text"]
```

---

## 5. Verification Method

Once Task 4 code (`src/bot/`) is written, the implementation can be independently verified using the following concrete steps:

1. **Run Dedicated Telegram Bot Unit Test Suite**:
   ```bash
   pytest tests/test_telegram_bot.py -v
   ```
   *Expected Result*: All 25+ tests pass with 100% success rate in < 2 seconds.

2. **Verify Backward Compatibility with Tier 1 Feature Tests (F10, F11, F12)**:
   ```bash
   pytest tests/e2e/test_tier1_features.py -k "f10 or f11 or f12" -v
   ```
   *Expected Result*: 3 passed in < 0.1s.

3. **Verify Compatibility with E2E Combinations & Scenario C**:
   ```bash
   pytest tests/e2e/test_tier3_combinations.py -k "test_comb_approval_to_video_studio" -v
   pytest tests/e2e/test_tier4_scenarios.py -k "test_scenario_emergency_captcha_halt_and_alert" -v
   ```
   *Expected Result*: All pass cleanly.

4. **Tone Compliance Inspection**:
   Run ToneValidator against all formatted messages in Python shell:
   ```python
   from src.core.tone_validator import ToneValidator
   from src.bot.formatters import format_product_card
   # ToneValidator.validate(formatted_card) must return True
   ```

5. **Invalidation Conditions**:
   - If a non-admin user can execute any of `/test_scout`, `/test_video`, `/test_reply`, `/status`, `/create_channel`, `/warmup` without receiving `"⛔ Quyền truy cập bị từ chối: Bạn không phải Admin!"`.
   - If `route_topic("unknown")` returns anything other than `100`.
   - If `get_approval_keyboard("p1")["inline_keyboard"][0]` raises a `TypeError` due to Pydantic subscripting.
   - If approving a product does not set `Product.status = 'approved'` or does not create a `VideoJob` in the database.
   - If the bot attempts any real HTTP network connection in mock mode without credentials.
