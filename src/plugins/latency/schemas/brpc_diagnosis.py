"""BRPC diagnosis interchange and query API models."""

from datetime import datetime, timedelta, timezone
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    PlainSerializer,
    model_validator,
)

from latency.schemas.response import ResponseBase


BrpcNodeType = Literal["interface", "failure_mode"]
BrpcComponent = Literal["ubsocket", "umq", "urma"]
BrpcInterfaceComponent = Literal["ubsocket", "umq", "urma", "unknown"]
BrpcEdgeType = Literal["intra_component", "cross_component"]
BrpcInterfaceResolution = Literal[
    "static_unique", "thread_chain", "cross_component", "unresolved"
]


_UTC_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
_UTC_PLUS_8 = timezone(timedelta(hours=8))


def format_brpc_api_time(timestamp: int) -> str:
    """Format an epoch-microsecond BRPC timestamp as a UTC+8 wall-clock string."""
    value = (_UTC_EPOCH + timedelta(microseconds=timestamp)).astimezone(
        _UTC_PLUS_8
    )
    return value.strftime("%Y-%m-%d %H:%M:%S")


def parse_brpc_query_timestamp(value: object) -> int:
    """Parse an exact UTC+8 API time string into epoch microseconds."""
    if not isinstance(value, str):
        raise ValueError("时间必须使用 YYYY-MM-DD HH:MM:SS 字符串格式")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    except ValueError as exc:
        raise ValueError("时间必须使用 YYYY-MM-DD HH:MM:SS 格式") from exc
    if parsed.strftime("%Y-%m-%d %H:%M:%S") != value:
        raise ValueError("时间必须使用 YYYY-MM-DD HH:MM:SS 格式")
    delta = parsed.replace(tzinfo=_UTC_PLUS_8) - _UTC_EPOCH
    timestamp = (
        delta.days * 86_400_000_000
        + delta.seconds * 1_000_000
        + delta.microseconds
    )
    if timestamp < 0:
        raise ValueError("时间不能早于 Unix Epoch")
    return timestamp


# BRPC query services keep epoch microseconds internally for range arithmetic,
# stable event IDs and database filters.  Only the JSON response boundary is
# converted to a UTC+8 string.
BrpcApiTime = Annotated[
    int,
    PlainSerializer(format_brpc_api_time, return_type=str, when_used="json"),
]

# Query parameters are strings on the HTTP boundary and epoch-microsecond
# integers after Pydantic validation.
BrpcQueryTimestamp = Annotated[
    int,
    BeforeValidator(
        parse_brpc_query_timestamp,
        json_schema_input_type=str,
    ),
    Field(
        description=(
            "UTC+8 时间字符串，严格使用 YYYY-MM-DD HH:MM:SS 格式；"
            "后端转换为 epoch 微秒时间戳"
        ),
        examples=["2026-08-06 15:07:41"],
    ),
]


class _StrictProtocolModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class BrpcDiagNode(_StrictProtocolModel):
    node_id: str = Field(min_length=1)
    node_type: BrpcNodeType
    component: BrpcComponent
    name: str
    filename: str
    function_name: str
    phenomenon: str
    cause: str
    solution: str
    error_code: int | str | None


class BrpcDiagEdge(_StrictProtocolModel):
    source_node_id: str = Field(min_length=1)
    target_node_id: str = Field(min_length=1)
    edge_type: BrpcEdgeType


class BrpcFailureInterface(_StrictProtocolModel):
    failure_mode_id: str = Field(min_length=1)
    interface_ids: list[str] = Field(min_length=1)
    subgraph_edge_indexes: list[int] = Field(min_length=1)


class BrpcDiagSchema(_StrictProtocolModel):
    format_version: Literal[1]
    schema_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    nodes: list[BrpcDiagNode]
    edges: list[BrpcDiagEdge]
    failure_interface_mappings: list[BrpcFailureInterface]

    @model_validator(mode="after")
    def validate_graph(self) -> "BrpcDiagSchema":
        nodes_by_id: dict[str, BrpcDiagNode] = {}
        for node in self.nodes:
            if node.node_id in nodes_by_id:
                raise ValueError(f"duplicate node_id: {node.node_id}")
            nodes_by_id[node.node_id] = node

        edge_keys: set[tuple[str, str, str]] = set()
        for edge in self.edges:
            if edge.source_node_id not in nodes_by_id:
                raise ValueError(
                    f"edge source node does not exist: {edge.source_node_id}"
                )
            if edge.target_node_id not in nodes_by_id:
                raise ValueError(
                    f"edge target node does not exist: {edge.target_node_id}"
                )
            edge_key = (
                edge.source_node_id,
                edge.target_node_id,
                edge.edge_type,
            )
            if edge_key in edge_keys:
                raise ValueError(
                    "duplicate edge: "
                    f"{edge.source_node_id}->{edge.target_node_id} ({edge.edge_type})"
                )
            edge_keys.add(edge_key)

        failure_node_ids = {
            node.node_id
            for node in self.nodes
            if node.node_type == "failure_mode"
        }
        mapped_failure_ids: set[str] = set()
        for mapping in self.failure_interface_mappings:
            failure_id = mapping.failure_mode_id
            if failure_id in mapped_failure_ids:
                raise ValueError(
                    f"failure mode has more than one mapping: {failure_id}"
                )
            mapped_failure_ids.add(failure_id)

            failure_node = nodes_by_id.get(failure_id)
            if failure_node is None or failure_node.node_type != "failure_mode":
                raise ValueError(
                    f"mapping does not reference a failure_mode node: {failure_id}"
                )
            if len(mapping.interface_ids) != len(set(mapping.interface_ids)):
                raise ValueError(
                    f"mapping contains duplicate interface IDs: {failure_id}"
                )
            for interface_id in mapping.interface_ids:
                interface_node = nodes_by_id.get(interface_id)
                if interface_node is None or interface_node.node_type != "interface":
                    raise ValueError(
                        f"mapping does not reference an interface node: {interface_id}"
                    )
                if interface_node.component != failure_node.component:
                    raise ValueError(
                        "mapping nodes belong to different components: "
                        f"{failure_id}, {interface_id}"
                    )
            if len(mapping.subgraph_edge_indexes) != len(
                set(mapping.subgraph_edge_indexes)
            ):
                raise ValueError(
                    "mapping contains duplicate subgraph edge indexes: "
                    f"{failure_id}"
                )
            for edge_index in mapping.subgraph_edge_indexes:
                if edge_index < 0 or edge_index >= len(self.edges):
                    raise ValueError(
                        "mapping contains out-of-range subgraph edge index: "
                        f"{failure_id}, {edge_index}"
                    )

        missing_mappings = failure_node_ids - mapped_failure_ids
        extra_mappings = mapped_failure_ids - failure_node_ids
        if missing_mappings:
            raise ValueError(
                "failure modes without a mapping: "
                + ", ".join(sorted(missing_mappings))
            )
        if extra_mappings:
            raise ValueError(
                "mappings for unknown failure modes: "
                + ", ".join(sorted(extra_mappings))
            )
        return self


class BrpcDiagBatch(_StrictProtocolModel):
    record_type: Literal["batch"]
    format_version: Literal[2]
    task_id: str = Field(
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9_-]+$",
    )
    batch_id: str = Field(min_length=1)
    schema_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    created_at_timestamp: int = Field(ge=0)
    start_timestamp: int = Field(ge=0)
    end_timestamp: int = Field(ge=0)
    hit_count: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_interval(self) -> "BrpcDiagBatch":
        if self.end_timestamp < self.start_timestamp:
            raise ValueError(
                "batch end_timestamp must not be earlier than start_timestamp"
            )
        return self


class BrpcDiagHit(_StrictProtocolModel):
    record_type: Literal["hit"]
    hit_id: str = Field(min_length=1)
    failure_mode_id: str = Field(min_length=1)
    interface_id: str | None = None
    interface_resolution: BrpcInterfaceResolution = "unresolved"
    timestamp: int
    pod_name: str | None
    pod_ip: str | None
    component: BrpcComponent | None
    filename: str | None
    function_name: str | None
    line_number: int | None
    thread_id: int | None
    trace_id: str | None
    message: str

    @model_validator(mode="after")
    def validate_interface_resolution(self) -> "BrpcDiagHit":
        if (self.interface_id is None) != (self.interface_resolution == "unresolved"):
            raise ValueError(
                "interface_id must be set exactly when interface_resolution is resolved"
            )
        return self


# Query models deliberately live next to the protocol models.  This keeps the
# public BRPC contract in one module while using different class names for the
# immutable schema/batch file records and database-backed API records.
BrpcWindowSize = Literal["10s", "1m", "10m", "1h"]
BrpcAggregateWindowSize = Literal["1s", "1m", "1h"]
BrpcSortOrder = Literal["asc", "desc"]
BRPC_TOTAL_SORT_FIELD = "total_interface_hit_count"


class BrpcMetricSortField(BaseModel):
    field: str = Field(min_length=1, max_length=256)
    order: BrpcSortOrder


class BrpcDiagBatchMetadata(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    batch_id: str
    task_id: str
    schema_id: str
    created_at_time: BrpcApiTime = Field(
        validation_alias="created_at_timestamp"
    )
    start_time: BrpcApiTime = Field(validation_alias="start_timestamp")
    end_time: BrpcApiTime = Field(validation_alias="end_timestamp")
    hit_count: int = Field(ge=0)


class BrpcDiagHitLog(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    hit_id: str
    batch_id: str
    schema_id: str
    failure_mode_id: str
    interface_id: str | None = None
    interface_resolution: BrpcInterfaceResolution = "unresolved"
    time: BrpcApiTime = Field(validation_alias="timestamp")
    pod_name: str | None
    pod_ip: str | None
    component: BrpcComponent | None
    filename: str | None
    function_name: str | None
    line_number: int | None
    thread_id: int | None
    trace_id: str | None
    message: str


class BrpcInterfaceTimelinePoint(BaseModel):
    window_start_time: BrpcApiTime
    window_end_time: BrpcApiTime
    interface_hit_count: int = Field(ge=0)


class BrpcInterfaceTimelineSeries(BaseModel):
    component: BrpcInterfaceComponent
    interface_id: str
    interface_name: str
    function_name: str
    points: list[BrpcInterfaceTimelinePoint] = Field(default_factory=list)


class GetBrpcTaskBatchMsg(BaseModel):
    task_id: str
    batch_id: str


class GetBrpcTaskBatchResponse(ResponseBase):
    result: GetBrpcTaskBatchMsg


class GetBrpcBatchMsg(BaseModel):
    batch: BrpcDiagBatchMetadata


class GetBrpcBatchResponse(ResponseBase):
    result: GetBrpcBatchMsg


class ListBrpcDiagHitsMsg(BaseModel):
    batch_id: str
    total: int = Field(ge=0)
    hits: list[BrpcDiagHitLog] = Field(default_factory=list)


class ListBrpcDiagHitsResponse(ResponseBase):
    result: ListBrpcDiagHitsMsg


class GetBrpcInterfaceTimelineMsg(BaseModel):
    batch_id: str
    start_time: BrpcApiTime
    end_time: BrpcApiTime
    window_size: BrpcWindowSize
    series: list[BrpcInterfaceTimelineSeries] = Field(default_factory=list)


class GetBrpcInterfaceTimelineResponse(ResponseBase):
    result: GetBrpcInterfaceTimelineMsg


class BrpcInterfaceHit(BaseModel):
    component: BrpcInterfaceComponent
    interface_id: str
    interface_name: str
    function_name: str
    interface_hit_count: int = Field(ge=0)


class BrpcFailureModeHit(BaseModel):
    failure_mode_id: str
    component: BrpcComponent
    failure_mode_name: str
    hit_count: int = Field(ge=0)


class BrpcFailureGraphNode(BaseModel):
    node_id: str
    node_type: BrpcNodeType
    component: BrpcComponent
    name: str
    filename: str
    function_name: str
    phenomenon: str
    cause: str
    solution: str
    error_code: int | str | None
    directly_hit: bool = False
    hit_count: int = Field(default=0, ge=0)


class BrpcFailureGraph(BaseModel):
    nodes: list[BrpcFailureGraphNode] = Field(default_factory=list)
    edges: list[BrpcDiagEdge] = Field(default_factory=list)


class BrpcPodAggregatedEvent(BaseModel):
    event_id: str
    batch_id: str
    window_start_time: BrpcApiTime
    window_end_time: BrpcApiTime
    pod_ip: str
    pod_name: str | None
    interface_hits: list[BrpcInterfaceHit] = Field(default_factory=list)


class BrpcThreadAggregatedEvent(BaseModel):
    event_id: str
    batch_id: str
    window_start_time: BrpcApiTime
    window_end_time: BrpcApiTime
    pod_ip: str
    pod_name: str | None
    thread_id: int
    interface_hits: list[BrpcInterfaceHit] = Field(default_factory=list)


class ListBrpcPodEventsMsg(BaseModel):
    batch_id: str
    total: int = Field(ge=0)
    events: list[BrpcPodAggregatedEvent] = Field(default_factory=list)


class ListBrpcPodEventsResponse(ResponseBase):
    result: ListBrpcPodEventsMsg


class ListBrpcThreadEventsMsg(BaseModel):
    batch_id: str
    total: int = Field(ge=0)
    events: list[BrpcThreadAggregatedEvent] = Field(default_factory=list)


class ListBrpcThreadEventsResponse(ResponseBase):
    result: ListBrpcThreadEventsMsg


class GetBrpcPodEventDetailMsg(BaseModel):
    event: BrpcPodAggregatedEvent
    failure_modes: list[BrpcFailureModeHit] = Field(default_factory=list)
    failure_graph: BrpcFailureGraph
    hit_total: int = Field(ge=0)
    hits: list[BrpcDiagHitLog] = Field(default_factory=list)


class GetBrpcPodEventDetailResponse(ResponseBase):
    result: GetBrpcPodEventDetailMsg


class GetBrpcThreadEventDetailMsg(BaseModel):
    event: BrpcThreadAggregatedEvent
    failure_modes: list[BrpcFailureModeHit] = Field(default_factory=list)
    failure_graph: BrpcFailureGraph
    hit_total: int = Field(ge=0)
    hits: list[BrpcDiagHitLog] = Field(default_factory=list)


class GetBrpcThreadEventDetailResponse(ResponseBase):
    result: GetBrpcThreadEventDetailMsg


class BrpcAbnormalThread(BaseModel):
    thread_key: str
    batch_id: str
    pod_ip: str
    pod_name: str | None
    thread_id: int
    first_hit_time: BrpcApiTime
    last_hit_time: BrpcApiTime
    total_interface_hit_count: int = Field(ge=0)
    interface_hits: list[BrpcInterfaceHit] = Field(default_factory=list)


class ListBrpcAbnormalThreadsMsg(BaseModel):
    batch_id: str
    total: int = Field(ge=0)
    threads: list[BrpcAbnormalThread] = Field(default_factory=list)


class ListBrpcAbnormalThreadsResponse(ResponseBase):
    result: ListBrpcAbnormalThreadsMsg


class GetBrpcAbnormalThreadDetailMsg(BaseModel):
    thread: BrpcAbnormalThread
    start_time: BrpcApiTime
    end_time: BrpcApiTime
    window_size: BrpcWindowSize
    interface_timeline: list[BrpcInterfaceTimelineSeries] = Field(
        default_factory=list
    )
    failure_modes: list[BrpcFailureModeHit] = Field(default_factory=list)
    failure_graph: BrpcFailureGraph
    hit_total: int = Field(ge=0)
    hits: list[BrpcDiagHitLog] = Field(default_factory=list)


class GetBrpcAbnormalThreadDetailResponse(ResponseBase):
    result: GetBrpcAbnormalThreadDetailMsg
