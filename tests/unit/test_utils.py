"""Unit tests for tests.utils helpers."""

import dataclasses

import pytest
from pydantic import BaseModel

from tests.utils import to_dict

pytestmark = pytest.mark.unit


class PlainModel(BaseModel):
    items: list[str]


@dataclasses.dataclass
class InnerRoot:
    id: str
    score: float


@dataclasses.dataclass
class OuterRoot:
    items: list[InnerRoot]
    total: int


def test_to_dict_passthrough_dict():
    assert to_dict({"items": ["a"], "total": 1}) == {"items": ["a"], "total": 1}


def test_to_dict_passthrough_non_mapping():
    assert to_dict(42) == 42
    assert to_dict("hello") == "hello"
    assert to_dict(None) is None


def test_to_dict_dumps_pydantic_model():
    assert to_dict(PlainModel(items=["a"])) == {"items": ["a"]}


def test_to_dict_converts_dataclass_instance_recursively():
    """FastMCP's synthetic Root type is a dataclass — asdict handles it."""
    wrapped = OuterRoot(items=[InnerRoot(id="HGNC:11998", score=1.0)], total=1)
    assert to_dict(wrapped) == {
        "items": [{"id": "HGNC:11998", "score": 1.0}],
        "total": 1,
    }


def test_to_dict_does_not_convert_dataclass_type_itself():
    """Passing the dataclass *class* (not an instance) should return it unchanged."""
    assert to_dict(InnerRoot) is InnerRoot
