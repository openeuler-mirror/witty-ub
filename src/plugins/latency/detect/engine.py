from __future__ import annotations

from datetime import datetime
from operator import attrgetter
from typing import List

from latency.config.config import Config
from latency.schemas.detect import DetectionResult, MetricConfig
from latency.schemas.log import (
    AnomalousEventDataclass,
    LogParseResultModel,
    SparseLogParseResultDataclass,
)
from latency.detect.detectors import DetectorBase, get_detector
from latency.ENUM.detect import DetectionMode
from latency.schemas.config import DSLogAnalyzerConfig

class DetectionEngine:
    """检测引擎 - 协调多个检测器并行执行"""

    def __init__(self, metric_configs: List[MetricConfig]):
        self.detectors: List[DetectorBase] = []
        for cfg in metric_configs:
            if not cfg.enabled:
                continue
            try:
                detector = get_detector(cfg.mode, cfg)
                self.detectors.append(detector)
            except ValueError as e:
                from latency.common.logger import logger
                logger.warning(f"Failed to create detector for mode {cfg.mode}: {e}")

    async def run_parallel(self, results: List[LogParseResultModel]) -> List[DetectionResult]:
        """按指标执行检测，每个指标使用直接阈值判断。"""
        if not self.detectors:
            return []

        sparse_hint = getattr(results, "all_sparse", None)
        all_sparse = (
            sparse_hint
            if sparse_hint is not None
            else bool(results)
            and all(
                type(result) is SparseLogParseResultDataclass
                for result in results
            )
        )
        sparse_slots = SparseLogParseResultDataclass.__slots__

        detection_results: List[DetectionResult] = []
        for detector in self.detectors:
            field_name = detector.config.field_name
            threshold_ms = detector.config.threshold_ms

            if all_sparse and field_name not in sparse_slots:
                detection_results.append(
                    DetectionResult(
                        metric_name=field_name,
                        anomalous_indices=[],
                        reasons={},
                    )
                )
                continue

            values = list(map(attrgetter(field_name), results))
            exceeded_indices = [
                idx
                for idx, value in enumerate(values)
                if value is not None and value > threshold_ms
            ]

            detection_results.append(
                await detector.detect(
                    results,
                    values,
                    None not in values,
                    exceeded_indices,
                )
            )
        return detection_results

    def merge_results(
        self,
        detection_results: List[DetectionResult],
        original_results: List[LogParseResultModel]
    ) -> List[AnomalousEventDataclass]:
        """合并多个检测器结果，去重并聚合原因，同时补充额外异常检查"""
        merged_reasons: dict[int, dict[str, None]] = {}

        for result in detection_results:
            for idx in result.anomalous_indices:
                target_reasons = merged_reasons.setdefault(idx, {})
                for reason in result.reasons.get(idx, []):
                    target_reasons[reason] = None

        events = []
        shared_created_at = datetime.now().isoformat(
            sep=" ", timespec="milliseconds"
        )
        for idx, reasons in merged_reasons.items():
            # 补充额外的异常原因检查
            r = original_results[idx]
            extra_reasons = []
            if r.c2w_latency is not None and r.c2w_latency < 0:
                extra_reasons.append("Client2WorkerTime(us) < 0")
            if r.c2w_urma_latency is not None:
                extra_reasons.append(f"c2w_urma_latency={r.c2w_urma_latency:.3f}ms (remote URMA path)")

            all_reasons = extra_reasons + list(reasons)

            events.append(AnomalousEventDataclass(
                id="",
                log_id=r.log_id or "",
                aggregated_event_id="",
                start_log_parse_offset=idx,
                end_log_parse_offset=idx,
                anomaly_reason="; ".join(all_reasons),
                existed_status=True,
                created_at=shared_created_at,
            ))

        return events


class AnomalyDetector:
    """异常检测主入口"""

    def __init__(self, configs: List[MetricConfig]):
        self.engine = DetectionEngine(configs)

    @classmethod
    def from_config(
        cls, analyzer_config: DSLogAnalyzerConfig | None = None
    ) -> "AnomalyDetector":
        """从配置文件创建检测器（全部使用直接阈值判断）"""

        cfg = analyzer_config or Config().get_config().log_analyzer_params

        # 指标配置映射（固定指标列表，全部使用直接阈值检测）
        metrics_config = [
            {"field_name": "total_latency", "threshold_attr": "total_p99_threshold_ms"},
            {"field_name": "c2w_latency", "threshold_attr": "c2w_p99_threshold_ms"},
            {"field_name": "w2w_urma_latency", "threshold_attr": "w2w_p99_threshold_ms"},
            {"field_name": "urma_link_latency", "threshold_attr": "urma_link_p99_threshold_ms"},
            {"field_name": "worker_query_meta_latency", "threshold_attr": "query_meta_p99_threshold_ms"},
        ]

        # 每个指标创建一个直接阈值检测器
        metric_configs = [
            MetricConfig(
                field_name=metric["field_name"],
                threshold_ms=getattr(cfg, metric["threshold_attr"]),
                mode=DetectionMode.THRESHOLD_DIRECT,
            )
            for metric in metrics_config
        ]

        return cls(metric_configs)

    async def detect(
        self, results: List[LogParseResultModel]
    ) -> List[AnomalousEventDataclass]:
        """执行检测流程"""
        detection_results = await self.engine.run_parallel(results)
        events = self.engine.merge_results(detection_results, results)
        return events
