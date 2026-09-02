"""Regression tests for PostgreSQL array filters on trace failure events."""

from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import array

from latency.database.models import TraceFailureEvent


def test_status_code_supports_postgresql_overlap_operator() -> None:
    expression = TraceFailureEvent.status_code.overlap(array(["7"]))

    compiled = str(
        expression.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )

    assert compiled == "trace_failure_event.status_code && ARRAY['7']"
