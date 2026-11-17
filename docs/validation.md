# Verification record

Verified on Windows with Python 3.12, the committed dependency lock, and
FFmpeg 9.0.2. This record describes observed checks, not a guarantee for every
source file, machine, resolution, or creative choice.

## Automated checks

- `python -m pytest -q`: 23 passing tests. Coverage includes synchronized cuts,
  frame-aligned boundaries, captions, audio mixing, silent inputs, social padding,
  source protection, rejected output verification, and effect timing.
- `scripts/qa_catalog.py`: all 51 named effects and five additional looks rendered
  and fully decoded successfully on a private three-second talking-head fixture.
  Each output contained 36 frames at 12 fps, 270×480, with a detected face.
- Representative frames from the catalog were reviewed. Layout fixes were also
  checked at higher resolution for messages, tape labels, glass widgets,
  over-the-shoulder graphics, and the editorial cover.
- The installed personal skill successfully located the runtime and enumerated
  all 51 effects. The skill passed structural validation.

## Real-footage workflow

A private portrait recording was processed end to end: local transcription,
pause removal, camera grading, six timed graphic cues, captions, dialogue
cleanup, cue sounds, and loudness normalization. A 1080×1920 H.264/AAC master,
1080×1080 square export, and 1920×1080 landscape export passed stream, duration,
and full-decode checks. Social exports preserve the complete composition with
solid padding. No user footage or transcript is included in this repository.

Local `small` and `medium.en` speech recognition models were both exercised.
The larger model corrected a duplicated word produced by the smaller model.
Machine transcripts still need review against the recording or supplied script.
Technical loudness checks do not replace listening review.

## Limits and reproduction

Windows is the validated platform. Linux/macOS setup is supplied but has not been
verified here. Exhaustive 4K, HDR, multilingual typography, long recordings,
multiple speakers, and unusual codecs have not been tested. Automatic masking
and face placement require visual review, especially at hair and moving hands.

The GitHub workflow installs the pinned runtime on a clean Windows runner and
runs synthetic tests only. Current CI results are visible in the repository's
Actions tab; consult those results for the specific commit you use.

To reproduce catalog checks, supply your own short private video outside the
checkout and run `python scripts/qa_catalog.py INPUT PRIVATE_OUTPUT_DIRECTORY`.
Keep the resulting media and reports private. For a full edit, follow
[the plan reference](plan.md) and inspect the generated verification report.
