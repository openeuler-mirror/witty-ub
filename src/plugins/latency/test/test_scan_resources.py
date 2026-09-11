import pytest

from latency.parse.parallel_scanner import resources
from latency.schemas.config import TaskConfig


@pytest.mark.parametrize('count,affinity,expected', [(64, 8, 8), (8, 64, 8), (None, 8, 1)])
def test_cpu_capacity_respects_affinity(monkeypatch, count, affinity, expected):
    monkeypatch.setattr(resources.os, 'cpu_count', lambda: count)
    monkeypatch.setattr(resources.os, 'sched_getaffinity', lambda _: set(range(affinity)))
    assert resources.cpu_capacity() == expected


def test_cpu_capacity_without_affinity(monkeypatch):
    monkeypatch.setattr(resources.os, 'cpu_count', lambda: 8)
    monkeypatch.delattr(resources.os, 'sched_getaffinity')
    assert resources.cpu_capacity() == 8


def test_scan_options_not_exposed_in_task_schema():
    assert 'scan_max_processes' not in TaskConfig.model_fields
    assert 'scan_spill_dir' not in TaskConfig.model_fields


def test_child_thread_limit_restores_parent_environment(monkeypatch):
    monkeypatch.setenv('POLARS_MAX_THREADS', '8')
    with resources.scan_process_environment():
        assert resources.os.environ['POLARS_MAX_THREADS'] == '1'
    assert resources.os.environ['POLARS_MAX_THREADS'] == '8'
    monkeypatch.delenv('POLARS_MAX_THREADS')
    with resources.scan_process_environment():
        assert resources.os.environ['POLARS_MAX_THREADS'] == '1'
    assert 'POLARS_MAX_THREADS' not in resources.os.environ


def test_child_thread_limit_restored_when_submit_fails(monkeypatch):
    monkeypatch.setenv('POLARS_MAX_THREADS', '8')
    with pytest.raises(RuntimeError):
        with resources.scan_process_environment():
            raise RuntimeError('spawn failed')
    assert resources.os.environ['POLARS_MAX_THREADS'] == '8'


def _child_polars_threads():
    import polars as pl
    return pl.thread_pool_size()


def test_spawned_scan_worker_has_one_polars_thread():
    import multiprocessing
    import polars as pl
    from concurrent.futures import ProcessPoolExecutor
    parent_threads = pl.thread_pool_size()
    with ProcessPoolExecutor(max_workers=1, mp_context=multiprocessing.get_context('spawn')) as executor:
        with resources.scan_process_environment():
            result = executor.submit(_child_polars_threads)
        assert result.result(timeout=30) == 1
    assert pl.thread_pool_size() == parent_threads
