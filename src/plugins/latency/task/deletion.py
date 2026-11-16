"""Filesystem cleanup used after the task deletion fence has drained writers."""
from __future__ import annotations

import logging
import os
import shutil
import stat
import time
from pathlib import Path

from latency.ENUM.general import FilePath
from latency.task.log_preprocessor import default_preprocess_dir

logger = logging.getLogger(__name__)


def default_upload_root() -> str:
    latency_dir = os.path.dirname(os.path.dirname(__file__))
    return os.path.join(latency_dir, FilePath.FILE_UPLOAD_PATH.value)


def _make_writable_and_retry(function, path, _exc_info) -> None:
    os.chmod(path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
    function(path)


def remove_path_strict(path: str | os.PathLike[str]) -> None:
    """Remove one owned path, retrying transient concurrent-filesystem errors."""
    target = Path(path)
    for attempt in range(5):
        try:
            if target.is_symlink() or target.is_file():
                target.unlink(missing_ok=True)
            elif target.exists():
                shutil.rmtree(target, onerror=_make_writable_and_retry)
            if not target.exists() and not target.is_symlink():
                return
        except FileNotFoundError:
            return
        except OSError:
            if attempt == 4:
                raise
            time.sleep(0.1 * (attempt + 1))
    raise RuntimeError(f"删除路径后仍然存在: {target}")


def is_owned_upload(path: str, upload_root: str) -> bool:
    """Only uploaded/downloaded copies are owned; never delete a local source."""
    if not path:
        return False
    try:
        resolved = os.path.realpath(path)
        root = os.path.realpath(upload_root)
        return os.path.commonpath([resolved, root]) == root and resolved != root
    except (OSError, ValueError):
        return False


def cleanup_log_artifacts(
    log_file,
    *,
    witty_dir: str,
    upload_root: str,
) -> None:
    """Delete every application-owned temporary/source artifact for one log."""
    log_id = log_file.id
    cleanup_log_temp_dirs(log_id, witty_dir=witty_dir)

    source_path = str(getattr(log_file, "file_path", "") or "")
    if is_owned_upload(source_path, upload_root):
        remove_path_strict(source_path)
        logger.info("删除日志级联文件: %s", source_path)


def cleanup_log_temp_dirs(log_id: str, *, witty_dir: str) -> None:
    """Delete temp directories even if the owning log row is already gone."""
    targets = [
        default_preprocess_dir(log_id),
        os.path.join(witty_dir, "log_" + log_id[:8]),
    ]
    for target in targets:
        remove_path_strict(target)
        logger.info("删除日志级联文件: %s", target)
