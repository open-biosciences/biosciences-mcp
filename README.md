# biosciences-mcp

FastMCP wrappers for life sciences APIs, enabling LLM agents to query biological databases for drug discovery and repurposing. Part of the [Open Biosciences](https://github.com/open-biosciences) platform.

## Status

**Active — Wave 2 (Platform) migration complete.** 12 FastMCP servers, 697+ tests (399 unit + 294 integration + 4 e2e), unified gateway ready for FastMCP Cloud deployment.

## What This Repo Contains

- **12 FastMCP server implementations** covering HGNC, UniProt, ChEMBL, Open Targets, STRING, BioGRID, Ensembl, Entrez, PubChem, IUPHAR, WikiPathways, and ClinicalTrials.gov
- **13 async client libraries** for programmatic access to all servers (httpx-based)
- **Pydantic v2 models** including response envelopes, cross-reference schemas, and domain entities
- **Unified gateway server** aggregating all 12 servers behind a single endpoint
- **697+ tests** organized by pytest marker (unit, integration, e2e)

All servers implement the Fuzzy-to-Fact protocol (ADR-001 §3): natural language discovery followed by strict CURIE-based lookup.

## Quick Start

```bash
# Install dependencies (including dev extras)
uv sync --extra dev

# Run unit tests (no network required)
uv run pytest -m unit -v
```

## FastMCP Cloud

Deployment is managed via the Prefect Horizon web UI at [horizon.prefect.io](https://horizon.prefect.io) —
there is no `fastmcp deploy` CLI command in FastMCP 2.x. See [CLAUDE.md](CLAUDE.md#deploying-to-fastmcp-cloud)
for step-by-step instructions.

Once deployed, the gateway endpoint will be:

```
https://biosciences-mcp.fastmcp.app/mcp
```

### Connecting via Claude Code (.mcp.json)

Add this to your `.mcp.json` to use the deployed gateway:

```json
{
  "mcpServers": {
    "biosciences-mcp": {
      "type": "http",
      "url": "https://biosciences-mcp.fastmcp.app/mcp"
    }
  }
}
```

### Required Environment Variables (Deployment Secrets)

Set these in the Horizon console when creating the deployment:

| Variable | Description | Required |
|----------|-------------|----------|
| `BIOGRID_API_KEY` | BioGRID interactions API key (free registration) | Yes for BioGRID |
| `NCBI_API_KEY` | Entrez/PubMed rate limit increase (optional, free) | No |
| `DRUGBANK_API_KEY` | DrugBank commercial API key | Yes for DrugBank |

Most life sciences APIs (HGNC, UniProt, ChEMBL, Open Targets, STRING, Ensembl, PubChem, IUPHAR, WikiPathways, ClinicalTrials.gov) are fully public and require no API key.

## Local Development

```bash
# Run the gateway in interactive dev mode (MCP Inspector UI)
fastmcp dev src/biosciences_mcp/servers/gateway.py

# Run a specific server
uv run fastmcp run src/biosciences_mcp/servers/hgnc.py
uv run fastmcp dev src/biosciences_mcp/servers/<server>.py
```

## Test Commands

```bash
# By tier
uv run pytest -m unit -v                              # 399 unit tests — no network
uv run pytest -m integration -v                       # 294 integration tests — live APIs
uv run pytest -m e2e -v                               # 4 e2e tests — requires live gateway
uv run pytest -m "not integration" -v                 # Fast local dev (unit only)

# By API
uv run pytest -m "unit and hgnc" -v
uv run pytest -m "unit and clinicaltrials" -v
uv run pytest -m "integration and chembl" -v

# E2e against the deployed cloud endpoint
FASTMCP_CLOUD_ENDPOINT=https://biosciences-mcp.fastmcp.app/mcp \
  uv run pytest -m e2e -v
```

## Package Structure

```
src/biosciences_mcp/
├── clients/          # Async HTTP clients (httpx-based)
│   ├── base.py       # LifeSciencesClient base class
│   ├── hgnc.py
│   ├── uniprot.py
│   └── ...           # 13 clients total
├── models/           # Pydantic v2 models
│   ├── envelopes.py  # PaginationEnvelope, ErrorEnvelope
│   ├── cross_references.py
│   └── ...           # Domain entity models
└── servers/          # FastMCP server definitions
    ├── gateway.py    # Unified gateway (mounts all 12 servers)
    ├── hgnc.py
    └── ...           # 12 servers
```

## Fuzzy-to-Fact Protocol

All servers enforce a two-phase workflow (ADR-001 §3):

1. **Phase 1 — Fuzzy Discovery**: Tools accept natural language, return ranked candidates with CURIEs
2. **Phase 2 — Strict Lookup**: Tools accept only resolved CURIEs (e.g., `HGNC:1100`, `UniProtKB:P38398`)
3. **Failure Mode**: Passing raw strings to strict tools returns `UNRESOLVED_ENTITY` error

```python
# Example: fuzzy search -> CURIE resolution -> strict lookup
result = await client.call_tool("search_genes", {"query": "BRCA1"})
curie = result["items"][0]["id"]  # "HGNC:1100"
gene = await client.call_tool("get_gene", {"hgnc_id": curie})
```

## Agent Ownership

Maintained by the **MCP Platform Engineer** agent (Agent 3). See [AGENTS.md](../biosciences-program/AGENTS.md) for full team definitions.

## Dependencies

| Direction | Repository | Relationship |
|-----------|------------|--------------|
| Upstream | biosciences-architecture | Schemas and ADRs |
| Downstream | biosciences-deepagents | LangGraph agents consume MCP tools |
| Downstream | biosciences-temporal | Temporal activities call MCP tools |
| Downstream | biosciences-research | Graph-builder workflows use MCP tools |

## Related Repositories

- [biosciences-architecture](https://github.com/open-biosciences/biosciences-architecture) — ADRs and schemas
- [biosciences-deepagents](https://github.com/open-biosciences/biosciences-deepagents) — LangGraph multi-agent system
- [biosciences-temporal](https://github.com/open-biosciences/biosciences-temporal) — Temporal durable workflows
- [biosciences-research](https://github.com/open-biosciences/biosciences-research) — Research workflows

## License

MIT
