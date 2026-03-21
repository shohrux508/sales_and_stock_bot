from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

def main_worker_kb() -> ReplyKeyboardMarkup:
    kb = [
        [KeyboardButton(text="🛒 Оформить продажу")],
        [KeyboardButton(text="📈 Мои продажи (смена)")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def sell_product_list_kb(products) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    for product in products:
        # Show products that are in stock
        if product.quantity > 0:
            builder.button(
                text=f"{product.name} ({product.price} руб., ост. {product.quantity})",
                callback_data=f"sell_{product.id}"
            )
            
    builder.button(text="Отмена", callback_data="cancel_sale")
    builder.adjust(1)
    return builder.as_markup()

def cancel_worker_kb() -> ReplyKeyboardMarkup:
    kb = [[KeyboardButton(text="Отмена")]]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
