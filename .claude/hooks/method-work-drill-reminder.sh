#!/bin/bash
# Method/Work Drill Reminder Hook
# Event: UserPromptSubmit
# Инжектит агенту напоминание провести ежедневный ручной drill "метод (8) + работа (6)"
# (extensions/ritual.method-work-artifact.md), ПОКА маркер дня не создан.
# Причина: у ритуала открытия СЕССИИ нет детерминированного загрузчика (в отличие
# от Day Open с load-extensions.sh) → Шаг 1d держался на памяти агента и пропускался
# (14-15.07.2026). Хук делает напоминание детерминированным.
# Read-only: возвращает JSON additionalContext, ничего не модифицирует.
# see extensions/ritual.method-work-artifact.md, WP-15

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$HOME/IWE}"
MARKER_DIR="$PROJECT_DIR/DS-strategy/inbox/method-work"
TODAY=$(date +%F)
MARKER="$MARKER_DIR/.manual-drill-$TODAY"

# Маркер на сегодня есть → drill проведён, тихо выходим (без доп. контекста).
if [ -f "$MARKER" ]; then
  exit 0
fi

# Маркера нет → напомнить агенту про drill на первой содержательной сессии дня.
# Экранируем путь маркера для безопасной вставки в JSON.
cat <<EOF
{"additionalContext": "🔁 MW-DRILL: сегодняшний ручной drill Распожаризации (метод 8 объектов + работа 6) ещё НЕ проведён — маркер отсутствует. Если это содержательная сессия с работой над РП (verification_class != trivial, есть >=10 мин работы) — на Шаге 1d предложи пилоту заполнить обе таблицы ВРУЧНУЮ по extensions/ritual.method-work-artifact.md, проверь как R3, запиши строку в трекер-таблицу упражнений (ссылка в extension-доке) и создай маркер .manual-drill-${TODAY}. Если сессия trivial или без изменений файлов — НЕ навязывай, просто продолжай."}
EOF
exit 0
