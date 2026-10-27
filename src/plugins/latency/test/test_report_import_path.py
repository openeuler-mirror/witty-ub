import json
import os
import zipfile
import pytest

from latency.services.report_import import ImportSourceError
from latency.services.report_import_path import allowed_import_roots, snapshot_import_path


@pytest.fixture
def import_root(tmp_path, monkeypatch):
    root = tmp_path / "imports"
    root.mkdir()
    monkeypatch.setenv("WITTY_REPORT_IMPORT_ROOTS", str(root))
    return root


def report_bytes():
    return json.dumps({
        "report": {"title": "外部定界报告"},
        "conclusion": {"one_line_conclusion": "客户端连接失败"},
    }).encode()


def test_path_import_disabled_unless_explicitly_configured(monkeypatch, tmp_path):
    monkeypatch.delenv("WITTY_REPORT_IMPORT_ROOTS", raising=False)
    assert allowed_import_roots() == []
    with pytest.raises(ImportSourceError, match="path_import_disabled"):
        with snapshot_import_path(str(tmp_path / "source.json")):
            pytest.fail("unconfigured directory must not be readable")


def test_path_import_snapshots_source_and_removes_private_copy(import_root):
    path = import_root / "one.json"
    path.write_bytes(report_bytes())
    with snapshot_import_path(str(path)) as snapshot:
        assert snapshot != path
        assert snapshot.name == path.name
        assert snapshot.read_bytes() == path.read_bytes()
        saved = snapshot
    assert not saved.exists()
    assert path.exists()


@pytest.mark.parametrize("value", ["relative.json", "~/one.json", "file:///tmp/one.json", "/etc/passwd", " /tmp/one.json"])
def test_disallowed_paths_are_rejected(import_root, value):
    with pytest.raises(ImportSourceError):
        with snapshot_import_path(value):
            pytest.fail("unsafe path read")


def test_parent_traversal_and_prefix_sibling_are_rejected(import_root):
    for path in (str(import_root / ".." / "outside.json"), str(import_root) + "-other/one.json"):
        with pytest.raises(ImportSourceError):
            with snapshot_import_path(path):
                pytest.fail("outside file read")


def test_symlink_file_and_intermediate_directory_are_not_followed(import_root, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "one.json").write_bytes(report_bytes())
    (import_root / "linked.json").symlink_to(outside / "one.json")
    (import_root / "linked-dir").symlink_to(outside, target_is_directory=True)
    for path in (import_root / "linked.json", import_root / "linked-dir" / "one.json"):
        with pytest.raises(ImportSourceError, match="source_unreadable"):
            with snapshot_import_path(str(path)):
                pytest.fail("symlink followed")


@pytest.mark.parametrize("content", [b"", b"{bad", b"[]", b'{"a":1}', b'{"report":{},"faults":[]}', b'{"report":{},"conclusion":{},"confidence":NaN}'])
def test_bad_json_rejected_before_import_writes(import_root, content):
    path = import_root / "bad.json"
    path.write_bytes(content)
    with pytest.raises(ImportSourceError):
        with snapshot_import_path(str(path)):
            pytest.fail("malformed file reached import")


def test_non_regular_files_do_not_block(import_root):
    path = import_root / "pipe.json"
    os.mkfifo(path)
    with pytest.raises(ImportSourceError, match="source_not_regular_file"):
        with snapshot_import_path(str(path)):
            pytest.fail("FIFO accepted")


def test_directory_and_oversize_file_rejected(import_root):
    from latency.services.report_import import MAX_ITEM_BYTES
    (import_root / "dir.json").mkdir()
    with pytest.raises(ImportSourceError):
        with snapshot_import_path(str(import_root / "dir.json")):
            pytest.fail("directory accepted")
    path = import_root / "large.json"
    with path.open("wb") as stream:
        stream.truncate(MAX_ITEM_BYTES + 1)
    with pytest.raises(ImportSourceError, match="source_size_invalid"):
        with snapshot_import_path(str(path)):
            pytest.fail("oversized file accepted")


def test_zip_members_are_checked_without_extracting(import_root):
    path = import_root / "batch.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("reports/one.json", report_bytes())
    with snapshot_import_path(str(path)) as snapshot:
        assert snapshot.is_file()
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("../outside.json", report_bytes())
    with pytest.raises(ImportSourceError, match="zip_entry_traversal"):
        with snapshot_import_path(str(path)):
            pytest.fail("dangerous ZIP accepted")

def test_archive_entry_count_includes_non_json_items(import_root):
    from latency.services.report_import import MAX_ZIP_ENTRIES
    path = import_root / "many.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("one.json", report_bytes())
        for index in range(MAX_ZIP_ENTRIES):
            archive.writestr(f"not-a-report-{index}.txt", "")
    with pytest.raises(ImportSourceError, match="zip_too_many_entries"):
        with snapshot_import_path(str(path)):
            pytest.fail("unbounded metadata count accepted")


def test_zip_symbolic_link_entry_is_rejected(import_root):
    path = import_root / "link.zip"
    info = zipfile.ZipInfo("link.json")
    info.create_system = 3
    info.external_attr = 0o120777 << 16
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(info, "outside.json")
    with pytest.raises(ImportSourceError, match="zip_entry_symlink"):
        with snapshot_import_path(str(path)):
            pytest.fail("archive link accepted")


@pytest.mark.parametrize("root", ["/", ".", "../imports"])
def test_invalid_root_configuration_fails_explicitly(monkeypatch, root):
    monkeypatch.setenv("WITTY_REPORT_IMPORT_ROOTS", root)
    with pytest.raises(ImportSourceError, match="import_root_invalid"):
        allowed_import_roots()
