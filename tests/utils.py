"""Shared test utilities and helper functions."""

import dataclasses
from typing import Any


def to_dict(result: Any) -> Any:
    """Normalize a tool return value to a plain dict when possible.

    FastMCP exposes ``CallToolResult.data`` as a dynamically generated
    dataclass (``fastmcp.utilities.json_schema_type.Root``) whose fields
    mirror the tool's JSON response schema. Convert such dataclass
    instances recursively via ``dataclasses.asdict``. Pydantic models fall
    back to ``model_dump``. Plain values are returned unchanged.
    """
    if dataclasses.is_dataclass(result) and not isinstance(result, type):
        return dataclasses.asdict(result)
    if hasattr(result, "model_dump"):
        return result.model_dump()
    return result
