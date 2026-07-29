import glob
import gzip
import io
import os
import sys
from datetime import datetime


class Progress:
    def __init__(self, label: str, total_file=None):
        self.label = label
        self.total_file = total_file
        self.last_len = 0

    def update(self, file_idx=None, path=None, line=None, row=None, match=None):
        parts = [self.label]
        if file_idx is not None and self.total_file is not None:
            parts.append(f"file {file_idx}/{self.total_file}")
        if path is not None:
            parts.append(f"path {os.path.basename(os.path.dirname(path))}/{os.path.basename(path)}")
        if line is not None:
            parts.append(f"line {line:,}")
        if row is not None:
            parts.append(f"row {row:,}")
        if match is not None:
            parts.append(f"match {match:,}")
        msg = " " + "|".join(parts)
        sys.stdout.write("\r" + msg + " " * max(0, self.last_len - len(parts)))
        sys.stdout.flush()
        self.last_len = len(msg)

    def done(self, match=None, rows=None):
        parts = [self.label, "done"]
        if rows is not None:
            parts.append(f"rows {rows:,}")
        if match is not None:
            parts.append(f"match {match:,}")
        msg = " " + "|".join(parts)
        sys.stdout.write("\r" + msg + " " * max(0, self.last_len - len(parts)))
        sys.stdout.flush()
        self.last_len = 0


def glob_paths(patterns: list[str]) -> list[str]:
    paths = []
    seen = set()
    for pattern in patterns:
        for path in glob.glob(pattern, recursive=True):
            if path not in seen:
                paths.append(path)
                seen.add(path)
    return paths


def parse_timestamp(ts: str) -> datetime:
    """Parse log timestamp string to naive datetime.

    Timestamps are interpreted in the database session timezone, which
    matches the timezone of the machine where the logs were generated.
    This ensures consistent behavior across UTC and Asia/Shanghai deployments.
    """
    try:
        return datetime(
            int(ts[0:4]), int(ts[5:7]), int(ts[8:10]),
            int(ts[11:13]), int(ts[14:16]), int(ts[17:19]),
            int(ts[20:26]) if len(ts) > 20 else 0,
        )
    except (ValueError, IndexError):
        raise ValueError(f"Invalid timestamp: {ts}")


def open_log(path: str):
    if path.endswith(".gz"):
        try:
            return gzip.open(path, "rt", encoding="utf-8")
        except OSError as e:
            print(f"Warning: Corrupted gzip file {path} - {e}", file=sys.stderr)
            return io.StringIO("")
    return open(path, "r", errors="replace")