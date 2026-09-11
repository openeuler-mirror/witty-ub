import asyncio
import threading
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from latency.parse.parallel_scanner import scanner as module
from latency.parse.parallel_scanner import resources


@pytest.mark.parametrize('requested,cpus,expected', [
    (None, 64, 16), (64, 64, 16), (2, 64, 2),
    (None, 2, 2), (None, 1, 1), (None, 16, 16),
    (None, 12, 12), (8, 4, 4),
])
def test_scan_limit(monkeypatch, requested, cpus, expected):
    monkeypatch.setattr(resources, 'cpu_capacity', lambda: cpus)
    assert resources.scan_worker_limit(requested) == expected
    assert module.ParallelFileScanner(max_processes=requested).max_processes == expected


@pytest.mark.asyncio
async def test_each_scan_uses_cpu_limit(monkeypatch):
    monkeypatch.setattr(resources, 'cpu_capacity', lambda: 64)
    scanner = module.ParallelFileScanner()
    monkeypatch.setattr(scanner, '_scan_all', AsyncMock(return_value={}))
    for cpus in [64, 8, 16]:
        monkeypatch.setattr(resources, 'cpu_capacity', lambda: cpus)
        await scanner.scan_all()
        assert scanner.max_processes == min(16, cpus)


@pytest.mark.asyncio
async def test_failure_waits_for_shutdown_without_blocking_loop(monkeypatch):
    scanner = module.ParallelFileScanner(max_processes=2)
    entered = threading.Event()
    release = threading.Event()
    exited = threading.Event()
    events = []

    class Pool:
        def __init__(self, max_workers, mp_context):
            assert max_workers == 2
            assert mp_context.get_start_method() == "spawn"

        def shutdown(self, *, wait, cancel_futures=False):
            assert wait and cancel_futures
            entered.set()
            assert release.wait(5)
            events.append('exited')
            exited.set()

    monkeypatch.setattr(module, 'ProcessPoolExecutor', Pool)
    scanner._submit_bounded_multiprocessing = AsyncMock(side_effect=RuntimeError('scan failed'))

    async def scan_then_fallback():
        try:
            await scanner._scan_with_multiprocessing([object(), object()], [], '', None, None)
        except RuntimeError:
            assert exited.is_set()
            events.append('fallback')

    task = asyncio.create_task(scan_then_fallback())
    try:
        async with asyncio.timeout(3):
            while not entered.is_set():
                await asyncio.sleep(0.01)
        assert not task.done()
    finally:
        release.set()
        await asyncio.wait_for(task, timeout=3)
    assert events == ['exited', 'fallback']


@pytest.mark.asyncio
async def test_thread_fallback_respects_scan_limit(monkeypatch):
    scanner = module.ParallelFileScanner(max_processes=2)
    active = peak = 0

    def scan_file(*args):
        nonlocal active, peak
        import time
        active += 1
        peak = max(peak, active)
        time.sleep(0.02)
        active -= 1
        return {}

    from latency.parse.parallel_scanner import process_worker
    monkeypatch.setattr(process_worker, '_scan_file_multi', scan_file)
    groups = [SimpleNamespace(group_id=i, files=[(str(i), [0])]) for i in range(8)]
    await scanner._scan_with_asyncio(groups, [object()], io_concurrency=16)
    assert peak == 2
