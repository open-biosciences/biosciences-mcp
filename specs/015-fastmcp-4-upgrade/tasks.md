# Tasks: FastMCP 4 Upgrade and Connector Version Policy

**Input**: Design documents from `specs/015-fastmcp-4-upgrade/`

**Prerequisites**: [plan.md](plan.md) (approved 2026-09-30), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

**Tracking issue**: AGE-718 (its 3.4.7 target is superseded by this feature; see the AGE-718 comment of 2026-09-30)

**Tests**: Included. The spec and plan require them: the tool-surface contract test (FR-001, FR-002, FR-006), the version-policy test (FR-017, SC-007), and the existing tiers as regression gates.

**Organization**: Grouped by user story. Code ships as **two PRs**, plus ADR acceptance afterwards:
- **Core PR** (biosciences-mcp, branch `implement/015-fastmcp-4-upgrade-core`): Phase 2, US1, the core half of US4, and the core polish items.
- **Edge PR** (biosciences-mcp-edge, branch `implement/015-fastmcp-4-upgrade-edge`): US3 and the edge half of US4.
- US2 is deployment work on the core PR, done between opening and merging it.

**Ordering rule inside each PR**: the tool-surface contract test is committed and green on the **current** framework version before the commit that raises the pin. The guard exists before the change it guards (AGE-718 Step 1).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: US1 to US4, from spec.md

## Path Conventions

- Core: repository root `biosciences-mcp/`. Paths below are relative to it unless prefixed `edge:`.
- Edge: repository root `biosciences-mcp-edge/`, written `edge:<path>`.
- Feature artifacts: `specs/015-fastmcp-4-upgrade/` in core.
- Worktrees live under each repository's `.worktrees/` (ADR-PRG-001 §3.3). Launch Claude from the main checkout, not from inside a worktree (§3.6).

---

## Phase 1: Setup

**Purpose**: Prerequisite fix and isolated workspaces

- [x] T001 Gateway mounts use `tool_names` only; `prefix=`/`as_proxy=` removed in `src/biosciences_mcp/servers/gateway.py` (PR #18, `a319044`). Verified: identical 34-tool surface on 2.14.5, and the same 34 names on 3.4.7 and 4.0.10. Principle V waiver in plan.md Complexity Tracking.
- [ ] T002 Get PR #18 reviewed (`/pr-review 18`) and merged to `main` by merge commit. Then remove `.worktrees/fix-gateway-mount-tool-names` and its local branch (ADR-PRG-001 §3.4).
- [ ] T003 Create the core worktree `.worktrees/implement-015-core` on a new branch `implement/015-fastmcp-4-upgrade-core` from `origin/main` (after T002). Run `uv sync --extra dev`, and record `fastmcp`/`mcp` versions (quickstart §1; expect 2.14.5 / 1.26.0).
- [ ] T004 [P] Create the edge worktree `edge:.worktrees/implement-015-edge` on a new branch `implement/015-fastmcp-4-upgrade-edge` from edge `origin/main`. Add `.worktrees/` to `edge:.gitignore` as the branch's first commit; edge lacks the entry that ADR-PRG-001 assumes is org-wide.

---

## Phase 2: Foundational (core, on fastmcp 2.14.5, before any pin change)

**Purpose**: The caller-visible guard that every later core task is checked against

**⚠️ CRITICAL**: T005 must be committed and green on 2.14.5 before T008 raises the pin.

- [ ] T005 Write `tests/contract/test_tool_surface.py` (markers `contract`, `unit`; no network). Load `biosciences_mcp.servers.gateway.mcp` in process with `fastmcp.Client`, call `list_tools`, and compare against `specs/015-fastmcp-4-upgrade/contracts/tool-surface-baseline-core.json` (path resolved from the repository root), implementing all four invariants in `contracts/tool-surface-invariants.md`:
  1. The name set is equal.
  2. Each parameter's name, `type`, `required`, and `default` are equal.
  3. Every guidance line of the baseline description appears in the current tool description or in one of its parameter descriptions.
  4. Every baseline `Args:` entry's text appears in that parameter's description or in the tool description.

  Read schema fields version-tolerantly (`input_schema` if present, else `inputSchema`) so the same test runs on 2.14.5 and 4.x. On failure, the test names the tool and the missing line.
- [ ] T006 Run `uv run pytest tests/contract/test_tool_surface.py -v` on 2.14.5. It must pass for all 34 tools. Commit T005 alone, message citing FR-001, FR-002, FR-006, and AGE-718 Step 1.

**Checkpoint**: The guard is in place on the current version; the pin can now move.

---

## Phase 3: User Story 1: Agent callers are unaffected by the core upgrade (Priority: P1) 🎯 MVP

**Goal**: Core runs on fastmcp `>=4.0.10,<4.1` with identical tool names, parameters, and wire contract, and no lost description guidance.

**Independent Test**: In the core worktree, quickstart §2 passes:
- `tests/contract/test_tool_surface.py` is green.
- `contract and unit` is green (104 cases).
- `contract and integration` shows no failure beyond the 2.14.5 baseline.
- No Pydantic serializer warnings appear.

### Tests for User Story 1

- [ ] T007 [US1] Record the 2.14.5 baseline in the core worktree before the pin change. Run quickstart §2's four commands and save the outputs under `specs/015-fastmcp-4-upgrade/evidence/core-2.14.5/` (unit, contract-unit, gateway, contract-integration logs). This is the comparison set for FR-012. Expected on 2026-09-30: 11 contract-integration failures, all Ensembl 500 or IUPHAR 401 (IUPHAR is tracked separately as AGE-734).

### Implementation for User Story 1

- [ ] T008 [US1] Raise the pin in `pyproject.toml` to `"fastmcp>=4.0.10,<4.1",`. Add a reason comment on the preceding line: floor = version verified in spec 015, ceiling = upstream issue #5213 (Host guard default) and ADR-009 (FR-018). Run `uv lock` and `uv sync --extra dev`. Record the resolved `fastmcp` and `mcp` versions (expect 4.0.10 / 2.2.0).
- [ ] T009 [P] [US1] In `tests/integration/test_gateway.py`, replace `await mcp.get_tools()` (removed in 3.x) with `await mcp.list_tools()`. Keep the dict/list handling and all assertions unchanged.
- [ ] T010 [P] [US1] In `tests/contract/test_serialization_unit.py`, replace the import from `fastmcp.tools.tool` (absent in 4.x) with the 4.x location. Research B found it at `fastmcp.tools.base`; confirm by import before editing. No assertion changes.
- [ ] T011 [P] [US1] Parameterize envelope construction so 4.x serializes without warnings (research R8). Change `PaginationEnvelope.create(` to `PaginationEnvelope[<ItemModel>].create(` at each site, using the item type from that tool's return annotation, in `src/biosciences_mcp/clients/hgnc.py`, `uniprot.py`, `chembl.py`, `opentargets.py`, `string.py`, `biogrid.py`, and `ensembl.py`.
- [ ] T012 [P] [US1] Same change as T011 in `src/biosciences_mcp/clients/entrez.py`, `pubchem.py`, `iuphar.py`, `wikipathways.py`, `clinicaltrials.py`, and `drugbank.py`. 22 sites in total across T011 and T012; verify with `grep -rn 'PaginationEnvelope.create(' src/biosciences_mcp/clients`, which should return nothing.
- [ ] T013 [P] [US1] Restructure the tool docstrings in `src/biosciences_mcp/servers/hgnc.py` (`search_genes`, `get_gene`) and `src/biosciences_mcp/servers/uniprot.py` (`search_proteins`, `get_protein`).
  - Move every line of the `Returns:`, `Examples:`, `Error Codes:`, `Note:`, and response-shape blocks verbatim into the leading prose section, above `Args:`, as plain sentences or a short list. Leave `Args:` in place.
  - Don't reword the guidance. Invariant 3 matches lines after whitespace normalisation.
- [ ] T014 [P] [US1] Same restructuring as T013 in `src/biosciences_mcp/servers/chembl.py` (`search_compounds`, `get_compound`, `get_compounds_batch`) and `src/biosciences_mcp/servers/opentargets.py` (`search_targets`, `get_target`, `get_associations`).
- [ ] T015 [P] [US1] Same restructuring as T013 in `src/biosciences_mcp/servers/string.py` (`search_proteins`, `get_interactions`, `get_network_image_url`) and `src/biosciences_mcp/servers/biogrid.py` (`search_genes`, `get_interactions`).
- [ ] T016 [P] [US1] Same restructuring as T013 in `src/biosciences_mcp/servers/ensembl.py` (`search_genes`, `get_gene`, `get_transcript`) and `src/biosciences_mcp/servers/entrez.py` (`search_genes`, `get_gene`, `get_pubmed_links`).
- [ ] T017 [P] [US1] Same restructuring as T013 in `src/biosciences_mcp/servers/pubchem.py` (`search_compounds`, `get_compound`), `src/biosciences_mcp/servers/wikipathways.py` (`search_pathways`, `get_pathway`, `get_pathways_for_gene`, `get_pathway_components`), and `src/biosciences_mcp/servers/clinicaltrials.py` (`search_trials`, `get_trial`, `get_trial_locations`). That completes 30 tools across T013 to T017. The 4 IUPHAR tools have no `Args:` section and need no change.
- [ ] T018 [US1] Run `uv run pytest tests/contract/test_tool_surface.py -v` on 4.0.10. It must pass for all 34 tools, with invariant 3 proving no guidance was lost (FR-006). Fix any reported missing line in its server file and rerun.
- [ ] T019 [US1] Run quickstart §2 on 4.0.10 and save the outputs under `specs/015-fastmcp-4-upgrade/evidence/core-4.0.10/`. Confirm:
  - unit and contract+unit all pass
  - `test_gateway.py` passes
  - contract-integration failures are a subset of T007's, with persistent upstream failures rerun once after 10 seconds per FR-012
  - `grep -c PydanticSerializationUnexpectedValue` on the logs returns 0
- [ ] T020 [US1] Verify the telemetry. Run the gateway from this worktree under biosciences-otel-stack's `mcp` profile (`docker compose --profile mcp up -d --build`), call three tools, and confirm in Phoenix:
  - tool-level spans appear (`gen_ai.tool.name` or the 4.x equivalent): this is AGE-718's acceptance criterion
  - the `opentelemetry-instrument` wrapper still starts (FR-019)
  - with no collector running, the server still serves `list_tools` (graceful degradation)

  Record the span names and a screenshot path in `specs/015-fastmcp-4-upgrade/evidence/core-4.0.10/telemetry.md`.
- [ ] T021 [US1] Write the core PR's "User-visible contract" section from the allowed-changes table in `contracts/tool-surface-invariants.md`, with the observed counts from T018 and T019, and its effect on biosciences-deepagents, biosciences-temporal, and Claude Code plugin users (FR-007). Include the gateway validation-message change (research R5).

**Checkpoint**: The core upgrade is complete and verified locally. Open the core PR.

---

## Phase 4: User Story 2: The upgraded core is deployable to the hosting platform (Priority: P2)

**Goal**: The core PR's head runs on a Horizon preview deployment with no host-validation rejections; then production is updated with a timed rollback path.

**Independent Test**: Quickstart §4 checks 4.1 to 4.5 and 4.7 pass against the preview URL.

- [ ] T022 [US2] Create a Horizon preview deployment from `implement/015-fastmcp-4-upgrade-core`. Use entrypoint `src/biosciences_mcp/servers/gateway.py:mcp` and the same secrets as production (`BIOGRID_API_KEY`, `NCBI_API_KEY`), under a non-production server name. Leave every `FASTMCP_HTTP_*` variable unset (research R2). This needs Horizon web UI access, so it's a repository-owner action.
- [ ] T023 [US2] Run quickstart §4 checks 4.1 (Host accepted), 4.2 (34 names equal to the baseline keys), 4.3 (one success call per server; upstream failures per FR-012, IUPHAR expected to fail until AGE-734), and 4.4 (`hgnc_get_gene` free text returns `UNRESOLVED_ENTITY`) against the preview URL. Record the results in `specs/015-fastmcp-4-upgrade/evidence/core-preview.md`.
- [ ] T024 [US2] Run quickstart check 4.5 (a raw sessionless JSON-RPC `tools/call`, as `biosciences-deepagents` `apps/api/shared/mcp.py:69-143` sends it) against the preview URL, and record the result. "400 Missing session ID" means No-Go until Horizon's session mode is resolved (research R12).
- [ ] T025 [US2] Run quickstart check 4.7: redeploy the preview from the pre-upgrade `main` commit, and time it until check 4.2 passes on 2.14.5. Record the time against SC-005 (under 15 minutes). Then redeploy the upgrade head.
- [ ] T026 [US2] Record the decision (Go or No-Go, date, decider) in `specs/015-fastmcp-4-upgrade/evidence/core-preview.md` and in the core PR description (FR-011). A No-Go stops here: leave the pin on the branch, and file the blocker.
- [ ] T027 [US2] On Go: merge the core PR by merge commit and redeploy production. Run quickstart §5 (checks 4.1, 4.2, and 4.5 against `https://biosciences-mcp.fastmcp.app/mcp`, plus `FASTMCP_CLOUD_ENDPOINT=https://biosciences-mcp.fastmcp.app/mcp uv run pytest -m e2e -v`), and record the results. Delete the preview deployment.

**Checkpoint**: Core runs FastMCP 4 in production.

---

## Phase 5: User Story 3: Edge is upgraded under the same guarantees (Priority: P3)

**Goal**: Edge runs fastmcp `>=4.0.10,<4.1` with identical tool names, parameters, and wire responses, no lost description guidance, and no imports from core.

**Independent Test**: In the edge worktree:
- `uv run pytest -m unit` is green, including the new tool-surface test.
- The research C wire capture matches its 3.0.2 baseline.
- Quickstart §4 checks 4.1 to 4.4 and 4.7 pass on an edge preview deployment.

### Tests for User Story 3

- [ ] T028 [US3] Copy `specs/015-fastmcp-4-upgrade/contracts/tool-surface-baseline-edge.json` (core) to `edge:tests/fixtures/tool-surface-baseline.json`. Write `edge:tests/unit/test_tool_surface.py` (marker `unit`), implementing the same four invariants as T005 against `biosciences_mcp_edge.server.mcp` in process. Run it on 3.0.2; it must pass. Commit before T029.

### Implementation for User Story 3

- [ ] T029 [US3] In `edge:pyproject.toml`, replace `"fastmcp>=2.0,<3.4.3"` with `"fastmcp>=4.0.10,<4.1",`, with a reason comment as in T008. The `<3.4.3` Host-guard reason is obsolete since 3.4.4 (research R2). Run `uv lock` (this also clears finding F7, the lock/pyproject drift) and `uv sync --extra dev`, and record the resolved versions.
- [ ] T030 [P] [US3] In `edge:src/biosciences_mcp_edge/server.py`, change the two success-path envelope constructions (`server.py:56` and `:97`) to `PaginationEnvelope[OrcsScreenResult].create(...)` and `PaginationEnvelope[MechanismResult].create(...)` (research R8).
- [ ] T031 [P] [US3] In `edge:src/biosciences_mcp_edge/server.py`, restructure the `get_orcs_essentiality` and `get_mechanism` docstrings as in T013: move the `Returns:` text into the leading section, above `Args:`.
  - Don't change parameter types, hint text, or error mapping. Those belong to AGE-735 and AGE-733 (FR-014).
  - T030 and T031 edit the same file: make them separate commits, or do them in sequence.
- [ ] T032 [US3] Run `uv run pytest -m unit -v`; it must pass, including `test_tool_surface.py`. Then rerun the research wire capture (`_audits/fastmcp-4-2026-09-30/research/C-edge_capture.py`, outside the repository) against the worktree, and diff it with `C-wire_edge_baseline.json`: payloads must be identical (FR-004, FR-014). Save the diff summary to `specs/015-fastmcp-4-upgrade/evidence/edge-4.0.10.md` (core repository).
- [ ] T033 [US3] Confirm FR-013 with `grep -rn "biosciences_mcp\b" edge:src edge:tests | grep -v biosciences_mcp_edge`: no output.
- [ ] T034 [P] [US3] In `edge:docs/adr/README.md`:
  - Add a row for ADR-008 (not yet adopted; it isn't implemented in core either).
  - Add a row for ADR-009 (adopted via `tests/unit/test_framework_version_policy.py`; status "proposed" until T045).
  - Don't change the other rows; AGE-735 and AGE-736 own those corrections.
- [ ] T035 [P] [US3] Update `edge:CLAUDE.md`: the framework version line, the removal of the `<3.4.3` rationale, and a note that tool descriptions keep only the first docstring section, so return and error guidance goes above `Args:`.
- [ ] T036 [US3] Edge preview and production: run quickstart §4 checks 4.1 to 4.4 and 4.7 on an edge preview deployment (no `FASTMCP_HTTP_*` variables). Record them in `specs/015-fastmcp-4-upgrade/evidence/edge-preview.md` with the Go or No-Go decision. On Go, merge the edge PR, redeploy production, and repeat 4.1 and 4.2 against the production edge URL.

**Checkpoint**: Core and edge run the same framework major (SC-006, partial; US4 completes it).

---

## Phase 6: User Story 4: One framework version policy governs every connector repository (Priority: P4)

**Goal**: ADR-009 is written, and both repositories fail their own checks when outside it.

**Independent Test**: Quickstart §3. Setting a known-bad version in a scratch copy fails the policy test with a message naming ADR-009, in both repositories, and CI runs it on pull requests.

**Placement**: T037 to T041 ship in the **core PR**, after T008. T042 and T043 ship in the **edge PR**, after T029.

- [ ] T037 [US4] Write `docs/adr/proposed/adr-009-v0.1.md` (core). Create `docs/adr/proposed/`, and fill in every section required by `contracts/version-policy.md`:
  - scope and consumers
  - the supported range with the reason for each bound
  - the known-bad table (`==3.4.3`)
  - the mount usage rule
  - the change procedure
  - the divergence window
  - the Host-guard deployment rule

  Adopt AGE-718's pin convention (`>=X.Y.Z,<X.(Y+1)`, exact known-good floor, minor ceiling) as the rule for dependency bounds. Record biosciences-memory (`fastmcp>=2.13.3,<3`) as an open question: in scope or not.
- [ ] T038 [US4] Write `tests/unit/test_framework_version_policy.py` (core; marker `unit`; no network) per `contracts/version-policy.md` "Policy test contract":
  - constants `SUPPORTED = ">=4.0.10,<4.1"` and `KNOWN_BAD`, with a comment citing ADR-009 v0.1
  - check 1: the `pyproject.toml` specifier is within the range and excludes known-bad versions
  - check 2: the `uv.lock` version
  - check 3: the reason comment on the upper bound

  Failure messages name ADR-009 and the incident. Use `packaging.specifiers`, and add `packaging` to the dev extras if it isn't already available.
- [ ] T039 [US4] Add a self-check test in the same file (SC-007). It writes known-bad copies of `pyproject.toml` and `uv.lock` to `tmp_path`, runs the three checks against them, and asserts each check fails with the ADR-009 message.
- [ ] T040 [P] [US4] Create `.github/workflows/ci.yml` (core): on `pull_request` and `push` to `main`, set up uv on Python 3.12, run `uv sync --extra dev`, then `uv run pytest -m unit -q`. Unit only: no secrets, no network.
- [ ] T041 [US4] Run quickstart §3 by hand in the core worktree (set `fastmcp==3.4.3` in a scratch copy and run the policy test), and record the expected failure output in `specs/015-fastmcp-4-upgrade/evidence/core-4.0.10/policy-selfcheck.md`.
- [ ] T042 [P] [US4] Write `edge:tests/unit/test_framework_version_policy.py` (a copy of T038 and T039 with edge paths; the constants are a local copy per FR-013, with a comment citing ADR-009 v0.1 and the core path), and `edge:.github/workflows/ci.yml` (as T040).
- [ ] T043 [US4] Run quickstart §3 in the edge worktree, and record the result in `specs/015-fastmcp-4-upgrade/evidence/edge-4.0.10.md`.
- [ ] T044 [P] [US4] File a Linear issue (project "Open-Biosciences Platform v1.1 — dogfooding + Synapse alignment"): psychology-mcp adopts ADR-009. It means raising `fastmcp>=2.14.1,<3.0` (locked 2.14.7) to the ADR-009 range, adding the policy test and the tool-surface test, and doing a preview deployment. Link it to AGE-718.
- [ ] T045 [US4] After both PRs merge and production runs inside the range: move `docs/adr/proposed/adr-009-v0.1.md` to `docs/adr/accepted/adr-009-v1.0.md` with status Accepted, in a core docs PR. In a separate biosciences-program PR, add an ADR-009 row to the "Where things are" table in `biosciences-program/docs/adr/README.md`. Update edge's ADR-009 row (T034) to "adopted".

**Checkpoint**: The policy is accepted and enforced in core and edge (SC-006, SC-007).

---

## Phase 7: Polish & Cross-Cutting Concerns

- [ ] T046 [P] Update core `CLAUDE.md` in the core PR:
  - framework versions in the deployment section (replace "There is no `fastmcp deploy` or `fastmcp auth` CLI command in FastMCP 2.x" with what 4.x provides; research A notes `fastmcp login`/`whoami`; deployment stays web-UI)
  - a Known Issues entry saying tool descriptions keep only the first docstring section, so return and error guidance goes above `Args:`, enforced by `tests/contract/test_tool_surface.py`
  - a Known Issues entry for the mount usage rule
  - the new test counts from T019
- [ ] T047 Append rows to `docs/speckit-process-record.md`, each in the PR that carries the artifact: `/speckit-tasks` (this file), `/speckit-implement` (core PR, edge PR), and `/speckit-converge` (T048).
- [ ] T048 Run `/speckit-converge` with `SPECIFY_FEATURE_DIRECTORY=specs/015-fastmcp-4-upgrade` after the core PR's code is complete. It appends a Convergence phase to this file. Re-grade any constitution-derived CRITICAL item against accepted-ADR precedence before acting on it (CLAUDE.md, Spec Kit). Converge sees only core's code, so record edge's evidence (T032, T033, T036, T043) by hand in the edge PR.
- [ ] T049 [P] When the core PR opens, update AGE-718's title and target to FastMCP 4.0.10, link the core PR, and set its status to In Progress. Link the edge PR when it opens.
- [ ] T050 Clean up per ADR-PRG-001 §3.4 after each merge: remove `.worktrees/implement-015-core`, `edge:.worktrees/implement-015-edge`, and the research scratch worktrees `.worktrees/scratch-015-core` and `_audits/fastmcp-4-2026-09-30/worktrees/edge` (each holds only unpushed research commits), plus the feature worktree `.worktrees/feature-015-fastmcp-4-upgrade` once the spec PR merges. Delete the matching local branches.
- [ ] T051 Set `spec.md` **Status** to Implemented once T045 is done, and close AGE-718.

---

## Dependencies & Execution Order

### Phase dependencies

```text
T001 (done) → T002 → T003 ─┬→ Phase 2 (T005–T006) → US1 (T007–T021) ─┬→ US2 (T022–T027)
                           │                                          └→ US4-core (T037–T041, same PR, after T008)
T004 ──────────────────────┴→ US3 (T028–T036) → US4-edge (T042–T043)
US2 + US3 merged → T045 → T051
```

- **US1** depends on Phase 2: T005 must be green on 2.14.5 before T008.
- **US2** depends on US1: the core PR head is what gets deployed.
- **US3** is independent of US1 and US2 in code, since edge has no imports from core. It's sequenced after core in production by plan.md's delivery order, so a Horizon problem shows up first on the larger caller base, with one rollback.
- **US4** tasks split across both PRs. T045 (acceptance) waits for both merges.

### Within the core PR (commit order)

T005 → T007 → T008 → (T009, T010, T011, T012) → (T013–T017) → T018 → T019 → T020 → T037–T041 → T046 → T021 (PR text)

### Within the edge PR (commit order)

T004 (.gitignore) → T028 → T029 → (T030 then T031, same file) → T032 → T033 → T034, T035 → T042 → T043

### Parallel opportunities

- T003 and T004 (different repositories).
- T009, T010, T011, and T012: four different files or file groups, all after T008.
- T013 to T017: five disjoint groups of server files. The [P] markers allow five concurrent agents, each taking one group, with T018 as the join.
- T034 and T035 (different edge files); T040 and T042 (different repositories); T044 and T049 (Linear only).

### Parallel example: US1 docstrings

```text
Agent A: T013  servers/hgnc.py, servers/uniprot.py
Agent B: T014  servers/chembl.py, servers/opentargets.py
Agent C: T015  servers/string.py, servers/biogrid.py
Agent D: T016  servers/ensembl.py, servers/entrez.py
Agent E: T017  servers/pubchem.py, servers/wikipathways.py, servers/clinicaltrials.py
Join:    T018  uv run pytest tests/contract/test_tool_surface.py -v
```

Per ADR-005, parallel agents each work in their own worktree on a sub-branch of `implement/015-fastmcp-4-upgrade-core`, and the joins are merged before T018.

---

## Implementation Strategy

### MVP (US1)

Phase 1 → Phase 2 → US1 gives a core branch on FastMCP 4 that is provably caller-identical locally: names, parameters, description guidance, wire contract, and no serializer warnings. This is the slice where review effort pays off most. It doesn't ship until US2's preview gate passes.

### Incremental delivery

1. Core PR (US1 plus US4-core) → preview (US2) → Go → production.
2. Edge PR (US3 plus US4-edge) → preview → Go → production.
3. ADR-009 acceptance (T045), then the psychology-mcp follow-up (T044, its own repository).

### Out of scope here (tracked elsewhere)

AGE-733 (edge key leak: fix before or alongside the edge PR, never inside it), AGE-734 (IUPHAR API key), AGE-735 and AGE-736 (edge compliance), AGE-737 (argument-name drift), AGE-738 (deploy-cloud skill), and AGE-698 (ADR-007 base client).
