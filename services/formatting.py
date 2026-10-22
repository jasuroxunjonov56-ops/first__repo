def format_som(amount) -> str:
    """Summani O'zbekiston so'mida, mingliklarni bo'shliq bilan formatlaydi."""
    value = int(amount)
    return f"{value:,}".replace(",", " ") + " so'm"
