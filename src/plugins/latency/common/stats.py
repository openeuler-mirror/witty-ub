def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    values = sorted(values)
    k = (len(values) - 1) * pct / 100.0
    lo = int(k)
    hi = min(lo + 1, len(values) - 1)
    frac = k - lo
    return values[lo] + frac * (values[hi] - values[lo])


def stats(values: list[float]) -> dict:
    if not values:
        return dict(ave=None, min=None, max=None, p95=None, p99=None)
    return dict(
        ave=sum(values) / len(values),
        min=min(values),
        max=max(values),
        p95=percentile(values, 95),
        p99=percentile(values, 99),
    )
