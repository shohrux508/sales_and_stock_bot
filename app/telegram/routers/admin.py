from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from app.database.models import User, UserRole
from app.container import Container

from app.services.product_service import ProductService
from app.telegram.states.admin import AddProductState, WaitAdminReply
from app.telegram.keyboards.admin import main_admin_kb, products_list_kb, cancel_kb, product_edit_kb

router = Router()

# Filter for admin role only
# We can do this with a Custom Filter, but for simplicity we'll check inside or use F.role == UserRole.ADMIN
# Since db_user is passed to every handler, we can filter using it (Aiogram 3 allows checking kwargs in F-magic)
# However, the easiest way for now is a custom function or simple lambda.
router.message.filter(lambda msg, db_user: db_user is not None and db_user.role == UserRole.ADMIN)
router.callback_query.filter(lambda call, db_user: db_user is not None and db_user.role == UserRole.ADMIN)

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

# --- Add Product ---
@router.callback_query(F.data == "add_product")
async def start_add_product(call: types.CallbackQuery, state: FSMContext):
    await call.message.delete()
    await call.message.answer("Введите название нового товара:", reply_markup=cancel_kb())
    await state.set_state(AddProductState.name)

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
        await product_service.create_product(name=data['name'], price=data['price'], quantity=qty)
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

# Update start command for admin
@router.message(F.text == "/start")
async def admin_start(message: types.Message, db_user: User):
    await message.answer(f"Добро пожаловать в панель администратора, {db_user.username}!", reply_markup=main_admin_kb())

# --- Manage Staff ---
@router.message(F.text == "👥 Сотрудники")
async def show_staff(message: types.Message, container: Container):
    from app.services.user_service import UserService
    user_service: UserService = container.get("user_service")
    
    users = await user_service.get_all_users()
    workers = [u for u in users if u.role == UserRole.WORKER]
    
    if not workers:
        text = "Сотрудников пока нет."
    else:
        text = "👥 Список сотрудников:\n\n"
        for w in workers:
            text += f"• ID {w.tg_id} (@{w.username or 'без_юзернейма'})\n"
            
    # For now MVP only - admin can manage lists manually if needed.
    await message.answer(text, reply_markup=main_admin_kb())

# --- Statistics ---
@router.message(F.text == "📊 Статистика")
async def show_stats_menu(message: types.Message):
    from app.telegram.keyboards.admin import stats_periods_kb
    await message.answer("Выберите период для отчета:", reply_markup=stats_periods_kb())

@router.callback_query(F.data.startswith("stats_period_"))
async def process_stats(call: types.CallbackQuery, container: Container):
    period = call.data.split("_")[2] # "today" or "week"
    from app.services.transaction_service import TransactionService
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
    
    period_str = "сегодня" if period == "today" else "последние 7 дней"
    
    text = f"📊 *Статистика за {period_str}:*\n\n"
    text += f"Всего чеков: {total_sales}\n"
    text += f"Продано единиц: {total_items} шт.\n"
    text += f"Общая выручка: *{total_revenue} руб.*\n\n"
    
    text += "🏆 *Топ-3 продаваемых товаров:*\n"
    for rank, (p_name, stats) in enumerate(top_products, 1):
        text += f"{rank}. {p_name} — {stats['count']} шт. ({stats['revenue']} руб.)\n"
        
    await call.message.edit_text(text, parse_mode="Markdown")
