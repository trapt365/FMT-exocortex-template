---
name: "Aisystant: читаем через Obsidian Clipper, не Playwright"
description: "При прохождении курсов Aisystant Claude должен читать клиппинги из Vault1/Clippings/ — там и текст, и комментарии пользователя. Playwright только если клиппинга нет"
type: feedback
horizon: hot
domains: [учёба, aisystant, obsidian, workflow]
status: active
valid_from: 2026-05-08
owner: user
schema_version: 1
originSessionId: 258d6035-fb3a-4373-8a35-43c708f9e423
---
При прохождении курса на Aisystant пользователь параллельно читает + комментирует через Obsidian Clipper. Файлы кладутся в `/mnt/c/Users/Timur/Documents/Vault1/Clippings/<R1.X.X - название>.md`. В клиппинге:
- frontmatter с source URL и created date
- raw-текст подраздела с разметкой (жирный/курсив автора)
- **комментарии пользователя в `%% ... %%`** (Obsidian comment syntax) — это самое ценное: его конспект + черновик размышлений + выбор контекста для упражнений

**Why:** Playwright через CDP — медленный (Chrome поднять, MCP подключить, snapshot, evaluate, click). Пока Claude парсит платформу, Тимур уже прочитал и сделал заметки. Параллельная работа через Clipper даёт Claude богаче контекст (raw-текст + размышления), а Тимуру — естественный read-and-annotate flow.

**How to apply:**
1. При R3-сессии или прохождении курса R1/R6/R5 — **сначала** проверять `ls /mnt/c/Users/Timur/Documents/Vault1/Clippings/ | grep <код подраздела>`
2. Если клиппинг есть — читать его (включая `%%...%%` комментарии); Playwright не нужен
3. Если клиппинга нет — попросить Тимура заклиппить, или поднять Playwright как fallback
4. R3-обратку давать **по комментариям пользователя**, не по raw-тексту
5. Отмечать «прочитано» на платформе пользователь делает сам — Claude этим не занимается

**Связь с другими feedback:**
- `feedback-false-completion-learning.md` — клиппинг с комментариями = форма «согласую но не понимаю» легче ловится: сразу видно где есть пример, где нет
- `feedback-ritual-roles.md` — учёба R16 ↔ R3 сохраняется
