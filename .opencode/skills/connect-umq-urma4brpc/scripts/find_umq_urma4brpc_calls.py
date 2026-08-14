#!/usr/bin/env python3
"""Find physical UMQ call sites that invoke URMA4BRPC public APIs."""

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
OUTPUT_FILE = Path("/tmp/umq_urma4brpc_calls.json")
URMA_API_HEADER = Path("core/include/urma_api.h")
URMA_TYPES_HEADER = Path("core/include/urma_types.h")
TYPES_PUBLIC_APIS = {"urma_u32_to_eid", "urma_str_to_eid"}
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
    "return",
    "sizeof",
    "static_assert",
    "switch",
    "throw",
    "while",
}
FUNCTION_NAME_RE = re.compile(r"(?P<name>[A-Za-z_]\w*)\s*\(")
DECLARATION_RE = re.compile(r"\b(?P<name>urma_[A-Za-z0-9_]+)\s*\([^;{}]*\)\s*;")
CALL_RE = re.compile(r"(?<![A-Za-z0-9_])(?P<name>urma_[A-Za-z0-9_]+)\s*\(")
LOAD_SYMBOL_RE = re.compile(
    r"\bLOAD_SYMBOL\s*\(\s*[^,]+,\s*[^,]+,\s*[^,]+,\s*(?P<name>urma_[A-Za-z0-9_]+)\s*\)"
)


@dataclass
class FunctionSpan:
    name: str
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


def sanitize_source(text: str) -> str:
    """Blank comments, literals, and directives while preserving offsets."""
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
            end = size if end < 0 else end
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
            terminator = ")" + raw_match.group("delimiter") + '"'
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
    paren_depth = 0
    depth_at: Dict[int, int] = {}
    for index, char in enumerate(prefix):
        depth_at[index] = paren_depth
        if char == "(":
            paren_depth += 1
        elif char == ")" and paren_depth > 0:
            paren_depth -= 1

    for match in FUNCTION_NAME_RE.finditer(prefix):
        name = match.group("name")
        if depth_at.get(match.start("name"), 0) != 0 or name in CONTROL_NAMES:
            continue
        if find_matching_paren(prefix, match.end() - 1) is None:
            continue
        return name, absolute_start + match.start("name")
    return None


def parse_functions(clean_text: str) -> List[FunctionSpan]:
    functions: List[FunctionSpan] = []
    brace_stack: List[Optional[FunctionSpan]] = []
    last_boundary: Dict[int, int] = {0: 0}
    depth = 0
    for index, char in enumerate(clean_text):
        if char == ";":
            last_boundary[depth] = index + 1
        elif char == "{":
            prefix_start = last_boundary.get(depth, 0)
            info = extract_function_name(clean_text[prefix_start:index], prefix_start)
            function = None
            if info is not None:
                function = FunctionSpan(info[0], index, len(clean_text), info[1])
                functions.append(function)
            brace_stack.append(function)
            depth += 1
            last_boundary[depth] = index + 1
        elif char == "}" and brace_stack:
            function = brace_stack.pop()
            if function is not None:
                function.end = index + 1
            last_boundary.pop(depth, None)
            depth -= 1
            last_boundary[depth] = index + 1
    return functions


def public_api_names(header: Path, allowlist: Optional[Set[str]] = None) -> List[str]:
    clean_text = sanitize_source(header.read_text(encoding="utf-8", errors="replace"))
    names: List[str] = []
    seen: Set[str] = set()
    for match in DECLARATION_RE.finditer(clean_text):
        name = match.group("name")
        if allowlist is not None and name not in allowlist:
            continue
        if name not in seen:
            names.append(name)
            seen.add(name)
    return names


def source_files(root: Path) -> Iterable[Path]:
    for path in sorted(root.rglob("*")):
        if any(part in {"build", ".git", "output", "3rdparty"} for part in path.parts):
            continue
        if path.is_file() and path.suffix.lower() in SOURCE_SUFFIXES:
            yield path


def line_and_column(text: str, offset: int) -> Tuple[int, int]:
    line = text.count("\n", 0, offset) + 1
    line_start = text.rfind("\n", 0, offset)
    return line, offset - line_start


def find_parent(functions: Sequence[FunctionSpan], offset: int) -> Optional[str]:
    candidates = [function for function in functions if function.body_start < offset < function.end]
    if not candidates:
        return None
    return max(candidates, key=lambda function: function.body_start).name


def classify_style(clean_text: str, name_start: int) -> str:
    prefix = clean_text[max(0, name_start - 160):name_start]
    if re.search(r"umq_symbol_urma\s*\(\s*\)\s*->\s*$", prefix):
        return "umq_symbol_urma"
    if re.search(r"(?:->|\.)\s*$", prefix):
        return "function_pointer"
    return "direct"


def scan_file(path: Path, display_path: str, public_names: Set[str]) -> Tuple[List[CallSite], List[CallSite]]:
    text = path.read_text(encoding="utf-8", errors="replace")
    clean_text = sanitize_source(text)
    functions = parse_functions(clean_text)
    definition_offsets = {function.definition_name_start for function in functions}
    included: List[CallSite] = []
    excluded: List[CallSite] = []
    for match in CALL_RE.finditer(clean_text):
        if match.start("name") in definition_offsets:
            continue
        parent = find_parent(functions, match.start("name"))
        if parent is None:
            continue
        line, column = line_and_column(clean_text, match.start("name"))
        call = CallSite(
            parent=parent,
            child=match.group("name"),
            style=classify_style(clean_text, match.start("name")),
            path=display_path,
            line=line,
            column=column,
        )
        (included if call.child in public_names else excluded).append(call)
    return included, excluded


def resolve_umq_source(value: str) -> Path:
    path = Path(value).expanduser().resolve()
    candidates = [path, path / "src", path / "src" / "hcom" / "umq" / "src"]
    marker = Path("umq_ub/core/private/umq_symbol_private.h")
    for candidate in candidates:
        if (candidate / marker).is_file():
            return candidate
    raise RuntimeError("cannot find UMQ source marker {} under {}".format(marker, path))


def resolve_urma_source(value: str) -> Path:
    path = Path(value).expanduser().resolve()
    candidates = [path, path / "src" / "urma" / "lib" / "urma"]
    for candidate in candidates:
        if (candidate / URMA_API_HEADER).is_file() and (candidate / URMA_TYPES_HEADER).is_file():
            return candidate
    raise RuntimeError("cannot find URMA public headers under {}".format(path))


def loaded_symbol_names(umq_source: Path) -> Set[str]:
    loader = umq_source / "umq_ub/core/private/umq_symbol_private.c"
    clean_text = sanitize_source(loader.read_text(encoding="utf-8", errors="replace"))
    return {match.group("name") for match in LOAD_SYMBOL_RE.finditer(clean_text)}


def call_json(call: CallSite, root_ids: Dict[str, str]) -> Dict[str, object]:
    result: Dict[str, object] = {
        "parent": call.parent,
        "parent_qualified": call.parent,
        "child": call.child,
        "file": call.path,
        "line": call.line,
        "column": call.column,
        "style": call.style,
    }
    if call.child in root_ids:
        result["target_root_id"] = root_ids[call.child]
    return result


def write_json(
    calls: Sequence[CallSite],
    excluded: Sequence[CallSite],
    roots: Sequence[str],
    loaded: Set[str],
    umq_source: Path,
    urma_source: Path,
    output: TextIO,
) -> None:
    root_ids = {name: "urma4brpc_{:03d}".format(index + 1) for index, name in enumerate(roots)}
    called = {call.child for call in calls}
    uncalled = [name for name in roots if name not in called]
    style_counts = Counter(call.style for call in calls)
    payload = {
        "umq_path": str(umq_source),
        "urma_path": str(urma_source),
        "summary": {
            "public_api_count": len(roots),
            "loaded_public_api_count": len(loaded.intersection(roots)),
            "called_public_api_count": len(called),
            "uncalled_public_api_count": len(uncalled),
            "call_count": len(calls),
            "umq_symbol_urma_call_count": style_counts.get("umq_symbol_urma", 0),
            "function_pointer_call_count": style_counts.get("function_pointer", 0),
            "direct_call_count": style_counts.get("direct", 0),
            "excluded_non_root_call_count": len(excluded),
        },
        "public_roots": [
            {"api": name, "root_id": root_ids[name], "called": name in called}
            for name in roots
        ],
        "called_root_ids": [root_ids[name] for name in roots if name in called],
        "uncalled_roots": [
            {"api": name, "root_id": root_ids[name]}
            for name in uncalled
        ],
        "loaded_public_but_uncalled": [name for name in roots if name in loaded and name not in called],
        "called_without_loaded_symbol": [name for name in roots if name in called and name not in loaded],
        "calls": [call_json(call, root_ids) for call in calls],
        "excluded_non_root_calls": [call_json(call, root_ids) for call in excluded],
    }
    json.dump(payload, output, ensure_ascii=False, indent=2)
    output.write("\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Find physical UMQ calls to URMA4BRPC public APIs."
    )
    parser.add_argument("umq_path", help="UMQ source, component, or repository path")
    parser.add_argument("urma_path", help="URMA lib/urma or repository path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        umq_source = resolve_umq_source(args.umq_path)
        urma_source = resolve_urma_source(args.urma_path)
        roots = public_api_names(urma_source / URMA_API_HEADER)
        roots.extend(public_api_names(urma_source / URMA_TYPES_HEADER, TYPES_PUBLIC_APIS))
        roots = list(dict.fromkeys(roots))
        if not roots:
            raise RuntimeError("no URMA public APIs found")
        loaded = loaded_symbol_names(umq_source)
    except RuntimeError as error:
        print("error: {}".format(error), file=sys.stderr)
        return 2

    calls: List[CallSite] = []
    excluded: List[CallSite] = []
    public_names = set(roots)
    for path in source_files(umq_source):
        display_path = str(path.relative_to(umq_source))
        file_calls, file_excluded = scan_file(path, display_path, public_names)
        calls.extend(file_calls)
        excluded.extend(file_excluded)
    sort_key = lambda call: (call.path, call.line, call.column, call.parent, call.child)
    calls.sort(key=sort_key)
    excluded.sort(key=sort_key)

    temporary_output = OUTPUT_FILE.with_suffix(OUTPUT_FILE.suffix + ".tmp")
    with temporary_output.open("w", encoding="utf-8", newline="") as output:
        write_json(calls, excluded, roots, loaded, umq_source, urma_source, output)
    temporary_output.replace(OUTPUT_FILE)
    print("UMQ-to-URMA4BRPC call sites written to {}".format(OUTPUT_FILE))
    return 0


if __name__ == "__main__":
    sys.exit(main())
