---
name: notebooklm-singularity-inbox
description: "После генерации NotebookLM-материалов (Audio Overview / Quiz / Flashcards) обязательно создавать задачу в Singularity «Входящие» с ссылкой на notebook, чтобы пользователь не забыл прослушать подкаст и пройти квиз/тест"
metadata: 
  node_type: memory
  type: feedback
  horizon: hot
  domains: 
    - study-prep
    - notebooklm
    - singularity
    - followup
  status: active
  valid_from: 2026-05-18
  owner: user
  schema_version: 1
  originSessionId: e94e54f4-7915-4a15-8a24-7ec8c8809071
---

После того, как сгенерировал NotebookLM-материалы (подкаст / Quiz / Flashcards / Study guide) — **обязательно создать задачу в Singularity папке «Входящие»** (Inbox, без projectId) с:
- **title:** `Прослушать NotebookLM <тема> (Audio Overview + Quiz + Flashcards)` или короче — глагол-действие + рабочий продукт ([[feedback-singularity-tasks]])
- **notes:** прямая ссылка на notebook (`https://notebooklm.google.com/notebook/<id>`), перечень источников (R1.1:12, R1.1:13, R1.1:14), что сгенерировано (✅/⏳)
- **priority:** normal (если не критично) / high (если связано с предстоящим экзаменом/публикацией)
- **startDate:** сегодня

**Why:** 18 мая 2026 пользователь явно зафиксировал правило: NotebookLM-материалы генерируются параллельно с другой работой и легко забываются — без задачи в Singularity подкаст остаётся непрослушанным, квиз — непройденным. «Входящие» = универсальная папка для разбора при следующем Singularity-триаже (не привязка к проекту).

**How to apply:**
1. После последнего шага study-prep (или эквивалентного создания NotebookLM-материалов) → перед финальным отчётом → `mcp__singularity__create-task`.
2. **БЕЗ projectId** — задача попадает в Inbox.
3. Формулировка title строго в стиле [[feedback-singularity-tasks]] (глагол-действие + рабочий продукт в скобках).
4. В notes добавить URL notebook + что сгенерировано (Audio / Quiz / Flashcards / Study guide / Mind Map).
5. После создания — сообщить пользователю: *«Задача в Singularity Inbox создана: <title>»* в финальном отчёте.
6. Не путать с [[singularity-sync]] (он про сверку РП↔Singularity на старте дня/сессии); это правило срабатывает на закрытии конкретного артефакта.
7. Применимо ко всем study-prep сессиям: СМ R1, R5, R6, любым курсам Aisystant и аналогичным.

**Сопряжённые memory:** [[singularity-sync]], [[feedback-singularity-tasks]], [[feedback-daily-planning-singularity]].
