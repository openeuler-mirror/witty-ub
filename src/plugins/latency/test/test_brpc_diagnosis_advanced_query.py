import asyncio
from contextlib import asynccontextmanager
import hashlib
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy.dialects import postgresql

import latency.services.brpc_diagnosis as service_module
from latency.database.managers.brpc_diagnosis import BrpcDiagnosisPGManager
from latency.exceptions import BadRequestBizException
from latency.parse.brpc_diag_parser import BrpcDiagParser
from latency.schemas.brpc_diagnosis import (
    BRPC_TOTAL_SORT_FIELD,
    BrpcMetricSortField,
)
from latency.services.brpc_diagnosis import BrpcDiagnosisService


FIXTURES = Path(__file__).parent / "fixtures" / "brpc_diag"
SCHEMA_ID = "1" * 64
BATCH_ID = "0198aaaa-1111-7111-8111-111111111111"
START_TIMESTAMP = 1_786_000_061_000_000
END_TIMESTAMP = 1_786_000_082_000_000
POD_IP = "10.0.0.12"
COMPONENT = "ubsocket"
THREAD_ID = 4567


class AdvancedStore:
    def __init__(self):
        self.schema = BrpcDiagParser.parse_schema(
            FIXTURES / "valid" / f"schema_{SCHEMA_ID}.json"
        )
        self.batch = SimpleNamespace(
            batch_id=BATCH_ID,
            task_id="task-normal",
            schema_id=SCHEMA_ID,
        )
        self.hit = SimpleNamespace(
            hit_id=f"{BATCH_ID}:hit:0",
            batch_id=BATCH_ID,
            schema_id=SCHEMA_ID,
            failure_mode_id="ubsocket_005",
            timestamp=START_TIMESTAMP,
            pod_name="brpc-worker-0",
            pod_ip=POD_IP,
            component=COMPONENT,
            filename="ubsocket_fast_heap.h",
            function_name="Pop",
            line_number=123,
            thread_id=THREAD_ID,
            trace_id="trace-1",
            message="[ERROR] heap is empty",
        )

    @asynccontextmanager
    async def session(self):
        yield SimpleNamespace()


def _configure_store(monkeypatch, store: AdvancedStore):
    interface_hits = [
        {
            "component": "ubsocket",
            "interface_id": "ubsocket_001",
            "interface_name": "数据读取接口",
            "function_name": "Pop",
            "interface_hit_count": 1,
        }
    ]
    failure_hits = [
        {
            "failure_mode_id": "ubsocket_005",
            "component": "ubsocket",
            "failure_mode_name": "弹出乱序接收元素时堆对象为空",
            "hit_count": 1,
            "interface_ids": ["ubsocket_001"],
            "unresolved_hit_count": 0,
        }
    ]
    summary = {
        "pod_ip": POD_IP,
        "pod_name": "brpc-worker-0",
        "thread_id": THREAD_ID,
        "first_hit_timestamp": START_TIMESTAMP,
        "last_hit_timestamp": START_TIMESTAMP,
        "total_interface_hit_count": 1,
        "interface_hits": interface_hits,
    }

    class AdvancedManager:
        @staticmethod
        async def get_batch(_session, batch_id):
            return store.batch if batch_id == BATCH_ID else None

        @staticmethod
        async def list_pod_events(_session, **_kwargs):
            return 1, [
                {
                    "window_start_timestamp": 1_786_000_060_000_000,
                    "pod_ip": POD_IP,
                    "pod_name": "brpc-worker-0",
                    "interface_hits": interface_hits,
                }
            ]

        @staticmethod
        async def list_thread_events(_session, **_kwargs):
            return 1, [
                {
                    "window_start_timestamp": 1_786_000_060_000_000,
                    "pod_ip": POD_IP,
                    "pod_name": "brpc-worker-0",
                    "thread_id": THREAD_ID,
                    "interface_hits": interface_hits,
                }
            ]

        @staticmethod
        async def get_interface_hit_counts(_session, **_kwargs):
            return interface_hits

        @staticmethod
        async def get_failure_mode_hit_counts(_session, **_kwargs):
            return failure_hits

        @staticmethod
        async def list_hits(_session, **_kwargs):
            return 1, [store.hit]

        @staticmethod
        async def get_schema(_session, schema_id):
            return store.schema if schema_id == SCHEMA_ID else None

        @staticmethod
        async def list_abnormal_threads(_session, **_kwargs):
            return 1, [summary]

        @staticmethod
        async def get_interface_timeline_aggregates(_session, **_kwargs):
            return [
                {
                    "window_start_timestamp": 1_786_000_060_000_000,
                    **interface_hits[0],
                }
            ]

    monkeypatch.setattr(
        service_module,
        "PGManager",
        SimpleNamespace(session=store.session),
    )
    monkeypatch.setattr(
        service_module,
        "BrpcDiagnosisPGManager",
        AdvancedManager,
    )


def test_event_and_thread_hashes_are_stable_and_use_pod_thread_keys():
    expected = hashlib.sha256(
        b'["batch-a",10,20,"10.0.0.1"]'
    ).hexdigest()

    assert BrpcDiagnosisService.pod_event_id(
        "batch-a", 10, 20, "10.0.0.1"
    ) == expected
    assert BrpcDiagnosisService.pod_event_id(
        "batch-a", 10, 21, "10.0.0.1"
    ) != expected
    assert BrpcDiagnosisService.thread_event_id(
        "batch-a", 10, 20, "10.0.0.1", 7
    ) == hashlib.sha256(
        b'["batch-a",10,20,"10.0.0.1",7]'
    ).hexdigest()
    assert BrpcDiagnosisService.thread_event_id(
        "batch-a", 10, 20, "10.0.0.1", 7
    ) != BrpcDiagnosisService.thread_event_id(
        "batch-a", 10, 20, "10.0.0.1", 8
    )
    assert BrpcDiagnosisService.thread_key(
        "batch-a", "10.0.0.1", 7
    ) == BrpcDiagnosisService.thread_key(
        "batch-a", "10.0.0.1", 7
    )


def test_pod_and_thread_event_lists_return_interface_mappings(monkeypatch):
    store = AdvancedStore()
    _configure_store(monkeypatch, store)

    pod_result = asyncio.run(
        BrpcDiagnosisService.list_pod_events(
            batch_id=BATCH_ID,
            start_timestamp=START_TIMESTAMP,
            end_timestamp=END_TIMESTAMP,
            window_size="1m",
            page_num=1,
            page_cnt=100,
            pod_ip=POD_IP,
            pod_name="brpc-worker-0",
        )
    )
    thread_result = asyncio.run(
        BrpcDiagnosisService.list_thread_events(
            batch_id=BATCH_ID,
            start_timestamp=START_TIMESTAMP,
            end_timestamp=END_TIMESTAMP,
            window_size="1m",
            page_num=1,
            page_cnt=100,
            pod_ip=POD_IP,
            pod_name="brpc-worker-0",
        )
    )

    assert pod_result.total == 1
    assert pod_result.events[0].pod_ip == POD_IP
    assert pod_result.events[0].interface_hits[0].interface_hit_count == 1
    assert thread_result.total == 1
    assert thread_result.events[0].thread_id == THREAD_ID
    assert "component" not in thread_result.events[0].model_dump()


def test_detail_recomputes_event_id_and_returns_pruned_graph(monkeypatch):
    store = AdvancedStore()
    _configure_store(monkeypatch, store)
    event_id = BrpcDiagnosisService.thread_event_id(
        BATCH_ID,
        START_TIMESTAMP,
        END_TIMESTAMP,
        POD_IP,
        THREAD_ID,
    )

    result = asyncio.run(
        BrpcDiagnosisService.get_thread_event_detail(
            event_id=event_id,
            batch_id=BATCH_ID,
            window_start_timestamp=START_TIMESTAMP,
            window_end_timestamp=END_TIMESTAMP,
            pod_ip=POD_IP,
            thread_id=THREAD_ID,
            page_num=1,
            page_cnt=100,
            pod_name="brpc-worker-0",
        )
    )

    assert result.hit_total == 1
    assert [node.node_id for node in result.failure_graph.nodes] == [
        "ubsocket_001",
        "ubsocket_005",
    ]
    assert len(result.failure_graph.edges) == 1
    hit_node = next(
        node for node in result.failure_graph.nodes if node.directly_hit
    )
    assert hit_node.node_id == "ubsocket_005"
    assert hit_node.hit_count == 1

    with pytest.raises(BadRequestBizException, match="event_id"):
        asyncio.run(
            BrpcDiagnosisService.get_thread_event_detail(
                event_id="0" * 64,
                batch_id=BATCH_ID,
                window_start_timestamp=START_TIMESTAMP,
                window_end_timestamp=END_TIMESTAMP,
                pod_ip=POD_IP,
                thread_id=THREAD_ID,
                page_num=1,
                page_cnt=100,
            )
        )


def test_cross_component_edge_requires_both_retained_endpoints():
    store = AdvancedStore()
    partial = BrpcDiagnosisService._build_failure_graph(
        store.schema,
        [
            {
                "failure_mode_id": "umq_006",
                "component": "umq",
                "failure_mode_name": "消息接收失败",
                "hit_count": 2,
                "interface_ids": ["umq_001"],
                "unresolved_hit_count": 0,
            }
        ],
    )
    complete = BrpcDiagnosisService._build_failure_graph(
        store.schema,
        [
            {
                "failure_mode_id": "ubsocket_005",
                "component": "ubsocket",
                "failure_mode_name": "ubsocket failure",
                "hit_count": 1,
                "interface_ids": ["ubsocket_001"],
                "unresolved_hit_count": 0,
            },
            {
                "failure_mode_id": "umq_006",
                "component": "umq",
                "failure_mode_name": "umq failure",
                "hit_count": 2,
                "interface_ids": ["umq_001"],
                "unresolved_hit_count": 0,
            },
        ],
    )

    assert {node.node_id for node in partial.nodes} == {"umq_001", "umq_006"}
    assert all(edge.edge_type == "intra_component" for edge in partial.edges)
    assert len(complete.nodes) == 4
    assert {edge.edge_type for edge in complete.edges} == {
        "intra_component",
        "cross_component",
    }


def test_failure_graph_omits_subgraph_only_intermediate_nodes():
    store = AdvancedStore()
    schema = store.schema.model_copy(deep=True)
    intermediate_node = schema.nodes[1].model_copy(
        update={
            "node_id": "ubsocket_003",
            "name": "仅用于连接的中间节点",
        }
    )
    intermediate_edge = schema.edges[0].model_copy(
        update={
            "source_node_id": intermediate_node.node_id,
            "target_node_id": "ubsocket_005",
        }
    )
    schema.nodes.append(intermediate_node)
    schema.edges.append(intermediate_edge)
    schema.failure_interface_mappings[0] = schema.failure_interface_mappings[
        0
    ].model_copy(
        update={
            "subgraph_edge_indexes": [
                *schema.failure_interface_mappings[0].subgraph_edge_indexes,
                len(schema.edges) - 1,
            ]
        }
    )

    graph = BrpcDiagnosisService._build_failure_graph(
        schema,
        [
            {
                "failure_mode_id": "ubsocket_005",
                "component": "ubsocket",
                "failure_mode_name": "ubsocket failure",
                "hit_count": 1,
                "interface_ids": ["ubsocket_001"],
                "unresolved_hit_count": 0,
            }
        ],
    )

    assert {node.node_id for node in graph.nodes} == {
        "ubsocket_001",
        "ubsocket_005",
    }
    assert all(
        edge.source_node_id != intermediate_node.node_id
        and edge.target_node_id != intermediate_node.node_id
        for edge in graph.edges
    )


def test_failure_graph_only_adds_resolved_interface_without_synthetic_edge():
    store = AdvancedStore()
    schema = store.schema.model_copy(deep=True)
    second_interface = schema.nodes[0].model_copy(
        update={
            "node_id": "ubsocket_002",
            "name": "另一个候选接口",
        }
    )
    schema.nodes.append(second_interface)
    schema.failure_interface_mappings[0] = schema.failure_interface_mappings[
        0
    ].model_copy(
        update={
            "interface_ids": ["ubsocket_001", second_interface.node_id],
        }
    )

    graph = BrpcDiagnosisService._build_failure_graph(
        schema,
        [
            {
                "failure_mode_id": "ubsocket_005",
                "component": "ubsocket",
                "failure_mode_name": "ubsocket failure",
                "hit_count": 3,
                "interface_ids": [second_interface.node_id],
                "unresolved_hit_count": 0,
            }
        ],
    )

    assert {node.node_id for node in graph.nodes} == {
        second_interface.node_id,
        "ubsocket_005",
    }
    assert graph.edges == []


def test_failure_graph_preserves_original_parent_path_without_shortcut():
    store = AdvancedStore()
    interface = store.schema.nodes[0].model_copy(
        update={"node_id": "ubsocket_003"}
    )
    parent_failure = store.schema.nodes[1].model_copy(
        update={"node_id": "ubsocket_072"}
    )
    child_failure = store.schema.nodes[1].model_copy(
        update={"node_id": "ubsocket_077"}
    )
    interface_to_parent = store.schema.edges[0].model_copy(
        update={
            "source_node_id": interface.node_id,
            "target_node_id": parent_failure.node_id,
        }
    )
    parent_to_child = store.schema.edges[0].model_copy(
        update={
            "source_node_id": parent_failure.node_id,
            "target_node_id": child_failure.node_id,
        }
    )
    parent_mapping = store.schema.failure_interface_mappings[0].model_copy(
        update={
            "failure_mode_id": parent_failure.node_id,
            "interface_ids": [interface.node_id],
            "subgraph_edge_indexes": [0],
        }
    )
    child_mapping = store.schema.failure_interface_mappings[0].model_copy(
        update={
            "failure_mode_id": child_failure.node_id,
            "interface_ids": [interface.node_id],
            "subgraph_edge_indexes": [0, 1],
        }
    )
    schema = store.schema.model_copy(
        update={
            "nodes": [interface, parent_failure, child_failure],
            "edges": [interface_to_parent, parent_to_child],
            "failure_interface_mappings": [parent_mapping, child_mapping],
        }
    )

    graph = BrpcDiagnosisService._build_failure_graph(
        schema,
        [
            {
                "failure_mode_id": parent_failure.node_id,
                "component": "ubsocket",
                "failure_mode_name": "parent failure",
                "hit_count": 1,
                "interface_ids": [interface.node_id],
                "unresolved_hit_count": 0,
            },
            {
                "failure_mode_id": child_failure.node_id,
                "component": "ubsocket",
                "failure_mode_name": "child failure",
                "hit_count": 1,
                "interface_ids": [interface.node_id],
                "unresolved_hit_count": 0,
            },
        ],
    )

    assert [
        (edge.source_node_id, edge.target_node_id)
        for edge in graph.edges
    ] == [
        ("ubsocket_003", "ubsocket_072"),
        ("ubsocket_072", "ubsocket_077"),
    ]


def test_failure_graph_keeps_unresolved_hits_as_an_interface_less_tree():
    store = AdvancedStore()

    graph = BrpcDiagnosisService._build_failure_graph(
        store.schema,
        [
            {
                "failure_mode_id": "ubsocket_005",
                "component": "ubsocket",
                "failure_mode_name": "ubsocket failure",
                "hit_count": 2,
                "interface_ids": None,
                "unresolved_hit_count": 2,
            }
        ],
    )

    assert [node.node_id for node in graph.nodes] == ["ubsocket_005"]
    assert graph.nodes[0].hit_count == 2
    assert graph.edges == []


def test_abnormal_thread_detail_contains_timeline_graph_and_logs(monkeypatch):
    store = AdvancedStore()
    _configure_store(monkeypatch, store)
    thread_key = BrpcDiagnosisService.thread_key(
        BATCH_ID,
        POD_IP,
        THREAD_ID,
    )

    result = asyncio.run(
        BrpcDiagnosisService.get_abnormal_thread_detail(
            thread_key=thread_key,
            batch_id=BATCH_ID,
            pod_ip=POD_IP,
            thread_id=THREAD_ID,
            start_timestamp=START_TIMESTAMP,
            end_timestamp=END_TIMESTAMP,
            window_size="10s",
            page_num=1,
            page_cnt=100,
            pod_name="brpc-worker-0",
        )
    )

    assert result.thread.thread_key == thread_key
    assert result.thread.first_hit_time == START_TIMESTAMP
    assert result.thread.last_hit_time == START_TIMESTAMP
    assert result.thread.total_interface_hit_count == 1
    assert result.thread.interface_hits[0].interface_id == "ubsocket_001"
    assert result.hit_total == 1
    assert result.interface_timeline[0].points[0].interface_hit_count == 1
    assert result.failure_modes[0].failure_mode_id == "ubsocket_005"


def test_thread_aggregation_sql_excludes_incomplete_group_keys():
    class ScalarResult:
        def scalar_one(self):
            return 0

    class MappingResult:
        def mappings(self):
            return self

        def all(self):
            return []

    class CaptureSession:
        def __init__(self):
            self.statements = []

        async def execute(self, statement):
            self.statements.append(statement)
            return ScalarResult() if len(self.statements) == 1 else MappingResult()

    session = CaptureSession()
    total, rows = asyncio.run(
        BrpcDiagnosisPGManager.list_thread_events(
            session,
            batch_id=BATCH_ID,
            start_timestamp=START_TIMESTAMP,
            end_timestamp=END_TIMESTAMP,
            window_us=60_000_000,
            page_num=1,
            page_cnt=100,
            pod_ip=POD_IP,
            pod_name="brpc-worker-0",
        )
    )

    assert total == 0
    assert rows == []
    for statement in session.statements:
        sql = str(
            statement.compile(
                dialect=postgresql.dialect(),
                compile_kwargs={"literal_binds": True},
            )
        )
        assert f"brpc_diag_hit.batch_id = '{BATCH_ID}'" in sql
        assert "brpc_diag_hit.pod_ip IS NOT NULL" in sql
        assert "brpc_diag_hit.component" not in sql
        assert "brpc_diag_hit.thread_id IS NOT NULL" in sql
        assert f"brpc_diag_hit.pod_ip = '{POD_IP}'" in sql
        assert "brpc_diag_hit.pod_name = 'brpc-worker-0'" in sql


@pytest.mark.parametrize("aggregation", ["pod", "thread"])
@pytest.mark.parametrize("sort_order", ["asc", "desc"])
def test_event_aggregation_sql_orders_windows_by_requested_direction(
    aggregation,
    sort_order,
):
    class ScalarResult:
        def scalar_one(self):
            return 0

    class MappingResult:
        def mappings(self):
            return self

        def all(self):
            return []

    class CaptureSession:
        def __init__(self):
            self.statements = []

        async def execute(self, statement):
            self.statements.append(statement)
            return ScalarResult() if len(self.statements) == 1 else MappingResult()

    session = CaptureSession()
    asyncio.run(
        getattr(BrpcDiagnosisPGManager, f"list_{aggregation}_events")(
            session,
            batch_id=BATCH_ID,
            start_timestamp=START_TIMESTAMP,
            end_timestamp=END_TIMESTAMP,
            window_us=60_000_000,
            sort_order=sort_order,
            page_num=1,
            page_cnt=100,
        )
    )

    sql = str(
        session.statements[-1].compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )
    expected_direction = sort_order.upper()
    opposite_direction = "DESC" if sort_order == "asc" else "ASC"
    assert f"window_start_timestamp {expected_direction}" in sql
    assert f"window_start_timestamp {opposite_direction}" not in sql


@pytest.mark.parametrize("aggregation", ["pod", "thread"])
def test_event_aggregation_sql_applies_metric_sort_priority(aggregation):
    class ScalarResult:
        def scalar_one(self):
            return 0

    class MappingResult:
        def mappings(self):
            return self

        def all(self):
            return []

    class CaptureSession:
        def __init__(self):
            self.statements = []

        async def execute(self, statement):
            self.statements.append(statement)
            return ScalarResult() if len(self.statements) == 1 else MappingResult()

    session = CaptureSession()
    asyncio.run(
        getattr(BrpcDiagnosisPGManager, f"list_{aggregation}_events")(
            session,
            batch_id=BATCH_ID,
            start_timestamp=START_TIMESTAMP,
            end_timestamp=END_TIMESTAMP,
            window_us=60_000_000,
            sort_order="asc",
            metric_sort_fields=[
                BrpcMetricSortField(field=BRPC_TOTAL_SORT_FIELD, order="desc"),
                BrpcMetricSortField(field="ubsocket_001", order="asc"),
            ],
            page_num=1,
            page_cnt=100,
        )
    )

    sql = str(
        session.statements[-1].compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )
    outer_order_by = sql.rsplit("ORDER BY", maxsplit=1)[1]
    assert outer_order_by.index("sort_metric_0 DESC") < outer_order_by.index(
        "sort_metric_1 ASC"
    )
    assert outer_order_by.index("sort_metric_1 ASC") < outer_order_by.index(
        "window_start_timestamp ASC"
    )
    assert "FILTER (WHERE brpc_diag_hit.interface_id = 'ubsocket_001')" in sql


def test_abnormal_thread_sql_groups_by_pod_and_thread_only():
    class ScalarResult:
        def scalar_one(self):
            return 0

    class MappingResult:
        def mappings(self):
            return self

        def all(self):
            return []

    class CaptureSession:
        def __init__(self):
            self.statements = []

        async def execute(self, statement):
            self.statements.append(statement)
            if len(self.statements) == 1:
                return ScalarResult()
            return MappingResult()

    session = CaptureSession()
    total, rows = asyncio.run(
        BrpcDiagnosisPGManager.list_abnormal_threads(
            session,
            batch_id=BATCH_ID,
            start_timestamp=START_TIMESTAMP,
            end_timestamp=END_TIMESTAMP,
            page_num=1,
            page_cnt=100,
            pod_ip=POD_IP,
            thread_id=THREAD_ID,
            search="worker",
            metric_sort_fields=[
                BrpcMetricSortField(field=BRPC_TOTAL_SORT_FIELD, order="desc"),
                BrpcMetricSortField(field="ubsocket_001", order="asc"),
            ],
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
        assert "brpc_diag_hit.component" not in sql
        assert f"brpc_diag_hit.pod_ip = '{POD_IP}'" in sql
        assert f"brpc_diag_hit.thread_id = {THREAD_ID}" in sql
        assert "CAST(brpc_diag_hit.thread_id AS VARCHAR) ILIKE" in sql
        assert "brpc_diag_hit.pod_ip ILIKE" in sql
        assert "brpc_diag_hit.pod_name ILIKE" in sql
        if "interface_hits" in sql:
            assert "brpc_diag_failure_interface" not in sql
            assert "brpc_diag_hit.interface_id" in sql
            assert "brpc_diag_node.function_name" in sql
            assert "__unresolved__" in sql

    outer_order_by = str(
        session.statements[-1].compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    ).rsplit("ORDER BY", maxsplit=1)[1]
    assert outer_order_by.index("sum(") < outer_order_by.index("coalesce(")
    assert "sum(" in outer_order_by and " DESC" in outer_order_by
    assert "interface_id = 'ubsocket_001'" in outer_order_by
    assert " ASC" in outer_order_by
