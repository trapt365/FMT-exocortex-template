---
name: wakatime-claude-code-wakatime-s-50
description: "С 24 мая WakaTime CLI v2.14+ тянет Claude Code сессии через плагин claude-code-wakatime/0.1.0. Покрытие выросло, но остаётся «Unknown Editor» (Windows-окна) и Telegram учитывается в work-time."
metadata: 
  node_type: memory
  type: feedback
  horizon: warm
  status: active
  valid_from: 2026-05-28
  schema_version: 1
  supersedes: WakaTime не трекает Claude Code сессии (WP-14 техдолг)
  originSessionId: fa2a010a-56f3-4cea-9793-8ba7bb3dc89d
---

**Правило:** для расчёта мультипликатора IWE можно опираться на WakaTime, но с тремя поправками — (1) вычитать Telegram, (2) понимать что «Unknown Editor» = Windows-tracker (накладывается с Claude Code), (3) проверять провалы (в выходные WakaTime даёт 0 минут).

**Why:** Состояние на 2026-05-28 (проверка через API `/users/current/stats/last_7_days`):
- Claude Code: 15ч 14мин/нед (32%) — плагин `claude-code-wakatime/0.1.0` живёт в `~/.wakatime/wakatime-cli` v2.14.7, активен с 24 мая.
- Chrome: 9ч 18мин/нед (19%) — браузерный плагин трекает Aisystant + research.
- Obsidian: 3ч 4мин (6%), VS Code: 1ч 5мин (2%) — отдельные плагины.
- Unknown Editor: 11ч 53мин (25%) — Windows-окна без user_agent. Entity = «Проводник» (216), «Переключение задач» (206), куски Claude Code (144). Похоже работает desktop-wrapper / accessibility-API трекер.
- TelegramDesktop: 2ч 29мин (5%) — засчитывается в work-time, надо вычитать.
- ZoomMeetings: 3ч 51мин (8%) — встречи трекаются отдельной категорией Meeting.

В апреле было 31 мин в редакторе на 1ч 23мин сессии (4× занижение). Сейчас при сессии Claude Code 4ч 17мин (19 мая) реальные ~5-6ч сессии = коэффициент 1.2-1.4×, не 4×.

**How to apply:**
- Daily breakdown: `curl -s -H "Authorization: Basic $(printf '%s' $(grep ^api_key ~/.wakatime.cfg | awk -F' = ' '{print $2}') | base64 -w0)" "https://api.wakatime.com/api/v1/users/current/summaries?start=YYYY-MM-DD&end=YYYY-MM-DD"`.
- При Day Close: total minus TelegramDesktop = «чистое» work-time.
- «Unknown Editor» **накладывается** с Claude Code/Obsidian/Chrome — это вторая система трекинга на Windows-стороне, не считать в сумму отдельно (если total = 8ч, а sum(editors) = 12ч+, расхождение нормально, total — это unique active minutes).
- Free-план API: stats доступны только за 7 дней. Для 14d брать `/summaries?start=...&end=...`. 30d требует pro.
- Проверка живости плагина Claude Code: `grep "claude-code-wakatime" ~/.wakatime/wakatime.log | tail -3`. Если последний heartbeat >3 часа назад в активной сессии — плагин завис.
- WP-14 пункт «доделать трекинг Claude Code» закрыт автоматически (Anthropic выпустил плагин). Открытый пункт: WakaTime для bash/zsh-сессий вне Claude Code (если когда-то понадобится).

**Аномалии:**
- В логах warnings `parseTranscript: invalid character '\x00'` — Claude Code transcript содержит null-байты, плагин не парсит. Хартбиты при этом всё равно отправляются, метрики корректные.
- Дни без активности (16-17 мая) = выходные/отдых от компьютера, не сбой.

**Архитектура трекинга (на 2026-05-28):**
- **wakatime-cli WSL** v2.14.7 (`~/.wakatime/wakatime-cli`) — Claude Code сессии в Linux-окружении, проект = IWE через маркер `/home/trapt22/IWE/.wakatime-project`.
- **wakatime-cli Windows** (`C:\Users\Timur\.wakatime\wakatime-cli.exe`) — для Obsidian-plugin, VS Code-extension, Chrome-extension.
- **desktop-wakatime** (Electron, `C:\Users\Timur\AppData\Local\Programs\desktop-wakatime\WakaTime.exe`) — Windows-tracker по заголовкам окон. Конфиг `~AppData\Roaming\WakaTime\desktop-wakatime.cfg`, секция `[monitoring]` — флаг `is_<path>_monitored = True/False` per-app.
- **Сейчас включено в desktop-wakatime** (9 apps): Telegram, Zoom, Postman, Singularity, WhatsApp, Claude desktop, Handy, Anki (pythonw), Chrome/Brave/Edge (для browser-monitoring через extension fallback). **Отключено 28 мая:** explorer.exe (давал 71% Unknown Project — Проводник + Alt+Tab).

**Управление desktop-wakatime apps:**
- Включить/отключить app: `sed -i 's|<path>_monitored *= True|...= False|'` в `/mnt/c/Users/Timur/AppData/Roaming/WakaTime/desktop-wakatime.cfg` (CRLF, использовать `python3 -c "re.sub on raw bytes"` если sed не цепляет).
- После правки cfg обязательно: `powershell.exe -Command "Get-Process WakaTime | Stop-Process -Force; Start-Process 'C:\...\WakaTime.exe'"` — иначе конфиг не перечитывается.
- Все heartbeats от desktop-wakatime получают `category=Coding, language=None, type=app` — нельзя переклассифицировать их как Communicating/Browsing.

**Что разобрано про Unknown Project:**
- До 28 мая ~40% всех heartbeats = Unknown Project, из них 71% = explorer.exe (Проводник + переключатель задач).
- Остальные источники: Telegram-чаты (заголовки окон вида `IWE: команда развития @ T R (12982)`), Zoom-конференции, Handy, реже WhatsApp/Singularity/Postman.
- После отключения explorer.exe ожидается Unknown Project ~5%.
