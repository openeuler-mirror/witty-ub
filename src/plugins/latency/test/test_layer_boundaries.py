"""层级边界测试：扫描器子树与任务层不得 import 老解析器实现。

规矩见 `witty-ub-解析架构-目标结构.md` §4（R4）：**契约数据只在三处** ——
`parse/labels.py`、`parse/keywords.py`、`parse/columns.py`。
`parse/parallel_scanner/**` 与 `task/**` 只要 import 到下面 8 个老解析器模块，
本测试即 fail 并打印越界清单：

    base_parser / sdk_access_log_parser / worker_access_log_parser /
    worker_info_parser / urma_log_parser / remote_pull_log_parser /
    link_log_parser / query_meta_log_parser

两条口径（都写死在测试里，改口径必须改这里）：

1. **`if TYPE_CHECKING:` 块内的 import 不计越界** —— 它不产生运行时依赖
   （现在只有 `file_parser_map_builder.py` 用它做类型注解）。这类 import 仍会
   被列出来，供 P2 一起收拾。
2. **运行时行为依赖走白名单**：4 个解析器**类**目前仍被实例化 / isinstance 分派
   （P2 才处理），允许 `from latency.parse import <类名>`。每个白名单条目是
   (相对 src 的文件路径, 类名)，**多一条少一条都会 fail**，逼着改的人显式表态。
"""

from __future__ import annotations

import ast
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[3]  # .../src
SCAN_ROOTS = (
    SRC_ROOT / "plugins/latency/parse/parallel_scanner",
    SRC_ROOT / "plugins/latency/task",
)

#: 越界模块名（`latency.parse.<名>` 或 `parse.<名>`）
FORBIDDEN_MODULES = frozenset({
    "base_parser",
    "sdk_access_log_parser",
    "worker_access_log_parser",
    "worker_info_parser",
    "urma_log_parser",
    "remote_pull_log_parser",
    "link_log_parser",
    "query_meta_log_parser",
})

#: 仍被运行时使用的解析器类（isinstance 分派 / 实例化），P2 处理
PARSER_CLASSES = frozenset({
    "SdkAccessLogParser",
    "WorkerAccessLogParser",
    "WorkerInfoParser",
    "ClientInfoParser",
})

#: 允许的「老解析器类」运行时 import：(相对 src 的路径, 类名)
ALLOWED_RUNTIME_CLASS_IMPORTS = frozenset({
    ("plugins/latency/parse/parallel_scanner/scan_vector.py", "SdkAccessLogParser"),
    ("plugins/latency/parse/parallel_scanner/scan_vector.py", "WorkerAccessLogParser"),
    ("plugins/latency/parse/parallel_scanner/scan_vector.py", "WorkerInfoParser"),
    ("plugins/latency/parse/parallel_scanner/scan_vector.py", "ClientInfoParser"),
    ("plugins/latency/parse/parallel_scanner/scan_vector_access.py", "SdkAccessLogParser"),
    ("plugins/latency/parse/parallel_scanner/scan_vector_access.py", "WorkerAccessLogParser"),
    ("plugins/latency/parse/parallel_scanner/scan_vector_access.py", "ClientInfoParser"),
    ("plugins/latency/parse/parallel_scanner/scan_vector_info.py", "ClientInfoParser"),
    ("plugins/latency/task/worker/kv_cache_log_parse_worker.py", "SdkAccessLogParser"),
    ("plugins/latency/task/worker/kv_cache_log_parse_worker.py", "WorkerAccessLogParser"),
    ("plugins/latency/task/worker/kv_cache_log_parse_worker.py", "WorkerInfoParser"),
    ("plugins/latency/task/worker/kv_cache_log_parse_worker.py", "ClientInfoParser"),
})


def _rel(path: Path) -> str:
    return path.relative_to(SRC_ROOT).as_posix()


def _is_type_checking_guard(node: ast.If) -> bool:
    test = node.test
    names = []
    if isinstance(test, ast.Name):
        names.append(test.id)
    elif isinstance(test, ast.Attribute):
        names.append(test.attr)
    return any(name == "TYPE_CHECKING" for name in names)


def _collect_imports(path: Path):
    """返回 [(行号, 模块名, 名字列表, 是否在 TYPE_CHECKING 块内), ...]。"""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found = []

    def visit(node, in_type_checking: bool) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.If) and _is_type_checking_guard(child):
                for sub in child.body:
                    visit(sub, True)
                for sub in child.orelse:
                    visit(sub, in_type_checking)
                continue
            if isinstance(child, ast.ImportFrom):
                found.append((
                    child.lineno,
                    child.module or "",
                    [alias.name for alias in child.names],
                    in_type_checking,
                ))
            elif isinstance(child, ast.Import):
                for alias in child.names:
                    found.append((child.lineno, alias.name, [], in_type_checking))
            visit(child, in_type_checking)

    visit(tree, False)
    return found


def _scan():
    violations = []          # (文件, 行, 模块, 名字)
    type_only = []           # 同上，但在 TYPE_CHECKING 块内
    class_imports = set()    # 白名单用的 (文件, 类名)

    for root in SCAN_ROOTS:
        for path in sorted(root.rglob("*.py")):
            rel = _rel(path)
            for lineno, module, names, in_tc in _collect_imports(path):
                parts = module.split(".")

                # 相对 import（from .columnar import ...）留在同层，不算跨层
                if module == "" or not module.startswith("latency"):
                    continue

                is_package = module == "latency.parse"
                leaf = parts[3] if len(parts) > 3 and parts[:2] == ["latency", "parse"] else None

                if leaf in FORBIDDEN_MODULES or (
                    leaf is None and any(p in FORBIDDEN_MODULES for p in parts)
                ):
                    (type_only if in_tc else violations).append((rel, lineno, module, names))
                elif is_package and any(name in PARSER_CLASSES for name in names):
                    class_imports.add((rel, tuple(n for n in names if n in PARSER_CLASSES)))
                elif leaf is not None and not module.startswith("latency.parse."):
                    continue

    return violations, type_only, class_imports


def test_no_cross_layer_import_of_reference_parsers():
    """parallel_scanner/** 与 task/** 不得 import 老解析器实现（TYPE_CHECKING 除外）。"""
    violations, type_only, class_imports = _scan()

    report = "\n".join(
        f"  {rel}:{lineno}  from {module} import {names}" for rel, lineno, module, names in violations
    )
    assert not violations, (
        f"跨层 import 越界 {len(violations)} 处（契约数据只准来自 "
        f"parse/labels.py、parse/keywords.py、parse/columns.py）：\n{report}"
    )

    # TYPE_CHECKING 内的 import 不算越界，但列出来（P2 一并处理）
    if type_only:
        print("TYPE_CHECKING 内的老解析器 import（无运行时依赖，P2 处理）：")
        for rel, lineno, module, names in type_only:
            print(f"  {rel}:{lineno}  from {module} import {names}")


def test_runtime_class_imports_stay_on_the_allowlist():
    """4 个解析器类仍被使用时，必须逐条登记在白名单里（P2 才清）。"""
    _, _, class_imports = _scan()

    pairs = {(rel, name) for rel, names in class_imports for name in names}
    missing = pairs - ALLOWED_RUNTIME_CLASS_IMPORTS
    stale = ALLOWED_RUNTIME_CLASS_IMPORTS - pairs

    assert not missing, (
        "新增了未登记的「老解析器类」运行时依赖（要么改回契约文件，要么显式加进白名单）：\n  "
        + "\n  ".join(sorted(f"{rel} → {name}" for rel, name in missing))
    )
    assert not stale, (
        "白名单里有已经不存在的条目（说明老依赖已清掉，请同步收窄白名单）：\n  "
        + "\n  ".join(sorted(f"{rel} → {name}" for rel, name in stale))
    )


def test_contract_modules_are_leaf_modules():
    """三个契约文件不得反向 import 老解析器（否则收敛会绕回来）。"""
    offenders = []
    for name in ("labels", "keywords", "columns"):
        path = SRC_ROOT / "plugins/latency/parse" / f"{name}.py"
        for lineno, module, _names, _tc in _collect_imports(path):
            leaf = module.rsplit(".", 1)[-1]
            if leaf in FORBIDDEN_MODULES:
                offenders.append(f"{_rel(path)}:{lineno} → {module}")
    assert not offenders, "契约文件反向依赖老解析器：\n  " + "\n  ".join(offenders)
