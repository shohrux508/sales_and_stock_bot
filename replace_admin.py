import sys
import os

replacements = {
    '"📦 Склад"': '"📦 Ombor"',
    '"Склад пуст."': '"Ombor bo\'sh."',
    '"📦 Список товаров на складе:"': '"📦 Ombordagi mahsulotlar ro\'yxati:"',
    '"Отмена"': '"Bekor qilish"',
    '"Действие отменено."': '"Amal bekor qilindi."',
    '"🗂 Категории"': '"🗂 Kategoriyalar"',
    '"Категорий пока нет. Вы можете их добавить."': '"Kategoriyalar hozircha yo\'q. Ularni qo\'shishingiz mumkin."',
    '"Управление категориями:"': '"Kategoriyalarni boshqarish:"',
    '"Введите название новой категории:"': '"Yangi kategoriya nomini kiriting:"',
    '"Или нажмите \'Отмена\' для возврата."': '"Yoki qaytish uchun \'Bekor qilish\' tugmasini bosing."',
    'f"✅ Категория \'{category_name}\' успешно создана!"': 'f"✅ \'{category_name}\' kategoriyasi muvaffaqiyatli yaratildi!"',
    'f"❌ Ошибка: {e}"': 'f"❌ Xatolik: {e}"',
    'f"Управление категорией ID {cat_id} (в разработке)"': 'f"Kategoriya ID {cat_id} ni boshqarish (ishlanmoqda)"',
    '"Сначала создайте категорию (🗂 Категории)!"': '"Avvalo kategoriya yarating (🗂 Kategoriyalar)!"',
    '"Выберите категорию для нового товара:"': '"Yangi mahsulot uchun kategoriya tanlang:"',
    '"Отлично. Введите название нового товара:"': '"Ajoyib. Yangi mahsulot nomini kiriting:"',
    '"Или отправьте \'Отмена\'"': '"Yoki \'Bekor qilish\' ni yuboring"',
    '"Введите цену товара (число):"': '"Mahsulot narxini kiriting (raqam):"',
    '"Пожалуйста, введите корректное число для цены."': '"Iltimos, narx uchun to\'g\'ri raqam kiriting."',
    '"Введите начальное количество на складе:"': '"Ombordagi boshlang\'ich miqdorni kiriting:"',
    '"Пожалуйста, введите целое число."': '"Iltimos, butun son kiriting."',
    'f"✅ Товар \'{data[\'name\']}\' добавлен!"': 'f"✅ \'{data[\'name\']}\' mahsuloti qo\'shildi!"',
    '"❌ Ошибка при добавлении в БД. Возможно, товар с таким именем уже существует."': '"❌ MBga qo\'shishda xatolik. Ehtimol bunday nomdagi mahsulot mavjud."',
    'f"📦 Товар: *{product.name}*\\nЦена: {product.price}\\nОстаток: {product.quantity}"': 'f"📦 Mahsulot: *{product.name}*\\nNarx: {product.price}\\nQoldiq: {product.quantity}"',
    'f"📦 Товар: *{new_product.name}*\\nЦена: {new_product.price}\\nОстаток: {new_product.quantity}"': 'f"📦 Mahsulot: *{new_product.name}*\\nNarx: {new_product.price}\\nQoldiq: {new_product.quantity}"',
    '"Товар не найден"': '"Mahsulot topilmadi"',
    '"Нельзя уменьшить (остаток 0 или товар не найден)"': '"Kamaytirib bo\'lmaydi (qoldiq 0 yoki mahsulot topilmadi)"',
    'f"⚠️ Вы уверены, что хотите удалить товар *{product.name}*?\\nЭто действие нельзя отменить."': 'f"⚠️ *{product.name}* mahsulotini o\'chirishga ishonchingiz komilmi?\\nBu amalni ortga qaytarib bo\'lmaydi."',
    '"Товар удален"': '"Mahsulot o\'chirildi"',
    '"Ошибка при удалении"': '"O\'chirishda xatolik"',
    'f"Добро пожаловать в панель администратора, {db_user.username}!"': 'f"Administrator paneliga xush kelibsiz, {db_user.username}!"',
    'f"✅ Пользователь @{updated_user.username or user_id} получил доступ (WORKER)."': 'f"✅ @{updated_user.username or user_id} foydalanuvchisi ruxsat oldi (WORKER)."',
    '"🎉 Ваша заявка одобрена! Теперь вам доступно меню сотрудника.\\nНажмите /start."': '"🎉 Sizning so\'rovingiz tasdiqlandi! Endi sizga xodim menyusi ruxsat etildi.\\n/start tugmasini bosing."',
    '"Ошибка при обновлении роли"': '"Rolni yangilashda xatolik"',
    'f"⛔ Пользователь @{updated_user.username or user_id} отклонен (BANNED)."': 'f"⛔ @{updated_user.username or user_id} foydalanuvchi rad etildi (BANNED)."',
    '"👥 Сотрудники"': '"👥 Xodimlar"',
    '"Сотрудников и заявок пока нет."': '"Xodimlar va so\'rovlar hozircha yo\'q."',
    '"👥 Выберите сотрудника или кандидата для управления:"': '"👥 Boshqarish uchun xodim yoki nomzodni tanlang:"',
    '"Пользователь не найден."': '"Foydalanuvchi topilmadi."',
    '"✅ Активен"': '"✅ Faol"',
    '"⛔ Заблокирован"': '"⛔ Bloklangan"',
    '"⏳ Ожидает одобрения"': '"⏳ Tasdiqlash kutilmoqda"',
    'f"👤 *Профиль:* {full_name}\\n\\n" \\': 'f"👤 *Profil:* {full_name}\\n\\n" \\',
    'f"• Телефон: {escape_md(user.phone)}\\n" \\': 'f"• Telefon: {escape_md(user.phone)}\\n" \\',
    'f"• Роль: {user.role.value}\\n" \\': 'f"• Rol: {user.role.value}\\n" \\',
    'f"• Статус: {status}\\n" \\': 'f"• Holat: {status}\\n" \\',
    'f"• Регистрация: {user.joined_at.strftime(\'%Y-%m-%d\') if user.joined_at else \'---\'}\\n\\n" \\': 'f"• Ro\'yxatdan o\'tgan: {user.joined_at.strftime(\'%Y-%m-%d\') if user.joined_at else \'---\'}\\n\\n" \\',
    'f"🎯 *KPI на сегодня:*\\n" \\': 'f"🎯 *Bugungi KPI:*\\n" \\',
    'f"• Цель: {user.kpi} руб.\\n" \\': 'f"• Maqsad: {user.kpi} so\'m.\\n" \\',
    'f"• Выручка: {round(revenue_today, 2)} руб.\\n" \\': 'f"• Daromad: {round(revenue_today, 2)} so\'m.\\n" \\',
    'f"• Прогресс: {min(100, int(revenue_today/user.kpi*100)) if user.kpi > 0 else 0}%\\n\\n" \\': 'f"• Jarayon: {min(100, int(revenue_today/user.kpi*100)) if user.kpi > 0 else 0}%\\n\\n" \\',
    'f"Выберите действие:"': 'f"Amalni tanlang:"',
    '"Введите ФИО сотрудника:"': '"Xodim F.I.Sh ni kiriting:"',
    '"Или нажмите \'Отмена\'"': '"Yoki \'Bekor qilish\' ni bosing"',
    'f"✅ ФИО обновлено!"': 'f"✅ F.I.Sh yangilandi!"',
    '"Введите номер телефона сотрудника:"': '"Xodim telefon raqamini kiriting:"',
    'f"✅ Телефон обновлен!"': 'f"✅ Telefon yangilandi!"',
    '"Введите новый KPI (целевое значение в рублях или штуках):"': '"Yangi KPI kiriting (so\'m yoki donada maqsadli qiymat):"',
    'f"✅ KPI успешно обновлен до {new_kpi}!"': 'f"✅ KPI muvaffaqiyatli {new_kpi} gacha yangilandi!"',
    '"❌ Ошибка при обновлении KPI."': '"❌ KPI yangilashda xatolik."',
    '"🗑 Сотрудник удален из активного списка. (Чтобы вернуть его, он должен нажать /start)"': '"🗑 Xodim faol ro\'yxatdan o\'chirildi. (Uni qaytarish uchun u /start bosishi kerak)"',
    '"Ваш профиль был удален администратором. Ваш доступ закрыт."': '"Profilingiz administrator tomonidan o\'chirildi. Ruxsatingiz yopilgan."',
    '"Ошибка"': '"Xatolik"',
    '"Нет транзакций за этот период"': '"Bu davrda tranzaksiyalar yo\'q"',
    '"Продажи"': '"Sotuvlar"',
    '["ID чека", "Дата/Время (UTC)", "Категория", "Товар", "Кол-во", "Сумма (руб)"]': '["Chek ID", "Sana/Vaqt (UTC)", "Kategoriya", "Mahsulot", "Miqdor", "Summa (so\'m)"]',
    '["ID чека", "Дата/Время (UTC)", "Сотрудник", "Категория", "Товар", "Кол-во", "Сумма (руб)"]': '["Chek ID", "Sana/Vaqt (UTC)", "Xodim", "Kategoriya", "Mahsulot", "Miqdor", "Summa (so\'m)"]',
    '"Удален"': '"O\'chirilgan"',
    '"Не указана"': '"Ko\'rsatilmagan"',
    'f"📥 Отчет по сотруднику @{user.username or tg_id} готов!"': 'f"📥 @{user.username or tg_id} xodimi bo\'yicha hisobot tayyor!"',
    '"📊 Статистика"': '"📊 Statistika"',
    '"Выберите период для отчета:"': '"Hisobot davrini tanlang:"',
    '"За этот период продаж не было."': '"Bu davrda sotuvlar bo\'lmagan."',
    'f"📊 *Статистика за {period_str}:*\\n\\n"': 'f"📊 *{period_str} statistikasi:*\\n\\n"',
    'f"Всего чеков: {total_sales}\\n"': 'f"Jami cheklar: {total_sales}\\n"',
    'f"Продано единиц: {total_items} шт.\\n"': 'f"Sotilgan mahsulotlar: {total_items} dona.\\n"',
    'f"Общая выручка: *{total_revenue} руб.*\\n\\n"': 'f"Umumiy daromad: *{total_revenue} so\'m.*\\n\\n"',
    '"🏆 *Топ-3 продаваемых товаров:*\\n"': '"🏆 *Eng ko\'p sotilgan Top-3 mahsulot:*\\n"',
    'f"{rank}. {p_name} — {stats[\'count\']} шт. ({stats[\'revenue\']} руб.)\\n"': 'f"{rank}. {p_name} — {stats[\'count\']} dona. ({stats[\'revenue\']} so\'m)\\n"',
    '"\\n👥 *Рейтинг сотрудников:*\\n"': '"\\n👥 *Xodimlar reytingi:*\\n"',
    'f"{i}. {name} — {rank.revenue} руб. ({rank.items} ед.)\\n"': 'f"{i}. {name} — {rank.revenue} so\'m. ({rank.items} dona.)\\n"',
    '"сегодня"': '"bugun"',
    '"последние 7 дней"': '"so\'nggi 7 kun"',
    '"Детали неизвестны"': '"Tafsilotlar noma\'lum"',
    'f"❌ *Транзакция отменена. Товар возвращен на склад.*\\n\\n~~{original_text}~~"': 'f"❌ *Tranzaksiya bekor qilindi. Mahsulot omborga qaytarildi.*\\n\\n~~{original_text}~~"',
    '"Возврат оформлен!"': '"Qaytarish rasmiylashtirildi!"',
    '"📥 Ваш Excel-отчет готов!"': '"📥 Sizning Excel hisobotingiz tayyor!"',
    '"На складе нет товаров."': '"Omborda mahsulotlar yo\'q."',
    '["ID", "Категория", "Наименование", "Цена", "Остаток", "Штрихкод"]': '["ID", "Kategoriya", "Nomi", "Narx", "Qoldiq", "Shtrix-kod"]',
    '"Без категории"': '"Kategoriyasiz"',
    '"📦 Актуальный отчет по остаткам на складе готов!"': '"📦 Ombordagi qoldiqlar bo\'yicha joriy hisobot tayyor!"',
    '"📥 Приемка"': '"📥 Qabul qilish"',
    '"Сначала создайте категории!"': '"Avvalo kategoriyalarni yarating!"',
    '"Выберите категорию для приемки:"': '"Qabul qilish uchun kategoriyani tanlang:"',
    '"В этой категории нет товаров."': '"Bu kategoriyada mahsulotlar yo\'q."',
    '"Выберите товар для приемки:"': '"Qabul qilish uchun mahsulotni tanlang:"',
    'f"📦 Приемка: *{product.name}*\\nТекущий остаток: {product.quantity} шт.\\n\\nВведите количество для зачисления:"': 'f"📦 Qabul qilish: *{product.name}*\\nJoriy qoldiq: {product.quantity} dona.\\n\\nKirim miqdorini kiriting:"',
    '"Введите положительное число."': '"Musbat son kiriting."',
    'f"✅ Успешно зачислено {qty} шт. товара *{data[\'product_name\']}*."': 'f"✅ *{data[\'product_name\']}* mahsulotidan {qty} dona muvaffaqiyatli qabul qilindi."',
    '"🗑 Списание"': '"🗑 Hisobdan chiqarish"',
    '"Выберите категорию для списания:"': '"Hisobdan chiqarish uchun kategoriyani tanlang:"',
    '"Нет доступных товаров для списания."': '"Hisobdan chiqarish uchun mavjud mahsulotlar yo\'q."',
    '"Выберите товар для списания:"': '"Hisobdan chiqarish uchun mahsulotni tanlang:"',
    'f"🗑 Списание: *{product.name}*\\nДоступно: {product.quantity} шт.\\n\\nВведите количество для списания:"': 'f"🗑 Hisobdan chiqarish: *{product.name}*\\nMavjud: {product.quantity} dona.\\n\\nHisobdan chiqarish miqdorini kiriting:"',
    'f"Нельзя списать больше, чем есть на складе ({data[\'max_qty\']}). Введите заново:"': 'f"Ombordagidan ({data[\'max_qty\']}) ko\'prog\'ini hisobdan chiqarib bo\'lmaydi. Qaytadan kiriting:"',
    '"Введите причину списания (например, \'брак\', \'просрок\'):"': """ "Hisobdan chiqarish sababini kiriting (masalan, 'yaroqsiz', 'muddati o'tgan'):" """,
    'f"✅ Успешно списано {data[\'quantity\']} шт. товара *{data[\'product_name\']}* по причине: {reason}"': 'f"✅ *{data[\'product_name\']}* mahsulotidan {data[\'quantity\']} dona muvaffaqiyatli hisobdan chiqarildi, sabab: {reason}"',
    '"Отправьте штрих-код товара (просто напишите цифры или отсканируйте камерой):"': '"Mahsulot shtrix-kodini yuboring (raqamlarni yozing yoki kamera yordamida skanerlang):"',
    '"Или отмените действие:"': '"Yoki amalni bekor qiling:"',
    '"Этот штрихкодуже привязан к другому товару. Попробуйте другой:"': '"Bu shtrix-kod boshqa mahsulotga biriktirilgan. Boshqasini sinab ko\'ring:"',
    'f"✅ Штрих-код {barcode} успешно привязан!"': 'f"✅ Shtrix-kod {barcode} muvaffaqiyatli biriktirildi!"',
    '"Ошибка при привязке штрих-кода."': '"Shtrix-kod biriktirishda xatolik."'
}

target_file = r"c:\Antigravity\projects\sales_and_stock_bot\app\telegram\routers\admin.py"

with open(target_file, "r", encoding="utf-8") as f:
    content = f.read()

for k, v in replacements.items():
    content = content.replace(k, v)

with open(target_file, "w", encoding="utf-8") as f:
    f.write(content)

# Worker replacements
worker_replacements = {
    'items_text_admin = "\\n".join([f"• {tx.product.name} ({tx.amount} шт) - {tx.total_price} руб" for tx in transactions])': 'items_text_admin = "\\n".join([f"• {tx.product.name} ({tx.amount} dona) - {tx.total_price} so\'m" for tx in transactions])',
    'alert_text = f"💰 *Новая продажа (Чек)!*\\n\\nТовары:\\n{items_text_admin}\\n\\nИтого: {total_qty} шт.\\nСумма: {total_rub} руб\\nСотрудник: {worker_name}"': 'alert_text = f"💰 *Yangi sotuv (Chek)!*\\n\\nMahsulotlar:\\n{items_text_admin}\\n\\nJami: {total_qty} dona.\\nSumma: {total_rub} so\'m\\nXodim: {worker_name}"',
    'alert_text += f"\\n\\n⚠️ *Critical Stock*\\nОстаток {prod_after.name}: {prod_after.quantity} шт!"': 'alert_text += f"\\n\\n⚠️ *Kritik qoldiq*\\nOmborda {prod_after.name}: {prod_after.quantity} dona!"'
}

worker_file = r"c:\Antigravity\projects\sales_and_stock_bot\app\telegram\routers\worker.py"
with open(worker_file, "r", encoding="utf-8") as f:
    w_content = f.read()

for k, v in worker_replacements.items():
    w_content = w_content.replace(k, v)

with open(worker_file, "w", encoding="utf-8") as f:
    f.write(w_content)
