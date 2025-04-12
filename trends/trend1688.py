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
    translator = GoogleTranslator(source='auto', target='ru')

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            await page.goto(BASE_URL, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_selector(".pc-venue-recommend--categoryItem--1-S7oI6", timeout=10000)

            # Клик по нужной категории
            await page.locator(".pc-venue-recommend--categoryItem--1-S7oI6", has_text=category_name.strip()).click()
            await page.wait_for_timeout(2000)

            # Скроллим к нужному блоку
            await page.locator('[id="381063652735401"]').scroll_into_view_if_needed()
            await page.mouse.wheel(0, 1500)
            await page.wait_for_timeout(2000)

            # Ждём появления карточек
            await page.wait_for_selector('#\\33 81063652735401 .pc-venue-recommend--productList--1zf8r21 > .pc-venue-recommend--cardItem--2GZieDa', timeout=10000)

            # Получаем HTML блока
            html = await page.eval_on_selector('[id="381063652735401"]', "el => el.outerHTML")

        except Exception as e:
            print("❌ Ошибка при загрузке трендов:", e)
            await browser.close()
            return []

        await browser.close()

    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select(".pc-venue-recommend--productList--1zf8r21 > .pc-venue-recommend--cardItem--2GZieDa")

    trends = []
    for card in cards[:5]:
        try:
            title_tag = card.select_one(".pc-venue-recommend--title--1SH-UhM")
            image_tag = card.select_one("img.pc-venue-recommend--cardImg--Bbz2Eyk")
            link_tag = card.select_one("a.pc-venue-recommend--cardBox--14KaPCf")
            priceA = card.select_one(".pc-venue-recommend--priceNumA--1cFOcI5")
            priceB = card.select_one(".pc-venue-recommend--priceNumB--2DsAtei")

            if not title_tag or not image_tag or not link_tag:
                continue

            raw_title = title_tag.get_text(strip=True)
            translated_title = translator.translate(raw_title)

            image_url = image_tag.get("data-src") or image_tag.get("src") or "https://via.placeholder.com/150"
            product_link = link_tag.get("href", "#")
            price = f"¥{priceA.text.strip()}.{priceB.text.strip()}" if priceA and priceB else "Цена не указана"

            trends.append({
                "title": translated_title,
                "image_url": image_url,
                "product_link": product_link,
                "price": price,
                "company": "1688"
            })

        except Exception as e:
            print(f"❌ Ошибка при парсинге карточки: {e}")

    return trends
