import requests
import json
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


# Формируем корректную ссылку на продукт Shein
def generate_shein_link(goods_url_name, goods_id):
    if not goods_id or not goods_url_name:
        return None

    return f"https://us.shein.com/{goods_url_name}-p-{goods_id}.html"


# Основная функция для получения трендов Shein через API
def get_shein_trends():
    url = "https://us.shein.com/bff-api/product/trending_channel/trending_products_recommend?_ver=1.1.8&_lang=en&adp=37824789,37149333,30718430,27595779,42334787,26898704&limit=5&page=1"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
        "accept": "application/json, text/plain, */*",
        "origin": "https://us.shein.com",
        "referer": "https://us.shein.com/top-trend",
        "content-type": "application/json;charset=UTF-8",
        "sec-fetch-site": "same-origin",
        "sec-fetch-mode": "cors",
        "sec-fetch-dest": "empty",
        "x-requested-with": "XMLHttpRequest",
    }

    logging.info(f"Отправка запроса к API Shein: {url}")
    response = requests.post(url, headers=headers)

    if response.status_code != 200:
        logging.error(f"Ошибка запроса к API Shein: статус-код {response.status_code}")
        return []

    try:
        data = response.json()
        products = data.get("info", {}).get("products", [])
    except (json.JSONDecodeError, KeyError):
        logging.error("❌ Ошибка при разборе ответа API Shein.")
        return []

    if not products:
        logging.error("❌ Товары не найдены в API-ответе.")
        return []

    trends = []

    for item in products[:5]:  # Ограничиваем до 5 товаров
        title = item.get("goods_name", "Без названия")
        image_url = f"https:{item.get('goods_img')}" if item.get("goods_img") else None
        product_link = generate_shein_link(item.get("goods_url_name"), item.get("goods_id"))
        price = item.get("salePrice", {}).get("amountWithSymbol", "Нет цены")

        if image_url and product_link:
            trends.append({
                "title": title,
                "image_url": image_url,
                "product_link": product_link,
                "price": price,
            })

        logging.info(f"Найден товар: {title}")

    return trends
