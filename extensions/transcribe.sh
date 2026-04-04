#!/bin/bash
# transcribe.sh — транскрипция аудио через Deepgram Nova-2
# Использование: ./transcribe.sh <audio_file> [output_title]
#
# Результат: Obsidian-заметка в $VAULT_DIR с диаризацией
#
# Требует в .exocortex.env:
#   DEEPGRAM_API_KEY=...
#   VAULT_DIR=...        (путь к Obsidian vault)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/../.exocortex.env"

# Load config
if [ ! -f "$ENV_FILE" ]; then
    echo "ERROR: $ENV_FILE not found. Create it with DEEPGRAM_API_KEY and VAULT_DIR."
    exit 1
fi
# shellcheck source=/dev/null
source "$ENV_FILE"

if [ -z "${DEEPGRAM_API_KEY:-}" ]; then
    echo "ERROR: DEEPGRAM_API_KEY not set in $ENV_FILE"
    exit 1
fi
if [ -z "${VAULT_DIR:-}" ]; then
    echo "ERROR: VAULT_DIR not set in $ENV_FILE"
    exit 1
fi

# Args
AUDIO_FILE="${1:?Usage: transcribe.sh <audio_file> [output_title]}"
OUTPUT_TITLE="${2:-}"

if [ ! -f "$AUDIO_FILE" ]; then
    echo "ERROR: File not found: $AUDIO_FILE"
    exit 1
fi

# Detect format from extension
EXT="${AUDIO_FILE##*.}"
CONTENT_TYPE="audio/$EXT"

# Generate output title from filename if not provided
if [ -z "$OUTPUT_TITLE" ]; then
    BASENAME=$(basename "$AUDIO_FILE" ".$EXT")
    # Extract date from parent dir if possible (format: YYYY-MM-DD)
    PARENT_DIR=$(basename "$(dirname "$AUDIO_FILE")")
    if [[ "$PARENT_DIR" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
        OUTPUT_TITLE="транскрипт ${PARENT_DIR} ${BASENAME}"
    else
        OUTPUT_TITLE="транскрипт ${BASENAME}"
    fi
fi

OUTPUT_FILE="$VAULT_DIR/${OUTPUT_TITLE}.md"
TEMP_JSON=$(mktemp /tmp/deepgram-XXXXX.json)

echo "Транскрибирую: $(basename "$AUDIO_FILE") ($(du -h "$AUDIO_FILE" | cut -f1))"
echo "Deepgram Nova-2 (ru, diarize, punctuate, smart_format, paragraphs)..."

# Call Deepgram API
HTTP_CODE=$(curl -s -w "%{http_code}" \
    --request POST \
    --url 'https://api.deepgram.com/v1/listen?model=nova-2&language=ru&diarize=true&punctuate=true&paragraphs=true&smart_format=true' \
    --header "Authorization: Token $DEEPGRAM_API_KEY" \
    --header "Content-Type: $CONTENT_TYPE" \
    --data-binary @"$AUDIO_FILE" \
    -o "$TEMP_JSON")

if [ "$HTTP_CODE" != "200" ]; then
    echo "ERROR: Deepgram returned HTTP $HTTP_CODE"
    cat "$TEMP_JSON"
    rm -f "$TEMP_JSON"
    exit 1
fi

echo "Получен ответ ($(du -h "$TEMP_JSON" | cut -f1)). Форматирую..."

# Parse JSON → Obsidian markdown
python3 -c "
import json, sys

with open('$TEMP_JSON') as f:
    data = json.load(f)

if 'err_msg' in data:
    print(f'ERROR: {data[\"err_msg\"]}', file=sys.stderr)
    sys.exit(1)

alt = data['results']['channels'][0]['alternatives'][0]
paras_data = alt.get('paragraphs', {})
paras = paras_data.get('paragraphs', [])
duration = data['metadata']['duration']

speakers = set()
for p in paras:
    speakers.add(p.get('speaker', 0))

lines = []
lines.append('---')
lines.append('source: Just Press Record')
lines.append(f'duration: {int(duration)}s ({int(duration//60)} мин)')
lines.append(f'speakers: {len(speakers)}')
lines.append('transcription: Deepgram Nova-2 (diarize+punctuate+smart_format)')
lines.append('---')
lines.append('')
lines.append('# $OUTPUT_TITLE')
lines.append('')

current_speaker = None
for p in paras:
    speaker = p.get('speaker', 0)
    if speaker != current_speaker:
        current_speaker = speaker
        lines.append(f'**Speaker {speaker}:**')
        lines.append('')

    sentences = [s['text'] for s in p.get('sentences', [])]
    lines.append(' '.join(sentences))
    lines.append('')

with open('$OUTPUT_FILE', 'w') as f:
    f.write('\n'.join(lines))

print(f'Готово: {len(paras)} параграфов, {len(speakers)} спикеров, {int(duration//60)} мин')
print(f'Файл: $OUTPUT_FILE')
"

rm -f "$TEMP_JSON"
