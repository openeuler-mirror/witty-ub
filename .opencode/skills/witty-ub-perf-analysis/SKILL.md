---
name: witty-ub-perf-analysis
description: Diagnose Witty-UB performance bottlenecks (parse/aggregation/scan pipeline) from real evidence instead of guessing. Use when the user asks why a task or pipeline is slow, wants to see the timing breakdown / latency distribution of a parse run, needs to decide whether multiprocessing/parallelism actually helps, wants to measure pickle/spawn/transfer overhead, or wants to predict how latency scales with data size. Encodes the proven method: read the instrumented timings first (task_report [TASK]/[perf]/[PERF][AGG] entries), then run small controlled experiments (serial-vs-parallel, pickle size, spawn startup) before any conclusion, and never extrapolate a small-data result to large data without separating fixed vs linear costs.
---

# Witty-UB Performance Analysis

Find where a parse/aggregation pipeline spends its time — from evidence, not intuition. Every shortcut in this skill produced a wrong answer when skipped.

## Where the timings live (read these FIRST, before touching code)

All are real instrumented output, no profiling needed to get the top-level picture:

1. **Per-task phase breakdown** — `task_report` table, `message` column:
   ```sql
   SELECT to_char(created_at,'HH24:MI:SS.US') ts, round(progress::numeric,1) prog, left(message,70) msg
   FROM task_report WHERE task_id='<task_id>' ORDER BY created_at;
   ```
   Look for `[TASK] Parse log: Xs`, `[TASK] Aggregate result: Ys`, `[TASK] Store to DB: Zs`,
   `[parse_log] Bucket stats: ...`, `[perf][scan.summary]`, `[perf][aggregate.summary]`.
   These give the phase tree: scan / aggregate / bucket-stats / store.

2. **Aggregation IPC-vs-compute split** (added in 886b60b):
   ```
   [PERF][AGG] shard=90ms spawn_pool=3921ms workers=4 shards=4 traces=367244 shard_sizes=[91811,91811,91811,91811]
   [PERF][AGG] merge=819ms total=4830ms
   [PERF][AGG][shard] traces=91811 metrics=86868 calc=491ms     (child process, per shard)
   ```
   - `spawn_pool` = spawn start + trace pickle IN + child compute + result pickle BACK.
   - `merge` + child `calc` are the real compute. If `spawn_pool` dwarfs them, **IPC (not compute) is the bottleneck**.

3. **Per-file io/parse** — `[perf][file.io]` / `[perf][file.parse]` / `[perf][total]` (child processes).
4. **Wall-clock per task** — `task` table: `completed_at - created_at` (includes preprocess + scheduler queueing).

## Method (the proven order)

### Step 0 — Get the wall-clock tree first
```sql
SELECT task_type, status, to_char(created_at,'HH24:MI:SS') c, to_char(completed_at,'HH24:MI:SS') d,
       round(EXTRACT(EPOCH FROM (completed_at-created_at)),1) dur
FROM task WHERE op_id='<log_file_id>' ORDER BY task_type;
```
End-to-end = max(completed_at) - min(created_at) across the task family. Tasks run in
PARALLEL (diagnosis/parse/store start together) — do not sum their durations.

### Step 1 — Phase tree from task_report
Read all `[TASK]`/`[perf]` entries of the parse task. This answers "which phase is the largest"
(scan vs aggregate vs bucket vs store) with zero guessing.

### Step 2 — IPC-vs-compute split from [PERF][AGG]
If aggregation is the big phase, the `spawn_pool` vs `merge`/`calc` numbers decide the story.

### Step 3 — Controlled experiments (only when you need to PROVE a hypothesis)
Before claiming "X is the bottleneck", measure it directly:

```python
# A. Pickle size of a shard result (the IPC payload)
import pickle, time
pk = pickle.dumps(shard_result)          # len(pk)/1e6 -> MB
# B. Spawn startup cost (import full module tree, per process)
t0=time.perf_counter()
with ProcessPoolExecutor(max_workers=4, mp_context=multiprocessing.get_context("spawn")) as pool:
    list(pool.map(functools.partial(_worker_process_shard, threshold_ms=5.0, log_file_id="x"), [empty]*4))
print(time.perf_counter()-t0)            # fixed per-call cost, does NOT scale with data
# C. Serial vs parallel on the SAME data (env UB_AGGREGATE_WORKERS=1 vs 4)
#    -> answers "does multiprocessing actually help at this size?"
```

Save the trace_index once to a pickle (`/tmp/opencode/ti_100m.pkl`) so experiments
reuse identical input instead of re-scanning each time.

### Step 4 — Scaling reasoning (fixed vs linear)
Separate costs that scale with data (pickle transfer, compute, merge) from fixed costs
(spawn process startup, import). Then extrapolate honestly:

```
serial_367k  -> serial_73M (200x)   = 1.97s * 200
spawn4_367k  -> spawn4_73M          = fixed_startup + pickle*200 + (compute/4)*200
```
A small-data conclusion can REVERSE at large data (serial wins at 367k, spawn wins at
20GB because compute parallelizes but pickle is only ~2x). Never extrapolate without
doing this split.

## What each number means (quick reference)

| Signal | Meaning |
|---|---|
| `[TASK] Aggregate result: 7.2s (54.6%)` | Aggregation is the largest parse phase |
| `[PERF][AGG] spawn_pool=3900ms merge=800ms` | 81% of aggregation is IPC, not compute |
| `[PERF][AGG][shard] calc=490ms` per shard ×4 | Real compute is tiny (~2s total) |
| `serial=1.97s` vs `spawn4=4.32s` at 367k | spawn fixed cost > parallel gain at this size |
| `[perf][file.parse] ds_client_access=2.7s` ×2 | Two parse tasks scanning the same file (duplicate) |
| Two parse tasks same op_id | Upload + manual `run` double-parse (see deploy-e2e skill) |

## Anti-Patterns (each one produced a wrong answer here)

| Anti-pattern | What actually happened |
|---|---|
| Sum the task durations as "end-to-end" | Tasks run in parallel; sum double-counts. End-to-end = max completion - min start. |
| Claim "serial is faster" from a 367k test | At 20GB the conclusion REVERSES (compute parallelizes). Always split fixed vs linear costs. |
| Estimate pickle size by eyeballing "347k dicts" | Measure with `pickle.dumps()` — 31.5MB/shard, not the guessed 500MB. |
| Expect 4-core = 4x speedup | Aggregation is memory-bandwidth-bound + spawn costs; measured gain ~1.4x at 367k. |
| Judge by wall-clock alone | Preprocess copy (3s), scheduler queueing, and store-trace tail-wait are in the wall clock, not the parse compute. |
| `sleep N` then check | Task is usually already done; poll DB every 1s instead. |
| Blame compute when `spawn_pool` is huge | The [PERF][AGG] split separates IPC from compute — read it before concluding. |

## References

- [references/measured-numbers.md](references/measured-numbers.md) — the 100M/367k baseline measurements these methods were built on.
