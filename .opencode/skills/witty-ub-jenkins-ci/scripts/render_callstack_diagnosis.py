#!/usr/bin/env python3
"""Validate and render an agent-authored call-stack diagnosis."""

from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
import re
from typing import Any


VALID_STATUSES = {"confirmed", "investigation"}
VALID_CONFIDENCE = {"high", "medium", "low"}
CAUSE_PATTERN_LABELS = {
    "algorithmic_complexity": "算法复杂度",
    "repeated_work": "重复计算/重复扫描",
    "process_overhead": "进程调度固定开销",
    "io_wait": "I/O 等待",
    "lock_contention": "锁竞争",
    "serialization_overhead": "序列化开销",
    "database_query": "数据库查询",
    "memory_allocation": "内存分配",
    "other": "其他",
}
PLACEHOLDER_MARKERS = {"todo", "tbd", "待补充", "待填写"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--diagnosis", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--json-report", type=Path, required=True)
    parser.add_argument("--markdown-report", type=Path, required=True)
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def require_string(container: dict[str, Any], field: str, minimum: int = 1) -> str:
    value = container.get(field)
    if not isinstance(value, str) or len(value.strip()) < minimum:
        raise ValueError(f"{field} must be a string of at least {minimum} characters")
    lowered = value.lower()
    if any(marker in lowered for marker in PLACEHOLDER_MARKERS) or re.search(
        r"<[^>\n]{1,40}>",
        value,
    ):
        raise ValueError(f"{field} contains a placeholder marker")
    return value.strip()


def require_exact_keys(
    container: dict[str, Any],
    required: set[str],
    optional: set[str] | None = None,
    label: str = "object",
) -> None:
    optional = optional or set()
    missing = sorted(required - container.keys())
    extra = sorted(container.keys() - required - optional)
    if missing:
        raise ValueError(f"{label} is missing required fields: {missing}")
    if extra:
        raise ValueError(f"{label} contains unsupported fields: {extra}")


def require_list(
    container: dict[str, Any],
    field: str,
    minimum: int = 1,
) -> list[Any]:
    value = container.get(field)
    if not isinstance(value, list) or len(value) < minimum:
        raise ValueError(f"{field} must be a list with at least {minimum} item(s)")
    return value


def verify_source_location(
    source_root: Path,
    location: dict[str, Any],
) -> dict[str, Any]:
    require_exact_keys(
        location,
        {"path", "symbol", "anchor", "line_hint", "line_span", "role"},
        label="source_location",
    )
    path = require_string(location, "path")
    symbol = require_string(location, "symbol")
    anchor = require_string(location, "anchor", minimum=4)
    role = require_string(location, "role", minimum=10)
    line_hint = location.get("line_hint")
    line_span = location.get("line_span")
    if not isinstance(line_hint, int) or line_hint < 1:
        raise ValueError(f"{path}: line_hint must be a positive integer")
    if not isinstance(line_span, int) or line_span < 1:
        raise ValueError(f"{path}: line_span must be a positive integer")

    source_path = (source_root / path).resolve()
    root = source_root.resolve()
    if root not in source_path.parents:
        raise ValueError(f"source path escapes source root: {path}")
    if not source_path.is_file():
        raise ValueError(f"source file does not exist: {path}")
    lines = source_path.read_text(encoding="utf-8", errors="replace").splitlines()
    matches = [
        index for index, line in enumerate(lines, start=1) if anchor in line
    ]
    if len(matches) != 1:
        raise ValueError(
            f"{path}: anchor must resolve exactly once, found {len(matches)}: {anchor}"
        )
    line_start = matches[0]
    line_end = min(len(lines), line_start + line_span - 1)
    return {
        "path": path,
        "symbol": symbol,
        "anchor": anchor,
        "line_hint": line_hint,
        "line_span": line_span,
        "role": role,
        "line_start": line_start,
        "line_end": line_end,
        "reference": f"{path}:{line_start}",
        "line_verification": "verified",
    }


def validate_recommendation(
    finding_id: str,
    recommendation: dict[str, Any],
) -> str:
    require_exact_keys(
        recommendation,
        {
            "target_layer",
            "target_symbol",
            "change_steps",
            "mechanism",
            "expected_effect",
            "risks",
            "alternatives",
        },
        label=f"{finding_id}.recommendation",
    )
    require_string(recommendation, "target_layer", minimum=2)
    require_string(recommendation, "target_symbol", minimum=2)
    steps = require_list(recommendation, "change_steps")
    normalized_steps = []
    for index, step in enumerate(steps, start=1):
        if not isinstance(step, str) or len(step.strip()) < 15:
            raise ValueError(
                f"{finding_id}: recommendation step {index} is not specific enough"
            )
        normalized_steps.append(re.sub(r"\s+", " ", step.strip().lower()))
    require_string(recommendation, "mechanism", minimum=20)
    require_string(recommendation, "expected_effect", minimum=15)
    require_list(recommendation, "risks")
    alternatives = recommendation.get("alternatives")
    if not isinstance(alternatives, list):
        raise ValueError(f"{finding_id}: alternatives must be a list")
    return json.dumps(normalized_steps, ensure_ascii=False, sort_keys=True)


def validate_cause_pattern(
    finding_id: str,
    cause_pattern: dict[str, Any],
) -> None:
    require_exact_keys(
        cause_pattern,
        {"type", "plain_cause", "cost_model", "before", "after"},
        label=f"{finding_id}.cause_pattern",
    )
    pattern_type = cause_pattern.get("type")
    if pattern_type not in CAUSE_PATTERN_LABELS:
        raise ValueError(f"{finding_id}: invalid cause pattern type")
    require_string(cause_pattern, "plain_cause", minimum=15)
    cost_model = require_string(cause_pattern, "cost_model", minimum=8)
    before = require_string(cause_pattern, "before", minimum=15)
    after = require_string(cause_pattern, "after", minimum=15)
    if pattern_type == "algorithmic_complexity" and "O(" not in cost_model:
        raise ValueError(
            f"{finding_id}: algorithmic_complexity requires explicit O(...) notation"
        )
    if re.sub(r"\s+", "", before) == re.sub(r"\s+", "", after):
        raise ValueError(f"{finding_id}: cause pattern before and after are identical")


def validate_verification(
    finding_id: str,
    status: str,
    verification: dict[str, Any],
) -> None:
    require_list(verification, "correctness_invariants")
    benchmark = verification.get("benchmark")
    if not isinstance(benchmark, dict):
        raise ValueError(f"{finding_id}: benchmark must be an object")
    require_exact_keys(
        benchmark,
        {"command", "same_input", "metrics", "acceptance"},
        label=f"{finding_id}.benchmark",
    )
    require_string(benchmark, "command", minimum=3)
    require_string(benchmark, "same_input", minimum=5)
    require_list(benchmark, "metrics")
    require_string(benchmark, "acceptance", minimum=10)

    if status == "confirmed":
        controlled = verification.get("controlled_validation")
        if not isinstance(controlled, dict):
            raise ValueError(
                f"{finding_id}: confirmed finding requires controlled_validation"
            )
        require_exact_keys(
            controlled,
            {
                "method",
                "baseline",
                "variant",
                "controlled_variables",
                "result",
            },
            label=f"{finding_id}.controlled_validation",
        )
        for field in ("method", "baseline", "variant", "result"):
            require_string(controlled, field, minimum=5)
        require_list(controlled, "controlled_variables")
    else:
        experiment = verification.get("next_experiment")
        if not isinstance(experiment, dict):
            raise ValueError(
                f"{finding_id}: investigation requires next_experiment"
            )
        require_exact_keys(
            experiment,
            {
                "hypothesis",
                "change",
                "controlled_variables",
                "metrics",
                "confirmation_rule",
            },
            label=f"{finding_id}.next_experiment",
        )
        for field in ("hypothesis", "change", "confirmation_rule"):
            require_string(experiment, field, minimum=10)
        require_list(experiment, "controlled_variables")
        require_list(experiment, "metrics")


def validate(
    evidence: dict[str, Any],
    diagnosis: dict[str, Any],
    source_root: Path,
) -> dict[str, Any]:
    if evidence.get("artifact_type") != "witty_ub_callstack_evidence":
        raise ValueError("unsupported evidence artifact")
    require_exact_keys(
        diagnosis,
        {
            "schema_version",
            "artifact_type",
            "evidence_artifact",
            "summary",
            "findings",
        },
        label="diagnosis",
    )
    if diagnosis.get("schema_version") != "1.1":
        raise ValueError("diagnosis schema_version must be 1.1")
    if diagnosis.get("artifact_type") != "witty_ub_callstack_diagnosis":
        raise ValueError("unsupported diagnosis artifact")

    artifact = diagnosis.get("evidence_artifact")
    if not isinstance(artifact, dict):
        raise ValueError("evidence_artifact must be an object")
    require_exact_keys(
        artifact,
        {"file", "source_revision", "target"},
        label="evidence_artifact",
    )
    if require_string(artifact, "source_revision") != str(
        evidence.get("source_revision")
    ):
        raise ValueError("diagnosis and evidence source revisions differ")
    if require_string(artifact, "target") != str(evidence.get("target")):
        raise ValueError("diagnosis and evidence targets differ")
    require_string(artifact, "file")

    evidence_ids = {
        item["function_id"] for item in evidence.get("functions", [])
    }
    findings = diagnosis.get("findings")
    if not isinstance(findings, list):
        raise ValueError("findings must be a list")
    validated = deepcopy(diagnosis)
    seen_finding_ids: set[str] = set()
    recommendation_signatures: dict[str, str] = {}
    status_counts = {"confirmed": 0, "investigation": 0}
    verified_location_count = 0

    for finding in validated["findings"]:
        if not isinstance(finding, dict):
            raise ValueError("every finding must be an object")
        require_exact_keys(
            finding,
            {
                "finding_id",
                "title",
                "status",
                "confidence",
                "classification",
                "cause_pattern",
                "evidence_function_ids",
                "observation",
                "causal_chain",
                "root_cause",
                "source_locations",
                "recommendation",
                "verification",
            },
            label="finding",
        )
        finding_id = require_string(finding, "finding_id")
        if not re.fullmatch(r"PERF-[0-9]{3}", finding_id):
            raise ValueError(f"invalid finding_id: {finding_id}")
        if finding_id in seen_finding_ids:
            raise ValueError(f"duplicate finding_id: {finding_id}")
        seen_finding_ids.add(finding_id)
        require_string(finding, "title", minimum=10)
        status = finding.get("status")
        if status not in VALID_STATUSES:
            raise ValueError(f"{finding_id}: invalid status {status}")
        if finding.get("confidence") not in VALID_CONFIDENCE:
            raise ValueError(f"{finding_id}: invalid confidence")
        if finding.get("classification") != "performance_investigation":
            raise ValueError(f"{finding_id}: invalid classification")
        status_counts[status] += 1

        cause_pattern = finding.get("cause_pattern")
        if not isinstance(cause_pattern, dict):
            raise ValueError(f"{finding_id}: cause_pattern must be an object")
        validate_cause_pattern(finding_id, cause_pattern)

        ids = require_list(finding, "evidence_function_ids")
        unknown_ids = sorted(set(ids) - evidence_ids)
        if unknown_ids:
            raise ValueError(
                f"{finding_id}: unknown evidence function IDs: {unknown_ids}"
            )
        require_string(finding, "observation", minimum=20)
        chain = require_list(finding, "causal_chain", minimum=2)
        for index, step in enumerate(chain, start=1):
            if not isinstance(step, dict):
                raise ValueError(f"{finding_id}: causal step {index} must be an object")
            require_exact_keys(
                step,
                {"source_location", "symbol", "role", "evidence"},
                label=f"{finding_id}.causal_chain[{index}]",
            )
            for field in ("source_location", "symbol", "role", "evidence"):
                require_string(step, field, minimum=5)

        root_cause = finding.get("root_cause")
        if not isinstance(root_cause, dict):
            raise ValueError(f"{finding_id}: root_cause must be an object")
        require_exact_keys(
            root_cause,
            {"statement", "mechanism", "evidence_boundary"},
            label=f"{finding_id}.root_cause",
        )
        for field in ("statement", "mechanism", "evidence_boundary"):
            require_string(root_cause, field, minimum=20)

        locations = require_list(finding, "source_locations")
        finding["source_locations"] = [
            verify_source_location(source_root, location) for location in locations
        ]
        verified_location_count += len(finding["source_locations"])

        recommendation = finding.get("recommendation")
        if not isinstance(recommendation, dict):
            raise ValueError(f"{finding_id}: recommendation must be an object")
        signature = validate_recommendation(finding_id, recommendation)
        if signature in recommendation_signatures:
            other = recommendation_signatures[signature]
            raise ValueError(
                f"{finding_id} repeats the same change steps as {other}; "
                "merge the findings or write mechanism-specific changes"
            )
        recommendation_signatures[signature] = finding_id

        verification = finding.get("verification")
        if not isinstance(verification, dict):
            raise ValueError(f"{finding_id}: verification must be an object")
        require_exact_keys(
            verification,
            {"correctness_invariants", "benchmark"},
            {"controlled_validation", "next_experiment"},
            label=f"{finding_id}.verification",
        )
        validate_verification(finding_id, status, verification)

    summary = validated.get("summary")
    if not isinstance(summary, dict):
        raise ValueError("summary must be an object")
    require_exact_keys(
        summary,
        {
            "overall_status",
            "findings_count",
            "confirmed_count",
            "investigation_count",
            "conclusion",
        },
        label="summary",
    )
    require_string(summary, "conclusion", minimum=20)
    expected_counts = {
        "findings_count": len(findings),
        "confirmed_count": status_counts["confirmed"],
        "investigation_count": status_counts["investigation"],
    }
    for field, expected in expected_counts.items():
        if summary.get(field) != expected:
            raise ValueError(
                f"summary.{field}={summary.get(field)!r}, expected {expected}"
            )
    expected_status = (
        "confirmed"
        if status_counts["confirmed"]
        else "investigation"
        if status_counts["investigation"]
        else "no_action"
    )
    if summary.get("overall_status") != expected_status:
        raise ValueError(
            f"summary.overall_status must be {expected_status!r}"
        )

    validated["validation"] = {
        "status": "passed",
        "evidence_function_references_verified": True,
        "source_locations_verified": verified_location_count,
        "all_locations_verified": True,
        "summary_counts_verified": True,
        "duplicate_recommendations_found": False,
    }
    return validated


def markdown_escape(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Witty-UB 函数调用栈根因诊断报告",
        "",
        f"- 总体状态：`{summary['overall_status']}`",
        f"- 已确认：`{summary['confirmed_count']}`",
        f"- 待验证：`{summary['investigation_count']}`",
        f"- 源码版本：`{report['evidence_artifact']['source_revision']}`",
        f"- 分析目标：`{report['evidence_artifact']['target']}`",
        f"- 结论：{summary['conclusion']}",
        "",
        "## 先看结论：哪里慢、为什么、怎么改",
        "",
    ]
    for index, finding in enumerate(report["findings"], start=1):
        cause_pattern = finding["cause_pattern"]
        first_location = finding["source_locations"][0]
        recommendation = finding["recommendation"]
        lines.extend(
            [
                f"### {index}. {finding['title']}",
                "",
                f"- **直接原因**：{cause_pattern['plain_cause']}",
                f"- **原因范式**：{CAUSE_PATTERN_LABELS[cause_pattern['type']]}",
                f"- **复杂度/开销模型**：`{markdown_escape(cause_pattern['cost_model'])}`",
                f"- **改前**：{cause_pattern['before']}",
                f"- **改后**：{cause_pattern['after']}",
                f"- **修改位置**：`{first_location['reference']}` "
                f"`{recommendation['target_symbol']}`",
                f"- **当前结论**：`{finding['status']}`，"
                f"`{finding['confidence']}` 置信度",
                "",
            ]
        )
    lines.extend(["## 详细证据", ""])
    for finding in report["findings"]:
        cause_pattern = finding["cause_pattern"]
        lines.extend(
            [
                f"### {finding['finding_id']} {finding['title']}",
                "",
                f"- 状态：`{finding['status']}`",
                f"- 置信度：`{finding['confidence']}`",
                f"- 原因范式：`{CAUSE_PATTERN_LABELS[cause_pattern['type']]}`",
                f"- 开销模型：`{markdown_escape(cause_pattern['cost_model'])}`",
                f"- Profile 证据：`{', '.join(finding['evidence_function_ids'])}`",
                f"- 观察：{finding['observation']}",
                "",
                "#### 因果链",
                "",
            ]
        )
        for index, step in enumerate(finding["causal_chain"], start=1):
            lines.append(
                f"{index}. `{markdown_escape(step['source_location'])}` "
                f"`{markdown_escape(step['symbol'])}`：{step['role']} "
                f"证据：{step['evidence']}"
            )
        lines.extend(
            [
                "",
                "#### 根因结论与边界",
                "",
                f"- 结论：{finding['root_cause']['statement']}",
                f"- 机制：{finding['root_cause']['mechanism']}",
                f"- 证据边界：{finding['root_cause']['evidence_boundary']}",
                "",
                "#### 源码位置",
                "",
            ]
        )
        for location in finding["source_locations"]:
            lines.append(
                f"- `{location['reference']}` `{location['symbol']}`："
                f"{location['role']}（锚点已验证）"
            )
        recommendation = finding["recommendation"]
        lines.extend(
            [
                "",
                "#### 具体修改方案",
                "",
                f"- 修改层：`{recommendation['target_layer']}`",
                f"- 目标符号：`{recommendation['target_symbol']}`",
            ]
        )
        for index, step in enumerate(recommendation["change_steps"], start=1):
            lines.append(f"{index}. {step}")
        lines.extend(
            [
                f"- 生效机制：{recommendation['mechanism']}",
                f"- 预期影响：{recommendation['expected_effect']}",
                "- 风险：",
            ]
        )
        for risk in recommendation["risks"]:
            lines.append(f"  - {risk}")
        if recommendation["alternatives"]:
            lines.append("- 备选方案：")
            for alternative in recommendation["alternatives"]:
                lines.append(f"  - {alternative}")

        verification = finding["verification"]
        benchmark = verification["benchmark"]
        lines.extend(
            [
                "",
                "#### 验证",
                "",
                f"- 命令：`{markdown_escape(benchmark['command'])}`",
                f"- 同输入要求：{benchmark['same_input']}",
                f"- 指标：{', '.join(benchmark['metrics'])}",
                f"- 验收：{benchmark['acceptance']}",
                "- 正确性不变量：",
            ]
        )
        for invariant in verification["correctness_invariants"]:
            lines.append(f"  - {invariant}")
        if finding["status"] == "confirmed":
            controlled = verification["controlled_validation"]
            lines.extend(
                [
                    f"- 对照方法：{controlled['method']}",
                    f"- 基线：{controlled['baseline']}",
                    f"- 变体：{controlled['variant']}",
                    f"- 结果：{controlled['result']}",
                ]
            )
        else:
            experiment = verification["next_experiment"]
            lines.extend(
                [
                    f"- 待验证假设：{experiment['hypothesis']}",
                    f"- 实验改动：{experiment['change']}",
                    f"- 判定规则：{experiment['confirmation_rule']}",
                ]
            )
        lines.append("")

    lines.extend(
        [
            "## 诊断完整性",
            "",
            f"- 源码锚点验证数：`{report['validation']['source_locations_verified']}`",
            "- Profile 引用：`已验证`",
            "- 重复模板建议：`未发现`",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    evidence = load_json(args.evidence)
    diagnosis = load_json(args.diagnosis)
    validated = validate(evidence, diagnosis, args.source_root)
    args.json_report.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_report.parent.mkdir(parents=True, exist_ok=True)
    args.json_report.write_text(
        json.dumps(validated, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    args.markdown_report.write_text(
        render_markdown(validated),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": "passed",
                "findings": len(validated["findings"]),
                "verified_source_locations": validated["validation"][
                    "source_locations_verified"
                ],
                "json_report": str(args.json_report),
                "markdown_report": str(args.markdown_report),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
