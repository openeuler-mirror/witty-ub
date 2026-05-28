#!/usr/bin/env python3
"""
全链路验证测试脚本
验证从 API 创建任务到 Worker 执行的完整流程
"""
import asyncio
import os
import sys
import uuid
import time
import requests

# 设置 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))
# $env:PYTHONPATH="e:\witty-ub\src\plugins"; python e:\witty-ub\src\plugins\latency\test\test_full_link.py
from latency.schemas.log import LogFileModel, LogKnowledgeModel
from latency.database.managers.log_file import LogFileManager
from latency.database.managers.log_knowledge import LogKnowledgeManager
from latency.database.engine import AsyncSQLiteSingleton
from latency.ENUM.task import TaskStatusEnum


async def setup_test_data(log_dir: str) -> tuple[str, str]:
    """设置测试数据：创建 log_knowledge 和 log_file"""
    db = AsyncSQLiteSingleton()
    await db.init_database()
    
    # 创建 log_knowledge
    kb_id = str(uuid.uuid4())[:8]  # 简化ID便于查看
    kb_model = LogKnowledgeModel(
        id=kb_id,
        image_bytes=b"",
        name="test_kb",
        description="测试知识库",
    )
    await LogKnowledgeManager.add_log_kb(kb_model)
    print(f"✅ 创建 log_knowledge: {kb_id}")
    
    # 创建 log_file
    log_file_id = str(uuid.uuid4())[:8]
    log_file_model = LogFileModel(
        id=log_file_id,
        kb_id=kb_id,
        name="test_log_file.log",
        file_path=log_dir,
        file_size=1024,
        parse_status=TaskStatusEnum.PENDING.value,
        anomaly_cnt=0,
    )
    await LogFileManager.add_log_file(log_file_model)
    print(f"✅ 创建 log_file: {log_file_id}")
    print(f"✅ 日志目录: {log_dir}")
    
    return kb_id, log_file_id


def create_task_via_api(kb_id: str, log_file_id: str) -> str:
    """通过 API 创建任务"""
    url = "http://localhost:9772/task/create"
    payload = {
        "task_type": "kv_cache_log_parse_worker",
        "op_id": log_file_id,
        "kb_id": kb_id,
        "task_name": "全链路测试任务"
    }
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        task_id = data.get("result", {}).get("task_id")
        if task_id:
            print(f"✅ API 创建任务成功: {task_id}")
            return task_id
        else:
            print("❌ API 创建任务失败: task_id 为 None")
            return None
    except Exception as e:
        print(f"❌ API 请求失败: {e}")
        return None


def query_task_status(task_id: str) -> str:
    """查询任务状态"""
    url = f"http://localhost:9772/task/{task_id}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        task = data.get("result", {}).get("task")
        if task:
            return task.get("status")
        return "未知"
    except Exception as e:
        print(f"❌ 查询任务状态失败: {e}")
        return "未知"


def query_task_list():
    """查询任务列表"""
    url = "http://localhost:9772/task/list"
    payload = {"page_num": 1, "page_cnt": 5}
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        tasks = data.get("result", {}).get("tasks", [])
        print("\n=== 任务列表 ===")
        for task in tasks:
            print(f"ID: {task['id']}")
            print(f"  名称: {task['task_name']}")
            print(f"  类型: {task['task_type']}")
            print(f"  状态: {task['status']}")
            print(f"  创建时间: {task['created_at']}")
            print("---")
    except Exception as e:
        print(f"❌ 查询任务列表失败: {e}")


async def query_task_reports():
    """查询任务报告"""
    db = AsyncSQLiteSingleton()
    results = await db.execute_query(
        'SELECT task_id, progress, message, created_at FROM task_report_table '
        'WHERE existed_status=1 ORDER BY created_at DESC LIMIT 10'
    )
    print("\n=== 任务报告 ===")
    for row in results:
        print(f"任务ID: {row['task_id']}")
        print(f"  进度: {row['progress']}%")
        print(f"  消息: {row['message']}")
        print(f"  时间: {row['created_at']}")
        print("---")


async def main():
    print("=" * 70)
    print("全链路验证测试")
    print("=" * 70)
    
    # 1. 设置测试数据
    log_dir = r"D:\test_log_1"
    print(f"\n[Step 1] 设置测试数据，日志目录: {log_dir}")
    kb_id, log_file_id = await setup_test_data(log_dir)
    
    # 2. 通过 API 创建任务
    print("\n[Step 2] 通过 API 创建任务")
    task_id = create_task_via_api(kb_id, log_file_id)
    if not task_id:
        print("❌ 任务创建失败，退出测试")
        return
    
    # 3. 等待调度器执行任务
    print("\n[Step 3] 等待调度器执行任务（最多等待20秒）")
    print("=" * 50)
    for i in range(20):
        status = query_task_status(task_id)
        print(f"第 {i+1:2d} 秒 - 任务状态: {status}")
        
        if status == "running":
            print("✅ 任务已开始执行！")
            break
        
        if status == "successful_pending_remove" or status == "successful":
            print("✅ 任务已执行完成！")
            break
            
        time.sleep(1)
    else:
        print("❌ 调度器在20秒内未执行任务")
    
    # 4. 查询任务列表
    print("\n[Step 4] 查询任务列表")
    query_task_list()
    
    # 5. 查询任务报告
    print("\n[Step 5] 查询任务报告")
    await query_task_reports()
    
    # 6. 循环监控任务状态
    print("\n[Step 6] 循环监控任务状态（按 Ctrl+C 退出）")
    print("=" * 70)
    print("提示：按 Ctrl+C 可以退出监控")
    print("-" * 70)
    
    try:
        while True:
            status = query_task_status(task_id)
            current_time = time.strftime("%H:%M:%S")
            print(f"[{current_time}] 任务状态：{status}")
            
            # 如果任务已完成，可以选择退出或继续监控
            if status in ["successful", "failed", "cancelled"]:
                print(f"✅ 任务已结束，状态：{status}")
                choice = input("是否继续监控？(y/n): ").strip().lower()
                if choice != 'y':
                    break
                print("-" * 70)
            
            time.sleep(2)  # 每2秒查询一次
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断监控")
    
    print("\n" + "=" * 70)
    print("全链路测试完成")
    print("=" * 70)

# Invoke-WebRequest -Uri http://localhost:9772/task/{task_id} -Method GET | Select-Object -ExpandProperty Content
if __name__ == "__main__":
    asyncio.run(main())