"""Internal scan concurrency: at most 16 workers, bounded by available CPUs."""
import logging
import os
import threading
from contextlib import contextmanager

logger = logging.getLogger(__name__)
DEFAULT_SCAN_WORKERS = 16


def cpu_capacity():
    count = os.cpu_count() or 1
    try:
        return max(1, min(count, len(os.sched_getaffinity(0))))
    except (AttributeError, OSError):
        return count


def scan_worker_limit(requested=None):
    """Internal callers may request a lower limit; memory does not affect admission."""
    cpus = cpu_capacity()
    workers = min(DEFAULT_SCAN_WORKERS, cpus)
    if requested is not None:
        workers = min(workers, max(1, requested))
    logger.info('Scan admission: workers=%d available_cpus=%d', workers, cpus)
    return workers


_SCAN_SPAWN_LOCK = threading.Lock()


@contextmanager
def scan_process_environment():
    """Set child-only Polars limits before spawn imports initialize its thread pool.

    ProcessPoolExecutor starts a child synchronously inside submit(). Restore the
    parent environment immediately afterwards; the parent's pool is unchanged.
    """
    with _SCAN_SPAWN_LOCK:
        previous = os.environ.get("POLARS_MAX_THREADS")
        os.environ["POLARS_MAX_THREADS"] = "1"
        try:
            yield
        finally:
            if previous is None:
                os.environ.pop("POLARS_MAX_THREADS", None)
            else:
                os.environ["POLARS_MAX_THREADS"] = previous
