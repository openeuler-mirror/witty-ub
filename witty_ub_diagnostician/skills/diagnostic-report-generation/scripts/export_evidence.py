#!/usr/bin/env python3
"""Export Agent matching observations through the shared fixed policy extractor."""
from pathlib import Path
import sys

SCRIPTS = Path(__file__).resolve().parents[2]/'case-matching/scripts'
sys.path.insert(0, str(SCRIPTS))


def main(argv=None):
    from match_baseline import main as export
    return export(argv)


if __name__ == '__main__':
    raise SystemExit(main())
