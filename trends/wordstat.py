# save_cookies.py
from playwright.sync_api import sync_playwright
import pickle

def save_cookies():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.goto("https://wordstat.yandex.ru")

        print("🔐 Войди вручную и нажми Enter...")
        input("⏳ Жду подтверждение...")

        cookies = context.cookies()
        with open("yandex_cookies.pkl", "wb") as f:
            pickle.dump(cookies, f)

        print("✅ Cookies сохранены.")
        browser.close()

save_cookies()
import pickle
from playwright.async_api import async_playwright

async def get_wordstat_count(query: str) -> str:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()

        # Загружаем сохранённые куки (авторизация)
        with open("yandex_cookies.pkl", "rb") as f:
            cookies = pickle.load(f)
        await context.add_cookies(cookies)

        page = await context.new_page()
        await page.goto("https://wordstat.yandex.ru")

        # Вводим запрос и жмем кнопку
        await page.fill("input.textinput__control", query)
        await page.click("button.wordstat__search-button")

        try:
            # Ждём таблицу с результатами
            await page.wait_for_selector("tr.table__even_highlighted", timeout=10000)
        except:
            await browser.close()
            return f"⚠️ Не удалось загрузить данные Wordstat. Попробуй позже."

        rows = await page.locator("tr.table__even_highlighted").all()

        for row in rows:
            word = await row.locator("td:nth-child(1)").inner_text()
            count = await row.locator("td:nth-child(2)").inner_text()
            if query.lower() in word.lower():
                await browser.close()
                return f"🔍 <b>{word.strip()}</b>\n📈 <b>{count.strip()} показов</b>"

        await browser.close()
        return f"📉 Нет данных по фразе: <b>{query}</b>"