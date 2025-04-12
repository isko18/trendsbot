import random
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

async def get_pinterest_trends():
    url = "https://www.pinterest.com/search/pins/?q=самые%20продаваемые%20товары%202025"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Отключаем ненужные ресурсы
        await page.route("**/*", lambda route, request: route.abort()
                         if request.resource_type in ["image", "stylesheet", "font"]
                         else route.continue_())

        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(5000)  # дать странице подгрузиться
        html = await page.content()
        await browser.close()

    soup = BeautifulSoup(html, "html.parser")
    pin_items = soup.select("div[data-test-id='pin']")  # ищем пины

    pins = random.sample(pin_items, k=min(5, len(pin_items)))
    results = []

    for pin in pins:
        try:
            link_tag = pin.find("a", href=True)
            if not link_tag:
                continue
            pin_link = "https://www.pinterest.com" + link_tag["href"]
            title = link_tag.get("aria-label") or "Без названия"
            image_tag = pin.find("img")
            image_url = image_tag["src"] if image_tag else "Изображение не найдено"
            description = image_tag.get("alt", "Описание не указано") if image_tag else "Описание не указано"

            results.append({
                "title": title,
                "image_url": image_url,
                "pin_link": pin_link,
                "description": description
            })
        except Exception as e:
            print(f"❌ Ошибка при обработке пина: {e}")

    return results
