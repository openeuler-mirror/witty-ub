import asyncio
from contextlib import asynccontextmanager
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import latency.services.brpc_diagnosis_importer as importer_module
from latency.parse.brpc_diag_parser import BrpcDiagParseError
from latency.services.brpc_diagnosis_importer import BrpcDiagnosisImporter


FIXTURES = Path(__file__).parent / "fixtures" / "brpc_diag"
SCHEMA_ID = "1" * 64
SCHEMA_PATH = FIXTURES / "valid" / f"schema_{SCHEMA_ID}.json"


class InMemoryImportStore:
    def __init__(self):
        self.schemas = {}
        self.batches = {}
        self.batch_ids_by_task = {}
        self.hits_by_batch = {}
        self.commits = 0
        self.rollbacks = 0
        self.fail_batch_id = None

    @asynccontextmanager
    async def session(self):
        snapshot = (
            self.schemas.copy(),
            self.batches.copy(),
            self.batch_ids_by_task.copy(),
            deepcopy(self.hits_by_batch),
        )
        try:
            yield SimpleNamespace()
        except Exception:
            (
                self.schemas,
                self.batches,
                self.batch_ids_by_task,
                self.hits_by_batch,
            ) = snapshot
            self.rollbacks += 1
            raise
        else:
            self.commits += 1


def _manager_for(store):
    class InMemoryManager:
        @staticmethod
        async def get_schema(_session, schema_id):
            return store.schemas.get(schema_id)

        @staticmethod
        async def add_schema(_session, schema):
            store.schemas[schema.schema_id] = schema

        @staticmethod
        async def batch_exists(_session, batch_id):
            return batch_id in store.batches

        @staticmethod
        async def get_batch_by_task_id(_session, task_id):
            batch_id = store.batch_ids_by_task.get(task_id)
            return store.batches.get(batch_id)

        @staticmethod
        async def delete_batch(_session, batch_id):
            batch = store.batches.pop(batch_id, None)
            if batch is None:
                return False
            store.batch_ids_by_task.pop(batch.task_id, None)
            store.hits_by_batch.pop(batch_id, None)
            return True

        @staticmethod
        async def add_batch(_session, batch, hits):
            if batch.batch_id == store.fail_batch_id:
                raise RuntimeError("injected batch write failure")
            store.batches[batch.batch_id] = batch
            store.batch_ids_by_task[batch.task_id] = batch.batch_id
            store.hits_by_batch[batch.batch_id] = tuple(hits)

    return InMemoryManager


def _configure_store(monkeypatch, store):
    fake_pg_manager = SimpleNamespace(session=store.session)
    monkeypatch.setattr(importer_module, "PGManager", fake_pg_manager)
    monkeypatch.setattr(
        importer_module,
        "BrpcDiagnosisPGManager",
        _manager_for(store),
    )


def _import(schema_path, batch_path, expected_task_id):
    return asyncio.run(
        BrpcDiagnosisImporter.import_result(
            schema_path=schema_path,
            batch_path=batch_path,
            expected_task_id=expected_task_id,
        )
    )


def _rewrite_batch(source, target, *, task_id, batch_id):
    records = [
        json.loads(line)
        for line in source.read_text(encoding="utf-8").splitlines()
    ]
    records[0]["task_id"] = task_id
    records[0]["batch_id"] = batch_id
    for index, hit in enumerate(records[1:]):
        hit["hit_id"] = f"{batch_id}:hit:{index}"
    target.write_text(
        "".join(json.dumps(record) + "\n" for record in records),
        encoding="utf-8",
    )
    return target


def test_first_import_persists_schema_batch_and_hits(monkeypatch):
    store = InMemoryImportStore()
    _configure_store(monkeypatch, store)

    result = _import(
        SCHEMA_PATH,
        FIXTURES / "valid" / "batch_task-normal.jsonl",
        "task-normal",
    )

    assert result.status == "imported"
    assert result.schema_created is True
    assert result.hit_count == 2
    assert result.replaced_batch_id is None
    assert set(store.schemas) == {SCHEMA_ID}
    assert set(store.batches) == {result.batch_id}
    stored_batch = store.batches[result.batch_id]
    assert stored_batch.start_timestamp == 1_786_000_061_000_000
    assert stored_batch.end_timestamp == 1_786_000_062_000_000
    assert len(store.hits_by_batch[result.batch_id]) == 2
    assert store.commits == 1
    assert store.rollbacks == 0


def test_empty_batch_is_a_successful_import(monkeypatch):
    store = InMemoryImportStore()
    _configure_store(monkeypatch, store)

    result = _import(
        SCHEMA_PATH,
        FIXTURES / "valid" / "batch_task-empty.jsonl",
        "task-empty",
    )

    assert result.status == "imported"
    assert result.hit_count == 0
    assert store.hits_by_batch[result.batch_id] == ()
    stored_batch = store.batches[result.batch_id]
    assert stored_batch.start_timestamp == 1_786_000_063_000_000
    assert stored_batch.end_timestamp == 1_786_000_064_000_000


def test_import_normalizes_unbounded_scan_interval_to_hit_range(
    monkeypatch,
    tmp_path,
):
    store = InMemoryImportStore()
    _configure_store(monkeypatch, store)
    records = [
        json.loads(line)
        for line in (
            FIXTURES / "valid" / "batch_task-normal.jsonl"
        ).read_text(encoding="utf-8").splitlines()
    ]
    records[0]["start_timestamp"] = 0
    records[0]["end_timestamp"] = 1_900_000_000_000_000
    batch_path = tmp_path / "batch_task-normal.jsonl"
    batch_path.write_text(
        "".join(json.dumps(record) + "\n" for record in records),
        encoding="utf-8",
    )

    result = _import(SCHEMA_PATH, batch_path, "task-normal")

    stored_batch = store.batches[result.batch_id]
    assert stored_batch.start_timestamp == 1_786_000_061_000_000
    assert stored_batch.end_timestamp == 1_786_000_062_000_000


def test_duplicate_batch_is_idempotently_skipped(monkeypatch):
    store = InMemoryImportStore()
    _configure_store(monkeypatch, store)
    batch_path = FIXTURES / "valid" / "batch_task-normal.jsonl"

    first = _import(SCHEMA_PATH, batch_path, "task-normal")
    second = _import(SCHEMA_PATH, batch_path, "task-normal")

    assert first.status == "imported"
    assert second.status == "skipped"
    assert second.schema_created is False
    assert set(store.batches) == {first.batch_id}
    assert len(store.hits_by_batch[first.batch_id]) == 2


def test_duplicate_batch_is_still_fully_validated(monkeypatch, tmp_path):
    store = InMemoryImportStore()
    _configure_store(monkeypatch, store)
    batch_path = FIXTURES / "valid" / "batch_task-normal.jsonl"
    imported = _import(SCHEMA_PATH, batch_path, "task-normal")
    records = [
        json.loads(line)
        for line in batch_path.read_text(encoding="utf-8").splitlines()
    ]
    records[1]["timestamp"] = records[0]["end_timestamp"]
    damaged_path = tmp_path / "batch_task-normal.jsonl"
    damaged_path.write_text(
        "".join(json.dumps(record) + "\n" for record in records),
        encoding="utf-8",
    )

    with pytest.raises(BrpcDiagParseError, match="outside"):
        _import(SCHEMA_PATH, damaged_path, "task-normal")

    assert set(store.batches) == {imported.batch_id}
    assert len(store.hits_by_batch[imported.batch_id]) == 2
    assert store.rollbacks == 1


def test_retry_atomically_replaces_previous_batch(monkeypatch):
    store = InMemoryImportStore()
    _configure_store(monkeypatch, store)

    first = _import(
        SCHEMA_PATH,
        FIXTURES / "retry_first" / "batch_task-retry.jsonl",
        "task-retry",
    )
    second = _import(
        SCHEMA_PATH,
        FIXTURES / "retry_second" / "batch_task-retry.jsonl",
        "task-retry",
    )

    assert second.status == "imported"
    assert second.replaced_batch_id == first.batch_id
    assert first.batch_id not in store.batches
    assert first.batch_id not in store.hits_by_batch
    assert set(store.batches) == {second.batch_id}
    assert store.hits_by_batch[second.batch_id] == ()


def test_different_tasks_do_not_deduplicate_hits(monkeypatch, tmp_path):
    store = InMemoryImportStore()
    _configure_store(monkeypatch, store)
    source = FIXTURES / "valid" / "batch_task-normal.jsonl"
    second_batch_id = "0198bbbb-1111-7111-8111-111111111111"
    second_path = _rewrite_batch(
        source,
        tmp_path / "batch_task-second.jsonl",
        task_id="task-second",
        batch_id=second_batch_id,
    )

    first = _import(SCHEMA_PATH, source, "task-normal")
    second = _import(SCHEMA_PATH, second_path, "task-second")

    assert first.batch_id != second.batch_id
    assert len(store.batches) == 2
    assert sum(len(hits) for hits in store.hits_by_batch.values()) == 4


def test_schema_conflict_rolls_back_without_replacing_data(monkeypatch):
    store = InMemoryImportStore()
    _configure_store(monkeypatch, store)
    batch_path = FIXTURES / "valid" / "batch_task-normal.jsonl"
    imported = _import(SCHEMA_PATH, batch_path, "task-normal")
    state_before = (
        store.schemas.copy(),
        store.batches.copy(),
        deepcopy(store.hits_by_batch),
    )

    with pytest.raises(BrpcDiagParseError, match="content conflicts"):
        _import(
            FIXTURES / "invalid" / f"schema_{SCHEMA_ID}.json",
            batch_path,
            "task-normal",
        )

    assert store.schemas == state_before[0]
    assert store.batches == state_before[1]
    assert store.hits_by_batch == state_before[2]
    assert set(store.batches) == {imported.batch_id}
    assert store.rollbacks == 1


def test_invalid_batch_rolls_back_new_schema(monkeypatch):
    store = InMemoryImportStore()
    _configure_store(monkeypatch, store)

    with pytest.raises(BrpcDiagParseError, match="unknown schema_id"):
        _import(
            SCHEMA_PATH,
            FIXTURES / "invalid" / "batch_task-missing-schema.jsonl",
            "task-missing-schema",
        )

    assert store.schemas == {}
    assert store.batches == {}
    assert store.hits_by_batch == {}
    assert store.commits == 0
    assert store.rollbacks == 1


def test_write_failure_restores_batch_deleted_for_retry(monkeypatch):
    store = InMemoryImportStore()
    _configure_store(monkeypatch, store)
    first = _import(
        SCHEMA_PATH,
        FIXTURES / "retry_first" / "batch_task-retry.jsonl",
        "task-retry",
    )
    second_path = FIXTURES / "retry_second" / "batch_task-retry.jsonl"
    second_batch_id = json.loads(
        second_path.read_text(encoding="utf-8").splitlines()[0]
    )["batch_id"]
    store.fail_batch_id = second_batch_id

    with pytest.raises(RuntimeError, match="injected batch write failure"):
        _import(SCHEMA_PATH, second_path, "task-retry")

    assert set(store.batches) == {first.batch_id}
    assert store.batch_ids_by_task["task-retry"] == first.batch_id
    assert len(store.hits_by_batch[first.batch_id]) == 1
    assert store.rollbacks == 1
