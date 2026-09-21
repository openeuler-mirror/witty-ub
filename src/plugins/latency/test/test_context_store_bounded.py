from types import SimpleNamespace
from unittest.mock import AsyncMock
from contextlib import asynccontextmanager

import pytest
from latency.task.worker import store_trace_context_logs_worker as module
from latency.database.managers.log_failure_event import LogFailureEventPGManager


def _csv_records(data):
    import csv
    import io

    if isinstance(data, bytes):
        data = data.decode('utf-8')
    return [
        tuple(None if value == '\\N' else value for value in row)
        for row in csv.reader(io.StringIO(data))
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize('fail', [False, True])
@pytest.mark.parametrize('legacy', [False, True])
async def test_single_pass_bounded_context_store(tmp_path, monkeypatch, fail, legacy):
    monkeypatch.setenv('WITTY_STORE_POLARS', '0' if legacy else '1')
    monkeypatch.setattr(module, '_CONTEXT_BATCH_ROWS', 8192)
    line = '2026-09-11T12:00:00 | I | access.cpp | pod | 1:2 | t | cluster | 0 | GET | more|payload\n'
    path = tmp_path / 'access.log'
    path.write_text(line * 16400)
    monkeypatch.setattr(module.LogFilePGManager, 'get_log_file_by_log_file_id', AsyncMock(return_value=SimpleNamespace(kb_id='kb')))
    monkeypatch.setattr(module.KVCacheLogEventDiagnosisWorker, 'parse_filepath_config', AsyncMock(return_value={'ds_client_access_log_file': ['access.log']}))
    monkeypatch.setattr(module.FailureModeKnowledgePGManager, 'get_all_failure_modes', AsyncMock(return_value={}))
    def no_count(*args):
        pytest.fail('must not scan logs a second time just to count')
    monkeypatch.setattr(module.KVCacheLogEventDiagnosisWorker, '_count_log_failure_events', no_count)
    monkeypatch.setattr(module.StoreTraceContextLogsWorker, '_context_scan_frame', no_count)
    sizes = []
    async def write_raw(batch):
        sizes.append(len(batch))
        row = batch[0]
        assert row['message'] == '0 | GET | more|payload'
        assert row['status_code'] == '0'
        import uuid
        assert uuid.UUID(row['id']).version == 4
        if fail:
            raise RuntimeError('database unavailable')
    async def write_csv(source):
        rows = []
        async for chunk in source:
            rows.extend(_csv_records(chunk.decode('utf-8')))
            if fail:
                break
        sizes.append(len(rows))
        if fail:
            raise RuntimeError('database unavailable')
        assert rows, 'CSV stream produced no records'
        row = dict(zip(module.LogFailureEventPGManager._LOG_FAILURE_COPY_COLUMNS, rows[0]))
        assert row['message'] == '0 | GET | more|payload'
        assert row['status_code'] == '0'
        import uuid
        assert uuid.UUID(row['id']).version == 4
    monkeypatch.setattr(module.LogFailureEventPGManager, 'add_log_failure_event_raw', write_raw)
    monkeypatch.setattr(module.LogFailureEventPGManager, 'add_log_failure_event_csv', write_csv)
    traces = AsyncMock()
    monkeypatch.setattr(module.LogFailureEventPGManager, 'add_trace_failure_event_raw', traces)
    report = AsyncMock()
    monkeypatch.setattr(module.BaseWorker, 'report', report)
    operation = module.StoreTraceContextLogsWorker._store_trace_context_logs(
        str(tmp_path), 'log', {'t'}, {}, task_id='task', progress_base=65, progress_end=90)
    if fail:
        with pytest.raises(module.ContextStoreError):
            await operation
        assert sizes == [8192]
        traces.assert_not_awaited()
    else:
        await operation
        assert sizes == ([8192, 8192, 16] if legacy else [16400])
        traces.assert_awaited_once()
        assert report.await_args.args[2] == 90


@pytest.mark.asyncio
async def test_context_copy_converts_lazily(monkeypatch):
    from latency.database.managers import log_failure_event as db
    converted = []
    def convert(row):
        converted.append(row)
        return (str(row),)
    monkeypatch.setattr(LogFailureEventPGManager, '_log_failure_event_dict_to_tuple', convert)
    async def copy(table, *, records, columns):
        assert converted == []
        assert next(records) == ('1',)
        assert converted == [1]
        assert list(records) == [('2',), ('3',)]
    driver = SimpleNamespace(copy_records_to_table=AsyncMock(side_effect=copy))
    @asynccontextmanager
    async def connection():
        yield SimpleNamespace(get_raw_connection=AsyncMock(return_value=SimpleNamespace(driver_connection=driver)))
    monkeypatch.setattr(db.PGManager, 'connection', connection)
    assert await LogFailureEventPGManager._copy_log_failure_events([1, 2, 3]) == ['1', '2', '3']
    driver.copy_records_to_table.assert_awaited_once()


@pytest.mark.asyncio
async def test_prepared_context_copy_keeps_one_transaction(monkeypatch):
    from latency.database.managers import log_failure_event as db
    rows = [('already', 'converted')]
    events = []
    async def copy(table, *, records, columns):
        events.append('copy')
        assert table == 'log_failure_event'
        assert records is rows
        assert columns is LogFailureEventPGManager._LOG_FAILURE_COPY_COLUMNS
        raise RuntimeError('copy failed')
    driver = SimpleNamespace(copy_records_to_table=copy)
    @asynccontextmanager
    async def connection():
        events.append('begin')
        try:
            yield SimpleNamespace(get_raw_connection=AsyncMock(return_value=SimpleNamespace(driver_connection=driver)))
        except RuntimeError:
            events.append('rollback')
            raise
    monkeypatch.setattr(db.PGManager, 'connection', connection)
    with pytest.raises(RuntimeError, match='copy failed'):
        await LogFailureEventPGManager.add_log_failure_event_records(rows)
    assert events == ['begin', 'copy', 'rollback']


def test_compact_trace_aggregation_matches_existing_merge():
    from itertools import permutations
    diagnosis = module.KVCacheLogEventDiagnosisWorker
    cache = {
        'root': SimpleNamespace(children_failure_mode_ids='child', error_code='K_ROOT(1001)'),
        'child': SimpleNamespace(children_failure_mode_ids='leaf', error_code='K_CHILD(1002)'),
        'leaf': SimpleNamespace(children_failure_mode_ids='', error_code='K_LEAF(1003)'),
        'other': SimpleNamespace(children_failure_mode_ids='', error_code='K_OTHER(1004)'),
    }
    base = dict(log_id='log', trace_id='trace', raw_text='', host_name='Unknown',
                pod_name='pod1', cluster_name='cluster1', timestamp='2026-09-18 10:00:00',
                status_code='0', src_ip='', dst_ip='', operation='', failure_mode=[])
    updates = [
        dict(failure_mode=['root', 'child'], src_ip='1.2.3.4', dst_ip='2.3.4.5', operation='GET'),
        dict(failure_mode=['other'], pod_name='pod2', timestamp='2026-09-18 09:00:00'),
        dict(failure_mode=['root', 'leaf'], status_code='', cluster_name='cluster2', operation='SET'),
        dict(failure_mode=['root'], src_ip='3.4.5.6', dst_ip='4.5.6.7'),
    ]
    for ordering in permutations(updates):
        expected = {}
        compact = module._TraceContextState('9999', (), ())
        for change in ordering:
            row = base | change
            diagnosis._merge_trace_failure_event(expected, row, cache)
            compact.merge(row)
        event = expected['trace']
        event['failure_mode'] = diagnosis._leaf_failure_modes(event['failure_mode'], cache)
        event['status_code'] = diagnosis._failure_mode_error_codes(event.pop('_access_failure_modes'), cache)
        assert compact.event('log', 'trace', cache) == event


@pytest.mark.asyncio
async def test_compact_failure_index_preserves_last_line_and_shares_modes(tmp_path):
    raw = '2026-09-18T00:00:00 | I | file | pod | 1:2 | trace | c | 日志|payload'
    other = raw.replace('trace', 'other')
    (tmp_path / 'failure_trace.log').write_text(
        f'parent | {raw}\nchild,child | {raw}\nchild | {other}\n', encoding='utf-8')
    traces, original = await module.StoreTraceContextLogsWorker._generate_trace_id_set_diagnosis(str(tmp_path))
    compact_traces, compact = await module.StoreTraceContextLogsWorker._generate_trace_id_set_diagnosis(str(tmp_path), compact=True)
    assert traces == compact_traces == {'trace', 'other'}
    assert isinstance(compact, module._FailureModeFrame)
    assert compact.get(raw) == original[raw] == ['child']
    assert compact.get(other) is compact.get(raw)
    assert compact.get('absent') is None
    assert len(compact) == len(original) == 2
    # Native contract: one deduplicated (raw_text, modes) frame, keep="last".
    assert compact.frame.columns == ['raw_text', 'modes']
    assert compact.frame['raw_text'].to_list() == [raw, other]
    assert compact.frame['modes'].to_list() == [['child'], ['child']]
    # A row without '|' is not indexed; blank modes stay an empty list.
    (tmp_path / 'failure_trace.log').write_text(
        f'no-separator line\nparent, child | {raw}\n', encoding='utf-8')
    traces, compact = await module.StoreTraceContextLogsWorker._generate_trace_id_set_diagnosis(str(tmp_path), compact=True)
    assert traces == {'trace'}
    assert len(compact) == 1
    assert compact.get(raw) == ['parent', 'child']


@pytest.mark.parametrize('compressed', [False, True])
def test_context_input_chunks_preserve_long_lines_and_order(tmp_path, monkeypatch, compressed):
    import gzip
    import polars as pl
    monkeypatch.setattr(module, '_CONTEXT_INPUT_BYTES', 96)
    monkeypatch.setattr(module, '_CONTEXT_BATCH_ROWS', 3)
    lines = [f'2026-09-18T00:00:0{i} | I | file | pod | 1:2 | t | c | ' + 'x' * length
             for i, length in enumerate([1, 190, 2, 220, 3])]
    path = tmp_path / ('runtime.log.gz' if compressed else 'runtime.log')
    data = ('\n'.join(lines[:3]) + '\r\n' + '\n'.join(lines[3:])).encode()
    path.write_bytes(gzip.compress(data) if compressed else data)
    batches = list(module.StoreTraceContextLogsWorker._context_scan_batches([(path.name, str(path))], {'t'}, [], []))
    assert all(batch.height <= 3 for batch in batches)
    assert pl.concat(batches)['raw_text'].to_list() == lines


@pytest.mark.parametrize('compressed', [False, True])
def test_context_invalid_utf8_falls_back_to_in_memory_block(tmp_path, monkeypatch, compressed):
    """A gz/large-file block with invalid UTF-8 must be sanitized in-memory.

    Verified by counting how often the file is opened: the in-memory path
    opens it once (in _context_source_queries); the file-based fallback would
    open it a second time after the failed collect().
    """
    import builtins
    import gzip
    import polars as pl
    monkeypatch.setattr(module, '_CONTEXT_INPUT_BYTES', 96)
    monkeypatch.setattr(module, '_CONTEXT_BATCH_ROWS', 3)
    line = '2026-09-18T00:00:00 | I | file | pod | 1:2 | t | c | payload\n'
    data = (line * 5).encode() + b'\xff\xff\xff non-utf8 \xff\n' + (line * 5).encode()
    path = tmp_path / ('runtime.log.gz' if compressed else 'runtime.log')
    path.write_bytes(gzip.compress(data) if compressed else data)

    opens = []
    if compressed:
        # Count only gzip.open; its internal builtins.open would double count.
        real_gzip_open = gzip.open

        def counting_gzip_open(target, *args, **kwargs):
            opens.append(str(target))
            return real_gzip_open(target, *args, **kwargs)

        monkeypatch.setattr(gzip, 'open', counting_gzip_open)
    else:
        real_open = builtins.open

        def counting_open(target, *args, **kwargs):
            if str(target) == str(path):
                opens.append(str(target))
            return real_open(target, *args, **kwargs)

        monkeypatch.setattr(builtins, 'open', counting_open)

    flag = [False]
    batches = list(module.StoreTraceContextLogsWorker._context_scan_batches(
        [(path.name, str(path))], {'t'}, [], [], flag))
    assert flag[0] is True, 'invalid utf8 was not detected'
    assert batches, 'in-memory sanitization produced no batches'
    out = pl.concat(batches)
    # All 10 valid lines recovered; the non-UTF-8 line is filtered by the
    # projection (it has no '|' fields) but must not have crashed the scan.
    assert out.height == 10, out['raw_text'].to_list()
    assert set(out['trace_id'].to_list()) == {'t'}
    # Opened once; a file-based fallback would open it a second time.
    assert opens.count(str(path)) == 1, f'file re-read: {opens}'


def test_context_prefetch_stops_and_closes_source_when_consumer_fails(monkeypatch):
    import polars as pl
    scanned = []
    closed = []

    def sources(_files):
        try:
            for index in range(100):
                scanned.append(index)
                yield pl.DataFrame({'index': [index]}).lazy(), [f'file_{index}'], None
        finally:
            closed.append(True)

    worker = module.StoreTraceContextLogsWorker
    monkeypatch.setattr(worker, '_context_source_queries', sources)
    monkeypatch.setattr(worker, '_context_projection', lambda source, *_args: source)
    reader = worker._context_scan_batches([], {'t'}, [], [])
    assert next(reader)['index'].to_list() == [0]
    reader.close()  # The store closes this reader when COPY raises.
    assert scanned in ([0], [0, 1])
    assert closed == [True]


@pytest.mark.asyncio
async def test_trace_copy_converts_lazily(monkeypatch):
    from latency.database.managers import log_failure_event as db
    converted = []
    def convert(row):
        converted.append(row)
        return ('id', 'log', str(row))
    monkeypatch.setattr(LogFailureEventPGManager, '_trace_failure_event_dict_to_tuple', convert)
    async def copy(table, *, records, columns):
        assert converted == []
        assert next(records) == ('id', 'log', '1')
        assert converted == [1]
        assert list(records) == [('id', 'log', '2'), ('id', 'log', '3')]
    driver = SimpleNamespace(copy_records_to_table=AsyncMock(side_effect=copy))
    @asynccontextmanager
    async def connection():
        yield SimpleNamespace(get_raw_connection=AsyncMock(return_value=SimpleNamespace(driver_connection=driver)))
    monkeypatch.setattr(db.PGManager, 'connection', connection)
    assert await LogFailureEventPGManager._copy_trace_failure_events([1, 2, 3]) == ['1', '2', '3']


def test_sorted_trace_selection_matches_hash_membership():
    import polars as pl
    ids = pl.Series('trace_id', ['z', '中', 'a', 'middle'])
    values = ['before', 'a', 'z', 'middle', '中', 'zzzz', '', 'middle']
    source = pl.DataFrame({
        '_path': ['runtime.log'] * len(values),
        'line': [f'2026-09-18T00:00:00 | I | file | pod | 1:2 | {trace} | c | message'
                 for trace in values],
    }).lazy()
    projection = module.StoreTraceContextLogsWorker._context_projection
    hashed = projection(source, ids, []).collect()
    indexed = projection(source, ids.sort(), []).collect()
    assert indexed.to_dicts() == hashed.to_dicts()
    assert indexed['trace_id'].to_list() == ['a', 'z', 'middle', '中', 'middle']


@pytest.mark.asyncio
async def test_native_context_records_and_group_merge_preserve_values(monkeypatch):
    import polars as pl
    import uuid
    from latency.database.utils import parse_timestamp
    timestamps = [
        '2026-09-18 10:00:00', '2026-09-18 10:00:00.123456',
        '2026-9-8 1:2:3', '2026-09-18 10:00:60', '0000-01-01 00:00:00',
        '2026-09-18 10:00:00.1234567', '2026-02-30 00:00:00',
        '2026-09-18 24:00:00', 'invalid',
    ]
    rows = []
    modes = {}
    expected = {}
    for index, stamp in enumerate(timestamps):
        row = dict(zip(module._CONTEXT_COLUMNS, [''] * len(module._CONTEXT_COLUMNS)))
        row.update(raw_text=f'raw{index}', timestamp=stamp, trace_id=f't{index % 2}',
                   pod_name=f'pod{index % 3}', cluster_name=f'cluster{index % 2}',
                   operation='GET' if index % 3 else 'SET', status_code='0' if index % 2 else '',
                   src_ip='1.2.3.4' if index % 3 else '', dst_ip='2.3.4.5' if index % 3 else '')
        modes[row['raw_text']] = [f'mode{index % 3}', 'common'] if index % 3 else []
        rows.append(row)
        state = expected.setdefault(row['trace_id'], module._TraceContextState(stamp, (), ()))
        state.merge(row | {'failure_mode': modes[row['raw_text']]})
    copied = []

    async def write(source):
        async for chunk in source:
            copied.extend(_csv_records(chunk.decode('utf-8')))

    monkeypatch.setattr(module.LogFailureEventPGManager, 'add_log_failure_event_csv', write)
    count, states = await module.StoreTraceContextLogsWorker._ingest_context_frames(
        pl.DataFrame(rows).iter_slices(3), modes, 'log', None, 0, 0, 100)
    assert count == len(rows)
    for source, record in zip(rows, copied):
        event = dict(zip(module.LogFailureEventPGManager._LOG_FAILURE_COPY_COLUMNS, record))
        assert uuid.UUID(event.pop('id')).version == 4
        assert event.pop('log_id') == 'log'
        assert event.pop('host_name') == 'Unknown'
        stamp = event.pop('timestamp')
        expected_stamp = parse_timestamp(source['timestamp'])
        assert (parse_timestamp(stamp) if stamp else None) == expected_stamp
        assert event.pop('failure_mode') == ','.join(modes[source['raw_text']])
        assert all(value == source[key] for key, value in event.items())
    assert states == expected
