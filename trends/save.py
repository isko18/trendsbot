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