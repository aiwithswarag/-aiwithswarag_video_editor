# Edit plan, version 1

Plans are private files named `edit.plan.json`. Paths resolve relative to the plan
file. **All times refer to the original input**, including captions, effects,
ticks, and sound cues. The pipeline remaps once after cuts.

```json
{
  "version": 1,
  "input": "input.mp4",
  "output": "deliverables/master.mp4",
  "width": 1080,
  "fps": 30,
  "grade": "natural",
  "trim": {"silence": true, "threshold_db": -35, "minimum": 0.65, "padding": 0.15},
  "captions": {"enabled": true, "style": "clean", "words": "input.words.json", "position": "auto"},
  "audio": {"clean": true, "normalize": true, "lufs": -16, "sfx": [{"at": 3.2, "kind": "click", "gain_db": -18}]},
  "effects": [{"fx": "lean-in", "start": 3.2, "end": 4.5, "zoom": 1.12}],
  "exports": ["vertical", "square"]
}
```

This is a schema illustration, not timing guidance for uninspected footage.

| Field | Behavior |
|---|---|
| `input`, `output` | Required paths; output must be MP4 and different from input. |
| `width` | Short side, even pixels, default 1080; 2160 requests 4K short side. |
| `fps` | Default min(source fps, 30); explicit values 1–120. |
| `grade` | `natural`, `none`, `warm`, `cool`, `bw`. Before graphics. HDR inputs tone-map to SDR BT.709. |
| `trim.keep` | Ordered non-overlapping `[start,end]` ranges. Cannot combine with silence removal. |
| `trim.silence` | Audio pause detection; defaults -35 dB, minimum 0.65 s, padding 0.15 s. Entirely silent clips are rejected. |
| `captions.enabled` | Default true. Silent inputs have no automatic transcript. |
| `captions.words` | Word JSON list of `{w,s,e}` or object containing `words`. |
| `captions.model` | Local faster-whisper model; default `small`. Larger models use more time and disk. |
| `captions.language` | Optional language code, otherwise detected. Verify font glyphs for non-Latin scripts. |
| `captions.offline` | True requires a cached model and prevents downloading. |
| `captions.style` | `clean`, `boxed`, `emphasis`. |
| `captions.position` | `auto`, `top`, `bottom`. Auto samples three frames for stable placement. |
| `audio.clean` | Default true: high-pass and gentle adaptive noise reduction. |
| `audio.normalize` | Default true: measured two-pass loudness. Target `audio.lufs` defaults -16, ceiling -1.5 dBTP. |
| `audio.music` | Optional user-supplied audio, looped and ducked under dialogue. |
| `audio.music_gain_db` | Default -26 dB before ducking. |
| `audio.sfx` | Source-time cues `{at,kind,gain_db}`; kinds `click`, `whoosh`, `chime`. `file` can replace `kind`. Default gain -12 dB. |
| `effects` | Names, source start/end, effect options. Empty list is valid; composition follows list order. |
| `exports` | `vertical` 1080×1920, `portrait` 1080×1350, `square` 1080×1080, `landscape` 1920×1080. Solid padding preserves content. |

The verified master and social exports have a `.report.json` with cuts, remapped
effects, stream properties, and review requirements. Captions also produce SRT
and word JSON. Temporary intermediates are cleaned on normal completion and
errors; a machine crash can leave `.swarag-work-*` folders.

Effects spanning removed footage split into windows and restart their entrance
animation. Choose cue boundaries accordingly. Silence removal makes hard cuts;
review each boundary and preserve intentional pauses. `wave-trim` is a separate
visual waveform effect, not the actual cutting command.

Charts require real values: `profile-wall` needs `count`; `liquid-glass-graph`
needs `to`; its `bento` look also needs `donut`, `kpi`, and `bars`.
`over-the-shoulder-zoom` needs two labels and two values separated by `|` in
`text` and `to`. Graph curves are illustrative animation, not measured time-series
data. Do not use them to imply unprovided evidence.
