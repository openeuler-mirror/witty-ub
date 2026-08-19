import asyncio
from pathlib import Path

from sqlalchemy import BigInteger, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB

from latency.database.init import BRPC_DIAG_INDEX_DDL
from latency.database.managers.brpc_diagnosis import BrpcDiagnosisPGManager
from latency.database.models import (
    Base,
    BrpcDiagBatch,
    BrpcDiagEdge,
    BrpcDiagFailureInterface,
    BrpcDiagFailureSubgraph,
    BrpcDiagHit,
    BrpcDiagNode,
    BrpcDiagSchema,
)
from latency.parse.brpc_diag_parser import BrpcDiagParser


FIXTURES = Path(__file__).parent / "fixtures" / "brpc_diag"
SCHEMA_ID = "1" * 64


class FakeWriteSession:
    def __init__(self):
        self.rows = []
        self.flush_count = 0
        self.pending_rows = []
        self.flushed_row_types = []

    def add_all(self, rows):
        rows = list(rows)
        self.rows.extend(rows)
        self.pending_rows.extend(rows)

    async def flush(self):
        self.flush_count += 1
        self.flushed_row_types.append(
            tuple(type(row) for row in self.pending_rows)
        )
        self.pending_rows.clear()


class FakeScalarResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return self._rows


class FakeReadSession:
    def __init__(self, rows):
        self.rows = rows

    async def get(self, row_type, key):
        primary_key = "schema_id" if row_type is BrpcDiagSchema else "batch_id"
        return next(
            (
                row
                for row in self.rows
                if isinstance(row, row_type)
                and getattr(row, primary_key) == key
            ),
            None,
        )

    async def execute(self, statement):
        row_type = statement.column_descriptions[0]["entity"]
        return FakeScalarResult(
            [row for row in self.rows if isinstance(row, row_type)]
        )


def test_brpc_diagnosis_tables_are_registered():
    expected_tables = {
        "brpc_diag_schema",
        "brpc_diag_node",
        "brpc_diag_edge",
        "brpc_diag_failure_interface",
        "brpc_diag_failure_subgraph",
        "brpc_diag_batch",
        "brpc_diag_hit",
    }

    assert expected_tables <= set(Base.metadata.tables)
    assert BrpcDiagSchema.__table__.primary_key.columns.keys() == ["schema_id"]
    assert BrpcDiagNode.__table__.primary_key.columns.keys() == [
        "schema_id",
        "node_id",
    ]
    assert BrpcDiagEdge.__table__.primary_key.columns.keys() == [
        "schema_id",
        "source_node_id",
        "target_node_id",
        "edge_type",
    ]
    assert BrpcDiagFailureInterface.__table__.primary_key.columns.keys() == [
        "schema_id",
        "failure_mode_id",
        "interface_id",
    ]
    assert BrpcDiagFailureSubgraph.__table__.primary_key.columns.keys() == [
        "schema_id",
        "failure_mode_id",
    ]
    assert BrpcDiagBatch.__table__.primary_key.columns.keys() == ["batch_id"]
    assert BrpcDiagHit.__table__.primary_key.columns.keys() == ["hit_id"]


def test_brpc_column_types_and_task_uniqueness():
    for column_name in (
        "created_at_timestamp",
        "start_timestamp",
        "end_timestamp",
    ):
        assert isinstance(BrpcDiagBatch.__table__.c[column_name].type, BigInteger)
    for column_name in ("timestamp", "thread_id"):
        assert isinstance(BrpcDiagHit.__table__.c[column_name].type, BigInteger)
    assert isinstance(BrpcDiagHit.__table__.c.message.type, Text)
    assert BrpcDiagHit.__table__.c.message.nullable is False
    assert BrpcDiagHit.__table__.c.interface_id.nullable is True
    assert BrpcDiagHit.__table__.c.interface_resolution.nullable is False
    assert "raw_text" not in BrpcDiagHit.__table__.c
    assert isinstance(BrpcDiagNode.__table__.c.error_code.type, JSONB)
    assert isinstance(
        BrpcDiagFailureSubgraph.__table__.c.subgraph_edge_indexes.type,
        JSONB,
    )

    unique_columns = {
        tuple(constraint.columns.keys())
        for constraint in BrpcDiagBatch.__table__.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    assert ("task_id",) in unique_columns


def test_brpc_foreign_keys_and_batch_hit_cascade():
    node_targets = {
        foreign_key.target_fullname
        for foreign_key in BrpcDiagNode.__table__.foreign_keys
    }
    batch_targets = {
        foreign_key.target_fullname
        for foreign_key in BrpcDiagBatch.__table__.foreign_keys
    }
    hit_foreign_keys = list(BrpcDiagHit.__table__.foreign_keys)

    assert "brpc_diag_schema.schema_id" in node_targets
    assert "brpc_diag_schema.schema_id" in batch_targets
    assert {
        foreign_key.target_fullname for foreign_key in hit_foreign_keys
    } >= {
        "brpc_diag_batch.batch_id",
        "brpc_diag_schema.schema_id",
        "brpc_diag_node.schema_id",
        "brpc_diag_node.node_id",
    }
    batch_fk = next(
        foreign_key
        for foreign_key in hit_foreign_keys
        if foreign_key.target_fullname == "brpc_diag_batch.batch_id"
    )
    assert batch_fk.ondelete == "CASCADE"


def test_all_recommended_brpc_indexes_are_declared():
    ddl = "\n".join(BRPC_DIAG_INDEX_DDL)

    assert len(BRPC_DIAG_INDEX_DDL) == 5
    assert "brpc_diag_hit (batch_id, timestamp)" in ddl
    assert "brpc_diag_hit (batch_id, pod_ip, timestamp)" in ddl
    assert (
        "brpc_diag_hit (batch_id, pod_ip, thread_id, timestamp)"
        in ddl
    )
    assert "pod_ip, component, thread_id" not in ddl
    assert "brpc_diag_hit (batch_id, schema_id, failure_mode_id)" in ddl
    assert (
        "brpc_diag_failure_interface "
        "(schema_id, failure_mode_id, interface_id)"
        in ddl
    )


def test_manager_expands_schema_and_batch_in_caller_session():
    schema = BrpcDiagParser.parse_schema(
        FIXTURES / "valid" / f"schema_{SCHEMA_ID}.json"
    )
    parsed_batch = BrpcDiagParser.parse_batch(
        FIXTURES / "valid" / "batch_task-normal.jsonl",
        {schema.schema_id: schema},
    )
    session = FakeWriteSession()

    async def add_rows():
        await BrpcDiagnosisPGManager.add_schema(session, schema)
        await BrpcDiagnosisPGManager.add_batch(
            session,
            parsed_batch.batch,
            parsed_batch.hits,
        )

    asyncio.run(add_rows())

    row_counts = {
        row_type: sum(isinstance(row, row_type) for row in session.rows)
        for row_type in (
            BrpcDiagSchema,
            BrpcDiagNode,
            BrpcDiagEdge,
            BrpcDiagFailureInterface,
            BrpcDiagFailureSubgraph,
            BrpcDiagBatch,
            BrpcDiagHit,
        )
    }
    assert row_counts == {
        BrpcDiagSchema: 1,
        BrpcDiagNode: len(schema.nodes),
        BrpcDiagEdge: len(schema.edges),
        BrpcDiagFailureInterface: sum(
            len(mapping.interface_ids)
            for mapping in schema.failure_interface_mappings
        ),
        BrpcDiagFailureSubgraph: len(schema.failure_interface_mappings),
        BrpcDiagBatch: 1,
        BrpcDiagHit: len(parsed_batch.hits),
    }
    assert session.flush_count == 5
    assert set(session.flushed_row_types[0]) == {BrpcDiagSchema}
    assert set(session.flushed_row_types[1]) == {BrpcDiagNode}
    assert set(session.flushed_row_types[2]) == {
        BrpcDiagEdge,
        BrpcDiagFailureInterface,
        BrpcDiagFailureSubgraph,
    }
    assert set(session.flushed_row_types[3]) == {BrpcDiagBatch}
    assert set(session.flushed_row_types[4]) == {BrpcDiagHit}
    assert not hasattr(session, "commit")

    hit_rows = [row for row in session.rows if isinstance(row, BrpcDiagHit)]
    assert all(row.batch_id == parsed_batch.batch.batch_id for row in hit_rows)
    assert all(row.schema_id == schema.schema_id for row in hit_rows)
    batch_row = next(
        row for row in session.rows if isinstance(row, BrpcDiagBatch)
    )
    assert batch_row.hit_count == len(parsed_batch.hits)

    loaded_schema = asyncio.run(
        BrpcDiagnosisPGManager.get_schema(
            FakeReadSession(session.rows),
            schema.schema_id,
        )
    )
    assert loaded_schema is not None
    assert loaded_schema.model_dump() == schema.model_dump()
