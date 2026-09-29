"""generate_kvcache_conn_code.py 测试。"""

import csv
import json
import os

import generate_kvcache_conn_code as gen


def test_file_name_from_id():
    assert gen.file_name_from_id("kvcache_conn_fault_001") == "kvcache_conn_fault_001"


def test_class_name_from_id():
    assert gen.class_name_from_id("kvcache_conn_fault_001") == "KvcacheConnFault001"


def test_is_leaf():
    assert gen.is_leaf({"id": "x"}) is True
    assert gen.is_leaf({"id": "x", "children": []}) is True
    assert gen.is_leaf({"id": "x", "children": ["y"]}) is False


def test_fault_modes_data_complete():
    ids = {fm["id"] for fm in gen.FAULT_MODES}
    assert len(ids) == len(gen.FAULT_MODES)
    # 所有 children 引用都存在
    for fm in gen.FAULT_MODES:
        for child in fm.get("children", []):
            assert child in ids


def test_generate_header():
    fm = gen.FAULT_MODES[0]
    header = gen.generate_header(fm)
    assert "#pragma once" in header
    assert "class KvcacheConnFault001 : public FailureMode" in header
    assert "namespace diag" in header


# ---------------- generate_validation_code ----------------


def _fm(logic_type, **kw):
    base = {
        "id": "kvcache_conn_fault_001",
        "name": "n",
        "validation": "v",
        "root_cause": "r",
        "fix_sugg": "f",
        "logic_type": logic_type,
        "sources": ["doc.md L1"],
        "lines": "L1-L2",
    }
    base.update(kw)
    return base


def test_validation_uniq_code():
    code = gen.generate_validation_code(_fm("uniq_code", codes=[2, 3]))
    assert "HasCodeInUniqOutput" in code
    assert "{2, 3}" in code


def test_validation_grep():
    code = gen.generate_validation_code(_fm("grep", grep_keyword="kw1|kw2"))
    assert "kw1`或`kw2" in code
    assert "grep -E 'kw1|kw2'" in code


def test_validation_cmd_check_all_expecteds():
    for expected, marker in [
        ("empty", "return output.empty();"),
        ("non_empty", "return !output.empty();"),
        ("unreachable", 'output.find("unreachable")'),
        ("not_ready", 'output.find("NotReady")'),
        ("whatever", "return !output.empty();"),
    ]:
        code = gen.generate_validation_code(_fm("cmd_check", cmd="ss -tnlp", expected=expected))
        assert marker in code


def test_validation_composite_all_case_types():
    fm = _fm(
        "composite",
        cases=[
            {"type": "uniq_code", "check": "has_nonzero_code", "codes": [25], "desc": "c1"},
            {"type": "uniq_code", "check": "has_code", "codes": [1001], "desc": "c2"},
            {"type": "grep", "cmd": "grep x $LOG/a.log", "desc": "c3"},
            {"type": "access_log", "cmd": "grep y $LOG/b.log", "desc": "c4"},
            {
                "type": "access_log_field",
                "cmd": "grep z $LOG/c.log",
                "field": "respMsg",
                "keywords": ["k1", "k2"],
                "desc": "c5",
            },
            {"type": "process_check", "cmd": "pgrep -x", "desc": "c6"},
            {"type": "cmd_check", "cmd": "free -g", "check": "non_empty", "desc": "c7"},
            {"type": "cmd_check", "cmd": "free -g", "check": "empty", "desc": "c8"},
            {"type": "cmd_check", "cmd": "ip link", "check": "contains_down", "desc": "c9"},
            {"type": "cmd_check", "cmd": "free -m", "check": "memory_low", "desc": "c10"},
            {"type": "cmd_check", "cmd": "df -h", "check": "disk_usage_high", "desc": "c11"},
            {"type": "cmd_check", "cmd": "ulimit -u", "check": "not_unlimited", "desc": "c12"},
            {"type": "cmd_check", "cmd": "ls /proc/1/fd", "check": "fd_near_limit", "desc": "c13"},
            {"type": "cmd_check", "cmd": "other", "check": "unknown_check", "desc": "c14"},
            {"type": "grep_and_metrics", "grep_cmd": "grep m $LOG/d", "metrics_check": "x=+0", "desc": "c15"},
            {
                "type": "grep_and_process",
                "grep_cmd": "grep p $LOG/e",
                "process_expected": "empty",
                "desc": "c16",
            },
            {
                "type": "grep_and_process",
                "grep_cmd": "grep p $LOG/e",
                "process_expected": "nonempty",
                "desc": "c17",
            },
            {"type": "metrics_increased", "cmd": "grep mm $LOG/f", "metrics": ["m1", "m2"], "desc": "c18"},
            {"type": "resource_log", "cmd": "grep r $LOG/g", "desc": "c19"},
            {"type": "totally_unknown", "desc": "c20"},
        ],
    )
    code = gen.generate_validation_code(fm)
    assert "HasNonZeroCode(uniqOutput0)" in code
    assert "HasCodeInUniqOutput(uniqOutput1, {1001})" in code
    assert "!grepOutput2.empty()" in code
    assert "HasCodeZeroWithNotFound(accessOutput3)" in code
    assert 'accessOutput4.find("k1")' in code
    assert 'ProcessExists("datasystem_worker")' in code
    assert "!cmdOutput6.empty()" in code
    assert "cmdOutput7.empty()" in code
    assert 'cmdOutput8.find("DOWN")' in code
    assert "memory_low check requires baseline" in code
    assert "disk_usage_high check requires parsing" in code
    assert 'cmdOutput11.find("unlimited") == std::string::npos' in code
    assert "fd_near_limit requires comparing" in code
    assert "!cmdOutput13.empty()" in code
    assert "ZMQ fault=0 check requires parsing" in code
    assert "!grepOut15.empty() && !kvcache_conn_utils::ProcessExists" in code
    assert "!grepOut16.empty() && kvcache_conn_utils::ProcessExists" in code
    assert 'HasMetricsIncreased(metricsOut17, "m1")' in code
    assert "resource log check requires parsing" in code
    assert "Unrecognized case type 'totally_unknown'" in code
    assert "return case0_matched || case1_matched" in code


def test_validation_composite_no_cases():
    code = gen.generate_validation_code(_fm("composite", cases=[]))
    assert "return false;" in code


def test_validation_unknown_logic_type():
    code = gen.generate_validation_code(_fm("mystery"))
    assert "Unrecognized logic_type 'mystery'" in code
    assert "return false;" in code


def test_validation_on_all_real_fault_modes():
    """真实 FAULT_MODES 全量过一遍，保证数据驱动分支可生成。"""
    for fm in gen.FAULT_MODES:
        code = gen.generate_validation_code(fm)
        assert "return" in code


# ---------------- generate_cpp ----------------


def test_generate_cpp_leaf_and_nonleaf():
    leaf = next(fm for fm in gen.FAULT_MODES if gen.is_leaf(fm))
    nonleaf = next(fm for fm in gen.FAULT_MODES if not gen.is_leaf(fm))

    cpp = gen.generate_cpp(leaf)
    assert f'static AutoRegister' in cpp
    assert "RootCause(true," in cpp

    cpp = gen.generate_cpp(nonleaf)
    assert "RootCause(false," in cpp
    assert f'"{nonleaf["id"]}"' in cpp


# ---------------- CSV / fault tree ----------------


def test_generate_csv(tmp_path, monkeypatch):
    monkeypatch.setattr(gen, "DATA_DIR", str(tmp_path))
    gen.generate_csv()
    csv_path = tmp_path / "kvcache_conn_fault_mode.csv"
    assert csv_path.exists()
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == len(gen.FAULT_MODES)
    first = rows[0]
    assert first["故障编码"] == "kvcache_conn_fault_001"
    assert first["逻辑类型"] == "composite"
    # uniq_code 行的现象列填错误码
    uniq_row = next(r for r in rows if r["故障编码"] == "kvcache_conn_fault_002")
    assert "错误码为: 2, 3, 8" in uniq_row["故障现象"]
    # grep 行填关键字
    grep_row = next(r for r in rows if r["故障编码"] == "kvcache_conn_fault_004")
    assert "关键字:" in grep_row["故障现象"]


def test_generate_fault_tree(tmp_path, monkeypatch):
    monkeypatch.setattr(gen, "DATA_DIR", str(tmp_path))
    gen.generate_fault_tree()
    tree_path = tmp_path / "kvcache_conn_fault_mode_tree.json"
    with open(tree_path, encoding="utf-8") as f:
        tree = json.load(f)
    inner = tree["kvcache_conn"]
    assert inner["kvcache_conn_fault_001"] == gen.FAULT_MODES[0]["children"]
    assert len(inner) == len(gen.FAULT_MODES)


# ---------------- update_cmake_lists ----------------


def _write_cmake(path, body):
    path.write_text(body, encoding="utf-8")


CMAKE_BODY = """cmake_minimum_required(VERSION 3.10)
add_library(diagnosis_tool STATIC
    src/a.cpp
)
target_link_libraries(diagnosis_tool pthread)
"""


def test_update_cmake_missing_file(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(gen, "CMAKE_FILE", str(tmp_path / "CMakeLists.txt"))
    gen.update_cmake_lists(["x.cpp"])
    assert "not found" in capsys.readouterr().out


def test_update_cmake_no_block(tmp_path, monkeypatch, capsys):
    cmake = tmp_path / "CMakeLists.txt"
    _write_cmake(cmake, "no block here")
    monkeypatch.setattr(gen, "CMAKE_FILE", str(cmake))
    gen.update_cmake_lists(["x.cpp"])
    assert "Could not find add_library block" in capsys.readouterr().out


def test_update_cmake_adds_and_idempotent(tmp_path, monkeypatch, capsys):
    cmake = tmp_path / "CMakeLists.txt"
    _write_cmake(cmake, CMAKE_BODY)
    monkeypatch.setattr(gen, "CMAKE_FILE", str(cmake))

    gen.update_cmake_lists(["x.cpp", "y.cpp"])
    out = capsys.readouterr().out
    assert "Updated CMakeLists.txt with 2 new files." in out
    content = cmake.read_text(encoding="utf-8")
    assert "failure_mode_realization/x.cpp" in content
    assert "failure_mode_realization/y.cpp" in content
    assert content.count("target_link_libraries") == 1

    gen.update_cmake_lists(["x.cpp"])
    out = capsys.readouterr().out
    assert "already up to date" in out


# ---------------- main ----------------


def test_main(tmp_path, monkeypatch, capsys):
    out_dir = tmp_path / "realization"
    data_dir = tmp_path / "data"
    cmake = tmp_path / "CMakeLists.txt"
    _write_cmake(cmake, CMAKE_BODY)

    monkeypatch.setattr(gen, "OUTPUT_DIR", str(out_dir))
    monkeypatch.setattr(gen, "DATA_DIR", str(data_dir))
    monkeypatch.setattr(gen, "CMAKE_FILE", str(cmake))

    gen.main()

    assert capsys.readouterr().out.count("Generated:") >= 2 * len(gen.FAULT_MODES)
    for fm in gen.FAULT_MODES:
        assert (out_dir / f"{fm['id']}.h").exists()
        assert (out_dir / f"{fm['id']}.cpp").exists()
    assert (data_dir / "kvcache_conn_fault_mode.csv").exists()
    assert (data_dir / "kvcache_conn_fault_mode_tree.json").exists()
    assert "failure_mode_realization/" in cmake.read_text(encoding="utf-8")
    assert os.path.isdir(out_dir)
