#!/bin/bash
# Шаблон уведомлений: Экстрактор (R2)
# Вызывается из notify.sh через source

REPORTS_DIR="{{WORKSPACE_DIR}}/DS-strategy/inbox/extraction-reports"
DATE=$(date +%Y-%m-%d)

build_message() {
    local process="$1"

    case "$process" in
        "inbox-check")
            local report
            report=$(ls -t "$REPORTS_DIR"/${DATE}-*.md 2>/dev/null | head -1)

            if [ -z "$report" ] || [ ! -f "$report" ]; then
                echo ""
                return
            fi

            local candidates
            candidates=$(grep -c '^## Кандидат' "$report" 2>/dev/null || echo "0")
            local accept
            accept=$(grep -c 'Вердикт.*accept' "$report" 2>/dev/null || echo "0")

            printf "<b>🔍 Knowledge Extractor: %s</b>\n\n" "$process"
            printf "📅 %s\n\n" "$DATE"
            printf "📊 Кандидатов: %s, Accept: %s\n\n" "$candidates" "$accept"

            if [ "$candidates" -gt 0 ]; then
                printf "Для применения: в Claude скажите «review extraction report»"
            else
                printf "Inbox пуст."
            fi
            ;;

        "audit")
            printf "<b>🔍 Knowledge Audit завершён</b>\n\n📅 %s\n\nПроверьте лог: ~/logs/extractor/%s.log" "$DATE" "$DATE"
            ;;

        *)
            echo ""
            ;;
    esac
}

build_buttons() {
    echo '[]'
}
