import json
import os
import requests

URL = "https://data.prismaxserver.com/data/qa/uploads"
STATE_FILE = "state.json"

TG_TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]
AUTH = " ".join(os.environ["PRISMAX_AUTH"].split())
if not AUTH.lower().startswith("bearer "):
    AUTH = "Bearer " + AUTH

HEADERS = {
    "Authorization": AUTH,
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://app.prismax.ai",
    "Referer": "https://app.prismax.ai/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
}


def notify(text):
    requests.post(
        f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
        json={"chat_id": CHAT_ID, "text": text},
        timeout=20,
    )


def item_key(item):
    if isinstance(item, dict) and "id" in item:
        return str(item["id"])
    return json.dumps(item, sort_keys=True)


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"seen": [], "initialized": False, "auth_alerted": False}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


state = load_state()
r = requests.get(URL, headers=HEADERS, timeout=30)

if r.status_code != 200:
    print("STATUS", r.status_code, r.text[:200])
    if r.status_code in (401, 403) and not state.get("auth_alerted"):
        notify(f"PrismaX rejected the login (status {r.status_code}). Update the PRISMAX_AUTH secret on GitHub.")
        state["auth_alerted"] = True
        save_state(state)
else:
    state["auth_alerted"] = False
    data = r.json().get("data", [])
    keys = [item_key(i) for i in data]
    if state.get("initialized"):
        for k in keys:
            if k not in state["seen"]:
                notify(f"New PrismaX upload to validate (ID: {k[:60]})")
    state["seen"] = sorted(set(state["seen"]) | set(keys))[-500:]
    state["initialized"] = True
    save_state(state)
    print("checked,", len(keys), "item(s)")
