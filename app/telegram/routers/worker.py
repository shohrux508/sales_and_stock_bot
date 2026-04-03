from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from app.database.models import User, UserRole
from app.container import Container

from app.services.product_service import ProductService
from app.services.transaction_service import TransactionService
from app.services.category_service import CategoryService

from app.telegram.states.worker import SellState
from app.telegram.keyboards.worker import (
    main_worker_kb, sell_product_list_kb, cancel_inline_kb,
    worker_categories_kb, cart_decision_kb, after_checkout_kb,
    kpi_progress_bar
)
from app.telegram.keyboards.admin import undo_tx_kb
from app.config import settings

router = Router()

# This filter applies to all handlers in this router.
router.message.filter(lambda event, db_user=None: db_user is not None)
router.callback_query.filter(lambda event, db_user=None: db_user is not None)

@router.message(F.text == "/start")
async def worker_start(message: types.Message, db_user: User):
    await message.answer(f"Xodimlar paneliga xush kelibsiz, {db_user.username or db_user.tg_id}!", reply_markup=main_worker_kb())

@router.message(F.text == "Bekor qilish")
async def cancel_handler(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Amal bekor qilindi.", reply_markup=main_worker_kb())

@router.callback_query(F.data == "cancel_sale")
async def cancel_sale_cb(call: types.CallbackQuery, state: FSMContext):
    await state.clear()
    # Редактируем сообщение вместо удаления + нового
    try:
        await call.message.edit_text("❌ Sotuvni rasmiylashtirish bekor qilindi.")
    except Exception:
        await call.message.delete()
        await call.message.answer("❌ Sotuvni rasmiylashtirish bekor qilindi.", reply_markup=main_worker_kb())

# --- Quick New Sale (from inline button after checkout) ---
@router.callback_query(F.data == "quick_new_sale")
async def quick_new_sale(call: types.CallbackQuery, state: FSMContext, container: Container):
    """Быстрый старт новой продажи прямо из inline-кнопки после чека."""
    category_service: CategoryService = container.get("category_service")
    categories = await category_service.get_all_categories()
    
    if not categories:
        await call.answer("Hozircha kategoriyalar yo'q.", show_alert=True)
        return
    
    await state.set_state(SellState.category_id)
    await call.message.edit_text("Sotish uchun mahsulotni tanlang:\nKategoriyani tanlang:", reply_markup=worker_categories_kb(categories))

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
        await message.answer(f"Mahsulot <b>{product.name}</b> topildi, ammo u omborda qolmagan (0 dona).", parse_mode="HTML")
        return
        
    await state.update_data(product_id=product.id, max_qty=product.quantity, product_name=product.name, price=product.price)
    # Отправляем inline-кнопку отмены вместо ReplyKeyboard
    await message.answer(
        f"🔍 Mahsulot topildi: <b>{product.name}</b>\nOmborda: <b>{product.quantity}</b> dona.\n\nSotish miqdorini kiriting:",
        parse_mode="HTML",
        reply_markup=cancel_inline_kb()
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
        products = await product_service.get_all_products()
        await call.message.edit_reply_markup(reply_markup=sell_product_list_kb(products))
        return
        
    await state.update_data(product_id=product_id, max_qty=product.quantity, product_name=product.name, price=product.price)
    # Редактируем текущее сообщение + inline-отмена (нижнее меню остается!)
    await call.message.edit_text(
        f"📦 Tanlangan mahsulot: <b>{product.name}</b>\nOmborda: <b>{product.quantity}</b> dona.\n\nSotish miqdorini kiriting:",
        parse_mode="HTML",
        reply_markup=cancel_inline_kb()
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
    
    # Показываем содержимое корзины
    cart_text = "\n".join([f"• <b>{item['product_name']}</b> <i>({item['amount']} dona)</i>" for item in cart])
    total_sum = sum(item['price'] * item['amount'] for item in cart)
    
    msg = (
        f"✅ <b>Mahsulot savatga qo'shildi.</b>\n\n"
        f"📋 <b>Savat:</b>\n"
        f"<blockquote>{cart_text}</blockquote>\n"
        f"💰 <b>Jami:</b> {total_sum:,} so'm\n\n"
        f"Keyingi amalni tanlang?"
    )
    
    await message.answer(
        msg, 
        parse_mode="HTML",
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
    
    items_text_worker = "\n".join([f"• <b>{tx.product.name}</b> <i>({tx.amount} dona)</i> — {tx.total_price:,} so'm" for tx in transactions])
    items_text_admin = "\n".join([f"• <b>{tx.product.name}</b> <i>({tx.amount} dona)</i> — {tx.total_price:,} so'm" for tx in transactions])
    
    # Редактируем сообщение с чеком + кнопка "Новая продажа"
    msg_checkout = (
        f"✅ <b>Chek chiqarildi!</b>\n\n"
        f"📦 <b>Mahsulotlar:</b>\n"
        f"<blockquote>{items_text_worker}</blockquote>\n"
        f"💰 <b>Jami:</b> {total_rub:,} so'm"
    )
    await call.message.edit_text(
        msg_checkout,
        parse_mode="HTML",
        reply_markup=after_checkout_kb()
    )
    
    # --- TRIGGER PRINT ---
    worker_name = call.from_user.full_name or call.from_user.username or str(db_user.tg_id)
    
    from datetime import datetime
    print_data = {
        "order_id": order_group_id,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "worker_name": worker_name,
        "items": [
            {
                "name": tx.product.name,
                "quantity": tx.amount,
                "price": tx.product.price,
                "sum": tx.total_price
            } for tx in transactions
        ],
        "total_amount": total_rub,
        "currency": "UZS"
    }
    
    from app.api.printer_manager import PrinterConnectionManager
    printer_manager: PrinterConnectionManager = container.get("printer_manager")
    print_sent = await printer_manager.send_print_job(print_data)
    
    # Notify admin
    alert_text = (
        f"💰 <b>Yangi sotuv (Chek)!</b>\n\n"
        f"📦 <b>Mahsulotlar:</b>\n"
        f"<blockquote>{items_text_admin}</blockquote>\n"
        f"Jami: <b>{total_qty}</b> dona.\n"
        f"Summa: <b>{total_rub:,}</b> so'm\n"
        f"Xodim: <b>{worker_name}</b>"
    )
    
    # Critical Stock Check for all products
    product_service: ProductService = container.get("product_service")
    for tx in transactions:
        prod_after = await product_service.get_product_by_id(tx.product_id)
        if prod_after and prod_after.quantity < 5:
            alert_text += f"\n\n⚠️ <b>Kritik qoldiq</b>\nOmborda {prod_after.name}: {prod_after.quantity} dona!"
    
    # Статус печати для админа
    if print_sent:
        alert_text += "\n\n🖨️ <i>Chek printerga yuborildi.</i>"
    else:
        alert_text += "\n\n⚠️ <i>Printer ulanmagan. Chekni qo'lda chop etish mumkin.</i>"
            
    try:
        from app.telegram.keyboards.admin import undo_and_print_kb, print_retry_kb
        admin_ids = [int(x.strip()) for x in settings.ADMIN_IDS.split(",") if x.strip().isdigit()]
        for admin_id in admin_ids:
            try:
                kb = undo_and_print_kb(transactions[0].id, order_group_id)
                await call.bot.send_message(admin_id, alert_text, parse_mode="HTML", reply_markup=kb)
            except Exception:
                pass
    except Exception:
        pass
    
    # Не отправляем отдельного сообщения "Tanlang:" — нижнее меню уже на месте!
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
    
    text = f"📈 <b>Bugungi savdo ko'rsatkichlaringiz:</b>\n\n"
    sales_list = []
    for t in sales:
        product_name = t.product.name if t.product else "O'chirilgan mahsulot"
        sales_list.append(f"• <b>{product_name}</b> <i>({t.amount} dona)</i> — {t.total_price:,} so'm")
        
    text += f"<blockquote>{chr(10).join(sales_list)}</blockquote>\n"
    text += f"<b>Jami:</b> {total_items} ta mahsulot, {total_money:,} so'm.\n"
    
    if db_user.kpi > 0:
        progress_bar = kpi_progress_bar(total_money, db_user.kpi)
        text += f"\n🎯 <b>Kunlik reja (KPI):</b>\n"
        text += f"• Reja: <b>{db_user.kpi:,}</b> so'm\n"
        text += f"• Bajarildi: <b>{total_money:,}</b> so'm\n\n"
        text += f"{progress_bar}\n"
    
    await message.answer(text, parse_mode="HTML")
