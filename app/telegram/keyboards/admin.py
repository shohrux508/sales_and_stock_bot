from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder
from app.config import settings
from app.database.models import UserRole

def main_admin_kb() -> ReplyKeyboardMarkup:
    kb = [
        [KeyboardButton(text="📦 Ombor"), KeyboardButton(text="🗂 Kategoriyalar")],
        [KeyboardButton(text="📥 Qabul qilish"), KeyboardButton(text="🗑 Hisobdan chiqarish")],
        [KeyboardButton(text="👥 Xodimlar"), KeyboardButton(text="📊 Statistika")],
        [KeyboardButton(text="🌐 Web Dashboard", web_app=WebAppInfo(url=f"{settings.WEBAPP_URL}/?u=admin&p={settings.DASHBOARD_PASSWORD}"))]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def categories_list_kb(categories, for_selection=False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    for cat in categories:
        cb_data = f"select_cat_{cat.id}" if for_selection else f"manage_cat_{cat.id}"
        builder.button(text=cat.name, callback_data=cb_data)
        
    if not for_selection:
        builder.button(text="➕ Kategoriya yaratish", callback_data="add_category")
        
    builder.adjust(1)
    return builder.as_markup()

def products_list_kb(products) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    for product in products:
        builder.button(
            text=f"{product.name} ({product.quantity} dona)",
            callback_data=f"prod_edit_{product.id}"
        )
    
    # Add new product at the end
    builder.button(text="➕ Mahsulot qo'shish", callback_data="add_product")
    
    builder.adjust(1) # one button per row
    return builder.as_markup()

def product_edit_kb(product_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ To'ldirish (+)", callback_data=f"prod_inc_{product_id}")
    builder.button(text="➖ Kamaytirish (-)", callback_data=f"prod_dec_{product_id}")
    builder.button(text="🏷 Shtrix-kod biriktirish", callback_data=f"prod_barcode_{product_id}")
    builder.button(text="🗑 O'chirish", callback_data=f"prod_del_conf_{product_id}")
    builder.button(text="🔙 Omborga qaytish", callback_data="back_to_stock")
    builder.adjust(2, 1, 1, 1)
    return builder.as_markup()

def product_delete_confirm_kb(product_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Ha, o'chirish", callback_data=f"prod_del_yes_{product_id}")
    builder.button(text="❌ Yo'q, qoldirish", callback_data=f"prod_edit_{product_id}")
    builder.adjust(1)
    return builder.as_markup()

def cancel_kb() -> ReplyKeyboardMarkup:
    kb = [[KeyboardButton(text="Bekor qilish")]]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def stats_periods_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📅 Bugun uchun", callback_data="stats_period_today")
    builder.button(text="🗓 7 kun uchun", callback_data="stats_period_week")
    builder.button(text="📥 Sotuvlar hisoboti (bugun)", callback_data="export_excel_today")
    builder.button(text="📦 Ombor hisoboti", callback_data="export_inventory_excel")
    builder.adjust(2, 1, 1)
    return builder.as_markup()

def approve_user_kb(tg_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Tasdiqlash", callback_data=f"approve_{tg_id}")
    builder.button(text="⛔ Rad etish", callback_data=f"reject_{tg_id}")
    builder.adjust(2)
    return builder.as_markup()

def undo_tx_kb(tx_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Bekor qilish", callback_data=f"undo_tx_{tx_id}")
    return builder.as_markup()

def undo_and_print_kb(tx_id: int, order_id: str) -> InlineKeyboardMarkup:
    """Кнопки отмены транзакции и печати чека (для уведомления админу)."""
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Bekor qilish", callback_data=f"undo_tx_{tx_id}")
    builder.button(text="🖨️ Chekni chop etish", callback_data=f"print_receipt_{order_id}")
    builder.adjust(1)
    return builder.as_markup()

def print_retry_kb(order_id: str) -> InlineKeyboardMarkup:
    """Кнопка повторной печати чека (когда принтер не был подключен)."""
    builder = InlineKeyboardBuilder()
    builder.button(text="🖨️ Chekni chop etish", callback_data=f"print_receipt_{order_id}")
    return builder.as_markup()

def staff_list_kb(workers) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for w in workers:
        role_label = ""
        if w.role == UserRole.PENDING:
            role_label = " (⏳ so'rov)"
        elif w.role == UserRole.BANNED:
            role_label = " (🚫 bloklangan)"
            
        name = w.username or f"ID {w.tg_id}"
        builder.button(text=f"👤 {name}{role_label}", callback_data=f"staff_profile_{w.tg_id}")
    builder.adjust(1)
    return builder.as_markup()

def staff_profile_kb(tg_id: int, role: UserRole) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    # If the user is pending, show approve/reject buttons first
    if role == UserRole.PENDING:
        builder.button(text="✅ Tasdiqlash", callback_data=f"approve_{tg_id}")
        builder.button(text="⛔ Rad etish", callback_data=f"reject_{tg_id}")
    elif role == UserRole.BANNED:
        builder.button(text="✅ Ruxsatni qaytarish", callback_data=f"approve_{tg_id}")
    
    builder.button(text="📝 F.I.Sh ni o'zgartirish", callback_data=f"staff_edit_name_{tg_id}")
    builder.button(text="📞 Telefonni o'zgartirish", callback_data=f"staff_edit_phone_{tg_id}")
    builder.button(text="🎯 KPI ni o'zgartirish", callback_data=f"staff_edit_kpi_{tg_id}")
    builder.button(text="📅 Hisobot (bugun)", callback_data=f"staff_excel_today_{tg_id}")
    builder.button(text="🗓 Hisobot (7 kun)", callback_data=f"staff_excel_week_{tg_id}")
    
    if role == UserRole.WORKER:
        builder.button(text="🗑 O'chirish/Bo'shatish", callback_data=f"staff_revoke_{tg_id}")
        
    builder.button(text="🔙 Xodimlar ro'yxatiga qaytish", callback_data="staff_list")
    
    # Calculate row adjustment: 
    # If pending: 2 (approve/reject), then the rest
    if role == UserRole.PENDING:
        builder.adjust(2, 2, 1, 2, 1, 1)
    elif role == UserRole.BANNED:
        builder.adjust(1, 2, 1, 2, 1, 1)
    else:
        builder.adjust(2, 1, 2, 1, 1)
        
    return builder.as_markup()
