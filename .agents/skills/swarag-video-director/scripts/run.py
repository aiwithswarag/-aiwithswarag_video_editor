"""Portable entry point for repository-local or installed Swarag skills."""
from pathlib import Path
import json
import os
import subprocess
import sys

skill = Path(__file__).resolve().parents[1]
config = skill/'installation.json'
if config.exists():
    root = Path(json.loads(config.read_text(encoding='utf-8-sig'))['root'])
else:
    root = skill.parents[2]
python = root/'.venv'/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
if not python.is_file():
    raise SystemExit(f'Run {root / "Setup.ps1"} to install the local runtime first.')
raise SystemExit(subprocess.call([str(python),'-m','swarag',*sys.argv[1:]],cwd=root))
