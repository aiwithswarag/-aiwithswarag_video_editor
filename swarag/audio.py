"""Local dialogue cleanup, ducked music, original cue sounds, and loudness."""
import json
import math
from pathlib import Path
import re
import wave
import numpy as np
from .runtime import ffmpeg
from .timeline import number


def synthesize(path, kind):
    lengths = {"click": .06, "whoosh": .32, "chime": .48}
    if kind not in lengths: raise ValueError(f"Unknown cue sound: {kind}")
    sr = 48000; t = np.arange(round(sr * lengths[kind])) / sr
    if kind == "click":
        values = .22 * np.sin(2*np.pi*1300*t) * np.exp(-t*95)
    elif kind == "chime":
        values = .14 * (np.sin(2*np.pi*660*t) + .4*np.sin(2*np.pi*990*t)) * np.exp(-t*9)
    else:
        noise = np.random.default_rng(42).normal(0, 1, len(t))
        noise = np.convolve(noise, np.ones(12)/12, mode="same")
        values = .25 * noise * np.sin(np.pi*t/lengths[kind])**2
    values *= np.minimum(1, t/.004) * np.minimum(1, (lengths[kind]-t)/.012)
    with wave.open(str(path), "wb") as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(sr)
        f.writeframes((np.clip(values,-1,1)*32767).astype("<i2").tobytes())


def finish_audio(source, output, duration, options, directory, has_audio):
    directory = Path(directory)
    args = ["-y", "-i", source]
    graph, inputs, idx = [], [], 1
    if has_audio:
        filters = ["aresample=48000", "aformat=channel_layouts=stereo", "apad", f"atrim=0:{duration}"]
        if options.get("clean", True): filters += ["highpass=f=70", "afftdn=nf=-25:tn=1"]
        graph.append(f"[0:a:0]{','.join(filters)}[voice]")
    else:
        graph.append(f"anullsrc=r=48000:cl=stereo,atrim=0:{duration}[voice]")
    music = options.get("music")
    if music:
        args += ["-stream_loop", "-1", "-i", music]
        gain = number(options.get("music_gain_db", -26), "music gain", -60, 0)
        graph += ["[voice]asplit=2[dialogue][side]",
                  f"[{idx}:a:0]aresample=48000,aformat=channel_layouts=stereo,volume={gain}dB,atrim=0:{duration},afade=t=in:d=0.5,afade=t=out:st={max(0,duration-.8)}:d=0.8[music]",
                  "[music][side]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=350[ducked]"]
        inputs = ["dialogue", "ducked"]; idx += 1
    else:
        inputs = ["voice"]
    for n, cue in enumerate(options.get("sfx", [])):
        cue_path = directory / f"cue-{n}.wav"
        if cue.get("file"):
            cue_path = Path(cue["file"])
        else:
            synthesize(cue_path, cue.get("kind", "click"))
        args += ["-i", cue_path]
        delay = round(number(cue["at"], "cue time", 0, duration) * 1000)
        gain = number(cue.get("gain_db", -12), "cue gain", -60, 0)
        label = f"sfx{n}"
        graph.append(f"[{idx}:a:0]aresample=48000,aformat=channel_layouts=stereo,volume={gain}dB,adelay={delay}|{delay}[{label}]")
        inputs.append(label); idx += 1
    graph.append("".join(f"[{s}]" for s in inputs) + f"amix=inputs={len(inputs)}:duration=first:normalize=0,atrim=0:{duration}[mix]")
    mixed = directory / "mixed.wav"
    ffmpeg([*args, "-filter_complex", ";".join(graph), "-map", "[mix]", "-c:a", "pcm_s24le", mixed])
    if not options.get("normalize", True):
        mixed.replace(output); return {"normalized": False}
    target = number(options.get("lufs", -16), "target LUFS", -24, -12)
    measured = ffmpeg(["-i", mixed, "-af", f"loudnorm=I={target}:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"])
    blocks = re.findall(r'\{\s*"input_i".*?\}', measured.stderr, re.S)
    if not blocks: raise RuntimeError("Loudness analysis did not return measurements")
    values = json.loads(blocks[-1])
    if not all(math.isfinite(float(values[k])) for k in ("input_i", "input_tp", "input_lra", "input_thresh", "target_offset")):
        # True digital silence is valid and must not be amplified into noise.
        mixed.replace(output); return {"normalized": False, "reason": "silent or unmeasurable audio"}
    settings = f"loudnorm=I={target}:TP=-1.5:LRA=11:measured_I={values['input_i']}:measured_TP={values['input_tp']}:measured_LRA={values['input_lra']}:measured_thresh={values['input_thresh']}:offset={values['target_offset']}:linear=true:print_format=json"
    ffmpeg(["-y", "-i", mixed, "-af", settings, "-ar", "48000", "-c:a", "pcm_s24le", output])
    return {"normalized": True, "target_lufs": target, "input_lufs": float(values["input_i"])}
