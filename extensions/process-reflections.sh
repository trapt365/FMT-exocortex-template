#!/bin/bash
# process-reflections.sh — batch-обработка аудиорефлексий
#
# Транскрибирует аудио из Just Press Record за указанную дату,
# категоризирует через Claude (сделано / мысли) и дописывает
# в daily note Obsidian (Vault1/Calendar/YYYY-MM-DD.md).
#
# Использование:
#   process-reflections.sh              # сегодня
#   process-reflections.sh 2026-04-15   # конкретная дата
#   process-reflections.sh --dry-run    # показать что будет, не писать
#
# Требует в .exocortex.env:
#   DEEPGRAM_API_KEY, VAULT_DIR, JUST_PRESS_RECORD

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/../.exocortex.env"
CLAUDE_PATH="$HOME/.npm-global/bin/claude"

# Load config
if [ ! -f "$ENV_FILE" ]; then
    echo "ERROR: $ENV_FILE not found"
    exit 1
fi
source "$ENV_FILE"

for var in DEEPGRAM_API_KEY VAULT_DIR JUST_PRESS_RECORD; do
    if [ -z "${!var:-}" ]; then
        echo "ERROR: $var not set in $ENV_FILE"
        exit 1
    fi
done

# Args
DRY_RUN=false
TARGET_DATE=$(date +%Y-%m-%d)

for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN=true ;;
        [0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]) TARGET_DATE="$arg" ;;
    esac
done

JPR_DIR="$JUST_PRESS_RECORD/$TARGET_DATE"
DAILY_NOTE="$VAULT_DIR/Calendar/$TARGET_DATE.md"

echo "=== Process Reflections: $TARGET_DATE ==="

# 1. Найти аудиофайлы
if [ ! -d "$JPR_DIR" ]; then
    echo "Нет аудиофайлов за $TARGET_DATE ($JPR_DIR)"
    exit 0
fi

# Идемпотентность: трекаем обработанные файлы
PROCESSED_LOG="$HOME/.local/state/exocortex/reflections-processed.log"
mkdir -p "$(dirname "$PROCESSED_LOG")"
touch "$PROCESSED_LOG"

# Фильтруем только необработанные файлы
ALL_AUDIO=("$JPR_DIR"/*.m4a)
if [ ! -f "${ALL_AUDIO[0]}" ]; then
    echo "Нет .m4a файлов в $JPR_DIR"
    exit 0
fi

AUDIO_FILES=()
for f in "${ALL_AUDIO[@]}"; do
    if ! grep -qF "$(basename "$f")" "$PROCESSED_LOG" 2>/dev/null; then
        AUDIO_FILES+=("$f")
    fi
done

if [ ${#AUDIO_FILES[@]} -eq 0 ]; then
    echo "Все ${#ALL_AUDIO[@]} файлов уже обработаны"
    exit 0
fi

echo "Найдено файлов: ${#ALL_AUDIO[@]}, новых: ${#AUDIO_FILES[@]}"

# 2. Транскрибировать новые файлы
ALL_TRANSCRIPTS=""
TEMP_DIR=$(mktemp -d /tmp/reflections-XXXXX)

for audio in "${AUDIO_FILES[@]}"; do
    BASENAME=$(basename "$audio" .m4a)
    TEMP_JSON="$TEMP_DIR/$BASENAME.json"

    echo "  Транскрибирую: $BASENAME..."

    HTTP_CODE=$(curl -s -w "%{http_code}" \
        --request POST \
        --url 'https://api.deepgram.com/v1/listen?model=nova-2&language=ru&diarize=true&punctuate=true&paragraphs=true&smart_format=true' \
        --header "Authorization: Token $DEEPGRAM_API_KEY" \
        --header "Content-Type: audio/m4a" \
        --data-binary @"$audio" \
        -o "$TEMP_JSON")

    if [ "$HTTP_CODE" != "200" ]; then
        echo "  WARN: Deepgram вернул HTTP $HTTP_CODE для $BASENAME, пропускаю"
        continue
    fi

    # Извлечь текст
    TRANSCRIPT=$(python3 -c "
import json, sys
with open('$TEMP_JSON') as f:
    data = json.load(f)
alt = data['results']['channels'][0]['alternatives'][0]
paras = alt.get('paragraphs', {}).get('paragraphs', [])
duration = int(data['metadata']['duration'])
text = ' '.join(s['text'] for p in paras for s in p.get('sentences', []))
print(f'[{duration//60}:{duration%60:02d}] {text}')
")

    ALL_TRANSCRIPTS+="**$BASENAME** $TRANSCRIPT
"
    echo "  OK: $(echo "$TRANSCRIPT" | head -c 80)..."
done

rm -rf "$TEMP_DIR"

if [ -z "$ALL_TRANSCRIPTS" ]; then
    echo "Нет транскриптов для обработки"
    exit 0
fi

echo ""
echo "Все транскрипты получены. Категоризирую..."

# 3. Claude категоризация
CATEGORIZED=$(echo "$ALL_TRANSCRIPTS" | "$CLAUDE_PATH" \
    --dangerously-skip-permissions \
    --allowedTools "" \
    -p "Ты получил набор аудиорефлексий. Раздели их на две категории и выведи ТОЛЬКО результат без пояснений:

## Сделано
ТОЛЬКО свершившиеся факты и события. БЕЗ времени каждого события — время будет у заголовка аудиорефлексии.

Формат: буллеты без времени. Связанные подфакты — вложенные буллеты (4 пробела отступ).

ВАЖНО: различай события СЕГОДНЯ и события ПРОШЛЫХ ДНЕЙ (человек вспоминает что было раньше — маркеры: «вспомнил», «мы сходили», «было ещё», прошедшее время о событиях явно не сегодняшних). События прошлых дней группируй под подзаголовком «Вспомнил» с дополнительным отступом.

Пример формата:
- Позвонил X, договорились на 17:00
- Инцидент с Y: описание
- Вспомнил
    - Сходили к окулисту: результат
        - Назначили то-то
        - Заказали то-то
    - Сходили к ортопеду: результат
- Прогулялся, сделал рутину: 15 отжиманий

## Мысли
ВСЁ остальное: идеи, планы, намерения, реакции, выводы, наблюдения, бытовые задачи, что НУЖНО сделать. Формат: буллеты без времени.

СТРОГОЕ правило: если фраза содержит «нужно», «надо», «хочу», «планирую», «подумать» — это Мысли, даже если рядом с фактом. Факт отдельно в Сделано, намерение отдельно в Мысли. Язык: русский.

Транскрипты:
$ALL_TRANSCRIPTS" 2>/dev/null)

echo ""
echo "$CATEGORIZED"

if $DRY_RUN; then
    echo ""
    echo "[DRY RUN] Не записываю в $DAILY_NOTE"
    exit 0
fi

# 4. Извлечь секции
DONE_SECTION=$(echo "$CATEGORIZED" | sed -n '/^## Сделано/,/^## Мысли/{ /^## /d; p; }' | sed '/^$/d')
THOUGHTS_SECTION=$(echo "$CATEGORIZED" | sed -n '/^## Мысли/,$ { /^## Мысли/d; p; }' | sed '/^$/d')

# 5. Дописать в daily note
if [ ! -f "$DAILY_NOTE" ]; then
    echo "WARN: Daily note не найден: $DAILY_NOTE"
    echo "Создаю минимальный..."
    mkdir -p "$(dirname "$DAILY_NOTE")"
    cat > "$DAILY_NOTE" << EOF
---
tags:
  - calendar
created: $(date -Iseconds)
---

### Log (дела)

### Scratchpad
EOF
fi

# Время вставки
INSERT_TIME=$(date +%H:%M)

# Дописать в Log (дела) — перед ### Scratchpad
if [ -n "$DONE_SECTION" ]; then
    DONE_BLOCK="- $INSERT_TIME (аудиорефлексия)
$(echo "$DONE_SECTION" | sed 's/^/\t/')"

    # Вставить перед ### Scratchpad
    if grep -q '### Scratchpad' "$DAILY_NOTE"; then
        python3 -c "
import sys
content = open('$DAILY_NOTE', 'r').read()
marker = '### Scratchpad'
idx = content.index(marker)
new_content = content[:idx] + '''$DONE_BLOCK
\n''' + content[idx:]
open('$DAILY_NOTE', 'w').write(new_content)
print('  Добавлено в Log (дела)')
"
    else
        echo "" >> "$DAILY_NOTE"
        echo "$DONE_BLOCK" >> "$DAILY_NOTE"
        echo "  Добавлено в конец (Scratchpad не найден)"
    fi
fi

# Дописать в Scratchpad — в конец файла
if [ -n "$THOUGHTS_SECTION" ]; then
    THOUGHTS_BLOCK="- $INSERT_TIME (аудиорефлексия)
$(echo "$THOUGHTS_SECTION" | sed 's/^/\t/')"

    echo "" >> "$DAILY_NOTE"
    echo "$THOUGHTS_BLOCK" >> "$DAILY_NOTE"
    echo "  Добавлено в Scratchpad"
fi

# 6. Сохранить полный транскрипт в fleeting-notes как контекст IWE
FLEETING="$HOME/IWE/DS-strategy/inbox/fleeting-notes.md"
if [ -f "$FLEETING" ]; then
    echo "" >> "$FLEETING"
    echo "### Аудиорефлексия $TARGET_DATE $INSERT_TIME" >> "$FLEETING"
    echo "" >> "$FLEETING"
    echo "$ALL_TRANSCRIPTS" >> "$FLEETING"
    echo "  Полный транскрипт → fleeting-notes.md"
fi

# 7. Отметить файлы как обработанные
for audio in "${AUDIO_FILES[@]}"; do
    echo "$TARGET_DATE/$(basename "$audio")" >> "$PROCESSED_LOG"
done

echo ""
echo "Готово: ${#AUDIO_FILES[@]} файлов обработано → $DAILY_NOTE"
