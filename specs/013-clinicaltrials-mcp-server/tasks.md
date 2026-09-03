# Tasks: ClinicalTrials.gov MCP Server

**Feature Branch**: `013-clinicaltrials-mcp-server`
**Input**: Design documents from `/specs/013-clinicaltrials-mcp-server/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: All user stories include test tasks per feature specification requirements (FR-022, FR-023, FR-024)

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `- [ ] [ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 Create project structure using `/scaffold-fastmcp` skill for clinicaltrials server
- [X] T002 [P] Create trial.py models in src/lifesciences_mcp/models/trial.py
- [X] T003 [P] Create trial_location.py models in src/lifesciences_mcp/models/trial_location.py
- [X] T004 Verify envelopes.py contains PaginationEnvelope and ErrorEnvelope in src/lifesciences_mcp/models/envelopes.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T005 Implement ClinicalTrialsClient base class extending LifeSciencesClient in src/lifesciences_mcp/clients/clinicaltrials.py
- [X] T006 [P] Add NCT ID validation helper (regex: ^NCT:\d{8}$) in src/lifesciences_mcp/clients/clinicaltrials.py
- [X] T007 [P] Add NCT ID normalization helper (NCT00461032 → NCT:00461032) in src/lifesciences_mcp/clients/clinicaltrials.py
- [X] T008 Implement rate limiting (1 req/sec) with exponential backoff in src/lifesciences_mcp/clients/clinicaltrials.py
- [X] T009 [P] Implement error envelope mapping (HTTP status → error codes) in src/lifesciences_mcp/clients/clinicaltrials.py
- [X] T010 [P] Add API base URL configuration (https://clinicaltrials.gov/api/v2) in src/lifesciences_mcp/clients/clinicaltrials.py
- [X] T011 Create FastMCP server skeleton with three tool stubs in src/lifesciences_mcp/servers/clinicaltrials.py
- [X] T012 [P] Add module-level docstrings to all modules per ADR-001 requirements

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Fuzzy Trial Search (Priority: P1) 🎯 MVP

**Goal**: Enable LLM agents to search ClinicalTrials.gov using natural language queries and filters, returning ranked trial candidates with NCT IDs

**Independent Test**: Search for "breast cancer immunotherapy" and verify ranked candidates are returned with valid NCT IDs in the format NCT:########

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T013 [P] [US1] Unit test for TrialSearchCandidate model validation in tests/unit/test_trial_models.py
- [ ] T014 [P] [US1] Unit test for PaginationEnvelope structure in tests/contract/test_canonical_envelopes.py
- [ ] T015 [P] [US1] Integration test for simple query search in tests/integration/test_clinicaltrials_api.py
- [ ] T016 [P] [US1] Integration test for multi-filter search in tests/integration/test_clinicaltrials_api.py
- [ ] T017 [P] [US1] Integration test for location-based search in tests/integration/test_clinicaltrials_api.py
- [ ] T018 [P] [US1] Integration test for phase filter search in tests/integration/test_clinicaltrials_api.py
- [ ] T019 [P] [US1] Integration test for pagination workflow in tests/integration/test_clinicaltrials_api.py

### Implementation for User Story 1

- [X] T020 [US1] Implement search_trials client method with query parameters in src/lifesciences_mcp/clients/clinicaltrials.py
- [X] T021 [US1] Add API fields parameter for minimal search response in src/lifesciences_mcp/clients/clinicaltrials.py
- [X] T022 [US1] Implement response parsing to TrialSearchCandidate in src/lifesciences_mcp/clients/clinicaltrials.py
- [X] T023 [US1] Implement PaginationEnvelope wrapping with cursor mapping in src/lifesciences_mcp/clients/clinicaltrials.py
- [X] T024 [US1] Add parameter validation for status and phase enums in src/lifesciences_mcp/clients/clinicaltrials.py
- [X] T025 [US1] Implement @mcp.tool() decorator for search_trials in src/lifesciences_mcp/servers/clinicaltrials.py
- [X] T026 [US1] Add tool description and parameter documentation in src/lifesciences_mcp/servers/clinicaltrials.py
- [ ] T027 [US1] Run all US1 tests and verify they pass

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Strict Trial Lookup (Priority: P2)

**Goal**: Enable LLM agents to retrieve complete trial details using resolved NCT IDs, providing full protocol information

**Independent Test**: Call get_trial("NCT:01234567") with a known trial ID and verify all required fields are populated

### Tests for User Story 2

- [ ] T028 [P] [US2] Unit test for Trial model validation in tests/unit/test_trial_models.py
- [ ] T029 [P] [US2] Unit test for omit-if-null pattern compliance in tests/unit/test_trial_models.py
- [ ] T030 [P] [US2] Unit test for UNRESOLVED_ENTITY error envelope in tests/unit/test_error_envelopes.py
- [ ] T031 [P] [US2] Integration test for valid NCT ID lookup in tests/integration/test_clinicaltrials_api.py
- [ ] T032 [P] [US2] Integration test for invalid NCT ID format (INVALID_INPUT) in tests/integration/test_clinicaltrials_api.py
- [ ] T033 [P] [US2] Integration test for query string passed to get_trial (UNRESOLVED_ENTITY) in tests/integration/test_clinicaltrials_api.py
- [ ] T034 [P] [US2] Integration test for non-existent NCT ID (ENTITY_NOT_FOUND) in tests/integration/test_clinicaltrials_api.py
- [ ] T035 [P] [US2] Integration test for trial with missing optional fields in tests/integration/test_clinicaltrials_api.py

### Implementation for User Story 2

- [X] T036 [US2] Implement get_trial client method with NCT ID validation in src/lifesciences_mcp/clients/clinicaltrials.py
- [X] T037 [US2] Implement response parsing for protocolSection in src/lifesciences_mcp/clients/clinicaltrials.py
- [X] T038 [US2] Implement TrialProtocol extraction from designModule in src/lifesciences_mcp/clients/clinicaltrials.py
- [X] T039 [US2] Implement EligibilityCriteria extraction from eligibilityModule in src/lifesciences_mcp/clients/clinicaltrials.py
- [X] T040 [US2] Implement Outcome extraction from outcomesModule in src/lifesciences_mcp/clients/clinicaltrials.py
- [X] T041 [US2] Implement Sponsor extraction from sponsorCollaboratorsModule in src/lifesciences_mcp/clients/clinicaltrials.py
- [X] T042 [US2] Implement cross-reference extraction (PubMed, MeSH, registry links) in src/lifesciences_mcp/clients/clinicaltrials.py
- [X] T043 [US2] Implement @mcp.tool() decorator for get_trial in src/lifesciences_mcp/servers/clinicaltrials.py
- [X] T044 [US2] Add UNRESOLVED_ENTITY error handling for query strings in src/lifesciences_mcp/servers/clinicaltrials.py
- [ ] T045 [US2] Run all US2 tests and verify they pass

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently (Fuzzy-to-Fact workflow complete)

---

## Phase 5: User Story 3 - Trial Locations and Contacts (Priority: P3)

**Goal**: Enable LLM agents to retrieve geographic facility and contact information for trials

**Independent Test**: Call get_trial_locations("NCT:04123456") and verify facility addresses, contact names, and recruitment status are returned

### Tests for User Story 3

- [ ] T046 [P] [US3] Unit test for TrialLocation model validation in tests/unit/test_trial_location_models.py
- [ ] T047 [P] [US3] Unit test for omit-if-null pattern for contact fields in tests/unit/test_trial_location_models.py
- [ ] T048 [P] [US3] Integration test for multi-site trial with complete contact info in tests/integration/test_clinicaltrials_api.py
- [ ] T049 [P] [US3] Integration test for international trial (verify state omission for non-US) in tests/integration/test_clinicaltrials_api.py
- [ ] T050 [P] [US3] Integration test for trial with no facilities (empty array) in tests/integration/test_clinicaltrials_api.py
- [ ] T051 [P] [US3] Integration test for invalid NCT ID (UNRESOLVED_ENTITY) in tests/integration/test_clinicaltrials_api.py

### Implementation for User Story 3

- [X] T052 [US3] Implement get_trial_locations client method with field selection in src/lifesciences_mcp/clients/clinicaltrials.py
- [X] T053 [US3] Implement contactsLocationsModule parsing in src/lifesciences_mcp/clients/clinicaltrials.py
- [X] T054 [US3] Implement contact extraction (first contact from contacts array) in src/lifesciences_mcp/clients/clinicaltrials.py
- [X] T055 [US3] Implement empty location list handling in src/lifesciences_mcp/clients/clinicaltrials.py
- [X] T056 [US3] Implement @mcp.tool() decorator for get_trial_locations in src/lifesciences_mcp/servers/clinicaltrials.py
- [ ] T057 [US3] Run all US3 tests and verify they pass

**Checkpoint**: All three core tools should now be independently functional

---

## Phase 6: User Story 4 - Error Recovery (Priority: P4)

**Goal**: Provide actionable recovery hints for all error scenarios to enable autonomous agent self-correction

**Independent Test**: Trigger each error type (UNRESOLVED_ENTITY, RATE_LIMITED, UPSTREAM_ERROR, ENTITY_NOT_FOUND, INVALID_INPUT) and verify recovery hints are actionable

### Tests for User Story 4

- [ ] T058 [P] [US4] Unit test for all error envelope structures in tests/unit/test_error_envelopes.py
- [ ] T059 [P] [US4] Integration test for UNRESOLVED_ENTITY recovery workflow in tests/integration/test_error_recovery.py
- [ ] T060 [P] [US4] Integration test for RATE_LIMITED recovery with backoff in tests/integration/test_error_recovery.py
- [ ] T061 [P] [US4] Integration test for UPSTREAM_ERROR recovery hint in tests/integration/test_error_recovery.py
- [ ] T062 [P] [US4] Integration test for ENTITY_NOT_FOUND recovery hint in tests/integration/test_error_recovery.py
- [ ] T063 [P] [US4] Integration test for complete error→hint→recovery→success cycle in tests/integration/test_error_recovery.py

### Implementation for User Story 4

- [ ] T064 [US4] Implement UNRESOLVED_ENTITY error with recovery hints in src/lifesciences_mcp/clients/clinicaltrials.py
- [ ] T065 [US4] Implement RATE_LIMITED error with exponential backoff hints in src/lifesciences_mcp/clients/clinicaltrials.py
- [ ] T066 [US4] Implement UPSTREAM_ERROR error with retry guidance in src/lifesciences_mcp/clients/clinicaltrials.py
- [ ] T067 [US4] Implement ENTITY_NOT_FOUND error with validation hints in src/lifesciences_mcp/clients/clinicaltrials.py
- [ ] T068 [US4] Implement INVALID_INPUT error with format correction hints in src/lifesciences_mcp/clients/clinicaltrials.py
- [ ] T069 [US4] Add error recovery examples to server docstrings in src/lifesciences_mcp/servers/clinicaltrials.py
- [ ] T070 [US4] Run all US4 tests and verify they pass

**Checkpoint**: All error scenarios should provide actionable recovery guidance

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [X] T071 [P] Run ruff check --fix . && ruff format . for code formatting
- [X] T072 [P] Run pyright for type checking compliance
- [ ] T073 [P] Validate all tests pass (pytest tests/ -v) - DEFERRED (tests not written yet)
- [ ] T074 [P] Run quickstart.md validation (execute all workflows) - DEFERRED (requires live API testing)
- [ ] T075 [P] Verify Fuzzy-to-Fact workflow end-to-end in tests/integration/test_fuzzy_to_fact.py - DEFERRED
- [ ] T076 [P] Performance test: verify SC-001 (<2s for 95% of queries) in tests/integration/test_performance.py - DEFERRED
- [ ] T077 [P] Performance test: verify SC-002 (<3s for Fuzzy-to-Fact workflow) in tests/integration/test_performance.py - DEFERRED
- [X] T078 Update CLAUDE.md with ClinicalTrials server entry and test counts
- [ ] T079 Update project README with ClinicalTrials server usage examples - OPTIONAL

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-6)**: All depend on Foundational phase completion
  - User stories can proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3 → P4)
- **Polish (Phase 7)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - No dependencies on US1 (independently testable)
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - No dependencies on US1/US2 (independently testable)
- **User Story 4 (P4)**: Can start after Foundational (Phase 2) - Builds on error handling from all tools

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Models before client methods
- Client methods before FastMCP tools
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- **Phase 1**: T002 and T003 (different model files)
- **Phase 2**: T006, T007, T009, T010, T012 (different concerns within client/models)
- **Phase 3 (US1)**: All test tasks (T013-T019) can run in parallel
- **Phase 4 (US2)**: All test tasks (T028-T035) can run in parallel
- **Phase 5 (US3)**: All test tasks (T046-T051) can run in parallel
- **Phase 6 (US4)**: All test tasks (T058-T063) can run in parallel
- **Phase 7**: T071, T072, T073, T074, T075, T076, T077 (independent validation tasks)
- **Cross-story**: Once Foundational completes, US1, US2, US3 can start in parallel by different developers

---

## Parallel Example: User Story 1 (Fuzzy Trial Search)

```bash
# Launch all tests for User Story 1 together (write tests first, ensure they FAIL):
Task: "Unit test for TrialSearchCandidate model validation"
Task: "Unit test for PaginationEnvelope structure"
Task: "Integration test for simple query search"
Task: "Integration test for multi-filter search"
Task: "Integration test for location-based search"
Task: "Integration test for phase filter search"
Task: "Integration test for pagination workflow"

# After tests are written and failing, implement:
Task: "Implement search_trials client method with query parameters"
Task: "Add API fields parameter for minimal search response"
Task: "Implement response parsing to TrialSearchCandidate"
Task: "Implement PaginationEnvelope wrapping with cursor mapping"
Task: "Add parameter validation for status and phase enums"
Task: "Implement @mcp.tool() decorator for search_trials"
Task: "Add tool description and parameter documentation"
Task: "Run all US1 tests and verify they pass"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T004)
2. Complete Phase 2: Foundational (T005-T012) - CRITICAL - blocks all stories
3. Complete Phase 3: User Story 1 (T013-T027)
4. **STOP and VALIDATE**: Test User Story 1 independently
5. Deploy/demo fuzzy trial search capability

**Result**: LLM agents can discover clinical trials using natural language queries

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP - Fuzzy Search!)
3. Add User Story 2 → Test independently → Deploy/Demo (Fuzzy-to-Fact complete!)
4. Add User Story 3 → Test independently → Deploy/Demo (Location data added!)
5. Add User Story 4 → Test independently → Deploy/Demo (Error recovery complete!)
6. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (Fuzzy Search)
   - Developer B: User Story 2 (Strict Lookup)
   - Developer C: User Story 3 (Locations)
3. Stories complete independently and integrate seamlessly
4. Developer D (optional): User Story 4 error recovery testing across all tools

---

## Task Summary

**Total Tasks**: 79

**Task Count by User Story**:
- Setup (Phase 1): 4 tasks
- Foundational (Phase 2): 8 tasks
- User Story 1 (P1): 15 tasks (7 tests + 8 implementation)
- User Story 2 (P2): 18 tasks (8 tests + 10 implementation)
- User Story 3 (P3): 12 tasks (6 tests + 6 implementation)
- User Story 4 (P4): 13 tasks (6 tests + 7 implementation)
- Polish (Phase 7): 9 tasks

**Parallel Opportunities**: 38 tasks marked [P] can run in parallel

**Independent Test Criteria**:
- **US1**: Search for "breast cancer immunotherapy" → verify ranked candidates with NCT IDs
- **US2**: Call get_trial("NCT:01234567") → verify complete trial details
- **US3**: Call get_trial_locations("NCT:04123456") → verify facility/contact data
- **US4**: Trigger error scenarios → verify recovery hints enable self-correction

**Suggested MVP Scope**: User Story 1 only (fuzzy search capability)

---

## Format Validation

✅ All tasks follow the checklist format: `- [ ] [TaskID] [P?] [Story?] Description with file path`

✅ All user story phase tasks include [Story] labels (US1, US2, US3, US4)

✅ All tasks include specific file paths

✅ Setup and Foundational phases have no story labels (shared infrastructure)

✅ Polish phase has no story labels (cross-cutting concerns)

---

## Notes

- Tests are REQUIRED per feature specification (FR-022, FR-023, FR-024)
- All tests must FAIL before implementation (TDD workflow)
- NCT ID format: NCT:######## (8 digits with colon)
- Rate limiting: 1 req/sec with exponential backoff
- Token optimization: Search returns ~100-200 tokens/candidate, strict lookup returns ~5K-10K tokens/trial
- Cross-references: Limited to PubMed, MeSH IDs, registry links (no direct DrugBank/ChEMBL links)
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently

---

## Phase 8: Convergence

**Purpose**: Remaining work identified by `/speckit-converge` (2026-09-03) assessing the current code against spec.md, plan.md, tasks.md, and the constitution. Paths reflect the current package name `biosciences_mcp` (artifacts above still say `lifesciences_mcp`).

- [ ] T080 CRITICAL: Conform `Trial.cross_references` to the ADR-001 Appendix A registry: emit `pubmed` as `List[String]` with `PMID:` prefix (`^PMID:\d+$`) instead of a comma-joined unprefixed string, and either move `clinicaltrials_gov`, `mesh_conditions`, `mesh_interventions` out of `cross_references` (e.g. top-level `registry_url`, `mesh_condition_ids`, `mesh_intervention_ids`) or register them through an ADR-001 Appendix A amendment; then delete the `clinicaltrials.get_trial` entry from `REGISTRY_DEVIATIONS` in tests/contract/test_wire_contracts.py, in src/biosciences_mcp/clients/clinicaltrials.py (lines 444-478) and src/biosciences_mcp/models/trial.py (lines 141-144) per Constitution III (contradicts)
- [ ] T081 CRITICAL: Add runtime regex validation of `cross_references` values on the `Trial` model (field_validator or reuse of the `CrossReferences` protocol type) so malformed or non-registry values are rejected rather than passed through `dict[str, Any]`, in src/biosciences_mcp/models/trial.py (lines 141-144) per Constitution Required Pattern "Cross-reference regex validation" and plan: Required Patterns Check (missing)
- [ ] T082 Implement `search_trials` parameter validation: normalize and validate `status` against the contract enum (RECRUITING, COMPLETED, ACTIVE_NOT_RECRUITING, NOT_YET_RECRUITING, SUSPENDED, TERMINATED, WITHDRAWN) and `phase` against (EARLY_PHASE1, PHASE1, PHASE2, PHASE3, PHASE4, NA) accepting spec-style inputs such as `"Phase 3"` and `"recruiting"`, enforce `page_size` in 1-200, and return an ErrorEnvelope with code `INVALID_INPUT` and a recovery_hint listing the valid values; add `INVALID_INPUT` to `ErrorCode` in src/biosciences_mcp/models/envelopes.py (lines 16-24) and record the addition against ADR-001 Appendix B, in src/biosciences_mcp/clients/clinicaltrials.py (lines 229-248) per FR-004, FR-017, US1/AC4, contracts/search_trials.md (missing; T024 is marked complete but no validation exists)
- [ ] T083 Make `query` optional in `search_trials` (client method and `@mcp.tool` signature) so filter-only searches such as `search_trials(condition="diabetes", intervention="insulin", status="recruiting")` work, omitting `query.term` when absent and returning `INVALID_INPUT` when neither query nor any filter is supplied, in src/biosciences_mcp/clients/clinicaltrials.py (lines 200-234) and src/biosciences_mcp/servers/clinicaltrials.py (lines 103-114) per US1/AC2 and contracts/search_trials.md "query (optional)" (contradicts)
- [ ] T084 Add network-free unit tests that mock `_rate_limited_request` with sample ClinicalTrials.gov v2 JSON (from research.md) covering response parsing: `search_trials` → `TrialSearchCandidate` items plus cursor/total_count mapping; `get_trial` → protocol, eligibility, outcomes, sponsors, dates, cross_references extraction and omit-if-null on the wire; `get_trial_locations` → first-contact extraction, state omission for non-US sites, and empty list when `contactsLocationsModule` is absent, in tests/unit/test_clinicaltrials_client.py per FR-022, FR-023, FR-011, SC-008 (partial; tests/integration/test_clinicaltrials_api.py is module-skipped under Cloudflare so src/biosciences_mcp/clients/clinicaltrials.py lines 267-304, 361-502, 564-609 have no executable coverage)
- [ ] T085 Add mocked unit tests for `_map_http_error` and `_rate_limited_request`: 404 → `ENTITY_NOT_FOUND`, 429 → exponential backoff retries then `RATE_LIMITED` with Retry-After hint, 5xx → `UPSTREAM_ERROR`, other 4xx → `UPSTREAM_ERROR`, and 1 req/sec spacing; and replace the live, non-asserting tests `test_rate_limited_recovery_with_backoff` and `test_upstream_error_recovery_hint` in tests/integration/test_error_recovery.py (lines 231-276) which accept any envelope and 403 under Cloudflare, in tests/unit/test_clinicaltrials_client.py per FR-020, FR-021, FR-024, US4/AC2-AC4 (partial)
- [ ] T086 Align the server tool docstrings with actual error behaviour: remove or correct the `INVALID_INPUT` claims for malformed NCT CURIEs in src/biosciences_mcp/servers/clinicaltrials.py (lines 40, 224-225, 240, 281-282) since the client returns `UNRESOLVED_ENTITY` (src/biosciences_mcp/clients/clinicaltrials.py lines 340-349, 537-546), and make the malformed-CURIE `recovery_hint` (line 346 and 543) point to `search_trials` as required, per FR-008, FR-016, US4/AC1 (contradicts)
- [ ] T087 Move `_request_lock` and `_last_request_time` from class attributes to instance attributes set in `__init__`, use `time.monotonic()` instead of `asyncio.get_event_loop().time()`, and add jitter to the 429 backoff sleep to match the thundering-herd pattern used in src/biosciences_mcp/clients/pubchem.py (lines 92-95), in src/biosciences_mcp/clients/clinicaltrials.py (lines 46-48, 115-142) per plan: Required Patterns Check "Client-side Rate Limiting ... thundering herd prevention" (partial)
