"""Open Targets MCP Server - Target-disease association resolution using the Fuzzy-to-Fact protocol.

This server provides tools for target-disease association queries:
- search_targets: Fuzzy search returning ranked target candidates
- get_target: Strict lookup by Ensembl gene ID CURIE
- get_associations: Target-disease associations with evidence

Usage:
    uv run fastmcp run src/biosciences_mcp/servers/opentargets.py
"""

from fastmcp import FastMCP

from biosciences_mcp.clients import OpenTargetsClient
from biosciences_mcp.models import (
    ErrorEnvelope,
    PaginationEnvelope,
)

# Initialize the MCP server
mcp = FastMCP("Open Targets Server")

# Shared client instance (connection pooling)
_client: OpenTargetsClient | None = None


async def get_client() -> OpenTargetsClient:
    """Get or create the shared Open Targets client."""
    global _client
    if _client is None:
        _client = OpenTargetsClient()
    return _client


@mcp.tool
async def search_targets(
    query: str,
    slim: bool = False,
    cursor: str | None = None,
    page_size: int = 50,
) -> PaginationEnvelope | ErrorEnvelope:
    """Fuzzy search for targets (genes/proteins) by name, symbol, or description.

    Returns ranked candidates for resolution. Use this before calling get_target.

    PaginationEnvelope with target candidates, or ErrorEnvelope on failure.

    Args:
        query: Search term (gene symbol, name, or natural language query).
               Minimum 2 characters required.
        slim: If true, return minimal fields (~20 tokens per entity).
              Default false returns full candidates.
        cursor: Opaque cursor for pagination. Pass from previous response for next page.
        page_size: Number of results per page (1-100, default 50).
    """
    client = await get_client()
    return await client.search_targets(
        query=query,
        slim=slim,
        cursor=cursor,
        page_size=page_size,
    )


@mcp.tool
async def get_target(ensembl_id: str, slim: bool = False) -> dict | ErrorEnvelope:
    """Get complete target record by Ensembl gene ID CURIE.

    Returns full Agentic Biolink entity with cross-references.
    Requires resolved CURIE from search_targets.

    Target record with cross_references, or ErrorEnvelope on failure.

    Args:
        ensembl_id: Ensembl gene ID CURIE in format 'ENSG[0-9]{11}' (e.g., 'ENSG00000141510').
        slim: If true, return minimal fields for token efficiency.
    """
    client = await get_client()
    return await client.get_target(ensembl_id=ensembl_id, slim=slim)


@mcp.tool
async def get_associations(
    target_id: str,
    disease_id: str | None = None,
    cursor: str | None = None,
    page_size: int = 50,
) -> PaginationEnvelope | ErrorEnvelope:
    """Get target-disease associations with evidence.

    PaginationEnvelope with association records, or ErrorEnvelope on failure.

    Args:
        target_id: Ensembl gene ID CURIE.
        disease_id: Optional EFO disease ID to filter associations.
        cursor: Opaque cursor for pagination.
        page_size: Number of results per page (1-100, default 50).
    """
    client = await get_client()
    return await client.get_associations(
        target_id=target_id,
        disease_id=disease_id,
        cursor=cursor,
        page_size=page_size,
    )


if __name__ == "__main__":
    mcp.run()
