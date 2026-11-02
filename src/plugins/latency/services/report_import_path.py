"""Bounded snapshots of operator-entered files under deployment-owned import roots."""
from __future__ import annotations

import json
import os
import stat
import tempfile
from contextlib import contextmanager
from pathlib import Path
from collections.abc import Iterator

from latency.services.report_import import (
    MAX_BATCH_BYTES, MAX_ITEM_BYTES, ImportSourceError, collect_json_entries,
)

IMPORT_ROOTS_ENV = "WITTY_REPORT_IMPORT_ROOTS"


def allowed_import_roots() -> list[Path]:
    roots: list[Path] = []
    for raw in os.environ.get(IMPORT_ROOTS_ENV, "").split(os.pathsep):
        if not raw.strip():
            continue
        path = Path(raw.strip())
        if not path.is_absolute() or ".." in path.parts or path == Path(path.anchor):
            raise ImportSourceError("import_root_invalid", "导入根目录必须为明确的绝对目录，不能是文件系统根目录")
        try:
            resolved = path.resolve(strict=True)
        except (OSError, RuntimeError) as exc:
            raise ImportSourceError("import_root_unavailable", "配置的导入目录不可访问") from exc
        if not resolved.is_dir() or resolved == Path(resolved.anchor):
            raise ImportSourceError("import_root_invalid", "配置的导入根路径不是目录")
        if resolved not in roots:
            roots.append(resolved)
    return roots


def _validate_content(path: Path) -> None:
    for entry in collect_json_entries(path):
        try:
            payload = json.loads(entry.data.decode("utf-8"), parse_constant=_reject_constant)
        except (UnicodeDecodeError, ValueError) as exc:
            raise ImportSourceError("invalid_json", entry.name) from exc
        if not isinstance(payload, dict) or not isinstance(payload.get("report"), dict):
            raise ImportSourceError("invalid_report", f"{entry.name}: 缺少 report 对象")
        faults = payload.get("faults")
        if faults is not None:
            if not isinstance(faults, list) or not faults:
                raise ImportSourceError("invalid_report", f"{entry.name}: faults 必须为非空数组")
            conclusions = [fault.get("conclusion") if isinstance(fault, dict) else None for fault in faults]
        else:
            conclusions = [payload.get("conclusion")]
        if any(not isinstance(value, dict) for value in conclusions):
            raise ImportSourceError("invalid_report", f"{entry.name}: 缺少故障结论对象")
        if any(not isinstance(value.get("one_line_conclusion"), str)
               or not value["one_line_conclusion"].strip() for value in conclusions):
            raise ImportSourceError("invalid_report", f"{entry.name}: 缺少非空的定界结论文本")


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON value: {value}")


@contextmanager
def snapshot_import_path(raw: str) -> Iterator[Path]:
    """Never follow a user-controlled symlink, including intermediate directories."""
    roots = allowed_import_roots()
    if not roots:
        raise ImportSourceError("path_import_disabled", "尚未配置服务器导入目录，请使用文件上传")
    if not raw or raw != raw.strip() or any(ord(char) < 32 for char in raw):
        raise ImportSourceError("source_path_invalid", "请输入完整的服务器绝对文件路径")
    source = Path(raw)
    if not source.is_absolute() or ".." in source.parts:
        raise ImportSourceError("source_path_invalid", "不支持相对路径或父目录跳转")
    relative = None
    root = None
    for candidate in roots:
        if source.is_relative_to(candidate) and source != candidate:
            root, relative = candidate, source.relative_to(candidate)
            break
    if root is None or relative is None:
        raise ImportSourceError("source_outside_import_roots", "文件必须位于配置的导入目录内")
    suffix = source.suffix.lower()
    if suffix not in {".json", ".zip"}:
        raise ImportSourceError("source_unsupported", "仅支持 JSON 或 ZIP 文件，不支持目录")
    if not hasattr(os, "O_NOFOLLOW") or os.open not in os.supports_dir_fd:
        raise ImportSourceError("path_import_unsupported", "此后端平台不支持安全路径读取，请使用上传")
    parent_fd = None
    file_fd = None
    try:
        parent_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        for part in relative.parts[:-1]:
            next_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent_fd)
            os.close(parent_fd)
            parent_fd = next_fd
        file_fd = os.open(relative.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent_fd)
        before = os.fstat(file_fd)
        limit = MAX_ITEM_BYTES if suffix == ".json" else MAX_BATCH_BYTES
        if not stat.S_ISREG(before.st_mode):
            raise ImportSourceError("source_not_regular_file", "导入源必须是普通文件")
        if before.st_size <= 0 or before.st_size > limit:
            raise ImportSourceError("source_size_invalid", "文件为空或超过导入限制")
        with tempfile.TemporaryDirectory(prefix="witty-path-import-") as directory:
            snapshot = Path(directory) / source.name
            with os.fdopen(file_fd, "rb") as stream, snapshot.open("wb") as target:
                file_fd = None
                copied = 0
                while chunk := stream.read(min(1024 * 1024, limit + 1 - copied)):
                    copied += len(chunk)
                    if copied > limit:
                        raise ImportSourceError("source_too_large", "读取过程中发现文件超过限制")
                    target.write(chunk)
                after = os.fstat(stream.fileno())
            if (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
                after.st_size, after.st_mtime_ns, after.st_ctime_ns
            ) or copied != before.st_size:
                raise ImportSourceError("source_changed", "读取期间文件发生变化，请重试")
            _validate_content(snapshot)
            yield snapshot
    except OSError as exc:
        raise ImportSourceError(
            "source_unreadable", "路径不存在、权限不足或包含符号链接；Docker 请使用已挂载的容器内路径",
        ) from exc
    finally:
        if file_fd is not None:
            os.close(file_fd)
        if parent_fd is not None:
            os.close(parent_fd)
