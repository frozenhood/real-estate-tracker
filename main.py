import requests
from bs4 import BeautifulSoup
import json
from pathlib import Path

FILTER_URL = "https://www.halooglasi.com/nekretnine/prodaja-kuca?grad_id_l-lokacija_id_l-mikrolokacija_id_l=40381%2C528336%2C529392%2C530392%2C531045%2C40761%2C35237&cena_d_to=140000&cena_d_unit=4"

DATA_FILE = Path("urls.json")
REMOVED_FILE = Path("removed_urls.json")

def fetch_current_urls():
    response = requests.get(FILTER_URL)
    soup = BeautifulSoup(response.text, 'html.parser')
    return [
        a['href']
        for a in soup.select('a.product-title')
        if a.has_attr('href')
    ]

def load_previous_urls():
    if DATA_FILE.exists():
        with open(DATA_FILE, 'r') as f:
            return set(json.load(f))
    return set()

def save_urls(urls, path):
    with open(path, 'w') as f:
        json.dump(list(urls), f, indent=2)

def main():
    current_urls = set(fetch_current_urls())
    previous_urls = load_previous_urls()
    removed = previous_urls - current_urls

    print(f"Найдено {len(removed)} удалённых ссылок")

    save_urls(current_urls, DATA_FILE)

    if removed:
        print("\nУдалённые ссылки:")
        for url in removed:
            print(url)
        save_urls(removed, REMOVED_FILE)

if __name__ == "__main__":
    main()