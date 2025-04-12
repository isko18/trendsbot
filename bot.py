import asyncio
import sqlite3
from datetime import datetime, timedelta
from functools import wraps

from aiogram import Bot, Dispatcher, types
from aiogram.types import (
    Message, CallbackQuery, LabeledPrice, PreCheckoutQuery,
    ReplyKeyboardMarkup, KeyboardButton, BotCommand
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import BOT_TOKEN, PAY_TOKEN
from deep_translator import GoogleTranslator
from trends.amazon import get_amazon_trends
from trends.shein import get_shein_trends
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from trends.trend1688 import get_1688_categories, get_1688_trends_by_category

from trends.pinterest import get_pinterest_trends

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

DB_NAME = "denushki.db"


# ========== БАЗА ПОДПИСОК ==========
def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            end_date TEXT
        )
        """)
        conn.commit()


def save_user_subscription(user_id: int, username: str, days: int):
    current_end = get_user_subscription_end(user_id)
    now = datetime.now()
    base_date = current_end if current_end and current_end > now else now
    end_date = (base_date + timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO subscriptions (user_id, username, end_date)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET end_date = excluded.end_date
        """, (user_id, username, end_date))
        conn.commit()


def get_user_subscription_end(user_id: int):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT end_date FROM subscriptions WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        if result:
            return datetime.strptime(result[0], "%Y-%m-%d %H:%M:%S")
        return None


def is_premium_active(user_id: int) -> bool:
    end = get_user_subscription_end(user_id)
    return bool(end and end > datetime.now())


# ========== ПРЕМИУМ ЗАЩИТА ==========
def premium_required(handler):
    @wraps(handler)
    async def wrapper(message: Message, *args, **kwargs):
        if not is_premium_active(message.from_user.id):
            keyboard = InlineKeyboardBuilder()
            keyboard.button(text="🚀 Получить доступ к трендам", callback_data="open_buy_menu")
            keyboard.adjust(1)
            await message.answer(
                "🚫 Доступ ограничен! Оформи подписку и получи мгновенный доступ к самым прибыльным трендам 💥",
                reply_markup=keyboard.as_markup()
            )
            return
        return await handler(message, *args, **kwargs)
    return wrapper


# ========== КЛАВИАТУРА ТРЕНДОВ ==========
trend_keyboard = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="Amazon"), KeyboardButton(text="Shein")],
    [KeyboardButton(text="1688"), KeyboardButton(text="Pinterest")]
], resize_keyboard=True)


# ========== КОМАНДА /start ==========
@dp.message(lambda msg: msg.text == "/start")
async def start(message: Message):
    user_id = message.from_user.id

    if is_premium_active(user_id):
        await message.answer(
            "🎉 Добро пожаловать обратно! Подписка активна.\n\nВыбирай платформу ниже и лови тренды первым:",
            reply_markup=trend_keyboard
        )
    else:
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="💳 Купить подписку", callback_data="open_buy_menu")
        keyboard.adjust(1)
        await message.answer(
            "👋 Привет! Я бот, который помогает находить самые 🔥 товары с маркетплейсов.\nПодписка даст тебе доступ к:\n• Актуальным трендам\n• Инсайтам с Amazon, Shein, 1688 и Pinterest\n• Ежедневным идеям для продаж\nОформи подписку и начни зарабатывать!",
            reply_markup=keyboard.as_markup()
        )


# ========== ПОКУПКА ПОДПИСКИ ==========
@dp.callback_query(lambda c: c.data == "open_buy_menu")
async def show_buy_options(callback: CallbackQuery):
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="🔓 Базовый доступ — 30 дней за 100 ₽", callback_data="buy_30")
    keyboard.button(text="🔥 Оптимум — 3 месяца за 250 ₽", callback_data="buy_90")
    keyboard.button(text="🚀 Продвинутый — 6 месяцев за 450 ₽", callback_data="buy_180")
    keyboard.button(text="💎 Безлимит — 12 месяцев за 800 ₽", callback_data="buy_365")
    keyboard.adjust(1)

    await callback.message.answer(
        "💼 Выберите свой идеальный тариф и начните получать эксклюзивные тренды уже сегодня:",
        reply_markup=keyboard.as_markup()
    )
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith("buy_"))
async def process_payment(callback: CallbackQuery):
    periods = {
        "buy_30": {"label": "Подписка на 1 месяц", "amount": 10000, "days": 30},
        "buy_90": {"label": "Подписка на 3 месяца", "amount": 25000, "days": 90},
        "buy_180": {"label": "Подписка на 6 месяцев", "amount": 45000, "days": 180},
        "buy_365": {"label": "Подписка на 1 год", "amount": 80000, "days": 365},
    }

    plan = periods.get(callback.data)
    if not plan:
        await callback.answer("Ошибка при выборе подписки", show_alert=True)
        return

    price = [LabeledPrice(label=plan["label"], amount=plan["amount"])]
    payload = f"sub:{plan['days']}"

    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title="Премиум-доступ к трендам",
        description=plan["label"],
        provider_token=PAY_TOKEN,
        currency="RUB",
        prices=price,
        start_parameter="premium_plan",
        payload=payload,
        need_email=False,
        is_flexible=False
    )
    await callback.answer()


# ========== ОПЛАТА ==========
@dp.pre_checkout_query(lambda q: True)
async def checkout(pre_checkout_q: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_q.id, ok=True)


@dp.message(lambda msg: msg.successful_payment is not None)
async def payment_done(message: Message):
    days = int(message.successful_payment.invoice_payload.split(":")[1])
    username = message.from_user.username or ""
    save_user_subscription(message.from_user.id, username, days)
    end = get_user_subscription_end(message.from_user.id)
    await message.answer(f"🎉 Готово! Вы открыли доступ к трендам.\n📅 Подписка действует до: <b>{end.strftime('%Y-%m-%d %H:%M:%S')}</b>", parse_mode="HTML")


# ========== СТАТУС ==========
@dp.message(lambda msg: msg.text == "/status")
async def status(message: Message):
    end = get_user_subscription_end(message.from_user.id)
    if end and end > datetime.now():
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="🔁 Продлить подписку", callback_data="open_buy_menu")
        keyboard.adjust(1)
        await message.answer(
            f"✨ Подписка подтверждена!\nВы с нами до: <b>{end.strftime('%Y-%m-%d %H:%M:%S')}</b>",
            reply_markup=keyboard.as_markup(),
            parse_mode="HTML"
        )
    else:
        await message.answer("😔 Подписка не найдена. Не упусти шанс — оформи доступ и будь в курсе самых прибыльных трендов! 🔥")


# ========== ТРЕНДЫ ==========
@dp.message(lambda msg: msg.text == "Amazon")
@premium_required
async def trends_amazon(message: Message):
    await message.answer("🛒 Отслеживаем горячие товары на Amazon — только то, что продаётся лучше всего! 🚀")
    trends = get_amazon_trends()
    if not trends:
        return await message.answer("😓 Что-то пошло не так... Не удалось загрузить тренды. Попробуйте позже — мы уже чиним! 🔧")
    for item in trends:
        caption = f"🔥 <b>{item['title']}</b>\n<a href='{item['product_link']}'>🛍️ Подробнее о товаре</a>"
        await bot.send_photo(message.chat.id, item['image_url'], caption=caption, parse_mode='HTML')


@dp.message(lambda msg: msg.text == "Shein")
@premium_required
async def trends_shein(message: Message):
    await message.answer("💃 Ловим тренды на Shein — стиль, который выбирают миллионы! 🌟")
    trends = get_shein_trends()
    if not trends:
        return await message.answer("😓 Что-то пошло не так... Не удалось загрузить тренды. Попробуйте позже — мы уже чиним! 🔧")
    for item in trends:
        caption = f"✨ <b>{item['title']}</b>\n💰 Цена: {item['price']}\n<a href='{item['product_link']}'>🛍️ Смотреть товар</a>"
        await bot.send_photo(message.chat.id, item['image_url'], caption=caption, parse_mode='HTML')
@dp.callback_query(lambda c: c.data.startswith("cat1688:"))
async def show_1688_by_category(callback: CallbackQuery):
    await callback.answer()  # важно сразу ответить, чтобы Telegram не ругался

    cat_name = callback.data.split(":", 1)[1]  # оригинальное китайское название

    # Переводим для красивого отображения
    try:
        translated = GoogleTranslator(source='auto', target='ru').translate(cat_name)
    except:
        translated = cat_name

    await callback.message.answer(f"🔍 Загружаю тренды из категории «{translated}»...")

    trends = await get_1688_trends_by_category(cat_name)

    if not trends:
        await callback.message.answer("❌ Не удалось получить тренды по этой категории.")
        return

    for item in trends:
        caption = (
            f"<b>{item['title']}</b>\n"
            f"💰 {item['price']}\n"
            f"🏢 Продавец: {item['company']}\n"
            f"<a href='{item['product_link']}'>🔗 Перейти к товару</a>"
        )
        await bot.send_photo(
            chat_id=callback.message.chat.id,
            photo=item['image_url'],
            caption=caption,
            parse_mode='HTML'
        )

@dp.message(lambda msg: msg.text == "1688")
async def choose_1688_category(message: types.Message):
    await message.answer("📦 Загружаю категории 1688...")
    category_dict = await get_1688_categories()


    if not category_dict:
        return await message.answer("❌ Не удалось получить список категорий.")

    keyboard = InlineKeyboardBuilder()
    for original, translated in category_dict.items():
        keyboard.button(text=translated, callback_data=f"cat1688:{original}")
    keyboard.adjust(2)

    await message.answer("🧭 Выбери категорию:", reply_markup=keyboard.as_markup())

    

@dp.message(lambda msg: msg.text == "Pinterest")
async def trends_pinterest(message: types.Message):
    await message.answer("🔥 Ищу тренды на Pinterest...")
    trends = await get_pinterest_trends()

    if not trends:
        await message.answer("❌ Не удалось получить тренды с Pinterest.")
        return

    for item in trends:
        caption = f"<b>{item['title']}</b>\n<a href='{item['pin_link']}'>🔗 Посмотреть на Pinterest</a>"
        await bot.send_photo(
            chat_id=message.chat.id,
            photo=item['image_url'],
            caption=caption,
            parse_mode='HTML'
        )
# ========== ЗАПУСК ==========
async def main():
    init_db()
    await bot.set_my_commands([
        BotCommand(command="/start", description="Запустить бота"),
        BotCommand(command="/status", description="Проверка подписки"),
    ])
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())




#условие на товары 