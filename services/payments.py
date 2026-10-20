
from config import ENTRY_FEE, COMMISSION_PERCENT


def calculate_payment(price: int) -> dict:
    """Buyurtma pulini platforma va ijrochi o'rtasida hisoblaydi."""

    if price <= 0:
        raise ValueError("Narx musbat bo'lishi kerak.")

    commission = price * COMMISSION_PERCENT // 100
    worker_amount = price - commission

    return {
        "total": price,
        "commission": commission,
        "worker_amount": worker_amount,
    }


def get_entry_fee() -> int:
    """Ijrochining ro'yxatdan o'tish to'lovi."""
    return ENTRY_FEE
