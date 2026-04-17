# Singularity API v2 — Справка

> Источник: https://api.singularity-app.com/v2/api
> Дата: 2026-04-17

## Базовый URL

`https://api.singularity-app.com/v2`

## Аутентификация

`Authorization: Bearer <token>` — токен из me.singularity-app.com → «Доступ AI и API».

---

## Эндпоинты

### Задачи (Task)

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/task` | Список задач (фильтры: projectId, startDateFrom, startDateTo, maxCount, offset) |
| POST | `/task` | Создать задачу |
| GET | `/task/{id}` | Получить задачу по ID |
| PATCH | `/task/{id}` | Обновить задачу |
| DELETE | `/task/{id}` | Удалить задачу |

**Поля задачи:** title, note, priority (0=high, 1=normal, 2=low), start (ISO 8601), deadline (ISO 8601), checked (0=empty, 1=completed, 2=cancelled), projectId, parent, useTime, timeLength, tags[], deferred, scheduleOrder.

### Проекты (Project)

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/project` | Список проектов (includeArchived, includeRemoved, maxCount, offset) |
| POST | `/project` | Создать проект |
| GET | `/project/{id}` | Получить проект по ID |
| PATCH | `/project/{id}` | Обновить проект |
| DELETE | `/project/{id}` | Удалить проект |

### Привычки (Habit)

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/habit` | Список привычек (maxCount, offset) |
| POST | `/habit` | Создать привычку |
| GET | `/habit/{id}` | Получить привычку по ID |
| PATCH | `/habit/{id}` | Обновить привычку |
| DELETE | `/habit/{id}` | Удалить привычку |

**HabitCreateDto:**

```json
{
  "title": "string (required)",
  "description": "string",
  "color": "enum: red|pink|purple|deepPurple|indigo|lightBlue|cyan|teal|green|lightGreen|lime|yellow|amber|orange|deepOrange|brown|grey|blueGrey",
  "order": "number",
  "status": "number (0=active, 1=?, 2=archived, 3=?)",
  "externalId": "string"
}
```

### Прогресс привычек (Habit Progress)

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/habit-progress` | Список записей (habit, startDate, endDate, maxCount, offset) |
| POST | `/habit-progress` | Создать запись прогресса |
| GET | `/habit-progress/{id}` | Получить запись по ID |
| PATCH | `/habit-progress/{id}` | Обновить запись |
| DELETE | `/habit-progress/{id}` | Удалить запись |

**HabitDailyProgressCreateDto:**

```json
{
  "habit": "string (required) — ID привычки",
  "date": "string (required) — YYYY-MM-DD",
  "progress": "number (required) — 0=not done, 1=done, 2=skipped",
  "externalId": "string"
}
```

### Прочие эндпоинты

| Путь | Описание |
|------|----------|
| `/checklist-item` | Чеклист-элементы задач |
| `/tag` | Теги |
| `/task-group` | Группы задач |
| `/kanban-status` | Kanban-статусы |
| `/kanban-task-status` | Kanban-статусы задач |
| `/time-stat` | Статистика времени |

---

## MCP-сервер (singularity-mcp v0.3.0)

Реализованные tools:

| Tool | Описание |
|------|----------|
| list-tasks-today | Задачи на сегодня |
| list-tasks | Задачи с фильтрами |
| get-task | Задача по ID |
| create-task | Создать задачу |
| update-task | Обновить задачу |
| complete-task | Завершить/отменить задачу |
| delete-task | Удалить задачу |
| list-projects | Список проектов |
| **list-habits** | Список привычек |
| **create-habit** | Создать привычку |
| **update-habit** | Обновить привычку |
| **log-habit-progress** | Записать прогресс (done/skip/reset) |
| **get-habit-progress** | Прогресс за период |
