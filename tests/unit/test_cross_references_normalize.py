"""normalize_xref: one place that turns upstream identifier spellings into the
ADR-001 Appendix A registry form for a given cross_references key."""

import pytest

from biosciences_mcp.models.cross_references import normalize_xref

pytestmark = [pytest.mark.unit]


@pytest.mark.parametrize(
    "key,raw,expected",
    [
        # hgnc: registry ^HGNC:\d+$ ; upstreams send bare, single, or double prefix
        ("hgnc", "11998", "HGNC:11998"),
        ("hgnc", "HGNC:11998", "HGNC:11998"),
        ("hgnc", "HGNC:HGNC:11998", "HGNC:11998"),
        # chembl: registry ^CHEMBL\d+$ ; upstreams send bare digits or CHEMBL: prefix
        ("chembl", "CHEMBL521", "CHEMBL521"),
        ("chembl", "521", "CHEMBL521"),
        ("chembl", "CHEMBL:CHEMBL4096", "CHEMBL4096"),
        ("chembl", "CHEMBL:25", "CHEMBL25"),
        # drugbank: registry ^DB\d{5}$
        ("drugbank", "DB08363", "DB08363"),
        ("drugbank", "DB:DB08363", "DB08363"),
        ("drugbank", "DrugBank:DB00945", "DB00945"),
        # uniprot: registry bare accession
        ("uniprot", "P04637", "P04637"),
        ("uniprot", "UniProtKB:P04637", "P04637"),
        ("uniprot", "P04637.4", "P04637"),
        # orphanet: registry ^ORPHA:\d+$
        ("orphanet", "ORPHA121177", "ORPHA:121177"),
        ("orphanet", "121177", "ORPHA:121177"),
        ("orphanet", "ORPHA:121177", "ORPHA:121177"),
        # pubmed: registry ^PMID:\d+$
        ("pubmed", "12345", "PMID:12345"),
        ("pubmed", "PMID:12345", "PMID:12345"),
        # ensembl ids: registry has no version suffix
        ("ensembl_gene", "ENSG00000141510.18", "ENSG00000141510"),
        ("ensembl_transcript", "ENST00000269305.9", "ENST00000269305"),
        # keys without a rewrite rule pass through
        ("entrez", "7157", "7157"),
        ("omim", "191170", "191170"),
    ],
)
def test_normalize_xref_returns_registry_form(key: str, raw: str, expected: str) -> None:
    assert normalize_xref(key, raw) == expected


def test_normalize_xref_strips_whitespace() -> None:
    assert normalize_xref("chembl", " CHEMBL25 ") == "CHEMBL25"
