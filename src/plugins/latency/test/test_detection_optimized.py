import asyncio
from dataclasses import asdict

from latency.ENUM.detect import DetectionMode
from latency.common.stats import (
    percentile,
    percentile_from_sorted,
    stats,
)
from latency.database.managers import anomalous_event as anomalous_event_module
from latency.database.managers import (
    src_dst_aggregated_event as aggregated_event_module,
)
from latency.database.managers.anomalous_event import _anomalous_event_to_db_tuple
from latency.database.managers.anomalous_event import AnomalousEventManager
from latency.database.managers.src_dst_aggregated_event import (
    SrcDstAggregatedEventManager,
    _aggregated_event_to_db_tuple,
)
from latency.detect.detectors import SlidingWindowP99Detector
from latency.detect.engine import DetectionEngine
from latency.schemas.detect import DetectionResult, MetricConfig, WindowConfig
from latency.schemas.log import (
    AnomalousEventDataclass,
    LogParseResultDataclass,
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


class FakeAsyncLock:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False


class FakeConnection:
    def __init__(self) -> None:
        self.insert_sql = ""
        self.params = []

    def execute(self, sql):
        return None

    def executemany(self, sql, params):
        self.insert_sql = sql
        self.params.extend(params)

    def commit(self):
        return None

    def rollback(self):
        return None


class FakeDatabase:
    def __init__(self) -> None:
        self._async_lock = FakeAsyncLock()
        self._conn = FakeConnection()


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
    }
def test_windows_for_same_metric_share_field_extraction() -> None:
    configs = [
        MetricConfig(
            field_name="latency",
            threshold_ms=1000.0,
            mode=DetectionMode.SLIDING_WINDOW_P99,
            window_config=WindowConfig(window_size=size, window_step=2),
        )
        for size in (4, 8)
    ]
    results = [CountingResult(float(index)) for index in range(20)]
    CountingResult.field_reads = 0

    detected = asyncio.run(DetectionEngine(configs).run_parallel(results))

    assert len(detected) == 2
    assert CountingResult.field_reads == len(results)
    assert all(not result.anomalous_indices for result in detected)


def test_sliding_window_complete_hint_preserves_detection_result() -> None:
    config = MetricConfig(
        field_name="latency",
        threshold_ms=10.0,
        mode=DetectionMode.SLIDING_WINDOW_P99,
        window_config=WindowConfig(
            window_size=4,
            window_step=1,
            density_threshold=0.5,
        ),
    )
    detector = SlidingWindowP99Detector(config)
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
    assert hinted.anomalous_indices


def test_sliding_window_incomplete_values_keep_none_filtering() -> None:
    config = MetricConfig(
        field_name="latency",
        threshold_ms=10.0,
        mode=DetectionMode.SLIDING_WINDOW_P99,
        window_config=WindowConfig(window_size=4, window_step=1),
    )
    detector = SlidingWindowP99Detector(config)
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

    aggregates, id_map = asyncio.run(
        KVCacheLogParseWorker.generate_aggregate_result(results)
    )

    assert len(aggregates) == 1
    aggregate = aggregates[0]
    assert isinstance(aggregate, SrcDstAggregatedEventDataclass)
    assert id_map[("10.0.0.1", "10.0.0.2")] == aggregate.id
    assert aggregate.ave_total_latency == 3.0
    assert aggregate.min_total_latency == 1.0
    assert aggregate.max_total_latency == 5.0
    assert aggregate.p95_total_latency == percentile([1.0, 3.0, 5.0], 95)
    assert aggregate.p99_total_latency == percentile([1.0, 3.0, 5.0], 99)


def test_internal_dataclasses_convert_directly_to_database_tuples() -> None:
    anomaly = AnomalousEventDataclass(
        id="anomaly-id",
        log_id="log-id",
        start_log_parse_offset=1,
        end_log_parse_offset=2,
        anomaly_reason="slow",
        created_at="created-at",
    )
    aggregate = SrcDstAggregatedEventDataclass(
        id="aggregate-id",
        src_ip="10.0.0.1",
        dst_ip="10.0.0.2",
        log_id="log-id",
        ave_total_latency=3.0,
        created_at="created-at",
    )

    assert _anomalous_event_to_db_tuple(anomaly) == (
        "anomaly-id",
        "log-id",
        "",
        1,
        2,
        "slow",
        True,
        "created-at",
    )
    aggregate_tuple = _aggregated_event_to_db_tuple(aggregate)
    assert len(aggregate_tuple) == 39
    assert aggregate_tuple[:8] == (
        "aggregate-id",
        "10.0.0.1",
        "10.0.0.2",
        "log-id",
        0,
        0,
        0,
        3.0,
    )


def test_dataclass_batch_managers_use_positional_sql(monkeypatch) -> None:
    anomaly = AnomalousEventDataclass(id="anomaly-id", log_id="log-id")
    aggregate = SrcDstAggregatedEventDataclass(
        id="aggregate-id",
        src_ip="10.0.0.1",
        dst_ip="10.0.0.2",
        log_id="log-id",
    )

    anomaly_db = FakeDatabase()
    monkeypatch.setattr(
        anomalous_event_module, "AsyncSQLiteSingleton", lambda: anomaly_db
    )
    anomaly_ids = asyncio.run(
        AnomalousEventManager.add_anomalous_events([anomaly])
    )
    assert anomaly_ids == ["anomaly-id"]
    assert anomaly_db._conn.insert_sql.count("?") == 8
    assert anomaly_db._conn.params == [_anomalous_event_to_db_tuple(anomaly)]

    aggregate_db = FakeDatabase()
    monkeypatch.setattr(
        aggregated_event_module, "AsyncSQLiteSingleton", lambda: aggregate_db
    )
    aggregate_ids = asyncio.run(
        SrcDstAggregatedEventManager.add_aggregated_events([aggregate])
    )
    assert aggregate_ids == ["aggregate-id"]
    assert aggregate_db._conn.insert_sql.count("?") == 39
    assert aggregate_db._conn.params == [_aggregated_event_to_db_tuple(aggregate)]
