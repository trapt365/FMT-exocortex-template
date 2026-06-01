---
name: feedback-dayopen-after-extensions
description: "Day Open шаг 6c (extensions after) пропускается — там живёт Singularity sync, спринт-дашборд, scheduler marker"
metadata: 
  node_type: memory
  type: feedback
  horizon: hot
  domains: 
    - day-open
    - singularity
    - extensions
  status: active
  valid_from: 2026-05-25
  owner: user
  schema_version: 1
  originSessionId: d5d04322-c20e-4aff-bf1b-9cf9787dd305
---

Шаг 6c (`load-extensions.sh day-open after`) пропускается при Day Open. В этом файле живут:
- Singularity Sync (создание задач DayPlan → Singularity с useTime)
- Спринт-дашборд + еженедельные метрики (WP-16)
- Buddy Prep (понедельник)
- Scheduler marker (`~/.local/state/exocortex/strategist-morning-YYYY-MM-DD`)
- Study Prep (при наличии учёбы в плане)

**Why:** Буквенные суффиксы шагов (5a2, 5c, 5d, 6b, 6c, 7a-7d) воспринимаются как «под-пункт родительского шага», а не самостоятельный обязательный шаг. После выполнения 6b взгляд перепрыгивает на цифру 7, 6c проглатывается. Тимур фиксировал пропуск несколько раз подряд.

**How to apply:** В TodoWrite при Day Open каждый буквенный шаг = ОТДЕЛЬНАЯ задача. Никогда не группировать «5+5a2+5c+5d» или «6+6b+6c» в одну строку. Полный список отдельных задач для TodoWrite:
- Шаг 5a2: Видео
- Шаг 5c: Редактор контента
- Шаг 5d: Scout
- Шаг 6: Мир (новости)
- Шаг 6b: Требует внимания
- Шаг 6c: Extensions after (Singularity sync + спринт-дашборд + маркер) — ОТДЕЛЬНО
- Шаг 7a+7a2: DayPlan + session log записать
- Шаг 7b: Extensions checks
- Шаг 7c: git commit + push
- Шаг 7d (из extensions after): Singularity sync + scheduler marker
- Шаг 7e: Compact dashboard
