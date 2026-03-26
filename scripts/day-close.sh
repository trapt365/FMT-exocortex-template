#!/bin/bash
# day-close.sh — Автоматические шаги Day Close (backup + reindex + linear sync)
#
# Вызывается Claude из протокола Day Close (protocol-close.md § День, шаг 4).
# Объединяет три механических операции в одну команду.
#
# Использование:
#   day-close.sh              # все три шага
#   day-close.sh --backup     # только backup
#   day-close.sh --reindex    # только reindex
#   day-close.sh --linear     # только linear sync
#
# Конфигурация: Пути заданы через переменные ниже — настроить при установке.

set -euo pipefail

# === КОНФИГУРАЦИЯ (настроить при установке) ===
WORKSPACE_DIR="${WORKSPACE_DIR:-$HOME/IWE}"
DS_STRATEGY="$WORKSPACE_DIR/DS-strategy"
MEMORY_SRC="$HOME/.claude/projects/-home-$(whoami)-IWE/memory"
EXOCORTEX_DST="$DS_STRATEGY/exocortex"
SELECTIVE_REINDEX="$WORKSPACE_DIR/DS-MCP/knowledge-mcp/scripts/selective-reindex.sh"
LINEAR_SYNC="$WORKSPACE_DIR/DS-IT-systems/DS-ai-systems/synchronizer/scripts/linear-sync.sh"
FETCH_WAKATIME="$WORKSPACE_DIR/DS-exocortex/roles/strategist/scripts/fetch-wakatime.sh"
ENV_FILE="$HOME/.config/aist/env"
LOG_FILE="$DS_STRATEGY/inbox/day-close.log"
# === /КОНФИГУРАЦИЯ ===

# Цвета
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log() { echo -e "${GREEN}[day-close]${NC} $1"; }
warn() { echo -e "${YELLOW}[day-close]${NC} $1"; }
err() { echo -e "${RED}[day-close]${NC} $1" >&2; }

# --- Шаг 1: Backup memory/ + CLAUDE.md → exocortex/ ---
do_backup() {
  log "Шаг 1/3: Backup memory/ → exocortex/"

  if [ ! -d "$MEMORY_SRC" ]; then
    err "Memory source not found: $MEMORY_SRC"
    return 1
  fi

  mkdir -p "$EXOCORTEX_DST"

  local count=0
  for f in "$MEMORY_SRC"/*.md "$MEMORY_SRC"/*.yaml "$MEMORY_SRC"/*.yml; do
    [ -f "$f" ] || continue
    cp "$f" "$EXOCORTEX_DST/"
    count=$((count + 1))
  done

  if [ -f "$WORKSPACE_DIR/CLAUDE.md" ]; then
    cp "$WORKSPACE_DIR/CLAUDE.md" "$EXOCORTEX_DST/CLAUDE.md"
    count=$((count + 1))
  fi

  log "  Скопировано: $count файлов → $EXOCORTEX_DST/"
}

# --- Шаг 2: Knowledge-MCP reindex ---
do_reindex() {
  log "Шаг 2/3: Knowledge-MCP reindex"

  if [ ! -x "$SELECTIVE_REINDEX" ]; then
    warn "  selective-reindex.sh не найден: $SELECTIVE_REINDEX — пропуск"
    return 0
  fi

  local changed_sources=""
  for repo in "$WORKSPACE_DIR"/PACK-* "$WORKSPACE_DIR"/DS-*; do
    [ -d "$repo/.git" ] || continue
    local repo_name
    repo_name=$(basename "$repo")
    local today_commits
    today_commits=$(git -C "$repo" log --since="today 00:00" --oneline --no-merges 2>/dev/null | wc -l | tr -d ' ')
    if [ "$today_commits" -gt 0 ]; then
      changed_sources="$changed_sources $repo_name"
    fi
  done

  if [ -z "$changed_sources" ]; then
    log "  Нет изменений в Pack/DS сегодня — пропуск reindex"
    return 0
  fi

  log "  Изменённые источники:$changed_sources"
  # shellcheck disable=SC2086
  "$SELECTIVE_REINDEX" $changed_sources
}

# --- Шаг 3: Linear sync ---
do_linear() {
  log "Шаг 3/3: Linear sync"

  if [ ! -x "$LINEAR_SYNC" ]; then
    warn "  linear-sync.sh не найден: $LINEAR_SYNC — пропуск"
    return 0
  fi

  "$LINEAR_SYNC"
}

# --- Шаг 4: WakaTime → DayPlan (мультипликатор) ---
do_wakatime() {
  log "Шаг 4/4: WakaTime → DayPlan"

  local today
  today=$(date +%Y-%m-%d)
  local dayplan="$DS_STRATEGY/current/DayPlan $today.md"

  if [ ! -f "$dayplan" ]; then
    warn "  DayPlan не найден: $dayplan — пропуск"
    return 0
  fi

  # Проверяем, есть ли уже секция мультипликатора
  if grep -q "### Мультипликатор IWE" "$dayplan" 2>/dev/null; then
    log "  Мультипликатор уже есть в DayPlan — пропуск"
    return 0
  fi

  # Загружаем env с ключами
  if [ -f "$ENV_FILE" ]; then
    set -a; source "$ENV_FILE"; set +a
  fi

  # Пробуем wakatime-cli
  local waka_today=""
  if command -v wakatime >/dev/null 2>&1; then
    waka_today=$(wakatime --today 2>/dev/null || true)
  elif [ -x "$HOME/.wakatime/wakatime-cli" ]; then
    waka_today=$("$HOME/.wakatime/wakatime-cli" --today 2>/dev/null || true)
  fi

  if [ -z "$waka_today" ]; then
    warn "  WakaTime недоступен — пропуск"
    return 0
  fi

  # Ищем маркер для вставки (после строки "**Коммиты:**")
  if ! grep -q '^\*\*Коммиты:\*\*' "$dayplan" 2>/dev/null; then
    warn "  Не найдена строка **Коммиты:** в DayPlan — пропуск"
    return 0
  fi

  # Вставляем секцию после строки **Коммиты:**
  local marker_line
  marker_line=$(grep -n '^\*\*Коммиты:\*\*' "$dayplan" | tail -1 | cut -d: -f1)

  local wakatime_block
  wakatime_block=$(cat <<WAKA

### Мультипликатор IWE

| Метрика | Значение |
|---------|----------|
| **WakaTime (физическое время)** | $waka_today |
| **Бюджет закрыт (оценки РП)** | _(заполняется Claude)_ |
| **Мультипликатор** | _(заполняется Claude)_ |

> WakaTime добавлен автоматически. Бюджет и мультипликатор заполняет Claude при Day Close.
WAKA
)

  # Вставляем после marker_line
  local tmp
  tmp=$(mktemp)
  head -n "$marker_line" "$dayplan" > "$tmp"
  echo "$wakatime_block" >> "$tmp"
  tail -n +"$((marker_line + 1))" "$dayplan" >> "$tmp"
  mv "$tmp" "$dayplan"

  log "  WakaTime ($waka_today) добавлен в DayPlan"
}

# --- Лог ---
write_log() {
  local date_str
  date_str=$(date "+%Y-%m-%d %H:%M")
  mkdir -p "$(dirname "$LOG_FILE")"
  echo "$date_str | day-close | backup=$1 reindex=$2 linear=$3 wakatime=${4:-skip}" >> "$LOG_FILE"
}

# --- Main ---
main() {
  local do_all=true
  local run_backup=false
  local run_reindex=false
  local run_linear=false
  local run_wakatime=false

  for arg in "$@"; do
    case "$arg" in
      --backup)   run_backup=true; do_all=false ;;
      --reindex)  run_reindex=true; do_all=false ;;
      --linear)   run_linear=true; do_all=false ;;
      --wakatime) run_wakatime=true; do_all=false ;;
      --help|-h)
        echo "Использование: day-close.sh [--backup] [--reindex] [--linear] [--wakatime]"
        echo "  Без аргументов — все четыре шага"
        exit 0
        ;;
      *)
        err "Неизвестный аргумент: $arg"
        exit 1
        ;;
    esac
  done

  if $do_all; then
    run_backup=true
    run_reindex=true
    run_linear=true
    run_wakatime=true
  fi

  log "=== Day Close (автоматические шаги) ==="

  local backup_status="skip" reindex_status="skip" linear_status="skip" wakatime_status="skip"

  if $run_wakatime; then
    if do_wakatime; then wakatime_status="ok"; else wakatime_status="fail"; fi
  fi

  if $run_backup; then
    if do_backup; then backup_status="ok"; else backup_status="fail"; fi
  fi

  if $run_reindex; then
    if do_reindex; then reindex_status="ok"; else reindex_status="fail"; fi
  fi

  if $run_linear; then
    if do_linear; then linear_status="ok"; else linear_status="fail"; fi
  fi

  write_log "$backup_status" "$reindex_status" "$linear_status" "$wakatime_status"

  log "=== Готово ==="
  log "  wakatime=$wakatime_status  backup=$backup_status  reindex=$reindex_status  linear=$linear_status"
}

main "$@"
