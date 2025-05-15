from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator

BASE_URL = "https://mindx.1688.com/rcyy/xfxrcym/d9zcxdzkq/index.html?spm=a2637j.22917583.34492506.1.e10724fe1k8M1m&wh_pha=true&wh_pid=3810636"

STATIC_CATEGORIES = {
    "为你推荐": "Рекомендовано для вас",
    "数码电脑": "Цифровая электроника",
    "办公文化": "Офис и канцтовары",
    "日用餐厨": "Кухня и быт",
    "收纳清洁": "Хранение и уборка",
    "运动户外": "Спорт и туризм",
    "宠物园艺": "Животные и сад",
    "服饰配件": "Аксессуары",
    "个护家清": "Личная гигиена",
    "家纺家饰": "Домашний текстиль",
    "家用电器": "Бытовая техника",
    "居家日用": "Домашние товары",
    "护肤彩妆": "Уход и макияж",
    "内衣": "Нижнее белье",
    "潮流服饰": "Модная одежда"
}


async def get_1688_categories() -> dict[str, str]:
    return STATIC_CATEGORIES


async def get_1688_trends_by_category(category_name: str):
    translator = GoogleTranslator(source='zh-CN', target='ru')

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(BASE_URL, wait_until="domcontentloaded", timeout=20000)

            # Клик по категории
            category_button = page.locator(".pc-venue-recommend--categoryItem--1-S7oI6", has_text=category_name.strip())
            await category_button.click(timeout=5000)

            # Подскроллим и подождём
            await page.mouse.wheel(0, 1500)
            await page.wait_for_selector('#\\33 81063652735401 .pc-venue-recommend--cardItem--2GZieDa', timeout=10000)

            # Получаем HTML
            html = await page.eval_on_selector('[id="381063652735401"]', "el => el.outerHTML")
            await browser.close()
    except Exception as e:
        print(f"❌ Ошибка при загрузке трендов: {e}")
        return []

    # Парсинг HTML
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select(".pc-venue-recommend--productList--1zf8r21 > .pc-venue-recommend--cardItem--2GZieDa")

    trends = []
    for card in cards[:5]:  # до 5 карточек
        try:
            title = card.select_one(".pc-venue-recommend--title--1SH-UhM")
            img = card.select_one("img.pc-venue-recommend--cardImg--Bbz2Eyk")
            link = card.select_one("a.pc-venue-recommend--cardBox--14KaPCf")
            priceA = card.select_one(".pc-venue-recommend--priceNumA--1cFOcI5")
            priceB = card.select_one(".pc-venue-recommend--priceNumB--2DsAtei")

            if not (title and img and link):
                continue

            trends.append({
                "title": translator.translate(title.get_text(strip=True)),
                "image_url": img.get("data-src") or img.get("src") or "https://via.placeholder.com/150",
                "product_link": link.get("href", "#"),
                "price": f"¥{priceA.get_text(strip=True)}.{priceB.get_text(strip=True)}" if priceA and priceB else "Цена не указана",
                "company": "1688"
            })
        except Exception as e:
            print(f"⚠️ Пропущена карточка: {e}")
            continue

    return trends
