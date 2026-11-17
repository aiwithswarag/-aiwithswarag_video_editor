![Swarag Video Director](assets/swarag-mark.svg)

# Swarag Video Director

A local video editing and finishing workflow by **Swarag Ravikumar · @aiwithSwarag**.
Give ChatGPT Work or Codex your footage and describe the edit. Python and FFmpeg
render the complete MP4 on your computer.

## Use it with ChatGPT

Open this repository folder in desktop ChatGPT Work/Codex and ask:

> Set up Swarag Video Director, then edit the video at my local path. Keep the
> style credible and restrained, add clean captions, tighten long pauses, and
> use relevant effects on the words I actually say. Deliver the full MP4.

The agent uses `.agents/skills/swarag-video-director` and handles setup, timing,
internal plans, rendering, and checks. You do not need to write JSON or operate
a terminal. `Install-ChatGPT-Skill.ps1` installs a personal skill pointing to
this checkout for use outside this project.

On Windows, `Setup.cmd` / `Setup.ps1` creates a Python 3.12 environment, installs
the tested dependency lock, downloads checksum-verified FFmpeg, and checks the
installation. It can use the desktop app's bundled Python. Initial dependencies
and speech-model download need internet; media processing runs locally afterward.
The renderer requires no Claude account or OpenAI API key. The AI assistant has
its own account and connection requirements. Ordinary web chat needs an authorized
connection to your computer; uploading this repository alone is not a backend.

## Included

- 51 effects, aliases, and five additionally tested looks. [Catalog](docs/effects.md)
- Local word timestamps, transcript JSON, and SRT sidecars.
- Clean, boxed, and active-word emphasis captions with measured line wrapping
  and sampled face-aware placement.
- Explicit cuts or conservative silence removal, with synchronized remapping
  of effects, caption words, and audio cues.
- Camera grading before graphics, dialogue cleanup, two-pass loudness
  normalization, ducked user-supplied music, and synthesized cue sounds.
- H.264/AAC master plus vertical, portrait, square, and landscape exports.
- Bounded-memory mask storage, checked subprocesses, full output decoding,
  duration/audio checks, and validation before publishing a final path.

## Operator reference

These commands are for the agent or developers. Use `.venv/Scripts/python.exe`
on Windows or `.venv/bin/python` on Linux/macOS from this folder.

```text
python -m swarag doctor
python -m swarag inspect input.mp4
python -m swarag effects
python -m swarag transcribe input.mp4 input.words.json --model small
python -m swarag edit --plan edit.plan.json
python -m swarag verify output.mp4
python scripts/fx.py orbit input.mp4 output.mp4 --start 3 --end 6
```

See [edit plans](docs/plan.md), [verification notes](docs/validation.md), and
[third-party notices](THIRD_PARTY_NOTICES.md).

## Quality and privacy

Inputs are never overwritten; replacing an existing deliverable requires explicit
`--overwrite`. Private media, transcripts, plans, and renders are ignored by Git.
The renderer does not upload footage. Content you share with an AI assistant is
subject to that assistant's data handling, separately from this local engine.

Speech recognition can mishear words. Segmentation can struggle with hair, hands,
motion, or multiple speakers. Automatic caption placement samples frames rather
than tracking every moving face. Sound cleanup cannot repair clipped recordings.
Reports identify creative and transcript review requirements; inspect the actual
video before posting.

This product extends an MIT-licensed effects engine. Original author, font, and
model notices are preserved in [LICENSE](LICENSE) and
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). Separately sold commercial
studio assets are not included.
