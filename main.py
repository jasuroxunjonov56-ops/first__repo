
import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart, CommandObject
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

from database import init_db, link_worker_account
from handlers import student, worker, admin, payment


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
    dp.include_router(payment.router)

    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📝 Buyurtma berish")],
            [KeyboardButton(text="👷 Buyurtmalarni ko'rish")],
            [KeyboardButton(text="💳 Bajaruvchi bo‘lish")],
            [KeyboardButton(text="🛡 Admin panel")],
        ],
        resize_keyboard=True,
    )

    @dp.message(CommandStart())
    async def start(message: Message, command: CommandObject):
        args = command.args or ""
        if args.startswith("link_"):
            link_token = args[5:]
            linked = await link_worker_account(link_token, message.from_user.id)
            if not linked:
                await message.answer(
                    "⚠️ Ro‘yxatdan o‘tish havolasi topilmadi yoki eskirgan. "
                    "Saytga qaytib, qaytadan ro‘yxatdan o‘ting.",
                    reply_markup=keyboard,
                )
                return
            await message.answer(
                "🔗 Saytdagi login akkauntingiz Telegram bilan bog‘landi!\n\n"
                "🔐 Sayt va botda bitta login/parol bilan foydalanasiz.\n"
                "💳 Bajaruvchi akkauntini faollashtirish uchun bir martalik "
                "to‘lovni amalga oshiring. To‘lovni «Bajaruvchi bo‘lish» tugmasidan boshlang.",
                reply_markup=keyboard,
            )
            return

        await message.answer(
            "🎓 UniXizmat botiga xush kelibsiz!\n\n"
            "Saytdagi login akkauntingizni Telegram bilan bog‘lang yoki "
            "buyurtmalarni ko‘rish uchun menyudan foydalaning.\n"
            "Buyurtma olish uchun «💳 Bajaruvchi bo‘lish» tugmasini bosing.",
            reply_markup=keyboard,
        )

    await init_db()
    print("UniXizmat ishga tushdi!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
