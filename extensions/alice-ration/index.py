# Webhook навыка Алисы «Мой рацион» (WP-41) — Yandex Cloud Function, python312.
# Читает снимок alice-ration.json из приватного GitHub-репо и озвучивает:
#   «остаток» → остаток до дневных таргетов; «что съесть / меню» → готовые блюда
#   и рекомендация; иначе — короткая сводка + подсказка.
#
# Переменные окружения функции:
#   GITHUB_TOKEN — fine-grained PAT, только чтение contents репо DS-strategy
#   GITHUB_REPO  — trapt365/DS-strategy
#   FILE_PATH    — current/alice-ration.json (по умолчанию)
#   LOCAL_FILE   — путь к локальному JSON (только для тестов, вместо GitHub)
import base64
import json
import os
import time
import urllib.request
from datetime import datetime, timedelta, timezone

TZ = timezone(timedelta(hours=5))
STALE_AFTER_HOURS = 6
_CACHE = {"snap": None, "ts": 0.0}

STOP_WORDS = ("хватит", "стоп", "выход", "спасибо", "закрой")
REMAINING_WORDS = ("остаток", "осталось", "сколько", "таргет", "цел")
FOOD_WORDS = ("съесть", "поесть", "меню", "еда", "еды", "запас", "блюд", "готово")


def load_snapshot() -> dict:
    local = os.environ.get("LOCAL_FILE")
    if local:
        with open(local, encoding="utf-8") as f:
            return json.load(f)
    if _CACHE["snap"] and time.time() - _CACHE["ts"] < 60:
        return _CACHE["snap"]
    repo = os.environ["GITHUB_REPO"]
    path = os.environ.get("FILE_PATH", "current/alice-ration.json")
    req = urllib.request.Request(
        f"https://api.github.com/repos/{repo}/contents/{path}",
        headers={
            "Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "alice-ration-skill",
        },
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        payload = json.load(resp)
    snap = json.loads(base64.b64decode(payload["content"]).decode("utf-8"))
    _CACHE.update(snap=snap, ts=time.time())
    return snap


def staleness_note(snap: dict) -> str:
    try:
        generated = datetime.fromisoformat(snap["generated_at"])
    except (KeyError, ValueError):
        return "Не вижу, когда обновлялась сводка. "
    age = datetime.now(TZ) - generated
    if age > timedelta(hours=STALE_AFTER_HOURS):
        if generated.date() == datetime.now(TZ).date():
            when = f"сегодня в {generated.strftime('%H:%M')}"
        else:
            when = generated.strftime("%d.%m в %H:%M")
        return f"Данные обновлялись {when}. "
    return ""


def fmt_remaining(rem: dict | None) -> str:
    if not rem:
        return ("По остатку данных нет — попроси Тимура прогнать проверку "
                "Кронометра, тогда я буду знать цифры.")
    parts = []
    for key, label in (
        ("kcal", "килокалорий"),
        ("protein_g", "граммов белка"),
        ("net_carbs_g", "граммов чистых углеводов"),
        ("fat_g", "граммов жира"),
        ("fiber_g", "граммов клетчатки"),
    ):
        val = rem.get(key)
        if val is not None:
            parts.append(f"{round(val)} {label}")
    if not parts:
        return "Снимок остатка пустой."
    return "Осталось на сегодня: " + ", ".join(parts) + "."


def fmt_food(snap: dict) -> str:
    lines = []
    rec = (snap.get("remaining") or {}).get("recommendation") or snap.get("recommendation")
    if rec:
        lines.append(f"Рекомендация: {rec}")
    dishes = snap.get("ready_dishes") or []
    if dishes:
        names = ", ".join(d["name"] for d in dishes[:7])
        lines.append(f"Из готового в запасах: {names}.")
    if not lines:
        lines.append("Про готовую еду данных нет — обнови инвентарь.")
    return " ".join(lines)


def build_reply(command: str, snap: dict) -> tuple[str, bool]:
    cmd = command.lower()
    if any(w in cmd for w in STOP_WORDS):
        return "Приятного аппетита!", True
    note = staleness_note(snap)
    if any(w in cmd for w in REMAINING_WORDS):
        return note + fmt_remaining(snap.get("remaining")), False
    if any(w in cmd for w in FOOD_WORDS):
        return note + fmt_food(snap), False
    # Первый вход / непонятная фраза — короткая сводка + подсказка
    brief = fmt_remaining(snap.get("remaining"))
    dishes = snap.get("ready_dishes") or []
    if dishes:
        brief += f" Готовых блюд в запасах: {len(dishes)}."
    hint = " Спроси: сколько осталось — или: что съесть."
    return note + brief + hint, False


def handler(event, context):
    command = (event.get("request") or {}).get("command", "")
    try:
        snap = load_snapshot()
        text, end = build_reply(command, snap)
    except Exception:
        text, end = ("Не смог достать сводку рациона. "
                     "Проверь выгрузку снимка и токен доступа."), False
    if len(text) > 1000:
        text = text[:990] + "…"
    return {
        "version": event.get("version", "1.0"),
        "response": {"text": text, "end_session": end},
    }
