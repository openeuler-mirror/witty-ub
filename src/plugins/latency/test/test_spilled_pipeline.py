"""Memory-bounded path: cross-batch joins, scalar summaries and complete details."""
from collections import Counter

import polars as pl
import pytest
from polars.testing import assert_frame_equal

from latency.parse.parallel_scanner.columnar import entries_to_columns, TRACE_COLUMNS
from latency.parse.parallel_scanner.spill import EntrySpool, build_spilled_traces
from latency.parse.parallel_scanner.trace_frame import build_trace_frame, _yuanrong_from_grouped
from latency.task.worker.kv_cache_log_parse_worker import KVCacheLogParseWorker as Worker
from test_trace_frame import _fixture_raw, _sdk, _worker_access, _urma


def canonical(frame):
    return frame.with_columns(pl.col('pod_ip').list.sort(), pl.col('cluster_name').list.sort()).sort('tid')


def test_spill_cross_batches_and_groups(tmp_path):
    raw = _fixture_raw()
    # Repeated trace and address priorities across batch AND process boundaries.
    raw['Worker access parse'].extend([_worker_access('t1', 900), _worker_access('t1', 100)])
    raw['Worker urma parse'].append(_urma('t1', 'high-priority', 'dest', 800))
    a, b = EntrySpool(tmp_path, 0, batch_rows=2), EntrySpool(tmp_path, 1, batch_rows=1)
    for spool in (a, b):
        spool.register(raw)
    left, right = {}, {}
    for label, entries in raw.items():
        left[label], right[label] = entries[:1], entries[1:]
        for entry in left[label]:
            a.append(label, entry)
        for entry in right[label]:
            b.append(label, entry)
    expected_columns = entries_to_columns(left)
    for key, values in entries_to_columns(right).items():
        expected_columns[key].extend(values)
    expected = build_trace_frame(expected_columns)
    # Completion order must not change first/last selection.
    output = build_spilled_traces([b.finish(), a.finish()])
    assert_frame_equal(canonical(output['trace_frame']), canonical(expected), check_dtypes=False)
    assert output['entry_counts'] == dict(Counter(expected_columns['_label']))
    assert a.size == b.size == 0


def test_scalar_worker_summaries():
    frame = build_trace_frame(entries_to_columns({
        'SDK access parse': [_sdk('t', elapsed_us=9000)],
        'Worker access parse': [_worker_access('t', 100), _worker_access('t', 200)],
        'Worker urma parse': [_urma('t', elapsed_us=50), _urma('t', elapsed_us=80)],
    }))
    assert all(not isinstance(frame.schema[c], pl.List) for c in frame.columns if c.startswith('__'))
    row = _yuanrong_from_grouped(frame).row(0, named=True)
    assert row['sdk_processing_us'] == 8700
    assert row['worker_access_latency_us'] == 200
    assert row['urma_processing_us'] == 80


def test_detail_projection_preserves_all_storage_fields():
    from dataclasses import asdict
    from latency.schemas.log import YUANRONG_METRIC_FIELDS

    frame = build_trace_frame(entries_to_columns(_fixture_raw()))
    expected = {}
    for flat in _yuanrong_from_grouped(frame).iter_rows(named=True):
        row = Worker._make_field_row(flat, log_file_id='log', is_anomalous=True)
        for name in YUANRONG_METRIC_FIELDS:
            if flat.get(name) is not None:
                setattr(row, name, flat[name])
        values = asdict(row)
        values.pop('created_at')
        expected[row.trace_id] = values
    actual = {}
    for batch in Worker._iter_detail_batches(frame, frame['tid'], {}, 'log', batch_size=2):
        for row in batch:
            values = asdict(row)
            values.pop('created_at')
            actual[row.trace_id] = values
    assert actual == expected


@pytest.mark.parametrize('anomaly_count', [0, 1500, 3000])
def test_detail_batches_include_all_anomalies_without_duplicates(anomaly_count):
    frame = build_trace_frame(entries_to_columns({
        'SDK access parse': [_sdk(f't{i}', elapsed_us=i + 1) for i in range(3000)],
    }))
    anomalies = pl.Series('tid', [f't{i}' for i in range(anomaly_count)], dtype=pl.String)
    batches = Worker._iter_detail_batches(frame, anomalies, {('', '', 'GET'): 'aggregate'}, 'log', batch_size=127)
    got = {}
    for batch in batches:
        assert 0 < len(batch) <= 127
        for row in batch:
            assert row.trace_id not in got
            assert row.aggregated_event_id == 'aggregate'
            got[row.trace_id] = row.is_anomalous
    top_ids = {f't{i}' for i in range(2000, 3000)}
    assert set(got) == top_ids | set(anomalies.to_list())
    assert sum(got.values()) == anomaly_count


def test_empty_spool():
    output = build_spilled_traces([{'spill_paths': {}, 'entry_counts': {}}])
    assert output['trace_frame'].is_empty()
    assert set(TRACE_COLUMNS) <= set(output['trace_frame'].columns)


@pytest.mark.asyncio
@pytest.mark.parametrize('multiprocessing', [False, True])
async def test_real_scanner_spill_matches_in_memory_and_cleans(tmp_path, monkeypatch, multiprocessing):
    from latency.parse.parallel_scanner.scanner import ParallelFileScanner
    from test_scan_merge import _SDK_LINE, _WORKER_LINE, _URMA_LINE, _SRC_DST_LINE, _mk_parsers
    import tempfile

    monkeypatch.setattr(tempfile, 'tempdir', str(tmp_path))
    log_dir = tmp_path / 'logs'
    log_dir.mkdir()
    (log_dir / 'a_access.log').write_text(_SDK_LINE + '\n' + _WORKER_LINE + '\n')
    (log_dir / 'b_runtime.log').write_text(_URMA_LINE + '\n' + _SRC_DST_LINE + '\n')
    # Split a single trace across files and force the single-parser INFO fast path.
    (log_dir / 'c_runtime.log').write_text(_URMA_LINE.replace('trace-urma-1', 'trace-sdk-1') + '\n')
    sdk, worker, info = _mk_parsers()
    sdk._runtime_patterns = ['*_access.log']
    worker._runtime_patterns = ['*_access.log']
    info._runtime_patterns = ['*_runtime.log']
    parsers = [sdk, worker, info]
    old = ParallelFileScanner(max_processes=2, use_multiprocessing=False)
    old_result = await old.scan_all(str(log_dir), parsers)
    expected = build_trace_frame(old_result['columns']).drop('log_id')
    new = ParallelFileScanner(max_processes=2, use_multiprocessing=multiprocessing, spill_to_disk=True, spill_directory=str(tmp_path))
    output = await new.scan_all(str(log_dir), parsers)
    assert_frame_equal(canonical(output['trace_frame'].drop('log_id')), canonical(expected), check_dtypes=False)
    assert new.metrics.total_entries == len(old_result['columns']['tid'])
    assert not list(tmp_path.glob('latency-scan-*'))


def test_spill_write_error_not_swallowed(tmp_path, monkeypatch):
    from latency.parse.parallel_scanner.process_worker import _parse_lines
    from latency.parse.parallel_scanner.spill import SpillError
    from test_scan_merge import _SDK_LINE, _mk_parsers

    spool = EntrySpool(tmp_path, 0, batch_rows=1)
    monkeypatch.setattr(pl.DataFrame, 'write_ipc', lambda *a, **kw: (_ for _ in ()).throw(OSError('disk full')))
    with pytest.raises(SpillError, match='write scan batch'):
        _parse_lines([_mk_parsers()[0]], str(tmp_path / 'log'), [_SDK_LINE], entry_sink=spool)



def test_scalar_rpc_first_last_and_sum():
    from datetime import datetime
    from latency.schemas.ds_log import LogEntry
    from latency.parse.worker_info_parser import CLIENT_RPC_LABEL

    rpc = [LogEntry(timestamp=datetime(2026, 1, 1), trace_id='t',
                    pod_ip='pod', entry_type=None, elapsed_us=None,
                    resp_msg=f'e2e_us={e},server_exec_us={s},network_residual_us={n}')
           for e, s, n in [(900, 700, 50), (800, 600, 60), (700, 500, 70)]]
    frame = build_trace_frame(entries_to_columns({
        'SDK access parse': [_sdk('t', elapsed_us=9000)], CLIENT_RPC_LABEL: rpc,
    }))
    row = _yuanrong_from_grouped(frame).row(0, named=True)
    assert row['request_mode'] == 'remote'
    assert row['sdk_processing_us'] == 6600
    assert row['master_processing_us'] == 700
    assert row['remote_worker_processing_us'] == 500
    assert row['client_master_rpc_framework_us'] == 150
    assert row['client_remote_rpc_framework_us'] == 130


@pytest.mark.asyncio
async def test_cancel_waits_for_spool_reader_before_cleanup(tmp_path, monkeypatch):
    import asyncio
    import tempfile
    import threading
    from pathlib import Path
    from latency.parse.parallel_scanner.scanner import ParallelFileScanner

    monkeypatch.setattr(tempfile, 'tempdir', str(tmp_path))
    scanner = ParallelFileScanner(spill_to_disk=True, spill_directory=str(tmp_path))
    started, release = threading.Event(), threading.Event()
    def read_spool():
        directory = Path(scanner._spill_dir)
        started.set()
        assert release.wait(5)
        assert directory.exists()
    async def scan(*args, **kwargs):
        await scanner._thread_until_done(read_spool)
    monkeypatch.setattr(scanner, '_scan_all', scan)
    task = asyncio.create_task(scanner.scan_all())
    try:
        async with asyncio.timeout(3):
            while not started.is_set():
                await asyncio.sleep(0.01)
        task.cancel()
        await asyncio.sleep(0.02)
        assert not task.done()
        assert list(tmp_path.glob('latency-scan-*'))
    finally:
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await asyncio.wait_for(task, 3)
    assert not list(tmp_path.glob('latency-scan-*'))


@pytest.mark.asyncio
async def test_run_stores_all_details_in_batches_then_aggregates(monkeypatch):
    from types import SimpleNamespace
    from unittest.mock import AsyncMock
    from latency.task.worker import kv_cache_log_parse_worker as module
    from latency.common.stage_progress import StageProgress

    frame = build_trace_frame(entries_to_columns({
        'SDK access parse': [_sdk(f't{i}', elapsed_us=10000 + i) for i in range(2500)],
    }))
    task = SimpleNamespace(id='task', op_id='log', status='RUNNING')
    monkeypatch.setattr(module.TaskPGManager, 'get_task_by_task_id', AsyncMock(return_value=task))
    update_task = AsyncMock()
    monkeypatch.setattr(module.TaskPGManager, 'update_task', update_task)
    monkeypatch.setattr(module.LogFilePGManager, 'get_log_file_by_log_file_id', AsyncMock(return_value=SimpleNamespace(kb_id=None)))
    update_file = AsyncMock()
    monkeypatch.setattr(module.LogFilePGManager, 'update_log_file', update_file)
    monkeypatch.setattr(module.BaseWorker, 'report', AsyncMock())
    monkeypatch.setattr(StageProgress, 'report', AsyncMock())
    monkeypatch.setattr(StageProgress, 'stage_log', AsyncMock())
    monkeypatch.setattr(Worker, 'parse_log', AsyncMock(return_value=frame))
    monkeypatch.setattr(Worker, '_store_bucket_stats_degraded', AsyncMock())
    stored = set()
    async def copy_batches(batches):
        for batch in batches:
            assert len(batch) <= 2048
            for row in batch:
                assert row.trace_id not in stored
                assert row.is_anomalous
                stored.add(row.trace_id)
            batch.clear()
        return len(stored)
    monkeypatch.setattr(module.LogParseResultPGManager, 'add_log_parse_result_batches', copy_batches)
    async def store_result(**kwargs):
        assert len(stored) == 2500
        assert kwargs['anomalous_detail_rows'] == []
        return True
    monkeypatch.setattr(Worker, 'store_result', store_result)
    assert await Worker.run('task') is True
    update_file.assert_awaited_once_with('log', {'anomalous_count': 2500})
    assert update_task.await_args.args[1]['status'] == module.TaskStatusEnum.SUCCESSFUL_PENDING_REMOVE.value


def test_sparse_anomalies_are_packed_before_enrichment(monkeypatch):
    from latency.parse.parallel_scanner import trace_frame
    frame = build_trace_frame(entries_to_columns({
        'SDK access parse': [_sdk(f't{i}', elapsed_us=i + 1) for i in range(10000)],
    }))
    anomalies = pl.Series('tid', [f't{i}' for i in range(0, 9000, 10)])
    enriched_sizes = []
    original = trace_frame._yuanrong_from_grouped
    def enrich(batch):
        enriched_sizes.append(batch.height)
        return original(batch)
    monkeypatch.setattr(trace_frame, '_yuanrong_from_grouped', enrich)
    batches = Worker._iter_detail_batches(frame, anomalies, {}, 'log', batch_size=256)
    sizes = [len(batch) for batch in batches]
    assert sizes == [256] * 7 + [108]  # 1000 top + 900 sparse anomalies
    assert enriched_sizes == [1900]


def test_spool_file_count_stays_bounded_across_flushes(tmp_path):
    from latency.parse.parallel_scanner.spill import PARTITIONS
    with EntrySpool(tmp_path, 0, batch_rows=5) as spool:
        for i in range(200):
            spool.append('SDK access parse', _sdk(f't{i}'))
        result = spool.finish()
    assert spool.sequence == 40
    paths = [path for paths in result['spill_paths'].values() for path in paths]
    assert len(paths) <= PARTITIONS
    assert not spool._writers
    assert build_spilled_traces([result])['trace_frame'].height == 200


def test_corrupt_spool_is_rejected(tmp_path):
    from latency.parse.parallel_scanner.spill import _read_partition_batches, SpillError
    path = tmp_path / 'truncated.ipcseq'
    path.write_bytes(b'\x01')
    with pytest.raises(SpillError, match='Truncated'):
        list(_read_partition_batches(path))
