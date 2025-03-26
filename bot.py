import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from config import BOT_TOKEN
from trends.amazon import get_amazon_trends
from trends.shein import get_shein_trends
from trends.trend1688 import get_1688_trends
from trends.pinterest import get_pinterest_trends

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

keyboard = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="Amazon"), KeyboardButton(text="Shein")],
    [KeyboardButton(text="1688"), KeyboardButton(text="Pinterest")]
], resize_keyboard=True)

@dp.message(lambda msg: msg.text == "/start")
async def start(message: types.Message):
    await message.answer("Привет! Я бот, который находит тренды с маркетплейсов. Нажми /trends, чтобы начать.")

@dp.message(lambda msg: msg.text == "/trends")
async def show_sources(message: types.Message):
    await message.answer("Выбери источник трендов:", reply_markup=keyboard)

@dp.message(lambda msg: msg.text == "Amazon")
async def trends_amazon(message: types.Message):
    await message.answer("Ищу тренды на Amazon...")
    trends = get_amazon_trends()
    await message.answer(trends)

@dp.message(lambda msg: msg.text == "Shein")
async def trends_shein(message: types.Message):
    await message.answer("Ищу тренды на Shein...")
    trends = get_shein_trends()
    await message.answer(trends)

@dp.message(lambda msg: msg.text == "1688")
async def trends_1688(message: types.Message):
    await message.answer("Ищу тренды на 1688...")
    trends = get_1688_trends()
    await message.answer(trends)

@dp.message(lambda msg: msg.text == "Pinterest")
async def trends_pinterest(message: types.Message):
    await message.answer("Ищу тренды на Pinterest...")
    trends = get_pinterest_trends()
    await message.answer(trends)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())