import random
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

async def get_1688_trends():
    url = "https://global.1688.com/?spm=a260k.home2024.centercontrol.dshangpin_kjzg_809152989389.663335e4SBWoVV&topOfferIds=809152989389"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # 💡 отключаем картинки, CSS, шрифты
        await page.route("**/*", lambda route, request: route.abort()
                         if request.resource_type in ["image", "stylesheet", "font"]
                         else route.continue_())

        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_selector("a.offer-item", timeout=5000)
        html = await page.content()
        await browser.close()

    soup = BeautifulSoup(html, "html.parser")
    all_items = soup.select("a.offer-item")

    items = random.sample(all_items, k=min(5, len(all_items)))
    trends = []

    for item in items:
        try:
            title = item.select_one(".offer-title").get_text(strip=True)
            image_url = item.select_one(".offer-img-container img")["src"]
            product_link = item["href"]
            price = item.select_one(".offer-price").get_text(strip=True) if item.select_one(".offer-price") else "Цена не указана"
            company = item.select_one(".company-name").get_text(strip=True) if item.select_one(".company-name") else "Без продавца"

            trends.append({
                "title": title,
                "image_url": image_url,
                "product_link": product_link,
                "price": price,
                "company": company
            })
        except Exception as e:
            print(f"❌ Ошибка при обработке товара: {e}")

    return trends
