---
name: Playwright MCP для браузера
description: Настроен Playwright MCP через CDP к Chrome Windows для доступа к залогиненным страницам (Aisystant, Google Sheets и др.)
type: reference
valid_from: 2026-04-13
---

Playwright MCP добавлен в `.mcp.json` (IWE проект) — подключается к Chrome через CDP `localhost:9222`.
Запускается через `cmd.exe` (на стороне Windows), чтобы обойти WSL2 NAT.

**Запуск:** `C:\Users\Timur\Desktop\Chrome-Debug.bat` — убивает все Chrome, ждёт, запускает с `--remote-debugging-port=9222 --user-data-dir=%LOCALAPPDATA%\Google\Chrome\User Data`.

**ВАЖНО:**
- Chrome должен быть запущен через bat-файл ДО старта Claude Code, иначе MCP не подключится.
- Без `--user-data-dir` явно — порт 9222 НЕ открывается (баг Chrome с дефолтным профилем).
- Если Chrome перезапускался во время сессии — нужно перезапустить Claude Code.

**Возможности:** навигация по страницам, чтение DOM, клики, скриншоты — всё через залогиненную сессию пользователя.

**Aisystant:** платформа курсов на `https://aisystant.system-school.ru/lk/` (не app.aisystant.com).
