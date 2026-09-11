from types import SimpleNamespace
from unittest.mock import AsyncMock
from contextlib import asynccontextmanager

import pytest
from latency.task.worker import store_trace_context_logs_worker as module
from latency.database.managers.log_failure_event import LogFailureEventPGManager


@pytest.mark.asyncio
@pytest.mark.parametrize('fail', [False, True])
async def test_single_pass_bounded_context_store(tmp_path, monkeypatch, fail):
    line = '2026-09-11T12:00:00 | I | access.cpp | pod | 1:2 | t | cluster | 0 | GET | more|payload\n'
    path = tmp_path / 'access.log'
    path.write_text(line * 16400)
    monkeypatch.setattr(module.LogFilePGManager, 'get_log_file_by_log_file_id', AsyncMock(return_value=SimpleNamespace(kb_id='kb')))
    monkeypatch.setattr(module.KVCacheLogEventDiagnosisWorker, 'parse_filepath_config', AsyncMock(return_value={'ds_client_access_log_file': ['access.log']}))
    monkeypatch.setattr(module.FailureModeKnowledgePGManager, 'get_all_failure_modes', AsyncMock(return_value={}))
    def no_count(*args):
        pytest.fail('must not scan logs a second time just to count')
    monkeypatch.setattr(module.KVCacheLogEventDiagnosisWorker, '_count_log_failure_events', no_count)
    sizes = []
    async def write(batch):
        sizes.append(len(batch))
        assert batch[0]['message'] == '0 | GET | more|payload'
        assert batch[0]['status_code'] == '0'
        if fail:
            raise RuntimeError('database unavailable')
    monkeypatch.setattr(module.LogFailureEventPGManager, 'add_log_failure_event_raw', write)
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
        assert sizes == [8192, 8192, 16]
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
