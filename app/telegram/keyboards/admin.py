from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder
from app.config import settings

def main_admin_kb() -> ReplyKeyboardMarkup:
    kb = [
        [KeyboardButton(text="📦 Склад"), KeyboardButton(text="🗂 Категории")],
        [KeyboardButton(text="📥 Приемка"), KeyboardButton(text="🗑 Списание")],
        [KeyboardButton(text="👥 Сотрудники"), KeyboardButton(text="📊 Статистика")],
        [KeyboardButton(text="🌐 Web Dashboard", web_app=WebAppInfo(url=f"{settings.WEBAPP_URL}/?user=admin&pwd={settings.DASHBOARD_PASSWORD}"))]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def categories_list_kb(categories, for_selection=False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    for cat in categories:
        cb_data = f"select_cat_{cat.id}" if for_selection else f"manage_cat_{cat.id}"
        builder.button(text=cat.name, callback_data=cb_data)
        
    if not for_selection:
        builder.button(text="➕ Создать категорию", callback_data="add_category")
        
    builder.adjust(1)
    return builder.as_markup()

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
    builder.button(text="🏷 Привязать штрихкод", callback_data=f"prod_barcode_{product_id}")
    builder.button(text="🗑 Удалить", callback_data=f"prod_del_conf_{product_id}")
    builder.button(text="🔙 Назад к складу", callback_data="back_to_stock")
    builder.adjust(2, 1, 1, 1)
    return builder.as_markup()

def product_delete_confirm_kb(product_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да, удалить", callback_data=f"prod_del_yes_{product_id}")
    builder.button(text="❌ Нет, оставить", callback_data=f"prod_edit_{product_id}")
    builder.adjust(1)
    return builder.as_markup()

def cancel_kb() -> ReplyKeyboardMarkup:
    kb = [[KeyboardButton(text="Отмена")]]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def stats_periods_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📅 За сегодня", callback_data="stats_period_today")
    builder.button(text="🗓 За 7 дней", callback_data="stats_period_week")
    builder.button(text="📥 Отчет Продаж (сегодня)", callback_data="export_excel_today")
    builder.button(text="📦 Отчет по Складу", callback_data="export_inventory_excel")
    builder.adjust(2, 1, 1)
    return builder.as_markup()

def approve_user_kb(tg_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Одобрить", callback_data=f"approve_{tg_id}")
    builder.button(text="⛔ Отклонить", callback_data=f"reject_{tg_id}")
    builder.adjust(2)
    return builder.as_markup()

def undo_tx_kb(tx_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отменить (Rollback)", callback_data=f"undo_tx_{tx_id}")
    return builder.as_markup()

def staff_list_kb(workers) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for w in workers:
        name = w.username or f"ID {w.tg_id}"
        builder.button(text=f"👤 {name}", callback_data=f"staff_profile_{w.tg_id}")
    builder.adjust(1)
    return builder.as_markup()

def staff_profile_kb(tg_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📝 Изменить ФИО", callback_data=f"staff_edit_name_{tg_id}")
    builder.button(text="📞 Изменить Телефон", callback_data=f"staff_edit_phone_{tg_id}")
    builder.button(text="🎯 Изменить KPI", callback_data=f"staff_edit_kpi_{tg_id}")
    builder.button(text="📅 Отчет (сегодня)", callback_data=f"staff_excel_today_{tg_id}")
    builder.button(text="🗓 Отчет (7 дней)", callback_data=f"staff_excel_week_{tg_id}")
    builder.button(text="🗑 Удалить/Уволить", callback_data=f"staff_revoke_{tg_id}")
    builder.button(text="🔙 К списку сотрудников", callback_data="staff_list")
    builder.adjust(2, 1, 2, 1, 1)
    return builder.as_markup()
