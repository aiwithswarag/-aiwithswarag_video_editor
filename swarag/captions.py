"""Word-timed captions with measured line wrapping and ASS escaping."""
from pathlib import Path
import cv2
from PIL import ImageFont
import subprocess
import numpy as np
from .runtime import ROOT, probe, executable

STYLES = ("clean", "boxed", "emphasis")


def safe_text(text):
    return str(text).replace("\\", "＼").replace("{", "｛").replace("}", "｝").replace("\n", " ").replace("\r", " ")


def clock(t):
    value = max(0, round(t * 100))
    hours, value = divmod(value, 360000)
    minutes, value = divmod(value, 6000)
    seconds, centiseconds = divmod(value, 100)
    return f"{hours}:{minutes:02d}:{seconds:02d}.{centiseconds:02d}"


def groups(words, width, font):
    current, chars = [], []
    for word in words:
        candidate = " ".join([*chars, word["w"]])
        if current and (font.getlength(candidate) > width * 1.65 or len(current) >= 9 or word["e"] - current[0]["s"] > 3.2 or word["s"] - current[-1]["e"] > 0.65):
            yield current; current, chars = [], []
        current.append(word); chars.append(word["w"])
        if word["w"].endswith((".", "?", "!")):
            yield current; current, chars = [], []
    if current: yield current


def wrap(words, font, width, highlight=None):
    lines, line = [], []
    for i, word in enumerate(words):
        if line and font.getlength(" ".join(w[1] for w in line) + " " + word["w"]) > width:
            lines.append(line); line = []
        line.append((i, word["w"]))
    if line: lines.append(line)
    rendered = []
    for line in lines:
        parts = []
        for i, text in line:
            text = safe_text(text)
            parts.append((r"{\c&H50D9F2&}" + text + r"{\c&HFFFFFF&}") if i == highlight else text)
        rendered.append(" ".join(parts))
    return r"\N".join(rendered)


def caption_position(source, width, height):
    """Avoid a lower-frame face; stable placement avoids jumping between words."""
    info = probe(source)
    detector = cv2.FaceDetectorYN.create(str(ROOT / "models" / "yunet.onnx"), "", (320, 320), 0.65)
    low, high = 0, 0
    for fraction in (0.15, 0.5, 0.85):
        result = subprocess.run([executable('ffmpeg'),'-v','error','-nostdin','-ss',str(info['duration']*fraction),
                                 '-i',str(source),'-frames:v','1','-vf','scale=320:-2','-f','image2pipe','-vcodec','png','-'],capture_output=True,check=True)
        small = cv2.imdecode(np.frombuffer(result.stdout,np.uint8),cv2.IMREAD_COLOR)
        if small is None: continue
        detector.setInputSize((small.shape[1], small.shape[0]))
        _, faces = detector.detect(small)
        if faces is not None:
            for face in faces:
                y1, y2 = face[1] / small.shape[0], (face[1] + face[3]) / small.shape[0]
                low += int(y2 > 0.68)
                high += int(y1 < 0.28)
    return "top" if low > high else "bottom"


def write_ass(path, words, *, width, height, style="clean", position="bottom"):
    if style not in STYLES: raise ValueError(f"Caption style must be one of {STYLES}")
    if position not in ("top", "bottom"): raise ValueError("Caption position must be top or bottom")
    size = max(18, round(min(width, height) * 0.056))
    font = ImageFont.truetype(str(ROOT / "fonts" / "Inter.ttf"), size)
    # ASS border style 3 produces a real opaque box, not a fake image overlay.
    border, outline = (3, 10) if style == "boxed" else (1, max(1, round(size * 0.055)))
    align, margin = (8, round(height * 0.13)) if position == "top" else (2, round(height * 0.14))
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Inter,{size},&H00FFFFFF,&H0050D9F2,&H00181818,&H60181818,-1,0,0,0,100,100,0,0,{border},{outline},1,{align},{round(width*.09)},{round(width*.09)},{margin},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    chunks = list(groups(words, width * .82, font))
    for index, group in enumerate(chunks):
        # Adjacent cues must not overlap and get stacked by libass.
        cue_end = group[-1]['e'] + .08
        if index+1 < len(chunks): cue_end = min(cue_end, chunks[index+1][0]['s'])
        if style == "emphasis":
            for i, word in enumerate(group):
                end = group[i+1]["s"] if i + 1 < len(group) else cue_end
                if end <= word['s']: continue
                events.append(f"Dialogue: 0,{clock(word['s'])},{clock(end)},Default,,0,0,0,,{wrap(group,font,width*.82,i)}")
        else:
            events.append(f"Dialogue: 0,{clock(group[0]['s'])},{clock(cue_end)},Default,,0,0,0,,{wrap(group,font,width*.82)}")
    Path(path).write_text(header + "\n".join(events) + "\n", encoding="utf-8-sig")


def write_srt(path, words, *, width=1080, height=1920):
    def stamp(t):
        ms = round(t * 1000); h, ms = divmod(ms, 3600000); m, ms = divmod(ms, 60000); s, ms = divmod(ms, 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
    font = ImageFont.truetype(str(ROOT / "fonts" / "Inter.ttf"), max(18,round(min(width,height)*.056)))
    chunks = []
    for i, group in enumerate(groups(words, width*.82, font), 1):
        chunks.append(f"{i}\n{stamp(group[0]['s'])} --> {stamp(group[-1]['e'])}\n{' '.join(w['w'] for w in group)}\n")
    Path(path).write_text("\n".join(chunks), encoding="utf-8")
