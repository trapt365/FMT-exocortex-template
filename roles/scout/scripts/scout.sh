#!/bin/bash
# Scout (Разведчик) Agent Runner — R3
# Сканирует базу знаний на пробелы, выдаёт отчёт с findings
#
# Использование:
#   scout.sh knowledge-gaps   # сканирование Pack на пробелы (nightly)

set -e

# Конфигурация
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
WORKSPACE="$HOME/IWE"
PROMPTS_DIR="$REPO_DIR/prompts"
LOG_DIR="$HOME/logs/scout"
CLAUDE_PATH="$HOME/.npm-global/bin/claude"
CLAUDE_TIMEOUT=1800  # 30 мин
ENV_FILE="$HOME/.config/aist/env"

AGENT_WORKSPACE="$WORKSPACE/DS-agent-workspace"
RESULTS_DIR="$AGENT_WORKSPACE/scout/results"
TRAJECTORY_DIR="$AGENT_WORKSPACE/scout/trajectory"

# AI CLI: переопределение через переменные окружения
AI_CLI="${AI_CLI:-$CLAUDE_PATH}"
AI_CLI_PROMPT_FLAG="${AI_CLI_PROMPT_FLAG:--p}"
AI_CLI_EXTRA_FLAGS="${AI_CLI_EXTRA_FLAGS:---dangerously-skip-permissions --allowedTools Read,Glob,Grep,Bash,mcp__iwe-knowledge__knowledge_graph_stats,mcp__iwe-knowledge__knowledge_search,mcp__iwe-knowledge__knowledge_list_sources}"

# macOS не имеет GNU timeout — perl fallback
if ! command -v timeout &>/dev/null; then
    timeout() {
        local duration="$1"; shift
        perl -e '
            use POSIX ":sys_wait_h";
            my $timeout = shift @ARGV;
            my $pid = fork();
            if ($pid == 0) { exec @ARGV; die "exec failed: $!"; }
            eval {
                local $SIG{ALRM} = sub { kill "TERM", $pid; die "timeout\n"; };
                alarm $timeout;
                waitpid($pid, 0);
                alarm 0;
            };
            if ($@ && $@ eq "timeout\n") { waitpid($pid, WNOHANG); exit 124; }
            exit ($? >> 8);
        ' "$duration" "$@"
    }
fi

# Предотвращаем сон (macOS: caffeinate, Linux: systemd-inhibit)
if command -v caffeinate &>/dev/null; then
    caffeinate -diu -w $$ &
elif command -v systemd-inhibit &>/dev/null; then
    # Linux: inhibit idle sleep для текущего PID (noop wrapper — запускаем как parent)
    :
fi

# Создаём папки
mkdir -p "$LOG_DIR" "$RESULTS_DIR" "$TRAJECTORY_DIR"

DATE=$(date +%Y-%m-%d)
LOG_FILE="$LOG_DIR/$DATE.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

notify() {
    local title="$1"
    local message="$2"
    printf 'display notification "%s" with title "%s"' "$message" "$title" | osascript 2>/dev/null \
        || notify-send "$title" "$message" 2>/dev/null \
        || true
}

notify_telegram() {
    local scenario="$1"
    local notify_script="$REPO_DIR/../synchronizer/scripts/notify.sh"
    if [ -f "$notify_script" ]; then
        "$notify_script" scout "$scenario" >> "$LOG_FILE" 2>&1 || true
    fi
}

load_env() {
    if [ -f "$ENV_FILE" ]; then
        set -a
        source "$ENV_FILE"
        set +a
    fi
}

run_claude() {
    local command_file="$1"
    local command_path="$PROMPTS_DIR/$command_file.md"

    if [ ! -f "$command_path" ]; then
        log "ERROR: Prompt file not found: $command_path"
        exit 1
    fi

    local prompt
    prompt=$(cat "$command_path")

    # Inject date context (prevents LLM calendar errors)
    local ru_date_context
    ru_date_context=$(python3 -c "
import datetime
days = ['Понедельник','Вторник','Среда','Четверг','Пятница','Суббота','Воскресенье']
months = ['января','февраля','марта','апреля','мая','июня','июля','августа','сентября','октября','ноября','декабря']
d = datetime.date.today()
print(f'{d.day} {months[d.month-1]} {d.year}, {days[d.weekday()]}')
")

    prompt="[Системный контекст] Сегодня: ${ru_date_context}. ISO: ${DATE}. ЯЗЫК: отвечай ТОЛЬКО на русском.
Результат записать в: ${RESULTS_DIR}/ScoutReport ${DATE}.md

${prompt}"

    log "Starting scenario: $command_file"
    log "Prompt: $command_path"
    log "Results dir: $RESULTS_DIR"

    cd "$WORKSPACE"

    # Запуск Claude CLI с timeout-защитой
    local rc=0
    timeout "$CLAUDE_TIMEOUT" "$AI_CLI" $AI_CLI_EXTRA_FLAGS \
        $AI_CLI_PROMPT_FLAG "$prompt" \
        >> "$LOG_FILE" 2>&1 || rc=$?

    if [ $rc -eq 124 ]; then
        log "WARN: Claude CLI timed out after ${CLAUDE_TIMEOUT}s for: $command_file"
    elif [ $rc -ne 0 ]; then
        log "WARN: Claude CLI exited with code $rc for: $command_file"
    else
        log "SUCCESS: $command_file"
    fi

    # Trajectory log (краткая запись о запуске)
    echo "$DATE | $command_file | rc=$rc" >> "$TRAJECTORY_DIR/trajectory.log"

    # Commit + push результата в agent-workspace
    if [ -d "$AGENT_WORKSPACE/.git" ]; then
        git -C "$AGENT_WORKSPACE" add "scout/results/" "scout/trajectory/" >> "$LOG_FILE" 2>&1 || true
        if ! git -C "$AGENT_WORKSPACE" diff --cached --quiet 2>/dev/null; then
            git -C "$AGENT_WORKSPACE" commit -m "scout: $command_file $DATE" >> "$LOG_FILE" 2>&1 \
                && log "Committed to agent-workspace" \
                || log "WARN: git commit failed"
        else
            log "No new changes to commit"
        fi

        if ! git -C "$AGENT_WORKSPACE" diff --quiet origin/main..HEAD 2>/dev/null; then
            git -C "$AGENT_WORKSPACE" push >> "$LOG_FILE" 2>&1 \
                && log "Pushed agent-workspace" \
                || log "WARN: git push failed"
        fi
    fi

    # Очистить staging area
    git -C "$AGENT_WORKSPACE" reset --quiet 2>/dev/null || true

    notify "Разведчик: $command_file" "Сканирование завершено (rc=$rc)"
    return $rc
}

# Загружаем env
load_env

# Определяем сценарий
case "$1" in
    "knowledge-gaps")
        log "=== Scout: knowledge-gaps ==="
        run_claude "knowledge-gaps"
        notify_telegram "knowledge-gaps"
        ;;

    *)
        echo "Scout — Разведчик (R3)"
        echo ""
        echo "Usage: $0 <scenario>"
        echo ""
        echo "Scenarios:"
        echo "  knowledge-gaps   Сканирование Pack на пробелы (nightly)"
        exit 1
        ;;
esac

log "Done"
