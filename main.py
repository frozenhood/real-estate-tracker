import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime, timedelta
import re

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

        kvadratura_tag = None
        for li in ad.select('ul.product-features li'):
            if 'Kvadratura' in li.get_text():
                kvadratura_tag = li.select_one('.value-wrapper')
                break

        kvadratura = kvadratura_tag.get_text(strip=True) if kvadratura_tag else None

        if kvadratura:
            match = re.search(r"[\d,.]+", kvadratura)
            kvadratura = match.group(0).replace(".", "").replace(",", ".") + " m2" if match else None

        url = title_tag['href'] if title_tag else None
        title = title_tag.get_text(strip=True) if title_tag else None
        price = price_tag.get_text(strip=True) if price_tag else None

        publish_date = publish_date_tag.get_text(strip=True) if publish_date_tag else None
        advertiser = advertiser_tag.get_text(strip=True) if advertiser_tag else None
        price_by_surface = price_by_surface_tag.get_text(strip=True) if price_by_surface_tag else None

        if url:
            full_url = f"https://www.halooglasi.com{url}"
            results.append({
                'title': title,
                'location': location_full,
                'kvadratura': kvadratura,
                'price': price,
                'price_by_surface': price_by_surface,
                'publish_date': publish_date,
                'advertiser': advertiser,
                'id': ad_id,
                'url': full_url
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

def remove_duplicates_by_id(ads):
    """Remove duplicate ads by id, keeping the first occurrence"""
    seen_ids = set()
    unique_ads = []
    for ad in ads:
        ad_id = str(ad['id']).strip()
        if ad_id not in seen_ids:
            seen_ids.add(ad_id)
            unique_ads.append(ad)
    return unique_ads

def generate_report(current_ads, previous_ads):
    # Remove duplicates before comparison
    current_ads_unique = remove_duplicates_by_id(current_ads)
    previous_ads_unique = remove_duplicates_by_id(previous_ads)
    
    # Always use string id and strip spaces for robust comparison
    current_dict = {str(ad['id']).strip(): ad for ad in current_ads_unique}
    previous_dict = {str(ad['id']).strip(): ad for ad in previous_ads_unique}

    # Load price history to determine truly new ads
    history = load_price_history()
    
    # Find ads that are truly new (not in history at all)
    truly_new_ads = []
    for ad_id, ad in current_dict.items():
        if ad_id not in history:
            truly_new_ads.append(ad)
    
    # Find ads that were in previous day but not in current day
    removed = [previous_dict[k] for k in previous_dict.keys() - current_dict.keys()]
    
    # Find ads with price changes
    price_changed = []
    date_str = datetime.now().strftime("%Y-%m-%d")

    for ad_id in current_dict.keys() & previous_dict.keys():
        current_ad = current_dict[ad_id]
        previous_ad = previous_dict[ad_id]
        if current_ad['price'] != previous_ad['price']:
            price_changed.append({
                "id": ad_id,
                "url": current_ad['url'],
                "title": current_ad['title'],
                "location": current_ad['location'],
                "kvadratura": current_ad['kvadratura'],
                "price": current_ad['price'],
                "old_price": previous_ad['price']
            })

        # Update history
        if ad_id not in history:
            history[ad_id] = []
        if not history[ad_id] or history[ad_id][-1]['price'] != current_ad['price']:
            history[ad_id].append({"date": date_str, "price": current_ad['price']})

    save_price_history(history)

    report = {
        "total_ads": len(current_ads),
        "added": truly_new_ads,  # Only truly new ads
        "removed": removed,
        "price_changed": price_changed
    }

    os.makedirs(REPORT_DIR, exist_ok=True)
    report_file = os.path.join(REPORT_DIR, f"{date_str}-changes.json")
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    return report_file, report

def generate_telegram_message(new_ads, price_changes):
    lines = []

    if new_ads:
        lines.append("<b>🆕 New ads:</b>")
        for ad in new_ads:
            lines.append(f"🏠 <b>{ad['title']}</b>\n📍 {ad['location']}\n📏 {ad.get('kvadratura', '')}\n💶 {ad['price']}\n🔗 <a href='{ad['url']}'>Open</a>\n")

    if price_changes:
        lines.append("<b>💰 Price changes:</b>")
        for ad_id, changes in price_changes.items():
            current = changes['current']
            old_price = changes['previous_price']
            lines.append(f"🏠 <b>{current['title']}</b>\n📍 {current['location']}\n📏 {current.get('kvadratura', '')}\n💶 <s>{old_price}</s> → <b>{current['price']}</b>\n🔗 <a href='{current['url']}'>Open</a>\n")

    if not new_ads and not price_changes:
        lines.append("No new ads or price changes today.")

    return "\n".join(lines)

if __name__ == "__main__":
    current_ads = fetch_current_ads()
    current_ads_sorted = sort_ads_by_location_and_price(current_ads)
    previous_ads = load_previous_snapshot()
    save_daily_snapshot(current_ads_sorted)
    report_file, report_data = generate_report(current_ads_sorted, previous_ads)

    # Telegram message generation
    new_ads = report_data.get("added", [])
    price_changes = {
        entry["id"]: {"current": entry, "previous_price": entry["old_price"]}
        for entry in report_data.get("price_changed", [])
    }
    telegram_message = generate_telegram_message(new_ads, price_changes)

    with open("telegram-message.txt", "w", encoding="utf-8") as f:
        f.write(telegram_message)

    print(f"Report saved: {report_file}")
    print("Telegram message generated.")
