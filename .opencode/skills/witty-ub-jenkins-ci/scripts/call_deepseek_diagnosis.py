#!/usr/bin/env python3
import argparse
import copy
import json
import os
import urllib.request
from pathlib import Path

from render_callstack_diagnosis import validate as validate_diagnosis

parser = argparse.ArgumentParser()
parser.add_argument("--evidence", type=Path, required=True)
parser.add_argument("--schema", type=Path, required=True)
parser.add_argument("--prompt", type=Path, required=True)
parser.add_argument("--source-root", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()

evidence = json.loads(args.evidence.read_text(encoding="utf-8"))
schema = args.schema.read_text(encoding="utf-8")
prompt = args.prompt.read_text(encoding="utf-8")

# 收集证据中涉及的源码文件，限制长度，避免请求过大
source_parts = []
total_chars = 0

for function in evidence.get("functions", []):
    relative = function.get("source_path")
    if not relative:
        continue

    path = (args.source_root / relative).resolve()
    if not path.is_file():
        continue

    marker = f"\n===== FILE: {relative} =====\n"
    content = path.read_text(encoding="utf-8", errors="replace")

    if marker + content in source_parts:
        continue
    if total_chars + len(content) > 160000:
        continue

    source_parts.append(marker + content)
    total_chars += len(content)

user_content = f"""
请返回一个 JSON 对象，不要使用 Markdown 代码块。

诊断要求：
{prompt}

输出 Schema：
{schema}

调用栈证据：
{json.dumps(evidence, ensure_ascii=False)}

相关源码：
{''.join(source_parts)}
"""

payload = {
    "model": os.getenv("DEEPSEEK_MODEL", "deepseek-v4-pro"),
    "messages": [
        {
            "role": "system",
            "content": (
                "你是源码性能诊断工程师。只能依据提供的证据和源码下结论。"
                "无法确认的原因必须标记为 investigation。输出必须是 JSON。"
                "JSON 顶层必须直接包含 schema_version、artifact_type、"
                "evidence_artifact、summary、findings，禁止添加 diagnosis、"
                "result 或 output 等外层包装。JSON 顶层格式示例："
                '{"schema_version":"1.1","artifact_type":'
                '"witty_ub_callstack_diagnosis","evidence_artifact":'
                '{"file":"callstack-evidence.json","source_revision":'
                '"证据版本","target":"证据目标"},"summary":'
                '{"overall_status":"no_action","findings_count":0,'
                '"confirmed_count":0,"investigation_count":0,'
                '"conclusion":"根据实际证据填写至少二十字的结论，不得照抄示例"},'
                '"findings":[]}'
            ),
        },
        {"role": "user", "content": user_content},
    ],
    "response_format": {"type": "json_object"},
    "stream": False,
    "thinking": {"type": "disabled"},
    "max_tokens": 8192,
}

base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")


def invoke(request_payload):
    request = urllib.request.Request(
        base_url.rstrip("/") + "/chat/completions",
        data=json.dumps(request_payload).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.environ['DEEPSEEK_API_KEY']}",
        },
    )
    with urllib.request.urlopen(request, timeout=300) as response:
        return json.load(response)


def invoke_with_content(request_payload, purpose, attempts=3):
    current_payload = request_payload
    for attempt in range(1, attempts + 1):
        result = invoke(current_payload)
        choice = result["choices"][0]
        message = choice["message"]
        content = message.get("content") or ""
        print(
            json.dumps(
                {
                    "event": "deepseek_response",
                    "purpose": purpose,
                    "attempt": attempt,
                    "finish_reason": choice.get("finish_reason"),
                    "content_chars": len(content),
                    "usage": result.get("usage"),
                },
                ensure_ascii=False,
            ),
            flush=True,
        )
        if content.strip():
            return result, content

        current_payload = copy.deepcopy(request_payload)
        current_payload["messages"].append(
            {
                "role": "user",
                "content": (
                    "上一次 API 响应的 content 为空。请重新执行原任务，"
                    "现在直接返回一个非空、完整、可由 json.loads 解析的 "
                    "JSON 对象，不要返回解释或 Markdown。"
                ),
            }
        )

    raise RuntimeError(
        f"DeepSeek returned empty content for {purpose} "
        f"after {attempts} attempts"
    )


_, content = invoke_with_content(payload, "initial_diagnosis")
raw_output = args.output.with_suffix(".raw.txt")
raw_output.write_text(content, encoding="utf-8")
repair_raw_output = args.output.with_name(
    f"{args.output.stem}.repair.raw.txt"
)

required_top_level = {
    "schema_version",
    "artifact_type",
    "evidence_artifact",
    "summary",
    "findings",
}


def unwrap_diagnosis(candidate):
    if not isinstance(candidate, dict):
        return candidate
    if required_top_level.issubset(candidate):
        return candidate
    for wrapper in ("diagnosis", "result", "output"):
        nested = candidate.get(wrapper)
        if isinstance(nested, dict) and required_top_level.issubset(nested):
            return nested
    return candidate


def require_diagnosis_shape(candidate):
    if not isinstance(candidate, dict):
        raise ValueError("diagnosis output must be a JSON object")
    missing = sorted(required_top_level - set(candidate))
    if missing:
        raise ValueError(
            f"diagnosis output is missing required top-level fields: {missing}"
        )


try:
    diagnosis = unwrap_diagnosis(json.loads(content))
    require_diagnosis_shape(diagnosis)
except (json.JSONDecodeError, ValueError) as first_error:
    repair_payload = {
        "model": os.getenv("DEEPSEEK_MODEL", "deepseek-v4-pro"),
        "messages": [
            {
                "role": "system",
                "content": (
                    "你是 JSON 结构修复器。只修复 JSON 语法、转义和 Schema"
                    "结构，不添加新事实，不输出 Markdown。JSON 顶层必须直接"
                    "包含 schema_version、artifact_type、evidence_artifact、"
                    "summary、findings，禁止使用外层包装。"
                ),
            },
            {
                "role": "user",
                "content": (
                    "下面的性能诊断输出不是合法 JSON。请依据 Schema 修复，"
                    "保持原有诊断内容和证据引用不变。\n\n"
                    f"Schema:\n{schema}\n\nInvalid JSON:\n{content}"
                ),
            },
        ],
        "response_format": {"type": "json_object"},
        "stream": False,
        "thinking": {"type": "disabled"},
        "max_tokens": 8192,
    }
    _, repaired_content = invoke_with_content(
        repair_payload,
        "json_structure_repair",
    )
    repair_raw_output.write_text(repaired_content, encoding="utf-8")
    try:
        diagnosis = unwrap_diagnosis(json.loads(repaired_content))
        require_diagnosis_shape(diagnosis)
    except (json.JSONDecodeError, ValueError) as second_error:
        raise RuntimeError(
            "DeepSeek returned invalid diagnosis JSON twice: "
            f"first={first_error}; repair={second_error}"
        ) from second_error

def apply_evidence_metadata(candidate):
    # These fields are deterministic evidence metadata, not model judgments.
    candidate["schema_version"] = "1.1"
    candidate["artifact_type"] = "witty_ub_callstack_diagnosis"
    candidate["evidence_artifact"] = {
        "file": args.evidence.name,
        "source_revision": evidence["source_revision"],
        "target": evidence["target"],
    }
    return candidate


def build_verified_location(function_record, source_root, role):
    source_path = function_record.get("source_path")
    line_hint = function_record.get("line")
    symbol = function_record.get("function")
    if (
        not isinstance(source_path, str)
        or not isinstance(line_hint, int)
        or not isinstance(symbol, str)
    ):
        return None

    path = (source_root / source_path).resolve()
    root = source_root.resolve()
    if root not in path.parents or not path.is_file():
        return None
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()

    candidates = []
    if symbol.isidentifier():
        candidates.extend(
            line.strip()
            for line in lines
            if f"def {symbol}(" in line
        )

    context = function_record.get("source_context")
    if isinstance(context, dict):
        context_anchor = context.get("anchor")
        if isinstance(context_anchor, str):
            candidates.append(context_anchor.strip())

    center = max(0, min(len(lines) - 1, line_hint - 1))
    nearby_indexes = sorted(
        range(max(0, center - 10), min(len(lines), center + 11)),
        key=lambda index: abs(index - center),
    )
    candidates.extend(lines[index].strip() for index in nearby_indexes)

    anchor = None
    seen = set()
    for candidate in candidates:
        if (
            len(candidate) < 4
            or candidate in seen
            or candidate.startswith("#")
            or candidate in {"try:", "else:", "finally:"}
        ):
            continue
        seen.add(candidate)
        if sum(candidate in line for line in lines) == 1:
            anchor = candidate
            break
    if anchor is None:
        return None

    if not isinstance(role, str) or len(role.strip()) < 10:
        role = (
            f"该位置对应证据函数 {function_record['function_id']}，"
            "用于定位本问题的实际调用路径。"
        )
    line_span = 1
    if isinstance(context, dict):
        start = context.get("start_line")
        end = context.get("end_line")
        if isinstance(start, int) and isinstance(end, int) and end >= start:
            line_span = end - start + 1

    return {
        "path": source_path,
        "symbol": symbol,
        "anchor": anchor,
        "line_hint": line_hint,
        "line_span": line_span,
        "role": role,
    }


def normalize_source_links(candidate):
    evidence_by_id = {
        item.get("function_id"): item
        for item in evidence.get("functions", [])
        if isinstance(item, dict)
    }
    findings = candidate.get("findings")
    if not isinstance(findings, list):
        return candidate

    for finding in findings:
        if not isinstance(finding, dict):
            continue
        old_locations = finding.get("source_locations")
        roles_by_path = {}
        if isinstance(old_locations, list):
            for location in old_locations:
                if isinstance(location, dict):
                    path = location.get("path")
                    role = location.get("role")
                    if isinstance(path, str) and isinstance(role, str):
                        roles_by_path[path] = role

        locations = []
        location_keys = set()
        evidence_ids = finding.get("evidence_function_ids")
        if isinstance(evidence_ids, list):
            for function_id in evidence_ids:
                function_record = evidence_by_id.get(function_id)
                if not isinstance(function_record, dict):
                    continue
                source_path = function_record.get("source_path")
                location = build_verified_location(
                    function_record,
                    args.source_root,
                    roles_by_path.get(source_path),
                )
                if location is None:
                    continue
                key = (location["path"], location["anchor"])
                if key in location_keys:
                    continue
                location_keys.add(key)
                locations.append(location)
                if len(locations) == 4:
                    break

        if not locations:
            raise ValueError(
                f"{finding.get('finding_id', 'finding')}: no verified source "
                "location can be derived from evidence_function_ids"
            )
        finding["source_locations"] = locations

        chain = finding.get("causal_chain")
        if not isinstance(chain, list):
            chain = []
        while len(chain) < 2:
            chain.append({})
        normalized_chain = []
        for index, step in enumerate(chain):
            if not isinstance(step, dict):
                step = {}
            location = locations[index % len(locations)]
            symbol = step.get("symbol")
            role = step.get("role")
            step_evidence = step.get("evidence")
            normalized_chain.append(
                {
                    "source_location": (
                        f"{location['path']}:{location['line_hint']}"
                    ),
                    "symbol": (
                        symbol
                        if isinstance(symbol, str) and len(symbol.strip()) >= 5
                        else location["symbol"]
                    ),
                    "role": (
                        role
                        if isinstance(role, str) and len(role.strip()) >= 5
                        else location["role"]
                    ),
                    "evidence": (
                        step_evidence
                        if isinstance(step_evidence, str)
                        and len(step_evidence.strip()) >= 5
                        else (
                            "该步骤由调用栈证据函数 "
                            f"{evidence_ids[index % len(evidence_ids)]} 定位。"
                        )
                    ),
                }
            )
        finding["causal_chain"] = normalized_chain
    return candidate


diagnosis = normalize_source_links(apply_evidence_metadata(diagnosis))

try:
    validate_diagnosis(evidence, diagnosis, args.source_root)
except ValueError as validation_error:
    validation_repair_payload = {
        "model": os.getenv("DEEPSEEK_MODEL", "deepseek-v4-pro"),
        "messages": [
            {
                "role": "system",
                "content": (
                    "你是源码诊断 JSON 修复器。根据校验错误修复诊断对象，"
                    "不得添加证据中不存在的事实。只返回符合 Schema 的 JSON"
                    "对象，顶层不得添加包装字段。"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"完整诊断上下文：\n{user_content}\n\n"
                    f"当前诊断：\n"
                    f"{json.dumps(diagnosis, ensure_ascii=False)}\n\n"
                    f"确定性校验错误：\n{validation_error}\n\n"
                    "请修复当前诊断，并确保 summary、findings、证据函数 ID、"
                    "源码锚点和状态判定全部通过给定 Schema 与校验要求。"
                ),
            },
        ],
        "response_format": {"type": "json_object"},
        "stream": False,
        "thinking": {"type": "disabled"},
        "max_tokens": 8192,
    }
    _, validation_repair_content = invoke_with_content(
        validation_repair_payload,
        "deterministic_validation_repair",
    )
    repair_raw_output.write_text(
        validation_repair_content,
        encoding="utf-8",
    )
    try:
        diagnosis = unwrap_diagnosis(
            json.loads(validation_repair_content)
        )
        require_diagnosis_shape(diagnosis)
        diagnosis = normalize_source_links(
            apply_evidence_metadata(diagnosis)
        )
        validate_diagnosis(evidence, diagnosis, args.source_root)
    except (json.JSONDecodeError, ValueError) as repaired_validation_error:
        raise RuntimeError(
            "DeepSeek diagnosis still failed deterministic validation after "
            f"one repair: first={validation_error}; "
            f"repair={repaired_validation_error}"
        ) from repaired_validation_error

args.output.write_text(
    json.dumps(diagnosis, ensure_ascii=False, indent=2),
    encoding="utf-8",
)
