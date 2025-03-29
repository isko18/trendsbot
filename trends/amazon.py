import requests
from bs4 import BeautifulSoup
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_amazon_trends():
    url = "https://www.amazon.com/Best-Sellers/zgbs"
    headers = {"User-Agent": "Mozilla/5.0"}
    logging.info(f"Отправка запроса на {url}")
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        logging.error(f"Ошибка получения данных с Amazon: статус-код {response.status_code}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")

    items = soup.select(".zg-carousel-general-faceout")[:5]
    trends = []

    for item in items:
        title_elem = item.select_one(".p13n-sc-truncate-desktop-type2")
        image_elem = item.select_one("img.p13n-product-image")
        link_elem = item.select_one("a.a-link-normal")

        title = title_elem.get_text(strip=True) if title_elem else "Без названия"
        image_url = image_elem["src"] if image_elem else None
        product_link = f"https://www.amazon.com{link_elem['href']}" if link_elem else None

        if image_url:
            trends.append({
                'title': title,
                'image_url': image_url,
                'product_link': product_link
            })

        logging.info(f"Найден товар: {title}")

    return trends