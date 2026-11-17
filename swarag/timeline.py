"""Source-time cuts, transcript validation, and timing remapping."""
from __future__ import annotations
import math
import re


def number(value, name, low=None, high=None):
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a number")
    result = float(value)
    if not math.isfinite(result) or (low is not None and result < low) or (high is not None and result > high):
        raise ValueError(f"Invalid {name}: {value}")
    return result


def validate_keeps(keeps, duration):
    result = []
    for pair in keeps:
        if len(pair) != 2:
            raise ValueError("Each keep range needs start and end")
        start, end = (number(x, "keep time", 0, duration + 0.001) for x in pair)
        end = min(duration, end)
        if end <= start or (result and start < result[-1][1]):
            raise ValueError("Keep ranges must be ordered, non-overlapping, and have positive duration")
        result.append([start, end])
    if not result:
        raise ValueError("No footage remains after trimming")
    return result


def keeps_from_silence(log, duration, padding=0.15):
    events = re.findall(r"silence_(start|end):\s*([0-9.eE+-]+)", log)
    silence, start = [], None
    for kind, value in events:
        t = max(0, min(duration, float(value)))
        if kind == "start":
            start = t
        elif start is not None:
            silence.append((start, t)); start = None
    if start is not None:
        silence.append((start, duration))
    cursor, keeps = 0.0, []
    for a, b in silence:
        cut_start = a + padding if a > 0.01 else 0.0
        cut_end = b - padding if b < duration - 0.01 else duration
        if cut_end <= cut_start:
            continue
        if cut_start > cursor:
            keeps.append([cursor, cut_start])
        cursor = max(cursor, cut_end)
    if cursor < duration:
        keeps.append([cursor, duration])
    return validate_keeps([r for r in keeps if r[1] - r[0] >= 0.08], duration)


def remap_interval(start, end, keeps):
    offset = 0.0
    result = []
    for a, b in keeps:
        left, right = max(start, a), min(end, b)
        if right > left:
            result.append((offset + left - a, offset + right - a))
        offset += b - a
    return result


def remap_items(items, keeps, start_key="start", end_key="end", *, sort=True):
    result = []
    for item in items:
        for start, end in remap_interval(float(item[start_key]), float(item[end_key]), keeps):
            result.append({**item, start_key: round(start, 6), end_key: round(end, 6)})
    return sorted(result, key=lambda x: x[start_key]) if sort else result


def frame_aligned_keeps(keeps, fps, duration):
    """Expand cuts to frame boundaries, preserving speech and shared A/V timing."""
    aligned = []
    for a, b in keeps:
        start = max(0, math.floor(a * fps + 1e-7) / fps)
        end = min(duration, math.ceil(b * fps - 1e-7) / fps)
        if aligned and start <= aligned[-1][1] + 1e-7:
            aligned[-1][1] = max(end, aligned[-1][1])
        else:
            aligned.append([start, end])
    return aligned


def validate_words(data, duration=None):
    if isinstance(data, dict):
        data = data.get("words")
    if not isinstance(data, list):
        raise ValueError("Transcript must be a list of {w,s,e} words")
    result = []
    previous = -1.0
    for word in data:
        text = str(word["w"]).strip()
        start = number(word["s"], "word start", 0, duration + 0.2 if duration else None)
        end = number(word["e"], "word end", start, duration + 0.2 if duration else None)
        if start < previous or end <= start or not text:
            raise ValueError("Words must have text, positive duration, and ordered timestamps")
        previous = start
        result.append({"w": text, "s": start, "e": end})
    return result
