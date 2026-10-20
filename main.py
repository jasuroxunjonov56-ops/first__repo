
import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

from database import init_db
from handlers import student, worker, admin


async def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise ValueError("BOT_TOKEN sozlanmagan!")

    logging.basicConfig(level=logging.INFO)

    bot = Bot(token=token)
    dp = Dispatcher()

    dp.include_router(student.router)
    dp.include_router(worker.router)
    dp.include_router(admin.router)

    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📝 Buyurtma berish")],
            [KeyboardButton(text="👷 Buyurtmalarni ko'rish")],
            [KeyboardButton(text="🛡 Admin panel")],
        ],
        resize_keyboard=True,
    )

    @dp.message(CommandStart())
    async def start(message: Message):
        await message.answer(
            "🎓 UniXizmat botiga xush kelibsiz!",
            reply_markup=keyboard,
        )

    await init_db()
    print("UniXizmat ishga tushdi!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
