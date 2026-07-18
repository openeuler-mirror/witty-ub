"""验证 list_current_tasks + task_reports + progress 计算链路。

连接本地 PG15 测试容器，模拟：
1. 正常场景
2. parse/store 的 BaseWorker.report 静默失败（没存进去）
3. stored=False/吞异常仍 report(100) + SUCCESSFUL_PENDING_REMOVE
"""
from __future__ import annotations

import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from latency.ENUM.task import TaskStatusEnum, TaskTypeEnum
from latency.database.engine import PGManager
from latency.database.init import init_postgresql_database
from latency.database.managers.log_file import LogFilePGManager
from latency.database.managers.task import TaskPGManager
from latency.database.managers.task_report import TaskReportPGManager
from latency.schemas.log import LogFileModel
from latency.schemas.task import TaskModel, TaskReportModel
from latency.services.log_file import LogFileService
from latency.task.progress import (
    _task_progress,
    parallel_overall_progress,
    task_progress,
)

DSN = "postgresql+asyncpg://testuser:testpass@localhost:55432/testdb"


def _new_id() -> str:
    return str(uuid.uuid4())


async def _insert_log_file(kb_id: str, name: str) -> LogFileModel:
    m = LogFileModel(id=_new_id(), kb_id=kb_id, name=name, file_path="/tmp/"+name, file_size=1024, existed_status=True)
    async with PGManager.session() as s:
        from latency.database.models import LogFile as LFR
        await s.execute(
            __import__("sqlalchemy").insert(LFR),
            [{
                "id": m.id, "kb_id": m.kb_id, "name": m.name, "file_path": m.file_path,
                "file_size": m.file_size, "existed_status": m.existed_status, "created_at": datetime.now(timezone.utc),
            }],
        )
    return m


async def _insert_task(op_id: str, task_type: TaskTypeEnum, status: TaskStatusEnum) -> TaskModel:
    m = TaskModel(
        id=_new_id(), op_id=op_id, kb_id="kb-test",
        task_name=f"{task_type.value}:{op_id[:8]}", task_type=task_type, status=status,
        existed_status=True, retry_times=0, progress=0.0,
    )
    await TaskPGManager.add_task(m)
    return m


async def _insert_report(task_id: str, progress: float, msg: str) -> TaskReportModel:
    r = TaskReportModel(id=_new_id(), task_id=task_id, progress=progress, message=msg, existed_status=True)
    await TaskReportPGManager.add_task_report(r)
    return r


async def scenario_normal() -> None:
    """场景A：三个任务正常，reports 也全部写入正常。"""
    print("\n" + "="*80)
    print(" 场景 A：正常场景——parse(20%), diagnosis(80%), store(65%)")
    print("="*80)
    kb_id = "kb-normal"
    lf = await _insert_log_file(kb_id, "normal.log")
    parse_task = await _insert_task(lf.id, TaskTypeEnum.KV_CACHE_LOG_PARSE_WORKER, TaskStatusEnum.RUNNING)
    diagnosis_task = await _insert_task(lf.id, TaskTypeEnum.KV_CACHE_LOG_EVENT_DIAGNOSIS_WORKER, TaskStatusEnum.RUNNING)
    store_task = await _insert_task(lf.id, TaskTypeEnum.STORE_TRACE_CONTEXT_LOGS_WORKER, TaskStatusEnum.RUNNING)
    await _insert_report(parse_task.id, 0.0, "Task initialized")
    await _insert_report(parse_task.id, 5.0, "Task running")
    await _insert_report(parse_task.id, 20.0, "Log parse completed")   # 实际 20%
    await _insert_report(diagnosis_task.id, 0.0, "Task initialized")
    await _insert_report(diagnosis_task.id, 5.0, "运行任务")
    await _insert_report(diagnosis_task.id, 80.0, "故障定界完成，等待Trace上下文落库任务处理")  # 实际 80%
    await _insert_report(store_task.id, 0.0, "Task initialized")
    await _insert_report(store_task.id, 5.0, "Task running")
    await _insert_report(store_task.id, 20.0, "Waiting for diagnosis task, current status: running")  # 等待期
    await _insert_report(store_task.id, 45.0, "Trace context logs stored after diagnosis: 100")
    await _insert_report(store_task.id, 65.0, "Waiting for parse task, current status: running")    # 等待期 65%

    log_file_ids = [lf.id]
    p_tsk = await TaskPGManager.list_current_tasks_by_op_ids(log_file_ids, TaskTypeEnum.KV_CACHE_LOG_PARSE_WORKER)
    d_tsk = await TaskPGManager.list_current_tasks_by_op_ids(log_file_ids, TaskTypeEnum.KV_CACHE_LOG_EVENT_DIAGNOSIS_WORKER)
    s_tsk = await TaskPGManager.list_current_tasks_by_op_ids(log_file_ids, TaskTypeEnum.STORE_TRACE_CONTEXT_LOGS_WORKER)
    print(f"  parse 任务数：{len(p_tsk)}, id={[t.id for t in p_tsk]}")
    print(f"  diagnosis 任务数：{len(d_tsk)}, id={[t.id for t in d_tsk]}")
    print(f"  store 任务数：{len(s_tsk)}, id={[t.id for t in s_tsk]}")
    p, d, s = p_tsk[0], d_tsk[0], s_tsk[0]

    all_task_ids = [p.id, d.id, s.id]
    reports = await TaskReportPGManager.list_task_reports_by_task_ids(all_task_ids)
    print(f"  总共拉到 reports 数：{len(reports)}")
    from collections import defaultdict
    rmap = defaultdict(list)
    for r in reports:
        rmap[r.task_id].append(r)
    p.task_reports = rmap[p.id]
    d.task_reports = rmap[d.id]
    s.task_reports = rmap[s.id]

    visible = LogFileService._select_visible_task(p, d, s)
    print(f"  visible_task={visible.task_type.value if visible else None}, status={visible.status if visible else None}")
    print(f"    _task_progress(parse)     = {_task_progress(p)}%  (reports max={max((r.progress for r in p.task_reports), default=0)})")
    print(f"    _task_progress(diagnosis) = {_task_progress(d)}%  (reports max={max((r.progress for r in d.task_reports), default=0)})")
    print(f"    _task_progress(store)     = {_task_progress(s)}%  (reports max={max((r.progress for r in s.task_reports), default=0)})")
    overall = parallel_overall_progress(p, d, s)
    visible_p = task_progress(visible) if visible else None
    print(f"  >>> OVERALL_PROGRESS = {overall:.2f}%")
    print(f"  >>> VISIBLE_PROGRESS = {visible_p:.2f}%" if visible_p is not None else "  >>> NO VISIBLE")


async def scenario_missing_parse_store_reports() -> None:
    """场景B：用户怀疑的点——parse/store 的 reports 没存进去（比如 add_task_report 抛错 create_task 吞了），只有 diagnosis 的 reports 存成功。"""
    print("\n" + "="*80)
    print(" 场景 B：parse/store reports 没存进去，只有 diagnosis 有 reports + SUCCESSFUL_PENDING_REMOVE")
    print("="*80)
    kb_id = "kb-missing"
    lf = await _insert_log_file(kb_id, "missing-reports.log")
    parse_task = await _insert_task(lf.id, TaskTypeEnum.KV_CACHE_LOG_PARSE_WORKER, TaskStatusEnum.RUNNING)
    diagnosis_task = await _insert_task(lf.id, TaskTypeEnum.KV_CACHE_LOG_EVENT_DIAGNOSIS_WORKER, TaskStatusEnum.SUCCESSFUL_PENDING_REMOVE)
    store_task = await _insert_task(lf.id, TaskTypeEnum.STORE_TRACE_CONTEXT_LOGS_WORKER, TaskStatusEnum.RUNNING)

    # 故意不写 parse/store 的 reports！（模拟 BaseWorker.report 抛错 / 异步 create_task 没等到就退出子进程）
    # 只写 diagnosis 的 reports：initialized → 5% → 80% → 100%
    await _insert_report(diagnosis_task.id, 0.0, "Task initialized")
    await _insert_report(diagnosis_task.id, 5.0, "运行任务")
    await _insert_report(diagnosis_task.id, 80.0, "故障定界完成，等待Trace上下文落库任务处理")
    await _insert_report(diagnosis_task.id, 100.0, "任务成功")

    log_file_ids = [lf.id]
    p_tsk = await TaskPGManager.list_current_tasks_by_op_ids(log_file_ids, TaskTypeEnum.KV_CACHE_LOG_PARSE_WORKER)
    d_tsk = await TaskPGManager.list_current_tasks_by_op_ids(log_file_ids, TaskTypeEnum.KV_CACHE_LOG_EVENT_DIAGNOSIS_WORKER)
    s_tsk = await TaskPGManager.list_current_tasks_by_op_ids(log_file_ids, TaskTypeEnum.STORE_TRACE_CONTEXT_LOGS_WORKER)
    print(f"  parse 任务数：{len(p_tsk)}, id={[t.id for t in p_tsk]}")
    print(f"  diagnosis 任务数：{len(d_tsk)}, id={[t.id for t in d_tsk]}")
    print(f"  store 任务数：{len(s_tsk)}, id={[t.id for t in s_tsk]}")
    p, d, s = p_tsk[0], d_tsk[0], s_tsk[0]

    all_task_ids = [p.id, d.id, s.id]
    reports = await TaskReportPGManager.list_task_reports_by_task_ids(all_task_ids)
    print(f"  总共拉到 reports 数：{len(reports)} (应只有diagnosis的4条)")
    from collections import defaultdict
    rmap = defaultdict(list)
    for r in reports:
        rmap[r.task_id].append(r)
    p.task_reports = rmap[p.id]
    d.task_reports = rmap[d.id]
    s.task_reports = rmap[s.id]

    visible = LogFileService._select_visible_task(p, d, s)
    print(f"  visible_task={visible.task_type.value if visible else None}, status={visible.status if visible else None}")
    print(f"    _task_progress(parse)     = {_task_progress(p)}%  (reports={len(p.task_reports)})")
    print(f"    _task_progress(diagnosis) = {_task_progress(d)}%  ← SUCCESSFUL_PENDING_REMOVE 短路=100")
    print(f"    _task_progress(store)     = {_task_progress(s)}%  (reports={len(s.task_reports)})")
    overall = parallel_overall_progress(p, d, s)
    visible_p = task_progress(visible) if visible else None
    print(f"  >>> OVERALL_PROGRESS = {overall:.2f}%")
    print(f"  >>> VISIBLE_PROGRESS = {visible_p:.2f}%" if visible_p is not None else "  >>> NO VISIBLE")
    if overall >= 100:
        print("  ❌  异常：整体进度已到 100%，但 parse/store 实际都没 reports！")
    else:
        print("  ✅  还没到 100%。diagnosis 短路 100% 但另外两个没数据，整体被拉低")


async def scenario_false_success_all() -> None:
    """场景C：三个任务的 status 都被改成 SUCCESSFUL_PENDING_REMOVE（比如 stored=False/吞异常仍强行改），但实际 reports 还没推到对应进度。"""
    print("\n" + "="*80)
    print(" 场景 C：所有三个任务 status=SUCCESSFUL_PENDING_REMOVE，但实际业务还在跑 reports 只到一半")
    print("="*80)
    kb_id = "kb-false-success"
    lf = await _insert_log_file(kb_id, "false-success.log")
    parse_task = await _insert_task(lf.id, TaskTypeEnum.KV_CACHE_LOG_PARSE_WORKER, TaskStatusEnum.SUCCESSFUL_PENDING_REMOVE)
    diagnosis_task = await _insert_task(lf.id, TaskTypeEnum.KV_CACHE_LOG_EVENT_DIAGNOSIS_WORKER, TaskStatusEnum.SUCCESSFUL_PENDING_REMOVE)
    store_task = await _insert_task(lf.id, TaskTypeEnum.STORE_TRACE_CONTEXT_LOGS_WORKER, TaskStatusEnum.SUCCESSFUL_PENDING_REMOVE)

    # reports 里实际都只写了一半进度（实际没跑完）
    await _insert_report(parse_task.id, 20.0, "Log parse completed")
    await _insert_report(diagnosis_task.id, 80.0, "故障定界完成，等待...")
    await _insert_report(store_task.id, 65.0, "Waiting for parse task")

    log_file_ids = [lf.id]
    p_tsk = await TaskPGManager.list_current_tasks_by_op_ids(log_file_ids, TaskTypeEnum.KV_CACHE_LOG_PARSE_WORKER)
    d_tsk = await TaskPGManager.list_current_tasks_by_op_ids(log_file_ids, TaskTypeEnum.KV_CACHE_LOG_EVENT_DIAGNOSIS_WORKER)
    s_tsk = await TaskPGManager.list_current_tasks_by_op_ids(log_file_ids, TaskTypeEnum.STORE_TRACE_CONTEXT_LOGS_WORKER)
    p, d, s = p_tsk[0], d_tsk[0], s_tsk[0]

    all_task_ids = [p.id, d.id, s.id]
    reports = await TaskReportPGManager.list_task_reports_by_task_ids(all_task_ids)
    from collections import defaultdict
    rmap = defaultdict(list)
    for r in reports:
        rmap[r.task_id].append(r)
    p.task_reports = rmap[p.id]
    d.task_reports = rmap[d.id]
    s.task_reports = rmap[s.id]

    visible = LogFileService._select_visible_task(p, d, s)
    print(f"  visible_task={visible.task_type.value if visible else None}, status={visible.status if visible else None}")
    print(f"    _task_progress(parse)     = {_task_progress(p)}%  ← SUCCESSFUL_PENDING_REMOVE 短路100，实际reports max=20")
    print(f"    _task_progress(diagnosis) = {_task_progress(d)}%  ← SUCCESSFUL_PENDING_REMOVE 短路100，实际reports max=80")
    print(f"    _task_progress(store)     = {_task_progress(s)}%  ← SUCCESSFUL_PENDING_REMOVE 短路100，实际reports max=65")
    overall = parallel_overall_progress(p, d, s)
    visible_p = task_progress(visible) if visible else None
    print(f"  >>> OVERALL_PROGRESS = {overall:.2f}%")
    print(f"  >>> VISIBLE_PROGRESS = {visible_p:.2f}%" if visible_p is not None else "  >>> NO VISIBLE")
    if overall >= 100:
        print("  ❌  异常：OVERALL=100%，但三个任务的真实 reports max 分别只有 20/80/65！")
        print("      ← 这就是用户看到的：进度100%但任务没跑完！")


async def main() -> None:
    PGManager.initialize(DSN, pool_size=2, max_overflow=5)
    try:
        await init_postgresql_database()
        print("PG 建表、分区、索引完成")
        await scenario_normal()
        await scenario_missing_parse_store_reports()
        await scenario_false_success_all()
    finally:
        await PGManager.close()


if __name__ == "__main__":
    asyncio.run(main())
