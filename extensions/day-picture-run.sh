#!/bin/bash
# day-picture-run.sh — единый вход WP-40: обработка рефлексий + сборка картины дня.
# Вызывается по расписанию (cron, каждые 3ч в окне 05-20) и из ритуальных хуков
# (open-session / Day Open / Day Close). Не падает целиком, если один шаг сбойнул.
# see WP-40 Ф4
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODE="${1:-scheduled}"

echo "=== $(date '+%F %T') day-picture-run ($MODE) ==="

# 1. Рефлексии за сегодня
bash "$SCRIPT_DIR/process-reflections.sh" || echo "  process-reflections rc=$?"

# 2. Утренний догон вчерашних записей (iCloud-задержка Just Press Record)
if [ "$(date +%H)" -lt 10 ]; then
    bash "$SCRIPT_DIR/process-reflections.sh" "$(date -d 'yesterday' +%F)" 2>/dev/null || true
fi

# 3. Картина дня → daily note + Telegram
bash "$SCRIPT_DIR/build-day-picture.sh" || echo "  build-day-picture rc=$?"

echo "=== $(date '+%F %T') day-picture-run готов ==="
