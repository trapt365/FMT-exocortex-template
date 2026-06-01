---
name: Extensions path для протоколов
description: При запуске day-open/day-close/week-close/strategy-session всегда проверять /home/trapt22/IWE/extensions/, а не skill-dir/extensions/
type: feedback
originSessionId: 4cb14cf9-0f70-49e5-a551-e0acf34fe367
---
**Правило:** когда SKILL.md (day-open, day-close, week-close, strategy-session) говорит «проверить `extensions/day-open.before.md`» — искать файл по **абсолютному пути** `/home/trapt22/IWE/extensions/day-open.before.md`, НЕ в `<skill-dir>/extensions/`.

**Why:** SKILL.md написан как L1-шаблон с относительным путём. Claude по умолчанию интерпретирует его как skill-dir (`/home/trapt22/IWE/.claude/skills/day-open/extensions/`) — там файлов нет, и extensions пропускаются молча. Пользователь держит свои extensions в `/home/trapt22/IWE/extensions/` (workspace root), потому что `params.yaml → author_mode: false` запрещает прямое редактирование L1 skills (Extensions Gate из CLAUDE.md §9). Это было повторяющимся багом на Day Open несколько раз.

**How to apply:**
- Day Open step 0 «Extensions (before)» → `ls /home/trapt22/IWE/extensions/day-open.before.md` (абсолютный путь, не `ls extensions/...`)
- Day Open step 6c «Extensions (after)» → `ls /home/trapt22/IWE/extensions/day-open.after.md`
- Day Open step 7b «Extensions (checks)» → `/home/trapt22/IWE/extensions/day-open.checks.md`
- Аналогично для day-close, week-close, strategy-session: `/home/trapt22/IWE/extensions/{protocol}.{before|after|checks}.md`
- Если файл есть — прочитать и выполнить **до** записи DayPlan (для before/after) или **до** commit (для checks)
- Если файлов нет — пропустить молча

**Текущий inventory `/home/trapt22/IWE/extensions/`:**
- `day-open.before.md` — process-reflections.sh
- `day-open.after.md` — Buddy Prep (пн), спринт-дашборд, еженедельные метрики + эскалация, автоэскалация привычек в DayPlan, Study Prep, Singularity Sync, Scheduler marker
- `day-close.after.md`
- `strategy-session.after.md`
- `week-close.after.md`
