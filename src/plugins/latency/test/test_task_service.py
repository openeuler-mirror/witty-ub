#!/usr/bin/env python3
"""
TaskService 单元测试
验证从 TaskService 到 TaskHandler 的完整任务创建流程
"""
import asyncio
import os
import sys
import uuid
from datetime import datetime

# 设置正确的 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from latency.schemas.request import CreateTaskRequest
from latency.schemas.response import CreateTaskMsg, GetTaskMsg
from latency.services.task import TaskService
from latency.database.managers.log_file import LogFileManager
from latency.database.managers.log_knowledge import LogKnowledgeManager
from latency.database.managers.task import TaskManager
from latency.database.engine import AsyncSQLiteSingleton
from latency.schemas.log import LogFileModel, LogKnowledgeModel
from latency.ENUM.task import TaskTypeEnum, TaskStatusEnum
# 必须导入 Worker 类，否则 BaseWorker.find_worker_class() 无法找到
from latency.task.worker.kv_cache_log_parse_worker import KVCacheLogParseWorker


async def setup_mock_data() -> tuple[str, str]:
    """设置 mock 数据：创建 log_knowledge 和 log_file"""
    # 创建 log_knowledge
    kb_id = str(uuid.uuid4())
    kb_model = LogKnowledgeModel(
        id=kb_id,
        image_bytes=b"",
        name="test_kb",
        description="测试知识库",
        src_ip_list=["192.168.1.1"],
        dst_ip_list=["192.168.1.2"],
    )
    await LogKnowledgeManager.add_log_kb(kb_model)
    print(f"✅ 创建 mock log_knowledge: {kb_id}")

    # 创建 log_file
    log_file_id = str(uuid.uuid4())
    log_file_model = LogFileModel(
        id=log_file_id,
        kb_id=kb_id,
        name="test_log_file.log",
        file_path="/tmp/test_logs",
        file_size=1024,
        parse_status=TaskStatusEnum.PENDING.value,
        anomaly_cnt=0,
    )
    await LogFileManager.add_log_file(log_file_model)
    print(f"✅ 创建 mock log_file: {log_file_id}")

    return kb_id, log_file_id


async def test_task_creation():
    """测试任务创建完整流程"""
    print("\n" + "=" * 60)
    print("TaskService 单元测试 - 任务创建流程")
    print("=" * 60)

    # 1. 初始化数据库
    print("\n[Step 1] 初始化数据库连接")
    db = AsyncSQLiteSingleton()
    await db.init_database()
    print("✅ 数据库连接初始化成功")

    # 2. 设置 mock 数据
    print("\n[Step 2] 设置 mock 数据")
    kb_id, log_file_id = await setup_mock_data()

    # 3. 调用 TaskService.create_task()
    print("\n[Step 3] 调用 TaskService.create_task()")
    req = CreateTaskRequest(
        task_type=TaskTypeEnum.KV_CACHE_LOG_PARSE_WORKER,
        op_id=log_file_id,
        kb_id=kb_id,
        task_name="测试任务"
    )
    result: CreateTaskMsg = await TaskService.create_task(req)
    
    if result.task_id:
        print(f"✅ 任务创建成功，task_id: {result.task_id}")
    else:
        print("❌ 任务创建失败")
        return

    # 4. 验证任务是否真的创建到数据库中
    print("\n[Step 4] 验证数据库中的任务")
    task_result: GetTaskMsg = await TaskService.get_task_by_id(result.task_id)
    
    if task_result.task:
        print(f"✅ 从数据库查询到任务:")
        print(f"   - task_id: {task_result.task.id}")
        print(f"   - task_name: {task_result.task.task_name}")
        print(f"   - task_type: {task_result.task.task_type}")
        print(f"   - status: {task_result.task.status}")
        print(f"   - kb_id: {task_result.task.kb_id}")
        print(f"   - op_id: {task_result.task.op_id}")
        print(f"   - created_at: {task_result.task.created_at}")
        
        # 验证状态是否正确
        if task_result.task.status == TaskStatusEnum.PENDING.value:
            print("✅ 任务状态正确: PENDING")
        else:
            print(f"❌ 任务状态不正确: {task_result.task.status}")
            
        # 验证关联关系
        if task_result.task.op_id == log_file_id:
            print("✅ op_id 关联正确")
        else:
            print(f"❌ op_id 关联不正确: {task_result.task.op_id} != {log_file_id}")
    else:
        print("❌ 无法从数据库查询到任务")

    # 5. 测试停止任务
    print("\n[Step 5] 测试停止任务")
    stop_result = await TaskService.stop_task(result.task_id)
    
    if stop_result.task_id:
        print("✅ 任务停止成功")
        
        # 验证状态变化
        task_result = await TaskService.get_task_by_id(result.task_id)
        if task_result.task and task_result.task.status == TaskStatusEnum.CANCELLED.value:
            print("✅ 任务状态已更新为 CANCELLED")
        else:
            print(f"❌ 任务状态未正确更新: {task_result.task.status if task_result.task else 'None'}")
    else:
        print("❌ 任务停止失败")

    # 6. 测试删除任务
    print("\n[Step 6] 测试删除任务")
    delete_result = await TaskService.delete_task(result.task_id)
    
    if delete_result.task_id:
        print("✅ 任务删除成功")
        
        # 验证任务已删除
        task_result = await TaskService.get_task_by_id(result.task_id)
        if not task_result.task:
            print("✅ 任务已从数据库删除")
        else:
            print("❌ 任务仍存在于数据库中")
    else:
        print("❌ 任务删除失败")

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_task_creation())