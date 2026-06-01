---
name: audio-pipeline
description: "Just Press Record → Deepgram → daily note (Log/Scratchpad) + fleeting-notes, с идемпотентностью и автозапуском при ОРЗ"
metadata: 
  node_type: memory
  type: reference
  valid_from: 2026-04-15
  originSessionId: 1805c871-ec36-4b66-8ffd-e95011d8431b
---

Audio pipeline для транскрипции аудиозаметок и обработки рефлексий.

**Скрипты:**
- `DS-exocortex/extensions/transcribe.sh` — единичная транскрипция → Vault1
- `DS-exocortex/extensions/process-reflections.sh` — batch: JPR → Deepgram → Claude категоризация → daily note (Log + Scratchpad) + fleeting-notes

**API:** Deepgram Nova-2 (ru, diarize, punctuate, smart_format)
**Ключ:** `.exocortex.env` (DEEPGRAM_API_KEY, gitignored)
**Источник:** `$JUST_PRESS_RECORD` (из .exocortex.env) — iCloud Just Press Record
**Выход:** `$VAULT_DIR/Calendar/YYYY-MM-DD.md` (daily note) + `DS-strategy/inbox/fleeting-notes.md`

**Категоризация:** Claude разделяет на факты/события (→ Log) и мысли/намерения (→ Scratchpad). События прошлых дней → блок «Вспомнил».

**Идемпотентность:** `~/.local/state/exocortex/reflections-processed.log` — трекает обработанные файлы, безопасно запускать несколько раз.

**Автозапуск (extensions):**
- `extensions/protocol-open.after.md` — при Session Open
- `extensions/day-open.before.md` — при Day Open
- `extensions/day-close.after.md` — при Day Close

**Ручной синк:** открыть JPR на iPhone перед работой (Apple Watch → iCloud).

**Известная хрупкость — iCloud-заглушки (2026-06-01):** новые записи синкаются в `$JUST_PRESS_RECORD` как online-only placeholders (Files On-Demand). `stat` показывает размер из метаданных, но чтение байтов из WSL даёт `Input/output error` → curl в Deepgram падает (`--data-binary: error reading file`, exit 26), скрипт молча обрывается без записи в processed-log (повтор безопасен). **Диагностика:** `head -c 16 файл | od` → I/O error = заглушка. **Обход:** материализовать с Windows-стороны —
`powershell.exe -NoProfile -Command "Get-ChildItem -LiteralPath '<win-path>' -Filter *.m4a | %{ [System.IO.File]::ReadAllBytes(\$_.FullName) }"` → затем перезапустить `process-reflections.sh YYYY-MM-DD`. Баг по молчаливому падению: `DS-strategy/inbox/bugs/bug-2026-06-01-icloud-placeholder-silent-fail.md`.
