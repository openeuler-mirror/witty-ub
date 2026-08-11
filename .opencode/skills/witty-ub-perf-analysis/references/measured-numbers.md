# Measured Baseline (data/logs/e2e-test-100m, 106MB, 367k traces)

Reference numbers captured during the perf overhaul. Use them to sanity-check
any new measurement — if a run on the same data disagrees wildly, something
changed.

## Data shape

- 4 files, 106MB total; main file `ds_client_access_3941...log` = 104MB / 395,364 lines.
- Scan output: 367,244 entries (SDK 347,471 + Worker access 19,773; INFO 0 matches here).
- Aggregation input: 367,244 traces; sharded into 4 x ~91,811.

## Timing baseline (production run, single parse, poll 1s)

| Phase | Time | Notes |
|---|---|---|
| Preprocess (copy 106MB) | ~3.0s | Skipped since 886b60b for pure-text dirs ("日志无需预处理") |
| Scan (scan.worker_exec) | 5.4-5.9s | 4 processes, bounded submission (HDD=3) |
| Aggregate ([TASK] Aggregate) | 5.8-7.2s | varies with load |
| Bucket stats (parallel pick) | 1.4-2.3s | 6 workers spawn pool |
| Store to DB | 0.1s | 14,380 rows across 4 latency_bucket tables |
| Parse task total | 15-20s | includes preprocess + scheduler queueing |
| Diagnosis (parallel) | 5-8s | C++ diag-tool, does not add to wall clock |
| Store-trace (parallel) | 15-25s | mostly WAITING on parse; 75 trace events in ~0.3s |
| **End-to-end** | **15-23s** | = parse + store tail; varies with cache/load |

## Aggregation IPC vs compute (the key lesson)

Measured on 367k traces:

| Measurement | Value |
|---|---|
| Serial aggregation (workers=1, no spawn) | **1.97s** |
| Spawn 4 workers | **4.32s** (slower than serial!) |
| Single shard calc (child) | ~0.49s |
| Single shard result pickle | 31.5MB / 0.47s |
| 4 shard result pickle total | ~126MB |
| spawn startup (4 procs, import) | ~2.6s (fixed, does not scale) |
| `[PERF][AGG]` production | shard=90ms spawn_pool=3921ms merge=819ms total=4830ms |

Conclusion at THIS size: spawn+pickle (~4.9s) > compute (~2.4s). Multiprocessing is
a net loss at 367k. At ~20GB (73M traces) the balance flips: compute parallelizes
(1.97s*200/4 ~= 100s) while pickle grows linearly (~200s) and spawn stays fixed —
spawn still wins over serial, but shared_memory + persistent pool would win over both.

## Parallel efficiency (why not 4x)

- 4 shards serial = 2.33-2.67s -> single shard ~0.6s (small).
- Spawn 4-core gains only ~1.4x over serial (2.4s -> 1.7s compute).
- Reasons: memory-bandwidth bound (numpy on shared RAM), per-trace dict allocation,
  spawn startup 2.6s eats the gain.

## Fixed vs linear (extrapolation template)

```
serial:      t = c * n                        (c ~ 5.4us/trace)
spawn:       t = fixed(~2.6s) + pickle(n) + compute(n)/workers
shared_mem:  t = fixed(~2.6s) + compute(n)/workers     (pickle removed)
```
For any data-size question, compute all three and pick the crossover.
