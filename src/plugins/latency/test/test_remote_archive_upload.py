import asyncio
from unittest.mock import AsyncMock

import pytest

import latency.services.log_file as log_file_service_module
from latency.ENUM.general import SourceType
from latency.exceptions import BadRequestBizException
from latency.schemas.request import UpLoadLogFileConfig, UpLoadLogFilesRequest
from latency.services.log_file import LogFileService


class _FakeResponse:
    def __init__(self, content: bytes):
        self._content = content

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    def raise_for_status(self):
        return None

    async def read(self):
        return self._content


class _FakeSession:
    def __init__(self, content: bytes):
        self._content = content

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    def get(self, *args, **kwargs):
        return _FakeResponse(self._content)


class _FakeAsyncFile:
    def __init__(self, path):
        self._path = path
        self._file = None

    async def __aenter__(self):
        self._file = open(self._path, "wb")
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        self._file.close()
        return False

    async def write(self, content):
        return self._file.write(content)


@pytest.mark.parametrize("suffix", [".zip", ".tar.gz", ".tgz", ".rar"])
def test_remote_archive_uses_same_suffix_as_local_archive(
    monkeypatch, tmp_path, suffix
):
    added_models = []

    async def add_log_files(models):
        added_models.extend(models)
        return [model.id for model in models]

    monkeypatch.setattr(log_file_service_module, "_validate_remote_url", lambda _: True)
    monkeypatch.setattr(
        log_file_service_module.aiohttp,
        "ClientSession",
        lambda: _FakeSession(b"archive-content"),
    )
    monkeypatch.setattr(
        log_file_service_module.aiofiles,
        "open",
        lambda path, mode: _FakeAsyncFile(path),
    )
    monkeypatch.setattr(log_file_service_module, "is_valid_archive_file", lambda _: True)
    monkeypatch.setattr(
        LogFileService,
        "get_upload_path",
        staticmethod(lambda *paths: str(tmp_path.joinpath(*paths))),
    )
    monkeypatch.setattr(
        log_file_service_module.LogFilePGManager,
        "add_log_files",
        add_log_files,
    )
    init_task = AsyncMock(return_value="task-id")
    monkeypatch.setattr(log_file_service_module.TaskHandler, "init_task", init_task)

    result = asyncio.run(
        LogFileService.upload_log_files(
            "kb-id",
            UpLoadLogFilesRequest(
                upload_log_file_configs=[
                    UpLoadLogFileConfig(
                        name=f"logs{suffix}",
                        source_type=SourceType.REMOTE,
                        source=f"https://example.com/logs{suffix}?token=secret",
                        log_type="brpc",
                    )
                ]
            ),
        )
    )

    assert result.log_file_ids == [added_models[0].id]
    assert added_models[0].file_path.endswith(suffix)
    assert added_models[0].file_size == len(b"archive-content")
    assert tmp_path.joinpath(added_models[0].id + suffix).read_bytes() == b"archive-content"
    assert init_task.await_count == 2


def test_remote_archive_rejects_unsupported_suffix(monkeypatch):
    monkeypatch.setattr(log_file_service_module, "_validate_remote_url", lambda _: True)

    with pytest.raises(BadRequestBizException):
        asyncio.run(
            LogFileService.upload_log_files(
                "kb-id",
                UpLoadLogFilesRequest(
                    upload_log_file_configs=[
                        UpLoadLogFileConfig(
                            name="logs.7z",
                            source_type=SourceType.REMOTE,
                            source="https://example.com/logs.7z",
                            log_type="brpc",
                        )
                    ]
                ),
            )
        )
