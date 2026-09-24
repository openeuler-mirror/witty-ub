# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""latency.common.stats 单元测试。"""
import pytest

from latency.common.stats import percentile, percentile_from_sorted, stats


class TestPercentileFromSorted:
    def test_empty_returns_zero(self):
        assert percentile_from_sorted([], 50) == 0.0

    def test_single_element(self):
        assert percentile_from_sorted([7.0], 0) == 7.0
        assert percentile_from_sorted([7.0], 50) == 7.0
        assert percentile_from_sorted([7.0], 100) == 7.0

    def test_p0_p50_p100(self):
        values = [10.0, 20.0, 30.0]
        assert percentile_from_sorted(values, 0) == 10.0
        assert percentile_from_sorted(values, 50) == 20.0
        assert percentile_from_sorted(values, 100) == 30.0

    def test_interpolation(self):
        # k = (4-1)*0.5 = 1.5 → lo=1, frac=0.5 → 20 + 0.5*(30-20) = 25
        assert percentile_from_sorted([10.0, 20.0, 30.0, 40.0], 50) == 25.0


class TestPercentile:
    def test_empty_returns_zero(self):
        assert percentile([], 95) == 0.0

    def test_sorts_input(self):
        # 未排序输入应与排序后结果一致
        assert percentile([30.0, 10.0, 20.0], 50) == 20.0

    def test_matches_sorted_variant(self):
        values = [5.0, 1.0, 9.0, 3.0, 7.0]
        assert percentile(values, 95) == percentile_from_sorted(sorted(values), 95)


class TestStats:
    def test_empty_returns_none_fields(self):
        result = stats([])
        assert result == {
            "ave": None, "min": None, "max": None,
            "p95": None, "p99": None, "p9999": None,
        }

    def test_single_value(self):
        result = stats([4.0])
        assert result["ave"] == 4.0
        assert result["min"] == 4.0
        assert result["max"] == 4.0
        assert result["p95"] == 4.0
        assert result["p99"] == 4.0
        assert result["p9999"] == 4.0

    def test_multiple_values(self):
        result = stats([1.0, 2.0, 3.0, 4.0, 5.0])
        assert result["ave"] == 3.0
        assert result["min"] == 1.0
        assert result["max"] == 5.0
        # sorted=[1..5], p95: k=4*0.95=3.8 → 4+0.8=4.8
        assert result["p95"] == 4.8
        # p99: k=3.96 → 4.96
        assert result["p99"] == 4.96
        # p9999: k=3.9996 → 4+0.9996=4.9996
        assert result["p9999"] == pytest.approx(4.9996)

    def test_unsorted_input(self):
        result = stats([5.0, 1.0, 3.0])
        assert result["min"] == 1.0
        assert result["max"] == 5.0
        assert result["ave"] == 3.0
