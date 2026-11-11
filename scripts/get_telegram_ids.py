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
