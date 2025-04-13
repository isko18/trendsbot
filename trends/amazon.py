import requests
from bs4 import BeautifulSoup
import logging
import random
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_amazon_trends():
    url = "https://www.amazon.com/Best-Sellers/zgbs"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9"
    }

    logging.info(f"Отправка запроса на {url}")
    try:
        response = requests.get(url, headers=headers, timeout=15)
    except Exception as e:
        logging.error(f"Ошибка при запросе: {e}")
        return []

    if response.status_code != 200:
        logging.error(f"Ошибка получения данных с Amazon: статус-код {response.status_code}")
        return []

    if "To discuss automated access" in response.text or "captcha" in response.text.lower():
        logging.error("❌ Amazon заблокировал доступ — капча или антибот защита.")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    all_items = soup.select(".zg-carousel-general-faceout")

    if not all_items:
        logging.error("❌ Товары не найдены на странице Amazon.")
        return []

    items = random.sample(all_items, k=min(5, len(all_items)))
    trends = []

    for item in items:
        try:
            title_elem = item.select_one(".p13n-sc-truncate-desktop-type2") or item.select_one(".zg-text-center-align .a-link-normal")
            image_elem = item.select_one("img")  # иногда просто img
            link_elem = item.select_one("a.a-link-normal")
            price_elem = item.select_one(".p13n-sc-price")

            title = title_elem.get_text(strip=True) if title_elem else "Без названия"
            image_url = image_elem["src"] if image_elem and image_elem.get("src") else "https://via.placeholder.com/150"
            product_link = f"https://www.amazon.com{link_elem['href']}" if link_elem and link_elem.get("href") else "#"
            price = price_elem.get_text(strip=True) if price_elem else "Цена не указана"

            trends.append({
                'title': title,
                'image_url': image_url,
                'product_link': product_link,
                'price': price
            })

            logging.info(f"Найден товар: {title}")
        except Exception as e:
            logging.warning(f"⚠️ Пропущен товар из-за ошибки: {e}")
            continue

    return trends
