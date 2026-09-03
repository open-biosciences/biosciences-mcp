"""ADR-001 v1.4 Appendix A: Cross-Reference Key Registry as executable data.

One entry per key. ``pattern`` is the Format Regex column verbatim; ``multi``
is True where the Cardinality column says ``List[String]``.

This table is the contract the wire tests assert against. When ADR-001 is
amended (a v1.5 is pending), change this table in the same commit.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class KeySpec:
    """Format and cardinality of one registry key."""

    pattern: re.Pattern[str]
    multi: bool
    tier: str

    def accepts(self, value: object) -> list[str]:
        """Return a list of violations for ``value`` (empty means conformant)."""
        problems: list[str] = []
        if self.multi:
            if not isinstance(value, list):
                return [f"expected List[String], got {type(value).__name__}"]
            items = value
        else:
            if isinstance(value, list):
                return [f"expected String, got list of {len(value)}"]
            items = [value]
        for item in items:
            if not isinstance(item, str):
                problems.append(f"non-string value {item!r}")
            elif not self.pattern.match(item):
                problems.append(f"{item!r} does not match {self.pattern.pattern}")
        return problems


def _k(pattern: str, *, multi: bool = False, tier: str) -> KeySpec:
    return KeySpec(pattern=re.compile(pattern), multi=multi, tier=tier)


REGISTRY: dict[str, KeySpec] = {
    # Core Identifiers
    "hgnc": _k(r"^HGNC:\d+$", tier="core"),
    "ensembl_gene": _k(r"^ENSG\d{11}$", tier="core"),
    "ensembl_transcript": _k(r"^ENST\d{11}$", multi=True, tier="core"),
    "uniprot": _k(r"^[A-Z0-9]{6,10}$", multi=True, tier="core"),
    "entrez": _k(r"^\d+$", tier="core"),
    "refseq": _k(r"^[NX][MR]_\d+$", multi=True, tier="core"),
    "ucsc": _k(r"^UCSC:[\w]+\.[\d]+$", tier="core"),
    "pubmed": _k(r"^PMID:\d+$", multi=True, tier="core"),
    # Tier 0: Drug Discovery Core
    "chembl": _k(r"^CHEMBL\d+$", tier="0"),
    "drugbank": _k(r"^DB\d{5}$", tier="0"),
    # Tier 1-2: Interaction Networks
    "string": _k(r"^\d+\.[A-Za-z0-9]+$", tier="1-2"),
    "biogrid": _k(r"^\d+$", tier="1-2"),
    "stitch": _k(r"^(CID[sm])?\d+$", tier="1-2"),
    "iuphar": _k(r"^\d+$", tier="1-2"),
    # Tier 3: Pathways & Disease
    "kegg": _k(r"^[a-z]{3,4}:\d+$", tier="3"),
    "kegg_pathway": _k(r"^[a-z]{3,4}\d{5}$", multi=True, tier="3"),
    "omim": _k(r"^\d{6}$", tier="3"),
    "orphanet": _k(r"^ORPHA:\d+$", tier="3"),
    "mondo": _k(r"^MONDO:\d{7}$", tier="3"),
    "efo": _k(r"^EFO:\d{7}$", tier="3"),
    # Tier 4: Structural & Chemical
    "pdb": _k(r"^[0-9][A-Z0-9]{3}$", multi=True, tier="4"),
    "pubchem_compound": _k(r"^\d+$", tier="4"),
    "pubchem_substance": _k(r"^\d+$", tier="4"),
}

assert len(REGISTRY) == 23, "ADR-001 v1.4 Appendix A defines 23 keys"


def check_cross_references(xrefs: object) -> list[str]:
    """Return every registry violation in a ``cross_references`` payload."""
    if not isinstance(xrefs, dict):
        return [f"cross_references must be an object, got {type(xrefs).__name__}"]
    problems: list[str] = []
    for key, value in xrefs.items():
        spec = REGISTRY.get(key)
        if spec is None:
            problems.append(f"key {key!r} is not in the ADR-001 registry")
            continue
        if value is None:
            problems.append(f"key {key!r} is null (must be omitted)")
            continue
        problems.extend(f"{key}: {p}" for p in spec.accepts(value))
    return problems
