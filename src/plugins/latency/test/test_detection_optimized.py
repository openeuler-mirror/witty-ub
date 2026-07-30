import asyncio
from dataclasses import asdict

from latency.ENUM.detect import DetectionMode
from latency.common.stats import (
    percentile,
    percentile_from_sorted,
    stats,
)
from latency.detect.detectors import ThresholdDirectDetector
from latency.detect.engine import DetectionEngine
from latency.schemas.detect import DetectionResult, MetricConfig
from latency.schemas.log import (
    AnomalousEventDataclass,
    LogParseResultBatch,
    LogParseResultDataclass,
    SparseLogParseResultDataclass,
    SrcDstAggregatedEventDataclass,
)
from latency.task.worker.kv_cache_log_parse_worker import KVCacheLogParseWorker


class CountingResult:
    field_reads = 0

    def __init__(self, latency: float) -> None:
        self.latency = latency

    def __getattribute__(self, name: str):
        if name == "latency":
            type(self).field_reads += 1
        return object.__getattribute__(self, name)


def test_percentiles_reuse_one_sorted_sequence() -> None:
    values = [5.0, 1.0, 9.0, 3.0, 7.0]
    sorted_values = sorted(values)

    assert percentile_from_sorted(sorted_values, 95) == percentile(values, 95)
    assert percentile_from_sorted(sorted_values, 99) == percentile(values, 99)
    assert stats(values) == {
        "ave": 5.0,
        "min": 1.0,
        "max": 9.0,
        "p95": percentile(values, 95),
        "p99": percentile(values, 99),
        "p9999": percentile(values, 99.99),
    }
def test_multiple_detectors_share_field_extraction() -> None:
    configs = [
        MetricConfig(
            field_name="latency",
            threshold_ms=1000.0,
            mode=DetectionMode.THRESHOLD_DIRECT,
        )
        for _ in range(2)
    ]
    results = [CountingResult(float(index)) for index in range(20)]
    CountingResult.field_reads = 0

    detected = asyncio.run(DetectionEngine(configs).run_parallel(results))

    assert len(detected) == 2
    assert all(not result.anomalous_indices for result in detected)


def test_all_sparse_results_skip_only_unavailable_metrics() -> None:
    configs = [
        MetricConfig(
            field_name=field_name,
            threshold_ms=threshold,
            mode=DetectionMode.THRESHOLD_DIRECT,
        )
        for field_name, threshold in (
            ("total_latency", 10.0),
            ("c2w_urma_latency", 5.0),
            ("c2w_latency", 1.0),
            ("worker_query_meta_latency", 1.0),
        )
    ]
    sparse_results = [
        SparseLogParseResultDataclass(
            total_latency=1.0,
            is_anomalous=False,
            c2w_urma_latency=None,
        ),
        SparseLogParseResultDataclass(
            total_latency=20.0,
            is_anomalous=False,
            c2w_urma_latency=7.0,
        ),
    ]
    results = LogParseResultBatch(len(sparse_results), all_sparse=True)
    results[:] = sparse_results

    detected = asyncio.run(DetectionEngine(configs).run_parallel(results))

    assert [result.metric_name for result in detected] == [
        "total_latency",
        "c2w_urma_latency",
        "c2w_latency",
        "worker_query_meta_latency",
    ]
    assert [result.anomalous_indices for result in detected] == [
        [1],
        [1],
        [],
        [],
    ]


def test_threshold_complete_hint_preserves_detection_result() -> None:
    config = MetricConfig(
        field_name="latency",
        threshold_ms=10.0,
        mode=DetectionMode.THRESHOLD_DIRECT,
    )
    detector = ThresholdDirectDetector(config)
    values = [1.0, 2.0, 20.0, 30.0, 2.0, 1.0]
    results = [CountingResult(value) for value in values]

    inferred = asyncio.run(detector.detect(results, values))
    hinted = asyncio.run(
        detector.detect(
            results,
            values,
            values_complete=True,
            exceeded_indices=[2, 3],
        )
    )

    assert hinted == inferred
    assert hinted.anomalous_indices == [2, 3]


def test_threshold_incomplete_values_keep_none_filtering() -> None:
    config = MetricConfig(
        field_name="latency",
        threshold_ms=10.0,
        mode=DetectionMode.THRESHOLD_DIRECT,
    )
    detector = ThresholdDirectDetector(config)
    values = [None, 2.0, 20.0, None, 30.0, 1.0]

    inferred = asyncio.run(detector.detect([object()] * len(values), values))
    hinted = asyncio.run(
        detector.detect(
            [object()] * len(values),
            values,
            values_complete=False,
            exceeded_indices=[2, 4],
        )
    )

    assert hinted == inferred
    assert hinted.anomalous_indices == [2, 4]


def test_merged_events_have_complete_constructed_fields() -> None:
    source = type(
        "SourceResult",
        (),
        {
            "log_id": "log-id",
            "is_anomalous": False,
            "anomaly_reason": None,
            "c2w_latency": None,
            "c2w_urma_latency": None,
        },
    )()
    detection = DetectionResult(
        metric_name="latency",
        anomalous_indices=[0],
        reasons={0: ["slow"]},
    )

    events = DetectionEngine([]).merge_results([detection], [source])

    assert len(events) == 1
    assert asdict(events[0]) == {
        "id": "",
        "log_id": "log-id",
        "aggregated_event_id": "",
        "start_log_parse_offset": 0,
        "end_log_parse_offset": 0,
        "anomaly_reason": "slow",
        "existed_status": True,
        "created_at": events[0].created_at,
    }


def test_merge_results_deduplicates_repeated_reasons() -> None:
    source = type(
        "SourceResult",
        (),
        {
            "log_id": "log-id",
            "is_anomalous": False,
            "anomaly_reason": None,
            "c2w_latency": None,
            "c2w_urma_latency": None,
        },
    )()
    duplicate = DetectionResult(
        metric_name="latency",
        anomalous_indices=[0],
        reasons={0: ["slow"]},
    )

    events = DetectionEngine([]).merge_results([duplicate, duplicate], [source])

    assert events[0].anomaly_reason == "slow"


def test_aggregate_hot_path_returns_dataclass_with_all_statistics() -> None:
    results = [
        LogParseResultDataclass(
            total_latency=value,
            is_anomalous=index == 1,
            log_id="log-id",
            src_ip="10.0.0.1",
            dst_ip="10.0.0.2",
        )
        for index, value in enumerate((1.0, 3.0, 5.0))
    ]

    aggregates, id_map, time_window_aggregates = asyncio.run(
        KVCacheLogParseWorker.generate_aggregate_result(results)
    )

    assert len(aggregates) == 1
    assert len(time_window_aggregates) == 1
    aggregate = aggregates[0]
    assert isinstance(aggregate, SrcDstAggregatedEventDataclass)
    assert id_map[("10.0.0.1", "10.0.0.2", "GET")] == aggregate.id
    assert aggregate.ave_total_latency == 3.0
    assert aggregate.min_total_latency == 1.0
    assert aggregate.max_total_latency == 5.0
    assert aggregate.p95_total_latency == percentile([1.0, 3.0, 5.0], 95)
    assert aggregate.p99_total_latency == percentile([1.0, 3.0, 5.0], 99)


def test_all_sparse_results_skip_endpoint_aggregation() -> None:
    results = [
        SparseLogParseResultDataclass(
            total_latency=float(index),
            is_anomalous=False,
        )
        for index in range(3)
    ]

    aggregates, id_map, time_window_aggregates = asyncio.run(
        KVCacheLogParseWorker.generate_aggregate_result(results)
    )

    assert aggregates == []
    assert id_map == {}
    assert time_window_aggregates == []
    assert all(result.aggregated_event_id == "" for result in results)


