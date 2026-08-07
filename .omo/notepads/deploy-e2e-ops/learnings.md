# witty-ub 部署与端到端验证操作手册

> 本手册记录 witty-ub 正确的一键部署、API 端到端验证流程，以及过往踩过的坑。
> 任何涉及"部署"或"验证"的操作必须先读本手册，避免重复犯错。

---

## 1. 正确的一键部署流程

### 1.1 前置：本地/服务器 PostgreSQL 准备

deploy.sh **不会**创建数据库和用户，需要预先就绪：

```bash
# 以 postgres 超级用户执行（服务器上用 sudo -u postgres 或 root）
CREATE ROLE "witty-ub" LOGIN PASSWORD 'witty-ub';
CREATE DATABASE "witty-ub" OWNER "witty-ub";
GRANT ALL ON ALL TABLES IN SCHEMA public TO "witty-ub";
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO "witty-ub";
```

> ⚠️ 如果是从旧版本升级，数据库里可能残留旧的 `time_window_aggregated`
> RANGE 分区表。这是正常情况，后端启动时的 `migrate_timestamptz_to_timestamp()`
> 已修复为跳过分区键列（见 `src/plugins/latency/database/init.py`），不会崩溃。

### 1.2 配置数据库连接

`config/diagnosis_config.toml` 的 `[db]` 段必须指向实际可用的 PG：

```toml
[db]
pg_host = "127.0.0.1"
pg_port = 5432            # RPM部署常为15432，本地常为5432
pg_database = "witty-ub"
pg_user = "witty-ub"
pg_password = "witty-ub"
```

部署前验证连接：

```bash
PGPASSWORD=witty-ub psql -U witty-ub -h 127.0.0.1 -p <port> -d witty-ub -c "SELECT 1"
```

### 1.3 执行部署

```bash
bash deploy/deploy.sh
```

部署脚本会自动：初始化 PG（已存在则跳过）→ 安装 Python 依赖 → 编译 C++ diag-tool →
部署数据文件 → 启动后端(9772) + 前端(5173)。

### 1.4 部署后必做的健康检查（缺一不可）

```bash
# 1. 后端健康
curl -s http://127.0.0.1:9772/health_check          # 期望 {"status":"ok"}

# 2. 前端可用（很多人只查后端，漏了前端）
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:5173/   # 期望 200

# 3. 后端日志无崩溃
tail -50 .deploy-logs/backend.log | grep -iE "error|exception|traceback"
# 期望：无 startup failed / ProgrammingError / InvalidTableDefinitionError

# 4. 数据库表已建
PGPASSWORD=witty-ub psql -U witty-ub -h 127.0.0.1 -d witty-ub \
  -c "SELECT count(*) FROM information_schema.tables WHERE table_schema='public'"
```

---

## 2. 正确的 API 端到端验证流程（不触发任务竞态）

### ⚠️ 最重要的规则：上传后不要手动调 run！

`POST /log_file/{kb_id}` 上传接口**会自动创建全部 3 个任务**：
parse（日志解析）+ diagnosis（故障定界）+ store（Trace 上下文落库）。

这三个任务由后端 APScheduler（每 5 秒）自动调度执行，**不需要任何额外触发**。
如果此时再调 `PUT /log_file/run/{id}?run=true`，会**多创建一个重复的 parse 任务**，
导致 2 个 parse 并发共享同一个预处理目录 `log_preprocessed_<log_file_id>/`，
产生竞态（半成品目录被另一个任务消费、diag-tool 拿到空目录 → 诊断失败）。

### 2.1 完整验证步骤

```bash
# ── Step 1: 创建知识库 ──
KB_ID=$(curl -s -X POST http://127.0.0.1:9772/log_kb \
  -H 'Content-Type: application/json' \
  -d '{"name":"e2e_test_kb","description":"e2e"}' \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['result']['kb_id'])")

# ── Step 2: 上传日志（local 模式，路径引用不传输文件）──
curl -s -X POST "http://127.0.0.1:9772/log_file/${KB_ID}" \
  -H 'Content-Type: application/json' \
  -d "{\"upload_log_file_configs\":[{\"name\":\"my_logs\",\"source_type\":\"local\",\"source\":\"/path/to/logs\"}]}"
# 返回 log_file_ids，记下它。⚠️ 不要在此之后调 run！

# ── Step 3: 轮询任务状态（等待自动完成）──
# 用 GET /task/{task_id} 逐个查，或 POST /task/list 查该 kb 的任务
# 期望看到 3 个任务：kv_cache_log_parse_worker / kv_cache_log_event_diagnosis_worker
#                   / store_trace_context_logs_worker 最终都 successful

# ── Step 4: 验证数据落库 ──
PGPASSWORD=witty-ub psql -U witty-ub -h 127.0.0.1 -d witty-ub <<EOF
SELECT log_id, count(*) FROM log_parse_result GROUP BY log_id;      -- log_id 应是顶层 log_file.id
SELECT count(*) FROM anomalous_event WHERE log_id='<log_file_id>';
SELECT count(*) FROM src_dst_aggregated_event WHERE log_id='<log_file_id>';
SELECT task_type, status FROM task WHERE op_id='<log_file_id>';      -- 3 任务全 successful
SELECT count(*) FROM trace_failure_event;                            -- 诊断产物
SELECT count(*) FROM log_failure_event;                              -- 诊断产物
EOF

# ── Step 5: 前端页面抽查 ──
# 浏览器打开 http://<host>:5173，确认：日志列表、解析任务进度、折线图、诊断结果
```

### 2.2 验证通过的标准

1. 后端 health_check = ok，前端 HTTP 200
2. 3 个任务全部 `successful`（无 FAILED_PENDING_REMOVE 残留）
3. `log_parse_result.log_id` = 顶层 log_file.id（非 per-file UUID）
4. `trace_failure_event` / `log_failure_event` 有数据（诊断链路通）

---

## 3. 停止与清理

```bash
bash deploy/deploy.sh --stop       # 停止后端+前端
# 清理测试库（可选）
DROP DATABASE IF EXISTS "witty-ub";
DROP ROLE IF EXISTS "witty-ub";
```

---

## 4. 历史踩坑记录（务必避免重犯）

### 坑 1：改动后只做单元级验证就提交 → 服务器部署即崩
- **错误**：`migrate_timestamptz_to_timestamp()` 改动只在临时 PG 里跑了函数，
  没跑完整 `deploy.sh` + 启动。结果服务器（带旧分区表残留）启动时
  `ALTER ... partition key` 崩溃，`InvalidTableDefinitionError`。
- **正确**：任何数据库/启动链路改动，必须本地完整部署 + 启动 + API 全链路，
  并且**预置服务器同款残留数据**（旧分区表带数据）后再提交。

### 坑 2：上传后手动调 run → 触发重复 parse 竞态
- **错误**：测试脚本上传后又调了 `PUT /log_file/run`，多创建 1 个 parse 任务，
  与上传自动创建的 parse 共享预处理目录 → 竞态 → 诊断失败（diag-tool 拿空目录）。
- **正确**：上传接口已自动创建全部任务，**只上传 + 轮询等待**，不手动 run。

### 坑 3：误判诊断失败为"环境时序问题"
- **错误**：诊断任务 failed 时归因"环境时序"，没往竞态方向查。
- **正确**：诊断失败先查 `.deploy-logs/backend.log` 里 diag-tool 的
  `Error reading ... No such file` / 返回码，这些是共享预处理目录被并发消费的铁证。

### 坑 4：验证只覆盖后端，漏掉前端
- **错误**：端到端只 curl 后端 API，从未打开前端页面确认。
- **正确**：前端(5173) 必须启动并抽查（HTTP 200 + 页面内容）。

### 坑 5：并发任务竞态（设计缺陷，待修复）
- `PUT /log_file/run` 接口不做幂等，重复调用会创建重复 parse 任务（`log_file.py:315`）。
- 修复方向：run 时先查该 op_id 是否已有 PENDING/RUNNING 的 parse 任务，有则复用。
- 当前规避手段：流程上只上传、不手动 run。

---

## 5. 故障诊断排障速查

| 症状 | 可能原因 | 排查 |
|---|---|---|
| 后端启动崩溃 `cannot alter column ... partition key` | 旧分区表残留，migrate 撞分区键 | 已修复；确认 init.py 有 pg_partitioned_table 跳过逻辑 |
| 诊断任务 failed，日志 `Error reading ... No such file` | 重复 parse 共享预处理目录竞态 | 检查 task 表是否有重复 parse；只上传不 run |
| 诊断任务 failed，`定界工具运行失败，返回码: -6` | diag-tool 收到空/半成品日志目录 | 同上 |
| 折线图稀疏 / 按 log_id 查不到 | 历史数据 log_id 错位（per-file UUID） | 已修复；重新解析后 log_id=顶层 log_file.id |
| 前端打不开 | 只启动了后端 | `bash deploy/deploy.sh --start` 补启动前端 |
