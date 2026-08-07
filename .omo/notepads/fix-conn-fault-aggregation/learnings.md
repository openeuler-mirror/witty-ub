# Learnings — fix-conn-fault-aggregation

## Task 1 (T1): TDD tests for `generate_aggregate_result` — COMPLETE

### What was done
Added 5 tests to `TestPipelineIntegration` in `src/plugins/latency/test/test_integration_pipeline.py`:
1. `test_aggregate_ip_from_urma_fallback` — SDK (no IPs) + `"Worker urma parse"` entry with src_addr="10.0.0.1"/dst_addr="10.0.0.2"
2. `test_aggregate_ip_fallback_to_remote_pull` — SDK + `"Worker remote pull parse"` entry with src_addr="10.1.0.1"/dst_addr="10.1.0.2"
3. `test_aggregate_ip_empty_when_no_urma_or_pull` — SDK-only → src_ip/dst_ip must be `""`
4. `test_aggregate_status_code_anomaly` — SDK elapsed_us=0 (total_ms=0.0), status_code=1 → tid in `anomalous_tids`
5. `test_aggregate_normal_not_anomalous` — SDK elapsed_us=500 (total_ms=0.5), status_code=0 → tid NOT in `anomalous_tids`

### TDD red-phase evidence
Log: `.omo/evidence/fix-conn-fault-aggregation/test-T1.log`
- 3 FAILED: test 1 (`'' == '10.0.0.1'`), test 2 (`'' == '10.1.0.1'`), test 4 (`'trace_conn_fault' in set()`)
- 2 PASSED: test 3 (graceful degrade — IPs already empty), test 5 (normal not anomalous)

### Key facts for the implementation fix (separate task)
- **Fix A** targets `kv_cache_log_parse_worker.py` L1371-1372: `src = (first[TupleField.SRC_ADDR] or "").strip()` reads SDK entry's indices 11/12 (always None). Must fall back to `entries.get("Worker urma parse", [])` then `entries.get("Worker remote pull parse", [])`, reading `TupleField.SRC_ADDR`/`DST_ADDR` (11/12) from the first entry.
- **Fix B** targets L1386: anomaly check is only `if total_ms > threshold_ms:`. Must add `or first[TupleField.STATUS_CODE] != 0` condition (status_code=1 conn-fault traces must be flagged even at total_ms=0.0). Keep `anomalous_tids.add(tid)`, `sd_anomaly_count[sd_key] += 1`, `tw_anomaly_count[tw_key] += 1`.
- Labels verified: `URMA_LABEL = "Worker urma parse"`, `REMOTE_PULL_LABEL = "Worker remote pull parse"` (defined in `parse/worker_info_parser.py` L26-27).
- Tuple is 16 elements in `TupleField` order (`ENUM/ds_log.py`): timestamp, operation, elapsed_us, data_size, object_key, trace_id, pod_ip, status_code, resp_msg, entry_type, cluster_name, src_addr, dst_addr, inflight_count, request_size, log_id. Confirmed against `_serialize_entry` (`parse/parallel_scanner/process_worker.py` L294-312).
- Serial path always taken for tiny indexes: the ProcessPoolExecutor branch needs `len(trace_index) > 10000`.

### Environment quirks
- `tee` to relative path `../../.omo/evidence/...` fails intermittently ("No such file or directory") even when the dir exists — use absolute paths for evidence files.
- Tests run via: `cd src/plugins/latency && PYTHONPATH=$(pwd)/../.. python3 -m pytest ...` (system python3, not .venv).
- basedpyright reports `reportMissingTypeArgument` for untyped `dict` in tests — pre-existing accepted pattern in this file (same in `test_empty_trace_index_produces_empty_results`, `test_trace_with_missing_sdk_label_is_skipped`).

## Task 2 (T2): Fix A (IP resolution) — COMPLETE

### What was done
Applied Fix A to TWO locations in `src/plugins/latency/task/worker/kv_cache_log_parse_worker.py` (only file touched):
1. `generate_aggregate_result` Phase 1 loop (was L1371-1372, 12-space indent) — replaced SDK-index src/dst reads with URMA→RemotePull→empty fallback chain.
2. `_worker_process_shard` Phase 1 loop (was L2001-2002, 8-space indent) — identical block at module-level indentation.

Fallback block content (identical in both):
```python
_urma = entries.get(URMA_LABEL, [])
_pop = entries.get(REMOTE_PULL_LABEL, [])
if _urma:
    src = str(_urma[0][TupleField.SRC_ADDR] or "").strip() or ""
    dst = str(_urma[0][TupleField.DST_ADDR] or "").strip() or ""
elif _pop:
    src = str(_pop[0][TupleField.SRC_ADDR] or "").strip() or ""
    dst = str(_pop[0][TupleField.DST_ADDR] or "").strip() or ""
else:
    src = ""
    dst = ""
```

### Evidence
Log: `.omo/evidence/fix-conn-fault-aggregation/test-T23.log` (absolute-path tee)
- **4 passed, 1 failed** as predicted:
  - PASSED: `test_aggregate_ip_from_urma_fallback`, `test_aggregate_ip_fallback_to_remote_pull`, `test_aggregate_ip_empty_when_no_urma_or_pull`, `test_aggregate_normal_not_anomalous`
  - FAILED (expected, Fix B scope): `test_aggregate_status_code_anomaly` — `assert 'trace_conn_fault' in set()` still empty because anomaly check at L1386 remains `if total_ms > threshold_ms:` only.
- Syntax check: `python3 -c "import ast; ast.parse(...)"` → OK.

### Verification details
- `URMA_LABEL`/`REMOTE_PULL_LABEL` already imported at worker top (L29-31) — no import change needed.
- `TupleField.SRC_ADDR=11`/`DST_ADDR=12` confirmed in `ENUM/ds_log.py`.
- Edits were unambiguous: both locations had identical source lines but different indentation depth (12 vs 8 spaces), so the edit `oldString` matched uniquely per location.
- `_worker_process_shard` is not exercised by the TDD tests (serial path only for tiny trace_indexes; ProcessPool branch requires >10000 traces) — its correctness rests on byte-identical content + full test suite run later.

### Next task (T4+T5: Fix B)
Anomaly check in `generate_aggregate_result` (now around L1407-1411 after Fix A insertion) must become:
`if total_ms > threshold_ms or first[TupleField.STATUS_CODE] != 0:` to make `test_aggregate_status_code_anomaly` pass. `_worker_process_shard` has the analogous check (~L2027-2031) — keep in sync.

## Task 4+5 (T4+T5): Fix B (status_code anomaly detection) — COMPLETE

### What was done
Applied Fix B to TWO locations in `src/plugins/latency/task/worker/kv_cache_log_parse_worker.py` (only file touched; test file untouched):
1. `generate_aggregate_result` Phase 1 loop (now L1397-1405, 12-space indent)
2. `_worker_process_shard` Phase 1 loop (now L2039-2047, 8-space indent)

Replacement block (identical in both, indentation differs):
```python
# ── anomaly check (before anything else) ──
status_code = first[TupleField.STATUS_CODE]
is_anomalous = total_ms > threshold_ms or (
    status_code is not None and status_code != 0
)
if is_anomalous:
    anomalous_tids.add(tid)
    sd_anomaly_count[sd_key] += 1
    tw_anomaly_count[tw_key] += 1
```

Design notes:
- Null-safe: `status_code is not None and status_code != 0` — a None status_code (absent field) does NOT trigger anomaly; only an explicit non-zero value does. Preserves `test_aggregate_normal_not_anomalous` (status_code=0, total_ms=0.5 → not anomalous).
- `first` is `sdk_entries[0]`, `TupleField.STATUS_CODE=7` (confirmed `ENUM/ds_log.py`); `total_ms = elapsed_us / 1000.0` computed above both loops.
- Byte-identity verified programmatically: regex-extracted both blocks, normalized per-line whitespace → `True`; indents [12, 8].

### Evidence
Log: `.omo/evidence/fix-conn-fault-aggregation/test-T45.log` (absolute-path tee)
- **5 passed, 0 failed**:
  - PASSED (were red in T1): `test_aggregate_ip_from_urma_fallback`, `test_aggregate_ip_fallback_to_remote_pull`, `test_aggregate_status_code_anomaly`
  - PASSED (already green, must stay): `test_aggregate_ip_empty_when_no_urma_or_pull`, `test_aggregate_normal_not_anomalous`

### Verification details
- Only run command: `cd src/plugins/latency && PYTHONPATH=$(pwd)/../.. python3 -m pytest <5 tests> -v | tee ...` (system python3, 0.47s).
- lsp_diagnostics on the file: 510 pre-existing basedpyright diagnostics (implicit relative imports, unknown types, etc.) — none reference the new `status_code`/`is_anomalous` lines; no new diagnostics introduced.
- Fix A blocks (URMA→RemotePull fallback, now L1371-1384 / L2013-2026) untouched.
- `threshold_ms`, sd/tw counter logic, and all other logic unchanged.

### Handoff to T6/T7
- T6 (full test suite) and T7 (E2E) come next. `_worker_process_shard` is still not directly exercised by unit tests (serial path only) — rely on byte-identical block + full suite.

## Task 7 (T7): End-to-end live-deployment verification — COMPLETE

### What was done
Ran the conn-fault multi-log scenario (`data/kvcache-conn-fault-log/multi-log/002_005+010+020_002/`, files `ds_client_access.log` + `ds_client_10411.INFO.log`) against the live backend at http://127.0.0.1:9772 via a Python script (fresh KB → upload dir as ONE log_file → `PUT /log_file/run/{id}?run=true` → poll → query 4 endpoint families → psql cross-check).

Evidence: `.omo/evidence/fix-conn-fault-aggregation/test-T7.log` — **RESULT: PASS, 0 failed assertions, 18 PASSes**.

### Key findings (all fix goals verified end-to-end)
- **Fix B verified**: `POST /log_parse_result/list` now returns **4 anomalous conn-fault rows** (`tid-002-005-s3`, `tid-010-s3`; `is_anomalous=True`) — was 0 before the fix. Both traces flagged via status_code≠0 and/or latency>threshold.
- **Fix A verified at data level**: `src_dst_aggregated_event` rows carry `log_parse_result_cnt=2, anomaly_cnt=2` per event (conn-fault anomalies now aggregated). `anomaly_cnt>0` asserted via both API (`aggregated_event/list` total=2, `list_time_window` total=1) and psql.
- **Empty src/dst IPs are EXPECTED for this dataset**: the 2-file scenario contains NO URMA/RemotePull entries, so the Fix A fallback chain (URMA→RemotePull→empty) correctly degrades to `""`. Non-empty-IP proof needs a scenario WITH URMA/worker logs (none ship in the multi-log set — only SDK access + INFO lines). This is the T1 test-3 behavior, not a regression.

### Environment findings (pre-existing, NOT caused by T2-T5)
1. **Stale `/tmp/tmp*.log` tasks poisoned the scheduler queue.** 41 pending tasks pointed at deleted temp files; `TaskHandler.handle_pending_tasks` iterates oldest-first and `break`s on the first failure, so every 5s cycle died on `/tmp/test.log` → all real tasks (incl. ours) starved. Fixed by deleting the 16 stale `/tmp` pending tasks via `DELETE /task/{id}` + psql cleanup (21 task_report+task rows). Our 4 tasks (real scenario dir) untouched. This is a pre-existing queue-management gap (a single bad task blocks the whole queue).
2. **Double parse task per upload**: upload service auto-creates a `kv_cache_log_parse_worker` AND `run=true` creates a second one for the same log_id (see `services/log_file.py` init_task at upload + `run_or_stop_log_parse_by_log_file_id`). Both run; one wipes the other's rows mid-flight (reinit/stop clears `existed_status`). E2E script needed a 12s settle wait. Duplicated detail rows (2× per tid) observed as a side effect.
3. **Aggregate rows store the scan-time LOG_ID (random UUID), not the real log_file id.** `generate_aggregate_result` reads `first[TupleField.LOG_ID]`, which the parallel scanner sets to a per-file `LogFileModel` UUID (`process_worker.py` L191/245/249). So `src_dst_aggregated_event.log_id` ≠ `log_file.id`; only detail rows (`_build_anomalous_detail_rows`, uses `log_file_id` param) carry the real id. The API still returns aggregates because `list_aggregated_events` falls back to the kb_id fast path (`_list_by_kb`), which filters by `kb_id` only — hence querying by `log_id` alone returns 0. Pre-existing inconsistency (blamed to c3f496b/171db91, untouched by our diffs).
4. **Backend parent process is stale** (started Jul 30 18:51; fixes committed Jul 31 15:02/15:04). The parse worker runs in a spawned child (multiprocessing.spawn re-imports modules from disk), so the CHILD executes the fixed code — verified by the successful outcome. The parent HTTP process is old but serves data from PG, so no restart was needed for this verification.

### API payload shapes (verified against live deployment)
- `POST /log_kb {"name","description"}` → `result.kb_id`
- `POST /log_file/{kb_id} {"upload_log_file_configs":[{"name","source_type":"local","source":"<DIR>"}]}` → `result.log_file_ids[0]` (upload the whole directory as one log_file)
- `PUT /log_file/run/{log_file_id}?run=true` → task created
- `GET /log_file/{id}` → `result.log_file.parse_status` (`successful`/`failed`/`pending`)
- `POST /log_parse_result/list {"log_id","page_num","page_cnt"}` → `result.total`, `result.log_parse_results[].{trace_id,is_anomalous}`
- `POST /aggregated_event/list {"log_id"|"kb_id","page_num","page_cnt"}` → `result.total`, `result.events[].{src_ip,dst_ip,log_parse_result_cnt,anomaly_cnt}` (kb_id is the reliable filter — see finding 3)
- `POST /aggregated_event/list_time_window {"kb_id","page_num","page_cnt","interval"}` → `result.total`, `result.events[].anomaly_cnt`
- DB: psql `-h 127.0.0.1 -p 15432 -U witty-ub -d witty-ub` (no password; from `config/diagnosis_config.toml`, database `witty-ub`).

### Test-time traps
- The T7 script must sleep ~12s after `parse_status==successful` to let the SECOND (duplicate) parse task settle, otherwise the API can transiently return total=0 (race in finding 2).
- Evidence files: use absolute paths for `tee`/write (relative `../../.omo/...` fails intermittently — inherited from T1).

## Task F2 (F2): Code quality review — COMPLETE

### Verdict
**APPROVE** — no blocking defects. Evidence: `.omo/evidence/fix-conn-fault-aggregation/F2-quality.txt`.

### What was checked
1. **IP fallback block (L1371-1384 / L2017-2030)**: `_urma[0][TupleField.SRC_ADDR]` (idx 11) IndexError risk is NEGLIGIBLE — every production entry is a 16-element tuple from `_serialize_entry` (both `_scan_with_multiprocessing`→`_process_worker_func` process_worker.py L106-109 and `_scan_with_asyncio` scanner.py L300 serialize all entries). `_deserialize_entry` reads idx 15 (LOG_ID), proving the 16-field invariant is an existing hard contract; pre-change code already indexed `first[11]`/`first[15]`. `str(x or "").strip() or ""` is null-safe (None→""; non-str coerced). Chain URMA→RemotePull→empty matches plan exactly.
2. **Anomaly check (L1397-1405 / L2043-2051)**: `status_code is not None and status_code != 0` is null-safe (None does NOT trigger). `anomalous_tids.add(tid)` + `sd_anomaly_count`/`tw_anomaly_count` increments all inside `if is_anomalous:`, keys defined above. Type-safe: `parse_status_code` (base_parser.py L236-240) always returns int (`int(raw)` or `StatusCode.OK=0`).
3. **Consistency**: both blocks byte-identical after per-line indent normalization (verified by python script: 2+2 blocks, indents [12, 8], AST parse OK).
4. **Tests (L408-557)**: real assertions on real output; literals are inputs only; all tuples exactly 16 fields in TupleField order (verified positionally). t5 pins normal case (status=0, 0.5ms). t4 isolates Fix B (elapsed=0 → only status_code can trigger).
5. **Anti-patterns**: grep on diff for `except`/`print(`/`pass`/`TODO`/`FIXME` → none in added lines.

### Non-blocking notes
1. t4/t5 assert only `anomalous_tids` membership; `anomaly_cnt` column increments (sd/tw counters) not pinned by unit tests — covered by T7 E2E only. Optional follow-up: add `assert agg[0].anomaly_cnt == 1`.
2. Comment "# ── anomaly check (before anything else) ──" sits after sd_key/tw_key computation — means "before bucket accumulation", cosmetic drift.
3. URMA presence wins even if its src_addr is empty while RemotePull has a valid one (no per-field fallthrough) — correct-by-spec per plan's per-list chain, noted for future readers.

## Final Verification Wave F1: Plan compliance audit — COMPLETE → **APPROVE**

Read-only audit of `fix-conn-fault-aggregation.md` against git history (no source files touched). Full evidence: `.omo/evidence/fix-conn-fault-aggregation/F1-compliance.txt`.

### Verdict per plan todo
- **T1** — commit `d621b6b`: only `test_integration_pipeline.py` (+159) + notepad changed; 5 test methods match plan acceptance names exactly. ✅
- **T2+T3 (Fix A)** — commit `eb1a118`: only `kv_cache_log_parse_worker.py` (+28/−4); one commit covers both locations (per plan commit strategy). IP blocks content-identical (normalized; 14 lines, indents 12 vs 8). ✅
- **T4+T5 (Fix B)** — commit `2057a86`: only `kv_cache_log_parse_worker.py` (+10/−2). Anomaly blocks content-identical (normalized; 8 lines, indents 12 vs 8). ✅
- **T6** — `test-T6.log` exists: 121 passed, 8 failed = same 8 pre-existing WITHOUT changes → no regressions. ✅
- **T7** — `test-T7.log` exists (557 lines): PASS, 18 assertions; 4 anomalous conn-fault rows (was 0). ✅

### Scope / Must-NOT-Have
- `git diff d621b6b^..2057a86 --stat | grep -E "parse/|detect/"` → EMPTY (grep exit 1). No changes to `detect_exception`, `AnomalyDetector`, `ParseResultBuilder`, `LogCorrelator`.
- Plan-range file list is exactly: `kv_cache_log_parse_worker.py`, `test_integration_pipeline.py`, `learnings.md`. No extras, no stubs (`TODO|FIXME|HACK` count = 0).

### Gotcha worth remembering (audit scope)
- The plan's own F1 command `git diff --stat HEAD~5..HEAD` includes TWO **pre-plan** commits (`a793e59` benchmark harness → `bench_aggregate_parallel.py`+`identity.txt`; `625a688` tw_key fix). Those sit BELOW the plan base (`d621b6b^ == 625a688`), so the plan-scoped range `d621b6b^..2057a86` is the correct audit window and is exactly clean. When auditing a plan, anchor the range at the plan's first commit `^`, not at `HEAD~N`, or pre-plan commits will look like scope violations.

## F4 — Scope Fidelity Audit (2026-07-31) — APPROVE
Plan commits confirmed: `d621b6b` (test), `eb1a118` (fix A), `2057a86` (fix B).
`git diff d621b6b^..2057a86 --name-only` → exactly 3 files, ALL in scope:
1. `.omo/notepads/fix-conn-fault-aggregation/learnings.md` (bookkeeping)
2. `src/plugins/latency/task/worker/kv_cache_log_parse_worker.py` (core worker)
3. `src/plugins/latency/test/test_integration_pipeline.py` (5 tests)
Out-of-scope grep (`detect/|correlat|result_builder|process_worker|frontend|web/|config`) → EMPTY.
TODO/FIXME/HACK/XXX in current worker → 0 hits (baseline snapshot also 0).
Verdict: **APPROVE** — zero out-of-scope changes. Evidence: `.omo/evidence/fix-conn-fault-aggregation/F4-scope.txt`.

## F3 — Independent manual QA (2026-07-31) — PASS

Ran a FRESH E2E against the LIVE deployment (http://127.0.0.1:9772) using scenario `006_001+007+012_002` — **different from T7's `002_005+010+020_002`**, no reuse of T7 results. Evidence: `.omo/evidence/fix-conn-fault-aggregation/F3-e2e-results.txt` (57 lines).

### Verdict: **PASS — 14/14 assertions** (after one aborted first attempt, see trap below)

### What was verified
1. **Fresh KB + upload**: `POST /log_kb` → kb `a615181a…`; `POST /log_file/{kb_id}` with `source_type: "local"` + `source: <scenario DIR>` → log_file `80d65c55…`.
2. **Parse**: `PUT /log_file/run/{id}?run=true` → successful in ~9s (progress 68.3).
3. **Fix B end-to-end**: `POST /log_parse_result/list` → total=6, ALL anomalous, all 3 expected conn-fault traces present: `tid-006-001-s2` (code=5), `tid-007-s2` (code=6), `tid-012-002-s2` (code=23). (6 rows = 3 traces × 2 from the double-parse race.)
4. **Aggregation**: `POST /aggregated_event/list` (kb_id filter) → total=2 events, both `anomaly_cnt=3` (parse_cnt=3). `POST /aggregated_event/list_time_window` → total=1 event, `total_cnt=6, anomaly_cnt=6`.
5. **psql cross-check**: `log_parse_result` is_anomalous=true rows = 6 (rc 0); `src_dst_aggregated_event` anomaly_cnt>=1 rows = 2 (rc 0).
6. **Frontend**: http://192.168.169.63:5173/ serves HTTP 200 (Vite dev, proxies `/api`-style paths → 127.0.0.1:9772 per `src/web/vite.config.ts`). The latency/fault panels call `/aggregated_event/list`, `/aggregated_event/list_time_window`, `/log_parse_result/list`, `/log_parse_result/metrics/latency` (App.vue L2142/4728/5856/5987/6104) — I exercised `/aggregated_event/list` THROUGH the frontend origin (`curl POST http://192.168.169.63:5173/aggregated_event/list`) → HTTP 200, same kb → total=2, anomaly_cnt=3. So the折线图 data path is confirmed live.

### Scenario-choice trap (pre-existing parser behavior, NOT a regression)
First attempt used `002_001+009+020_007` (2 PUT + 1 GET traces) → only `tid-009-s1` (GET) got parse results; the 2 PUT traces (`tid-002-001-s1`, `tid-020-007-s1`) were silently dropped. Root cause: **`SdkAccessLogParser.match_line` only accepts handles in `SDK_GET_OPS`/`SDK_SET_OPS`** (`base_parser.py` L20-22: `DS_KV_CLIENT_GET`/`DS_OBJECT_CLIENT_GET`/`DS_KV_CLIENT_SET`); `DS_KV_CLIENT_PUT` is NOT accepted. T7's scenario had the same blind spot (its `tid-020-002-s3` PUT code=1002 was dropped too) — T7 only passed because its 2 GET traces both appeared. **Lesson for future E2E: pick scenarios whose conn-fault traces are GET/SET ops, or expect PUT traces to be absent from `log_parse_result`.** The all-GET scenario `006_001+007+012_002` gives a clean 3/3 proof.
- Scheduler queue was CLEAN this run (0 pending/running tasks — T7's cleanup persists); no stale `/tmp` tasks to clear. Frontend was reachable throughout.

### Notes
- Empty src/dst IPs still expected: this scenario (like T7's) ships no URMA/RemotePull entries, so Fix A's chain degrades to `""` correctly.
- Parent backend process still stale (started Jul 30 18:51); parse ran in spawned children re-importing fixed code — consistent with T7 finding 4.

## Task TZ1: Backend datetime serialization timezone fix — COMPLETE

### Symptom
DB stores `timestamptz` as aware local `2026-07-31 22:17:19.529+08`, but `POST /log_kb/list` returned `"created_at":"2026-07-31 14:17:19.529"` — a naive UTC-looking string. Frontend `new Date()` parses it as local → 8h shift.

### Root cause
`src/plugins/latency/database/utils.py::format_timestamp` did `value.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]`, which silently drops tzinfo. asyncpg returns `timestamptz` as **aware UTC** datetime (`14:17:19+00:00`); strftime without `%z` yields the naive-looking UTC wall clock. This single helper is the universal DB→string serialization point for ALL managers (log_knowledge, log_file, log_parse_result, src_dst_aggregated_event, anomalous_event, anomalous_event_chain, diagnosis_case, log_failure_event).

### Fix (minimal, one function)
```python
def format_timestamp(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is not None:
        value = value.astimezone()  # aware -> local tz (CST/UTC+8 on this host)
        base = value.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        tz = value.strftime("%z")  # "+0800"
        if len(tz) == 5:
            tz = tz[:3] + ":" + tz[3:]  # -> "+08:00"
        return base + tz
    return value.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]  # naive unchanged
```
- Aware datetime `2026-07-31 14:17:19.529+00:00` → `2026-07-31 22:17:19.529+08:00` (localized).
- Naive values keep historical format (write-path `parse_timestamp` round-trips untouched).

### Verification (live, after `systemctl --user restart witty-ub-backend.service`)
- `POST /log_kb/list` → all `created_at`/`updated_at` = `...+08:00` (was naive `14:17:19`).
- `POST /log_file/list/{kb_id}` → `created_at` = `22:17:19.556+08:00`.
- `POST /log_parse_result/list` → `timestamp`/`created_at` = `...+08:00`.
- `POST /task/list` → `created_at` serialized by Pydantic from `TaskModel.created_at: datetime` as ISO `...Z` (UTC-aware). NOT naive — JS parses `Z` correctly (no 8h bug). Left as-is (schema is datetime-typed, already correct).
- Unit check: `format_timestamp(aware_utc)` → `2026-07-31 22:17:19.529+08:00`; `format_timestamp(naive)` → unchanged; `None` → `None`.

### Tests — no new failures
- `pytest test/` collection fails on 5 files (`test_database_unit`, `test_full_link`, `test_result_builder_optimized`, `test_scheduler_run`, `test_task_service`) importing removed classes (`AsyncSQLiteSingleton`, `LogParseResultManager`) — verified IDENTICAL with change stashed (pre-existing, PostgreSQL migration left stale tests).
- `test_detection_optimized.py` 2 failures — verified pre-existing with stash, zero reference to `format_timestamp`.
- Fast unit set (`test_data_builder`, `test_detection_optimized`[part], `test_diagnosis_case`, `test_openapi_contract`) = 12 passed / 2 pre-existing failed.

### Notes for future
- `ParseResultBuilder._format_timestamp` (`parse/correlation/result_builder.py`) is a SEPARATE write-path formatter (creates parse-result timestamps stored to DB) — intentionally untouched; it produces naive strings, which asyncpg writes into `timestamptz` using the session tz. Its output never reaches API responses.
- FastAPI full `pytest test/` run exceeds 10 min (integration/e2e tests); run targeted unit subsets for quick checks.

## Task DB2: Dangling /tmp log_file + task cleanup — COMPLETE

### Symptom
`journalctl --user -u witty-ub-backend.service` errored every ~5s with `FileNotFoundError: 日志路径不存在: /tmp/tmpx2t790uu.log` — the APScheduler job `TaskHandler.handle_tasks` (interval 5s, `fastapi_server.py` L167) was stuck on stale pending tasks whose `log_file.file_path` pointed at deleted `/tmp/tmp*.log` temp files.

### Root cause (two distinct findings)
1. **Stale pending tasks referencing deleted temp files.** 7 pending tasks (created 22:47 by a test upload batch) pointed at `/tmp/tmpx2t790uu.log`, `/tmp/tmp6ck1xd_z.log`, `/tmp/test.log` — all deleted from disk. `handle_pending_tasks` iterates oldest-first and `break`s on the first failure, so one bad task blocks the whole queue (pre-existing queue-management gap, same as T7 finding 1).
2. **`failed_pending_remove` is NOT terminal in this codebase.** Critical: the instruction's recommended status `failed_pending_remove` triggers `handle_failed_tasks` → `BaseWorker.reinit()` (`base.py` L49-76) which flips the task **back to `pending`** (retry_times+1) whenever `worker.reinit()` returns True. `kv_cache_log_parse_worker.reinit` (L175-208) also re-sets `log_file.parse_status=PENDING` (L204-206). So marking tasks `failed_pending_remove` **cannot** stop the loop — after the first attempt (UPDATE 6 → all 6 flipped back to pending within one 5s cycle, confirmed by task_report rows 4033-4038 "Task reinitialized"), the FileNotFoundError resumed. **Deletion of the task rows is the only effective terminal fix** (also explicitly allowed by the instruction; verified `task` table has zero FK constraints referencing it, so plain `DELETE FROM task WHERE id=...` is safe).

### What was done (pure data cleanup, no code changes, only `log_file` + `task` tables)
1. Cross-checked `ls /tmp/tmp*.log` vs `SELECT ... FROM log_file WHERE file_path LIKE '/tmp/tmp%'` → 11 of 15 log_file rows dangle (files gone); 4 keep (`/tmp/tmp8zh6_ect.log`, `/tmp/tmptk2bl8gp.log`, `/tmp/tmphf45gurt.log`, `/tmp/tmp7anmw8f5.log` all exist with content "test log content").
2. `UPDATE task SET status='failed_pending_remove', completed_at=now(), duration_seconds=...` for the 6 non-terminal tasks of dangling op_ids (this did NOT stick — see root cause 2; reinit flipped them back).
3. `UPDATE log_file SET parse_status='failed', updated_at=now()` for all 11 dangling log_file rows (kept rows for audit, per instruction recommendation).
4. `DELETE FROM task WHERE id IN (...7 ids...)` — 3× d32a8c9f (tmpx2t790uu), 3× 941ab08c (tmp6ck1xd_z), 1× 3440cde6 (1da94f9a → /tmp/test.log, also missing). **Deletion is what actually fixed the queue.**
5. Re-applied `UPDATE log_file SET parse_status='failed'` for d32a8c9f/941ab08c (reinit had flipped them back to pending mid-loop).
6. Kept all legitimate records: daas `SDK_6.62.222.228` log_files (successful), `/tmp/e2e-clean-v2` (KB f1a4670f), `/tmp/e2e-diag-clean`, `/tmp/test.log` log_file rows (all 6 parse_status=successful, only their dangling *pending task* was removed), plus the 4 existing `/tmp/tmp*.log` rows.

### Final DB state (verified via psql)
- `task`: **0 pending**, 7 cancelled (terminal, dangling op_ids), 71 failed, 110 successful, 1 running (`/tmp/e2e-diag-clean`, file exists — legit, finishes on its own).
- `log_file`: 11 dangling rows `parse_status='failed'`; 4 existing-path `/tmp/tmp%` rows left `pending` (legit, their tasks ran and reached terminal).
- `log_knowledge`/`log_parse_result`/other tables: untouched.

### Verification
- `journalctl --user -u witty-ub-backend.service --since "60 sec ago" | grep FileNotFoundError` → **no matches** across multiple 5s scheduler cycles (backend stayed up, serving 200s).
- Remaining pending/running tasks all point to paths that exist on disk.

### Lessons for future
- **In this codebase, `failed_pending_remove` = retry staging, not terminal.** The 7-state FSM is: PENDING→RUNNING→SUCCESSFUL_PENDING_REMOVE→SUCCESSFUL, or →FAILED_PENDING_REMOVE→(reinit)→PENDING (loop, retry_times+1)→FAILED when retry_times exceeds `task.task_retry_times`. To *permanently* kill a poisoned pending task: delete its task row (or set status `cancelled`), NOT `failed_pending_remove`.
- Task rows are the scheduler's only input — a `log_file` with `parse_status` untouched still blocks the queue if a `pending` task references it; conversely a `failed`/`successful` log_file is harmless with zero tasks. Always fix at the `task` level first, `log_file` status is cosmetic for queue health.
- The 22:47 test-upload batch (KB 3b71c5e3) created 3 tasks per log_file (parse + event-diagnosis + store-trace) pointing at temp paths that were deleted shortly after — the natural hazard of testing uploads with `/tmp` sources. No code change requested; queue-manager hardening (mark task failed instead of break-on-first-error) is a separate concern.

(End of file - total 290 lines)
