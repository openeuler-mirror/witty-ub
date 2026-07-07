#!/usr/bin/env python3
"""Build a source-linked evidence bundle from a combined cProfile file.

This script is deliberately not a root-cause engine. It preserves profile facts,
call relationships, and source context so a code agent can perform semantic
diagnosis without inventing conclusions from a hotspot ranking.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import pstats
from typing import Any, Optional


DEFAULT_RUNTIME_PREFIX = "/var/witty-ub/latency/"
DEFAULT_REPOSITORY_PREFIX = "src/plugins/latency/"
FunctionKey = tuple[str, int, str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--json-report", type=Path, required=True)
    parser.add_argument("--markdown-report", type=Path, required=True)
    parser.add_argument("--target", default="unspecified")
    parser.add_argument("--source-revision", default="unspecified")
    parser.add_argument(
        "--experiment-json",
        type=Path,
        help="Optional scanner-mode comparison JSON to embed as controlled evidence.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Maximum entries in each cumulative/self/call-count view.",
    )
    parser.add_argument(
        "--context-lines",
        type=int,
        default=8,
        help="Source lines retained before and after a profiled function line.",
    )
    parser.add_argument("--runtime-prefix", default=DEFAULT_RUNTIME_PREFIX)
    parser.add_argument("--repository-prefix", default=DEFAULT_REPOSITORY_PREFIX)
    return parser.parse_args()


def normalize_source_path(
    filename: str,
    runtime_prefix: str,
    repository_prefix: str,
) -> Optional[str]:
    normalized = filename.replace("\\", "/")
    runtime_prefix = runtime_prefix.rstrip("/") + "/"
    repository_prefix = repository_prefix.rstrip("/") + "/"

    if normalized.startswith(runtime_prefix):
        return repository_prefix + normalized[len(runtime_prefix) :]

    repository_marker = "/" + repository_prefix
    if repository_marker in normalized:
        return repository_prefix + normalized.split(repository_marker, 1)[1]

    return None


def caller_metrics(raw: Any) -> tuple[int, int, float, float]:
    if isinstance(raw, tuple):
        values = list(raw) + [0, 0, 0.0, 0.0]
        return int(values[0]), int(values[1]), float(values[2]), float(values[3])
    if isinstance(raw, (int, float)):
        value = int(raw)
        return value, value, 0.0, 0.0
    return 0, 0, 0.0, 0.0


def read_source_context(
    filename: str,
    line: int,
    radius: int,
) -> dict[str, Any]:
    path = Path(filename)
    if not path.is_file():
        return {
            "available": False,
            "start_line": None,
            "end_line": None,
            "anchor": "",
            "code": "",
        }

    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return {
            "available": False,
            "start_line": None,
            "end_line": None,
            "anchor": "",
            "code": "",
        }

    start = max(1, line - radius)
    end = min(len(lines), line + radius)
    code = "\n".join(
        f"{line_number:6d} | {lines[line_number - 1]}"
        for line_number in range(start, end + 1)
    )
    anchor = lines[line - 1].strip() if 1 <= line <= len(lines) else ""
    return {
        "available": True,
        "start_line": start,
        "end_line": end,
        "anchor": anchor,
        "code": code,
    }


def raw_location(key: FunctionKey) -> str:
    filename, line, function = key
    return f"{filename}:{line} ({function})"


def build_relationship(
    key: FunctionKey,
    raw: Any,
    args: argparse.Namespace,
) -> dict[str, Any]:
    primitive_calls, total_calls, self_seconds, cumulative_seconds = caller_metrics(
        raw
    )
    filename, line, function = key
    source_path = normalize_source_path(
        filename,
        runtime_prefix=args.runtime_prefix,
        repository_prefix=args.repository_prefix,
    )
    return {
        "function": function,
        "source_path": source_path,
        "raw_location": raw_location(key),
        "line": line,
        "is_project_source": source_path is not None,
        "primitive_calls": primitive_calls,
        "total_calls": total_calls,
        "self_seconds": round(self_seconds, 6),
        "cumulative_seconds": round(cumulative_seconds, 6),
    }


def factual_signals(
    total_calls: int,
    self_seconds: float,
    cumulative_seconds: float,
    total_profile_cpu_seconds: float,
) -> list[dict[str, Any]]:
    signals: list[dict[str, Any]] = []
    self_ratio = self_seconds / cumulative_seconds if cumulative_seconds else 0.0
    self_cpu_percent = (
        self_seconds * 100.0 / total_profile_cpu_seconds
        if total_profile_cpu_seconds
        else 0.0
    )

    if cumulative_seconds > 0 and self_ratio < 0.05:
        signals.append(
            {
                "kind": "wrapper_or_wait_candidate",
                "observation": (
                    f"self/cumulative ratio is {self_ratio:.3f}; most cumulative "
                    "time is attributed to descendants or waiting."
                ),
            }
        )
    if self_cpu_percent >= 1.0:
        signals.append(
            {
                "kind": "self_time_contributor",
                "observation": (
                    f"self time accounts for {self_cpu_percent:.3f}% of combined "
                    "profile CPU time."
                ),
            }
        )
    if total_calls >= 10_000:
        signals.append(
            {
                "kind": "high_call_count",
                "observation": f"profile recorded {total_calls} total calls.",
            }
        )
    return signals


def build_evidence(args: argparse.Namespace) -> dict[str, Any]:
    if args.limit <= 0:
        raise ValueError("--limit must be greater than zero")
    if args.context_lines < 0:
        raise ValueError("--context-lines must not be negative")
    if not args.profile.is_file():
        raise FileNotFoundError(args.profile)
    controlled_experiment: Optional[dict[str, Any]] = None
    if args.experiment_json is not None:
        if not args.experiment_json.is_file():
            raise FileNotFoundError(args.experiment_json)
        controlled_experiment = json.loads(
            args.experiment_json.read_text(encoding="utf-8")
        )
        if not isinstance(controlled_experiment, dict):
            raise ValueError("--experiment-json must contain a JSON object")
        if (
            controlled_experiment.get("artifact_type")
            != "witty_ub_scanner_mode_comparison"
        ):
            raise ValueError("--experiment-json has an unsupported artifact_type")
        if controlled_experiment.get("status") != "passed":
            raise ValueError("--experiment-json did not pass integrity checks")

    stats = pstats.Stats(str(args.profile))
    total_profile_cpu_seconds = float(stats.total_tt)
    callees_by_caller: dict[FunctionKey, list[tuple[FunctionKey, Any]]] = defaultdict(
        list
    )
    for callee_key, raw_stats in stats.stats.items():
        for caller_key, edge_raw in raw_stats[4].items():
            callees_by_caller[caller_key].append((callee_key, edge_raw))

    project_rows: list[dict[str, Any]] = []
    external_rows: list[dict[str, Any]] = []
    for key, raw in stats.stats.items():
        filename, line, function = key
        primitive_calls, total_calls, self_seconds, cumulative_seconds, callers = raw
        source_path = normalize_source_path(
            filename,
            runtime_prefix=args.runtime_prefix,
            repository_prefix=args.repository_prefix,
        )
        base = {
            "_key": key,
            "function": function,
            "line": line,
            "primitive_calls": primitive_calls,
            "total_calls": total_calls,
            "self_seconds": round(self_seconds, 6),
            "cumulative_seconds": round(cumulative_seconds, 6),
            "average_self_ms": round(
                self_seconds * 1000.0 / total_calls if total_calls else 0.0,
                6,
            ),
            "average_cumulative_ms": round(
                cumulative_seconds * 1000.0 / primitive_calls
                if primitive_calls
                else 0.0,
                6,
            ),
            "self_cpu_percent": round(
                self_seconds * 100.0 / total_profile_cpu_seconds
                if total_profile_cpu_seconds
                else 0.0,
                3,
            ),
        }
        if source_path is None:
            external_rows.append(
                {
                    **base,
                    "raw_location": raw_location(key),
                }
            )
            continue
        if source_path.startswith(args.repository_prefix.rstrip("/") + "/test/"):
            continue

        callers_normalized = [
            build_relationship(caller_key, caller_raw, args)
            for caller_key, caller_raw in callers.items()
        ]
        callers_normalized.sort(
            key=lambda item: (
                item["cumulative_seconds"],
                item["self_seconds"],
                item["total_calls"],
            ),
            reverse=True,
        )
        callees_normalized = [
            build_relationship(callee_key, edge_raw, args)
            for callee_key, edge_raw in callees_by_caller.get(key, [])
        ]
        callees_normalized.sort(
            key=lambda item: (
                item["cumulative_seconds"],
                item["self_seconds"],
                item["total_calls"],
            ),
            reverse=True,
        )
        project_rows.append(
            {
                **base,
                "source_path": source_path,
                "source_location": f"{source_path}:{line}",
                "source_context": read_source_context(
                    filename,
                    line,
                    args.context_lines,
                ),
                "callers": callers_normalized[:10],
                "callees": callees_normalized[:15],
                "signals": factual_signals(
                    total_calls,
                    self_seconds,
                    cumulative_seconds,
                    total_profile_cpu_seconds,
                ),
            }
        )

    sort_specs = {
        "by_cumulative_time": (
            "cumulative_seconds",
            "self_seconds",
            "total_calls",
        ),
        "by_self_time": ("self_seconds", "cumulative_seconds", "total_calls"),
        "by_call_count": ("total_calls", "self_seconds", "cumulative_seconds"),
    }
    selected_keys: set[FunctionKey] = set()
    views: dict[str, list[str]] = {}
    ordered_by_view: dict[str, list[dict[str, Any]]] = {}
    for view_name, fields in sort_specs.items():
        ordered = sorted(
            project_rows,
            key=lambda item: tuple(item[field] for field in fields),
            reverse=True,
        )[: args.limit]
        ordered_by_view[view_name] = ordered
        selected_keys.update(item["_key"] for item in ordered)

    selected = [item for item in project_rows if item["_key"] in selected_keys]
    selected.sort(
        key=lambda item: (
            item["cumulative_seconds"],
            item["self_seconds"],
            item["total_calls"],
        ),
        reverse=True,
    )
    id_by_key: dict[FunctionKey, str] = {}
    for index, item in enumerate(selected, start=1):
        function_id = f"F{index:03d}"
        id_by_key[item["_key"]] = function_id
        item["function_id"] = function_id
    for view_name, ordered in ordered_by_view.items():
        views[view_name] = [id_by_key[item["_key"]] for item in ordered]

    for item in selected:
        item.pop("_key", None)
    external_rows.sort(
        key=lambda item: (
            item["cumulative_seconds"],
            item["self_seconds"],
            item["total_calls"],
        ),
        reverse=True,
    )
    for item in external_rows[: args.limit]:
        item.pop("_key", None)

    return {
        "schema_version": "1.0",
        "artifact_type": "witty_ub_callstack_evidence",
        "status": "evidence_ready",
        "target": args.target,
        "source_revision": args.source_revision,
        "profile_file": args.profile.name,
        "profiling_scope": "cProfile parent process plus ProcessPool scan workers",
        "profile_semantics": {
            "total_profile_cpu_seconds": round(total_profile_cpu_seconds, 6),
            "combined_worker_time_is_additive": True,
            "cumulative_times_overlap": True,
            "cprofile_overhead_present": True,
        },
        "selection": {
            "limit_per_view": args.limit,
            "source_context_radius_lines": args.context_lines,
            "project_function_count": len(project_rows),
            "selected_function_count": len(selected),
            "views": views,
        },
        "functions": selected,
        "external_runtime_hotspots": external_rows[: args.limit],
        "controlled_experiment": controlled_experiment,
        "semantic_diagnosis": {
            "performed": False,
            "required_input": (
                "The optional Jenkins semantic-diagnosis stage or a code agent "
                "must inspect this evidence and the checked-out source revision, "
                "trace callers and callees, and author a diagnosis that conforms "
                "to callstack-diagnosis.schema.json."
            ),
            "rules": [
                "Do not treat a high cumulative-time wrapper as the root cause.",
                "Separate observations, causal claims, impact, and recommendations.",
                "Use status=confirmed only with source-supported causality and a controlled validation result.",
                "Otherwise use status=investigation and specify the exact next experiment.",
                "Every recommendation must name the symbol to change, the mechanism, risks, and measurable verification.",
            ],
        },
    }


def markdown_escape(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def render_markdown(evidence: dict[str, Any]) -> str:
    lines = [
        "# Witty-UB 函数调用栈证据包",
        "",
        f"- 状态：`{evidence['status']}`",
        f"- 目标：`{evidence['target']}`",
        f"- 源码版本：`{evidence['source_revision']}`",
        f"- Profile：`{evidence['profile_file']}`",
        f"- 采集范围：{evidence['profiling_scope']}",
        "- 根因结论：`待复验`",
        "",
        "> 本文件只保存性能证据，不自动认定根因，也不生成模板化修改建议。",
        "> 后续如需形成结论，请结合 JSON 证据包和同版本源码继续分析，并保留可复验依据。",
        "",
    ]
    experiment = evidence.get("controlled_experiment")
    if experiment:
        decision = experiment["decision"]
        lines.extend(
            [
                "## 进程数对照结论",
                "",
                f"- 结果一致性：`{experiment['result_consistency']}`",
                f"- 每种模式运行：`{experiment['repeats']}` 次",
                f"- 结论：{decision['plain_conclusion']}",
                f"- 判定状态：`{decision['status']}`",
                "",
            ]
        )

    lines.extend(["## 三种证据视图", ""])
    functions = {
        item["function_id"]: item for item in evidence["functions"]
    }
    labels = {
        "by_cumulative_time": "累计时间",
        "by_self_time": "自身时间",
        "by_call_count": "调用次数",
    }
    for view_name, ids in evidence["selection"]["views"].items():
        lines.extend(
            [
                f"### 按{labels[view_name]}排序",
                "",
                "| ID | 累计(s) | 自身(s) | 调用次数 | 源码位置 |",
                "| --- | ---: | ---: | ---: | --- |",
            ]
        )
        for function_id in ids:
            row = functions[function_id]
            lines.append(
                "| {function_id} | {cumulative_seconds:.6f} | "
                "{self_seconds:.6f} | {total_calls} | "
                "`{source_location}` |".format(**row)
            )
        lines.append("")

    lines.extend(
        [
            "## 诊断使用要求",
            "",
            "后续分析时应读取 JSON 中的源码片段、调用者、",
            "子调用和外部运行时热点，并检查同版本仓库源码。若没有对照实验",
            "或足够的因果证据，只能输出 `investigation`，不能把相关性包装成",
            "已确认根因。",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    evidence = build_evidence(args)
    args.json_report.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_report.parent.mkdir(parents=True, exist_ok=True)
    args.json_report.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    args.markdown_report.write_text(
        render_markdown(evidence),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": evidence["status"],
                "selected_function_count": evidence["selection"][
                    "selected_function_count"
                ],
                "json_report": str(args.json_report),
                "markdown_report": str(args.markdown_report),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
