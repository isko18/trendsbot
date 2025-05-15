import asyncio
import sqlite3
from datetime import datetime, timedelta
from functools import wraps

from aiogram import Bot, Dispatcher, types
from aiogram.types import (
    Message, CallbackQuery, BotCommand, ReplyKeyboardMarkup, KeyboardButton
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import LabeledPrice, PreCheckoutQuery
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, PAY_TOKEN
from deep_translator import GoogleTranslator
from trends.amazon import get_amazon_trends
from trends.shein import get_shein_trends
from trends.trend1688 import get_1688_categories, get_1688_trends_by_category
from trends.pinterest import get_pinterest_trends
from trends.wordstat import get_wordstat_count

# === FSM ===
class PromoInput(StatesGroup):
    waiting_for_code = State()

class WordstatFSM(StatesGroup):
    waiting_for_phrase = State()


# === Инициализация ===
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

DB_NAME = "denushki.db"
SEEN_PRODUCTS_DB = "seen_products.db"
PROMO_DB = "promos.db"
ADMIN_ID = {5268023094, 1230525163}

# === БД ===

# wordstat_limit.py
import sqlite3
from datetime import datetime

def init_wordstat_limit_db():
    with sqlite3.connect("wordstat_limit.db") as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS requests (
            user_id INTEGER,
            date TEXT,
            count INTEGER,
            PRIMARY KEY (user_id, date)
        )
        """)

def check_wordstat_limit(user_id: int) -> bool:
    if user_id in ADMIN_ID:
        return True 
    today = datetime.now().strftime("%Y-%m-%d")
    with sqlite3.connect("wordstat_limit.db") as conn:
        cur = conn.cursor()
        row = cur.execute("SELECT count FROM requests WHERE user_id = ? AND date = ?", (user_id, today)).fetchone()

        if row and row[0] >= 5:
            return False
        elif row:
            cur.execute("UPDATE requests SET count = count + 1 WHERE user_id = ? AND date = ?", (user_id, today))
        else:
            cur.execute("INSERT INTO requests (user_id, date, count) VALUES (?, ?, 1)", (user_id, today))

        conn.commit()
        return True

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            end_date TEXT
        )""")

def init_seen_products_db():
    with sqlite3.connect(SEEN_PRODUCTS_DB) as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS seen_products (
            user_id INTEGER,
            product_link TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, product_link)
        )""")
        conn.execute("""
        CREATE TABLE IF NOT EXISTS user_clicks (
            user_id INTEGER,
            platform TEXT,
            PRIMARY KEY (user_id, platform)
        )""")
        conn.execute("""
        CREATE TABLE IF NOT EXISTS promo_clicks (
            user_id INTEGER,
            platform TEXT,
            click_date TEXT,
            clicks INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, platform, click_date)
        )""")

def init_promo_db():
    with sqlite3.connect(PROMO_DB) as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS promo_codes (
            code TEXT PRIMARY KEY,
            max_uses INTEGER DEFAULT 100,
            used_count INTEGER DEFAULT 0
        )""")
        conn.execute("""
        CREATE TABLE IF NOT EXISTS promo_uses (
            user_id INTEGER,
            code TEXT,
            PRIMARY KEY (user_id, code)
        )""")


# === Лимит кликов ===
# def check_promo_click_limit(user_id: int, platform: str) -> bool:
#     if user_id in ADMIN_ID:
#         return True 
#     today = datetime.now().strftime("%Y-%m-%d")
#     with sqlite3.connect(SEEN_PRODUCTS_DB) as conn:
#         cur = conn.cursor()
#         row = cur.execute("""
#             SELECT clicks FROM promo_clicks
#             WHERE user_id = ? AND platform = ? AND click_date = ?
#         """, (user_id, platform, today)).fetchone()
#         if row and row[0] >= 3:
#             return False  # Превышен лимит
#         if row:
#             cur.execute("""
#                 UPDATE promo_clicks SET clicks = clicks + 1
#                 WHERE user_id = ? AND platform = ? AND click_date = ?
#             """, (user_id, platform, today))
#         else:
#             cur.execute("""
#                 INSERT INTO promo_clicks (user_id, platform, click_date, clicks)
#                 VALUES (?, ?, ?, 1)
#             """, (user_id, platform, today))
#         conn.commit()
#     return True
# === Подписка ===
def save_user_subscription(user_id: int, username: str, days: int):
    now = datetime.now()
    end_date = max(get_user_subscription_end(user_id) or now, now) + timedelta(days=days)
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("""
        INSERT INTO subscriptions (user_id, username, end_date)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET end_date = excluded.end_date
        """, (user_id, username, end_date.strftime("%Y-%m-%d %H:%M:%S")))
        print(f"[OK] Подписка для {user_id} до {end_date}")  # ← лог

async def remind_expiring_subscriptions():
    while True:
        now = datetime.now()
        tomorrow = (now + timedelta(days=1)).strftime("%Y-%m-%d")

        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            rows = cursor.execute("""
                SELECT user_id, username, end_date FROM subscriptions
            """).fetchall()

            for user_id, username, end_date in rows:
                try:
                    end_dt = datetime.strptime(end_date, "%Y-%m-%d %H:%M:%S")
                    if end_dt.date() == (now + timedelta(days=1)).date():
                        kb = InlineKeyboardBuilder()
                        kb.button(text="💳 Продлить подписку", callback_data="open_buy_menu")
                        await bot.send_message(
                            user_id,
                            f"⏳ Подписка заканчивается <b>завтра ({end_dt.strftime('%Y-%m-%d')})</b>.\n"
                            "Продлите сейчас, чтобы не потерять доступ к трендам 👇",
                            parse_mode="HTML",
                            reply_markup=kb.as_markup()
                        )
                except Exception as e:
                    print(f"[ERROR] Напоминание для {user_id} — {e}")

        await asyncio.sleep(3600 * 12)  # проверка каждые 12 часов

def get_user_subscription_end(user_id: int):
    with sqlite3.connect(DB_NAME) as conn:
        row = conn.execute("SELECT end_date FROM subscriptions WHERE user_id = ?", (user_id,)).fetchone()
        print(f"[DEBUG] row for {user_id}:", row)
        return datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S") if row else None

def is_premium_active(user_id: int):
    if user_id in ADMIN_ID:
        return True
    end = get_user_subscription_end(user_id)
    return end and end > datetime.now()

# === Промокод ===
@dp.callback_query(lambda c: c.data == "enter_promo")
async def ask_promo(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("✏️ Введите промокод:")
    await state.set_state(PromoInput.waiting_for_code)
    await callback.answer()

@dp.message(PromoInput.waiting_for_code)
async def handle_promo_input(message: Message, state: FSMContext):
    code = message.text.strip()
    user_id = message.from_user.id

    with sqlite3.connect(PROMO_DB) as conn:
        cur = conn.cursor()
        promo = cur.execute(
            "SELECT max_uses, used_count FROM promo_codes WHERE code = ?", (code,)
        ).fetchone()

        if not promo:
            await message.answer(
                "❌ <b>Промокод не найден.</b>\n"
                "Проверь правильность ввода и попробуй снова.",
                parse_mode="HTML"
            )
            await state.clear()
            return

        if promo[1] >= promo[0]:
            await message.answer(
                "😔 <b>Этот промокод больше недействителен.</b>\n"
                "Он уже использован максимальное количество раз.",
                parse_mode="HTML"
            )
            await state.clear()
            return

        if cur.execute(
            "SELECT 1 FROM promo_uses WHERE user_id = ? AND code = ?", (user_id, code)
        ).fetchone():
            await message.answer(
                "⚠️ <b>Вы уже активировали этот промокод ранее.</b>",
                parse_mode="HTML"
            )
            await state.clear()
            return

        # ✅ Всё в порядке — активируем подписку
        save_user_subscription(user_id, message.from_user.username or "", 3)
        cur.execute("INSERT INTO promo_uses (user_id, code) VALUES (?, ?)", (user_id, code))
        cur.execute("UPDATE promo_codes SET used_count = used_count + 1 WHERE code = ?", (code,))
        conn.commit()

        # 🎉 Сообщение об активации
        kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="🛍 Amazon 🦅"), KeyboardButton(text="👗 Shein ✨")],
                [KeyboardButton(text="📦 1688 🐉"), KeyboardButton(text="📌 Pinterest 💡")],
                [KeyboardButton(text="🔍 Wordstat 📊")]
            ],
            resize_keyboard=True
        )

        await message.answer(
            "🎁 <b>Промокод успешно активирован!</b>\n\n"
            "✅ Вы получили <b>3 дня премиум-доступа</b> к трендам.\n"
            "Выбирай маркетплейс и вдохновляйся новинками 👇",
            parse_mode="HTML",
            reply_markup=kb
        )

    await state.clear()

@dp.message(lambda msg: msg.text == "/privacy")
async def show_privacy(msg: Message):
    await msg.answer(
        "<b>🔐 Политика конфиденциальности</b>\n\n"
        "Мы уважаем вашу конфиденциальность и обязуемся защищать персональные данные.\n\n"
        "<b>Собираемые данные:</b>\n"
        "• Идентификатор Telegram (user_id)\n"
        "• Имя пользователя (username)\n"
        "• Информация о покупке (дата, срок подписки)\n\n"
        "<b>Цель обработки:</b>\n"
        "• Предоставление доступа к платным функциям бота\n"
        "• Идентификация пользователя и управление подпиской\n"
        "• Поддержка и уведомления\n\n"
        "Данные не передаются третьим лицам, кроме случаев, предусмотренных законом.\n\n"
        "Хранение осуществляется на защищённых серверах. Доступ имеют только администраторы.\n\n"
        "По вопросам конфиденциальности: <a href='mailto:support@example.com'>support@example.com</a>",
        parse_mode="HTML"
    )

@dp.message(lambda msg: msg.text == "/offer")
async def show_offer(msg: Message):
    await msg.answer(
        "<b>📄 Публичная оферта</b>\n\n"
        "Настоящий документ является официальным предложением (офертой) для физических и юридических лиц о заключении "
        "договора на возмездное предоставление доступа к цифровому контенту в Telegram-боте.\n\n"
        "<b>Услуга:</b> подписка на доступ к трендам, аналитике и цифровому контенту.\n"
        "<b>Срок действия:</b> согласно выбранному тарифу при оплате.\n"
        "<b>Порядок заключения договора:</b>\n"
        "• Оплата подписки через встроенные платежные системы Telegram (Visa / Mastercard / Элкарт)\n"
        "• С момента оплаты пользователь считается акцептовавшим оферту\n\n"
        "Сторонами считается:\n"
        "• Продавец — ИП/ОсОО\n"
        "• Покупатель — пользователь Telegram, осуществивший оплату\n\n"
        "Контакт для юридических запросов: <a href='mailto:support@example.com'>support@example.com</a>",
        parse_mode="HTML"
    )

@dp.message(lambda msg: msg.text == "/about")
async def show_about(msg: Message):
    await msg.answer(
        "<b>🏢 Информация о продавце</b>\n\n"
        "<b>Название:</b> ИП Нишамбаева Айжан Бекмулдоевна\n"
        "<b>ИНН:</b> 12203198800263\n"
        "<b>ОКПО:</b> 30505619\n"
        "<b>Юридический адрес:</b> г. Ош, ул. Узгенская, 13/7\n"
        "<b>Телефон:</b> +996 556 432 322\n"
        "<b>Email:</b> <a href='mailto:support@example.com'>support@example.com</a>\n\n"
        "<b>Банковские реквизиты:</b>\n"
        "ОАО «ОплатБанк»\n"
        "Р/с: 1234567890123456\n"
        "БИК: 123456\n\n"
        "<b>Платёжные системы:</b> Visa, Mastercard, Элкарт",
        parse_mode="HTML"
    )

@dp.message(lambda msg: msg.text == "/refund")
async def show_refund(msg: Message):
    await msg.answer(
        "<b>🔁 Политика возврата средств</b>\n\n"
        "Вы можете запросить возврат оплаты в следующих случаях:\n"
        "• Не предоставлен доступ к платным функциям\n"
        "• Ошибка при оплате (дублирование транзакции)\n"
        "• Сбои в работе бота, не устранённые в течение 48 часов\n\n"
        "<b>Срок запроса:</b> не позднее 7 календарных дней с момента оплаты.\n"
        "<b>Форма возврата:</b> на ту же банковскую карту, с которой производилась оплата.\n"
        "<b>Срок возврата:</b> до 10 рабочих дней, в зависимости от банка.\n\n"
        "Запрос отправляется на: <a href='mailto:support@example.com'>support@example.com</a> с указанием:\n"
        "• ФИО\n• Telegram ID\n• Даты и суммы платежа\n• Причины запроса",
        parse_mode="HTML"
    )

@dp.message(lambda m: m.text and m.text.startswith("/createpromo "))
async def create_promo(message: Message):
    if message.from_user.id not in ADMIN_ID:
        return await message.answer("⛔ Только админ может создавать промокоды.")
    
    code = message.text.split(maxsplit=1)[1].strip()
    with sqlite3.connect(PROMO_DB) as conn:
        try:
            conn.execute("INSERT INTO promo_codes (code) VALUES (?)", (code,))
            await message.answer(f"✅ Промокод '{code}' создан.")
        except sqlite3.IntegrityError:
            await message.answer(f"⚠️ Промокод '{code}' уже существует.")

@dp.callback_query(lambda c: c.data == "open_buy_menu")
async def show_buy_options(callback: CallbackQuery):
    kb = InlineKeyboardBuilder()
    kb.button(text="📆 15 дней — 500 сом", callback_data="buy_15")
    kb.button(text="🗓 30 дней — 1000 сом", callback_data="buy_30")
    kb.button(text="🔥 90 дней — 2500 сом", callback_data="buy_90")
    kb.button(text="💎 365 дней — 10 000 сом", callback_data="buy_365")
    kb.adjust(1)

    await callback.message.answer(
        "<b>💳 Тарифы на доступ к трендам:</b>\n\n"
        "📆 <b>15 дней — 500 сом</b> — краткосрочный старт\n"
        "🗓 <b>30 дней — 1000 сом</b> — на месяц\n"
        "🔥 <b>90 дней — 2500 сом</b> — популярный выбор\n"
        "💎 <b>365 дней — 10 000 сом</b> — выгодно на год\n\n"
        "👇 Выберите нужный тариф:",
        parse_mode="HTML",
        reply_markup=kb.as_markup()
    )
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith("buy_"))
async def handle_buy(callback: CallbackQuery):
    plans = {
        "buy_15": {"label": "Подписка на 15 дней", "amount": 50000, "days": 15},
        "buy_30": {"label": "Подписка на 30 дней", "amount": 100000, "days": 30},
        "buy_90": {"label": "Подписка на 90 дней", "amount": 250000, "days": 90},
        "buy_365": {"label": "Подписка на 365 дней", "amount": 1000000, "days": 365},
    }
    plan = plans.get(callback.data)

    if not plan:
        return await callback.answer("❌ Не удалось найти тарифный план.", show_alert=True)

    await callback.message.answer(
        "<b>📌 Перед оплатой, ознакомьтесь с:</b>\n"
        "🔐 /privacy | 📄 /offer | 🔁 /refund | 🏢 /about\n\n"
        "💳 Оплачивая, вы подтверждаете согласие с условиями.",
        parse_mode="HTML"
    )

    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title="Премиум-доступ к трендам",
        description=plan["label"],
        provider_token=PAY_TOKEN,
        currency="KGS",
        prices=[LabeledPrice(label=plan["label"], amount=plan["amount"])],
        payload=f"sub:{plan['days']}"
    )
    await callback.answer()


# ✅ Подтверждение перед оплатой
@dp.pre_checkout_query(lambda q: True)
async def checkout_handler(query: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(query.id, ok=True)

# ✅ Оплата прошла успешно
@dp.message(lambda m: m.successful_payment is not None)
async def successful_payment(message: Message):
    days = int(message.successful_payment.invoice_payload.split(":")[1])
    save_user_subscription(message.from_user.id, message.from_user.username or "", days)
    end = get_user_subscription_end(message.from_user.id)

    # Клавиатура с маркетплейсами
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
                [KeyboardButton(text="🛍 Amazon 🦅"), KeyboardButton(text="👗 Shein ✨")],
                [KeyboardButton(text="📦 1688 🐉"), KeyboardButton(text="📌 Pinterest 💡")],
                [KeyboardButton(text="🔍 Wordstat 📊")]
        ],
        resize_keyboard=True
    )

    await message.answer(
        f"✅ Подписка оформлена до <b>{end.strftime('%Y-%m-%d %H:%M:%S')}</b>\n\n"
        "Выбирай маркетплейс ниже 👇",
        parse_mode="HTML",
        reply_markup=keyboard
    )

    
# === Клавиатуры и фильтрация ===
@dp.message(lambda msg: msg.text == "/start")
async def start(message: Message):
    if is_premium_active(message.from_user.id):
        text = (
            "🎉 <b>Подписка активна!</b>\n\n"
            "Выбери платформу, чтобы посмотреть самые 🔥 тренды прямо сейчас:"
        )
        kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="🛍 Amazon 🦅"), KeyboardButton(text="👗 Shein ✨")],
                [KeyboardButton(text="📦 1688 🐉"), KeyboardButton(text="📌 Pinterest 💡")],
                [KeyboardButton(text="🔍 Wordstat 📊")]
            ],
            resize_keyboard=True
        )
        await message.answer(text, parse_mode="HTML", reply_markup=kb)
    else:
        text = (
            "👋 <b>Добро пожаловать!</b>\n\n"
            "Я показываю тренды с самых популярных платформ:\n\n"
            "🛍 <b>Amazon</b> — товары из США\n"
            "👗 <b>Shein</b> — тренды моды\n"
            "📦 <b>1688</b> — опт из Китая\n"
            "📌 <b>Pinterest</b> — идеи и вдохновение\n\n"
            "🔓 Чтобы получить доступ, выбери один из вариантов ниже 👇"
        )
        kb = InlineKeyboardBuilder()
        kb.button(text="💳 Купить подписку", callback_data="open_buy_menu")
        kb.button(text="🎁 Ввести промокод", callback_data="enter_promo")
        await message.answer(text, parse_mode="HTML", reply_markup=kb.as_markup())

    
@dp.message(lambda msg: msg.text == "/status")
async def status(message: Message):
    end = get_user_subscription_end(message.from_user.id)

    if end and end > datetime.now():
        await message.answer(
            f"✅ <b>Подписка активна!</b>\n\n"
            f"🔐 Доступ открыт до: <u>{end.strftime('%Y-%m-%d %H:%M:%S')}</u>\n\n"
            "Спасибо, что с нами 💛",
            parse_mode="HTML"
        )
    else:
        kb = InlineKeyboardBuilder()
        kb.button(text="💳 Купить подписку", callback_data="open_buy_menu")
        kb.button(text="🔑 Ввести промокод", callback_data="enter_promo")

        await message.answer(
            "❌ <b>У вас нет активной подписки.</b>\n\n"
            "Чтобы открыть доступ к трендам, выберите один из вариантов ниже 👇",
            parse_mode="HTML",
            reply_markup=kb.as_markup()
        )

# === Декоратор ===
def premium_required(handler):
    @wraps(handler)
    async def wrapper(message: Message, *args, **kwargs):
        if not is_premium_active(message.from_user.id):
            kb = InlineKeyboardBuilder()
            kb.button(text="🚀 Получить доступ", callback_data="open_buy_menu")
            kb.button(text="🔑 Ввести промокод", callback_data="enter_promo")

            return await message.answer(
                "🔒 <b>Доступ ограничен</b>\n\n"
                "Чтобы просматривать тренды, необходимо <u>оформить подписку</u> или <u>ввести промокод</u> 🎁\n\n"
                "👇 Выбери один из вариантов ниже:",
                parse_mode="HTML",
                reply_markup=kb.as_markup()
            )
        return await handler(message, *args, **kwargs)
    return wrapper

def filter_unseen_products(user_id: int, products: list[dict]) -> list[dict]:
    return products  # теперь возвращаем все товары, независимо от истории

# === Отправка трендов ===
# def filter_unseen_products(user_id: int, products: list[dict]) -> list[dict]:
#     result = []
#     week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
#     with sqlite3.connect(SEEN_PRODUCTS_DB) as conn:
#         cur = conn.cursor()
#         for p in products:
#             if "product_link" not in p:
#                 continue
#             cur.execute("""
#                 SELECT 1 FROM seen_products 
#                 WHERE user_id = ? AND product_link = ? AND timestamp > ?
#             """, (user_id, p["product_link"], week_ago))
#             if not cur.fetchone():
#                 result.append(p)
#                 cur.execute("""
#                     INSERT OR REPLACE INTO seen_products (user_id, product_link, timestamp)
#                     VALUES (?, ?, CURRENT_TIMESTAMP)
#                 """, (user_id, p["product_link"]))
#         conn.commit()
#     return result

async def send_trends(user_id: int, trends: list[dict], chat_id: int):
    trends = filter_unseen_products(user_id, trends)
    if not trends:
        return await bot.send_message(chat_id, "😕 Новых товаров пока нет.")
    for item in trends:
        caption = f"<b>{item.get('title', 'Без названия')}</b>\n💰 {item.get('price', 'Цена не указана')}\n<a href='{item.get('product_link', '#')}'>🛍 Подробнее</a>"
        await bot.send_photo(chat_id, item.get("image_url", ""), caption=caption, parse_mode="HTML")

# === Хендлеры маркетплейсов с лимитом ===
@dp.message(lambda msg: msg.text == "🛍 Amazon 🦅")
@premium_required
async def amazon_handler(msg: Message):
    await msg.answer("🛍 <b>Собираем горячие тренды Amazon...</b>\nПожалуйста, подождите немного 🔄", parse_mode="HTML")
    trends = await get_amazon_trends()
    await send_trends(msg.from_user.id, trends, msg.chat.id)


@dp.message(lambda msg: msg.text == "👗 Shein ✨")
@premium_required
async def shein_handler(msg: Message):
    await msg.answer("💃 <b>Ищем стильные тренды Shein...</b>\nПодождите пару секунд ✨", parse_mode="HTML")
    await send_trends(msg.from_user.id, get_shein_trends(), msg.chat.id)


@dp.message(lambda msg: msg.text == "📌 Pinterest 💡")
@premium_required
async def pinterest_handler(msg: Message):
    await msg.answer("📌 <b>Анализируем вдохновение из Pinterest...</b>\nЭто займёт немного времени 🧠", parse_mode="HTML")
    await send_trends(msg.from_user.id, await get_pinterest_trends(), msg.chat.id)


@dp.message(lambda msg: msg.text == "📦 1688 🐉")
@premium_required
async def choose_1688(msg: Message):
    await msg.answer("📦 <b>Выбираем категорию с топовыми товарами 1688...</b>", parse_mode="HTML")
    cats = await get_1688_categories()
    kb = InlineKeyboardBuilder()
    for original, translated in cats.items():
        kb.button(text=translated, callback_data=f"cat1688:{original}")
    kb.adjust(2)
    await msg.answer("🗂 <b>Выберите интересующую категорию:</b>", parse_mode="HTML", reply_markup=kb.as_markup())


@dp.callback_query(lambda c: c.data.startswith("cat1688:"))
async def category_1688(call: CallbackQuery):
    await call.answer()
    category_key = call.data.split(":", 1)[1]
    await call.message.answer("📦 Получаем тренды по выбранной категории 1688...")
    trends = await get_1688_trends_by_category(category_key)
    await send_trends(call.from_user.id, trends, call.message.chat.id)

@dp.message(lambda msg: msg.text == "🔍 Wordstat 📊")
async def wordstat_start(msg: Message, state: FSMContext):
    await msg.answer("✏️ Введите ключевую фразу:")
    await state.set_state(WordstatFSM.waiting_for_phrase)

@dp.message(WordstatFSM.waiting_for_phrase)
async def wordstat_handler(msg: Message, state: FSMContext):
    if not check_wordstat_limit(msg.from_user.id):
        await msg.answer("⚠️ Ты исчерпал лимит запросов на сегодня (5). Попробуй завтра.")
        await state.clear()
        return

    await msg.answer("⏳ Получаю данные из Wordstat...")
    try:
        result = await get_wordstat_count(msg.text.strip())  # ← вот здесь await
        await msg.answer(result, parse_mode="HTML")
    except Exception as e:
        await msg.answer("❌ Не удалось получить данные. Попробуй позже.")
        print(f"[ERROR] Wordstat: {e}")

    await state.clear()

# === Запуск ===
async def main():
    # Инициализация баз данных
    init_db()
    init_seen_products_db()
    init_promo_db()
    init_wordstat_limit_db()

    # Установка команд бота
    await bot.set_my_commands([
        BotCommand(command="/start", description="Запустить бота"),
        BotCommand(command="/status", description="Проверка подписки")
    ])

    # Запуск фоновой задачи напоминания
    asyncio.create_task(remind_expiring_subscriptions())

    # Запуск polling
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("🚫 Бот остановлен")
