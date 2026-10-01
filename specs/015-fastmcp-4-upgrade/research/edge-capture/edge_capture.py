"""Phase 0 capture for biosciences-mcp-edge: tool surface + wire payloads.

Usage (from the edge worktree): uv run python edge_capture.py <step> <research_dir>
Writes C-tool_surface_edge_<step>.json and C-wire_edge_<step>.json.
The real BIOGRID_API_KEY is redacted from every captured string.
"""

import asyncio
import importlib.metadata as md
import json
import os
import sys
from contextlib import contextmanager
from unittest import mock

import httpx
from fastmcp import Client

from biosciences_mcp_edge.server import mcp

STEP = sys.argv[1]
OUT = sys.argv[2]
REAL_KEY = os.environ.get("BIOGRID_API_KEY") or ""
FAKE_KEY = "FAKE-KEY-FOR-CAPTURE"


def redact(obj):
    if isinstance(obj, str):
        return obj.replace(REAL_KEY, "<REDACTED_REAL_BIOGRID_KEY>") if REAL_KEY else obj
    if isinstance(obj, list):
        return [redact(x) for x in obj]
    if isinstance(obj, dict):
        return {k: redact(v) for k, v in obj.items()}
    return obj


def versions():
    return {p: md.version(p) for p in ("fastmcp", "mcp", "pydantic", "httpx")}


@contextmanager
def upstream_status(status: int, headers=None):
    """Make every httpx.AsyncClient.send return `status` (no network)."""

    async def fake_send(self, request, *a, **kw):
        return httpx.Response(status, request=request, text="simulated", headers=headers or {})

    with mock.patch.object(httpx.AsyncClient, "send", fake_send):
        yield


@contextmanager
def env(**kv):
    old = {k: os.environ.get(k) for k in kv}
    for k, v in kv.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
    try:
        yield
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def dump_result(res):
    content = []
    for c in res.content:
        d = c.model_dump(mode="json", by_alias=True, exclude_none=True)
        if d.get("type") == "text":
            try:
                d["text_parsed"] = json.loads(d["text"])
            except Exception:
                pass
        content.append(d)
    return {
        "isError": res.isError,
        "content": content,
        "structuredContent": res.structuredContent,
    }


def find_nulls(obj, path="$"):
    out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if v is None:
                out.append(f"{path}.{k}")
            else:
                out.extend(find_nulls(v, f"{path}.{k}"))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out.extend(find_nulls(v, f"{path}[{i}]"))
    return out


def is_upstream_5xx(d):
    sc = d.get("structuredContent") or {}
    body = sc.get("result", sc) if isinstance(sc, dict) else {}
    err = (body or {}).get("error") or {}
    msg = err.get("message", "")
    return err.get("code") == "UPSTREAM_ERROR" and any(
        f"error {c}" in msg for c in range(500, 600)
    )


async def call(client, name, args):
    try:
        res = await client.call_tool_mcp(name, args)
        return dump_result(res)
    except Exception as e:  # transport-level exception
        return {"exception": f"{type(e).__name__}: {e}"}


async def main():
    surface = {"versions": versions(), "tools": []}
    wire = {"versions": versions(), "cases": {}}
    async with Client(mcp) as client:
        tools = await client.list_tools_mcp()
        for t in tools.tools:
            surface["tools"].append(
                {
                    "name": t.name,
                    "description": t.description,
                    "inputSchema": t.inputSchema,
                    "outputSchema": t.outputSchema,
                    "annotations": t.annotations.model_dump(mode="json", exclude_none=True)
                    if t.annotations
                    else None,
                    "meta": getattr(t, "meta", None),
                    "title": getattr(t, "title", None),
                }
            )
        surface["tools"].sort(key=lambda x: x["name"])

        cases = {
            # (a) live success
            "orcs_success_live": ("get_orcs_essentiality", {"entrez_id": 7298}, None),
            "mechanism_success_live": ("get_mechanism", {"chembl_id": "CHEMBL:225072"}, None),
            # (b) free text
            "orcs_free_text": ("get_orcs_essentiality", {"entrez_id": "TYMS"}, None),
            "mechanism_free_text": ("get_mechanism", {"chembl_id": "pemetrexed"}, None),
            # (c) simulated upstream 500 (fake key so nothing real can leak)
            "orcs_upstream_500": ("get_orcs_essentiality", {"entrez_id": 7298}, 500),
            "mechanism_upstream_500": ("get_mechanism", {"chembl_id": "CHEMBL:225072"}, 500),
            # extras for envelope parity
            "mechanism_upstream_429": ("get_mechanism", {"chembl_id": "CHEMBL:225072"}, 429),
            "orcs_missing_api_key": ("get_orcs_essentiality", {"entrez_id": 7298}, "nokey"),
            "mechanism_not_found_live": ("get_mechanism", {"chembl_id": "CHEMBL:1"}, None),
        }
        for label, (tool, args, mode) in cases.items():
            if mode is None:
                d = await call(client, tool, args)
                if label.endswith("_live") and is_upstream_5xx(d):
                    await asyncio.sleep(10)
                    d2 = await call(client, tool, args)
                    d = {"first_attempt": d, "retry": d2}
                    if is_upstream_5xx(d2):
                        d["status"] = "UPSTREAM_FLAKE"
            elif mode == "nokey":
                with env(BIOGRID_API_KEY=None):
                    d = await call(client, tool, args)
            else:
                with env(BIOGRID_API_KEY=FAKE_KEY), upstream_status(mode):
                    d = await call(client, tool, args)
            d = redact(d)
            d["args"] = args
            d["simulated_status"] = mode
            d["null_paths_structured"] = find_nulls(d.get("structuredContent"))
            wire["cases"][label] = d

    with open(f"{OUT}/C-tool_surface_edge_{STEP}.json", "w") as f:
        json.dump(redact(surface), f, indent=2, sort_keys=True)
    with open(f"{OUT}/C-wire_edge_{STEP}.json", "w") as f:
        json.dump(wire, f, indent=2, sort_keys=True)
    print(json.dumps(wire["versions"]))
    for k, v in wire["cases"].items():
        print(k, "isError=", v.get("isError"), "nulls=", len(v["null_paths_structured"]),
              "exc=" if "exception" in v else "", v.get("exception", "")[:120])


asyncio.run(main())
