#!/usr/bin/env python3

"""Extract and pre-group ERROR/FATAL log sites.

The result keeps physical source locations for coverage, but also carries the
source facts needed for downstream analysis: the complete statement, lexical
callable, stable log literals, normalized output template and a conservative
aggregation key.  Error codes are resolved only when a non-zero ``K_*`` value
from ``include/datasystem/utils/status.h`` is explicit at the site or fixed by
the macro.  Anything that needs data-flow analysis is routed to the semantic
lane with a machine-readable analysis task.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import signal
import sys
from bisect import bisect_right
from dataclasses import dataclass
from pathlib import Path


OUTPUT_FILE = Path("/tmp/kvcache_runtime_err.json")
SOURCE_SUFFIXES = {".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp"}
SCHEMA_VERSION = 5
INFRASTRUCTURE_BASENAMES = {"logging.cpp", "failure_handler.cpp", "inject_point.h"}

# Public call-site macros whose first argument is a severity.  Only ERROR and
# FATAL invocations are candidates.  LOG_IMPL/SLOW_LOG_IMPL are expansion
# details, not call-site APIs, so they are metadata but are not scanned.
SEVERITY_MACROS = {
    "LOG": {"severity": 0},
    "LOG_IF": {"severity": 0, "condition": 1},
    "DLOG": {"severity": 0},
    "LOG_EVERY_N": {"severity": 0},
    "LOG_EVERY_T": {"severity": 0},
    "LOG_FIRST_N": {"severity": 0},
    "LOG_IF_EVERY_N": {"severity": 0, "condition": 1},
    "LOG_FIRST_AND_EVERY_N": {"severity": 0},
    "LOG_FIRST_EVERY_N": {"severity": 0},
    "SLOW_LOG": {"severity": 0},
    "SLOW_LOG_IF": {"severity": 0, "condition": 1},
    "SLOW_LOG_IF_OR_VLOG": {
        "severity": 0,
        "condition": 1,
        "content_argument": 3,
    },
}

CHECK_MACROS = {
    "CHECK": "condition",
    "CHECK_EQ": "compare",
    "CHECK_NE": "compare",
    "CHECK_LT": "compare",
    "CHECK_LE": "compare",
    "CHECK_GT": "compare",
    "CHECK_GE": "compare",
    "CHECK_NOTNULL": "notnull",
    "CHECK_STRNE": "strne",
    "DCHECK": "condition",
    "DS_CHECK_OP": "internal_compare",
}

# Macros whose expansion submits an ERROR log.  ``code`` identifies an explicit
# K_* argument, ``status`` identifies a Status-producing expression, and
# ``fixed_code`` identifies a code bound by the macro implementation.
EMITTED_WRAPPER_MACROS = {
    "RETURN_IF_NOT_OK_PRINT_ERROR_MSG": {"kind": "return_status", "status": 0},
    "ASSIGN_IF_NOT_OK_PRINT_ERROR_MSG": {"kind": "assign_status", "status": 1},
    "RETURN_STATUS_LOG_ERROR": {"kind": "return_code", "code": 0},
    "CHECK_FAIL_RETURN_STATUS_PRINT_ERROR": {"kind": "predicate_return_code", "code": 1},
    "LOG_IF_ERROR": {"kind": "log_status", "status": 0},
    "LOG_IF_ERROR_EXCEPT": {"kind": "log_status_except", "status": 0},
    "DLOG_IF_ERROR": {"kind": "debug_log_status", "status": 0},
    "RETRY_ON_EINTR": {"kind": "retry_errno"},
    "RETURN_IF_NOT_OK_API": {"kind": "return_status_api", "status": 0},
    "CHK_RET": {"kind": "return_external_code"},
    "CHK_PTR_NULL": {"kind": "return_external_code"},
    "LOG_AND_SET_FIRST_ERROR": {"kind": "assign_first_status", "code": 0},
    "EXEC_UTIL_SUCCESS": {"kind": "log_status", "status": 0},
    "SHUTDOWN_IF_NOT_OK": {"kind": "return_status", "status": 0},
}

INTERNAL_EXPANSION_MACROS = ["LOG_IMPL", "SLOW_LOG_IMPL"]

SEARCH_SYMBOLS = sorted(
    {*SEVERITY_MACROS, *CHECK_MACROS, *EMITTED_WRAPPER_MACROS},
    key=lambda item: (-len(item), item),
)
signal.signal(signal.SIGPIPE, signal.SIG_DFL)


@dataclass
class FunctionEntry:
    name: str
    start: int
    body_start: int
    end: int
    start_line: int


@dataclass
class LogEntry:
    candidate_id: str
    candidate_kind: str
    file: Path
    macro: str
    line: int
    severity: str | None
    function: str | None
    callable: str | None
    callable_start_line: int | None
    callable_body_hash: str
    statement: str
    statement_end_line: int
    stable_literals: list[str]
    normalized_template: str
    template_confidence: str
    group_id: str
    analysis_lane: str
    error_code: str | None
    error_code_value: int | None
    error_code_expression: str | None
    error_code_resolution: str
    need_skill: bool
    skill_analysis: list[dict[str, str]]


def build_line_starts(source: str) -> list[int]:
    starts = [0]
    starts.extend(pos + 1 for pos, char in enumerate(source) if char == "\n")
    return starts


def line_number(line_starts: list[int], pos: int) -> int:
    return bisect_right(line_starts, pos)


def is_cpp_digit_separator(source: str, pos: int) -> bool:
    """Return whether an apostrophe is a C++14 numeric digit separator."""
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


def skip_whitespace_and_comments_back(source: str, pos: int) -> int:
    pos -= 1
    while pos >= 0:
        if source[pos].isspace():
            pos -= 1
            continue
        if pos > 0 and source[pos - 1:pos + 1] == "*/":
            start = source.rfind("/*", 0, pos - 1)
            if start == -1:
                return pos
            pos = start - 1
            continue
        return pos
    return -1


def find_call_end(source: str, open_paren: int) -> int | None:
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


def find_matching_open_paren(source: str, close_paren: int) -> int | None:
    depth = 0
    pos = close_paren
    while pos >= 0:
        char = source[pos]
        if char == ")":
            depth += 1
        elif char == "(":
            depth -= 1
            if depth == 0:
                return pos
        pos -= 1
    return None


def normalize_code(code: str) -> str:
    result: list[str] = []
    pos = 0
    state = "normal"
    pending_space = False
    while pos < len(code):
        char = code[pos]
        next_char = code[pos + 1] if pos + 1 < len(code) else ""
        if state == "normal":
            if char == '"' or (char == "'" and not is_cpp_digit_separator(code, pos)):
                if pending_space and result:
                    result.append(" ")
                pending_space = False
                result.append(char)
                state = "string" if char == '"' else "char"
            elif char == "/" and next_char == "/":
                pending_space = True
                state = "line_comment"
                pos += 1
            elif char == "/" and next_char == "*":
                pending_space = True
                state = "block_comment"
                pos += 1
            elif char.isspace() or (char == "\\" and next_char == "\n"):
                pending_space = True
                if char == "\\":
                    pos += 1
            else:
                if pending_space and result:
                    result.append(" ")
                pending_space = False
                result.append(char)
        elif state in {"string", "char"}:
            result.append(char)
            if char == "\\" and pos + 1 < len(code):
                pos += 1
                result.append(code[pos])
            elif (state == "string" and char == '"') or (state == "char" and char == "'"):
                state = "normal"
        elif state == "line_comment":
            if char == "\n":
                state = "normal"
        elif state == "block_comment" and char == "*" and next_char == "/":
            state = "normal"
            pos += 1
        pos += 1
    return "".join(result).strip()


def mask_non_code(source: str) -> str:
    result = list(source)
    pos = 0
    state = "normal"
    while pos < len(source):
        char = source[pos]
        next_char = source[pos + 1] if pos + 1 < len(source) else ""
        if state == "normal":
            if char == '"':
                result[pos] = " "
                state = "string"
            elif char == "'" and not is_cpp_digit_separator(source, pos):
                result[pos] = " "
                state = "char"
            elif char == "/" and next_char in {"/", "*"}:
                result[pos] = result[pos + 1] = " "
                state = "line_comment" if next_char == "/" else "block_comment"
                pos += 1
        elif state in {"string", "char"}:
            if char != "\n":
                result[pos] = " "
            if char == "\\" and pos + 1 < len(source):
                pos += 1
                if source[pos] != "\n":
                    result[pos] = " "
            elif (state == "string" and char == '"') or (state == "char" and char == "'"):
                state = "normal"
        elif state == "line_comment":
            if char == "\n":
                state = "normal"
            else:
                result[pos] = " "
        elif state == "block_comment":
            if char != "\n":
                result[pos] = " "
            if char == "*" and next_char == "/":
                result[pos + 1] = " "
                state = "normal"
                pos += 1
        pos += 1
    return "".join(result)


def mask_macro_definitions(masked_source: str) -> str:
    """Blank complete #define continuations while preserving offsets/newlines."""
    result = list(masked_source)
    starts = build_line_starts(masked_source)
    line = 0
    while line < len(starts):
        start = starts[line]
        end = starts[line + 1] if line + 1 < len(starts) else len(masked_source)
        if re.match(r"\s*#\s*define\b", masked_source[start:end]) is None:
            line += 1
            continue
        while True:
            for pos in range(start, end):
                if result[pos] != "\n":
                    result[pos] = " "
            physical = masked_source[start:end].rstrip("\r\n")
            if not physical.rstrip().endswith("\\") or line + 1 >= len(starts):
                break
            line += 1
            start = starts[line]
            end = starts[line + 1] if line + 1 < len(starts) else len(masked_source)
        line += 1
    return "".join(result)


def split_top_level_arguments(source: str, open_paren: int, call_end: int) -> list[str]:
    text = source[open_paren + 1:call_end - 1]
    arguments: list[str] = []
    start = 0
    paren = bracket = brace = angle = 0
    pos = 0
    state = "normal"
    while pos < len(text):
        char = text[pos]
        next_char = text[pos + 1] if pos + 1 < len(text) else ""
        if state == "normal":
            if char == '"':
                state = "string"
            elif char == "'" and not is_cpp_digit_separator(text, pos):
                state = "char"
            elif char == "/" and next_char == "/":
                state = "line_comment"
                pos += 1
            elif char == "/" and next_char == "*":
                state = "block_comment"
                pos += 1
            elif char == "(":
                paren += 1
            elif char == ")":
                paren = max(0, paren - 1)
            elif char == "[":
                bracket += 1
            elif char == "]":
                bracket = max(0, bracket - 1)
            elif char == "{":
                brace += 1
            elif char == "}":
                brace = max(0, brace - 1)
            elif char == "," and paren == bracket == brace == angle == 0:
                arguments.append(normalize_code(text[start:pos]))
                start = pos + 1
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
    final = normalize_code(text[start:])
    if final or arguments:
        arguments.append(final)
    return arguments


def strip_comments(text: str) -> str:
    return normalize_code(text)


def first_nonblank_pos(source: str, start: int, end: int) -> int:
    while start < end and source[start].isspace():
        start += 1
    return start


def find_parameter_close(source: str, brace_pos: int) -> int | None:
    pos = skip_whitespace_and_comments_back(source, brace_pos)
    suffix_words = {"const", "volatile", "override", "final", "noexcept"}
    while pos >= 0:
        if source[pos] == ")":
            open_paren = find_matching_open_paren(source, pos)
            if open_paren is None:
                return None
            prefix_end = skip_whitespace_and_comments_back(source, open_paren) + 1
            match = re.search(r"([A-Za-z_][A-Za-z0-9_]*)\s*$", source[:prefix_end])
            if match is not None and match.group(1) == "noexcept":
                pos = skip_whitespace_and_comments_back(source, match.start(1))
                continue
            return pos
        if source[pos].isalnum() or source[pos] == "_":
            end = pos + 1
            while pos >= 0 and (source[pos].isalnum() or source[pos] == "_"):
                pos -= 1
            if source[pos + 1:end] in suffix_words:
                pos = skip_whitespace_and_comments_back(source, pos + 1)
                continue
            return None
        if source[pos] in {"&"}:
            pos = skip_whitespace_and_comments_back(source, pos)
            continue
        return None
    return None


def find_function_name(source: str, header_start: int, open_paren: int) -> str | None:
    prefix = source[header_start:open_paren]
    match = re.search(r"(?:[A-Za-z_][A-Za-z0-9_]*::)*([A-Za-z_~][A-Za-z0-9_]*)\s*$", prefix)
    return match.group(1) if match is not None else None


def parse_function_at_brace(source: str, brace_pos: int, header_start: int,
                            line_starts: list[int]) -> tuple[str, int, int, int] | None:
    close_paren = find_parameter_close(source, brace_pos)
    if close_paren is None:
        return None
    open_paren = find_matching_open_paren(source, close_paren)
    if open_paren is None:
        return None
    name = find_function_name(source, header_start, open_paren)
    if name is None or name in {"if", "for", "while", "switch", "return", "sizeof", "catch"}:
        return None
    header = strip_comments(source[header_start:brace_pos])
    if ";" in header:
        return None
    function_start = first_nonblank_pos(source, header_start, open_paren)
    return name, function_start, brace_pos, line_number(line_starts, function_start)


def find_function_end(source: str, open_brace: int) -> int:
    depth = 0
    pos = open_brace
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
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return pos + 1
        elif state in {"string", "char"}:
            if char == "\\":
                pos += 1
            elif (state == "string" and char == '"') or (state == "char" and char == "'"):
                state = "normal"
        elif state == "line_comment":
            if char == "\n":
                state = "normal"
        elif state == "block_comment" and char == "*" and next_char == "/":
            state = "normal"
            pos += 1
        pos += 1
    return len(source)


def find_functions(source: str) -> list[FunctionEntry]:
    line_starts = build_line_starts(source)
    functions: list[FunctionEntry] = []
    header_starts = [0]
    depth = 0
    pos = 0
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
            elif char == "{":
                parsed = parse_function_at_brace(source, pos, header_starts[depth], line_starts)
                if parsed is not None:
                    name, start, body_start, start_line = parsed
                    end = find_function_end(source, pos)
                    functions.append(FunctionEntry(name, start, body_start, end, start_line))
                    header_starts[depth] = end
                    pos = end
                    continue
                depth += 1
                header_starts.append(pos + 1)
            elif char == "}" and depth > 0:
                header_starts.pop()
                depth -= 1
                header_starts[depth] = pos + 1
            elif char == ";":
                header_starts[depth] = pos + 1
        elif state in {"string", "char"}:
            if char == "\\":
                pos += 1
            elif (state == "string" and char == '"') or (state == "char" and char == "'"):
                state = "normal"
        elif state == "line_comment":
            if char == "\n":
                state = "normal"
        elif state == "block_comment" and char == "*" and next_char == "/":
            state = "normal"
            pos += 1
        pos += 1
    return functions


def find_containing_function(functions: list[FunctionEntry], pos: int) -> FunctionEntry | None:
    containing = [function for function in functions if function.start <= pos < function.end]
    return max(containing, key=lambda item: item.start) if containing else None


def find_enclosing_callable(source: str, pos: int,
                            line_starts: list[int]) -> FunctionEntry | None:
    """Fallback for operators, lambdas and signatures with braced defaults."""
    code = mask_non_code(source)
    stack: list[tuple[int, FunctionEntry | None]] = []
    cursor = 0
    while cursor < pos:
        char = code[cursor]
        if char == "{":
            entry: FunctionEntry | None = None
            close_paren = skip_whitespace_and_comments_back(source, cursor)
            if close_paren >= 0 and source[close_paren] != ")":
                search_start = max(0, cursor - 1000)
                arrow = code.rfind("->", search_start, cursor)
                if arrow >= 0:
                    candidate = code.rfind(")", search_start, arrow)
                    if candidate >= 0:
                        close_paren = candidate
            if close_paren >= 0 and source[close_paren] == ")":
                open_paren = find_matching_open_paren(code, close_paren)
                if open_paren is not None:
                    prefix_start = max(0, open_paren - 1000)
                    prefix = code[prefix_start:open_paren]
                    name_match = re.search(
                        r"(?:[A-Za-z_][A-Za-z0-9_]*::)*([A-Za-z_~][A-Za-z0-9_]*)\s*$",
                        prefix,
                    )
                    name = name_match.group(1) if name_match is not None else None
                    if re.search(r"operator\s*\(\s*\)\s*$", prefix):
                        name = "operator()"
                    elif prefix.rstrip().endswith("]"):
                        name = "<lambda>"
                    if name not in {None, "if", "for", "while", "switch", "catch"}:
                        delimiter = max(
                            code.rfind(";", prefix_start, open_paren),
                            code.rfind("{", prefix_start, open_paren),
                            code.rfind("}", prefix_start, open_paren),
                        )
                        start = first_nonblank_pos(source, prefix_start + delimiter + 1, open_paren)
                        entry = FunctionEntry(
                            name=name,
                            start=start,
                            body_start=cursor,
                            end=find_function_end(source, cursor),
                            start_line=line_number(line_starts, start),
                        )
            stack.append((cursor, entry))
        elif char == "}" and stack:
            stack.pop()
        cursor += 1
    for _, entry in reversed(stack):
        if entry is not None:
            return entry
    return None


def find_statement_end(source: str, start: int, limit: int) -> int | None:
    paren = bracket = brace = 0
    pos = start
    state = "normal"
    while pos < limit:
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
                paren += 1
            elif char == ")":
                paren = max(0, paren - 1)
            elif char == "[":
                bracket += 1
            elif char == "]":
                bracket = max(0, bracket - 1)
            elif char == "{":
                brace += 1
            elif char == "}":
                if brace == 0:
                    return None
                brace -= 1
            elif char == ";" and paren == bracket == brace == 0:
                return pos + 1
        elif state in {"string", "char"}:
            if char == "\\":
                pos += 1
            elif (state == "string" and char == '"') or (state == "char" and char == "'"):
                state = "normal"
        elif state == "line_comment":
            if char == "\n":
                state = "normal"
        elif state == "block_comment" and char == "*" and next_char == "/":
            state = "normal"
            pos += 1
        pos += 1
    return None


def starts_with_keyword(source: str, pos: int, keyword: str) -> bool:
    if not source.startswith(keyword, pos):
        return False
    before = pos == 0 or not (source[pos - 1].isalnum() or source[pos - 1] == "_")
    end = pos + len(keyword)
    after = end >= len(source) or not (source[end].isalnum() or source[end] == "_")
    return before and after


def strip_outer_parentheses(expression: str) -> str:
    result = expression.strip()
    while result.startswith("(") and result.endswith(")"):
        open_pos = find_matching_open_paren(result, len(result) - 1)
        if open_pos != 0:
            break
        result = result[1:-1].strip()
    return result


def extract_error_code(expression: str | None,
                       error_definitions: dict[str, int]) -> tuple[str | None, bool]:
    if expression is None:
        return None, True
    value = strip_outer_parentheses(expression)
    if re.fullmatch(r"(?:datasystem::)?Status::OK\(\)", value):
        return "K_OK", True
    status = re.search(
        r"(?:datasystem::)?Status\s*\(\s*(?:StatusCode::)?(K_[A-Z0-9_]+)\b",
        value,
    )
    if status is not None:
        return status.group(1), status.group(1) in error_definitions
    symbol = re.fullmatch(r"(?:StatusCode::)?(K_[A-Z0-9_]+)", value)
    if symbol is not None:
        return symbol.group(1), symbol.group(1) in error_definitions
    return None, False


def parse_status_definitions(root: Path) -> dict[str, int]:
    header = root / "include/datasystem/utils/status.h"
    if not header.is_file():
        return {}
    try:
        source = header.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {}
    source = re.sub(r"//[^\n]*|/\*.*?\*/", " ", source, flags=re.S)
    match = re.search(r"enum\s+StatusCode\s*:[^{]+\{(.*?)\};", source, re.S)
    if match is None:
        return {}
    definitions: dict[str, int] = {}
    current = -1
    for item in match.group(1).split(","):
        item = item.strip()
        if not item:
            continue
        parsed = re.match(r"(K_[A-Z0-9_]+)(?:\s*=\s*([^\s]+))?", item)
        if parsed is None:
            continue
        name, raw_value = parsed.groups()
        if raw_value is None:
            current += 1
        else:
            try:
                current = int(raw_value, 0)
            except ValueError:
                continue
        definitions[name] = current
    return definitions


def make_code_result(
    code: str | None,
    expression: str | None,
    resolution: str,
    error_definitions: dict[str, int],
) -> dict:
    value = error_definitions.get(code) if code is not None else None
    # K_OK is deliberately not reported as a failure code.
    if value == 0:
        code = None
        value = None
        expression = None
        resolution = "none"
    return {
        "error_code": code,
        "error_code_value": value,
        "error_code_expression": expression,
        "error_code_resolution": resolution,
        "skill_analysis": [],
    }


def resolve_code_expression(
    expression: str | None,
    error_definitions: dict[str, int],
    resolution: str = "explicit",
) -> dict:
    code, known = extract_error_code(expression, error_definitions)
    if known:
        # Once a K_* is resolved, retain only the code token. This avoids
        # leaking Status message arguments into the location-oriented output.
        return make_code_result(code, code, resolution, error_definitions)
    return make_code_result(None, expression, "dynamic", error_definitions)


def status_code_expression(status_expression: str | None) -> str | None:
    if status_expression is None:
        return None
    return f"Status({status_expression}).GetCode()"


def resolve_status_expression(
    status_expression: str | None,
    error_definitions: dict[str, int],
) -> dict:
    resolved = resolve_code_expression(status_expression, error_definitions)
    if resolved["error_code_resolution"] == "dynamic":
        resolved["error_code_expression"] = status_code_expression(status_expression)
    return resolved


def expression_may_be_status(expression: str | None) -> bool:
    if expression is None:
        return False
    value = strip_outer_parentheses(expression)
    if re.search(r"\b(?:Status|StatusCode)\b|\bK_[A-Z0-9_]+\b|\.GetCode\s*\(", value):
        return True
    return re.fullmatch(
        r"(?:[A-Za-z_][A-Za-z0-9_]*::)*(?:rc\w*|\w*[Ss]tatus\w*|lastRc\w*)",
        value,
    ) is not None


def add_resolve_code_task(result: dict, expression: str | None, reason: str) -> None:
    result["skill_analysis"].append({
        "task": "resolve_status_code",
        "expression": expression or "<unknown>",
        "reason": reason,
    })


def analyze_following_return_code(
    source: str,
    function: FunctionEntry | None,
    statement_end: int,
    error_definitions: dict[str, int],
) -> dict:
    result = make_code_result(None, None, "none", error_definitions)
    if function is None:
        return result
    pos = statement_end
    assignments: dict[str, str] = {}
    for _ in range(16):
        pos = skip_whitespace_and_comments(source, pos)
        if pos >= function.end or source[pos] == "}":
            return result
        if starts_with_keyword(source, pos, "return"):
            end = find_statement_end(source, pos, function.end)
            if end is None:
                return result
            statement = normalize_code(source[pos:end])
            expression = statement[len("return"):].rstrip(";").strip() or None
            expression = assignments.get(expression or "", expression)
            _, directly_known = extract_error_code(expression, error_definitions)
            resolved = resolve_code_expression(expression, error_definitions)
            if directly_known:
                return resolved
            if expression_may_be_status(expression):
                resolved["error_code_expression"] = (
                    expression if expression and ".GetCode(" in expression
                    else status_code_expression(expression)
                )
                add_resolve_code_task(
                    resolved,
                    resolved["error_code_expression"],
                    "The return statement carries a Status or StatusCode whose concrete non-zero K_* is not local.",
                )
                return resolved
            return result
        if any(starts_with_keyword(source, pos, item) for item in
               ("if", "else", "for", "while", "switch", "do", "case", "default", "goto", "break", "continue")) \
                or source[pos] == "{":
            return result
        end = find_statement_end(source, pos, function.end)
        if end is None:
            return result
        statement = normalize_code(source[pos:end])
        match = re.match(
            r"^(?:[A-Za-z_][A-Za-z0-9_:<>*& ]*\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=(?!=)\s*(.+);$",
            statement,
        )
        if match is not None:
            assignments[match.group(1)] = match.group(2).strip()
        pos = end
    return result


def find_status_expression_in_stream(stream_content: str) -> str | None:
    get_code = re.search(
        r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\.\s*GetCode\s*\(",
        stream_content,
    )
    if get_code is not None:
        return f"{get_code.group(1)}.GetCode()"
    status_render = re.search(
        r"\b((?:rc\w*|\w*[Ss]tatus\w*|lastRc\w*))\s*\.\s*(?:ToString|GetMsg)\s*\(",
        stream_content,
    )
    return f"{status_render.group(1)}.GetCode()" if status_render is not None else None


def stream_log_content(source: str, call_end: int, statement_end: int) -> str:
    tail = normalize_code(source[call_end:statement_end - 1])
    if tail.startswith("<<"):
        tail = tail[2:].strip()
    return tail


def callable_signature(source: str, function: FunctionEntry | None) -> str | None:
    if function is None:
        return None
    return normalize_code(source[function.start:function.body_start]).strip() or function.name


def decode_cpp_string_literal(token: str) -> str:
    """Decode the common C++ string forms without evaluating C++ expressions."""
    raw = re.fullmatch(r'(?:u8|u|U|L)?R"([^ ()\\\t\r\n]{0,16})\((.*)\)\1"', token, re.S)
    if raw is not None:
        return raw.group(2)
    value = re.sub(r"^(?:u8|u|U|L)", "", token)
    try:
        decoded = ast.literal_eval(value)
    except (SyntaxError, ValueError):
        return value[1:-1] if len(value) >= 2 else value
    return decoded if isinstance(decoded, str) else str(decoded)


def cpp_string_literals(expression: str) -> list[tuple[int, int, str]]:
    """Return source spans and rendered content for C++ string literals."""
    literals: list[tuple[int, int, str]] = []
    pos = 0
    while pos < len(expression):
        match = re.match(r'(?:u8|u|U|L)?R"([^ ()\\\t\r\n]{0,16})\(', expression[pos:])
        if match is not None:
            delimiter = match.group(1)
            end_marker = f'){delimiter}"'
            end = expression.find(end_marker, pos + match.end())
            if end != -1:
                end += len(end_marker)
                token = expression[pos:end]
                literals.append((pos, end, decode_cpp_string_literal(token)))
                pos = end
                continue
        match = re.match(r'(?:u8|u|U|L)?"', expression[pos:])
        if match is None:
            pos += 1
            continue
        start = pos
        pos += match.end()
        while pos < len(expression):
            if expression[pos] == "\\":
                pos += 2
                continue
            if expression[pos] == '"':
                pos += 1
                token = expression[start:pos]
                literals.append((start, pos, decode_cpp_string_literal(token)))
                break
            pos += 1
    return literals


FORMAT_PLACEHOLDER = re.compile(
    r"%(?:\d+\$)?[-+ #0']*(?:\d+|\*)?(?:\.(?:\d+|\*))?"
    r"(?:hh|h|ll|l|j|z|t|L)?[diuoxXfFeEgGaAcspn]"
)


def split_format_literal(value: str) -> list[str]:
    """Split printf placeholders while retaining escaped percent signs."""
    sentinel = "\x00PERCENT\x00"
    escaped = value.replace("%%", sentinel)
    parts = [part.replace(sentinel, "%") for part in FORMAT_PLACEHOLDER.split(escaped)]
    return [part for part in parts if part]


def stable_literals_from_expression(expression: str, formatted: bool = False) -> list[str]:
    if formatted:
        call = re.search(r"\b(?P<name>FormatString|printf|fprintf|snprintf)\s*\(", expression)
        if call is not None:
            open_paren = expression.find("(", call.start())
            call_end = find_call_end(expression, open_paren)
            if call_end is not None:
                arguments = split_top_level_arguments(expression, open_paren, call_end)
                format_index = {"FormatString": 0, "printf": 0, "fprintf": 1, "snprintf": 2}[call.group("name")]
                if format_index < len(arguments):
                    values = [value for _, _, value in cpp_string_literals(arguments[format_index])]
                    return [part for value in values for part in split_format_literal(value)]
    values: list[str] = []
    for _, _, value in cpp_string_literals(expression):
        values.extend(split_format_literal(value) if formatted else [value])
    return [value for value in values if value]


LOCAL_STRING_TYPE = re.compile(
    r"(?:const\s+)?(?:(?:std::)?(?:string|stringstream|ostringstream)|auto)\s+"
)


def simple_logged_value(expression: str) -> str | None:
    """Return the local/constant identifier rendered by a simple log expression."""
    value = strip_outer_parentheses(expression)
    match = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_]*)(?:\s*\.\s*str\s*\(\s*\))?", value)
    return match.group(1) if match is not None else None


def stable_literals_from_local_value(expression: str, local_context: str) -> list[str]:
    """Conservatively resolve literals assigned/appended to a local string value.

    This intentionally handles only straight-line local construction. Branch-dependent
    values, function parameters, Status messages and mutating method calls remain work
    for ``resolve_log_template`` source analysis.
    """
    name = simple_logged_value(expression)
    if name is None:
        return []
    declaration = re.compile(
        rf"\b{LOCAL_STRING_TYPE.pattern}{re.escape(name)}\b(?P<initializer>[^;]*);",
        re.S,
    )
    declarations = list(declaration.finditer(local_context))
    if not declarations:
        return []
    start = declarations[-1]
    segment = local_context[start.start():]
    masked_segment = mask_non_code(segment)
    initializer = start.group("initializer")
    literals = stable_literals_from_expression(
        initializer,
        formatted=bool(re.search(r"\bFormatString\s*\(", initializer)),
    )
    # An immutable local string keeps the same value regardless of surrounding
    # control flow.  In particular, a conditional LOG must not turn a directly
    # initialized const error message into a dynamic-only template.
    if re.search(r"\bconst\s+(?:(?:std::)?string|auto)\b", start.group(0)) and literals:
        return literals
    tail = segment[start.end() - start.start():]
    reassigned = re.search(rf"\b{re.escape(name)}\s*(?:=|\+=|<<)", tail)
    mutated = re.search(rf"\b{re.escape(name)}\s*\.\s*(?!str\s*\()\w+\s*\(", tail)
    # A non-const local with a literal initializer is equally stable when no
    # statement before the log can replace or mutate it.  Permit ternaries in
    # FormatString arguments because they affect only dynamic substitutions.
    if literals and not reassigned and not mutated and \
            ("?" not in mask_non_code(initializer) or "FormatString" in initializer):
        return literals
    if re.search(r"\b(?:if|else|for|while|switch|case|default|catch)\b", masked_segment) or \
            "?" in masked_segment:
        return []
    if re.search(rf"\b{re.escape(name)}\s*\.\s*(?!str\s*\()\w+\s*\(", masked_segment):
        return []
    modification = re.compile(
        rf"(?:^|[;{{}}])\s*{re.escape(name)}\s*(?P<operator><<|\+=|=)\s*(?P<value>.*?);",
        re.S,
    )
    for match in modification.finditer(tail):
        value = match.group("value")
        formatted = bool(re.search(r"\b(?:FormatString|printf|fprintf|snprintf)\s*\(", value))
        values = stable_literals_from_expression(value, formatted=formatted)
        if match.group("operator") == "=":
            literals = values
        else:
            literals.extend(values)
    return literals


def stable_literals_from_named_constant(expression: str, source_context: str) -> list[str]:
    """Resolve a directly logged file-scope const/constexpr string declaration."""
    name = simple_logged_value(expression)
    if name is None:
        return []
    declaration = re.compile(
        rf"\b(?:inline\s+)?(?:static\s+)?(?:constexpr|const)\s+"
        rf"(?:(?:std::)?string(?:_view)?|char(?:\s+const)?\s*\*?|char)\s+"
        rf"{re.escape(name)}(?:\s*\[\s*\])?\s*=\s*(?P<value>.*?);",
        re.S,
    )
    matches = list(declaration.finditer(strip_comments(source_context)))
    if not matches:
        return []
    return stable_literals_from_expression(matches[-1].group("value"))


def resolve_expression_literals(expression: str, local_context: str, source_context: str,
                                formatted: bool = False) -> list[str]:
    literals = stable_literals_from_expression(expression, formatted=formatted)
    if literals:
        return literals
    literals = stable_literals_from_local_value(expression, local_context)
    if literals:
        return literals
    name = simple_logged_value(expression)
    if name is not None and re.search(
        rf"\b{LOCAL_STRING_TYPE.pattern}{re.escape(name)}\b", local_context,
    ):
        return []
    return stable_literals_from_named_constant(expression, source_context)


WRAPPER_TEMPLATE_SPECS: dict[str, dict[str, object]] = {
    "RETURN_IF_NOT_OK_PRINT_ERROR_MSG": {"message": 1, "suffix": ["Detail: "]},
    "ASSIGN_IF_NOT_OK_PRINT_ERROR_MSG": {"message": 2, "suffix": ["Detail: "]},
    "RETURN_STATUS_LOG_ERROR": {"message": 1},
    "CHECK_FAIL_RETURN_STATUS_PRINT_ERROR": {"message": 2},
    "LOG_IF_ERROR": {"message": 1, "suffix": ["Detail: "]},
    "LOG_IF_ERROR_EXCEPT": {"message": 1, "suffix": ["Detail: "]},
    "RETURN_IF_NOT_OK_API": {"fixed": ["Send status failed. Detail: "]},
    "RETRY_ON_EINTR": {"fixed": ["Get error after retry, retry count: ", ", errno: "]},
    "CHK_RET": {"fixed": ["hcclRet ", " at ", ":"]},
    "CHK_PTR_NULL": {"fixed": ["ptr [", "] is NULL at ", ":"], "stringify": 0},
    "LOG_AND_SET_FIRST_ERROR": {"message": 1},
    "EXEC_UTIL_SUCCESS": {"fixed": ["Execute ETCD op failed: "]},
}


CHECK_OPERATORS = {
    "CHECK_EQ": "==", "CHECK_NE": "!=", "CHECK_LT": "<",
    "CHECK_LE": "<=", "CHECK_GT": ">", "CHECK_GE": ">=",
}


def normalized_template_from_literals(literals: list[str], trailing_dynamic: bool) -> str:
    if not literals:
        return "<dynamic>"
    result = "<dynamic>".join(literals)
    return result + ("<dynamic>" if trailing_dynamic else "")


def has_matchable_application_literal(literals: list[str]) -> bool:
    """Reject punctuation-only and connector-only fragments as log keywords."""
    return any(len(re.findall(r"[A-Za-z0-9\u4e00-\u9fff]", literal)) >= 3 for literal in literals)


def build_log_template(
    macro: str,
    arguments: list[str],
    stream_content: str,
    local_context: str = "",
    source_context: str = "",
) -> tuple[list[str], str, str, str]:
    """Return (stable literals, normalized template, confidence, analyzed expression)."""
    if macro in CHECK_MACROS:
        condition = arguments[0].strip() if arguments else "<unknown>"
        if macro in CHECK_OPERATORS and len(arguments) >= 2:
            condition = f"{arguments[0].strip()} {CHECK_OPERATORS[macro]} {arguments[1].strip()}"
        literals = ["Check failed: ", condition]
        return literals, normalized_template_from_literals(literals, True), "exact", condition

    spec = WRAPPER_TEMPLATE_SPECS.get(macro)
    if spec is not None:
        literals = list(spec.get("fixed", []))
        message_index = spec.get("message")
        template_expression = macro
        unresolved_message = False
        if isinstance(message_index, int) and message_index < len(arguments):
            template_expression = arguments[message_index]
            message_literals = resolve_expression_literals(
                template_expression, local_context, source_context,
                formatted=bool(re.search(r"\bFormatString\s*\(", template_expression)),
            )
            unresolved_message = not has_matchable_application_literal(message_literals)
            literals = message_literals + literals
        literals.extend(spec.get("suffix", []))
        stringify_index = spec.get("stringify")
        if isinstance(stringify_index, int) and stringify_index < len(arguments):
            literals.insert(1, arguments[stringify_index].strip())
        trailing_dynamic = macro not in {"RETURN_STATUS_LOG_ERROR", "CHECK_FAIL_RETURN_STATUS_PRINT_ERROR", "LOG_AND_SET_FIRST_ERROR"}
        confidence = "dynamic_only" if unresolved_message or not literals else "exact"
        return literals, normalized_template_from_literals(literals, trailing_dynamic), confidence, template_expression

    content = stream_content
    spec = SEVERITY_MACROS.get(macro, {})
    content_index = spec.get("content_argument")
    if isinstance(content_index, int) and content_index < len(arguments):
        content = arguments[content_index]
    formatted = bool(re.search(r"\b(?:FormatString|printf|fprintf|snprintf)\s*\(", content))
    literals = resolve_expression_literals(content, local_context, source_context, formatted=formatted)
    # A stream or formatting call may contain runtime values before, between or
    # after its literals. Retaining a dynamic separator is conservative and is
    # sufficient for stable-keyword matching.
    template = normalized_template_from_literals(literals, trailing_dynamic=True)
    return literals, template, "exact" if has_matchable_application_literal(literals) else "dynamic_only", content


def stable_digest(parts: list[str]) -> str:
    raw = "\x1f".join(parts).encode("utf-8", errors="replace")
    return hashlib.sha256(raw).hexdigest()


def analysis_lane(file: Path, need_skill: bool) -> str:
    if file.name in INFRASTRUCTURE_BASENAMES:
        return "excluded_infrastructure"
    return "semantic" if need_skill else "deterministic"


def emitted_wrapper_code(
    macro: str,
    arguments: list[str],
    error_definitions: dict[str, int],
) -> dict:
    spec = EMITTED_WRAPPER_MACROS[macro]
    code_index = spec.get("code")
    if isinstance(code_index, int):
        expression = arguments[code_index] if code_index < len(arguments) else None
        result = resolve_code_expression(expression, error_definitions)
        if result["error_code_resolution"] == "dynamic":
            add_resolve_code_task(
                result,
                expression,
                "The ERROR-emitting wrapper receives a runtime StatusCode expression.",
            )
        return result

    status_index = spec.get("status")
    if isinstance(status_index, int):
        expression = arguments[status_index] if status_index < len(arguments) else None
        # RETURN_IF_NOT_OK_API logs the SendStatus result (rc2), not the original
        # status that it returns. Keep that distinction explicit for the skill.
        if spec["kind"] == "return_status_api":
            result = make_code_result(
                None,
                f"SendStatus(Status({expression})).GetCode()" if expression else None,
                "dynamic",
                error_definitions,
            )
            add_resolve_code_task(
                result,
                result["error_code_expression"],
                "The DLOG(ERROR) contains the secondary SendStatus failure code, while the macro returns the original Status.",
            )
            return result
        result = resolve_status_expression(expression, error_definitions)
        if result["error_code_resolution"] == "dynamic":
            add_resolve_code_task(
                result,
                result["error_code_expression"],
                "The emitted log contains a runtime Status whose concrete non-zero K_* is not local.",
            )
        return result

    # errno and external HCCL return values are not StatusCode values from
    # include/datasystem/utils/status.h.
    return make_code_result(None, None, "none", error_definitions)


def find_log_entries(file_path: Path, root: Path,
                     error_definitions: dict[str, int]) -> list[LogEntry]:
    try:
        source = file_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        print(f"警告：无法读取 {file_path}: {exc}", file=sys.stderr)
        return []
    line_starts = build_line_starts(source)
    functions = find_functions(source)
    code = mask_macro_definitions(mask_non_code(source))
    pattern = re.compile(
        r"(?<![A-Za-z0-9_])(?P<macro>" + "|".join(re.escape(item) for item in SEARCH_SYMBOLS)
        + r")(?![A-Za-z0-9_])"
    )
    entries: list[LogEntry] = []
    try:
        display_path = file_path.relative_to(root)
    except ValueError:
        display_path = file_path
    for match in pattern.finditer(code):
        macro = match.group("macro")
        open_paren = skip_whitespace_and_comments(source, match.end())
        if open_paren >= len(source) or source[open_paren] != "(":
            continue
        call_end = find_call_end(source, open_paren)
        if call_end is None:
            print(f"警告：{file_path}:{line_number(line_starts, match.start())} 的 {macro} 括号不完整",
                  file=sys.stderr)
            continue
        arguments = split_top_level_arguments(source, open_paren, call_end)
        if macro in SEVERITY_MACROS:
            severity_index = SEVERITY_MACROS[macro]["severity"]
            if severity_index >= len(arguments):
                continue
            severity = strip_outer_parentheses(arguments[severity_index])
            if severity not in {"ERROR", "FATAL"}:
                continue
        elif macro in CHECK_MACROS:
            severity = "FATAL"
        else:
            severity = "ERROR"
        function = find_containing_function(functions, match.start())
        if function is None:
            function = find_enclosing_callable(source, match.start(), line_starts)
        function_name = function.name if function is not None else None
        signature = callable_signature(source, function)
        callable_start_line = function.start_line if function is not None else None
        callable_body_hash = stable_digest([
            source[function.start:function.end] if function is not None else ""
        ])
        limit = function.end if function is not None else len(source)
        statement_end = find_statement_end(source, call_end, limit)
        if statement_end is None:
            statement_end = call_end
        statement = normalize_code(source[match.start():statement_end])
        if function is None:
            callable_body_hash = stable_digest([statement])
        stream_content = stream_log_content(source, call_end, statement_end)
        local_context = source[function.body_start + 1:match.start()] if function is not None else ""
        literals, template, template_confidence, template_expression = build_log_template(
            macro, arguments, stream_content, local_context, source[:match.start()]
        )
        if macro in EMITTED_WRAPPER_MACROS:
            error = emitted_wrapper_code(macro, arguments, error_definitions)
        elif severity == "FATAL":
            error = make_code_result(None, None, "none", error_definitions)
        else:
            error = analyze_following_return_code(
                source, function, statement_end, error_definitions
            )
            if error["error_code_resolution"] == "none":
                status_expression = find_status_expression_in_stream(stream_content)
                if status_expression is not None:
                    error = make_code_result(
                        None, status_expression, "dynamic", error_definitions
                    )
                    add_resolve_code_task(
                        error,
                        status_expression,
                        "The ERROR log renders a runtime Status; determine its concrete non-zero K_*.",
                    )
        if template_confidence == "dynamic_only":
            error["skill_analysis"].append({
                "task": "resolve_log_template",
                "expression": template_expression or statement,
                "reason": (
                    "The emitted log template has no source-proven stable application literal; "
                    "trace local construction, wrapper expansion and upstream message sources."
                ),
            })
        line = line_number(line_starts, match.start())
        candidate_id = "candidate_" + stable_digest([
            str(display_path), str(line), macro, statement,
        ])[:20]
        # Two visually identical dynamic-only statements in one callable may
        # render Status values from unrelated upstream operations.  Keep them
        # as separate analysis units until resolve_log_template proves a common
        # source template; otherwise aggregation can erase every usable keyword.
        grouping_template = (
            template if template_confidence == "exact"
            else f"{template}\x1e{statement}\x1e{line}"
        )
        group_id = "group_" + stable_digest([
            str(display_path), str(callable_start_line), signature or function_name or "<global>",
            severity, grouping_template,
        ])[:20]
        lane = analysis_lane(display_path, bool(error["skill_analysis"]))
        entries.append(LogEntry(
            candidate_id=candidate_id,
            candidate_kind="emitted_log",
            file=display_path,
            macro=macro,
            line=line,
            severity=severity,
            function=function_name,
            callable=signature,
            callable_start_line=callable_start_line,
            callable_body_hash=callable_body_hash,
            statement=statement,
            statement_end_line=line_number(line_starts, max(match.start(), statement_end - 1)),
            stable_literals=literals,
            normalized_template=template,
            template_confidence=template_confidence,
            group_id=group_id,
            analysis_lane=lane,
            error_code=error["error_code"],
            error_code_value=error["error_code_value"],
            error_code_expression=error["error_code_expression"],
            error_code_resolution=error["error_code_resolution"],
            need_skill=bool(error["skill_analysis"]),
            skill_analysis=error["skill_analysis"],
        ))
    return entries


def collect_logs(root: Path, error_definitions: dict[str, int]) -> list[LogEntry]:
    entries: list[LogEntry] = []
    for file_path in sorted(root.rglob("*")):
        if file_path.is_file() and file_path.suffix.lower() in SOURCE_SUFFIXES:
            entries.extend(find_log_entries(file_path, root, error_definitions))
    return entries


def build_groups(entries: list[LogEntry]) -> list[dict]:
    grouped: dict[str, list[LogEntry]] = {}
    for entry in entries:
        grouped.setdefault(entry.group_id, []).append(entry)
    results: list[dict] = []
    for group_entries in grouped.values():
        first = group_entries[0]
        lanes = {entry.analysis_lane for entry in group_entries}
        lane = (
            "excluded_infrastructure" if lanes == {"excluded_infrastructure"}
            else "semantic" if "semantic" in lanes
            else "deterministic"
        )
        codes = {entry.error_code for entry in group_entries}
        resolved_code = next(iter(codes)) if len(codes) == 1 else None
        code_value = (
            next((entry.error_code_value for entry in group_entries if entry.error_code == resolved_code), None)
            if resolved_code is not None else None
        )
        tasks: list[dict[str, str]] = []
        seen_tasks: set[str] = set()
        for entry in group_entries:
            for task in entry.skill_analysis:
                key = json.dumps(task, ensure_ascii=False, sort_keys=True)
                if key not in seen_tasks:
                    tasks.append(task)
                    seen_tasks.add(key)
        results.append({
            "group_id": first.group_id,
            "file": str(first.file),
            "function": first.function,
            "callable": first.callable,
            "callable_start_line": first.callable_start_line,
            "callable_body_hash": first.callable_body_hash,
            "callable_key": "::".join([
                str(first.file), str(first.callable_start_line), first.callable or first.function or "<global>",
            ]),
            "severity": first.severity,
            "normalized_template": first.normalized_template,
            "stable_literals": first.stable_literals,
            "template_confidence": first.template_confidence,
            "analysis_lane": lane,
            "error_code": resolved_code,
            "error_code_value": code_value,
            "need_skill": lane == "semantic",
            "skill_analysis": tasks,
            "candidate_count": len(group_entries),
            "candidate_ids": [entry.candidate_id for entry in group_entries],
            "physical_sites": [
                {
                    "candidate_id": entry.candidate_id,
                    "line": entry.line,
                    "statement_end_line": entry.statement_end_line,
                    "macro": entry.macro,
                    "error_code": entry.error_code,
                    "error_code_expression": entry.error_code_expression,
                }
                for entry in group_entries
            ],
        })
        results[-1]["content_hash"] = stable_digest([
            "runtime-group-v2", str(first.file), first.callable_body_hash,
            first.severity or "<none>", first.normalized_template,
            json.dumps(tasks, ensure_ascii=False, sort_keys=True),
            *[
                "\x1e".join([
                    entry.macro, entry.statement,
                    entry.error_code or "<null>", entry.error_code_expression or "<null>",
                ])
                for entry in group_entries
            ],
        ])
    return results


def scan_fingerprint(entries: list[LogEntry]) -> str:
    return stable_digest([
        "schema=" + str(SCHEMA_VERSION),
        *[
            "\x1e".join([
                str(entry.file), str(entry.line), entry.statement, entry.group_id,
                entry.error_code or "<null>", entry.error_code_expression or "<null>",
            ])
            for entry in entries
        ],
    ])


def build_json_result(
    entries: list[LogEntry], error_definitions: dict[str, int], source_root: Path | None = None,
) -> dict:
    groups = build_groups(entries)
    return {
        "schema_version": SCHEMA_VERSION,
        "source_root": str(source_root) if source_root is not None else None,
        "scan_fingerprint": scan_fingerprint(entries),
        "macro_groups": {
            "emitted_severity_macros": sorted(SEVERITY_MACROS),
            "emitted_fatal_check_macros": sorted(CHECK_MACROS),
            "emitted_wrapper_macros": sorted(EMITTED_WRAPPER_MACROS),
            "internal_expansion_macros": INTERNAL_EXPANSION_MACROS,
        },
        "error_definitions": error_definitions,
        "total": len(entries),
        "emitted_log_total": len(entries),
        "need_skill_total": sum(entry.need_skill for entry in entries),
        "group_total": len(groups),
        "lane_totals": {
            lane: sum(group["analysis_lane"] == lane for group in groups)
            for lane in ("deterministic", "semantic", "excluded_infrastructure")
        },
        "groups": groups,
        "entries": [
            {
                "candidate_id": entry.candidate_id,
                "candidate_kind": entry.candidate_kind,
                "file": str(entry.file),
                "line": entry.line,
                "macro": entry.macro,
                "severity": entry.severity,
                "function": entry.function,
                "callable": entry.callable,
                "callable_start_line": entry.callable_start_line,
                "callable_body_hash": entry.callable_body_hash,
                "statement": entry.statement,
                "statement_end_line": entry.statement_end_line,
                "stable_literals": entry.stable_literals,
                "normalized_template": entry.normalized_template,
                "template_confidence": entry.template_confidence,
                "group_id": entry.group_id,
                "analysis_lane": entry.analysis_lane,
                "error_code": entry.error_code,
                "error_code_value": entry.error_code_value,
                "error_code_expression": entry.error_code_expression,
                "error_code_resolution": entry.error_code_resolution,
                "need_skill": entry.need_skill,
                "skill_analysis": entry.skill_analysis,
            }
            for entry in entries
        ],
    }


def dump_json(entries: list[LogEntry], error_definitions: dict[str, int],
              output_file: Path | None = None, source_root: Path | None = None) -> None:
    result = build_json_result(entries, error_definitions, source_root)
    if output_file is None:
        json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
        print()
        return
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("w", encoding="utf-8") as file:
        json.dump(result, file, ensure_ascii=False, indent=2)
        file.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "输入yuanrong-datasystem仓库根，下探到src/datasystem递归提取ERROR/FATAL"
            "日志宏调用点；只输出源码位置、宏类型、可直接确定的StatusCode和后续Skill"
            "分析任务，不输出日志原文，不提取仅创建或传播Status的无日志宏。"
        )
    )
    parser.add_argument("source", type=Path, help="yuanrong-datasystem 仓库根目录")
    parser.add_argument("-o", "--output", type=Path, default=OUTPUT_FILE,
                        help=f"JSON 输出路径，默认：{OUTPUT_FILE}")
    args = parser.parse_args()
    source_root = args.source.expanduser().resolve()
    if not source_root.is_dir():
        parser.error(f"目录不存在：{source_root}")
    repository_source = source_root / "src/datasystem"
    if not repository_source.is_dir():
        parser.error(f"必须输入yuanrong-datasystem仓库根（未找到 {repository_source}）")
    scan_root = repository_source
    error_definitions = parse_status_definitions(source_root)
    if error_definitions.get("K_OK") != 0 or not any(
            name.startswith("K_") and value != 0
            for name, value in error_definitions.items()):
        parser.error(
            "无法从 include/datasystem/utils/status.h 解析 StatusCode，"
            "拒绝在缺少非零 K_* 定义时生成不完整结果"
        )
    entries = collect_logs(scan_root, error_definitions)
    output_file = args.output.expanduser().resolve()
    try:
        dump_json(entries, error_definitions, output_file, scan_root)
    except OSError as exc:
        print(f"错误：无法写入 {output_file}: {exc}", file=sys.stderr)
        return 1
    error_count = sum(entry.severity == "ERROR" for entry in entries)
    fatal_count = sum(entry.severity == "FATAL" for entry in entries)
    need_skill_count = sum(entry.need_skill for entry in entries)
    print(
        f"共找到 {len(entries)} 条日志候选（ERROR日志={error_count}, FATAL日志={fatal_count}, "
        f"需Skill分析={need_skill_count}），"
        f"JSON 结果已写入：{output_file}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
