"""Disk-capacity policy shared by health checks and task scheduling."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass


GIB = 1024**3


@dataclass(frozen=True)
class DiskCapacity:
    mode: str
    free_bytes: int
    total_bytes: int
    warning_bytes: int
    critical_bytes: int
    recovery_bytes: int

    @property
    def writable(self) -> bool:
        return self.mode == "normal"


_restricted = False


def _configured_bytes(name: str, default: int) -> int:
    try:
        return max(0, int(os.getenv(name, str(default))))
    except ValueError:
        return default


def disk_capacity(path: str | None = None) -> DiskCapacity:
    """Return normal/warning/critical with hysteresis for automatic recovery."""
    global _restricted
    target = path or os.path.dirname(os.path.dirname(__file__))
    usage = shutil.disk_usage(target)
    warning_default = max(10 * GIB, int(usage.total * 0.10))
    critical_default = max(2 * GIB, int(usage.total * 0.02))
    recovery_default = max(15 * GIB, int(usage.total * 0.15))
    warning = _configured_bytes("WITTY_MIN_FREE_DISK_BYTES", warning_default)
    critical = min(warning, _configured_bytes("WITTY_CRITICAL_FREE_DISK_BYTES", critical_default))
    recovery = max(warning, _configured_bytes("WITTY_RECOVERY_FREE_DISK_BYTES", recovery_default))

    if usage.free <= critical:
        mode = "critical"
        _restricted = True
    elif usage.free < warning or (_restricted and usage.free < recovery):
        mode = "warning"
        _restricted = True
    else:
        mode = "normal"
        _restricted = False
    return DiskCapacity(mode, usage.free, usage.total, warning, critical, recovery)
