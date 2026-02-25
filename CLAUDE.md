# CLAUDE.md — biosciences-mcp

## Purpose

FastMCP wrappers for life sciences APIs, enabling LLM agents to query biological databases for drug discovery and repurposing. This repo is owned by the **MCP Platform Engineer** agent.

## Status

| Server | Version | Tests | Status |
|--------|---------|-------|--------|
| HGNC | v0.1.0 | 7 | ✅ Complete |
| UniProt | v0.1.0 | 12 | ✅ Complete |
| ChEMBL | v0.1.0 | 62 | ✅ Complete |
| Open Targets | v0.1.0 | 9 | ✅ Complete |
| DrugBank | v0.1.0 | 33 | ⛔ Blocked (API key required) |
| STRING | v0.1.0 | 11 | ✅ Complete |
| BioGRID | v0.1.0 | 11 | ✅ Complete |
| Ensembl | v0.1.0 | 86 | ✅ Complete |
| Entrez | v0.1.0 | 58 | ✅ Complete |
| PubChem | v0.1.0 | 85 | ✅ Complete |
| IUPHAR/GtoPdb | v0.1.0 | 59 | ✅ Complete |
| WikiPathways | v0.1.0 | 17 | ✅ Complete |
| ClinicalTrials.gov | v0.1.0 | 13 | ✅ Complete |

**Total: 12 active servers, 697+ tests (399 unit + 294 integration + 4 e2e)**

## Architecture (ADR-001 v1.4)

### Package Structure (post-migration)
```
src/biosciences_mcp/
├── clients/          # Async HTTP clients (httpx-based)
│   ├── base.py       # LifeSciencesClient base class
│   ├── hgnc.py       # HGNCClient
│   ├── uniprot.py    # UniProtClient
│   └── ...           # 13 clients total
├── models/           # Pydantic v2 models
│   ├── envelopes.py  # PaginationEnvelope, ErrorEnvelope
│   ├── cross_references.py  # Shared cross-reference schema
│   ├── gene.py       # Gene, SearchCandidate
│   └── ...           # Entity models per API
└── servers/          # FastMCP server definitions
    ├── hgnc.py       # HGNC MCP server
    ├── gateway.py    # Unified gateway (mounts all 12 servers)
    └── ...           # 12 servers + gateway
```

### Core Patterns

1. **Hybrid Client**: Native `httpx` async for modern APIs; `run_in_executor` for ChEMBL SDK only
2. **Fuzzy-to-Fact Protocol**: Fuzzy search → ranked candidates → strict lookup requires CURIEs
3. **Agentic Biolink Schema**: Flattened JSON with `cross_references` object
4. **Token Budgeting**: `slim=True` for batch operations (~20 vs ~115 tokens/entity)

### Implemented Tools

| Server | Tools | CURIE Format |
|--------|-------|--------------|
| HGNC | `search_genes`, `get_gene` | `HGNC:1100` |
| UniProt | `search_proteins`, `get_protein` | `UniProtKB:P38398` |
| ChEMBL | `search_compounds`, `get_compound`, `get_compounds_batch` | `CHEMBL:25` |
| Open Targets | `search_targets`, `get_target`, `get_associations` | `ENSG00000141510` |
| STRING | `search_proteins`, `get_interactions`, `get_network_image_url` | `STRING:9606.ENSP*` |
| BioGRID | `search_genes`, `get_interactions` | Gene symbol |
| Ensembl | `search_genes`, `get_gene`, `get_transcript` | `ENSG*`, `ENST*` |
| Entrez | `search_genes`, `get_gene`, `get_pubmed_links` | `NCBIGene:7157` |
| PubChem | `search_compounds`, `get_compound` | `PubChem:CID2244` |
| IUPHAR | `search_ligands`, `get_ligand`, `search_targets`, `get_target` | `IUPHAR:2713` |
| WikiPathways | `search_pathways`, `get_pathway`, `get_pathways_for_gene`, `get_pathway_components` | `WP:WP534` |
| ClinicalTrials | `search_trials`, `get_trial`, `get_trial_locations` | `NCT:00461032` |
| DrugBank | `search_drugs`, `get_drug` | `DrugBank:DB00945` |

## Development Commands

```bash
# Package management
uv sync                          # Install dependencies
uv sync --extra dev              # Install with dev dependencies

# Testing (marker-based)
uv run pytest -m unit -v                              # Unit tests (399 tests, no network)
uv run pytest -m integration -v                       # Integration tests (294 tests)
uv run pytest -m e2e -v                               # End-to-end tests (4 tests)
uv run pytest -m "not integration" -v                 # Fast local dev
uv run pytest -m "unit and clinicaltrials" -v         # API-specific unit tests
uv run pytest -m "integration and chembl" -v          # API-specific integration tests

# Run MCP server
uv run fastmcp run src/biosciences_mcp/servers/hgnc.py
uv run fastmcp dev src/biosciences_mcp/servers/<server>.py

# Linting
uv run ruff check --fix . && uv run ruff format .
uv run pyright
```

## Environment Variables

```bash
# Most life sciences APIs are public (no keys required)
BIOGRID_API_KEY=...              # BioGRID interactions (free)
DRUGBANK_API_KEY=...             # DrugBank (commercial tier)
NCBI_API_KEY=...                 # Entrez/PubMed rate limits (optional, free)
```

## Git Workflow

```bash
# Specification work
git switch -c feature/<id>-<description>

# Implementation work (after spec merged)
git switch -c implement/<id>-<description>
```

## Known Issues

- **ClinicalTrials.gov**: Cloudflare blocks Python httpx clients (403). Use curl for manual testing. Unit tests with mocks verify parameter logic.
- **DrugBank**: Requires commercial API key. Implementation complete, integration tests skip without key.
- **ChEMBL**: Frequently returns 500 errors. Use Open Targets `knownDrugs` GraphQL as fallback.

## Dependencies

- **Upstream**: `biosciences-architecture` (ADR schemas)
- **Downstream**: `biosciences-deepagents`, `biosciences-temporal`, `biosciences-research` (tool consumers)

## Pre-Migration Source

Until Wave 2 migration: `/home/donbr/graphiti-org/lifesciences-research/`
