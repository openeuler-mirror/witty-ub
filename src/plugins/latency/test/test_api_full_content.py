#!/usr/bin/env python3
"""
 richer API 集成测试：通过 PG Manager 预置完整 mock 数据，
 调用所有接口并校验返回内容。
"""

import asyncio
import uuid
from datetime import datetime, timezone

import pytest
import requests

from latency.config.config import Config
from latency.database.engine import PGManager
from latency.database.init import init_postgresql_database
from latency.database.managers.log_knowledge import LogKnowledgePGManager
from latency.database.managers.log_file import LogFilePGManager
from latency.database.managers.log_parse_result import LogParseResultPGManager
from latency.database.managers.src_dst_aggregated_event import (
    SrcDstAggregatedEventPGManager,
)
from latency.database.managers.time_window_aggregated_event import (
    TimeWindowAggregatedEventPGManager,
)
from latency.database.managers.anomalous_event import AnomalousEventPGManager
from latency.database.managers.anomalous_event_chain import (
    AnomalousEventChainPGManager,
)
from latency.database.managers.diagnosis_case import DiagnosisCasePGManager
from latency.database.managers.diagnosis_config import DiagnosisConfigPGManager
from latency.database.managers.log_failure_event import LogFailureEventPGManager
from latency.database.managers.failure_mode_knowledge import (
    FailureModeKnowledgePGManager,
)
from latency.schemas.log import (
    LogKnowledgeModel,
    LogFileModel,
    LogParseResultDataclass,
    SrcDstAggregatedEventDataclass,
    TimeWindowAggregatedEventDataclass,
    AnomalousEventDataclass,
    AnomalousEventChainModel,
)
from latency.schemas.diagnosis_case import DiagnosisCaseModel
from latency.schemas.failure_mode import FailureModeModel, StatusCodeKnowledgeModel
from latency.schemas.config import DiagnosisRuntimeConfig


def now_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


@pytest.fixture(scope="session")
def base_url(request):
    return request.config.getoption("--base-url", default="http://localhost:9772")


@pytest.fixture(scope="session")
def session_client():
    session = requests.Session()
    yield session
    session.close()


@pytest.fixture(scope="session")
def seeded(base_url):
    """初始化 PGManager 并写入一套完整 mock 数据，返回所有 ID。"""
    config = Config().get_config()
    PGManager.initialize(config.db.pg_dsn_url())

    async def _setup():
        await init_postgresql_database()
        return await _seed()

    async def _seed():
        kb_id = str(uuid.uuid4())
        log_id = str(uuid.uuid4())
        case_id = str(uuid.uuid4())
        event_id = str(uuid.uuid4())
        result_id = str(uuid.uuid4())
        anomaly_id = str(uuid.uuid4())
        chain_id = str(uuid.uuid4())
        failure_mode_id = f"FM-{uuid.uuid4().hex[:8]}"
        status_code = f"{uuid.uuid4().int % 9000 + 1000}"

        # 1. knowledge base
        await LogKnowledgePGManager.add_log_kb(
            LogKnowledgeModel(
                id=kb_id,
                name=f"test_kb_{kb_id[:8]}",
                description="full content test kb",
            )
        )

        # 2. log file
        await LogFilePGManager.add_log_file(
            LogFileModel(
                id=log_id,
                kb_id=kb_id,
                name="test.log",
                file_path="/tmp/test.log",
                file_size=1024,
            )
        )

        # 3. log parse result
        await LogParseResultPGManager.add_log_parse_results(
            [
                LogParseResultDataclass(
                    id=result_id,
                    log_id=log_id,
                    trace_id="trace-001",
                    timestamp=now_str(),
                    src_ip="192.168.1.1",
                    dst_ip="192.168.1.2",
                    pod_ips=["10.0.0.1"],
                    cluster_name="cluster-a",
                    host="host-a",
                    total_latency=5.0,
                    is_anomalous=True,
                    content="test content",
                    created_at=now_str(),
                )
            ]
        )

        # 4. src-dst aggregated event
        await SrcDstAggregatedEventPGManager.add_aggregated_events(
            [
                SrcDstAggregatedEventDataclass(
                    id=event_id,
                    kb_id=kb_id,
                    log_id=log_id,
                    src_ip="192.168.1.1",
                    dst_ip="192.168.1.2",
                    log_parse_result_cnt=1,
                    created_at=now_str(),
                )
            ]
        )

        # 5. time window aggregated event
        await TimeWindowAggregatedEventPGManager.add_events(
            [
                TimeWindowAggregatedEventDataclass(
                    id=str(uuid.uuid4()),
                    kb_id=kb_id,
                    log_id=log_id,
                    time_bucket=now_str(),
                    src_ip="192.168.1.1",
                    dst_ip="192.168.1.2",
                    log_parse_result_cnt=1,
                    created_at=now_str(),
                )
            ]
        )

        # 6. anomalous event
        await AnomalousEventPGManager.add_anomalous_events(
            [
                AnomalousEventDataclass(
                    id=anomaly_id,
                    log_id=log_id,
                    aggregated_event_id=event_id,
                    anomaly_reason="high latency",
                    created_at=now_str(),
                )
            ]
        )

        # 7. anomalous event chain
        await AnomalousEventChainPGManager.add_event_chains(
            [
                AnomalousEventChainModel(
                    id=chain_id,
                    log_id=log_id,
                    anomalous_event_id=anomaly_id,
                    name="chain-001",
                    created_at=now_str(),
                )
            ]
        )

        # 8. diagnosis case
        await DiagnosisCasePGManager.add_case(
            DiagnosisCaseModel(
                id=case_id,
                kb_id=kb_id,
                fault_type="latency",
                symptom_summary="P99 latency spike",
                root_cause="URMA link slow",
                recommendation="Check link",
                confidence=0.85,
                status_codes=[status_code],
                failure_mode_ids=[failure_mode_id],
                source_log_ids=[log_id],
            )
        )

        # 9. diagnosis config
        await DiagnosisConfigPGManager.upsert(
            kb_id, DiagnosisRuntimeConfig.model_validate(Config().get_diagnosis_config())
        )

        # 10. failure mode knowledge
        await FailureModeKnowledgePGManager.add_failure_mode_knowledge(
            [
                FailureModeModel(
                    id=failure_mode_id,
                    name="URMA link slow",
                    symptom="latency spike",
                    root_cause="link congestion",
                    solution="Check link",
                    failure_domain="network",
                    children_failure_mode_ids="",
                    error_code="K_LINK_SLOW(-1)",
                )
            ]
        )
        await FailureModeKnowledgePGManager.add_status_code_knowledge(
            [
                StatusCodeKnowledgeModel(
                    status_code=status_code,
                    symptom="connection timeout",
                    root_cause="network issue",
                )
            ]
        )

        # 11. log failure event / trace failure event
        await LogFailureEventPGManager.add_log_failure_event_raw(
            [
                {
                    "id": str(uuid.uuid4()),
                    "log_id": log_id,
                    "host_name": "host-a",
                    "timestamp": now_str(),
                    "status_code": status_code,
                    "failure_mode": [failure_mode_id],
                }
            ]
        )
        await LogFailureEventPGManager.add_trace_failure_event_raw(
            [
                {
                    "id": str(uuid.uuid4()),
                    "log_id": log_id,
                    "trace_id": "trace-001",
                    "timestamp": now_str(),
                    "status_code": [status_code],
                    "failure_mode": failure_mode_id,
                    "pod_names": [],
                    "host_names": [],
                    "cluster_names": [],
                }
            ]
        )

        await PGManager.close()

        return {
            "kb_id": kb_id,
            "log_id": log_id,
            "case_id": case_id,
            "event_id": event_id,
            "result_id": result_id,
            "anomaly_id": anomaly_id,
            "chain_id": chain_id,
            "failure_mode_id": failure_mode_id,
            "status_code": status_code,
        }

    return asyncio.run(_setup())


class TestHealthAndMeta:
    def test_health_check(self, base_url, session_client):
        resp = session_client.get(f"{base_url}/health_check", timeout=10)
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


class TestLogKnowledgeContent:
    def test_get_kb_content(self, base_url, session_client, seeded):
        resp = session_client.get(f"{base_url}/log_kb/{seeded['kb_id']}", timeout=10)
        data = resp.json()
        assert resp.status_code == 200
        assert data["result"]["kb"]["id"] == seeded["kb_id"]
        assert data["result"]["kb"]["name"].startswith("test_kb_")

    def test_list_kb_contains_seed(self, base_url, session_client, seeded):
        resp = session_client.post(
            f"{base_url}/log_kb/list",
            json={"page_num": 1, "page_cnt": 100},
            timeout=10,
        )
        data = resp.json()
        assert resp.status_code == 200
        kb_ids = {kb["id"] for kb in data["result"]["kbs"]}
        assert seeded["kb_id"] in kb_ids


class TestLogFileContent:
    def test_get_log_file_content(self, base_url, session_client, seeded):
        resp = session_client.get(f"{base_url}/log_file/{seeded['log_id']}", timeout=10)
        data = resp.json()
        assert resp.status_code == 200
        assert data["result"]["log_file"]["id"] == seeded["log_id"]
        assert data["result"]["log_file"]["kb_id"] == seeded["kb_id"]

    def test_list_log_files_content(self, base_url, session_client, seeded):
        resp = session_client.post(
            f"{base_url}/log_file/list/{seeded['kb_id']}",
            json={"page_num": 1, "page_cnt": 10},
            timeout=10,
        )
        data = resp.json()
        assert resp.status_code == 200
        log_ids = {lf["id"] for lf in data["result"]["log_files"]}
        assert seeded["log_id"] in log_ids


class TestLogParseResultContent:
    def test_list_results_content(self, base_url, session_client, seeded):
        resp = session_client.post(
            f"{base_url}/log_parse_result/list",
            json={"log_id": seeded["log_id"], "page_num": 1, "page_cnt": 10},
            timeout=10,
        )
        data = resp.json()
        assert resp.status_code == 200
        assert data["result"]["total"] >= 1
        assert data["result"]["log_parse_results"][0]["id"] == seeded["result_id"]

    def test_get_result_content(self, base_url, session_client, seeded):
        resp = session_client.get(
            f"{base_url}/log_parse_result/{seeded['result_id']}", timeout=10
        )
        data = resp.json()
        assert resp.status_code == 200
        assert data["result"]["log_parse_result"]["id"] == seeded["result_id"]
        assert data["result"]["log_parse_result"]["log_id"] == seeded["log_id"]

    def test_get_options_content(self, base_url, session_client, seeded):
        resp = session_client.get(
            f"{base_url}/log_parse_result/options?kb_id={seeded['kb_id']}", timeout=10
        )
        data = resp.json()
        assert resp.status_code == 200
        assert "clusters" in data["result"]
        assert "hosts" in data["result"]

    def test_list_traces_by_host_content(self, base_url, session_client, seeded):
        resp = session_client.post(
            f"{base_url}/log_parse_result/traces/host/list",
            json={"host": "10.0.0.1", "page_num": 1, "page_cnt": 10},
            timeout=10,
        )
        data = resp.json()
        assert resp.status_code == 200
        assert data["result"]["total"] >= 1

    def test_get_latency_metrics_content(self, base_url, session_client, seeded):
        resp = session_client.post(
            f"{base_url}/log_parse_result/metrics/latency",
            json={"log_id": seeded["log_id"], "max_points": 100},
            timeout=10,
        )
        data = resp.json()
        assert resp.status_code == 200
        assert "metrics" in data["result"]


class TestAggregatedEventContent:
    def test_list_src_dst_events_content(self, base_url, session_client, seeded):
        resp = session_client.post(
            f"{base_url}/aggregated_event/list",
            json={"log_id": seeded["log_id"], "page_num": 1, "page_cnt": 10},
            timeout=10,
        )
        data = resp.json()
        assert resp.status_code == 200
        assert data["result"]["total"] >= 1
        ids = {e["id"] for e in data["result"]["events"]}
        assert seeded["event_id"] in ids

    def test_get_src_dst_event_content(self, base_url, session_client, seeded):
        resp = session_client.get(
            f"{base_url}/aggregated_event/{seeded['event_id']}", timeout=10
        )
        data = resp.json()
        assert resp.status_code == 200
        assert data["result"]["event"]["id"] == seeded["event_id"]

    def test_list_time_window_content(self, base_url, session_client, seeded):
        resp = session_client.post(
            f"{base_url}/aggregated_event/list_time_window",
            json={"log_id": seeded["log_id"], "page_num": 1, "page_cnt": 10},
            timeout=10,
        )
        data = resp.json()
        assert resp.status_code == 200
        assert data["result"]["total"] >= 1


class TestAnomalousEventContent:
    def test_get_anomalous_event_content(self, base_url, session_client, seeded):
        resp = session_client.get(
            f"{base_url}/anomalous_event/{seeded['anomaly_id']}", timeout=10
        )
        data = resp.json()
        assert resp.status_code == 200
        assert data["result"]["event"]["id"] == seeded["anomaly_id"]

    def test_list_anomalous_events_content(self, base_url, session_client, seeded):
        resp = session_client.post(
            f"{base_url}/anomalous_event/list",
            json={"log_id": seeded["log_id"], "page_num": 1, "page_cnt": 10},
            timeout=10,
        )
        data = resp.json()
        assert resp.status_code == 200
        ids = {e["id"] for e in data["result"]["events"]}
        assert seeded["anomaly_id"] in ids

    def test_list_anomalous_events_by_log_id_content(
        self, base_url, session_client, seeded
    ):
        resp = session_client.get(
            f"{base_url}/anomalous_event/log/{seeded['log_id']}", timeout=10
        )
        data = resp.json()
        assert resp.status_code == 200
        ids = {e["id"] for e in data["result"]["events"]}
        assert seeded["anomaly_id"] in ids


class TestAnomalousEventChainContent:
    def test_list_chains_content(self, base_url, session_client, seeded):
        resp = session_client.post(
            f"{base_url}/anomalous_event_chain/list",
            json={"log_id": seeded["log_id"], "page_num": 1, "page_cnt": 10},
            timeout=10,
        )
        data = resp.json()
        assert resp.status_code == 200
        ids = {c["id"] for c in data["result"]["event_chains"]}
        assert seeded["chain_id"] in ids


class TestLogFailureEventResultContent:
    def test_list_log_events_content(self, base_url, session_client, seeded):
        resp = session_client.post(
            f"{base_url}/log_failure_event_result/list_log_events",
            json={"log_id": seeded["log_id"]},
            timeout=10,
        )
        data = resp.json()
        assert resp.status_code == 200
        assert data["result"]["total"] >= 1

    def test_list_trace_events_content(self, base_url, session_client, seeded):
        resp = session_client.post(
            f"{base_url}/log_failure_event_result/list_trace_events",
            json={"kb_id": seeded["kb_id"], "trace_ids": ["trace-001"]},
            timeout=10,
        )
        data = resp.json()
        assert resp.status_code == 200
        assert data["result"]["total"] >= 1

    def test_list_time_aggregated_content(self, base_url, session_client, seeded):
        resp = session_client.post(
            f"{base_url}/log_failure_event_result/list_time_aggregated_failure_events",
            json={"kb_id": seeded["kb_id"], "page_num": 1, "page_cnt": 10},
            timeout=10,
        )
        data = resp.json()
        assert resp.status_code == 200
        assert "events" in data["result"]

    def test_list_pod_aggregated_content(self, base_url, session_client, seeded):
        resp = session_client.post(
            f"{base_url}/log_failure_event_result/list_pod_aggregated_failure_events",
            json={"kb_id": seeded["kb_id"], "page_num": 1, "page_cnt": 10},
            timeout=10,
        )
        data = resp.json()
        assert resp.status_code == 200
        assert "events" in data["result"]

    def test_list_src_dst_aggregated_content(self, base_url, session_client, seeded):
        resp = session_client.post(
            f"{base_url}/log_failure_event_result/list_src_dst_aggregated_failure_events",
            json={"kb_id": seeded["kb_id"], "page_num": 1, "page_cnt": 10},
            timeout=10,
        )
        data = resp.json()
        assert resp.status_code == 200
        assert "events" in data["result"]

    def test_get_err_code_metrics_content(self, base_url, session_client, seeded):
        resp = session_client.post(
            f"{base_url}/log_failure_event_result/metrics/err_code",
            json={"kb_id": seeded["kb_id"], "err_codes": [seeded["status_code"]]},
            timeout=10,
        )
        data = resp.json()
        assert resp.status_code == 200
        assert "metrics" in data["result"]


class TestDiagnosisCaseContent:
    def test_get_case_content(self, base_url, session_client, seeded):
        resp = session_client.get(
            f"{base_url}/diagnosis_case/{seeded['case_id']}", timeout=10
        )
        data = resp.json()
        assert resp.status_code == 200
        assert data["result"]["case"]["id"] == seeded["case_id"]
        assert data["result"]["case"]["kb_id"] == seeded["kb_id"]

    def test_search_case_content(self, base_url, session_client, seeded):
        resp = session_client.post(
            f"{base_url}/diagnosis_case/search",
            json={"kb_id": seeded["kb_id"], "page_num": 1, "page_cnt": 10},
            timeout=10,
        )
        data = resp.json()
        assert resp.status_code == 200
        ids = {c["case"]["id"] for c in data["result"]["matches"]}
        assert seeded["case_id"] in ids

    def test_hit_case_content(self, base_url, session_client, seeded):
        resp = session_client.post(
            f"{base_url}/diagnosis_case/{seeded['case_id']}/hit",
            json={
                "status_codes": [seeded["status_code"]],
                "failure_mode_ids": [seeded["failure_mode_id"]],
            },
            timeout=10,
        )
        data = resp.json()
        assert resp.status_code == 200
        assert data["result"]["case"]["id"] == seeded["case_id"]


class TestFailureModeKnowledgeContent:
    def test_get_status_code_knowledge_content(self, base_url, session_client, seeded):
        resp = session_client.get(
            f"{base_url}/failure_mode/status_code/{seeded['status_code']}", timeout=10
        )
        data = resp.json()
        assert resp.status_code == 200
        assert data["result"]["status_code_info"]["status_code"] == seeded["status_code"]

    def test_get_failure_mode_content(self, base_url, session_client, seeded):
        resp = session_client.get(
            f"{base_url}/failure_mode/{seeded['failure_mode_id']}", timeout=10
        )
        data = resp.json()
        assert resp.status_code == 200
        assert data["result"]["failure_mode"]["id"] == seeded["failure_mode_id"]
        assert data["result"]["failure_mode"]["error_code"] == "K_LINK_SLOW(-1)"


class TestDiagnosisConfigContent:
    def test_get_config_content(self, base_url, session_client, seeded):
        resp = session_client.get(
            f"{base_url}/diagnosis_config/{seeded['kb_id']}",
            params={"log_type": "KVCache"},
            timeout=10,
        )
        data = resp.json()
        assert resp.status_code == 200
        assert data["result"]["log_type"] == "KVCache"
        assert "log_filename_pattern" in data["result"]["config"]

    def test_update_and_reset_config_content(self, base_url, session_client, seeded):
        # update
        put_resp = session_client.put(
            f"{base_url}/diagnosis_config/{seeded['kb_id']}",
            params={"log_type": "KVCache"},
            json={
                "log_filename_pattern": {
                    "ds_client_access_log_file": ["*.log"],
                    "ds_client_info_log_file": ["*.INFO.log"],
                    "ds_worker_access_log_file": ["access*.log"],
                    "ds_worker_info_log_file": ["*.INFO*.log"],
                    "resource_log_file": ["resource.log"],
                },
                "log_analyzer_params": {
                    "total_p99_threshold_ms": 1.0,
                    "c2w_p99_threshold_ms": 1.0,
                    "w2w_p99_threshold_ms": 1.0,
                    "urma_link_p99_threshold_ms": 1.0,
                    "query_meta_p99_threshold_ms": 1.0,
                    "total_p9999_threshold_ms": 5.0,
                    "total_pmax_threshold_ms": 5.0,
                    "total_ave_threshold_ms": 5.0,
                    "sliding_window_sizes": [100],
                    "sliding_window_steps": [20],
                    "zone_anomaly_density_threshold": 0.5,
                },
            },
            timeout=10,
        )
        assert put_resp.status_code == 200

        # reset
        reset_resp = session_client.post(
            f"{base_url}/diagnosis_config/{seeded['kb_id']}/reset",
            params={"log_type": "KVCache"},
            timeout=10,
        )
        data = reset_resp.json()
        assert reset_resp.status_code == 200
        assert "log_filename_pattern" in data["result"]["config"]


class TestTaskContent:
    def test_create_task_content(self, base_url, session_client, seeded):
        resp = session_client.post(
            f"{base_url}/task/create",
            json={
                "task_type": "store_trace_context_logs_worker",
                "op_id": seeded["log_id"],
                "kb_id": seeded["kb_id"],
            },
            timeout=10,
        )
        data = resp.json()
        assert resp.status_code == 200
        assert data["result"]["task_id"]

    def test_list_tasks_content(self, base_url, session_client, seeded):
        resp = session_client.post(
            f"{base_url}/task/list",
            json={"kb_id": seeded["kb_id"], "page_num": 1, "page_cnt": 10},
            timeout=10,
        )
        data = resp.json()
        assert resp.status_code == 200
        assert "tasks" in data["result"]
