import json
import os
import urllib.request
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

FEED = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
WEBHOOK = os.environ["DISCORD_WEBHOOK"]
TZ = ZoneInfo("Asia/Jakarta")  # ganti kalau zona waktumu beda
REMINDERS = [timedelta(minutes=30), timedelta(hours=5)]  # urut dari yang terkecil
CURRENCIES = {"USD"}  # tambah kalau mau, misal {"USD", "EUR"}
PRIORITAS = ("Non-Farm", "FOMC", "CPI")  # news yang ditaruh paling atas
SENT_FILE = "sent.json"
UA = {"User-Agent": "Mozilla/5.0"}

HARI = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
BULAN = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
GARIS = "━━━━━━━━━━━━━━━"


def load_sent():
    try:
        with open(SENT_FILE) as f:
            return set(json.load(f))
    except Exception:
        return set()


def post_discord(embed):
    req = urllib.request.Request(
        WEBHOOK,
        data=json.dumps({"embeds": [embed]}).encode(),
        headers={"Content-Type": "application/json", **UA},
    )
    urllib.request.urlopen(req, timeout=30).read()


def tanggal(lokal):
    return f"{HARI[lokal.weekday()]}, {lokal.day} {BULAN[lokal.month - 1]} {lokal.year}"


def sisa_waktu(diff):
    menit = int(diff.total_seconds() // 60)
    if menit < 60:
        return f"{menit} menit lagi"
    return f"Sekitar {round(diff.total_seconds() / 3600)} jam lagi"


def build_embed(country, t, window, items, diff):
    lokal = t.astimezone(TZ)
    if window == REMINDERS[0]:
        title = f"⏰ 30 MENIT LAGI: {country}"
        head = f"🕗 **{lokal:%H:%M} WIB** ({tanggal(lokal)})"
        color = 0xE67E22
        note = "*Reminder 30 menit sebelum rilis*"
    else:
        title = f"🔴 HIGH IMPACT: {country}"
        head = (
            f"📅 **{tanggal(lokal)}**\n"
            f"🕗 **{lokal:%H:%M} WIB**\n"
            f"⏳ **{sisa_waktu(diff)}**"
        )
        color = 0xE74C3C
        note = "*Reminder 5 jam sebelum rilis*"

    blok = []
    for e in items:
        fc = e.get("forecast") or "-"
        pv = e.get("previous") or "-"
        blok.append(f"**{e['title']}**\nForecast: `{fc}`  ·  Previous: `{pv}`")

    desc = head + "\n\n" + GARIS + "\n\n" + "\n\n".join(blok) + "\n\n" + note
    return {"title": title, "description": desc, "color": color}


def main():
    req = urllib.request.Request(FEED, headers=UA)
    events = json.load(urllib.request.urlopen(req, timeout=30))
    now = datetime.now(timezone.utc)
    sent = load_sent()

    groups = {}  # (waktu rilis, reminder, mata uang) -> news yang rilis bareng
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

        g = groups.setdefault((t, window, e["country"]), {"items": [], "ids": [], "diff": diff})
        g["items"].append(e)
        g["ids"].append(eid)

    for key in sorted(groups, key=lambda k: (k[0], k[1])):
        t, window, country = key
        g = groups[key]
        g["items"].sort(key=lambda e: 0 if any(p in e["title"] for p in PRIORITAS) else 1)
        post_discord(build_embed(country, t, window, g["items"], g["diff"]))
        sent.update(g["ids"])

    with open(SENT_FILE, "w") as f:
        json.dump(sorted(sent), f)


if __name__ == "__main__":
    main()
