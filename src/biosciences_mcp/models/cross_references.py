"""Core identifier models for Biosciences MCP Server.

This module defines general-purpose identifier models and validation patterns
used across multiple domain models (Gene, Protein, Target, etc.).

Refactored from models/gene.py to decouple Protocol Types from Domain Types.
"""

import re

from pydantic import Field, model_validator

from biosciences_mcp.models.base import OmitNoneModel

# Cross-reference regex patterns from ADR-001 Appendix A
CROSS_REF_PATTERNS = {
    "ensembl_gene": re.compile(r"^ENSG\d{11}$"),
    "ensembl_transcript": re.compile(r"^ENST\d{11}$"),
    "uniprot": re.compile(r"^[A-Z0-9]{6,10}$"),
    "entrez": re.compile(r"^\d+$"),
    "refseq": re.compile(r"^[NX][MR]_\d+$"),
    "omim": re.compile(r"^\d{6}$"),
    "chembl": re.compile(r"^CHEMBL\d+$"),
    "pubchem_compound": re.compile(r"^\d+$"),
}


def _strip_prefixes(value: str, prefixes: tuple[str, ...]) -> str:
    """Remove any of the given prefixes, repeatedly, case-insensitively."""
    changed = True
    while changed:
        changed = False
        for prefix in sorted(
            prefixes, key=len, reverse=True
        ):  # longest first: "Orphanet:" before "ORPHA"
            if value.lower().startswith(prefix.lower()):
                value = value[len(prefix) :]
                changed = True
    return value


def normalize_xref(key: str, value: str) -> str:
    """Return ``value`` in the ADR-001 Appendix A registry form for ``key``.

    Upstream APIs spell the same identifier several ways (``521``, ``CHEMBL521``,
    ``CHEMBL:CHEMBL521``). Every client must call this before storing a value in
    ``cross_references`` so the wire form is the registry form. Keys without a
    rewrite rule are returned unchanged (apart from surrounding whitespace).
    """
    value = value.strip()
    if key == "hgnc":
        return f"HGNC:{_strip_prefixes(value, ('HGNC:',))}"
    if key == "chembl":
        return f"CHEMBL{_strip_prefixes(value, ('CHEMBL:', 'CHEMBL'))}"
    if key == "drugbank":
        local = _strip_prefixes(value, ("DrugBank:", "DB:"))
        return f"DB{local.zfill(5)}" if local.isdigit() else local
    if key == "uniprot":
        # NCBI product records carry a sequence version (P04637.4); the registry does not
        return _strip_prefixes(value, ("UniProtKB:", "UniProt:")).split(".", 1)[0]
    if key == "orphanet":
        return f"ORPHA:{_strip_prefixes(value, ('ORPHA:', 'ORPHA', 'Orphanet:'))}"
    if key == "pubmed":
        return f"PMID:{_strip_prefixes(value, ('PMID:',))}"
    if key in ("ensembl_gene", "ensembl_transcript", "refseq"):
        return value.split(".", 1)[0]
    return value


class CrossReferences(OmitNoneModel):
    """External database identifiers per the ADR-001 Appendix A registry.

    Keys are omitted if no value exists (never null or empty string).
    All values are validated against their respective regex patterns.
    """

    # Core identifiers
    ensembl_gene: str | None = Field(
        default=None,
        description="Ensembl gene ID (e.g., ENSG00000012048)",
    )
    ensembl_transcript: list[str] | None = Field(
        default=None,
        description="Ensembl transcript IDs",
    )
    uniprot: list[str] | None = Field(
        default=None,
        description="UniProt accessions",
    )
    entrez: str | None = Field(
        default=None,
        description="NCBI Entrez gene ID",
    )
    refseq: list[str] | None = Field(
        default=None,
        description="RefSeq accessions",
    )
    hgnc: str | None = Field(
        default=None,
        description="HGNC gene ID (e.g., HGNC:5)",
    )

    # Disease/phenotype
    omim: str | None = Field(
        default=None,
        description="OMIM ID",
    )
    orphanet: str | None = Field(
        default=None,
        description="Orphanet rare disease ID (e.g., ORPHA:558)",
    )
    mondo: str | None = Field(
        default=None,
        description="MONDO disease ontology ID",
    )
    efo: str | None = Field(
        default=None,
        description="Experimental Factor Ontology ID",
    )

    # Drug/compound
    chembl: str | None = Field(
        default=None,
        description="ChEMBL target/compound ID",
    )
    drugbank: str | None = Field(
        default=None,
        description="DrugBank ID (e.g., DB01050)",
    )
    pubchem_compound: str | None = Field(
        default=None,
        description="PubChem compound ID",
    )
    pubchem_substance: str | None = Field(
        default=None,
        description="PubChem substance ID",
    )

    # Pathway databases
    kegg: str | None = Field(
        default=None,
        description="KEGG gene ID",
    )
    kegg_pathway: list[str] | None = Field(
        default=None,
        description="KEGG pathway IDs",
    )

    # Interaction databases
    string: str | None = Field(
        default=None,
        description="STRING protein ID",
    )
    biogrid: str | None = Field(
        default=None,
        description="BioGRID gene ID",
    )
    stitch: str | None = Field(
        default=None,
        description="STITCH chemical-protein interaction ID",
    )
    iuphar: str | None = Field(
        default=None,
        description="IUPHAR/GtoPdb ligand or target ID",
    )

    # Structural
    pdb: list[str] | None = Field(
        default=None,
        description="Protein Data Bank IDs",
    )

    # Genomic location
    ucsc: str | None = Field(
        default=None,
        description="UCSC Genome Browser ID (e.g., UCSC:uc001kfb.4)",
    )

    # Literature
    pubmed: list[str] | None = Field(
        default=None,
        description="Related PubMed IDs (e.g., PMID:123456)",
    )

    @model_validator(mode="after")
    def omit_empty_values(self) -> "CrossReferences":
        """Ensure no empty strings or empty lists are stored (omit instead)."""
        for field_name in type(self).model_fields:
            value = getattr(self, field_name)
            if value == "" or value == []:
                setattr(self, field_name, None)
        return self


#: Registry keys with List[String] cardinality (ADR-001 Appendix A), derived from the model.
MULTI_VALUE_KEYS: frozenset[str] = frozenset(
    name for name, f in CrossReferences.model_fields.items() if "list[" in str(f.annotation)
)
