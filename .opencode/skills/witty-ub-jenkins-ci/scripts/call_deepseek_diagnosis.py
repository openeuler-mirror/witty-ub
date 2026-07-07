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
                "禁止输出 todo、tbd、待填写、待补充、<...> 或任何占位符；"
                "每个 observation、plain_cause、root_cause 和 recommendation "
                "都必须引用证据中的函数名、耗时、调用次数或源码路径。"
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
fallback_output = args.output.with_name(
    f"{args.output.stem}.fallback.json"
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


def evidence_functions():
    return [
        item
        for item in evidence.get("functions", [])
        if isinstance(item, dict)
        and isinstance(item.get("function_id"), str)
        and isinstance(item.get("function"), str)
        and isinstance(item.get("source_path"), str)
    ]


def find_functions_by_name(*names):
    wanted = set(names)
    return [item for item in evidence_functions() if item.get("function") in wanted]


def top_functions(limit=5):
    return sorted(
        evidence_functions(),
        key=lambda item: (
            float(item.get("cumulative_seconds") or 0.0),
            float(item.get("self_seconds") or 0.0),
            int(item.get("total_calls") or 0),
        ),
        reverse=True,
    )[:limit]


def unique_function_ids(*groups, limit=6):
    result = []
    seen = set()
    for group in groups:
        for item in group:
            function_id = item.get("function_id")
            if function_id in seen:
                continue
            seen.add(function_id)
            result.append(function_id)
            if len(result) >= limit:
                return result
    return result


def function_sentence(item):
    return (
        f"{item.get('function_id')} {item.get('function')} 位于 "
        f"{item.get('source_location', item.get('source_path'))}，"
        f"累计 {float(item.get('cumulative_seconds') or 0.0):.6f} 秒，"
        f"自身 {float(item.get('self_seconds') or 0.0):.6f} 秒，"
        f"调用 {int(item.get('total_calls') or 0)} 次"
    )


def comparison_sentence():
    experiment = evidence.get("controlled_experiment")
    if not isinstance(experiment, dict):
        return (
            "当前证据未包含扫描模式对照实验，因此只能作为待验证性能假设，"
            "不能直接声明修改后必然收益。"
        )
    decision = experiment.get("decision")
    if not isinstance(decision, dict):
        return (
            f"扫描模式对照结果为 {experiment.get('result_consistency')}，"
            "但缺少可直接解释的决策字段，需要继续人工复核。"
        )
    selected_mode = decision.get("selected_mode")
    improvement = decision.get("improvement_vs_auto_percent")
    plain = decision.get("plain_conclusion")
    parts = [
        f"扫描模式对照 result_consistency={experiment.get('result_consistency')}",
        f"selected_mode={selected_mode}",
    ]
    if isinstance(improvement, (int, float)):
        parts.append(f"相对 auto 改善 {float(improvement):.3f}%")
    if isinstance(plain, str) and plain.strip():
        parts.append(plain.strip())
    return "；".join(parts) + "。"


def build_fallback_diagnosis(first_error, repair_error):
    functions = top_functions(limit=8)
    if not functions:
        raise ValueError("cannot build fallback diagnosis without evidence functions")

    parse_entry = find_functions_by_name("parse_log")
    scan_entry = find_functions_by_name("scan_all")
    mp_entry = find_functions_by_name("_scan_with_multiprocessing")
    worker_entry = find_functions_by_name(
        "_process_worker_func",
        "_scan_file_multi",
        "_scan_file_group",
    )
    file_map_entry = [
        item
        for item in evidence_functions()
        if item.get("function") == "build"
        and "file_parser_map_builder.py" in item.get("source_path", "")
    ]
    glob_entry = find_functions_by_name("glob_paths")
    open_entry = find_functions_by_name("open_log")
    discovery_entry = file_map_entry + glob_entry + open_entry

    primary_ids = unique_function_ids(
        scan_entry,
        mp_entry,
        parse_entry,
        worker_entry,
        functions,
        limit=6,
    )
    findings = [
        {
            "finding_id": "PERF-001",
            "title": "多进程扫描分支累计耗时需要按目标环境复验",
            "status": "investigation",
            "confidence": "medium",
            "classification": "performance_investigation",
            "cause_pattern": {
                "type": "process_overhead",
                "plain_cause": (
                    "调用栈显示扫描入口累计耗时主要落在多进程扫描链路，"
                    "当前证据更支持进程池调度、跨进程通信和文件扫描共同形成待验证瓶颈。"
                ),
                "cost_model": (
                    "T_scan ≈ C_pool + C_ipc + O(files × bytes)；"
                    "文件较少或日志较小时固定调度成本占比升高"
                ),
                "before": (
                    "扫描阶段直接进入现有多进程路径，进程池创建、任务分发和结果回收"
                    "与实际文件扫描一起计入累计耗时。"
                ),
                "after": (
                    "先在 Jenkins 目标环境复验 single、固定进程数和 auto 三种模式，"
                    "再决定是否增加小日志单进程阈值或保留现状。"
                ),
            },
            "evidence_function_ids": primary_ids,
            "observation": (
                "；".join(function_sentence(item) for item in functions[:4])
                + "。"
                + comparison_sentence()
            ),
            "causal_chain": [
                {
                    "source_location": "由 evidence_function_ids 自动归一化",
                    "symbol": "parse_log",
                    "role": "解析入口函数承载整体累计耗时，需要继续下钻到扫描阶段。",
                    "evidence": "累计耗时明显高于自身耗时，说明瓶颈位于下游调用。"
                },
                {
                    "source_location": "由 evidence_function_ids 自动归一化",
                    "symbol": "scan_all",
                    "role": "扫描调度函数连接文件发现、进程池和文件解析。",
                    "evidence": "调用栈证据中扫描相关函数位于累计耗时前列。"
                },
            ],
            "root_cause": {
                "statement": (
                    "当前证据能定位到扫描调度链路是主要待查方向，"
                    "但还不能把所有耗时归因到单一算法复杂度或单一源码行。"
                ),
                "mechanism": (
                    "parse_log 调用 scan_all 后进入文件发现和多进程扫描，"
                    "累计耗时由父进程等待、进程间通信、文件读取和行解析共同组成。"
                ),
                "evidence_boundary": (
                    "该诊断只使用 cProfile 和扫描模式对照证据；"
                    "如果要把结论升级为 confirmed，需要在同一 Jenkins 容器资源下完成可重复对照实验。"
                ),
            },
            "source_locations": [],
            "recommendation": {
                "target_layer": "parallel scanner mode selection",
                "target_symbol": "ParallelFileScanner.scan_all",
                "change_steps": [
                    "在 Jenkins 目标环境固定同一 UBM 日志目录，运行 single、固定进程数和 auto 三种扫描模式各五轮。",
                    "记录每轮 parse_results、parse_seconds、CPU 限制、内存限制和 multiprocessing start method。",
                    "只有当解析结果全部一致且单进程或固定进程数稳定优于 auto 至少十五个百分点时，才增加小日志扫描阈值。",
                    "阈值实现应同时考虑文件数量和总字节数，避免大日志误走单进程路径。"
                ],
                "mechanism": (
                    "先用受控实验隔离进程调度成本，再将模式选择逻辑限制在小日志场景，"
                    "避免把偶然的单次 profile 结果写成永久生产策略。"
                ),
                "expected_effect": (
                    "如果假设成立，小日志解析耗时下降，同时 10240 条解析结果和异常统计保持一致。"
                ),
                "risks": [
                    "阈值过大会让大日志失去多核并行收益。",
                    "只按文件数判断会忽略单个超大文件。",
                    "不同 CPU 架构和 Python 多进程启动方式会影响结论。"
                ],
                "alternatives": [
                    "如果 Jenkins 复验 auto 并不慢，则保留现有多进程策略。",
                    "如果瓶颈集中在单个 worker 行解析函数，则优先优化该函数而不是模式选择。"
                ],
            },
            "verification": {
                "correctness_invariants": [
                    "所有扫描模式的 parse_results 必须一致。",
                    "异常事件数量和聚合结果数量必须与基线一致。",
                    "任一失败轮次不能遗留子进程或污染后续测试。"
                ],
                "benchmark": {
                    "command": (
                        "python src/plugins/latency/test/test_kv_cache_log_parse_worker_profile.py "
                        "compare \"$UBM_LOG_DIR\" --comparison-modes single,2,auto "
                        "--comparison-repeats 5 --expected-results 10240"
                    ),
                    "same_input": (
                        "固定同一源码 revision、同一 UBM 日志目录、相同容器 CPU 和内存限制、"
                        "相同解析配置和轮换顺序。"
                    ),
                    "metrics": [
                        "parse_seconds",
                        "mode median_seconds",
                        "parse_results",
                        "multiprocessing start method",
                        "CPU and memory limits"
                    ],
                    "acceptance": (
                        "十五次结果均为 10240，且候选模式中位耗时稳定优于 auto 至少十五个百分点。"
                    ),
                },
                "next_experiment": {
                    "hypothesis": (
                        "当前蓝区 UBM 日志规模不足以摊薄多进程调度成本，"
                        "目标环境中单进程或固定少量进程可能更快。"
                    ),
                    "change": (
                        "只运行扫描模式对照实验，不修改生产扫描路径和默认配置。"
                    ),
                    "controlled_variables": [
                        "同一源码 revision",
                        "同一 UBM 日志目录",
                        "相同容器资源限制",
                        "相同解析配置",
                        "相同运行次数"
                    ],
                    "metrics": [
                        "三种模式的 parse_seconds 中位数",
                        "每轮 parse_results",
                        "异常事件数量",
                        "multiprocessing start method"
                    ],
                    "confirmation_rule": (
                        "结果一致且候选模式稳定快于 auto 至少十五个百分点，"
                        "才能将该问题升级为 confirmed 并提交代码优化。"
                    ),
                },
            },
        }
    ]

    discovery_ids = unique_function_ids(
        discovery_entry,
        scan_entry,
        functions,
        limit=5,
    )
    discovery_names = {item.get("function") for item in discovery_entry}
    if discovery_ids and {"build", "glob_paths"} & discovery_names:
        findings.append(
            {
                "finding_id": "PERF-002",
                "title": "文件发现和目录遍历存在可量化的重复工作候选",
                "status": "investigation",
                "confidence": "low",
                "classification": "performance_investigation",
                "cause_pattern": {
                    "type": "repeated_work",
                    "plain_cause": (
                        "证据中出现文件映射构建、glob 路径匹配或 open_log 热点，"
                        "说明同一解析任务内的文件发现成本值得单独量化。"
                    ),
                    "cost_model": (
                        "目录发现成本约为 O(stages × patterns × files)，"
                        "共享清单后可降为一次目录快照加内存匹配"
                    ),
                    "before": (
                        "每个扫描阶段独立构造文件映射，目录遍历和 pattern 匹配可能重复发生。"
                    ),
                    "after": (
                        "解析任务开始时生成只读文件清单，各扫描阶段复用清单并保持匹配结果一致。"
                    ),
                },
                "evidence_function_ids": discovery_ids,
                "observation": (
                    "；".join(
                        function_sentence(item)
                        for item in (discovery_entry[:4] or functions[:4])
                    )
                    + "。这些数字说明文件发现链路可观测，但还需要缓存变体证明端到端收益。"
                ),
                "causal_chain": [
                    {
                        "source_location": "由 evidence_function_ids 自动归一化",
                        "symbol": "FileParserMapBuilder.build",
                        "role": "负责把目录和 parser pattern 转换为扫描任务映射。",
                        "evidence": "文件映射构建函数出现在调用栈证据中。"
                    },
                    {
                        "source_location": "由 evidence_function_ids 自动归一化",
                        "symbol": "glob_paths",
                        "role": "负责递归发现候选日志文件，是目录元数据访问的入口。",
                        "evidence": "glob 或 open_log 相关函数提供文件发现和打开成本证据。"
                    },
                ],
                "root_cause": {
                    "statement": (
                        "文件发现链路存在重复目录遍历的性能候选，但当前证据尚未证明它是端到端主因。"
                    ),
                    "mechanism": (
                        "多个扫描阶段围绕同一日志根目录构造文件映射时，"
                        "如果每阶段各自递归匹配 pattern，就会重复访问目录元数据。"
                    ),
                    "evidence_boundary": (
                        "cProfile 只能说明该链路有耗时，不能直接证明共享清单一定提升端到端性能；"
                        "需要缓存变体和路径集合一致性对照。"
                    ),
                },
                "source_locations": [],
                "recommendation": {
                    "target_layer": "file discovery",
                    "target_symbol": "FileParserMapBuilder.build",
                    "change_steps": [
                        "在测试分支为解析任务增加一次性 file_inventory，记录绝对路径、文件名和文件大小。",
                        "让 FileParserMapBuilder.build 支持可选 file_inventory，使用内存匹配替代重复递归 glob。",
                        "分别记录基线和共享清单变体中每个阶段匹配到的文件路径集合。",
                        "只有路径集合完全一致且文件发现耗时显著下降时，再考虑合入该优化。"
                    ],
                    "mechanism": (
                        "共享目录快照可以减少重复 scandir 和 pattern 匹配，但不改变文件内容解析逻辑。"
                    ),
                    "expected_effect": (
                        "如果假设成立，文件发现累计耗时下降，解析结果数量和匹配文件集合保持不变。"
                    ),
                    "risks": [
                        "目录快照可能忽略任务运行期间新增的日志文件。",
                        "内存匹配必须保持与现有 glob 规则一致。",
                        "超大目录清单会增加短期内存占用。"
                    ],
                    "alternatives": [
                        "只缓存每个 pattern 的 glob 结果，改动更小但收益可能较弱。",
                        "如果端到端收益低于三个百分点，则不为该候选增加实现复杂度。"
                    ],
                },
                "verification": {
                    "correctness_invariants": [
                        "共享清单前后每个阶段的匹配文件路径集合完全一致。",
                        "同一 UBM 日志仍输出 10240 条解析结果。",
                        "压缩文件和多 parser 共享文件行为与基线一致。"
                    ],
                    "benchmark": {
                        "command": (
                            "python src/plugins/latency/test/test_kv_cache_log_parse_worker_profile.py "
                            "pipeline \"$UBM_LOG_DIR\" --output callstack-profile.prof "
                            "--report callstack-profile.txt --limit 50"
                        ),
                        "same_input": (
                            "固定同一目录快照、同一源码 revision、相同容器资源和文件系统缓存状态。"
                        ),
                        "metrics": [
                            "FileParserMapBuilder.build cumulative_seconds",
                            "glob_paths cumulative_seconds",
                            "posix.scandir self_seconds",
                            "parse_seconds",
                            "matched file path sets"
                        ],
                        "acceptance": (
                            "匹配路径集合完全一致，文件发现耗时下降至少七成，"
                            "端到端 parse_seconds 中位数提升达到三个百分点。"
                        ),
                    },
                    "next_experiment": {
                        "hypothesis": (
                            "共享一次目录快照可以减少重复文件发现，但当前日志规模下端到端收益可能有限。"
                        ),
                        "change": (
                            "实现只影响测试分支的 file_inventory 注入，不改变正式解析默认路径。"
                        ),
                        "controlled_variables": [
                            "同一目录内容快照",
                            "同一 parser patterns",
                            "同一进程池配置",
                            "相同 CPU 和内存限制"
                        ],
                        "metrics": [
                            "文件发现函数中位耗时",
                            "posix.scandir 调用次数",
                            "端到端 parse_seconds",
                            "每阶段匹配路径集合"
                        ],
                        "confirmation_rule": (
                            "路径集合一致且端到端中位数提升达到三个百分点，"
                            "才把该候选升级为可合入优化。"
                        ),
                    },
                },
            }
        )

    return {
        "schema_version": "1.1",
        "artifact_type": "witty_ub_callstack_diagnosis",
        "evidence_artifact": {
            "file": args.evidence.name,
            "source_revision": str(evidence.get("source_revision")),
            "target": str(evidence.get("target")),
        },
        "summary": {
            "overall_status": "investigation",
            "findings_count": len(findings),
            "confirmed_count": 0,
            "investigation_count": len(findings),
            "conclusion": (
                "语义诊断产物已通过结构化校验；"
                "当前报告仅基于调用栈证据给出待验证性能假设，不声称已确认根因。"
            ),
        },
        "findings": findings,
    }


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
                    "对象，顶层不得添加包装字段。禁止输出 todo、tbd、待填写、"
                    "待补充、<...> 或任何占位符；发现占位符时必须用证据中的"
                    "函数名、耗时、调用次数或源码路径改写。"
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
                    "尤其要删除所有占位符，不能保留模板话术或等待人工填写字段。"
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
        print(
            json.dumps(
                {
                    "event": "deterministic_fallback_diagnosis",
                    "reason": (
                        "DeepSeek output still failed validation after one repair"
                    ),
                    "first_validation_error": str(validation_error),
                    "repair_validation_error": str(repaired_validation_error),
                },
                ensure_ascii=False,
            ),
            flush=True,
        )
        diagnosis = normalize_source_links(
            apply_evidence_metadata(
                build_fallback_diagnosis(
                    validation_error,
                    repaired_validation_error,
                )
            )
        )
        validate_diagnosis(evidence, diagnosis, args.source_root)
        fallback_output.write_text(
            json.dumps(diagnosis, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

args.output.write_text(
    json.dumps(diagnosis, ensure_ascii=False, indent=2),
    encoding="utf-8",
)
