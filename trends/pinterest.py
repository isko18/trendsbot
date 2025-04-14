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
        await page.wait_for_timeout(8000)  # дать больше времени на подгрузку
        html = await page.content()
        await browser.close()

    soup = BeautifulSoup(html, "html.parser")

    # Новый селектор: ищем изображения внутри пинов с ссылкой
    pin_imgs = soup.select("a[href*='/pin/'] img")
    print(f"🔍 Найдено пинов: {len(pin_imgs)}")

    # Выбираем максимум 5 случайных
    selected = random.sample(pin_imgs, k=min(5, len(pin_imgs)))
    results = []

    for img_tag in selected:
        try:
            image_url = img_tag.get("src")
            description = img_tag.get("alt", "Описание не указано")
            link_tag = img_tag.find_parent("a")
            pin_link = "https://www.pinterest.com" + link_tag["href"] if link_tag and link_tag.get("href") else "#"

            results.append({
                "title": description[:50] or "Без названия",
                "image_url": image_url,
                "product_link": pin_link,
                "description": description
            })
        except Exception as e:
            print(f"❌ Ошибка при обработке пина: {e}")

    return results
