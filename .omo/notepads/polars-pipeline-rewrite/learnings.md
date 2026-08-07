# Learnings — polars-pipeline-rewrite

Conventions, patterns, and successful approaches discovered during work on this plan.

_Auto-scaffolded by /start-work. Append new entries below - never overwrite._

---

## 2026-08-05 - T8 E2E: 抓到 2 个真 bug 并修复

### Bug 1 (部署环境, 非代码): systemd 服务用系统 python → polars ImportError
- 症状: parse worker 4 次重试后 failed, journald `ModuleNotFoundError: No module named 'polars'`(trace_frame.py:64)
- 根因: `~/.config/systemd/user/witty-ub-backend.service` ExecStart=`/usr/bin/python3`(系统 python 无 polars)。T7 前 numpy 路径不依赖 polars 所以没暴露。
- 修复: ExecStart → `.venv/bin/python`(已验证 venv 依赖完整: fastapi/uvicorn/asyncpg/sqlalchemy/polars/numpy)
- 教训: 部署环境必须用 venv python;T0 M1(polars 进 requirements.txt)已落实,但服务解释器是另一回事。

### Bug 2 (产品代码, 历史遗留): 聚合事件 log_id 用了扫描器随机文件 id
- 症状: 任务 successful 但 `SELECT count(*) FROM src_dst_aggregated_event WHERE log_id='<顶层log_file.id>'` = 0; 表里 log_id 是随机 uuid(如 208ed358...)
- 根因链: `process_worker.py:541` 每次 `LogFileModel(file_path=...)` 新建 → id=uuid4 随机 → `entry.log_id = log_file.id`(:608) → df_trace.log_id=随机 id → `_aggregate_polars` 用 `pl.col("log_id").drop_nulls().first()` 当事件 log_id → API 按顶层 log_file.id 永远查不到
- 证明: bucket 表正常(显式传 task.op_id),聚合表全错(用 first_log) → 问题只在聚合事件
- 修复: `_aggregate_polars` src_dst/time_window 事件 `log_id = log_file_id or first_log or ""`(run() 已传 log_file_id=task.op_id)。2 行。
- 测试: `test_polars_pipeline_parity.py` 排除 log_id 字段(golden 捕获旧语义) + 新增 `test_aggregate_log_id_binds_log_file_id` 断言 log_id==log_file_id
- 教训: parity 测试用 fixture(entry.log_id="log1" 固定)没覆盖真实目录随机 id 场景 → 测试盲区。真实 E2E 才能抓到。

### E2E 性能 (data/logs/e2e-test-100m, 347471 traces)
- 扫描 7.9s → 聚合 76ms → 总 8.0s(旧 numpy baseline 155s, ~20x)
- [PERF][AGG] polars traces=347471 sd=2 tw=1210 anom=0 total=76ms
- 明细 log_parse_result=0 是设计行为: e2e-100m 无超阈值 trace (anomalous=0), 只写 anomalous 明细

### 队列卫生 (已有 learnings 复现)
- 崩溃会话遗留 74 个 pending 任务(指向已删 /tmp 与 daas 数据)会饿死调度队列
- 修复: `DELETE FROM task WHERE status IN ('pending','running')` + 孤儿 task_report 清理
