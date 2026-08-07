# pipeline-rewrite Learnings

## 2026-07-28 - State After Todos 1 & 2

### Completed
- **Todo 1 (MERGE)**: `scanner.py` now builds `trace_index` = `dict[tid, dict[label, list[tuple]]]` in `_merge_results()` and `_scan_group_asyncio()`. Returns `dict(trace_index)` from `scan_all()`.
- **Todo 2 (SORT/INDEX/CORRELATE removal)**: SORT code blocks and LogCorrelator removed from `parse_log()`. `CorrelationResult()` still passed to ParseResultBuilder with empty maps.

### Current State
- `parse_log()` still uses old pipeline: pops SDK/Worker entries → ParseResultBuilder → `list[LogParseResultModel]`
- `run()` calls `detect_exception()` then `generate_aggregate_result(list_log_parse_results)` (old per-field stats approach)
- Scanner `scan_all()` returns `dict[str, dict[str, list]]` (trace_index format), but parse_log still expects flat `{label: [entries]}`

### Key Data Structures
- `trace_index` = `dict[tid → dict[label → list[tuple]]]`
- Tuple structure: see `TupleField` (IntEnum) in `ENUM/ds_log.py`
  - `TRACE_ID=5`, `ELAPSED_US=2`, `OPERATION=1`, `SRC_ADDR=11`, `DST_ADDR=12`, `TIMESTAMP=0`, `POD_IP=6`
- Labels: "SDK access parse", "Worker access parse", URMA_LABEL, REMOTE_PULL_LABEL, LINK_LABEL, QUERY_META_LABEL, and 8 TIMED_LABELS
