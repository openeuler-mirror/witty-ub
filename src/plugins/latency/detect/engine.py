from __future__ import annotations

from datetime import datetime
from operator import attrgetter
from typing import List

from latency.config.config import Config
from latency.schemas.detect import DetectionResult, MetricConfig, WindowConfig
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
        """按指标执行检测，同一指标的多个窗口共享一次字段提取。"""
        if not self.detectors:
            return []

        detectors_by_field: dict[str, list[DetectorBase]] = {}
        for detector in self.detectors:
            field_name = detector.config.field_name
            detectors_by_field.setdefault(field_name, []).append(detector)

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
        for field_name, detectors in detectors_by_field.items():
            if all_sparse and field_name not in sparse_slots:
                detection_results.extend(
                    DetectionResult(
                        metric_name=field_name,
                        anomalous_indices=[],
                        reasons={},
                    )
                    for _ in detectors
                )
                continue
            values = list(map(attrgetter(field_name), results))
            thresholds = {detector.config.threshold_ms for detector in detectors}
            values_complete = None not in values
            exceeded_by_threshold = {
                threshold: [
                    idx
                    for idx, value in enumerate(values)
                    if value is not None and value > threshold
                ]
                for threshold in thresholds
            }

            for detector in detectors:
                detection_results.append(
                    await detector.detect(
                        results,
                        values,
                        values_complete,
                        exceeded_by_threshold[detector.config.threshold_ms],
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
            if r.is_anomalous and r.anomaly_reason:
                extra_reasons.append(r.anomaly_reason)
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
        """从配置文件创建检测器"""

        cfg = analyzer_config or Config().get_config().log_analyzer_params

        # 获取窗口配置（多窗口模式）
        window_sizes = cfg.sliding_window_sizes
        window_steps = cfg.sliding_window_steps

        # 确保窗口大小和步长数量匹配
        if len(window_steps) < len(window_sizes):
            window_steps = window_steps + [window_steps[-1]] * (len(window_sizes) - len(window_steps))

        # 指标配置映射（固定指标列表）
        metrics_config = [
            {"field_name": "total_latency", "threshold_attr": "total_p99_threshold_ms", "mode": DetectionMode.SLIDING_WINDOW_P99},
            {"field_name": "c2w_latency", "threshold_attr": "c2w_p99_threshold_ms", "mode": DetectionMode.SLIDING_WINDOW_P99},
            {"field_name": "w2w_urma_latency", "threshold_attr": "w2w_p99_threshold_ms", "mode": DetectionMode.SLIDING_WINDOW_P99},
            {"field_name": "urma_link_latency", "threshold_attr": "urma_link_p99_threshold_ms", "mode": DetectionMode.SLIDING_WINDOW_P99},
            {"field_name": "worker_query_meta_latency", "threshold_attr": "query_meta_p99_threshold_ms", "mode": DetectionMode.THRESHOLD_DIRECT},
        ]

        # 构建各指标的配置（每个指标 × 每个窗口大小）
        metric_configs = []

        for metric in metrics_config:
            field_name = metric["field_name"]
            threshold_ms = getattr(cfg, metric["threshold_attr"])
            mode = metric["mode"]

            # 直接阈值检测不需要窗口配置
            if mode == DetectionMode.THRESHOLD_DIRECT:
                metric_configs.append(MetricConfig(
                    field_name=field_name,
                    threshold_ms=threshold_ms,
                    mode=mode
                ))
                continue

            # 滑动窗口检测：为每个窗口大小创建一个检测器
            for win_size, win_step in zip(window_sizes, window_steps):
                metric_configs.append(MetricConfig(
                    field_name=field_name,
                    threshold_ms=threshold_ms,
                    window_config=WindowConfig(
                        window_size=win_size,
                        window_step=win_step,
                        density_threshold=cfg.zone_anomaly_density_threshold
                    ),
                    mode=mode
                ))

        return cls(metric_configs)

    async def detect(
        self, results: List[LogParseResultModel]
    ) -> List[AnomalousEventDataclass]:
        """执行检测流程"""
        detection_results = await self.engine.run_parallel(results)
        events = self.engine.merge_results(detection_results, results)
        return events
