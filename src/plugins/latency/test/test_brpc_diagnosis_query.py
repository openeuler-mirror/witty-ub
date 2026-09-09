import asyncio
import zipfile
from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest
from fastapi import FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient
from sqlalchemy.dialects import postgresql

import latency.services.brpc_diagnosis as service_module
from latency.database.managers.brpc_diagnosis import BrpcDiagnosisPGManager
from latency.database.managers.log_file import LogFilePGManager
from latency.database.managers.task import TaskPGManager
from latency.exceptions import BadRequestBizException, NotFoundBizException
from latency.routers.brpc_diagnosis import _build_metric_sort_fields, router
from latency.schemas.brpc_diagnosis import (
    GetBrpcBatchResponse,
    GetBrpcInterfaceTimelineResponse,
    ListBrpcDiagHitsMsg,
    ListBrpcDiagHitsResponse,
    parse_brpc_query_timestamp,
)
from latency.services.brpc_diagnosis import BrpcDiagnosisService


BATCH_ID = "0198aaaa-1111-7111-8111-111111111111"
SCHEMA_ID = "1" * 64
POD_IP = "10.0.0.1"
THREAD_ID = 9


class QueryStore:
    def __init__(self):
        self.batch = SimpleNamespace(
            batch_id=BATCH_ID,
            task_id="task-normal",
            schema_id=SCHEMA_ID,
            created_at_timestamp=1_786_000_063_000_000,
            start_timestamp=1_786_000_061_000_000,
            end_timestamp=1_786_000_082_000_000,
            hit_count=2,
        )
        self.hits = [
            SimpleNamespace(
                hit_id=f"{BATCH_ID}:hit:1",
                batch_id=BATCH_ID,
                schema_id=SCHEMA_ID,
                failure_mode_id="umq.failure.1",
                timestamp=1_786_000_071_000_000,
                pod_name="pod-a",
                pod_ip="10.0.0.1",
                component="umq",
                filename="umq.cc",
                function_name="Send",
                line_number=42,
                thread_id=9,
                trace_id="trace-a",
                message="newest",
            ),
            SimpleNamespace(
                hit_id=f"{BATCH_ID}:hit:0",
                batch_id=BATCH_ID,
                schema_id=SCHEMA_ID,
                failure_mode_id="umq.failure.1",
                timestamp=1_786_000_062_000_000,
                pod_name=None,
                pod_ip=None,
                component="umq",
                filename=None,
                function_name=None,
                line_number=None,
                thread_id=None,
                trace_id=None,
                message="oldest",
            ),
        ]
        self.hit_calls = []
        self.timeline_calls = []
        self.timeline_bucket_calls = []

    @asynccontextmanager
    async def session(self):
        yield SimpleNamespace()


def _configure_store(monkeypatch, store: QueryStore):
    class QueryManager:
        @staticmethod
        async def get_batch_by_task_id(_session, task_id):
            return store.batch if task_id == store.batch.task_id else None

        @staticmethod
        async def get_batch(_session, batch_id):
            return store.batch if batch_id == store.batch.batch_id else None

        @staticmethod
        async def list_hits(_session, **kwargs):
            store.hit_calls.append(kwargs)
            return len(store.hits), store.hits

        @staticmethod
        async def get_interface_timeline_aggregates(session, **kwargs):
            del session
            store.timeline_calls.append(kwargs)
            rows = [
                {
                    "window_start_timestamp": 1_786_000_060_000_000,
                    "component": "umq",
                    "interface_id": "umq.interface.send",
                    "interface_name": "Send",
                    "function_name": "umq_send",
                    "interface_hit_count": 2,
                },
                {
                    "window_start_timestamp": 1_786_000_080_000_000,
                    "component": "umq",
                    "interface_id": "umq.interface.send",
                    "interface_name": "Send",
                    "function_name": "umq_send",
                    "interface_hit_count": 1,
                },
                {
                    "window_start_timestamp": 1_786_000_060_000_000,
                    "component": "umq",
                    "interface_id": "umq.interface.publish",
                    "interface_name": "Publish",
                    "function_name": "umq_publish",
                    "interface_hit_count": 2,
                },
            ]
            return [
                row
                for row in rows
                if row["window_start_timestamp"] < kwargs["end_timestamp"]
                and row["window_start_timestamp"] + kwargs["window_us"]
                > kwargs["start_timestamp"]
            ]

        @staticmethod
        async def get_interface_timeline_bucket_aggregates(session, **kwargs):
            del session
            store.timeline_bucket_calls.append(kwargs)
            return []

    monkeypatch.setattr(
        service_module,
        "PGManager",
        SimpleNamespace(session=store.session),
    )
    monkeypatch.setattr(service_module, "BrpcDiagnosisPGManager", QueryManager)


def test_task_batch_and_batch_metadata_queries(monkeypatch):
    store = QueryStore()
    _configure_store(monkeypatch, store)

    task_result = asyncio.run(
        BrpcDiagnosisService.get_batch_by_task_id("task-normal")
    )
    batch_result = asyncio.run(BrpcDiagnosisService.get_batch(BATCH_ID))

    assert task_result.model_dump() == {
        "task_id": "task-normal",
        "batch_id": BATCH_ID,
    }
    assert batch_result.batch.model_dump() == {
        "batch_id": BATCH_ID,
        "task_id": "task-normal",
        "schema_id": SCHEMA_ID,
        "created_at_time": 1_786_000_063_000_000,
        "start_time": 1_786_000_061_000_000,
        "end_time": 1_786_000_082_000_000,
        "hit_count": 2,
    }


def test_missing_batch_is_not_reported_as_an_empty_result(monkeypatch):
    store = QueryStore()
    _configure_store(monkeypatch, store)

    with pytest.raises(NotFoundBizException):
        asyncio.run(BrpcDiagnosisService.get_batch("missing"))
    with pytest.raises(NotFoundBizException):
        asyncio.run(
            BrpcDiagnosisService.list_hits(
                batch_id="missing",
                pod_ip=POD_IP,
                thread_id=THREAD_ID,
                page_num=1,
                page_cnt=100,
            )
        )


def test_hits_are_returned_with_single_batch_pagination(monkeypatch):
    store = QueryStore()
    _configure_store(monkeypatch, store)

    result = asyncio.run(
        BrpcDiagnosisService.list_hits(
            batch_id=BATCH_ID,
            pod_ip=POD_IP,
            thread_id=THREAD_ID,
            page_num=2,
            page_cnt=1,
            start_timestamp=1_786_000_061_000_000,
            end_timestamp=1_786_000_082_000_000,
            pod_name="pod-a",
        )
    )

    assert result.batch_id == BATCH_ID
    assert result.total == 2
    assert [hit.message for hit in result.hits] == ["newest", "oldest"]
    assert store.hit_calls == [
        {
            "batch_id": BATCH_ID,
            "pod_ip": POD_IP,
            "thread_id": THREAD_ID,
            "page_num": 2,
            "page_cnt": 1,
            "start_timestamp": 1_786_000_061_000_000,
            "end_timestamp": 1_786_000_082_000_000,
            "pod_name": "pod-a",
        }
    ]


@pytest.mark.parametrize(
    "source_layout",
    ["local_archive", "uploaded_zip", "directory_archive"],
)
def test_thread_logs_read_preprocessed_archive_sources(
    monkeypatch, tmp_path, source_layout
):
    store = QueryStore()
    _configure_store(monkeypatch, store)
    log_line = (
        "[20260804 01:47:51.000000][pod-a][10.0.0.1][UMQ]"
        "[umq.cc:Send:42][9][trace-a] runtime line\n"
    )
    archive_path = tmp_path / "logs.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("nested/10.0.0.1.log", log_line)
    if source_layout == "directory_archive":
        source_path = tmp_path / "server-logs"
        source_path.mkdir()
        archive_path.rename(source_path / archive_path.name)
    else:
        # LOCAL archive paths and browser UPLOADs both persist as an archive
        # path in LogFile.file_path; their runtime-log read path is identical.
        source_path = archive_path

    async def get_task(task_id):
        return (
            SimpleNamespace(op_id="log-file-id")
            if task_id == "task-normal"
            else None
        )

    async def get_log_file(log_file_id):
        if log_file_id != "log-file-id":
            return None
        return SimpleNamespace(id=log_file_id, file_path=str(source_path))

    monkeypatch.setattr(TaskPGManager, "get_task_by_task_id", get_task)
    monkeypatch.setattr(
        LogFilePGManager, "get_log_file_by_log_file_id", get_log_file
    )
    monkeypatch.setattr(
        service_module,
        "default_preprocess_dir",
        lambda _log_file_id: str(tmp_path / "preprocessed"),
    )
    monkeypatch.setattr(service_module, "needs_preprocess", lambda _source: True)

    def preprocess(_source, output):
        output_path = tmp_path / "preprocessed"
        output_path.mkdir(exist_ok=True)
        source_archive = (
            next(source_path.glob("*.zip"))
            if source_path.is_dir()
            else source_path
        )
        with zipfile.ZipFile(source_archive) as archive:
            archive.extractall(output_path)
        return SimpleNamespace(output_dir=output)

    monkeypatch.setattr(service_module, "preprocess_log_dir", preprocess)

    async def run_inline(function, *args):
        return function(*args)

    monkeypatch.setattr(service_module.asyncio, "to_thread", run_inline)

    result = asyncio.run(
        BrpcDiagnosisService.list_thread_logs(
            batch_id=BATCH_ID,
            pod_ip=POD_IP,
            thread_id=THREAD_ID,
        )
    )

    assert result.total == 1
    assert result.hits[0].message == "runtime line"


def test_brpc_response_times_are_serialized_as_utc_plus_8_strings(monkeypatch):
    store = QueryStore()
    _configure_store(monkeypatch, store)

    batch_result = asyncio.run(BrpcDiagnosisService.get_batch(BATCH_ID))
    hits_result = asyncio.run(
        BrpcDiagnosisService.list_hits(
            batch_id=BATCH_ID,
            pod_ip=POD_IP,
            thread_id=THREAD_ID,
            page_num=1,
            page_cnt=100,
        )
    )
    timeline_result = asyncio.run(
        BrpcDiagnosisService.get_interface_timeline(
            batch_id=BATCH_ID,
            start_timestamp=1_786_000_061_000_000,
            end_timestamp=1_786_000_082_000_000,
            window_size="10s",
        )
    )

    batch_json = GetBrpcBatchResponse(result=batch_result).model_dump(
        mode="json"
    )
    hits_json = ListBrpcDiagHitsResponse(result=hits_result).model_dump(
        mode="json"
    )
    timeline_json = GetBrpcInterfaceTimelineResponse(
        result=timeline_result
    ).model_dump(mode="json")

    assert batch_json["result"]["batch"]["created_at_time"] == (
        "2026-08-06 15:07:43"
    )
    assert "created_at_us" not in batch_json["result"]["batch"]
    assert batch_json["result"]["batch"]["start_time"] == (
        "2026-08-06 15:07:41"
    )
    assert hits_json["result"]["hits"][0]["time"] == (
        "2026-08-06 15:07:51"
    )
    assert "timestamp" not in hits_json["result"]["hits"][0]
    assert hits_json["result"]["hits"][0]["message"] == "newest"
    assert "raw_text" not in hits_json["result"]["hits"][0]
    assert timeline_json["result"]["start_time"] == (
        "2026-08-06 15:07:41"
    )
    assert timeline_json["result"]["series"][0]["points"][0][
        "window_start_time"
    ] == "2026-08-06 15:07:40"


def test_brpc_response_openapi_declares_time_fields_as_strings():
    app = FastAPI()
    app.include_router(router)
    schemas = app.openapi()["components"]["schemas"]

    time_fields_by_schema = {
        "BrpcDiagBatchMetadata-Output": {
            "created_at_time",
            "start_time",
            "end_time",
        },
        "BrpcDiagHitLog-Output": {"time"},
        "BrpcInterfaceTimelinePoint-Output": {
            "window_start_time",
            "window_end_time",
        },
        "GetBrpcInterfaceTimelineMsg-Output": {"start_time", "end_time"},
        "BrpcPodAggregatedEvent-Output": {
            "window_start_time",
            "window_end_time",
        },
        "BrpcThreadAggregatedEvent-Output": {
            "window_start_time",
            "window_end_time",
        },
        "BrpcAbnormalThread-Output": {
            "first_hit_time",
            "last_hit_time",
        },
        "GetBrpcAbnormalThreadDetailMsg-Output": {"start_time", "end_time"},
    }
    for schema_name, field_names in time_fields_by_schema.items():
        properties = schemas[schema_name]["properties"]
        for field_name in field_names:
            assert properties[field_name]["type"] == "string"
    assert "component" not in schemas["BrpcThreadAggregatedEvent-Output"][
        "properties"
    ]
    assert "component" not in schemas["BrpcAbnormalThread-Output"][
        "properties"
    ]


def test_interface_timeline_is_epoch_aligned_and_zero_filled(monkeypatch):
    store = QueryStore()
    _configure_store(monkeypatch, store)
    start_timestamp = 1_786_000_061_000_000
    end_timestamp = 1_786_000_082_000_000

    result = asyncio.run(
        BrpcDiagnosisService.get_interface_timeline(
            batch_id=BATCH_ID,
            start_timestamp=start_timestamp,
            end_timestamp=end_timestamp,
            window_size="10s",
            component="umq",
            interface_id=None,
            pod_ip=POD_IP,
            pod_name="pod-a",
        )
    )

    assert len(result.series) == 2
    series_by_id = {item.interface_id: item for item in result.series}
    assert [
        point.window_start_time
        for point in series_by_id["umq.interface.send"].points
    ] == [
        1_786_000_060_000_000,
        1_786_000_070_000_000,
        1_786_000_080_000_000,
    ]
    assert [
        point.interface_hit_count
        for point in series_by_id["umq.interface.send"].points
    ] == [2, 0, 1]
    assert [
        point.interface_hit_count
        for point in series_by_id["umq.interface.publish"].points
    ] == [2, 0, 0]
    assert series_by_id["umq.interface.send"].function_name == "umq_send"
    assert series_by_id["umq.interface.publish"].function_name == "umq_publish"
    assert len(store.timeline_bucket_calls) == 1
    assert (
        store.timeline_bucket_calls[0]["start_timestamp"]
        == 1_786_000_070_000_000
    )
    assert (
        store.timeline_bucket_calls[0]["end_timestamp"]
        == 1_786_000_080_000_000
    )
    assert len(store.timeline_calls) == 2
    assert store.timeline_calls[0]["batch_id"] == BATCH_ID
    assert store.timeline_calls[0]["window_us"] == 10_000_000
    assert store.timeline_calls[0]["pod_ip"] == POD_IP
    assert store.timeline_calls[0]["pod_name"] == "pod-a"


def test_unfiltered_interface_timeline_always_includes_unresolved_series(monkeypatch):
    store = QueryStore()
    _configure_store(monkeypatch, store)

    result = asyncio.run(
        BrpcDiagnosisService.get_interface_timeline(
            batch_id=BATCH_ID,
            start_timestamp=1_786_000_061_000_000,
            end_timestamp=1_786_000_082_000_000,
            window_size="10s",
        )
    )

    unresolved = next(
        item for item in result.series if item.interface_id == "__unresolved__"
    )
    assert unresolved.component == "unknown"
    assert unresolved.interface_name == "未确定接口"
    assert [point.interface_hit_count for point in unresolved.points] == [0, 0, 0]


def test_invalid_query_intervals_are_rejected_before_database_access():
    with pytest.raises(BadRequestBizException):
        asyncio.run(
            BrpcDiagnosisService.get_interface_timeline(
                batch_id=BATCH_ID,
                start_timestamp=100,
                end_timestamp=100,
                window_size="10s",
            )
        )


def test_query_routes_are_registered_for_batch_and_knowledge_scopes():
    app = FastAPI()
    app.include_router(router)
    paths = app.openapi()["paths"]

    assert set(paths) == {
        "/brpc-diagnosis/task/{task_id}/batch",
        "/brpc-diagnosis/batch/{batch_id}",
        "/brpc-diagnosis/batch/{batch_id}/hits",
        "/brpc-diagnosis/batch/{batch_id}/thread-logs",
        "/brpc-diagnosis/batch/{batch_id}/interface-timeline",
        "/brpc-diagnosis/batch/{batch_id}/pod-events",
        "/brpc-diagnosis/batch/{batch_id}/pod-events/{event_id}",
        "/brpc-diagnosis/batch/{batch_id}/thread-events",
        "/brpc-diagnosis/batch/{batch_id}/thread-events/{event_id}",
        "/brpc-diagnosis/batch/{batch_id}/abnormal-threads",
        "/brpc-diagnosis/batch/{batch_id}/abnormal-threads/{thread_key}",
        "/brpc-diagnosis/knowledge/{kb_id}/scope",
        "/brpc-diagnosis/knowledge/{kb_id}/interface-timeline",
        "/brpc-diagnosis/knowledge/{kb_id}/pod-events",
        "/brpc-diagnosis/knowledge/{kb_id}/thread-events",
        "/brpc-diagnosis/knowledge/{kb_id}/abnormal-threads",
    }
    timeline_parameters = paths[
        "/brpc-diagnosis/batch/{batch_id}/interface-timeline"
    ]["get"]["parameters"]
    parameters_by_name = {
        parameter["name"]: parameter for parameter in timeline_parameters
    }
    assert parameters_by_name["batch_id"]["in"] == "path"
    assert parameters_by_name["batch_id"]["required"] is True
    assert parameters_by_name["start_time"]["required"] is True
    assert parameters_by_name["end_time"]["required"] is True
    assert parameters_by_name["window_size"]["required"] is True
    assert parameters_by_name["start_time"]["schema"]["type"] == "string"
    assert parameters_by_name["end_time"]["schema"]["type"] == "string"
    assert "YYYY-MM-DD HH:MM:SS" in parameters_by_name["start_time"][
        "schema"
    ]["description"]

    hit_parameters = paths[
        "/brpc-diagnosis/batch/{batch_id}/hits"
    ]["get"]["parameters"]
    hit_parameters_by_name = {
        parameter["name"]: parameter for parameter in hit_parameters
    }
    for name in ("pod_ip", "thread_id"):
        assert hit_parameters_by_name[name]["in"] == "query"
        assert hit_parameters_by_name[name]["required"] is True
    assert "component" not in hit_parameters_by_name

    filter_names_by_path = {
        "/brpc-diagnosis/batch/{batch_id}/hits": {
            "start_time",
            "end_time",
            "pod_ip",
            "pod_name",
        },
        "/brpc-diagnosis/batch/{batch_id}/interface-timeline": {
            "start_time",
            "end_time",
            "pod_ip",
            "pod_name",
        },
        "/brpc-diagnosis/batch/{batch_id}/pod-events": {
            "start_time",
            "end_time",
            "pod_ip",
            "pod_name",
            "sort_order",
            "sort_field",
            "sort_direction",
        },
        "/brpc-diagnosis/batch/{batch_id}/pod-events/{event_id}": {
            "window_start_time",
            "window_end_time",
            "pod_ip",
            "pod_name",
        },
        "/brpc-diagnosis/batch/{batch_id}/thread-events": {
            "start_time",
            "end_time",
            "pod_ip",
            "pod_name",
            "sort_order",
            "sort_field",
            "sort_direction",
        },
        "/brpc-diagnosis/batch/{batch_id}/thread-events/{event_id}": {
            "window_start_time",
            "window_end_time",
            "pod_ip",
            "pod_name",
        },
        "/brpc-diagnosis/batch/{batch_id}/abnormal-threads": {
            "start_time",
            "end_time",
            "pod_ip",
            "pod_name",
            "search",
            "sort_field",
            "sort_direction",
        },
        "/brpc-diagnosis/batch/{batch_id}/abnormal-threads/{thread_key}": {
            "start_time",
            "end_time",
            "pod_ip",
            "pod_name",
        },
    }
    for path, expected_filter_names in filter_names_by_path.items():
        parameter_names = {
            parameter["name"]
            for parameter in paths[path]["get"]["parameters"]
        }
        assert expected_filter_names <= parameter_names

    for path in (
        "/brpc-diagnosis/batch/{batch_id}/pod-events",
        "/brpc-diagnosis/batch/{batch_id}/thread-events",
    ):
        sort_parameter = next(
            parameter
            for parameter in paths[path]["get"]["parameters"]
            if parameter["name"] == "sort_order"
        )
        assert sort_parameter["schema"]["default"] == "asc"
        assert sort_parameter["schema"]["enum"] == ["asc", "desc"]

    for path in (
        "/brpc-diagnosis/batch/{batch_id}/thread-events/{event_id}",
        "/brpc-diagnosis/batch/{batch_id}/abnormal-threads/{thread_key}",
    ):
        assert "component" not in {
            parameter["name"]
            for parameter in paths[path]["get"]["parameters"]
        }

    assert "component" not in {
        parameter["name"]
        for parameter in paths[
            "/brpc-diagnosis/batch/{batch_id}/abnormal-threads"
        ]["get"]["parameters"]
    }


def test_metric_sort_query_preserves_click_priority_and_validates_pairs():
    sort_fields = _build_metric_sort_fields(
        ["total_interface_hit_count", "ubsocket_001"],
        ["desc", "asc"],
    )

    assert [field.field for field in sort_fields] == [
        "total_interface_hit_count",
        "ubsocket_001",
    ]
    assert [field.order for field in sort_fields] == ["desc", "asc"]

    with pytest.raises(HTTPException) as exc_info:
        _build_metric_sort_fields(["ubsocket_001"], [])
    assert exc_info.value.status_code == 422


def test_interface_timeline_sql_uses_each_hits_resolved_interface_once():
    class EmptyMappingsResult:
        def mappings(self):
            return self

        def all(self):
            return []

    class CaptureSession:
        statement = None

        async def execute(self, statement):
            self.statement = statement
            return EmptyMappingsResult()

    session = CaptureSession()
    result = asyncio.run(
        BrpcDiagnosisPGManager.get_interface_timeline_aggregates(
            session,
            batch_id=BATCH_ID,
            start_timestamp=100,
            end_timestamp=200,
            window_us=10_000_000,
            interface_component="umq",
            interface_id="umq.interface.send",
            pod_ip=POD_IP,
            pod_name="pod-a",
        )
    )

    assert result == []
    compiled = str(
        session.statement.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )
    assert f"brpc_diag_hit.batch_id = '{BATCH_ID}'" in compiled
    assert "brpc_diag_hit.timestamp >= 100" in compiled
    assert "brpc_diag_hit.timestamp < 200" in compiled
    assert f"brpc_diag_hit.pod_ip = '{POD_IP}'" in compiled
    assert "brpc_diag_hit.pod_name = 'pod-a'" in compiled
    assert "brpc_diag_failure_interface" not in compiled
    assert "brpc_diag_node" in compiled
    assert "brpc_diag_hit.interface_id = 'umq.interface.send'" in compiled
    assert "LEFT OUTER JOIN brpc_diag_node" in compiled
    assert "floor" in compiled


def test_interface_timeline_bucket_sql_uses_precomputed_rows():
    class EmptyMappingsResult:
        def mappings(self):
            return self

        def all(self):
            return []

    class CaptureSession:
        statement = None

        async def execute(self, statement):
            self.statement = statement
            return EmptyMappingsResult()

    session = CaptureSession()
    result = asyncio.run(
        BrpcDiagnosisPGManager.get_interface_timeline_bucket_aggregates(
            session,
            batch_id=BATCH_ID,
            start_timestamp=100,
            end_timestamp=200,
            window_us=60_000_000,
            interface_component="ubsocket",
            pod_ip=POD_IP,
        )
    )

    assert result == []
    compiled = str(
        session.statement.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )
    assert "FROM brpc_diag_interface_bucket" in compiled
    assert "brpc_diag_hit" not in compiled
    assert "window_seconds = 60" in compiled
    assert "window_start_timestamp >= 100" in compiled
    assert "window_start_timestamp < 200" in compiled
    assert "component = 'ubsocket'" in compiled
    assert f"pod_ip = '{POD_IP}'" in compiled


def test_hit_sql_filters_by_pod_and_thread_key():
    class EmptyResult:
        def __init__(self, *, total=None):
            self.total = total

        def scalar_one(self):
            return self.total

        def scalars(self):
            return self

        def all(self):
            return []

    class CaptureSession:
        def __init__(self):
            self.statements = []

        async def execute(self, statement):
            self.statements.append(statement)
            return EmptyResult(total=0 if len(self.statements) == 1 else None)

    session = CaptureSession()
    total, rows = asyncio.run(
        BrpcDiagnosisPGManager.list_hits(
            session,
            batch_id=BATCH_ID,
            pod_ip=POD_IP,
            thread_id=THREAD_ID,
            pod_name="pod-a",
            page_num=1,
            page_cnt=100,
        )
    )

    assert (total, rows) == (0, [])
    for statement in session.statements:
        sql = str(
            statement.compile(
                dialect=postgresql.dialect(),
                compile_kwargs={"literal_binds": True},
            )
        )
        assert f"brpc_diag_hit.batch_id = '{BATCH_ID}'" in sql
        assert f"brpc_diag_hit.pod_ip = '{POD_IP}'" in sql
        assert "brpc_diag_hit.component =" not in sql
        assert f"brpc_diag_hit.thread_id = {THREAD_ID}" in sql
        assert "brpc_diag_hit.pod_name = 'pod-a'" in sql


def test_query_times_are_parsed_as_utc_plus_8_epoch_microseconds():
    assert parse_brpc_query_timestamp(
        "2026-08-06 15:07:41"
    ) == 1_786_000_061_000_000

    with pytest.raises(ValueError, match="YYYY-MM-DD HH:MM:SS"):
        parse_brpc_query_timestamp("2026-08-06T15:07:41")
    with pytest.raises(ValueError, match="YYYY-MM-DD HH:MM:SS"):
        parse_brpc_query_timestamp("1786000061000000")


def test_query_route_converts_utc_plus_8_times_before_service(monkeypatch):
    captured = {}

    async def fake_list_hits(**kwargs):
        captured.update(kwargs)
        return ListBrpcDiagHitsMsg(batch_id=BATCH_ID, total=0, hits=[])

    monkeypatch.setattr(BrpcDiagnosisService, "list_hits", fake_list_hits)
    app = FastAPI()
    app.include_router(router)

    async def call_api():
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get(
                f"/brpc-diagnosis/batch/{BATCH_ID}/hits",
                params={
                    "pod_ip": POD_IP,
                    "thread_id": THREAD_ID,
                    "pod_name": "pod-a",
                    "start_time": "2026-08-06 15:07:41",
                    "end_time": "2026-08-06 15:07:42",
                },
            )
            invalid_response = await client.get(
                f"/brpc-diagnosis/batch/{BATCH_ID}/hits",
                params={
                    "pod_ip": POD_IP,
                    "thread_id": THREAD_ID,
                    "start_time": "2026-08-06T15:07:41",
                },
            )
            timestamp_response = await client.get(
                f"/brpc-diagnosis/batch/{BATCH_ID}/hits",
                params={
                    "pod_ip": POD_IP,
                    "thread_id": THREAD_ID,
                    "start_time": "1786000061000000",
                },
            )
        return response, invalid_response, timestamp_response

    response, invalid_response, timestamp_response = asyncio.run(call_api())

    assert response.status_code == 200
    assert captured["pod_ip"] == POD_IP
    assert "component" not in captured
    assert captured["thread_id"] == THREAD_ID
    assert captured["pod_name"] == "pod-a"
    assert captured["start_timestamp"] == 1_786_000_061_000_000
    assert captured["end_timestamp"] == 1_786_000_062_000_000

    assert invalid_response.status_code == 422
    assert timestamp_response.status_code == 422
