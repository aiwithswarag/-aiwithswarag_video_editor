"""Bounded-memory rendering of the original 51-effect catalog."""
from __future__ import annotations
import argparse
import importlib.util
import json
import math
import os
from pathlib import Path
import subprocess
import tempfile
import zlib
import numpy as np
import cv2
from PIL import Image
from .runtime import ROOT, executable, probe, verify_video
from .timeline import number


def engine():
    global _ENGINE
    if "_ENGINE" not in globals():
        spec = importlib.util.spec_from_file_location("swarag_legacy_fx", ROOT / "scripts" / "fx.py")
        _ENGINE = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_ENGINE)
    return _ENGINE


def validate_effects(plan, duration):
    fx = engine()
    if isinstance(plan, dict):
        plan = plan.get("effects")
    if not isinstance(plan, list):
        raise ValueError("Effects must be a list")
    result = []
    for raw in plan:
        d = dict(raw)
        name = str(d["fx"]).lower().lstrip("/")
        name = fx.ALIASES.get(name, name)
        if name in fx.LOOK_NAMES:
            name, look = fx.LOOK_NAMES[name]; d.setdefault("look", look)
        if name not in fx.EFFECTS:
            raise ValueError(f"Unknown effect: {name}")
        d["fx"] = name
        d["start"] = number(d.get("start", 0), "effect start", 0, duration)
        d["end"] = number(d.get("end", duration), "effect end", 0, duration + 0.05)
        d["end"] = min(duration, d["end"])
        if d["end"] <= d["start"]:
            raise ValueError(f"{name}: end must follow start")
        for key in ("size", "speed", "zoom", "cell"):
            if key in d:
                number(d[key], key, 0.01, 200)
        if "count" in d:
            count = number(d["count"], "count", 0 if name == "profile-wall" else 1, 1e12 if name == "profile-wall" else 200)
            if int(count) != count: raise ValueError("count must be an integer")
        if name == "profile-wall" and "count" not in d:
            raise ValueError("profile-wall needs your actual count")
        if "images" in d and not Path(d["images"]).is_dir():
            raise ValueError(f"Image folder does not exist: {d['images']}")
        if "ticks" in d:
            ticks = str(d["ticks"]).split("|")
            for tick in ticks: number(tick, "tick time", 0, duration)
            if name in ("todo", "apple-toggles"):
                rows = len(str(d["text"]).split("|")) if "text" in d else 3
                if len(ticks) != rows: raise ValueError(f"{name}: supply one tick time per row")
        if name in ("liquid-glass-graph", "over-the-shoulder-zoom") and "to" not in d:
            raise ValueError(f"{name}: supply real values with 'to'; invented metrics are disabled")
        if name == "over-the-shoulder-zoom" and (len(str(d.get("text", "")).split("|")) != 2 or len(str(d["to"]).split("|")) != 2):
            raise ValueError("over-the-shoulder-zoom needs two labels and two values separated by |")
        if name == "liquid-glass-graph" and d.get("look") == "bento" and not all(k in d for k in ("donut", "kpi", "bars")):
            raise ValueError("bento needs actual donut, kpi, and bars values")
        result.append(d)
    return result


class MaskCache:
    """Compressed temporary storage; RAM usage does not grow with pixel count."""
    def __init__(self):
        self.file = tempfile.TemporaryFile()
        self.index = {}

    def put(self, key, array):
        data = zlib.compress(array.tobytes(), 1)
        self.index[key] = (self.file.tell(), len(data), array.shape)
        self.file.write(data)

    def get(self, key):
        if key not in self.index:
            return None
        offset, size, shape = self.index[key]
        self.file.seek(offset)
        return np.frombuffer(zlib.decompress(self.file.read(size)), np.uint8).reshape(shape)

    def close(self):
        self.file.close()


def frames(path, width, height, rate):
    # A file-backed stderr avoids deadlocks on long decoder diagnostics.
    with tempfile.TemporaryFile() as error:
        proc = subprocess.Popen([executable("ffmpeg"), "-nostdin", "-v", "error", "-xerror", "-i", str(path),
                                 "-vf", f"fps={rate},scale={width}:{height}:flags=bicubic,format=rgb24", "-f", "rawvideo", "-"],
                                stdout=subprocess.PIPE, stderr=error)
        complete = False
        try:
            size = width * height * 3
            while True:
                data = proc.stdout.read(size)
                if not data:
                    complete = True
                    break
                if len(data) != size:
                    raise RuntimeError("Decoder returned a partial frame")
                yield np.frombuffer(data, np.uint8).reshape(height, width, 3)
            code = proc.wait()
            if code:
                error.seek(0)
                raise RuntimeError(error.read().decode(errors="replace")[-4000:])
        finally:
            if not complete and proc.poll() is None:
                proc.kill()
            proc.stdout.close()
            proc.wait()


def waveform(source):
    proc = subprocess.run([executable("ffmpeg"), "-v", "error", "-nostdin", "-i", str(source),
                           "-vn", "-ac", "1", "-ar", "8000", "-f", "f32le", "-"], capture_output=True, check=True)
    data = np.frombuffer(proc.stdout, np.float32)
    if not len(data):
        return [0.0] * 60
    bins = np.array([np.sqrt(np.mean(x*x)) if len(x) else 0 for x in np.array_split(data, 60)])
    return (bins / max(float(bins.max()), 1e-6)).tolist()


def render(source, destination, effects, *, width=1080, fps=None, stills=None, overwrite=False):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if source == destination:
        raise ValueError("Output must never overwrite the source")
    if destination.exists() and not overwrite:
        raise FileExistsError(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    info = probe(source)
    effects = validate_effects(effects, info["duration"])
    width = int(number(width, "short-side resolution", 128, 4320))
    if width % 2:
        raise ValueError("Resolution must be even")
    rate = number(fps if fps is not None else min(info["fps"], 30), "fps", 1, 120)
    sw, sh = info["width"], info["height"]
    if sw <= sh:
        W, H = width, round(width * sh / sw / 2) * 2
    else:
        W, H = round(width * sw / sh / 2) * 2, width
    aw = min(540, W)
    ah = round(aw * H / W / 2) * 2
    fx = engine()
    objects = [fx.Fx(d, rate) for d in effects]
    if any(f.name == "wave-trim" for f in objects):
        values = waveform(source) if info["audio"] else [0.0] * 60
        for f in objects:
            if f.name == "wave-trim": f.o["waveform"] = values
    cache, faces, thumbs, enc = MaskCache(), [], [], None
    tracker = None
    partial = None
    error_file = tempfile.TemporaryFile()
    try:
        print("Pass 1/2: face tracking and segmentation", flush=True)
        if objects:
            tracker = fx.Tracker(aw, ah)
        thumbnail_frames = {int(info["duration"] * rate * (j + 0.5) / 10) for j in range(10)}
        for i, frame in enumerate(frames(source, aw, ah, rate)):
            t = i / rate
            if i in thumbnail_frames or (i == 0 and not thumbs):
                thumbs.append(Image.fromarray(frame.copy()))
            if tracker and any(f.start - 0.5 <= t < f.end + 0.5 for f in objects):
                mask, face = tracker(frame, round(t * 1000))
                cache.put(i, mask); faces.append(face)
            else:
                faces.append(None)
                if tracker: tracker.prev = None
        if not faces:
            raise RuntimeError("No frames decoded")
        sm = fx.smooth(faces, rate)
        face_found = sm is not None
        if sm is None:
            sm = np.tile([aw / 2, ah * 0.33, aw * 0.15], (len(faces), 1))
        for f in objects:
            if f.name in fx.CARD_FX:
                f.cards = fx.load_cards(f.o.get("images"), thumbs)
        still_indices = {int(round(number(s, "still time", 0, info["duration"] - 1 / rate) * rate)) for s in stills} if stills else None
        if still_indices is None:
            handle, temporary = tempfile.mkstemp(prefix=".swarag-", suffix=".mp4", dir=destination.parent)
            os.close(handle); partial = Path(temporary)
            enc = subprocess.Popen([executable("ffmpeg"), "-nostdin", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                                    "-s", f"{W}x{H}", "-r", str(rate), "-i", "-", "-i", str(source),
                                    "-map", "0:v:0", "-map", "1:a:0?", "-c:v", "libx264", "-crf", "17", "-preset", "medium",
                                    "-vf", "scale=out_color_matrix=bt709", "-pix_fmt", "yuv420p", "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-c:a", "aac", "-b:a", "192k", "-af", "apad", "-shortest",
                                    "-movflags", "+faststart", str(partial)], stdin=subprocess.PIPE, stderr=error_file)
        print("Pass 2/2: rendering effects", flush=True)
        saved, frame_count = [], 0
        for i, frame in enumerate(frames(source, W, H, rate)):
            t = i / rate
            frame_count += 1
            if still_indices is not None and i not in still_indices:
                if i > max(still_indices): break
                continue
            active = [f for f in objects if f.start <= t < f.end]
            if active:
                ctx = fx.Ctx(); ctx.W, ctx.H, ctx.t, ctx.fps = W, H, t, rate
                ctx.img = frame.astype(np.float32) / 255
                mask = cache.get(i)
                ctx.m = cv2.resize(mask, (W, H)).astype(np.float32) / 255 if mask is not None else np.zeros((H, W), np.float32)
                x, y, w = sm[min(i, len(sm)-1)]
                ctx.fx, ctx.fy, ctx.fw = x * W / aw, y * H / ah, max(w * W / aw, W * 0.05)
                for f in active:
                    ctx.lt = t - f.start
                    fx.EFFECTS[f.name][0](ctx, f)
                frame = (np.clip(ctx.img, 0, 1) * 255 + 0.5).astype(np.uint8)
            if still_indices is not None:
                target = destination if len(still_indices) == 1 else destination.with_name(f"{destination.stem}_{t:.2f}.png")
                if target.exists() and not overwrite:
                    raise FileExistsError(target)
                Image.fromarray(frame).save(target); saved.append(str(target))
            else:
                try:
                    enc.stdin.write(frame.tobytes())
                except BrokenPipeError as exc:
                    enc.wait(); error_file.seek(0)
                    raise RuntimeError(f"Encoder stopped: {error_file.read().decode(errors='replace')[-4000:]}") from exc
                if i % max(1, round(rate * 5)) == 0: print(f"  {t:.1f}s / {info['duration']:.1f}s", flush=True)
        if enc:
            enc.stdin.close()
            code = enc.wait()
            if code:
                error_file.seek(0)
                raise RuntimeError(f"Encoder failed: {error_file.read().decode(errors='replace')[-4000:]}")
            verify_video(partial, expected_duration=frame_count/rate, expected_audio=info["audio"])
            os.replace(partial, destination)
        elif len(saved) != len(still_indices):
            raise RuntimeError("One or more requested still frames were unavailable")
        return {"output": str(destination), "frames": frame_count, "fps": rate, "face_found": face_found, "stills": saved}
    finally:
        if enc and enc.poll() is None:
            enc.kill(); enc.wait()
        if enc and enc.stdin and not enc.stdin.closed: enc.stdin.close()
        if tracker: tracker.seg.close()
        cache.close(); error_file.close()
        if partial and partial.exists(): partial.unlink()


def main():
    parser = argparse.ArgumentParser(description="Swarag's 51 local video effects")
    parser.add_argument("args", nargs="*")
    for key in ("plan", "text", "images", "still"): parser.add_argument("--"+key)
    parser.add_argument("--start", type=float, default=0)
    parser.add_argument("--end", type=float)
    parser.add_argument("--width", type=int, default=1080)
    parser.add_argument("--fps", type=float)
    parser.add_argument("--opt", action="append", default=[])
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    if args.list:
        for n, (name, (_, desc)) in enumerate(engine().EFFECTS.items(), 1): print(f"{n:2}. {name}: {desc}")
        return
    if args.plan:
        if len(args.args) != 2: parser.error("Expected INPUT OUTPUT with --plan")
        source, output = args.args
        effects = json.loads(Path(args.plan).read_text(encoding="utf-8-sig"))
    else:
        if len(args.args) != 3: parser.error("Expected EFFECT INPUT OUTPUT")
        name, source, output = args.args
        item = {"fx": name, "start": args.start, "end": args.end if args.end is not None else probe(source)["duration"]}
        for key in ("text", "images"):
            if getattr(args, key): item[key] = getattr(args, key)
        for option in args.opt:
            key, value = option.split("=", 1); item[key] = value
        effects = [item]
    render(source, output, effects, width=args.width, fps=args.fps,
           stills=[float(s) for s in args.still.split(",")] if args.still else None, overwrite=args.overwrite)
    print("Verified:", output)
