<![CDATA[<div align="center">

# 📦 Sales & Stock Bot

### Telegram-бот для автоматизации учёта товаров, продаж и печати чеков

![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Aiogram](https://img.shields.io/badge/Aiogram-3.x-0088CC?style=for-the-badge&logo=telegram&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.135-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-D71F00?style=for-the-badge&logo=sqlalchemy&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-7.4-DC382D?style=for-the-badge&logo=redis&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![Railway](https://img.shields.io/badge/Railway-Deployed-0B0D0E?style=for-the-badge&logo=railway&logoColor=white)
![Tests](https://img.shields.io/badge/Tests-pytest-FFDD57?style=for-the-badge&logo=pytest&logoColor=black)

---

**Полнофункциональная бизнес-система** для управления складом, фиксации продаж сотрудниками и оперативного контроля администратором — через Telegram-бот, REST API и Web Dashboard с автоматической печатью товарных чеков на термопринтере.

[Возможности](#-возможности) •
[Быстрый старт](#-быстрый-старт) •
[Деплой](#-деплой) •
[API](#-api-эндпоинты) •
[Печать чеков](#-настройка-печати-чеков-xprinter) •
[Тесты](#-тестирование) •
[FAQ](#-faq)

</div>

---

## 📋 Оглавление

- [Возможности](#-возможности)
  - [V1 → Ядро системы](#v1--ядро-системы)
  - [V2 → Архитектурные фичи](#v2--архитектурные-фичи)
  - [V3 → Бизнес-логика](#v3--бизнес-логика)
  - [V4 → Автоматическая печать чеков](#v4--автоматическая-печать-чеков)
- [Архитектура](#-архитектура)
- [Ролевая модель](#-ролевая-модель)
- [Технологический стек](#-технологический-стек)
- [Структура проекта](#-структура-проекта)
- [Быстрый старт](#-быстрый-старт)
- [Переменные окружения](#-переменные-окружения)
- [Деплой](#-деплой)
- [API эндпоинты](#-api-эндпоинты)
- [База данных](#-база-данных)
- [Настройка печати чеков](#-настройка-печати-чеков-xprinter)
- [Web Dashboard](#-web-dashboard)
- [Тестирование](#-тестирование)
- [CI/CD](#-cicd)
- [Бэкап базы данных](#-бэкап-базы-данных)
- [Логирование](#-логирование)
- [Безопасность](#-безопасность)
- [FAQ](#-faq)
- [Лицензия](#-лицензия)

---

## 🚀 Возможности

### V1 — Ядро системы

Базовый функционал Telegram-бота для учёта склада и продаж:

| Функция | Описание |
|---------|----------|
| 📦 Управление товарами | Добавление, редактирование, удаление товаров через FSM |
| 💰 Продажи | Пошаговое оформление продаж сотрудниками |
| 📊 Статистика | Просмотр продаж за день/неделю в боте |
| ⚠️ Алерты | Critical Stock Alert — уведомление при остатке < 5 шт. |

### V2 — Архитектурные фичи

5 крупных функциональных блоков:

| Функция | Описание |
|---------|----------|
| 🔐 **Премодерация (White List)** | Новый пользователь → статус `PENDING` → заявка администратору → `[✅ Одобрить]` / `[⛔ Отклонить]` |
| 🗂 **Категории товаров** | Группировка товаров по категориям; при продаже: Категория → Товар → Количество |
| ⏪ **Откат продаж (Rollback)** | Кнопка `[❌ Отменить]` под уведомлением о продаже. Атомарное восстановление остатков |
| 📥 **Экспорт в Excel** | Генерация XLSX прямо в оперативной памяти через `openpyxl`. Отправка файла в чат |
| 🌐 **Web Dashboard** | Telegram WebApp — Chart.js графики, Топ-5 сотрудников, auto-refresh каждые 10 сек |

### V3 — Бизнес-логика

Реальные складские и торговые процессы:

| Функция | Описание |
|---------|----------|
| 📥 **Приёмка товара** | Отдельный бизнес-процесс поступления (+) с регистрацией в `TransactionType.RECEIPT` |
| 🗑 **Списание / Брак** | Списание (-) с обязательным указанием причины. `TransactionType.WRITE_OFF` |
| 🛒 **Мульти-корзина** | Несколько товаров в одном заказе, объединённых `order_group_id` (UUID) |
| 🏷 **Штрих-коды** | Привязка уникального баркода к товару. Сканирование → мгновенный переход к продаже |

### V4 — Автоматическая печать чеков

Мгновенная печать на термопринтере Xprinter:

| Функция | Описание |
|---------|----------|
| 🖨️ **Автопечать** | При продаже — чек мгновенно на принтер через WebSocket (Cloud → Local) |
| 📡 **WebSocket-канал** | Защищённый эндпоинт `/ws/printer/{secret_token}`, авто-переподключение каждые 5 сек |
| 🔄 **Redis-дедупликация** | Один `order_id` не печатается дважды (TTL 24 часа) |
| 📋 **Очередь чеков** | Если принтер offline — чек в Redis-очередь (до 100 шт., TTL 7 дней) |
| 🔘 **Ручная печать** | Кнопка `🖨️ Chekni chop etish` в Telegram-уведомлении о продаже |

---

## 🏗 Архитектура

```
┌──────────────────────────────────────────────────────────┐
│                    ОБЛАКО (Railway)                       │
│                                                          │
│  ┌─────────────┐   ┌──────────────┐   ┌──────────────┐  │
│  │  Telegram    │   │   FastAPI     │   │   Redis      │  │
│  │  Bot (Aiogram│◄─►│   Server     │◄─►│   (FSM +     │  │
│  │  3.x + FSM) │   │  (Uvicorn)   │   │  Dedup)      │  │
│  └──────┬───────┘   └──────┬───────┘   └──────────────┘  │
│         │                  │                              │
│         │      ┌───────────┼─────────────┐               │
│         │      │           │             │               │
│  ┌──────▼──────▼───┐  ┌───▼──────┐  ┌───▼──────────┐    │
│  │  Service Layer   │  │ REST API │  │ WebSocket    │    │
│  │  (Transaction,   │  │ /api/*   │  │ /ws/printer/ │    │
│  │   Product,       │  └──────────┘  └──────┬───────┘    │
│  │   User, Category)│                       │            │
│  └────────┬─────────┘                       │            │
│           │                                 │            │
│  ┌────────▼─────────┐                       │            │
│  │  PostgreSQL       │                       │            │
│  │  (asyncpg)        │                       │            │
│  └──────────────────┘                       │            │
└─────────────────────────────────────────────┼────────────┘
                                              │ WebSocket
                                              │ (wss://)
┌─────────────────────────────────────────────▼────────────┐
│               ЛОКАЛЬНЫЙ ПК (Магазин)                     │
│                                                          │
│  ┌──────────────────┐   ┌──────────────────┐             │
│  │  printer_client/  │──►│  Xprinter        │             │
│  │  (WebSocket +     │   │  (USB / Windows  │             │
│  │   ESC/POS)        │   │   RAW Print)     │             │
│  └──────────────────┘   └──────────────────┘             │
└──────────────────────────────────────────────────────────┘
```

### Ключевые архитектурные решения

| Решение | Обоснование |
|---------|-------------|
| **DI-контейнер** | Собственный `Container` класс — регистрация/резолвинг сервисов без фреймворков |
| **Слоистая архитектура** | `Models → Services → Handlers/Routers` — строгое разделение ответственности |
| **Асинхронность** | Весь I/O через `asyncio` — `asyncpg`, `aiosqlite`, `redis.asyncio`, Aiogram 3.x |
| **Atomic Transactions** | `UPDATE ... WHERE quantity >= amount RETURNING` — race-condition-safe операции |
| **Timezone-aware** | Все `datetime` в UTC; статистика конвертируется в UZT (UTC+5) для фильтрации |

---

## 🎭 Ролевая модель

### 👑 Администратор (`ADMIN`)

Определяется по `ADMIN_IDS` в `.env`. Автоматически повышается при первом контакте.

| Возможность | Описание |
|-------------|----------|
| 📦 Товары | Добавление, редактирование (название, цена, остаток, штрихкод), удаление |
| 🗂 Категории | Создание, просмотр, удаление категорий |
| 📥 Приёмка | Поступление товара с записью в журнал операций |
| 🗑 Списание | Списание товара с указанием причины |
| 📊 Статистика | Отчёты за день/неделю + выгрузка Excel |
| ❌ Rollback | Отмена любой продажи с восстановлением остатков |
| 👥 Персонал | Одобрение/блокировка сотрудников, редактирование профилей, KPI |
| 🌐 Dashboard | Web-интерфейс с графиками и рейтингом сотрудников |
| 🖨️ Печать | Ручная отправка чеков на принтер через кнопку |

### 👷 Сотрудник (`WORKER`)

Получает доступ только после одобрения администратором.

| Возможность | Описание |
|-------------|----------|
| 🛒 Продажа | Категория → Товар → Количество (с защитой от overselling) |
| 🛒 Корзина | Добавление нескольких товаров в один чек |
| 🏷 Штрихкод | Сканирование штрихкода → мгновенный переход к продаже |
| 📊 Моя смена | Личная статистика продаж за текущий день |

### ⏳ Ожидающий (`PENDING`)

Новый пользователь, нажавший `/start`. Не имеет доступа к функционалу до одобрения.

### 🚫 Заблокированный (`BANNED`)

Отклонённый пользователь. Может отправить повторный запрос через `/start`.

---

## 🛠 Технологический стек

### Backend

| Технология | Версия | Назначение |
|-----------|--------|-----------|
| Python | 3.12+ | Основной язык |
| Aiogram | 3.26.0 | Telegram Bot Framework (асинхронный) |
| FastAPI | 0.135.1 | REST API + WebSocket + отдача WebApp |
| Uvicorn | 0.42.0 | ASGI-сервер |
| SQLAlchemy | 2.0.48 | ORM (Strict Asyncio, 2.0 style) |
| Alembic | 1.18.4 | Миграции базы данных |
| asyncpg | 0.31.0 | Асинхронный PostgreSQL-драйвер |
| aiosqlite | 0.22.1 | Асинхронный SQLite-драйвер (fallback) |
| Redis | 7.4.0 | FSM-хранилище + дедупликация чеков + очередь |
| Pydantic Settings | 2.13.1 | Типизированная конфигурация из `.env` |
| Loguru | 0.7.3 | Структурированное логирование с ротацией |
| openpyxl | 3.1.5 | Генерация Excel-отчётов |
| websockets | 16.0 | WebSocket-клиент для принтера |

### Frontend

| Технология | Назначение |
|-----------|-----------|
| HTML5 / CSS3 / JavaScript | Web Dashboard (Single Page) |
| Chart.js | Интерактивные графики (Pie, Bar) |
| Glassmorphism | Премиальный UI-дизайн |
| Plus Jakarta Sans | Типографика |

### Инфраструктура

| Технология | Назначение |
|-----------|-----------|
| Docker | Контейнеризация приложения |
| Docker Compose | Оркестрация локально |
| Railway | Облачный хостинг (PostgreSQL + Redis + App) |
| GitHub Actions | CI/CD pipeline (`pytest --cov`) |

### Принтер-клиент (Локальный ПК)

| Технология | Назначение |
|-----------|-----------|
| websockets | WebSocket-подключение к серверу |
| python-escpos | ESC/POS команды для USB-принтеров |
| pywin32 | Печать через стандартный Windows-драйвер |

---

## 📂 Структура проекта

```
sales_and_stock_bot/
│
├── main.py                          # 🚀 Точка входа (asyncio.run)
├── requirements.txt                 # 📦 Зависимости сервера (18 пакетов)
├── Dockerfile                       # 🐳 Docker-образ (python:3.12-slim)
├── docker-compose.yml               # 🐳 Оркестрация с volume для данных
├── entrypoint.sh                    # 🐳 Авто-миграции + запуск приложения
├── alembic.ini                      # 🔧 Конфигурация Alembic
├── pytest.ini                       # 🧪 Конфигурация pytest (asyncio_mode=auto)
├── .env.example                     # 📄 Шаблон переменных окружения
├── .gitignore                       # Git — исключения (.env, .venv, *.db, etc.)
├── .dockerignore                    # Docker — исключения (tests, printer_client)
│
├── app/                             # ═══ ЯДРО ПРИЛОЖЕНИЯ ═══
│   ├── app.py                       # 🔧 Класс App — сборка и запуск всех модулей
│   ├── config.py                    # ⚙️  Pydantic Settings (чтение .env)
│   ├── container.py                 # 💉 DI-контейнер (register / get / resolve)
│   ├── logger.py                    # 📝 Loguru + InterceptHandler (ротация 10MB)
│   │
│   ├── database/                    # 💾 Слой данных
│   │   ├── core.py                  #     Engine, SessionMaker, Base, NamingConvention
│   │   └── models.py               #     User, Category, Product, Transaction + Enums
│   │
│   ├── services/                    # 📋 Бизнес-логика
│   │   ├── user_service.py          #     CRUD пользователей, роли, get_or_create
│   │   ├── product_service.py       #     CRUD товаров, поиск по штрихкоду
│   │   ├── category_service.py      #     CRUD категорий
│   │   └── transaction_service.py   #     Продажи, приёмка, списание, откат, статистика
│   │
│   ├── telegram/                    # 🤖 Telegram-бот
│   │   ├── bot.py                   #     Создание Bot + Dispatcher + Redis FSM Storage
│   │   ├── routers/
│   │   │   ├── admin.py             #     Хендлеры администратора (~900 строк)
│   │   │   └── worker.py            #     Хендлеры сотрудника (продажи + корзина)
│   │   ├── keyboards/
│   │   │   ├── admin.py             #     Reply + Inline клавиатуры админа
│   │   │   └── worker.py            #     Reply + Inline клавиатуры сотрудника
│   │   ├── states/
│   │   │   ├── admin.py             #     FSM: AddProduct, Receipt, WriteOff, BindBarcode...
│   │   │   └── worker.py            #     FSM: SellState (корзина)
│   │   └── middlewares/
│   │       └── auth.py              #     AuthMiddleware — ролевое разграничение + авторег
│   │
│   └── api/                         # 🌐 FastAPI
│       ├── server.py                #     Создание FastAPI app + CORS + Webhook + Lifespan
│       ├── printer_manager.py       #     PrinterConnectionManager (WS + Redis)
│       ├── dependencies.py          #     FastAPI-зависимости
│       ├── routers/
│       │   ├── stats.py             #     GET /api/stats, GET /api/inventory, GET /
│       │   └── printer.py           #     GET /api/printer/status, WS /ws/printer/{token}
│       └── templates/
│           └── index.html           #     Web Dashboard (26 KB, SPA, Chart.js)
│
├── printer_client/                  # 🖨️ ═══ КЛИЕНТ ПРИНТЕРА (для локального ПК) ═══
│   ├── client.py                    #     WebSocket-клиент (авто-переподключение)
│   ├── receipt_printer.py           #     Формирование чека + USB/Windows печать
│   ├── config.py                    #     Настройки: URL, токен, VID/PID, режим
│   ├── requirements.txt             #     websockets, pywin32
│   ├── start_printer.bat            #     Windows: автозапуск с перезапуском при падении
│   └── README.md                    #     Документация клиента
│
├── migrations/                      # 🔄 Alembic-миграции
│   ├── env.py                       #     Конфигурация (render_as_batch для SQLite)
│   └── versions/                    #     4 миграции:
│       ├── 15206d5e0a8e_initial..   #       Начальная схема
│       ├── 41ccc8d96408_money..     #       Numeric(15,2) для денежных полей
│       ├── e28ee6e67995_timezone..  #       Timezone-aware DateTime
│       └── f878fcb8bb2c_is_active.. #       is_active + каскады
│
├── scripts/                         # 🔧 Утилиты
│   ├── db_backup.py                 #     Бэкап PostgreSQL через pg_dump
│   └── manual_migrate.py            #     Ручная миграция SQLite (legacy)
│
├── tests/                           # 🧪 Тесты (pytest)
│   ├── conftest.py                  #     Фикстуры: in-memory SQLite, моки сервисов
│   ├── test_api.py                  #     Тесты REST API (/api/stats, /api/inventory)
│   ├── test_inventory.py            #     Тесты CRUD товаров и остатков
│   ├── test_printer_ws.py           #     Тесты WebSocket принтера + дедупликация
│   ├── test_receipt_format.py       #     Тесты формата чеков (ESC/POS)
│   └── test_service.py             #     Тесты сервисного слоя
│
├── logs/                            #     Логи приложения (ротация 10 MB, хранение 1 неделя)
│
└── .github/
    └── workflows/
        └── deploy.yml               #     CI: pytest --cov на каждый push/PR в main
```

---

## 🏁 Быстрый старт

### Требования

- **Python** 3.12+
- **PostgreSQL** 15+ (или SQLite для разработки)
- **Redis** 7+ (опционально, для FSM и дедупликации чеков)
- **Git**

### 1. Клонирование

```bash
git clone https://github.com/your-username/sales_and_stock_bot.git
cd sales_and_stock_bot
```

### 2. Виртуальное окружение

```bash
python -m venv .venv

# Windows:
.venv\Scripts\activate

# Linux/macOS:
source .venv/bin/activate
```

### 3. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 4. Настройка окружения

```bash
# Скопируйте шаблон
cp .env.example .env

# Отредактируйте .env — минимально необходимо:
# BOT_TOKEN, ADMIN_IDS
```

> 📌 Подробное описание всех переменных — в разделе [Переменные окружения](#-переменные-окружения).

### 5. Миграции базы данных

```bash
# SQLite (без DATABASE_URL → автоматически файл app.db)
python -m alembic upgrade head

# PostgreSQL (при наличии DATABASE_URL в .env)
python -m alembic upgrade head
```

### 6. Запуск

```bash
python main.py
```

В логах вы увидите:
```
✅ Setting up services...
✅ PrinterConnectionManager зарегистрирован в DI-контейнере
✅ Initializing Telegram Bot...
✅ Starting API Server...
INFO:     Uvicorn running on http://0.0.0.0:8000
```

---

## 🔐 Переменные окружения

Создайте файл `.env` в корне проекта. Полный список параметров:

| Переменная | Обязательная | По умолчанию | Описание |
|------------|:-----------:|-------------|----------|
| `BOT_TOKEN` | ✅ | — | Токен Telegram-бота от [@BotFather](https://t.me/BotFather) |
| `ADMIN_IDS` | ✅ | — | Telegram ID администраторов через запятую (узнать у [@userinfobot](https://t.me/userinfobot)) |
| `RUN_TELEGRAM` | ❌ | `True` | Включить Telegram-бота |
| `RUN_API` | ❌ | `True` | Включить FastAPI-сервер |
| `API_HOST` | ❌ | `0.0.0.0` | Хост для Uvicorn |
| `API_PORT` | ❌ | `8000` | Порт для Uvicorn (перезаписывается `PORT` от Railway) |
| `WEBAPP_URL` | ❌ | `https://localhost:8000` | URL для Telegram WebApp кнопки в боте |
| `DATABASE_URL` | ❌ | `sqlite+aiosqlite:///app.db` | URL подключения к БД. Поддерживается `postgresql://` и `sqlite+aiosqlite://` |
| `REDIS_URL` | ❌ | `redis://localhost:6379/0` | URL Redis для FSM-хранилища и дедупликации чеков |
| `PRINTER_SECRET_TOKEN` | ❌ | `change-me-to-secure-token` | Секретный токен для WebSocket-авторизации принтера |
| `DASHBOARD_PASSWORD` | ❌ | `admin123` | Пароль для Web Dashboard (Basic Auth, логин: `admin`) |
| `WEBHOOK_URL` | ❌ | `""` (пусто) | URL для Telegram Webhook. Если пусто — используется Long Polling |
| `WEBHOOK_PATH` | ❌ | `/webhook` | Путь для Webhook-эндпоинта |

### Пример `.env` для разработки

```env
BOT_TOKEN=1234567890:YOUR_TELEGRAM_BOT_TOKEN
ADMIN_IDS=123456789
RUN_TELEGRAM=True
RUN_API=True
WEBAPP_URL=https://localhost:8000
```

### Пример `.env` для продакшена (Railway)

```env
BOT_TOKEN=1234567890:YOUR_TELEGRAM_BOT_TOKEN
ADMIN_IDS=123456789,987654321
RUN_API=True
WEBAPP_URL=https://your-app.up.railway.app
DATABASE_URL=postgresql://user:pass@host:port/db
REDIS_URL=redis://default:pass@host:port
PRINTER_SECRET_TOKEN=super-secure-random-token-2026
DASHBOARD_PASSWORD=strong-password-here
```

---

## 🐳 Деплой

### Docker (Локально)

```bash
# Сборка и запуск
docker-compose up --build -d

# Просмотр логов
docker-compose logs -f

# Остановка
docker-compose down
```

`entrypoint.sh` автоматически:
1. Применяет миграции (`alembic upgrade head`)
2. Запускает `python main.py`

### Railway (Рекомендуется для продакшена)

Проект полностью готов к деплою на [Railway](https://railway.app):

1. **Подключите репозиторий** к Railway
2. **Создайте сервисы:**
   - PostgreSQL (Plugin)
   - Redis (Plugin)
   - App (из репозитория)
3. **Настройте переменные окружения** в Settings → Variables:
   - `BOT_TOKEN`, `ADMIN_IDS`, `WEBAPP_URL`, `PRINTER_SECRET_TOKEN`
   - `DATABASE_URL` и `REDIS_URL` — подставляются автоматически из Plugins
4. Railway автоматически обнаружит `Dockerfile` и запустит деплой

> 💡 Railway автоматически устанавливает переменную `PORT`, которая подхватывается в `config.py`.

### Render / DigitalOcean / Другие

Проект совместим с любой платформой, поддерживающей Docker:

- Укажите `DATABASE_URL` для PostgreSQL
- Укажите `REDIS_URL` для Redis
- `Dockerfile` сам выполнит миграции через `entrypoint.sh`

---

## 📡 API эндпоинты

### REST API

Все эндпоинты требуют Basic Auth (`admin` / `DASHBOARD_PASSWORD`) или query-параметры `?u=admin&p=password`.

| Метод | Путь | Описание |
|-------|------|----------|
| `GET` | `/` | Web Dashboard (HTML-страница) |
| `GET` | `/api/stats?period=today\|week` | Статистика продаж (JSON): выручка, количество, разбивка по товарам и сотрудникам |
| `GET` | `/api/inventory` | Список всех товаров с остатками и категориями |
| `GET` | `/api/printer/status` | Проверка работоспособности сервиса (healthcheck) |

### WebSocket

| Путь | Описание |
|------|----------|
| `WS /ws/printer/{secret_token}` | Канал для локального клиента-принтера. Авторизация через `secret_token` |

#### Протокол WebSocket:

```
┌──────────┐                        ┌──────────┐
│  Сервер  │                        │  Клиент  │
└────┬─────┘                        └────┬─────┘
     │◄────── connect (secret_token) ─────│
     │                                    │
     │─── JSON (order data) ────────────►│
     │                                    │
     │◄──── "ACK" (успешно) ──────────────│
     │◄──── "ERROR:msg" (ошибка) ─────────│
     │                                    │
     │◄──── "ping" ───────────────────────│
     │─── "pong" ────────────────────────►│
```

#### Формат JSON задания на печать:

```json
{
  "order_id": "abc12345-uuid-format",
  "worker_name": "Имя сотрудника",
  "timestamp": "2026-04-03 20:30:00",
  "items": [
    {
      "name": "Coca-Cola 1L",
      "quantity": 2,
      "price": 12000,
      "sum": 24000
    }
  ],
  "total_amount": 24000,
  "currency": "UZS"
}
```

---

## 💾 База данных

### ER-диаграмма

```mermaid
erDiagram
    users ||--o{ transactions : "has"
    products ||--o{ transactions : "involved_in"
    categories ||--o{ products : "contains"

    users {
        int id PK
        bigint tg_id UK
        string username
        string full_name
        string phone
        enum role "ADMIN|WORKER|PENDING|BANNED"
        int kpi
        datetime joined_at
        int is_active
    }

    categories {
        int id PK
        string name UK
    }

    products {
        int id PK
        string name UK
        decimal price "Numeric(15,2)"
        int quantity
        string barcode UK
        int category_id FK
        int is_active
    }

    transactions {
        int id PK
        int user_id FK
        int product_id FK
        int amount
        decimal total_price "Numeric(15,2)"
        datetime timestamp
        enum type "SALE|RECEIPT|WRITE_OFF"
        string reason "nullable"
        string order_group_id "UUID, nullable"
    }
```

### Модели

| Модель | Описание |
|--------|----------|
| `User` | Telegram-пользователь. Роли: `ADMIN`, `WORKER`, `PENDING`, `BANNED` |
| `Category` | Категория товаров (группировка) |
| `Product` | Товар: название, цена (`Numeric(15,2)`), остаток, штрихкод, `is_active` |
| `Transaction` | Операция: продажа, приёмка, списание. Связь с `order_group_id` для корзины |

### Миграции

Управляются через Alembic. На текущий момент 4 миграции:

```bash
# Просмотр текущей ревизии
python -m alembic current

# Применить все миграции
python -m alembic upgrade head

# Откатить на одну миграцию
python -m alembic downgrade -1

# Создать новую миграцию (после изменения моделей)
python -m alembic revision --autogenerate -m "описание изменений"
```

---

## 🖨️ Настройка печати чеков (Xprinter)

Модуль печати работает по схеме **Cloud Server → WebSocket → Local Client → USB Printer**.

### Схема работы

```
Продажа в боте
     │
     ▼
TransactionService.create_bulk_sale()
     │
     ▼
PrinterManager.send_print_job()
     │
     ├─► Принтер подключен?
     │       ├─ ДА → WebSocket → JSON → Клиент → ESC/POS → 🖨️ Чек напечатан
     │       └─ НЕТ → Redis-очередь + кнопка "🖨️ Chekni chop etish" в Telegram
     │
     ▼
Redis: printed_order:{id} = 1 (TTL 24h) — дедупликация
```

### Подготовка принтера

1. **Подключите Xprinter** к ПК через USB
2. Выберите режим:
   - **Windows-режим** (рекомендуется): Установите стандартный драйвер принтера через «Устройства и принтеры»
   - **USB-режим**: Установите [WinUSB драйвер через Zadig](https://zadig.akeo.ie/)
3. Узнайте параметры:
   - **Windows**: Имя принтера в «Устройствах и принтерах» → `PRINTER_NAME_WIN`
   - **USB**: Vendor/Product ID через Диспетчер устройств → `PRINTER_VENDOR_ID / PRINTER_PRODUCT_ID`

### Настройка клиента

```bash
# 1. Скопируйте папку printer_client/ на ПК с принтером

# 2. Отредактируйте printer_client/config.py:
#    SERVER_WS_URL = "wss://your-domain.railway.app/ws/printer/{token}"
#    SECRET_TOKEN = "ваш-PRINTER_SECRET_TOKEN-из-.env"
#    PRINTER_MODE = "windows"  # или "usb"
#    PRINTER_NAME_WIN = "POSPrinter POS58"  # для Windows-режима

# 3. Установите зависимости
cd printer_client
pip install -r requirements.txt

# 4. Запустите
python client.py
```

### Автозапуск (Windows)

Дважды кликните `start_printer.bat` — скрипт:
- Проверяет наличие Python и зависимостей
- Запускает `client.py` в цикле
- При падении — перезапускает через 3 секунды

Для автозапуска при включении ПК:
```
Win+R → shell:startup → скопируйте ярлык start_printer.bat
```

### Тестовый режим

Клиент работает **без физического принтера** — чеки выводятся в консоль. При подключении USB-принтера автоматически переключается на реальную печать.

### Формат чека (58 мм)

```
================================
      Sale & Stock Bot
================================
Chek: abc12345-uuid
Xodim: Alisher
Sana: 2026-04-03 20:30:00
--------------------------------
Nomi              Son     Summa
--------------------------------
Coca-Cola 1L        2    24,000
Snickers 50g        3    18,000
--------------------------------
         JAMI: 42,000 UZS

   2026-04-03 20:30:00

   Rahmat! Xaridingiz uchun
        minnatdormiz!

================================
```

---

## 🖥 Web Dashboard

### Доступ

| Способ | URL |
|--------|-----|
| Браузер | `https://your-domain.com/?u=admin&p=password` |
| Telegram WebApp | Кнопка **🌐 Web Dashboard** в панели администратора |

### Возможности

- 📊 **Графики**: Pie-chart по товарам, Bar-chart по сотрудникам (Chart.js)
- 💰 **KPI**: Общая выручка, количество чеков, проданных единиц
- 👥 **Рейтинг**: Топ-5 лучших сотрудников по выручке
- 🔄 **Auto-refresh**: Обновление данных каждые 10 секунд без перезагрузки
- 🎨 **Дизайн**: Glassmorphism, Plus Jakarta Sans, тёмная тема
- 🌐 **Локализация**: Узбекский язык, валюта UZS

### HTTPS для Telegram WebApp

Telegram требует HTTPS для Web Apps. Для локальной разработки:

```bash
# 1. Установите ngrok: https://ngrok.com/download
ngrok http 8000

# 2. Скопируйте https://... URL
# 3. Вставьте в .env: WEBAPP_URL=https://xxxx.ngrok-free.app
# 4. Перезапустите бота
```

---

## 🧪 Тестирование

Проект использует **pytest** с поддержкой `asyncio`:

```bash
# Запуск всех тестов
python -m pytest

# С покрытием кода
python -m pytest --cov=app tests/

# Подробный вывод
python -m pytest -v

# Конкретный тест-файл
python -m pytest tests/test_printer_ws.py -v
```

### Тест-файлы

| Файл | Покрытие |
|------|----------|
| `test_api.py` | REST API эндпоинты (`/api/stats`, `/api/inventory`) |
| `test_inventory.py` | CRUD товаров, валидация остатков |
| `test_printer_ws.py` | WebSocket принтера, дедупликация, очередь |
| `test_receipt_format.py` | Формат чеков, ESC/POS, кириллица |
| `test_service.py` | Сервисный слой |
| `conftest.py` | Фикстуры: in-memory SQLite, моки сервисов |

### Конфигурация

```ini
# pytest.ini
[pytest]
pythonpath = .
asyncio_mode = auto
asyncio_default_fixture_loop_scope = function
```

---

## 🔄 CI/CD

### GitHub Actions

При каждом `push` или `pull_request` в ветку `main` автоматически запускается:

```yaml
# .github/workflows/deploy.yml
- Python 3.12
- pip install -r requirements.txt
- python -m pytest --cov=app tests/
```

Пайплайн проверяет:
- ✅ Все тесты проходят
- ✅ Покрытие кода собирается

---

## 💾 Бэкап базы данных

### Автоматический бэкап PostgreSQL

```bash
python scripts/db_backup.py
```

Скрипт:
- Читает `DATABASE_URL` из `.env`
- Создаёт SQL-дамп через `pg_dump`
- Сохраняет в `backups/db_backup_YYYYMMDD_HHMMSS.sql`
- Работает только с PostgreSQL

### Ручной бэкап

```bash
# PostgreSQL
pg_dump $DATABASE_URL -f backup.sql

# Восстановление
psql $DATABASE_URL < backup.sql
```

---

## 📝 Логирование

Система логирования на базе **Loguru** с перехватом стандартного `logging`:

| Канал | Формат | Ротация |
|-------|--------|---------|
| `stdout` | Цветной с уровнями | — |
| `logs/sales_bot.log` | Файловый без цвета | 10 MB / 1 неделя |

Вся `stdlib logging` перенаправляется через `InterceptHandler` в Loguru.

---

## 🔒 Безопасность

| Аспект | Реализация |
|--------|-----------|
| **Telegram Auth** | `AuthMiddleware` — проверка роли на каждый message/callback |
| **WebSocket Auth** | Секретный токен (`PRINTER_SECRET_TOKEN`) в URL |
| **Dashboard Auth** | HTTP Basic Auth + query-параметры |
| **SQL Injection** | SQLAlchemy ORM — параметризованные запросы |
| **Race Conditions** | Атомарный `UPDATE ... WHERE quantity >= amount RETURNING` |
| **Double Rollback** | `SELECT ... FOR UPDATE` при откате транзакций |
| **Double Print** | Redis-дедупликация по `order_id` (TTL 24h) |
| **CORS** | Настроен через `CORSMiddleware` |
| **Secrets** | `.env` в `.gitignore`, `.env.example` без реальных данных |

---

## ❓ FAQ

<details>
<summary><b>Как узнать свой Telegram ID?</b></summary>

Напишите боту [@userinfobot](https://t.me/userinfobot) в Telegram — он ответит вашим ID.
</details>

<details>
<summary><b>Бот не отвечает после запуска</b></summary>

1. Проверьте `BOT_TOKEN` в `.env`
2. Убедитесь, что `RUN_TELEGRAM=True`
3. Проверьте логи на ошибки: `logs/sales_bot.log`
4. Если бот ранее использовал Webhook — удалите его: `https://api.telegram.org/bot<TOKEN>/deleteWebhook`
</details>

<details>
<summary><b>Ошибка «Service 'X' already registered»</b></summary>

DI-контейнер запрещает повторную регистрацию. Это защита от дублирования сервисов. Проверьте, что `App.setup_services()` вызывается один раз.
</details>

<details>
<summary><b>Как переключиться между SQLite и PostgreSQL?</b></summary>

- **SQLite** (по умолчанию): Не указывайте `DATABASE_URL` или оставьте пустой
- **PostgreSQL**: Укажите `DATABASE_URL=postgresql://user:pass@host:port/dbname`
- Система автоматически добавит `+asyncpg` к URL для асинхронного драйвера
</details>

<details>
<summary><b>Как добавить второго администратора?</b></summary>

В `.env` через запятую: `ADMIN_IDS=123456789,987654321`. Перезапустите бота. Новый администратор будет автоматически повышен при следующем `/start`.
</details>

<details>
<summary><b>Принтер не печатает</b></summary>

1. Проверьте режим в `config.py`: `PRINTER_MODE = "windows"` или `"usb"`
2. Для Windows: убедитесь, что имя принтера в `PRINTER_NAME_WIN` совпадает с именем в «Устройствах и принтерах»
3. Для USB: проверьте `PRINTER_VENDOR_ID` и `PRINTER_PRODUCT_ID` через Диспетчер устройств
4. Клиент работает в тестовом режиме без принтера — чеки выводятся в консоль
</details>

<details>
<summary><b>Redis недоступен — что будет?</b></summary>

Система продолжит работать:
- FSM переключится на `MemoryStorage` (состояния потеряются при перезапуске)
- Дедупликация чеков будет отключена
- Очередь чеков не будет сохраняться
- В логах будет предупреждение
</details>

<details>
<summary><b>Как создать новую миграцию?</b></summary>

```bash
# 1. Измените модели в app/database/models.py
# 2. Сгенерируйте миграцию
python -m alembic revision --autogenerate -m "описание"
# 3. Примените
python -m alembic upgrade head
```
</details>

<details>
<summary><b>Как запустить только API без Telegram?</b></summary>

В `.env`: `RUN_TELEGRAM=False`, `RUN_API=True`. Полезно для отладки Dashboard.
</details>

---

## 📄 Лицензия

Этот проект разработан для внутреннего использования. Все права защищены.

---

<div align="center">

**Разработано с ❤️ для автоматизации торговых точек**

![Python](https://img.shields.io/badge/Made_with-Python-3776AB?style=flat&logo=python&logoColor=white)
![Telegram](https://img.shields.io/badge/Powered_by-Telegram_Bot_API-26A5E4?style=flat&logo=telegram&logoColor=white)

</div>
]]>
