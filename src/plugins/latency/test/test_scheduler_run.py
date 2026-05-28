#!/usr/bin/env python3
"""
测试调度器自动执行任务
创建任务后等待调度器触发
"""
import asyncio
import os
import sys
import uuid
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from latency.schemas.request import CreateTaskRequest
from latency.schemas.response import CreateTaskMsg, GetTaskMsg
from latency.services.task import TaskService
from latency.database.managers.log_file import LogFileManager
from latency.database.managers.log_knowledge import LogKnowledgeManager
from latency.database.engine import AsyncSQLiteSingleton
from latency.schemas.log import LogFileModel, LogKnowledgeModel
from latency.ENUM.task import TaskTypeEnum, TaskStatusEnum
from latency.task.worker.kv_cache_log_parse_worker import KVCacheLogParseWorker


async def setup_mock_data() -> tuple[str, str]:
    """设置 mock 数据"""
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


async def test_scheduler_execution():
    """测试调度器自动执行任务"""
    print("\n" + "=" * 60)
    print("测试调度器自动执行任务")
    print("=" * 60)

    # 初始化数据库
    db = AsyncSQLiteSingleton()
    await db.init_database()

    # 设置 mock 数据
    kb_id, log_file_id = await setup_mock_data()

    # 创建任务
    req = CreateTaskRequest(
        task_type=TaskTypeEnum.KV_CACHE_LOG_PARSE_WORKER,
        op_id=log_file_id,
        kb_id=kb_id,
        task_name="测试调度器任务"
    )
    result: CreateTaskMsg = await TaskService.create_task(req)
    
    if not result.task_id:
        print("❌ 任务创建失败")
        return
    
    print(f"\n✅ 任务创建成功，task_id: {result.task_id}")

    # 检查初始状态
    task_result: GetTaskMsg = await TaskService.get_task_by_id(result.task_id)
    print(f"初始状态: {task_result.task.status}")

    # 等待调度器执行（调度器每5秒执行一次）
    print("\n⏳ 等待调度器执行（最多等待15秒）...")
    for i in range(15):
        time.sleep(1)
        
        # 检查任务状态
        task_result = await TaskService.get_task_by_id(result.task_id)
        current_status = task_result.task.status if task_result.task else "未知"
        print(f"  第{i+1}秒 - 当前状态: {current_status}")
        
        # 如果状态不再是 pending，说明调度器已执行
        if current_status != TaskStatusEnum.PENDING.value:
            print("\n✅ 调度器已执行任务！")
            print(f"   任务状态已从 PENDING 变为 {current_status}")
            break
    else:
        print("\n❌ 调度器在15秒内未执行任务")

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_scheduler_execution())