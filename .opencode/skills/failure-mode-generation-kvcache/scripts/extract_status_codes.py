#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extract all K_* enumerators from include/datasystem/utils/status.h.

Usage:
    python3 extract_status_codes.py <yuanrong-datasystem-repo-root>

The input must be the kvcache repository root; the script drills down to
``include/datasystem/utils/status.h``.

Output:
    /tmp/kvcache_status_codes.json
"""

import json
import os
import re
import sys


def extract_status_codes(status_h_path: str) -> list:
    """Parse the StatusCode enum in status.h and return a list of
    {name, value} dicts sorted by value.

    The parser only recognises enumerators whose name starts with ``K_``.
    Enumerator values are parsed as decimal integers.  The status.h in
    yuanrong-datasystem assigns explicit values to every enumerator, so no
    implicit-value inference is needed.
    """
    with open(status_h_path, "r", encoding="utf-8") as fh:
        text = fh.read()

    # Locate the StatusCode enum body.
    m = re.search(r"enum\s+StatusCode\s*:[^}]*\{([^}]*)\}", text, re.DOTALL)
    if not m:
        raise RuntimeError("StatusCode enum not found in {}".format(status_h_path))

    body = m.group(1)

    pattern = re.compile(
        r"""
        \b(?P<name>K_[A-Z0-9_]+)\b       # enumerator name
        \s*=\s*
        (?P<value>\d+)                    # explicit decimal value
        \s*,?                             # optional comma
        """,
        re.VERBOSE,
    )

    entries = []
    seen = set()
    for match in pattern.finditer(body):
        name = match.group("name")
        value = int(match.group("value"))
        if name in seen:
            continue
        seen.add(name)
        entries.append({"name": name, "value": value})

    entries.sort(key=lambda e: e["value"])
    return entries


def main() -> int:
    if len(sys.argv) != 2:
        sys.stderr.write(
            "usage: extract_status_codes.py <yuanrong-datasystem-repo-root>\n"
        )
        return 2

    src_root = sys.argv[1]
    status_h = os.path.join(src_root, "include", "datasystem", "utils", "status.h")
    if not os.path.isfile(status_h):
        sys.stderr.write(
            "status.h not found at {}; input must be the yuanrong-datasystem "
            "repository root\n".format(status_h)
        )
        return 1

    entries = extract_status_codes(status_h)

    out_path = "/tmp/kvcache_status_codes.json"
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(
            {
                "schema_version": 1,
                "source_root": os.path.abspath(src_root),
                "status_h": os.path.relpath(status_h, src_root),
                "status_codes": entries,
                "total": len(entries),
            },
            fh,
            ensure_ascii=False,
            indent=2,
        )

    sys.stdout.write(
        "extracted {} K_* codes from {}\n".format(len(entries), status_h)
    )
    sys.stdout.write("output: {}\n".format(out_path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
