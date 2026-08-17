#!/usr/bin/env python3

import argparse
import json
import re
import signal
import sys
from bisect import bisect_right
from dataclasses import dataclass
from pathlib import Path


LOG_FUNCTION = "URMA_LOG_ERR"
CHECK_MACROS = [
    "URMA_CHECK_CTX_INVALID_RETURN_STATUS",
    "URMA_CHECK_OP_INVALID_RETURN_POINTER",
    "URMA_CHECK_OP_INVALID_RETURN_STATUS",
    "URMA_CHECK_OP_INVALID_RETURN_NEG_STATUS",
]
SEARCH_SYMBOLS = [LOG_FUNCTION, *CHECK_MACROS]
CHECK_MACRO_LOG_CONTENT = '"Invalid parameter.\\n"'
OUTPUT_FILE = Path("/tmp/urma_log_err.json")
URMA_CP_API_EXCLUDE_LINES = 60
RETURN_SENTINELS = {"NULL", "nullptr", "0", "-1"}
ERROR_DEFINITIONS = {
    "URMA_SUCCESS": 0,
    "URMA_EAGAIN": 11,
    "URMA_ENOMEM": 12,
    "URMA_ENOPERM": 1,
    "URMA_ETIMEOUT": 110,
    "URMA_EINVAL": 22,
    "URMA_EEXIST": 17,
    "URMA_EINPROGRESS": 115,
    "URMA_FAIL": 0x1000,
}
ERRNO_TO_URMA = {
    "EAGAIN": "URMA_EAGAIN",
    "ENOMEM": "URMA_ENOMEM",
    "EPERM": "URMA_ENOPERM",
    "ETIMEDOUT": "URMA_ETIMEOUT",
    "EINVAL": "URMA_EINVAL",
    "EEXIST": "URMA_EEXIST",
    "EINPROGRESS": "URMA_EINPROGRESS",
}
CHECK_MACRO_RESULTS = {
    "URMA_CHECK_CTX_INVALID_RETURN_STATUS": (
        "URMA_EINVAL", "return", "URMA_EINVAL"
    ),
    "URMA_CHECK_OP_INVALID_RETURN_POINTER": (
        "URMA_EINVAL", "errno", "EINVAL"
    ),
    "URMA_CHECK_OP_INVALID_RETURN_STATUS": (
        "URMA_EINVAL", "return", "URMA_EINVAL"
    ),
    "URMA_CHECK_OP_INVALID_RETURN_NEG_STATUS": (
        "URMA_EINVAL", "return", "-URMA_EINVAL"
    ),
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


def parse_function_at_brace(source: str, brace_pos: int, header_start: int,
                            line_starts: list[int]) -> tuple[str, int, int] | None:
    before_brace = skip_whitespace_and_comments_back(source, brace_pos)
    if before_brace < 0 or source[before_brace] != ")":
        return None

    open_paren = find_matching_open_paren(source, before_brace)
    if open_paren is None:
        return None

    name_match = re.search(r"([A-Za-z_][A-Za-z0-9_]*)\s*$", source[header_start:open_paren])
    if name_match is None:
        return None

    name = name_match.group(1)
    if name in {"if", "for", "while", "switch", "return", "sizeof"}:
        return None

    header = strip_comments(source[header_start:brace_pos])
    if ";" in header or "=" in header:
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
    header_start = 0
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
                if depth == 0:
                    parsed = parse_function_at_brace(source, pos, header_start, line_starts)
                    if parsed is not None:
                        name, function_start, start_line = parsed
                        end = find_function_end(source, pos)
                        functions.append(FunctionEntry(name, function_start, end, start_line))
                depth += 1
            elif char == "}":
                depth = max(0, depth - 1)
                if depth == 0:
                    header_start = pos + 1
            elif char == ";" and depth == 0:
                header_start = pos + 1

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


def normalize_log_content(source: str, open_paren: int, call_end: int) -> str:
    close_paren = call_end - 1
    while close_paren > open_paren and source[close_paren].isspace():
        close_paren -= 1
    if close_paren > open_paren and source[close_paren] == ";":
        close_paren -= 1
        while close_paren > open_paren and source[close_paren].isspace():
            close_paren -= 1

    return normalize_code(source[open_paren + 1:close_paren])


def mask_non_code(source: str) -> str:
    """Replace comments and literals with spaces while preserving offsets."""
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
                result[pos] = result[pos + 1] = " "
                pos += 1
                state = "line_comment"
            elif char == "/" and next_char == "*":
                result[pos] = result[pos + 1] = " "
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
        elif state == "block_comment" and char == "*" and next_char == "/":
            state = "normal"
            cursor += 1
        cursor += 1

    if not block_stack:
        return start, pos
    block_start = block_stack[-1]
    return block_start, find_function_end(source, block_start) - 1


def find_statement_end(source: str, start: int, limit: int) -> int | None:
    paren_depth = bracket_depth = brace_depth = 0
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
            elif char == ";" and not (paren_depth or bracket_depth or brace_depth):
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
            pos += label_match.end()
            continue

        for keyword in ("return", "goto", "continue", "break"):
            if not starts_with_keyword(source, pos, keyword):
                continue
            statement_end = find_statement_end(source, pos, limit)
            if statement_end is None:
                return {"assignments": assignments, "control": None,
                        "ambiguous_pos": pos}
            statement = normalize_code(source[pos:statement_end])
            expression = statement[len(keyword):].strip()
            if expression.endswith(";"):
                expression = expression[:-1].strip()
            return {
                "assignments": assignments,
                "control": {"kind": keyword, "expression": expression or None,
                            "pos": pos},
                "ambiguous_pos": None,
            }

        if any(starts_with_keyword(source, pos, keyword) for keyword in (
            "if", "else", "for", "while", "switch", "do", "case", "default"
        )) or source[pos] == "{":
            return {"assignments": assignments, "control": None,
                    "ambiguous_pos": pos}

        statement_end = find_statement_end(source, pos, limit)
        if statement_end is None:
            return {"assignments": assignments, "control": None,
                    "ambiguous_pos": pos}
        assignment = parse_simple_assignment(source[pos:statement_end])
        if assignment is not None:
            assignments.append({"target": assignment[0],
                                "expression": assignment[1], "pos": pos})
        pos = statement_end

    return {"assignments": assignments, "control": None, "ambiguous_pos": pos}


def find_label(source: str, function: FunctionEntry, label: str) -> tuple[int, int] | None:
    masked_source = mask_non_code(source[function.start:function.end])
    match = re.search(rf"(?m)^[ \t]*{re.escape(label)}\s*:", masked_source)
    if match is None:
        return None
    colon = masked_source.find(":", match.start(), match.end())
    return function.start + match.start(), function.start + colon + 1


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


def add_evidence(evidence: list[dict], item: dict) -> None:
    key = tuple(item.get(field) for field in ("kind", "line", "target", "expression"))
    if any(tuple(current.get(field) for field in
                 ("kind", "line", "target", "expression")) == key
           for current in evidence):
        return
    evidence.append(item)


def expression_identifier(expression: str | None) -> str | None:
    if expression is None:
        return None
    match = re.fullmatch(
        r"(?:\([A-Za-z_][A-Za-z0-9_ \t*]*\)\s*)*[+-]?"
        r"([A-Za-z_][A-Za-z0-9_]*)",
        expression,
    )
    return match.group(1) if match is not None else None


def map_error_symbol(symbol: str) -> str | None:
    if symbol in ERROR_DEFINITIONS:
        return symbol
    return ERRNO_TO_URMA.get(symbol)


def strip_outer_parentheses(expression: str) -> str:
    result = expression.strip()
    while result.startswith("(") and result.endswith(")"):
        depth = 0
        closes_at_end = False
        for pos, char in enumerate(result):
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth == 0:
                    closes_at_end = pos == len(result) - 1
                    break
        if not closes_at_end:
            break
        result = result[1:-1].strip()
    return result


def mapped_error_codes(expression: str | None) -> list[str]:
    if expression is None:
        return []
    direct_expression = strip_outer_parentheses(expression)
    match = re.fullmatch(
        r"(?:\([A-Za-z_][A-Za-z0-9_ \t*]*\)\s*)*[+-]?\s*"
        r"([A-Za-z_][A-Za-z0-9_]*)",
        direct_expression,
    )
    if match is None:
        return []
    error_code = map_error_symbol(match.group(1))
    return [error_code] if error_code is not None else []


def resolve_assigned_expression(
    source: str,
    line_starts: list[int],
    function: FunctionEntry,
    block_start: int,
    before_pos: int,
    expression: str | None,
    evidence: list[dict],
) -> str | None:
    """Resolve a short chain such as errno = ret; ret = -EINVAL."""
    resolved = expression
    visited: set[str] = set()
    for _ in range(4):
        variable = expression_identifier(resolved)
        if variable is None or variable in visited:
            break
        visited.add(variable)
        assignment = find_last_assignment(
            source, block_start + 1, before_pos, variable
        )
        if assignment is None:
            assignment = find_last_assignment(
                source, function.start, before_pos, variable
            )
        if assignment is None:
            break
        add_evidence(evidence, {
            "kind": "assignment",
            "line": line_number(line_starts, assignment["pos"]),
            "target": assignment["target"],
            "expression": assignment["expression"],
        })
        resolved = assignment["expression"]
        before_pos = assignment["pos"]
    return resolved


def analyze_error_flow(source: str, line_starts: list[int],
                       function: FunctionEntry | None, log_pos: int,
                       call_end: int) -> dict:
    evidence: list[dict] = []
    if function is None:
        return {
            "error_source": "unknown", "return_expression": None,
            "errno_expression": None, "resolved_expression": None,
            "flow_kind": "unknown", "confidence": "needs_skill",
            "evidence": evidence,
        }

    block_start, block_end = find_enclosing_block(source, function.start, log_pos)
    errno_assignment = find_last_assignment(source, block_start + 1, log_pos, "errno")
    if errno_assignment is not None:
        masked_between = mask_non_code(source[errno_assignment["pos"]:log_pos])
        if "{" in masked_between or "}" in masked_between:
            errno_assignment = None

    flow = scan_linear_flow(source, call_end, block_end)
    assignments = list(flow["assignments"])
    control = flow["control"]
    used_goto = control is not None and control["kind"] == "goto"
    unresolved_flow = flow["ambiguous_pos"] is not None

    if used_goto:
        visited_labels: set[str] = set()
        for _ in range(8):
            if control is None or control["kind"] != "goto" or control["expression"] is None:
                break
            label = control["expression"]
            add_evidence(evidence, {"kind": "goto",
                         "line": line_number(line_starts, control["pos"]),
                         "target": label})
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
            add_evidence(evidence, {"kind": "label",
                         "line": line_number(line_starts, label_pos),
                         "target": label})
            next_flow = scan_linear_flow(source, label_end, function.end)
            assignments.extend(next_flow["assignments"])
            control = next_flow["control"]
            unresolved_flow = unresolved_flow or next_flow["ambiguous_pos"] is not None

    for assignment in assignments:
        if assignment["target"] == "errno":
            errno_assignment = assignment

    control_kind = control["kind"] if control is not None else None
    return_expression = control["expression"] if control_kind == "return" else None
    if control_kind is not None:
        item = {"kind": control_kind, "line": line_number(line_starts, control["pos"])}
        if return_expression is not None:
            item["expression"] = return_expression
        add_evidence(evidence, item)

    errno_expression = errno_assignment["expression"] if errno_assignment is not None else None
    if errno_assignment is not None:
        add_evidence(evidence, {
            "kind": "errno_assignment",
            "line": line_number(line_starts, errno_assignment["pos"]),
            "target": "errno", "expression": errno_expression,
        })

    if errno_expression is not None:
        error_source = "errno"
        resolved_expression = resolve_assigned_expression(
            source, line_starts, function, block_start,
            errno_assignment["pos"], errno_expression, evidence
        )
    elif control_kind in {"continue", "break"} or (
        control_kind == "return" and return_expression is None
    ):
        error_source = "none"
        resolved_expression = None
    elif control_kind == "return":
        error_source = "return"
        resolved_expression = resolve_assigned_expression(
            source, line_starts, function, block_start,
            control["pos"], return_expression, evidence
        )
    else:
        error_source = "unknown"
        resolved_expression = None

    if error_source == "none":
        flow_kind = "none"
    elif error_source == "return" and return_expression in RETURN_SENTINELS:
        flow_kind = "sentinel"
    elif resolved_expression is not None and mapped_error_codes(resolved_expression):
        flow_kind = "assigned_goto" if used_goto else "direct"
    elif resolved_expression != return_expression:
        flow_kind = "propagated"
    elif control_kind == "return":
        flow_kind = "direct"
    else:
        flow_kind = "unknown"

    if unresolved_flow or error_source == "unknown":
        confidence = "needs_skill"
    elif mapped_error_codes(resolved_expression) or flow_kind in {"sentinel", "none"}:
        confidence = "high"
    elif flow_kind == "propagated":
        confidence = "medium"
    else:
        confidence = "needs_skill"

    return {
        "error_source": error_source,
        "return_expression": return_expression,
        "errno_expression": errno_expression,
        "resolved_expression": resolved_expression,
        "flow_kind": flow_kind,
        "confidence": confidence,
        "evidence": sorted(evidence, key=lambda item: item["line"]),
    }


def simplify_error_flow(error_flow: dict) -> dict:
    error_source = error_flow["error_source"]
    error_expression = error_flow["resolved_expression"]
    mapped_codes = mapped_error_codes(error_expression)
    error_code: str | int | None = None

    if error_flow["confidence"] == "high" and len(mapped_codes) == 1:
        error_code = mapped_codes[0]
    elif (
        error_flow["confidence"] == "high"
        and error_source == "return"
        and error_expression in {"NULL", "nullptr"}
    ):
        error_code = error_expression
    elif (
        error_flow["confidence"] == "high"
        and error_source == "return"
        and error_expression in {"0", "-1"}
    ):
        error_code = int(error_expression)

    # An unambiguous URMA mapping, explicit null return, or path without an
    # error carrier is complete. Bare numeric sentinels and dynamic propagated
    # statuses still need review.
    needs_skill = not (
        error_code in ERROR_DEFINITIONS
        or error_code in {"NULL", "nullptr"}
        or error_source == "none"
    )
    return {
        "error_code": error_code,
        "error_source": error_source,
        "error_expression": error_expression,
        "needs_skill": needs_skill,
    }


def find_containing_function(functions: list[FunctionEntry], pos: int) -> FunctionEntry | None:
    for function in functions:
        if function.start <= pos < function.end:
            return function
    return None


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


def find_log_entries(file_path: Path, root: Path) -> list[LogEntry]:
    try:
        source = file_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        print(f"警告：无法读取 {file_path}: {exc}", file=sys.stderr)
        return []

    entries: list[LogEntry] = []
    line_starts = build_line_starts(source)
    functions = find_functions(source)
    masked_source = mask_non_code(source)
    symbol_pattern = "|".join(re.escape(symbol) for symbol in SEARCH_SYMBOLS)
    pattern = re.compile(rf"(?<![A-Za-z0-9_])(?P<symbol>{symbol_pattern})(?![A-Za-z0-9_])")

    for match in pattern.finditer(masked_source):
        log_pos = match.start()
        log_line = line_number(line_starts, log_pos)
        symbol = match.group("symbol")
        if file_path.name == "urma_cp_api.c" and log_line <= URMA_CP_API_EXCLUDE_LINES:
            continue

        pos = skip_whitespace_and_comments(source, match.end())
        if pos >= len(source) or source[pos] != "(":
            continue

        call_end = find_call_end(source, pos)
        if call_end is None:
            print(f"警告：{file_path}:{log_line} 的 {symbol} 括号不完整",
                  file=sys.stderr)
            continue

        statement_end = skip_whitespace_and_comments(source, call_end)
        if statement_end < len(source) and source[statement_end] == ";":
            call_end = statement_end + 1

        function = find_containing_function(functions, log_pos)
        macro = None if function is not None else find_macro_context(source, line_starts, log_pos)
        if symbol in CHECK_MACRO_RESULTS:
            error_code, error_source, error_expression = CHECK_MACRO_RESULTS[symbol]
            simple_error = {
                "error_code": error_code,
                "error_source": error_source,
                "error_expression": error_expression,
                "needs_skill": False,
            }
        else:
            simple_error = simplify_error_flow(analyze_error_flow(
                source, line_starts, function, log_pos, call_end
            ))
        try:
            display_path = file_path.relative_to(root)
        except ValueError:
            display_path = file_path

        entries.append(LogEntry(
            file=display_path,
            function=function.name if function is not None else (macro[0] if macro is not None else "<global>"),
            function_start_line=(
                function.start_line if function is not None
                else macro[1] if macro is not None else 0
            ),
            log_line=log_line,
            log_content=(
                CHECK_MACRO_LOG_CONTENT if symbol in CHECK_MACROS
                else normalize_log_content(source, pos, call_end)
            ),
            error_code=simple_error["error_code"],
            error_source=simple_error["error_source"],
            error_expression=simple_error["error_expression"],
            needs_skill=simple_error["needs_skill"],
        ))

    return entries


def collect_logs(root: Path) -> list[LogEntry]:
    entries: list[LogEntry] = []
    for file_path in sorted(root.rglob("*.c")):
        if file_path.is_file():
            entries.extend(find_log_entries(file_path, root))
    return entries


def build_json_result(entries: list[LogEntry]) -> dict:
    return {
        "log_macro": LOG_FUNCTION,
        "search_symbols": SEARCH_SYMBOLS,
        "error_definitions": ERROR_DEFINITIONS,
        "return_sentinels": sorted(RETURN_SENTINELS),
        "total": len(entries),
        "entries": [
            {
                "file": str(entry.file),
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


def dump_json(entries: list[LogEntry], output_file: Path | None = None) -> None:
    result = build_json_result(entries)
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
            f"递归查询 .c 文件中的 {LOG_FUNCTION} 和参数检查宏，"
            f"提取源码文件、函数返回值或 errno，并写入 {OUTPUT_FILE}。"
        )
    )
    parser.add_argument("directory", type=Path, help="要扫描的目录")
    parser.add_argument(
        "-o", "--output", type=Path, default=OUTPUT_FILE,
        help=f"将结果写入 JSON 文件，默认：{OUTPUT_FILE}",
    )
    args = parser.parse_args()

    root = args.directory.expanduser().resolve()
    if not root.exists():
        parser.error(f"目录不存在：{root}")
    if not root.is_dir():
        parser.error(f"指定路径不是目录：{root}")

    entries = collect_logs(root)
    output_file = args.output.expanduser().resolve()
    try:
        dump_json(entries, output_file)
    except OSError as exc:
        print(f"错误：无法写入 {output_file}: {exc}", file=sys.stderr)
        return 1
    print(f"共找到 {len(entries)} 条日志，JSON 结果已写入：{output_file}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
