#!/usr/bin/env python3

"""Generate a conservative call graph rooted at the public URMA C APIs."""

import argparse
import bisect
import json
import os
import re
import signal
import sys
from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path


SCHEMA_VERSION = 1
OUTPUT_FILE = Path("/tmp/urma_api_callchains.json")
API_HEADER = "core/include/urma_api.h"
TYPES_HEADER = "core/include/urma_types.h"
TYPES_PUBLIC_APIS = ("urma_u32_to_eid", "urma_str_to_eid")
SOURCE_SUFFIXES = {".c", ".h"}
IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
TOKEN_PATTERN = re.compile(
    r"[A-Za-z_][A-Za-z0-9_]*|0[xX][0-9A-Fa-f]+|\d+|->|\.\.\."
    r"|<<=|>>=|==|!=|<=|>=|\+\+|--|&&|\|\||<<|>>|\+=|-=|\*=|/=|%=|&=|\|=|\^="
    r"|[{}()\[\].,;:=*&#?+\-/<>!~%^|]"
)
IGNORED_CALLS = {
    "if", "for", "while", "switch", "return", "sizeof", "_Alignof",
    "__alignof__", "__attribute__", "__builtin_offsetof",
}
QUALIFIERS = {
    "auto", "const", "extern", "inline", "register", "restrict", "static",
    "typedef", "volatile", "_Atomic", "struct",
}
CALLBACK_REGISTRARS = {
    "pthread_create",
    "bondp_worker_schedule",
    "bondp_worker_add_fd",
    "nl_socket_modify_cb",
}
signal.signal(signal.SIGPIPE, signal.SIG_DFL)


@dataclass(frozen=True)
class Token:
    value: str
    line: int


@dataclass
class FunctionDef:
    name: str
    source: Path
    line: int
    body_open: int
    body_close: int
    function_id: str = ""


@dataclass(frozen=True)
class Binding:
    field: str
    target_name: str
    target_id: str
    table_type: str
    table_name: str
    source: Path
    line: int

    @property
    def slot(self) -> str:
        prefix = self.table_type or self.table_name
        return f"{prefix}.{self.field}" if prefix else self.field


@dataclass(frozen=True)
class Edge:
    caller: str
    callee: str
    kind: str
    via: str = ""

    def as_json(self) -> list[str]:
        row = [self.caller, self.callee, self.kind]
        if self.via:
            row.append(self.via)
        return row


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "纯Python分析URMA C源码调用链；根API来自core/include/urma_api.h，"
            "并额外包含urma_types.h中的urma_u32_to_eid和urma_str_to_eid。"
        )
    )
    parser.add_argument("source", type=Path, help="URMA源码目录")
    parser.add_argument(
        "-o", "--output", type=Path, default=OUTPUT_FILE,
        help=f"输出JSON路径，默认{OUTPUT_FILE}",
    )
    parser.add_argument(
        "--root", action="append", default=[],
        help="仅输出指定public API的可达调用图，可重复使用",
    )
    return parser.parse_args()


def resolve_source_root(path: Path) -> Path:
    root = path.expanduser().resolve()
    if (root / API_HEADER).is_file() and (root / TYPES_HEADER).is_file():
        return root
    raise ValueError(f"指定的URMA源码目录中缺少公开头文件：{root}")


def blank_comments_strings_directives(text: str) -> str:
    pattern = re.compile(
        r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|//[^\n]*|/\*.*?\*/',
        re.DOTALL,
    )

    def blank(match: re.Match) -> str:
        return "".join("\n" if char == "\n" else " " for char in match.group(0))

    sanitized = pattern.sub(blank, text)
    lines = sanitized.splitlines(keepends=True)
    in_directive = False
    for index, line in enumerate(lines):
        stripped = line.lstrip()
        if not in_directive and stripped.startswith("#"):
            in_directive = True
        if not in_directive:
            continue
        has_newline = line.endswith("\n")
        content = line[:-1] if has_newline else line
        continued = content.rstrip().endswith("\\")
        lines[index] = " " * len(content) + ("\n" if has_newline else "")
        in_directive = continued
    return "".join(lines)


def tokenize(text: str) -> list[Token]:
    sanitized = blank_comments_strings_directives(text)
    newlines = [pos for pos, char in enumerate(sanitized) if char == "\n"]
    return [
        Token(match.group(0), bisect.bisect_right(newlines, match.start()) + 1)
        for match in TOKEN_PATTERN.finditer(sanitized)
    ]


def build_pairs(tokens: list[Token]) -> dict[int, int]:
    pairs: dict[int, int] = {}
    stacks = {"(": [], "[": [], "{": []}
    closes = {")": "(", "]": "[", "}": "{"}
    for index, token in enumerate(tokens):
        if token.value in stacks:
            stacks[token.value].append(index)
        elif token.value in closes and stacks[closes[token.value]]:
            other = stacks[closes[token.value]].pop()
            pairs[index] = other
            pairs[other] = index
    return pairs


def is_identifier(value: str) -> bool:
    return IDENTIFIER.match(value) is not None


def parse_functions(source: Path, tokens: list[Token], pairs: dict[int, int]) -> list[FunctionDef]:
    functions: list[FunctionDef] = []
    index = 0
    while index < len(tokens) - 2:
        name = tokens[index].value
        if (
            not is_identifier(name)
            or name in IGNORED_CALLS
            or tokens[index + 1].value != "("
            or (index > 0 and tokens[index - 1].value in {".", "->"})
        ):
            index += 1
            continue
        close = pairs.get(index + 1)
        if close is None:
            index += 1
            continue
        body = close + 1
        while body < len(tokens) and tokens[body].value in {"const", "noexcept"}:
            body += 1
        if body >= len(tokens) or tokens[body].value != "{":
            index += 1
            continue
        body_close = pairs.get(body)
        if body_close is None:
            index += 1
            continue
        functions.append(FunctionDef(name, source, tokens[index].line, body, body_close))
        index = body_close + 1
    return functions


def public_api_names(header: Path, allowlist: set[str] | None = None) -> list[str]:
    tokens = tokenize(header.read_text(encoding="utf-8", errors="replace"))
    pairs = build_pairs(tokens)
    names: list[str] = []
    seen: set[str] = set()
    for index in range(len(tokens) - 2):
        name = tokens[index].value
        if not name.startswith("urma_") or not is_identifier(name):
            continue
        if allowlist is not None and name not in allowlist:
            continue
        if tokens[index + 1].value != "(":
            continue
        close = pairs.get(index + 1)
        if close is None or close + 1 >= len(tokens) or tokens[close + 1].value != ";":
            continue
        if name not in seen:
            names.append(name)
            seen.add(name)
    return names


def assign_function_ids(functions: list[FunctionDef], source_root: Path) -> None:
    by_name: dict[str, list[FunctionDef]] = defaultdict(list)
    for function in functions:
        by_name[function.name].append(function)
    for name, definitions in by_name.items():
        if len(definitions) == 1:
            definitions[0].function_id = name
        else:
            for function in definitions:
                relative = function.source.relative_to(source_root).as_posix()
                function.function_id = f"{relative}:{function.line}:{name}"


def resolve_name(
    name: str, source: Path, definitions: dict[str, list[FunctionDef]]
) -> list[str]:
    candidates = definitions.get(name, [])
    local = [item.function_id for item in candidates if item.source == source]
    return local or [item.function_id for item in candidates]


def brace_depths(tokens: list[Token]) -> list[int]:
    depth = 0
    result: list[int] = []
    for token in tokens:
        result.append(depth)
        if token.value == "{":
            depth += 1
        elif token.value == "}":
            depth = max(0, depth - 1)
    return result


def initializer_decl(
    tokens: list[Token], equals: int, depths: list[int], pairs: dict[int, int]
) -> tuple[str, str]:
    start = 0
    for index in range(equals - 1, -1, -1):
        if depths[index] == 0 and tokens[index].value in {";", "}"}:
            start = index + 1
            break
    variable = -1
    for index in range(equals - 1, start - 1, -1):
        if is_identifier(tokens[index].value):
            variable = index
            break
    if variable < 0:
        return "", ""
    table_name = tokens[variable].value
    table_type = ""
    for index in range(variable - 1, start - 1, -1):
        value = tokens[index].value
        if is_identifier(value) and value not in QUALIFIERS:
            table_type = value
            break
    return table_type, table_name


def collect_bindings(
    source: Path,
    tokens: list[Token],
    pairs: dict[int, int],
    definitions: dict[str, list[FunctionDef]],
) -> list[Binding]:
    bindings: list[Binding] = []
    depths = brace_depths(tokens)
    for equals in range(len(tokens) - 1):
        if tokens[equals].value != "=" or depths[equals] != 0 or tokens[equals + 1].value != "{":
            continue
        body_close = pairs.get(equals + 1)
        if body_close is None:
            continue
        table_type, table_name = initializer_decl(tokens, equals, depths, pairs)
        index = equals + 2
        while index + 3 < body_close:
            if (
                tokens[index].value != "."
                or not is_identifier(tokens[index + 1].value)
                or tokens[index + 2].value != "="
            ):
                index += 1
                continue
            field = tokens[index + 1].value
            target = index + 3
            if tokens[target].value == "&":
                target += 1
            if target >= body_close:
                break
            target_name = tokens[target].value
            for target_id in resolve_name(target_name, source, definitions):
                bindings.append(Binding(
                    field, target_name, target_id, table_type, table_name,
                    source, tokens[index].line,
                ))
            index = target + 1
    return bindings


def callback_targets(
    tokens: list[Token], open_index: int, close_index: int,
    source: Path, definitions: dict[str, list[FunctionDef]],
) -> set[str]:
    targets: set[str] = set()
    for index in range(open_index + 1, close_index):
        name = tokens[index].value
        if not is_identifier(name) or name not in definitions:
            continue
        if index + 1 < close_index and tokens[index + 1].value == "(":
            continue
        targets.update(resolve_name(name, source, definitions))
    return targets


def collect_edges(
    functions: list[FunctionDef],
    tokens_by_source: dict[Path, list[Token]],
    pairs_by_source: dict[Path, dict[int, int]],
    definitions: dict[str, list[FunctionDef]],
    bindings: list[Binding],
) -> tuple[set[Edge], set[tuple[str, str]]]:
    edges: set[Edge] = set()
    unresolved: set[tuple[str, str]] = set()
    bindings_by_field: dict[str, list[Binding]] = defaultdict(list)
    for binding in bindings:
        bindings_by_field[binding.field].append(binding)

    for function in functions:
        tokens = tokens_by_source[function.source]
        pairs = pairs_by_source[function.source]
        index = function.body_open + 1
        while index < function.body_close - 1:
            name = tokens[index].value
            if not is_identifier(name) or tokens[index + 1].value != "(":
                index += 1
                continue
            close = pairs.get(index + 1)
            member = index > 0 and tokens[index - 1].value in {".", "->"}
            if member:
                candidates = bindings_by_field.get(name, [])
                if not candidates:
                    unresolved.add((function.function_id, name))
                for binding in candidates:
                    edges.add(Edge(function.function_id, binding.target_id, "function_pointer", binding.slot))
            elif name in definitions and name not in IGNORED_CALLS:
                for target_id in resolve_name(name, function.source, definitions):
                    edges.add(Edge(function.function_id, target_id, "direct"))
            if name in CALLBACK_REGISTRARS and close is not None:
                for target_id in callback_targets(tokens, index + 1, close, function.source, definitions):
                    edges.add(Edge(function.function_id, target_id, "callback_registration", name))
            index += 1
    return edges, unresolved


def reachable_graph(
    roots: list[str], definitions: dict[str, list[FunctionDef]], edges: set[Edge]
) -> tuple[set[str], set[Edge], list[str]]:
    root_ids: list[str] = []
    missing: list[str] = []
    for root in roots:
        candidates = definitions.get(root, [])
        if candidates:
            root_ids.extend(item.function_id for item in candidates)
        else:
            missing.append(root)
    outgoing: dict[str, list[Edge]] = defaultdict(list)
    for edge in edges:
        outgoing[edge.caller].append(edge)
    reachable = set(root_ids)
    selected: set[Edge] = set()
    queue = deque(root_ids)
    while queue:
        caller = queue.popleft()
        for edge in outgoing.get(caller, []):
            selected.add(edge)
            if edge.callee not in reachable:
                reachable.add(edge.callee)
                queue.append(edge.callee)
    return reachable, selected, missing


def build_output(
    root: Path,
    roots: list[str],
    functions: list[FunctionDef],
    reachable: set[str],
    edges: set[Edge],
    unresolved: set[tuple[str, str]],
    missing: list[str],
    bindings: list[Binding],
) -> dict:
    by_id = {function.function_id: function for function in functions}
    locations = {
        function_id: f"{by_id[function_id].source.relative_to(root).as_posix()}:{by_id[function_id].line}"
        for function_id in sorted(reachable)
    }
    edge_rows = [
        edge.as_json() for edge in sorted(edges, key=lambda item: (item.caller, item.callee, item.kind, item.via))
    ]
    reachable_unresolved = sorted(
        [caller, field] for caller, field in unresolved if caller in reachable
    )
    binding_rows = [
        {
            "slot": item.slot,
            "field": item.field,
            "target": item.target_id,
            "table": item.table_name,
            "location": f"{item.source.relative_to(root).as_posix()}:{item.line}",
        }
        for item in sorted(bindings, key=lambda value: (value.slot, value.target_id, str(value.source), value.line))
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "source_root": str(root),
        "public_headers": [API_HEADER, TYPES_HEADER],
        "types_header_api_allowlist": list(TYPES_PUBLIC_APIS),
        "roots": roots,
        "analysis": {
            "complete": not missing,
            "missing_roots": missing,
            "function_count": len(locations),
            "edge_count": len(edge_rows),
            "unresolved_indirect_count": len(reachable_unresolved),
            "limitations": [
                "候选图不证明错误传播关系",
                "运行时赋值的函数指针和跨DSO provider实现可能需要人工补充",
                "WR/CR、notifier、线程、eventfd、epoll和共享状态异步关系需要源码证据复核",
            ],
        },
        "functions": locations,
        "edges": edge_rows,
        "provider_bindings": binding_rows,
        "unresolved_indirect_calls": reachable_unresolved,
    }


def write_json(result: dict, output: Path) -> None:
    output = output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f".{output.name}.{os.getpid()}.tmp")
    try:
        with temporary.open("w", encoding="utf-8") as file:
            json.dump(result, file, ensure_ascii=False, indent=2)
            file.write("\n")
        os.replace(temporary, output)
    finally:
        if temporary.exists():
            temporary.unlink()


def main() -> int:
    args = parse_arguments()
    try:
        root = resolve_source_root(args.source)
        public_roots = public_api_names(root / API_HEADER)
        public_roots.extend(public_api_names(root / TYPES_HEADER, set(TYPES_PUBLIC_APIS)))
        public_roots = list(dict.fromkeys(public_roots))
        roots = args.root or public_roots
        unknown = sorted(set(roots) - set(public_roots))
        if unknown:
            raise ValueError("--root必须是指定公开头文件中的API：" + ", ".join(unknown))

        sources = sorted(
            path for path in root.rglob("*")
            if path.is_file() and path.suffix.lower() in SOURCE_SUFFIXES
        )
        tokens_by_source: dict[Path, list[Token]] = {}
        pairs_by_source: dict[Path, dict[int, int]] = {}
        functions: list[FunctionDef] = []
        for source in sources:
            tokens = tokenize(source.read_text(encoding="utf-8", errors="replace"))
            pairs = build_pairs(tokens)
            tokens_by_source[source] = tokens
            pairs_by_source[source] = pairs
            functions.extend(parse_functions(source, tokens, pairs))

        assign_function_ids(functions, root)
        definitions: dict[str, list[FunctionDef]] = defaultdict(list)
        for function in functions:
            definitions[function.name].append(function)
        bindings: list[Binding] = []
        for source in sources:
            bindings.extend(collect_bindings(source, tokens_by_source[source], pairs_by_source[source], definitions))
        all_edges, unresolved = collect_edges(
            functions, tokens_by_source, pairs_by_source, definitions, bindings
        )
        reachable, edges, missing = reachable_graph(roots, definitions, all_edges)
        result = build_output(root, roots, functions, reachable, edges, unresolved, missing, bindings)
        write_json(result, args.output)
    except (OSError, ValueError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 2
    analysis = result["analysis"]
    print(
        f"调用链JSON已生成：{args.output.expanduser().resolve()}，{len(roots)}个API，"
        f"{analysis['function_count']}个函数，{analysis['edge_count']}条边，"
        f"{analysis['unresolved_indirect_count']}个未解析间接调用",
        file=sys.stderr,
    )
    return 0 if analysis["complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
