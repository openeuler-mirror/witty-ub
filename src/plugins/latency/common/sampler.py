# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.

from latency.ENUM.sampling import SampleMode
from datetime import datetime
from typing import Tuple, List, Dict, Any, Optional
import json


# 预编译百分位映射
_PERCENTILE_MAP = {
    SampleMode.P9999: 0.9999,
    SampleMode.P99: 0.99,
    SampleMode.P95: 0.95,
}


class LatencyMetricsSampler:
    """延迟指标采样器

    用于对时间序列延迟指标数据进行采样，减少前端渲染压力，同时保留关键特征。
    支持多种采样模式：最大值、最小值、平均值、百分位等。
    """

    @staticmethod
    def sample(
        metrics: List[Dict[str, Any]],
        max_points: int,
        sample_mode: SampleMode,
        original_count: int = 0,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """对时间序列数据进行采样

        Args:
            metrics: 数据点列表，支持两种格式：
                     1. 原始数据：[{"time": "...", "total_latency": 1.2, ...}]
                     2. 分桶数据：[{"time": "...", "total_latency_values": "[1.2,3.4,...]", ...}]
            max_points: 最大返回点数
            sample_mode: 采样模式
            original_count: 原始数据总数（可选，用于分桶模式传递 COUNT 结果）

        Returns:
            (采样后数据 dict 列表，采样信息字典)
        """
        # 检测是否为 SQL 分桶数据（包含 JSON 数组字段）
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
        """对原始逐条数据进行采样（数据量 <= max_points 时直接返回）"""
        original_count = len(metrics)
        if original_count <= max_points or max_points == -1:
            return metrics, {
                "mode": "none",
                "window_ms": 0,
                "original_count": original_count,
                "sampled_count": original_count,
            }

        # 一次性解析所有时间戳，缓存到预计算结构中
        parsed = []
        for item in metrics:
            ts_ms = LatencyMetricsSampler._parse_timestamp_to_ms(item["time"])
            if ts_ms is not None:
                parsed.append((
                    ts_ms,
                    item.get("total_latency"),
                    item.get("urma_total_latency"),
                    item.get("worker_query_meta_latency"),
                    item["time"],
                ))

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
            return [{
                "time": parsed[0][4],
                "total_latency": parsed[0][1],
                "urma_total_latency": parsed[0][2],
                "worker_query_meta_latency": parsed[0][3],
            }], {
                "mode": sample_mode.value,
                "window_ms": 0,
                "original_count": original_count,
                "sampled_count": 1,
            }

        window_ms = time_span_ms / max_points
        sampled = []
        window_values = [[], [], []]
        window_timestamps = []
        window_start = start_ts

        for ts_ms, tl, ul, wl, _ in parsed:
            if ts_ms < window_start + window_ms:
                window_timestamps.append(ts_ms)
                if tl is not None: window_values[0].append(tl)
                if ul is not None: window_values[1].append(ul)
                if wl is not None: window_values[2].append(wl)
            else:
                if window_timestamps:
                    sampled.append(
                        LatencyMetricsSampler._build_sampled_item(window_timestamps, window_values, sample_mode)
                    )
                window_timestamps = [ts_ms]
                window_values = [[], [], []]
                if tl is not None: window_values[0].append(tl)
                if ul is not None: window_values[1].append(ul)
                if wl is not None: window_values[2].append(wl)
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
        """对 SQL 分桶后的数据进行聚合（JSON 数组 → 单值）"""
        sampled = []
        for row in bucketed_rows:
            time_str = row.get("time", "")

            # 解析 JSON 数组（SQLite 返回 JSON 字符串）
            total_values = LatencyMetricsSampler._parse_json_array(row.get("total_latency_values"))
            urma_values = LatencyMetricsSampler._parse_json_array(row.get("urma_total_latency_values"))
            worker_values = LatencyMetricsSampler._parse_json_array(row.get("worker_query_meta_latency_values"))

            sampled.append({
                "time": time_str,
                "total_latency": LatencyMetricsSampler._aggregate_values(total_values, sample_mode),
                "urma_total_latency": LatencyMetricsSampler._aggregate_values(urma_values, sample_mode),
                "worker_query_meta_latency": LatencyMetricsSampler._aggregate_values(worker_values, sample_mode),
            })

        # 计算窗口大小（估算）
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
        """解析 SQLite JSON_GROUP_ARRAY 返回的 JSON 字符串为数值列表"""
        if not json_str or json_str == "[]":
            return []
        try:
            raw = json.loads(json_str)
            # 过滤 None/NaN 值，保留原始精度
            return [float(v) for v in raw if v is not None]
        except (json.JSONDecodeError, TypeError, ValueError):
            return []

    @staticmethod
    def _parse_timestamp_to_ms(timestamp_str: str) -> Optional[int]:
        """将时间戳字符串转换为毫秒数
        
        优先使用手动字符串解析（比 strptime 快 5-10 倍），
        回退到 strptime 以支持非标准格式。
        """
        # 尝试数字格式（最快路径）
        try:
            return int(float(timestamp_str))
        except (ValueError, TypeError):
            pass

        # 手动解析固定格式 "YYYY-MM-DD HH:MM:SS.fff" 或 "YYYY-MM-DD HH:MM:SS"
        # 这比 datetime.strptime 快 5-10 倍
        try:
            length = len(timestamp_str)
            if length >= 19:
                # "2024-01-15 08:30:45.123" 或 "2024-01-15T08:30:45.123"
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

        # 回退到 strptime 处理其他格式
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
        """聚合单个字段的值列表"""
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
        """从聚合后的数值构建采样项（返回 dict）"""
        # 计算中间时间戳
        if len(timestamps) == 1:
            mid_ts = float(timestamps[0])
        else:
            mid_ts = timestamps[0] + (timestamps[-1] - timestamps[0]) / 2

        mid_time = LatencyMetricsSampler._ms_to_timestamp(mid_ts)

        return {
            "time": mid_time,
            "total_latency": LatencyMetricsSampler._aggregate_values(values[0], mode),
            "urma_total_latency": LatencyMetricsSampler._aggregate_values(values[1], mode),
            "worker_query_meta_latency": LatencyMetricsSampler._aggregate_values(values[2], mode),
        }

    @staticmethod
    def _ms_to_timestamp(ms: float) -> str:
        """将毫秒数转换为时间戳字符串"""
        dt = datetime.fromtimestamp(ms / 1000)
        return dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
