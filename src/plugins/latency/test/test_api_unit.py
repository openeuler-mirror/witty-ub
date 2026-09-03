#!/usr/bin/env python3
"""
API 集成测试 - 覆盖所有 routers 接口
"""

import pytest
import uuid
import requests
import tempfile
import os
from typing import Any, Dict, Optional


@pytest.fixture(scope="session")
def base_url(request):
    return request.config.getoption("--base-url", default="http://localhost:9772")


@pytest.fixture(scope="session")
def session_client():
    """创建 requests Session（复用连接池）"""
    session = requests.Session()
    yield session
    session.close()


@pytest.fixture(scope="session")
def existing_kb(base_url, session_client):
    """创建一个临时知识库,所有测试共享"""
    kb_name = f"test_kb_{str(uuid.uuid4())[:8]}"
    resp = session_client.post(
        f"{base_url}/log_kb",
        json={"name": kb_name, "description": "pytest temp"},
        timeout=30
    )
    assert resp.status_code == 200, f"创建知识库失败: {resp.status_code} {resp.text}"
    
    data = resp.json()
    kb_id = data.get("result", {}).get("kb_id")
    assert kb_id, "创建知识库未返回 kb_id"
    
    yield kb_id
    
    try:
        session_client.delete(f"{base_url}/log_kb/{kb_id}", timeout=10)
    except Exception:
        pass


@pytest.fixture(scope="session")
def existing_log_file(base_url, session_client, existing_kb):
    """创建一个临时日志文件"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as f:
        f.write("test log content")
        temp_path = f.name
    
    try:
        resp = session_client.post(
            f"{base_url}/log_file/{existing_kb}",
            json={
                "upload_log_file_configs": [
                    {"name": "test_log", "source_type": "local", "source": temp_path}
                ]
            },
            timeout=30
        )
        assert resp.status_code == 200, f"上传日志失败: {resp.status_code} {resp.text}"
        
        data = resp.json()
        log_file_ids = data.get("result", {}).get("log_file_ids", [])
        assert log_file_ids, "上传日志未返回 log_file_ids"
        
        yield log_file_ids[0]
    finally:
        os.unlink(temp_path)


class TestHealthCheck:
    """健康检查"""
    
    def test_health_check(self, base_url, session_client):
        resp = session_client.get(f"{base_url}/health_check", timeout=10)
        assert resp.status_code == 200


class TestLogKnowledge:
    """日志知识库接口"""
    
    def test_create_kb(self, base_url, session_client):
        kb_name = f"test_kb_{str(uuid.uuid4())[:8]}"
        resp = session_client.post(
            f"{base_url}/log_kb",
            json={"name": kb_name, "description": "test"},
            timeout=10
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 200
        assert data["result"]["kb_id"]
    
    def test_get_kb(self, base_url, session_client, existing_kb):
        resp = session_client.get(f"{base_url}/log_kb/{existing_kb}", timeout=10)
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 200
        assert data["result"]["kb"]["id"] == existing_kb
    
    def test_get_nonexistent_kb(self, base_url, session_client):
        resp = session_client.get(f"{base_url}/log_kb/{str(uuid.uuid4())}", timeout=10)
        assert resp.status_code == 404
        data = resp.json()
        assert data["code"] == 404
    
    def test_list_kb(self, base_url, session_client):
        resp = session_client.post(
            f"{base_url}/log_kb/list",
            json={"page_num": 1, "page_cnt": 10},
            timeout=10
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 200
    
    def test_update_kb(self, base_url, session_client, existing_kb):
        resp = session_client.put(
            f"{base_url}/log_kb/{existing_kb}",
            json={"name": "updated_name", "description": "updated_desc"},
            timeout=10
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 200
    
    def test_update_nonexistent_kb(self, base_url, session_client):
        resp = session_client.put(
            f"{base_url}/log_kb/{str(uuid.uuid4())}",
            json={"name": "test"},
            timeout=10
        )
        assert resp.status_code == 404
    
    def test_delete_kb(self, base_url, session_client):
        kb_name = f"test_kb_{str(uuid.uuid4())[:8]}"
        create_resp = session_client.post(
            f"{base_url}/log_kb",
            json={"name": kb_name, "description": "to delete"},
            timeout=10
        )
        kb_id = create_resp.json()["result"]["kb_id"]
        
        delete_resp = session_client.delete(f"{base_url}/log_kb/{kb_id}", timeout=10)
        assert delete_resp.status_code == 200
    
    def test_delete_nonexistent_kb(self, base_url, session_client):
        resp = session_client.delete(f"{base_url}/log_kb/{str(uuid.uuid4())}", timeout=10)
        assert resp.status_code == 404


class TestLogFile:
    """日志文件接口"""
    
    def test_upload_log_file(self, base_url, session_client, existing_kb):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as f:
            f.write("test log")
            temp_path = f.name
        
        try:
            resp = session_client.post(
                f"{base_url}/log_file/{existing_kb}",
                json={
                    "upload_log_file_configs": [
                        {"name": "test", "source_type": "local", "source": temp_path}
                    ]
                },
                timeout=10
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["code"] == 200
            assert data["result"]["log_file_ids"]
        finally:
            os.unlink(temp_path)
    
    def test_get_log_file(self, base_url, session_client, existing_log_file):
        resp = session_client.get(f"{base_url}/log_file/{existing_log_file}", timeout=10)
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 200
    
    def test_get_nonexistent_log_file(self, base_url, session_client):
        resp = session_client.get(f"{base_url}/log_file/{str(uuid.uuid4())}", timeout=10)
        assert resp.status_code == 404
    
    def test_list_log_files(self, base_url, session_client, existing_kb):
        resp = session_client.post(
            f"{base_url}/log_file/list/{existing_kb}",
            json={"page_num": 1, "page_cnt": 10},
            timeout=10
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 200
    
    def test_update_log_file(self, base_url, session_client, existing_log_file):
        resp = session_client.put(
            f"{base_url}/log_file/{existing_log_file}",
            json={"name": "updated"},
            timeout=10
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 200
    
    def test_delete_log_file(self, base_url, session_client, existing_kb):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as f:
            f.write("to delete")
            temp_path = f.name
        
        try:
            create_resp = session_client.post(
                f"{base_url}/log_file/{existing_kb}",
                json={
                    "upload_log_file_configs": [
                        {"name": "to_delete", "source_type": "local", "source": temp_path}
                    ]
                },
                timeout=10
            )
            log_id = create_resp.json()["result"]["log_file_ids"][0]
            
            delete_resp = session_client.delete(f"{base_url}/log_file/{log_id}", timeout=10)
            assert delete_resp.status_code == 200
        finally:
            os.unlink(temp_path)
    
    def test_delete_nonexistent_log_file(self, base_url, session_client):
        resp = session_client.delete(f"{base_url}/log_file/{str(uuid.uuid4())}", timeout=10)
        assert resp.status_code == 404


class TestTask:
    """任务接口"""
    
    def test_create_task(self, base_url, session_client, existing_log_file):
        resp = session_client.post(
            f"{base_url}/task/create",
            json={"task_type": "kv_cache_log_parse_worker", "op_id": existing_log_file},
            timeout=10
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 200
    
    def test_create_task_invalid_op(self, base_url, session_client, existing_kb):
        resp = session_client.post(
            f"{base_url}/task/create",
            json={"task_type": "INVALID_OP", "op_id": existing_kb},
            timeout=10
        )
        assert resp.status_code == 422
    
    def test_create_task_nonexistent_kb(self, base_url, session_client):
        resp = session_client.post(
            f"{base_url}/task/create",
            json={"task_type": "kv_cache_log_parse_worker", "op_id": str(uuid.uuid4()), "kb_id": str(uuid.uuid4())},
            timeout=10
        )
        assert resp.status_code == 404 or resp.status_code == 200
    
    def test_get_task(self, base_url, session_client):
        resp = session_client.get(f"{base_url}/task/{str(uuid.uuid4())}", timeout=10)
        assert resp.status_code == 200
    
    def test_list_tasks(self, base_url, session_client, existing_kb):
        resp = session_client.post(
            f"{base_url}/task/list",
            json={"kb_id": existing_kb},
            timeout=10
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 200
    
    def test_stop_task(self, base_url, session_client):
        resp = session_client.put(f"{base_url}/task/stop/{str(uuid.uuid4())}", timeout=10)
        assert resp.status_code == 404


class TestDiagnosisConfig:
    """诊断配置接口"""
    
    def test_get_config(self, base_url, session_client, existing_kb):
        resp = session_client.get(f"{base_url}/diagnosis_config/{existing_kb}", timeout=10)
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 200
    
    def test_get_nonexistent_config(self, base_url, session_client):
        resp = session_client.get(f"{base_url}/diagnosis_config/{str(uuid.uuid4())}", timeout=10)
        assert resp.status_code == 404
    
    def test_update_config(self, base_url, session_client, existing_kb):
        resp = session_client.put(
            f"{base_url}/diagnosis_config/{existing_kb}",
            json={
                "log_filename_pattern": {
                    "ds_client_access_log_file": ["*.log"],
                    "ds_client_info_log_file": ["*.log"],
                    "ds_worker_access_log_file": ["*.log"],
                    "ds_worker_info_log_file": ["*.log"],
                    "resource_log_file": ["*.log"]
                },
                "log_analyzer_params": {
                    "total_p99_threshold_ms": 2.0,
                    "total_p9999_threshold_ms": 5.0,
                    "total_pmax_threshold_ms": 5.0,
                    "total_ave_threshold_ms": 5.0
                }
            },
            timeout=10
        )
        assert resp.status_code == 200
    
    def test_reset_config(self, base_url, session_client, existing_kb):
        resp = session_client.post(f"{base_url}/diagnosis_config/{existing_kb}/reset", timeout=10)
        assert resp.status_code == 200

    def test_update_nonexistent_config(self, base_url, session_client):
        resp = session_client.put(
            f"{base_url}/diagnosis_config/{str(uuid.uuid4())}",
            json={
                "log_filename_pattern": {
                    "ds_client_access_log_file": ["*.log"],
                    "ds_client_info_log_file": ["*.log"],
                    "ds_worker_access_log_file": ["*.log"],
                    "ds_worker_info_log_file": ["*.log"],
                    "resource_log_file": ["*.log"],
                },
                "log_analyzer_params": {},
            },
            timeout=10,
        )
        assert resp.status_code == 404

    def test_reset_nonexistent_config(self, base_url, session_client):
        resp = session_client.post(
            f"{base_url}/diagnosis_config/{str(uuid.uuid4())}/reset", timeout=10
        )
        assert resp.status_code == 404


class TestDiagnosisCase:
    """诊断案例接口"""
    
    def test_create_case(self, base_url, session_client):
        resp = session_client.post(
            f"{base_url}/diagnosis_case",
            json={"symptom_summary": "test symptom", "root_cause": "test cause", "recommendation": "test recommendation"},
            timeout=10
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 200
    
    def test_get_case(self, base_url, session_client):
        resp = session_client.get(f"{base_url}/diagnosis_case/{str(uuid.uuid4())}", timeout=10)
        assert resp.status_code == 200 or resp.status_code == 404
    
    def test_search_case(self, base_url, session_client):
        resp = session_client.post(
            f"{base_url}/diagnosis_case/search",
            json={"case_name": "test", "page_num": 1, "page_cnt": 10},
            timeout=10
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 200
    
    def test_hit_case(self, base_url, session_client):
        resp = session_client.post(f"{base_url}/diagnosis_case/{str(uuid.uuid4())}/hit", timeout=10)
        assert resp.status_code == 200 or resp.status_code == 404


class TestFailureModeKnowledge:
    """故障模式知识接口"""
    
    def test_get_status_code_knowledge(self, base_url, session_client):
        resp = session_client.get(f"{base_url}/failure_mode/status_code/404", timeout=10)
        assert resp.status_code == 200 or resp.status_code == 404
    
    def test_get_failure_mode(self, base_url, session_client):
        resp = session_client.get(f"{base_url}/failure_mode/{str(uuid.uuid4())}", timeout=10)
        assert resp.status_code == 200 or resp.status_code == 404


class TestSrcDstAggregatedEvent:
    """源目标聚合事件接口"""
    
    def test_list_events(self, base_url, session_client):
        resp = session_client.post(
            f"{base_url}/aggregated_event/list",
            json={"page_num": 1, "page_cnt": 10},
            timeout=10
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 200
    
    def test_get_event(self, base_url, session_client):
        resp = session_client.get(f"{base_url}/aggregated_event/{str(uuid.uuid4())}", timeout=10)
        assert resp.status_code == 200 or resp.status_code == 404
    
    def test_list_time_window(self, base_url, session_client):
        resp = session_client.post(
            f"{base_url}/aggregated_event/list_time_window",
            json={"start_time": "2024-01-01 00:00:00", "end_time": "2024-01-02 00:00:00"},
            timeout=10
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 200


class TestLogParseResult:
    """日志解析结果接口"""
    
    def test_list_results(self, base_url, session_client):
        resp = session_client.post(
            f"{base_url}/log_parse_result/list",
            json={"page_num": 1, "page_cnt": 10},
            timeout=10
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 200
    
    def test_get_options(self, base_url, session_client):
        resp = session_client.get(f"{base_url}/log_parse_result/options", timeout=10)
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 200
    
    def test_get_result(self, base_url, session_client):
        resp = session_client.get(f"{base_url}/log_parse_result/{str(uuid.uuid4())}", timeout=10)
        assert resp.status_code == 200 or resp.status_code == 404
    
    def test_list_traces_by_host(self, base_url, session_client):
        resp = session_client.post(
            f"{base_url}/log_parse_result/traces/host/list",
            json={"host": "localhost"},
            timeout=10
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 200
    
    def test_get_latency_metrics(self, base_url, session_client):
        resp = session_client.post(
            f"{base_url}/log_parse_result/metrics/latency",
            json={"trace_id": str(uuid.uuid4())},
            timeout=10
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 200


class TestAnomalousEvent:
    """异常事件接口"""
    
    def test_get_event(self, base_url, session_client):
        resp = session_client.get(f"{base_url}/anomalous_event/{str(uuid.uuid4())}", timeout=10)
        assert resp.status_code == 200 or resp.status_code == 404
    
    def test_list_events(self, base_url, session_client):
        resp = session_client.post(
            f"{base_url}/anomalous_event/list",
            json={"page_num": 1, "page_cnt": 10},
            timeout=10
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 200
    
    def test_list_events_by_log_id(self, base_url, session_client, existing_log_file):
        resp = session_client.get(f"{base_url}/anomalous_event/log/{existing_log_file}", timeout=10)
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 200


class TestAnomalousEventChain:
    """异常事件链接口"""
    
    def test_list_chains(self, base_url, session_client):
        resp = session_client.post(
            f"{base_url}/anomalous_event_chain/list",
            json={"page_num": 1, "page_cnt": 10},
            timeout=10
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 200


class TestLogFailureEventResult:
    """日志失败事件结果接口"""
    
    def test_list_log_events(self, base_url, session_client):
        resp = session_client.post(
            f"{base_url}/log_failure_event_result/list_log_events",
            json={"page_num": 1, "page_cnt": 10},
            timeout=10
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 200
    
    def test_list_trace_events(self, base_url, session_client, existing_kb):
        resp = session_client.post(
            f"{base_url}/log_failure_event_result/list_trace_events",
            json={"kb_id": existing_kb},
            timeout=10
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 200
    
    def test_list_time_aggregated(self, base_url, session_client):
        resp = session_client.post(
            f"{base_url}/log_failure_event_result/list_time_aggregated_failure_events",
            json={"start_time": "2024-01-01 00:00:00", "end_time": "2024-01-02 00:00:00"},
            timeout=10
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 200
    
    def test_list_pod_aggregated(self, base_url, session_client):
        resp = session_client.post(
            f"{base_url}/log_failure_event_result/list_pod_aggregated_failure_events",
            json={"page_num": 1, "page_cnt": 10},
            timeout=10
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 200
    
    def test_get_err_code_metrics(self, base_url, session_client, existing_kb):
        resp = session_client.post(
            f"{base_url}/log_failure_event_result/metrics/err_code",
            json={"kb_id": existing_kb, "start_time": "2024-01-01 00:00:00", "end_time": "2024-01-02 00:00:00"},
            timeout=10
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 200


class TestValidationError:
    """参数校验错误测试"""
    
    def test_invalid_source_type(self, base_url, session_client, existing_kb):
        resp = session_client.post(
            f"{base_url}/log_file/{existing_kb}",
            json={
                "upload_log_file_configs": [
                    {"name": "test", "source_type": "invalid", "source": "/tmp/test.log"}
                ]
            },
            timeout=10
        )
        assert resp.status_code == 422
        data = resp.json()
        assert data["code"] == 422
    
    def test_empty_kb_name(self, base_url, session_client):
        resp = session_client.post(
            f"{base_url}/log_kb",
            json={"name": "", "description": "test"},
            timeout=10
        )
        assert resp.status_code == 422
        data = resp.json()
        assert data["code"] == 422
    
    def test_zero_page_size(self, base_url, session_client):
        resp = session_client.post(
            f"{base_url}/log_kb/list",
            json={"page_num": 1, "page_cnt": 0},
            timeout=10
        )
        assert resp.status_code == 422
        data = resp.json()
        assert data["code"] == 422
    
    def test_zero_page_num(self, base_url, session_client):
        resp = session_client.post(
            f"{base_url}/log_kb/list",
            json={"page_num": 0, "page_cnt": 10},
            timeout=10
        )
        assert resp.status_code == 422
        data = resp.json()
        assert data["code"] == 422


class TestBadRequest:
    """请求参数错误测试"""
    
    def test_nonexistent_local_path(self, base_url, session_client, existing_kb):
        resp = session_client.post(
            f"{base_url}/log_file/{existing_kb}",
            json={
                "upload_log_file_configs": [
                    {"name": "test", "source_type": "local", "source": "/nonexistent/path.log"}
                ]
            },
            timeout=10
        )
        assert resp.status_code == 400
        data = resp.json()
        assert data["code"] == 400


def pytest_addoption(parser):
    parser.addoption("--base-url", action="store", default="http://localhost:9772", help="API base URL")
