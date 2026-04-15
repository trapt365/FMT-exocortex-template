#!/bin/bash
# COLLECTOR: scout
# TARGET: 2_9_knowledge
# Description: метрики ночного разведчика (findings, capture candidates)

collect_scout() {
    local workspace="${WORKSPACE:-$HOME/IWE}"
    local results_dir="$workspace/DS-agent-workspace/scout/results"

    # Если Scout не настроен — пустой JSON
    if [ ! -d "$results_dir" ]; then
        echo '{}'
        return
    fi

    # Последний отчёт
    local latest
    latest=$(ls -t "$results_dir"/ScoutReport*.md 2>/dev/null | head -1)

    if [ -z "$latest" ]; then
        echo '{"scout_configured": true, "last_report": null, "findings": 0}'
        return
    fi

    local report_date
    report_date=$(basename "$latest" | grep -oP '\d{4}-\d{2}-\d{2}' || echo "unknown")

    # Считаем findings (строки таблицы с |)
    local findings=0
    findings=$(grep -cP '^\| \d+' "$latest" 2>/dev/null) || findings=0

    # Считаем capture candidates
    local captures=0
    captures=$(grep -ciP 'capture|захват' "$latest" 2>/dev/null) || captures=0

    # Severity breakdown
    local critical=0 high=0 medium=0 low=0
    critical=$(grep -ciP 'критическ' "$latest" 2>/dev/null) || critical=0
    high=$(grep -ciP 'высок' "$latest" 2>/dev/null) || high=0
    medium=$(grep -ciP 'средн' "$latest" 2>/dev/null) || medium=0
    low=$(grep -ciP 'низк' "$latest" 2>/dev/null) || low=0

    cat <<EOF
{
  "scout_configured": true,
  "last_report": "$report_date",
  "findings": $findings,
  "captures": $captures,
  "severity": {"critical": $critical, "high": $high, "medium": $medium, "low": $low}
}
EOF
}
