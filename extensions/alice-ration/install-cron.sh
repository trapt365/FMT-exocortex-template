#!/bin/bash
# install-cron.sh — идемпотентная установка расписания снимка рациона для Алисы (WP-41).
# Обновляет лёгкую часть снимка (запасы + питание дня) каждые 3 часа, на :20 —
# после обработчика рефлексий WP-40 (:00), чтобы подхватывать свежую еду в DayPlan.
# Остаток макросов обновляется только прогоном /cronometer (расширение cronometer.alice-export.md).
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXPORTER="$SCRIPT_DIR/export.py"
LOG="$HOME/.local/state/exocortex/alice-ration.log"
mkdir -p "$(dirname "$LOG")"
MARKER="# WP-41 Снимок рациона для Алисы"
LINE="20 5,8,11,14,17,20 * * * /usr/bin/python3 $EXPORTER --push >> $LOG 2>&1"

CUR=$(crontab -l 2>/dev/null || true)
if echo "$CUR" | grep -qF "$EXPORTER"; then
    NEW=$(echo "$CUR" | grep -v "$EXPORTER" | grep -vF "$MARKER")
    printf '%s\n%s\n%s\n' "$NEW" "$MARKER — каждые 3ч на :20, окно 05-21" "$LINE" | sed '/^$/N;/^\n$/D' | crontab -
    echo "Обновлено: расписание снимка рациона (05:20, 08:20, 11:20, 14:20, 17:20, 20:20)."
else
    printf '%s\n%s\n%s\n' "$CUR" "$MARKER — каждые 3ч на :20, окно 05-21" "$LINE" | sed '/^$/N;/^\n$/D' | crontab -
    echo "Установлено: расписание снимка рациона (05:20, 08:20, 11:20, 14:20, 17:20, 20:20)."
fi
crontab -l | grep -A1 "$MARKER"
