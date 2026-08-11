# Witty-UB Deploy & E2E Troubleshooting

Symptom -> cause -> fix. Each row is a real incident.

## Deployment

| Symptom | Cause | Fix |
|---|---|---|
| Backend startup crash `cannot alter column ... partition key` / `InvalidTableDefinitionError` | Old `time_window_aggregated` RANGE partitions left in DB from a previous version; migration hits the partition-key column | Already fixed in `database/init.py` (`migrate_timestamptz_to_timestamp` skips partitioned tables). Re-run full deploy. |
| `ModuleNotFoundError: No module named 'latency'` at backend start | Backend launched with system `/usr/bin/python3` without `PYTHONPATH` (e.g. manual `nohup python3 -u access/fastapi_server.py`) | Use `bash deploy/deploy.sh --start` or `systemctl --user restart witty-ub-backend.service` (the unit sets `PYTHONPATH=/.../src/plugins`). |
| Backend health OK but frontend 404 | Only backend was started | `bash deploy/deploy.sh --start` starts both; verify `curl :5173` = 200. |
| PG auth failure `InvalidPasswordError` | `config/diagnosis_config.toml [db]` password empty/mismatched vs `deploy/pg.conf` | `deploy.sh` syncs credentials from `deploy/pg.conf`; check both files. |

## E2E / Task failures

| Symptom | Cause | Fix |
|---|---|---|
| Diagnosis task failed, log `Error reading ... No such file` or `返回码: -6` | Two parse tasks raced on the same `log_preprocessed_<id>/` dir (upload + manual `run`) | Delete the duplicate parse task; re-upload WITHOUT calling `run`. |
| Parse task failed, "未识别到日志信息" | Log dir was split into per-file uploads; a file type scanned alone has no SDK entries | Upload the whole directory as one log_file. |
| `POST /task/list` returns 500 for everyone | Some `task.status` row holds an UPPERCASE enum (`'FAILED'`) that `TaskStatusEnum()` can't parse | `UPDATE task SET status=lower(status);` (values are lowercase: `failed`). |
| Tasks stuck `pending` forever | A broken task (file path no longer exists) in the queue makes the APScheduler loop throw every 5s | Mark stale-pending tasks `failed` in DB, or delete them; then new tasks dispatch. |
| Task `successful` but no rows in `log_parse_result` | Check the `log_id` used — it must equal the top-level `log_file.id`, not a per-file UUID | Re-parse; verify with `SELECT log_id, count(*) FROM log_parse_result GROUP BY log_id`. |
| Store task takes 20s+ while parse took 15s | Store must wait for parse then does its own tail work; poll interval used to be 5s (now 1s) | Verify `MONITOR_INTERVAL_SECONDS = 1` in `store_trace_context_logs_worker.py`. |

## Performance reading

| Observation | Meaning |
|---|---|
| `[PERF][AGG] spawn_pool=3900ms merge=800ms total=4800ms` | 81% of aggregation is spawn+pickle IPC, not compute. Compute is ~1s. |
| `日志无需预处理, 直接扫描源目录` | `needs_preprocess()` decided the dir is pure text matching patterns — copy skipped (saves ~2-3s + 106MB IO). |
| Two `kv_cache_log_parse_worker` tasks for one `op_id` | Duplicate parse (upload + manual run) — remove one. |

## Judging success (recap)

1. `task.status` in DB — all three types `successful`.
2. `log_parse_result.log_id` = top-level log_file.id.
3. `trace_failure_event` / `log_failure_event` non-empty (diagnosis chain works).
4. Frontend HTTP 200.
