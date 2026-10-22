
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database import get_open_orders, take_order, is_worker_active, get_order_details
from services.payments import calculate_payment

router = Router()


def format_som(value):
    return f"{int(value):,}".replace(",", " ") + " so‘m"


@router.message(F.text == "👷 Buyurtmalarni ko'rish")
async def show_orders(message: Message):
    orders = await get_open_orders()

    if not orders:
        await message.answer(
            "📭 Hozircha ochiq buyurtmalar yo'q.\n"
            "Keyinroq yana tekshirib ko'ring."
        )
        return

    if not await is_worker_active(message.from_user.id):
        await message.answer(
            "🔒 Buyurtma olish uchun avval bajaruvchi sifatida "
            "ro‘yxatdan o‘ting.\n\n"
            "💳 «Bajaruvchi bo‘lish» tugmasini bosing yoki /pay yozing. "
            "Admin to‘lovingizni tasdiqlagach, buyurtma olishingiz mumkin."
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
            f"💰 Buyurtma narxi: {format_som(order['price'])}\n"
            f"🏢 Platforma komissiyasi: {format_som(payment['commission'])}\n"
            f"👷 Ijrochiga qoladigan summa: "
            f"{format_som(payment['worker_amount'])}",
            reply_markup=keyboard.as_markup(),
        )


@router.callback_query(F.data.startswith("take:"))
async def take_order_handler(callback: CallbackQuery):
    if not await is_worker_active(callback.from_user.id):
        await callback.answer(
            "Avval bajaruvchi sifatida ro‘yxatdan o‘ting va "
            "to‘lov tasdiqlanishini kuting.",
            show_alert=True,
        )
        return

    order_id = int(callback.data.split(":")[1])

    success = await take_order(
        order_id=order_id,
        worker_id=callback.from_user.id,
    )

    if success:
        await callback.answer("Buyurtma sizga biriktirildi! ✅")
        await callback.message.edit_reply_markup(reply_markup=None)

        order = await get_order_details(order_id)
        contact = (order or {}).get("contact")
        contact_text = f"\n\n📞 Buyurtma beruvchi bilan aloqa: {contact}" if contact else ""
        await callback.message.answer(
            f"🎉 Siz #{order_id} buyurtmani oldingiz!\n\n"
            "Topshirish muddatini buyurtma beruvchi bilan kelishib oling."
            f"{contact_text}"
        )
    else:
        await callback.answer(
            "Bu buyurtmani boshqa ijrochi olgan yoki u yopilgan.",
            show_alert=True,
        )
