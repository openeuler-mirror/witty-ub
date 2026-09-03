"""Pagination request validation contract tests."""

import inspect

import pytest
from pydantic import BaseModel, ValidationError

from latency.schemas import request as request_schemas


PAGINATION_REQUEST_MODELS = [
    model
    for _, model in inspect.getmembers(request_schemas, inspect.isclass)
    if issubclass(model, BaseModel) and "page_num" in model.model_fields
]


@pytest.mark.parametrize(
    "request_model",
    PAGINATION_REQUEST_MODELS,
    ids=lambda model: model.__name__,
)
def test_page_num_must_be_positive(request_model: type[BaseModel]) -> None:
    page_num_schema = request_model.model_json_schema()["properties"]["page_num"]
    assert page_num_schema["minimum"] == 1

    with pytest.raises(ValidationError) as exc_info:
        request_model.model_validate({"page_num": 0})

    assert any(
        error["loc"] == ("page_num",) and error["type"] == "greater_than_equal"
        for error in exc_info.value.errors()
    )
