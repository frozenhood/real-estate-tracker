"""Backfill plot sizes for all known ads by scraping detail pages.

Reads ad IDs and URLs from every snapshot under data/, then fetches each
detail page and extracts the plot area from the embedded QuidditaEnvironment
JSON. Results are cached in plot-sizes.json keyed by ad id, so the script
is resumable and only fetches IDs not yet in the cache.
"""
from curl_cffi import requests
from bs4 import BeautifulSoup
import json
import os
import re
import sys
import time
from datetime import datetime

DATA_DIR = "data"
CACHE_FILE = "plot-sizes.json"
REQUEST_DELAY_SEC = 0.3
SAVE_EVERY = 25
TIMEOUT = 20

scraper = requests.Session(impersonate="chrome")

CLASSIFIED_RX = re.compile(r'CurrentClassified\s*=\s*(\{.*?\});', re.DOTALL)


def collect_ad_urls():
    """Walk every snapshot and return a dict id -> most-recent url."""
    url_map = {}
    for fn in sorted(os.listdir(DATA_DIR)):
        with open(os.path.join(DATA_DIR, fn), encoding="utf-8") as f:
            ads = json.load(f)
        for a in ads:
            i = str(a.get("id", "")).strip()
            u = a.get("url")
            if i and u:
                url_map[i] = u  # later snapshots overwrite — fine
    return url_map


def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_cache(cache):
    tmp = CACHE_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)
    os.replace(tmp, CACHE_FILE)


def extract_plot(html):
    """Return (plot_value, plot_unit) or (None, None) if not found."""
    m = CLASSIFIED_RX.search(html)
    if not m:
        return None, None
    try:
        obj = json.loads(m.group(1))
    except json.JSONDecodeError:
        return None, None
    other = obj.get("OtherFields") or {}
    val = other.get("povrsina_placa_d")
    unit = other.get("povrsina_placa_d_unit_s")
    if val is None:
        return None, None
    try:
        val = float(val)
    except (TypeError, ValueError):
        return None, None
    return val, unit


def fetch_one(url):
    """Return dict with status + extracted fields."""
    try:
        r = scraper.get(url, timeout=TIMEOUT)
    except Exception as e:
        return {"status": "error", "error": str(e)[:200]}
    if r.status_code != 200:
        return {"status": f"http_{r.status_code}"}
    val, unit = extract_plot(r.text)
    if val is None:
        return {"status": "no_plot_field"}
    return {"status": "ok", "plot_value": val, "plot_unit": unit}


def format_plot(entry):
    """Return a human-readable plot size string, or '' if not available."""
    if not entry or entry.get("status") != "ok":
        return ""
    val = entry.get("plot_value")
    unit = entry.get("plot_unit")
    if val is None:
        return ""
    if unit == "ar":
        m2 = val * 100
        return f"{val:g} ar (~{m2:,.0f} m²)".replace(",", ".")
    if unit == "ha":
        return f"{val:g} ha"
    if unit == "m2":
        return f"{val:,.0f} m²".replace(",", ".")
    return f"{val:g} {unit}"


def enrich_ads(ads, *, delay_sec=REQUEST_DELAY_SEC):
    """Enrich each ad dict with a 'plot' field (formatted string, may be '').

    Uses the on-disk cache. Fetches detail pages only for ads not yet cached.
    Persists the cache after each new fetch so partial runs aren't wasted.
    """
    cache = load_cache()
    new_fetches = 0
    for ad in ads:
        aid = str(ad.get("id", "")).strip()
        if not aid:
            ad["plot"] = ""
            continue
        if aid not in cache:
            url = ad.get("url")
            if not url:
                ad["plot"] = ""
                continue
            result = fetch_one(url)
            result["fetched_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cache[aid] = result
            new_fetches += 1
            save_cache(cache)
            time.sleep(delay_sec)
        ad["plot"] = format_plot(cache[aid])
    return new_fetches


def main():
    url_map = collect_ad_urls()
    cache = load_cache()
    todo = [(i, u) for i, u in url_map.items() if i not in cache]
    print(f"Total ads known:    {len(url_map)}")
    print(f"Already cached:     {len(cache)}")
    print(f"To fetch:           {len(todo)}")
    if not todo:
        print("Nothing to do.")
        return

    started = time.time()
    ok = 0
    failed = 0
    for n, (aid, url) in enumerate(todo, 1):
        result = fetch_one(url)
        result["fetched_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cache[aid] = result
        if result["status"] == "ok":
            ok += 1
        else:
            failed += 1

        if n % 10 == 0 or n == len(todo):
            elapsed = time.time() - started
            rate = n / elapsed if elapsed > 0 else 0
            eta = (len(todo) - n) / rate if rate > 0 else 0
            print(
                f"  [{n}/{len(todo)}] ok={ok} failed={failed} "
                f"rate={rate:.1f}/s eta={eta:.0f}s",
                flush=True,
            )
        if n % SAVE_EVERY == 0:
            save_cache(cache)
        time.sleep(REQUEST_DELAY_SEC)

    save_cache(cache)
    print(f"\nDone. ok={ok} failed={failed}")


if __name__ == "__main__":
    main()
