#!/usr/bin/env bash
# Голосовой цикл IWE (WP-35 Ф1) — hands-free voice-to-voice с Claude Code.
# Запуск: bash voice-loop.sh
# Аудио идёт через WSLg PulseServer (микрофон Windows = RDPSource).
set -euo pipefail
cd "$(dirname "$0")"
export PATH="$HOME/.local/bin:$PATH"
# глушим шумные предупреждения onnxruntime про GPU (CPU-режим)
exec python3 voice_loop.py "$@" 2> >(grep -vE "onnxruntime|device_discovery|GetGpuDevices|ReadFileContents" >&2)
