
from aiogram import Router, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from config import ADMIN_ID, ENTRY_FEE
from database import (
    create_payment_request,
    get_pending_payment_requests,
    approve_payment_request,
    reject_payment_request,
    is_worker_active,
)

router = Router()


class PaymentStates(StatesGroup):
    waiting_for_transaction_id = State()
    waiting_for_receipt = State()


def payment_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="📤 Chek yuborish",
            callback_data="payment_start"
        )]
    ])


def admin_keyboard(request_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✅ Tasdiqlash",
                callback_data=f"payment_approve:{request_id}"
            ),
            InlineKeyboardButton(
                text="❌ Rad etish",
                callback_data=f"payment_reject:{request_id}"
            )
        ]
    ])


@router.message(Command("pay"))
async def start_payment(message: Message, state: FSMContext):
    if await is_worker_active(message.from_user.id):
        await message.answer("✅ Sizning bajaruvchi akkauntingiz faol.")
        return

    await state.clear()
    await message.answer(
        f"Bajaruvchi bo‘lish uchun kirish to‘lovi: {ENTRY_FEE} so‘m.\n\n"
        "To‘lovni karta egasi tasdiqlagan rekvizitlar bo‘yicha amalga oshiring. "
        "Keyin «Chek yuborish» tugmasini bosing.",
        reply_markup=payment_keyboard()
    )


@router.callback_query(F.data == "payment_start")
async def payment_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(PaymentStates.waiting_for_transaction_id)
    await callback.message.answer(
        "Bank ilovasidagi tranzaksiya ID raqamini yuboring.\n\n"
        "To‘lov qilmagan bo‘lsangiz, avval to‘lovni amalga oshiring."
    )
    await callback.answer()


@router.message(PaymentStates.waiting_for_transaction_id)
async def get_transaction_id(message: Message, state: FSMContext):
    transaction_id = (message.text or "").strip()

    if len(transaction_id) < 4 or len(transaction_id) > 100:
        await message.answer("Tranzaksiya ID noto‘g‘ri ko‘rinadi. Qayta yuboring.")
        return

    await state.update_data(transaction_id=transaction_id)
    await state.set_state(PaymentStates.waiting_for_receipt)
    await message.answer("Endi to‘lov chekini rasm sifatida yuboring.")


@router.message(PaymentStates.waiting_for_receipt, F.photo)
async def get_receipt(message: Message, state: FSMContext):
    data = await state.get_data()
    transaction_id = data.get("transaction_id")

    if not transaction_id:
        await state.clear()
        await message.answer("Jarayon boshidan boshlansin: /pay")
        return

    created = await create_payment_request(
        user_id=message.from_user.id,
        transaction_id=transaction_id,
        receipt_file_id=message.photo[-1].file_id,
    )

    await state.clear()

    if not created:
        await message.answer(
            "Bu tranzaksiya ID oldin yuborilgan. "
            "Agar xato bo‘lsa, admin bilan bog‘laning."
        )
        return

    await message.answer(
        "📨 To‘lov so‘rovingiz adminga yuborildi. "
        "Pul tushgani tekshirilgach, javob beriladi."
    )

    admin_text = (
        "💳 Yangi bajaruvchi to‘lov so‘rovi\n\n"
        f"👤 Telegram ID: {message.from_user.id}\n"
        f"🧾 Tranzaksiya ID: {transaction_id}\n"
        f"💰 Kutilayotgan summa: {ENTRY_FEE} so‘m\n\n"
        "Tasdiqlashdan oldin bank hisobidagi haqiqiy tushumni tekshiring."
    )

    await message.bot.send_photo(
        chat_id=ADMIN_ID,
        photo=message.photo[-1].file_id,
        caption=admin_text,
        reply_markup=admin_keyboard(
            (await get_pending_payment_requests())[-1]["id"]
        )
    )


@router.message(PaymentStates.waiting_for_receipt)
async def receipt_must_be_photo(message: Message):
    await message.answer("Iltimos, chekni rasm sifatida yuboring.")


@router.callback_query(F.data.startswith("payment_approve:"))
async def approve_payment(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Bu amal faqat admin uchun.", show_alert=True)
        return

    request_id = int(callback.data.split(":")[1])
    user_id = await approve_payment_request(request_id)

    if user_id is None:
        await callback.answer("Bu so‘rov avval ko‘rib chiqilgan.", show_alert=True)
        return

    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        f"✅ {user_id} foydalanuvchisi faollashtirildi."
    )

    try:
        await callback.bot.send_message(
            user_id,
            "✅ To‘lovingiz admin tomonidan tasdiqlandi. "
            "Bajaruvchi akkauntingiz faollashtirildi."
        )
    except Exception:
        pass

    await callback.answer("Tasdiqlandi.")


@router.callback_query(F.data.startswith("payment_reject:"))
async def reject_payment(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Bu amal faqat admin uchun.", show_alert=True)
        return

    request_id = int(callback.data.split(":")[1])
    rejected = await reject_payment_request(request_id)

    if not rejected:
        await callback.answer("Bu so‘rov avval ko‘rib chiqilgan.", show_alert=True)
        return

    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("❌ To‘lov so‘rovi rad etildi.")
    await callback.answer("Rad etildi.")


@router.message(Command("pendingpayments"))
async def pending_payments(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    requests = await get_pending_payment_requests()

    if not requests:
        await message.answer("Kutilayotgan to‘lov so‘rovlari yo‘q.")
        return

    for request in requests:
        await message.answer(
            f"🧾 So‘rov ID: {request['id']}\n"
            f"👤 Foydalanuvchi: {request['user_id']}\n"
            f"💰 Summa: {ENTRY_FEE} so‘m\n"
            f"🧾 Tranzaksiya ID: {request['transaction_id']}",
            reply_markup=admin_keyboard(request["id"])
        )

