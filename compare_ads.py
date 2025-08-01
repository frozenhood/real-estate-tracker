import json
import os

# Load ads from file
def load_ads(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_price_history():
    if os.path.exists("price-history.json"):
        with open("price-history.json", "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

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

# Main comparison logic
if __name__ == "__main__":
    # Load data for 29th and 30th July
    ads_29 = load_ads('data/2025-07-29.json')
    ads_30 = load_ads('data/2025-07-30.json')
    
    # Load price history
    history = load_price_history()

    # Remove duplicates before comparison
    ads_29_unique = remove_duplicates_by_id(ads_29)
    ads_30_unique = remove_duplicates_by_id(ads_30)

    # Build dicts by id (as string, stripped)
    dict_29 = {str(ad['id']).strip(): ad for ad in ads_29_unique}
    dict_30 = {str(ad['id']).strip(): ad for ad in ads_30_unique}

    # Find truly new ads (not in history)
    truly_new_30 = []
    for ad_id, ad in dict_30.items():
        if ad_id not in history:
            truly_new_30.append(ad)

    # Old method: compare with previous day
    added_old_method = set(dict_30.keys()) - set(dict_29.keys())

    # Check price changes (new method vs old method)
    price_changed_new = []
    price_changed_old = []
    
    # New method: compare with previous day (correct logic)
    for ad_id in dict_30.keys() & dict_29.keys():
        current_ad = dict_30[ad_id]
        previous_ad = dict_29[ad_id]
        if current_ad['price'] != previous_ad['price']:
            price_changed_new.append({
                "id": ad_id,
                "title": current_ad['title'],
                "price": current_ad['price'],
                "old_price": previous_ad['price']
            })
    
    # Old method: compare with history (this was wrong)
    for ad_id, ad in dict_30.items():
        if ad_id in history and history[ad_id]:
            last_price = history[ad_id][-1]['price']
            if ad['price'] != last_price:
                price_changed_old.append({
                    "id": ad_id,
                    "title": ad['title'],
                    "price": ad['price'],
                    "old_price": last_price
                })

    print(f"Total in 29 (before dedup): {len(ads_29)}")
    print(f"Total in 30 (before dedup): {len(ads_30)}")
    print(f"Total in 29 (after dedup): {len(dict_29)}")
    print(f"Total in 30 (after dedup): {len(dict_30)}")
    print(f"Added (old method): {len(added_old_method)}")
    print(f"Truly new (using history): {len(truly_new_30)}")
    print(f"Price changed (new method): {len(price_changed_new)}")
    print(f"Price changed (old method): {len(price_changed_old)}")

    # Print truly new ads
    print("\nTruly new ads:")
    for ad in truly_new_30:
        print(f"  {ad['id']}: {ad['title']}")
    
    # Print price changes
    print("\nPrice changes (new method):")
    for change in price_changed_new:
        print(f"  {change['id']}: {change['title']} - {change['old_price']} → {change['price']}")
    
    print("\nPrice changes (old method):")
    for change in price_changed_old:
        print(f"  {change['id']}: {change['title']} - {change['old_price']} → {change['price']}")

    # For debug: check if any id is duplicated in source files
    def check_duplicates(ad_list, label):
        seen = set()
        dups = set()
        for ad in ad_list:
            adid = str(ad['id']).strip()
            if adid in seen:
                dups.add(adid)
            seen.add(adid)
        if dups:
            print(f"Duplicates in {label}: {dups}")
        else:
            print(f"No duplicates in {label}")

    check_duplicates(ads_29, '2025-07-29')
    check_duplicates(ads_30, '2025-07-30')

    # Check specific problematic ids
    problematic_ids = ["5425645730094", "5425643509702"]
    for pid in problematic_ids:
        in_29 = pid in dict_29
        in_30 = pid in dict_30
        print(f"ID {pid}: in_29={in_29}, in_30={in_30}")
        if in_29:
            print(f"  In 29: {dict_29[pid]['title']}")
        if in_30:
            print(f"  In 30: {dict_30[pid]['title']}") 