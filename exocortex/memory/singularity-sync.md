---
name: Singularity sync — РП → задачи
description: Как работает сверка рабочих продуктов с Singularity (§8b Day Open, §WP Gate Session Open), включая баги API
type: project
originSessionId: 6a6a74e9-9f6c-4569-a61a-d97c8fc239f5
---
Singularity MCP интеграция работает (с 2026-03-29). Две точки синхронизации:

1. **Day Open §8b** — полная сверка всех активных РП недели с проектами Singularity. Создаёт недостающие задачи-РП с priority=high.
2. **Session Open (WP Gate §3)** — точечная проверка: текущий РП отражён в Singularity?

Маппинг РП → проект: по ключевым словам из `protocol-open.md §8b`. Claude резолвит projectId через `list-projects` каждый раз (без хардкода ID).

**Why:** Тимур хочет видеть в Singularity не только мелкие действия, но и рабочие продукты (РП) недели — чтобы трекер отражал и стратегический, и тактический уровень.

**How to apply:** При Day Open — выполнять §8b после записи DayPlan. При Session Open — выполнять Singularity Gate (шаг 3 WP Gate). Не пропускать.

**Известные баги API (для WP-14 техдолг):**
- Rate limiting: 500 при быстрых последовательных create-task. Нужен retry с паузой в MCP-коде.
- Дочерние проекты: create-task в «Система трекинга» (дочерний ARB) нестабильно. Fallback — создавать в родительском проекте.
- `tags` параметр требует regex `/^A/u` (имя должно начинаться с заглавной A) — иначе 400 Bad Request. Workaround: передавать без tags. Подтверждено 2026-05-07 при создании WP-8 task.

**Пробелы маппинга §8b protocol-open:**
- «kense, Геонлайн → kense.app / geonline (дочерние ARB)» — **дочерних проектов в Singularity НЕ создано**. Fallback: создавать в ARB напрямую (проверено 2026-05-07). Нужно либо создать дочерние проекты в Singularity, либо обновить маппинг.
