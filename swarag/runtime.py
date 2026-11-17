"""Process execution, portable tool discovery, and output verification."""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
import shutil
import subprocess
from fractions import Fraction

ROOT = Path(__file__).resolve().parents[1]


def executable(name: str) -> str:
    configured = os.environ.get(f"SWARAG_{name.upper()}")
    if configured:
        if not Path(configured).is_file():
            raise FileNotFoundError(f"SWARAG_{name.upper()} does not point to a file")
        return configured
    suffix = ".exe" if os.name == "nt" else ""
    for directory in (ROOT / ".tools", ROOT.parent / ".tools"):
        matches = sorted(directory.glob(f"**/{name}{suffix}")) if directory.exists() else []
        if matches:
            return str(matches[0])
    found = shutil.which(name)
    if found:
        return found
    raise FileNotFoundError(f"{name} is missing. Run Setup.ps1 (Windows) or install FFmpeg and ffprobe.")


def run(args, *, cwd=None, capture=True):
    command = [str(x) for x in args]
    result = subprocess.run(command, cwd=cwd, capture_output=capture, text=True,
                            encoding="utf-8", errors="replace")
    if result.returncode:
        raise RuntimeError(f"{Path(command[0]).name} failed ({result.returncode}):\n{(result.stderr or '')[-6000:]}")
    return result


def ffmpeg(args, **kwargs):
    return run([executable("ffmpeg"), "-hide_banner", "-nostdin", *args], **kwargs)


def probe(path):
    path = Path(path).resolve()
    if not path.is_file():
        raise FileNotFoundError(path)
    result = run([executable("ffprobe"), "-v", "error", "-show_streams", "-show_format", "-of", "json", path])
    data = json.loads(result.stdout)
    videos = [s for s in data.get("streams", []) if s["codec_type"] == "video" and not s.get("disposition", {}).get("attached_pic")]
    if not videos:
        raise ValueError(f"No video stream: {path.name}")
    video = videos[0]
    rate = video.get("avg_frame_rate", "0/0")
    if rate in ("0/0", "0"):
        rate = video.get("r_frame_rate", "30/1")
    fps = float(Fraction(rate))
    duration = float(video.get("duration") or data.get("format", {}).get("duration", 0))
    if not math.isfinite(duration) or duration <= 0 or not 0 < fps <= 240:
        raise ValueError("Invalid video duration or frame rate")
    width, height = int(video["width"]), int(video["height"])
    rotation = next((int(s.get("rotation", 0)) for s in video.get("side_data_list", []) if "rotation" in s), 0)
    rotation = int(video.get("tags", {}).get("rotate", rotation))
    if abs(rotation) % 180 == 90:
        width, height = height, width
    return {"path": str(path), "width": width, "height": height, "fps": fps,
            "rate": rate, "duration": duration, "audio": any(s["codec_type"] == "audio" for s in data["streams"]),
            "codec": video.get("codec_name"), "pix_fmt": video.get("pix_fmt"),
            "color_transfer": video.get("color_transfer"), "raw": data}


def verify_video(path, *, expected_duration=None, expected_audio=None, decode=True):
    info = probe(path)
    if info["width"] % 2 or info["height"] % 2:
        raise RuntimeError("Output dimensions must be even")
    if expected_duration is not None and abs(info["duration"] - expected_duration) > max(0.2, 2 / info["fps"]):
        raise RuntimeError(f"Duration mismatch: expected {expected_duration:.3f}s, got {info['duration']:.3f}s")
    if expected_audio is not None and info["audio"] != expected_audio:
        raise RuntimeError("Output audio stream mismatch")
    if decode:
        ffmpeg(["-v", "error", "-xerror", "-i", path, "-map", "0:v:0", "-map", "0:a?", "-f", "null", "-"])
    return {k: v for k, v in info.items() if k != "raw"}


def write_json(path, data):
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
