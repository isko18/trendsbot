import requests
from bs4 import BeautifulSoup

def get_pinterest_trends():
    url = "https://www.pinterest.com/trending/"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")

    items = soup.select("h3")
    result = "🔥 Pinterest тренды:\n"
    for i, item in enumerate(items[:5], 1):
        result += f"{i}. {item.get_text(strip=True)}\n"
    return result
