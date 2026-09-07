import io
import errno
import tarfile
import zipfile
from types import SimpleNamespace

import pytest

import latency.task.log_preprocessor as preprocessor_module
from latency.task.log_preprocessor import (
    get_archive_extension,
    is_valid_archive_file,
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


def test_preprocess_propagates_disk_full(monkeypatch, tmp_path):
    source_path = tmp_path / "source"
    source_path.mkdir()
    (source_path / "access.log").write_text("log", encoding="utf-8")
    output_dir = tmp_path / "preprocessed"

    monkeypatch.setattr(
        preprocessor_module.shutil,
        "copy2",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            OSError(errno.ENOSPC, "No space left on device")
        ),
    )

    with pytest.raises(OSError) as exc_info:
        preprocess_log_dir(str(source_path), str(output_dir))

    assert exc_info.value.errno == errno.ENOSPC


def test_split_propagates_disk_full(monkeypatch, tmp_path):
    source_path = tmp_path / "unmatched.log"
    source_path.write_text(" | ".join(str(i) for i in range(8)), encoding="utf-8")
    real_open = open

    def open_with_disk_full(path, mode="r", *args, **kwargs):
        if "w" in mode:
            raise OSError(errno.ENOSPC, "No space left on device")
        return real_open(path, mode, *args, **kwargs)

    monkeypatch.setattr(preprocessor_module, "open", open_with_disk_full, raising=False)

    with pytest.raises(OSError) as exc_info:
        split_unmatched_log_files(str(tmp_path), {"known": ["known.log"]})

    assert exc_info.value.errno == errno.ENOSPC


def test_archive_extraction_propagates_disk_full(monkeypatch, tmp_path):
    source_path = tmp_path / "logs.zip"
    source_path.write_bytes(b"archive")
    monkeypatch.setattr(
        preprocessor_module,
        "_extract_zip",
        lambda *_args: (_ for _ in ()).throw(
            OSError(errno.ENOSPC, "No space left on device")
        ),
    )

    with pytest.raises(OSError) as exc_info:
        preprocessor_module._extract_archive(str(source_path), str(tmp_path / "output"))

    assert exc_info.value.errno == errno.ENOSPC


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


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("logs.zip", ".zip"),
        ("logs.TAR.GZ", ".tar.gz"),
        ("logs.tgz", ".tgz"),
        ("logs.rar", ".rar"),
        ("logs.gz", None),
        ("logs.tar", None),
    ],
)
def test_get_archive_extension(path, expected):
    assert get_archive_extension(path) == expected


@pytest.mark.parametrize("suffix", [".tar.gz", ".tgz"])
def test_is_valid_archive_file_for_tar_gzip(tmp_path, suffix):
    archive_path = tmp_path / f"logs{suffix}"
    content = b"log content\n"
    with tarfile.open(archive_path, "w:gz") as archive:
        member = tarfile.TarInfo("nested/service.log")
        member.size = len(content)
        archive.addfile(member, io.BytesIO(content))

    assert is_valid_archive_file(str(archive_path)) is True


def test_is_valid_archive_file_for_zip(tmp_path):
    archive_path = tmp_path / "logs.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("nested/service.log", b"log content\n")

    assert is_valid_archive_file(str(archive_path)) is True
