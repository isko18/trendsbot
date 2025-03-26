import requests
from bs4 import BeautifulSoup

def get_amazon_trends():
    url = "https://www.amazon.com/Best-Sellers/zgbs"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")

    titles = soup.select("div.p13n-sc-truncate") or soup.select("._cDEzb_p13n-sc-css-line-clamp-1_1Fn1y")
    result = "🔥 Amazon Best Sellers:\n"
    for i, title in enumerate(titles[:5], 1):
        result += f"{i}. {title.get_text(strip=True)}\n"
    return result
