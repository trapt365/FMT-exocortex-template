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

CLAUDE_PERMISSION = os.environ.get("VOICE_CLAUDE_PERM", "acceptEdits")  # режим прав claude -p
CLAUDE_CWD    = os.environ.get("VOICE_CLAUDE_CWD", str(Path.home() / "IWE"))
CLAUDE_MODEL  = os.environ.get("VOICE_CLAUDE_MODEL", "haiku")  # голос: самый быстрый
VOICE_SYSTEM  = os.environ.get("VOICE_SYSTEM_PROMPT",
    "Ты отвечаешь пользователю ГОЛОСОМ — ответ озвучивается вслух, и речь длится "
    "столько же, сколько текст. Поэтому будь предельно краток: МАКСИМУМ 2 коротких "
    "предложения. СТРОГО ЗАПРЕЩЕНО перечислять списком — даже если просят 'приоритеты' "
    "или 'список', назови ТОЛЬКО самое главное одним предложением и спроси, нужны ли "
    "детали. Никакого markdown, звёздочек, решёток, кода, ссылок, путей к файлам, "
    "технических кодов — говори по-человечески, как в живом разговоре. "
    "Длинную работу выполни и скажи итог одной фразой.")
PERF          = os.environ.get("VOICE_PERF", "1") == "1"  # печатать тайминги этапов

STOP_WORDS    = {"стоп", "выход", "хватит", "stop", "quit", "exit", "пока"}

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

# ── TTS (piper → pulse) ──────────────────────────────────────────────────────
_piper = None
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
        # Воспроизведение через ffmpeg->pulse: ffplay по умолчанию идёт в ALSA,
        # которого в WSL нет; pulse (RDPSink) — единственный рабочий путь.
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error",
                        "-i", out, "-f", "pulse", "voice-loop"], check=False)
    finally:
        os.unlink(out)

# ── Главный цикл ──────────────────────────────────────────────────────────────
import asyncio, time

async def amain():
    if not shutil.which("ffmpeg"):
        sys.exit("нет ffmpeg в PATH")
    from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions
    opts = ClaudeAgentOptions(model=CLAUDE_MODEL, cwd=CLAUDE_CWD,
                              permission_mode=CLAUDE_PERMISSION,
                              system_prompt=VOICE_SYSTEM)
    log("прогреваю мозг (один раз загружаю контекст IWE, ~30с)…")
    async with ClaudeSDKClient(opts) as client:
        await ask_claude(client, "Готов? Ответь одним словом: готов.")
        log("готов. Скажи «стоп» для выхода — говори.")
        await asyncio.to_thread(speak, "Готов, говори.")
        while True:
            try:
                pcm = await asyncio.to_thread(record_utterance)
                if len(pcm) < FRAME_BYTES * 5:
                    continue
                t0 = time.time()
                heard = await asyncio.to_thread(transcribe, pcm)
                t_stt = time.time() - t0
                if not heard:
                    continue
                print(f"\033[32m[ты]\033[0m {heard}", flush=True)
                low = heard.lower().strip(" .,!?")
                if any(w == low or low.startswith(w + " ") or low.endswith(" " + w) for w in STOP_WORDS):
                    await asyncio.to_thread(speak, "Останавливаюсь. Пока.")
                    break
                t1 = time.time()
                reply = await ask_claude(client, heard)
                t_brain = time.time() - t1
                print(f"\033[33m[claude]\033[0m {reply}", flush=True)
                t2 = time.time()
                await asyncio.to_thread(speak, reply)
                t_tts = time.time() - t2
                if PERF:
                    log(f"⏱ распознавание {t_stt:.1f}с · мозг {t_brain:.1f}с · озвучка {t_tts:.1f}с")
            except KeyboardInterrupt:
                print()
                break
            except Exception as e:
                log(f"ошибка в цикле: {e}")
    log("цикл завершён.")

if __name__ == "__main__":
    try:
        asyncio.run(amain())
    except KeyboardInterrupt:
        pass
