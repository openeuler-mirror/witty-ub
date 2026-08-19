"""Parser and cross-record validation for BRPC diagnosis V2.1 files."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from latency.schemas.brpc_diagnosis import (
    BrpcDiagBatch,
    BrpcDiagHit,
    BrpcDiagSchema,
)


class BrpcDiagParseError(ValueError):
    """Raised when a BRPC diagnosis output violates the V2.1 protocol."""


@dataclass(frozen=True, slots=True)
class ParsedBrpcDiagBatch:
    batch: BrpcDiagBatch
    hits: tuple[BrpcDiagHit, ...]


def _load_json_object(content: str, source: Path, line_number: int | None = None) -> dict[str, Any]:
    location = str(source)
    if line_number is not None:
        location += f":{line_number}"
    try:
        value = json.loads(content)
    except json.JSONDecodeError as exc:
        raise BrpcDiagParseError(f"invalid JSON at {location}: {exc.msg}") from exc
    if not isinstance(value, dict):
        raise BrpcDiagParseError(f"JSON record at {location} must be an object")
    return value


def _schema_content(schema: BrpcDiagSchema) -> dict[str, Any]:
    """Return order-independent schema content for same-ID conflict checks."""

    return {
        "format_version": schema.format_version,
        "nodes": sorted(
            (node.model_dump(mode="json") for node in schema.nodes),
            key=lambda node: node["node_id"],
        ),
        "edges": sorted(
            (edge.model_dump(mode="json") for edge in schema.edges),
            key=lambda edge: (
                edge["source_node_id"],
                edge["target_node_id"],
                edge["edge_type"],
            ),
        ),
        "failure_interface_mappings": sorted(
            (
                {
                    "failure_mode_id": mapping.failure_mode_id,
                    "interface_ids": sorted(mapping.interface_ids),
                    "subgraph_edge_indexes": sorted(
                        mapping.subgraph_edge_indexes
                    ),
                }
                for mapping in schema.failure_interface_mappings
            ),
            key=lambda mapping: mapping["failure_mode_id"],
        ),
    }


def ensure_same_schema_content(
    existing: BrpcDiagSchema, incoming: BrpcDiagSchema
) -> None:
    """Reject two different schema payloads that claim the same schema ID."""

    if existing.schema_id != incoming.schema_id:
        raise BrpcDiagParseError(
            f"cannot compare different schema IDs: {existing.schema_id}, "
            f"{incoming.schema_id}"
        )
    if _schema_content(existing) != _schema_content(incoming):
        raise BrpcDiagParseError(
            f"schema content conflicts with existing schema_id {incoming.schema_id}"
        )


class BrpcDiagParser:
    @staticmethod
    def parse_schema(
        schema_path: str | Path,
        known_schemas: Mapping[str, BrpcDiagSchema] | None = None,
    ) -> BrpcDiagSchema:
        path = Path(schema_path)
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise BrpcDiagParseError(f"cannot read schema file {path}: {exc}") from exc

        raw_schema = _load_json_object(content, path)
        try:
            schema = BrpcDiagSchema.model_validate(raw_schema)
        except ValidationError as exc:
            raise BrpcDiagParseError(f"invalid schema file {path}: {exc}") from exc

        expected_filename = f"schema_{schema.schema_id}.json"
        if path.name != expected_filename:
            raise BrpcDiagParseError(
                f"schema filename {path.name!r} does not match schema_id; "
                f"expected {expected_filename!r}"
            )

        if known_schemas is not None and schema.schema_id in known_schemas:
            ensure_same_schema_content(known_schemas[schema.schema_id], schema)
        return schema

    @staticmethod
    def parse_batch(
        batch_path: str | Path,
        schemas: Mapping[str, BrpcDiagSchema],
        expected_task_id: str | None = None,
    ) -> ParsedBrpcDiagBatch:
        path = Path(batch_path)
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeError) as exc:
            raise BrpcDiagParseError(f"cannot read batch file {path}: {exc}") from exc
        if not lines:
            raise BrpcDiagParseError(f"batch file {path} is empty")

        records: list[dict[str, Any]] = []
        for line_number, line in enumerate(lines, start=1):
            if not line.strip():
                raise BrpcDiagParseError(
                    f"empty JSONL record at {path}:{line_number}"
                )
            records.append(_load_json_object(line, path, line_number))

        if records[0].get("record_type") != "batch":
            raise BrpcDiagParseError(
                f"the first record in {path} must have record_type=batch"
            )
        try:
            batch = BrpcDiagBatch.model_validate(records[0])
        except ValidationError as exc:
            raise BrpcDiagParseError(f"invalid batch record at {path}:1: {exc}") from exc

        expected_filename = f"batch_{batch.task_id}.jsonl"
        if path.name != expected_filename:
            raise BrpcDiagParseError(
                f"batch filename {path.name!r} does not match task_id; "
                f"expected {expected_filename!r}"
            )
        if expected_task_id is not None and batch.task_id != expected_task_id:
            raise BrpcDiagParseError(
                f"batch task_id {batch.task_id!r} does not match expected task_id "
                f"{expected_task_id!r}"
            )

        schema = schemas.get(batch.schema_id)
        if schema is None:
            raise BrpcDiagParseError(
                f"batch references unknown schema_id {batch.schema_id}"
            )
        failure_mode_ids = {
            node.node_id
            for node in schema.nodes
            if node.node_type == "failure_mode"
        }
        interface_ids = {
            node.node_id
            for node in schema.nodes
            if node.node_type == "interface"
        }
        candidate_interfaces = {
            mapping.failure_mode_id: set(mapping.interface_ids)
            for mapping in schema.failure_interface_mappings
        }

        hits: list[BrpcDiagHit] = []
        hit_ids: set[str] = set()
        for hit_index, raw_hit in enumerate(records[1:]):
            line_number = hit_index + 2
            if raw_hit.get("record_type") == "batch":
                raise BrpcDiagParseError(
                    f"batch record must occur only once and on the first line: "
                    f"{path}:{line_number}"
                )
            try:
                hit = BrpcDiagHit.model_validate(raw_hit)
            except ValidationError as exc:
                raise BrpcDiagParseError(
                    f"invalid hit record at {path}:{line_number}: {exc}"
                ) from exc

            if hit.hit_id in hit_ids:
                raise BrpcDiagParseError(f"duplicate hit_id: {hit.hit_id}")
            hit_ids.add(hit.hit_id)
            expected_hit_id = f"{batch.batch_id}:hit:{hit_index}"
            if hit.hit_id != expected_hit_id:
                raise BrpcDiagParseError(
                    f"hit_id {hit.hit_id!r} does not match expected ID "
                    f"{expected_hit_id!r}"
                )
            if not batch.start_timestamp <= hit.timestamp < batch.end_timestamp:
                raise BrpcDiagParseError(
                    f"hit {hit.hit_id} timestamp {hit.timestamp} is outside "
                    f"[{batch.start_timestamp}, {batch.end_timestamp})"
                )
            if hit.failure_mode_id not in failure_mode_ids:
                raise BrpcDiagParseError(
                    f"hit {hit.hit_id} references unknown failure mode "
                    f"{hit.failure_mode_id}"
                )
            if hit.interface_id is not None:
                if hit.interface_id not in interface_ids:
                    raise BrpcDiagParseError(
                        f"hit {hit.hit_id} references unknown interface "
                        f"{hit.interface_id}"
                    )
                if hit.interface_id not in candidate_interfaces[hit.failure_mode_id]:
                    raise BrpcDiagParseError(
                        f"hit {hit.hit_id} interface {hit.interface_id} is not a "
                        f"candidate for failure mode {hit.failure_mode_id}"
                    )
            hits.append(hit)

        if len(hits) != batch.hit_count:
            raise BrpcDiagParseError(
                f"batch hit_count {batch.hit_count} does not match "
                f"{len(hits)} hit records"
            )

        return ParsedBrpcDiagBatch(batch=batch, hits=tuple(hits))


parse_schema = BrpcDiagParser.parse_schema
parse_batch = BrpcDiagParser.parse_batch
