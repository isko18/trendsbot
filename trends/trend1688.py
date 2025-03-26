import requests
from bs4 import BeautifulSoup

def get_1688_trends():
    url = "https://www.1688.com/"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")

    items = soup.select(".hot-word-list a")
    result = "🔥 1688 Тренды:\n"
    for i, item in enumerate(items[:5], 1):
        result += f"{i}. {item.get_text(strip=True)}\n"
    return result