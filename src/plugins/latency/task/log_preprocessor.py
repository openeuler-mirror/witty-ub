import fnmatch
import gzip
import logging
import os
import shutil
import tarfile
import zipfile
from dataclasses import dataclass

from latency.config.config import Config

logger = logging.getLogger(__name__)

WITTY_DIR_DEFAULT = "/var/witty-ub"
_BUFFER_SIZE = 8 * 1024 * 1024
_ARCHIVE_EXTENSIONS = (".tar.gz", ".tgz", ".zip", ".rar")


@dataclass(frozen=True)
class LogPreprocessResult:
    source_dir: str
    output_dir: str
    extracted_count: int
    copied_count: int
    split_count: int
    reused: bool = False


def default_preprocess_dir(log_file_id: str) -> str:
    witty_dir = os.getenv("WITTY_DIR", WITTY_DIR_DEFAULT)
    return os.path.join(witty_dir, f"log_preprocessed_{log_file_id}")


def cleanup_preprocess_dir(log_file_id: str) -> str | None:
    import time
    preprocess_dir = default_preprocess_dir(log_file_id)
    if not os.path.isdir(preprocess_dir):
        logger.info("日志预处理目录不存在: %s", preprocess_dir)
        return None
    
    # 重试机制：最多尝试3次，每次间隔2秒
    max_retries = 3
    for attempt in range(max_retries):
        try:
            shutil.rmtree(preprocess_dir)
            logger.info("删除日志预处理目录: %s", preprocess_dir)
            return preprocess_dir
        except OSError as exc:
            if attempt < max_retries - 1:
                logger.warning("删除日志预处理目录 %s 失败(尝试 %d/%d): %s, 2秒后重试", 
                              preprocess_dir, attempt + 1, max_retries, exc)
                time.sleep(2)
            else:
                logger.error("删除日志预处理目录 %s 失败(已重试%d次): %s", 
                            preprocess_dir, max_retries, exc)
                return None


def _configured_filename_patterns() -> list[str]:
    """返回配置里所有日志文件名 pattern(展平)。

    用于判断源目录文件是否都已匹配 filename_patterns —— 全部匹配则
    无需拆分,可直接扫描源目录,跳过预处理拷贝。
    """
    try:
        patterns_cfg = (
            Config().get_default_diagnosis_config().log_filename_pattern.model_dump()
        )
        return [p for plist in patterns_cfg.values() for p in plist]
    except Exception as exc:  # 配置不可用时不优化,走原有拷贝路径
        logger.warning("读取 filename_patterns 失败, 预处理将不跳过: %s", exc)
        return []


def needs_preprocess(source_path: str) -> bool:
    """判断 source_path 是否需要预处理(拷贝+解压+拆分)。

    返回 False 表示源是纯文本日志目录/文件,且每个文件都已匹配
    filename_patterns(无需 split_unmatched_log_files 拆分),也没有压缩包
    —— scan_all 可直接扫描源路径,省去 106MB 级重复拷贝。

    需要预处理的情形:
      - 源含压缩包(.tar.gz/.zip/.rar)—— 需要解压(.gz 不在此列;
        open_log 直接流式读取, 无需解压写盘)
      - 存在未匹配 filename_patterns 的文本文件 —— 需要拆分成 access/runtime
    """
    patterns = _configured_filename_patterns()

    def _needs_split(source_file: str) -> bool:
        rel = os.path.relpath(source_file, source_path).replace(os.sep, "/")
        if _matches_any_pattern(rel, os.path.basename(source_file), patterns):
            return False
        if filename_looks_like_text(source_file):
            return True
        return False

    if os.path.isfile(source_path):
        return _needs_split(source_path)

    saw_file = False
    for source_file, _ in _iter_source_files(source_path):
        saw_file = True
        if _is_archive(source_file):
            return True
        if source_file.lower().endswith(".gz"):
            # .gz handled transparently by open_log() + FileParserMapBuilder
            # .gz variant patterns — no extraction or splitting needed.
            continue
        if _needs_split(source_file):
            return True
    # 有文件且全部匹配 → 无需预处理;空目录/源不存在 → 保底交给原逻辑
    return not saw_file


def filename_looks_like_text(path: str) -> bool:
    """读前 8KB 判断是否文本文件(与 split 逻辑同判据)。"""
    return _looks_like_text_file(path)


def preprocess_log_dir(source_path: str, output_dir: str) -> LogPreprocessResult:
    """Copy/extract logs into output_dir, then split unmatched text logs."""
    if not os.path.exists(source_path):
        raise FileNotFoundError(f"日志路径不存在: {source_path}")

    if os.path.isdir(output_dir):
        return LogPreprocessResult(
            source_dir=source_path,
            output_dir=output_dir,
            extracted_count=0,
            copied_count=0,
            split_count=0,
            reused=True,
        )

    os.makedirs(output_dir, exist_ok=True)

    extracted_count = 0
    copied_count = 0
    for source_file, relative_dir in _iter_source_files(source_path):
        target_dir = os.path.join(output_dir, relative_dir)
        os.makedirs(target_dir, exist_ok=True)

        if _is_archive(source_file):
            extracted_count += _extract_archive(source_file, target_dir)
            continue

        target_file = os.path.join(target_dir, os.path.basename(source_file))
        try:
            shutil.copy2(source_file, target_file)
            copied_count += 1
        except OSError as exc:
            logger.error("复制日志文件 %s 失败: %s", source_file, exc)

    filename_patterns = (
        Config().get_default_diagnosis_config().log_filename_pattern.model_dump()
    )
    split_stats = split_unmatched_log_files(output_dir, filename_patterns)
    return LogPreprocessResult(
        source_dir=source_path,
        output_dir=output_dir,
        extracted_count=extracted_count,
        copied_count=copied_count,
        split_count=len(split_stats),
    )


def split_unmatched_log_files(
    log_dir: str, filename_patterns: dict[str, list[str]]
) -> dict[str, tuple[int, int]]:
    """Split text files not matched by configured patterns into access/runtime logs."""
    patterns = [
        pattern
        for pattern_list in filename_patterns.values()
        for pattern in pattern_list
    ]
    split_stats: dict[str, tuple[int, int]] = {}

    for root, _, files in os.walk(log_dir):
        for filename in files:
            source_path = os.path.join(root, filename)
            relative_path = os.path.relpath(source_path, log_dir)
            normalized_rel_path = relative_path.replace(os.sep, "/")

            if _matches_any_pattern(normalized_rel_path, filename, patterns):
                continue
            if filename.endswith(("_split_access.log", "_split_runtime.log")):
                continue
            if not _looks_like_text_file(source_path):
                continue

            access_path = os.path.join(root, f"{filename}_split_access.log")
            runtime_path = os.path.join(root, f"{filename}_split_runtime.log")
            runtime_count = 0
            access_count = 0

            try:
                with open(
                    source_path, "r", encoding="utf-8", errors="ignore"
                ) as source, open(
                    access_path, "w", encoding="utf-8"
                ) as access_file, open(
                    runtime_path, "w", encoding="utf-8"
                ) as runtime_file:
                    for line in source:
                        delimiter_count = line.count(" | ")
                        if delimiter_count == 7:
                            runtime_file.write(line)
                            runtime_count += 1
                        elif delimiter_count in (12, 13):
                            access_file.write(line)
                            access_count += 1
            except OSError as exc:
                logger.error("拆分日志 %s 失败: %s", source_path, exc)
                continue

            if runtime_count == 0 and access_count == 0:
                _remove_empty_file(runtime_path)
                _remove_empty_file(access_path)
                continue

            split_stats[source_path] = (runtime_count, access_count)
            logger.info(
                "拆分未匹配日志 %s: runtime=%d, access=%d",
                source_path,
                runtime_count,
                access_count,
            )

    return split_stats


def _iter_source_files(source_path: str):
    if os.path.isfile(source_path):
        yield source_path, ""
        return

    for root, _, files in os.walk(source_path):
        relative_dir = os.path.relpath(root, source_path)
        if relative_dir == ".":
            relative_dir = ""
        for filename in files:
            yield os.path.join(root, filename), relative_dir


def _is_archive(path: str) -> bool:
    lower_path = path.lower()
    return lower_path.endswith(_ARCHIVE_EXTENSIONS)


def _extract_archive(source_file: str, target_dir: str) -> int:
    lower_path = source_file.lower()
    try:
        if lower_path.endswith((".tar.gz", ".tgz")):
            return _extract_tar(source_file, target_dir)
        if lower_path.endswith(".gz"):
            return _extract_gzip_file(source_file, target_dir)
        if lower_path.endswith(".zip"):
            return _extract_zip(source_file, target_dir)
        if lower_path.endswith(".rar"):
            return _extract_rar(source_file, target_dir)
    except Exception as exc:
        logger.error("解压日志文件 %s 失败: %s", source_file, exc)
    return 0


def _extract_gzip_file(source_file: str, target_dir: str) -> int:
    filename = os.path.basename(source_file)
    target_file = os.path.join(target_dir, filename[:-3])
    with gzip.open(source_file, "rb") as source, open(target_file, "wb") as target:
        shutil.copyfileobj(source, target, length=_BUFFER_SIZE)
    return 1


def _extract_tar(source_file: str, target_dir: str) -> int:
    extracted = 0
    with tarfile.open(source_file, "r:gz") as archive:
        for member in archive.getmembers():
            if not member.isfile():
                continue
            _safe_extract_tar_member(archive, member, target_dir)
            extracted += 1
    return extracted


def _extract_zip(source_file: str, target_dir: str) -> int:
    extracted = 0
    with zipfile.ZipFile(source_file, "r") as archive:
        for member in archive.infolist():
            if member.is_dir():
                continue
            _safe_extract_zip_member(archive, member, target_dir)
            extracted += 1
    return extracted


def _extract_rar(source_file: str, target_dir: str) -> int:
    try:
        import rarfile
    except ImportError:
        logger.warning("rarfile 模块未安装，跳过 .rar 文件: %s", source_file)
        return 0

    extracted = 0
    with rarfile.RarFile(source_file, "r") as archive:
        for member in archive.infolist():
            if member.isdir():
                continue
            target_path = _safe_join(target_dir, member.filename)
            if target_path is None:
                logger.warning("跳过不安全的 rar 成员路径: %s", member.filename)
                continue
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            with archive.open(member) as source, open(target_path, "wb") as target:
                shutil.copyfileobj(source, target, length=_BUFFER_SIZE)
            extracted += 1
    return extracted


def _safe_extract_tar_member(
    archive: tarfile.TarFile, member: tarfile.TarInfo, target_dir: str
) -> None:
    target_path = _safe_join(target_dir, member.name)
    if target_path is None:
        logger.warning("跳过不安全的 tar 成员路径: %s", member.name)
        return
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    extracted = archive.extractfile(member)
    if extracted is None:
        return
    with extracted as source, open(target_path, "wb") as target:
        shutil.copyfileobj(source, target, length=_BUFFER_SIZE)


def _safe_extract_zip_member(
    archive: zipfile.ZipFile, member: zipfile.ZipInfo, target_dir: str
) -> None:
    target_path = _safe_join(target_dir, member.filename)
    if target_path is None:
        logger.warning("跳过不安全的 zip 成员路径: %s", member.filename)
        return
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    with archive.open(member) as source, open(target_path, "wb") as target:
        shutil.copyfileobj(source, target, length=_BUFFER_SIZE)


def _safe_join(base_dir: str, member_name: str) -> str | None:
    target_path = os.path.abspath(os.path.join(base_dir, member_name))
    base_path = os.path.abspath(base_dir)
    if os.path.commonpath([base_path, target_path]) != base_path:
        return None
    return target_path


def _matches_any_pattern(
    relative_path: str, filename: str, patterns: list[str]
) -> bool:
    return any(
        fnmatch.fnmatch(relative_path, pattern)
        or fnmatch.fnmatch(filename, pattern)
        for pattern in patterns
    )


def _looks_like_text_file(path: str) -> bool:
    try:
        with open(path, "rb") as file:
            chunk = file.read(8192)
    except OSError:
        return False
    return b"\x00" not in chunk


def _remove_empty_file(path: str) -> None:
    try:
        if os.path.exists(path) and os.path.getsize(path) == 0:
            os.remove(path)
    except OSError as exc:
        logger.warning("删除空拆分文件 %s 失败: %s", path, exc)
