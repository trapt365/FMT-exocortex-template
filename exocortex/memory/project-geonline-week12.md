---
name: Geonline week 12 reports completed
description: Week 12 transcription (8 files via Soniox) + Executive Summary + Hypothesis Tracker done 2026-05-07
type: project
horizon: warm
domains: [geonline, consulting, tracking]
status: active
valid_from: 2026-05-07
schema_version: 1
supersedes: project-geonline-week09.md
originSessionId: 6a6a74e9-9f6c-4569-a61a-d97c8fc239f5
---
Geonline week 12 deliverables completed 2026-05-07. Commit `6dee500` в `geonline-tracking`.

**What was done:**
- 8 audio files transcribed via Soniox API (ru+kk, diarization, ~4h 20min total)
- Маппинг audio_id ↔ имя дал пользователь (скриншоты Telegram).
- Transcripts saved to Vault1 (`geonline week-12 {name}.md`) and `geonline-tracking/transcripts/`
- Executive Summary: `reports/week-12-executive-summary.md`
- Hypothesis Tracker: `docs/week-12-hypothesis-tracker.md` (196 гипотез, +25 vs нед.11)
- Tracker notes: `tracker-notes/week-12-notes.md`

**Why:** Trekhn-week 12 встречи 29 апр–6 мая. Обычный недельный формат для Дамира (CEO) и Aziza (трекер).

**How to apply:** Для week 13+ flow тот же:
1. Symlink 8 audio файлов в `/tmp/geonline-w13-audio/`
2. `cd /mnt/c/Users/Timur/projects/strategy-tracking-system && set -a && source .env && set +a && npx tsx scripts/soniox-test.ts /tmp/geonline-w13-audio/`
3. Парсер: `python3 /tmp/parse-soniox.py <json> <person> 13 2026-05-XX > out.md`
4. Чтение всех транскриптов → синтез exec summary (по шаблону week-12) + hypothesis tracker (delta от 12)
5. Коммит в geonline-tracking

**Key findings week 12:**
- 🚨 **CFO Мерей уходит с июля** — конфликт интересов, передачи дел не запущена, CEO опубликовал вакансию через Threads без прямого разговора
- 🆕 **CEO Дамир впервые в трекинге** — по запросу Айдара, прошлись по 5 личным KR
- ✅ **Запуск 1 мая 88% плана** (618 пик, 4-5 предоплат — первый опыт)
- ✅ **Аудит маркетинга финализирован** (8 блоков, 3.05/5, brainstorm 8 мая)
- ✅ **Тест-драйв ROMI 2× рост** (400% → 816% за 2 недели, ДРР 9.1%)
- 🔴 **SuperApp регистрации замедлились в 2.4×** (1200 → 500/нед) — Шынгыс перегружен
- 🔴 **Mystery shopping #3** — те же системные пробелы ОП что и нед.11
- ⚠️ **Турар + Айым не на встречах** — нет данных по академии и PR
- 🟡 **План на май не готов до 7 мая** — задерживает буткемп 1 июня (цель 20-25К)
- 25 новых гипотез добавлено (13 в маркетинге после аудита)

**Маппинг audio_id (ref для будущих сверок):**
- audio1147679152 → мерей-финансист (CFO)
- audio1157108412 → аудит-маркетинга (group session)
- audio1218030947 → айбол (маркетинг)
- audio1246295812 → шынгыс (CPO/SuperApp)
- audio1592776112 → дамир (CEO впервые)
- audio1613198786 → жанель (продажи)
- audio1966774831 → мерей-ром (контент-маркетинг)
- audio1981596353 → арай (HR)

**Soniox config:** API key в `/mnt/c/Users/Timur/projects/strategy-tracking-system/.env`. Скрипт `scripts/soniox-test.ts` (model `stt-async-v4`, language hints ru+kk, diarization). Raw JSON в `data/soniox-results/`.
