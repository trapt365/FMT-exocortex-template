# Протокол Close (ОРЗ-фрактал)

> **Три масштаба:** Сессия (Quick Close), День (Day Close), Неделя (Week Close).
> **Источник:** CLAUDE.md § 2 (slim) → этот файл.
> **Принцип:** «не потерять» (сессия) отделено от «навести порядок» (день).

---

## § Масштаб: Сессия (Quick Close)

> **Триггер:** «закрываю сессию», «всё», «закрывай», или РП завершён.
> **Роль:** R6 Кодировщик
> **«Закрывай» = push сразу без вопросов** (пользователь дал согласие словом).
> **Бюджет:** ~3 мин. Цель — зафиксировать результат и не потерять знание.

### Различение: Quick Close vs Day Close vs Week Close

| | Quick Close (сессия) | Day Close (день) | Week Close (неделя) |
|---|------|--------|--------|
| **Цель** | Не потерять | Навести порядок | Ротация и стратегия |
| **Что пишем** | Итоги + «Осталось» | Итоги дня + «На завтра» | Метрики + carry-over |
| **Governance** | Только MEMORY.md | Batch: WeekPlan, DayPlan, WP-REGISTRY, Linear, backup | Ротация уроков, свежая таблица MEMORY |
| **Верификация** | Агент сам (6 пунктов) | Haiku R23 (полный чеклист) | В составе Week Review |

## Exit Protocol (ОБЯЗАТЕЛЬНО при завершении каждой роли)

> При завершении единицы работы в любой роли — ОБЯЗАН выполнить 3 шага.
> Тест: если роль не выполнит шаги — узнает ли кто-то, что работа выполнена? Нет → нарушен.

| # | Шаг | Что делать |
|---|-----|-----------|
| 1 | **Артефакт** | Зафиксировать результат (коммит, файл, запись) |
| 2 | **Статус** | Обновить трекер (MEMORY.md, WP context) |
| 3 | **Уведомление** | Сообщить следующему (пользователь, агент, Стратег) |

---

### Алгоритм Quick Close (6 шагов)

0. **Pull** → `cd DS-strategy && git pull --rebase`
1. **Commit + Push** — все изменения зафиксированы
1b. **CHANGELOG FMT** (если были коммиты в FMT-exocortex-template): обновить `FMT-exocortex-template/CHANGELOG.md` **сейчас**, пока контекст изменений свежий. На Day Close контекст потерян.
2. **KE (Knowledge Extraction)** → прочитай и выполни `DS-IT-systems/DS-ai-systems/extractor/prompts/session-close.md`:
   - Собрать отложенные captures + проверить пропущенные
   - Классифицировать → маршрутизировать → формализовать → валидировать
   - Показать Extraction Report → получить одобрение
   - Применить одобренные (accept → Pack/CLAUDE.md/memory)
   - Немедленные captures (CLAUDE.md, repo CLAUDE.md) — применить сразу
3. **Verification Gate** (VR.M.003 — приёмка WP):
   - Прочитать WP context file → извлечь критерии готовности
   - Проверить по verification_class:
     - **trivial/closed-loop:** автоматический pass (не задерживать Close)
     - **open-loop:** содержательная проверка → результат в секцию «Что проверить» отчёта
     - **problem-framing:** полная проверка + пометка «требует приёмки человеком»
   - Если РП done → verdict обязателен. Если in_progress → skip
   - Verdict НЕ блокирует Close — записывается в отчёт для решения человека
4. **MEMORY.md** — обновить статус РП (одна строка: `in_progress` / `done`)
5. **WP Context File:**
   - in_progress → обновить секцию «Осталось» в `DS-strategy/inbox/WP-{N}-{slug}.md`
   - done → пометить (архивация — на Day Close)
   - Незавершённое → context file. Идея → `<repo>/MAPSTRATEGIC.md`. Зерно → `DS-strategy/drafts/draft-list.md`
6. **Отчёт** (5-7 строк) + закоммитить DS-strategy

### Чеклист Quick Close (агент проверяет сам)

- [ ] Всё закоммичено и запушено
- [ ] **CHANGELOG FMT:** коммиты в FMT → CHANGELOG обновлён (пока контекст свежий)
- [ ] KE выполнен, captures применены
- [ ] MEMORY.md: статус РП обновлён
- [ ] WP Context: «Осталось» записано (или done помечен)
- [ ] Repo CLAUDE.md проверен (если feat-коммиты)
- [ ] Отчёт сформирован

> **Без верификации Haiku** — 6 фактических пунктов, context isolation не нужна.
> **Исключения:** сессия ≤15 мин, сессия-вопрос без изменений.

### Шаблон отчёта Quick Close

```
**РП:** #N — [название]
**Статус:** done / in_progress
**Класс верификации:** closed-loop / open-loop / problem-framing

**Исполнитель:** A1 Claude Code (модель: Opus 4.6 / Sonnet 4.6 / Haiku 4.5)
**Роли в сессии:**
- R6 Кодировщик: [что сделал]
- R2 Экстрактор: [N кандидатов → куда / не активирован]

**Сделано:** [итог]
**Captures:** [N → Pack, N → DS docs/, N → IWE root]. «0» только если ничего не записано.
**Что проверить:** [что требует внимания человека]
**Git:** закоммичено + запушено ✅
<!-- YOUR CUSTOM CHECKS HERE -->
**Осталось:** ничего / [что — Agent→Agent handoff для следующей сессии]
```

> Указывать только активированные роли. R2 — указывать всегда (даже «не активирован»).
> Основание: DP.D.033 — роль ≠ исполнитель.

---

## § Масштаб: День (Day Close)

> **Триггер:** «закрываю день» / «итоги дня»
> **Роль:** R1 Стратег
> **Бюджет:** ~10 мин. Включает governance, который не делается на Quick Close.
> **Формат:** Стратег собирает данные → показывает черновик → пользователь одобряет → запись.
> **Скрипт:** `day-close.sh` автоматизирует механические шаги (backup, reindex, linear sync).

### Алгоритм Day Close (12 шагов)

#### 1. Сбор данных

```bash
for repo in $(ls {{WORKSPACE_DIR}}/); do
  if [ -d {{WORKSPACE_DIR}}/$repo/.git ]; then
    commits=$(git -C {{WORKSPACE_DIR}}/$repo log --since="today 00:00" --oneline --no-merges 2>/dev/null)
    [ -n "$commits" ] && echo "=== $repo ===" && echo "$commits"
  fi
done
```

Сопоставить коммиты с таблицей «На сегодня» из DayPlan → определить статусы.

#### 2. Governance batch (одним проходом)

**2a.** Обновить `DS-strategy/current/Plan W{N}...` (WeekPlan): статусы РП. **Grep по номеру РП** — обновить ВСЕ упоминания.

**2b.** Обновить `DS-strategy/current/DayPlan YYYY-MM-DD.md`: статусы **всех строк** (РП + ad-hoc). Done → зачеркнуть.

**2c.** Обновить `DS-strategy/docs/WP-REGISTRY.md`: статусы + даты.

**2d.** Обновить `DS-strategy/inbox/open-sessions.log`: удалить строки закрытых сессий.

**2e.** Governance-синхронизация: новые репо/сервисы за день? → REPOSITORY-REGISTRY, navigation.md, MAP.002↔PROCESSES.md.

**2f.** ~~CHANGELOG FMT~~ — перенесён в Quick Close (шаг 1b). На Day Close только проверить, что не пропущен.

#### 3. Архивация

- Done WP context files → `mv inbox/WP-{N}-*.md → archive/wp-contexts/`
- **Done-РП → удалить строку из MEMORY.md** (они уже в WP-REGISTRY и WeekPlan)

> **Правило:** MEMORY.md хранит ТОЛЬКО активные РП (in_progress + pending). Done = удалить.

#### 4. Автоматические шаги (скрипт `day-close.sh`)

```bash
# Запуск одной командой:
{{WORKSPACE_DIR}}/DS-IT-systems/DS-ai-systems/synchronizer/scripts/day-close.sh
```

Скрипт выполняет:
- **Linear sync:** `linear-sync.sh` (синхронизация статусов)
- **knowledge-mcp reindex:** `selective-reindex.sh` для изменённых Pack/DS
- **Backup:** `memory/ + CLAUDE.md → DS-strategy/exocortex/`

#### 5. Мультипликатор IWE (расчёт)

> **Мультипликатор = Бюджет закрыт / WakaTime.** Показывает, насколько агент-экзоскелет усиливает работу.

**Алгоритм:**

1. **WakaTime** — физическое время за день. Источник: WakaTime API или `wakatime --today`.
2. **Бюджет закрыт** — сумма бюджетных оценок по всем РП, над которыми работали сегодня, взвешенная по прогрессу:
   - done → 100% бюджета РП
   - partial → % выполнения × бюджет РП
   - not started → 0
   - Источник: таблица «План на сегодня» из DayPlan (колонка «Бюджет»)
3. **Мультипликатор** = Бюджет закрыт / WakaTime. Формат: `N.Nx`
4. **Бюджет недели** = Бюджет_W{N} - WakaTime_total_week

#### 6. Черновик итогов (показать пользователю)

**а) Обзор:** таблица «что сделано» (РП × статус)

**б) Что нового узнал:** captures в Pack, различения, инсайты, новое из курса.

> Это экзоскелет: агент помогает увидеть, пользователь рефлексирует сам.

**в) Похвала:** что получилось, что было непросто но сделано.

**г) Не забыто?** Стратег проверяет:
- Незакоммиченные изменения (`git status` по всем репо)
<!-- YOUR CUSTOM CHECKS HERE -->
- Governance-синхронизация: новые репо или сервисы за день? → REPOSITORY-REGISTRY, navigation.md, MAP.002
- Незаписанные мысли? (спросить пользователя)
- Обещания кому-то? (спросить пользователя)

**д) Видео за день:**
- Если `video.enabled: true` → проверить новые видео
- Необработанные → перенести в задел на завтра

**е) Draft-list:** Pack обогащён → предложить черновик?

**ж) Задел на завтра** (Agent→Agent handoff: вечерний Стратег → утренний Стратег):
- С чего начать утром
- Какой контекст подготовить
- Незавершённые РП: что именно осталось

#### 7. Согласование

Пользователь читает черновик → корректирует → одобряет.

#### 8. Запись итогов

Дописать секцию «Итоги дня» в `DayPlan YYYY-MM-DD.md`:

```markdown
---

## Итоги дня

| РП | Что сделано | Статус |
|----|-------------|--------|
| #N | ... | done / partial |

**Коммиты:** N в M репо

### Мультипликатор IWE

| Метрика | Значение |
|---------|----------|
| **WakaTime (физическое время)** | Xч Yмин |
| **Бюджет закрыт (оценки РП)** | ~Nh |
| **Мультипликатор** | **N.Nx** |
| **Бюджет недели W{N}** | осталось Zh из Bh |

> Формула: Бюджет закрыт / WakaTime. Показывает усиление от агента-экзоскелета.

**Что нового узнал:** ...

**Похвала:** ...

**Не забыто:** всё чисто / [что осталось]

**Завтра начать с:** ...

*Закрыто: YYYY-MM-DD HH:MM*
```

#### 9. Закоммитить DS-strategy

#### 10. Верификация по чеклисту (Day Close)

Запустить sub-agent **Haiku** в роли **R23 Верификатор**. Передать: (1) чеклист Day Close, (2) черновик итогов, (3) список обновлённых файлов. По ❌ — исправить до показа пользователю.

**Почему sub-agent:** контекст основного агента загрязнён (VR.SOTA.002 context isolation).

### Чеклист Day Close

- [ ] Все изменения закоммичены и запушены (по всем репо)
- [ ] MEMORY.md: done-РП удалены, активные актуальны
- [ ] WP-REGISTRY.md обновлён
- [ ] WeekPlan обновлён (grep по номерам РП — ВСЕ упоминания)
- [ ] DayPlan обновлён (статусы ВСЕХ строк: РП + ad-hoc)
- [ ] open-sessions.log: строки закрытых сессий удалены
- [ ] Captures за день применены (все Quick Close → KE пройден)
- [ ] **Knowledge-mcp:** коммиты в Pack/DS → `selective-reindex.sh` выполнен
- [ ] **Linear sync:** статусы соответствуют git
- [ ] **Repo CLAUDE.md:** feat-коммиты → новые правила?
- [ ] **WP context:** done → `mv inbox/ → archive/wp-contexts/`
- [ ] **Draft-list:** Pack обогащён → черновик предложен?
- [ ] **Видео:** обработанные помечены (если video.enabled)
- [ ] **CHANGELOG FMT:** коммиты в FMT → CHANGELOG обновлён
- [ ] **Governance:** REPOSITORY-REGISTRY, navigation.md, MAP.002
- [ ] **Backup:** `day-close.sh` выполнен (backup + reindex + linear)
- [ ] **Верификация compliance:** /verify запускался сегодня?
- [ ] **WakaTime + Мультипликатор:** часы, бюджет, остаток недели
- [ ] Итоги дня записаны в DayPlan
- [ ] Новое репо → MAPSTRATEGIC.md + Strategy.md

Все ✅ → «День закрыт.» Иначе — указать, что осталось.

---

## § Масштаб: Неделя (Week Close)

> **Триггер:** автоматический (Пн 00:00) или «закрываю неделю» / «итоги недели».
> **Роль:** R1 Стратег
> **Протокол:** `week-review.md` + дополнительные шаги ниже.

### Дополнительные шаги Week Close (поверх Week Review)

#### 1. Ротация уроков в MEMORY.md

Для каждого урока в секции «Уроки»:
- Применялся за последние 2 недели? → оставить
- Нет → вынести в `memory/lessons-archive.md`
- Цель: ≤15 актуальных уроков в MEMORY.md

#### 2. Свежая таблица РП

- Удалить ВСЕ РП прошлой недели из MEMORY.md
- Перенести in_progress и pending в таблицу новой недели W{N+1}
- Источник: новый WeekPlan (создаётся в session-prep)

#### 3. Аудит memory-файлов

- ≤11 файлов? Лишние → объединить или удалить
- Лимиты: справочники ≤100, протоколы ≤150, MEMORY.md ≤100 строк
- Устаревшие записи → обновить или удалить

---

## Владельцы протоколов

> Владелец = роль (DP.D.033). Исполнитель всех ролей: A1 Claude Code (указывать модель).

| Протокол | Роль-владелец | Где описан |
|----------|---------------|-----------|
| Open, Work, Close (§ День) | R1 Стратег | protocol-*.md § День |
| Open, Work, Close (§ Сессия) | R6 Кодировщик | protocol-*.md § Сессия |
| Quick Close | R6 Кодировщик | protocol-close.md § Сессия |
| Day Close | R1 Стратег | protocol-close.md § День |
| Week Close | R1 Стратег | protocol-close.md § Неделя + week-review.md |
| Session-Close Extraction | R2 Экстрактор | extractor/prompts/session-close.md |
| On-Demand Extraction | R2 Экстрактор | extractor/prompts/on-demand.md |
| Bulk Extraction | R2 Экстрактор | extractor/prompts/bulk-extraction.md |
| Cross-Repo Sync | R2 Экстрактор | extractor/prompts/cross-repo-sync.md |
| Knowledge Audit | R2 Экстрактор | extractor/prompts/knowledge-audit.md |
| Inbox-Check | R2 Экстрактор | extractor/prompts/inbox-check.md |
| Ontology Sync | R2 Экстрактор | extractor/prompts/ontology-sync.md |
| Session-Prep | R1 Стратег | strategist/prompts/session-prep.md |
| Strategy-Session | R1 Стратег | strategist/prompts/strategy-session.md |
| Day-Plan | R1 Стратег | protocol-open.md § День |
| Note-Review | R1 Стратег | strategist/prompts/note-review.md |
| Week-Review | R1 Стратег | strategist/prompts/week-review.md |
