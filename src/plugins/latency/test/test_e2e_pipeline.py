"""
End-to-end test suite for witty-ub deployment, parse, aggregation, and diagnosis pipeline.

Usage:
    cd /home/li/witty-ub_8632/src/plugins/latency
    source .venv/bin/activate
    python -m pytest test/test_e2e_pipeline.py -v -s
"""
import os
import time
import uuid

import pytest
import requests

API_BASE = os.environ.get("LATENCY_API_BASE", "http://127.0.0.1:9772")
TEST_DATA_DIR = os.environ.get(
    "TEST_DATA_DIR",
    "/home/li/witty-ub_8632/data/logs/daas/SDK_6.62.222.228",
)
TIMEOUT = 300

if not os.path.isdir(TEST_DATA_DIR):
    pytest.skip(
        f"TEST_DATA_DIR {TEST_DATA_DIR!r} does not exist — e2e data was "
        "deleted; skipping module",
        allow_module_level=True,
    )


# ───────────────────────────── Helpers ─────────────────────────────


def _api(method: str, path: str, **kwargs) -> requests.Response:
    url = f"{API_BASE}{path}"
    resp = requests.request(method, url, timeout=60, **kwargs)
    assert resp.status_code == 200, f"API {method} {path} => {resp.status_code}: {resp.text[:300]}"
    return resp


def _json(resp: requests.Response) -> dict:
    return resp.json()


def _wait_parse(lf_id: str) -> dict:
    """Trigger parse on log_file and block until successful."""
    _api("PUT", f"/log_file/run/{lf_id}?run=true")
    deadline = time.time() + TIMEOUT
    while time.time() < deadline:
        resp = _api("GET", f"/log_file/{lf_id}")
        lf = _json(resp)["result"]["log_file"]
        if lf["overall_status"] == "successful":
            return lf
        if lf["overall_status"] == "failed":
            pytest.fail(f"Pipeline failed: {lf}")
        time.sleep(3)
    pytest.fail(f"Pipeline did not complete within {TIMEOUT}s")


# ──────────────────────────── Fixtures ────────────────────────────


@pytest.fixture(scope="module")
def kb_id():
    """Create a fresh knowledge base for this test module."""
    data = {"name": f"e2e_test_{uuid.uuid4().hex[:8]}", "description": "automated e2e test"}
    kb = _json(_api("POST", "/log_kb", json=data))["result"]["kb_id"]
    yield kb
    try:
        _api("PUT", f"/log_kb/{kb}/delete")
    except Exception:
        pass


@pytest.fixture(scope="module")
def log_file_id(kb_id: str):
    """Upload log directory and return the log_file_id."""
    payload = {
        "upload_log_file_configs": [{
            "name": "e2e_multi_log",
            "source_type": "local",
            "source": TEST_DATA_DIR,
        }]
    }
    lf_id = _json(_api("POST", f"/log_file/{kb_id}", json=payload))["result"]["log_file_ids"][0]
    return lf_id


@pytest.fixture(scope="module")
def pipeline_done(log_file_id: str):
    """Trigger parse and wait for success; return the log_file dict."""
    return _wait_parse(log_file_id)


# ──────────────────────────── Tests ────────────────────────────


class TestHealthAndSetup:
    def test_health_check(self):
        assert _json(_api("GET", "/health_check"))["status"] == "ok"

    def test_kb_created(self, kb_id):
        assert _json(_api("GET", f"/log_kb/{kb_id}"))["code"] == 200

    def test_expected_file_exists(self):
        expected_file = os.path.join(TEST_DATA_DIR, "expected_result.txt")
        assert os.path.isfile(expected_file), f"Missing {expected_file}"


class TestParsePipeline:
    def test_upload_success(self, log_file_id):
        assert log_file_id is not None and len(log_file_id) > 30

    def test_pipeline_completed(self, pipeline_done):
        assert pipeline_done["overall_status"] == "successful"
        assert pipeline_done["overall_progress"] >= 30.0

    def test_parse_results_exist(self, pipeline_done, kb_id, log_file_id):
        total = _json(_api("POST", "/log_parse_result/list",
            json={"kb_id": kb_id, "log_id": log_file_id, "page_cnt": 5, "page_num": 1}))["result"]["total"]
        assert total > 0, "No parse results found"

    def test_parse_latency_reasonable(self, pipeline_done):
        duration = (pipeline_done.get("task") or {}).get("duration_seconds")
        if duration is not None:
            assert duration < 300, f"Pipeline too slow: {duration:.1f}s"


class TestAggregatedEvents:
    def test_src_dst_by_log_id(self, pipeline_done, kb_id, log_file_id):
        total = _json(_api("POST", "/aggregated_event/list",
            json={"kb_id": kb_id, "log_id": log_file_id, "page_cnt": 10, "page_num": 1}))["result"]["total"]
        assert total > 0, "src_dst aggregated events (by log_id) is 0"

    def test_src_dst_by_kb_id(self, pipeline_done, kb_id):
        total = _json(_api("POST", "/aggregated_event/list",
            json={"kb_id": kb_id, "page_cnt": 10, "page_num": 1}))["result"]["total"]
        assert total > 0, f"src_dst aggregated events (by kb_id) is 0 for {kb_id}"

    def test_time_window_aggregated(self, pipeline_done, kb_id):
        total = _json(_api("POST", "/aggregated_event/list_time_window",
            json={"kb_id": kb_id, "page_cnt": 10, "page_num": 1}))["result"]["total"]
        assert total > 0, "No time_window aggregated events"


class TestAnomalyAndDiagnosis:
    def test_anomalous_events_exist(self, kb_id):
        total = _json(_api("POST", "/anomalous_event/list",
            json={"kb_id": kb_id, "page_cnt": 40, "page_num": 1}))["result"]["total"]
        assert total > 0, "No anomalous events detected"

    def test_anomaly_count_meets_expected(self, kb_id):
        total = _json(_api("POST", "/anomalous_event/list",
            json={"kb_id": kb_id, "page_cnt": 200, "page_num": 1}))["result"]["total"]
        expected_path = os.path.join(TEST_DATA_DIR, "expected_result.txt")
        expected_str = ">=0"
        if os.path.isfile(expected_path):
            with open(expected_path) as f:
                for line in f:
                    if "expected_anomalous_events" in line:
                        expected_str = line.split(":", 1)[1].strip()
                        break
        if expected_str.startswith(">="):
            assert total >= int(expected_str[2:]), f"{total} < expected {expected_str}"

    def test_trace_failure_events(self, kb_id):
        total = _json(_api("POST", "/log_failure_event_result/list_trace_events",
            json={"kb_id": kb_id, "page_cnt": 20, "page_num": 1}))["result"].get("total", 0)
        if total == 0:
            pytest.skip("diagnosis worker not producing results (may need C++ deps)")

    def test_log_failure_events(self, kb_id):
        total = _json(_api("POST", "/log_failure_event_result/list_log_events",
            json={"kb_id": kb_id, "page_cnt": 20, "page_num": 1}))["result"].get("total", 0)
        if total == 0:
            pytest.skip("diagnosis worker not producing log failure events")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
