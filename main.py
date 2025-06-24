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


def generate_telegram_message(new_ads, price_changes):
    lines = []

    if new_ads:
        lines.append("<b>🆕 New ads:</b>")
        for ad in new_ads:
            lines.append(f"🏠 <b>{ad['title']}</b>\n📍 {ad['location']}\n📏 {ad.get('kvadratura', '')}\n💶 {ad['price']}\n🔗 <a href='{ad['url']}'>Открыть</a>\n")

    if price_changes:
        lines.append("<b>💰 Price changes:</b>")
        for ad_id, changes in price_changes.items():
            current = changes['current']
            old_price = changes['previous_price']
            lines.append(f"🏠 <b>{current['title']}</b>\n📍 {current['location']}\n📏 {current.get('kvadratura', '')}\n💶 <s>{old_price}</s> → <b>{current['price']}</b>\n🔗 <a href='{current['url']}'>Открыть</a>\n")

    if not new_ads and not price_changes:
        lines.append("No new ads or price changes today.")

    return "\n".join(lines)


if __name__ == "__main__":
    current_ads = fetch_current_ads()
    current_ads_sorted = sort_ads_by_location_and_price(current_ads)
    previous_ads = load_previous_snapshot()
    save_daily_snapshot(current_ads_sorted)
    report_file = generate_report(current_ads_sorted, previous_ads)

    # Telegram message generation
    new_ads, removed_ads, price_changes = compare_ads(current_ads_sorted, previous_ads)
    telegram_message = generate_telegram_message(new_ads, price_changes)

    with open("telegram-message.txt", "w", encoding="utf-8") as f:
        f.write(telegram_message)

    print(f"Report saved: {report_file}")
    print("Telegram message generated.")

