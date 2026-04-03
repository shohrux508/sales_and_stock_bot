from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def main_worker_kb() -> ReplyKeyboardMarkup:
    kb = [
        [KeyboardButton(text="🛒 Sotuvni rasmiylashtirish")],
        [KeyboardButton(text="📈 Mening savdo ko'rsatkichlarim")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def worker_categories_kb(categories) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for cat in categories:
        builder.button(text=cat.name, callback_data=f"w_cat_{cat.id}")
    builder.adjust(2)
    builder.row(InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_sale"))
    return builder.as_markup()

def sell_product_list_kb(products) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    for product in products:
        # Show products that are in stock
        if product.quantity > 0:
            # Shorter text to fit in 2 columns
            builder.button(
                text=f"{product.name} ({product.quantity} ta)",
                callback_data=f"sell_{product.id}"
            )
            
    builder.adjust(2)
    builder.row(
        InlineKeyboardButton(text="🔙 Qaytish", callback_data="back_to_w_cats"),
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_sale")
    )
    return builder.as_markup()

def cancel_inline_kb() -> InlineKeyboardMarkup:
    """Inline-кнопка отмены (не заменяет нижнюю клавиатуру)."""
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Bekor qilish", callback_data="cancel_sale")
    return builder.as_markup()

def cart_decision_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Yana mahsulot qo'shish", callback_data="cart_add_more")
    builder.button(text="✅ Chekni chiqarish", callback_data="cart_checkout")
    builder.adjust(1)
    return builder.as_markup()

def after_checkout_kb() -> InlineKeyboardMarkup:
    """Inline-кнопка быстрого начала новой продажи после чека."""
    builder = InlineKeyboardBuilder()
    builder.button(text="🛒 Yangi sotuv", callback_data="quick_new_sale")
    builder.adjust(1)
    return builder.as_markup()

def kpi_progress_bar(current: float, target: float) -> str:
    """Генерирует визуальную полосу прогресса KPI."""
    if target <= 0:
        return "🎯 KPI belgilanmagan"
    
    percent = min(100, int(current / target * 100))
    filled = percent // 10
    empty = 10 - filled
    
    bar = "🟩" * filled + "⬜" * empty
    
    if percent >= 100:
        status = "🔥 Reja bajarildi!"
    elif percent >= 75:
        status = "💪 Ozgina qoldi!"
    elif percent >= 50:
        status = "📈 Yaxshi natija!"
    else:
        status = "🚀 Davom eting!"
    
    return f"{bar} {percent}%\n{status}"
