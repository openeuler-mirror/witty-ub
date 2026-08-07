# Learnings — trace-index-aggregation-rewrite

Conventions, patterns, and successful approaches discovered during work on this plan.

_Auto-scaffolded by /start-work. Append new entries below - never overwrite._

---

## 2026-08-04 Task 1 (删 build/关联 + 删滑窗 detect + run() 适配) — DONE
- parse_log now returns 1 value `dict[str, dict[str, list]]`; run() 2-tuple unpack updated at only prod
  call site. Test files still unpack 2-tuples but pytest.ini-ignored (Todo 6 deletes/adapts).
- Backfill (D1 replacement): run() iterates `anomalous_tids`, resolves src/dst from **URMA→RemotePull→""**
  chain (same source as generate_aggregate_result) — NEVER first-SDK entry (SDK tuples lack SRC_ADDR/DST_ADDR).
- Empty gate must be `len(trace_index.get("SDK access parse", []))`, NOT `if not trace_index` (dict always
  has label keys).
- Only prod residual: `schemas/ds_log.py:42 class CorrelationResult` (no producer/consumer) → Todo 6.
- Baseline: 8 pre-existing failures (test_task_progress 4 + test_latency_metrics_query 4), revert-verified
  unrelated. Smoke: e2e-test-100m 4.18s → 347,471 SDK entries, single dict, SMOKE_OK.
- bucket stats call removed from parse_log (consumed deleted `results`) — re-attach in Todo 5 from
  field-table source, keep degraded try/except.
- Deleting a package requires removing module-level imports (worker :48 AnomalyDetector) too; scrub
  stale __pycache__/*.pyc for deleted packages (done).

## 2026-08-04 Task 2 (一次切片 → 每片三路并行产出:字段表 + 聚合 + bucket) — DONE
- **一次切片三路共享**:`_shard_trace_index`(stride `items[i::n]`)切一次 → `_worker_process_shard` 单遍产出
  ①字段表片(list[LogParseResultDataclass])②聚合片③bucket 分位片;`_merge_and_finalize` 三路合并返回 6-tuple。
- **Backward-compat**:`generate_aggregate_result` 保留 4-tuple 返回(包 `_aggregate_three_way`),`run()` 走
  `_aggregate_three_way`(6-tuple,含 field_table + bucket_merged)。test_integration_pipeline/run_e2e_log_parse/
  bench_aggregate_parallel 全解 4-tuple,零改动。
- **字段表构造**:`_extract_trace_metrics`(逐 trace 提取,None=跳过:无 SDK 或 elapsed<0)+ `_make_field_row`
  (复用 `_resolve_snapshot` + query_meta→worker_query_meta remap + c2w_latency 派生)+ `_build_field_table_rows`
  (串行 golden 参考)。src/dst 取源统一 = URMA→RemotePull→"" 链(SDK 无 SRC_ADDR/DST_ADDR)。
- **c2w_latency 派生**:`max(0, sdk_elapsed_us − worker[0].elapsed_us)/1000`(result_builder.py:496-505 语义);
  worker 配对细节 worker_idx_get/SET create+publish 无法从 trace_index 复现 → 用首条 Worker access entry,
  golden fixture 记录该偏差。无 Worker access → None。
- **串行回退**:`_workers < 2 或 len(trace_index) <= 10000 或 len <= _workers` → 直接进程内
  `_worker_process_shard(trace_index, ...)`(不 spawn)。删掉了旧 generate_aggregate_result 主进程 first-pass
  循环(并行路径的重复劳动)。
- **三路 worker 的坑**:函数内 `from ... import _worker_process_shard` 会把模块全局变成局部名 → 串行路径
  引用时 UnboundLocalError。修法:去掉局部 import,直接引用模块全局(模块加载完后才调用,运行时解析 OK)。
- **ProcessPoolExecutor(spawn)细节**:`functools.partial(_worker_process_shard, threshold_ms=..., log_file_id=...)`
  可 pickle;返回 dict 含 LogParseResultDataclass 实例(已验证 pickle 往返);子进程 `_init_child_pgmanager()`
  try/except 防御式重初始化(PG 非切片计算必需)。
- **bucket 分位片**:`_compute_slice_bucket_picks`(进程内 numpy,无嵌套 spawn)对片内 field_table 行做
  C0-C3(过滤/桶号/lexsort+group edges/argpartition 选 5 分位),返回 {granularity: [(bucket_start_dt, op_code,
  mode_name, row), ...]};合并=按粒度 concat(每片独立算分位,跨片重复 (bucket,op) 组是 Todo 5 已接受的近似)。
  Todo 5 消费 merged bucket + 写 4 张 latency_bucket_* 表(本任务不写库)。
- **字段表 merge 保序**:片内行保 SDK entry 顺序;跨片按 shard 顺序 concat(≠ 原 dict 序)。golden fixture
  用 trace_id 建 dict 逐字段比较(排除 created_at 墙钟时间戳,每片自生成,并行≠串行)。
- **明细行**:`[r for r in field_table if r.trace_id in anomalous_tids]` + `is_anomalous=True` + 直接
  `sdmap.get((r.src_ip or '', r.dst_ip or '', op_key))` 回填(字段表行已带统一源 src/dst/op,不再从
  trace_index 二次解析)。`_build_anomalous_detail_rows` 保留给 legacy 测试,run() 已不调用。
- **验证**:`test/test_time_window_aggregation.py + test_api_unit.py + test_field_table_slice.py` 76 passed
  (.venv + /usr/bin/python3.12 双跑);8 个预存失败(test_task_progress 5 + test_latency_metrics_query 3)与本
  任务无关未修;test_database_unit.py 预存 ImportError(AsyncSQLiteSingleton 已删)与本任务无关。
- **遗留**:bucket 写库在 Todo 5;numpy 聚合(p99/latency_sum)在 Todo 3;`_build_anomalous_detail_rows`/
  `_process_tw_chunk`/`_time_bucket_10s` Todo 3 删(plan 明示)。

## 2026-08-04 Task 3 (time_window / src_dst numpy 聚合 + 碰撞桶 p99 合并) — DONE
- **每片 numpy 聚合**:新增模块级 `_aggregate_slice_numpy`(子进程可 pickle),替代 `_worker_process_shard` 内
  的 dict 累加循环。流程:每 trace 循环(必须保,供字段表行 + 异常判定)收集 7 个平行数组(src/dst/op 字符串、
  bucket_epoch int、total_ms float、anomaly 0/1、log_id)→ numpy 分组。
- **编码**:src/dst 用 `np.unique(return_inverse=True)` 编码 int;op 同样 unique(0/1);IP None 已在
  `_extract_trace_metrics` 归一为 `""`,`np.unique` 保留该字符串 → 输出键 `("","",op)` 与生产键一致。
- **复合键 int64 安全**:sd_key = ((src_id * n_dst + dst_id) * 2 + op_id);tw_key = ((src_id * n_dst + dst_id)
  * k + bucket_shift),k = max(bucket_shift)+1。n_dst/组数 ≪ 1e5,bucket ~1.7e8(2025 年),组合 < 2e13,远小于
  int64 上限。
- **bucket 编码**:`_bucket_epoch_10s`(新)返回 10s 对齐 epoch int(替代 `_time_bucket_10s` 的 str),不可解析
  ts → None(聚合侧归入 `time_bucket=""`);`_format_bucket_epoch(epoch)` 转 `YYYY-MM-DD HH:MM:SS`。
  **删除 `_time_bucket_10s` + `_process_tw_chunk`**(plan 明示,grep 无残留)。
- **reduceat**:按 tw_key 稳定 argsort(order=argsort(kind="stable"))→ np.unique(return_index=True) 得组起点 →
  `np.add.reduceat` 算 anomaly 和 lat_sum;cnt = diff(edges);首 log_id = `log_id_arr[order[s]]`(稳定排序组内
  首个 = 原迭代首个,与旧 `if not first_log.get` 语义一致)。**per-group Python 循环是 O(groups) 非 O(rows)**。
- **异常 dict 只存正数**:`np.bincount` 会为所有组生成 0 计数键;旧循环只在 is_anomalous 时 +1 才建键。
  过滤 `if anom_i:` 后 anomaly dict 与旧语义逐键相等(golden fixture 断言)。
- **ave/p99**:tw 行 `ave = lat_sum/cnt`、`p99 = _p99_from_values(lat_list)`。p99 用 `np.percentile(x, 99)`
  (线性插值),与查询侧回退 `percentile_cont(0.99)`(time_window_aggregated_event.py:238)一致——Todo 4 物化
  p99 与回退 SQL 对齐。空桶 → None。
- **_merge_and_finalize 碰撞桶**:非碰撞沿用片内预计算行(已带 p99);碰撞从 `merged_tw_buckets[key]` 合并
  latency 列表统一算 ave + p99(p99 无法从 sum/cnt 合并得出)。golden 断言:合并 [1.0,3.0] → ave 2.0, p99
  = np.percentile([1,3],99) = 2.98。
- **dual-track 已死**:旧 generate_aggregate_result 的 Python 循环 + ProcessPoolExecutor 双轨分支在 Todo 2
  已被 `_aggregate_three_way`(一次切片 + 串行回退)替代,grep 确认无残留(仅 `_aggregate_three_way` 内的
  单一路径 ProcessPoolExecutor + 回退)。
- **numpy 桶转换测试**:test_time_window_aggregation.py 的 `_time_bucket_10s` 测试改测 `_bucket_epoch_10s`
  (epoch int,2025-01-01 12:00:00 = 1735732800)+ `_format_bucket_epoch` 字符串往返。
- **golden fixture**:`_python_reference_aggregate`(旧循环语义规范)在测试里实现并断言 == `_aggregate_slice_numpy`
  输出(sd_total/sd_anomaly/sd_first/tw_buckets/tw_anomaly/tw_first/anom_tids/ave);p99 断言 == np.percentile。
  `_compute_slice_bucket_picks` 对垃圾 ts 会崩(statistics.py 既有限制,C0 只过滤 None),真实日志 ts 恒可解析,
  本任务不修(桶统计是 Todo 5 换源范围)。
- **验证**:test_field_table_slice.py(15)+ test_time_window_aggregation.py(11)+ test_api_unit.py(54)全过
  = 80 passed(.venv + /usr/bin/python3.12 双跑);预存 8 失败(test_task_progress 5 + latency_metrics 3)不变。
- **遗留**:p99 落库(schema 列/DDL/COPY/SQL/ip_pair 透传)是 Todo 4;bucket 换源写库是 Todo 5;`_build_
  anomalous_detail_rows` 保留给 legacy 测试(run() 已用字段表过滤)。

## 2026-08-04 Task 5 (bucket 折线图切片并行 + 换源) — DONE
- **重挂方式**:`compute_and_store_bucket_stats` 从 parse_log 移到 run();新增降级包装
  `_store_bucket_stats_degraded(log_id, kb_id, rows=field_table, task_id, tables)`——statistics.py
  本身打 FAILED 点后 re-raise,包装层 catch+log 返回 None,保证 bucket 失败不阻塞明细/聚合落库
  (parse_log 原 :706-714 try/except 语义迁移)。调用点=detail 行回填后、store_result 前。
- **换源**:rows 参数 = `_aggregate_three_way` 6-tuple 第 5 元素 field_table(list[LogParseResultDataclass]
  全 trace,切片并行产物),替代被删 results。statistics.py 无需改动(`rows: Sequence[Any]` 契约已兼容)。
- **切片并行**:复用 `_parallel_pick` 内部 `_split_into_segments` 按 (桶,op) 组边界切片 + spawn
  shared_memory argpartition,pool_size=1(串行)与 pool_size=4(并行)写同 log_id 表内容全等。
- **Todo 2 遗留权衡**:`_compute_slice_bucket_picks`/`bucket_merged` 保留(三路 worker 契约被
  test_field_table_slice.py 断言),但 run() 现在只用字段表喂 compute_and_store_bucket_stats,
  片内 bucket picks 只剩日志用途(冗余 CPU,后续 Todo 6 store_result gather + 零残留时清理)。
- **测试 4 连**:golden(100 行单组 [0..99] → 分位 [49,94,98,98,99] 手算,4 档粒度全等,无 epoch-0 桶)、
  换源(真实 _build_field_table_rows 400 trace → 包装 → 临时表 4 档非 0)、并行==串行(临时表内容
  ORDER BY bucket/operation/mode 全等)、降级(monkeypatch worker 模块全局 compute_and_store_bucket_stats
  抛异常 → 包装返回 None 不传播)。
- **验证**:bucket/test_bucket_statistics.py 11 passed + 回归(field_table_slice/time_window/api_unit)80
  passed(.venv);grep 确认 parse_log 0 处 compute_and_store_bucket_stats、run() 1 处。裸
  /usr/bin/python3.12 缺 pytest-asyncio → async 测试全挂是环境问题(文件头文档化测试环境=.venv)。
- **降级包装引用模块全局名**:函数内局部 `from ... import compute_and_store_bucket_stats` 会
  UnboundLocalError(Todo 2 同坑),必须引用模块级 import 名(monkeypatch 也因此可打点模块属性)。

## 2026-08-04 Task 4 (time_window 落库 latency_sum + p99,schema 完整 ip_pair 承载) — DONE
- **7 点位全通**:①dataclass 只加 latency_sum(p99 已在 :778)②models.py 加两列③init.py
  _MISSING_COLUMN_DDL 加两行(ALTER ADD COLUMN IF NOT EXISTS 幂等,防旧 DB COPY 缺列)
  ④COPY 列(:39)加两字段(13 列与 copy tuple 顺序一致)⑤写路径 _event_to_mapping/:78
  copy tuple 均透传⑥聚合 SQL 加 p99 = percentile_cont(0.99) within group + ave 改
  sum(COALESCE(latency_sum, ave_total_latency*cnt))⑦list SQL 透传 p99 + _rows_to_events
  ip_pair 字典加 p99_total_latency(逐行透传 row.p99)。
- **区间重聚合语义(已文档化)**:interval=10s 组内单行 → p99 原样透传(物化值);
  60/600/3600 = 桶内各 10s 行 p99 取 p99(p99-of-p99s,SQL percentile_cont 线性插值,近似);
  旧行全 NULL 组 → p99 None 前端显示空。percentile_cont(0.99) within_group 单公式同时
  满足两种语义(10s 是退化情况)。
- **旧行守卫 = SQL COALESCE 而非 backfill**:当前 worker 只物化 ave/p99 不产 latency_sum,
  所以 latency_sum 恒 NULL → 逐行 COALESCE(latency_sum, ave*cnt) 恒走 ave*cnt(=lat_sum),
  SQL 结果与改动前一致,天然向后兼容。sum(COALESCE(逐行)) 优于 COALESCE(sum(latency_sum),...)
  ——后者在混合新旧行时 sum(latency_sum) 非 NULL 不会回退,会算错。
- **slots dataclass 删字段会 AttributeError**:test_integration_pipeline.py:287 直接访问
  tw 事件 max_total_latency(已删)会崩 → 改 getattr(..., None)(值恒 None,断言语义不变)。
  删除 min/max/p95 只动 dataclass;TimeWindowAggregatedIpPair/EventModel(Pydantic 响应)
  保留原字段(默认 None 序列化为 null,前端不变,零回归)。
- **验证**:time_window_aggregation(12)+ field_table_slice(15)+ api_unit(54)全过 = 81;
  批量 86 passed;SQL 编译验证 percentile_cont/COALESCE 渲染正确;test_postgresql_
  integration 3 failed 为环境 PG down(ConnectionRefused)非改动;预存 8 失败不变。
- **遗留**:latency_sum 列已就位但无生产写入方(Todo 6 落库 gather + 前端核对时由未来
  写路径填充,或保持 COALESCE 兜底);p99 落库后前端详情卡片 ip_pair p99 路径 b 已通。

## 2026-08-04 Task 6 (store_result gather 并行 + 死代码零残留 + 测试适配/删除) — DONE
- **gather 并行**:store_result 三表(log_parse_result/src_dst/time_window)改
  asyncio.gather(return_exceptions=True)并行,每表独立协程;单表失败仅记日志置
  success=False;time_window kb_id 回填在 gather 前;bucket×4 仍由
  _store_bucket_stats_degraded 单独写(降级语义,不入 gather)。
- **死代码**:store_trace_context_logs/_collect_context_trace_ids/_is_failure_result/
  _is_timeout_result + TRACE_CONTEXT_TIMEOUT_THRESHOLDS_MS 常量 + import
  (LogParseResultModel/SparseLogParseResultDataclass/collect_trace_context_logs)
  全删;StoreTraceContextLogsWorker 独立同名方法不受影响(删前 grep 确认)。
- **import 残留**:schemas/ds_log.py CorrelationResult 删(保留 TupleField 再导出,
  worker :44 依赖);parse/correlation 与 detect 空目录 rmdir;import latency.parse 走通。
- **测试**:test_result_builder_optimized.py + bench_aggregate_parallel.py 删(测已删代码),
  test_detection_optimized.py 已由 Todo 1 删;pytest.ini 清悬空 --ignore。
- **适配**:test_kv_cache_log_parse_worker.py(parse_log 单值/_parse_target 双模式/
  store_result 新签名)、test_kv_cache_log_parse_worker_profile.py(删
  builder_line_sample 全套 + install/restore 去 LogCorrelator/ParseResultBuilder
  monkeypatch + 新 API)、test_log_parser.py(LogEntry→TupleField 元组后走
  _aggregate_three_way,slots dataclass 用 asdict 不用 vars)、
  test_integration_pipeline.py(_run_full_pipeline_standalone store_result 去
  anomalous_events/chains 参数)。
- **test_api_full_content 预存缺陷**:种子 src_dst event 缺 kb_id,而 _list_by_kb
  fastpath 按 kb_id 过滤→total=0;种子补 kb_id 一行修复(与 time_window 种子一致)。
- **环境迁移**:本地 PG(127.0.0.1:5432 witty-ub)表缺 Todo 4 列 → 对运行库执行
  database/init.py _ensure_missing_columns()(idempotent ALTER)后 test_api_full_content
  32 全过。
- **验证**:124 passed(field_table_slice 15+time_window_aggregation 12+api_unit 54+
  bucket_statistics 11+api_full_content 32)+ integration synthetic 8;
  store_result gather 真实 PG 三表并行写验证;e2e-100m 冒烟 parse/anomaly/aggregate/
  log_parser 全跑通;grep 零残留。
- **遗留**:profile 测试 worker .prof 合并失败 = scanner 多进程 cProfile 产 2-byte
  损坏文件(process_worker.py 未改动,预存工具缺陷);PG 3 failed + 预存 8 failed 不修。

## 2026-08-04 Task 7 (e2e + 零残留验证 + 前端) — DONE
- **OOM 根因确认**:Todo 7 上次卡死 = data/logs/daas/ 1.1GB~3.4GB 真实数据喂进
  scan + multiprocessing 聚合(主进程 4.9GB + 4 spawn 子进程 ~14GB → 15GB 爆)。
  **解法**:e2e 用 e2e-test-100m(106MB)symlink 布局零复制;test_integration_pipeline.py
  (硬编码 3.4GB)不跑——OOM 元凶,等价语义由 test_field_table_slice 并行一致性覆盖。
- **任务队列阻塞**:陈旧 pending 任务(指向已删 /tmp/test.log)卡住 task_handler,
  按序消费永远不前进。解法:清空 PG task/log_file 表只留新任务 → 一次解析 successful。
- **前端验证**:npm run dev → Vite 5173;chromium headless dump-dom 确认页面完整渲染
  (资产列表 t7_e2e + 时延/通断监控章节 + 筛选条件 + Trace 看板);当前模型不支持图像,
  用 DOM 文本 + API 数据源双重验证。Playwright MCP server 本机不可用(无全局包)。
- **详情卡片 P99 验收通**:time_window ip_pair p99_total_latency=1.36016 非空(路径 b);
  顶层 1min 聚合 p99=null 属正常(10s 行再聚合,前端读 ip_pair)。
- **落库数据达标**:log_parse_result=30(≥30)✓ src_dst=2(≥2)✓ time_window=8124(≥100)✓
  metrics/latency 404 点(时延趋势图)。
- **测试取舍(用户要求)**:只测接口+模块+集成验证;砍 deploy 脚本类杂项;
  test_database_unit.py 测已删 SQLite 引擎(AsyncSQLiteSingleton)→ 过期剔除。

## 2026-08-04 F2/F4 评审后缺陷修复 + 并行=串行实证(用户主导) — DONE
- **并行 vs 串行实证(bg_eca8b414,真实 347k 数据)**:time_window 1210 组全部
  ≤1e-9 一致(753 组逐位精确;457 组 ave 差 ~3.6e-16 = Python sum 左到右 vs
  numpy pairwise 求和顺序的 IEEE-754 结合律,非数据错);p99 逐位精确(排序同多集);
  src_dst 2 组 / anomalous_tids 30 / field_table 347,471 行全部精确一致。
  **结论:桶碰撞合并是精确的,不是近似**——桶号纯函数 + stride 切片不重叠 +
  碰撞桶拼 latency 重算。测试 test_parallel_aggregate_slices_equal_serial 15/15。
- **实证挖出真 bug(bucket_picks 并行翻倍)**:第 6 输出 bucket_picks 并行时恰好
  2× 串行(每片从局部样本选 10 代表行,merge 只 extend 不去重不重算)。
  生产 run() 不消费它(latency_bucket_* 由 _store_bucket_stats_degraded 从
  field_table 重算,field_table 已证并行==串行)→ 折线图数据是对的,但该腿
  既是白算又是错算 → **删除整条腿**:_compute_slice_bucket_picks 函数 +
  _worker_process_shard 调用 + _merge_and_finalize merged_bucket 拼接;
  _aggregate_three_way/_merge_and_finalize 6→5 元组;测试 4 文件适配。
- **P1 latency_sum 未写**:两构造点(_aggregate_slice_numpy / _merge_and_finalize
  碰撞桶)补 latency_sum=lat_sum;列真正落库,SQL COALESCE 兜底不再承担全部。
- **P2-3 删 _init_child_pgmanager()**:片内不用 PG,spawn 子进程白初始化。
- **P2-4 NULL ave 当 0**:_rows_to_events 改 row.ave is None 时跳过,不进 _ave_den。
- **P2-5 int64 复合键溢出守卫**:src_dst + time_window 键估算超 9.22e18 显式
  raise OverflowError(防 >1e4 IP/侧 静默环绕合并错组);守卫顺序正确
  (bucket_shift 先定义再算 tw 键估算)。
- **P2-1 原判暂缓被实证推翻**:实证给出新理由(并行翻倍 bug + 生产不消费),
  从"可选优化"变"修 bug",已删。

## 2026-08-04 部署脚本实测 + 修复 + 规范对照 — DONE
- **实测踩坑 5 个 bug(已修)**:
  1. deploy.sh 后端启动失败(InvalidPasswordError)仍 exit 0 假报"部署完成"→ start_services
     健康检查失败 return 1 + set -e 传播
  2. deploy_pg.sh --apt 静默把系统 PG 端口 5432 改成 15432(既有部署失效)→ 端口冲突
     检测 + confirm(非 TTY 自动继续)
  3. pg.conf 密码 witty-ub 与仓库 config pg_password="" 脱节 → 后端连不上 →
     新增 sync_pg_credentials(部署后从 pg.conf 同步凭据到仓库 + /var 两份 config)
  4. manage.sh 本地模式 do_restart_local 假设 systemd user 服务,但 deploy.sh 起的是
     nohup 裸进程 → 后端重启必然失败 → 新增 restart_backend_bare(按端口找进程 +
     杀 + nohup 重启 + 健康检查)回退
  5. deploy.sh start/stop 用 pkill -f "fastapi_server" 宽泛误杀 → 改精确 PID 文件 + fuser 端口
- **回归**:重跑 deploy.sh 全流程通过——后端旧 PID 被杀、新 PID 33264 健康检查通过、
  能查 402 条数据、前端 5173 正常、sync_pg_credentials 正确同步两份 config
- **规范对照(73 项清单,10 类)**:架构合理(分层:deploy.sh 编排/deploy_pg.sh PG/
  manage.sh 运维/deploy_witty.sh 应用),P0 全修,P1 遗留:set 选项不统一(3 脚本缺
  -u -o pipefail)、PG_PASSWORD 硬编码 pg.conf、无 trap 清理/回滚/备份、npm install 应
  换 npm ci;P2:缺磁盘/端口前置检查、无 daemon-reload、无 secret 脱敏
- **环境变化**:系统 PG 端口被脚本从 5432 改到 15432(witty-ub 数据完好 402 条),
  后端/前端现由 deploy.sh 管理
