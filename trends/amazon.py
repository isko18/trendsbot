from playwright.async_api import async_playwright
import random

async def get_amazon_trends():
    trends = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ))

        page = await context.new_page()
        await page.goto("https://www.amazon.com/Best-Sellers/zgbs", timeout=60000)
        await page.wait_for_selector(".zg-grid-general-faceout, .zg-carousel-general-faceout", timeout=15000)

        items = await page.query_selector_all(".zg-grid-general-faceout, .zg-carousel-general-faceout")

        if not items:
            print("❌ Не удалось найти товары.")
            await browser.close()
            return []

        sampled_items = random.sample(items, k=min(5, len(items)))

        for item in sampled_items:
            try:
                title_elem = await item.query_selector("img") or await item.query_selector("a")
                title_text = await title_elem.get_attribute("alt") if title_elem else "Без названия"

                image = await item.query_selector("img")
                image_url = await image.get_attribute("src") if image else "https://via.placeholder.com/150"

                link = await item.query_selector("a")
                href = await link.get_attribute("href") if link else "#"
                product_link = f"https://www.amazon.com{href}" if href and href.startswith("/") else href or "#"

                price_elem = await item.query_selector(".p13n-sc-price")
                price = await price_elem.inner_text() if price_elem else "Цена не указана"

                trends.append({
                    'title': title_text,
                    'image_url': image_url,
                    'product_link': product_link,
                    'price': price
                })

            except Exception as e:
                print(f"⚠️ Ошибка при обработке товара: {e}")
                continue

        await browser.close()
    return trends
