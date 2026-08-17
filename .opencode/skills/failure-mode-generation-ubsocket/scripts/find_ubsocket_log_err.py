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
    "UBS_VLOG_ERR",
    "UBS_SLOG_ERR",
]
OUTPUT_FILE = Path("/tmp/ubsocket_log_err.json")
SOURCE_SUFFIXES = {".c", ".h", ".cpp", ".hpp"}
EXCLUDED_FILE = "common/ubsocket_logger.h"
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
                    functions.append(FunctionEntry(
                        name, function_start, find_function_end(source, pos), start_line
                    ))
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


def normalize_log_content(source: str, open_paren: int, call_end: int) -> str:
    close_paren = call_end - 1
    while close_paren > open_paren and source[close_paren].isspace():
        close_paren -= 1
    if close_paren > open_paren and source[close_paren] == ";":
        close_paren -= 1
        while close_paren > open_paren and source[close_paren].isspace():
            close_paren -= 1

    return normalize_code(source[open_paren + 1:close_paren])


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


def find_log_entries(file_path: Path, root: Path) -> list[LogEntry]:
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
        try:
            display_path = file_path.relative_to(root)
        except ValueError:
            display_path = file_path

        entries.append(LogEntry(
            file=display_path,
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


def collect_logs(root: Path) -> list[LogEntry]:
    entries: list[LogEntry] = []
    for file_path in sorted(root.rglob("*")):
        if (
            file_path.is_file()
            and file_path.suffix.lower() in SOURCE_SUFFIXES
            and not is_excluded(file_path, root)
        ):
            entries.extend(find_log_entries(file_path, root))
    return entries


def build_json_result(entries: list[LogEntry]) -> dict:
    return {
        "log_macros": LOG_MACROS,
        "total": len(entries),
        "entries": [
            {
                "file": str(entry.file),
                "function": entry.function,
                "function_start_line": entry.function_start_line,
                "log_line": entry.log_line,
                "log_content": entry.log_content,
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
            "递归查询 C/C++ 文件中的 UBS_VLOG_ERR 和 UBS_SLOG_ERR，"
            f"并将源码文件及所在函数信息写入 {OUTPUT_FILE}。"
        )
    )
    parser.add_argument(
        "source",
        type=Path,
        help="UBSocket的csrc源码目录，例如/root/openeuler/ubs-comm/src/ubsocket/csrc",
    )
    args = parser.parse_args()

    root = args.source.expanduser().resolve()
    if not root.exists():
        parser.error(f"目录不存在：{root}")
    if not root.is_dir():
        parser.error(f"指定路径不是目录：{root}")

    entries = collect_logs(root)
    try:
        dump_json(entries, OUTPUT_FILE)
    except OSError as exc:
        print(f"错误：无法写入 {OUTPUT_FILE}: {exc}", file=sys.stderr)
        return 1
    print(f"共找到 {len(entries)} 条日志，JSON 结果已写入：{OUTPUT_FILE}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
