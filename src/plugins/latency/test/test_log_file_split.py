import io
import tarfile
import zipfile
from types import SimpleNamespace

import pytest

import latency.task.log_preprocessor as preprocessor_module
from latency.task.log_preprocessor import (
    needs_preprocess,
    preprocess_log_dir,
    split_unmatched_log_files,
)


def test_split_unmatched_log_files(tmp_path):
    matched = tmp_path / "access.log"
    unmatched = tmp_path / "abcd.log"
    runtime_line = " | ".join(str(i) for i in range(8)) + "\n"
    access_line_12 = " | ".join(str(i) for i in range(13)) + "\n"
    access_line_13 = " | ".join(str(i) for i in range(14)) + "\n"
    matched.write_text(runtime_line, encoding="utf-8")
    unmatched.write_text(
        runtime_line + access_line_12 + "unknown\n" + access_line_13,
        encoding="utf-8",
    )

    stats = split_unmatched_log_files(
        str(tmp_path),
        {"ds_worker_access_log_file": ["access.log"]},
    )

    assert stats == {str(unmatched): (1, 2)}
    assert (tmp_path / "abcd.log_split_runtime.log").read_text(encoding="utf-8") == runtime_line
    assert (tmp_path / "abcd.log_split_access.log").read_text(
        encoding="utf-8"
    ) == access_line_12 + access_line_13
    assert not (tmp_path / "access.log_split_runtime.log").exists()
    assert unmatched.exists()


def test_split_unmatched_rotated_log_file(tmp_path):
    unmatched = tmp_path / "abcd.log_yyy"
    runtime_line = " | ".join(str(i) for i in range(8)) + "\n"
    access_line = " | ".join(str(i) for i in range(13)) + "\n"
    unmatched.write_text(runtime_line + access_line, encoding="utf-8")

    stats = split_unmatched_log_files(
        str(tmp_path),
        {"ds_worker_access_log_file": ["access.log"]},
    )

    assert stats == {str(unmatched): (1, 1)}
    assert (
        tmp_path / "abcd.log_yyy_split_runtime.log"
    ).read_text(encoding="utf-8") == runtime_line
    assert (
        tmp_path / "abcd.log_yyy_split_access.log"
    ).read_text(encoding="utf-8") == access_line
    assert unmatched.exists()


def test_split_unmatched_plain_text_file(tmp_path):
    unmatched = tmp_path / "mixed-output"
    runtime_line = " | ".join(str(i) for i in range(8)) + "\n"
    access_line = " | ".join(str(i) for i in range(13)) + "\n"
    unmatched.write_text(runtime_line + access_line, encoding="utf-8")

    stats = split_unmatched_log_files(
        str(tmp_path),
        {"ds_worker_access_log_file": ["access.log"]},
    )

    assert stats == {str(unmatched): (1, 1)}
    assert (
        tmp_path / "mixed-output_split_runtime.log"
    ).read_text(encoding="utf-8") == runtime_line
    assert (
        tmp_path / "mixed-output_split_access.log"
    ).read_text(encoding="utf-8") == access_line


@pytest.mark.parametrize("suffix", [".zip", ".tar.gz", ".tgz"])
def test_preprocess_local_archive_file_path(monkeypatch, tmp_path, suffix):
    source_path = tmp_path / f"brpc-logs{suffix}"
    member_name = "nested/brpc.log"
    content = b"brpc log content\n"

    if suffix == ".zip":
        with zipfile.ZipFile(source_path, "w") as archive:
            archive.writestr(member_name, content)
    else:
        with tarfile.open(source_path, "w:gz") as archive:
            member = tarfile.TarInfo(member_name)
            member.size = len(content)
            archive.addfile(member, io.BytesIO(content))

    filename_patterns = SimpleNamespace(
        model_dump=lambda: {"brpc_log_file_patterns": ["*brpc*.log"]}
    )
    config = SimpleNamespace(
        get_default_diagnosis_config=lambda: SimpleNamespace(
            log_filename_pattern=filename_patterns
        )
    )
    monkeypatch.setattr(preprocessor_module, "Config", lambda: config)

    output_dir = tmp_path / "preprocessed"
    assert needs_preprocess(str(source_path)) is True

    result = preprocess_log_dir(str(source_path), str(output_dir))

    assert result.extracted_count == 1
    assert (output_dir / member_name).read_bytes() == content
