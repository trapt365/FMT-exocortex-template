---
name: reference-tagping
description: "tagping.py — TagTime-style хронометраж, ntfy.sh, настройка автозапуска"
metadata: 
  node_type: memory
  type: reference
  horizon: warm
  domains: 
    - хронометраж
    - tools
    - iwe
  status: active
  valid_from: 2026-05-19
  owner: user
  schema_version: 1
  originSessionId: 5854b539-85a4-4e69-8ef3-a95350c000e8
---

# TagPing — хронометраж по алгоритму TagTime

## Скрипт

`~/tagping.py` — Poisson-пинги, среднее 30 мин.

Запуск: `nohup python3 ~/tagping.py 30 > /tmp/tagping.log 2>&1 &`
Стоп: `pkill -f tagping.py`

## Уведомления

- **Телефон/Watch:** ntfy.sh, топик `timur-ping-7x3k`. Кнопка "Daily Note" открывает `obsidian://open?vault=Vault1&file=Calendar%2FYYYY-MM-DD`
- **Десктоп:** Windows Toast (PowerShell AUMID `{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\WindowsPowerShell\v1.0\powershell.exe`)

## Автозапуск

`/etc/wsl.conf` → `[boot] command = su - trapt22 -c "nohup python3 /home/trapt22/tagping.py 30 > /tmp/tagping.log 2>&1 &"`

`~/.bashrc` — guard: запускает если не запущен (для терминала).

## Формат записи в Obsidian

Daily note `Calendar/YYYY-MM-DD.md` → секция `## Хронометраж`:

```
- 14:23 П — WP-7 story review
- 15:41 Л — ролики YouTube
```

**Длительность не пишем** — каждый пинг весит ~45 мин статистически (Poisson).
Справочник категорий: `Vault1/Extras/Хронометраж — категории.md`

## Баг WSL host-sleep (2026-06-01, исправлен)

**Симптом:** пинги молча прекращаются после вечера и не возобновляются утром, хотя процесс жив (`ps` → `hrtimer_nanosleep`). Чаще ночью: интервал после 21:00 (QUIET_START) переносится на QUIET_END=05:00 → один длинный `time.sleep(~8ч)`.
**Причина:** `time.sleep()` спит по `CLOCK_MONOTONIC`, который в WSL2 **замирает при засыпании Windows-хоста** → длинный сон не дотикивает после пробуждения.
**Фикс (в `tagping.py`):** сон не одним `time.sleep(delay)`, а циклом по настенным часам — `target = time.time()+delay; while time.time()<target: sleep(min(remaining,60))`. После resume хоста `time.time()` прыгает вперёд → пинг срабатывает в течение ~минуты.
**Если опять молчит:** убить по PID (`pkill -f tagping.py` зацепит и собственный шелл — НЕ использовать), перезапустить `setsid nohup python3 ~/tagping.py 30 > /tmp/tagping.log 2>&1 </dev/null &`. См. [[audio-pipeline]] — соседний класс WSL2/iCloud-багов.
