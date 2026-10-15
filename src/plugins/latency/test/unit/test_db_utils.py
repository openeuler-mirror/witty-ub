# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""latency.database.utils 单元测试。"""
import ipaddress
from datetime import datetime, timezone, timedelta

from latency.database.utils import (
    escape_like,
    format_ip,
    format_timestamp,
    parse_ip,
    parse_pod_ips,
    parse_timestamp,
)


class TestEscapeLike:
    def test_plain_value_unchanged(self):
        assert escape_like("hello") == "hello"

    def test_escapes_percent(self):
        assert escape_like("a%b") == "a\\%b"

    def test_escapes_underscore(self):
        assert escape_like("a_b") == "a\\_b"

    def test_escapes_backslash_first(self):
        assert escape_like("a\\b") == "a\\\\b"

    def test_all_wildcards(self):
        assert escape_like("%_\\") == "\\%\\_\\\\"


class TestParseTimestamp:
    def test_none(self):
        assert parse_timestamp(None) is None

    def test_naive_datetime_passthrough(self):
        dt = datetime(2024, 1, 15, 10, 30, 0)
        assert parse_timestamp(dt) is dt

    def test_aware_datetime_stripped(self):
        dt = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        assert parse_timestamp(dt) == datetime(2024, 1, 15, 10, 30, 0)

    def test_standard_format(self):
        assert parse_timestamp("2024-01-15 10:30:00") == datetime(2024, 1, 15, 10, 30, 0)

    def test_standard_format_with_micro(self):
        assert parse_timestamp("2024-01-15 10:30:00.123456") == datetime(
            2024, 1, 15, 10, 30, 0, 123456
        )

    def test_iso_format(self):
        assert parse_timestamp("2024-01-15T10:30:00") == datetime(2024, 1, 15, 10, 30, 0)

    def test_iso_format_with_micro(self):
        assert parse_timestamp("2024-01-15T10:30:00.5") == datetime(
            2024, 1, 15, 10, 30, 0, 500000
        )

    def test_invalid_string(self):
        assert parse_timestamp("not-a-date") is None

    def test_empty_string(self):
        assert parse_timestamp("") is None


class TestParseIp:
    def test_none_and_empty(self):
        assert parse_ip(None) is None
        assert parse_ip("") is None

    def test_plain_ipv4(self):
        assert parse_ip("192.168.1.1") == ipaddress.IPv4Address("192.168.1.1")

    def test_plain_ipv6(self):
        assert parse_ip("::1") == ipaddress.IPv6Address("::1")

    def test_ipv4_with_port(self):
        assert parse_ip("192.168.1.1:8080") == ipaddress.IPv4Address("192.168.1.1")

    def test_ipv6_bracketed_with_port(self):
        assert parse_ip("[2001:db8::1]:443") == ipaddress.IPv6Address("2001:db8::1")

    def test_invalid(self):
        assert parse_ip("not-an-ip") is None
        assert parse_ip("999.999.999.999") is None


class TestParsePodIps:
    def test_none(self):
        assert parse_pod_ips(None) is None

    def test_empty_list(self):
        assert parse_pod_ips([]) is None

    def test_list_passthrough(self):
        assert parse_pod_ips(["10.0.0.1", "10.0.0.2"]) == ["10.0.0.1", "10.0.0.2"]

    def test_json_string(self):
        assert parse_pod_ips('["10.0.0.1","10.0.0.2"]') == ["10.0.0.1", "10.0.0.2"]

    def test_empty_json_string(self):
        assert parse_pod_ips("[]") is None

    def test_invalid_json(self):
        assert parse_pod_ips("not-json") is None


class TestFormatTimestamp:
    def test_none(self):
        assert format_timestamp(None) is None

    def test_naive(self):
        dt = datetime(2024, 1, 15, 10, 30, 0, 123456)
        assert format_timestamp(dt) == "2024-01-15 10:30:00.123"

    def test_aware_local_offset(self):
        tz = timezone(timedelta(hours=8))
        dt = datetime(2024, 1, 15, 10, 30, 0, 500000, tzinfo=tz)
        result = format_timestamp(dt)
        assert result.startswith("2024-01-15 10:30:00.500")
        assert result.endswith("+08:00")


class TestFormatIp:
    def test_none(self):
        assert format_ip(None) is None

    def test_plain_string(self):
        assert format_ip("1.2.3.4") == "1.2.3.4"

    def test_interface_object(self):
        assert format_ip(ipaddress.IPv4Interface("192.168.1.5/24")) == "192.168.1.5"

    def test_address_object(self):
        assert format_ip(ipaddress.IPv4Address("10.0.0.1")) == "10.0.0.1"
