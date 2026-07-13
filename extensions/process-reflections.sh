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
    RECORD_TIME=$(python3 -c "import os, datetime; print(datetime.datetime.fromtimestamp(os.path.getmtime('$audio')).strftime('%H:%M'))" 2>/dev/null || echo "??:??")

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

    ALL_TRANSCRIPTS+="**$BASENAME** [$RECORD_TIME] $TRANSCRIPT
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
    -p "Ты получил аудиозаписи. Каждая помечена временем [HH:MM]. Разложи их на ЧЕТЫРЕ категории и выведи ТОЛЬКО результат без пояснений. Всегда выводи все четыре заголовка (даже если раздел пустой — заголовок без строк).

## Хронометраж
ТОЛЬКО краткие пинг-ответы формата «что сейчас делаю + тип активности» (П/И/Л/О/Д/ТО).
Признаки: короткая запись, настоящее/недавнее время, фиксирует активность без развёрнутых мыслей.
Формат каждой строки: HH:MM — что делал (тип)
Пример:
14:30 — работаю над стратегией (И)

## Задачи
То, что НАДО СДЕЛАТЬ: явные намерения «надо / не забыть / нужно / купить / позвонить / отправить / записаться».
Формат каждой строки: глагол-действие + рабочий продукт (по Дорофееву), одна задача на строку, без времени.
Пример:
- Позвонить в сервис по поводу ГРМ (записаться на диагностику)
- Купить мульчу для сада

## Фундамент
То, что пилот СЪЕЛ/ПРИГОТОВИЛ или ПОТРАТИЛ/КУПИЛ (быт: питание и финансы). ОБЯЗАТЕЛЬНО сохраняй числа: суммы, граммы, порции, ккал — если названы.
Подстроки (пропусти пустую):
Финансы: <что потратил/купил + сумма, если названа>
Питание: <блюдо + количество (граммы/порции); несколько блюд через точку с запятой>
Если количество блюда не названо — добавь к нему пометку «(кол-во?)».

## Scratchpad
ВСЁ остальное: развёрнутые мысли, идеи, выводы, наблюдения, события с контекстом.
Формат: буллеты без времени.
Если запись содержит и пинг, и мысль, и задачу — разнеси части по разным разделам.

Язык вывода: русский.

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
HRON_SECTION=$(echo "$CATEGORIZED" | sed -n '/^## Хронометраж/,/^## /{ /^## /d; p; }' | sed '/^$/d')
TASKS_SECTION=$(echo "$CATEGORIZED" | sed -n '/^## Задачи/,/^## /{ /^## /d; p; }' | sed '/^$/d')
FUND_SECTION=$(echo "$CATEGORIZED" | sed -n '/^## Фундамент/,/^## /{ /^## /d; p; }' | sed '/^$/d')
THOUGHTS_SECTION=$(echo "$CATEGORIZED" | sed -n '/^## Scratchpad/,$ { /^## Scratchpad/d; p; }' | sed '/^$/d')

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

### Хронометраж

### Scratchpad
EOF
fi

# Вставить в ### Хронометраж — с нормализацией, дедупликацией и сортировкой
if [ -n "$HRON_SECTION" ]; then
    # Читаем существующий блок из файла
    EXISTING_HRON=$(python3 -c "
import re
content = open('$DAILY_NOTE').read()
m = re.search(r'### Хронометраж\n(.*?)(?=\n###|\Z)', content, re.DOTALL)
print(m.group(1).strip() if m else '')
" 2>/dev/null || echo "")

    COMBINED_HRON="$EXISTING_HRON
$HRON_SECTION"

    # Claude нормализует: единый формат, инференс типа курсивом, деdup, сортировка
    NORMALIZED_HRON=$(echo "$COMBINED_HRON" | "$CLAUDE_PATH" \
        --dangerously-skip-permissions \
        --allowedTools "" \
        -p "Нормализуй записи хронометража. Выводи ТОЛЬКО готовые строки, ничего лишнего.

Первая строка вывода — всегда: [[Хронометраж — категории|П · И · Л · О · Д · ТО]]

Формат каждой последующей строки: HH:MM — Глагол описание (Тип)
Типы: П=продуктивная работа, И=инвестиционная (развитие/системы), Л=личное/отдых, О=обеспечение/рутина, Д=движение/спорт, ТО=техобслуживание/уборка

Правила:
- Каждая запись начинается с глагола в настоящем времени (наблюдаемое действие): «Смотрю», «Работаю», «Сплю», «Убираю»
- Если тип явно указан в записи — оставь как есть: (И)
- Если тип не указан или неясен — определи по контексту и напиши курсивом: (*И*)
- Дубли (одинаковое время + похожее описание) → одна строка
- Строки без времени (легенды, ссылки [[...]], заголовки) → удалить (легенда добавляется автоматически первой строкой)
- Отсортировать по времени
- Выводить по одной строке, без маркеров списка и без пустых строк между

Входные записи:
$COMBINED_HRON" 2>/dev/null)

    # Записать нормализованный хронометраж в temp-файл — избегаем heredoc-инъекции
    # через кавычки (""") или спецсимволы в выводе Claude
    HRON_TMPFILE=$(mktemp /tmp/hron-normalized-XXXXX)
    printf '%s' "$NORMALIZED_HRON" > "$HRON_TMPFILE"

    python3 - "$DAILY_NOTE" "$HRON_TMPFILE" << 'PYEOF'
import re, sys

daily_note = sys.argv[1]
normalized = open(sys.argv[2]).read().strip()

with open(daily_note, 'r') as f:
    content = f.read()

marker = '### Хронометраж'
if marker not in content:
    content += f'\n{marker}\n'

pattern = re.compile(r'(### Хронометраж\n)(.*?)(?=\n###|\Z)', re.DOTALL)
new_section = f'{marker}\n{normalized}\n'
# lambda m: избегает интерпретации \1, \2 и т.п. в тексте замены
content = pattern.sub(lambda m: new_section, content)

with open(daily_note, 'w') as f:
    f.write(content)
print('  Хронометраж обновлён (нормализован, отсортирован)')
PYEOF

    rm -f "$HRON_TMPFILE"
fi

# Дописать в ### Scratchpad — в конец секции
if [ -n "$THOUGHTS_SECTION" ]; then
    THOUGHTS_TMPFILE=$(mktemp /tmp/thoughts-XXXXX)
    printf '%s' "$THOUGHTS_SECTION" > "$THOUGHTS_TMPFILE"

    python3 - "$DAILY_NOTE" "$THOUGHTS_TMPFILE" << 'PYEOF'
import re, sys

daily_note = sys.argv[1]
new_entries = open(sys.argv[2]).read().strip()
marker = '### Scratchpad'

with open(daily_note, 'r') as f:
    content = f.read()

if marker not in content:
    content += f'\n{marker}\n'

pattern = re.compile(r'(### Scratchpad\n)(.*?)(?=\n###|\n---|\Z)', re.DOTALL)
match = pattern.search(content)
existing = match.group(2).rstrip() if match else ''

combined = (existing + '\n' + new_entries).strip()
new_section = f'{marker}\n{combined}\n'
content = pattern.sub(lambda m: new_section, content)

with open(daily_note, 'w') as f:
    f.write(content)
print('  Добавлено в Scratchpad')
PYEOF

    rm -f "$THOUGHTS_TMPFILE"
fi

# 5b. Задачи → очередь Singularity Inbox + секция daily note (WP-40 Ф2)
DS_STRATEGY="$HOME/IWE/DS-strategy"
QUEUE="$DS_STRATEGY/inbox/singularity-queue.md"
if [ -n "$TASKS_SECTION" ]; then
    TASKS_TMPFILE=$(mktemp /tmp/tasks-XXXXX)
    printf '%s' "$TASKS_SECTION" > "$TASKS_TMPFILE"
    python3 - "$DAILY_NOTE" "$QUEUE" "$TASKS_TMPFILE" "$TARGET_DATE" << 'PYEOF'
import os, re, sys
note, queue, tf, date = sys.argv[1:5]
tasks = [re.sub(r'^\s*[-*]\s*', '', l).strip() for l in open(tf, encoding='utf-8') if l.strip()]
tasks = [t for t in tasks if t]
if not tasks:
    sys.exit(0)
os.makedirs(os.path.dirname(queue), exist_ok=True)
existing = (open(queue, encoding='utf-8').read() if os.path.isfile(queue)
            else "# Очередь задач в Singularity Inbox\n\n> Наполняется обработчиком рефлексий (WP-40). Дренаж — при открытии сессии через MCP Singularity: создать незакрытые в Inbox, отметить [x].\n")
added = 0
for t in tasks:
    if t not in existing:
        existing = existing.rstrip() + f"\n- [ ] {t}  <!-- {date} -->"
        added += 1
open(queue, 'w', encoding='utf-8').write(existing.rstrip() + "\n")
c = open(note, encoding='utf-8').read() if os.path.isfile(note) else "---\ntags:\n  - calendar\n---\n"
marker = "### Задачи (→ Singularity)"
block = "\n".join(f"- {t}" for t in tasks)
if marker in c:
    c = re.sub(r'(### Задачи \(→ Singularity\)\n)(.*?)(?=\n###|\n---|\Z)',
               lambda m: m.group(1) + (m.group(2).rstrip() + "\n" + block + "\n"), c, count=1, flags=re.DOTALL)
else:
    c = c.rstrip() + f"\n\n{marker}\n{block}\n"
open(note, 'w', encoding='utf-8').write(c)
print(f'  Задачи: +{added} в очередь Singularity, {len(tasks)} в daily note')
PYEOF
    rm -f "$TASKS_TMPFILE"
fi

# 5c. Фундамент (еда/траты) → DayPlan (S-48) + очередь Cronometer (WP-40)
if [ -n "$FUND_SECTION" ]; then
    DAYPLAN="$DS_STRATEGY/current/DayPlan $TARGET_DATE.md"
    CRONQ="$DS_STRATEGY/inbox/cronometer-queue.md"
    FUND_TMPFILE=$(mktemp /tmp/fund-XXXXX)
    printf '%s' "$FUND_SECTION" > "$FUND_TMPFILE"
    python3 - "$DAYPLAN" "$FUND_TMPFILE" "$CRONQ" "$TARGET_DATE" << 'PYEOF'
import os, re, sys
dayplan, tf, cronq, date = sys.argv[1:5]
lines = [l.strip() for l in open(tf, encoding='utf-8') if l.strip()]
fin = [re.sub(r'(?i)^финансы:\s*', '', l) for l in lines if l.lower().startswith('финансы')]
pit = [re.sub(r'(?i)^питание:\s*', '', l) for l in lines if l.lower().startswith('питание')]
if not fin and not pit:
    sys.exit(0)
# 1) DayPlan «Фундамент»
if os.path.isfile(dayplan):
    c = open(dayplan, encoding='utf-8').read()
    add = []
    if fin: add.append('- Финансы: ' + '; '.join(fin))
    if pit: add.append('- Питание: ' + '; '.join(pit))
    block = "\n".join(add)
    if '## Фундамент' in c:
        c = re.sub(r'(## Фундамент\n)(.*?)(?=\n##|\n---|\Z)',
                   lambda m: m.group(1) + (m.group(2).rstrip() + "\n" + block + "\n"), c, count=1, flags=re.DOTALL)
    else:
        c = c.rstrip() + f"\n\n## Фундамент\n{block}\n"
    open(dayplan, 'w', encoding='utf-8').write(c)
    print('  Фундамент: DayPlan обновлён')
else:
    print('  Фундамент: DayPlan не найден — пропускаю запись в план')
# 2) Очередь Cronometer: каждое блюдо отдельной строкой (дренаж при Day Open через /cronometer)
dishes = []
for p in pit:
    for d in re.split(r'[;.]\s*', p):
        d = d.strip()
        if d: dishes.append(d)
if dishes:
    os.makedirs(os.path.dirname(cronq), exist_ok=True)
    existing = (open(cronq, encoding='utf-8').read() if os.path.isfile(cronq)
                else "# Очередь еды в Cronometer\n\n> Наполняется обработчиком рефлексий (WP-40). Дренаж при Day Open: залогировать через /cronometer (log-food); если количество неясно «(кол-во?)» — уточнить у пилота.\n")
    added = 0
    for d in dishes:
        if d not in existing:
            existing = existing.rstrip() + f"\n- [ ] {d}  <!-- {date} -->"; added += 1
    open(cronq, 'w', encoding='utf-8').write(existing.rstrip() + "\n")
    print(f'  Cronometer: +{added} блюд(а) в очередь')
PYEOF
    rm -f "$FUND_TMPFILE"
fi

# 6. Сохранить полный транскрипт в fleeting-notes как контекст IWE
INSERT_TIME=$(date +%H:%M)
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
