# Разведчик (R3) — Scout

> Автономный агент ночного сканирования базы знаний.

## Обещание

Обнаруживать пробелы в базе знаний (Pack-репозитории) и предлагать capture-кандидатов для ревью пользователем. Результат: структурированный отчёт с findings и action proposals.

## Сценарии использования

### 1. Ночной скан (потребитель: Day Open)
- **Кто:** Scheduler (22:00+), автоматически
- **Зачем:** К утреннему Day Open готов отчёт с находками
- **Результат:** `ScoutReport YYYY-MM-DD.md` в `DS-agent-workspace/scout/results/`
- **Что делает потребитель:** Day Open §5d показывает статус и находки

### 2. Ручной запуск (потребитель: пользователь)
- **Кто:** Пользователь, `scout.sh knowledge-gaps`
- **Зачем:** Проверить состояние Pack перед работой над знаниями
- **Результат:** Тот же отчёт, доступен немедленно

### 3. Digital Twin метрики (потребитель: dt-collect)
- **Кто:** Коллектор `collectors.d/scout.sh`, ежедневно
- **Зачем:** Трекинг здоровья базы знаний во времени
- **Результат:** JSON-метрики в `2_9_knowledge` (количество gaps, capture candidates, review rate)

## Сценарии (runner)

| Сценарий | Описание | Расписание |
|----------|----------|-----------|
| `knowledge-gaps` | Сканирование Pack на пробелы | Nightly 22:00+ |

## Формат отчёта

```markdown
# ScoutReport YYYY-MM-DD

## Summary
N findings, M capture candidates

## Coverage Gaps
...

## Structure Gaps
...

## Freshness Gaps
...
```

## Зависимости

- Claude CLI (`claude`)
- Pack-репозитории (`PACK-*`) в workspace
- `DS-agent-workspace/scout/` для результатов
- MCP: `iwe-knowledge` (knowledge_graph_stats, knowledge_search)
