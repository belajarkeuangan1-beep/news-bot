import json
import os
import urllib.request
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

FEED = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
WEBHOOK = os.environ["DISCORD_WEBHOOK"]
TZ = ZoneInfo("Asia/Jakarta")  # ganti kalau zona waktumu beda
REMINDERS = [timedelta(minutes=30), timedelta(hours=200)]  # urut dari yang terkecil
CURRENCIES = {"USD"}  # tambah kalau mau, misal {"USD", "EUR"}
SENT_FILE = "sent.json"
UA = {"User-Agent": "Mozilla/5.0"}


def load_sent():
    try:
        with open(SENT_FILE) as f:
            return set(json.load(f))
    except Exception:
        return set()


def post_discord(text):
    req = urllib.request.Request(
        WEBHOOK,
        data=json.dumps({"content": text}).encode(),
        headers={"Content-Type": "application/json", **UA},
    )
    urllib.request.urlopen(req, timeout=30).read()


def sisa_waktu(diff):
    menit = int(diff.total_seconds() // 60)
    if menit < 60:
        return f"{menit} menit lagi"
    return f"sekitar {round(diff.total_seconds() / 3600, 1)} jam lagi"


def main():
    req = urllib.request.Request(FEED, headers=UA)
    events = json.load(urllib.request.urlopen(req, timeout=30))
    now = datetime.now(timezone.utc)
    sent = load_sent()

    for e in events:
        if e.get("impact") != "High" or e.get("country") not in CURRENCIES:
            continue
        t = datetime.fromisoformat(e["date"])
        diff = t - now
        if diff <= timedelta(0):
            continue

        # ambil reminder terkecil yang masih berlaku, supaya tidak dobel
        window = next((r for r in REMINDERS if diff <= r), None)
        if window is None:
            continue

        eid = f'{e["date"]}|{e["country"]}|{e["title"]}|{int(window.total_seconds())}'
        if eid in sent:
            continue

        waktu = t.astimezone(TZ).strftime("%a %d %b, %H:%M")
        icon = "⏰" if window == REMINDERS[0] else "🔴"
        msg = (
            f"{icon} **HIGH IMPACT** — {e['country']} {e['title']}\n"
            f"Rilis: {waktu} WIB ({sisa_waktu(diff)})\n"
            f"Forecast: {e.get('forecast') or '-'} | Previous: {e.get('previous') or '-'}"
        )
        post_discord(msg)
        sent.add(eid)

    with open(SENT_FILE, "w") as f:
        json.dump(sorted(sent), f)


if __name__ == "__main__":
    main()
