from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from app.database.models import User, UserRole
from app.container import Container

from app.services.product_service import ProductService
from app.services.transaction_service import TransactionService
from app.services.category_service import CategoryService

from app.telegram.states.worker import SellState
from app.telegram.keyboards.worker import main_worker_kb, sell_product_list_kb, cancel_worker_kb, worker_categories_kb
from app.telegram.keyboards.admin import undo_tx_kb
from app.config import settings

router = Router()

# This filter applies to all handlers in this router.
# Let's say WORKER can access this. Wait, can ADMIN also sell? Usually yes. 
# So we just filter for db_user is not None. 
# For now, let's allow everyone to do this (since admin might want to test the checkout)
router.message.filter(lambda event, db_user=None: db_user is not None)
router.callback_query.filter(lambda event, db_user=None: db_user is not None)

@router.message(F.text == "/start")
async def worker_start(message: types.Message, db_user: User):
    # If the user is admin, this might get intercepted by admin.py if it's registered first.
    # We will register admin router first.
    await message.answer(f"Добро пожаловать в панель сотрудника, {db_user.username or db_user.tg_id}!", reply_markup=main_worker_kb())

@router.message(F.text == "Отмена")
async def cancel_handler(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Действие отменено.", reply_markup=main_worker_kb())

@router.callback_query(F.data == "cancel_sale")
async def cancel_sale_cb(call: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.delete()
    await call.message.answer("Оформление продажи отменено.", reply_markup=main_worker_kb())

# --- Sell Logic ---
@router.message(F.text.regexp(r'^\d{8,14}$'))
async def process_scanned_barcode(message: types.Message, state: FSMContext, container: Container):
    barcode = message.text.strip()
    product_service: ProductService = container.get("product_service")
    product = await product_service.get_product_by_barcode(barcode)
    
    if not product:
        await message.answer(f"Товар со штрих-кодом {barcode} не найден.")
        return
        
    if product.quantity == 0:
        await message.answer(f"Товар *{product.name}* найден, но его нет в наличии (0 шт).", parse_mode="Markdown")
        return
        
    await state.update_data(product_id=product.id, max_qty=product.quantity, product_name=product.name, price=product.price)
    await message.answer(
        f"🔍 Найден товар: *{product.name}*\nДоступно: {product.quantity} шт.\n\nВведите количество для продажи:",
        parse_mode="Markdown",
        reply_markup=cancel_worker_kb()
    )
    await state.set_state(SellState.amount)

@router.message(F.text == "🛒 Оформить продажу")
async def start_sell(message: types.Message, container: Container, state: FSMContext):
    category_service: CategoryService = container.get("category_service")
    categories = await category_service.get_all_categories()
    
    if not categories:
        await message.answer("Категорий пока нет. Продажи недоступны.")
        return
        
    await state.set_state(SellState.category_id)
    await message.answer("Выберите категорию:", reply_markup=worker_categories_kb(categories))

@router.callback_query(SellState.category_id, F.data.startswith("w_cat_"))
async def process_sell_cat(call: types.CallbackQuery, state: FSMContext, container: Container):
    cat_id = int(call.data.split("_")[2])
    await state.update_data(category_id=cat_id)
    
    product_service: ProductService = container.get("product_service")
    products = await product_service.get_products_by_category(cat_id)
    
    available_products = [p for p in products if p.quantity > 0]
    
    if not available_products:
        await call.answer("В этой категории нет доступных товаров.", show_alert=True)
        return
        
    await state.set_state(SellState.product_id)
    await call.message.edit_text("Выберите товар для продажи:", reply_markup=sell_product_list_kb(available_products))

@router.callback_query(F.data == "back_to_w_cats")
async def process_back_to_w_cats(call: types.CallbackQuery, state: FSMContext, container: Container):
    from app.services.category_service import CategoryService
    from app.telegram.keyboards.worker import worker_categories_kb
    category_service: CategoryService = container.get("category_service")
    categories = await category_service.get_all_categories()
    await state.set_state(SellState.category_id)
    await call.message.edit_text("Выберите категорию:", reply_markup=worker_categories_kb(categories))

@router.callback_query(F.data.startswith("sell_"))
async def process_sell_product(call: types.CallbackQuery, state: FSMContext, container: Container):
    product_id = int(call.data.split("_")[1])
    product_service: ProductService = container.get("product_service")
    product = await product_service.get_product_by_id(product_id)
    
    if not product or product.quantity == 0:
        await call.answer("Этот товар закончился или удален.", show_alert=True)
        # Edit markup
        products = await product_service.get_all_products()
        await call.message.edit_reply_markup(reply_markup=sell_product_list_kb(products))
        return
        
    await state.update_data(product_id=product_id, max_qty=product.quantity, product_name=product.name, price=product.price)
    await call.message.delete()
    await call.message.answer(
        f"Выбран товар: *{product.name}*\nДоступно: {product.quantity} шт.\n\nВведите количество для продажи:",
        parse_mode="Markdown",
        reply_markup=cancel_worker_kb()
    )
    await state.set_state(SellState.amount)

@router.message(SellState.amount)
async def process_sell_amount(message: types.Message, state: FSMContext, container: Container, db_user: User):
    try:
        amount = int(message.text)
        if amount <= 0:
            raise ValueError()
    except ValueError:
        await message.answer("Пожалуйста, введите корректное положительное число.")
        return
        
    data = await state.get_data()
    max_qty = data['max_qty']
    
    cart = data.get('cart', [])
    already_in_cart = sum(item['amount'] for item in cart if item['product_id'] == data['product_id'])
    
    if amount + already_in_cart > max_qty:
        await message.answer(f"Ошибка! Всего на складе {max_qty} шт. В корзине уже {already_in_cart}. Введите количество заново:")
        return
        
    cart.append({
        'product_id': data['product_id'],
        'product_name': data['product_name'],
        'price': data.get('price', 0),
        'amount': amount
    })
    await state.update_data(cart=cart)
    
    from app.telegram.keyboards.worker import cart_decision_kb
    await message.answer(
        f"✅ Товар добавлен в чек.\nВсего в чеке: {len(cart)} позиций.\nЧто делаем дальше?", 
        reply_markup=cart_decision_kb()
    )
    await state.set_state(SellState.checkout_decision)

@router.callback_query(SellState.checkout_decision, F.data == "cart_add_more")
async def cart_add_more(call: types.CallbackQuery, state: FSMContext, container: Container):
    from app.services.category_service import CategoryService
    from app.telegram.keyboards.worker import worker_categories_kb
    category_service: CategoryService = container.get("category_service")
    categories = await category_service.get_all_categories()
    await state.set_state(SellState.category_id)
    await call.message.edit_text("Выберите категорию:", reply_markup=worker_categories_kb(categories))

@router.callback_query(SellState.checkout_decision, F.data == "cart_checkout")
async def cart_checkout(call: types.CallbackQuery, state: FSMContext, container: Container, db_user: User):
    data = await state.get_data()
    cart = data.get('cart', [])
    if not cart:
        await call.answer("Корзина пуста!", show_alert=True)
        return
        
    import uuid
    order_group_id = str(uuid.uuid4())
    
    transaction_service: TransactionService = container.get("transaction_service")
    transactions = []
    
    for item in cart:
        tx = await transaction_service.create_sale(
            user_id=db_user.id, 
            product_id=item['product_id'], 
            amount=item['amount'],
            order_group_id=order_group_id
        )
        if tx:
            transactions.append(tx)
            
    if not transactions:
        await call.message.edit_text("Ошибка при оформлении. Возможно, товары закончились.")
        await state.clear()
        return
        
    total_rub = sum(tx.total_price for tx in transactions)
    total_qty = sum(tx.amount for tx in transactions)
    
    items_text = "\n".join([f"• {tx.product.name} ({tx.amount} шт) - {tx.total_price} руб." for tx in transactions])
    
    await call.message.edit_text(f"✅ Чек пробит!\n\nТовары:\n{items_text}\n\n*Итого:* {total_rub} руб.", parse_mode="Markdown")
    
    # Notify admin
    worker_name = call.from_user.full_name or call.from_user.username or str(db_user.tg_id)
    alert_text = f"💰 *Новая продажа (Чек)!*\n\nТовары:\n{items_text}\n\nВсего: {total_qty} шт.\nСумма: {total_rub} руб.\nОформил: {worker_name}"
    
    # Critical Stock Check for all products
    product_service: ProductService = container.get("product_service")
    for tx in transactions:
        prod_after = await product_service.get_product_by_id(tx.product_id)
        if prod_after and prod_after.quantity < 5:
            alert_text += f"\n\n⚠️ *Critical Stock*\nОстаток {prod_after.name}: {prod_after.quantity} шт!"
            
    try:
        await call.bot.send_message(settings.ADMIN_ID, alert_text, parse_mode="Markdown", reply_markup=undo_tx_kb(transactions[0].id))
    except Exception:
        pass
        
    await call.message.answer("Выберите:", reply_markup=main_worker_kb())
    await state.clear()

# --- Worker Stats ---
@router.message(F.text == "📈 Мои продажи (смена)")
async def worker_stats(message: types.Message, container: Container, db_user: User):
    transaction_service: TransactionService = container.get("transaction_service")
    sales = await transaction_service.get_worker_sales_today(user_id=db_user.id)
    
    if not sales:
        await message.answer("За сегодня продаж пока нет.")
        return
        
    total_items = sum(t.amount for t in sales)
    total_money = sum(t.total_price for t in sales)
    
    text = f"📈 *Ваши продажи за сегодня:*\n\n"
    for t in sales:
        product_name = t.product.name if t.product else "Удаленный товар"
        text += f"• {product_name} ({t.amount} шт) — {t.total_price} руб.\n"
        
    text += f"\n*Итого:* {total_items} шт. на сумму {total_money} руб."
    
    await message.answer(text, parse_mode="Markdown")
