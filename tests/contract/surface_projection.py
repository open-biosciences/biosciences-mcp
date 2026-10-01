"""Tool-surface projection shared by the tool-surface contract test (spec 015).

Copied from ``specs/015-fastmcp-4-upgrade/research/surface-tools/project_surface.py``,
which generated the committed baseline, so the test and the baseline project the
surface the same way. Version-tolerant across FastMCP 2.x, 3.x and 4.x.
"""

from __future__ import annotations

import re
from typing import Any

from fastmcp import Client

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

# Any column-0 "Name:" line starts a docstring section (FastMCP 3.2.4+ drops it and
# everything after it from the description). "Args:" is the only one kept in source.
SECTION_HEADER = re.compile(r"^([A-Z][A-Za-z ]{1,30}):\s*$")


def first_attr(obj: Any, *names: str) -> Any:
    for name in names:
        value = getattr(obj, name, None)
        if value is not None:
            return value
    return None


def deref(schema: dict | None) -> dict | None:
    if not schema:
        return schema
    defs = schema.get("$defs", {})

    def walk(node: Any, seen: tuple[str, ...] = ()) -> Any:
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


def strip_keys(node: Any, keys: tuple[str, ...] = ("description", "title")) -> Any:
    if isinstance(node, dict):
        return {k: strip_keys(v, keys) for k, v in node.items() if k not in keys}
    if isinstance(node, list):
        return [strip_keys(v, keys) for v in node]
    return node


def norm_meta(meta: Any) -> dict:
    meta = meta if isinstance(meta, dict) else {}
    inner = meta.get("fastmcp") or meta.get("_fastmcp") or {}
    return {"tags": sorted(inner.get("tags") or [])}


def project_param(name: str, spec: dict, required: set[str]) -> dict:
    alternatives = spec.get("anyOf", [])
    param: dict[str, Any] = {
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


def project_tool(tool: Any) -> dict:
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


async def capture_surface(server: Any) -> dict[str, dict]:
    async with Client(server) as client:
        tools = await client.list_tools()
    return {tool.name: project_tool(tool) for tool in tools}


def normalise(text: str) -> str:
    return " ".join(text.split())


def split_sections(description: str) -> tuple[list[str], list[tuple[str, list[str]]]]:
    """Split a docstring-derived description into leading lines and (header, body) sections."""
    lead: list[str] = []
    sections: list[tuple[str, list[str]]] = []
    for line in description.splitlines():
        match = SECTION_HEADER.match(line)
        if match and not line.startswith(" "):
            sections.append((match.group(1), []))
        elif sections:
            sections[-1][1].append(line)
        else:
            lead.append(line)
    return lead, sections


def guidance_lines(description: str) -> list[str]:
    """Every non-blank line except section headers and the per-parameter Args: lines."""
    lead, sections = split_sections(description)
    lines = list(lead)
    for header, body in sections:
        if header != "Args":
            lines.extend(body)
    return [normalise(line) for line in lines if line.strip()]


def args_entries(description: str, param_names: set[str]) -> list[tuple[str, str]]:
    """(parameter, text) pairs from the Args: section, one per non-blank line.

    A line starts a new entry only when its leading name is a declared parameter;
    any other line (for example an indented ``Example: "..."`` or ``Default: ...``)
    continues the current parameter's entry.
    """
    _, sections = split_sections(description)
    entries = []
    for header, body in sections:
        if header != "Args":
            continue
        current = None
        for line in body:
            if not line.strip():
                continue
            match = re.match(r"\s*(\w+)\s*(?:\([^)]*\))?:\s*(.*)", line)
            if match and match.group(1) in param_names:
                current = match.group(1)
                text = match.group(2)
            else:
                text = line
            if current and text.strip():
                entries.append((current, normalise(text)))
    return entries
