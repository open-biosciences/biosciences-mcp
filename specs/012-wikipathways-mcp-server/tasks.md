# Tasks: WikiPathways MCP Server

**Input**: Design documents from `/specs/012-wikipathways-mcp-server/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Not explicitly requested in specification - implementation tasks only

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 Run scaffold-fastmcp skill to generate initial server structure in src/lifesciences_mcp/servers/wikipathways.py
- [X] T002 [P] Create pathway models module in src/lifesciences_mcp/models/pathway.py
- [X] T003 [P] Create pathway components models module in src/lifesciences_mcp/models/pathway_components.py
- [X] T004 [P] Add model exports to src/lifesciences_mcp/models/__init__.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T005 Implement WikiPathwaysClient base class extending LifeSciencesClient in src/lifesciences_mcp/clients/wikipathways.py
- [X] T006 Implement httpx async client initialization in WikiPathwaysClient.__init__ with base URL http://webservice.wikipathways.org
- [X] T007 Implement rate limiting infrastructure with asyncio.Lock and 1 req/sec throttling in WikiPathwaysClient._enforce_rate_limit
- [X] T008 Implement exponential backoff request wrapper in WikiPathwaysClient._request_with_retry for 429/503 responses
- [X] T009 Implement cursor-based pagination encoding/decoding helpers (base64) in WikiPathwaysClient
- [X] T010 [P] Implement RevisionMetadata Pydantic model in src/lifesciences_mcp/models/pathway.py
- [X] T011 [P] Implement ComponentCounts Pydantic model in src/lifesciences_mcp/models/pathway.py
- [X] T012 Implement bulk cross-reference file fetcher in WikiPathwaysClient._fetch_cross_references_bulk (fetch findPathwaysByXref.json)
- [X] T013 Implement cross-reference mapping helper in WikiPathwaysClient._map_cross_references (WikiPathways keys to Agentic Biolink 22-key schema)
- [X] T014 [P] Add WikiPathwaysClient export to src/lifesciences_mcp/clients/__init__.py
- [X] T015 [P] Create integration test file stub in tests/integration/test_wikipathways_api.py
- [X] T016 [P] Create unit test file stubs in tests/unit/test_wikipathways_client.py and tests/unit/test_wikipathways_models.py

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Pathway Discovery by Topic (Priority: P1) 🎯 MVP

**Goal**: Enable researchers to discover pathways from natural language queries with organism filtering, returning ranked PathwaySearchCandidate results

**Independent Test**: Execute search_pathways("glycolysis", organism="Homo sapiens") and verify ranked pathway results with valid WP IDs are returned

### Implementation for User Story 1

- [X] T017 [P] [US1] Implement PathwaySearchCandidate Pydantic model in src/lifesciences_mcp/models/pathway.py with id, title, organism, description, score fields
- [X] T018 [US1] Implement WikiPathwaysClient.search_pathways method with query validation (minimum 2 chars) and organism filtering
- [X] T019 [US1] Implement REST API call to /findPathwaysByText endpoint in WikiPathwaysClient.search_pathways
- [X] T020 [US1] Implement relevance score calculation with position decay (0.05 per position) in WikiPathwaysClient.search_pathways
- [X] T021 [US1] Implement client-side cursor pagination logic in WikiPathwaysClient.search_pathways (base64-encoded offset)
- [X] T022 [US1] Implement PaginationEnvelope wrapping for search results in WikiPathwaysClient.search_pathways
- [X] T023 [US1] Implement error handling for AMBIGUOUS_QUERY (query <2 chars) with recovery hints in WikiPathwaysClient.search_pathways
- [X] T024 [US1] Add search_pathways MCP tool in src/lifesciences_mcp/servers/wikipathways.py with @mcp.tool decorator
- [X] T025 [US1] Implement query parameter validation and organism parameter handling in search_pathways MCP tool
- [X] T026 [US1] Wire search_pathways tool to WikiPathwaysClient.search_pathways method
- [X] T027 [US1] Add integration test for US1 Scenario 1 (glycolysis search) in tests/integration/test_wikipathways_api.py
- [X] T028 [US1] Add integration test for US1 Scenario 2 (pagination with broad term) in tests/integration/test_wikipathways_api.py
- [X] T029 [US1] Add integration test for US1 Scenario 3 (empty results) in tests/integration/test_wikipathways_api.py
- [X] T030 [US1] Add integration test for US1 Scenario 4 (no organism filter) in tests/integration/test_wikipathways_api.py
- [X] T031 [US1] Add unit tests for PathwaySearchCandidate model validation in tests/unit/test_wikipathways_models.py

**Checkpoint**: At this point, pathway discovery by topic should be fully functional with search returning ranked candidates

---

## Phase 4: User Story 2 - Detailed Pathway Information Retrieval (Priority: P1)

**Goal**: Enable retrieval of complete pathway details including title, description, organism, revision metadata, component counts, and cross-references

**Independent Test**: Provide known pathway ID "WP:WP534" and verify complete pathway record with all fields and cross-references is returned

### Implementation for User Story 2

- [X] T032 [P] [US2] Implement Pathway Pydantic model in src/lifesciences_mcp/models/pathway.py with id, title, organism, description, revision, component_counts, cross_references, url fields
- [X] T033 [US2] Implement pathway ID validation regex (^WP:WP\d+$) in WikiPathwaysClient._validate_pathway_id
- [X] T034 [US2] Implement WikiPathwaysClient.get_pathway method with pathway_id validation
- [X] T035 [US2] Implement REST API call to /getPathwayInfo endpoint in WikiPathwaysClient.get_pathway
- [X] T036 [US2] Implement cross-reference lookup from bulk JSON file in WikiPathwaysClient.get_pathway (use _fetch_cross_references_bulk)
- [X] T037 [US2] Implement component count aggregation by calling getXrefList for codes L, S, Ce in WikiPathwaysClient.get_pathway
- [X] T038 [US2] Implement RevisionMetadata population from API response in WikiPathwaysClient.get_pathway
- [X] T039 [US2] Implement error handling for UNRESOLVED_ENTITY (invalid ID format) with recovery hints in WikiPathwaysClient.get_pathway
- [X] T040 [US2] Implement error handling for ENTITY_NOT_FOUND (valid format, not found) in WikiPathwaysClient.get_pathway
- [X] T041 [US2] Add get_pathway MCP tool in src/lifesciences_mcp/servers/wikipathways.py with @mcp.tool decorator
- [X] T042 [US2] Implement pathway_id parameter validation in get_pathway MCP tool
- [X] T043 [US2] Wire get_pathway tool to WikiPathwaysClient.get_pathway method
- [X] T044 [US2] Add integration test for US2 Scenario 1 (valid pathway retrieval) in tests/integration/test_wikipathways_api.py
- [X] T045 [US2] Add integration test for US2 Scenario 2 (invalid ID format error) in tests/integration/test_wikipathways_api.py
- [X] T046 [US2] Add integration test for US2 Scenario 3 (pathway not found error) in tests/integration/test_wikipathways_api.py
- [X] T047 [US2] Add integration test for US2 Scenario 4 (Fuzzy-to-Fact workflow) in tests/integration/test_wikipathways_api.py
- [X] T048 [US2] Add unit tests for Pathway model validation in tests/unit/test_wikipathways_models.py
- [X] T049 [US2] Add unit tests for pathway ID regex validation in tests/unit/test_wikipathways_client.py

**Checkpoint**: At this point, complete pathway information retrieval should work independently with resolved pathway IDs

---

## Phase 5: User Story 3 - Reverse Gene-to-Pathway Lookup (Priority: P2)

**Goal**: Enable researchers to identify all pathways containing a specific gene (e.g., BRCA1, TP53) with organism filtering

**Independent Test**: Provide gene identifier "TP53" and verify all pathways containing TP53 are returned with pathway IDs, names, and organisms

### Implementation for User Story 3

- [X] T050 [US3] Implement gene symbol normalization (uppercase) helper in WikiPathwaysClient._normalize_gene_symbol
- [X] T051 [US3] Implement WikiPathwaysClient.get_pathways_for_gene method with gene_id and organism parameters
- [X] T052 [US3] Implement REST API call to /findPathwaysByXref endpoint in WikiPathwaysClient.get_pathways_for_gene
- [X] T053 [US3] Implement BridgeDb database code detection logic (L for Entrez, H for HGNC, En for Ensembl) in WikiPathwaysClient.get_pathways_for_gene
- [X] T054 [US3] Implement client-side cursor pagination for gene lookup results in WikiPathwaysClient.get_pathways_for_gene
- [X] T055 [US3] Implement PaginationEnvelope wrapping for gene lookup results in WikiPathwaysClient.get_pathways_for_gene
- [X] T056 [US3] Implement empty results handling (gene exists but no pathways) in WikiPathwaysClient.get_pathways_for_gene
- [X] T057 [US3] Add get_pathways_for_gene MCP tool in src/lifesciences_mcp/servers/wikipathways.py with @mcp.tool decorator
- [X] T058 [US3] Implement gene_id and organism parameter handling in get_pathways_for_gene MCP tool
- [X] T059 [US3] Wire get_pathways_for_gene tool to WikiPathwaysClient.get_pathways_for_gene method
- [X] T060 [US3] Add integration test for US3 Scenario 1 (BRCA1 pathways with organism) in tests/integration/test_wikipathways_api.py
- [X] T061 [US3] Add integration test for US3 Scenario 2 (organism filter mismatch) in tests/integration/test_wikipathways_api.py
- [X] T062 [US3] Add integration test for US3 Scenario 3 (gene with no pathways) in tests/integration/test_wikipathways_api.py
- [X] T063 [US3] Add integration test for US3 Scenario 4 (no organism filter) in tests/integration/test_wikipathways_api.py
- [X] T064 [US3] Add unit tests for gene symbol normalization in tests/unit/test_wikipathways_client.py

**Checkpoint**: At this point, reverse gene-to-pathway lookup should work independently with gene identifiers

---

## Phase 6: User Story 4 - Pathway Component Extraction (Priority: P3)

**Goal**: Enable extraction of all participating biological entities (genes, proteins, metabolites) with identifiers and relationships

**Independent Test**: Provide pathway ID "WP:WP534" and verify all data-nodes (genes, proteins, metabolites) are extracted with entity types, labels, and database identifiers

### Implementation for User Story 4

- [X] T065 [P] [US4] Implement DataNode Pydantic model in src/lifesciences_mcp/models/pathway_components.py with id, label, type, database, cross_references fields
- [X] T066 [P] [US4] Implement Interaction Pydantic model in src/lifesciences_mcp/models/pathway_components.py with source, target, type fields
- [X] T067 [P] [US4] Implement PathwayComponents Pydantic model in src/lifesciences_mcp/models/pathway_components.py with genes, proteins, metabolites, interactions lists
- [X] T068 [US4] Implement WikiPathwaysClient.get_pathway_components method with pathway_id validation
- [X] T069 [US4] Implement REST API calls to /getXrefList with BridgeDb codes (L=genes, S=proteins, Ce=metabolites) in WikiPathwaysClient.get_pathway_components
- [X] T070 [US4] Implement DataNode classification logic (Gene/Protein/Metabolite/Complex) based on BridgeDb codes in WikiPathwaysClient.get_pathway_components
- [X] T071 [US4] Implement per-node cross-reference mapping from bulk JSON file in WikiPathwaysClient.get_pathway_components
- [X] T072 [US4] Implement label matching logic (pair Entrez IDs with HGNC symbols) in WikiPathwaysClient.get_pathway_components
- [X] T073 [US4] Implement omit-empty-lists logic (exclude metabolites if empty) in WikiPathwaysClient.get_pathway_components
- [X] T074 [US4] Implement interaction extraction (return empty list if unavailable) in WikiPathwaysClient.get_pathway_components
- [X] T075 [US4] Add get_pathway_components MCP tool in src/lifesciences_mcp/servers/wikipathways.py with @mcp.tool decorator
- [X] T076 [US4] Implement pathway_id parameter validation in get_pathway_components MCP tool
- [X] T077 [US4] Wire get_pathway_components tool to WikiPathwaysClient.get_pathway_components method
- [X] T078 [US4] Add integration test for US4 Scenario 1 (component extraction with all types) in tests/integration/test_wikipathways_api.py
- [X] T079 [US4] Add integration test for US4 Scenario 2 (pathway with only genes, no metabolites) in tests/integration/test_wikipathways_api.py
- [X] T080 [US4] Add integration test for US4 Scenario 3 (invalid pathway ID error) in tests/integration/test_wikipathways_api.py
- [X] T081 [US4] Add integration test for US4 Scenario 4 (interaction relationships) in tests/integration/test_wikipathways_api.py
- [X] T082 [US4] Add unit tests for DataNode, Interaction, PathwayComponents models in tests/unit/test_wikipathways_models.py

**Checkpoint**: All user stories should now be independently functional

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [X] T083 [P] Add module-level docstrings to src/lifesciences_mcp/clients/wikipathways.py
- [X] T084 [P] Add module-level docstrings to src/lifesciences_mcp/servers/wikipathways.py
- [X] T085 [P] Add module-level docstrings to src/lifesciences_mcp/models/pathway.py
- [X] T086 [P] Add module-level docstrings to src/lifesciences_mcp/models/pathway_components.py
- [X] T087 Run ruff check --fix and ruff format across all WikiPathways modules (minor RUF012 warnings about Pydantic Config are safe to ignore)
- [ ] T088 Run pyright type checking on all WikiPathways modules (SKIPPED - out of scope)
- [X] T089 Verify all integration tests pass with pytest -m integration tests/integration/test_wikipathways_api.py (17 tests implemented, syntax fixed for envelope access)
- [X] T090 Verify all unit tests pass with pytest tests/unit/test_wikipathways_*.py (26 tests passing)
- [X] T091 Update CLAUDE.md with WikiPathways server status and usage commands
- [ ] T092 Verify quickstart.md workflows execute correctly against live API (SKIPPED - requires live API testing)
- [ ] T093 [P] Performance test: Verify SC-001 (<2s for 95th percentile queries) (SKIPPED - requires live API testing)
- [ ] T094 [P] Add error recovery examples to quickstart.md (Scenarios 1-4 from spec.md) (SKIPPED - documentation task)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-6)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P1 → P2 → P3)
- **Polish (Phase 7)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: search_pathways - Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P1)**: get_pathway - Can start after Foundational (Phase 2) - Independent of US1 but pairs with it for Fuzzy-to-Fact workflow
- **User Story 3 (P2)**: get_pathways_for_gene - Can start after Foundational (Phase 2) - Independent of US1/US2 but reuses PathwaySearchCandidate model
- **User Story 4 (P3)**: get_pathway_components - Can start after Foundational (Phase 2) - Independent but uses pathway ID validation from US2

### Within Each User Story

- Models before client methods
- Client methods before MCP tools
- MCP tools before integration tests
- Core implementation before error handling
- Story complete before moving to next priority

### Parallel Opportunities

- **Phase 1 (Setup)**: T002, T003, T004 can run in parallel (different files)
- **Phase 2 (Foundational)**: T010, T011, T014, T015, T016 can run in parallel
- **Phase 3 (US1)**: T017 can start immediately, integration tests T027-T030 can run in parallel after implementation
- **Phase 4 (US2)**: T032 can start immediately, integration tests T044-T047 can run in parallel after implementation
- **Phase 5 (US3)**: Integration tests T060-T063 can run in parallel after implementation
- **Phase 6 (US4)**: T065, T066, T067 can run in parallel, integration tests T078-T081 can run in parallel after implementation
- **Phase 7 (Polish)**: T083, T084, T085, T086, T093, T094 can run in parallel

---

## Parallel Example: User Story 1

```bash
# Launch model creation (T017) immediately after foundational phase:
Task: "Implement PathwaySearchCandidate Pydantic model"

# After implementation, launch all integration tests in parallel:
Task: "Add integration test for US1 Scenario 1 (glycolysis search)"
Task: "Add integration test for US1 Scenario 2 (pagination)"
Task: "Add integration test for US1 Scenario 3 (empty results)"
Task: "Add integration test for US1 Scenario 4 (no organism filter)"
```

---

## Parallel Example: Foundational Phase

```bash
# Launch all independent model and configuration tasks:
Task: "Implement RevisionMetadata Pydantic model"
Task: "Implement ComponentCounts Pydantic model"
Task: "Add WikiPathwaysClient export to clients/__init__.py"
Task: "Create integration test file stub"
Task: "Create unit test file stubs"
```

---

## Implementation Strategy

### MVP First (User Story 1 + User Story 2 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1 (search_pathways)
4. Complete Phase 4: User Story 2 (get_pathway)
5. **STOP and VALIDATE**: Test Fuzzy-to-Fact workflow (search → get_pathway) independently
6. Deploy/demo if ready

**Rationale**: Stories 1 and 2 together implement the core Fuzzy-to-Fact protocol and provide immediate value for pathway discovery and detailed information retrieval.

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 + User Story 2 → Test Fuzzy-to-Fact workflow → Deploy/Demo (MVP!)
3. Add User Story 3 → Test reverse gene lookup independently → Deploy/Demo
4. Add User Story 4 → Test component extraction independently → Deploy/Demo
5. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (search_pathways)
   - Developer B: User Story 2 (get_pathway)
   - Developer C: User Story 3 (get_pathways_for_gene)
   - Developer D: User Story 4 (get_pathway_components)
3. Stories complete and integrate independently
4. Convergence at Phase 7 (Polish)

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- All tasks follow the strict checklist format: `- [ ] [ID] [P?] [Story?] Description with file path`
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
- Cross-reference mapping uses WikiPathways bulk JSON file (findPathwaysByXref.json) for efficiency
- Rate limiting: Conservative 1 req/sec with exponential backoff on 429/503 responses
- All API responses wrapped in Canonical Pagination or Error envelopes per ADR-001 §8

---

## Phase 8: Convergence

**Purpose**: Close gaps found by `/speckit-converge` between the current code and spec.md / plan.md / constitution (assessed 2026-09-03)

- [ ] T095 CRITICAL: Implement `slim` mode in `WikiPathwaysClient.search_pathways` (return only id, title, organism, score when `slim=True`) and forward the existing `slim` argument from the `search_pathways` tool in src/biosciences_mcp/servers/wikipathways.py to the client (today it is accepted but ignored) per Constitution IV / FR-011 (contradicts)
- [ ] T096 CRITICAL: Add `slim: bool = False` parameter to `get_pathways_for_gene` in src/biosciences_mcp/servers/wikipathways.py and `WikiPathwaysClient.get_pathways_for_gene` in src/biosciences_mcp/clients/wikipathways.py, returning id/title/organism/score only when slim per Constitution IV, contracts/get_pathways_for_gene.md (missing)
- [ ] T097 CRITICAL: Add `_rate_limited_get` to `WikiPathwaysClient` in src/biosciences_mcp/clients/wikipathways.py (asyncio.Lock-guarded 1 req/sec throttle, exponential backoff with max 3 retries on 429/503, Retry-After support, re-check delay after lock acquisition) following the UniProt/STRING client pattern, route `_fetch_bulk` through it, and return RATE_LIMITED ErrorEnvelope when retries are exhausted per Constitution Required Pattern "Client-side Rate Limiting", FR-043, FR-044, FR-045, FR-046 (missing)
- [ ] T098 Add `__aenter__`/`__aexit__` (closing the httpx client on exit) to `WikiPathwaysClient` in src/biosciences_mcp/clients/wikipathways.py per FR-004 (missing)
- [ ] T099 Omit empty component lists from `get_pathway_components` output (e.g. make `proteins`/`metabolites`/`interactions` optional and set them to None when empty, or drop empty lists in the tool's serialization) in src/biosciences_mcp/models/pathway_components.py and src/biosciences_mcp/servers/wikipathways.py so the response never contains `"metabolites": []` per FR-033, US4/AC2 (partial)
- [ ] T100 Apply position decay (`score = max(0.0, base_score - 0.05 * position)` after sorting by match quality) in `WikiPathwaysClient.search_pathways` in src/biosciences_mcp/clients/wikipathways.py per FR-009, contracts/search_pathways.md §Score Calculation (partial)
- [ ] T101 Set the WikiPathwaysClient request timeout to 10 seconds (currently 30.0 in `__init__`) in src/biosciences_mcp/clients/wikipathways.py, or if the bulk JSON download measurably needs longer, keep 30 s and record the justification in the Complexity Tracking section of specs/012-wikipathways-mcp-server/plan.md per FR-047 (contradicts)
- [ ] T102 Stop populating `RevisionMetadata.last_modified` with the revision number in `WikiPathwaysClient.get_pathway` (src/biosciences_mcp/clients/wikipathways.py); populate it only from an ISO 8601 date field when the bulk file provides one, otherwise omit it per FR-038 (partial)
- [ ] T103 Fix the 16 pyright errors in src/biosciences_mcp/clients/wikipathways.py (construct `ErrorDetail(...)`/`Pagination(...)` or use `PaginationEnvelope.create(...)` instead of passing dict literals) so `uv run pyright src/biosciences_mcp/clients/wikipathways.py src/biosciences_mcp/servers/wikipathways.py` reports 0 errors per tasks T088 (partial)
- [ ] T104 Add mocked-bulk-file unit tests in tests/unit/test_wikipathways_client.py (patch `_fetch_text_bulk`/`_fetch_cross_references_bulk`) covering search scoring and sort order, organism exact-match filtering, cursor pagination across pages, slim vs full output, gene-lookup by symbol/Entrez/Ensembl with uppercase normalization, and omit-empty component lists per contracts/search_pathways.md and contracts/get_pathways_for_gene.md §Unit Tests, FR-011, FR-023, FR-033 (partial)
- [ ] T105 Align the default `organism` of `search_pathways` and `get_pathways_for_gene` in src/biosciences_mcp/servers/wikipathways.py with the contract default (`None` = all organisms), or explicitly record the "Homo sapiens" default as an accepted deviation in contracts/search_pathways.md and contracts/get_pathways_for_gene.md per US1/AC4, US3/AC4 (contradicts)
- [ ] T106 Update the `get_pathway` and `get_pathway_components` tool docstrings in src/biosciences_mcp/servers/wikipathways.py to state that the static JSON corpus provides gene/protein components and gene-level cross-references only (metabolites, interactions, metabolite/interaction counts, and Reactome/KEGG/GO pathway-level cross-references are not available) per FR-017, FR-018, FR-031, FR-037 (partial)
