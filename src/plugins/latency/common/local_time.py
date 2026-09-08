"""Server wall-clock timestamps that follow runtime timezone changes."""
import time
from datetime import datetime


def refresh_local_timezone() -> None:
    # Python/libc retain process-local timezone state after /etc/localtime changes.
    # Reload it before generating or formatting server-local timestamps.
    if hasattr(time, "tzset"):
        time.tzset()


def local_now() -> datetime:
    """Return naive server time, matching the database TIMESTAMP convention."""
    refresh_local_timezone()
    return datetime.now()


def utc_now() -> datetime:
    """Absolute time for asset metadata; display timezone is chosen on each read."""
    from datetime import timezone

    return datetime.now(timezone.utc)


def parse_asset_timestamp(value: str | datetime | None) -> datetime | None:
    """Preserve offsets; legacy inputs and date filters use current server time."""
    if value is None:
        return None
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    if value.tzinfo is None:
        refresh_local_timezone()
        value = value.astimezone()
    return value


def legacy_asset_timezone() -> str:
    """Timezone used to interpret naive metadata during the one-time migration."""
    import os
    from pathlib import Path

    configured = os.environ.get("WITTY_LEGACY_ASSET_TIMEZONE")
    if configured:
        return configured
    if os.environ.get("TZ"):
        return os.environ["TZ"].removeprefix(":")
    # Most Linux installations link /etc/localtime to an IANA timezone file.
    path = str(Path("/etc/localtime").resolve())
    if "/zoneinfo/" in path:
        return path.split("/zoneinfo/", 1)[1]
    refresh_local_timezone()
    # A copied localtime file has no IANA name. Use the current offset, with
    # PostgreSQL's POSIX sign convention; configure the IANA name for DST history.
    seconds = int(datetime.now().astimezone().utcoffset().total_seconds())
    sign = "-" if seconds >= 0 else "+"
    hours, remainder = divmod(abs(seconds), 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"UTC{sign}{hours:02}:{minutes:02}:{seconds:02}"
