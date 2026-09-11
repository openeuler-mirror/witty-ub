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
