"""
单元测试：测试所有 API 接口
使用 pytest + requests 进行测试
"""
import pytest
import requests
import asyncio
from datetime import datetime
import uuid

# 服务地址
BASE_URL = "http://127.0.0.1:9772"

# 测试数据
TEST_HOST = "10.0.0.1"
TEST_SRC_IP = "192.168.1.1"
TEST_DST_IP = "192.168.1.2"
TEST_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def now():
    return datetime.now().strftime(TEST_TIME_FORMAT)


class TestHealthCheck:
    """健康检查接口测试"""

    @pytest.mark.asyncio
    async def test_health_check(self):
        """测试健康检查接口"""
        response = requests.get(f"{BASE_URL}/health_check")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"


class TestLogKnowledge:
    """日志知识接口测试"""

    kb_id = None

    @pytest.mark.asyncio
    async def test_create_log_knowledge(self):
        """测试创建日志知识"""
        payload = {
            "name": f"test_kb_{uuid.uuid4().hex[:8]}",
            "description": "Test knowledge base"
        }
        response = requests.post(f"{BASE_URL}/log_kb", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "kb_id" in data["result"]
        TestLogKnowledge.kb_id = data["result"]["kb_id"]

    @pytest.mark.asyncio
    async def test_list_log_knowledge(self):
        """测试查询日志知识列表"""
        payload = {
            "page_cnt": 10,
            "page_num": 1
        }
        response = requests.post(f"{BASE_URL}/log_kb/list", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "total" in data["result"]
        assert "kbs" in data["result"]

    @pytest.mark.asyncio
    async def test_get_log_knowledge(self):
        """测试获取日志知识详情"""
        if not TestLogKnowledge.kb_id:
            pytest.skip("No kb_id available")
        
        response = requests.get(f"{BASE_URL}/log_kb/{TestLogKnowledge.kb_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "kb" in data["result"]

    @pytest.mark.asyncio
    async def test_update_log_knowledge(self):
        """测试更新日志知识"""
        if not TestLogKnowledge.kb_id:
            pytest.skip("No kb_id available")
        
        payload = {
            "name": f"updated_kb_{uuid.uuid4().hex[:8]}",
            "description": "Updated description"
        }
        response = requests.put(f"{BASE_URL}/log_kb/{TestLogKnowledge.kb_id}", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200

    @pytest.mark.asyncio
    async def test_delete_log_knowledge(self):
        """测试删除日志知识"""
        if not TestLogKnowledge.kb_id:
            pytest.skip("No kb_id available")
        
        response = requests.delete(f"{BASE_URL}/log_kb/{TestLogKnowledge.kb_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200


class TestLogFile:
    """日志文件接口测试"""

    kb_id = None
    log_file_id = None

    async def _ensure_kb_id(self):
        """确保有一个知识库ID"""
        if TestLogFile.kb_id:
            return TestLogFile.kb_id
        
        response = requests.post(f"{BASE_URL}/log_kb/list", json={"page_cnt": 1, "page_num": 1})
        data = response.json()
        if data["result"]["total"] > 0:
            TestLogFile.kb_id = data["result"]["kbs"][0]["id"]
        else:
            payload = {"name": f"test_kb_{uuid.uuid4().hex[:8]}", "description": "Test KB"}
            response = requests.post(f"{BASE_URL}/log_kb", json=payload)
            TestLogFile.kb_id = response.json()["result"]["kb_id"]
        return TestLogFile.kb_id

    @pytest.mark.asyncio
    async def test_upload_log_file(self):
        """测试上传日志文件（需要存在的本地文件路径，跳过）"""
        pytest.skip("Upload test requires a valid local file path")

    @pytest.mark.asyncio
    async def test_list_log_files(self):
        """测试查询日志文件列表"""
        kb_id = await self._ensure_kb_id()
        
        payload = {
            "page_cnt": 10,
            "page_num": 1
        }
        response = requests.post(f"{BASE_URL}/log_file/list/{kb_id}", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "total" in data["result"]
        assert "log_files" in data["result"]

    @pytest.mark.asyncio
    async def test_get_log_file(self):
        """测试获取日志文件详情"""
        if not TestLogFile.log_file_id:
            pytest.skip("No log_file_id available")
        
        
        response = requests.post(f"{BASE_URL}/log_file/{TestLogFile.log_file_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "log_file" in data["result"]


class TestLogParseResult:
    """日志解析结果接口测试"""

    @pytest.mark.asyncio
    async def test_list_log_parse_results(self):
        """测试查询日志解析结果列表"""
        
        payload = {
            "page_cnt": 10,
            "page_num": 1,
            "src_ip": TEST_SRC_IP,
            "host": "test-host",      # 新增：主机名称查询
            "cluster_name": "test-cluster",  # 新增：集群名称查询
            "is_anomalous": False
        }
        response = requests.post(f"{BASE_URL}/log_parse_result/list", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "total" in data["result"]
        assert "log_parse_results" in data["result"]

    @pytest.mark.asyncio
    async def test_list_log_parse_results_by_cluster(self):
        """测试根据集群名称查询日志解析结果"""
        
        payload = {
            "page_cnt": 10,
            "page_num": 1,
            "cluster_name": "jp",  # 根据实际集群名称查询
            "is_anomalous": None    # 不区分异常状态
        }
        response = requests.post(f"{BASE_URL}/log_parse_result/list", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "total" in data["result"]
        assert "log_parse_results" in data["result"]

    @pytest.mark.asyncio
    async def test_list_log_parse_results_by_host(self):
        """测试根据主机名称查询日志解析结果"""
        
        payload = {
            "page_cnt": 10,
            "page_num": 1,
            "host": "192.168",  # 根据主机IP或名称查询
            "is_anomalous": None
        }
        response = requests.post(f"{BASE_URL}/log_parse_result/list", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "total" in data["result"]
        assert "log_parse_results" in data["result"]

    @pytest.mark.asyncio
    async def test_get_log_parse_options(self):
        """测试获取日志解析选项（集群和主机列表）"""
        
        response = requests.get(f"{BASE_URL}/log_parse_result/options")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "clusters" in data["result"]
        assert "hosts" in data["result"]
        assert isinstance(data["result"]["clusters"], list)
        assert isinstance(data["result"]["hosts"], list)

    @pytest.mark.asyncio
    async def test_list_traces_by_host(self):
        """测试根据主机获取trace列表（修改后的接口）"""
        
        payload = {
            "host": TEST_HOST,
            "start_time": "2024-01-01 00:00:00",
            "end_time": now(),
            "operation": "READ",
            "page_cnt": 10,
            "page_num": 1,
            "sort_by": "timestamp",
            "sort_order": "desc"
        }
        response = requests.post(f"{BASE_URL}/log_parse_result/traces/host/list", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "total" in data["result"]
        assert "traces" in data["result"]

    @pytest.mark.asyncio
    async def test_get_latency_metrics(self):
        """测试获取延迟指标时间曲线数据"""
        
        payload = {
            "host": TEST_HOST,
            "start_time": "2024-01-01 00:00:00",
            "end_time": now(),
            "max_points": -1,  # 获取全部数据
            "sort_by": "timestamp",
            "sort_order": "asc"
        }
        response = requests.post(f"{BASE_URL}/log_parse_result/metrics/latency", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "total" in data["result"]
        assert "metrics" in data["result"]


class TestAggregatedEvent:
    """聚合事件接口测试"""

    @pytest.mark.asyncio
    async def test_list_aggregated_events(self):
        """测试查询聚合事件列表"""
        
        payload = {
            "page_cnt": 10,
            "page_num": 1,
            "src_ip": TEST_SRC_IP,
            "dst_ip": TEST_DST_IP
        }
        response = requests.post(f"{BASE_URL}/aggregated_event/list", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "total" in data["result"]
        assert "events" in data["result"]


class TestAnomalousEvent:
    """异常事件接口测试"""

    @pytest.mark.asyncio
    async def test_list_anomalous_events(self):
        """测试查询异常事件列表"""
    
        payload = {
            "page_cnt": 10,
            "page_num": 1
        }
        response = requests.post(f"{BASE_URL}/anomalous_event/list", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "total" in data["result"]
        assert "events" in data["result"]


class TestAnomalousEventChain:
    """异常事件链接口测试"""

    @pytest.mark.asyncio
    async def test_list_anomalous_event_chains(self):
        """测试查询异常事件链列表"""
        
        payload = {
            "page_cnt": 10,
            "page_num": 1
        }
        response = requests.post(f"{BASE_URL}/anomalous_event_chain/list", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "total" in data["result"]
        assert "event_chains" in data["result"]


class TestTask:
    """任务接口测试"""

    task_id = None
    log_file_id = None

    @pytest.mark.asyncio
    async def test_list_tasks(self):
        """测试查询任务列表"""
        
        payload = {
            "page_cnt": 10,
            "page_num": 1
        }
        response = requests.post(f"{BASE_URL}/task/list", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "total" in data["result"]
        assert "tasks" in data["result"]

    @pytest.mark.asyncio
    async def test_create_task(self):
        """测试创建任务（使用 mock 数据）"""
        
        # 尝试获取一个 log_file_id，如果没有则创建 mock 数据
        kb_response = requests.post(f"{BASE_URL}/log_kb/list", json={"page_cnt": 1, "page_num": 1})
        assert kb_response.status_code == 200
        kb_data = kb_response.json()
        
        kb_id = None
        if kb_data["result"]["total"] > 0:
            kb_id = kb_data["result"]["kbs"][0]["id"]
        
        # 尝试获取日志文件
        log_file_id = None
        if kb_id:
            lf_response = requests.post(f"{BASE_URL}/log_file/list/{kb_id}", json={"page_cnt": 1, "page_num": 1})
            if lf_response.status_code == 200:
                lf_data = lf_response.json()
                if lf_data["result"]["total"] > 0:
                    log_file_id = lf_data["result"]["log_files"][0]["id"]
        
        # 如果没有日志文件，使用 mock 的 op_id（服务端应该能够处理）
        if not log_file_id:
            log_file_id = f"mock_log_file_{uuid.uuid4().hex[:8]}"
            print(f"Using mock log_file_id: {log_file_id}")
        
        payload = {
            "task_type": "kv_cache_log_parse_worker",
            "op_id": log_file_id,
            "task_name": f"test_task_{uuid.uuid4().hex[:8]}"
        }
        response = requests.post(f"{BASE_URL}/task/create", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "task_id" in data["result"]
        TestTask.task_id = data["result"]["task_id"]

    @pytest.mark.asyncio
    async def test_get_task(self):
        """测试获取任务详情"""
        if not TestTask.task_id:
            # 如果没有 task_id，先创建一个
            await self._create_mock_task()
        
        response = requests.get(f"{BASE_URL}/task/{TestTask.task_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "task" in data["result"]

    @pytest.mark.asyncio
    async def test_stop_task(self):
        """测试停止任务"""
        if not TestTask.task_id:
            # 如果没有 task_id，先创建一个
            await self._create_mock_task()
        
        response = requests.put(f"{BASE_URL}/task/stop/{TestTask.task_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200

    @pytest.mark.asyncio
    async def test_delete_task(self):
        """测试删除任务"""
        if not TestTask.task_id:
            # 如果没有 task_id，先创建一个
            await self._create_mock_task()
        
        response = requests.delete(f"{BASE_URL}/task/{TestTask.task_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
    
    async def _create_mock_task(self):
        """创建一个 mock 任务（用于测试）"""
        log_file_id = f"mock_log_file_{uuid.uuid4().hex[:8]}"
        payload = {
            "task_type": "kv_cache_log_parse_worker",
            "op_id": log_file_id,
            "task_name": f"test_task_{uuid.uuid4().hex[:8]}"
        }
        response = requests.post(f"{BASE_URL}/task/create", json=payload)
        assert response.status_code == 200
        data = response.json()
        TestTask.task_id = data["result"]["task_id"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
