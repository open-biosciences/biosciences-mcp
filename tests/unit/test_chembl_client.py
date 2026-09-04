"""Unit tests for ChEMBL client error handling.

Tests for T031: Error code mapping (US4)
"""

import pytest

from biosciences_mcp.clients.chembl import ChEMBLClient
from biosciences_mcp.models.envelopes import ErrorCode, ErrorEnvelope
from tests.contract.registry import check_cross_references

pytestmark = [pytest.mark.unit, pytest.mark.chembl]


class TestChEMBLClientCurieValidation:
    """Tests for CURIE validation."""

    def test_valid_curie_returns_numeric_id(self):
        """Test valid CURIE returns numeric ID."""
        client = ChEMBLClient()
        result = client._validate_chembl_curie("CHEMBL:25")
        assert result == "25"

    def test_valid_curie_large_id(self):
        """Test valid CURIE with large numeric ID."""
        client = ChEMBLClient()
        result = client._validate_chembl_curie("CHEMBL:1201583")
        assert result == "1201583"

    def test_invalid_curie_missing_colon_returns_error(self):
        """Test: invalid CURIE -> UNRESOLVED_ENTITY."""
        client = ChEMBLClient()
        result = client._validate_chembl_curie("CHEMBL25")
        assert isinstance(result, ErrorEnvelope)
        assert result.error.code == ErrorCode.UNRESOLVED_ENTITY
        assert "CHEMBL:NNNNN" in result.error.recovery_hint

    def test_invalid_curie_lowercase_returns_error(self):
        """Test: lowercase prefix -> UNRESOLVED_ENTITY."""
        client = ChEMBLClient()
        result = client._validate_chembl_curie("chembl:25")
        assert isinstance(result, ErrorEnvelope)
        assert result.error.code == ErrorCode.UNRESOLVED_ENTITY

    def test_invalid_curie_no_prefix_returns_error(self):
        """Test: no prefix -> UNRESOLVED_ENTITY."""
        client = ChEMBLClient()
        result = client._validate_chembl_curie("25")
        assert isinstance(result, ErrorEnvelope)
        assert result.error.code == ErrorCode.UNRESOLVED_ENTITY

    def test_invalid_curie_non_numeric_returns_error(self):
        """Test: non-numeric ID -> UNRESOLVED_ENTITY."""
        client = ChEMBLClient()
        result = client._validate_chembl_curie("CHEMBL:ABC")
        assert isinstance(result, ErrorEnvelope)
        assert result.error.code == ErrorCode.UNRESOLVED_ENTITY


class TestChEMBLClientErrorMapping:
    """Tests for SDK error to ErrorEnvelope mapping."""

    def test_404_error_maps_to_entity_not_found(self):
        """Test: 404 response -> ENTITY_NOT_FOUND."""
        client = ChEMBLClient()
        error = Exception("HTTPError: 404 Not Found")
        result = client._map_sdk_error(error, "CHEMBL:99999")

        assert isinstance(result, ErrorEnvelope)
        assert result.error.code == ErrorCode.ENTITY_NOT_FOUND
        assert result.error.invalid_input == "CHEMBL:99999"

    def test_429_error_maps_to_rate_limited(self):
        """Test: 429 response -> RATE_LIMITED."""
        client = ChEMBLClient()
        error = Exception("HTTPError: 429 Too Many Requests - rate limit exceeded")
        result = client._map_sdk_error(error, "query")

        assert isinstance(result, ErrorEnvelope)
        assert result.error.code == ErrorCode.RATE_LIMITED
        assert "rate limit" in result.error.recovery_hint.lower()

    def test_500_error_maps_to_upstream_error(self):
        """Test: 500 response -> UPSTREAM_ERROR."""
        client = ChEMBLClient()
        error = Exception("HTTPError: 500 Internal Server Error")
        result = client._map_sdk_error(error, "query")

        assert isinstance(result, ErrorEnvelope)
        assert result.error.code == ErrorCode.UPSTREAM_ERROR

    def test_502_error_maps_to_upstream_error(self):
        """Test: 502 response -> UPSTREAM_ERROR."""
        client = ChEMBLClient()
        error = Exception("HTTPError: 502 Bad Gateway")
        result = client._map_sdk_error(error, "query")

        assert isinstance(result, ErrorEnvelope)
        assert result.error.code == ErrorCode.UPSTREAM_ERROR

    def test_503_error_maps_to_upstream_error(self):
        """Test: 503 response -> UPSTREAM_ERROR."""
        client = ChEMBLClient()
        error = Exception("HTTPError: 503 Service Unavailable")
        result = client._map_sdk_error(error, "query")

        assert isinstance(result, ErrorEnvelope)
        assert result.error.code == ErrorCode.UPSTREAM_ERROR

    def test_timeout_maps_to_upstream_error(self):
        """Test: timeout -> UPSTREAM_ERROR."""
        client = ChEMBLClient()
        error = Exception("Connection timeout after 30 seconds")
        result = client._map_sdk_error(error, "query")

        assert isinstance(result, ErrorEnvelope)
        assert result.error.code == ErrorCode.UPSTREAM_ERROR

    def test_unknown_error_maps_to_upstream_error(self):
        """Test: unknown error -> UPSTREAM_ERROR."""
        client = ChEMBLClient()
        error = Exception("Unknown error occurred")
        result = client._map_sdk_error(error, "query")

        assert isinstance(result, ErrorEnvelope)
        assert result.error.code == ErrorCode.UPSTREAM_ERROR


class TestChEMBLClientSearchValidation:
    """Tests for search query validation."""

    @pytest.mark.asyncio
    async def test_short_query_returns_ambiguous_query(self):
        """Test: query too short -> AMBIGUOUS_QUERY."""
        client = ChEMBLClient()
        result = await client.search_compounds("X")

        assert isinstance(result, ErrorEnvelope)
        assert result.error.code == ErrorCode.AMBIGUOUS_QUERY
        assert "2 characters" in result.error.recovery_hint
        assert result.error.invalid_input == "X"

    @pytest.mark.asyncio
    async def test_empty_query_returns_ambiguous_query(self):
        """Test: empty query -> AMBIGUOUS_QUERY."""
        client = ChEMBLClient()
        result = await client.search_compounds("")

        assert isinstance(result, ErrorEnvelope)
        assert result.error.code == ErrorCode.AMBIGUOUS_QUERY

    @pytest.mark.asyncio
    async def test_single_char_query_returns_ambiguous_query(self):
        """Test: single character query -> AMBIGUOUS_QUERY."""
        client = ChEMBLClient()
        result = await client.search_compounds("a")

        assert isinstance(result, ErrorEnvelope)
        assert result.error.code == ErrorCode.AMBIGUOUS_QUERY


class TestChEMBLClientCrossReferenceNormalization:
    """AGE-687 (chembl): cross_references values in ADR-001 Appendix A registry form."""

    @pytest.mark.parametrize(
        "key,raw,expected",
        [
            ("uniprot", "P23219", "P23219"),
            ("uniprot", "UniProtKB:P23219", "P23219"),
            ("drugbank", "00945", "DB00945"),
            ("drugbank", "DB00945", "DB00945"),
            ("drugbank", "DB:00945", "DB00945"),
            ("pdb", "1pty", "1PTY"),
            ("unknown", "some_id", "some_id"),
        ],
    )
    def test_normalize_xref_id_returns_registry_form(self, key, raw, expected):
        assert ChEMBLClient()._normalize_xref_id(key, raw) == expected

    def test_build_cross_references_returns_registry_form(self):
        sdk_result = {
            "molecule_chembl_id": "CHEMBL25",
            "cross_references": [
                {"xref_name": "UniProt", "xref_id": "P23219"},
                {"xref_name": "UniProt", "xref_id": "P35354"},
                {"xref_name": "PDBe", "xref_id": "1pty"},
                {"xref_name": "PubChem", "xref_id": "2244"},
                {"xref_name": "PubChem", "xref_id": "2245"},
                {"xref_name": "DrugBank", "xref_id": "DB00945"},
                {"xref_name": "Wikipedia", "xref_id": "Aspirin"},
            ],
        }
        refs = ChEMBLClient()._build_cross_references(sdk_result)
        dumped = refs.model_dump(exclude_none=True)
        assert check_cross_references(dumped) == []
        assert dumped == {
            "chembl": "CHEMBL25",
            "uniprot": ["P23219", "P35354"],
            "pdb": ["1PTY"],
            "pubchem_compound": "2244",
            "drugbank": "DB00945",
        }
