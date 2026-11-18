#!/usr/bin/env python3
"""Import the shared Agent runtime from this checkout or an explicit override."""
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
DEFAULT = HERE.parents[1]/'witty_ub_diagnostician/skills/case-matching/scripts'
SCRIPTS = Path(os.environ.get('WITTY_SKILL_SCRIPTS') or
               (HERE if (HERE/'baseline_matching.py').is_file() else DEFAULT)).resolve()
if not (SCRIPTS/'fixed_matching.py').is_file():
    raise RuntimeError('Set WITTY_SKILL_SCRIPTS to the Agent case-matching/scripts directory')
sys.path.insert(0, str(SCRIPTS))
