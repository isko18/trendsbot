import requests
from bs4 import BeautifulSoup
import logging
import random
import re

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def get_shein_trends():
    url = "https://us.shein.com/top-trend?src_module=all&src_identifier=on%3DONE_THIRD_COMPONENT%60cn%3DWEEKLY%20WONDERS%60hz%3D0%60ps%3D1_1%60jc%3DtrendsChannel_0&src_tab_page_id=page_home1743247988882&ici=CCCSN%3Dall_ON%3DONE_THIRD_COMPONENT_OI%3D0_CN%3DONE_THIRD_TREND_ITEMS_TI%3D50000_aod%3D0_PS%3D1-1_ABT%3D0&contentCarrierId_adp=1664102_31226496,4618770_37149333,4616162_42334787,309413_41606614,1822069_42704868,315263_34199279&entry_from=page_home`1`all`ONE_THIRD_TREND_ITEMS&entranceType=h1"
    headers = {"User-Agent": "Mozilla/5.0"}
    logging.info(f"Отправка запроса на {url}")
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        logging.error(f"Ошибка получения данных с Shein: статус-код {response.status_code}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")

    items = soup.select("section.product-card")  # Берем все товары
    trends = []

    for item in items:
        title_elem = item.select_one(".goods-title-link")
        image_elem = item.select_one(".crop-image-container img")
        link_elem = item.select_one("a.S-product-card__img-container")

        title = title_elem.get_text(strip=True) if title_elem else "Без названия"
        image_url = image_elem.get("src") or image_elem.get("data-src") if image_elem else None
        product_id = link_elem.get("data-id") if link_elem else None

        # Очистка названия для ссылки
        if product_id and title != "Без названия":
            clean_title = re.sub(r"[^a-zA-Z0-9\s]", "", title)  # Удаляем все спецсимволы
            clean_title = re.sub(r"\s+", "-", clean_title.strip())  # Заменяем пробелы на "-"
            product_link = f"https://us.shein.com/{clean_title}-p-{product_id}.html"
        else:
            product_link = "Нет ссылки"

        # Проверяем корректность ссылки на изображение
        if image_url and image_url.startswith("//"):
            image_url = "https:" + image_url

        if image_url:
            trends.append({
                'title': title,
                'image_url': image_url,
                'product_link': product_link
            })

    # Если есть товары, выбираем 5 случайных
    if len(trends) > 5:
        trends = random.sample(trends, 5)  # Берем 5 случайных товаров

    for trend in trends:
        logging.info(f"Выбран случайный товар: {trend['title']}")

    return trends
