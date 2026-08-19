"""Atomic importer for BRPC diagnosis V2.1 output files."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from latency.database.engine import PGManager
from latency.database.managers.brpc_diagnosis import BrpcDiagnosisPGManager
from latency.parse.brpc_diag_parser import (
    BrpcDiagParser,
    ensure_same_schema_content,
)
from latency.schemas.brpc_diagnosis import BrpcDiagBatch, BrpcDiagHit


_MICROSECONDS_PER_SECOND = 1_000_000


def _normalize_batch_time_range(
    batch: BrpcDiagBatch,
    hits: tuple[BrpcDiagHit, ...],
) -> BrpcDiagBatch:
    """Describe imported hits, not a potentially unbounded scan interval."""
    if not hits:
        end_timestamp = (
            batch.created_at_timestamp // _MICROSECONDS_PER_SECOND + 1
        ) * _MICROSECONDS_PER_SECOND
        return batch.model_copy(
            update={
                "start_timestamp": batch.created_at_timestamp,
                "end_timestamp": end_timestamp,
            }
        )
    start_timestamp = min(hit.timestamp for hit in hits)
    last_timestamp = max(hit.timestamp for hit in hits)
    end_timestamp = (
        last_timestamp // _MICROSECONDS_PER_SECOND + 1
    ) * _MICROSECONDS_PER_SECOND
    return batch.model_copy(
        update={
            "start_timestamp": start_timestamp,
            "end_timestamp": end_timestamp,
        }
    )


@dataclass(frozen=True, slots=True)
class BrpcDiagnosisImportResult:
    status: Literal["imported", "skipped"]
    task_id: str
    batch_id: str
    schema_id: str
    hit_count: int
    schema_created: bool
    replaced_batch_id: str | None = None


class BrpcDiagnosisImporter:
    """Validate and persist one explicitly selected schema/batch pair."""

    @staticmethod
    async def import_result(
        *,
        schema_path: str | Path,
        batch_path: str | Path,
        expected_task_id: str,
    ) -> BrpcDiagnosisImportResult:
        async with PGManager.session() as session:
            schema = BrpcDiagParser.parse_schema(schema_path)
            stored_schema = await BrpcDiagnosisPGManager.get_schema(
                session, schema.schema_id
            )
            schema_created = stored_schema is None
            if stored_schema is None:
                await BrpcDiagnosisPGManager.add_schema(session, schema)
            else:
                ensure_same_schema_content(stored_schema, schema)

            parsed_batch = BrpcDiagParser.parse_batch(
                batch_path,
                {schema.schema_id: schema},
                expected_task_id=expected_task_id,
            )
            batch = _normalize_batch_time_range(
                parsed_batch.batch,
                parsed_batch.hits,
            )

            if await BrpcDiagnosisPGManager.batch_exists(
                session, batch.batch_id
            ):
                return BrpcDiagnosisImportResult(
                    status="skipped",
                    task_id=batch.task_id,
                    batch_id=batch.batch_id,
                    schema_id=batch.schema_id,
                    hit_count=len(parsed_batch.hits),
                    schema_created=schema_created,
                )

            existing_batch = await BrpcDiagnosisPGManager.get_batch_by_task_id(
                session, batch.task_id
            )
            replaced_batch_id = None
            if existing_batch is not None:
                replaced_batch_id = existing_batch.batch_id
                await BrpcDiagnosisPGManager.delete_batch(
                    session, existing_batch.batch_id
                )

            await BrpcDiagnosisPGManager.add_batch(
                session,
                batch,
                parsed_batch.hits,
            )
            return BrpcDiagnosisImportResult(
                status="imported",
                task_id=batch.task_id,
                batch_id=batch.batch_id,
                schema_id=batch.schema_id,
                hit_count=len(parsed_batch.hits),
                schema_created=schema_created,
                replaced_batch_id=replaced_batch_id,
            )
