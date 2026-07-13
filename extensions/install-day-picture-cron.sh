#!/bin/bash
# install-day-picture-cron.sh — идемпотентная установка расписания картины дня (WP-40 Ф4).
# Ставит запуск day-picture-run.sh каждые 3 часа в дневном окне 05-20 (окно 05-21).
# Не трогает остальные строки crontab. Повторный запуск не дублирует.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNNER="$SCRIPT_DIR/day-picture-run.sh"
LOG="$HOME/.local/state/exocortex/day-picture.log"
mkdir -p "$(dirname "$LOG")"
MARKER="# WP-40 Картина дня"
LINE="0 5,8,11,14,17,20 * * * /bin/bash $RUNNER cron >> $LOG 2>&1"

CUR=$(crontab -l 2>/dev/null || true)
if echo "$CUR" | grep -qF "$RUNNER"; then
    # обновляем существующую строку (на случай смены окна)
    NEW=$(echo "$CUR" | grep -v "$RUNNER" | grep -vF "$MARKER")
    printf '%s\n%s\n%s\n' "$NEW" "$MARKER — каждые 3ч, окно 05-21" "$LINE" | sed '/^$/N;/^\n$/D' | crontab -
    echo "Обновлено: расписание картины дня (05,08,11,14,17,20)."
else
    printf '%s\n%s\n%s\n' "$CUR" "$MARKER — каждые 3ч, окно 05-21" "$LINE" | sed '/^$/N;/^\n$/D' | crontab -
    echo "Установлено: расписание картины дня (05,08,11,14,17,20)."
fi
crontab -l | grep -A1 "$MARKER"
