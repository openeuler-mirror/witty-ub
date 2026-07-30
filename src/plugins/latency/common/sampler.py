# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.

from latency.ENUM.sampling import SampleMode
from datetime import datetime
from typing import Tuple, List, Dict, Any, Optional
import json


_PERCENTILE_MAP = {
    SampleMode.P9999: 0.9999,
    SampleMode.P99: 0.99,
    SampleMode.P95: 0.95,
}

_METRIC_KEYS = [
    "total_latency",
    "urma_total_latency",
    "worker_query_meta_latency",
    "sdk_process",
    "sdk_rpc",
    "local_worker_cost",
    "local_worker_lock",
    "remote_worker_cost",
    "remote_worker_rpc",
    "master_process",
    "master_rpc_total",
    "create_latency",
    "publish_latency",
    "worker_total_latency",
]


class LatencyMetricsSampler:

    @staticmethod
    def sample(
        metrics: List[Dict[str, Any]],
        max_points: int,
        sample_mode: SampleMode,
        original_count: int = 0,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        is_bucketed = metrics and "total_latency_values" in metrics[0]

        if is_bucketed:
            return LatencyMetricsSampler._aggregate_bucketed_data(
                metrics, sample_mode, original_count
            )
        else:
            return LatencyMetricsSampler._sample_raw_data(
                metrics, max_points, sample_mode
            )

    @staticmethod
    def _sample_raw_data(
        metrics: List[Dict[str, Any]],
        max_points: int,
        sample_mode: SampleMode,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        original_count = len(metrics)
        if original_count <= max_points or max_points == -1:
            return metrics, {
                "mode": "none",
                "window_ms": 0,
                "original_count": original_count,
                "sampled_count": original_count,
            }

        parsed = []
        for item in metrics:
            ts_ms = LatencyMetricsSampler._parse_timestamp_to_ms(item["time"])
            if ts_ms is not None:
                metric_vals = tuple(item.get(key) for key in _METRIC_KEYS)
                parsed.append((ts_ms, metric_vals, item["time"]))

        if not parsed:
            return [], {
                "mode": sample_mode.value,
                "window_ms": 0,
                "original_count": original_count,
                "sampled_count": 0,
            }

        parsed.sort(key=lambda x: x[0])
        start_ts = parsed[0][0]
        end_ts = parsed[-1][0]
        time_span_ms = end_ts - start_ts

        if time_span_ms <= 0:
            first_vals = parsed[0][1]
            item = {"time": parsed[0][2]}
            for i, key in enumerate(_METRIC_KEYS):
                item[key] = first_vals[i]
            return [item], {
                "mode": sample_mode.value,
                "window_ms": 0,
                "original_count": original_count,
                "sampled_count": 1,
            }

        window_ms = time_span_ms / max_points
        sampled = []
        n_keys = len(_METRIC_KEYS)
        window_values: List[List[float]] = [[] for _ in range(n_keys)]
        window_timestamps: List[int] = []
        window_start = start_ts

        for ts_ms, metric_vals, _ in parsed:
            if ts_ms < window_start + window_ms:
                window_timestamps.append(ts_ms)
                for i in range(n_keys):
                    if metric_vals[i] is not None:
                        window_values[i].append(metric_vals[i])
            else:
                if window_timestamps:
                    sampled.append(
                        LatencyMetricsSampler._build_sampled_item(window_timestamps, window_values, sample_mode)
                    )
                window_timestamps = [ts_ms]
                window_values = [[] for _ in range(n_keys)]
                for i in range(n_keys):
                    if metric_vals[i] is not None:
                        window_values[i].append(metric_vals[i])
                window_start = ts_ms

        if window_timestamps:
            sampled.append(
                LatencyMetricsSampler._build_sampled_item(window_timestamps, window_values, sample_mode)
            )

        return sampled, {
            "mode": sample_mode.value,
            "window_ms": round(window_ms, 2),
            "original_count": original_count,
            "sampled_count": len(sampled),
        }

    @staticmethod
    def _aggregate_bucketed_data(
        bucketed_rows: List[Dict[str, Any]],
        sample_mode: SampleMode,
        original_count: int,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        sampled = []
        for row in bucketed_rows:
            time_str = row.get("time", "")
            item: Dict[str, Any] = {"time": time_str}
            for key in _METRIC_KEYS:
                values = LatencyMetricsSampler._parse_json_array(row.get(f"{key}_values"))
                item[key] = LatencyMetricsSampler._aggregate_values(values, sample_mode)
            sampled.append(item)

        if len(bucketed_rows) > 1:
            ts_list = []
            for row in bucketed_rows:
                ts = LatencyMetricsSampler._parse_timestamp_to_ms(row.get("time", ""))
                if ts is not None:
                    ts_list.append(ts)
            if len(ts_list) >= 2:
                window_ms = (ts_list[-1] - ts_list[0]) / (len(ts_list) - 1)
            else:
                window_ms = 0
        else:
            window_ms = 0

        return sampled, {
            "mode": sample_mode.value,
            "window_ms": round(window_ms, 2),
            "original_count": original_count,
            "sampled_count": len(sampled),
        }

    @staticmethod
    def _parse_json_array(json_str) -> List[float]:
        if not json_str or json_str == "[]":
            return []
        try:
            raw = json.loads(json_str)
            return [float(v) for v in raw if v is not None]
        except (json.JSONDecodeError, TypeError, ValueError):
            return []

    @staticmethod
    def _parse_timestamp_to_ms(timestamp_value) -> Optional[int]:
        if isinstance(timestamp_value, datetime):
            if timestamp_value.tzinfo is not None:
                timestamp_value = timestamp_value.replace(tzinfo=None)
            return int(timestamp_value.timestamp() * 1000)

        timestamp_str = timestamp_value
        try:
            return int(float(timestamp_str))
        except (ValueError, TypeError):
            pass

        try:
            length = len(timestamp_str)
            if length >= 19:
                year = int(timestamp_str[0:4])
                month = int(timestamp_str[5:7])
                day = int(timestamp_str[8:10])
                hour = int(timestamp_str[11:13])
                minute = int(timestamp_str[14:16])
                second = int(timestamp_str[17:19])
                microsecond = 0
                if length > 20 and timestamp_str[19] == '.':
                    microsecond = int(timestamp_str[20:23]) * 1000

                dt = datetime(year, month, day, hour, minute, second, microsecond)
                return int(dt.timestamp() * 1000)
        except (ValueError, IndexError):
            pass

        formats = [
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
        ]
        for fmt in formats:
            try:
                dt = datetime.strptime(timestamp_str, fmt)
                return int(dt.timestamp() * 1000)
            except ValueError:
                continue

        return None

    @staticmethod
    def _aggregate_values(values: List[float], mode: SampleMode) -> Optional[float]:
        if not values:
            return None

        if mode == SampleMode.MAX:
            return max(values)
        elif mode == SampleMode.MIN:
            return min(values)
        elif mode == SampleMode.AVG:
            return sum(values) / len(values)
        elif mode in _PERCENTILE_MAP:
            values.sort()
            percentile = _PERCENTILE_MAP[mode]
            index = max(0, int(len(values) * percentile) - 1)
            return values[index]
        else:
            return max(values)

    @staticmethod
    def _build_sampled_item(
        timestamps: List[int],
        values: List[List[float]],
        mode: SampleMode,
    ) -> Dict[str, Any]:
        if len(timestamps) == 1:
            mid_ts = float(timestamps[0])
        else:
            mid_ts = timestamps[0] + (timestamps[-1] - timestamps[0]) / 2

        mid_time = LatencyMetricsSampler._ms_to_timestamp(mid_ts)

        item: Dict[str, Any] = {"time": mid_time}
        for i, key in enumerate(_METRIC_KEYS):
            item[key] = LatencyMetricsSampler._aggregate_values(values[i], mode)
        return item

    @staticmethod
    def _ms_to_timestamp(ms: float) -> str:
        dt = datetime.fromtimestamp(ms / 1000)
        return dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
