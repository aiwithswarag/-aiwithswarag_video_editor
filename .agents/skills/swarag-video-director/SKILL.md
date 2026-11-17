---
name: swarag-video-director
description: Edit and finish real videos locally with Swarag's 51 effects, word-timed captions, pause removal, dialogue cleanup, and social MP4 exports. Use when the user supplies footage or a local video path and asks for an edited video. Requires local Python/FFmpeg execution; a normal chat without execution tools cannot render.
---

# Swarag Video Director

Deliver the complete edited MP4. Use the user's recorded face and voice. Never replace a requested video with a storyboard or sample. Use Swarag Ravikumar / @aiwithSwarag for default product identity; retain repository license notices.

## Locate and run

The repository is three parents above this skill folder when used in place. An installed copy has `installation.json` containing its local repository root. The helper `scripts/run.py` locates the repository, selects its `.venv` interpreter, and forwards arguments to `python -m swarag`. On Windows, `<root>/Swarag.ps1` is also an entry point. Run `doctor` before the first edit; use `<root>/Setup.ps1` if the runtime is missing. Perform the commands for the user; do not ask them to write JSON or use a terminal.

## Editing workflow

1. Inspect the actual file with `inspect INPUT`. Inspect representative frames. Transcribe locally with `transcribe INPUT OUTPUT.words.json`; verify names and quotations against the audio and supplied script. The first use downloads a speech model; media processing stays local. Use `--offline` once cached.
2. Read `<root>/docs/plan.md` for the edit schema and `<root>/docs/effects.md` for options. All requested times and transcript words refer to the ORIGINAL input. The pipeline remaps effects, caption words, and audio cues after cuts. Do not remap them manually a second time.
3. Write a private plan beside the deliverable, not into tracked source directories. Use the user's requested effects; choose restrained additional cues only when helpful. Never invent numbers, graphs, view counts, quotations, or timestamps. Graphs require real supplied values. Use actual B-roll/assets where requested. Preserve natural skin; the pipeline grades footage before graphics. Do not add artificial bokeh by default.
4. Produce previews of uncertain effects with `scripts/fx.py --plan EFFECTS.json INPUT CHECK.png --still TIMES`. Review face clearance, text fit, contrast, and edge clipping. A still does not establish animation or audio quality.
5. Run `edit --plan PLAN.json`. Default output is H.264/AAC MP4, 1080 short side, up to 30 fps, subtle natural grade, local captions, dialogue cleanup, and loudness normalization. Silence removal, music, cue sounds, and extra aspect ratios are explicit plan options. `--overwrite` only applies to an existing deliverable, never the input.
6. Wait for completion. Inspect the returned report, full decode verification, frames at each cue, caption timing, cut boundaries, and beginning/end. Listen to the audio when tools support it; otherwise state that listening review is pending. Correct failures and rerender. Deliver the actual master and requested social exports through local file links. State any remaining transcript/creative review caveats accurately.

## Operating boundaries

- The product includes 51 effects plus documented variants; do not promise the separately advertised commercial studio's assets.
- `wave-trim` is a visual waveform animation sourced from real audio. Actual pause removal is `trim.silence` or explicit `trim.keep`.
- The original effect catalog contains aggressive styles. Preserve availability without using all effects in one edit. Face tracking and segmentation are imperfect; inspect hair/hand edges and every graphic crossing the speaker.
- Captions support `clean`, `boxed`, and word-highlighted `emphasis`; automatic placement samples face position and requires visual review on moving subjects. Source audio stays recognizable, but is re-encoded and optionally processed.
- Keep footage, scripts, transcripts, plans, and rendered outputs private and out of Git. A request to edit video does not authorize publication or social posting.
- Render on the local machine. No Claude account or OpenAI API key is required for the renderer. ChatGPT/Codex needs authorized local execution; web-only ChatGPT needs a separate supported computer/connector integration.
