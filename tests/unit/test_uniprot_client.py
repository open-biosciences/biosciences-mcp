"""Unit tests for UniProtClient cross-reference mapping (no network)."""

import pytest

from biosciences_mcp.clients.uniprot import UniProtClient
from tests.contract.registry import check_cross_references

pytestmark = [pytest.mark.unit, pytest.mark.uniprot]

# Shape of uniProtKBCrossReferences entries in the UniProt REST JSON for P04637
P04637_REFS = [
    {"database": "HGNC", "id": "HGNC:11998", "properties": [{"key": "GeneName", "value": "TP53"}]},
    {"database": "GeneID", "id": "7157", "properties": []},
    {
        "database": "Ensembl",
        "id": "ENST00000269305.9",
        "properties": [
            {"key": "ProteinId", "value": "ENSP00000269305.4"},
            {"key": "GeneId", "value": "ENSG00000141510.18"},
        ],
    },
    {
        "database": "Ensembl",
        "id": "ENST00000359597.8",
        "properties": [
            {"key": "ProteinId", "value": "ENSP00000352610.4"},
            {"key": "GeneId", "value": "ENSG00000141510.18"},
        ],
    },
    {
        "database": "RefSeq",
        "id": "NP_000537.3",
        "properties": [{"key": "NucleotideSequenceId", "value": "NM_000546.6"}],
    },
    {
        "database": "RefSeq",
        "id": "NP_001119584.1",
        "properties": [{"key": "NucleotideSequenceId", "value": "NM_001126112.3"}],
    },
    {"database": "MIM", "id": "191170", "properties": [{"key": "Type", "value": "gene"}]},
    {"database": "MIM", "id": "151623", "properties": [{"key": "Type", "value": "phenotype"}]},
    {"database": "Orphanet", "id": "524", "properties": [{"key": "Disease", "value": "LFS"}]},
    {"database": "Orphanet", "id": "1331", "properties": [{"key": "Disease", "value": "x"}]},
    {"database": "STRING", "id": "9606.ENSP00000269305", "properties": []},
    {"database": "BioGRID", "id": "113010", "properties": []},
    {"database": "KEGG", "id": "hsa:7157", "properties": []},
    {"database": "PDB", "id": "1TUP", "properties": []},
]


class TestCrossReferenceRegistryForm:
    """AGE-687 (uniprot): values in ADR-001 Appendix A registry form."""

    def test_mapped_values_conform_to_registry(self):
        refs = UniProtClient()._map_cross_references(P04637_REFS)
        assert check_cross_references(refs.model_dump(exclude_none=True)) == []

    def test_disease_ids_are_single_values_not_comma_joined(self):
        refs = UniProtClient()._map_cross_references(P04637_REFS)
        assert refs.omim == "191170"  # Type == gene preferred
        assert refs.orphanet == "ORPHA:524"

    def test_ensembl_ids_have_no_version_and_gene_id_is_derived(self):
        refs = UniProtClient()._map_cross_references(P04637_REFS)
        assert refs.ensembl_transcript == ["ENST00000269305", "ENST00000359597"]
        assert refs.ensembl_gene == "ENSG00000141510"

    def test_refseq_uses_nucleotide_accessions(self):
        refs = UniProtClient()._map_cross_references(P04637_REFS)
        assert refs.refseq == ["NM_000546", "NM_001126112"]

    def test_omim_prefers_gene_plus_phenotype_over_a_leading_phenotype_entry(self):
        # Live UniProt shape for P04637: phenotype entries precede the gene entry,
        # and the gene entry is typed "gene+phenotype", not "gene".
        refs = UniProtClient()._map_cross_references(
            [
                {
                    "database": "MIM",
                    "id": "133239",
                    "properties": [{"key": "Type", "value": "phenotype"}],
                },
                {
                    "database": "MIM",
                    "id": "191170",
                    "properties": [{"key": "Type", "value": "gene+phenotype"}],
                },
            ]
        )
        assert refs.omim == "191170"

    def test_omim_falls_back_to_first_when_no_gene_type(self):
        refs = UniProtClient()._map_cross_references(
            [
                {
                    "database": "MIM",
                    "id": "151623",
                    "properties": [{"key": "Type", "value": "phenotype"}],
                }
            ]
        )
        assert refs.omim == "151623"
