import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime, timedelta

FILTER_URL = "https://www.halooglasi.com/nekretnine/prodaja-kuca/beograd?cena_d_to=140000&cena_d_unit=4"
DATA_DIR = "data"
REPORT_DIR = "reports"
HISTORY_FILE = "price-history.json"


def fetch_ads_from_page(page):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    url = f"{FILTER_URL}&page={page}"
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, 'html.parser')
    ads = soup.find_all('div', class_='product-item')

    results = []

    for ad in ads:
        title_tag = ad.select_one('h3.product-title a')
        price_tag = ad.select_one('.central-feature i')
        location_tag = ad.select_one('ul.subtitle-places')
        location_parts = location_tag.find_all('li') if location_tag else []
        location_full = " | ".join([li.get_text(strip=True) for li in location_parts]) if location_parts else None

        publish_date_tag = ad.select_one('span.publish-date')
        advertiser_tag = ad.select_one('span[data-field-name="oglasivac_nekretnine_s"]')
        price_by_surface_tag = ad.select_one('div.price-by-surface span')
        ad_id = ad.get('data-id')

        url = title_tag['href'] if title_tag else None
        title = title_tag.get_text(strip=True) if title_tag else None
        price = price_tag.get_text(strip=True) if price_tag else None

        publish_date = publish_date_tag.get_text(strip=True) if publish_date_tag else None
        advertiser = advertiser_tag.get_text(strip=True) if advertiser_tag else None
        price_by_surface = price_by_surface_tag.get_text(strip=True) if price_by_surface_tag else None

        if url:
            full_url = f"https://www.halooglasi.com{url}"
            results.append({
                'id': ad_id,
                'url': full_url,
                'title': title,
                'price': price,
                'price_by_surface': price_by_surface,
                'location': location_full,
                'publish_date': publish_date,
                'advertiser': advertiser
            })

    return results


def fetch_current_ads():
    all_ads = []
    page = 1

    while True:
        ads = fetch_ads_from_page(page)
        if not ads:
            break
        all_ads.extend(ads)
        page += 1

    return all_ads


def sort_ads_by_location_and_price(ads):
    def extract_obshchina(location):
        parts = location.split('|') if location else []
        parts = [p.strip() for p in parts]
        return parts[1] if len(parts) >= 2 else ''

    def extract_price(ad):
        price_str = ad.get("price", "").replace("€", "").replace(".", "").replace(",", "").strip()
        try:
            return int(price_str)
        except ValueError:
            return float('inf')

    return sorted(
        ads,
        key=lambda ad: (extract_obshchina(ad.get("location")), extract_price(ad))
    )


def save_daily_snapshot(ads):
    date_str = datetime.now().strftime("%Y-%m-%d")
    os.makedirs(DATA_DIR, exist_ok=True)
    filename = os.path.join(DATA_DIR, f"{date_str}.json")
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(ads, f, indent=2, ensure_ascii=False)
    return filename


def load_previous_snapshot():
    if not os.path.exists(DATA_DIR):
        return []
    files = sorted(os.listdir(DATA_DIR))
    if len(files) < 2:
        return []
    with open(os.path.join(DATA_DIR, files[-2]), "r", encoding="utf-8") as f:
        return json.load(f)


def load_price_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_price_history(history):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


def generate_report(current_ads, previous_ads):
    current_dict = {ad['id']: ad for ad in current_ads}
    previous_dict = {ad['id']: ad for ad in previous_ads}

    added = [current_dict[k] for k in current_dict.keys() - previous_dict.keys()]
    removed = [previous_dict[k] for k in previous_dict.keys() - current_dict.keys()]

    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    recent_dates = {today.strftime("%d.%m.%Y."), yesterday.strftime("%d.%m.%Y.")}

    added_recent = [ad for ad in current_ads if ad['publish_date'] in recent_dates]

    price_changed = []
    history = load_price_history()
    date_str = datetime.now().strftime("%Y-%m-%d")

    for ad_id in current_dict.keys() & previous_dict.keys():
        current_ad = current_dict[ad_id]
        previous_ad = previous_dict[ad_id]
        if current_ad['price'] != previous_ad['price']:
            price_changed.append({
                "id": ad_id,
                "url": current_ad['url'],
                "title": current_ad['title'],
                "old_price": previous_ad['price'],
                "new_price": current_ad['price']
            })

        if ad_id not in history:
            history[ad_id] = []
        if not history[ad_id] or history[ad_id][-1]['price'] != current_ad['price']:
            history[ad_id].append({"date": date_str, "price": current_ad['price']})

    save_price_history(history)

    report = {
        "total_ads": len(current_ads),
        "added": added,
        "added_recent": added_recent,
        "removed": removed,
        "price_changed": price_changed
    }

    os.makedirs(REPORT_DIR, exist_ok=True)
    report_file = os.path.join(REPORT_DIR, f"{date_str}-changes.json")
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    return report_file


if __name__ == "__main__":
    current_ads = fetch_current_ads()
    current_ads_sorted = sort_ads_by_location_and_price(current_ads)
    previous_ads = load_previous_snapshot()
    save_daily_snapshot(current_ads_sorted)
    report_file = generate_report(current_ads_sorted, previous_ads)
    print(f"Report saved: {report_file}")

