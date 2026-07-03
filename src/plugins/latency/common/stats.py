from heapq import nlargest


def percentile_from_sorted(values: list[float], pct: float) -> float:
    """Calculate a percentile from an already sorted list."""
    if not values:
        return 0.0
    k = (len(values) - 1) * pct / 100.0
    lo = int(k)
    hi = min(lo + 1, len(values) - 1)
    frac = k - lo
    return values[lo] + frac * (values[hi] - values[lo])


def percentile_near_max(values: list[float], pct: float) -> float:
    """精确计算高百分位，仅选择插值所需的顶部元素。"""
    if not values:
        return 0.0
    size = len(values)
    rank = (size - 1) * pct / 100.0
    lo = int(rank)
    hi = min(lo + 1, size - 1)
    largest = nlargest(size - lo, values)
    lo_value = largest[size - 1 - lo]
    hi_value = largest[size - 1 - hi]
    return lo_value + (rank - lo) * (hi_value - lo_value)


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    return percentile_from_sorted(sorted(values), pct)


def stats(values: list[float]) -> dict:
    if not values:
        return dict(ave=None, min=None, max=None, p95=None, p99=None)
    sorted_values = sorted(values)
    return dict(
        ave=sum(values) / len(values),
        min=sorted_values[0],
        max=sorted_values[-1],
        p95=percentile_from_sorted(sorted_values, 95),
        p99=percentile_from_sorted(sorted_values, 99),
    )
