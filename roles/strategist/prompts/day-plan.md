Выполни сценарий Day Open для роли Стратег (R1).

> **Триггер:** Автоматический — ежедневно (кроме strategy_day).

## Контекст

- **WeekPlan:** /mnt/c/Users/Timur/Documents/IWE/DS-strategy/current/WeekPlan W*.md
- **DayPlan (вчера):** /mnt/c/Users/Timur/Documents/IWE/DS-strategy/current/DayPlan *.md
- **Day rhythm config:** /home/trapt22/.claude/projects/-mnt-c-Users-Timur-Documents-IWE/memory/day-rhythm-config.yaml
- **Протокол:** /home/trapt22/.claude/projects/-mnt-c-Users-Timur-Documents-IWE/memory/protocol-open.md § День

## Алгоритм

Прочитай протокол Day Open из `memory/protocol-open.md § День` и выполни все шаги:

1. **Вчера** — собрать коммиты за вчера из всех репо, сопоставить с DayPlan
2. **План на сегодня** — выбрать 2-4 РП из WeekPlan, слот 1 = саморазвитие
3. **Саморазвитие** — текущее руководство, где остановился, черновики
4. **IWE за ночь** — проверить логи автоматики
5. **Мир** — новости по топикам из day-rhythm-config.yaml
6. **Запись** — создать DayPlan, архивировать предыдущий, закоммитить

## Результат

- `DS-strategy/current/DayPlan YYYY-MM-DD.md` создан
- Предыдущий DayPlan → `archive/day-plans/`
- Закоммичено и запушено в DS-strategy
