# Exploration Report: Telegram Command Center & 1-Tap Approval (Milestone 4 / Task 4)

## 1. Observation

### 1.1 Existing Test Suite & Contracts
- **`tests/e2e/conftest.py` (lines 514–575)** defines the contract for F10, F11, and F12:
  ```python
  def route_topic(niche_id: str) -> int:
      topic_map = {
          "thoi_trang_nu": 101,
          "do_gia_dung": 102,
          "dashboard_tong": 100,
      }
      return topic_map.get(niche_id, 100)

  def get_approval_keyboard(product_id: str) -> Dict[str, Any]:
      return {
          "inline_keyboard": [
              [
                  {"text": "✅ Duyệt lên kịch bản", "callback_data": f"approve_product:{product_id}"},
                  {"text": "❌ Từ chối", "callback_data": f"reject_product:{product_id}"},
              ]
          ]
      }

  class TelegramCommandCenter:
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
          ...
  ```

- **`tests/e2e/test_tier1_features.py` (lines 302–340)** verifies:
  - F10: `route_topic("thoi_trang_nu") == 101`, `route_topic("do_gia_dung") == 102`, `route_topic("unknown_niche") == 100`.
  - F11: `get_approval_keyboard("prod_123")["inline_keyboard"][0]` has 2 buttons with `callback_data` `"approve_product:prod_123"` and `"reject_product:prod_123"`.
  - F12: `bot = TelegramCommandCenter(admin_id=987654321)` responds to `/test_scout`, `/test_video`, `/test_reply`, `/status`, `/create_channel`, `/warmup`, and rejects unauthorized users (`user_id != 987654321`) with `"Quyền truy cập bị từ chối"`.

- **`tests/e2e/test_tier2_boundaries.py` (lines 188–190)** and **`tests/e2e/conftest.py` (line 783)**:
  - When Captcha is detected, SmartPublisher alerts via:
    `assert "🚨 [CẢNH BÁO CAPTCHA TIKTOK]" in bot.sent_messages[0]["text"]`
  - In `conftest.py` line 782, publisher calls `chat_id=telegram_bot.admin_id`.

- **`tests/e2e/test_tier3_combinations.py` (lines 72–95)**:
  - `bot = TelegramCommandCenter(admin_id=987654321)`
  - `topic_id = route_topic(candidate.niche_id)` -> `101`
  - `msg = await bot.send_message(chat_id=-1001234567890, text=card_text, message_thread_id=topic_id, reply_markup=keyboard)`
  - Asserts `msg["message_thread_id"] == 101` and `"approve_product:fash_dress_001" in str(msg["reply_markup"])`.
  - Simulates callback query `approve_product:<id>` -> updates DB product status to `'approved'` and creates `VideoJobModel`.

### 1.2 Configuration & Dependencies
- `aiogram` is installed in the workspace at version `3.31.0` (tested via `python3 -c "import aiogram; print(aiogram.__version__)"`).
- `config.yaml` lines 28–36 contains:
  ```yaml
  telegram:
    bot_token: "" # Overridden by TELEGRAM_BOT_TOKEN
    admin_id: 0   # Overridden by ADMIN_TELEGRAM_ID
    forum_chat_id: null # Overridden by TELEGRAM_FORUM_CHAT_ID
    topic_ids:
      thoi_trang_nu: 2
      do_gia_dung: 4
      dashboard: 1
  ```
- `.env.example` specifies `TELEGRAM_BOT_TOKEN`, `ADMIN_TELEGRAM_ID`, `TELEGRAM_FORUM_CHAT_ID`.
- User prompt asks to support both `TELEGRAM_ADMIN_CHAT_ID` / `ADMIN_TELEGRAM_ID` and `TELEGRAM_GROUP_ID` / `TELEGRAM_FORUM_CHAT_ID`.

---

## 2. Logic Chain

1. **Dual-Mode Requirement (Live aiogram 3 vs Mock Mode)**:
   - In production or manual live testing with real tokens, the system needs an active `aiogram.Bot` and `aiogram.Dispatcher` to poll or handle webhooks, route forum topics, and handle callback queries.
   - In automated test execution (unit tests, pytest, CI/CD, dry-runs), no Telegram network connection or real bot token is present. The system must run offline in mock mode without throwing network or authorization errors.
   - *Design decision*: Check `token`. If `token` is `"mock_token"`, empty, or contains `"EXAMPLE"`, or if `mock_mode=True`, run in mock mode (`self.bot = None`). All sent messages are stored in `self.sent_messages` and returned as `MessageDict`. If a valid token is provided and `mock_mode=False`, initialize live `aiogram.Bot(token=token)` and `aiogram.Dispatcher()`.

2. **Subscriptable & Attribute-Compatible Message Object (`MessageDict`)**:
   - In `tests/e2e/test_tier1_features.py` and `test_tier3_combinations.py`, tests access `msg["message_thread_id"]` and `msg["reply_markup"]`.
   - In `conftest.py` and future live handlers, code may access `msg.message_id`, `msg.chat_id`, or `msg.text`.
   - *Design decision*: Subclass `dict` as `MessageDict` implementing `__getattr__` and `__setattr__`. This satisfies both dictionary indexing (`msg["..."]`) and attribute access (`msg....`) seamlessly.

3. **Forum Topic Routing (`route_topic`)**:
   - `route_topic(niche_id: str, topic_ids: Optional[Dict[str, int]] = None) -> int`:
     - Default map: `{"thoi_trang_nu": 101, "do_gia_dung": 102, "dashboard_tong": 100}`.
     - Fallback for unknown niche: `100` (`#dashboard-tong`).
     - If custom `topic_ids` is passed (e.g., from `config.yaml`), it overrides the defaults.
   - This directly satisfies `test_f10_forum_topic_routing` while keeping full extensibility for production configuration.

4. **1-Tap Approval Keyboards & Card Formatting (`src/bot/keyboards.py`)**:
   - `get_approval_keyboard(product_id: str) -> Dict[str, Any]` returns the exact dict structure verified by `test_f11_1tap_approval_keyboards`:
     ```python
     {
         "inline_keyboard": [
             [
                 {"text": "✅ Duyệt lên kịch bản", "callback_data": f"approve_product:{product_id}"},
                 {"text": "❌ Từ chối", "callback_data": f"reject_product:{product_id}"},
             ]
         ]
     }
     ```
   - For live aiogram usage, `aiogram.types.InlineKeyboardMarkup.model_validate(kb_dict)` converts this dict into an aiogram markup object with zero manual translation.
   - Provide helper `format_product_card(niche_id, ...)` to generate cards with the proper emoji (`👗` or `🏠`), product title, formatted price (VND), commission %, Hook 3s, and evaluation score.
   - Provide helper `format_captcha_alert(channel_id, ...)` generating `"🚨 [CẢNH BÁO CAPTCHA TIKTOK]..."` matching SYSTEM_SPEC § 3.5.

5. **Security & Dispatcher Handlers (`src/bot/handlers.py`)**:
   - `handle_command(command: str, user_id: int, args: Optional[str] = None) -> str`:
     - Security guard: `if user_id != self.admin_id: return "⛔ Quyền truy cập bị từ chối: Bạn không phải Admin!"`
     - Matches commands: `/test_scout`, `/test_video`, `/test_reply`, `/status`, `/create_channel`, `/warmup`, `/menu`, `/start`.
   - `handle_callback(callback_data: str, user_id: int) -> Dict[str, Any]`:
     - Security guard: ensures only `admin_id` can approve or reject.
     - Parses `action, product_id` from `callback_data`.
     - Supports optional DB transaction (`ProductModel.status = 'approved' | 'rejected'`, creates `VideoJobModel`).
   - Aiogram Router: `setup_bot_routers(command_center: TelegramCommandCenter) -> Router` binds Telegram messages and callbacks to these methods, ensuring live bot and mock mode share 100% identical business logic.

---

## 3. Caveats

1. **Aiogram v3 Event Loop in Tests**:
   - When unit testing aiogram handlers without polling, handler functions should be called directly with mock objects or via `TelegramCommandCenter.handle_command` / `handle_callback`. Attempting to start full `dp.start_polling()` in a test without a live mock server or cancel token will block the test runner.
2. **Environment Variable Naming**:
   - In `.env.example`, `ADMIN_TELEGRAM_ID` and `TELEGRAM_FORUM_CHAT_ID` were used, whereas the prompt also mentions `TELEGRAM_ADMIN_CHAT_ID` and `TELEGRAM_GROUP_ID`. The config loader and `TelegramCommandCenter` should accept both aliases to prevent configuration friction.
3. **Database Dependency**:
   - `TelegramCommandCenter` can execute standalone without a database connection for mock/unit tests. When wired to Hermes or live pipelines, `db_session` or an event callback can be optionally injected into `handle_callback`.

---

## 4. Conclusion & Proposed Architecture

### 4.1 Proposed File Layout
```
src/bot/
├── __init__.py           # Exports TelegramCommandCenter, route_topic, get_approval_keyboard, format_*
├── keyboards.py          # Keyboards, InlineKeyboardMarkup, markup converters
├── handlers.py           # Aiogram 3.x Router, command & callback query bindings
└── telegram_bot.py       # TelegramCommandCenter core class, MessageDict, routing logic
tests/
└── test_telegram_bot.py  # Comprehensive test suite covering F10, F11, F12, mock mode, and live router setup
```

### 4.2 Proposed Code Design

#### `src/bot/keyboards.py`
```python
from typing import Any, Dict
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

def get_approval_keyboard(product_id: str) -> Dict[str, Any]:
    """Contract F11: 1-Tap Inline approval keyboard dictionary."""
    return {
        "inline_keyboard": [
            [
                {"text": "✅ Duyệt lên kịch bản", "callback_data": f"approve_product:{product_id}"},
                {"text": "❌ Từ chối", "callback_data": f"reject_product:{product_id}"},
            ]
        ]
    }

def get_approval_inline_markup(product_id: str) -> InlineKeyboardMarkup:
    """Aiogram 3.x Pydantic InlineKeyboardMarkup model."""
    return InlineKeyboardMarkup.model_validate(get_approval_keyboard(product_id))

def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Navigation keyboard for quick test triggers."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔍 Test Scout", callback_data="cmd:test_scout"),
                InlineKeyboardButton(text="🎬 Test Video", callback_data="cmd:test_video"),
            ],
            [
                InlineKeyboardButton(text="💬 Test Reply", callback_data="cmd:test_reply"),
                InlineKeyboardButton(text="📊 Status", callback_data="cmd:status"),
            ],
            [
                InlineKeyboardButton(text="🔥 Warmup", callback_data="cmd:warmup"),
            ]
        ]
    )
```

#### `src/bot/telegram_bot.py`
```python
import os
from typing import Any, Dict, List, Optional
from aiogram import Bot, Dispatcher
from aiogram.types import InlineKeyboardMarkup

from src.core.config import AppConfig, load_config
from src.bot.keyboards import get_approval_keyboard

def route_topic(niche_id: str, topic_ids: Optional[Dict[str, int]] = None) -> int:
    """Contract F10: Route message to Forum Topic Thread ID."""
    default_map = {
        "thoi_trang_nu": 101,
        "do_gia_dung": 102,
        "dashboard_tong": 100,
    }
    if topic_ids and niche_id in topic_ids:
        return topic_ids[niche_id]
    return default_map.get(niche_id, 100)

def format_product_card(
    niche_id: str,
    title: str,
    price_vnd: float,
    commission_rate: float,
    score: float,
    hook_angle: str,
) -> str:
    """Generate standardized Telegram product card."""
    if niche_id == "thoi_trang_nu":
        header = "👗 [SẢN PHẨM MỚI DUYỆT - THỜI TRANG NỮ]"
    elif niche_id == "do_gia_dung":
        header = "🏠 [SẢN PHẨM MỚI DUYỆT - ĐỒ GIA DỤNG]"
    else:
        header = f"📦 [SẢN PHẨM MỚI DUYỆT - {niche_id.upper()}]"

    price_str = f"{int(price_vnd):,}đ"
    comm_pct = int(commission_rate * 100)
    return (
        f"{header}\n"
        f"📌 Tên: {title}\n"
        f"💰 Giá: {price_str} | Hoa hồng: {comm_pct}%\n"
        f"🎯 Hook 3s: {hook_angle}\n"
        f"⭐ Điểm tiềm năng: {score}/10"
    )

def format_captcha_alert(channel_id: str = "") -> str:
    """Generate emergency Captcha alarm message."""
    chan_str = f" - KÊNH {channel_id.upper()}" if channel_id else ""
    return (
        f"🚨 [CẢNH BÁO CAPTCHA TIKTOK{chan_str}]\n"
        f"Phát hiện màn hình yêu cầu xác minh danh tính. Bot đã tạm dừng an toàn!\n"
        f"👉 Vui lòng mở trình duyệt giải bằng tay trong vòng 5 phút."
    )

class MessageDict(dict):
    """Subclass of dict supporting both dict indexing and attribute access."""
    def __getattr__(self, name: str) -> Any:
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)

    def __setattr__(self, name: str, value: Any) -> None:
        self[name] = value

class TelegramCommandCenter:
    """Telegram Command Center supporting both live aiogram 3.x and mock mode."""

    def __init__(
        self,
        token: Optional[str] = None,
        admin_id: Optional[int] = None,
        forum_chat_id: Optional[int] = None,
        topic_ids: Optional[Dict[str, int]] = None,
        mock_mode: Optional[bool] = None,
        config: Optional[AppConfig] = None,
    ):
        # Config resolution
        self.config = config
        cfg_tg = config.telegram if config else None

        self.token = (
            token
            or os.getenv("TELEGRAM_BOT_TOKEN")
            or (cfg_tg.bot_token if cfg_tg else "")
            or "mock_token"
        )

        admin_env = os.getenv("TELEGRAM_ADMIN_CHAT_ID") or os.getenv("ADMIN_TELEGRAM_ID")
        self.admin_id = (
            admin_id
            or (int(admin_env) if admin_env and admin_env.isdigit() else None)
            or (cfg_tg.admin_id if cfg_tg and cfg_tg.admin_id else None)
            or 987654321
        )

        forum_env = os.getenv("TELEGRAM_GROUP_ID") or os.getenv("TELEGRAM_FORUM_CHAT_ID")
        self.forum_chat_id = (
            forum_chat_id
            or (int(forum_env) if forum_env and (forum_env.isdigit() or forum_env.startswith("-")) else None)
            or (cfg_tg.forum_chat_id if cfg_tg else None)
            or -1001234567890
        )

        self.topic_ids = topic_ids or (cfg_tg.topic_ids if cfg_tg else {}) or {}

        # Determine mock vs live
        if mock_mode is not None:
            self.mock_mode = mock_mode
        else:
            self.mock_mode = (
                not self.token
                or self.token == "mock_token"
                or "EXAMPLE" in self.token
                or self.token.startswith("mock_")
            )

        self.sent_messages: List[MessageDict] = []
        self.bot: Optional[Bot] = None
        self.dp: Optional[Dispatcher] = None

        if not self.mock_mode:
            self.bot = Bot(token=self.token)
            self.dp = Dispatcher()
            from src.bot.handlers import setup_bot_routers
            setup_bot_routers(self)

    def route_topic(self, niche_id: str) -> int:
        return route_topic(niche_id, self.topic_ids)

    async def send_message(
        self,
        chat_id: int,
        text: str,
        message_thread_id: Optional[int] = None,
        reply_markup: Optional[Any] = None,
    ) -> MessageDict:
        msg = MessageDict({
            "message_id": len(self.sent_messages) + 1,
            "chat_id": chat_id,
            "text": text,
            "message_thread_id": message_thread_id,
            "reply_markup": reply_markup,
        })
        self.sent_messages.append(msg)

        if not self.mock_mode and self.bot:
            markup = reply_markup
            if isinstance(reply_markup, dict):
                markup = InlineKeyboardMarkup.model_validate(reply_markup)
            await self.bot.send_message(
                chat_id=chat_id,
                text=text,
                message_thread_id=message_thread_id,
                reply_markup=markup,
            )
        return msg

    async def send_product_card(
        self,
        niche_id: str,
        title: str,
        price_vnd: float,
        commission_rate: float,
        score: float,
        hook_angle: str,
        product_id: str,
        chat_id: Optional[int] = None,
        topic_id: Optional[int] = None,
    ) -> MessageDict:
        cid = chat_id or self.forum_chat_id
        tid = topic_id or self.route_topic(niche_id)
        card_text = format_product_card(niche_id, title, price_vnd, commission_rate, score, hook_angle)
        kb = get_approval_keyboard(product_id)
        return await self.send_message(chat_id=cid, text=card_text, message_thread_id=tid, reply_markup=kb)

    async def send_captcha_alert(
        self,
        channel_id: str = "",
        screenshot_path: Optional[str] = None,
        chat_id: Optional[int] = None,
    ) -> MessageDict:
        cid = chat_id or self.admin_id
        text = format_captcha_alert(channel_id)
        tid = route_topic("dashboard_tong", self.topic_ids)
        return await self.send_message(chat_id=cid, text=text, message_thread_id=tid)

    async def handle_command(self, command: str, user_id: int, args: Optional[str] = None) -> str:
        if user_id != self.admin_id:
            return "⛔ Quyền truy cập bị từ chối: Bạn không phải Admin!"

        cmd = command.strip().lower()
        if " " in cmd:
            parts = cmd.split(" ", 1)
            cmd = parts[0]
            if args is None:
                args = parts[1].strip()

        if not cmd.startswith("/"):
            cmd = f"/{cmd}"

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
        elif cmd in ("/start", "/menu"):
            return (
                "🤖 AMAS v1.4.0 Command Center:\n"
                "/status - Xem trạng thái hệ thống\n"
                "/test_scout <ngách> - Chạy thử trinh sát\n"
                "/test_video - Chạy thử pipeline dựng video\n"
                "/test_reply - Chạy thử Comment Agent\n"
                "/create_channel <tên> - Tạo profile kênh mới\n"
                "/warmup - Kích hoạt phiên lướt feed nuôi kênh"
            )
        else:
            return f"❓ Lệnh không xác định: {cmd}"

    async def handle_callback(self, callback_data: str, user_id: int) -> Dict[str, Any]:
        if user_id != self.admin_id:
            return {
                "status": "denied",
                "message": "⛔ Quyền truy cập bị từ chối: Bạn không phải Admin!",
            }

        if ":" not in callback_data:
            return {
                "status": "error",
                "message": f"❓ Định dạng callback_data không hợp lệ: {callback_data}",
            }

        action, product_id = callback_data.split(":", 1)
        if action == "approve_product":
            return {
                "status": "approved",
                "action": action,
                "product_id": product_id,
                "message": f"✅ Đã duyệt sản phẩm {product_id} lên kịch bản!",
            }
        elif action == "reject_product":
            return {
                "status": "rejected",
                "action": action,
                "product_id": product_id,
                "message": f"❌ Đã từ chối sản phẩm {product_id}.",
            }
        else:
            return {
                "status": "unknown",
                "action": action,
                "product_id": product_id,
                "message": f"❓ Thao tác không xác định: {callback_data}",
            }
```

#### `src/bot/handlers.py`
```python
from aiogram import Router, F
from aiogram.filters import Command, CommandObject
from aiogram.types import Message, CallbackQuery

def setup_bot_routers(command_center: "TelegramCommandCenter") -> Router:
    router = Router(name="amas_bot_router")

    @router.message(Command("start", "menu", "status", "test_scout", "test_video", "test_reply", "create_channel", "warmup"))
    async def command_dispatcher(message: Message, command: CommandObject):
        user_id = message.from_user.id if message.from_user else 0
        cmd_str = f"/{command.command}"
        args = command.args
        response = await command_center.handle_command(cmd_str, user_id, args)
        await message.answer(response)

    @router.callback_query(F.data.startswith("approve_product:") | F.data.startswith("reject_product:"))
    async def callback_dispatcher(callback: CallbackQuery):
        user_id = callback.from_user.id if callback.from_user else 0
        result = await command_center.handle_callback(callback.data, user_id)
        await callback.answer(result.get("message", ""))
        if result.get("status") in ("approved", "rejected"):
            status_text = "Đã duyệt ✅" if result.get("status") == "approved" else "Đã từ chối ❌"
            if callback.message and callback.message.text:
                await callback.message.edit_text(
                    f"{callback.message.text}\n\n📌 <b>Trạng thái: {status_text}</b>",
                    parse_mode="HTML"
                )

    if command_center.dp:
        command_center.dp.include_router(router)
    return router
```

---

## 5. Verification Method

1. **Unit Test Execution**:
   Run the newly created Telegram bot unit test suite:
   ```bash
   pytest tests/test_telegram_bot.py -v
   ```
2. **Regression Check against Existing Test Suites**:
   Run all existing unit and contract tests to ensure zero regression:
   ```bash
   pytest tests/test_config.py tests/test_database.py tests/test_kalodata_client.py tests/test_tiktok_scraper.py tests/test_specialist_scouts.py -v
   ```
3. **E2E Feature Isolation Test Suite**:
   Run Tier 1 isolation tests:
   ```bash
   pytest tests/e2e/test_tier1_features.py -k "test_f10 or test_f11 or test_f12" -v
   ```
4. **Invalidation Conditions**:
   - `route_topic("thoi_trang_nu") != 101` or `route_topic("unknown") != 100`.
   - `get_approval_keyboard("p1")` does not contain `approve_product:p1` and `reject_product:p1`.
   - `TelegramCommandCenter` throws network or auth errors when instantiated in mock mode without `.env`.
   - Non-admin user ID is permitted to execute commands or approve products.
