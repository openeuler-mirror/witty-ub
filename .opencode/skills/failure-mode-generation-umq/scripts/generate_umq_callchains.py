#!/usr/bin/env python3

"""Generate a conservative call graph rooted at the public UMQ APIs."""

import argparse
import bisect
import json
import os
import re
import sys
from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path


SCHEMA_VERSION = 1
OUTPUT_FILE = Path("/tmp/umq_api_callchains.json")
PUBLIC_HEADERS = (
    "umq_api.h",
    "umq_dfx_api.h",
    "umq_pro_api.h",
)
SOURCE_SUFFIXES = {".c", ".h"}
IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
TOKEN_PATTERN = re.compile(
    r"[A-Za-z_][A-Za-z0-9_]*"
    r"|0[xX][0-9A-Fa-f]+"
    r"|\d+"
    r"|->|\.\.\.|<<=|>>=|==|!=|<=|>=|\+\+|--|&&|\|\||<<|>>"
    r"|\+=|-=|\*=|/=|%=|&=|\|=|\^="
    r"|[{}()\[\].,;:=*&#?+\-/<>!~%^|]"
)
IGNORED_CALL_NAMES = {
    "if",
    "for",
    "while",
    "switch",
    "return",
    "sizeof",
    "_Alignof",
    "__alignof__",
    "__attribute__",
    "__builtin_offsetof",
}
DECLARATION_QUALIFIERS = {
    "auto",
    "const",
    "extern",
    "inline",
    "register",
    "restrict",
    "static",
    "typedef",
    "volatile",
    "_Atomic",
}


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
        if self.table_type:
            return f"{self.table_type}.{self.field}"
        return self.field


@dataclass(frozen=True)
class Edge:
    caller: str
    callee: str
    kind: str
    via: str = ""

    def as_json(self) -> list[str]:
        result = [self.caller, self.callee, self.kind]
        if self.via:
            result.append(self.via)
        return result


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "纯Python分析UMQ C源码调用链，并展开designated initializer"
            "定义的函数指针调用。入口来自umq_api.h、umq_dfx_api.h和"
            "umq_pro_api.h。"
        )
    )
    parser.add_argument(
        "source",
        type=Path,
        help="UMQ的src源码目录，例如src/hcom/umq/src",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=OUTPUT_FILE,
        help=f"输出JSON路径，默认{OUTPUT_FILE}",
    )
    parser.add_argument(
        "--root",
        action="append",
        default=[],
        help="仅输出指定public API的可达调用图，可重复使用",
    )
    return parser.parse_args()


def resolve_source_root(path: Path) -> tuple[Path, Path]:
    candidate = path.expanduser().resolve()
    candidates = [
        candidate,
        candidate / "src",
        candidate / "src/hcom/umq/src",
    ]

    for source_root in candidates:
        umq_root = source_root.parent
        include_root = umq_root / "include/umq"
        if (
            (source_root / "umq_api.c").is_file()
            and all((include_root / header).is_file() for header in PUBLIC_HEADERS)
        ):
            return source_root, include_root

    raise ValueError(
        "无法定位UMQ源码和public header，需要传入src/hcom/umq/src目录："
        f"{candidate}"
    )


def strip_comments_strings_and_directives(text: str) -> str:
    pattern = re.compile(
        r'"(?:\\.|[^"\\])*"'
        r"|'(?:\\.|[^'\\])*'"
        r"|//[^\n]*"
        r"|/\*.*?\*/",
        re.DOTALL,
    )

    def blank(match: re.Match) -> str:
        value = match.group(0)
        return "".join("\n" if char == "\n" else " " for char in value)

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
        lines[index] = (" " * len(content)) + ("\n" if has_newline else "")
        in_directive = continued
    return "".join(lines)


def tokenize(text: str) -> list[Token]:
    sanitized = strip_comments_strings_and_directives(text)
    newline_offsets = [
        index
        for index, char in enumerate(sanitized)
        if char == "\n"
    ]
    return [
        Token(
            value=match.group(0),
            line=bisect.bisect_right(newline_offsets, match.start()) + 1,
        )
        for match in TOKEN_PATTERN.finditer(sanitized)
    ]


def build_pairs(tokens: list[Token]) -> dict[int, int]:
    pairs: dict[int, int] = {}
    stacks: dict[str, list[int]] = {
        "(": [],
        "[": [],
        "{": [],
    }
    closing_to_opening = {
        ")": "(",
        "]": "[",
        "}": "{",
    }

    for index, token in enumerate(tokens):
        if token.value in stacks:
            stacks[token.value].append(index)
            continue
        opening = closing_to_opening.get(token.value)
        if opening is None or not stacks[opening]:
            continue
        other = stacks[opening].pop()
        pairs[other] = index
        pairs[index] = other
    return pairs


def is_identifier(value: str) -> bool:
    return IDENTIFIER_PATTERN.match(value) is not None


def parse_functions(source: Path, tokens: list[Token], pairs: dict[int, int]) -> list[FunctionDef]:
    functions: list[FunctionDef] = []
    index = 0
    while index < len(tokens) - 2:
        name = tokens[index].value
        if not is_identifier(name) or name in IGNORED_CALL_NAMES:
            index += 1
            continue
        if tokens[index + 1].value != "(":
            index += 1
            continue
        if index > 0 and tokens[index - 1].value in {".", "->"}:
            index += 1
            continue

        close_paren = pairs.get(index + 1)
        if close_paren is None or close_paren + 1 >= len(tokens):
            index += 1
            continue
        body_open = close_paren + 1
        if tokens[body_open].value != "{":
            index += 1
            continue
        body_close = pairs.get(body_open)
        if body_close is None:
            index += 1
            continue

        functions.append(
            FunctionDef(
                name=name,
                source=source,
                line=tokens[index].line,
                body_open=body_open,
                body_close=body_close,
            )
        )
        index = body_close + 1
    return functions


def public_api_names(header: Path) -> list[str]:
    tokens = tokenize(header.read_text(encoding="utf-8", errors="replace"))
    pairs = build_pairs(tokens)
    names: list[str] = []
    seen: set[str] = set()

    for index in range(len(tokens) - 2):
        name = tokens[index].value
        if not name.startswith("umq_") or not is_identifier(name):
            continue
        if tokens[index + 1].value != "(":
            continue
        close_paren = pairs.get(index + 1)
        if close_paren is None or close_paren + 1 >= len(tokens):
            continue
        if tokens[close_paren + 1].value != ";":
            continue
        if name not in seen:
            seen.add(name)
            names.append(name)
    return names


def assign_function_ids(functions: list[FunctionDef], source_root: Path) -> None:
    by_name: dict[str, list[FunctionDef]] = defaultdict(list)
    for function in functions:
        by_name[function.name].append(function)

    for name, definitions in by_name.items():
        if len(definitions) == 1:
            definitions[0].function_id = name
            continue
        for function in definitions:
            relative = function.source.relative_to(source_root)
            function.function_id = f"{relative}:{function.line}:{name}"


def resolve_function_name(
    name: str,
    source: Path,
    definitions: dict[str, list[FunctionDef]],
) -> list[str]:
    candidates = definitions.get(name, [])
    same_source = [
        function.function_id
        for function in candidates
        if function.source == source
    ]
    if same_source:
        return same_source
    return [function.function_id for function in candidates]


def brace_depths(tokens: list[Token]) -> list[int]:
    depths: list[int] = []
    depth = 0
    for token in tokens:
        depths.append(depth)
        if token.value == "{":
            depth += 1
        elif token.value == "}":
            depth = max(0, depth - 1)
    return depths


def declaration_start(tokens: list[Token], equals_index: int, depths: list[int]) -> int:
    for index in range(equals_index - 1, -1, -1):
        if depths[index] == 0 and tokens[index].value in {";", "}"}:
            return index + 1
    return 0


def initializer_declaration(
    tokens: list[Token],
    equals_index: int,
    depths: list[int],
    pairs: dict[int, int],
) -> tuple[str, str]:
    start = declaration_start(tokens, equals_index, depths)
    segment = list(range(start, equals_index))
    if not segment:
        return "", ""

    variable_index = -1
    for index in segment:
        if tokens[index].value != "[":
            continue
        close = pairs.get(index)
        if close is not None and close < equals_index and index > start:
            variable_index = index - 1
            break
    if variable_index < 0:
        for index in reversed(segment):
            if is_identifier(tokens[index].value):
                variable_index = index
                break
    if variable_index < 0:
        return "", ""

    table_name = tokens[variable_index].value
    table_type = ""
    for index in range(variable_index - 1, start - 1, -1):
        value = tokens[index].value
        if is_identifier(value) and value not in DECLARATION_QUALIFIERS:
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

    for equals_index in range(len(tokens) - 1):
        if (
            tokens[equals_index].value != "="
            or depths[equals_index] != 0
            or tokens[equals_index + 1].value != "{"
        ):
            continue

        body_open = equals_index + 1
        body_close = pairs.get(body_open)
        if body_close is None:
            continue
        table_type, table_name = initializer_declaration(
            tokens,
            equals_index,
            depths,
            pairs,
        )

        index = body_open + 1
        while index + 3 < body_close:
            if (
                tokens[index].value != "."
                or not is_identifier(tokens[index + 1].value)
                or tokens[index + 2].value != "="
            ):
                index += 1
                continue

            field = tokens[index + 1].value
            target_index = index + 3
            if tokens[target_index].value == "&":
                target_index += 1
            if target_index >= body_close:
                break
            target_name = tokens[target_index].value
            target_ids = resolve_function_name(
                target_name,
                source,
                definitions,
            )
            for target_id in target_ids:
                bindings.append(
                    Binding(
                        field=field,
                        target_name=target_name,
                        target_id=target_id,
                        table_type=table_type,
                        table_name=table_name,
                        source=source,
                        line=tokens[index].line,
                    )
                )
            index = target_index + 1
    return bindings


def collect_edges(
    functions: list[FunctionDef],
    tokens_by_source: dict[Path, list[Token]],
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
        index = function.body_open + 1
        while index < function.body_close - 1:
            name = tokens[index].value
            if not is_identifier(name) or tokens[index + 1].value != "(":
                index += 1
                continue

            is_member_call = index > 0 and tokens[index - 1].value in {".", "->"}
            if is_member_call:
                candidates = bindings_by_field.get(name, [])
                if not candidates:
                    unresolved.add((function.function_id, name))
                for binding in candidates:
                    edges.add(
                        Edge(
                            caller=function.function_id,
                            callee=binding.target_id,
                            kind="function_pointer",
                            via=binding.slot,
                        )
                    )
                index += 1
                continue

            if name in definitions and name not in IGNORED_CALL_NAMES:
                for target_id in resolve_function_name(
                    name,
                    function.source,
                    definitions,
                ):
                    edges.add(
                        Edge(
                            caller=function.function_id,
                            callee=target_id,
                            kind="direct",
                        )
                    )
            index += 1
    return edges, unresolved


def reachable_graph(
    roots: list[str],
    definitions: dict[str, list[FunctionDef]],
    edges: set[Edge],
) -> tuple[set[str], set[Edge], list[str]]:
    root_ids: list[str] = []
    missing_roots: list[str] = []
    for root in roots:
        candidates = definitions.get(root, [])
        if not candidates:
            missing_roots.append(root)
            continue
        root_ids.extend(function.function_id for function in candidates)

    outgoing: dict[str, list[Edge]] = defaultdict(list)
    for edge in edges:
        outgoing[edge.caller].append(edge)

    reachable = set(root_ids)
    reachable_edges: set[Edge] = set()
    queue = deque(root_ids)
    while queue:
        caller = queue.popleft()
        for edge in outgoing.get(caller, []):
            reachable_edges.add(edge)
            if edge.callee in reachable:
                continue
            reachable.add(edge.callee)
            queue.append(edge.callee)
    return reachable, reachable_edges, missing_roots


def relative_location(function: FunctionDef, source_root: Path) -> str:
    relative = function.source.relative_to(source_root)
    return f"{relative}:{function.line}"


def build_output(
    source_root: Path,
    roots: list[str],
    functions: list[FunctionDef],
    reachable: set[str],
    edges: set[Edge],
    unresolved: set[tuple[str, str]],
    missing_roots: list[str],
) -> dict:
    by_id = {
        function.function_id: function
        for function in functions
    }
    reachable_unresolved = sorted(
        [caller, field]
        for caller, field in unresolved
        if caller in reachable
    )
    function_locations = {
        function_id: relative_location(by_id[function_id], source_root)
        for function_id in sorted(reachable)
    }
    edge_rows = [
        edge.as_json()
        for edge in sorted(
            edges,
            key=lambda item: (item.caller, item.callee, item.kind, item.via),
        )
    ]

    return {
        "schema_version": SCHEMA_VERSION,
        "source_root": str(source_root),
        "roots": roots,
        "analysis": {
            "complete": not missing_roots,
            "missing_roots": missing_roots,
            "function_count": len(function_locations),
            "edge_count": len(edge_rows),
            "unresolved_indirect_count": len(reachable_unresolved),
        },
        "functions": function_locations,
        "edges": edge_rows,
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
        source_root, include_root = resolve_source_root(args.source)
        public_roots: list[str] = []
        seen_roots: set[str] = set()
        for header_name in PUBLIC_HEADERS:
            for name in public_api_names(include_root / header_name):
                if name not in seen_roots:
                    seen_roots.add(name)
                    public_roots.append(name)

        roots = args.root or public_roots
        unknown_roots = sorted(set(roots) - seen_roots)
        if unknown_roots:
            raise ValueError(
                "--root必须是三个public header中声明的API："
                + ", ".join(unknown_roots)
            )

        sources = sorted(
            path
            for path in source_root.rglob("*")
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

        assign_function_ids(functions, source_root)
        definitions: dict[str, list[FunctionDef]] = defaultdict(list)
        for function in functions:
            definitions[function.name].append(function)

        bindings: list[Binding] = []
        for source in sources:
            bindings.extend(
                collect_bindings(
                    source,
                    tokens_by_source[source],
                    pairs_by_source[source],
                    definitions,
                )
            )

        all_edges, unresolved = collect_edges(
            functions,
            tokens_by_source,
            definitions,
            bindings,
        )
        reachable, edges, missing_roots = reachable_graph(
            roots,
            definitions,
            all_edges,
        )
        result = build_output(
            source_root,
            roots,
            functions,
            reachable,
            edges,
            unresolved,
            missing_roots,
        )
        write_json(result, args.output)
    except (OSError, ValueError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 2

    analysis = result["analysis"]
    print(
        f"调用链JSON已生成：{args.output.expanduser().resolve()}，"
        f"{len(roots)}个API，{analysis['function_count']}个函数，"
        f"{analysis['edge_count']}条边，"
        f"{analysis['unresolved_indirect_count']}个未解析间接调用",
        file=sys.stderr,
    )
    return 0 if analysis["complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
