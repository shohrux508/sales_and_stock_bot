from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup
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
    builder.button(text="Bekor qilish", callback_data="cancel_sale")
    builder.adjust(1)
    return builder.as_markup()

def sell_product_list_kb(products) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    for product in products:
        # Show products that are in stock
        if product.quantity > 0:
            builder.button(
                text=f"{product.name} ({product.price} so'm, qoldiq: {product.quantity})",
                callback_data=f"sell_{product.id}"
            )
            
    builder.button(text="🔙 Kategoriyalarga qaytish", callback_data="back_to_w_cats")
    builder.button(text="Bekor qilish", callback_data="cancel_sale")
    builder.adjust(1)
    return builder.as_markup()

def cancel_worker_kb() -> ReplyKeyboardMarkup:
    kb = [[KeyboardButton(text="Bekor qilish")]]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def cart_decision_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Yana mahsulot qo'shish", callback_data="cart_add_more")
    builder.button(text="✅ Chekni chiqarish", callback_data="cart_checkout")
    builder.adjust(1)
    return builder.as_markup()
