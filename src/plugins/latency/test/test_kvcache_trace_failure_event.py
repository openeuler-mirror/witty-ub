from types import SimpleNamespace

from latency.task.worker.kv_cache_log_event_diagnosis_worker import (
    KVCacheLogEventDiagnosisWorker,
)


def _log_event(*, failure_modes: list[str], status_code: str = "raw-status") -> dict:
    return {
        "log_id": "log-1",
        "trace_id": "trace-1",
        "pod_name": "pod-1",
        "host_name": "host-1",
        "cluster_name": "cluster-1",
        "timestamp": "2026-08-29 10:00:00",
        "status_code": status_code,
        "failure_mode": failure_modes,
        "raw_text": "",
    }


def test_trace_failure_codes_come_only_from_access_log_failure_modes():
    failure_mode_cache = {
        "access": SimpleNamespace(
            children_failure_mode_ids="runtime", error_code="K_ACCESS(7)"
        ),
        "runtime": SimpleNamespace(children_failure_mode_ids="", error_code="K_RUNTIME(5)"),
        "other": SimpleNamespace(children_failure_mode_ids="", error_code=None),
    }
    events: dict[str, dict] = {}

    KVCacheLogEventDiagnosisWorker._merge_trace_failure_event(
        events,
        _log_event(failure_modes=["access"], status_code="7"),
        failure_mode_cache,
    )
    KVCacheLogEventDiagnosisWorker._merge_trace_failure_event(
        events,
        _log_event(failure_modes=["runtime", "other"], status_code=""),
        failure_mode_cache,
    )

    # Runtime leaf pruning still controls trace detail modes, but aggregate
    # codes retain their independent access-log attribution.
    assert events["trace-1"]["failure_mode"] == ["runtime", "other"]
    assert events["trace-1"]["status_code"] == ["7"]


def test_runtime_only_trace_has_no_aggregate_failure_codes():
    failure_mode_cache = {
        "runtime": SimpleNamespace(
            children_failure_mode_ids="", error_code="K_RUNTIME(5)"
        ),
    }
    events: dict[str, dict] = {}

    KVCacheLogEventDiagnosisWorker._merge_trace_failure_event(
        events,
        _log_event(failure_modes=["runtime"], status_code=""),
        failure_mode_cache,
    )

    assert events["trace-1"]["failure_mode"] == ["runtime"]
    assert events["trace-1"]["status_code"] == []


def test_failure_mode_error_codes_ignore_missing_and_duplicate_codes():
    failure_mode_cache = {
        "first": SimpleNamespace(error_code="K_SAME(1004)"),
        "second": SimpleNamespace(error_code="K_SAME_ALIAS(1004)"),
        "empty": SimpleNamespace(error_code="NULL"),
    }

    assert KVCacheLogEventDiagnosisWorker._failure_mode_error_codes(
        ["first", "unknown", "second", "empty"], failure_mode_cache
    ) == ["1004"]


def test_zero_code_requires_a_failure_mode_with_zero_error_code():
    failure_mode_cache = {
        "kvcache_access_034": SimpleNamespace(error_code="K_OK(0)"),
        "runtime_without_code": SimpleNamespace(error_code=None),
        "runtime_with_raw_zero": SimpleNamespace(error_code="0"),
        "runtime_with_raw_nonzero": SimpleNamespace(error_code="-1"),
        "runtime_with_nullptr": SimpleNamespace(error_code="nullptr"),
        "runtime_with_other_zero": SimpleNamespace(error_code="URMA_OK(0)"),
    }

    assert KVCacheLogEventDiagnosisWorker._failure_mode_error_codes(
        [
            "runtime_without_code",
            "runtime_with_raw_zero",
            "runtime_with_raw_nonzero",
            "runtime_with_nullptr",
            "runtime_with_other_zero",
        ],
        failure_mode_cache,
    ) == []
    assert KVCacheLogEventDiagnosisWorker._failure_mode_error_codes(
        ["kvcache_access_034"], failure_mode_cache
    ) == ["0"]
