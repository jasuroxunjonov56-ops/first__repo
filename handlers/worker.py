
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database import get_open_orders, take_order
from services.payments import calculate_payment

router = Router()


@router.message(F.text == "👷 Buyurtmalarni ko'rish")
async def show_orders(message: Message):
    orders = await get_open_orders()

    if not orders:
        await message.answer(
            "📭 Hozircha ochiq buyurtmalar yo'q.\n"
            "Keyinroq yana tekshirib ko'ring."
        )
        return

    for order in orders:
        payment = calculate_payment(order["price"])

        keyboard = InlineKeyboardBuilder()
        keyboard.button(
            text="✅ Buyurtmani olish",
            callback_data=f"take:{order['id']}",
        )

        await message.answer(
            f"📌 Buyurtma #{order['id']}\n"
            f"📝 {order['description']}\n"
            f"💰 Buyurtma narxi: {order['price']:,} so'm\n"
            f"🏢 Platforma komissiyasi (15%): "
            f"{payment['commission']:,} so'm\n"
            f"👷 Ijrochiga qoladigan summa (85%): "
            f"{payment['worker_amount']:,} so'm",
            reply_markup=keyboard.as_markup(),
        )


@router.callback_query(F.data.startswith("take:"))
async def take_order_handler(callback: CallbackQuery):
    order_id = int(callback.data.split(":")[1])

    success = await take_order(
        order_id=order_id,
        worker_id=callback.from_user.id,
    )

    if success:
        await callback.answer("Buyurtma sizga biriktirildi! ✅")
        await callback.message.edit_reply_markup(reply_markup=None)

        await callback.message.answer(
            f"🎉 Siz #{order_id} buyurtmani oldingiz!\n\n"
            "Talaba bilan topshirish muddatini kelishib oling."
        )
    else:
        await callback.answer(
            "Bu buyurtmani boshqa ijrochi olgan yoki u yopilgan.",
            show_alert=True,
        )

