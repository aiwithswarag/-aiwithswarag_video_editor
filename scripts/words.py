"""Compatibility entry point for local word timestamps."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from swarag.transcribe import transcribe
if len(sys.argv)!=2: raise SystemExit('Usage: python scripts/words.py INPUT')
source=Path(sys.argv[1])
words=transcribe(source,source.with_suffix('.words.json'))
for word in words: print(f"{word['s']:7.2f}  {word['w']}")
