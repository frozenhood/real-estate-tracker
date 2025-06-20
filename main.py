import requests
from bs4 import BeautifulSoup
import json
from pathlib import Path

FILTER_URL = "https://www.halooglasi.com/nekretnine/prodaja-kuca?grad_id_l-lokacija_id_l-mikrolokacija_id_l=40381%2C528336%2C529392%2C530392%2C531045%2C40761%2C35237&cena_d_to=140000&cena_d_unit=4"

DATA_FILE = Path("urls.json")
REMOVED_FILE = Path("removed_urls.json")

def fetch_current_urls():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        response = requests.get(FILTER_URL, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error loading page: {e}")
        return set()

    # Print first 1000 characters of HTML to see what we get
    print(response.text[:1000])

    soup = BeautifulSoup(response.text, 'html.parser')
    urls = {
        a['href']
        for a in soup.select('a.product-title')
        if a.has_attr('href')
    }
    return urls

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

    print(f"Found {len(removed)} removed links")

    save_urls(current_urls, DATA_FILE)

    if removed:
        print("\nRemoved links:")
        for url in removed:
            print(url)
        save_urls(removed, REMOVED_FILE)

if __name__ == "__main__":
    main()