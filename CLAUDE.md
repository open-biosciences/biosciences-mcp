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

**Total: 12 active servers, 875+ tests (510 unit + 363 integration + 4 e2e; the `contract` marker selects the 175-case wire-level ADR-001 tier inside those)**

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
uv run pytest -m unit -v                              # Unit tests (510 tests, no network)
uv run pytest -m integration -v                       # Integration tests (363 tests)
uv run pytest -m e2e -v                               # End-to-end tests (4 tests)
uv run pytest -m "contract and unit" -v               # ADR-001 serialisation contract (106, no network)
uv run pytest -m "contract and integration" -v        # ADR-001 wire contract per server (69, network)
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

## Spec Kit

Spec Kit v1.0.4 (upgraded 2026-09-03, AGE-702). Commands are skills under `.claude/skills/speckit-*/` and are invoked with a hyphen: `/speckit-specify`, `/speckit-plan`, `/speckit-tasks`, `/speckit-implement`, `/speckit-analyze`, `/speckit-checklist`, `/speckit-converge`. The January 2026 dotted commands are gone.

- Select the feature explicitly: `SPECIFY_FEATURE_DIRECTORY=specs/NNN-<name>` in the environment, or `.specify/feature.json` (per-checkout, git-ignored). The branch name does not select it.
- `/speckit-converge` audits the code against `spec.md`, `plan.md`, `tasks.md`, and the constitution and **appends** a `## Phase N: Convergence` section to `tasks.md`; it never edits code or specs. Run it per feature after changing that feature's code; it is the artifact-side gate that pairs with `pytest -m contract`.
- `/speckit-analyze` reads artifacts only; it cannot see code drift.
- The constitution (`.specify/memory/constitution.md`) was preserved byte-for-byte by the upgrade; the four stock templates and four scripts were refreshed (no local customizations existed).

## Known Issues

- **Serialisation (ADR-001 §4)**: every entity model MUST inherit `OmitNoneModel` from `models/base.py`. FastMCP never calls `model_dump()`, so `model_dump` overrides and `ConfigDict(exclude_none=True)` do not reach the wire; `tests/contract/` fails on either. Envelopes stay on `BaseModel` (§8 allows null `cursor`/`total_count`).
- **ClinicalTrials.gov**: Cloudflare blocks Python httpx clients (403). Use curl for manual testing. Unit tests with mocks verify parameter logic.
- **DrugBank**: Requires commercial API key. Implementation complete, integration tests skip without key.
- **ChEMBL**: Frequently returns 500 errors. Use Open Targets `knownDrugs` GraphQL as fallback.

## FastMCP Deployment

### fastmcp.json Role

The `fastmcp.json` at the repo root declares the gateway entrypoint for the FastMCP CLI and FastMCP Cloud. Key fields:

- `source.path`: `src/biosciences_mcp/servers/gateway.py`
- `source.entrypoint`: `mcp` (the `FastMCP("Biosciences MCP Gateway")` variable)
- `environment.python`: `>=3.11`
- `environment.project`: `.` (uses `pyproject.toml` for dependency resolution)
- `deployment.transport`: `http`

Per the FastMCP documentation, only the `source` field is required. The `environment` and `deployment` sections are optional. **There is no `name` field in the `fastmcp.json` schema** — the deployment name (which determines the subdomain `biosciences-mcp.fastmcp.app`) is set via the FastMCP Cloud / Prefect Horizon web UI when creating the server, not in the config file.

### Deploying to FastMCP Cloud

Deployment is managed via the **Prefect Horizon web UI** at [horizon.prefect.io](https://horizon.prefect.io).
There is no `fastmcp deploy` or `fastmcp auth` CLI command in FastMCP 2.x — deployment is web-UI-only.

1. Go to [horizon.prefect.io](https://horizon.prefect.io) and sign in with GitHub
2. Create a new server deployment pointing to this repo with entrypoint:
   ```
   src/biosciences_mcp/servers/gateway.py:mcp
   ```
3. Set secrets in the Horizon console UI: `BIOGRID_API_KEY`, `NCBI_API_KEY`
4. Set the server name to `biosciences-mcp` in the UI — this determines the subdomain
5. Endpoint after deployment: `https://biosciences-mcp.fastmcp.app/mcp`

### Running E2E Tests Against Cloud

```bash
FASTMCP_CLOUD_ENDPOINT=https://biosciences-mcp.fastmcp.app/mcp \
  uv run pytest -m e2e -v
```

### Local Development Server

```bash
fastmcp dev src/biosciences_mcp/servers/gateway.py
```

### Authentication

FastMCP Cloud requires a Bearer API key for all clients. Set `BIOSCIENCES_API_KEY` in your
environment — obtain the key from the Prefect Horizon console.

```bash
# In .env (gitignored) or shell environment
BIOSCIENCES_API_KEY=fmcp_<your-key>
```

The key is passed automatically by:
- **Python clients**: `Client(url, auth=os.getenv("BIOSCIENCES_API_KEY"))`
- **Claude Code .mcp.json**: `"Authorization": "Bearer ${BIOSCIENCES_API_KEY}"` header
- **E2E tests**: fixture reads `BIOSCIENCES_API_KEY` from env; skips if absent

### .mcp.json Integration (Claude Code)

```json
{
  "mcpServers": {
    "biosciences-mcp": {
      "type": "http",
      "url": "https://biosciences-mcp.fastmcp.app/mcp",
      "headers": {
        "Authorization": "Bearer ${BIOSCIENCES_API_KEY}"
      }
    }
  }
}
```

Set `BIOSCIENCES_API_KEY` in your shell or `.env` before starting Claude Code.

## Dependencies

- **Upstream**: `biosciences-architecture` (ADR schemas)
- **Downstream**: `biosciences-deepagents`, `biosciences-temporal`, `biosciences-research` (tool consumers)
