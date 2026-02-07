import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
import os

SEARCH_URL = "https://rent.placesforpeople.co.uk/properties.aspx?loc=Watford&lat=51.66112829999999&lon=-0.3970199&mil=50&max=9999&bed=1&typ=0&pag=1"


EMAIL_FROM = os.environ.get("ALERT_EMAIL_FROM")
EMAIL_TO = os.environ.get("ALERT_EMAIL_TO")
SMTP_SERVER = os.environ.get("SMTP_SERVER")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER")
SMTP_PASS = os.environ.get("SMTP_PASS")

STATE_FILE = "seen_properties.txt"


def load_seen_ids():
    if not os.path.exists(STATE_FILE):
        return set()
    with open(STATE_FILE, "r") as f:
        return set(line.strip() for line in f.readlines())


def save_seen_ids(ids):
    with open(STATE_FILE, "w") as f:
        for _id in ids:
            f.write(_id + "\n")


def fetch_listings():
    resp = requests.get(SEARCH_URL, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    listings = []
    for card in soup.select("a"):
        href = card.get("href")
        if not href or "/find-a-home/" not in href:
            continue
        url = href
        if url.startswith("/"):
            url = "https://www.placesforpeople.co.uk" + url
        listing_id = url
        title = card.get_text(strip=True)[:120]
        listings.append({"id": listing_id, "url": url, "title": title})
    return listings


def send_email(new_listings):
    if not new_listings:
        return

    body_lines = []
    for l in new_listings:
        body_lines.append(f"{l['title']}\n{l['url']}\n")

    body = "\n\n".join(body_lines)
    msg = MIMEText(body)
    msg["Subject"] = f"New rental properties found ({len(new_listings)})"
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)


def main():
    seen_ids = load_seen_ids()
    listings = fetch_listings()

    new_listings = [l for l in listings if l["id"] not in seen_ids]

    if new_listings:
        print(f"Found {len(new_listings)} new listings")
        send_email(new_listings)
        all_ids = seen_ids.union({l["id"] for l in listings})
        save_seen_ids(all_ids)
    else:
        print("No new listings")


if __name__ == "__main__":
    main()
