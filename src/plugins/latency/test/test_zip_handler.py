# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import asyncio
import stat
import zipfile

import pytest

from latency.common.zip_handler import ZipHandler


@pytest.fixture(autouse=True)
def run_to_thread_inline(monkeypatch):
    async def to_thread(function, *args, **kwargs):
        return function(*args, **kwargs)

    monkeypatch.setattr(asyncio, "to_thread", to_thread)


def test_unzip_file_extracts_regular_members(tmp_path):
    archive_path = tmp_path / "logs.zip"
    target_dir = tmp_path / "logs"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("nested/example.log", "safe content")

    asyncio.run(ZipHandler.unzip_file(str(archive_path), str(target_dir)))

    assert (target_dir / "nested" / "example.log").read_text() == "safe content"


@pytest.mark.parametrize(
    "member_name", ["../escaped.log", "..\\escaped.log", "/tmp/escaped.log"]
)
def test_unzip_file_rejects_path_traversal(tmp_path, member_name):
    archive_path = tmp_path / "malicious.zip"
    target_dir = tmp_path / "logs"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("valid.log", "must not be extracted")
        archive.writestr(member_name, "malicious content")

    with pytest.raises(ValueError, match="不安全的成员路径"):
        asyncio.run(ZipHandler.unzip_file(str(archive_path), str(target_dir)))

    assert not target_dir.exists()


def test_unzip_file_rejects_symbolic_links(tmp_path):
    archive_path = tmp_path / "symlink.zip"
    target_dir = tmp_path / "logs"
    link = zipfile.ZipInfo("link.log")
    link.create_system = 3
    link.external_attr = (stat.S_IFLNK | 0o777) << 16
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr(link, "../escaped.log")

    with pytest.raises(ValueError, match="符号链接"):
        asyncio.run(ZipHandler.unzip_file(str(archive_path), str(target_dir)))

    assert not target_dir.exists()
