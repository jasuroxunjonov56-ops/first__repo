
from aiogram import Router, F
from aiogram.types import Message

from config import ADMIN_ID
from database import get_all_orders

router = Router()


@router.message(F.text == "🛡 Admin panel")
async def admin_panel(message: Message):
    # Admin ID sozlanmagan yoki foydalanuvchi admin bo'lmasa
    if ADMIN_ID == 0 or message.from_user.id != ADMIN_ID:
        await message.answer(
            "⛔ Bu bo'lim faqat administrator uchun."
        )
        return

    orders = await get_all_orders()

    if not orders:
        await message.answer(
            "📭 Hozircha buyurtmalar mavjud emas."
        )
        return

    await message.answer(
        f"🛡 UniXizmat admin paneli\n"
        f"📊 Buyurtmalar soni: {len(orders)}"
    )

    for order in orders:
        worker_id = order["worker_id"] or "Biriktirilmagan"

        await message.answer(
            f"📌 Buyurtma #{order['id']}\n"
            f"📝 Tavsif: {order['description']}\n"
            f"💰 Narx: {order['price']:,} so'm\n"
            f"📍 Holati: {order['status']}\n"
            f"🎓 Talaba ID: {order['student_id']}\n"
            f"👷 Ijrochi ID: {worker_id}"
        )
