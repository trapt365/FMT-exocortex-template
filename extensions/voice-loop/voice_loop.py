#!/usr/bin/env python3
"""Голосовой цикл IWE (WP-35 Ф1) — hands-free voice-to-voice с Claude Code.

Поток: микрофон → VAD → распознавание (faster-whisper) → claude -p (онлайн мозг,
держит сессию) → озвучка (piper) → ожидание следующей команды.

Аудио в WSL идёт через WSLg PulseServer: запись `ffmpeg -f pulse -i default`,
воспроизведение `ffplay`. Главный риск (микрофон в WSL) проверен — работает.

Стек локальный (STT/TTS) → переиспользуется в офлайн-фазе (Ойтал). Сейчас мозг
онлайн (claude -p); офлайн-мозг (локальная LLM) — отдельная фаза WP-35.

Запуск: bash voice-loop.sh   (или python3 voice_loop.py)
Стоп:   скажи «стоп» / «выход» / Ctrl-C.
"""
import os
import sys
import json
import wave
import struct
import shutil
import tempfile
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent

# ── Конфиг (правится здесь или через env VOICE_*) ──────────────────────────
SAMPLE_RATE   = 16000          # Гц, требование whisper
FRAME_MS      = 30             # длина кадра VAD
FRAME_BYTES   = int(SAMPLE_RATE * FRAME_MS / 1000) * 2  # 16-bit моно
START_FACTOR  = float(os.environ.get("VOICE_START_FACTOR", "3.5"))  # порог старта = шум * фактор
MIN_ABS_START = float(os.environ.get("VOICE_MIN_START", "200"))     # абс. минимум порога (фильтр шороха)
END_SILENCE_MS= int(os.environ.get("VOICE_END_SILENCE_MS", "900"))  # тишина для конца фразы
MIN_SPEECH_MS = 300            # короче — считаем шумом
MAX_UTTER_MS  = int(os.environ.get("VOICE_MAX_UTTER_MS", "30000"))  # потолок длины фразы
PREROLL_MS    = 300            # буфер перед стартом речи, чтобы не срезать начало

WHISPER_MODEL = os.environ.get("VOICE_WHISPER_MODEL", "small")
WHISPER_LANG  = os.environ.get("VOICE_LANG", "ru")
PIPER_MODEL   = os.environ.get("VOICE_PIPER_MODEL", str(HERE / "voices" / "ru_RU-dmitri-medium.onnx"))

# bypassPermissions: hands-free → подтверждать запросы прав руками нельзя; своя машина.
CLAUDE_PERMISSION = os.environ.get("VOICE_CLAUDE_PERM", "bypassPermissions")
CLAUDE_CWD    = os.environ.get("VOICE_CLAUDE_CWD", str(Path.home() / "IWE"))
# Доп. папки за пределами рабочей (SDK иначе не пускает инструменты вне cwd).
# Vault1 (Obsidian) — нужен для запасов, заметок и т.п. Список через ':'.
_extra = os.environ.get("VOICE_EXTRA_DIRS", "/mnt/c/Users/Timur/Documents/Vault1")
CLAUDE_EXTRA_DIRS = [d for d in _extra.split(":") if d and Path(d).exists()]
CLAUDE_MODEL  = os.environ.get("VOICE_CLAUDE_MODEL", "haiku")  # голос: самый быстрый
VOICE_SYSTEM  = os.environ.get("VOICE_SYSTEM_PROMPT",
    "Ты отвечаешь пользователю ГОЛОСОМ — ответ озвучивается вслух. Говори живой речью, "
    "короткими предложениями (так озвучка успевает начаться раньше). По умолчанию — "
    "1-2 фразы и только суть. Если просят перечислить (план, приоритеты, список) — "
    "перечисляй устно, обычными предложениями: 'первое… второе…', КОРОТКО по каждому "
    "пункту, без воды. "
    "НЕ зачитывай вслух свои шаги ('запускаю', 'проверяю', 'давайте посмотрим') — твои "
    "действия и так озвучиваются системой автоматически. Просто делай и в КОНЦЕ скажи "
    "итог одной короткой фразой. Действуй решительно: не исследуй лишнего, выполни "
    "команду кратчайшим путём. "
    "ВАЖНО: это быстрый голосовой помощник, НЕ формальная рабочая сессия IWE. НЕ запускай "
    "ритуал согласования рабочего продукта, НЕ объявляй роли, класс верификации, оценку "
    "времени и модель, НЕ проси подтверждения 'делаем?'. Если команда понятна — сразу "
    "выполняй. Уточняй только при реальной двусмысленности, одним коротким вопросом. "
    "БЕЗОПАСНОСТЬ: распознавание речи неточное. НЕ изменяй, не перезаписывай и не удаляй "
    "файлы, если команда ЯВНО не просит этого словами 'запиши', 'добавь', 'измени', "
    "'удали', 'сохрани'. По умолчанию — только читай и отвечай голосом. "
    "НИКАКОГО markdown: ни звёздочек, ни решёток, ни кода, ни ссылок, ни путей к файлам, "
    "ни технических кодов — произноси по-человечески, как в разговоре. Числа и время "
    "проговаривай словами естественно.")
PERF          = os.environ.get("VOICE_PERF", "1") == "1"  # печатать тайминги этапов

STOP_WORDS    = {"стоп", "выход", "хватит", "stop", "quit", "exit", "пока"}
# Короткое подтверждение сразу после распознавания — убирает немую паузу, пока
# мозг думает (TTFT на полном контексте IWE ~9-12с). Чередуем, чтобы не роботело.
FILLERS       = ["Секунду.", "Смотрю.", "Сейчас.", "Минуту."]

# Wake-слово (как «эй, Siri»): помощник реагирует только на фразу, начинающуюся с
# имени, остальную речь игнорирует. Варианты — под неточность распознавания «Клод».
# VOICE_WAKE="off" → всегда слушать (старое поведение, без wake-слова).
_wake_raw  = os.environ.get("VOICE_WAKE", "компьютер,компьютор,компьютр,компьюте")
WAKE_WORDS = [w.strip().lower() for w in _wake_raw.split(",")
              if w.strip() and w.strip().lower() not in ("off", "none", "-", "")]

# ── Утилиты ────────────────────────────────────────────────────────────────
def log(msg):
    print(f"\033[36m[voice]\033[0m {msg}", flush=True)

def rms(frame_bytes):
    n = len(frame_bytes) // 2
    if n == 0:
        return 0.0
    samples = struct.unpack(f"<{n}h", frame_bytes[: n * 2])
    return (sum(s * s for s in samples) / n) ** 0.5

# ── Запись фразы по VAD ──────────────────────────────────────────────────────
def record_utterance():
    """Открывает поток с микрофона, ждёт речь, пишет до тишины. Возвращает PCM-байты."""
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "quiet",
           "-f", "pulse", "-i", "default",
           "-ar", str(SAMPLE_RATE), "-ac", "1", "-f", "s16le", "-"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    try:
        # калибровка шума (первые ~0.5с)
        noise_frames = []
        for _ in range(int(500 / FRAME_MS)):
            f = proc.stdout.read(FRAME_BYTES)
            if len(f) < FRAME_BYTES:
                break
            noise_frames.append(rms(f))
        noise_floor = max(1.0, sorted(noise_frames)[len(noise_frames) // 2] if noise_frames else 1.0)
        start_thr = max(noise_floor * START_FACTOR, MIN_ABS_START)
        log(f"шум≈{noise_floor:.0f}, порог старта≈{start_thr:.0f} — говори")

        preroll = []
        preroll_max = max(1, int(PREROLL_MS / FRAME_MS))
        speaking = False
        voiced = []
        silence_ms = 0
        speech_ms = 0
        total_ms = 0
        while True:
            f = proc.stdout.read(FRAME_BYTES)
            if len(f) < FRAME_BYTES:
                break
            level = rms(f)
            if not speaking:
                preroll.append(f)
                if len(preroll) > preroll_max:
                    preroll.pop(0)
                if level > start_thr:
                    speaking = True
                    voiced = list(preroll)
                    voiced.append(f)
                    speech_ms = FRAME_MS
            else:
                voiced.append(f)
                total_ms += FRAME_MS
                if level > start_thr:
                    silence_ms = 0
                    speech_ms += FRAME_MS
                else:
                    silence_ms += FRAME_MS
                if silence_ms >= END_SILENCE_MS and speech_ms >= MIN_SPEECH_MS:
                    break
                if total_ms >= MAX_UTTER_MS:
                    log("достигнут потолок длины фразы")
                    break
        return b"".join(voiced)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except Exception:
            proc.kill()

def pcm_to_wav(pcm, path):
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(pcm)

# ── STT ──────────────────────────────────────────────────────────────────────
_whisper = None
def transcribe(pcm):
    global _whisper
    if _whisper is None:
        from faster_whisper import WhisperModel
        log(f"загружаю модель распознавания «{WHISPER_MODEL}» (первый раз — качается)…")
        threads = int(os.environ.get("VOICE_CPU_THREADS", "8"))
        _whisper = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8",
                                cpu_threads=threads)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
        wav_path = tf.name
    pcm_to_wav(pcm, wav_path)
    try:
        segments, _ = _whisper.transcribe(
            wav_path, language=WHISPER_LANG, vad_filter=True,
            beam_size=1, condition_on_previous_text=False)
        return " ".join(s.text.strip() for s in segments).strip()
    finally:
        os.unlink(wav_path)

# ── Brain (живая SDK-сессия: контекст грузится один раз, круги короткие) ──────
# Холодный `claude -p` стартует ~9-20с КАЖДЫЙ раз (грузит контекст IWE заново).
# Постоянная сессия через ClaudeSDKClient: прогрев один раз, далее ~3-6с/круг.
async def ask_claude(client, text):
    """Непотоковый сбор всего ответа (для прогрева)."""
    from claude_agent_sdk import AssistantMessage
    await client.query(text)
    parts = []
    async for msg in client.receive_response():
        if isinstance(msg, AssistantMessage):
            for b in msg.content:
                t = getattr(b, "text", None)
                if t:
                    parts.append(t)
    return " ".join(parts).strip() or "(пустой ответ)"

# Короткие человеческие фразы для озвучки действий агента по ходу работы.
TOOL_PHRASES = {
    "Read": "читаю файл", "Glob": "ищу файлы", "Grep": "ищу по тексту",
    "Bash": "выполняю команду", "Write": "пишу файл", "Edit": "правлю файл",
    "MultiEdit": "правлю файл", "NotebookEdit": "правлю блокнот",
    "WebFetch": "смотрю страницу", "WebSearch": "ищу в интернете",
    "Task": "запускаю помощника",
}
TOOL_SKIP = {"TodoWrite"}  # внутреннее — не озвучиваем

def tool_detail(name, inp):
    """Короткая деталь для печати в окно (не для озвучки — там чисто глагол)."""
    inp = inp or {}
    if name in ("Read", "Write", "Edit", "MultiEdit"):
        p = inp.get("file_path", "")
        return os.path.basename(p) if p else ""
    if name == "Bash":
        c = (inp.get("command", "") or "").strip().split()
        return c[0] if c else ""
    if name in ("Grep", "Glob"):
        return inp.get("pattern", "") or inp.get("query", "")
    if name in ("WebFetch", "WebSearch"):
        return inp.get("query", "") or inp.get("url", "")
    return ""

async def stream_events(client, text):
    """Отдаёт поток событий хода: ('text', дельта) по мере генерации и
    ('tool', (имя, вход)) когда агент запускает инструмент. Текст идёт по токенам
    (ранняя озвучка), действия — для проговаривания процесса."""
    from claude_agent_sdk import StreamEvent, AssistantMessage, ToolUseBlock, TextBlock
    await client.query(text)
    got_delta = False
    async for msg in client.receive_response():
        if isinstance(msg, StreamEvent):
            ev = msg.event
            if ev.get("type") == "content_block_delta":
                d = ev.get("delta", {})
                if d.get("type") == "text_delta":
                    piece = d.get("text", "")
                    if piece:
                        got_delta = True
                        yield ("text", piece)
        elif isinstance(msg, AssistantMessage):
            for b in msg.content:
                if isinstance(b, ToolUseBlock):
                    yield ("tool", (b.name, b.input))
                elif isinstance(b, TextBlock) and not got_delta and b.text:
                    # запасной путь: дельты не пришли — отдаём текст целиком
                    yield ("text", b.text)

# ── Чистка текста под озвучку (снимаем markdown/спецзнаки) ───────────────────
import re
def clean_for_speech(text):
    t = text
    t = re.sub(r"```.*?```", " ", t, flags=re.S)        # блоки кода
    t = re.sub(r"`([^`]*)`", r"\1", t)                   # инлайн-код
    t = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", t)        # ссылки [текст](url)
    t = re.sub(r"https?://\S+", " ", t)                   # голые url
    t = re.sub(r"[*_#>~|]", "", t)                        # markdown-символы
    t = re.sub(r"^\s*[-•]\s+", "", t, flags=re.M)         # маркеры списков
    t = re.sub(r"^\s*\d+\.\s+", "", t, flags=re.M)        # нумерация списков
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{2,}", ". ", t)
    return t.strip()

# ── TTS (piper → один непрерывный поток в pulse) ─────────────────────────────
# Раньше каждая фраза игралась отдельным ffmpeg; старт следующего обрывал хвост
# предыдущего из аудиобуфера WSL (отсюда «обрезает фразы»). Теперь держим ОДИН
# процесс ffmpeg, читающий сырой PCM из pipe → один pulse-поток на сессию, который
# не закрывается между фразами → нечему обрывать. Запись в pipe блокируется в темпе
# воспроизведения (естественный backpressure) — фразы играются по очереди слитно.
_piper = None
_player = None          # subprocess ffmpeg: s16le pipe → pulse (открыт на ход)
_player_rate = None

def _ensure_player(rate):
    global _player, _player_rate
    if _player is not None and _player.poll() is None and _player_rate == rate:
        return _player
    if _player is not None:
        try:
            _player.stdin.close()
            _player.terminate()
        except Exception:
            pass
    _player = subprocess.Popen(
        ["ffmpeg", "-hide_banner", "-loglevel", "error",
         "-f", "s16le", "-ar", str(rate), "-ac", "1", "-i", "pipe:0",
         "-f", "pulse", "voice-loop"],
        stdin=subprocess.PIPE)
    _player_rate = rate
    return _player

def _close_player():
    """Закрыть поток и ДОЖДАТЬСЯ слива (ffmpeg доигрывает остаток в pulse и выходит).
    Вызывать перед записью: гарантирует, что короткий ответ ('Москва') точно прозвучал,
    и освобождает RDP-аудиоканал для микрофона."""
    global _player
    if _player is not None:
        try:
            _player.stdin.close()
            _player.wait(timeout=30)   # дать доиграть весь буфер
        except Exception:
            try:
                _player.kill()
            except Exception:
                pass
        _player = None

def speak(text):
    global _piper
    if not text:
        return
    text = clean_for_speech(text)
    if not text:
        return
    if _piper is None:
        from piper import PiperVoice
        if not Path(PIPER_MODEL).exists():
            log(f"⚠ нет голосовой модели: {PIPER_MODEL} — печатаю ответ вместо озвучки")
            print(f"\033[33m[claude]\033[0m {text}", flush=True)
            return
        _piper = PiperVoice.load(PIPER_MODEL)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
        out = tf.name
    try:
        with wave.open(out, "wb") as wf:
            _piper.synthesize_wav(text, wf)
        with wave.open(out, "rb") as wf:
            rate = wf.getframerate()
            pcm = wf.readframes(wf.getnframes())
        # короткая пауза между фразами, чтобы слова не сливались
        pause = b"\x00\x00" * int(rate * 0.18)
        player = _ensure_player(rate)
        try:
            player.stdin.write(pcm + pause)
            player.stdin.flush()
        except (BrokenPipeError, ValueError):
            # поток умер — пересоздаём и пробуем один раз
            player = _ensure_player(rate)
            player.stdin.write(pcm + pause)
            player.stdin.flush()
    finally:
        os.unlink(out)

# ── Потоковая озвучка: режем поток на фразы, играем из очереди ───────────────
import asyncio, time

# Граница фразы: знак конца, за которым пробел/кавычка/скобка ИЛИ сразу заглавная
# (модель часто стримит без пробела: «аудиорефлексий.Проверяю»). Lookahead не съедает
# следующий символ. «0.5» и «07:30» не режутся (после точки цифра, не пробел/заглавная).
SENT_END = re.compile(r"[.!?…]+(?=[\s\"')\]]|[А-ЯЁA-Z])|[\n\r]+")
MIN_SENT_CHARS = 10  # короче — копим дальше, чтобы не дробить на огрызки

def split_sentences(buf):
    """Возвращает (готовые_фразы, остаток_буфера). Короткие огрызки (< MIN_SENT_CHARS)
    приклеиваются к следующему сегменту, а не режутся (иначе «Да.» уходит отдельно)."""
    out = []
    last = 0
    for m in SENT_END.finditer(buf):
        seg = buf[last:m.end()].strip()
        if len(seg) >= MIN_SENT_CHARS:
            out.append(seg)
            last = m.end()
    return out, buf[last:]

WAKE_PREFIX = {"эй", "окей", "окэй", "привет", "слушай", "ok", "hey"}

def extract_command(heard):
    """Wake-режим: вернуть команду после имени, '' если сказали только имя,
    None если обращения по имени не было (игнорировать). Без wake-слов — вернуть как есть.
    Имя должно стоять ПЕРВЫМ словом (или после 'эй/окей/привет'), иначе 'я купил
    компьютер' ложно сработало бы."""
    if not WAKE_WORDS:
        return heard
    norm = re.sub(r"[^\w\s]", " ", heard.lower())
    toks = norm.split()
    if not toks:
        return None
    i = 1 if (toks[0] in WAKE_PREFIX and len(toks) > 1) else 0
    if i < len(toks) and any(toks[i] == w or toks[i].startswith(w) for w in WAKE_WORDS):
        return " ".join(heard.split()[i + 1:]).strip(" ,.!?—-:")
    return None

async def speak_worker(queue):
    """Берёт фразы из очереди и проговаривает по одной (синтез+воспроизведение)."""
    while True:
        sent = await queue.get()
        if sent is None:
            queue.task_done()
            break
        await asyncio.to_thread(speak, sent)
        queue.task_done()

async def stream_and_speak(client, heard):
    """Стримит ход агента: проговаривает действия по ходу (читаю файл, выполняю
    команду) и финальный ответ по фразам на лету. Возвращает
    (полный_текст, время_до_первого_звука, общее_время)."""
    queue = asyncio.Queue()
    worker = asyncio.create_task(speak_worker(queue))
    t0 = time.time()
    t_first = None
    buf = ""
    full = []
    last_tool = None
    async for kind, payload in stream_events(client, heard):
        if kind == "text":
            full.append(payload)
            buf += payload
            sents, buf = split_sentences(buf)
            for s in sents:
                if t_first is None:
                    t_first = time.time() - t0
                await queue.put(s)
        elif kind == "tool":
            name, inp = payload
            if name in TOOL_SKIP:
                continue
            if buf.strip():            # доскажем недоговорённый текст перед действием
                await queue.put(buf.strip())
                buf = ""
            detail = tool_detail(name, inp)
            phrase = TOOL_PHRASES.get(name, "работаю")
            print(f"\033[35m[…]\033[0m {phrase}" + (f" ({detail})" if detail else ""), flush=True)
            if phrase != last_tool:    # не дублируем одинаковое подряд («читаю, читаю»)
                if t_first is None:
                    t_first = time.time() - t0
                await queue.put(phrase + ".")
                last_tool = phrase
    tail = buf.strip()
    if tail:
        if t_first is None:
            t_first = time.time() - t0
        await queue.put(tail)
    await queue.put(None)
    await worker
    # дельты уже содержат свои пробелы — склеиваем без разделителя
    return "".join(full).strip() or "(готово)", t_first, time.time() - t0

async def amain():
    if not shutil.which("ffmpeg"):
        sys.exit("нет ffmpeg в PATH")
    from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions
    opts = ClaudeAgentOptions(model=CLAUDE_MODEL, cwd=CLAUDE_CWD,
                              permission_mode=CLAUDE_PERMISSION,
                              system_prompt=VOICE_SYSTEM,
                              add_dirs=CLAUDE_EXTRA_DIRS,       # доступ к Vault1 и т.п.
                              include_partial_messages=True)  # потоковая выдача → ранняя озвучка
    if CLAUDE_EXTRA_DIRS:
        log(f"доступ к папкам вне рабочей: {', '.join(CLAUDE_EXTRA_DIRS)}")
    log("прогреваю мозг (один раз загружаю контекст IWE, ~30с)…")
    async with ClaudeSDKClient(opts) as client:
        await ask_claude(client, "Готов? Ответь одним словом: готов.")
        log("готов. Скажи «стоп» для выхода — говори.")
        if WAKE_WORDS:
            await asyncio.to_thread(speak, f"Готов. Обращайся по имени: {WAKE_WORDS[0].capitalize()}.")
            log(f"wake-слово: «{WAKE_WORDS[0]}» — реагирую только на обращение по имени")
        else:
            await asyncio.to_thread(speak, "Готов, говори.")
        turn = 0
        while True:
            try:
                await asyncio.to_thread(_close_player)  # слить звук до записи
                pcm = await asyncio.to_thread(record_utterance)
                if len(pcm) < FRAME_BYTES * 5:
                    continue
                t0 = time.time()
                heard = await asyncio.to_thread(transcribe, pcm)
                t_stt = time.time() - t0
                if not heard:
                    continue
                print(f"\033[32m[ты]\033[0m {heard}", flush=True)
                # фильтр по имени (wake-слово). None → не ко мне, тихо игнорирую.
                cmd = extract_command(heard)
                if cmd is None:
                    log("(не по имени — жду обращения)")
                    continue
                if cmd == "":
                    # сказали только имя → отзываюсь и слушаю команду следующей фразой
                    await asyncio.to_thread(speak, "Да?")
                    await asyncio.to_thread(_close_player)
                    pcm = await asyncio.to_thread(record_utterance)
                    if len(pcm) < FRAME_BYTES * 5:
                        continue
                    cmd = await asyncio.to_thread(transcribe, pcm)
                    if not cmd:
                        continue
                    print(f"\033[32m[ты]\033[0m {cmd}", flush=True)
                low = cmd.lower().strip(" .,!?")
                if any(w == low or low.startswith(w + " ") or low.endswith(" " + w) for w in STOP_WORDS):
                    await asyncio.to_thread(speak, "Останавливаюсь. Пока.")
                    break
                # мгновенное подтверждение, чтобы не было немой паузы пока мозг думает
                await asyncio.to_thread(speak, FILLERS[turn % len(FILLERS)])
                turn += 1
                reply, t_first, t_answer = await stream_and_speak(client, cmd)
                print(f"\033[33m[claude]\033[0m {reply}", flush=True)
                if PERF:
                    fa = f"{t_first:.1f}с" if t_first is not None else "—"
                    log(f"⏱ распознавание {t_stt:.1f}с · до первого звука {fa} · весь ответ {t_answer:.1f}с")
            except KeyboardInterrupt:
                print()
                break
            except Exception as e:
                log(f"ошибка в цикле: {e}")
        await asyncio.to_thread(_close_player)  # дать доиграть последнюю фразу
    log("цикл завершён.")

if __name__ == "__main__":
    try:
        asyncio.run(amain())
    except KeyboardInterrupt:
        pass
