from latency.task.worker.kv_cache_log_event_diagnosis_worker import (
    KVCacheLogEventDiagnosisWorker,
)
from latency.task.worker.kv_cache_log_parse_worker import (
    KVCacheLogParseWorker,
    MIXED_ROTATED_GZ_PATTERN,
)


def test_split_unmatched_log_files(tmp_path):
    matched = tmp_path / "access.log"
    unmatched = tmp_path / "abcd.log"
    runtime_line = " | ".join(str(i) for i in range(8)) + "\n"
    access_line_12 = " | ".join(str(i) for i in range(13)) + "\n"
    access_line_13 = " | ".join(str(i) for i in range(14)) + "\n"
    matched.write_text(runtime_line, encoding="utf-8")
    unmatched.write_text(
        runtime_line + access_line_12 + "unknown\n" + access_line_13,
        encoding="utf-8",
    )

    stats = KVCacheLogEventDiagnosisWorker.split_unmatched_log_files(
        str(tmp_path),
        {"ds_worker_access_log_file": ["access.log"]},
    )

    assert stats == {str(unmatched): (1, 2)}
    assert (tmp_path / "abcd_runtime.log").read_text(encoding="utf-8") == runtime_line
    assert (tmp_path / "abcd_access.log").read_text(
        encoding="utf-8"
    ) == access_line_12 + access_line_13
    assert not (tmp_path / "access_runtime.log").exists()
    assert not unmatched.exists()


def test_split_unmatched_rotated_log_file(tmp_path):
    unmatched = tmp_path / "abcd.log_yyy"
    runtime_line = " | ".join(str(i) for i in range(8)) + "\n"
    access_line = " | ".join(str(i) for i in range(13)) + "\n"
    unmatched.write_text(runtime_line + access_line, encoding="utf-8")

    stats = KVCacheLogEventDiagnosisWorker.split_unmatched_log_files(
        str(tmp_path),
        {"ds_worker_access_log_file": ["access.log"]},
    )

    assert stats == {str(unmatched): (1, 1)}
    assert (
        tmp_path / "abcd.log_yyy_runtime.log"
    ).read_text(encoding="utf-8") == runtime_line
    assert (
        tmp_path / "abcd.log_yyy_access.log"
    ).read_text(encoding="utf-8") == access_line
    assert not unmatched.exists()


def test_latency_parser_derives_gzip_patterns():
    patterns = KVCacheLogParseWorker._include_gzip_patterns(
        ["access.log", "*_access.log", "access.log.gz"]
    )

    assert patterns == [
        "access.log",
        "access.log.gz",
        "*_access.log",
        "*_access.log.gz",
        MIXED_ROTATED_GZ_PATTERN,
    ]
    assert KVCacheLogParseWorker._include_gzip_patterns(patterns) == patterns
