"""In-memory cache for aggregated events, populated during pipeline AGGREGATE.

Routes in ``services/src_dst_aggregated_event.py`` check this cache first
and fall back to SQLite on a miss, keeping the API fast after pipeline completion.
"""

import logging
from latency.schemas.log import SrcDstAggregatedEventDataclass
from latency.database.managers.time_window_aggregated_event import (
    TimeWindowAggregatedEventDataclass,
)

logger = logging.getLogger(__name__)

# Keyed by ``task.op_id`` (log_file_id), NOT by kb_id.
_aggregated_event_cache: dict[str, list[SrcDstAggregatedEventDataclass]] = {}
_time_window_cache: dict[str, list[TimeWindowAggregatedEventDataclass]] = {}


def set_aggregated_events(
    log_id: str,
    events: list[SrcDstAggregatedEventDataclass],
    kb_id: str = "",
) -> None:
    if kb_id:
        for e in events:
            e.kb_id = kb_id
    _aggregated_event_cache[log_id] = events
    logger.info(
        "[CACHE] set_aggregated_events log_id=%s kb_id=%s count=%d",
        log_id,
        kb_id or "(unset)",
        len(events),
    )


def get_aggregated_events(
    log_id: str,
) -> list[SrcDstAggregatedEventDataclass] | None:
    return _aggregated_event_cache.get(log_id)


def set_time_window_events(
    log_id: str,
    events: list[TimeWindowAggregatedEventDataclass],
) -> None:
    _time_window_cache[log_id] = events
    logger.info(
        "[CACHE] set_time_window_events log_id=%s count=%d",
        log_id,
        len(events),
    )


def get_time_window_events(
    log_id: str,
) -> list[TimeWindowAggregatedEventDataclass] | None:
    return _time_window_cache.get(log_id)


def find_aggregated_by_kb_id(
    kb_id: str,
) -> list[SrcDstAggregatedEventDataclass] | None:
    for log_id, cached_events in _aggregated_event_cache.items():
        if cached_events:
            first_kb = getattr(cached_events[0], "kb_id", "")
            match = any(getattr(e, "kb_id", "") == kb_id for e in cached_events)
            logger.info(
                "[CACHE] find_agg_by_kb query=%s cache_log_id=%s first_kb=%r match=%s",
                kb_id, log_id, first_kb, match,
            )
            if match:
                return cached_events
    logger.info("[CACHE] find_agg_by_kb query=%s NOT_FOUND keys=%s", kb_id, list(_aggregated_event_cache.keys()))
    return None


def clear_cache(log_id: str | None = None) -> None:
    if log_id is None:
        _aggregated_event_cache.clear()
        _time_window_cache.clear()
        logger.info("[CACHE] cleared all entries")
        return
    _aggregated_event_cache.pop(log_id, None)
    _time_window_cache.pop(log_id, None)
    logger.info("[CACHE] cleared entries for log_id=%s", log_id)
