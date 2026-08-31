#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]


def load_script(name: str):
    path = SKILL_ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


runtime_scan = load_script("find_kvcache_runtime_err")
runtime_batches = load_script("prepare_kvcache_runtime_batches")
runtime_state = load_script("kvcache_runtime_state")
callgraph_query = load_script("query_kvcache_callgraph")
status_ast = load_script("analyze_kvcache_status_ast")
pipeline_validator = load_script("validate_kvcache_pipeline")


class RuntimePipelineTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        header = self.root / "include/datasystem/utils/status.h"
        header.parent.mkdir(parents=True)
        header.write_text(
            "enum StatusCode : int { K_OK = 0, K_INVALID = 2, K_RUNTIME_ERROR = 5 };\n",
            encoding="utf-8",
        )
        source = self.root / "src/datasystem/sample.cpp"
        source.parent.mkdir(parents=True)
        source.write_text(
            """
inline constexpr char kStableMarker[] = "Coordinator callback failed";

Status Worker::Run()
{
    LOG_IF_ERROR(FetchOne(), "Fetch failed");
    LOG_IF_ERROR(FetchTwo(), "Fetch failed");
    RETURN_STATUS_LOG_ERROR(StatusCode::K_INVALID, "Bad key");
}

void Worker::Report()
{
    LOG(ERROR) << "Read " << key << " failed";
}

void Worker::ReportLocalString()
{
    const std::string errMsg = "AccessRecorder is not init.";
    if (ShouldReport()) {
        LOG(ERROR) << errMsg;
    }
}

void Worker::ReportLocalStream()
{
    std::ostringstream err;
    err << "Open " << path << " failed";
    LOG(ERROR) << err.str();
}

void Worker::ReportFormattedLocal(bool final)
{
    std::string errMsg = FormatString("Submit failed, %sbatch=%u", final ? "final " : "", batch);
    LOG(ERROR) << errMsg;
}

void Worker::ReportAutoLocal()
{
    const auto errorMsg = "Worker wait failed: id=" + std::to_string(id);
    LOG(ERROR) << errorMsg;
}

void Worker::ReportConstant()
{
    LOG(ERROR) << kStableMarker;
}

void Worker::ReportException(const std::exception &error)
{
    LOG(ERROR) << ": " << error.what();
}

void Worker::ReportStatus(Status rc)
{
    LOG(ERROR) << rc.GetMsg();
    rc = FetchAnotherStatus();
    LOG(ERROR) << rc.GetMsg();
}

void Worker::ReportBranch(bool first)
{
    std::string errMsg;
    if (first) {
        errMsg = "first failure";
    } else {
        errMsg = "second failure";
    }
    LOG(ERROR) << errMsg;
}

void Worker::ReportWrapper(std::string message)
{
    LOG_IF_ERROR(FetchThree(), message);
}
""".lstrip(),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_scan_extracts_templates_lanes_and_groups(self) -> None:
        definitions = runtime_scan.parse_status_definitions(self.root)
        entries = runtime_scan.collect_logs(self.root / "src/datasystem", definitions)
        result = runtime_scan.build_json_result(
            entries, definitions, self.root / "src/datasystem"
        )

        self.assertEqual(result["schema_version"], 5)
        self.assertEqual(result["total"], 14)
        self.assertEqual(result["group_total"], 13)
        self.assertEqual(result["lane_totals"]["semantic"], 6)
        self.assertEqual(result["lane_totals"]["deterministic"], 7)
        self.assertEqual(pipeline_validator.validate_runtime(result), [])

        fetch_group = next(
            group for group in result["groups"]
            if group["stable_literals"] == ["Fetch failed", "Detail: "]
        )
        self.assertEqual(fetch_group["candidate_count"], 2)
        self.assertEqual(fetch_group["analysis_lane"], "semantic")
        self.assertEqual(len(fetch_group["physical_sites"]), 2)
        self.assertEqual(len(fetch_group["content_hash"]), 64)

        invalid = next(entry for entry in result["entries"] if entry["error_code"] == "K_INVALID")
        self.assertEqual(invalid["analysis_lane"], "deterministic")
        self.assertIn("RETURN_STATUS_LOG_ERROR", invalid["statement"])
        self.assertIn("Worker::Run", invalid["callable"])

        stream = next(entry for entry in result["entries"] if entry["function"] == "Report")
        self.assertEqual(stream["stable_literals"], ["Read ", " failed"])
        self.assertIn("<dynamic>", stream["normalized_template"])

        local_string = next(entry for entry in result["entries"] if entry["function"] == "ReportLocalString")
        self.assertEqual(local_string["stable_literals"], ["AccessRecorder is not init."])
        self.assertFalse(local_string["need_skill"])

        local_stream = next(entry for entry in result["entries"] if entry["function"] == "ReportLocalStream")
        self.assertEqual(local_stream["stable_literals"], ["Open ", " failed"])
        self.assertFalse(local_stream["need_skill"])

        formatted = next(entry for entry in result["entries"] if entry["function"] == "ReportFormattedLocal")
        self.assertEqual(formatted["stable_literals"], ["Submit failed, ", "batch="])
        self.assertFalse(formatted["need_skill"])

        auto_local = next(entry for entry in result["entries"] if entry["function"] == "ReportAutoLocal")
        self.assertEqual(auto_local["stable_literals"], ["Worker wait failed: id="])
        self.assertFalse(auto_local["need_skill"])

        constant = next(entry for entry in result["entries"] if entry["function"] == "ReportConstant")
        self.assertEqual(constant["stable_literals"], ["Coordinator callback failed"])

        exception = next(entry for entry in result["entries"] if entry["function"] == "ReportException")
        self.assertEqual(exception["stable_literals"], [": "])
        self.assertEqual(exception["template_confidence"], "dynamic_only")
        self.assertIn("resolve_log_template", {task["task"] for task in exception["skill_analysis"]})

        status_entries = [entry for entry in result["entries"] if entry["function"] == "ReportStatus"]
        self.assertEqual(len({entry["group_id"] for entry in status_entries}), 2)
        status = status_entries[0]
        self.assertEqual(status["template_confidence"], "dynamic_only")
        self.assertTrue(status["need_skill"])
        self.assertEqual(
            {task["task"] for task in status["skill_analysis"]},
            {"resolve_status_code", "resolve_log_template"},
        )

        branch = next(entry for entry in result["entries"] if entry["function"] == "ReportBranch")
        self.assertEqual(branch["stable_literals"], [])
        self.assertEqual(
            [task["task"] for task in branch["skill_analysis"]],
            ["resolve_log_template"],
        )

        wrapper = next(entry for entry in result["entries"] if entry["function"] == "ReportWrapper")
        self.assertEqual(wrapper["stable_literals"], ["Detail: "])
        self.assertEqual(wrapper["template_confidence"], "dynamic_only")
        self.assertIn("resolve_log_template", {task["task"] for task in wrapper["skill_analysis"]})

    def test_batching_never_splits_a_callable(self) -> None:
        groups = [
            {"callable_key": "a", "group_id": "a1"},
            {"callable_key": "a", "group_id": "a2"},
            {"callable_key": "b", "group_id": "b1"},
        ]
        batches = runtime_batches.make_batches(
            runtime_batches.group_by_callable(groups), target_groups=1
        )
        self.assertEqual([[group["group_id"] for group in batch] for batch in batches], [
            ["a1", "a2"], ["b1"],
        ])

    def test_state_reuses_only_exact_unique_content(self) -> None:
        runtime = {
            "schema_version": 5,
            "groups": [
                {
                    "group_id": "new-a", "content_hash": "hash-a", "callable_key": "a",
                    "analysis_lane": "semantic",
                },
                {
                    "group_id": "new-b", "content_hash": "hash-b", "callable_key": "b",
                    "analysis_lane": "deterministic",
                },
            ],
        }
        old = [
            {
                "group_id": "old-a", "content_hash": "hash-a", "callable_key": "a",
                "analysis_lane": "semantic", "state": "resolved", "result": {"node": 1},
            }
        ]
        records, reused = runtime_state.initialize(runtime, old)
        self.assertEqual(reused, 1)
        self.assertEqual(records[0]["state"], "resolved")
        self.assertEqual(records[0]["result"], {"node": 1})
        self.assertEqual(records[1]["state"], "pending")

    def test_callgraph_query_returns_only_local_slice(self) -> None:
        runtime = {
            "groups": [
                {"group_id": "g1", "callable": "Status Worker::Run()", "function": "Run"},
                {"group_id": "g2", "callable": "Status Worker::Leaf()", "function": "Leaf"},
            ]
        }
        callgraph = {
            "functions": [
                {"qualified_name": "datasystem::Api::Get", "function_name": "Get", "entry": True,
                 "callers": [], "callees": ["datasystem::Worker::Run"]},
                {"qualified_name": "datasystem::Worker::Run", "function_name": "Run", "entry": False,
                 "callers": ["datasystem::Api::Get"], "callees": ["datasystem::Worker::Leaf"]},
                {"qualified_name": "datasystem::Worker::Leaf", "function_name": "Leaf", "entry": False,
                 "callers": ["datasystem::Worker::Run"], "callees": []},
                {"qualified_name": "datasystem::Other", "function_name": "Other", "entry": True,
                 "callers": [], "callees": []},
            ],
            "edges": [
                {"caller": "datasystem::Api::Get", "callee": "datasystem::Worker::Run", "kind": "direct"},
                {"caller": "datasystem::Worker::Run", "callee": "datasystem::Worker::Leaf", "kind": "direct"},
            ],
        }
        result = callgraph_query.build_slice(callgraph, runtime, [runtime["groups"][1]], 2, "callers")
        names = {item["qualified_name"] for item in result["functions"]}
        self.assertEqual(names, {
            "datasystem::Api::Get", "datasystem::Worker::Run", "datasystem::Worker::Leaf",
        })
        self.assertEqual(result["root_matches"][0]["matches"], ["datasystem::Worker::Leaf"])

    def test_libclang_status_propagation_resolves_complete_singleton(self) -> None:
        source = self.root / "src/datasystem/ast_sample.cpp"
        source.write_text(
            """
enum StatusCode { K_OK = 0, K_INVALID = 2 };
class Status {
public:
    Status(StatusCode code) : code_(code) {}
    bool IsError() const { return code_ != K_OK; }
private:
    StatusCode code_;
};
#define LOG_IF_ERROR(statement_, msg_) do { Status rc_ = (statement_); (void)rc_; } while (false)
Status Leaf() { return Status(K_INVALID); }
Status Top() { return Leaf(); }
void Report() { LOG_IF_ERROR(Top(), "top failed"); }
""".lstrip(),
            encoding="utf-8",
        )
        database = [{
            "directory": str(self.root),
            "file": str(source),
            "arguments": ["clang++", "-std=c++17", "-c", str(source), "-o", "ast_sample.o"],
        }]
        task = status_ast.compile_tasks(database, {source.resolve()})[0]
        task_result = status_ast.analyze_task(task)
        self.assertIsNone(task_result["error"])

        line = next(i for i, value in enumerate(source.read_text().splitlines(), 1) if "LOG_IF_ERROR" in value and "#define" not in value)
        runtime = {
            "scan_fingerprint": "scan",
            "error_definitions": {"K_OK": 0, "K_INVALID": 2},
            "entries": [{
                "candidate_id": "c1", "group_id": "g1", "file": "ast_sample.cpp",
                "line": line, "statement_end_line": line, "analysis_lane": "semantic",
            }],
            "groups": [{
                "group_id": "g1", "content_hash": "hash", "analysis_lane": "semantic",
                "candidate_ids": ["c1"],
            }],
        }
        result = status_ast.build_result(runtime, [task_result], self.root / "src/datasystem", self.root / "compile_commands.json")
        self.assertEqual(result["groups"][0]["auto_error_code"], "K_INVALID")
        self.assertEqual(pipeline_validator.validate_ast(runtime, result), [])

    def test_final_validator_checks_a_small_dag(self) -> None:
        nodes = [
            {
                "故障编号": "kvcache_access_001", "节点类型": "access_log_entry",
                "错误码": "K_OK(0)",
                "匹配条件": {"status_code": 0, "resp_msg_nonempty": True},
            },
            {
                "故障编号": "kvcache_runtime_001", "节点类型": "runtime_log",
                "故障现象": "依次匹配`stable failure`",
                "故障名称": "对象读取时数据不存在",
                "故障原因": "执行对象读取时，下游存储未找到目标数据，导致读取无法完成。",
            },
        ]
        tree = {"kvcache": {
            "kvcache_access_001": ["kvcache_runtime_001"],
            "kvcache_runtime_001": ["urma_001"],
        }, "urma": {"urma_001": []}}
        self.assertEqual(pipeline_validator.validate_final(nodes, tree), [])

        nodes[0]["错误码"] = None
        self.assertIn("错误码必须为 K_OK(0)", "\n".join(
            pipeline_validator.validate_final(nodes, tree)
        ))
        nodes[0]["错误码"] = "K_OK(0)"

        nodes[1]["错误码"] = "K_OK(0)"
        self.assertIn("仅 code=0 + respMsg 非空根可使用 K_OK(0)", "\n".join(
            pipeline_validator.validate_final(nodes, tree)
        ))
        nodes[1].pop("错误码")

        nodes[1]["故障现象"] = pipeline_validator.NO_STABLE_KEYWORD_PHENOMENON
        self.assertIn("无稳定关键字节点未显式禁用日志匹配", "\n".join(
            pipeline_validator.validate_final(nodes, tree)
        ))
        nodes[1]["日志匹配"] = {
            "enabled": False,
            "reason": "源码分析后仅输出上游动态 Status 消息",
        }
        self.assertEqual(pipeline_validator.validate_final(nodes, tree), [])

    def test_state_validator_requires_template_evidence_or_explicit_disable(self) -> None:
        runtime = {
            "scan_fingerprint": "scan",
            "groups": [{
                "group_id": "g1",
                "content_hash": "hash",
                "skill_analysis": [{"task": "resolve_log_template"}],
            }],
        }
        state = self.root / "state.jsonl"

        def write_result(log_template: dict) -> None:
            state.write_text("\n".join([
                '{"scan_fingerprint":"scan"}',
                '{"group_id":"g1","content_hash":"hash","state":"resolved","result":'
                + '{"log_template":' + json.dumps(log_template, ensure_ascii=False) + '}}',
            ]) + "\n", encoding="utf-8")

        write_result({
            "stable_literals": ["stable failure"],
            "normalized_template": "stable failure<dynamic>",
            "evidence": ["sample.cpp:10 的局部常量"],
            "match_enabled": True,
        })
        self.assertEqual(pipeline_validator.validate_state(runtime, state, True), [])

        write_result({
            "stable_literals": [],
            "evidence": ["sample.cpp:10 仅输出调用方传入的 message"],
            "match_enabled": False,
            "reason": "所有调用方消息均为运行时动态内容",
        })
        self.assertEqual(pipeline_validator.validate_state(runtime, state, True), [])


if __name__ == "__main__":
    unittest.main()
