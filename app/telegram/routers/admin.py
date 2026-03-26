from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from app.database.models import User, UserRole
from app.container import Container

from app.services.product_service import ProductService
from app.services.user_service import UserService
from app.services.category_service import CategoryService
from app.services.transaction_service import TransactionService

from app.telegram.states.admin import AddProductState, AddCategoryState, WaitAdminReply, EditStaffProfileState
from app.telegram.keyboards.admin import (
    main_admin_kb, 
    products_list_kb, 
    cancel_kb, 
    product_edit_kb, 
    categories_list_kb, 
    approve_user_kb,
    stats_periods_kb,
    undo_tx_kb
)

router = Router()

# Filter for admin role only
# We can do this with a Custom Filter, but for simplicity we'll check inside or use F.role == UserRole.ADMIN
# Since db_user is passed to every handler, we can filter using it (Aiogram 3 allows checking kwargs in F-magic)
# However, the easiest way for now is a custom function or simple lambda.
router.message.filter(lambda event, db_user=None: db_user is not None and db_user.role == UserRole.ADMIN)
router.callback_query.filter(lambda event, db_user=None: db_user is not None and db_user.role == UserRole.ADMIN)

@router.message(F.text == "📦 Склад")
async def show_stock(message: types.Message, container: Container):
    product_service: ProductService = container.get("product_service")
    products = await product_service.get_all_products()
    
    if not products:
        await message.answer("Склад пуст.", reply_markup=products_list_kb(products))
        return
        
    await message.answer("📦 Список товаров на складе:", reply_markup=products_list_kb(products))

@router.callback_query(F.data == "back_to_stock")
async def cb_back_to_stock(call: types.CallbackQuery, container: Container):
    product_service: ProductService = container.get("product_service")
    products = await product_service.get_all_products()
    await call.message.edit_text("📦 Список товаров на складе:", reply_markup=products_list_kb(products))

@router.message(F.text == "Отмена")
async def cancel_handler(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Действие отменено.", reply_markup=main_admin_kb())

# --- Category Management ---
@router.message(F.text == "🗂 Категории")
async def show_categories(message: types.Message, container: Container):
    from app.services.category_service import CategoryService
    from app.telegram.keyboards.admin import categories_list_kb
    category_service: CategoryService = container.get("category_service")
    categories = await category_service.get_all_categories()
    
    if not categories:
        await message.answer("Категорий пока нет. Вы можете их добавить.", reply_markup=categories_list_kb([]))
    else:
        await message.answer("Управление категориями:", reply_markup=categories_list_kb(categories))

@router.callback_query(F.data == "add_category")
async def cb_add_category(call: types.CallbackQuery, state: FSMContext):
    from app.telegram.states.admin import AddCategoryState
    await state.set_state(AddCategoryState.name)
    await call.message.edit_text("Введите название новой категории:", reply_markup=None)
    await call.bot.send_message(call.message.chat.id, "Или нажмите 'Отмена' для возврата.", reply_markup=cancel_kb())

@router.message(AddCategoryState.name)
async def process_add_category_name(message: types.Message, state: FSMContext, container: Container):
    category_name = message.text.strip()
    category_service: CategoryService = container.get("category_service")
    
    try:
        await category_service.create_category(category_name)
        await message.answer(f"✅ Категория '{category_name}' успешно создана!", reply_markup=main_admin_kb())
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}", reply_markup=main_admin_kb())
    finally:
        await state.clear()

@router.callback_query(F.data.startswith("manage_cat_"))
async def cb_manage_category(call: types.CallbackQuery):
    cat_id = int(call.data.split("_")[2])
    await call.answer(f"Управление категорией ID {cat_id} (в разработке)", show_alert=True)

# --- Add Product ---
@router.callback_query(F.data == "add_product")
async def start_add_product(call: types.CallbackQuery, state: FSMContext, container: Container):
    from app.services.category_service import CategoryService
    from app.telegram.keyboards.admin import categories_list_kb
    category_service: CategoryService = container.get("category_service")
    categories = await category_service.get_all_categories()
    
    if not categories:
        await call.answer("Сначала создайте категорию (🗂 Категории)!", show_alert=True)
        return
        
    await state.set_state(AddProductState.category_id)
    await call.message.edit_text("Выберите категорию для нового товара:", reply_markup=categories_list_kb(categories, for_selection=True))

@router.callback_query(AddProductState.category_id, F.data.startswith("select_cat_"))
async def cb_select_category_for_product(call: types.CallbackQuery, state: FSMContext):
    cat_id = int(call.data.split("_")[2])
    await state.update_data(category_id=cat_id)
    await state.set_state(AddProductState.name)
    await call.message.edit_text("Отлично. Введите название нового товара:", reply_markup=None)
    await call.bot.send_message(call.message.chat.id, "Или отправьте 'Отмена'", reply_markup=cancel_kb())

@router.message(AddProductState.name)
async def process_product_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Введите цену товара (число):")
    await state.set_state(AddProductState.price)

@router.message(AddProductState.price)
async def process_product_price(message: types.Message, state: FSMContext):
    try:
        price = float(message.text.replace(",", "."))
    except ValueError:
        await message.answer("Пожалуйста, введите корректное число для цены.")
        return
        
    await state.update_data(price=price)
    await message.answer("Введите начальное количество на складе:")
    await state.set_state(AddProductState.initial_quantity)

@router.message(AddProductState.initial_quantity)
async def process_product_quantity(message: types.Message, state: FSMContext, container: Container):
    try:
        qty = int(message.text)
    except ValueError:
        await message.answer("Пожалуйста, введите целое число.")
        return
        
    data = await state.get_data()
    product_service: ProductService = container.get("product_service")
    
    try:
        cat_id = data.get("category_id")
        await product_service.create_product(name=data['name'], price=data['price'], quantity=qty, category_id=cat_id)
        await message.answer(f"✅ Товар '{data['name']}' добавлен!", reply_markup=main_admin_kb())
    except Exception as e:
        await message.answer("❌ Ошибка при добавлении в БД. Возможно, товар с таким именем уже существует.", reply_markup=main_admin_kb())
        
    await state.clear()


# --- Edit Product Stock ---
@router.callback_query(F.data.startswith("prod_edit_"))
async def cb_edit_product(call: types.CallbackQuery, container: Container):
    product_id = int(call.data.split("_")[2])
    product_service: ProductService = container.get("product_service")
    
    product = await product_service.get_product_by_id(product_id)
    if product:
        text = f"📦 Товар: *{product.name}*\nЦена: {product.price}\nОстаток: {product.quantity}"
        await call.message.edit_text(text, parse_mode="Markdown", reply_markup=product_edit_kb(product_id))

@router.callback_query(F.data.startswith("prod_inc_"))
async def cb_inc_product(call: types.CallbackQuery, container: Container):
    product_id = int(call.data.split("_")[2])
    product_service: ProductService = container.get("product_service")
    
    product = await product_service.update_quantity(product_id, 1)
    if product:
        text = f"📦 Товар: *{product.name}*\nЦена: {product.price}\nОстаток: {product.quantity}"
        await call.message.edit_text(text, parse_mode="Markdown", reply_markup=product_edit_kb(product_id))
    else:
        await call.answer("Товар не найден", show_alert=True)

@router.callback_query(F.data.startswith("prod_dec_"))
async def cb_dec_product(call: types.CallbackQuery, container: Container):
    product_id = int(call.data.split("_")[2])
    product_service: ProductService = container.get("product_service")
    
    # Check if quantity > 0
    product = await product_service.get_product_by_id(product_id)
    if product and product.quantity > 0:
        new_product = await product_service.update_quantity(product_id, -1)
        text = f"📦 Товар: *{new_product.name}*\nЦена: {new_product.price}\nОстаток: {new_product.quantity}"
        await call.message.edit_text(text, parse_mode="Markdown", reply_markup=product_edit_kb(product_id))
    else:
        await call.answer("Нельзя уменьшить (остаток 0 или товар не найден)", show_alert=True)

@router.callback_query(F.data.startswith("prod_del_conf_"))
async def cb_delete_product_conf(call: types.CallbackQuery, container: Container):
    product_id = int(call.data.split("_")[3])
    from app.telegram.keyboards.admin import product_delete_confirm_kb
    product_service: ProductService = container.get("product_service")
    product = await product_service.get_product_by_id(product_id)
    if product:
        await call.message.edit_text(f"⚠️ Вы уверены, что хотите удалить товар *{product.name}*?\nЭто действие нельзя отменить.", parse_mode="Markdown", reply_markup=product_delete_confirm_kb(product_id))

@router.callback_query(F.data.startswith("prod_del_yes_"))
async def cb_delete_product_yes(call: types.CallbackQuery, container: Container):
    product_id = int(call.data.split("_")[3])
    product_service: ProductService = container.get("product_service")
    
    success = await product_service.delete_product(product_id)
    if success:
        await call.answer("Товар удален", show_alert=True)
        products = await product_service.get_all_products()
        await call.message.edit_text("📦 Список товаров на складе:", reply_markup=products_list_kb(products))
    else:
        await call.answer("Ошибка при удалении", show_alert=True)

# Update start command for admin
@router.message(F.text == "/start")
async def admin_start(message: types.Message, db_user: User):
    await message.answer(f"Добро пожаловать в панель администратора, {db_user.username}!", reply_markup=main_admin_kb())

# --- Staff Moderation ---
@router.callback_query(F.data.startswith("approve_"))
async def cb_approve_user(call: types.CallbackQuery, container: Container):
    user_id = int(call.data.split("_")[1])
    user_service: UserService = container.get("user_service")
    
    updated_user = await user_service.update_user_role(user_id, UserRole.WORKER)
    if updated_user:
        await call.message.edit_text(f"✅ Пользователь @{updated_user.username or user_id} получил доступ (WORKER).")
        try:
            await call.bot.send_message(user_id, "🎉 Ваша заявка одобрена! Теперь вам доступно меню сотрудника.\nНажмите /start.")
        except Exception:
            pass
    else:
        await call.answer("Ошибка при обновлении роли", show_alert=True)

@router.callback_query(F.data.startswith("reject_"))
async def cb_reject_user(call: types.CallbackQuery, container: Container):
    user_id = int(call.data.split("_")[1])
    user_service: UserService = container.get("user_service")
    
    updated_user = await user_service.update_user_role(user_id, UserRole.BANNED)
    if updated_user:
        await call.message.edit_text(f"⛔ Пользователь @{updated_user.username or user_id} отклонен (BANNED).")
    else:
        await call.answer("Ошибка при обновлении роли", show_alert=True)

# --- Manage Staff ---
@router.message(F.text == "👥 Сотрудники")
async def show_staff(message: types.Message, container: Container):
    user_service: UserService = container.get("user_service")
    
    users = await user_service.get_all_users()
    workers = [u for u in users if u.role == UserRole.WORKER]
    
    if not workers:
        text = "Сотрудников пока нет."
        await message.answer(text, reply_markup=main_admin_kb())
    else:
        from app.telegram.keyboards.admin import staff_list_kb
        text = "👥 Выберите сотрудника для просмотра профиля:"
        await message.answer(text, reply_markup=staff_list_kb(workers))

@router.callback_query(F.data == "staff_list")
async def cb_staff_list(call: types.CallbackQuery, container: Container):
    user_service: UserService = container.get("user_service")
    users = await user_service.get_all_users()
    workers = [u for u in users if u.role == UserRole.WORKER]
    
    from app.telegram.keyboards.admin import staff_list_kb
    text = "👥 Выберите сотрудника для просмотра профиля:"
    await call.message.edit_text(text, reply_markup=staff_list_kb(workers))

@router.callback_query(F.data.startswith("staff_profile_"))
async def cb_staff_profile(call: types.CallbackQuery, container: Container):
    tg_id = int(call.data.split("_")[2])
    user_service: UserService = container.get("user_service")
    user = await user_service.get_user_by_tg_id(tg_id)
    if not user:
        await call.answer("Пользователь не найден.", show_alert=True)
        return
        
    from app.telegram.keyboards.admin import staff_profile_kb
    username = user.username or "без_юзернейма"
    
    # Calculate current progress for KPI
    transaction_service: TransactionService = container.get("transaction_service")
    # Using 'today' statistics filtered by this user
    stats_today = await transaction_service.get_admin_statistics("today", user_id=user.id)
    revenue_today = sum(t.total_price for t in stats_today)
    
    status = "✅ Активен" if user.is_active else "⛔ Заблокирован"
    
    text = f"👤 *Профиль сотрудника:*\n\n" \
           f"• ID: `{user.tg_id}`\n" \
           f"• Username: @{username}\n" \
           f"• ФИО: {user.full_name or 'не указано'}\n" \
           f"• Телефон: {user.phone or 'не указано'}\n" \
           f"• Роль: {user.role.value}\n" \
           f"• Статус: {status}\n" \
           f"• Регистрация: {user.joined_at.strftime('%Y-%m-%d') if user.joined_at else '---'}\n\n" \
           f"🎯 *KPI на сегодня:*\n" \
           f"• Цель: {user.kpi} руб.\n" \
           f"• Исполнено: {revenue_today} руб.\n" \
           f"• Прогресс: {min(100, int(revenue_today/user.kpi*100)) if user.kpi > 0 else 0}%\n\n" \
           f"Выберите действие:"
    
    await call.message.edit_text(text, parse_mode="Markdown", reply_markup=staff_profile_kb(tg_id))

@router.callback_query(F.data.startswith("staff_edit_name_"))
async def cb_staff_edit_name(call: types.CallbackQuery, state: FSMContext):
    tg_id = int(call.data.split("_")[3])
    await state.update_data(target_tg_id=tg_id)
    await state.set_state(EditStaffProfileState.full_name)
    await call.message.edit_text("Введите ФИО сотрудника:", reply_markup=None)
    await call.bot.send_message(call.message.chat.id, "Или нажмите 'Отмена'", reply_markup=cancel_kb())

@router.message(EditStaffProfileState.full_name)
async def process_edit_staff_name(message: types.Message, state: FSMContext, container: Container):
    data = await state.get_data()
    tg_id = data.get("target_tg_id")
    user_service: UserService = container.get("user_service")
    await user_service.update_user_profile(tg_id, full_name=message.text.strip())
    await message.answer(f"✅ ФИО обновлено!", reply_markup=main_admin_kb())
    await state.clear()

@router.callback_query(F.data.startswith("staff_edit_phone_"))
async def cb_staff_edit_phone(call: types.CallbackQuery, state: FSMContext):
    tg_id = int(call.data.split("_")[3])
    await state.update_data(target_tg_id=tg_id)
    await state.set_state(EditStaffProfileState.phone)
    await call.message.edit_text("Введите номер телефона сотрудника:", reply_markup=None)
    await call.bot.send_message(call.message.chat.id, "Или нажмите 'Отмена'", reply_markup=cancel_kb())

@router.message(EditStaffProfileState.phone)
async def process_edit_staff_phone(message: types.Message, state: FSMContext, container: Container):
    data = await state.get_data()
    tg_id = data.get("target_tg_id")
    user_service: UserService = container.get("user_service")
    await user_service.update_user_profile(tg_id, phone=message.text.strip())
    await message.answer(f"✅ Телефон обновлен!", reply_markup=main_admin_kb())
    await state.clear()

from app.telegram.states.admin import EditStaffKPIState

@router.callback_query(F.data.startswith("staff_edit_kpi_"))
async def cb_staff_edit_kpi(call: types.CallbackQuery, state: FSMContext):
    tg_id = int(call.data.split("_")[3])
    await state.update_data(target_tg_id=tg_id)
    await state.set_state(EditStaffKPIState.kpi)
    await call.message.edit_text("Введите новый KPI (целевое значение в рублях или штуках):", reply_markup=None)
    await call.bot.send_message(call.message.chat.id, "Или нажмите 'Отмена'", reply_markup=cancel_kb())

@router.message(EditStaffKPIState.kpi)
async def process_edit_staff_kpi(message: types.Message, state: FSMContext, container: Container):
    try:
        new_kpi = int(message.text)
    except ValueError:
        await message.answer("Пожалуйста, введите целое число.")
        return
        
    data = await state.get_data()
    tg_id = data.get("target_tg_id")
    user_service: UserService = container.get("user_service")
    
    updated_user = await user_service.update_user_kpi(tg_id, new_kpi)
    if updated_user:
        await message.answer(f"✅ KPI успешно обновлен до {new_kpi}!", reply_markup=main_admin_kb())
    else:
        await message.answer("❌ Ошибка при обновлении KPI.", reply_markup=main_admin_kb())
    await state.clear()

@router.callback_query(F.data.startswith("staff_revoke_"))
async def cb_staff_revoke(call: types.CallbackQuery, container: Container):
    tg_id = int(call.data.split("_")[2])
    user_service: UserService = container.get("user_service")
    
    updated_user = await user_service.update_user_role(tg_id, UserRole.BANNED)
    if updated_user:
        await call.message.edit_text(f"⛔ Сотрудник {tg_id} заблокирован.")
        try:
            await call.bot.send_message(tg_id, "Ваш доступ закрыт администратором.")
        except:
            pass
    else:
        await call.answer("Ошибка", show_alert=True)

@router.callback_query(F.data.startswith("staff_excel_"))
async def cb_staff_export_excel(call: types.CallbackQuery, container: Container):
    parts = call.data.split("_")
    period = parts[2]
    tg_id = int(parts[3])
    
    transaction_service: TransactionService = container.get("transaction_service")
    user_service: UserService = container.get("user_service")
    
    user = await user_service.get_user_by_tg_id(tg_id)
    user_pk_id = user.id if user else None
    if not user_pk_id:
        await call.answer("Пользователь не найден.", show_alert=True)
        return
        
    transactions = await transaction_service.get_admin_statistics(period, user_id=user_pk_id)
    if not transactions:
        await call.answer("Нет транзакций за этот период", show_alert=True)
        return
        
    import openpyxl
    from aiogram.types import BufferedInputFile
    import io
    from datetime import datetime
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"Продажи"
    
    headers = ["ID чека", "Дата/Время (UTC)", "Категория", "Товар", "Кол-во", "Сумма (руб)"]
    ws.append(headers)
    
    for t in transactions:
        prod_name = t.product.name if t.product else "Удален"
        cat_name = t.product.category.name if getattr(t.product, 'category', None) else "Не указана"
        
        row = [
            t.id,
            t.timestamp.strftime("%Y-%m-%d %H:%M:%S") if t.timestamp else "",
            cat_name,
            prod_name,
            t.amount,
            t.total_price
        ]
        ws.append(row)
        
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    
    file_name = f"Report_Staff_{user.username or tg_id}_{period}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    file = BufferedInputFile(buf.read(), filename=file_name)
    
    await call.message.answer_document(document=file, caption=f"📥 Отчет по сотруднику @{user.username or tg_id} готов!")
    await call.answer()


# --- Statistics ---
@router.message(F.text == "📊 Статистика")
async def show_stats_menu(message: types.Message):
    from app.telegram.keyboards.admin import stats_periods_kb
    await message.answer("Выберите период для отчета:", reply_markup=stats_periods_kb())

@router.callback_query(F.data.startswith("stats_period_"))
async def process_stats(call: types.CallbackQuery, container: Container):
    period = call.data.split("_")[2] # "today" or "week"
    transaction_service: TransactionService = container.get("transaction_service")
    
    transactions = await transaction_service.get_admin_statistics(period)
    
    if not transactions:
        await call.answer("За этот период продаж не было.", show_alert=True)
        return
        
    total_sales = len(transactions)
    total_items = sum(t.amount for t in transactions)
    total_revenue = sum(t.total_price for t in transactions)
    
    # Simple top 3 calculation
    from collections import defaultdict
    product_sales = defaultdict(lambda: {"count": 0, "revenue": 0})
    
    for t in transactions:
        p_name = t.product.name if t.product else f"Товар {t.product_id} (удален)"
        product_sales[p_name]["count"] += t.amount
        product_sales[p_name]["revenue"] += t.total_price
        
    top_products = sorted(product_sales.items(), key=lambda x: x[1]['count'], reverse=True)[:3]
    
    # Staff rankings
    rankings = await transaction_service.get_staff_rankings(period)
    
    period_str = "сегодня" if period == "today" else "последние 7 дней"
    
    text = f"📊 *Статистика за {period_str}:*\n\n"
    text += f"Всего чеков: {total_sales}\n"
    text += f"Продано единиц: {total_items} шт.\n"
    text += f"Общая выручка: *{total_revenue} руб.*\n\n"
    
    text += "🏆 *Топ-3 продаваемых товаров:*\n"
    for rank, (p_name, stats) in enumerate(top_products, 1):
        text += f"{rank}. {p_name} — {stats['count']} шт. ({stats['revenue']} руб.)\n"
        
    if rankings:
        text += "\n👥 *Рейтинг сотрудников:*\n"
        for i, rank in enumerate(rankings, 1):
            name = rank.username or f"ID {rank.tg_id}"
            text += f"{i}. {name} — {rank.revenue} руб. ({rank.items} ед.)\n"
            
    await call.message.edit_text(text, parse_mode="Markdown")

# --- Rollbacks F3 ---
@router.callback_query(F.data.startswith("undo_tx_"))
async def cb_undo_tx(call: types.CallbackQuery, container: Container):
    tx_id = int(call.data.split("_")[2])
    transaction_service: TransactionService = container.get("transaction_service")
    
    success = await transaction_service.rollback_transaction(tx_id)
    if success:
        # Edit the original alert message
        original_text = call.message.text or call.message.caption or "Детали неизвестны"
        new_text = f"❌ *Транзакция отменена. Товар возвращен на склад.*\n\n~~{original_text}~~"
        await call.message.edit_text(new_text, parse_mode="Markdown")
        await call.answer("Возврат оформлен!", show_alert=True)
# --- Excel Export F4 ---
@router.callback_query(F.data.startswith("export_excel_"))
async def cb_export_excel(call: types.CallbackQuery, container: Container):
    period = call.data.split("_")[2]
    transaction_service: TransactionService = container.get("transaction_service")
    
    transactions = await transaction_service.get_admin_statistics(period)
    if not transactions:
        await call.answer("Нет транзакций за этот период", show_alert=True)
        return
        
    import openpyxl
    from aiogram.types import BufferedInputFile
    import io
    from datetime import datetime
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Продажи"
    
    headers = ["ID чека", "Дата/Время (UTC)", "Сотрудник", "Категория", "Товар", "Кол-во", "Сумма (руб)"]
    ws.append(headers)
    
    for t in transactions:
        prod_name = t.product.name if t.product else "Удален"
        cat_name = t.product.category.name if getattr(t.product, 'category', None) else "Не указана"
        user_name = t.user.username if t.user and t.user.username else str(t.user_id)
        
        row = [
            t.id,
            t.timestamp.strftime("%Y-%m-%d %H:%M:%S") if t.timestamp else "",
            user_name,
            cat_name,
            prod_name,
            t.amount,
            t.total_price
        ]
        ws.append(row)
        
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    
    file_name = f"Report_{period}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    file = BufferedInputFile(buf.read(), filename=file_name)
    
    await call.message.answer_document(document=file, caption="📥 Ваш Excel-отчет готов!")
    await call.answer()

@router.callback_query(F.data == "export_inventory_excel")
async def cb_export_inventory_excel(call: types.CallbackQuery, container: Container):
    product_service: ProductService = container.get("product_service")
    products = await product_service.get_all_products()
    
    if not products:
        await call.answer("На складе нет товаров.", show_alert=True)
        return
        
    import openpyxl
    from aiogram.types import BufferedInputFile
    import io
    from datetime import datetime
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Склад"
    
    headers = ["ID", "Категория", "Наименование", "Цена", "Остаток", "Штрихкод"]
    ws.append(headers)
    
    for p in products:
        cat_name = p.category.name if p.category else "Без категории"
        ws.append([p.id, cat_name, p.name, p.price, p.quantity, p.barcode or ""])
        
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    
    file_name = f"Inventory_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    file = BufferedInputFile(buf.read(), filename=file_name)
    
    await call.message.answer_document(document=file, caption="📦 Актуальный отчет по остаткам на складе готов!")
    await call.answer()

# --- Inventory Management (Receipt & Write-off) ---
from app.telegram.states.admin import ReceiptState, WriteOffState, BindBarcodeState
from app.telegram.keyboards.worker import worker_categories_kb, sell_product_list_kb

# Receipt Flow
@router.message(F.text == "📥 Приемка")
async def start_receipt(message: types.Message, state: FSMContext, container: Container):
    category_service: CategoryService = container.get("category_service")
    categories = await category_service.get_all_categories()
    if not categories:
        await message.answer("Сначала создайте категории!")
        return
    await state.set_state(ReceiptState.category_id)
    await message.answer("Выберите категорию для приемки:", reply_markup=worker_categories_kb(categories))

@router.callback_query(ReceiptState.category_id, F.data.startswith("w_cat_"))
async def receipt_select_cat(call: types.CallbackQuery, state: FSMContext, container: Container):
    cat_id = int(call.data.split("_")[2])
    await state.update_data(category_id=cat_id)
    product_service: ProductService = container.get("product_service")
    products = await product_service.get_products_by_category(cat_id)
    if not products:
        await call.answer("В этой категории нет товаров.", show_alert=True)
        return
    await state.set_state(ReceiptState.product_id)
    await call.message.edit_text("Выберите товар для приемки:", reply_markup=sell_product_list_kb(products))

@router.callback_query(ReceiptState.product_id, F.data.startswith("sell_"))
async def receipt_select_product(call: types.CallbackQuery, state: FSMContext, container: Container):
    product_id = int(call.data.split("_")[1])
    product_service: ProductService = container.get("product_service")
    product = await product_service.get_product_by_id(product_id)
    await state.update_data(product_id=product_id, product_name=product.name)
    await call.message.delete()
    await call.message.answer(f"📦 Приемка: *{product.name}*\nТекущий остаток: {product.quantity} шт.\n\nВведите количество для зачисления:", parse_mode="Markdown", reply_markup=cancel_kb())
    await state.set_state(ReceiptState.quantity)

@router.message(ReceiptState.quantity)
async def process_receipt_quantity(message: types.Message, state: FSMContext, container: Container, db_user: User):
    try:
        qty = int(message.text)
        if qty <= 0: raise ValueError()
    except ValueError:
        await message.answer("Введите положительное число.")
        return
    data = await state.get_data()
    transaction_service: TransactionService = container.get("transaction_service")
    await transaction_service.create_receipt(user_id=db_user.id, product_id=data['product_id'], amount=qty)
    await message.answer(f"✅ Успешно зачислено {qty} шт. товара *{data['product_name']}*.", parse_mode="Markdown", reply_markup=main_admin_kb())
    await state.clear()

# Write-off Flow
@router.message(F.text == "🗑 Списание")
async def start_write_off(message: types.Message, state: FSMContext, container: Container):
    category_service: CategoryService = container.get("category_service")
    categories = await category_service.get_all_categories()
    if not categories:
        await message.answer("Сначала создайте категории!")
        return
    await state.set_state(WriteOffState.category_id)
    await message.answer("Выберите категорию для списания:", reply_markup=worker_categories_kb(categories))

@router.callback_query(WriteOffState.category_id, F.data.startswith("w_cat_"))
async def write_off_select_cat(call: types.CallbackQuery, state: FSMContext, container: Container):
    cat_id = int(call.data.split("_")[2])
    await state.update_data(category_id=cat_id)
    product_service: ProductService = container.get("product_service")
    products = await product_service.get_products_by_category(cat_id)
    available = [p for p in products if p.quantity > 0]
    if not available:
        await call.answer("Нет доступных товаров для списания.", show_alert=True)
        return
    await state.set_state(WriteOffState.product_id)
    await call.message.edit_text("Выберите товар для списания:", reply_markup=sell_product_list_kb(available))

@router.callback_query(WriteOffState.product_id, F.data.startswith("sell_"))
async def write_off_select_product(call: types.CallbackQuery, state: FSMContext, container: Container):
    product_id = int(call.data.split("_")[1])
    product_service: ProductService = container.get("product_service")
    product = await product_service.get_product_by_id(product_id)
    await state.update_data(product_id=product_id, product_name=product.name, max_qty=product.quantity)
    await call.message.delete()
    await call.message.answer(f"🗑 Списание: *{product.name}*\nДоступно: {product.quantity} шт.\n\nВведите количество для списания:", parse_mode="Markdown", reply_markup=cancel_kb())
    await state.set_state(WriteOffState.quantity)

@router.message(WriteOffState.quantity)
async def process_write_off_quantity(message: types.Message, state: FSMContext):
    try:
        qty = int(message.text)
        if qty <= 0: raise ValueError()
    except ValueError:
        await message.answer("Введите положительное число.")
        return
    data = await state.get_data()
    if qty > data['max_qty']:
        await message.answer(f"Нельзя списать больше, чем есть на складе ({data['max_qty']}). Введите заново:")
        return
    await state.update_data(quantity=qty)
    await message.answer("Введите причину списания (например, 'брак', 'просрок'):", reply_markup=cancel_kb())
    await state.set_state(WriteOffState.reason)

@router.message(WriteOffState.reason)
async def process_write_off_reason(message: types.Message, state: FSMContext, container: Container, db_user: User):
    reason = message.text.strip()
    data = await state.get_data()
    transaction_service: TransactionService = container.get("transaction_service")
    await transaction_service.create_write_off(user_id=db_user.id, product_id=data['product_id'], amount=data['quantity'], reason=reason)
    await message.answer(f"✅ Успешно списано {data['quantity']} шт. товара *{data['product_name']}* по причине: {reason}", parse_mode="Markdown", reply_markup=main_admin_kb())
    await state.clear()

# --- Bind Barcode ---
@router.callback_query(F.data.startswith("prod_barcode_"))
async def cb_bind_barcode(call: types.CallbackQuery, state: FSMContext):
    product_id = int(call.data.split("_")[2])
    await state.update_data(product_id=product_id)
    await state.set_state(BindBarcodeState.barcode)
    await call.message.edit_text("Отправьте штрих-код товара (просто напишите цифры или отсканируйте камерой):")
    await call.message.answer("Или отмените действие:", reply_markup=cancel_kb())

@router.message(BindBarcodeState.barcode)
async def process_bind_barcode(message: types.Message, state: FSMContext, container: Container):
    barcode = message.text.strip()
    data = await state.get_data()
    product_service: ProductService = container.get("product_service")
    
    existing = await product_service.get_product_by_barcode(barcode)
    if existing and existing.id != data['product_id']:
        await message.answer("Этот штрихкодуже привязан к другому товару. Попробуйте другой:", reply_markup=cancel_kb())
        return
        
    success = await product_service.update_barcode(data['product_id'], barcode)
    if success:
        await message.answer(f"✅ Штрих-код {barcode} успешно привязан!", reply_markup=main_admin_kb())
    else:
        await message.answer("Ошибка при привязке штрих-кода.", reply_markup=main_admin_kb())
    await state.clear()

