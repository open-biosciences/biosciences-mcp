"""Serialisation contract: no model may emit ``null`` on the wire (ADR-001 §4).

FastMCP does not call ``model_dump()``. It serialises the text block with
``pydantic_core.to_json`` and the structured block with
``pydantic_core.to_jsonable_python``. A ``model_dump`` override or an
``exclude_none`` config key therefore has no effect on what an agent sees.

This test runs every entity model through both of FastMCP's real code paths
with all optional fields unset, and fails on the first ``null``. It needs no
network.

Envelopes are exempt: ADR-001 §8 explicitly allows ``cursor`` and
``total_count`` to be null in the pagination envelope, and ``invalid_input``
may be absent from an upstream error.
"""

from __future__ import annotations

import importlib
import inspect
import pkgutil
import typing
from typing import Any

import pydantic_core
import pytest
from fastmcp.tools.tool import default_serializer
from pydantic import BaseModel

import biosciences_mcp.models as models_pkg
from tests.contract.conftest import find_nulls

EXEMPT_MODULES = {"envelopes"}


def _dummy_for(annotation: Any) -> Any:
    """Produce a JSON-serialisable placeholder for a required field."""
    origin = typing.get_origin(annotation)
    args = typing.get_args(annotation)
    if origin is typing.Annotated:
        return _dummy_for(args[0])
    if origin in (typing.Union, getattr(__import__("types"), "UnionType", None)):
        non_none = [a for a in args if a is not type(None)]
        return _dummy_for(non_none[0]) if non_none else "x"
    if origin in (list, tuple, set):
        return []
    if origin is dict:
        return {}
    if inspect.isclass(annotation) and issubclass(annotation, BaseModel):
        return _construct_sparse(annotation)
    if annotation is int:
        return 1
    if annotation is float:
        return 0.5
    if annotation is bool:
        return True
    return "x"


def _construct_sparse(cls: type[BaseModel]) -> BaseModel:
    """Build an instance with only required fields set, leaving optionals at their defaults."""
    required = {
        name: _dummy_for(info.annotation)
        for name, info in cls.model_fields.items()
        if info.is_required()
    }
    return cls.model_construct(**required)


def _entity_models() -> list[Any]:
    params = []
    for module_info in pkgutil.iter_modules(models_pkg.__path__):
        if module_info.name in EXEMPT_MODULES:
            continue
        module = importlib.import_module(f"biosciences_mcp.models.{module_info.name}")
        for name, cls in inspect.getmembers(module, inspect.isclass):
            if issubclass(cls, BaseModel) and cls.__module__ == module.__name__:
                params.append(pytest.param(cls, id=f"{module_info.name}.{name}"))
    return params


@pytest.mark.unit
@pytest.mark.contract
@pytest.mark.parametrize("model_cls", _entity_models())
def test_text_content_omits_null_fields(model_cls: type[BaseModel]) -> None:
    """The text block FastMCP emits for a sparse instance contains no null."""
    instance = _construct_sparse(model_cls)
    payload = pydantic_core.from_json(default_serializer(instance))
    nulls = find_nulls(payload)
    assert not nulls, f"{model_cls.__name__} serialises nulls in text content: {nulls}"


@pytest.mark.unit
@pytest.mark.contract
@pytest.mark.parametrize("model_cls", _entity_models())
def test_structured_content_omits_null_fields(model_cls: type[BaseModel]) -> None:
    """The structured block FastMCP emits for a sparse instance contains no null."""
    instance = _construct_sparse(model_cls)
    payload = pydantic_core.to_jsonable_python(instance)
    nulls = find_nulls(payload)
    assert not nulls, f"{model_cls.__name__} serialises nulls in structured content: {nulls}"
