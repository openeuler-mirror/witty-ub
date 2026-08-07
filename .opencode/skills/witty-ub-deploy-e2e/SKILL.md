---
name: witty-ub-deploy-e2e
description: Deploy Witty-UB (backend 9772 + frontend 5173 + PostgreSQL) via deploy.sh and run a correct end-to-end API verification (create KB -> upload a whole log DIRECTORY as one local log_file -> let the auto-created task family run -> poll -> verify DB rows). Use when installing/deploying Witty-UB, restarting its backend/frontend, running an end-to-end log-parse test through the real API, checking whether a parse task succeeded, or debugging why a deployment or e2e run failed. Encodes hard-won lessons: never call PUT /log_file/run after upload (double-parse race), check task status via DB not poll scripts, poll every 1s not 5s, the backend is a systemd user service so journalctl is the log source, and pure-text log dirs skip preprocess copy.
---

# Witty-UB Deploy & E2E Test

Install/start Witty-UB and verify it end-to-end through the real API. This skill exists because every shortcut in it has already burned the author once — follow the flow exactly.

## Inputs

- Repository root. Default: current working directory (`/home/li/witty-ub_8632`).
- Target log directory to test with (upload as ONE log_file). Default: `data/logs/e2e-test-100m`.
- PostgreSQL connection. Default: `postgresql://witty-ub:witty-ub@127.0.0.1:15432/witty-ub`
  (deploy_pg.sh RPM installs use port 15432; plain local PG uses 5432 — check `config/diagnosis_config.toml [db]`).

## Preconditions

- PostgreSQL running with role `witty-ub` / db `witty-ub` already created (deploy.sh does NOT create them):
  ```bash
  CREATE ROLE "witty-ub" LOGIN PASSWORD 'witty-ub';
  CREATE DATABASE "witty-ub" OWNER "witty-ub";
  ```
- Python venv at `src/plugins/latency/.venv`, Node for the frontend.

## Deploy / Start

```bash
# Full first-time deploy (init PG if absent -> python deps -> C++ diag-tool -> data files -> start)
bash deploy/deploy.sh

# Start only (after already deployed)
bash deploy/deploy.sh --start
# Stop only
bash deploy/deploy.sh --stop
```

### The backend is a systemd USER service (critical)

`systemctl --user status witty-ub-backend.service` — `Restart=always` means:
- **Killing the PID does not stop it**; systemd immediately respawns it. To apply code changes: `systemctl --user restart witty-ub-backend.service`.
- **Logs go to journald, NOT `.deploy-logs/backend.log`**: `journalctl --user -u witty-ub-backend.service -n 200 --no-pager`.
- Never "restart" by `kill <pid>` + `nohup python ...` — your process loses to systemd and you waste hours wondering why new code is not loaded.

### Post-deploy health checks (all four, missing one = incomplete)

```bash
curl -s http://127.0.0.1:9772/health_check              # expect {"status":"ok"}
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:5173/   # expect 200
psql "<DSN>" -c "SELECT count(*) FROM information_schema.tables WHERE table_schema='public'"
```

## Correct E2E Flow (follow exactly)

### RULE 1 — NEVER call `PUT /log_file/run/{id}?run=true` after upload

Uploading already creates ALL 3 tasks (parse + diagnosis + store). Calling run
creates a SECOND parse task that shares the same preprocess dir -> race ->
diagnosis fails with "diag-tool got empty dir". Upload once, then only poll.

### Steps

```bash
DSN="postgresql://witty-ub:witty-ub@127.0.0.1:15432/witty-ub"
BASE="http://127.0.0.1:9772"

# 1. Create KB
KB_ID=$(curl -s -X POST "$BASE/log_kb" -H 'Content-Type: application/json' \
  -d '{"name":"e2e_test","description":"e2e"}' \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['result']['kb_id'])")

# 2. Upload the WHOLE log DIRECTORY as one local log_file (do NOT split files)
LOG_ID=$(curl -s -X POST "$BASE/log_file/$KB_ID" -H 'Content-Type: application/json' \
  -d '{"upload_log_file_configs":[{"name":"logs","source_type":"local","source":"/path/to/log/dir"}]}' \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['result']['log_file_ids'][0])")
#    ^-- source points at a DIRECTORY. Splitting into per-file uploads breaks
#        trace correlation (SDK/Worker/INFO must be scanned together).

# 3. Poll task status via DB every 1s (NOT a 5s loop, NOT /task/list which can 500)
while true; do
  DONE=$(psql "$DSN" -t -c "SELECT count(*) FROM task WHERE op_id='$LOG_ID' AND status NOT IN ('pending','running')" | tr -d ' ')
  TOTAL=$(psql "$DSN" -t -c "SELECT count(*) FROM task WHERE op_id='$LOG_ID'" | tr -d ' ')
  [ "$DONE" = "$TOTAL" ] && [ "$TOTAL" != "0" ] && break
  sleep 1
done

# 4. Judge success via DB status (authoritative), not logs
psql "$DSN" -c "SELECT task_type, status FROM task WHERE op_id='$LOG_ID' ORDER BY task_type"
#    ALL 3 rows must be 'successful' (or successful_pending_remove).
#    Any 'failed'/'failed_pending_remove' -> check task_report.message for the reason.

# 5. Verify data landed
psql "$DSN" -c "SELECT count(*) FROM log_parse_result WHERE log_id='$LOG_ID'"
psql "$DSN" -c "SELECT count(*) FROM src_dst_aggregated_event"
psql "$DSN" -c "SELECT count(*) FROM log_failure_event"   # diagnosis products
```

## Judgment Rules (how to know a task succeeded)

- **Authoritative check = `task.status` in DB** (values are LOWERCASE: `successful`,
  `failed`, `cancelled`, `pending`, `running`, `successful_pending_remove`).
  - ⚠️ Writing a UPPERCASE `'FAILED'` into the DB breaks `TaskStatusEnum(row.status)`
    and makes `POST /task/list` return 500 for everyone.
- Failure details live in `task_report.message`.
- Do not trust a poll script / logs alone; query the DB.
- `log_parse_result.log_id` must equal the top-level `log_file.id`.

## Performance-Reading (new in 886b60b)

Aggregation emits phase timings so a server operator sees the bottleneck at a glance:

```
[PERF][AGG] shard=90ms spawn_pool=3921ms workers=4 shards=4 traces=367244
[PERF][AGG] merge=819ms total=4830ms
```

- `spawn_pool` = spawn process start + trace pickle in + child compute + result pickle back.
  If it dwarfs merge+compute, IPC (not compute) is the bottleneck.
- Pure-text log dirs skip preprocess copy: log "日志无需预处理, 直接扫描源目录".

## Anti-Patterns (each one is a real past failure)

| Anti-pattern | What actually happened |
|---|---|
| Upload then call `PUT /log_file/run` | 2nd parse task races on shared preprocess dir; diagnosis fails |
| Split the log dir into per-file uploads | Each file scanned alone; SDK-only file has no Worker logs -> "未识别到日志信息" -> parse failed |
| Poll `/task/list` in a loop | It 500s when any DB row has bad enum status; loop dead-ends |
| Poll every 5s | Tail-of-chain store task stalls up to 5s extra (interval is now 1s) |
| `kill <pid>` to "restart" backend | systemd respawns it; new code not loaded; logs misread from wrong file |
| Look for logs in `.deploy-logs/backend.log` | Real logs are in journald for the systemd service |
| Rely on a `sleep N` then check | Wastes wall time; task is usually already done — poll, don't sleep |
| Judge success by log text | `status` column is the only truth; logs can show old-code behavior |

## References

- [references/troubleshooting.md](references/troubleshooting.md) — symptom -> cause -> fix table.
