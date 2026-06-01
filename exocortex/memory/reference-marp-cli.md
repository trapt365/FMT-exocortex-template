---
name: Marp CLI рендер без локальной установки
description: Команда для рендеринга Marp .md → .html в WSL без pre-install (работает через npx)
type: reference
originSessionId: 43b2d4f8-10a4-453a-b546-9dc50a58844f
---
# Marp CLI: рендер в WSL

Для рендера Marp-презентаций (presentation-v*.md → .html) в WSL **не нужна локальная установка**:

```bash
cd <каталог-с-md>
npx -y @marp-team/marp-cli@latest <file>.md --html --allow-local-files -o <file>.html
```

- `--html` разрешает HTML-теги в MD (нужно для `<div class="highlight">` и подобного)
- `--allow-local-files` для локальных изображений
- Результат self-contained HTML (стили и шрифты inline) — работает без интернета в браузере

**Стиль-референс:** `propresearch/_bmad-output/deliverables/client/presentation-v6.4.md` — проработанный CSS 16:9, цветовая схема (тёмно-синий #0d47a1, акцент #4fc3f7, блоки highlight/danger/success).

**Размер:** ~80 слайдов из стратегического отчёта (1200 строк) = ~80KB MD + ~550KB HTML.

**Открытие в браузере WSL:**

```bash
explorer.exe "$(wslpath -w <abs-path>.html)"
```
