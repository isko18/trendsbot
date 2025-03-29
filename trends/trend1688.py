import requests
from bs4 import BeautifulSoup
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_1688_trends():
    url = "https://1688.ru/search?s=%D1%82%D1%80%D0%B5%D0%BD%D0%B4"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8"
    }
    logging.info(f"Отправка запроса на {url}")
    
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        logging.error(f"Ошибка получения данных с 1688: статус-код {response.status_code}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")

    # Поиск товаров в блоках с классом .product-item
    items = soup.select(".product-item")[:5]  # Ограничиваем до 5 товаров
    trends = []

    for item in items:
        title_elem = item.select_one(".product-title")
        image_elem = item.select_one(".product-image img")
        link_elem = item.select_one("a.item-product")

        title = title_elem.get_text(strip=True) if title_elem else "Без названия"
        image_url = image_elem["src"] if image_elem else None
        product_link = f"https://1688.ru{link_elem['href']}" if link_elem else None

        # Добавляем в список только если есть изображение и ссылка
        if image_url and product_link:
            trends.append({
                'title': title,
                'image_url': image_url,
                'product_link': product_link
            })

        logging.info(f"Найден товар: {title}")

    return trends