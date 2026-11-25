import asyncio
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
WEBAPP_URL = os.getenv("WEBAPP_URL", "")

if not TOKEN:
    raise RuntimeError("Заполни TELEGRAM_BOT_TOKEN в .env")
if not WEBAPP_URL.startswith("https://"):
    raise RuntimeError("WEBAPP_URL должен быть публичным HTTPS-адресом")

bot = Bot(TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def start(message: Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Открыть VibeShopping", web_app=WebAppInfo(url=WEBAPP_URL))
    ]])
    await message.answer(
        "Привет! Это VibeShopping 🛍️\n"
        "Нажми кнопку, чтобы открыть приложение и найти аналоги товара по фотографии.",
        reply_markup=keyboard
    )

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
