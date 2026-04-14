---
name: protocol-close
description: Slim-ядро протокола Close — триггеры, маршрутизация, Quick Close inline
type: reference
valid_from: 2026-04-13
---

# Протокол Close (ОРЗ-фрактал)

> **Три масштаба:** Сессия (Quick Close), День (Day Close), Неделя (Week Close).
> **Точка входа:** Вызвать Skill `run-protocol` с нужным аргументом (см. таблицу ниже).
> **Принцип:** Quick Close = «не потерять» (inline, без TodoWrite, ~3 мин). Day/Week Close = через SKILL.md + TodoWrite (принудительное исполнение).

## Маршрутизация

| Триггер | Аргумент | Skill |
|---------|---------|-------|
| «закрываю сессию» / «всё» / «закрывай» | `close` или `close session` | Quick Close (ниже, inline) |
| «закрываю день» / «итоги дня» | `close day` | `.claude/skills/day-close/SKILL.md` |
| «закрываю неделю» / «итоги недели» | `week-close` | `.claude/skills/week-close/SKILL.md` |

> **`close` без уточнения** → Quick Close (сессия) по умолчанию.

---

## Quick Close (сессия, inline)

> **Роль:** R6 Кодировщик. **Бюджет:** ~3 мин. **Без TodoWrite** — намеренно, цель минимальный барьер.
> «Закрывай» = push сразу без вопросов (пользователь дал согласие словом).
> **Day Close ≠ Quick Close.** Day Close самодостаточен — Quick Close внутри него не повторять.

### Шаги (3 обязательных)

1. **Commit + Push** — все изменения зафиксированы
   **EXTENSION POINT:** Проверить `extensions/protocol-close.checks.md`. Если существует → `Read` и выполнить.

2. **WP Context File** — обновить секцию «Осталось» (structured формат):
   - in_progress → structured handoff
   - done → пометить `status: done`
   - Незавершённое → context file. Идея → `MAPSTRATEGIC.md`. Зерно → `drafts/draft-list.md`

3. **MEMORY.md** — обновить статус РП (одна строка: `in_progress` / `done`)

### Формат «Осталось»

```markdown
## Осталось

**Что пробовали:** [краткий итог сессии — 1-2 предложения]
**Что узнали:** [решения, инсайты, изменения контекста]
**Что дальше:**
- [ ] [конкретный следующий шаг]
- [ ] [следующий за ним]
**Следующий шаг:** [первый unchecked из списка выше]
**Контекст для следующей сессии:** [файлы, решения, блокеры]
```

### Отчёт Quick Close

```
**РП:** #N — [название]
**Статус:** done / in_progress
**Git:** закоммичено + запушено ✅
**EXTENSION POINT:** Проверить `extensions/protocol-close.after.md`. Если существует → `Read` и выполнить.
**Handoff:** → WP context «Осталось» обновлён / done
```

### Верификация Quick Close (Haiku R23)

> Условный шаг: если `params.yaml → verify_quick_close: false` → пропустить.
> Исключения: сессия ≤15 мин, сессия-вопрос без изменений файлов.

Запустить sub-agent Haiku в роли R23 (context isolation). Передать: чеклист, WP context «Осталось», `git diff --name-only`.

### Чеклист Quick Close

- [ ] Всё закоммичено и запушено
- [ ] WP Context: «Осталось» записано (или done помечен)
- [ ] MEMORY.md: статус РП обновлён
- [ ] Decision log: прочитать записи сессии в `decisions/decision-log-YYYY-MM.md`, скорректировать если неточно

---

## Deferred (отложены до Day Close)

> Quick Close намеренно не включает: DayPlan, WP-REGISTRY, KE, Verification Gate, отчёт.
> Причина (ADR-207): 3 атомарных шага выполняются всегда > 7 шагов, из которых 4 пропускаются.

---

## Exit Protocol (при завершении любой роли)

| # | Шаг | Что делать |
|---|-----|-----------|
| 1 | **Артефакт** | Зафиксировать результат (коммит, файл, запись) |
| 2 | **Статус** | Обновить трекер (MEMORY.md, WP context) |
| 3 | **Уведомление** | Сообщить следующему (пользователь, агент, Стратег) |
