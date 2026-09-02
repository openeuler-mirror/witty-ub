"""
数据库层单元测试

覆盖:
1. execute_modify 返回 (success, rowcount) 元组
2. 软删除语义 (existed_status 过滤)
3. 更新/删除不存在资源返回 rowcount=0
4. 级联删除
5. 批量操作
"""
import asyncio
import os
import sys
import uuid
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "../.."))

import pytest

from latency.database.engine import AsyncSQLiteSingleton
from latency.database.managers.log_knowledge import LogKnowledgeManager
from latency.database.managers.log_file import LogFileManager
from latency.database.managers.log_parse_result import LogParseResultManager
from latency.schemas.log import LogKnowledgeModel, LogFileModel, LogParseResultModel
from latency.schemas.request import ListLogParseResultRequest


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


@pytest.fixture(scope="session", autouse=True)
def initialize_database():
    """初始化数据库"""
    asyncio.run(_init_db())


async def _init_db():
    db = AsyncSQLiteSingleton()
    await db.init_database()


@pytest.mark.asyncio
async def test_execute_modify_returns_rowcount():
    """测试 execute_modify 返回 (success, rowcount) 元组"""
    db = AsyncSQLiteSingleton()

    kb_id = str(uuid.uuid4())
    sql = """
        INSERT INTO log_knowledge_table
        (id, image_bytes, name, description, task_cnt, log_file_cnt, anomaly_cnt, existed_status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    params = (kb_id, None, "test_kb", "test", 0, 0, 0, 1, now(), now())
    success, rowcount = await db.execute_modify(sql, params)
    assert success is True
    assert rowcount == 1

    sql = "UPDATE log_knowledge_table SET name = :name WHERE id = :kb_id"
    success, rowcount = await db.execute_modify(sql, {"name": "updated_kb", "kb_id": kb_id})
    assert success is True
    assert rowcount == 1

    fake_id = str(uuid.uuid4())
    sql = "UPDATE log_knowledge_table SET name = :name WHERE id = :kb_id"
    success, rowcount = await db.execute_modify(sql, {"name": "fake", "kb_id": fake_id})
    assert success is True
    assert rowcount == 0

    sql = "DELETE FROM log_knowledge_table WHERE id = :kb_id"
    success, rowcount = await db.execute_modify(sql, {"kb_id": kb_id})
    assert success is True
    assert rowcount == 1


@pytest.mark.asyncio
async def test_soft_delete_semantics():
    """测试软删除语义"""
    kb_id = str(uuid.uuid4())
    kb_model = LogKnowledgeModel(
        id=kb_id,
        image_bytes=b"",
        name="soft_delete_test_kb",
        description="test",
    )
    await LogKnowledgeManager.add_log_kb(kb_model)

    kb = await LogKnowledgeManager.get_log_kb_by_kb_id(kb_id)
    assert kb is not None
    assert kb.id == kb_id

    rowcount = await LogKnowledgeManager.update_log_kb(kb_id, {"existed_status": False})
    assert rowcount > 0

    kb = await LogKnowledgeManager.get_log_kb_by_kb_id(kb_id)
    assert kb is None


@pytest.mark.asyncio
async def test_update_delete_nonexistent_resource():
    """测试更新/删除不存在资源"""
    fake_id = str(uuid.uuid4())

    rowcount = await LogFileManager.update_log_file(fake_id, {"name": "fake"})
    assert rowcount == 0

    rowcount = await LogKnowledgeManager.update_log_kb(fake_id, {"name": "fake"})
    assert rowcount == 0


@pytest.mark.asyncio
async def test_cascade_delete():
    """测试级联删除"""
    kb_id = str(uuid.uuid4())
    kb_model = LogKnowledgeModel(
        id=kb_id,
        image_bytes=b"",
        name="cascade_test_kb",
        description="test",
    )
    await LogKnowledgeManager.add_log_kb(kb_model)

    log_file_id = str(uuid.uuid4())
    log_file_model = LogFileModel(
        id=log_file_id,
        kb_id=kb_id,
        name="test.log",
        file_path="/tmp/test.log",
        file_size=1024,
    )
    await LogFileManager.add_log_file(log_file_model)

    parse_result_id = str(uuid.uuid4())
    parse_result_model = LogParseResultModel(
        id=parse_result_id,
        log_id=log_file_id,
        trace_id="test-trace-1",
        timestamp=now(),
        src_ip="192.168.1.1",
        dst_ip="192.168.1.2",
        total_latency=1.5,
        is_anomalous=False,
    )
    await LogParseResultManager.add_log_parse_result(parse_result_model)

    req = ListLogParseResultRequest(log_id=log_file_id, page_num=1, page_cnt=10)
    _, results = await LogParseResultManager.list_log_parse_results(req)
    assert len(results) > 0

    rowcount = await LogFileManager.update_log_file(
        log_file_id, {"existed_status": False}
    )
    assert rowcount > 0

    await LogParseResultManager.delete_log_parse_results_by_log_id(log_file_id)

    req = ListLogParseResultRequest(log_id=log_file_id, page_num=1, page_cnt=10)
    _, results = await LogParseResultManager.list_log_parse_results(req)
    assert len(results) == 0


@pytest.mark.asyncio
async def test_batch_operations():
    """测试批量操作"""
    db = AsyncSQLiteSingleton()

    sql = """
        INSERT INTO log_knowledge_table
        (id, image_bytes, name, description, task_cnt, log_file_cnt, anomaly_cnt, existed_status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    batch_params = []
    for i in range(5):
        kb_id = str(uuid.uuid4())
        batch_params.append((kb_id, None, f"batch_kb_{i}", "test", 0, 0, 0, 1, now(), now()))

    success, rowcount = await db.execute_modify(sql, batch_params)
    assert success is True
    assert rowcount == 5
