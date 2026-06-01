---
name: "Mobile Claude branches in DS-strategy"
description: "На мобиле через claude.ai пользователь создаёт ветки claude/<topic>-<id> в DS-strategy — десктоп-сессия должна их искать"
type: feedback
horizon: warm
domains: [ds-strategy, session-open, mobile]
status: active
valid_from: 2026-05-13
owner: user
schema_version: 1
originSessionId: 0948ed41-92da-498e-9524-626b516d3c24
---
# Мобильные claude-ветки в DS-strategy

**Правило:** Когда пользователь говорит «то что мы сделали сегодня» / «вчера» по теме, для которой нет коммитов в основной ветке и нет dirty файлов — проверять `git -C /home/trapt22/IWE/<repo> branch -a | grep claude/` ДО того как уточнять у пользователя.

**Why:** Тимур работает с мобильного через claude.ai (приложение Claude). Мобильные сессии создают артефакты в feature-ветках формата `claude/<slug>-<id>` (например `claude/geoonline-quarterly-report-mh5lY`, `claude/end-of-day-RWhbt`, `claude/cottage-cheese-recipes-G4m9x`). Эти ветки — в `origin/`, в локальный main не мерджатся автоматически. Десктоп-сессия (Claude Code) может их пропустить, если ищет только в текущей ветке / dirty файлах / последних коммитах main.

**Прецедент 2026-05-13:** пользователь сказал «то что мы сделали сегодня по геонлайну». В main DS-strategy сегодня были коммиты только Day Open + Slot1 R3, в geonline-tracking — ничего за неделю. Я уточнил «где презентация?» через AskUserQuestion. Ответ: «в geonline-tracking». Не нашёл там, спросил повторно через скриншот. Оказалось — `inbox/WP-8-geoonline-3month-report.marp.md` в ветке `origin/claude/geoonline-quarterly-report-mh5lY` (создано в 03:38 на мобильной сессии). 2 раунда вопросов вместо одной grep-команды.

**How to apply:**
1. При неоднозначности «свежая работа» в DS-strategy / других репо: первым делом
   ```
   git -C /home/trapt22/IWE/<repo> fetch
   git -C /home/trapt22/IWE/<repo> branch -a | grep -i claude/
   git -C /home/trapt22/IWE/<repo> log --oneline --all --since="yesterday" --no-merges
   ```
2. Особенно DS-strategy (главный governance-репо, куда мобильные сессии чаще всего пишут).
3. Читать файлы из ветки без чекаута: `git show <branch>:<path>` — не перебивает рабочее дерево.
4. Если найден файл в claude-ветке — сообщить пользователю «нашёл в ветке X, читаю без переключения». Не предлагать merge без явного запроса.
