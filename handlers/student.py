
from aiogram import Router, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from database import add_order

router = Router()


class OrderForm(StatesGroup):
    description = State()
    price = State()


@router.message(F.text == "📝 Buyurtma berish")
async def start_order(message: Message, state: FSMContext):
    await state.set_state(OrderForm.description)
    await message.answer(
        "📝 Qanday ish kerak?\n"
        "Masalan: 10 slaydli taqdimot tayyorlash."
    )


@router.message(OrderForm.description)
async def get_description(message: Message, state: FSMContext):
    description = (message.text or "").strip()

    if len(description) < 5:
        await message.answer(
            "Iltimos, buyurtmani batafsilroq yoz."
        )
        return

    await state.update_data(description=description)
    await state.set_state(OrderForm.price)

    await message.answer(
        "💰 Buyurtma narxini so'mda yoz.\n"
        "Masalan: 30000"
    )


@router.message(OrderForm.price)
async def get_price(message: Message, state: FSMContext):
    try:
        price = int((message.text or "").strip())

        if price <= 0:
            raise ValueError
    except ValueError:
        await message.answer(
            "Narxni musbat butun son bilan yoz. Masalan: 30000"
        )
        return

    data = await state.get_data()

    order_id = await add_order(
        student_id=message.from_user.id,
        description=data["description"],
        price=price,
    )

    await state.clear()

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📋 Buyurtmalarni ko'rish",
                    callback_data="order_info",
                )
            ]
        ]
    )

    await message.answer(
        f"✅ Buyurtma #{order_id} yaratildi!\n\n"
        f"📝 Ish: {data['description']}\n"
        f"💰 Narx: {price:,} so'm\n\n"
        "Buyurtma ijrochilar ro'yxatida ko'rinishi mumkin.",
        reply_markup=keyboard,
    )


@router.callback_query(F.data == "order_info")
async def order_info(callback: CallbackQuery):
    await callback.answer(
        "Pastdagi menyudan buyurtmalarni ko'rish bo'limini tanlang."
    )

