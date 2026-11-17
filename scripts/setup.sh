#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
command -v ffmpeg >/dev/null || { echo 'Install FFmpeg first.'; exit 1; }
command -v ffprobe >/dev/null || { echo 'Install ffprobe first.'; exit 1; }
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m swarag doctor
