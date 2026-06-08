import os
import json
import re
import requests
from pathlib import Path
from html import unescape

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

STATE_FILE = Path("seen.json")
CONFIG_FILE = Path("config.json")


def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    r = requests.post(url, json={
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "disable_web_page_preview": False
    }, timeout=20)
    print(r.status_code, r.text)


def load_seen():
    if STATE_FILE.exists():
        return set(json.loads(STATE_FILE.read_text()))
    return set()


def save_seen(seen):
    STATE_FILE.write_text(json.dumps(sorted(list(seen)), indent=2))


def load_config():
    return json.loads(CONFIG_FILE.read_text())


def fetch_url(url):
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "pl-PL,pl;q=0.9,en;q=0.8"
    }
    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    return r.text


def find_links(html, domain):
    links = set()

    for match in re.findall(r'href="([^"]+)"', html):
        link = unescape(match)

        if domain == "olx":
            if "/d/oferta/" in link:
                if link.startswith("/"):
                    link = "https://www.olx.pl" + link
                links.add(link.split("?")[0])

        if domain == "vinted":
            if "/items/" in link:
                if link.startswith("/"):
                    link = "https://www.vinted.pl" + link
                links.add(link.split("?")[0])

    return list(links)


def check_source(source, seen):
    name = source["name"]
    platform = source["platform"]
    url = source["url"]

    print(f"Checking {name}: {url}")

    html = fetch_url(url)
    links = find_links(html, platform)

    print(f"Found {len(links)} links")

    new_links = []

    for link in links[:20]:
        key = f"{platform}:{link}"
        if key not in seen:
            new_links.append(link)
            seen.add(key)

    if new_links:
        for link in new_links[:5]:
            send_telegram(
                f"🔔 Nowe ogłoszenie\n\n"
                f"Źródło: {name}\n"
                f"Platforma: {platform.upper()}\n\n"
                f"{link}"
            )
    else:
        print("No new listings")


def main():
    config = load_config()
    seen = load_seen()

    for source in config["sources"]:
        try:
            check_source(source, seen)
        except Exception as e:
            send_telegram(f"⚠️ Błąd przy sprawdzaniu {source['name']}:\n{e}")

    save_seen(seen)


if __name__ == "__main__":
    main()
