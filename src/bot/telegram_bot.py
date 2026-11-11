"""AMAS v1.4.0 — Telegram Command Center & Topic Dispatcher (Features F10, F11, F12).

Provides:
- TOPIC_MAP: Standard mapping of niches to Forum Topic thread IDs.
- route_topic: Routing helper with fallback to #dashboard-tong (100).
- MessageDict: Dict subclass supporting both indexing and attribute access.
- TelegramCommandCenter: Unified coordinator for mock offline tests and live aiogram 3.x bot.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional, Union

from aiogram import Bot, Dispatcher
from aiogram.types import InlineKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.fashion_scout import SpecialistEvaluation
from src.bot.formatters import format_captcha_alert, format_product_card
from src.bot.handlers import execute_callback, execute_command, setup_bot_routers
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


def route_topic(niche_id: Optional[str], topic_ids: Optional[Dict[str, int]] = None) -> int:
    """Route Telegram message to appropriate Forum Topic (Feature F10)."""
    if topic_ids and niche_id and niche_id in topic_ids:
        return topic_ids[niche_id]
    if not niche_id:
        return 100
    return TOPIC_MAP.get(niche_id, 100)


class MessageDict(dict):
    """Subclass of dict supporting both dict indexing and attribute access."""

    def __getattr__(self, name: str) -> Any:
        try:
            return self[name]
        except KeyError:
            raise AttributeError(f"'MessageDict' object has no attribute '{name}'")

    def __setattr__(self, name: str, value: Any) -> None:
        self[name] = value


class TelegramCommandCenter:
    """Central bot dispatcher and security command center for AMAS."""

    def __init__(
        self,
        token: Optional[str] = None,
        admin_id: Optional[Union[int, str]] = None,
        forum_chat_id: Optional[Union[int, str]] = None,
        topic_ids: Optional[Dict[str, int]] = None,
        mock_mode: Optional[bool] = None,
        config: Optional[AppConfig] = None,
    ) -> None:
        self.config = config
        cfg_tg = config.telegram if config else None

        self.token = (
            token
            or os.getenv("TELEGRAM_BOT_TOKEN")
            or (cfg_tg.bot_token if cfg_tg else "")
            or "mock_token"
        )

        admin_env = os.getenv("TELEGRAM_ADMIN_CHAT_ID") or os.getenv("ADMIN_TELEGRAM_ID")
        raw_admin = (
            admin_id
            if admin_id is not None
            else (admin_env if admin_env else None)
            or (cfg_tg.admin_id if cfg_tg and cfg_tg.admin_id else None)
            or 987654321
        )
        try:
            self.admin_id: int = int(raw_admin)
        except (ValueError, TypeError):
            self.admin_id = 987654321

        forum_env = os.getenv("TELEGRAM_GROUP_ID") or os.getenv("TELEGRAM_FORUM_CHAT_ID")
        raw_forum = (
            forum_chat_id
            if forum_chat_id is not None
            else (forum_env if forum_env else None)
            or (cfg_tg.forum_chat_id if cfg_tg and cfg_tg.forum_chat_id else None)
            or -1001234567890
        )
        try:
            self.forum_chat_id: int = int(raw_forum)
        except (ValueError, TypeError):
            self.forum_chat_id = -1001234567890

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
            try:
                self.bot = Bot(token=self.token)
                self.dp = Dispatcher()
                setup_bot_routers(self)
            except Exception as e:
                logger.warning("Could not initialize live aiogram Bot (%s); running in mock mode.", e)
                self.mock_mode = True
                self.bot = None
                self.dp = None

    def route_topic(self, niche_id: Optional[str]) -> int:
        """Route niche identifier to topic thread id."""
        return route_topic(niche_id, self.topic_ids)

    async def send_message(
        self,
        chat_id: int,
        text: str,
        message_thread_id: Optional[int] = None,
        reply_markup: Optional[Any] = None,
    ) -> MessageDict:
        """Send a message to a chat or forum topic thread."""
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
            try:
                await self.bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    message_thread_id=message_thread_id,
                    reply_markup=markup,
                )
            except Exception as e:
                logger.warning("Failed to send live Telegram message: %s", e)
        return msg

    async def send_product_card(
        self,
        chat_id: Optional[int] = None,
        product: Optional[Union[Dict[str, Any], Any]] = None,
        evaluation: Optional[SpecialistEvaluation] = None,
        niche_id: Optional[str] = None,
        topic_id: Optional[int] = None,
        **kwargs: Any,
    ) -> MessageDict:
        """Format and dispatch a product card with 1-tap inline approval buttons."""
        target_chat = chat_id or self.forum_chat_id
        determined_niche = (
            niche_id
            or (evaluation.niche_id if evaluation else None)
            or (getattr(product, "niche_id", None) if product else None)
            or (product.get("niche_id") if isinstance(product, dict) else None)
            or "thoi_trang_nu"
        )
        target_topic = topic_id if topic_id is not None else self.route_topic(determined_niche)

        card_text = format_product_card(
            product=product or determined_niche,
            evaluation=evaluation,
            **kwargs,
        )

        prod_id = (
            (evaluation.product_id if evaluation else None)
            or (getattr(product, "product_id", None) if product else None)
            or (product.get("product_id") if isinstance(product, dict) else None)
            or "prod_unknown"
        )
        keyboard = get_approval_keyboard(prod_id)

        return await self.send_message(
            chat_id=target_chat,
            text=card_text,
            message_thread_id=target_topic,
            reply_markup=keyboard,
        )

    async def send_captcha_alert(
        self,
        channel_id: str = "",
        screenshot_path: Optional[str] = None,
        chat_id: Optional[int] = None,
    ) -> MessageDict:
        """Send emergency Captcha alarm message."""
        target_chat = chat_id or self.admin_id
        text = format_captcha_alert(channel_id=channel_id, screenshot_path=screenshot_path)
        tid = self.route_topic("dashboard_tong")
        return await self.send_message(
            chat_id=target_chat,
            text=text,
            message_thread_id=tid,
        )

    async def handle_command(
        self,
        command: str,
        user_id: Union[int, str],
        args: Optional[str] = None,
        session: Optional[AsyncSession] = None,
    ) -> str:
        """Process slash command with admin authorization guard."""
        clean_cmd = (command or "").strip()
        if "@" in clean_cmd:
            parts = clean_cmd.split(maxsplit=1)
            cmd_part = parts[0].split("@")[0]
            clean_cmd = cmd_part + (" " + parts[1] if len(parts) > 1 else "")

        return await execute_command(
            command=clean_cmd,
            user_id=user_id,
            admin_id=self.admin_id,
            args=args,
            session=session,
        )

    async def handle_callback(
        self,
        callback_data: str,
        user_id: Union[int, str],
        session: Optional[AsyncSession] = None,
    ) -> Dict[str, Any]:
        """Process inline callback query with admin authorization guard."""
        return await execute_callback(
            callback_data=callback_data,
            user_id=user_id,
            admin_id=self.admin_id,
            session=session,
        )
