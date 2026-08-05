# bot.py

import asyncio
import logging
from dotenv import load_dotenv
import os

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
allowed_users_raw = os.getenv("ALLOWED_USERS", "")
ALLOWED_USERS = [
    int(user_id)
    for user_id in allowed_users_raw.split(",")
    if user_id.strip()
]


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)


bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(
        parse_mode=ParseMode.HTML
    )
)

dp = Dispatcher()


# Handlers
@dp.message(CommandStart())
async def start_handler(message: Message):
    await message.answer(
      "🚀 Crypto News Bot started"
    )


# Sender function
async def send_news(ai_result: dict):
    sentiment = {
        "bullish": "📈 Рост",
        "bearish": "📉 Падение",
        "neutral": "⚖️ Нейтральный"
    }

    message = f"""
🚨 <b>{ai_result['source']}</b>

<b>{ai_result['title']}</b>

📃 Содержание: {ai_result['abridged_text']}

📊 Ожидаемое направление: <b>{sentiment[ai_result['sentiment']]}</b>
🔥 Вероятность: <b>{ai_result['score']}/100</b>

🧠 {ai_result['reason']}

<a href="{ai_result['url']}">Source</a>
"""
    for user_id in ALLOWED_USERS:
        try:
            await bot.send_message(
                chat_id=user_id,
                text=message
            )

            await asyncio.sleep(0.5)  # небольшой интервал между отправками
        except Exception as e:
            logging.error(f"Failed to send message to {user_id}: {e}")


async def main():

    logging.info("Bot started")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())