"""把 src/script 注入 sys.path，使 para_cnt 可直接 import。"""

import sys
from pathlib import Path

SCRIPT_DIR = str(Path(__file__).resolve().parent.parent)
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)
