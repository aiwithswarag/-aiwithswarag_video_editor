"""Validated, local end-to-end editing. All plan times refer to source footage."""
from __future__ import annotations
import copy
import json
import os
from pathlib import Path
import shutil
import tempfile
import time
from . import __version__
from .runtime import ROOT, ffmpeg, probe, verify_video, write_json
from .timeline import number, validate_keeps, keeps_from_silence, remap_items, remap_interval, validate_words, frame_aligned_keeps
from .effect_runner import render, validate_effects
from .captions import write_ass, write_srt, caption_position
from .audio import finish_audio
from .transcribe import transcribe

PROFILES = {"vertical": (1080, 1920), "square": (1080, 1080), "landscape": (1920, 1080), "portrait": (1080, 1350)}


def resolve_path(value, base):
    path = Path(value).expanduser()
    return path.resolve() if path.is_absolute() else (Path(base) / path).resolve()


def load_plan(path):
    path = Path(path).resolve()
    plan = json.loads(path.read_text(encoding="utf-8-sig"))
    return normalize_plan(plan, path.parent)


def normalize_plan(raw, base=Path.cwd()):
    plan = copy.deepcopy(raw)
    allowed = {"version", "input", "output", "effects", "captions", "audio", "trim", "grade", "width", "fps", "exports"}
    if set(plan) - allowed: raise ValueError(f"Unknown plan fields: {sorted(set(plan)-allowed)}")
    nested = {
        "captions": {"enabled", "words", "style", "position", "model", "language", "offline"},
        "audio": {"clean", "normalize", "lufs", "music", "music_gain_db", "sfx"},
        "trim": {"keep", "silence", "threshold_db", "minimum", "padding"},
    }
    for section, keys in nested.items():
        if section in plan:
            if not isinstance(plan[section], dict): raise ValueError(f"{section} must be an object")
            if set(plan[section]) - keys: raise ValueError(f"Unknown {section} fields: {sorted(set(plan[section])-keys)}")
    if plan.get("version", 1) != 1: raise ValueError("Unsupported plan version")
    for key in ("input", "output"):
        if key not in plan: raise ValueError(f"Missing plan field: {key}")
        plan[key] = str(resolve_path(plan[key], base))
    if plan["input"] == plan["output"]: raise ValueError("Input and output must be different files")
    if Path(plan["output"]).suffix.lower() != ".mp4": raise ValueError("Master output must use .mp4")
    for effect in plan.get("effects", []):
        if effect.get("images"): effect["images"] = str(resolve_path(effect["images"], base))
    captions = plan.setdefault("captions", {"enabled": True, "style": "clean"})
    if captions.get("words"): captions["words"] = str(resolve_path(captions["words"], base))
    audio = plan.setdefault("audio", {})
    if audio.get("music"): audio["music"] = str(resolve_path(audio["music"], base))
    for cue in audio.get("sfx", []):
        if cue.get("file"): cue["file"] = str(resolve_path(cue["file"], base))
    for profile in plan.get("exports", []):
        if profile not in PROFILES: raise ValueError(f"Unknown export profile: {profile}")
    if len(set(plan.get("exports", []))) != len(plan.get("exports", [])): raise ValueError("Duplicate export profiles")
    return plan


def prepare(source, destination, info, keeps, width, fps, grade):
    if grade not in ("natural", "none", "warm", "cool", "bw"): raise ValueError("Unknown grade")
    video_filters = []
    if info.get("color_transfer") in ("smpte2084", "arib-std-b67"):
        video_filters.append("zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv")
    if grade == "natural": video_filters.append("eq=contrast=1.015:saturation=1.025:brightness=0")
    elif grade == "warm": video_filters.append("colorbalance=rs=.025:bs=-.015")
    elif grade == "cool": video_filters.append("colorbalance=rs=-.015:bs=.025")
    elif grade == "bw": video_filters.append("hue=s=0")
    scale = f"scale={width}:-2:flags=lanczos:out_color_matrix=bt709" if info["width"] <= info["height"] else f"scale=-2:{width}:flags=lanczos:out_color_matrix=bt709"
    video_filters += [scale, "setsar=1", f"fps={fps}", "format=yuv420p"]
    graph, streams = [], []
    # Split once to make graph ownership explicit for many cuts.
    n = len(keeps)
    if n > 1:
        graph.append(f"[0:v:0]split={n}" + "".join(f"[vi{i}]" for i in range(n)))
        if info["audio"]: graph.append(f"[0:a:0]asplit={n}" + "".join(f"[ai{i}]" for i in range(n)))
    for i, (start, end) in enumerate(keeps):
        v = f"vi{i}" if n > 1 else "0:v:0"
        graph.append(f"[{v}]trim=start={start}:end={end},setpts=PTS-STARTPTS[v{i}]")
        streams.append(f"[v{i}]")
        if info["audio"]:
            a = f"ai{i}" if n > 1 else "0:a:0"
            graph.append(f"[{a}]atrim=start={start}:end={end},asetpts=PTS-STARTPTS,aresample=48000,apad,atrim=duration={end-start}[a{i}]")
            streams.append(f"[a{i}]")
    audio_out = "[aout]" if info["audio"] else ""
    graph.append("".join(streams) + f"concat=n={n}:v=1:a={int(info['audio'])}[joined]{audio_out}")
    graph.append("[joined]" + ",".join(video_filters) + "[vout]")
    args = ["-y", "-i", source, "-filter_complex", ";".join(graph), "-map", "[vout]"]
    if info["audio"]: args += ["-map", "[aout]", "-c:a", "pcm_s24le"]
    # Lossless H.264 intermediate avoids repeated lossy encodes of camera footage.
    args += ["-c:v", "libx264", "-crf", "0", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", destination]
    ffmpeg(args)


def edit(plan, *, overwrite=False):
    plan = normalize_plan(plan)
    started = time.monotonic()
    source, destination = Path(plan["input"]), Path(plan["output"])
    info = probe(source)
    destinations = [destination] + [destination.with_name(destination.stem + f"_{p}.mp4") for p in plan.get("exports", [])]
    if any(p.resolve() == source.resolve() for p in destinations): raise ValueError("An export would overwrite the source")
    if not overwrite:
        for p in destinations:
            if p.exists(): raise FileExistsError(p)
    destination.parent.mkdir(parents=True, exist_ok=True)
    width = int(number(plan.get("width", 1080), "resolution", 128, 4320))
    if width % 2: raise ValueError("Resolution must be even")
    fps = number(plan.get("fps", min(info["fps"],30)), "fps", 1, 120)
    effects = validate_effects(plan.get("effects", []), info["duration"])
    trim = plan.get("trim", {})
    if trim.get("keep") and trim.get("silence"): raise ValueError("Choose explicit keep ranges or silence removal, not both")
    keeps = validate_keeps(trim.get("keep", [[0, info["duration"]]]), info["duration"])
    if trim.get("silence"):
        if not info["audio"]: raise ValueError("Silence removal needs an audio stream")
        threshold = number(trim.get("threshold_db", -35), "silence threshold", -80, -10)
        minimum = number(trim.get("minimum", .65), "minimum silence", .2, 10)
        padding = number(trim.get("padding", .15), "speech padding", .05, 1)
        print("Detecting pauses in the original audio", flush=True)
        log = ffmpeg(["-i", source, "-vn", "-af", f"silencedetect=noise={threshold}dB:d={minimum}", "-f", "null", "-"])
        keeps = keeps_from_silence(log.stderr, info["duration"], padding)
    keeps = frame_aligned_keeps(keeps, fps, info["duration"])
    duration = sum(b-a for a,b in keeps)
    timed_effects = remap_items(effects, keeps, sort=False)
    # Absolute tick/flip times also need remapping when a cut removes footage.
    for item in timed_effects:
        if "ticks" in item:
            ticks = []
            for value in str(item["ticks"]).split("|"):
                t = float(value)
                mapped = remap_interval(t, t+1/fps, keeps)
                ticks.append(str(mapped[0][0] if mapped else item["start"]))
            item["ticks"] = "|".join(ticks)
        if item["fx"] == "tap" and "at" in item:
            mapped = remap_interval(float(item["at"]), float(item["at"])+1/fps, keeps)
            item["at"] = mapped[0][0] if mapped else item["start"]
    captions = plan.get("captions", {})
    audio = copy.deepcopy(plan.get("audio", {}))
    cues = []
    for cue in audio.get("sfx", []):
        t = number(cue["at"], "source cue time", 0, info["duration"])
        intervals = remap_interval(t, t+1/fps, keeps)
        if intervals: cues.append({**cue, "at": intervals[0][0]})
    audio["sfx"] = cues
    has_audio = info["audio"] or bool(audio.get("music") or cues)
    words, render_report, audio_report = [], {}, {}
    with tempfile.TemporaryDirectory(prefix=".swarag-work-", dir=destination.parent) as temp:
        work = Path(temp)
        if captions.get("enabled", True):
            if captions.get("words"):
                words = validate_words(json.loads(Path(captions["words"]).read_text(encoding="utf-8-sig")), info["duration"])
            elif info["audio"]:
                print("Transcribing locally", flush=True)
                words = transcribe(source, work/"source.words.json", model=captions.get("model", "small"), language=captions.get("language"), offline=captions.get("offline", False))
            words = remap_items(words, keeps, "s", "e")
        print("Preparing camera footage and synchronized cuts", flush=True)
        prepared = work/"prepared.mkv"
        prepare(source, prepared, info, keeps, width, fps, plan.get("grade", "natural"))
        prepared_info = probe(prepared)
        duration = prepared_info["duration"]
        visual = prepared
        if timed_effects:
            visual = work/"effects.mp4"
            render_report = render(prepared, visual, timed_effects, width=width, fps=fps)
        args = ["-y", "-i", visual]
        if has_audio:
            print("Mixing dialogue and requested sound design", flush=True)
            audio_report = finish_audio(prepared, work/"finished.wav", duration, audio, work, info["audio"])
            args += ["-i", work/"finished.wav"]
        filters = []
        position = None
        if words:
            position = captions.get("position", "auto")
            if position == "auto": position = caption_position(prepared, prepared_info["width"], prepared_info["height"])
            write_ass(work/"captions.ass", words, width=prepared_info["width"], height=prepared_info["height"], style=captions.get("style","clean"), position=position)
            (work/"fonts").mkdir()
            shutil.copy2(ROOT/"fonts"/"Inter.ttf", work/"fonts"/"Inter.ttf")
            filters.append("subtitles=captions.ass:fontsdir=fonts")
        args += ["-map", "0:v:0"]
        if has_audio: args += ["-map", "1:a:0", "-c:a", "aac", "-b:a", "192k"]
        if filters: args += ["-vf", ",".join(filters)]
        args += ["-c:v", "libx264", "-crf", "17", "-preset", "medium", "-pix_fmt", "yuv420p", "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-t", str(duration), "-movflags", "+faststart", work/"master.mp4"]
        print("Encoding and verifying the master", flush=True)
        ffmpeg(args, cwd=work)
        reports = [verify_video(work/"master.mp4", expected_duration=duration, expected_audio=has_audio)]
        staged = [work/"master.mp4"]
        for profile in plan.get("exports", []):
            w,h = PROFILES[profile]
            target = work/f"{profile}.mp4"
            # Fit rather than crop: the speaker and graphics remain intact.
            vf = f"scale={w}:{h}:force_original_aspect_ratio=decrease:force_divisible_by=2,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=0x121820,setsar=1"
            ffmpeg(["-y", "-i", work/"master.mp4", "-vf", vf, "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart", target])
            reports.append(verify_video(target, expected_duration=duration, expected_audio=has_audio)); staged.append(target)
        # Publish only after every requested video has passed validation.
        for temp_path, final_path, report in zip(staged, destinations, reports):
            if final_path.exists() and not overwrite: raise FileExistsError(final_path)
            os.replace(temp_path, final_path); report["path"] = str(final_path)
        if words:
            write_srt(destination.with_suffix(".srt"), words, width=prepared_info["width"], height=prepared_info["height"])
            write_json(destination.with_suffix(".words.json"), {"words":words,"review_required":True})
        if render_report: render_report['output'] = str(destination)
        report = {"version":__version__, "source":str(source), "source_duration":info["duration"], "keeps_source_seconds":keeps,
                  "effects_output_seconds":timed_effects,"caption_words":len(words),"caption_position":position,
                  "audio":audio_report,"render":render_report,"outputs":reports,"elapsed_seconds":round(time.monotonic()-started,2),
                  "visual_review_required":True,"transcript_review_required":bool(words)}
        write_json(destination.with_suffix(".report.json"), report)
    print("Verified output:", destination, flush=True)
    return report
