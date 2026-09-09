"""Reusable validation constraints for resource IDs accepted by API paths."""

from typing import Annotated

from fastapi import Path, Query


# Persisted UUID-backed resources normally use canonical UUID4 strings. Keep
# safe legacy alphanumeric IDs valid while rejecting path/control punctuation.
ResourceIdPath = Annotated[
    str,
    Path(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]*$"),
]

# Query-parameter twin of ResourceIdPath for endpoints that receive the same
# resource IDs through the query string instead of the path.
ResourceIdQuery = Annotated[
    str,
    Query(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]*$"),
]

# Failure-mode IDs are imported from data/*/*failure_mode.json. All current
# identifiers contain only ASCII letters, digits and underscores.
FailureModeIdPath = Annotated[
    str,
    Path(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9][A-Za-z0-9_]*$"),
]

# Status codes are external/business codes rather than UUIDs.
StatusCodePath = Annotated[
    str,
    Path(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]*$"),
]

# Dynamic BRPC event IDs are SHA-256 hashes of their complete grouping keys.
BrpcEventIdPath = Annotated[str, Path(pattern=r"^[0-9a-f]{64}$")]
