"""ErrorDetail must not put null keys on the wire (ADR-001 §4 omit-null)."""

import json

import pytest
from pydantic_core import to_json

from biosciences_mcp.models.envelopes import ErrorCode, ErrorDetail, ErrorEnvelope

pytestmark = [pytest.mark.unit]


def test_error_detail_without_invalid_input_omits_the_key():
    env = ErrorEnvelope(
        success=False,
        error=ErrorDetail(
            code=ErrorCode.UPSTREAM_ERROR, message="timed out", recovery_hint="Retry."
        ),
    )
    wire = json.loads(to_json(env))  # FastMCP serialises with pydantic_core, not model_dump
    assert "invalid_input" not in wire["error"]
    assert wire["error"]["code"] == "UPSTREAM_ERROR"


def test_error_detail_with_invalid_input_keeps_it():
    env = ErrorEnvelope.unresolved_entity("TP53")
    wire = json.loads(to_json(env))
    assert wire["error"]["invalid_input"] == "TP53"
