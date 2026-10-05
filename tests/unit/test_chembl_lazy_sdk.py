"""AGE-703: importing the package must not need EBI.

chembl_webresource_client downloads EBI's API schema when it is imported, with
no timeout. The client now loads the SDK on first use, inside the executor call
that carries the client timeout, so the gateway starts during an EBI outage and
only the ChEMBL tools report the failure.
"""

import asyncio
import sys
import textwrap

import pytest
from fastmcp import Client

from biosciences_mcp.clients import chembl as chembl_module
from biosciences_mcp.clients.chembl import ChEMBLClient, ChEMBLSchemaUnavailable
from biosciences_mcp.models.envelopes import ErrorCode, ErrorEnvelope
from biosciences_mcp.servers.gateway import mcp

pytestmark = [pytest.mark.unit, pytest.mark.chembl]

# Runs in a fresh interpreter so the import happens with outbound network blocked.
_IMPORT_WITH_NETWORK_BLOCKED = textwrap.dedent(
    """
    import asyncio
    import socket
    import sys

    def _blocked(*args, **kwargs):
        raise OSError("network blocked by test")

    socket.socket.connect = _blocked
    socket.create_connection = _blocked
    socket.getaddrinfo = _blocked

    from fastmcp import Client
    from biosciences_mcp.servers.gateway import mcp

    assert "chembl_webresource_client.new_client" not in sys.modules

    async def main():
        async with Client(mcp) as client:
            tools = await client.list_tools()
        print("\\n".join(sorted(tool.name for tool in tools)))

    asyncio.run(main())
    """
)


async def test_gateway_imports_and_lists_tools_with_network_blocked():
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        "-c",
        _IMPORT_WITH_NETWORK_BLOCKED,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=120)
    assert process.returncode == 0, stderr.decode()[-2000:]

    async with Client(mcp) as client:
        expected = sorted(tool.name for tool in await client.list_tools())
    assert stdout.decode().split() == expected
    assert "chembl_search_compounds" in expected


async def test_schema_fetch_failure_returns_upstream_error(monkeypatch):
    def unavailable(name: str):
        raise ChEMBLSchemaUnavailable("ChEMBL schema fetch from EBI failed with status 500")

    monkeypatch.setattr(chembl_module, "_load_sdk_resource", unavailable)
    client = ChEMBLClient()
    client.BASE_DELAY = 0

    result = await client.search_compounds("aspirin")

    assert isinstance(result, ErrorEnvelope)
    assert result.error.code == ErrorCode.UPSTREAM_ERROR
    assert "status 500" in result.error.message


def test_sdk_import_failure_is_condensed(monkeypatch):
    def import_fails():
        raise Exception(
            "Error getting schema from url https://www.ebi.ac.uk/chembl/api/data/spore "
            "with status 500 and msg <!doctype html><html><body>Error: 500</body></html>"
        )

    monkeypatch.setattr(chembl_module, "_import_new_client", import_fails)

    with pytest.raises(ChEMBLSchemaUnavailable) as raised:
        chembl_module._load_sdk_resource("molecule")

    assert str(raised.value) == "ChEMBL schema fetch from EBI failed with status 500"


def test_resources_can_be_replaced_without_loading_the_sdk(monkeypatch):
    def must_not_load(name: str):
        raise AssertionError("SDK loaded")

    monkeypatch.setattr(chembl_module, "_load_sdk_resource", must_not_load)
    client = ChEMBLClient()
    stub = object()

    client._molecule = stub
    client._drug_indication = stub

    assert client._molecule is stub
    assert client._drug_indication is stub
