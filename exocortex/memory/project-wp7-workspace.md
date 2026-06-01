---
name: project-wp7-workspace
description: "WP-7 ARB AI-Tracking: роль IWE и workspace разделение"
metadata: 
  node_type: memory
  type: project
  originSessionId: f2ea1cf6-b8d5-4a3f-983d-052456e88086
---

WP-7 coding (R6 Кодировщик) выполняется в Windows-workspace `/mnt/c/Users/Timur/projects/strategy-tracking-system` — **вне IWE**.

**Why:** репозиторий клиентского проекта живёт в Windows, не в `/home/trapt22/IWE/`. IWE не владеет этим кодом.

**Роль IWE в WP-7:**
1. **Фиксация результатов** — WP context file (`DS-strategy/inbox/WP-7-*.md`), WeekPlan/DayPlan статусы, коммиты в DS-strategy.
2. **Верхнеуровневый project management** — sprint-статусы, carry-over, КТ, scope-решения.
3. **Push** — при Quick/Day Close коммитит изменения DS-strategy (не strategy-tracking-system).

**Что IWE НЕ делает:**
- Не пишет код в strategy-tracking-system напрямую через Edit/Write (это происходит в отдельной сессии Claude Code в Windows workspace).
- Не запускает тесты (`npx vitest`) в контексте IWE-сессии — это делается в Windows workspace.

**How to apply:** при Session Open WP-7 — Ритуал объявляет R6 Кодировщика, но сама кодировка идёт в другом контексте. IWE-сессия занимается только project management и фиксацией. Если нужна реальная dev-работа → переключиться в Windows workspace (отдельная Claude Code сессия).
