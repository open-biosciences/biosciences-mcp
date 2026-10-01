"""Project a FastMCP server's tool surface into the spec 015 baseline shape.

Usage (from a checkout whose environment has the server package installed):
    uv run python project_surface.py <module> <out.json>
    e.g. project_surface.py biosciences_mcp.servers.gateway surface.json

Version-tolerant across FastMCP 2.x, 3.x and 4.x: reads inputSchema/input_schema,
outputSchema/output_schema, and _meta._fastmcp/_meta.fastmcp. Output schemas are
$ref-dereferenced so $defs inlining (3.x+) does not register as a change.
"""

import asyncio
import importlib
import json
import sys
import warnings

import fastmcp
from fastmcp import Client

warnings.simplefilter("ignore")

CONSTRAINT_KEYS = (
    "minLength",
    "maxLength",
    "minimum",
    "maximum",
    "exclusiveMinimum",
    "exclusiveMaximum",
    "pattern",
    "enum",
    "items",
    "minItems",
    "maxItems",
    "format",
)


def first_attr(obj, *names):
    for name in names:
        value = getattr(obj, name, None)
        if value is not None:
            return value
    return None


def deref(schema):
    if not schema:
        return schema
    defs = schema.get("$defs", {})

    def walk(node, seen=()):
        if isinstance(node, dict):
            ref = node.get("$ref", "")
            if ref.startswith("#/$defs/"):
                key = ref.split("/")[-1]
                if key in seen:
                    return {"$recursive": key}
                return walk(defs.get(key, {}), (*seen, key))
            return {k: walk(v, seen) for k, v in node.items() if k != "$defs"}
        if isinstance(node, list):
            return [walk(v, seen) for v in node]
        return node

    return walk(schema)


def norm_meta(meta):
    meta = meta if isinstance(meta, dict) else {}
    inner = meta.get("fastmcp") or meta.get("_fastmcp") or {}
    return {"tags": sorted(inner.get("tags") or [])}


def project_param(name, spec, required):
    alternatives = spec.get("anyOf", [])
    param = {
        "type": spec.get("type", [alt.get("type") for alt in alternatives] or None),
        "required": name in required,
    }
    if "default" in spec:
        param["default"] = spec["default"]
    if spec.get("description"):
        param["description"] = spec["description"]
    constraints = {key: spec[key] for key in CONSTRAINT_KEYS if key in spec}
    for alt in alternatives:
        for key in CONSTRAINT_KEYS:
            if key in alt:
                constraints.setdefault(key, alt[key])
    if constraints:
        param["constraints"] = constraints
    return param


def project_tool(tool):
    input_schema = first_attr(tool, "inputSchema", "input_schema") or {}
    output_schema = first_attr(tool, "outputSchema", "output_schema")
    required = set(input_schema.get("required", []))
    annotations = first_attr(tool, "annotations")
    return {
        "description": tool.description,
        "params": {
            name: project_param(name, spec, required)
            for name, spec in sorted(input_schema.get("properties", {}).items())
        },
        "output_schema": deref(output_schema),
        "wrap_result": bool((output_schema or {}).get("x-fastmcp-wrap-result")),
        "annotations": annotations.model_dump(exclude_none=True) if annotations else None,
        "meta": norm_meta(first_attr(tool, "meta", "_meta")),
    }


async def capture(module_name):
    server = importlib.import_module(module_name).mcp
    async with Client(server) as client:
        tools = await client.list_tools()
    return {
        "captured_with": f"fastmcp {fastmcp.__version__}",
        "tools": {tool.name: project_tool(tool) for tool in sorted(tools, key=lambda t: t.name)},
    }


def main():
    module_name, out_path = sys.argv[1], sys.argv[2]
    surface = asyncio.run(capture(module_name))
    with open(out_path, "w") as fh:
        json.dump(surface, fh, indent=1, sort_keys=True)
        fh.write("\n")
    print(surface["captured_with"], len(surface["tools"]), "tools ->", out_path)


if __name__ == "__main__":
    main()
