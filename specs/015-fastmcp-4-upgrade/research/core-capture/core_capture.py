"""Spec 015 T018: core wire capture through the gateway, network-free.

Usage (from a core checkout root, so `tests` is importable):
    PYTHONPATH=src:. uv run python <this file> <step> <out_dir>

The cases come from the contract tier's own definitions
(`tests.contract.conftest.SERVERS`): each server's strict lookups with their
identifier argument, valid CURIE, raw-string input, and extra arguments. Nothing
here is hand-written per tool, so the capture can't drift from the contract tests.

It calls the gateway (`biosciences_mcp.servers.gateway.mcp`, the surface Horizon
serves) in process and records each full CallToolResult: content,
structuredContent, isError and _meta. All outbound HTTP is intercepted (httpx and,
for ChEMBL's SDK, requests) and backoff sleeps are stubbed, so results are
deterministic and independent of upstream availability. Cases:

- raw_string: every strict tool with its raw-string input (Fuzzy-to-Fact failure mode)
- validation: hgnc_get_gene with an undeclared argument, a missing one, and a wrong type
- upstream_500 / upstream_429: every httpx-based server's strict tool with its valid
  CURIE, against a simulated upstream status (ChEMBL is recorded as not simulated)

Writes core_wire_<step>.json.
"""

import asyncio
import importlib.metadata as md
import json
import sys
from unittest import mock

import httpx
import requests
from fastmcp import Client

from biosciences_mcp.servers.gateway import mcp
from tests.contract.conftest import SERVERS

STEP, OUT = sys.argv[1], sys.argv[2]
CALL_TIMEOUT = 60
SDK_SERVERS = {"chembl"}  # upstream calls go through requests, not httpx


def versions():
    return {p: md.version(p) for p in ("fastmcp", "mcp", "pydantic", "httpx")}


def dump_result(res):
    content = []
    for block in res.content:
        d = block.model_dump(mode="json", by_alias=True, exclude_none=True)
        if d.get("type") == "text":
            try:
                d["text_parsed"] = json.loads(d["text"])
            except ValueError:
                pass
        content.append(d)
    return {
        "isError": res.isError,
        "content": content,
        "structuredContent": res.structuredContent,
        "meta": getattr(res, "meta", None),
    }


def httpx_upstream(status):
    async def send(_client, request, *_args, **_kwargs):
        if status is None:
            raise httpx.ConnectError("network blocked by core_capture", request=request)
        headers = {"Retry-After": "0"} if status == 429 else {}
        return httpx.Response(status, request=request, headers=headers, json={"error": status})

    return send


def requests_blocked(_session, request, **_kwargs):
    raise requests.ConnectionError(f"network blocked by core_capture: {request.url}")


async def no_sleep(*_args, **_kwargs):
    return None


async def call(client, name, args):
    try:
        result = await asyncio.wait_for(client.call_tool_mcp(name, args), CALL_TIMEOUT)
        return dump_result(result)
    except TimeoutError:
        return {"timeout": f">{CALL_TIMEOUT}s"}
    except Exception as exc:  # transport-level failure, recorded as data
        return {"exception": f"{type(exc).__name__}: {exc}"}


def network(status):
    return (
        mock.patch.object(httpx.AsyncClient, "send", httpx_upstream(status)),
        mock.patch.object(requests.Session, "send", requests_blocked),
        mock.patch("asyncio.sleep", no_sleep),
    )


async def capture():
    cases = {}
    async with Client(mcp) as client:
        mounted = {t.name for t in await client.list_tools()}
        skipped = sorted(
            f"{s.name}_{c.tool}"
            for s in SERVERS.values()
            for c in s.strict
            if f"{s.name}_{c.tool}" not in mounted
        )
        p1, p2, p3 = network(None)
        with p1, p2, p3:
            for server in SERVERS.values():
                for case in server.strict:
                    tool = f"{server.name}_{case.tool}"
                    if case.raw is None or tool not in mounted:
                        continue
                    cases[f"raw_string:{tool}"] = await call(
                        client, tool, {case.arg: case.raw, **case.extra}
                    )
            cases["validation:undeclared_argument"] = await call(
                client, "hgnc_get_gene", {"hgnc_id": "HGNC:1100", "bogus_extra": 1}
            )
            cases["validation:missing_argument"] = await call(client, "hgnc_get_gene", {})
            cases["validation:wrong_type"] = await call(client, "hgnc_get_gene", {"hgnc_id": 1100})
        for status in (500, 429):
            p1, p2, p3 = network(status)
            with p1, p2, p3:
                for server in SERVERS.values():
                    if not server.strict:
                        continue
                    case = server.strict[0]
                    tool = f"{server.name}_{case.tool}"
                    if tool not in mounted:
                        continue
                    key = f"upstream_{status}:{tool}"
                    if server.name in SDK_SERVERS:
                        cases[key] = {"not_simulated": "SDK client (requests), not httpx"}
                        continue
                    cases[key] = await call(client, tool, {case.arg: case.curie, **case.extra})
    return {"versions": versions(), "not_on_gateway": skipped, "cases": cases}


def main():
    result = asyncio.run(capture())
    path = f"{OUT}/core_wire_{STEP}.json"
    with open(path, "w") as fh:
        json.dump(result, fh, indent=1, sort_keys=True)
    timeouts = [k for k, v in result["cases"].items() if "timeout" in v]
    print(
        json.dumps(result["versions"]),
        len(result["cases"]),
        "cases ->",
        path,
        "timeouts:",
        timeouts,
    )


if __name__ == "__main__":
    main()
