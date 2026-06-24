# Голосовой цикл IWE (WP-35 Ф1)

Hands-free voice-to-voice с Claude Code: говоришь команду → распознаётся → `claude -p`
исполняет → ответ озвучивается → цикл ждёт следующую команду. Сценарии: кухня, машина, сад.

## Запуск

```bash
bash DS-exocortex/extensions/voice-loop/voice-loop.sh
```

Скажи **«стоп» / «выход» / «хватит»** или нажми Ctrl-C для завершения.

## Как устроено

```
микрофон → ffmpeg (PulseServer) → VAD по энергии → faster-whisper (STT, локально)
  → claude -p (онлайн мозг, держит сессию через session_id) → piper (TTS, локально) → ffplay
```

- **STT и TTS локальные** → переиспользуются в офлайн-фазе (Ойтал); сейчас мозг онлайн (`claude -p`).
- `claude -p` запускается в `~/IWE`, поэтому видит CLAUDE.md и контекст РП.

## Настройки (env)

| Переменная | По умолчанию | Что |
|---|---|---|
| `VOICE_WHISPER_MODEL` | `small` | модель распознавания (`small`/`medium` — точнее, медленнее) |
| `VOICE_LANG` | `ru` | язык распознавания |
| `VOICE_PIPER_MODEL` | `voices/ru_RU-dmitri-medium.onnx` | голос озвучки |
| `VOICE_END_SILENCE_MS` | `900` | пауза, после которой фраза считается законченной |
| `VOICE_START_FACTOR` | `3.5` | чувствительность старта (выше = строже к шуму) |
| `VOICE_CLAUDE_PERM` | `acceptEdits` | режим прав `claude -p` |
| `VOICE_CPU_THREADS` | `8` | потоки CPU для распознавания |

## Зависимости

- `ffmpeg`, `ffplay` (есть в системе)
- `faster-whisper`, `piper-tts` (pip --user)
- голос piper: `python3 -m piper.download_voices ru_RU-dmitri-medium --download-dir voices`

## Известные ограничения (Ф1 MVP)

- Озвучивается **финальный** ответ; пошаговая «болтовня по ходу» (что делает в процессе) — отдельная фаза (нужен stream-json).
- Точность распознавания русского на `small` средняя — настраивается моделью.
- Прерывание ответа голосом («перебить») пока нет.
- Офлайн-мозг (локальная LLM вместо `claude -p`) — отдельная фаза WP-35.
