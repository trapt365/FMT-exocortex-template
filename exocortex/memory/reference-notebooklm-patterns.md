---
name: NotebookLM — паттерны работы
description: Как быстро вставлять текст и генерировать аудиоподкаст в NotebookLM через Playwright MCP
type: reference
valid_from: 2026-04-21
originSessionId: 85850573-4339-455b-8308-aaa4baf8e576
---
## Вставка текстового источника (Copied text)

**Паттерн:** "Add sources" → диалог с источниками → "Copied text" → textarea → `browser_type` → Insert

### Детали

1. Для **пустого** ноутбука кнопка "Add sources" открывает **промо-диалог** "Create Audio and Video Overviews..." — это НЕ ошибка, это онбординг.
2. Внутри промо-диалога есть кнопки: Upload files / Websites / Drive / **Copied text** — найти через `dialog.querySelectorAll('button')`.
3. После клика "Copied text" появляется `<textarea placeholder="Paste text here">` — активная.
4. **КРИТИЧНО: использовать `browser_type`, а не `browser_fill_form` или нативный setter** — Angular не детектирует программный `setValue`, кнопка Insert остаётся disabled. `browser_type` → fill() → Angular детектирует → Insert активируется.
5. Нажать Insert: `button.find(b => b.textContent?.includes('Insert')).click()`.

```js
// Шаг 1: открыть диалог
btn_addSources.click(); // открывает промо-диалог

// Шаг 2: найти Copied text внутри диалога
dialog.querySelector('button с "Copied text"').click();

// Шаг 3: вставить текст через browser_type (не evaluate!)
// browser_type ref=<textarea_ref> text="..." — Angular детектирует ввод

// Шаг 4: Insert
button("Insert").click(); // теперь enabled
```

## Переименование ноутбука

- Заголовок — `<input class="title-input ...">` в шапке
- Найти через `document.querySelector('input.title-input')` или `textbox` ref
- `browser_type ref=e122 text="Новое название" submit=true` (Enter подтверждает)
- Если textbox пустой после fill — сначала click(), потом type

## Удаление источника

1. Кнопка "More" рядом с источником → menuitem "Remove source" → диалог "Delete?" → кнопка "Delete"

## Генерация Audio Overview

- В правой панели Studio: кнопка "Audio Overview" (с chevron_forward) — открывает панель
- Генерация занимает 1-3 минуты, статус: "Generating Audio Overview… Come back in a few minutes"
- После готовности: уведомление снизу + кнопка play_arrow в Studio
- **Если источник изменился** — нужно перегенерировать: в Studio → Audio Overview → кнопка Generate/Refresh
- Имя подкаста автогенерируется NotebookLM на английском из контента

## URL ноутбука

`https://notebooklm.google.com/notebook/{uuid}` — сохранять сразу после создания, показывать пользователю.

## Частые ошибки

| Ошибка | Причина | Фикс |
|--------|---------|------|
| Insert disabled | browser_evaluate setter не триггерит Angular | Использовать browser_type |
| Промо-диалог вместо Add source | Ноутбук пустой — нормально | Найти Copied text ВНУТРИ этого диалога |
| Неправильное название ноутбука | NotebookLM автогенерирует из контента | Переименовать через title-input в шапке |
