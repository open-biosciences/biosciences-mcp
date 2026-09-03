"""Wire contracts for every server, asserted on what an agent receives.

Each test cites the ADR-001 clause it enforces. Known deviations that need an
architecture decision rather than a code fix are recorded in a deviation table
with the evidence; the test xfails while the deviation reproduces and fails
loudly once it stops, so an entry cannot outlive its bug.
"""

from __future__ import annotations

import pytest

from tests.contract.conftest import (
    ListCase,
    StrictCase,
    find_nulls,
    list_params,
    raw_string_params,
    strict_params,
)
from tests.contract.registry import check_cross_references

# One event loop for the module: servers hold module-level singleton clients
# (ADR-004), which cannot survive a per-test loop.
pytestmark = [
    pytest.mark.contract,
    pytest.mark.integration,
    pytest.mark.asyncio(loop_scope="module"),
]

ENVELOPE_KEYS = frozenset({"pagination", "error"})

# Registry deviations observed on the wire 2026-09-02. Each needs either a data
# fix in the client or an ADR-001 amendment (value format, cardinality, or new
# keys). They are recorded here so the harness stays green while the decision
# is pending, and so a fix is forced to delete its entry.
REGISTRY_DEVIATIONS: dict[str, str] = {
    "uniprot.get_protein": (
        "omim and orphanet are comma-joined strings; orphanet lacks ORPHA: prefix; "
        "ensembl_transcript carries version suffixes; refseq NP_ accessions are outside "
        "the ^[NX][MR]_ regex"
    ),
    "chembl.get_compound": "chembl is a list and carries a CHEMBL: prefix (registry: bare String)",
    "opentargets.get_target": "chembl is 'CHEMBL:CHEMBL4096' and drugbank is 'DB:DB08363' (double/wrong prefixes)",
    "ensembl.get_gene": "hgnc is 'HGNC:HGNC:11998' (double prefix)",
    "entrez.get_gene": "ensembl_gene holds a protein ID (ENSP...); uniprot values carry UniProtKB: prefix",
    "pubchem.get_compound": "pubchem_compound is a list (registry: String)",
    "iuphar.get_ligand": "chembl is a bare number '521' (registry: ^CHEMBL\\d+$)",
    "iuphar.get_target": "chembl is a bare number '233' (registry: ^CHEMBL\\d+$)",
    "wikipathways.get_pathway": (
        "hgnc holds gene symbols; entrez and ensembl_gene are lists (registry: String)"
    ),
    "clinicaltrials.get_trial": (
        "clinicaltrials_gov, mesh_conditions, mesh_interventions are not registry keys; "
        "pubmed is an unprefixed string"
    ),
}

# Strict tools whose raw-string rejection is done by FastMCP parameter
# validation, which returns a plain-text pydantic error instead of the
# ErrorEnvelope that ADR-001 §3 requires.
RAW_STRING_DEVIATIONS: dict[str, str] = {}


def _xfail_if_known(case_id: str, table: dict[str, str]) -> None:
    reason = table.get(case_id)
    if reason:
        pytest.xfail(reason)


def _fail_if_stale(case_id: str, table: dict[str, str]) -> None:
    """A recorded deviation that no longer reproduces must be deleted, not left to rot."""
    if case_id in table:
        pytest.fail(f"{case_id} now conforms; delete its entry from the deviation table")


@pytest.mark.parametrize("server_name,case", raw_string_params())
async def test_strict_tool_rejects_raw_string_with_error_envelope(
    wire_call, server_name: str, case: StrictCase
) -> None:
    """ADR-001 §3: a raw string to a strict tool returns UNRESOLVED_ENTITY."""
    result = await wire_call(server_name, case.tool, {case.arg: case.raw, **case.extra})
    case_id = f"{server_name}.{case.tool}"
    if not isinstance(result.data, dict):
        _xfail_if_known(case_id, RAW_STRING_DEVIATIONS)
    else:
        _fail_if_stale(case_id, RAW_STRING_DEVIATIONS)
    assert isinstance(result.data, dict), f"not JSON: {result.text[:200]}"
    assert result.data.get("success") is False, result.text[:300]
    error = result.data.get("error") or {}
    assert error.get("code") == "UNRESOLVED_ENTITY", result.text[:300]
    assert error.get("recovery_hint"), "ErrorEnvelope must carry a recovery_hint"


@pytest.mark.parametrize("server_name,case", list_params())
async def test_list_tool_returns_pagination_envelope(
    wire_call, server_name: str, case: ListCase
) -> None:
    """ADR-001 §8A: list tools wrap items in the canonical pagination envelope."""
    result = await wire_call(server_name, case.tool, case.args)
    assert isinstance(result.data, dict), f"not JSON: {result.text[:200]}"
    assert "items" in result.data and isinstance(result.data["items"], list), result.text[:300]
    pagination = result.data.get("pagination")
    assert isinstance(pagination, dict), "missing pagination object"
    assert set(pagination) == {"cursor", "total_count", "page_size"}, pagination
    assert isinstance(pagination["page_size"], int)


@pytest.mark.parametrize("server_name,case", list_params())
async def test_list_items_have_no_null_values(wire_call, server_name: str, case: ListCase) -> None:
    """ADR-001 §4 null policy applies to every candidate in a list."""
    result = await wire_call(server_name, case.tool, case.args)
    assert isinstance(result.data, dict), f"not JSON: {result.text[:200]}"
    nulls = find_nulls(result.data.get("items", []), "$.items")
    assert not nulls, f"null values on the wire: {nulls[:10]}"


@pytest.mark.parametrize("server_name,case", strict_params())
async def test_entity_has_no_null_values(wire_call, server_name: str, case: StrictCase) -> None:
    """ADR-001 §4 / Constitution Forbidden Patterns: omit keys, never emit null."""
    result = await wire_call(server_name, case.tool, {case.arg: case.curie, **case.extra})
    assert isinstance(result.data, dict), f"not JSON: {result.text[:200]}"
    assert "error" not in result.data, f"canonical CURIE errored: {result.text[:300]}"
    nulls = find_nulls(result.data, skip=ENVELOPE_KEYS)
    assert not nulls, f"null values on the wire: {nulls[:10]}"


@pytest.mark.parametrize("server_name,case", strict_params())
async def test_entity_cross_references_conform_to_registry(
    wire_call, server_name: str, case: StrictCase
) -> None:
    """ADR-001 §4 mandate + Appendix A: keys, formats, and cardinality."""
    if not case.has_cross_references:
        pytest.skip("tool does not return an entity with cross_references")
    result = await wire_call(server_name, case.tool, {case.arg: case.curie, **case.extra})
    assert isinstance(result.data, dict), f"not JSON: {result.text[:200]}"
    assert "error" not in result.data, f"canonical CURIE errored: {result.text[:300]}"
    assert "cross_references" in result.data, "entity lacks the mandated cross_references object"
    present = {k: v for k, v in result.data["cross_references"].items() if v is not None}
    problems = check_cross_references(present)
    case_id = f"{server_name}.{case.tool}"
    if problems:
        _xfail_if_known(case_id, REGISTRY_DEVIATIONS)
    else:
        _fail_if_stale(case_id, REGISTRY_DEVIATIONS)
    assert not problems, "\n".join(problems)
