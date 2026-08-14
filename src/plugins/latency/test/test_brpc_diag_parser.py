from copy import deepcopy
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from latency.parse.brpc_diag_parser import BrpcDiagParseError, BrpcDiagParser
from latency.schemas.brpc_diagnosis import BrpcDiagHit, BrpcDiagSchema


FIXTURES = Path(__file__).parent / "fixtures" / "brpc_diag"
SCHEMA_ID = "1" * 64
SCHEMA_PATH = FIXTURES / "valid" / f"schema_{SCHEMA_ID}.json"


@pytest.fixture
def schema():
    return BrpcDiagParser.parse_schema(SCHEMA_PATH)


def _schema_registry(schema: BrpcDiagSchema) -> dict[str, BrpcDiagSchema]:
    return {schema.schema_id: schema}


def _read_schema_payload() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _read_batch_records(name: str = "batch_task-normal.jsonl") -> list[dict]:
    path = FIXTURES / "valid" / name
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _write_batch(path: Path, records: list[dict]) -> Path:
    path.write_text(
        "".join(json.dumps(record, separators=(",", ":")) + "\n" for record in records),
        encoding="utf-8",
    )
    return path


def test_parse_normal_schema_and_batch(schema):
    parsed = BrpcDiagParser.parse_batch(
        FIXTURES / "valid" / "batch_task-normal.jsonl",
        _schema_registry(schema),
        expected_task_id="task-normal",
    )

    assert schema.format_version == 1
    assert parsed.batch.format_version == 2
    assert {node.component for node in schema.nodes} == {"ubsocket", "umq"}
    assert parsed.batch.schema_id == schema.schema_id
    assert parsed.batch.hit_count == 2
    assert len(parsed.hits) == 2
    assert parsed.hits[0].thread_id == 4567
    assert parsed.hits[0].message == "[ERROR] heap is empty"
    assert parsed.hits[1].pod_ip is None


@pytest.mark.parametrize("component", ["ubsocket", "umq", "urma"])
def test_hit_component_uses_thread_api_vocabulary(component):
    records = _read_batch_records()
    hit = deepcopy(records[1])
    hit["component"] = component

    assert BrpcDiagHit.model_validate(hit).component == component


@pytest.mark.parametrize("component", ["UBSOCKET", "UMQ", "URMA"])
def test_hit_component_rejects_raw_names(component):
    records = _read_batch_records()
    hit = deepcopy(records[1])
    hit["component"] = component

    with pytest.raises(ValidationError):
        BrpcDiagHit.model_validate(hit)


def test_batch_without_hits_is_valid(schema):
    parsed = BrpcDiagParser.parse_batch(
        FIXTURES / "valid" / "batch_task-empty.jsonl",
        _schema_registry(schema),
    )

    assert parsed.batch.task_id == "task-empty"
    assert parsed.hits == ()


def test_retry_fixtures_keep_task_id_but_change_batch_id(schema):
    first = BrpcDiagParser.parse_batch(
        FIXTURES / "retry_first" / "batch_task-retry.jsonl",
        _schema_registry(schema),
    )
    second = BrpcDiagParser.parse_batch(
        FIXTURES / "retry_second" / "batch_task-retry.jsonl",
        _schema_registry(schema),
    )

    assert first.batch.task_id == second.batch.task_id == "task-retry"
    assert first.batch.batch_id != second.batch.batch_id
    assert len(first.hits) == 1
    assert second.hits == ()


def test_schema_with_same_id_must_have_same_content(schema):
    with pytest.raises(BrpcDiagParseError, match="content conflicts"):
        BrpcDiagParser.parse_schema(
            FIXTURES / "invalid" / f"schema_{SCHEMA_ID}.json",
            _schema_registry(schema),
        )


def test_schema_graph_constraints_are_rejected():
    valid = _read_schema_payload()
    invalid_payloads = []

    urma_payload = deepcopy(valid)
    for node in urma_payload["nodes"]:
        node["component"] = "urma"
    assert {
        node.component for node in BrpcDiagSchema.model_validate(urma_payload).nodes
    } == {"urma"}

    payload = deepcopy(valid)
    payload["format_version"] = 2
    invalid_payloads.append(payload)

    payload = deepcopy(valid)
    payload["schema_id"] = "A" * 64
    invalid_payloads.append(payload)

    payload = deepcopy(valid)
    payload["nodes"].append(deepcopy(payload["nodes"][0]))
    invalid_payloads.append(payload)

    payload = deepcopy(valid)
    payload["nodes"][0]["node_type"] = "public_api"
    invalid_payloads.append(payload)

    payload = deepcopy(valid)
    payload["nodes"][0]["component"] = "brpc"
    invalid_payloads.append(payload)

    payload = deepcopy(valid)
    payload["edges"][0]["target_node_id"] = "ubsocket_unknown"
    invalid_payloads.append(payload)

    payload = deepcopy(valid)
    payload["edges"][0]["edge_type"] = "unknown_edge"
    invalid_payloads.append(payload)

    payload = deepcopy(valid)
    payload["failure_interface_mappings"] = payload[
        "failure_interface_mappings"
    ][1:]
    invalid_payloads.append(payload)

    payload = deepcopy(valid)
    payload["failure_interface_mappings"].append(
        deepcopy(payload["failure_interface_mappings"][0])
    )
    invalid_payloads.append(payload)

    payload = deepcopy(valid)
    payload["failure_interface_mappings"][0]["interface_ids"] = []
    invalid_payloads.append(payload)

    payload = deepcopy(valid)
    payload["failure_interface_mappings"][0]["interface_ids"] *= 2
    invalid_payloads.append(payload)

    payload = deepcopy(valid)
    payload["failure_interface_mappings"][0]["interface_ids"] = ["umq_001"]
    invalid_payloads.append(payload)

    payload = deepcopy(valid)
    payload["failure_interface_mappings"][0]["subgraph_edge_indexes"] = []
    invalid_payloads.append(payload)

    payload = deepcopy(valid)
    payload["failure_interface_mappings"][0]["subgraph_edge_indexes"] *= 2
    invalid_payloads.append(payload)

    payload = deepcopy(valid)
    payload["failure_interface_mappings"][0]["subgraph_edge_indexes"] = [99]
    invalid_payloads.append(payload)

    for payload in invalid_payloads:
        with pytest.raises(ValidationError):
            BrpcDiagSchema.model_validate(payload)


@pytest.mark.parametrize(
    ("filename", "message"),
    [
        ("batch_task-out-of-range.jsonl", "outside"),
        ("batch_task-duplicate-hit.jsonl", "duplicate hit_id"),
        ("batch_task-unknown-failure.jsonl", "unknown failure mode"),
    ],
)
def test_invalid_hit_fixtures_are_rejected(schema, filename, message):
    with pytest.raises(BrpcDiagParseError, match=message):
        BrpcDiagParser.parse_batch(
            FIXTURES / "invalid" / filename,
            _schema_registry(schema),
        )


def test_batch_referencing_missing_schema_is_rejected():
    with pytest.raises(BrpcDiagParseError, match="unknown schema_id"):
        BrpcDiagParser.parse_batch(
            FIXTURES / "invalid" / "batch_task-missing-schema.jsonl",
            {},
        )


def test_batch_filename_and_expected_task_id_must_match(schema, tmp_path):
    records = _read_batch_records()
    wrong_filename = _write_batch(tmp_path / "batch_other-task.jsonl", records)
    with pytest.raises(BrpcDiagParseError, match="does not match task_id"):
        BrpcDiagParser.parse_batch(wrong_filename, _schema_registry(schema))

    valid_filename = _write_batch(tmp_path / "batch_task-normal.jsonl", records)
    with pytest.raises(BrpcDiagParseError, match="expected task_id"):
        BrpcDiagParser.parse_batch(
            valid_filename,
            _schema_registry(schema),
            expected_task_id="another-task",
        )


def test_batch_record_must_be_first_and_unique(schema, tmp_path):
    records = _read_batch_records()

    hit_first = [records[1], records[0]]
    path = _write_batch(tmp_path / "batch_task-normal.jsonl", hit_first)
    with pytest.raises(BrpcDiagParseError, match="first record"):
        BrpcDiagParser.parse_batch(path, _schema_registry(schema))

    repeated_batch = [records[0], records[0]]
    path = _write_batch(tmp_path / "batch_task-normal.jsonl", repeated_batch)
    with pytest.raises(BrpcDiagParseError, match="only once"):
        BrpcDiagParser.parse_batch(path, _schema_registry(schema))


def test_batch_and_hit_required_fields_are_enforced(schema, tmp_path):
    records = _read_batch_records()
    del records[0]["format_version"]
    path = _write_batch(tmp_path / "batch_task-normal.jsonl", records)
    with pytest.raises(BrpcDiagParseError, match="invalid batch record"):
        BrpcDiagParser.parse_batch(path, _schema_registry(schema))

    records = _read_batch_records()
    del records[1]["message"]
    path = _write_batch(tmp_path / "batch_task-normal.jsonl", records)
    with pytest.raises(BrpcDiagParseError, match="invalid hit record"):
        BrpcDiagParser.parse_batch(path, _schema_registry(schema))

    records = _read_batch_records()
    records[1]["raw_text"] = records[1].pop("message")
    path = _write_batch(tmp_path / "batch_task-normal.jsonl", records)
    with pytest.raises(BrpcDiagParseError, match="invalid hit record"):
        BrpcDiagParser.parse_batch(path, _schema_registry(schema))


def test_hit_id_must_use_current_batch_and_sequence(schema, tmp_path):
    records = _read_batch_records()
    records[1]["hit_id"] = "another-batch:hit:0"
    path = _write_batch(tmp_path / "batch_task-normal.jsonl", records)

    with pytest.raises(BrpcDiagParseError, match="does not match expected ID"):
        BrpcDiagParser.parse_batch(path, _schema_registry(schema))


def test_batch_hit_count_must_match_jsonl_records(schema, tmp_path):
    records = _read_batch_records()
    records[0]["hit_count"] = 1
    path = _write_batch(tmp_path / "batch_task-normal.jsonl", records)

    with pytest.raises(BrpcDiagParseError, match="hit_count"):
        BrpcDiagParser.parse_batch(path, _schema_registry(schema))


def test_interface_node_cannot_be_used_as_failure_mode(schema, tmp_path):
    records = _read_batch_records()
    records[1]["failure_mode_id"] = "ubsocket_001"
    path = _write_batch(tmp_path / "batch_task-normal.jsonl", records)

    with pytest.raises(BrpcDiagParseError, match="unknown failure mode"):
        BrpcDiagParser.parse_batch(path, _schema_registry(schema))


def test_hit_resolved_interface_must_be_a_candidate(schema, tmp_path):
    records = _read_batch_records()
    records[1]["interface_id"] = "ubsocket_001"
    records[1]["interface_resolution"] = "static_unique"
    path = _write_batch(tmp_path / "batch_task-normal.jsonl", records)

    parsed = BrpcDiagParser.parse_batch(path, _schema_registry(schema))
    assert parsed.hits[0].interface_id == "ubsocket_001"

    records = _read_batch_records()
    records[1]["interface_id"] = "umq_001"
    records[1]["interface_resolution"] = "thread_chain"
    path = _write_batch(tmp_path / "batch_task-normal.jsonl", records)
    with pytest.raises(BrpcDiagParseError, match="is not a candidate"):
        BrpcDiagParser.parse_batch(path, _schema_registry(schema))


def test_hit_resolution_and_interface_must_agree():
    records = _read_batch_records()
    hit = records[1]
    hit["interface_id"] = "ubsocket_001"
    with pytest.raises(ValidationError, match="interface_id must be set"):
        BrpcDiagHit.model_validate(hit)
