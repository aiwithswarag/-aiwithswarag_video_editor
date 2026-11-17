"""Local speech recognition. Model downloads contain no user media."""
from pathlib import Path
import os
import tempfile
import wave
import numpy as np
from .runtime import ROOT, probe, write_json, ffmpeg
from .timeline import validate_words


def transcribe(source, output, *, model="small", language=None, offline=False):
    if not probe(source)["audio"]:
        raise ValueError("Cannot transcribe a video without audio")
    from faster_whisper import WhisperModel
    cache = Path(os.environ.get("SWARAG_MODEL_CACHE", ROOT / ".cache" / "whisper"))
    cache.mkdir(parents=True, exist_ok=True)
    recognizer = WhisperModel(model, device="cpu", compute_type="int8", download_root=str(cache), local_files_only=offline)
    # Decode through the same verified FFmpeg binary as rendering. Passing PCM
    # also avoids PyAV API differences and honors all supported input containers.
    with tempfile.TemporaryDirectory(prefix="swarag-speech-") as temp:
        pcm = Path(temp)/"speech.wav"
        ffmpeg(["-v","error","-y","-i",source,"-vn","-ac","1","-ar","16000","-c:a","pcm_s16le",pcm])
        with wave.open(str(pcm),"rb") as f:
            samples = np.frombuffer(f.readframes(f.getnframes()),np.int16).astype(np.float32)/32768
    segments, info = recognizer.transcribe(samples, word_timestamps=True, vad_filter=True,
                                           language=language, beam_size=5, condition_on_previous_text=False)
    words = []
    for segment in segments:
        for w in segment.words or []:
            if w.word.strip() and w.end > w.start:
                words.append({"w": w.word.strip(), "s": round(w.start, 3), "e": round(w.end, 3)})
    words = validate_words(words)
    write_json(output, {"language": info.language, "model": model, "words": words,
                        "review_required": True, "note": "Machine transcription; verify proper names and quotations against audio."})
    return words
