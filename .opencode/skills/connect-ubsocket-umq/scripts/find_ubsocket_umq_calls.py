#!/usr/bin/env python3
"""Find physical UBSocket call sites that invoke UMQ public APIs."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, TextIO, Tuple


SOURCE_SUFFIXES = {".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx"}
OUTPUT_FILE = Path("/tmp/ubsocket_umq_calls.json")
CONTROL_NAMES = {
    "alignas",
    "alignof",
    "catch",
    "decltype",
    "delete",
    "for",
    "if",
    "new",
    "noexcept",
    "requires",
    "return",
    "sizeof",
    "static_assert",
    "switch",
    "throw",
    "while",
}
FUNCTION_NAME_RE = re.compile(
    r"(?P<name>(?:(?:[A-Za-z_]\w*|~[A-Za-z_]\w*)::)*(?:[A-Za-z_]\w*|~[A-Za-z_]\w*))\s*\("
)
CALL_RE = re.compile(
    r"(?<![A-Za-z0-9_])"
    r"(?P<qualified>(?:(?:::)?(?:[A-Za-z_]\w*::)+)?)"
    r"(?P<name>umq_[A-Za-z0-9_]+)\s*\("
)


@dataclass
class FunctionSpan:
    name: str
    start: int
    body_start: int
    end: int
    definition_name_start: int


@dataclass
class CallSite:
    parent: str
    child: str
    style: str
    path: str
    line: int
    column: int


@dataclass
class BraceEntry:
    function: Optional[FunctionSpan]
    scope_kind: Optional[str]
    scope_name: Optional[str]


def sanitize_cpp(text: str) -> str:
    """Replace comments and literals with spaces while preserving offsets and newlines."""
    result = list(text)
    size = len(text)
    index = 0

    def blank(start: int, end: int) -> None:
        for pos in range(start, min(end, size)):
            if result[pos] != "\n":
                result[pos] = " "

    while index < size:
        if text.startswith("//", index):
            end = text.find("\n", index + 2)
            if end < 0:
                end = size
            blank(index, end)
            index = end
            continue

        if text.startswith("/*", index):
            end = text.find("*/", index + 2)
            end = size if end < 0 else end + 2
            blank(index, end)
            index = end
            continue

        raw_match = re.match(r'(?:u8|u|U|L)?R"(?P<delimiter>[^ ()\\\t\r\n]{0,16})\(', text[index:])
        if raw_match:
            delimiter = raw_match.group("delimiter")
            terminator = ")" + delimiter + '"'
            end = text.find(terminator, index + raw_match.end())
            end = size if end < 0 else end + len(terminator)
            blank(index, end)
            index = end
            continue

        literal_match = re.match(r'(?:u8|u|U|L)?(?P<quote>["\'])', text[index:])
        if literal_match:
            quote = literal_match.group("quote")
            end = index + literal_match.end()
            while end < size:
                if text[end] == "\\":
                    end += 2
                    continue
                end += 1
                if text[end - 1] == quote:
                    break
            blank(index, end)
            index = end
            continue

        index += 1

    sanitized = "".join(result)
    result = list(sanitized)
    line_start = 0
    in_directive = False
    for line in sanitized.splitlines(keepends=True):
        content = line.rstrip("\r\n")
        is_directive = in_directive or content.lstrip().startswith("#")
        in_directive = is_directive and content.rstrip().endswith("\\")
        if is_directive:
            blank(line_start, line_start + len(content))
        line_start += len(line)
    return "".join(result)


def find_matching_paren(text: str, opening: int) -> Optional[int]:
    depth = 0
    for index in range(opening, len(text)):
        if text[index] == "(":
            depth += 1
        elif text[index] == ")":
            depth -= 1
            if depth == 0:
                return index
    return None


def extract_function_name(prefix: str, absolute_start: int) -> Optional[Tuple[str, int]]:
    if prefix.lstrip().startswith("#"):
        return None

    paren_depth = 0
    depth_at: Dict[int, int] = {}
    for index, char in enumerate(prefix):
        depth_at[index] = paren_depth
        if char == "(":
            paren_depth += 1
        elif char == ")" and paren_depth > 0:
            paren_depth -= 1

    for match in FUNCTION_NAME_RE.finditer(prefix):
        if depth_at.get(match.start("name"), 0) != 0:
            continue
        short_name = match.group("name").rsplit("::", 1)[-1].lstrip("~")
        if short_name in CONTROL_NAMES:
            continue
        closing = find_matching_paren(prefix, match.end() - 1)
        if closing is None:
            continue
        return match.group("name"), absolute_start + match.start("name")
    return None


def extract_named_scope(prefix: str) -> Tuple[Optional[str], Optional[str]]:
    namespace_match = re.search(r"\bnamespace\s+([A-Za-z_]\w*(?:::[A-Za-z_]\w*)*)\s*$", prefix)
    if namespace_match:
        return "namespace", namespace_match.group(1)

    type_match = re.search(
        r"\b(class|struct|union)\s+(?:[A-Za-z_]\w*\s+)*([A-Za-z_]\w*)"
        r"(?:\s+(?:final|sealed))?(?:\s*:[^{]+)?\s*$",
        prefix,
    )
    if type_match:
        return "class", type_match.group(2)
    return None, None


def parse_functions(clean_text: str) -> List[FunctionSpan]:
    functions: List[FunctionSpan] = []
    brace_stack: List[BraceEntry] = []
    last_boundary: Dict[int, int] = {0: 0}
    depth = 0

    for index, char in enumerate(clean_text):
        if char == ";":
            last_boundary[depth] = index + 1
            continue

        if char == "{":
            prefix_start = last_boundary.get(depth, 0)
            prefix = clean_text[prefix_start:index]
            function_info = extract_function_name(prefix, prefix_start)

            if function_info is not None:
                raw_name, name_start = function_info
                namespace_scopes = [
                    entry.scope_name
                    for entry in brace_stack
                    if entry.scope_kind == "namespace" and entry.scope_name is not None
                ]
                class_scopes = [
                    entry.scope_name
                    for entry in brace_stack
                    if entry.scope_kind == "class" and entry.scope_name is not None
                ]
                function_name = raw_name.lstrip(":")
                scope_prefix = list(namespace_scopes)
                if "::" not in function_name:
                    scope_prefix.extend(class_scopes)
                if scope_prefix:
                    function_name = "::".join(scope_prefix + [function_name])
                function = FunctionSpan(
                    name=function_name,
                    start=prefix_start,
                    body_start=index,
                    end=len(clean_text),
                    definition_name_start=name_start,
                )
                functions.append(function)
                entry = BraceEntry(function=function, scope_kind=None, scope_name=None)
            else:
                scope_kind, scope_name = extract_named_scope(prefix)
                entry = BraceEntry(function=None, scope_kind=scope_kind, scope_name=scope_name)

            brace_stack.append(entry)
            depth += 1
            last_boundary[depth] = index + 1
            continue

        if char == "}":
            if not brace_stack:
                continue
            entry = brace_stack.pop()
            if entry.function is not None:
                entry.function.end = index + 1
            last_boundary.pop(depth, None)
            depth -= 1
            last_boundary[depth] = index + 1

    return functions


def line_and_column(text: str, offset: int) -> Tuple[int, int]:
    line = text.count("\n", 0, offset) + 1
    line_start = text.rfind("\n", 0, offset)
    return line, offset - line_start


def extract_umq_api_names(header: Path) -> Set[str]:
    clean_text = sanitize_cpp(header.read_text(encoding="utf-8", errors="replace"))
    functions = parse_functions(clean_text)
    names = {
        function.name.rsplit("::", 1)[-1]
        for function in functions
        if "UmqApi::" in function.name and function.name.rsplit("::", 1)[-1].startswith("umq_")
    }
    if not names:
        raise RuntimeError("no UmqApi::umq_* methods found in {}".format(header))
    return names


def classify_style(qualified: str) -> str:
    if "UmqApi::" in qualified:
        return "UmqApi"
    if qualified:
        return "qualified"
    return "direct"


def find_parent(functions: Sequence[FunctionSpan], offset: int) -> str:
    candidates = [
        function
        for function in functions
        if function.body_start < offset < function.end
    ]
    if not candidates:
        return "<global>"
    return max(candidates, key=lambda function: function.body_start).name


def scan_file(path: Path, display_path: str, api_names: Set[str]) -> List[CallSite]:
    text = path.read_text(encoding="utf-8", errors="replace")
    clean_text = sanitize_cpp(text)
    functions = parse_functions(clean_text)
    definition_offsets = {function.definition_name_start for function in functions}
    calls: List[CallSite] = []

    for match in CALL_RE.finditer(clean_text):
        child = match.group("name")
        if child not in api_names or match.start("name") in definition_offsets:
            continue
        line, column = line_and_column(clean_text, match.start("name"))
        qualified = match.group("qualified") or ""
        calls.append(
            CallSite(
                parent=find_parent(functions, match.start("name")),
                child=child,
                style=classify_style(qualified),
                path=display_path,
                line=line,
                column=column,
            )
        )
    return calls


def source_files(source_dir: Path) -> Iterable[Path]:
    for path in sorted(source_dir.rglob("*")):
        if any(part in {"build", ".git", "output", "3rdparty"} for part in path.parts):
            continue
        if path.is_file() and path.suffix.lower() in SOURCE_SUFFIXES:
            yield path


def write_json(
    calls: Sequence[CallSite],
    api_names: Set[str],
    ubsocket_root: Path,
    umq_root: Path,
    output: TextIO,
) -> None:
    style_counts = Counter(call.style for call in calls)
    payload = {
        "ubsocket_path": str(ubsocket_root),
        "umq_path": str(umq_root),
        "summary": {
            "api_count": len(api_names),
            "call_count": len(calls),
            "umq_api_call_count": style_counts.get("UmqApi", 0),
            "direct_call_count": style_counts.get("direct", 0),
            "qualified_call_count": style_counts.get("qualified", 0),
        },
        "calls": [
            {
                "parent": call.parent.rsplit("::", 1)[-1],
                "parent_qualified": call.parent,
                "child": call.child,
                "file": call.path,
                "line": call.line,
                "column": call.column,
                "style": call.style,
            }
            for call in calls
        ],
    }
    json.dump(payload, output, ensure_ascii=False, indent=2)
    output.write("\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Extract UmqApi::umq_* method names from dl_umq_api.h and find calls "
            "with the same literal names in UBSocket sources. Write physical call "
            "sites to /tmp/ubsocket_umq_calls.json."
        )
    )
    parser.add_argument(
        "ubsocket_path",
        help="UBSocket component path, csrc path, or repository root",
    )
    parser.add_argument(
        "umq_path",
        help="UMQ component path, source path, or repository root",
    )
    return parser.parse_args()


def resolve_ubsocket_layout(value: str) -> Tuple[Path, Path, Path]:
    path = Path(value).expanduser().resolve()
    candidates = [
        (path, path / "csrc"),
        (path.parent, path) if path.name == "csrc" else (path, path / "csrc"),
        (path / "src" / "ubsocket", path / "src" / "ubsocket" / "csrc"),
    ]
    for root, source_dir in candidates:
        header = source_dir / "under_api" / "dl_umq_api.h"
        if source_dir.is_dir() and header.is_file():
            return root, source_dir, header
    raise RuntimeError(
        "cannot find csrc/under_api/dl_umq_api.h under UBSocket path: {}".format(path)
    )


def resolve_umq_layout(value: str) -> Tuple[Path, Path]:
    path = Path(value).expanduser().resolve()
    candidates = [
        path,
        path / "src" / "hcom" / "umq",
    ]
    for root in candidates:
        if not root.is_dir():
            continue
        source_dir = root / "src"
        if source_dir.is_dir():
            return root, source_dir
        if root.name == "src" and any(source_files(root)):
            return root, root
    raise RuntimeError("cannot find UMQ source directory under: {}".format(path))


def main() -> int:
    args = parse_args()
    try:
        ubsocket_root, source_dir, header = resolve_ubsocket_layout(args.ubsocket_path)
        umq_root, _ = resolve_umq_layout(args.umq_path)
    except RuntimeError as error:
        print("error: {}".format(error), file=sys.stderr)
        return 2

    try:
        api_names = extract_umq_api_names(header)
    except RuntimeError as error:
        print("error: {}".format(error), file=sys.stderr)
        return 2

    calls: List[CallSite] = []
    for path in source_files(source_dir):
        if path.resolve() == header:
            continue
        try:
            display_path = str(path.relative_to(ubsocket_root))
        except ValueError:
            display_path = str(path)
        calls.extend(scan_file(path, display_path, api_names))
    calls.sort(key=lambda call: (call.path, call.line, call.column, call.parent, call.child))

    temporary_output = OUTPUT_FILE.with_suffix(OUTPUT_FILE.suffix + ".tmp")
    with temporary_output.open("w", encoding="utf-8", newline="") as output:
        write_json(calls, api_names, ubsocket_root, umq_root, output)
    temporary_output.replace(OUTPUT_FILE)
    print("UBSocket-to-UMQ call sites written to {}".format(OUTPUT_FILE))
    return 0


if __name__ == "__main__":
    sys.exit(main())
