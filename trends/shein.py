import requests
from bs4 import BeautifulSoup

def get_shein_trends():
    url = "https://www.shein.com/Top-Sellers-Sc-001.html"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")

    items = soup.select(".product-card__info span.name")
    result = "🔥 Shein тренды:\n"
    for i, item in enumerate(items[:5], 1):
        result += f"{i}. {item.get_text(strip=True)}\n"
    return result
