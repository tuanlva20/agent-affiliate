"""AMAS v1.4.0 — Telegram Command Center & 1-Tap Approval Package (Task 4).

Re-exports:
- TelegramCommandCenter: Central bot coordinator and command dispatcher.
- route_topic: Routing helper mapping niche identifiers to Forum Topic thread IDs.
- TOPIC_MAP: Standard mapping contract (101: Fashion, 102: HomeLife, 100: Dashboard).
- MessageDict: Dict subclass with dual subscripting and attribute access.
- get_approval_keyboard: 1-Tap Human-in-the-Loop approval inline keyboard builder.
- get_approval_inline_markup: aiogram-compatible inline keyboard builder.
- get_main_menu_keyboard: Quick-access admin command menu.
- CompatibleInlineKeyboardMarkup: Markup class supporting both aiogram and dict indexing.
- CompatibleInlineKeyboardButton: Button class supporting both attribute and dict indexing.
- format_product_card: Formats candidate product and evaluation into KOC card.
- format_product_message: Alias for format_product_card.
- format_captcha_alert: Emergency Captcha alarm message generator.
- execute_command: Pure function command dispatcher with security guard.
- execute_callback: Pure function callback processor with security guard and DB update.
- push_to_video_queue: Helper pushing pending jobs to Redis or in-memory fallback.
- router: aiogram 3.x Router instance.
- setup_bot_routers: Helper attaching router to TelegramCommandCenter.
- ADMIN_DENIED_MESSAGE: Verbatim security rejection message.
"""

from src.bot.formatters import (
    format_captcha_alert,
    format_product_card,
    format_product_message,
)
from src.bot.handlers import (
    ADMIN_DENIED_MESSAGE,
    _IN_MEMORY_VIDEO_QUEUE,
    execute_callback,
    execute_command,
    push_to_video_queue,
    router,
    setup_bot_routers,
)
from src.bot.keyboards import (
    CompatibleInlineKeyboardButton,
    CompatibleInlineKeyboardMarkup,
    get_approval_inline_markup,
    get_approval_keyboard,
    get_main_menu_keyboard,
)
from src.bot.telegram_bot import (
    TOPIC_MAP,
    MessageDict,
    TelegramCommandCenter,
    route_topic,
)

__all__ = [
    "TelegramCommandCenter",
    "route_topic",
    "TOPIC_MAP",
    "MessageDict",
    "get_approval_keyboard",
    "get_approval_inline_markup",
    "get_main_menu_keyboard",
    "CompatibleInlineKeyboardMarkup",
    "CompatibleInlineKeyboardButton",
    "format_product_card",
    "format_product_message",
    "format_captcha_alert",
    "execute_command",
    "execute_callback",
    "push_to_video_queue",
    "router",
    "setup_bot_routers",
    "ADMIN_DENIED_MESSAGE",
    "_IN_MEMORY_VIDEO_QUEUE",
]
