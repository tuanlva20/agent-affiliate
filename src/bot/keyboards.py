"""AMAS v1.4.0 — Telegram Keyboards & Dual-Mode Inline Markup (Feature F11).

Provides:
- CompatibleInlineKeyboardButton: button supporting both attribute and dict subscript access.
- CompatibleInlineKeyboardMarkup: markup supporting both aiogram Pydantic validation and dict subscripting.
- get_approval_keyboard: 1-Tap Human-in-the-Loop approval inline keyboard.
- get_main_menu_keyboard: Quick-access admin command keyboard.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


class CompatibleInlineKeyboardButton(InlineKeyboardButton):
    """InlineKeyboardButton supporting both object attribute and dictionary subscript access."""

    def __getitem__(self, item: str) -> Any:
        try:
            return getattr(self, item)
        except AttributeError:
            raise KeyError(item)

    def get(self, item: str, default: Any = None) -> Any:
        return getattr(self, item, default)


class CompatibleInlineKeyboardMarkup(InlineKeyboardMarkup):
    """InlineKeyboardMarkup supporting both aiogram Pydantic serialization and dict subscripting."""

    def __getitem__(self, item: str) -> Any:
        try:
            return getattr(self, item)
        except AttributeError:
            raise KeyError(item)

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


def get_approval_inline_markup(product_id: str) -> InlineKeyboardMarkup:
    """Return standard aiogram 3.x InlineKeyboardMarkup model."""
    return get_approval_keyboard(product_id)


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
