#!/usr/bin/env python3

import argparse
import json
import re
import signal
import sys
from bisect import bisect_right
from dataclasses import dataclass
from pathlib import Path


LOG_MACROS = [
    "UMQ_VLOG_ERR",
    "UMQ_LIMIT_VLOG_ERR",
    "UMQ_VLOG_WARN",
]
WARN_LOG_MACROS = {"UMQ_VLOG_WARN"}
OUTPUT_FILE = Path("/tmp/umq_log_err.json")
SOURCE_SUFFIXES = {".c", ".h", ".cpp", ".hpp"}
EXCLUDED_FILE = "umq_vlog.h"
FALLBACK_ERROR_SYMBOL_PATTERN = re.compile(
    r"\b(?:UMQ_ERR_[A-Z0-9_]+|UMQ_FAIL|UMQ_INVALID_HANDLE|UMQ_INVALID_FD)\b"
)
SENTINEL_EXPRESSIONS = {
    "NULL",
    "nullptr",
    "0",
    "-1",
    "UMQ_FAIL",
    "UMQ_INVALID_HANDLE",
    "UMQ_INVALID_FD",
}
ERROR_DEFINITIONS = {
    "UMQ_SUCCESS": 0,
    "UMQ_FAIL": -1,
    "UMQ_INVALID_HANDLE": 0,
    "UMQ_INVALID_FD": -1,
    "UMQ_ERR_EPERM": 1,
    "UMQ_ERR_EAGAIN": 11,
    "UMQ_ERR_ENOMEM": 12,
    "UMQ_ERR_EBUSY": 16,
    "UMQ_ERR_EEXIST": 17,
    "UMQ_ERR_EINVAL": 22,
    "UMQ_ERR_ENODEV": 19,
    "UMQ_ERR_ENOSR": 63,
    "UMQ_ERR_EFAULT": 14,
    "UMQ_ERR_EMLINK": 31,
    "UMQ_ERR_ENOBUFS": 105,
    "UMQ_ERR_ETIMEOUT": 110,
    "UMQ_ERR_EINPROGRESS": 115,
    "UMQ_ERR_ETOOMANYREFS": 109,
    "UMQ_ERR_ETSEG_NON_IMPORTED": 0x0201,
    "UMQ_ERR_EFLOWCTL": 0x0202,
}
signal.signal(signal.SIGPIPE, signal.SIG_DFL)


@dataclass
class FunctionEntry:
    name: str
    start: int
    end: int
    start_line: int


@dataclass
class LogEntry:
    file: Path
    log_macro: str
    function: str
    function_start_line: int
    log_line: int
    log_content: str
    error_code: str | int | None
    error_source: str
    error_expression: str | None
    needs_skill: bool


def build_line_starts(source: str) -> list[int]:
    starts = [0]
    for pos, char in enumerate(source):
        if char == "\n":
            starts.append(pos + 1)
    return starts


def line_number(line_starts: list[int], pos: int) -> int:
    return bisect_right(line_starts, pos)


def skip_whitespace_and_comments(source: str, pos: int) -> int:
    length = len(source)

    while pos < length:
        if source[pos].isspace():
            pos += 1
            continue

        if source.startswith("//", pos):
            newline = source.find("\n", pos + 2)
            if newline == -1:
                return length
            pos = newline + 1
            continue

        if source.startswith("/*", pos):
            comment_end = source.find("*/", pos + 2)
            if comment_end == -1:
                return length
            pos = comment_end + 2
            continue

        break

    return pos


def skip_whitespace_and_comments_back(source: str, pos: int) -> int:
    pos -= 1

    while pos >= 0:
        if source[pos].isspace():
            pos -= 1
            continue

        if pos > 0 and source[pos - 1:pos + 1] == "*/":
            comment_start = source.rfind("/*", 0, pos - 1)
            if comment_start == -1:
                return pos
            pos = comment_start - 1
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
            elif char == "'":
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

        elif state == "block_comment":
            if char == "*" and next_char == "/":
                state = "normal"
                pos += 1

        pos += 1

    return None


def find_matching_open_paren(source: str, close_paren: int) -> int | None:
    depth = 0
    pos = close_paren
    state = "normal"

    while pos >= 0:
        char = source[pos]
        prev_char = source[pos - 1] if pos > 0 else ""

        if state == "normal":
            if char == '"':
                state = "string"
            elif char == "'":
                state = "char"
            elif char == ")":
                depth += 1
            elif char == "(":
                depth -= 1
                if depth == 0:
                    return pos
            elif char == "*" and prev_char == "/":
                state = "block_comment"
                pos -= 1

        elif state == "string":
            if char == '"' and prev_char != "\\":
                state = "normal"

        elif state == "char":
            if char == "'" and prev_char != "\\":
                state = "normal"

        elif state == "block_comment":
            if char == "/" and source[pos + 1:pos + 2] == "*":
                state = "normal"

        pos -= 1

    return None


def strip_comments(header: str) -> str:
    result: list[str] = []
    pos = 0
    state = "normal"

    while pos < len(header):
        char = header[pos]
        next_char = header[pos + 1] if pos + 1 < len(header) else ""

        if state == "normal":
            if char == "/" and next_char == "/":
                state = "line_comment"
                pos += 1
            elif char == "/" and next_char == "*":
                state = "block_comment"
                pos += 1
            else:
                result.append(char)
        elif state == "line_comment":
            if char == "\n":
                result.append(char)
                state = "normal"
        elif state == "block_comment":
            if char == "*" and next_char == "/":
                state = "normal"
                pos += 1

        pos += 1

    return "".join(result)


def first_nonblank_pos(source: str, start: int, end: int) -> int:
    pos = start
    while pos < end and source[pos].isspace():
        pos += 1
    return pos


def find_parameter_close(source: str, brace_pos: int) -> int | None:
    pos = skip_whitespace_and_comments_back(source, brace_pos)
    suffix_words = {"const", "volatile", "override", "final", "noexcept"}

    while pos >= 0:
        if source[pos] == ")":
            open_paren = find_matching_open_paren(source, pos)
            if open_paren is None:
                return None
            word_end = skip_whitespace_and_comments_back(source, open_paren) + 1
            word_match = re.search(
                r"([A-Za-z_][A-Za-z0-9_]*)\s*$",
                source[:word_end],
            )
            if word_match is not None and word_match.group(1) == "noexcept":
                pos = skip_whitespace_and_comments_back(source, word_match.start(1))
                continue
            return pos

        if source[pos].isalnum() or source[pos] == "_":
            word_end = pos + 1
            while pos >= 0 and (source[pos].isalnum() or source[pos] == "_"):
                pos -= 1
            word = source[pos + 1:word_end]
            if word in suffix_words:
                pos = skip_whitespace_and_comments_back(source, pos + 1)
                continue
            return None

        if source[pos] == "&":
            pos = skip_whitespace_and_comments_back(source, pos)
            continue

        return None

    return None


def find_function_name(source: str, header_start: int, open_paren: int) -> str | None:
    prefix = source[header_start:open_paren]
    name_match = re.search(r"([A-Za-z_~][A-Za-z0-9_]*)\s*$", prefix)
    if name_match is not None:
        return name_match.group(1)

    wrapper_end = skip_whitespace_and_comments_back(source, open_paren)
    if wrapper_end < 0 or source[wrapper_end] != ")":
        return None
    wrapper_open = find_matching_open_paren(source, wrapper_end)
    if wrapper_open is None:
        return None
    wrapped_name = re.search(
        r"([A-Za-z_~][A-Za-z0-9_]*)\s*$",
        source[wrapper_open + 1:wrapper_end],
    )
    return wrapped_name.group(1) if wrapped_name is not None else None


def parse_function_at_brace(source: str, brace_pos: int, header_start: int,
                            line_starts: list[int]) -> tuple[str, int, int] | None:
    close_paren = find_parameter_close(source, brace_pos)
    if close_paren is None:
        return None

    open_paren = find_matching_open_paren(source, close_paren)
    if open_paren is None:
        return None

    name = find_function_name(source, header_start, open_paren)
    if name is None:
        return None

    if name in {"if", "for", "while", "switch", "return", "sizeof", "catch"}:
        return None

    header = strip_comments(source[header_start:brace_pos])
    if ";" in header:
        return None

    function_start = first_nonblank_pos(source, header_start, open_paren)
    return name, function_start, line_number(line_starts, function_start)


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
            elif char == "'":
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

        elif state == "block_comment":
            if char == "*" and next_char == "/":
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
            elif char == "'":
                state = "char"
            elif char == "/" and next_char == "/":
                state = "line_comment"
                pos += 1
            elif char == "/" and next_char == "*":
                state = "block_comment"
                pos += 1
            elif char == "{":
                parsed = parse_function_at_brace(
                    source, pos, header_starts[depth], line_starts
                )
                if parsed is not None:
                    name, function_start, start_line = parsed
                    function_end = find_function_end(source, pos)
                    functions.append(FunctionEntry(
                        name, function_start, function_end, start_line
                    ))
                    # A regular C/C++ function cannot be defined inside another
                    # function. Skip its body so macro constructs such as
                    # ``QBUF_LIST_FOR_EACH(...) {`` are not parsed as functions.
                    header_starts[depth] = function_end
                    pos = function_end
                    continue
                depth += 1
                header_starts.append(pos + 1)
            elif char == "}":
                if depth > 0:
                    header_starts.pop()
                    depth -= 1
                    header_starts[depth] = pos + 1
            elif char == ";":
                header_starts[depth] = pos + 1

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

        elif state == "block_comment":
            if char == "*" and next_char == "/":
                state = "normal"
                pos += 1

        pos += 1

    return functions


def normalize_code(code: str) -> str:
    result: list[str] = []
    pos = 0
    state = "normal"
    pending_space = False

    while pos < len(code):
        char = code[pos]
        next_char = code[pos + 1] if pos + 1 < len(code) else ""

        if state == "normal":
            if char == '"':
                if pending_space and result:
                    result.append(" ")
                pending_space = False
                result.append(char)
                state = "string"
            elif char == "'":
                if pending_space and result:
                    result.append(" ")
                pending_space = False
                result.append(char)
                state = "char"
            elif char == "/" and next_char == "/":
                pending_space = True
                state = "line_comment"
                pos += 1
            elif char == "/" and next_char == "*":
                pending_space = True
                state = "block_comment"
                pos += 1
            elif char.isspace():
                pending_space = True
            else:
                if pending_space and result:
                    result.append(" ")
                pending_space = False
                result.append(char)

        elif state == "string":
            result.append(char)
            if char == "\\" and pos + 1 < len(code):
                pos += 1
                result.append(code[pos])
            elif char == '"':
                state = "normal"

        elif state == "char":
            result.append(char)
            if char == "\\" and pos + 1 < len(code):
                pos += 1
                result.append(code[pos])
            elif char == "'":
                state = "normal"

        elif state == "line_comment":
            if char == "\n":
                state = "normal"

        elif state == "block_comment":
            if char == "*" and next_char == "/":
                state = "normal"
                pos += 1

        pos += 1

    return "".join(result).strip()


def find_first_top_level_comma(code: str) -> int | None:
    paren_depth = 0
    bracket_depth = 0
    brace_depth = 0
    pos = 0
    state = "normal"

    while pos < len(code):
        char = code[pos]
        next_char = code[pos + 1] if pos + 1 < len(code) else ""

        if state == "normal":
            if char == '"':
                state = "string"
            elif char == "'":
                state = "char"
            elif char == "/" and next_char == "/":
                state = "line_comment"
                pos += 1
            elif char == "/" and next_char == "*":
                state = "block_comment"
                pos += 1
            elif char == "(":
                paren_depth += 1
            elif char == ")":
                paren_depth = max(0, paren_depth - 1)
            elif char == "[":
                bracket_depth += 1
            elif char == "]":
                bracket_depth = max(0, bracket_depth - 1)
            elif char == "{":
                brace_depth += 1
            elif char == "}":
                brace_depth = max(0, brace_depth - 1)
            elif (
                char == ","
                and paren_depth == 0
                and bracket_depth == 0
                and brace_depth == 0
            ):
                return pos

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

        elif state == "block_comment":
            if char == "*" and next_char == "/":
                state = "normal"
                pos += 1

        pos += 1

    return None


def normalize_log_content(source: str, open_paren: int, call_end: int) -> str:
    close_paren = call_end - 1
    while close_paren > open_paren and source[close_paren].isspace():
        close_paren -= 1
    if close_paren > open_paren and source[close_paren] == ";":
        close_paren -= 1
        while close_paren > open_paren and source[close_paren].isspace():
            close_paren -= 1

    arguments = source[open_paren + 1:close_paren]
    first_comma = find_first_top_level_comma(arguments)
    if first_comma is None:
        return ""
    return normalize_code(arguments[first_comma + 1:])


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
            elif char == "'":
                result[pos] = " "
                state = "char"
            elif char == "/" and next_char == "/":
                result[pos] = " "
                result[pos + 1] = " "
                pos += 1
                state = "line_comment"
            elif char == "/" and next_char == "*":
                result[pos] = " "
                result[pos + 1] = " "
                pos += 1
                state = "block_comment"

        elif state == "string":
            if char != "\n":
                result[pos] = " "
            if char == "\\" and pos + 1 < len(source):
                pos += 1
                if source[pos] != "\n":
                    result[pos] = " "
            elif char == '"':
                state = "normal"

        elif state == "char":
            if char != "\n":
                result[pos] = " "
            if char == "\\" and pos + 1 < len(source):
                pos += 1
                if source[pos] != "\n":
                    result[pos] = " "
            elif char == "'":
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
                pos += 1
                state = "normal"

        pos += 1

    return "".join(result)


def find_enclosing_block(source: str, start: int, pos: int) -> tuple[int, int]:
    block_stack: list[int] = []
    cursor = start
    state = "normal"

    while cursor < pos:
        char = source[cursor]
        next_char = source[cursor + 1] if cursor + 1 < len(source) else ""

        if state == "normal":
            if char == '"':
                state = "string"
            elif char == "'":
                state = "char"
            elif char == "/" and next_char == "/":
                state = "line_comment"
                cursor += 1
            elif char == "/" and next_char == "*":
                state = "block_comment"
                cursor += 1
            elif char == "{":
                block_stack.append(cursor)
            elif char == "}" and block_stack:
                block_stack.pop()

        elif state == "string":
            if char == "\\":
                cursor += 1
            elif char == '"':
                state = "normal"

        elif state == "char":
            if char == "\\":
                cursor += 1
            elif char == "'":
                state = "normal"

        elif state == "line_comment":
            if char == "\n":
                state = "normal"

        elif state == "block_comment":
            if char == "*" and next_char == "/":
                state = "normal"
                cursor += 1

        cursor += 1

    if not block_stack:
        return start, pos

    block_start = block_stack[-1]
    return block_start, find_function_end(source, block_start) - 1


def find_statement_end(source: str, start: int, limit: int) -> int | None:
    paren_depth = 0
    bracket_depth = 0
    brace_depth = 0
    pos = start
    state = "normal"

    while pos < limit:
        char = source[pos]
        next_char = source[pos + 1] if pos + 1 < len(source) else ""

        if state == "normal":
            if char == '"':
                state = "string"
            elif char == "'":
                state = "char"
            elif char == "/" and next_char == "/":
                state = "line_comment"
                pos += 1
            elif char == "/" and next_char == "*":
                state = "block_comment"
                pos += 1
            elif char == "(":
                paren_depth += 1
            elif char == ")":
                paren_depth = max(0, paren_depth - 1)
            elif char == "[":
                bracket_depth += 1
            elif char == "]":
                bracket_depth = max(0, bracket_depth - 1)
            elif char == "{":
                brace_depth += 1
            elif char == "}":
                if brace_depth == 0:
                    return None
                brace_depth -= 1
            elif char == ";" and paren_depth == 0 and bracket_depth == 0 and brace_depth == 0:
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

        elif state == "block_comment":
            if char == "*" and next_char == "/":
                state = "normal"
                pos += 1

        pos += 1

    return None


def starts_with_keyword(source: str, pos: int, keyword: str) -> bool:
    if not source.startswith(keyword, pos):
        return False
    before_ok = pos == 0 or not (source[pos - 1].isalnum() or source[pos - 1] == "_")
    end = pos + len(keyword)
    after_ok = end >= len(source) or not (source[end].isalnum() or source[end] == "_")
    return before_ok and after_ok


def parse_simple_assignment(statement: str) -> tuple[str, str] | None:
    normalized = normalize_code(statement)
    match = re.match(
        r"^(?:[A-Za-z_][A-Za-z0-9_]*\s+)*(?:\*+\s*)?"
        r"([A-Za-z_][A-Za-z0-9_]*)\s*=(?!=)\s*(.+);$",
        normalized,
    )
    if match is None:
        return None
    return match.group(1), match.group(2).strip()


def scan_linear_flow(source: str, start: int, limit: int) -> dict:
    assignments: list[dict] = []
    labels: list[dict] = []
    pos = start

    for _ in range(32):
        pos = skip_whitespace_and_comments(source, pos)
        if pos >= limit or source[pos] == "}":
            break

        if source[pos] == "#":
            newline = source.find("\n", pos)
            pos = limit if newline == -1 else newline + 1
            continue

        label_match = re.match(r"([A-Za-z_][A-Za-z0-9_]*)\s*:", source[pos:])
        if label_match is not None:
            labels.append({
                "name": label_match.group(1),
                "pos": pos,
            })
            pos += label_match.end()
            continue

        for keyword in ("return", "goto", "continue", "break"):
            if not starts_with_keyword(source, pos, keyword):
                continue
            statement_end = find_statement_end(source, pos, limit)
            if statement_end is None:
                return {
                    "assignments": assignments,
                    "labels": labels,
                    "control": None,
                    "ambiguous_pos": pos,
                }
            statement = normalize_code(source[pos:statement_end])
            expression = statement[len(keyword):].strip()
            if expression.endswith(";"):
                expression = expression[:-1].strip()
            return {
                "assignments": assignments,
                "labels": labels,
                "control": {
                    "kind": keyword,
                    "expression": expression or None,
                    "pos": pos,
                },
                "ambiguous_pos": None,
            }

        if any(
            starts_with_keyword(source, pos, keyword)
            for keyword in ("if", "else", "for", "while", "switch", "do", "case", "default")
        ) or source[pos] == "{":
            return {
                "assignments": assignments,
                "labels": labels,
                "control": None,
                "ambiguous_pos": pos,
            }

        statement_end = find_statement_end(source, pos, limit)
        if statement_end is None:
            return {
                "assignments": assignments,
                "labels": labels,
                "control": None,
                "ambiguous_pos": pos,
            }

        assignment = parse_simple_assignment(source[pos:statement_end])
        if assignment is not None:
            assignments.append({
                "target": assignment[0],
                "expression": assignment[1],
                "pos": pos,
            })
        pos = statement_end

    return {
        "assignments": assignments,
        "labels": labels,
        "control": None,
        "ambiguous_pos": pos,
    }


def find_label(source: str, function: FunctionEntry, label: str) -> tuple[int, int] | None:
    function_source = source[function.start:function.end]
    masked_source = mask_non_code(function_source)
    pattern = re.compile(rf"(?m)^[ \t]*{re.escape(label)}\s*:")
    match = pattern.search(masked_source)
    if match is None:
        return None
    colon = masked_source.find(":", match.start(), match.end())
    label_pos = function.start + match.start()
    return label_pos, function.start + colon + 1


def find_last_assignment(source: str, start: int, end: int, variable: str) -> dict | None:
    section = source[start:end]
    masked_section = mask_non_code(section)
    pattern = re.compile(
        rf"(?m)(?:^|[;{{}}])\s*"
        rf"(?:[A-Za-z_][A-Za-z0-9_]*\s+)*(?:\*+\s*)?"
        rf"{re.escape(variable)}\s*=(?!=)\s*([^;]+);"
    )
    matches = list(pattern.finditer(masked_section))
    if not matches:
        return None

    match = matches[-1]
    expression_start = start + match.start(1)
    expression_end = start + match.end(1)
    assignment_pos = start + match.start()
    while assignment_pos < end and source[assignment_pos] in ";{} \t\r\n":
        assignment_pos += 1
    return {
        "target": variable,
        "expression": normalize_code(source[expression_start:expression_end]),
        "pos": assignment_pos,
    }


def extract_error_symbols(expressions: list[str | None], known_symbols: set[str]) -> list[str]:
    symbols: list[str] = []
    for expression in expressions:
        if expression is None:
            continue
        for match in FALLBACK_ERROR_SYMBOL_PATTERN.finditer(expression):
            symbol = match.group(0)
            if known_symbols and symbol not in known_symbols:
                continue
            if symbol not in symbols:
                symbols.append(symbol)
    return symbols


def add_evidence(evidence: list[dict], item: dict) -> None:
    key = (
        item.get("kind"),
        item.get("line"),
        item.get("target"),
        item.get("expression"),
    )
    for current in evidence:
        current_key = (
            current.get("kind"),
            current.get("line"),
            current.get("target"),
            current.get("expression"),
        )
        if current_key == key:
            return
    evidence.append(item)


def analyze_error_flow(
    source: str,
    line_starts: list[int],
    function: FunctionEntry | None,
    log_pos: int,
    call_end: int,
    known_symbols: set[str],
) -> dict:
    evidence: list[dict] = []
    if function is None:
        return {
            "error_carrier": "unknown",
            "return_expression": None,
            "errno_expression": None,
            "error_symbols": [],
            "flow_kind": "unknown",
            "evidence": evidence,
            "confidence": "needs_skill",
        }

    block_start, block_end = find_enclosing_block(source, function.start, log_pos)
    errno_assignment = find_last_assignment(source, block_start + 1, log_pos, "errno")
    if errno_assignment is not None:
        masked_between = mask_non_code(source[errno_assignment["pos"]:log_pos])
        if "{" in masked_between or "}" in masked_between:
            errno_assignment = None
    first_flow = scan_linear_flow(source, call_end, block_end)
    assignments = list(first_flow["assignments"])
    control = first_flow["control"]
    used_goto = control is not None and control["kind"] == "goto"
    unresolved_flow = first_flow["ambiguous_pos"] is not None

    if used_goto:
        visited_labels: set[str] = set()
        for _ in range(8):
            if control is None or control["kind"] != "goto" or control["expression"] is None:
                break
            label = control["expression"]
            add_evidence(evidence, {
                "kind": "goto",
                "line": line_number(line_starts, control["pos"]),
                "target": label,
            })
            if label in visited_labels:
                unresolved_flow = True
                control = None
                break
            visited_labels.add(label)
            label_location = find_label(source, function, label)
            if label_location is None:
                unresolved_flow = True
                control = None
                break
            label_pos, label_end = label_location
            add_evidence(evidence, {
                "kind": "label",
                "line": line_number(line_starts, label_pos),
                "target": label,
            })
            next_flow = scan_linear_flow(source, label_end, function.end)
            assignments.extend(next_flow["assignments"])
            control = next_flow["control"]
            unresolved_flow = unresolved_flow or next_flow["ambiguous_pos"] is not None

    for assignment in assignments:
        if assignment["target"] == "errno":
            errno_assignment = assignment

    return_expression = None
    control_kind = control["kind"] if control is not None else None
    if control_kind == "return":
        return_expression = control["expression"]
        add_evidence(evidence, {
            "kind": "return",
            "line": line_number(line_starts, control["pos"]),
            "expression": return_expression,
        })
    elif control_kind in {"continue", "break"}:
        add_evidence(evidence, {
            "kind": control_kind,
            "line": line_number(line_starts, control["pos"]),
        })

    source_assignment = None
    source_assignment_scope = None
    if return_expression is not None and re.fullmatch(
        r"[A-Za-z_][A-Za-z0-9_]*", return_expression
    ):
        for assignment in reversed(assignments):
            if assignment["target"] == return_expression:
                source_assignment = assignment
                source_assignment_scope = "flow"
                break
        if source_assignment is None:
            source_assignment = find_last_assignment(
                source, block_start + 1, log_pos, return_expression
            )
            if source_assignment is not None:
                source_assignment_scope = "block"
        if source_assignment is None:
            source_assignment = find_last_assignment(
                source, function.start, log_pos, return_expression
            )
            if source_assignment is not None:
                source_assignment_scope = "function"
        if source_assignment is not None:
            add_evidence(evidence, {
                "kind": "assignment",
                "line": line_number(line_starts, source_assignment["pos"]),
                "target": source_assignment["target"],
                "expression": source_assignment["expression"],
            })

    if errno_assignment is not None:
        add_evidence(evidence, {
            "kind": "errno_assignment",
            "line": line_number(line_starts, errno_assignment["pos"]),
            "target": "errno",
            "expression": errno_assignment["expression"],
        })
    errno_expression = (
        errno_assignment["expression"] if errno_assignment is not None else None
    )

    source_expression = (
        source_assignment["expression"] if source_assignment is not None else None
    )
    error_symbols = extract_error_symbols(
        [return_expression, errno_expression, source_expression],
        known_symbols,
    )

    if control_kind == "return":
        if return_expression is None:
            error_carrier = "errno" if errno_expression is not None else "none"
        elif errno_expression is not None:
            error_carrier = "return_and_errno"
        else:
            error_carrier = "return"
    elif errno_expression is not None:
        error_carrier = "errno"
    elif control_kind in {"continue", "break"}:
        error_carrier = "none"
    else:
        error_carrier = "unknown"

    effective_expression = source_expression or return_expression
    if control_kind in {"continue", "break"} or (
        control_kind == "return" and return_expression is None
    ):
        flow_kind = "none"
    elif effective_expression is not None and re.search(
        r"\b[A-Za-z_][A-Za-z0-9_]*convert[A-Za-z0-9_]*\s*\(",
        effective_expression,
        re.IGNORECASE,
    ):
        flow_kind = "converted"
    elif return_expression in SENTINEL_EXPRESSIONS:
        flow_kind = "sentinel"
    elif used_goto and source_expression is not None:
        if extract_error_symbols([source_expression], known_symbols):
            flow_kind = "assigned_goto"
        else:
            flow_kind = "propagated"
    elif source_expression is not None:
        if extract_error_symbols([source_expression], known_symbols):
            flow_kind = "direct"
        else:
            flow_kind = "propagated"
    elif control_kind == "return":
        flow_kind = "direct"
    else:
        flow_kind = "unknown"

    direct_errno_symbol = bool(extract_error_symbols([errno_expression], known_symbols))
    direct_return_symbol = bool(extract_error_symbols([return_expression], known_symbols))
    source_symbol = bool(extract_error_symbols([source_expression], known_symbols))
    if flow_kind == "converted" or unresolved_flow or flow_kind == "unknown":
        confidence = "needs_skill"
    elif flow_kind == "propagated":
        confidence = "medium"
    elif (
        direct_errno_symbol
        or direct_return_symbol
        or (source_symbol and source_assignment_scope == "flow")
        or flow_kind in {"sentinel", "none"}
    ):
        confidence = "high"
    else:
        confidence = "medium"

    return {
        "error_carrier": error_carrier,
        "return_expression": return_expression,
        "errno_expression": errno_expression,
        "error_symbols": error_symbols,
        "flow_kind": flow_kind,
        "evidence": sorted(evidence, key=lambda item: item["line"]),
        "confidence": confidence,
    }


def simplify_error_flow(error_flow: dict) -> dict:
    carrier = error_flow["error_carrier"]
    if carrier in {"errno", "return_and_errno"}:
        error_source = "errno"
    elif carrier in {"return", "none", "unknown"}:
        error_source = carrier
    else:
        error_source = "unknown"

    error_expression = None
    if error_source == "errno":
        error_expression = error_flow["errno_expression"]
    elif error_source == "return":
        return_expression = error_flow["return_expression"]
        if return_expression is not None and re.fullmatch(
            r"[A-Za-z_][A-Za-z0-9_]*", return_expression
        ):
            for item in error_flow["evidence"]:
                expression = item.get("expression")
                if (
                    item.get("kind") != "assignment"
                    or item.get("target") != return_expression
                    or expression is None
                ):
                    continue
                assignment_symbols = extract_error_symbols(
                    [expression], set(ERROR_DEFINITIONS)
                )
                if (
                    assignment_symbols
                    or expression in {"0", "-1"}
                    or error_flow["flow_kind"] in {"assigned_goto", "converted"}
                ):
                    error_expression = expression
                    break
        if error_expression is None:
            error_expression = return_expression

    reportable_symbols = [
        symbol for symbol in extract_error_symbols(
            [error_expression], set(ERROR_DEFINITIONS)
        )
        if (
            symbol.startswith("UMQ_ERR_")
            or symbol in {"UMQ_FAIL", "UMQ_INVALID_HANDLE", "UMQ_INVALID_FD"}
        )
    ]
    is_high_confidence = error_flow["confidence"] == "high"
    error_code = (
        reportable_symbols[0]
        if is_high_confidence and len(reportable_symbols) == 1
        else None
    )
    if (
        error_code is None
        and is_high_confidence
        and error_expression in {"0", "-1"}
    ):
        error_code = int(error_expression)

    needs_skill = (
        not is_high_confidence
        or error_source == "unknown"
        or len(reportable_symbols) > 1
        or (
            error_source == "errno"
            and error_expression is not None
            and not reportable_symbols
            and error_expression not in {"0", "-1"}
        )
    )
    return {
        "error_code": error_code,
        "error_source": error_source,
        "error_expression": error_expression,
        "needs_skill": needs_skill,
    }


def find_containing_function(functions: list[FunctionEntry], pos: int) -> FunctionEntry | None:
    containing = [
        function for function in functions
        if function.start <= pos < function.end
    ]
    if not containing:
        return None
    return max(containing, key=lambda function: function.start)


def find_macro_context(source: str, line_starts: list[int], pos: int) -> tuple[str, int] | None:
    line_index = line_number(line_starts, pos) - 1
    start_index = line_index

    while start_index > 0:
        previous_start = line_starts[start_index - 1]
        previous_end = line_starts[start_index]
        previous_line = source[previous_start:previous_end].rstrip()
        if not previous_line.endswith("\\"):
            break
        start_index -= 1

    line_start = line_starts[start_index]
    line_end = line_starts[start_index + 1] if start_index + 1 < len(line_starts) else len(source)
    first_line = source[line_start:line_end]
    match = re.match(r"\s*#\s*define\s+([A-Za-z_][A-Za-z0-9_]*)", first_line)
    if match is None:
        return None

    return f"#define {match.group(1)}", start_index + 1


def find_log_entries(
    file_path: Path,
    root: Path,
    known_symbols: set[str],
) -> list[LogEntry]:
    try:
        source = file_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        print(f"警告：无法读取 {file_path}: {exc}", file=sys.stderr)
        return []

    entries: list[LogEntry] = []
    line_starts = build_line_starts(source)
    functions = find_functions(source)
    macro_pattern = "|".join(re.escape(macro) for macro in LOG_MACROS)
    pattern = re.compile(
        rf"(?<![A-Za-z0-9_])(?P<macro>{macro_pattern})(?![A-Za-z0-9_])"
    )

    for match in pattern.finditer(source):
        log_pos = match.start()
        log_line = line_number(line_starts, log_pos)
        macro = match.group("macro")
        pos = skip_whitespace_and_comments(source, match.end())
        if pos >= len(source) or source[pos] != "(":
            continue

        call_end = find_call_end(source, pos)
        if call_end is None:
            print(f"警告：{file_path}:{log_line} 的 {macro} 括号不完整",
                  file=sys.stderr)
            continue

        statement_end = skip_whitespace_and_comments(source, call_end)
        if statement_end < len(source) and source[statement_end] == ";":
            call_end = statement_end + 1

        function = find_containing_function(functions, log_pos)
        macro_context = (
            None if function is not None
            else find_macro_context(source, line_starts, log_pos)
        )
        error_flow = analyze_error_flow(
            source,
            line_starts,
            function,
            log_pos,
            call_end,
            known_symbols,
        )
        simple_error = simplify_error_flow(error_flow)
        is_warn = macro in WARN_LOG_MACROS
        if is_warn and not isinstance(simple_error["error_code"], str):
            continue

        try:
            display_path = file_path.relative_to(root)
        except ValueError:
            display_path = file_path

        entries.append(LogEntry(
            file=display_path,
            log_macro=macro,
            function=(
                function.name if function is not None
                else macro_context[0] if macro_context is not None
                else "<global>"
            ),
            function_start_line=(
                function.start_line if function is not None
                else macro_context[1] if macro_context is not None
                else 0
            ),
            log_line=log_line,
            log_content=normalize_log_content(source, pos, call_end),
            error_code=simple_error["error_code"],
            error_source=simple_error["error_source"],
            error_expression=simple_error["error_expression"],
            needs_skill=False if is_warn else simple_error["needs_skill"],
        ))

    return entries


def is_excluded(file_path: Path, root: Path) -> bool:
    try:
        relative_path = file_path.relative_to(root).as_posix()
    except ValueError:
        return False
    return (
        relative_path == EXCLUDED_FILE
        or relative_path.endswith(f"/{EXCLUDED_FILE}")
    )


def collect_logs(root: Path, known_symbols: set[str]) -> list[LogEntry]:
    entries: list[LogEntry] = []
    for file_path in sorted(root.rglob("*")):
        if (
            file_path.is_file()
            and file_path.suffix.lower() in SOURCE_SUFFIXES
            and not is_excluded(file_path, root)
        ):
            entries.extend(find_log_entries(file_path, root, known_symbols))
    return entries


def build_json_result(
    entries: list[LogEntry],
    error_definitions: dict[str, int],
) -> dict:
    return {
        "log_macros": LOG_MACROS,
        "error_definitions": error_definitions,
        "total": len(entries),
        "entries": [
            {
                "file": str(entry.file),
                "log_macro": entry.log_macro,
                "function": entry.function,
                "function_start_line": entry.function_start_line,
                "log_line": entry.log_line,
                "log_content": entry.log_content,
                "error_code": entry.error_code,
                "error_source": entry.error_source,
                "error_expression": entry.error_expression,
                "needs_skill": entry.needs_skill,
            }
            for entry in entries
        ],
    }


def dump_json(
    entries: list[LogEntry],
    error_definitions: dict[str, int],
    output_file: Path | None = None,
) -> None:
    result = build_json_result(entries, error_definitions)
    if output_file is None:
        json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
        print()
        return

    with output_file.open("w", encoding="utf-8") as file:
        json.dump(result, file, ensure_ascii=False, indent=2)
        file.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "递归查询 C/C++ 文件中的 UMQ_VLOG_ERR、UMQ_LIMIT_VLOG_ERR、"
            "以及能够明确错误码的 UMQ_VLOG_WARN，"
            f"并将源码文件及所在函数信息写入 {OUTPUT_FILE}。"
        )
    )
    parser.add_argument(
        "source",
        type=Path,
        help="UMQ的源码目录",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT_FILE,
        help=f"JSON输出路径，默认：{OUTPUT_FILE}",
    )
    args = parser.parse_args()

    root = args.source.expanduser().resolve()
    if not root.exists():
        parser.error(f"目录不存在：{root}")
    if not root.is_dir():
        parser.error(f"指定路径不是目录：{root}")

    known_symbols = set(ERROR_DEFINITIONS)

    entries = collect_logs(root, known_symbols)
    output_file = args.output.expanduser().resolve()
    try:
        dump_json(entries, ERROR_DEFINITIONS, output_file)
    except OSError as exc:
        print(f"错误：无法写入 {output_file}: {exc}", file=sys.stderr)
        return 1
    print(f"共找到 {len(entries)} 条日志，JSON 结果已写入：{output_file}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
