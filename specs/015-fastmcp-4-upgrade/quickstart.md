# Quickstart: Validating the FastMCP 3.4 Upgrade

**Feature**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md) | **Contracts**: [contracts/](contracts/)

This runbook proves each upgraded repository meets the spec before its pin moves on `main` (FR-011). Run §1–§3 on the upgrade branch, and §4 on a Horizon preview deployment. Record the results in the evidence record ([data-model.md](data-model.md#upgrade-evidence-record)).

## Prerequisites

- A worktree on the repository's upgrade branch (`implement/015-…`), under `.worktrees/` (ADR-PRG-001 §3.3).
- `uv sync --extra dev` completed.
- For §4: Horizon access, `BIOSCIENCES_API_KEY` in the environment (`.env`, never committed), and the BioGRID and NCBI secrets set in the preview deployment.

## §1 Versions

```bash
uv run python -c "import importlib.metadata as m; print(m.version('fastmcp'), m.version('mcp'))"
```

**Expected**: `3.4.7` (or a later 3.4.x, if ADR-009 allows it) and `mcp` 1.x (1.26.0 in the current lock).

## §2 Test tiers (core)

```bash
uv run pytest -m unit -q -p no:cacheprovider
uv run pytest -m "contract and unit" -q -p no:cacheprovider
uv run pytest tests/integration/test_gateway.py -q -p no:cacheprovider
uv run pytest -m "contract and integration" -q -p no:cacheprovider
```

**Expected**:
- `unit` and `contract and unit` all pass, including the new tool-surface and policy tests.
- `test_gateway.py` passes.
- `contract and integration` shows no failure beyond the 2.14.5 baseline: 11 failures on 2026-09-30, all Ensembl 500s or IUPHAR 401s (research R7).
- Rerun any failure once after 10 seconds. A persistent upstream 5xx or 4xx that also fails on the baseline is recorded as upstream, not as a regression (FR-012).
- No Pydantic serializer warnings appear in the output (none were seen at 3.4.7; they are a 4.x issue, R8).

## §2e Test tiers (edge)

```bash
uv run pytest -m unit -q -p no:cacheprovider
```

**Expected**: all pass, including `test_tool_surface.py` and `test_framework_version_policy.py`. Edge's other unit tests cover models only and give no framework signal (research C). The tool-surface test is the framework check.

## §3 Policy self-check (SC-007)

On a scratch copy of the branch, set the lock or the dependency bound to a known-bad version (for example `fastmcp==3.4.3`), then run `uv run pytest tests/unit/test_framework_version_policy.py -q`.

**Expected**: the test fails, and the message names ADR-009 and the Host-guard incident. Discard the scratch change.

## §4 Preview deployment (one per repository)

Create a separate Horizon deployment from the upgrade branch. Use the same entrypoint (`src/biosciences_mcp/servers/gateway.py:mcp` for core) and the same secrets, under a non-production name. Leave all `FASTMCP_HTTP_*` host variables unset (research R2). Then check:

| # | Check | How | Expected |
|---|---|---|---|
| 4.1 | Host accepted | Authenticated MCP `initialize` POST to the preview's public `/mcp` URL | HTTP 200, not 421 |
| 4.2 | Tool count and names | `fastmcp.Client(url, auth=...)` then `list_tools` | Core: 34 names equal to the baseline keys. Edge: 2. |
| 4.3 | One call per server | One representative success call per server (core 12, edge 2). Upstream failures follow FR-012. | Pagination envelope, or a documented upstream failure |
| 4.4 | Strict-tool failure mode | `hgnc_get_gene` with free text (core); `get_mechanism` and `get_orcs_essentiality` with free text (edge) | Core: `UNRESOLVED_ENTITY` envelope. Edge: the same as the 3.0.2 capture, meaning `UNRESOLVED_ENTITY` for `get_mechanism` and a framework validation error for `get_orcs_essentiality` (spec US3 scenario 2; AGE-735) |
| 4.5 | Sessionless call (core) | Raw JSON-RPC `tools/call` POST with no `initialize` and no session header, as `biosciences-deepagents` `apps/api/shared/mcp.py` sends it | Success. "400 Missing session ID" means No-Go until Horizon's session mode is resolved (research R12). |
| 4.6 | Telemetry wrapper | Run the gateway under biosciences-otel-stack's `opentelemetry-instrument` wrapper locally at 3.4.7, built from the upgrade worktree (not the primary checkout; see tasks.md telemetry task) | Starts, serves `list_tools`, emits to the local collector, or degrades silently with no collector (FR-019) |
| 4.7 | Rollback timing | Redeploy the preview from the pre-upgrade commit, and time it until 4.2 passes on the old version | Under 15 minutes (SC-005) |
| 4.8 | Temporal client (core) | Locally, with `BIOSCIENCES_MCP_PATH` pointing at the upgrade worktree, use biosciences-temporal's `create_mcp_client()` (stdio, PydanticAI) to list tools and call `hgnc_search_genes` and `hgnc_get_gene`. Then run one agent workflow if its LLM key is configured. | 34 tools, both calls succeed. Temporal picks up core's checkout as soon as it updates after merge, so this runs before merge (SC-003). |

Record each result with the date and the preview URL. All checks passing turns the Phase 0 Conditional Go into Go for that repository. Failure of 4.1, or of 4.5 with no configuration fix, means No-Go.

## §5 After production

Repeat checks 4.1, 4.2, and 4.5 against the production endpoint. For core, also run `FASTMCP_CLOUD_ENDPOINT=https://biosciences-mcp.fastmcp.app/mcp uv run pytest -m e2e -v`.
