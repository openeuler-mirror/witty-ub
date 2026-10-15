"""aggregate_callstack.py 单元测试。"""

import json
import sys
from types import SimpleNamespace

import pytest

import aggregate_callstack as ac


# ---------------- 纯工具函数 ----------------


def test_strip_comments_and_strings_plain():
    code = "int x = 1;\nfoo(bar);"
    assert ac.strip_comments_and_strings(code) == code


def test_strip_comments_and_strings_comments():
    code = "a // c1\nb /* c2\nc3 */ d"
    out = ac.strip_comments_and_strings(code)
    # 长度与换行位置保持，注释内容被替换为空格
    assert len(out) == len(code)
    assert out.replace(" ", "") == "a\nb\nd"


def test_strip_comments_and_strings_strings():
    code = 'x = "a\\"(b"; y = \'c\';'
    out = ac.strip_comments_and_strings(code)
    assert out == "x = " + " " * 7 + "; y = " + " " * 3 + ";"


def test_strip_comments_and_strings_unterminated():
    out = ac.strip_comments_and_strings('f("abc')
    assert out == "f(" + " " * 4


def test_normalize_token():
    assert ac.normalize_token("  fn  ") == "fn"
    assert ac.normalize_token("::ns::fn") == "ns::fn"
    assert ac.normalize_token("fn") == "fn"


def test_split_name_variants():
    assert ac.split_name_variants("") == set()
    assert ac.split_name_variants("   ") == set()
    assert ac.split_name_variants("fn") == {"fn"}
    assert ac.split_name_variants("ns::fn") == {"ns::fn", "fn"}
    assert ac.split_name_variants("a::b::c") == {"a::b::c", "c"}


def test_endpoint_to_name():
    assert ac.endpoint_to_name(None, {}) == ""
    assert ac.endpoint_to_name("", {}) == ""
    # id 表优先
    assert ac.endpoint_to_name("n1", {"n1": "alpha"}) == "alpha"
    # @ 分隔取前缀
    assert ac.endpoint_to_name("fn@file.cpp:12", {}) == "fn"
    # :: 取尾
    assert ac.endpoint_to_name("ns::fn", {}) == "fn"
    # @ 先取前缀，再按 :: 取尾
    assert ac.endpoint_to_name("ns::fn@f.cpp", {}) == "fn"


# ---------------- argparse / 组件输入 ----------------


def _ns(**kw):
    base = {f"{c}_{k}": None for c in ac.SUPPORTED_COMPONENTS for k in ("src", "callstack")}
    base.update(kw)
    return SimpleNamespace(**base)


def test_parse_args_defaults(monkeypatch):
    monkeypatch.setattr(
        sys, "argv", ["p", "--ubsocket-src", "/a", "--ubsocket-callstack", "/b"]
    )
    args = ac.parse_args()
    assert args.ubsocket_src == "/a"
    assert args.ubsocket_callstack == "/b"
    assert args.umq_src is None
    assert args.output_dir == "/var/witty-ub/callstack-analysis"
    assert args.drop_existing_edges is False


def test_parse_args_flags(monkeypatch):
    monkeypatch.setattr(
        sys,
        "argv",
        ["p", "--umq-src", "/s", "--umq-callstack", "/c",
         "--output-dir", "/tmp/o", "--drop-existing-edges"],
    )
    args = ac.parse_args()
    assert args.umq_src == "/s"
    assert args.output_dir == "/tmp/o"
    assert args.drop_existing_edges is True


def test_collect_component_inputs_none():
    with pytest.raises(ValueError, match="at least one component pair"):
        ac.collect_component_inputs(_ns())


def test_collect_component_inputs_unpaired():
    with pytest.raises(ValueError, match="requires both --umq-src and --umq-callstack"):
        ac.collect_component_inputs(_ns(umq_src="/s"))


def test_collect_component_inputs_ok(tmp_path):
    src = tmp_path / "s"
    cs = tmp_path / "c.json"
    comps, roots, stacks = ac.collect_component_inputs(
        _ns(ubsocket_src=str(src), ubsocket_callstack=str(cs))
    )
    assert comps == ["ubsocket"]
    assert roots["ubsocket"] == src.resolve()
    assert stacks["ubsocket"] == cs.resolve()


# ---------------- 源文件查找 ----------------


def test_find_source_files(tmp_path):
    (tmp_path / "sub").mkdir()
    for name in ("sub/a.cpp", "b.CC", "c.h", "d.py", "e.txt", "f.hpp"):
        (tmp_path / name).write_text("", encoding="utf-8")

    files = ac.find_source_files(tmp_path)
    # 扩展名过滤（大小写不敏感），按路径长度排序
    assert {f.name for f in files} == {"a.cpp", "b.CC", "c.h", "f.hpp"}
    assert files == sorted(files, key=lambda p: len(str(p)))
    assert ac.find_source_files(tmp_path / "missing") == []


# ---------------- 花括号提取 ----------------


def test_extract_brace_block_nested():
    text = "a { b { c } d } e"
    assert ac.extract_brace_block(text, text.index("{")) == "{ b { c } d }"


def test_extract_brace_block_ignores_strings_and_comments():
    text = '{ "}" /* } */ }'
    assert ac.extract_brace_block(text, 0) == '{ "}" /* } */ }'
    text2 = "{ // }\n}"
    assert ac.extract_brace_block(text2, 0) == "{ // }\n}"


def test_extract_brace_block_invalid():
    assert ac.extract_brace_block("abc", -1) is None
    assert ac.extract_brace_block("abc", 10) is None
    assert ac.extract_brace_block("abc", 0) is None  # 非 '{' 起点
    assert ac.extract_brace_block("{ unterminated", 0) is None


# ---------------- 函数体定位 ----------------


def test_find_function_body_by_name():
    code = "int func(int x) { return x + 1; }\nint other() { return 0; }"
    assert ac.find_function_body_by_name(code, "func") == "{ return x + 1; }"
    assert ac.find_function_body_by_name(code, "missing") is None


def test_find_function_body_by_name_declaration_skipped():
    code = "void decl();\nvoid decl(int x) { body; }"
    assert ac.find_function_body_by_name(code, "decl") == "{ body; }"
    assert ac.find_function_body_by_name("void decl();", "decl") is None


def test_find_function_body_by_name_qualified_name():
    code = "void ns::fn(int x) { q; }"
    assert ac.find_function_body_by_name(code, "ns::fn") == "{ q; }"
    assert ac.find_function_body_by_name(code, "fn") == "{ q; }"


def test_find_function_body_by_name_substring_rejected():
    # myfunc( 的 'func' 前是字母，不视为命中
    code = "int myfunc() { a; }"
    assert ac.find_function_body_by_name(code, "func") is None


def test_find_function_body_by_name_with_comments():
    code = "void f/*c*/(int x) {/*b*/ return 1; }"
    assert ac.find_function_body_by_name(code, "f") == "{/*b*/ return 1; }"


# ---------------- 调用推断 ----------------


def test_build_callee_index():
    idx = ac.build_callee_index([ac.Node("ns::fn", "umq"), ac.Node("plain", "umq")])
    assert [n.name for n in idx["ns::fn"]] == ["ns::fn"]
    assert [n.name for n in idx["fn"]] == ["ns::fn"]
    assert [n.name for n in idx["plain"]] == ["plain"]
    assert idx.get("missing") is None


def test_infer_calls_from_body():
    body = 'if (x) { ns::call(); plain(); return sizeof(int); }'
    assert ac.infer_calls_from_body(body) == {"ns::call", "call", "plain"}


def test_infer_calls_from_body_strings_and_comments():
    body = '/* g(); */ s("h("); // k();\n'
    assert ac.infer_calls_from_body(body) == {"s"}


# ---------------- 边归一化 ----------------


def test_normalize_edge():
    assert ac.normalize_edge({}, {}) is None
    assert ac.normalize_edge({"src": "", "dst": "x"}, {}) is None
    assert ac.normalize_edge({"src": "n1", "dst": "n2"}, {"n1": "a", "n2": "b"}) == {
        "src": "a", "dst": "b",
    }
    assert ac.normalize_edge({"src": "f@g.cpp", "dst": "ns::g"}, {}) == {
        "src": "f", "dst": "g",
    }


# ---------------- callstack 加载 ----------------


def test_load_callstack(tmp_path):
    p = tmp_path / "cs.json"
    p.write_text(
        json.dumps(
            {
                "nodes": [
                    {"id": "n1", "name": "a", "component": "ubsocket"},
                    {"id": "n2", "name": "b"},  # 组件缺省 → expected
                    {"id": "n3", "name": ""},   # 空 name → legacy id 兜底
                    {"id": "n4"},                # 无 name，legacy id 兜底为名字
                    {},                          # 无 name 无 id → 跳过
                    {"id": "n5", "name": "a"},   # 重名去重
                ],
                "edges": [{"src": "n1", "dst": "n2"}],
            }
        ),
        encoding="utf-8",
    )
    nodes, edges, legacy = ac.load_callstack(p, "umq")
    assert [(n.name, n.component) for n in nodes] == [
        ("a", "ubsocket"), ("b", "umq"), ("n3", "umq"), ("n4", "umq"),
    ]
    assert edges == [{"src": "n1", "dst": "n2"}]
    assert legacy == {"n1": "a", "n2": "b", "n3": "n3", "n4": "n4", "n5": "a"}


# ---------------- main 集成 ----------------


UBSOCKET_SRC = """\
#include <cstdio>

static void helper_local() {}

void ub_socket_send(int fd, const void* buf) {
    umq_publish(1);
    helper_local();
}

void ub_socket_decl_only();
"""

UMQ_SRC = """\
void umq_publish(int id) {
    // body without calls
}

void umq_consume() { helper(); }
"""


@pytest.fixture()
def env(tmp_path):
    ub_src = tmp_path / "ubsocket-src"
    umq_src = tmp_path / "umq-src"
    (ub_src / "d").mkdir(parents=True)
    (ub_src / "d" / "ub_socket.cpp").write_text(UBSOCKET_SRC, encoding="utf-8")
    umq_src.mkdir(parents=True)
    (umq_src / "umq.cpp").write_text(UMQ_SRC, encoding="utf-8")

    ub_cs = tmp_path / "ubsocket.json"
    ub_cs.write_text(
        json.dumps(
            {
                "nodes": [
                    {"id": "n1", "name": "ub_socket_send", "component": "ubsocket"},
                    {"id": "n2", "name": "ub_local_recv", "component": "ubsocket"},
                ],
                "edges": [{"src": "n1", "dst": "n2"}],
            }
        ),
        encoding="utf-8",
    )
    umq_cs = tmp_path / "umq.json"
    umq_cs.write_text(
        json.dumps(
            {
                "nodes": [
                    {"id": "m1", "name": "umq_publish", "component": "umq"},
                    {"name": "umq_consume", "component": "umq"},
                ],
                "edges": [],
            }
        ),
        encoding="utf-8",
    )
    out_dir = tmp_path / "out"
    return {
        "argv": [
            "aggregate_callstack.py",
            "--ubsocket-src", str(ub_src),
            "--ubsocket-callstack", str(ub_cs),
            "--umq-src", str(umq_src),
            "--umq-callstack", str(umq_cs),
            "--output-dir", str(out_dir),
        ],
        "out_dir": out_dir,
    }


def test_main_integration(env, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", env["argv"])
    assert ac.main() == 0
    out = capsys.readouterr().out
    assert "[done] output_dir=" in out

    overall = json.loads((env["out_dir"] / "overall_callstack.json").read_text(encoding="utf-8"))
    by_name = {n["name"]: n["component"] for n in overall["nodes"]}
    assert by_name == {
        "ub_socket_send": "ubsocket",
        "ub_local_recv": "ubsocket",
        "umq_publish": "umq",
        "umq_consume": "umq",
    }
    assert {(e["src"], e["dst"]) for e in overall["edges"]} == {
        ("ub_socket_send", "ub_local_recv"),   # 既有边（legacy id 归一）
        ("ub_socket_send", "umq_publish"),    # 新推断的跨组件边
    }

    stats = json.loads((env["out_dir"] / "stats.json").read_text(encoding="utf-8"))
    assert stats["components"] == ["ubsocket", "umq"]
    assert stats["node_count"] == 4
    assert stats["existing_edge_count"] == 1
    assert stats["cross_component_edge_count"] == 1
    assert stats["merged_edge_count"] == 2
    assert stats["resolved_function_bodies"] == 3
    assert stats["unresolved_function_bodies"] == 1  # ub_local_recv 无源码定义
    assert stats["cross_edges_by_pair"] == {"ubsocket->umq": 1}


def test_main_drop_existing_edges(env, monkeypatch):
    monkeypatch.setattr(sys, "argv", env["argv"] + ["--drop-existing-edges"])
    assert ac.main() == 0
    overall = json.loads((env["out_dir"] / "overall_callstack.json").read_text(encoding="utf-8"))
    assert overall["edges"] == [{"src": "ub_socket_send", "dst": "umq_publish"}]
    stats = json.loads((env["out_dir"] / "stats.json").read_text(encoding="utf-8"))
    assert stats["merged_edge_count"] == 1


def test_main_missing_paths(tmp_path, monkeypatch):
    cs = tmp_path / "cs.json"
    cs.write_text("{}", encoding="utf-8")
    src = tmp_path / "src"
    src.mkdir()

    monkeypatch.setattr(
        sys, "argv",
        ["p", "--ubsocket-src", str(tmp_path / "nope"), "--ubsocket-callstack", str(cs),
         "--output-dir", str(tmp_path / "o")],
    )
    with pytest.raises(FileNotFoundError, match="source path not found"):
        ac.main()

    monkeypatch.setattr(
        sys, "argv",
        ["p", "--ubsocket-src", str(src), "--ubsocket-callstack", str(tmp_path / "nope.json"),
         "--output-dir", str(tmp_path / "o")],
    )
    with pytest.raises(FileNotFoundError, match="callstack not found"):
        ac.main()
