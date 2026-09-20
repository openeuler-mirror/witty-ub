"""COPY conversion retains legacy timestamp semantics and bounded caches."""
from datetime import datetime, timezone
import ipaddress

import pytest

from latency.database.utils import parse_timestamp, parse_ip, _parse_created_at


def reference_timestamp(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=None)
    for fmt in ('%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%dT%H:%M:%S.%f', '%Y-%m-%dT%H:%M:%S'):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            pass
    return None


@pytest.mark.parametrize('value', [
    None, '', '2026-09-11 12:34:56', '2026-09-11T12:34:56.123456',
    '2026-09-11 12:34:56.1', '2026-9-1 1:2:3', '2024-02-29 12:34:56',
    '2026-02-29 12:34:56', '2026-09-11 24:00:00',
    '2026-09-11T12:34:56Z', '2026-09-11T12:34:56+08:00',
    '2026-09-11 12:34:56.1234567', '2026-09-11',
    datetime(2026, 9, 11, tzinfo=timezone.utc),
])
def test_timestamp_matches_existing_contract(value):
    assert parse_timestamp(value) == reference_timestamp(value)


def test_ip_cache_preserves_port_handling_and_stays_bounded():
    parse_ip.cache_clear()
    assert parse_ip('10.0.0.1:8000') == ipaddress.ip_address('10.0.0.1')
    assert parse_ip('[2001:db8::1]:8000') == ipaddress.ip_address('2001:db8::1')
    assert parse_ip('invalid') is None
    for i in range(5000):
        parse_ip(f'10.0.{i // 256}.{i % 256}')
    assert parse_ip.cache_info().currsize <= 4096
    _parse_created_at.cache_clear()
    for i in range(100):
        _parse_created_at(f'2026-09-11 12:34:56.{i:06d}')
    assert _parse_created_at.cache_info().currsize <= 64


def test_bulk_records_keep_mapping_defaults_constants_and_uuid_contract():
    from dataclasses import replace
    from uuid import UUID
    import polars as pl
    from latency.database.managers.log_parse_result_bulk import LOG_PARSE_RESULT_SPEC, build_records

    spec = LOG_PARSE_RESULT_SPEC.with_columns((
        'id', 'trace_id', 'src_ip', 'pod_ips', 'operation', 'data_size',
        'log_id', 'host', 'aggregated_event_id', 'created_at',
    ))
    frame = pl.DataFrame({
        'id': ['provided', None, ''], 'tid': ['a', 'b', 'c'],
        'src': ['10.0.0.1:80', None, 'bad'], 'pod_ip': [['a'], [], None],
        'op': ['GET', '', None], 'data_size': [1, 0, None], 'host': ['ignored'] * 3,
    })
    created = datetime(2026, 9, 18, tzinfo=timezone.utc)
    rows, _ = build_records(frame, spec, values={'log_id': 'log'}, created_at=created)
    assert [row[1:] for row in rows] == [
        ('a', ipaddress.ip_address('10.0.0.1'), ['a'], 'GET', '1', 'log', None, '', created.replace(tzinfo=None)),
        ('b', None, None, None, None, 'log', None, '', created.replace(tzinfo=None)),
        ('c', None, None, None, None, 'log', None, '', created.replace(tzinfo=None)),
    ]
    assert rows[0][0] == 'provided'
    assert all(UUID(row[0]).version == 4 for row in rows[1:])
    generated, _ = build_records(pl.DataFrame({'tid': range(512)}), spec.with_columns(('id',)))
    assert len({row[0] for row in generated}) == 512
    assert all(UUID(row[0]).version == 4 for row in generated)
    arrays, _ = build_records(frame, replace(spec.with_columns(('pod_ips',)), constants={'pod_ips': ['x']}))
    arrays[0][0].append('changed')
    assert arrays[1][0] == ['x']


def test_bulk_records_preserve_null_validation_and_empty_frame_conversion():
    from dataclasses import replace
    import polars as pl
    from latency.database.managers.log_parse_result_bulk import CopySpec, LOG_PARSE_RESULT_SPEC, build_records

    frame = pl.DataFrame({'id': ['kept', None]})
    spec = LOG_PARSE_RESULT_SPEC.with_columns(('id',))
    with pytest.raises(ValueError, match='row 1 is NULL'):
        build_records(frame, spec, generate_ids=False)
    assert build_records(frame, replace(spec, strict_not_null=False), generate_ids=False)[0] == [('kept',), (None,)]
    with pytest.raises(ValueError, match='frame has no source column'):
        build_records(frame, spec.with_columns(('log_id',)))
    empty_spec = replace(spec.with_columns(('created_at',)), constants={'created_at': 123})
    assert build_records(frame.head(0), empty_spec)[0] == []
    scalar_spec = CopySpec('log_parse_result', ('operation',), created_at_column='operation')
    assert build_records(pl.DataFrame({'operation': ['GET']}), scalar_spec)[0] == [('GET',)]


def test_native_list_conversion_keeps_null_elements_and_empty_lists():
    import polars as pl
    from latency.database.managers.log_parse_result_bulk import LOG_PARSE_RESULT_SPEC, build_records

    stamp = datetime(2026, 9, 18)
    frame = pl.DataFrame({
        'pod_ip': [[None, '中文'], [], None, ['']],
        'cluster_name': [[None, '中文'], [], None, ['']],
        'timestamp': [stamp] * 4,
    })
    rows, _ = build_records(frame, LOG_PARSE_RESULT_SPEC.with_columns(('pod_ips', 'cluster_name', 'timestamp')))
    assert rows == [(['None', '中文'], 'None, 中文', stamp), (None, '', stamp),
                    (None, None, stamp), ([''], '', stamp)]
    stream, _ = build_records(
        frame, LOG_PARSE_RESULT_SPEC.with_columns(('pod_ips', 'cluster_name', 'timestamp')),
        materialize=False,
    )
    assert not isinstance(stream, list)
    assert list(stream) == rows
    assert list(stream) == []
