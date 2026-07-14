#!/usr/bin/env python3
"""Экспортёр сводки рациона для навыка Алисы «Мой рацион» (WP-41).

Собирает JSON-снимок в DS-strategy/current/alice-ration.json:
  - остаток до дневных таргетов + рекомендация — из cronometer-remaining.json
    (пишет скилл /cronometer, см. IWE/extensions/cronometer.alice-export.md);
  - готовые блюда — из Vault1/Meal Prep/inventory.md (таблицы секций «Готов…»);
  - съеденное сегодня — строка «Питание» из DayPlan (секция «Фундамент»).

Детерминированный, без LLM (урок: LLM вне критического пути).
Запуск: python3 export.py [--push]   (--push = закоммитить и отправить снимок)
"""
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

TZ = timezone(timedelta(hours=5))
INVENTORY = Path("/mnt/c/Users/Timur/Documents/Vault1/Meal Prep/inventory.md")
STRATEGY = Path("/home/trapt22/IWE/DS-strategy")
REMAINING_FILE = STRATEGY / "current" / "cronometer-remaining.json"
OUT_FILE = STRATEGY / "current" / "alice-ration.json"

SKIP_DISHES = ("соус", "нарезка")  # не самостоятельная еда


def parse_ready_dishes(md_text: str) -> list[dict]:
    """Таблицы секций, чей заголовок содержит «Готов» — имя + количество."""
    dishes = []
    section = None
    for line in md_text.splitlines():
        heading = re.match(r"^#{2,4}\s+(.*)", line)
        if heading:
            section = heading.group(1)
            continue
        if section and "готов" in section.lower() and line.startswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) < 2 or cells[0] in ("Продукт", "") or set(cells[0]) <= {"-", " "}:
                continue
            name = re.sub(r"\s+", " ", cells[0])
            if any(s in name.lower() for s in SKIP_DISHES):
                continue
            dishes.append({"name": name, "qty": cells[1]})
    return dishes


def parse_eaten_today() -> str | None:
    today = datetime.now(TZ).strftime("%Y-%m-%d")
    for folder in ("current", "archive/day-plans"):
        dayplan = STRATEGY / folder / f"DayPlan {today}.md"
        if not dayplan.exists():
            continue
        for line in dayplan.read_text(encoding="utf-8").splitlines():
            m = re.match(r"-\s+\*\*Питание:\*\*\s*(.+)", line.strip())
            if m:
                return m.group(1).strip()
    return None


def load_remaining() -> dict | None:
    if not REMAINING_FILE.exists():
        return None
    try:
        return json.loads(REMAINING_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def git_push(paths: list[Path]) -> None:
    """Best-effort: коммит только своих файлов; при расхождении с origin —
    rebase c autostash и повтор. Не валит запуск (cron)."""
    rel = [str(p.relative_to(STRATEGY)) for p in paths if p.exists()]
    try:
        subprocess.run(["git", "add", "--", *rel], cwd=STRATEGY, check=True)
        diff = subprocess.run(["git", "diff", "--cached", "--quiet", "--", *rel], cwd=STRATEGY)
        if diff.returncode == 0:
            print("Снимок не изменился — коммит не нужен.")
            return
        subprocess.run(
            ["git", "commit", "-m", "chore(WP-41): снимок рациона для навыка Алисы", "--", *rel],
            cwd=STRATEGY, check=True,
        )
        if subprocess.run(["git", "push"], cwd=STRATEGY).returncode != 0:
            subprocess.run(
                ["git", "pull", "--rebase", "--autostash", "origin", "master"],
                cwd=STRATEGY, check=True,
            )
            subprocess.run(["git", "push"], cwd=STRATEGY, check=True)
        print("Снимок закоммичен и отправлен.")
    except subprocess.CalledProcessError as e:
        print(f"ВНИМАНИЕ: снимок для Алисы не отправлен ({e}); данные останутся прежними до следующего запуска.")


def main() -> int:
    snapshot = {
        "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "remaining": load_remaining(),
        "eaten_today": parse_eaten_today(),
        "ready_dishes": [],
        "inventory_updated": None,
    }
    if INVENTORY.exists():
        text = INVENTORY.read_text(encoding="utf-8")
        snapshot["ready_dishes"] = parse_ready_dishes(text)
        m = re.search(r"^updated:\s*(\S+)", text, re.MULTILINE)
        if m:
            snapshot["inventory_updated"] = m.group(1)
    OUT_FILE.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Снимок записан: {OUT_FILE} ({len(snapshot['ready_dishes'])} блюд, "
          f"остаток: {'есть' if snapshot['remaining'] else 'нет'})")
    if "--push" in sys.argv:
        git_push([OUT_FILE])
    return 0


if __name__ == "__main__":
    sys.exit(main())
