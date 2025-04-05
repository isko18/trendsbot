import requests
from bs4 import BeautifulSoup
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_pinterest_trends():
    url = "https://www.pinterest.com/search/pins/?q=%D1%81%D0%B0%D0%BC%D1%8B%D0%B5%20%D0%BF%D1%80%D0%BE%D0%B4%D0%B0%D0%B2%D0%B0%D0%B5%D0%BC%D1%8B%D0%B5%20%D1%82%D0%BE%D0%B2%D0%B0%D1%80%D1%8B%202025&rs=typed"
    headers = {"User-Agent": "Mozilla/5.0"}
    logging.info(f"Отправка запроса на {url}")
    
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        logging.error(f"Ошибка получения данных с Pinterest: статус-код {response.status_code}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")

    items = soup.select("div.GrowthUnauthPinImage")[:5]
    trends = []

    for item in items:
        img_elem = item.select_one("img")
        link_elem = item.find_parent("a")

        title = img_elem["alt"] if img_elem and "alt" in img_elem.attrs else "Без названия"
        image_url = img_elem["src"] if img_elem else None
        product_link = f"https://www.pinterest.com{link_elem['href']}" if link_elem else None

        if image_url:
            trends.append({
                'title': title,
                'image_url': image_url,
                'product_link': product_link
            })

        logging.info(f"Найден товар: {title}")

    return trends
