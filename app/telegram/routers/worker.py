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
    await message.answer(f"Xodimlar paneliga xush kelibsiz, {db_user.username or db_user.tg_id}!", reply_markup=main_worker_kb())

@router.message(F.text == "Bekor qilish")
async def cancel_handler(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Amal bekor qilindi.", reply_markup=main_worker_kb())

@router.callback_query(F.data == "cancel_sale")
async def cancel_sale_cb(call: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.delete()
    await call.message.answer("Sotuvni rasmiylashtirish bekor qilindi.", reply_markup=main_worker_kb())

# --- Sell Logic ---
@router.message(F.text.regexp(r'^\d{8,14}$'))
async def process_scanned_barcode(message: types.Message, state: FSMContext, container: Container):
    barcode = message.text.strip()
    product_service: ProductService = container.get("product_service")
    product = await product_service.get_product_by_barcode(barcode)
    
    if not product:
        await message.answer(f"Shtrix-kod {barcode} bo'lgan mahsulot topilmadi.")
        return
        
    if product.quantity == 0:
        await message.answer(f"Mahsulot *{product.name}* topildi, ammo u omborda qolmagan (0 dona).", parse_mode="Markdown")
        return
        
    await state.update_data(product_id=product.id, max_qty=product.quantity, product_name=product.name, price=product.price)
    await message.answer(
        f"🔍 Mahsulot topildi: *{product.name}*\nOmborda: {product.quantity} dona.\n\nSotish miqdorini kiriting:",
        parse_mode="Markdown",
        reply_markup=cancel_worker_kb()
    )
    await state.set_state(SellState.amount)

@router.message(F.text == "🛒 Sotuvni rasmiylashtirish")
async def start_sell(message: types.Message, container: Container, state: FSMContext):
    category_service: CategoryService = container.get("category_service")
    categories = await category_service.get_all_categories()
    
    if not categories:
        await message.answer("Hozircha kategoriyalar yo'q. Sotuvni amalga oshirib bo'lmaydi.")
        return
        
    await state.set_state(SellState.category_id)
    await message.answer("Kategoriyani tanlang:", reply_markup=worker_categories_kb(categories))

@router.callback_query(SellState.category_id, F.data.startswith("w_cat_"))
async def process_sell_cat(call: types.CallbackQuery, state: FSMContext, container: Container):
    cat_id = int(call.data.split("_")[2])
    await state.update_data(category_id=cat_id)
    
    product_service: ProductService = container.get("product_service")
    products = await product_service.get_products_by_category(cat_id)
    
    available_products = [p for p in products if p.quantity > 0]
    
    if not available_products:
        await call.answer("Ushbu kategoriyada mavjud mahsulotlar yo'q.", show_alert=True)
        return
        
    await state.set_state(SellState.product_id)
    await call.message.edit_text("Sotish uchun mahsulotni tanlang:", reply_markup=sell_product_list_kb(available_products))

@router.callback_query(F.data == "back_to_w_cats")
async def process_back_to_w_cats(call: types.CallbackQuery, state: FSMContext, container: Container):
    from app.services.category_service import CategoryService
    from app.telegram.keyboards.worker import worker_categories_kb
    category_service: CategoryService = container.get("category_service")
    categories = await category_service.get_all_categories()
    await state.set_state(SellState.category_id)
    await call.message.edit_text("Kategoriyani tanlang:", reply_markup=worker_categories_kb(categories))

@router.callback_query(F.data.startswith("sell_"))
async def process_sell_product(call: types.CallbackQuery, state: FSMContext, container: Container):
    product_id = int(call.data.split("_")[1])
    product_service: ProductService = container.get("product_service")
    product = await product_service.get_product_by_id(product_id)
    
    if not product or product.quantity == 0:
        await call.answer("Ushbu mahsulot tugagan yoki o'chirilgan.", show_alert=True)
        # Edit markup
        products = await product_service.get_all_products()
        await call.message.edit_reply_markup(reply_markup=sell_product_list_kb(products))
        return
        
    await state.update_data(product_id=product_id, max_qty=product.quantity, product_name=product.name, price=product.price)
    await call.message.delete()
    await call.message.answer(
        f"Tanlangan mahsulot: *{product.name}*\nOmborda: {product.quantity} dona.\n\nSotish miqdorini kiriting:",
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
        await message.answer("Iltimos, to'g'ri musbat son kiriting.")
        return
        
    data = await state.get_data()
    max_qty = data['max_qty']
    
    cart = data.get('cart', [])
    already_in_cart = sum(item['amount'] for item in cart if item['product_id'] == data['product_id'])
    
    if amount + already_in_cart > max_qty:
        await message.answer(f"Xatolik! Omborda jami {max_qty} dona bor. Savatda esa {already_in_cart} dona. Miqdorni qayta kiriting:")
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
        f"✅ Mahsulot chekka qo'shildi.\nJami chekda: {len(cart)} ta mahsulot.\nKeyingi amalni tanlang?", 
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
    await call.message.edit_text("Kategoriyani tanlang:", reply_markup=worker_categories_kb(categories))

@router.callback_query(SellState.checkout_decision, F.data == "cart_checkout")
async def cart_checkout(call: types.CallbackQuery, state: FSMContext, container: Container, db_user: User):
    data = await state.get_data()
    cart = data.get('cart', [])
    if not cart:
        await call.answer("Savat bo'sh!", show_alert=True)
        return
        
    import uuid
    order_group_id = str(uuid.uuid4())
    
    transaction_service: TransactionService = container.get("transaction_service")
    
    transactions = await transaction_service.create_bulk_sale(
        user_id=db_user.id,
        items=cart,
        order_group_id=order_group_id
    )
            
    if not transactions:
        await call.message.edit_text("Rasmiylashtirishda xatolik. Ehtimol, tovarlar tugagan.")
        await state.clear()
        return
        
    total_rub = sum(tx.total_price for tx in transactions)
    total_qty = sum(tx.amount for tx in transactions)
    
    items_text_worker = "\n".join([f"• {tx.product.name} ({tx.amount} dona) - {tx.total_price} so'm" for tx in transactions])
    items_text_admin = "\n".join([f"• {tx.product.name} ({tx.amount} dona) - {tx.total_price} so'm" for tx in transactions])
    
    await call.message.edit_text(f"✅ Chek chiqarildi!\n\nMahsulotlar:\n{items_text_worker}\n\n*Jami:* {total_rub} so'm", parse_mode="Markdown")
    
    # Notify admin
    worker_name = call.from_user.full_name or call.from_user.username or str(db_user.tg_id)
    alert_text = f"💰 *Yangi sotuv (Chek)!*\n\nMahsulotlar:\n{items_text_admin}\n\nJami: {total_qty} dona.\nSumma: {total_rub} so'm\nXodim: {worker_name}"
    
    # Critical Stock Check for all products
    product_service: ProductService = container.get("product_service")
    for tx in transactions:
        prod_after = await product_service.get_product_by_id(tx.product_id)
        if prod_after and prod_after.quantity < 5:
            alert_text += f"\n\n⚠️ *Kritik qoldiq*\nOmborda {prod_after.name}: {prod_after.quantity} dona!"
            
    try:
        admin_ids = [int(x.strip()) for x in settings.ADMIN_IDS.split(",") if x.strip().isdigit()]
        for admin_id in admin_ids:
            try:
                await call.bot.send_message(admin_id, alert_text, parse_mode="Markdown", reply_markup=undo_tx_kb(transactions[0].id))
            except Exception:
                pass
    except Exception:
        pass
        
    await call.message.answer("Tanlang:", reply_markup=main_worker_kb())
    await state.clear()

# --- Worker Stats ---
@router.message(F.text == "📈 Mening savdo ko'rsatkichlarim")
async def worker_stats(message: types.Message, container: Container, db_user: User):
    transaction_service: TransactionService = container.get("transaction_service")
    sales = await transaction_service.get_worker_sales_today(user_id=db_user.id)
    
    if not sales:
        await message.answer("Bugun hali sotuvlar amalga oshirilmadi.")
        return
        
    total_items = sum(t.amount for t in sales)
    total_money = sum(t.total_price for t in sales)
    
    text = f"📈 *Bugungi savdo ko'rsatkichlaringiz:*\n\n"
    for t in sales:
        product_name = t.product.name if t.product else "O'chirilgan mahsulot"
        text += f"• {product_name} ({t.amount} dona) — {t.total_price} so'm\n"
        
    text += f"\n*Jami:* {total_items} ta mahsulot, {total_money} so'm.\n"
    
    if db_user.kpi > 0:
        progress = int(total_money / db_user.kpi * 100)
        text += f"\n🎯 *Kunlik reja (KPI):*\n"
        text += f"• Reja: {db_user.kpi} so'm\n"
        text += f"• Bajarildi: {total_money} so'm ({progress}%)\n"
    
    await message.answer(text, parse_mode="Markdown")
