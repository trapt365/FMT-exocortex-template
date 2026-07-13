#!/bin/bash
# build-day-picture.sh — Ф3 WP-40: сборка «картины дня» в daily note + пуш в Telegram.
#
# Таблица дня собирается ДЕТЕРМИНИРОВАННО (python) из источников:
#   хронометраж-лог (доверие 1) > WakaTime (2) > ActivityWatch окно/afk (3).
# Лакуны заполняются с пометкой «(догадка)»; отсутствие данных — «вне компьютера».
# Claude используется ТОЛЬКО для короткой «связки дня» с жёстким таймаутом и откатом —
# чтобы джоба по расписанию не висла под нагрузкой.
# Пишет секцию `### Картина дня` в Vault1/Calendar/DATE.md и шлёт дайджест в Telegram.
#
# Использование:
#   build-day-picture.sh [YYYY-MM-DD] [--dry-run] [--no-telegram] [--no-llm]
#
# .exocortex.env: VAULT_DIR. WakaTime: ~/.wakatime.cfg. Telegram: ~/.secrets/tagping-telegram.env
# see WP-40 Ф3

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/../.exocortex.env"
[ -f "$ENV_FILE" ] && source "$ENV_FILE"
if [ -z "${VAULT_DIR:-}" ]; then echo "ERROR: VAULT_DIR не задан" >&2; exit 1; fi

CLAUDE_PATH="$HOME/.npm-global/bin/claude"; [ -x "$CLAUDE_PATH" ] || CLAUDE_PATH="claude"
TARGET_DATE=$(date +%Y-%m-%d); NOW_HM=$(date +%H:%M)
DRY_RUN=false; SEND_TG=true; USE_LLM=true
for arg in "$@"; do case "$arg" in
    --dry-run) DRY_RUN=true ;; --no-telegram) SEND_TG=false ;; --no-llm) USE_LLM=false ;;
    [0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]) TARGET_DATE="$arg" ;;
esac; done

DAILY_NOTE="$VAULT_DIR/Calendar/$TARGET_DATE.md"
IWE_SUMMARY=$(bash "$SCRIPT_DIR/collect-iwe-work.sh" "$TARGET_DATE" --stdout-summary 2>/dev/null || echo "нет данных")

export DP_DATE="$TARGET_DATE" DP_NOTE="$DAILY_NOTE" DP_NOW="$NOW_HM" \
       DP_IWE="$IWE_SUMMARY" DP_CLAUDE="$CLAUDE_PATH" \
       DP_DRY="$DRY_RUN" DP_TG="$SEND_TG" DP_LLM="$USE_LLM"

python3 "$SCRIPT_DIR/_day_picture.py"
