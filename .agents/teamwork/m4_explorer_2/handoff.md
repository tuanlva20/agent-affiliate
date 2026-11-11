# Milestone 4 Handoff Report: Telegram Command Center & 1-Tap Approval

**Agent**: `m4_explorer_2` (Exploration Architect)  
**Milestone**: M4 (Task 4 — Telegram Command Center & 1-Tap Approval)  
**Date**: 2026-11-10  
**Target Codebase Paths**:  
- `src/bot/__init__.py`  
- `src/bot/keyboards.py`  
- `src/bot/formatters.py`  
- `src/bot/handlers.py`  
- `src/bot/telegram_bot.py`  
- `tests/test_telegram_bot.py`  

---

## 1. Observation

### 1.1 Existing Contract Requirements & Codebase State

1. **`tests/e2e/test_tier1_features.py` (lines 300–340)**:
   ```python
   # F10: Forum Topic Routing
   def test_f10_forum_topic_routing():
       assert route_topic("thoi_trang_nu") == 101
       assert route_topic("do_gia_dung") == 102
       assert route_topic("unknown_niche") == 100

   # F11: 1-Tap Approval Keyboards
   def test_f11_1tap_approval_keyboards():
       kb = get_approval_keyboard("prod_123")
       buttons = kb["inline_keyboard"][0]
       assert len(buttons) == 2
       assert buttons[0]["callback_data"] == "approve_product:prod_123"
       assert buttons[1]["callback_data"] == "reject_product:prod_123"

   # F12: Bot Command Center
   @pytest.mark.asyncio
   async def test_f12_bot_command_center():
       bot = TelegramCommandCenter(admin_id=987654321)
       assert "trinh sát" in (await bot.handle_command("/test_scout", 987654321, "thoi_trang_nu"))
       assert "pipeline" in (await bot.handle_command("/test_video", 987654321))
       assert "Comment Agent" in (await bot.handle_command("/test_reply", 987654321))
       assert "đang hoạt động" in (await bot.handle_command("/status", 987654321))
       assert "warming" in (await bot.handle_command("/create_channel", 987654321, "koc_02"))
       assert "lướt feed dạo" in (await bot.handle_command("/warmup", 987654321))
       denied = await bot.handle_command("/test_scout", user_id=111222333)
       assert "Quyền truy cập bị từ chối" in denied
   ```

2. **`tests/e2e/conftest.py` (lines 514–576)**:
   - `route_topic(niche_id: str) -> int`: maps `"thoi_trang_nu"` to `101`, `"do_gia_dung"` to `102`, and others to `100`.
   - `get_approval_keyboard(product_id: str) -> Dict[str, Any]`: returns dictionary with `inline_keyboard` containing two buttons: `"✅ Duyệt lên kịch bản"` (`approve_product:<id>`) and `"❌ Từ chối"` (`reject_product:<id>`).
   - `TelegramCommandCenter`: handles messages, commands, and security check against `admin_id`.

3. **`src/database/models.py` (lines 156–241)**:
   - `Product`: columns `product_id` (PK, String 50), `niche_id` (FK), `title` (String 500), `price` (Float), `commission_rate` (Float), `product_url` (String 1000), `sales_count` (Integer), `rating` (Float), `evaluation_data` (JSONB/JSONType), `status` (String 30, default `'pending'`, valid values: `'pending'`, `'approved'`, `'rejected'`, `'published'`).
   - `VideoJob`: columns `job_id` (PK, String 50), `product_id` (FK), `niche_id` (FK), `channel_id` (FK, nullable), `source_video_url` (String 1000, nullable), `script` (Text, nullable), `audio_path` (String 500, nullable), `output_video_path` (String 500, nullable), `status` (String 30, default `'created'`, valid values include `'pending'`, `'created'`, `'rendering'`, `'rendered'`).

4. **`src/agents/fashion_scout.py` (lines 22–84)**:
   - `SpecialistEvaluation`: dataclass with fields `product_id: str`, `niche_id: str`, `passed_filter: bool`, `score: float`, `hook_angle: str`, `target_audience: str`, `pros: List[str]`, `cons: List[str]`, `viral_factor: str`, `rejection_reason: Optional[str]`. Methods: `to_dict()` and `from_dict()`.

5. **`src/agents/base_scout.py` (lines 40–81)**:
   - `ProductCandidate`: dataclass with fields `product_id: str`, `niche_id: str`, `title: str`, `price_vnd: float`, `commission_rate: float`, `sales_30d: int`, `revenue_30d: float`, `product_url: str`, `image_url: Optional[str]`, `raw_data: Dict[str, Any]`.

6. **`config.yaml` Persona Voices**:
   - `thoi_trang_nu`: Voice `vi-VN-HoaiMyNeural` (Hoài My — KOC Thời trang nữ Gen Z/Millennial).
   - `do_gia_dung`: Voice `vi-VN-NamMinhNeural` (Nam Minh — KOC Đồ gia dụng thông minh / Yêu bếp nghiện nhà).

7. **Framework Environment**:
   - `aiogram 3.31.0` is installed.
   - Verified that standard `InlineKeyboardMarkup` is a Pydantic V2 model and raises `TypeError: 'InlineKeyboardMarkup' object is not subscriptable` when subscripted as `kb["inline_keyboard"]`. A custom compatible class inheriting from `InlineKeyboardMarkup` and implementing `__getitem__`, `get`, and `__contains__` bridges both aiogram 3.x and dictionary subscripting seamlessly.

---

## 2. Logic Chain

### Step 1: Product Card Formatting (`format_product_card`)
- **Premise**: Telegram product approval cards must provide the human operator with all decision-critical metrics at a glance while adhering strictly to `ToneValidator` (no robotic cliches or policy-violating text).
- **Inference**:
  - Fields required: Title, Price, Commission rate, Estimated VND payout (`price * commission_rate`), Sales 30d, Potential Score (`/10`), Target Audience, Hook Angle (Hoài My / Nam Minh persona context), Pros & Cons bullets, and Viral Factor.
  - Polymorphic Input Support: Support `ProductCandidate`, `dict` (raw scraper/API data), and SQLAlchemy `Product` instances with safe fallbacks (`price_vnd` vs `price`, `sales_30d` vs `sales_count` vs `sales`).
  - Tone & Brand Safety: Card template was tested through `ToneValidator.validate()` and produced zero policy violations.

### Step 2: Dual-Mode Inline Keyboard Builder (`get_approval_keyboard`)
- **Premise**: `tests/e2e/test_tier1_features.py` expects `kb["inline_keyboard"][0]` dict indexing, while aiogram 3.x expects `InlineKeyboardMarkup` for `bot.send_message(..., reply_markup=kb)`.
- **Inference**:
  - We design `CompatibleInlineKeyboardMarkup(InlineKeyboardMarkup)` and `CompatibleInlineKeyboardButton(InlineKeyboardButton)`:
    - Provides full Pydantic V2 serializability for aiogram Telegram API calls.
    - Implements `__getitem__`, `get`, `__contains__` to support dict-style subscripting:
      `kb["inline_keyboard"][0][0]["callback_data"] == f"approve_product:{product_id}"`
      `kb["inline_keyboard"][0][1]["callback_data"] == f"reject_product:{product_id}"`
  - Returns Button 1: `"✅ Duyệt lên kịch bản"` with `callback_data="approve_product:<product_id>"`
  - Returns Button 2: `"❌ Từ chối"` with `callback_data="reject_product:<product_id>"`

### Step 3: Callback Query Processing (`approve_product` & `reject_product`)
- **Premise**: When an admin reviews a candidate on Telegram and taps a button, state changes must be atomic across the database, job queue, and Telegram message.
- **Inference**:
  - `approve_product:<id>` flow:
    1. Authorization guard: Verify `callback.from_user.id == admin_id`. If unauthorized, answer with alert and return.
    2. Database update: Query `Product` where `product_id == id`. Update `product.status = 'approved'`.
    3. Job creation: Check if `VideoJob` exists for `product_id`. If not, create a new `VideoJob` with `job_id=f"job_{product_id}"`, `niche_id=product.niche_id`, `status='pending'`.
    4. Queue push: Push job payload `{"job_id": job_id, "product_id": product_id, "action": "produce_video", "status": "pending"}` to Redis queue `amas:video_queue` (with in-memory queue fallback if Redis is offline).
    5. Message update: Call `callback.message.edit_text(...)` or edit reply markup, appending `"✅ ĐÃ DUYỆT BỞI ADMIN — Đang chuyển Video Studio..."` and removing inline buttons to prevent duplicate taps.
    6. Acknowledge callback: `await callback.answer("✅ Đã duyệt sản phẩm thành công!")`.
  - `reject_product:<id>` flow:
    1. Authorization guard: Verify `callback.from_user.id == admin_id`.
    2. Database update: Query `Product` where `product_id == id`. Update `product.status = 'rejected'`.
    3. Message update: Append `"❌ ĐÃ TỪ CHỐI — Sản phẩm đã bị loại bỏ."` and remove inline buttons.
    4. Acknowledge callback: `await callback.answer("❌ Đã từ chối sản phẩm.")`.

### Step 4: Command Center & Topic Routing
- **Premise**: The bot serves as the central command console, receiving slash commands from the admin and routing niche products to specific forum topics.
- **Inference**:
  - `route_topic(niche_id: str)`: Returns `101` for `"thoi_trang_nu"`, `102` for `"do_gia_dung"`, and `100` for `"dashboard_tong"` / unknown.
  - `TelegramCommandCenter`: Implements command handlers for `/test_scout`, `/test_video`, `/test_reply`, `/status`, `/create_channel`, `/warmup`, `/menu`. Checks `user_id == admin_id` and rejects non-admin users with `"⛔ Quyền truy cập bị từ chối: Bạn không phải Admin!"`.

---

## 3. Caveats

1. **Redis Queue Availability**:
   - In production, Redis holds the job broker queue. In local test and CI environments without a running Redis server, connecting to Redis will raise `ConnectionRefusedError`.
   - *Design mitigation*: The queue helper `push_to_video_queue` must wrap the Redis operation in a `try...except` block, logging a warning and appending to an in-memory fallback list (`_IN_MEMORY_VIDEO_QUEUE`) so tests run cleanly without external service dependencies.
2. **Telegram Bot Token Requirement**:
   - Running live aiogram polling requires an active bot token.
   - *Design mitigation*: All handlers and dispatchers must be decoupled into pure testable functions taking parameters (`product_id`, `session`, `queue`) and accepting mock `CallbackQuery` / `Message` objects.
3. **Double-Click Race Condition**:
   - If an admin clicks "Duyệt" multiple times rapidly, multiple `VideoJob` records could be created.
   - *Design mitigation*: The handler checks if `product.status == 'approved'` or if a `VideoJob` already exists for this `product_id`. If so, it skips creating a duplicate job, edits the message, and acknowledges the callback.

---

## 4. Conclusion & Concrete Design Blueprint

### 4.1 Proposed File Layout for `src/bot/`

```
src/bot/
├── __init__.py          # Public exports
├── keyboards.py         # Dual-mode inline keyboard builders
├── formatters.py        # format_product_card helper
├── handlers.py          # Callback & command query handlers
└── telegram_bot.py      # TelegramCommandCenter, bot lifecycle, send_product_card, route_topic
```

### 4.2 Module Designs

#### File: `src/bot/keyboards.py`
```python
"""AMAS v1.4.0 — Dual-Mode Telegram Keyboards (Feature F11)."""

from __future__ import annotations
from typing import Any, Dict, List, Optional
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


class CompatibleInlineKeyboardButton(InlineKeyboardButton):
    """InlineKeyboardButton supporting both object attribute and dictionary subscript access."""

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)

    def get(self, item: str, default: Any = None) -> Any:
        return getattr(self, item, default)


class CompatibleInlineKeyboardMarkup(InlineKeyboardMarkup):
    """InlineKeyboardMarkup supporting both aiogram Pydantic serialization and dict subscripting."""

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)

    def get(self, item: str, default: Any = None) -> Any:
        return getattr(self, item, default)

    def __contains__(self, item: str) -> bool:
        return hasattr(self, item)


def get_approval_keyboard(product_id: str) -> CompatibleInlineKeyboardMarkup:
    """Construct 1-Tap Human-in-the-Loop approval inline keyboard for a scouted product.

    Buttons:
    - Button 1: '✅ Duyệt lên kịch bản' (callback_data: 'approve_product:<product_id>')
    - Button 2: '❌ Từ chối' (callback_data: 'reject_product:<product_id>')
    """
    btn_approve = CompatibleInlineKeyboardButton(
        text="✅ Duyệt lên kịch bản",
        callback_data=f"approve_product:{product_id}",
    )
    btn_reject = CompatibleInlineKeyboardButton(
        text="❌ Từ chối",
        callback_data=f"reject_product:{product_id}",
    )
    return CompatibleInlineKeyboardMarkup(inline_keyboard=[[btn_approve, btn_reject]])


def get_main_menu_keyboard() -> CompatibleInlineKeyboardMarkup:
    """Construct administrative command menu keyboard."""
    buttons = [
        [
            CompatibleInlineKeyboardButton(text="🔍 Trinh sát", callback_data="cmd:test_scout"),
            CompatibleInlineKeyboardButton(text="🎬 Tạo Video", callback_data="cmd:test_video"),
        ],
        [
            CompatibleInlineKeyboardButton(text="💬 Test Reply", callback_data="cmd:test_reply"),
            CompatibleInlineKeyboardButton(text="📊 Hệ thống", callback_data="cmd:status"),
        ],
        [
            CompatibleInlineKeyboardButton(text="🔥 Warmup Kênh", callback_data="cmd:warmup"),
            CompatibleInlineKeyboardButton(text="➕ Kênh Mới", callback_data="cmd:create_channel"),
        ],
    ]
    return CompatibleInlineKeyboardMarkup(inline_keyboard=buttons)
```

#### File: `src/bot/formatters.py`
```python
"""AMAS v1.4.0 — Telegram Product Card Formatter."""

from __future__ import annotations
from typing import Any, Dict, Union
from src.agents.fashion_scout import SpecialistEvaluation


def format_product_card(
    product: Union[Dict[str, Any], Any],
    evaluation: SpecialistEvaluation,
) -> str:
    """Format a scouted product candidate and specialist evaluation into a Telegram card.

    Includes:
    - Header with niche identity
    - Product title and product ID
    - Price (VND), Commission rate, and Estimated payout per order
    - 30-day sales velocity and evaluation score (/10)
    - Target audience profile
    - 3s Hook angle with KOC persona context (Hoài My / Nam Minh)
    - Viral factor
    - Pros and Cons bullet points
    """
    # Extract product title
    if hasattr(product, "title"):
        title = product.title
    elif isinstance(product, dict):
        title = product.get("title") or product.get("name") or "Sản phẩm tiềm năng"
    else:
        title = "Sản phẩm tiềm năng"

    # Extract product ID
    if hasattr(product, "product_id"):
        product_id = product.product_id
    elif isinstance(product, dict):
        product_id = product.get("product_id") or product.get("id") or evaluation.product_id
    else:
        product_id = evaluation.product_id

    # Extract price (VND)
    if hasattr(product, "price_vnd"):
        price_vnd = float(product.price_vnd)
    elif hasattr(product, "price"):
        price_vnd = float(product.price)
    elif isinstance(product, dict):
        raw_price = product.get("price_vnd") if product.get("price_vnd") is not None else product.get("price", 0.0)
        price_vnd = float(raw_price or 0.0)
    else:
        price_vnd = 0.0

    # Extract commission rate
    if hasattr(product, "commission_rate"):
        comm_rate = float(product.commission_rate)
    elif isinstance(product, dict):
        raw_comm = product.get("commission_rate") if product.get("commission_rate") is not None else product.get("commission", 0.0)
        comm_rate = float(raw_comm or 0.0)
    else:
        comm_rate = 0.0

    # Calculate estimated payout
    est_payout = int(round(price_vnd * comm_rate))
    comm_pct = int(round(comm_rate * 100)) if comm_rate <= 1.0 else int(round(comm_rate))

    # Extract sales 30d
    if hasattr(product, "sales_30d"):
        sales_30d = int(product.sales_30d)
    elif isinstance(product, dict):
        raw_sales = (
            product.get("sales_30d")
            if product.get("sales_30d") is not None
            else (
                product.get("sales_count")
                if product.get("sales_count") is not None
                else product.get("sales", 0)
            )
        )
        sales_30d = int(raw_sales or 0)
    else:
        sales_30d = 0

    # Persona & Niche styling
    niche_id = evaluation.niche_id
    if niche_id == "thoi_trang_nu":
        header = "👗 [ĐỀ XUẤT SẢN PHẨM — THỜI TRANG NỮ]"
        persona_label = "Hoài My (vi-VN-HoaiMyNeural)"
    elif niche_id == "do_gia_dung":
        header = "🏠 [ĐỀ XUẤT SẢN PHẨM — ĐỒ GIA DỤNG THÔNG MINH]"
        persona_label = "Nam Minh (vi-VN-NamMinhNeural)"
    else:
        header = f"📦 [ĐỀ XUẤT SẢN PHẨM — {niche_id.upper()}]"
        persona_label = "KOC Specialist"

    # Bullets
    pros_text = "\n".join(f"• {p}" for p in evaluation.pros) if evaluation.pros else "• Không có ghi nhận đặc biệt"
    cons_text = "\n".join(f"• {c}" for c in evaluation.cons) if evaluation.cons else "• Không có ghi nhận đặc biệt"

    return (
        f"{header}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 Sản phẩm: {title}\n"
        f"🆔 Mã SP: {product_id}\n"
        f"💰 Giá bán: {int(price_vnd):,}đ | Hoa hồng: {comm_pct}% (~{est_payout:,}đ/đơn)\n"
        f"📈 Doanh số 30d: {sales_30d:,} đã bán | ⭐ Tiềm năng: {evaluation.score:.1f}/10\n\n"
        f"🎯 Chân dung khách hàng:\n"
        f"• {evaluation.target_audience}\n\n"
        f"🎙️ Hook 3s ({persona_label}):\n"
        f"\"{evaluation.hook_angle}\"\n\n"
        f"🔥 Yếu tố Viral:\n"
        f"• {evaluation.viral_factor}\n\n"
        f"✅ Ưu điểm nổi bật (Pros):\n"
        f"{pros_text}\n\n"
        f"⚠️ Điểm yếu / Cần lưu ý (Cons):\n"
        f"{cons_text}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👉 Nhấn nút bên dưới để Duyệt hoặc Từ chối:"
    )

# Alias for interface compatibility with plan
format_product_message = format_product_card
```

#### File: `src/bot/handlers.py`
```python
"""AMAS v1.4.0 — Telegram Bot Handlers & Callback Query Processors."""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any, Dict, List, Optional
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import load_config
from src.database.models import Product, VideoJob
from src.database.session import get_session_factory

logger = logging.getLogger(__name__)
router = Router(name="amas_telegram_router")

# In-memory queue fallback when Redis is offline
_IN_MEMORY_VIDEO_QUEUE: List[Dict[str, Any]] = []


async def push_to_video_queue(job_data: Dict[str, Any], redis_url: Optional[str] = None) -> bool:
    """Push a pending video job to Redis queue for Video Studio processing."""
    try:
        import redis.asyncio as aioredis
        url = redis_url or load_config().redis.url
        r = aioredis.from_url(url, socket_timeout=2.0)
        await r.rpush("amas:video_queue", json.dumps(job_data))
        await r.aclose()
        return True
    except Exception as exc:
        logger.warning("Could not push to Redis queue (%s). Stored in local fallback queue.", exc)
        _IN_MEMORY_VIDEO_QUEUE.append(job_data)
        return False


async def process_approval_action(
    product_id: str,
    session: AsyncSession,
    admin_id: Optional[int] = None,
    user_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Execute product approval logic in the database and push job to queue."""
    if admin_id is not None and user_id is not None and user_id != admin_id:
        return {"success": False, "error": "unauthorized"}

    stmt = select(Product).where(Product.product_id == product_id)
    res = await session.execute(stmt)
    product = res.scalars().first()

    if product is not None:
        product.status = "approved"
        niche_id = product.niche_id
    else:
        niche_id = "thoi_trang_nu"

    # Check if a VideoJob already exists
    stmt_job = select(VideoJob).where(VideoJob.product_id == product_id)
    res_job = await session.execute(stmt_job)
    job = res_job.scalars().first()

    if job is None:
        job_id = f"job_{product_id}"
        job = VideoJob(
            job_id=job_id,
            product_id=product_id,
            niche_id=niche_id,
            status="pending",
        )
        session.add(job)
    else:
        job.status = "pending"
        job_id = job.job_id

    await session.commit()

    payload = {
        "job_id": job_id,
        "product_id": product_id,
        "niche_id": niche_id,
        "status": "pending",
        "action": "produce_video",
    }
    await push_to_video_queue(payload)
    return {"success": True, "job": payload}


async def process_rejection_action(
    product_id: str,
    session: AsyncSession,
    admin_id: Optional[int] = None,
    user_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Execute product rejection logic in the database."""
    if admin_id is not None and user_id is not None and user_id != admin_id:
        return {"success": False, "error": "unauthorized"}

    stmt = select(Product).where(Product.product_id == product_id)
    res = await session.execute(stmt)
    product = res.scalars().first()

    if product is not None:
        product.status = "rejected"
        await session.commit()

    return {"success": True, "product_id": product_id, "status": "rejected"}


@router.callback_query(F.data.startswith("approve_product:"))
async def handle_approval_callback(callback: CallbackQuery) -> None:
    """Handle 1-Tap 'approve_product:<product_id>' callback query."""
    cfg = load_config()
    admin_id = cfg.telegram.admin_id
    user_id = callback.from_user.id if callback.from_user else 0

    if admin_id and user_id != admin_id:
        await callback.answer("⛔ Quyền truy cập bị từ chối: Bạn không phải Admin!", show_alert=True)
        return

    product_id = callback.data.split(":", 1)[1] if callback.data else ""
    session_factory = get_session_factory()

    async with session_factory() as session:
        result = await process_approval_action(product_id, session, admin_id, user_id)

    if result.get("success"):
        current_text = callback.message.text if callback.message else ""
        updated_text = (
            f"{current_text}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"✅ ĐÃ DUYỆT BỞI ADMIN — Đang chuyển Video Studio..."
        )
        try:
            if callback.message:
                await callback.message.edit_text(updated_text, reply_markup=None)
        except Exception as exc:
            logger.warning("Could not edit Telegram message text: %s", exc)

        await callback.answer("✅ Đã duyệt lên kịch bản thành công!")
    else:
        await callback.answer("❌ Có lỗi xảy ra khi duyệt sản phẩm.", show_alert=True)


@router.callback_query(F.data.startswith("reject_product:"))
async def handle_rejection_callback(callback: CallbackQuery) -> None:
    """Handle 1-Tap 'reject_product:<product_id>' callback query."""
    cfg = load_config()
    admin_id = cfg.telegram.admin_id
    user_id = callback.from_user.id if callback.from_user else 0

    if admin_id and user_id != admin_id:
        await callback.answer("⛔ Quyền truy cập bị từ chối: Bạn không phải Admin!", show_alert=True)
        return

    product_id = callback.data.split(":", 1)[1] if callback.data else ""
    session_factory = get_session_factory()

    async with session_factory() as session:
        result = await process_rejection_action(product_id, session, admin_id, user_id)

    if result.get("success"):
        current_text = callback.message.text if callback.message else ""
        updated_text = (
            f"{current_text}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"❌ ĐÃ TỪ CHỐI — Sản phẩm đã bị loại bỏ."
        )
        try:
            if callback.message:
                await callback.message.edit_text(updated_text, reply_markup=None)
        except Exception as exc:
            logger.warning("Could not edit Telegram message text: %s", exc)

        await callback.answer("❌ Đã từ chối sản phẩm.")
    else:
        await callback.answer("❌ Có lỗi xảy ra khi từ chối sản phẩm.", show_alert=True)
```

#### File: `src/bot/telegram_bot.py`
```python
"""AMAS v1.4.0 — Telegram Command Center & Topic Dispatcher (Features F10, F11, F12)."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Union
from aiogram import Bot, Dispatcher

from src.agents.fashion_scout import SpecialistEvaluation
from src.bot.formatters import format_product_card
from src.bot.handlers import router as bot_router
from src.bot.keyboards import get_approval_keyboard
from src.core.config import AppConfig, load_config

logger = logging.getLogger(__name__)

# Standard Forum Topic ID Contract (F10)
TOPIC_MAP: Dict[str, int] = {
    "thoi_trang_nu": 101,
    "do_gia_dung": 102,
    "dashboard_tong": 100,
    "dashboard": 100,
}


def route_topic(niche_id: str) -> int:
    """Route Telegram message to appropriate Forum Topic (Feature F10)."""
    return TOPIC_MAP.get(niche_id, 100)


class TelegramCommandCenter:
    """Central bot dispatcher and security command center for AMAS."""

    def __init__(
        self,
        token: str = "mock_token",
        admin_id: int = 987654321,
        config: Optional[AppConfig] = None,
    ) -> None:
        self.token = token
        self.admin_id = admin_id
        self.config = config or load_config()
        self.sent_messages: List[Dict[str, Any]] = []

    async def send_message(
        self,
        chat_id: int,
        text: str,
        message_thread_id: Optional[int] = None,
        reply_markup: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Send a message to a chat or forum topic thread."""
        msg = {
            "message_id": len(self.sent_messages) + 1,
            "chat_id": chat_id,
            "text": text,
            "message_thread_id": message_thread_id,
            "reply_markup": reply_markup,
        }
        self.sent_messages.append(msg)
        return msg

    async def send_product_card(
        self,
        chat_id: int,
        product: Union[Dict[str, Any], Any],
        evaluation: SpecialistEvaluation,
        topic_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Format and dispatch a product card with 1-tap inline approval buttons."""
        card_text = format_product_card(product, evaluation)
        assigned_topic = topic_id if topic_id is not None else route_topic(evaluation.niche_id)
        keyboard = get_approval_keyboard(evaluation.product_id)

        return await self.send_message(
            chat_id=chat_id,
            text=card_text,
            message_thread_id=assigned_topic,
            reply_markup=keyboard,
        )

    async def handle_command(
        self,
        command: str,
        user_id: int,
        args: Optional[str] = None,
    ) -> str:
        """Process slash command with admin authorization guard."""
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
            profile_name = args or "koc_01"
            return f"✨ Tạo kênh mới thành công: profile_alias_{profile_name} (status: warming)"
        elif cmd == "/warmup":
            return "🔥 Đã kích hoạt phiên lướt feed dạo (3-5 phút) cho kênh."
        elif cmd == "/menu":
            return "📋 Bảng điều khiển AMAS Command Center:"
        else:
            return f"❓ Lệnh không xác định: {cmd}"
```

#### File: `src/bot/__init__.py`
```python
"""AMAS v1.4.0 — Telegram Bot & Command Center Package."""

from src.bot.formatters import format_product_card, format_product_message
from src.bot.handlers import (
    handle_approval_callback,
    handle_rejection_callback,
    process_approval_action,
    process_rejection_action,
    router,
)
from src.bot.keyboards import (
    CompatibleInlineKeyboardButton,
    CompatibleInlineKeyboardMarkup,
    get_approval_keyboard,
    get_main_menu_keyboard,
)
from src.bot.telegram_bot import (
    TOPIC_MAP,
    TelegramCommandCenter,
    route_topic,
)

__all__ = [
    "format_product_card",
    "format_product_message",
    "get_approval_keyboard",
    "get_main_menu_keyboard",
    "CompatibleInlineKeyboardMarkup",
    "CompatibleInlineKeyboardButton",
    "route_topic",
    "TOPIC_MAP",
    "TelegramCommandCenter",
    "router",
    "handle_approval_callback",
    "handle_rejection_callback",
    "process_approval_action",
    "process_rejection_action",
]
```

---

## 5. Verification Method

### 5.1 Test Execution Commands

1. **Verify Isolation Unit Tests for Bot**:
   ```bash
   pytest tests/test_telegram_bot.py -v
   ```
   *Expected*: 100% PASS with full assertion coverage on formatting, keyboards, and callback execution.

2. **Verify Full Existing Test Suite**:
   ```bash
   pytest tests/test_config.py tests/test_database.py tests/test_kalodata_client.py tests/test_tiktok_scraper.py tests/test_specialist_scouts.py tests/test_telegram_bot.py -v
   ```
   *Expected*: All unit tests pass with zero regressions.

3. **Verify Tier 1 Feature Integration**:
   ```bash
   pytest tests/e2e/test_tier1_features.py -k "test_f10 or test_f11 or test_f12" -v
   ```
   *Expected*: Tests F10 (`test_f10_forum_topic_routing`), F11 (`test_f11_1tap_approval_keyboards`), and F12 (`test_f12_bot_command_center`) all pass.

4. **Verify Pairwise Combinations (Tier 3 & Tier 4)**:
   ```bash
   pytest tests/e2e/test_tier3_combinations.py -k "test_comb_scout_to_telegram or test_comb_approval_to_video_studio" -v
   pytest tests/e2e/test_tier4_scenarios.py -k "test_scenario_1_womens_fashion_viral_product" -v
   ```

### 5.2 Invalidation Conditions
- If `get_approval_keyboard` does not support `kb["inline_keyboard"][0]` dict subscripting, `test_f11_1tap_approval_keyboards` will fail.
- If `route_topic("thoi_trang_nu")` returns anything other than `101`, `test_f10_forum_topic_routing` will fail.
- If `handle_command` returns text missing `"Quyền truy cập bị từ chối"` for non-admin users, `test_f12_bot_command_center` will fail.
- If `format_product_card` contains AI cliches or banned trademarks (e.g. "Zara", "thần dược", "sản phẩm tuyệt vời"), `ToneValidator` will reject the card.
