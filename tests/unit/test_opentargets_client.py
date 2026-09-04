"""Unit tests for OpenTargetsClient cross-reference normalization (no network)."""

import pytest

from biosciences_mcp.clients.opentargets import OpenTargetsClient

pytestmark = [pytest.mark.unit, pytest.mark.opentargets]


class TestCrossReferenceRegistryForm:
    """AGE-691: values must be in ADR-001 Appendix A registry form."""

    @pytest.mark.parametrize(
        "source,raw,expected",
        [
            ("chembl", "CHEMBL4096", "CHEMBL4096"),
            ("chembl", "4096", "CHEMBL4096"),
            ("drugbank", "DB08363", "DB08363"),
            ("hgnc", "11998", "HGNC:11998"),
            ("hgnc", "HGNC:11998", "HGNC:11998"),
            ("uniprot_swissprot", "P04637", "P04637"),
            ("uniprot_swissprot", "UniProtKB:P04637", "P04637"),
        ],
    )
    def test_normalize_curie_returns_registry_form(self, source, raw, expected):
        assert OpenTargetsClient()._normalize_curie(source, raw) == expected

    def test_list_cardinality_keys_accumulate_as_lists(self):
        refs = OpenTargetsClient()._build_cross_references(
            [
                {"source": "uniprot_swissprot", "id": "P04637"},
                {"source": "uniprot_swissprot", "id": "Q53GA5"},
                {"source": "refseq", "id": "NM_000546.6"},
                {"source": "drugbank", "id": "DB08363"},
                {"source": "drugbank", "id": "DB01254"},
            ]
        )
        assert refs.uniprot == ["P04637", "Q53GA5"]
        assert refs.refseq == ["NM_000546"]
        assert refs.drugbank == "DB08363"  # String key keeps the first value
