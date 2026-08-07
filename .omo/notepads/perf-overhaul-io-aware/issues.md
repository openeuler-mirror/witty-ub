# Issues — perf-overhaul-io-aware

Problems and gotchas encountered during work on this plan.

_Auto-scaffolded by /start-work. Append new entries below - never overwrite._

---

## 2026-08-05 — F7 final gate findings (all optional, none blocking)

- **[MINOR][T2] dev pg_password committed** — `config/diagnosis_config.toml`
  (`b489e14`) ships `pg_password = "witty-ub"` (pre-existing uncommitted dev
  edit, documented in commit msg). Dev-only value; hygiene flag for git
  history, not a real secret. Fix if team wants clean history: rotate the
  value / stop committing local TOML edits.
- **[MINOR][T8] `__perf__` marker typing mismatch** — `process_worker.py:195:9`
  `serialized[_PERF_MARKER] = timing_data` assigns `dict[str,dict[str,float]]`
  into a `dict[str, list]` (reportArgumentType at 195, reportReturnType at
  197). Runtime-safe: `_merge_results` pops it with an `isinstance(dict)`
  guard before merging; pickle round-trip covered by test. Optional fix:
  annotate `serialized` as `dict[str, object]` or `# type: ignore`.
- **[MINOR][T8] private cross-module marker protocol** — `scanner.py:21`
  imports `_PERF_MARKER` / `_TIMING_COLLECTOR` from process_worker
  (reportPrivateUsage). They form an inter-module protocol, not module
  internals — if touched again, rename public (`PERF_MARKER`,
  `TIMING_COLLECTOR`).
- **[NIT][T8]** `scanner.py:468` `for file_name, t in timing.items()` —
  `file_name` unused; and `t["io_ms"]` direct key access (`.get(..., 0.0)`
  would be more defensive; dicts are self-produced so KeyError is
  theoretical). Also theoretical `__perf__` label collision (labels are fixed
  constants, non-issue in practice).
- **[QUESTION][T1]** `parse_timestamp` now uses
  `datetime.fromisoformat(ts.replace(" ","T",1))` — Python 3.10
  fromisoformat accepts only 3/6-digit fractional seconds (old slicing code
  truncated arbitrary lengths). Only a regression if prod runs 3.10 AND logs
  carry non-3/6-digit fractions. Local .venv is 3.12 — confirm deploy Python
  before worrying.
- **[NIT][T6]** fast-path re-check (`len(parsers)==1 and hasattr(scan_file)`)
  duplicated inside `_scan_file_multi_sync`/`_scan_file_multi_decoupled`
  (defensive dead code, harmless).
- **[NIT]** T4 added explicit `Any` in `bucket/statistics.py:114`
  (`_normalize_op`) and `kv_cache_log_parse_worker.py:1491`
  (`rows: Sequence[Any]`) — both files already Any-heavy at baseline
  (reportExplicitAny=14/15 pre-existing); noise-level.
- **[NOTE]** `reportAttributeAccessIssue` +2 (`_pre_parsed` at
  process_worker 584/603) is the SAME pre-existing dynamic-attribute pattern,
  newly surfaced by T1's `isinstance(parser, AccessLogParser)` narrowing —
  not a regression.
- **[NOTE]** lint: pyflakes' only finding (kv_cache_log_parse_worker.py:62:1
  redefinition of TimeWindowAggregatedEventDataclass) is pre-existing —
  identical at baseline 575d963.
