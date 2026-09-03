"""Unit tests for the IUPHAR MCP server boundary (no network).

ADR-001 §3: a raw string passed to a strict tool must come back as the
canonical UNRESOLVED_ENTITY ErrorEnvelope, not as a pydantic validation
message. These tests call the server in-process through fastmcp.Client, so
they exercise the tool signature, not just the client method.
"""

import json

import pytest
from fastmcp import Client

from biosciences_mcp.servers.iuphar import mcp

pytestmark = [pytest.mark.unit, pytest.mark.iuphar]


@pytest.mark.parametrize("tool", ["get_ligand", "get_target"])
async def test_strict_tool_returns_unresolved_entity_envelope_for_raw_string(tool: str) -> None:
    async with Client(mcp) as client:
        result = await client.call_tool(tool, {"iuphar_id": "ibuprofen"}, raise_on_error=False)
    text = result.content[0].text
    payload = json.loads(text)  # a pydantic validation string is not JSON
    assert payload["success"] is False
    assert payload["error"]["code"] == "UNRESOLVED_ENTITY"
    assert payload["error"]["invalid_input"] == "ibuprofen"
    assert payload["error"]["recovery_hint"]
