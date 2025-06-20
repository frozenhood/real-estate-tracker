import requests
from bs4 import BeautifulSoup

FILTER_URL = "https://www.halooglasi.com/nekretnine/prodaja-kuca?grad_id_l-lokacija_id_l-mikrolokacija_id_l=40381%2C528336%2C529392%2C530392%2C531045%2C40761%2C35237&cena_d_to=140000&cena_d_unit=4"


def fetch_current_ads():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    response = requests.get(FILTER_URL, headers=headers, timeout=10)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, 'html.parser')

    ads = soup.find_all('div', class_='product-item')

    results = []

    for ad in ads:
        title_tag = ad.select_one('h3.product-title a')
        price_tag = ad.select_one('.central-feature i')
        location_tag = ad.select_one('ul.subtitle-places')

        url = title_tag['href'] if title_tag else None
        title = title_tag.text.strip() if title_tag else None
        price = price_tag.text.strip() if price_tag else None
        location = location_tag.text(separator=' | ', strip=True) if location_tag else None

        if url:
            full_url = f"https://www.halooglasi.com{url}"
            results.append({
                'url': full_url,
                'title': title,
                'price': price,
                'location': location,
            })

    return results

def main():
    ads = fetch_current_ads()
    print(f"Found {len(ads)} ads:\n")
    for ad in ads:
        print(f"{ad['price']} | {ad['location']}\n{ad['title']}\n{ad['url']}\n")

if __name__ == "__main__":
    main()