"""AGE-703: the gateway must start, and recover, without EBI.

chembl_webresource_client.new_client downloads EBI's API schema when it is
imported, with no timeout. The ChEMBL client never imports that module: it
fetches the schema on first use, with a timeout, from inside the executor call,
and builds the two SDK resources it needs from it.
"""

import asyncio
import json
import sys
import textwrap
import threading
from pathlib import Path

import httpx
import pytest
from fastmcp import Client

from biosciences_mcp.clients import chembl as chembl_module
from biosciences_mcp.clients.chembl import ChEMBLClient, ChEMBLSchemaUnavailable
from biosciences_mcp.models.envelopes import ErrorCode, ErrorEnvelope
from biosciences_mcp.servers import chembl as chembl_server
from biosciences_mcp.servers.gateway import mcp

pytestmark = [pytest.mark.unit, pytest.mark.chembl]

SPORE_SUBSET = Path(__file__).parent.parent / "fixtures" / "chembl_spore_subset.json"

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

# Builds the resources with the SDK's own client_from_url, fed the fixture
# instead of the network, and prints what QuerySet construction produced.
_SDK_REFERENCE_BUILD = textwrap.dedent(
    """
    import json
    import sys

    import requests

    schema = json.load(open(sys.argv[1]))

    class _Response:
        ok = True
        status_code = 200
        text = ""

        def json(self):
            return schema

    requests.get = lambda *args, **kwargs: _Response()

    from chembl_webresource_client.new_client import new_client

    print(json.dumps({
        name: {
            "collection_name": getattr(new_client, name).model.collection_name,
            "formats": list(getattr(new_client, name).model.formats),
            "searchable": getattr(new_client, name).model.searchable,
            "frmt": getattr(new_client, name).query.frmt,
        }
        for name in ("molecule", "drug_indication")
    }))
    """
)


@pytest.fixture
def empty_sdk_cache(monkeypatch):
    monkeypatch.setattr(chembl_module, "_sdk_resources", {})


async def _run(*args: str) -> tuple[int, str, str]:
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=120)
    return process.returncode or 0, stdout.decode(), stderr.decode()


async def test_gateway_imports_and_lists_tools_with_network_blocked():
    returncode, stdout, stderr = await _run("-c", _IMPORT_WITH_NETWORK_BLOCKED)
    assert returncode == 0, stderr[-2000:]

    async with Client(mcp) as client:
        expected = sorted(tool.name for tool in await client.list_tools())
    assert stdout.split() == expected
    assert "chembl_search_compounds" in expected


async def test_built_resources_match_the_sdk_builder():
    returncode, stdout, stderr = await _run("-c", _SDK_REFERENCE_BUILD, str(SPORE_SUBSET))
    assert returncode == 0, stderr[-2000:]
    reference = json.loads(stdout)

    built = chembl_module._build_sdk_resources(json.loads(SPORE_SUBSET.read_text()))
    ours = {
        name: {
            "collection_name": built[name].model.collection_name,
            "formats": list(built[name].model.formats),
            "searchable": built[name].model.searchable,
            "frmt": built[name].query.frmt,
        }
        for name in ("molecule", "drug_indication")
    }
    assert ours == reference


async def test_schema_failure_reaches_the_caller_as_upstream_error(monkeypatch, empty_sdk_cache):
    def unavailable():
        raise ChEMBLSchemaUnavailable("ChEMBL schema fetch from EBI failed with status 500")

    monkeypatch.setattr(chembl_module, "_fetch_schema", unavailable)
    monkeypatch.setattr(ChEMBLClient, "BASE_DELAY", 0)
    monkeypatch.setattr(chembl_server, "_client", None)

    try:
        async with Client(chembl_server.mcp) as client:
            result = await client.call_tool(
                "search_compounds", {"query": "aspirin"}, raise_on_error=False
            )
        payload = json.loads(getattr(result.content[0], "text", ""))
    finally:
        if chembl_server._client is not None:
            await chembl_server._client.close()

    assert payload["success"] is False
    assert payload["error"]["code"] == "UPSTREAM_ERROR"
    assert payload["error"]["message"] == "ChEMBL schema fetch from EBI failed with status 500"
    assert payload["error"]["recovery_hint"] == (
        "ChEMBL API temporarily unavailable. Retry in 60 seconds"
    )


def test_error_status_is_condensed(monkeypatch):
    html = "<!doctype html><html><body>Error: 500</body></html>"
    monkeypatch.setattr(chembl_module.httpx, "get", lambda *a, **k: httpx.Response(500, text=html))

    with pytest.raises(ChEMBLSchemaUnavailable) as raised:
        chembl_module._fetch_schema()

    assert str(raised.value) == "ChEMBL schema fetch from EBI failed with status 500"


def test_connection_failure_is_condensed(monkeypatch):
    def refuse(*args, **kwargs):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(chembl_module.httpx, "get", refuse)

    with pytest.raises(ChEMBLSchemaUnavailable) as raised:
        chembl_module._fetch_schema()

    assert str(raised.value) == "ChEMBL schema fetch from EBI failed: ConnectError"


@pytest.mark.parametrize(
    "message",
    [
        "ChEMBL schema fetch from EBI failed with status 404",
        "ChEMBL schema fetch from EBI failed: ConnectError",
        "ChEMBL schema fetch from EBI is still in progress",
    ],
)
def test_schema_errors_map_to_upstream_error_by_type(message):
    result = ChEMBLClient()._map_sdk_error(ChEMBLSchemaUnavailable(message), "aspirin")

    assert isinstance(result, ErrorEnvelope)
    assert result.error.code == ErrorCode.UPSTREAM_ERROR
    assert result.error.recovery_hint == "ChEMBL API temporarily unavailable. Retry in 60 seconds"


def test_failed_fetch_is_retried_on_the_next_call(monkeypatch, empty_sdk_cache):
    schema = json.loads(SPORE_SUBSET.read_text())
    outcomes = [ChEMBLSchemaUnavailable("ChEMBL schema fetch from EBI failed with status 500")]

    def fetch():
        if outcomes:
            raise outcomes.pop()
        return schema

    monkeypatch.setattr(chembl_module, "_fetch_schema", fetch)

    with pytest.raises(ChEMBLSchemaUnavailable):
        chembl_module._load_sdk_resource("molecule")
    assert chembl_module._load_sdk_resource("molecule").model.name == "molecule"


def test_a_stalled_fetch_does_not_block_other_callers_or_recovery(monkeypatch, empty_sdk_cache):
    schema = json.loads(SPORE_SUBSET.read_text())
    stalled = threading.Event()
    release = threading.Event()

    def fetch():
        if not stalled.is_set():
            stalled.set()
            release.wait(timeout=10)
            raise ChEMBLSchemaUnavailable("ChEMBL schema fetch from EBI failed: ReadTimeout")
        return schema

    monkeypatch.setattr(chembl_module, "_fetch_schema", fetch)
    monkeypatch.setattr(chembl_module, "_SCHEMA_LOCK_WAIT", 0.1)

    def first_caller():
        with pytest.raises(ChEMBLSchemaUnavailable):
            chembl_module._load_sdk_resource("molecule")

    first = threading.Thread(target=first_caller)
    first.start()
    assert stalled.wait(timeout=5)

    with pytest.raises(ChEMBLSchemaUnavailable, match="still in progress"):
        chembl_module._load_sdk_resource("molecule")

    release.set()
    first.join(timeout=5)
    assert chembl_module._load_sdk_resource("molecule").model.name == "molecule"


async def test_schema_load_runs_off_the_event_loop(monkeypatch):
    loop_thread = threading.get_ident()
    load_threads: list[int] = []

    class _Molecule:
        def search(self, query):
            return []

    def record(name: str):
        load_threads.append(threading.get_ident())
        return _Molecule()

    monkeypatch.setattr(chembl_module, "_load_sdk_resource", record)
    client = ChEMBLClient()
    try:
        await client.search_compounds("aspirin")
    finally:
        await client.close()

    assert load_threads, "schema was never loaded"
    assert loop_thread not in load_threads


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
