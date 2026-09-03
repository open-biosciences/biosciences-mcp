# Life Sciences MCP Testing Strategy

---

## Executive Summary

**875+ tests** validate that AI agents can reliably navigate 12 life sciences databases.

This isn't just about code coverage. It's about **trust**. When an AI agent tells a researcher that BRCA1 interacts with MDM2 with a STRING score of 0.999, that claim must be verifiable. Our tests ensure every step of that journey—from fuzzy search to strict lookup to cross-reference extraction—works exactly as documented.

**What we test:**
- 12 MCP servers against live APIs (HGNC, UniProt, ChEMBL, STRING, BioGRID, Ensembl, Entrez, PubChem, IUPHAR, WikiPathways, ClinicalTrials.gov, Open Targets)
- The Fuzzy-to-Fact protocol that resolves "BRCA1" → `HGNC:1100` → complete gene record
- Cross-database workflows that traverse gene → protein → drug → clinical trial
- Error recovery paths that guide agents back from mistakes
- The wire contract: what an agent actually receives from every tool, checked against ADR-001

---

## The Testing Challenge

Picture an AI agent trying to answer: *"What drugs target the ARID1A synthetic lethal partner EZH2?"*

The agent must:
1. Search HGNC for "ARID1A" → get `HGNC:11110`
2. Query STRING for interaction partners → find EZH2
3. Search ChEMBL for EZH2 inhibitors → find Tazemetostat
4. Validate the drug's mechanism → confirm EZH2 inhibition

Each step involves:
- **Rate-limited APIs** (10 req/s for most, 2 req/s for BioGRID)
- **Different identifier formats** (HGNC:11110 vs ENSG00000117713 vs UniProtKB:O14497)
- **Network failures** that could happen at any point
- **Schema variations** across 12 different databases

Traditional unit tests can't validate this. We need a multi-layered strategy.

---

## The Journey: Test Categories

### Act I: Unit Tests — The Foundation

**Location:** `tests/unit/` (19 files, ~6,300 lines)

**Purpose:** Validate components in isolation, with no network required.

**What they catch:**
- Invalid CURIE formats (`"BRCA1"` vs `"HGNC:1100"`)
- Pydantic validation errors
- Score bounds violations (0.0–1.0)
- Null handling (omit-if-null pattern from ADR-001 §4)
- Error envelope construction

**Example: The "Junior Dev" Cases**

From our [SpecKit Standard Prompt](../docs/speckit-standard-prompt-v2.md):
> "Include a `pytest-asyncio` test plan covering the 'Junior Dev' ambiguity cases and concurrency."

What would a junior developer get wrong?

```python
# tests/unit/test_models.py

def test_invalid_curie_format():
    """Junior dev might pass gene symbol instead of CURIE."""
    with pytest.raises(ValidationError):
        Gene(id="BRCA1", ...)  # Wrong! Should be "HGNC:1100"

def test_score_out_of_bounds():
    """Junior dev might not validate score ranges."""
    with pytest.raises(ValidationError):
        SearchCandidate(score=1.5, ...)  # Wrong! Must be 0.0-1.0

def test_empty_cross_references():
    """Junior dev might include empty dict instead of omitting."""
    gene = Gene(id="HGNC:1100", cross_references={})
    assert gene.cross_references is None  # Omit-if-null pattern
```

**Running unit tests:**
```bash
# Fast, no network required
uv run pytest tests/unit/ -v

# Single file
uv run pytest tests/unit/test_models.py -v
```

---

### Act II: Integration Tests — The Real World

**Location:** `tests/integration/` (25 files, ~6,800 lines)

**Purpose:** Validate end-to-end workflows against live APIs.

**What they catch:**
- API response format changes
- Rate limiting behavior
- Cross-reference extraction accuracy
- Fuzzy-to-Fact protocol violations

**The Fuzzy-to-Fact Workflow Test**

Every API server has this core test pattern:

```python
# tests/integration/test_hgnc_api.py

@pytest.mark.integration
@pytest.mark.asyncio
async def test_fuzzy_to_fact_workflow(hgnc_client):
    """
    Phase 1: Fuzzy search with natural language
    Phase 2: Strict lookup with resolved CURIE
    """
    # Phase 1: Fuzzy search
    search_result = await hgnc_client.search_genes("BRCA1")
    assert search_result.items[0].id == "HGNC:1100"

    # Phase 2: Strict lookup
    gene = await hgnc_client.get_gene("HGNC:1100")
    assert gene.symbol == "BRCA1"
    assert gene.cross_references.ensembl_gene == "ENSG00000012048"
```

**Error Recovery Tests (User Story 4)**

```python
# tests/integration/test_error_recovery.py

@pytest.mark.integration
async def test_error_recovery_workflow(client):
    """
    1. Trigger error with invalid input
    2. Validate error envelope with recovery hint
    3. Follow hint to correct operation
    4. Confirm success
    """
    # Step 1: Trigger error
    result = await client.get_gene("BRCA1")  # Wrong! Not a CURIE

    # Step 2: Validate recovery hint
    assert result["success"] is False
    assert result["error"]["code"] == "UNRESOLVED_ENTITY"
    assert "search_genes" in result["error"]["recovery_hint"]

    # Step 3: Follow hint
    search = await client.search_genes("BRCA1")
    curie = search["items"][0]["id"]

    # Step 4: Success
    gene = await client.get_gene(curie)
    assert gene["symbol"] == "BRCA1"
```

**Health Checks: Don't Hang on Unavailable Services**

```python
# tests/integration/conftest.py

@pytest.fixture
def check_string_available():
    """Skip tests if STRING API is down."""
    try:
        response = httpx.get("https://string-db.org/api/json/version", timeout=5)
        if response.status_code != 200:
            pytest.skip("STRING API unavailable")
    except httpx.RequestError:
        pytest.skip("STRING API unreachable")
```

**Running integration tests:**
```bash
# All integration tests (requires network)
uv run pytest -m integration -v

# Single API
uv run pytest tests/integration/test_chembl_api.py -v -m integration

# With timeout override for slow APIs
uv run pytest tests/integration/test_entrez_api.py -v --timeout=120
```

---

### Act III: End-to-End Tests — Production Validation

**Location:** `tests/e2e/` (1 file, ~5,300 lines)

**Purpose:** Validate the deployed gateway server against real cloud infrastructure.

**What they catch:**
- Cloud deployment configuration issues
- Gateway tool mounting
- Multi-server workflow orchestration

**Competency Question Workflows**

```python
# tests/e2e/test_competency_questions_cloud.py

@pytest.mark.e2e
async def test_cq1_synthetic_lethality_workflow(cloud_client):
    """
    CQ-1: Identify therapeutic strategies for ARID1A-deficient cancers

    Workflow:
    1. HGNC: Resolve ARID1A → HGNC:11110
    2. STRING: Find interaction partners → EZH2
    3. ChEMBL: Search inhibitors → Tazemetostat
    4. ClinicalTrials: Find studies → NCT03348631
    """
    # ... multi-server orchestration test
```

**Running E2E tests:**
```bash
# Requires cloud deployment endpoint
FASTMCP_CLOUD_ENDPOINT=https://your-deployment.fastmcp.app/mcp \
uv run pytest tests/e2e/ -v -m e2e
```

---

### Act IV: Contract Tests — What the Agent Actually Receives

**Location:** `tests/contract/` (registry, catalogue, one unit module, one wire module)

**Purpose:** Assert ADR-001 on the JSON that leaves the server, not on the Pydantic
object inside it.

**Why this tier exists:** FastMCP serialises tool results with
`pydantic_core.to_json` (text block) and `pydantic_core.to_jsonable_python`
(structured block). Neither calls `model_dump()`. For eight months every
server passed its unit tests while emitting `null` for every absent
cross-reference key, because the tests called `model_dump()` and the wire did
not. `get_gene("HGNC:1100")` returned 15 nulls. No unit or integration test
could see it.

**Two modules, two markers:**

| Module | Markers | Network | What it asserts |
|---|---|---|---|
| `test_serialization_unit.py` | `contract`, `unit` | No | Every entity model, built with only its required fields, produces no `null` through either of FastMCP's real serialisation paths |
| `test_wire_contracts.py` | `contract`, `integration`, per-server | Yes | For every server, through `fastmcp.Client`: raw strings to strict tools return `UNRESOLVED_ENTITY` (§3); list tools return the pagination envelope (§8A); entities and candidates carry no `null` (§4); `cross_references` keys, formats, and cardinality match Appendix A (`registry.py`) |

**The registry is data.** `tests/contract/registry.py` holds ADR-001 v1.4
Appendix A (23 keys, regex, cardinality) as a table. When the ADR is amended,
this table changes in the same commit.

**Deviations are recorded, not hidden.** `test_wire_contracts.py` carries a
deviation table keyed by `server.tool` with the evidence observed on the wire.
A listed case xfails while the deviation reproduces and **fails** once it
stops, so an entry cannot outlive its bug. As of 2026-09-02 there are twelve:
ten cross-reference registry violations awaiting a client fix or the ADR-001
v1.5 decision, and two IUPHAR strict tools whose parameter `pattern=` makes
FastMCP return a pydantic validation string instead of the error envelope.

**The rule the unit module enforces:** every entity model inherits
`OmitNoneModel` (`models/base.py`), whose wrap-mode `model_serializer` drops
`None` on every path. Do not add `model_dump` overrides or
`ConfigDict(exclude_none=True)`; the first is invisible on the wire and the
second is not a Pydantic v2 key. Envelopes stay on `BaseModel` because §8
defines `cursor` and `total_count` as nullable.

**Running contract tests:**
```bash
# Serialisation contract, no network, sub-second
uv run pytest -m "contract and unit" -v

# Wire contract for every server (network; BIOGRID_API_KEY / DRUGBANK_API_KEY skip without keys)
uv run pytest -m "contract and integration" -v

# One server
uv run pytest -m "contract and hgnc" -v
```

The wire module pins one event loop per module (`loop_scope="module"`)
because servers hold module-level singleton clients (ADR-004) that cannot
survive a per-test loop.

---

### Supporting Cast: Manual & Gap Tests

**Manual Tests** (`tests/manual/`)
- Debugging external service issues (Cloudflare blocking, rate limits)
- Not run in CI/CD
- Example: `test_ct_headers.py` diagnoses ClinicalTrials.gov TLS fingerprinting

**Gap Tests** (`tests/gaps/`)
- Validate grounding capabilities (synonym extraction)
- Identify missing features for future development

**Contract Tests** (`tests/contract/`)
- See Act IV below

---

## How Tests Fit Into SpecKit Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│  Step 1: /scaffold-fastmcp [api_name]                          │
│  Creates: tests/unit/test_{api}_models.py (stub)               │
│           tests/unit/test_{api}_client.py (stub)               │
│           tests/integration/test_{api}_api.py (stub)           │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 2: /speckit.specify                                       │
│  Defines: User Stories with test requirements                   │
│           US1: Fuzzy Search → tests search validation           │
│           US2: Strict Lookup → tests CURIE resolution           │
│           US3: Cross-References → tests schema extraction       │
│           US4: Error Recovery → tests recovery workflows        │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 3: /speckit.implement                                     │
│  Writes: Tests alongside implementation                         │
│          Each User Story gets dedicated test coverage           │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 4: Verification                                           │
│  Runs: Unit → Contract → Integration → E2E                     │
│        All tests must pass before merge                        │
└─────────────────────────────────────────────────────────────────┘
```

---

## Key Testing Patterns

### 1. Fuzzy-to-Fact Validation
Every server tests the two-phase resolution:
- Phase 1: `search_*()` returns ranked candidates
- Phase 2: `get_*()` requires resolved CURIE

### 2. Cross-Reference Extraction
Every `get_*` response validates the 23-key Agentic Biolink registry
(ADR-001 v1.4 Appendix A). Integration tests check that expected keys are
populated; the contract tier checks, on the wire, that no key is `null` and
that every present value matches the registry's format and cardinality:
```python
# tests/contract/test_wire_contracts.py
present = {k: v for k, v in data["cross_references"].items() if v is not None}
assert not check_cross_references(present)   # keys, regex, String vs List[String]
assert not find_nulls(data, skip={"pagination", "error"})
```

### 3. Performance Benchmarking (SC-001)
```python
# tests/integration/test_performance.py

async def test_95th_percentile_under_2_seconds():
    """SC-001: 95% of queries complete in <2 seconds."""
    times = [await measure_query_time() for _ in range(100)]
    p95 = sorted(times)[94]
    assert p95 < 2.0
```

### 4. Concurrency Testing
```python
# tests/integration/test_concurrency.py

async def test_20_concurrent_requests():
    """Validate connection pooling under load."""
    tasks = [client.search_genes(f"gene_{i}") for i in range(20)]
    results = await asyncio.gather(*tasks)
    assert all(r["success"] for r in results)
```

### 5. Error Recovery Workflows
```python
# Trigger → Validate hint → Follow hint → Success
```

---

## Running Tests

### Quick Reference

```bash
# All tests
uv run pytest tests/ -v

# Unit only (fast, no network)
uv run pytest tests/unit/ -v

# Contract, serialisation only (no network)
uv run pytest -m "contract and unit" -v

# Contract, wire level (requires network)
uv run pytest -m "contract and integration" -v

# Integration only (requires network; includes the wire contract)
uv run pytest -m integration -v

# E2E only (requires cloud deployment)
FASTMCP_CLOUD_ENDPOINT=... uv run pytest -m e2e -v

# Single server
uv run pytest tests/integration/test_chembl_api.py -v

# With coverage
uv run pytest tests/ -v --cov=src/biosciences_mcp

# Exclude slow tests
uv run pytest tests/ -v -m "not slow"
```

### Pytest Configuration

From `pyproject.toml`:
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
norecursedirs = ["tests/manual", "tests/gaps"]
markers = [
    "unit: marks tests as unit tests (no network required)",
    "integration: marks tests as integration tests (require network)",
    "e2e: marks tests as end-to-end tests (require live server)",
    "contract: wire-level ADR-001 contract tests (run through fastmcp.Client)",
    # plus one marker per server: hgnc, uniprot, chembl, ...
]
timeout = 60
```

---

## Writing New Tests

### Template: New Server Test Suite

```python
# tests/unit/test_{api}_models.py
"""Unit tests for {API} Pydantic models."""

class TestSearchCandidate:
    def test_valid_candidate(self): ...
    def test_invalid_curie_format(self): ...
    def test_score_bounds(self): ...

class TestEntity:
    def test_cross_references_extraction(self): ...
    def test_omit_if_null_pattern(self): ...


# tests/integration/test_{api}_api.py
"""Integration tests for {API} MCP server."""

@pytest.mark.integration
class TestFuzzyToFactWorkflow:
    async def test_search_returns_candidates(self): ...
    async def test_get_requires_curie(self): ...
    async def test_cross_references_populated(self): ...

@pytest.mark.integration
class TestErrorRecovery:
    async def test_invalid_curie_returns_hint(self): ...
    async def test_following_hint_succeeds(self): ...
```

### Fixture Usage

```python
# Use shared fixtures from conftest.py
@pytest.fixture
def sample_gene():
    return Gene(id="HGNC:1100", symbol="BRCA1", ...)

# Use mock HTTP client for unit tests
@pytest.fixture
def mock_httpx_client():
    return MagicMock(spec=httpx.AsyncClient)

# Use health checks for integration tests
@pytest.fixture
def check_api_available():
    # Skip if API unreachable
```

---

## Test Coverage by Server

| Server | Unit | Integration | Total | Status |
|--------|------|-------------|-------|--------|
| HGNC | 14 | 7 | 21 | ✅ |
| UniProt | 21 | 12 | 33 | ✅ |
| ChEMBL | 42 | 20 | 62 | ✅ |
| Open Targets | 0 | 9 | 9 | ✅ |
| STRING | 0 | 11 | 11 | ✅ |
| BioGRID | 0 | 11 | 11 | ✅ |
| Ensembl | 62 | 24 | 86 | ✅ |
| Entrez | 38 | 20 | 58 | ✅ |
| PubChem | 66 | 19 | 85 | ✅ |
| IUPHAR | 11 | 48 | 59 | ✅ |
| WikiPathways | 0 | 17 | 17 | ✅ |
| ClinicalTrials | 13 | 0* | 13 | ✅ |
| **Total** | **267** | **198** | **465+** | |

*ClinicalTrials.gov integration tests blocked by Cloudflare; use manual curl testing.

Contract tier (all servers, not per-server): **106** serialisation cases (unit) and
**69** wire cases (integration), of which 12 are recorded deviations (xfail) and 5
skip without `DRUGBANK_API_KEY`.

Marker totals on 2026-09-02: `unit` 510 (404 + 106 contract), `integration` 363
(294 + 69 contract), `e2e` 4.

---

## Further Reading

- [ADR-001: Agentic-First Architecture](../docs/adr/accepted/adr-001-v1.4.md) — Schema and protocol requirements
- [SpecKit Standard Prompt](../docs/speckit-standard-prompt-v2.md) — Test requirements in specifications
- [Competency Questions Catalog](../docs/competency-questions/competency-questions-catalog.md) — Research workflows to test
- [FastMCP Testing Patterns](https://gofastmcp.com/patterns/testing) — Framework-specific guidance

---

**Last Updated:** 2026-09-02
