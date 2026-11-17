# Swarag Video Director

This is a local video editor for Swarag Ravikumar (@aiwithSwarag). Use the repository skill in `.agents/skills/swarag-video-director` for video requests.

- Run the local `.venv` Python interpreter. Use `python -m swarag doctor` to check FFmpeg and dependencies.
- Preserve the original MIT copyright notice and bundled font/model licenses.
- Never commit user media, transcripts, scripts, private edit plans, or output artifacts. Keep test footage outside tracked source folders; `.gitignore` is a second layer, not a substitute for inspecting staged files.
- All edit-plan times are in source coordinates. Trim remapping belongs to the pipeline.
- Keep all 51 named effects and aliases compatible. Render changed effects and run `python -m pytest -q` after relevant changes. `scripts/qa_catalog.py INPUT OUTDIR` verifies every catalog effect with a short private fixture.
- Do not claim completion on an FFmpeg exit code alone: verify file existence, duration, streams, full decode, and relevant visual/audio quality.
