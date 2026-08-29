#!/usr/bin/env python3

"""Extract AccessRecorder entry candidates for access-log failure mode roots.

This script scans the datasystem source for:
  1. ``AccessRecorderKey`` definitions in ``access_point.def``;
  2. ``AccessRecorder`` construction sites (``AccessRecorder::Object/Stream/RequestOut(KEY)`` plus
     direct construction ``ObjectAccessRecorder var(KEY)`` etc.);
  3. ``recorder.Result(...)`` call sites — both explicit ``StatusCode::K_*`` and runtime Status variables.

Output is a candidate map only. It does NOT perform call-chain traversal from runtime ERROR sites;
that work belongs to the follow-up skill analysis stage. The script just provides anchors:
which API path (by AccessRecorderKey) can produce which K_* status code in the access log.
"""

from __future__ import annotations

import argparse
import json
import re
import signal
import sys
from bisect import bisect_right
from dataclasses import dataclass, field
from pathlib import Path


OUTPUT_FILE = Path("/tmp/kvcache_access_err.json")
SCHEMA_VERSION = 1

SOURCE_SUFFIXES = {".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp"}

# Factory entry points in access_recorder.h that wrap AccessRecorderKey into a typed recorder.
FACTORY_PATTERNS = {
    "AccessRecorder::Object": "OBJECT",
    "AccessRecorder::Stream": "STREAM",
    "AccessRecorder::RequestOut": "REQUEST_OUT",
}

# Direct construction class names (per access_recorder.h).
DIRECT_CONSTRUCTORS = {
    "ObjectAccessRecorder": "OBJECT",
    "StreamAccessRecorder": "STREAM",
    "RequestOutRecorder": "REQUEST_OUT",
}

# Regex patterns. Pre-compiled for performance.
# Match: AccessRecorder::Object( <expr> )  where <expr> may be AccessRecorderKey::DS_XXX or helper().
FACTORY_CALL_RE = re.compile(
    r"\bAccessRecorder\s*::\s*(Object|Stream|RequestOut)\s*\(",
)

# Match: AccessRecorderKey::DS_XXX
ACCESS_KEY_RE = re.compile(r"\bAccessRecorderKey\s*::\s*(DS_\w+)\b")

# Match: ObjectAccessRecorder <name>( <expr> ) — direct construction.
DIRECT_CTOR_RE = re.compile(
    r"\b(ObjectAccessRecorder|StreamAccessRecorder|RequestOutRecorder)\s+"
    r"(?:[A-Za-z_]\w*\s*=\s*)?([A-Za-z_]\w*)\s*\(",
)

# Match: .Result(  — call site on a recorder variable.
RESULT_CALL_RE = re.compile(r"\.Result\s*\(")

# Match: StatusCode::K_XXX inside Result() arguments.
STATUSCODE_RE = re.compile(r"\bStatusCode\s*::\s*(K_\w+)\b")

# Skip these directories during traversal.
SKIP_DIR_NAMES = {"build", ".git", "__pycache__", "third_party", ".third_party_cache"}


@dataclass
class ConstructionSite:
    file: str
    line: int
    function: str
    key_name: str | None  # DS_XXX if literal; None if dynamic (e.g. GetEtcdReqRecorderKey(methodName))
    key_type: str  # OBJECT / STREAM / REQUEST_OUT
    raw_argument: str  # original argument text for debugging


@dataclass
class ResultSite:
    file: str
    line: int
    function: str
    explicit_code: str | None  # K_XXX if StatusCode::K_XXX literal; None if passing a Status variable
    explicit_resp_msg: str | None  # string literal if present, None otherwise
    raw_argument: str
    matched_access_key: str | None = None  # nearest AccessRecorderKey in scope, filled in pass 2


@dataclass
class AccessPointInfo:
    key_name: str
    key_type: str  # CLIENT / ACCESS / REQUEST_OUT (from access_point.def)
    construction_sites: list[ConstructionSite] = field(default_factory=list)
    result_sites: list[ResultSite] = field(default_factory=list)


def parse_access_point_def(def_path: Path) -> list[tuple[str, str]]:
    """Parse access_point.def and return list of (key_name, key_type)."""
    pattern = re.compile(
        r"ACCESS_RECORDER_KEY_DEF\s*\(\s*(DS_\w+)\s*,\s*(CLIENT|ACCESS|REQUEST_OUT)\s*\)"
    )
    entries: list[tuple[str, str]] = []
    with def_path.open("r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if not stripped or stripped.startswith("//"):
                continue
            m = pattern.search(stripped)
            if m:
                entries.append((m.group(1), m.group(2)))
    return entries


def build_line_starts(source: str) -> list[int]:
    starts = [0]
    starts.extend(pos + 1 for pos, char in enumerate(source) if char == "\n")
    return starts


def line_number(line_starts: list[int], pos: int) -> int:
    return bisect_right(line_starts, pos)


def is_cpp_digit_separator(source: str, pos: int) -> bool:
    if source[pos:pos + 1] != "'" or pos == 0 or pos + 1 >= len(source):
        return False
    return source[pos - 1].isalnum() and source[pos + 1].isalnum()


def skip_whitespace_and_comments(source: str, pos: int) -> int:
    while pos < len(source):
        if source[pos].isspace():
            pos += 1
        elif source.startswith("//", pos):
            newline = source.find("\n", pos + 2)
            return len(source) if newline == -1 else skip_whitespace_and_comments(source, newline + 1)
        elif source.startswith("/*", pos):
            end = source.find("*/", pos + 2)
            return len(source) if end == -1 else skip_whitespace_and_comments(source, end + 2)
        else:
            break
    return pos


def find_call_end(source: str, open_paren: int) -> int | None:
    """Return position just after the matching close paren for the call starting at open_paren."""
    depth = 0
    pos = open_paren
    state = "normal"
    while pos < len(source):
        char = source[pos]
        next_char = source[pos + 1] if pos + 1 < len(source) else ""
        if state == "normal":
            if char == '"':
                state = "string"
            elif char == "'" and not is_cpp_digit_separator(source, pos):
                state = "char"
            elif char == "/" and next_char == "/":
                state = "line_comment"
                pos += 1
            elif char == "/" and next_char == "*":
                state = "block_comment"
                pos += 1
            elif char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth == 0:
                    return pos + 1
        elif state == "string":
            if char == "\\":
                pos += 1
            elif char == '"':
                state = "normal"
        elif state == "char":
            if char == "\\":
                pos += 1
            elif char == "'":
                state = "normal"
        elif state == "line_comment":
            if char == "\n":
                state = "normal"
        elif state == "block_comment" and char == "*" and next_char == "/":
            state = "normal"
            pos += 1
        pos += 1
    return None


def split_top_level_arguments(source: str, open_paren: int, close_paren_end: int) -> list[str]:
    """Return list of top-level argument text. open_paren points at '(', close_paren_end is one past ')'."""
    args: list[str] = []
    depth = 0
    pos = open_paren + 1
    end = close_paren_end - 1  # position of ')'
    state = "normal"
    arg_start = pos
    while pos < end:
        char = source[pos]
        next_char = source[pos + 1] if pos + 1 < len(source) else ""
        if state == "normal":
            if char == '"':
                state = "string"
            elif char == "'" and not is_cpp_digit_separator(source, pos):
                state = "char"
            elif char == "/" and next_char == "/":
                state = "line_comment"
                pos += 1
            elif char == "/" and next_char == "*":
                state = "block_comment"
                pos += 1
            elif char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
            elif char == "," and depth == 0:
                args.append(source[arg_start:pos].strip())
                arg_start = pos + 1
        elif state == "string":
            if char == "\\":
                pos += 1
            elif char == '"':
                state = "normal"
        elif state == "char":
            if char == "\\":
                pos += 1
            elif char == "'":
                state = "normal"
        elif state == "line_comment":
            if char == "\n":
                state = "normal"
        elif state == "block_comment" and char == "*" and next_char == "/":
            state = "normal"
            pos += 1
        pos += 1
    last = source[arg_start:end].strip()
    if last:
        args.append(last)
    return args


@dataclass
class FunctionRange:
    name: str
    start: int  # absolute source position
    end: int  # absolute source position (one past end)
    start_line: int


def find_functions(source: str, line_starts: list[int]) -> list[FunctionRange]:
    """Naive function detection: scan for `name(...) {` patterns. Sufficient for this script's purpose."""
    functions: list[FunctionRange] = []
    # Match: identifier (optional space) ( ... ) (optional space/qualifiers) {
    # This is a permissive pattern; we then walk forward to find the matching close brace.
    pattern = re.compile(
        r"\b([A-Za-z_][A-Za-z0-9_:~]*)\s*\("
    )
    for match in pattern.finditer(source):
        open_paren = match.end() - 1
        close_end = find_call_end(source, open_paren)
        if close_end is None:
            continue
        # Skip whitespace and comments between ) and {
        brace_pos = skip_whitespace_and_comments(source, close_end)
        if brace_pos >= len(source) or source[brace_pos] != "{":
            continue
        # Skip control-flow keywords (if/for/while/switch/catch) — they also match `name(...)` pattern.
        name = match.group(1)
        if name in {"if", "for", "while", "switch", "catch", "return", "sizeof", "new", "delete",
                    "static_assert", "noexcept", "decltype", "typeid", "and", "or", "not"}:
            continue
        # Find matching close brace
        open_brace = brace_pos
        depth = 0
        pos = open_brace
        while pos < len(source):
            char = source[pos]
            next_char = source[pos + 1] if pos + 1 < len(source) else ""
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    functions.append(FunctionRange(
                        name=name,
                        start=open_brace,
                        end=pos + 1,
                        start_line=line_number(line_starts, open_brace),
                    ))
                    break
            elif char == "/" and next_char == "/":
                # skip to end of line
                nl = source.find("\n", pos + 2)
                if nl == -1:
                    break
                pos = nl
                continue
            elif char == "/" and next_char == "*":
                end = source.find("*/", pos + 2)
                if end == -1:
                    break
                pos = end + 2
                continue
            elif char == '"':
                # skip string literal
                pos += 1
                while pos < len(source) and source[pos] != '"':
                    if source[pos] == "\\":
                        pos += 2
                    else:
                        pos += 1
            pos += 1
    functions.sort(key=lambda f: f.start)
    return functions


def find_containing_function(functions: list[FunctionRange], pos: int) -> FunctionRange | None:
    """Binary search for the function whose [start, end) contains pos."""
    # functions sorted by start; find the last one with start <= pos
    idx = bisect_right([f.start for f in functions], pos) - 1
    if idx < 0:
        return None
    f = functions[idx]
    if f.start <= pos < f.end:
        return f
    return None


def find_string_literal_end(source: str, quote_pos: int) -> int | None:
    """Return position just after the closing quote of a string literal starting at quote_pos."""
    pos = quote_pos + 1
    while pos < len(source):
        if source[pos] == "\\":
            pos += 2
        elif source[pos] == '"':
            return pos + 1
        else:
            pos += 1
    return None


def extract_first_string_literal(text: str) -> str | None:
    """Find the first string literal in text and return its decoded content (None if absent)."""
    pos = 0
    while pos < len(text):
        if text[pos] == '"':
            end = find_string_literal_end(text, pos)
            if end is None:
                return None
            raw = text[pos + 1:end - 1]
            # Decode common escapes
            decoded = raw.encode("utf-8").decode("unicode_escape", errors="replace")
            return decoded
        pos += 1
    return None


def find_access_point_def(source_root: Path) -> Path | None:
    """Locate access_point.def under source_root (the src/datasystem scan root)."""
    candidates = [
        source_root / "common" / "log" / "access_point.def",
    ]
    for c in candidates:
        if c.is_file():
            return c
    # Fall back to recursive search.
    for found in sorted(source_root.rglob("access_point.def")):
        return found
    return None


def scan_file(file_path: Path, source_root: Path, access_keys: dict[str, str]) -> tuple[list[ConstructionSite], list[ResultSite]]:
    """Scan one source file for AccessRecorder construction and Result() call sites."""
    try:
        source = file_path.read_text(encoding="utf-8", errors="replace")
    except (OSError, UnicodeDecodeError):
        return [], []

    line_starts = build_line_starts(source)
    functions = find_functions(source, line_starts)

    constructions: list[ConstructionSite] = []
    result_sites: list[ResultSite] = []

    # Pass 1: find factory calls (AccessRecorder::Object/Stream/RequestOut(...))
    for match in FACTORY_CALL_RE.finditer(source):
        factory_kind = match.group(1)  # Object / Stream / RequestOut
        key_type = FACTORY_PATTERNS[f"AccessRecorder::{factory_kind}"]
        open_paren = match.end() - 1
        close_end = find_call_end(source, open_paren)
        if close_end is None:
            continue
        args = split_top_level_arguments(source, open_paren, close_end)
        if not args:
            continue
        raw_arg = args[0]
        # Try to extract AccessRecorderKey::DS_XXX literal
        key_match = ACCESS_KEY_RE.search(raw_arg)
        key_name = key_match.group(1) if key_match else None
        function = find_containing_function(functions, match.start())
        func_name = function.name if function else "<global>"
        rel_path = str(file_path.relative_to(source_root))
        constructions.append(ConstructionSite(
            file=rel_path,
            line=line_number(line_starts, match.start()),
            function=func_name,
            key_name=key_name,
            key_type=key_type,
            raw_argument=raw_arg,
        ))

    # Pass 1b: find direct construction (ObjectAccessRecorder var(KEY))
    for match in DIRECT_CTOR_RE.finditer(source):
        class_name = match.group(1)
        var_name = match.group(2)
        key_type = DIRECT_CONSTRUCTORS[class_name]
        open_paren = match.end() - 1
        close_end = find_call_end(source, open_paren)
        if close_end is None:
            continue
        args = split_top_level_arguments(source, open_paren, close_end)
        if not args:
            continue
        raw_arg = args[0]
        key_match = ACCESS_KEY_RE.search(raw_arg)
        key_name = key_match.group(1) if key_match else None
        function = find_containing_function(functions, match.start())
        func_name = function.name if function else "<global>"
        rel_path = str(file_path.relative_to(source_root))
        # Skip false positives like `ObjectAccessRecorder &ObjectAccessRecorder::SomeMethod(...)`
        if key_name is None and "Recorder::" in raw_arg:
            continue
        constructions.append(ConstructionSite(
            file=rel_path,
            line=line_number(line_starts, match.start()),
            function=func_name,
            key_name=key_name,
            key_type=key_type,
            raw_argument=raw_arg,
        ))

    # Pass 2: find .Result(...) calls
    for match in RESULT_CALL_RE.finditer(source):
        open_paren = match.end() - 1
        close_end = find_call_end(source, open_paren)
        if close_end is None:
            continue
        args = split_top_level_arguments(source, open_paren, close_end)
        raw_arg = ", ".join(args)
        # Extract explicit StatusCode::K_XXX if present
        code_match = STATUSCODE_RE.search(raw_arg)
        explicit_code = code_match.group(1) if code_match else None
        # Extract first string literal as respMsg (if present)
        resp_msg = extract_first_string_literal(raw_arg)
        function = find_containing_function(functions, match.start())
        func_name = function.name if function else "<global>"
        rel_path = str(file_path.relative_to(source_root))
        result_sites.append(ResultSite(
            file=rel_path,
            line=line_number(line_starts, match.start()),
            function=func_name,
            explicit_code=explicit_code,
            explicit_resp_msg=resp_msg,
            raw_argument=raw_arg,
            matched_access_key=None,  # filled in pass 3
        ))

    # Pass 3: for each Result call, find the nearest AccessRecorder construction in the same function.
    # Build a per-function list of constructions for quick lookup.
    func_to_constructions: dict[str, list[ConstructionSite]] = {}
    for c in constructions:
        func_to_constructions.setdefault(c.function, []).append(c)
    for r in result_sites:
        cands = func_to_constructions.get(r.function, [])
        if cands:
            # Pick the construction with the smallest line distance above the Result call.
            # If multiple, choose the closest preceding one.
            same_file_cands = [c for c in cands if c.file == r.file]
            if same_file_cands:
                preceding = [c for c in same_file_cands if c.line <= r.line]
                if preceding:
                    preceding.sort(key=lambda c: r.line - c.line)
                    r.matched_access_key = preceding[0].key_name
                else:
                    # Result call before any construction in this function — pick the first.
                    r.matched_access_key = same_file_cands[0].key_name

    return constructions, result_sites


def collect_sites(source_root: Path, access_keys: dict[str, str]) -> tuple[list[ConstructionSite], list[ResultSite]]:
    all_constructions: list[ConstructionSite] = []
    all_results: list[ResultSite] = []
    for file_path in sorted(source_root.rglob("*")):
        if not file_path.is_file():
            continue
        if file_path.suffix.lower() not in SOURCE_SUFFIXES:
            continue
        # Skip directories we don't want
        if any(part in SKIP_DIR_NAMES for part in file_path.parts):
            continue
        c, r = scan_file(file_path, source_root, access_keys)
        all_constructions.extend(c)
        all_results.extend(r)
    return all_constructions, all_results


def build_json_result(
    access_points: list[tuple[str, str]],
    constructions: list[ConstructionSite],
    result_sites: list[ResultSite],
    source_root: Path | None,
) -> dict:
    # Group by key_name
    by_key: dict[str, AccessPointInfo] = {}
    for name, kind in access_points:
        by_key[name] = AccessPointInfo(key_name=name, key_type=kind)
    for c in constructions:
        if c.key_name and c.key_name in by_key:
            by_key[c.key_name].construction_sites.append(c)
    for r in result_sites:
        target_key = r.matched_access_key
        if target_key and target_key in by_key:
            by_key[target_key].result_sites.append(r)

    # Build per-K_* explicit code mapping (which access points can produce each K_*).
    explicit_code_to_keys: dict[str, list[str]] = {}
    for r in result_sites:
        if r.explicit_code and r.matched_access_key:
            explicit_code_to_keys.setdefault(r.explicit_code, []).append(r.matched_access_key)

    return {
        "schema_version": SCHEMA_VERSION,
        "source_root": str(source_root) if source_root is not None else None,
        "access_point_def_total": len(access_points),
        "construction_site_total": len(constructions),
        "result_site_total": len(result_sites),
        "explicit_code_site_total": sum(1 for r in result_sites if r.explicit_code),
        "runtime_status_site_total": sum(1 for r in result_sites if not r.explicit_code),
        "access_points": [
            {
                "key_name": info.key_name,
                "key_type": info.key_type,
                "construction_site_count": len(info.construction_sites),
                "result_site_count": len(info.result_sites),
                "construction_sites": [
                    {
                        "file": c.file,
                        "line": c.line,
                        "function": c.function,
                        "key_type": c.key_type,
                        "raw_argument": c.raw_argument,
                    }
                    for c in info.construction_sites
                ],
                "result_sites": [
                    {
                        "file": r.file,
                        "line": r.line,
                        "function": r.function,
                        "explicit_code": r.explicit_code,
                        "explicit_resp_msg": r.explicit_resp_msg,
                        "matched_access_key": r.matched_access_key,
                        "raw_argument": r.raw_argument,
                    }
                    for r in info.result_sites
                ],
            }
            for info in by_key.values()
        ],
        "explicit_code_to_access_keys": {
            code: sorted(set(keys)) for code, keys in explicit_code_to_keys.items()
        },
    }


def dump_json(result: dict, output_file: Path | None = None) -> None:
    if output_file is None:
        json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
        print()
        return
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "输入yuanrong-datasystem仓库根，下探到src/datasystem扫描AccessRecorder"
            "入口候选：解析access_point.def、定位AccessRecorder构造点和.Result()调用点，"
            "为access log故障模式根节点提供锚点。"
        )
    )
    parser.add_argument("source", type=Path, help="yuanrong-datasystem 仓库根目录")
    parser.add_argument("-o", "--output", type=Path, default=OUTPUT_FILE,
                        help=f"输出 JSON 路径，默认 {OUTPUT_FILE}")
    args = parser.parse_args()

    source_root: Path = args.source.resolve()
    if not source_root.is_dir():
        print(f"错误：目录 {source_root} 不存在", file=sys.stderr)
        return 1
    scan_root = source_root / "src" / "datasystem"
    if not scan_root.is_dir():
        print(f"错误：必须输入yuanrong-datasystem仓库根（未找到 {scan_root}）", file=sys.stderr)
        return 1

    def_path = find_access_point_def(scan_root)
    if def_path is None:
        print(f"错误：在 {scan_root} 下未找到 access_point.def", file=sys.stderr)
        return 1

    access_keys_list = parse_access_point_def(def_path)
    access_keys = dict(access_keys_list)
    print(f"解析 access_point.def：共 {len(access_keys)} 个 AccessRecorderKey", file=sys.stderr)

    constructions, result_sites = collect_sites(scan_root, access_keys)
    print(
        f"扫描完成：构造点 {len(constructions)} 个，Result 调用点 {len(result_sites)} 个"
        f"（其中 explicit StatusCode::K_* = {sum(1 for r in result_sites if r.explicit_code)}，"
        f"runtime Status 变量 = {sum(1 for r in result_sites if not r.explicit_code)}）",
        file=sys.stderr,
    )

    result = build_json_result(access_keys_list, constructions, result_sites, scan_root)
    dump_json(result, args.output)
    print(
        f"JSON 结果已写入：{args.output}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    sys.exit(main())
