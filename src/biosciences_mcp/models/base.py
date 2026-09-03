"""Shared serialisation base for every entity model (ADR-001 §4 null policy).

ADR-001 requires keys with no value to be omitted, never emitted as ``null``.
FastMCP serialises tool results with ``pydantic_core.to_json`` (text block)
and ``pydantic_core.to_jsonable_python`` (structured block); neither calls
``model_dump()``, so an override there is invisible on the wire. A wrap-mode
``model_serializer`` is applied on every serialisation path, including
``model_dump``, ``model_dump_json``, and nested models inside lists and
envelopes.

Envelopes (``models/envelopes.py``) deliberately do not use this base:
ADR-001 §8 defines ``cursor`` and ``total_count`` as nullable.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, SerializerFunctionWrapHandler, model_serializer


class OmitNoneModel(BaseModel):
    """Pydantic base whose serialised form never contains ``None`` values."""

    @model_serializer(mode="wrap")
    def _omit_none(self, handler: SerializerFunctionWrapHandler) -> Any:
        data = handler(self)
        if isinstance(data, dict):
            return {key: value for key, value in data.items() if value is not None}
        return data
