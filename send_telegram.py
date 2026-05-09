import glob
import json
import os
import urllib.error
import urllib.parse
import urllib.request

from main import generate_telegram_message

CHUNK_LIMIT = 3800


def split_for_telegram(text, limit=CHUNK_LIMIT):
    paragraphs = text.split("\n\n")
    chunks = []
    current = ""
    for p in paragraphs:
        candidate = (current + "\n\n" + p) if current else p
        if len(candidate) <= limit:
            current = candidate
            continue
        if current:
            chunks.append(current)
        while len(p) > limit:
            chunks.append(p[:limit])
            p = p[limit:]
        current = p
    if current:
        chunks.append(current)
    return chunks


def send_chunk(token, chat_id, text):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode(
        {"chat_id": chat_id, "parse_mode": "HTML", "text": text}
    ).encode()
    try:
        with urllib.request.urlopen(url, data=data, timeout=30) as r:
            body = json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = json.loads(e.read())
        raise RuntimeError(f"Telegram API HTTP {e.code}: {body}")
    if not body.get("ok"):
        raise RuntimeError(f"Telegram API error: {body}")


def main():
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]

    reports = sorted(glob.glob("reports/*-changes.json"))
    if not reports:
        print("No reports found, nothing to send")
        return

    with open(reports[-1]) as f:
        report = json.load(f)

    new_ads = report.get("added", [])
    price_changes = {
        e["id"]: {"current": e, "previous_price": e["old_price"]}
        for e in report.get("price_changed", [])
    }
    message = generate_telegram_message(new_ads, price_changes)

    chunks = split_for_telegram(message)
    print(f"Sending {len(chunks)} chunk(s), total {len(message)} chars")
    for i, chunk in enumerate(chunks, 1):
        send_chunk(token, chat_id, chunk)
        print(f"  chunk {i}/{len(chunks)} ({len(chunk)} chars) sent")


if __name__ == "__main__":
    main()
