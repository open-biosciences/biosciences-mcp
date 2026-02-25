# Wave 2 Migration Design — biosciences-mcp

**Date**: 2026-02-25
**Status**: Approved
**Linear Parent**: AGE-150 [Wave 2] Platform — MCP Servers + Memory
**Sub-issues**: AGE-159 through AGE-167

## Approach

Single-pass "rename on copy" migration. Copy all source code, tests, and config from
`lifesciences-research` into `biosciences-mcp`, renaming `lifesciences_mcp` to
`biosciences_mcp` during the copy. Drop unused deps (`pulumi`, `claude-agent-sdk`).
Validate with unit tests. Integration tests run separately post-commit.

## Source and Target

- **Source**: `/home/donbr/graphiti-org/lifesciences-research/`
- **Target**: `/home/donbr/open-biosciences/biosciences-mcp/`

## What Moves

| Category | Source Path | Target Path | Files |
|----------|-----------|-------------|-------|
| Clients | `src/lifesciences_mcp/clients/` | `src/biosciences_mcp/clients/` | 15 |
| Models | `src/lifesciences_mcp/models/` | `src/biosciences_mcp/models/` | 20 |
| Servers | `src/lifesciences_mcp/servers/` | `src/biosciences_mcp/servers/` | 15 |
| Package init | `src/lifesciences_mcp/__init__.py` | `src/biosciences_mcp/__init__.py` | 1 |
| Tests | `tests/` | `tests/` | 59 |
| Config | root | root | 3 |
| **Total** | | | **~113** |

## What Changes

1. **Directory name**: `src/lifesciences_mcp/` -> `src/biosciences_mcp/`
2. **All imports**: `lifesciences_mcp` -> `biosciences_mcp` (source + tests)
3. **pyproject.toml**: name `biosciences-mcp`, packages `["src/biosciences_mcp"]`, drop `pulumi` and `claude-agent-sdk`
4. **ruff.toml**: `known-first-party = ["biosciences_mcp"]`
5. **Empty `tools/` package**: Dropped (no content)

## What Stays the Same

- All tool names, CURIE formats, API behavior
- All Pydantic models and envelope schemas
- All test logic (only imports change)
- All pytest markers and configuration
- ADR compliance (Fuzzy-to-Fact, normative models)

## What Does NOT Move

- `.claude/` directory (Wave 1, already migrated)
- `docs/` (Wave 4 scope)
- `ra_agents/`, `ra_orchestrators/`, `ra_tools/` (Wave 3 scope)
- `.github/` CI workflows (out of scope)
- `scripts/`, `specs/`, `architecture/` (out of scope)

## Dependencies (pyproject.toml)

### Keep
- `chembl-webresource-client>=0.10.9` (ChEMBL Python SDK)
- `defusedxml>=0.7.1` (XML parsing safety)
- `fastmcp>=2.14.1` (FastMCP server framework)
- `httpx>=0.27` (async HTTP client)
- `pydantic>=2.0` (data validation)

### Drop
- `pulumi>=3.214.1` (infrastructure-as-code, not used by MCP source)
- `claude-agent-sdk>=0.1.18` (not used by MCP source)

### Dev Dependencies (keep all)
- `pytest>=8.0`, `pytest-asyncio>=0.23`, `pytest-timeout>=2.4.0`
- `ruff>=0.8`, `pyright>=1.1`

## biosciences-memory Scope

Wave 2 for memory is **verification only**. `.mcp.json` and `.env.example` are already
committed. No new code. AGE-167 is a connection verification task after MCP servers
are migrated.

## Validation Strategy

1. `uv sync` — dependencies install
2. `uv run pytest -m unit -v` — 399+ unit tests pass (proves rename correct)
3. `uv run ruff check .` — linting clean
4. `uv run pyright` — type checking clean
5. Security review via `/security-review` skill
6. Integration tests run post-commit as separate verification

## Linear Issue Mapping

| Step | Linear Issue | Description |
|------|-------------|-------------|
| Copy servers | AGE-159 | 12 servers + gateway |
| Copy clients | AGE-160 | 13 client libraries |
| Copy models | AGE-161 | 19 Pydantic models |
| Copy gateway | AGE-162 | Gateway server |
| Rename package | AGE-163 | Done during copy (rename on copy) |
| Copy unit tests | AGE-164 | 20 test files |
| Copy integration tests | AGE-165 | 23 test files |
| Copy e2e tests | AGE-166 | 1 test file |
| Verify memory | AGE-167 | MCP connection check |

## Migration Rules (from Graphiti priming namespace)

- **Rename on copy**: Never have `lifesciences_mcp` in new repo git history
- **Test after each wave**: Wave 3 cannot start until Wave 2 acceptance passes
- **ADRs travel first**: Already satisfied (Wave 1 complete)
