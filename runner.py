#!/usr/bin/env python3
import os
import json
import urllib.parse
import urllib.request
from pathlib import Path
from datetime import datetime

BASE_DIR = Path("/home/ubuntu/automacoes/lembretes_app")
DATA_DIR = BASE_DIR / "data"
LOG_DIR = BASE_DIR / "logs"
REMINDERS_FILE = DATA_DIR / "lembretes.json"
HERMES_ENV = Path("/home/ubuntu/.hermes/.env")
LOG_FILE = LOG_DIR / "runner.log"

DATA_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

if not REMINDERS_FILE.exists():
    REMINDERS_FILE.write_text("[]", encoding="utf-8")


def log(message):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(f"[{now}] {message}\n")


def load_env(path):
    if not path.exists():
        return

    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()

        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def load_reminders():
    try:
        return json.loads(REMINDERS_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        log(f"Erro lendo lembretes: {e}")
        return []


def save_reminders(reminders):
    REMINDERS_FILE.write_text(json.dumps(reminders, ensure_ascii=False, indent=2), encoding="utf-8")


def should_run_today(days, weekday):
    # weekday: Monday=0, Sunday=6
    if days == "daily":
        return True
    if days == "weekdays":
        return weekday <= 4
    if days == "weekends":
        return weekday >= 5
    return True


def send_telegram(text):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_ALLOWED_USERS")

    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN nao encontrado em /home/ubuntu/.hermes/.env")
    if not chat_id:
        raise RuntimeError("TELEGRAM_ALLOWED_USERS nao encontrado em /home/ubuntu/.hermes/.env")

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": chat_id, "text": text}).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")

    with urllib.request.urlopen(req, timeout=30) as response:
        return response.read().decode("utf-8")


def main():
    load_env(HERMES_ENV)

    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    current_time = now.strftime("%H:%M")
    weekday = now.weekday()

    reminders = load_reminders()
    changed = False

    for r in reminders:
        if not r.get("active", True):
            continue
        if not should_run_today(r.get("days", "daily"), weekday):
            continue

        times = r.get("times", [])
        if current_time not in times:
            continue

        last_sent = r.get("last_sent", {})
        if last_sent.get(current_time) == today:
            continue

        text = r.get("text", "").strip()
        if not text:
            continue

        message = f"🔔 Lembrete\n\n{text}\n\nHorário: {current_time}"

        try:
            send_telegram(message)
            r.setdefault("last_sent", {})[current_time] = today
            changed = True
            log(f"Enviado: {text} ({current_time})")
        except Exception as e:
            log(f"Erro enviando lembrete '{text}': {e}")

    if changed:
        save_reminders(reminders)


if __name__ == "__main__":
    main()
