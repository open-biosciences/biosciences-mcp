"""Fixtures for wire-level contract tests.

``SERVERS`` is the catalogue of every server, its strict tools with a canonical
CURIE and a raw-string counterexample, and its list tools with minimal
arguments. ``wire_call`` invokes a tool in-process through ``fastmcp.Client``
and returns exactly what an agent would receive.
"""

from __future__ import annotations

import importlib
import json
import os
from dataclasses import dataclass, field
from typing import Any

import pytest
from fastmcp import Client


@dataclass(frozen=True)
class StrictCase:
    """A strict (Phase 2) tool with a resolved CURIE and a raw-string input."""

    tool: str
    arg: str
    curie: str
    raw: str | None
    extra: dict[str, Any] = field(default_factory=dict)
    has_cross_references: bool = True


@dataclass(frozen=True)
class ListCase:
    """A fuzzy or list (Phase 1) tool with minimal arguments."""

    tool: str
    args: dict[str, Any]


@dataclass(frozen=True)
class ServerSpec:
    name: str
    strict: tuple[StrictCase, ...]
    lists: tuple[ListCase, ...]
    requires_env: str | None = None


SERVERS: dict[str, ServerSpec] = {
    "hgnc": ServerSpec(
        "hgnc",
        (StrictCase("get_gene", "hgnc_id", "HGNC:1100", "BRCA1"),),
        (ListCase("search_genes", {"query": "BRCA1", "page_size": 2}),),
    ),
    "uniprot": ServerSpec(
        "uniprot",
        (StrictCase("get_protein", "uniprot_id", "UniProtKB:P38398", "BRCA1"),),
        (ListCase("search_proteins", {"query": "BRCA1", "page_size": 2}),),
    ),
    "chembl": ServerSpec(
        "chembl",
        (StrictCase("get_compound", "chembl_id", "CHEMBL:25", "aspirin"),),
        (ListCase("search_compounds", {"query": "aspirin", "page_size": 2}),),
    ),
    "opentargets": ServerSpec(
        "opentargets",
        (StrictCase("get_target", "ensembl_id", "ENSG00000141510", "TP53"),),
        (ListCase("search_targets", {"query": "TP53", "page_size": 2}),),
    ),
    "string": ServerSpec(
        "string",
        (
            StrictCase(
                "get_interactions",
                "string_id",
                "STRING:9606.ENSP00000269305",
                "TP53",
                extra={"limit": 2},
            ),
        ),
        (ListCase("search_proteins", {"query": "TP53", "limit": 2}),),
    ),
    "biogrid": ServerSpec(
        "biogrid",
        # BioGRID's strict identifier is the validated gene symbol itself, so
        # there is no raw-string counterexample.
        (StrictCase("get_interactions", "gene_symbol", "TP53", None, extra={"max_results": 2}),),
        (ListCase("search_genes", {"query": "TP53"}),),
        requires_env="BIOGRID_API_KEY",
    ),
    "ensembl": ServerSpec(
        "ensembl",
        (StrictCase("get_gene", "ensembl_id", "ENSG00000141510", "TP53"),),
        (ListCase("search_genes", {"query": "TP53", "page_size": 2}),),
    ),
    "entrez": ServerSpec(
        "entrez",
        (StrictCase("get_gene", "entrez_id", "NCBIGene:7157", "TP53"),),
        (ListCase("search_genes", {"query": "TP53", "page_size": 2}),),
    ),
    "pubchem": ServerSpec(
        "pubchem",
        (StrictCase("get_compound", "pubchem_id", "PubChem:CID2244", "aspirin"),),
        (ListCase("search_compounds", {"query": "aspirin", "page_size": 2}),),
    ),
    "iuphar": ServerSpec(
        "iuphar",
        (
            StrictCase("get_ligand", "iuphar_id", "IUPHAR:2713", "morphine"),
            StrictCase("get_target", "iuphar_id", "IUPHAR:319", "opioid"),
        ),
        (
            ListCase("search_ligands", {"query": "morphine", "page_size": 2}),
            ListCase("search_targets", {"query": "opioid", "page_size": 2}),
        ),
    ),
    "wikipathways": ServerSpec(
        "wikipathways",
        (StrictCase("get_pathway", "pathway_id", "WP:WP534", "glycolysis"),),
        (ListCase("search_pathways", {"query": "glycolysis", "page_size": 2}),),
    ),
    "clinicaltrials": ServerSpec(
        "clinicaltrials",
        (StrictCase("get_trial", "nct_id", "NCT:00461032", "cancer"),),
        (ListCase("search_trials", {"query": "cancer", "page_size": 2}),),
    ),
    "drugbank": ServerSpec(
        "drugbank",
        (StrictCase("get_drug", "drugbank_id", "DrugBank:DB00945", "aspirin"),),
        (ListCase("search_drugs", {"query": "aspirin", "page_size": 2}),),
        requires_env="DRUGBANK_API_KEY",
    ),
}


@dataclass
class WireResult:
    """What the agent receives: the text block parsed as JSON, plus structured content."""

    text: str
    data: Any
    structured: dict[str, Any] | None
    is_error: bool


def find_nulls(obj: Any, path: str = "$", *, skip: frozenset[str] = frozenset()) -> list[str]:
    """Return JSON paths of every ``null`` value, skipping subtrees named in ``skip``."""
    found: list[str] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in skip:
                continue
            here = f"{path}.{key}"
            if value is None:
                found.append(here)
            else:
                found.extend(find_nulls(value, here, skip=skip))
    elif isinstance(obj, list):
        for index, value in enumerate(obj):
            found.extend(find_nulls(value, f"{path}[{index}]", skip=skip))
    return found


def strict_params() -> list[Any]:
    return [
        pytest.param(
            server.name,
            case,
            id=f"{server.name}.{case.tool}",
            marks=getattr(pytest.mark, server.name),
        )
        for server in SERVERS.values()
        for case in server.strict
    ]


def raw_string_params() -> list[Any]:
    return [
        pytest.param(
            server.name,
            case,
            id=f"{server.name}.{case.tool}",
            marks=getattr(pytest.mark, server.name),
        )
        for server in SERVERS.values()
        for case in server.strict
        if case.raw is not None
    ]


def list_params() -> list[Any]:
    return [
        pytest.param(
            server.name,
            case,
            id=f"{server.name}.{case.tool}",
            marks=getattr(pytest.mark, server.name),
        )
        for server in SERVERS.values()
        for case in server.lists
    ]


@pytest.fixture
def wire_call():
    """Call a tool on a named server in-process and return the wire payload."""

    async def _call(server_name: str, tool: str, args: dict[str, Any]) -> WireResult:
        spec = SERVERS[server_name]
        if spec.requires_env and not os.getenv(spec.requires_env):
            pytest.skip(f"{spec.requires_env} not set")
        module = importlib.import_module(f"biosciences_mcp.servers.{server_name}")
        async with Client(module.mcp) as client:
            result = await client.call_tool(tool, args, raise_on_error=False)
        text = getattr(result.content[0], "text", "") if result.content else ""
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            data = None
        return WireResult(
            text=text,
            data=data,
            structured=result.structured_content,
            is_error=bool(result.is_error),
        )

    return _call
