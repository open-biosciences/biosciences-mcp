# Wave 2 MCP Migration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Migrate all 12 FastMCP servers, 13 clients, 19 models, gateway, and 697+ tests from `lifesciences-research` into `biosciences-mcp` with package rename.

**Architecture:** Single-pass rename-on-copy. Source files are copied with directory renamed from `lifesciences_mcp` to `biosciences_mcp`, then a global find-and-replace fixes all imports. Config files are written fresh with correct values.

**Tech Stack:** Python 3.11+, FastMCP, httpx, Pydantic v2, pytest, ruff, pyright, uv, hatchling

**Linear Issues:** AGE-150 (parent), AGE-159 through AGE-167 (sub-issues)

---

### Task 1: Copy source code with directory rename

**Files:**
- Create: `src/biosciences_mcp/` (entire directory tree)
- Source: `/home/donbr/graphiti-org/lifesciences-research/src/lifesciences_mcp/`

**Step 1: Copy source directory with new name**

```bash
cd /home/donbr/open-biosciences/biosciences-mcp
cp -r /home/donbr/graphiti-org/lifesciences-research/src/lifesciences_mcp src/biosciences_mcp
```

**Step 2: Remove empty tools/ package (not needed)**

```bash
rm -rf src/biosciences_mcp/tools
```

**Step 3: Verify file count**

```bash
find src/biosciences_mcp -name "*.py" | wc -l
```

Expected: ~50 files (51 minus tools/__init__.py)

**Step 4: Global rename in source files**

```bash
find src/biosciences_mcp -name "*.py" -exec sed -i 's/lifesciences_mcp/biosciences_mcp/g' {} +
```

**Step 5: Verify no lifesciences_mcp references remain in source**

```bash
grep -r "lifesciences_mcp" src/
```

Expected: No output (zero matches)

---

### Task 2: Copy test files

**Files:**
- Create: `tests/` (entire directory tree)
- Source: `/home/donbr/graphiti-org/lifesciences-research/tests/`

**Step 1: Copy tests directory**

```bash
cd /home/donbr/open-biosciences/biosciences-mcp
cp -r /home/donbr/graphiti-org/lifesciences-research/tests .
```

**Step 2: Remove manual and gaps tests (excluded from CI)**

```bash
rm -rf tests/manual tests/gaps
```

**Step 3: Remove postman collection (not needed in new repo)**

```bash
rm -rf tests/postman
```

**Step 4: Global rename in test files**

```bash
find tests -name "*.py" -exec sed -i 's/lifesciences_mcp/biosciences_mcp/g' {} +
```

**Step 5: Update docstrings referencing old name**

```bash
find tests -name "*.py" -exec sed -i 's/Life Sciences MCP/Biosciences MCP/g' {} +
find src -name "*.py" -exec sed -i 's/Life Sciences MCP/Biosciences MCP/g' {} +
find src -name "*.py" -exec sed -i 's/lifesciences-research/biosciences-mcp/g' {} +
```

**Step 6: Verify no lifesciences references remain**

```bash
grep -r "lifesciences_mcp" tests/
grep -r "lifesciences-research" tests/ src/
```

Expected: No output for either command

---

### Task 3: Create pyproject.toml

**Files:**
- Create: `pyproject.toml`

**Step 1: Write pyproject.toml**

```toml
[project]
name = "biosciences-mcp"
version = "0.1.0"
description = "FastMCP wrappers for life sciences APIs - enabling AI agents to query biological databases for drug discovery and repurposing"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "chembl-webresource-client>=0.10.9",
    "defusedxml>=0.7.1",
    "fastmcp>=2.14.1",
    "httpx>=0.27",
    "pydantic>=2.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "python-dotenv>=1.0",
    "ruff>=0.8",
    "pyright>=1.1",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/biosciences_mcp"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"
testpaths = ["tests"]
markers = [
    "unit: marks tests as unit tests (no network required)",
    "integration: marks tests as integration tests (require network)",
    "e2e: marks tests as end-to-end tests (require live server)",
    "hgnc: tests for HGNC gene nomenclature API",
    "uniprot: tests for UniProt protein database API",
    "chembl: tests for ChEMBL compound database (Python SDK)",
    "opentargets: tests for Open Targets API",
    "string: tests for STRING protein interaction API",
    "biogrid: tests for BioGRID interaction API",
    "ensembl: tests for Ensembl genomics API",
    "entrez: tests for NCBI Entrez API",
    "pubchem: tests for PubChem compound API",
    "iuphar: tests for IUPHAR/GtoPdb pharmacology API",
    "wikipathways: tests for WikiPathways API",
    "clinicaltrials: tests for ClinicalTrials.gov API",
    "drugbank: tests for DrugBank API",
]
timeout = 60
timeout_method = "thread"

[tool.pyright]
include = ["src"]
pythonVersion = "3.11"
typeCheckingMode = "basic"
reportMissingTypeStubs = false

[dependency-groups]
dev = [
    "pytest-timeout>=2.4.0",
]
```

Notes vs source:
- Dropped `pulumi` and `claude-agent-sdk` (unused by MCP code)
- Added `python-dotenv>=1.0` to dev deps (used by `tests/conftest.py`)
- Package name: `biosciences-mcp`
- Wheel packages: `["src/biosciences_mcp"]`

---

### Task 4: Create ruff.toml and .env.example

**Files:**
- Create: `ruff.toml`
- Create: `.env.example`

**Step 1: Write ruff.toml**

```toml
# Ruff configuration for Biosciences MCP
# https://docs.astral.sh/ruff/

line-length = 100
target-version = "py311"

[lint]
select = [
    "E",      # pycodestyle errors
    "W",      # pycodestyle warnings
    "F",      # Pyflakes
    "I",      # isort
    "B",      # flake8-bugbear
    "C4",     # flake8-comprehensions
    "UP",     # pyupgrade
    "ASYNC",  # flake8-async
    "RUF",    # Ruff-specific rules
]
ignore = [
    "E501",   # line too long (handled by formatter)
]

[lint.isort]
known-first-party = ["biosciences_mcp"]

[format]
quote-style = "double"
indent-style = "space"
```

**Step 2: Write .env.example**

```bash
# Most life sciences APIs are public (no keys required)
BIOGRID_API_KEY=your_biogrid_api_key_here
NCBI_API_KEY=your_ncbi_api_key_here
DRUGBANK_API_KEY=your_drugbank_api_key_here
```

---

### Task 5: Install dependencies and run unit tests

**Step 1: Install dependencies**

```bash
cd /home/donbr/open-biosciences/biosciences-mcp
uv sync --extra dev
```

Expected: Clean install, no errors

**Step 2: Run unit tests**

```bash
uv run pytest -m unit -v 2>&1 | tail -20
```

Expected: 399+ tests pass. If any fail, debug import issues from the rename.

**Step 3: Count passing tests**

```bash
uv run pytest -m unit -v 2>&1 | grep -c "PASSED"
```

Expected: >= 399

---

### Task 6: Run linting and type checking

**Step 1: Run ruff check**

```bash
cd /home/donbr/open-biosciences/biosciences-mcp
uv run ruff check .
```

Expected: Clean (0 errors). If isort errors, run `uv run ruff check --fix .`

**Step 2: Run ruff format check**

```bash
uv run ruff format --check .
```

Expected: Clean. If formatting issues, run `uv run ruff format .`

**Step 3: Run pyright**

```bash
uv run pyright
```

Expected: Clean or only pre-existing issues from ChEMBL SDK (untyped).

---

### Task 7: Security review and commit

**Step 1: Check for secrets or private paths**

```bash
grep -r "sk-\|AKIA\|ghp_\|gho_\|eyJ" src/ tests/ --include="*.py"
grep -r "/home/" src/ tests/ pyproject.toml ruff.toml .env.example
```

Expected: No real secrets. No private paths in committed files.

**Step 2: Verify .env.example has only placeholders**

```bash
cat .env.example
```

Expected: All values are `your_*_here` placeholders

**Step 3: Stage and commit**

```bash
cd /home/donbr/open-biosciences/biosciences-mcp
git add src/ tests/ pyproject.toml ruff.toml .env.example
git status
```

Review staged files, then:

```bash
git commit -m "feat: migrate 12 MCP servers, clients, models, and tests from lifesciences-research

Rename-on-copy migration of the complete MCP platform:
- 12 FastMCP servers + gateway (HGNC, UniProt, ChEMBL, Open Targets,
  STRING, BioGRID, Ensembl, Entrez, PubChem, IUPHAR, WikiPathways,
  ClinicalTrials.gov)
- 13 async client libraries (base + 12 API clients)
- 19 Pydantic v2 domain models + envelopes
- 399+ unit tests, 294+ integration tests, 4 e2e tests
- Package renamed: lifesciences_mcp -> biosciences_mcp
- Dropped unused deps: pulumi, claude-agent-sdk

Closes AGE-159, AGE-160, AGE-161, AGE-162, AGE-163, AGE-164, AGE-165, AGE-166

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

**Step 4: Push**

```bash
git push
```

---

### Task 8: Verify biosciences-memory MCP connections (AGE-167)

**Step 1: Confirm memory repo config is in place**

```bash
cd /home/donbr/open-biosciences/biosciences-memory
cat .mcp.json
cat .env.example
```

Expected: 5 MCP server connections configured, .env.example has placeholders

**Step 2: Verify Docker MCP servers are running**

```bash
docker ps --format "table {{.Names}}\t{{.Ports}}\t{{.Status}}" | grep -E "(graphiti|neo4j)"
```

Expected: 5 containers healthy

**Step 3: Test Graphiti Docker connection**

```python
mcp__graphiti-docker__get_status()
```

Expected: status "ok"

**Step 4: Test Aura connection (read-only)**

```python
mcp__graphiti-aura__get_status()
```

Expected: status "ok"

---

### Task 9: Update Linear issues

**Step 1: Mark Wave 2 sub-issues as Done**

Update these Linear issues to "Done":
- AGE-159: Migrate 12 MCP server implementations
- AGE-160: Migrate 13 client libraries
- AGE-161: Migrate Pydantic models
- AGE-162: Migrate gateway server
- AGE-163: Rename package
- AGE-164: Migrate unit tests
- AGE-165: Migrate integration tests
- AGE-166: Migrate e2e tests
- AGE-167: Verify memory MCP connections

**Step 2: Close Wave 2 parent**

Update AGE-150 to "Done"

**Step 3: Record completion in Graphiti working memory**

```python
mcp__graphiti-docker__add_memory(
    group_id="open-biosciences-migration-2026",
    content="Migration Wave 2 (Platform) completed on 2026-02-25. Migrated 12 MCP servers, 13 clients, 19 models, gateway, and 697+ tests to biosciences-mcp. Package renamed lifesciences_mcp to biosciences_mcp. Unit tests passing. Linear issues AGE-159 through AGE-167 marked Done. AGE-150 closed.",
    name="Wave 2 Completion"
)
```
