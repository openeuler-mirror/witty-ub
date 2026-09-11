from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from latency.database.managers import log_parse_result as module


@pytest.mark.asyncio
@pytest.mark.parametrize('fail', [False, True])
async def test_one_copy_consumes_bounded_batches_and_closes_on_error(monkeypatch, fail):
    first, second = [1, 2], [3, 4]
    closed = []
    def batches():
        try:
            yield first
            assert first == []
            if fail:
                pytest.fail('COPY failure must not consume another batch')
            yield second
        finally:
            closed.append(True)

    received = []
    async def copy(table, *, records, columns):
        assert table == 'log_parse_result'
        assert not isinstance(records, list)
        for row in records:
            received.append(row)
            if fail:
                raise RuntimeError('COPY failed')

    copy = AsyncMock(side_effect=copy)
    connections = []
    @asynccontextmanager
    async def connection():
        connections.append(True)
        yield SimpleNamespace(get_raw_connection=AsyncMock(return_value=SimpleNamespace(
            driver_connection=SimpleNamespace(copy_records_to_table=copy))))

    monkeypatch.setattr(module.PGManager, 'connection', connection)
    monkeypatch.setattr(module, 'result_to_pg_tuple', lambda row: (row,))
    if fail:
        with pytest.raises(RuntimeError, match='COPY failed'):
            await module.LogParseResultPGManager.add_log_parse_result_batches(batches())
        assert received == [(1,)]
    else:
        assert await module.LogParseResultPGManager.add_log_parse_result_batches(batches()) == 4
        assert received == [(1,), (2,), (3,), (4,)]
        assert second == []
    assert first == []
    assert closed == [True]
    assert connections == [True]
    copy.assert_awaited_once()
    assert module.LogParseResultPGManager.last_store_metrics['success'] is (not fail)
