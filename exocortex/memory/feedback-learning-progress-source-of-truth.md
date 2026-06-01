---
name: Учебный прогресс — source-of-truth = Aisystant, не DayPlan
description: При Day Close не доверять только статусу pending в DayPlan для учебного прогресса; проверять Aisystant через course-progress skill или явно спрашивать пользователя «сделал/планируешь сделать?»
type: feedback
horizon: hot
domains: [day-close, learning, aisystant]
status: active
valid_from: 2026-05-07
owner: user
schema_version: 1
originSessionId: e910e041-9e2e-4d79-8eed-f93dbcd226e6
---
При Day Close, если у учебного слота (СМ R1.0:N, R6.X) статус `pending` в DayPlan и пользователь говорит «буду делать вечером» — НЕ помечать как carry-over автоматически. Спросить явно «сделано или ещё нет» при следующем взаимодействии в этот день, ИЛИ запустить `/course-progress` для актуальной сверки с Aisystant.

**Why:** 7 мая 2026 я закрыл день со статусом «СМ R1.0:7 carry-over», пользователь поправил: «R1.0:7 + R1.0:8 сделаны». Я опёрся на DayPlan-статус + ответ «буду делать вечером», но пользователь делает учёбу параллельно с моим Day Close. Aisystant + явное подтверждение = source-of-truth, DayPlan = планирующий слой.

**How to apply:**
- При Day Close, если учебный РП в pending: спросить «уже сделал или планируешь?» (а не просто «делал ли?»)
- При сомнении — запустить `/course-progress` (Playwright → Aisystant) перед записью итогов
- Не путать «не отмечено в DayPlan» с «не сделано»
- Учебный прогресс ≠ техзадача: пользователь может сделать в любое время суток, не обязательно в плановом слоте
