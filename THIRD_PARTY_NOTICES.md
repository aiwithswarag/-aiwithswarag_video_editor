# Third-party notices

Swarag Video Director is maintained and extended by Swarag Ravikumar (@aiwithSwarag).

The 51-effect implementation in `scripts/fx.py` is adapted from
[Vibha Ramprakash's claude-video-effects](https://github.com/Vibha-Ramprakash/claude-video-effects),
provided under the MIT license. Copyright (c) 2026 Vibha Ramprakash.
The original license is preserved in `LICENSE`. Changes include Swarag branding,
local workflow integration, input validation, face-aware layout fixes, bounded
mask storage, checked output handling, and audio-driven waveform data.

New workflow code, tests, and documentation: Copyright (c) 2026 Swarag Ravikumar,
also offered under the MIT license in `LICENSE`.

Bundled fonts retain their licenses in `fonts/`. YuNet and MediaPipe model notices
are in `models/NOTICE.md`; model license texts are distributed in `models/`.
Python dependencies retain their individual licenses in their installed packages.

FFmpeg is downloaded separately by setup, not committed in this repository.
The selected Gyan Windows build includes its own license and build information.
The speech recognition model is downloaded separately for local use and retains
its upstream model license. The generated click, whoosh, and chime cues in
`swarag/audio.py` are synthesized locally; no third-party sound library is bundled.
