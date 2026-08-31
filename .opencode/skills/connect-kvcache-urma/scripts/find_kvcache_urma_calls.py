#!/usr/bin/env python3
"""Map KVCache ds_urma_* calls exclusively to urma_NNN interface nodes."""

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
OUTPUT_FILE = Path("/tmp/kvcache_urma_calls.json")
TARGET_COMPONENT = "urma"
URMA_API_HEADER = Path("core/include/urma_api.h")
SHIM_HEADER = Path("common/rdma/urma_dlopen_util.h")
SKIPPED_DIRECTORY_NAMES = {".git", "3rdparty", "build", "output"}
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
URMA_DECLARATION_RE = re.compile(r"\b(?P<name>urma_[A-Za-z0-9_]+)\s*\([^;{}]*\)\s*;")
SHIM_DECLARATION_RE = re.compile(r"\b(?P<name>ds_urma_[A-Za-z0-9_]+)\s*\([^;{}]*\)\s*;")
SHIM_CALL_RE = re.compile(
    r"(?<![A-Za-z0-9_])"
    r"(?P<qualified>(?:(?:::)?(?:[A-Za-z_]\w*::)+)?)"
    r"(?P<name>ds_urma_[A-Za-z0-9_]+)\s*\("
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
    shim: str
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
    """Replace comments, literals, and directives with spaces, preserving offsets."""
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
        if find_matching_paren(prefix, match.end() - 1) is None:
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
                function = FunctionSpan(function_name, index, len(clean_text), name_start)
                functions.append(function)
                entry = BraceEntry(function, None, None)
            else:
                scope_kind, scope_name = extract_named_scope(prefix)
                entry = BraceEntry(None, scope_kind, scope_name)

            brace_stack.append(entry)
            depth += 1
            last_boundary[depth] = index + 1
            continue

        if char == "}" and brace_stack:
            entry = brace_stack.pop()
            if entry.function is not None:
                entry.function.end = index + 1
            last_boundary.pop(depth, None)
            depth -= 1
            last_boundary[depth] = index + 1

    return functions


def declaration_names(header: Path, pattern: re.Pattern[str]) -> List[str]:
    clean_text = sanitize_cpp(header.read_text(encoding="utf-8", errors="replace"))
    names: List[str] = []
    seen: Set[str] = set()
    for match in pattern.finditer(clean_text):
        name = match.group("name")
        if name not in seen:
            names.append(name)
            seen.add(name)
    return names


def source_files(root: Path) -> Iterable[Path]:
    for path in sorted(root.rglob("*")):
        if any(part in SKIPPED_DIRECTORY_NAMES for part in path.parts):
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


def classify_style(qualified: str) -> str:
    return "qualified_ds_urma_shim" if qualified else "ds_urma_shim"


def scan_file(path: Path, display_path: str) -> List[CallSite]:
    text = path.read_text(encoding="utf-8", errors="replace")
    clean_text = sanitize_cpp(text)
    functions = parse_functions(clean_text)
    definition_offsets = {function.definition_name_start for function in functions}
    calls: List[CallSite] = []
    for match in SHIM_CALL_RE.finditer(clean_text):
        if match.start("name") in definition_offsets:
            continue
        parent = find_parent(functions, match.start("name"))
        if parent is None:
            continue
        shim = match.group("name")
        line, column = line_and_column(clean_text, match.start("name"))
        calls.append(
            CallSite(
                parent=parent,
                shim=shim,
                child=shim.removeprefix("ds_"),
                style=classify_style(match.group("qualified") or ""),
                path=display_path,
                line=line,
                column=column,
            )
        )
    return calls


def resolve_kvcache_source(value: str) -> Tuple[Path, Path]:
    path = Path(value).expanduser().resolve()
    candidates = [path, path / "src" / "datasystem"]
    for candidate in candidates:
        header = candidate / SHIM_HEADER
        if candidate.is_dir() and header.is_file():
            return candidate, header
    raise RuntimeError("cannot find {} under KVCache path: {}".format(SHIM_HEADER, path))


def resolve_urma_source(value: str) -> Path:
    path = Path(value).expanduser().resolve()
    candidates = [path, path / "src" / "urma" / "lib" / "urma"]
    for candidate in candidates:
        if (candidate / URMA_API_HEADER).is_file():
            return candidate
    raise RuntimeError("cannot find {} under URMA path: {}".format(URMA_API_HEADER, path))


def call_json(call: CallSite, root_ids: Dict[str, str]) -> Dict[str, object]:
    result: Dict[str, object] = {
        "parent": call.parent.rsplit("::", 1)[-1],
        "parent_qualified": call.parent,
        "child": call.child,
        "shim": call.shim,
        "file": call.path,
        "line": call.line,
        "column": call.column,
        "style": call.style,
    }
    if call.child in root_ids:
        result["target_component"] = TARGET_COMPONENT
        result["target_root_id"] = root_ids[call.child]
    return result


def write_json(
    calls: Sequence[CallSite],
    excluded: Sequence[CallSite],
    roots: Sequence[str],
    declared_shims: Sequence[str],
    kvcache_source: Path,
    urma_source: Path,
    shim_header: Path,
    output: TextIO,
) -> None:
    root_ids = {
        name: "{}_{:03d}".format(TARGET_COMPONENT, index + 1)
        for index, name in enumerate(roots)
    }
    declared_shim_set = set(declared_shims)
    mapped_shims = [name for name in declared_shims if name.removeprefix("ds_") in root_ids]
    called = {call.child for call in calls}
    uncalled = [name for name in roots if name not in called]
    style_counts = Counter(call.style for call in calls)
    payload = {
        "kvcache_path": str(kvcache_source),
        "urma_path": str(urma_source),
        "shim_header": str(shim_header),
        "target_component": TARGET_COMPONENT,
        "summary": {
            "public_api_count": len(roots),
            "declared_shim_count": len(declared_shims),
            "mapped_public_shim_count": len(mapped_shims),
            "called_public_api_count": len(called),
            "uncalled_public_api_count": len(uncalled),
            "call_count": len(calls),
            "ds_urma_shim_call_count": style_counts.get("ds_urma_shim", 0),
            "qualified_ds_urma_shim_call_count": style_counts.get("qualified_ds_urma_shim", 0),
            "excluded_non_root_call_count": len(excluded),
        },
        "shim_apis": [
            {
                "shim": shim,
                "api": shim.removeprefix("ds_"),
                "target_root_id": root_ids[shim.removeprefix("ds_")],
                "called": shim.removeprefix("ds_") in called,
            }
            for shim in mapped_shims
        ],
        "called_root_ids": [root_ids[name] for name in roots if name in called],
        "uncalled_roots": [
            {"api": name, "root_id": root_ids[name]}
            for name in uncalled
        ],
        "calls": [call_json(call, root_ids) for call in calls],
        "excluded_non_root_calls": [
            {
                **call_json(call, root_ids),
                "reason": (
                    "shim_not_declared_in_urma_dlopen_util.h"
                    if call.shim not in declared_shim_set
                    else "target_not_declared_in_urma_api.h"
                ),
            }
            for call in excluded
        ],
    }
    json.dump(payload, output, ensure_ascii=False, indent=2)
    output.write("\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Find physical KVCache ds_urma_* calls and map them exclusively to "
            "urma_NNN interface nodes."
        )
    )
    parser.add_argument("kvcache_path", help="DataSystem src/datasystem or repository path")
    parser.add_argument("urma_path", help="URMA lib/urma or repository path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        kvcache_source, shim_header = resolve_kvcache_source(args.kvcache_path)
        urma_source = resolve_urma_source(args.urma_path)
        roots = declaration_names(urma_source / URMA_API_HEADER, URMA_DECLARATION_RE)
        declared_shims = declaration_names(shim_header, SHIM_DECLARATION_RE)
        if not roots:
            raise RuntimeError("no URMA public APIs found in {}".format(urma_source / URMA_API_HEADER))
        if not declared_shims:
            raise RuntimeError("no ds_urma_* shims found in {}".format(shim_header))
    except (OSError, RuntimeError) as error:
        print("error: {}".format(error), file=sys.stderr)
        return 2

    public_names = set(roots)
    declared_shim_set = set(declared_shims)
    calls: List[CallSite] = []
    excluded: List[CallSite] = []
    for path in source_files(kvcache_source):
        display_path = str(path.relative_to(kvcache_source))
        for call in scan_file(path, display_path):
            if call.shim in declared_shim_set and call.child in public_names:
                calls.append(call)
            else:
                excluded.append(call)

    sort_key = lambda call: (call.path, call.line, call.column, call.parent, call.child)
    calls.sort(key=sort_key)
    excluded.sort(key=sort_key)

    temporary_output = OUTPUT_FILE.with_suffix(OUTPUT_FILE.suffix + ".tmp")
    try:
        with temporary_output.open("w", encoding="utf-8", newline="") as output:
            write_json(
                calls,
                excluded,
                roots,
                declared_shims,
                kvcache_source,
                urma_source,
                shim_header,
                output,
            )
        temporary_output.replace(OUTPUT_FILE)
    except OSError as error:
        print("error: cannot write {}: {}".format(OUTPUT_FILE, error), file=sys.stderr)
        return 2

    print("KVCache-to-URMA call sites written to {}".format(OUTPUT_FILE))
    return 0


if __name__ == "__main__":
    sys.exit(main())
