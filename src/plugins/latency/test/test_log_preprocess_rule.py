"""预处理判定规则与完成标记语义的回归测试。

覆盖:
- needs_preprocess: 存在匹配文件时未匹配文件不再触发预处理(规则变更);
  压缩包、全未匹配文本、空目录仍触发。
- preprocess_log_dir: 完成标记记录产出计数; 产出为空不写标记并抛错;
  旧格式"空目录+标记"的假完成目录会被识别并重做; 合法完成目录正常复用。
"""
import errno
import os
import shutil
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from latency.task import log_preprocessor as preprocessor_module
from latency.task.log_preprocessor import (
    _PREPROCESS_COMPLETE_MARKER,
    needs_preprocess,
    preprocess_log_dir,
)


def _patterns_config(patterns):
    config = SimpleNamespace(
        get_default_diagnosis_config=lambda: SimpleNamespace(
            log_filename_pattern=SimpleNamespace(model_dump=lambda: patterns)
        )
    )
    return lambda: config


def _patch_patterns(monkeypatch, patterns):
    monkeypatch.setattr(preprocessor_module, "Config", _patterns_config(patterns))


_ACCESS = {"ds_worker_access_log_file": ["access.log", "ds_client_access*.log"]}


# ---------------------------------------------------------------------------
# needs_preprocess: 存在匹配文件 → 未匹配文件不触发
# ---------------------------------------------------------------------------


class TestNeedsPreprocessWithMatches:
    def test_match_plus_unmatched_text_skips(self, monkeypatch, tmp_path):
        """headline: 正常日志 + env/version.txt → 直扫源目录, 不再全量拷贝。"""
        _patch_patterns(monkeypatch, _ACCESS)
        (tmp_path / "access.log").write_text("x", encoding="utf-8")
        (tmp_path / "odd.log").write_text("hello", encoding="utf-8")
        (tmp_path / "env").write_text("PATH=/usr/bin", encoding="utf-8")
        (tmp_path / "version.txt").write_text("v1", encoding="utf-8")

        assert needs_preprocess(str(tmp_path)) is False

    def test_match_plus_archive_still_preprocesses(self, monkeypatch, tmp_path):
        _patch_patterns(monkeypatch, _ACCESS)
        (tmp_path / "access.log").write_text("x", encoding="utf-8")
        (tmp_path / "bundle.zip").write_bytes(b"zip")

        assert needs_preprocess(str(tmp_path)) is True

    def test_nested_match_skips(self, monkeypatch, tmp_path):
        _patch_patterns(monkeypatch, _ACCESS)
        (tmp_path / "SDK_1").mkdir()
        (tmp_path / "SDK_1" / "ds_client_access_81.log").write_text("x", "utf-8")
        (tmp_path / "SDK_1" / "env").write_text("PATH=/usr/bin", "utf-8")

        assert needs_preprocess(str(tmp_path)) is False


# ---------------------------------------------------------------------------
# needs_preprocess: 既有语义保持(压缩包/全未匹配/gz/单文件)
# ---------------------------------------------------------------------------


class TestNeedsPreprocessLegacySemantics:
    def test_all_unmatched_text_still_preprocesses(self, monkeypatch, tmp_path):
        """无任何匹配文件 + 存在文本 → 保留拆分救回路径。"""
        _patch_patterns(monkeypatch, _ACCESS)
        (tmp_path / "mixed.log").write_text("hello", encoding="utf-8")

        assert needs_preprocess(str(tmp_path)) is True

    def test_gz_only_dir_skips(self, monkeypatch, tmp_path):
        _patch_patterns(monkeypatch, _ACCESS)
        (tmp_path / "access.log.gz").write_bytes(b"gz")

        assert needs_preprocess(str(tmp_path)) is False

    def test_unmatched_gz_only_dir_skips(self, monkeypatch, tmp_path):
        _patch_patterns(monkeypatch, _ACCESS)
        (tmp_path / "odd.log.gz").write_bytes(b"gz")

        assert needs_preprocess(str(tmp_path)) is False

    def test_empty_dir_preprocesses(self, tmp_path):
        assert needs_preprocess(str(tmp_path)) is True

    def test_single_matched_file_skips(self, monkeypatch, tmp_path):
        _patch_patterns(monkeypatch, _ACCESS)
        source = tmp_path / "access.log"
        source.write_text("x", encoding="utf-8")

        assert needs_preprocess(str(source)) is False

    def test_single_unmatched_text_preprocesses(self, monkeypatch, tmp_path):
        _patch_patterns(monkeypatch, _ACCESS)
        source = tmp_path / "odd.log"
        source.write_text("x", encoding="utf-8")

        assert needs_preprocess(str(source)) is True

    def test_single_binary_skips(self, monkeypatch, tmp_path):
        _patch_patterns(monkeypatch, _ACCESS)
        source = tmp_path / "blob.bin"
        source.write_bytes(b"\x00\x01")

        assert needs_preprocess(str(source)) is False

    def test_single_archive_preprocesses(self, tmp_path):
        source = tmp_path / "bundle.tar.gz"
        source.write_bytes(b"tar")

        assert needs_preprocess(str(source)) is True


# ---------------------------------------------------------------------------
# preprocess_log_dir: 完成标记语义
# ---------------------------------------------------------------------------


class TestPreprocessMarkerSemantics:
    def _source_with_access_log(self, tmp_path):
        source = tmp_path / "src"
        source.mkdir()
        (source / "access.log").write_text("x", encoding="utf-8")
        return source

    def test_marker_records_counts(self, monkeypatch, tmp_path):
        _patch_patterns(monkeypatch, _ACCESS)
        source = self._source_with_access_log(tmp_path)
        output = tmp_path / "out"

        result = preprocess_log_dir(str(source), str(output))

        assert result.reused is False
        assert result.copied_count == 1
        marker = (output / _PREPROCESS_COMPLETE_MARKER).read_text(encoding="utf-8")
        assert "copied=1" in marker
        assert "extracted=0" in marker
        assert "copy_failed=0" in marker

    def test_poisoned_empty_marker_dir_is_redone(self, monkeypatch, tmp_path):
        """旧缺陷现场: 空目录 + 完成标记 → 不得复用, 必须重做。"""
        _patch_patterns(monkeypatch, _ACCESS)
        source = self._source_with_access_log(tmp_path)
        output = tmp_path / "out"
        output.mkdir()
        (output / _PREPROCESS_COMPLETE_MARKER).write_text(
            "complete\n", encoding="utf-8"
        )

        result = preprocess_log_dir(str(source), str(output))

        assert result.reused is False
        assert (output / "access.log").read_text(encoding="utf-8") == "x"
        assert "copied=1" in (
            output / _PREPROCESS_COMPLETE_MARKER
        ).read_text(encoding="utf-8")

    def test_valid_complete_dir_is_reused(self, monkeypatch, tmp_path):
        _patch_patterns(monkeypatch, _ACCESS)
        source = self._source_with_access_log(tmp_path)
        output = tmp_path / "out"

        preprocess_log_dir(str(source), str(output))
        result = preprocess_log_dir(str(source), str(output))

        assert result.reused is True
        assert result.copied_count == 0

    def test_partial_copy_failure_still_completes_with_counts(
        self, monkeypatch, tmp_path
    ):
        _patch_patterns(monkeypatch, _ACCESS)
        source = self._source_with_access_log(tmp_path)
        (source / "odd.log").write_text("hello", encoding="utf-8")
        real_copy2 = shutil.copy2
        calls = {"n": 0}

        def flaky_copy(src, dst, *args, **kwargs):
            calls["n"] += 1
            if calls["n"] == 1:
                raise OSError(errno.EIO, "io err")
            return real_copy2(src, dst, *args, **kwargs)

        monkeypatch.setattr(shutil, "copy2", flaky_copy)
        output = tmp_path / "out"

        result = preprocess_log_dir(str(source), str(output))

        assert result.copied_count == 1
        marker = (output / _PREPROCESS_COMPLETE_MARKER).read_text(encoding="utf-8")
        assert "copy_failed=1" in marker

    def test_all_copy_failed_raises_without_marker(self, monkeypatch, tmp_path):
        _patch_patterns(monkeypatch, _ACCESS)
        source = self._source_with_access_log(tmp_path)
        monkeypatch.setattr(
            shutil,
            "copy2",
            Mock(side_effect=OSError(errno.EIO, "io err")),
        )
        output = tmp_path / "out"

        with pytest.raises(RuntimeError, match="预处理产出为空"):
            preprocess_log_dir(str(source), str(output))

        assert not (output / _PREPROCESS_COMPLETE_MARKER).exists()
        # 未写标记的半成品目录会被下一次运行清掉重做, 不会沉淀为假完成目录。
        assert _dir_marker_absent_or_absent_dir(output)


def _dir_marker_absent_or_absent_dir(output_dir) -> bool:
    if not os.path.isdir(output_dir):
        return True
    return not os.path.isfile(os.path.join(output_dir, _PREPROCESS_COMPLETE_MARKER))
