"""Tool-surface contract for the gateway (spec 015, FR-001 to FR-006).

Compares what agents see from ``list_tools`` against the committed baseline in
``specs/015-fastmcp-4-upgrade/contracts/tool-surface-baseline-core.json``. The
invariants are defined in ``contracts/tool-surface-invariants.md``; this test is
committed green on FastMCP 2.14.5 before the pin moves, so it guards the upgrade.
It needs no network.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
from fastmcp import Client

from biosciences_mcp.servers.gateway import mcp
from tests.contract.surface_projection import (
    args_entries,
    capture_surface,
    guidance_lines,
    normalise,
    strip_keys,
)

pytestmark = [pytest.mark.contract, pytest.mark.unit]

BASELINE_PATH = (
    Path(__file__).resolve().parents[2]
    / "specs"
    / "015-fastmcp-4-upgrade"
    / "contracts"
    / "tool-surface-baseline-core.json"
)
BASELINE: dict[str, dict] = json.loads(BASELINE_PATH.read_text())["tools"]


@pytest.fixture(scope="module")
def surface() -> dict[str, dict]:
    return asyncio.run(capture_surface(mcp))


def _param_shape(param: dict) -> dict:
    return {k: v for k, v in param.items() if k != "description"}


def _searchable_text(tool: dict) -> str:
    texts = [tool["description"] or ""]
    texts += [p.get("description", "") for p in tool["params"].values()]
    return " ".join(normalise(t) for t in texts)


def test_invariant_1_names(surface):
    assert set(surface) == set(BASELINE), (
        f"added {sorted(set(surface) - set(BASELINE))}, removed {sorted(set(BASELINE) - set(surface))}"
    )


@pytest.mark.parametrize("name", sorted(BASELINE))
def test_invariant_2_parameters(surface, name):
    current = {k: _param_shape(v) for k, v in surface[name]["params"].items()}
    expected = {k: _param_shape(v) for k, v in BASELINE[name]["params"].items()}
    assert current == expected


@pytest.mark.parametrize("name", sorted(BASELINE))
def test_invariant_3_guidance_preserved(surface, name):
    haystack = _searchable_text(surface[name])
    missing = [
        line for line in guidance_lines(BASELINE[name]["description"]) if line not in haystack
    ]
    assert not missing, f"{name} lost guidance lines: {missing}"


@pytest.mark.parametrize("name", sorted(BASELINE))
def test_invariant_4_parameter_guidance(surface, name):
    tool = surface[name]
    tool_text = normalise(tool["description"] or "")
    missing = []
    for param, text in args_entries(BASELINE[name]["description"]):
        param_text = normalise(tool["params"].get(param, {}).get("description", ""))
        if text not in param_text and text not in tool_text:
            missing.append(f"Args {param}: {text}")
    for param, spec in BASELINE[name]["params"].items():
        expected = spec.get("description")
        if expected and normalise(expected) not in normalise(
            tool["params"].get(param, {}).get("description", "")
        ):
            missing.append(f"description of {param}: {expected}")
    assert not missing, f"{name} lost parameter guidance: {missing}"


def test_invariant_5_undeclared_argument_rejected():
    async def call():
        async with Client(mcp) as client:
            return await client.call_tool(
                "hgnc_get_gene",
                {"hgnc_id": "HGNC:1100", "bogus_extra": 1},
                raise_on_error=False,
            )

    result = asyncio.run(call())
    assert result.is_error, "a call with an undeclared argument must stay rejected (FR-003)"


@pytest.mark.parametrize("name", sorted(BASELINE))
def test_invariant_6_output_and_metadata(surface, name):
    current, expected = surface[name], BASELINE[name]
    assert strip_keys(current["output_schema"]) == strip_keys(expected["output_schema"])
    assert current["wrap_result"] == expected["wrap_result"]
    assert current["annotations"] == expected["annotations"]
    assert current["meta"] == expected["meta"]
