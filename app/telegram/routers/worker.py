from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from app.database.models import User, UserRole
from app.container import Container

from app.services.product_service import ProductService
from app.services.transaction_service import TransactionService
from app.telegram.states.worker import SellState
from app.telegram.keyboards.worker import main_worker_kb, sell_product_list_kb, cancel_worker_kb
from app.config import settings

router = Router()

# This filter applies to all handlers in this router.
# Let's say WORKER can access this. Wait, can ADMIN also sell? Usually yes. 
# So we just filter for db_user is not None. 
# For now, let's allow everyone to do this (since admin might want to test the checkout)
router.message.filter(lambda msg, db_user: db_user is not None)
router.callback_query.filter(lambda call, db_user: db_user is not None)

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
@router.message(F.text == "🛒 Оформить продажу")
async def start_sell(message: types.Message, container: Container):
    product_service: ProductService = container.get("product_service")
    products = await product_service.get_all_products()
    
    # Filter out products with 0 stock
    available_products = [p for p in products if p.quantity > 0]
    
    if not available_products:
        await message.answer("Все товары распроданы или склад пуст.")
        return
        
    await message.answer("Выберите товар для продажи:", reply_markup=sell_product_list_kb(products))

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
        
    await state.update_data(product_id=product_id, max_qty=product.quantity, product_name=product.name)
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
    product_id = data['product_id']
    product_name = data['product_name']
    
    if amount > max_qty:
        await message.answer(f"Ошибка! Вы не можете продать больше, чем есть на складе ({max_qty} шт). Введите количество заново:")
        return
        
    transaction_service: TransactionService = container.get("transaction_service")
    transaction = await transaction_service.create_sale(user_id=db_user.id, product_id=product_id, amount=amount)
    
    if not transaction:
        await message.answer("Ошибка при оформлении продажи. Возможно, остаток уже изменился.", reply_markup=main_worker_kb())
        await state.clear()
        return
        
    await message.answer(f"✅ Успешно!\nПродано: {product_name} - {amount} шт.\nСумма: {transaction.total_price} руб.", reply_markup=main_worker_kb())
    await state.clear()
    
    # Notify admin
    bot = message.bot
    worker_name = message.from_user.full_name or message.from_user.username or str(db_user.tg_id)
    alert_text = f"💰 *Продажа!*\nТовар: {product_name}\nКол-во: {amount} шт.\nСумма: {transaction.total_price} руб.\nОформил: {worker_name}"
    
    product_service: ProductService = container.get("product_service")
    product_after_sale = await product_service.get_product_by_id(product_id)
    
    if product_after_sale and product_after_sale.quantity < 5:
        alert_text += f"\n\n⚠️ *Critical Stock Alert*\nОстаток {product_name} критически мал: {product_after_sale.quantity} шт!"
        
    try:
        await bot.send_message(settings.ADMIN_ID, alert_text, parse_mode="Markdown")
    except Exception as e:
        pass # Admin might not have started the bot, ignore for MVP

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
