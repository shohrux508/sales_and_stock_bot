from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def main_admin_kb() -> ReplyKeyboardMarkup:
    kb = [
        [KeyboardButton(text="📦 Склад"), KeyboardButton(text="👥 Сотрудники")],
        [KeyboardButton(text="📊 Статистика")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def products_list_kb(products) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    for product in products:
        builder.button(
            text=f"{product.name} ({product.quantity} шт)",
            callback_data=f"prod_edit_{product.id}"
        )
    
    # Add new product at the end
    builder.button(text="➕ Добавить товар", callback_data="add_product")
    
    builder.adjust(1) # one button per row
    return builder.as_markup()

def product_edit_kb(product_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Пополнить (+)", callback_data=f"prod_inc_{product_id}")
    builder.button(text="➖ Уменьшить (-)", callback_data=f"prod_dec_{product_id}")
    # builder.button(text="🗑 Удалить", callback_data=f"prod_del_{product_id}")
    builder.button(text="🔙 Назад к складу", callback_data="back_to_stock")
    builder.adjust(2, 1)
    return builder.as_markup()

def cancel_kb() -> ReplyKeyboardMarkup:
    kb = [[KeyboardButton(text="Отмена")]]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def stats_periods_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📅 За сегодня", callback_data="stats_period_today")
    builder.button(text="🗓 За 7 дней", callback_data="stats_period_week")
    builder.adjust(2)
    return builder.as_markup()
