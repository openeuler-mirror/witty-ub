# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.

from latency.schemas.log import LatencyMetricItem
from latency.ENUM.sampling import SampleMode
from datetime import datetime
from typing import Tuple, List, Dict, Any


class LatencyMetricsSampler:
    """延迟指标采样器
    
    用于对时间序列延迟指标数据进行采样，减少前端渲染压力，同时保留关键特征。
    支持多种采样模式：最大值、最小值、平均值、百分位等。
    """
    
    @staticmethod
    def sample(
        metrics: List[LatencyMetricItem],
        max_points: int,
        sample_mode: SampleMode
    ) -> Tuple[List[LatencyMetricItem], Dict[str, Any]]:
        """对时间序列数据进行采样
        
        Args:
            metrics: 原始数据点列表（已按时间排序）
            max_points: 最大返回点数
            sample_mode: 采样模式
        
        Returns:
            (采样后数据，采样信息字典)
                - 采样后数据：List[LatencyMetricItem]
                - 采样信息：{
                    "mode": 采样模式,
                    "window_ms": 窗口大小 (毫秒),
                    "original_count": 原始数据点数,
                    "sampled_count": 采样后数据点数
                }
        """
        if len(metrics) <= max_points or max_points == -1:
            return metrics, {
                "mode": "none",
                "window_ms": 0,
                "original_count": len(metrics),
                "sampled_count": len(metrics)
            }
        
        metrics_with_ts = []
        for item in metrics:
            ts_ms = LatencyMetricsSampler._parse_timestamp_to_ms(item.time)
            if ts_ms is not None:
                metrics_with_ts.append((ts_ms, item))
        
        if not metrics_with_ts:
            return [], {
                "mode": sample_mode.value,
                "window_ms": 0,
                "original_count": len(metrics),
                "sampled_count": 0
            }
        
        metrics_with_ts.sort(key=lambda x: x[0])
        
        start_ts = metrics_with_ts[0][0]
        end_ts = metrics_with_ts[-1][0]
        time_span_ms = end_ts - start_ts
        
        if time_span_ms <= 0:
            return [metrics_with_ts[0][1]], {
                "mode": sample_mode.value,
                "window_ms": 0,
                "original_count": len(metrics),
                "sampled_count": 1
            }
        
        window_ms = time_span_ms / max_points
        
        sampled = []
        current_window = []
        window_start = start_ts
        
        for ts_ms, item in metrics_with_ts:
            if ts_ms < window_start + window_ms:
                current_window.append(item)
            else:
                if current_window:
                    sampled.append(
                        LatencyMetricsSampler._aggregate_window(current_window, sample_mode)
                    )
                current_window = [item]
                window_start = ts_ms
        
        if current_window:
            sampled.append(
                LatencyMetricsSampler._aggregate_window(current_window, sample_mode)
            )
        
        return sampled, {
            "mode": sample_mode.value,
            "window_ms": round(window_ms, 2),
            "original_count": len(metrics),
            "sampled_count": len(sampled)
        }
    
    @staticmethod
    def _parse_timestamp_to_ms(timestamp_str: str) -> int:
        """将时间戳字符串转换为毫秒数"""
        formats = [
            "%Y-%m-%d %H:%M:%S.%f",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S",
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(timestamp_str, fmt)
                return int(dt.timestamp() * 1000)
            except ValueError:
                continue
        
        try:
            return int(float(timestamp_str))
        except (ValueError, TypeError):
            return None
    
    @staticmethod
    def _aggregate_window(
        items: List[LatencyMetricItem],
        mode: SampleMode
    ) -> LatencyMetricItem:
        """聚合单个时间窗口内的数据点"""
        if not items:
            raise ValueError("窗口内无数据")
        
        if len(items) == 1:
            return items[0]
        
        timestamps = []
        for item in items:
            ts_ms = LatencyMetricsSampler._parse_timestamp_to_ms(item.time)
            if ts_ms is not None:
                timestamps.append(ts_ms)
        
        if timestamps:
            mid_ts = timestamps[0] + (timestamps[-1] - timestamps[0]) / 2
            mid_time = LatencyMetricsSampler._ms_to_timestamp(mid_ts)
        else:
            mid_time = items[0].time
        
        def aggregate_field(field_name: str):
            values = [
                getattr(item, field_name)
                for item in items
                if getattr(item, field_name) is not None
            ]
            if not values:
                return None
            
            if mode == SampleMode.MAX:
                return max(values)
            elif mode == SampleMode.MIN:
                return min(values)
            elif mode == SampleMode.AVG:
                return sum(values) / len(values)
            elif mode in (SampleMode.P99, SampleMode.P95):
                values.sort()
                percentile = 0.99 if mode == SampleMode.P99 else 0.95
                index = max(0, int(len(values) * percentile) - 1)
                return values[index]
            else:
                return max(values)
        
        return LatencyMetricItem(
            time=mid_time,
            total_latency=aggregate_field("total_latency"),
            urma_total_latency=aggregate_field("urma_total_latency"),
            worker_query_meta_latency=aggregate_field("worker_query_meta_latency")
        )
    
    @staticmethod
    def _ms_to_timestamp(ms: float) -> str:
        """将毫秒数转换为时间戳字符串"""
        dt = datetime.fromtimestamp(ms / 1000)
        return dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
