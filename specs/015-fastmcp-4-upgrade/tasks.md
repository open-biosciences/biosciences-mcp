# Tasks: FastMCP 3.4 Upgrade, Gated Path to 4.x, and Connector Version Policy

**Amended 2026-10-01**: target `fastmcp>=3.4.7,<3.5` (spec amendment, option B). Removed the four 4.x-only tasks: the `test_serialization_unit.py` import fix, core envelope parameterization (two tasks), and edge envelope parameterization. Added a task to file the 4.x follow-up. Tasks renumbered; none had started.

**Remediated 2026-10-01** (/speckit-analyze H1–H5, E1, E2, B1, C1, C2, F1, approved by the owner): added the spec-PR merge task (H2), the temporal check (H5), and edge's user-visible-contract task (E2); added an undeclared-argument invariant (E1); clarified the docstring rule (B1); versioned the edge capture script (C1); fixed the evidence location (C2); corrected the CLAUDE.md task (F1). Renumbered again.

**Remediated again 2026-10-01** (/speckit-analyze re-run: F4, C3, F5, F6, C4, approved by the owner): edge evidence is committed to core before the edge PR merges (T036, FR-011); the edge wire comparison recaptures 3.0.2 in the same session (T031); smaller consistency fixes. No renumbering.

**Remediated after the PR #19 review 2026-10-01** (owner-approved): the docstring header rule covers every column-0 `Name:` line (T011); the telemetry task builds from the upgrade worktree (T019); the tool-surface test covers six invariants, including output schema, wrap flag, annotations, `_meta` tags, parameter descriptions, and constraints (T006, T028); a core wire capture through the gateway was added; the edge capture records `_meta` and refuses to run without a key (T031); a follow-up filing task was added (ADR-008 reconciliation, gateway recovery hints, empty entity output schemas); ADR-009 records psychology-mcp's interim status. Renumbered.

**Input**: Design documents from `specs/015-fastmcp-4-upgrade/`

**Prerequisites**: [plan.md](plan.md) (approved 2026-09-30; amended plan approved 2026-10-01), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

**Tracking issue**: AGE-718. Its 3.4.7 target is this feature's target again after the 2026-10-01 amendment.

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
- Evidence: every evidence file for both repositories lives under `specs/015-fastmcp-4-upgrade/evidence/` in **core**. Core evidence is committed on the core implement branch. Edge evidence (T031, T033, T043, and T036's preview record) is committed to core in a docs PR that T036 opens and merges **before** the edge PR merges (FR-011), and summarised in the edge PR description. T045 adds only edge's production results.
- Worktrees live under each repository's `.worktrees/` (ADR-PRG-001 §3.3). Launch Claude from the main checkout, not from inside a worktree (§3.6).

---

## Phase 1: Setup

**Purpose**: Prerequisite fix and isolated workspaces

- [x] T001 Gateway mounts use `tool_names` only; `prefix=`/`as_proxy=` removed in `src/biosciences_mcp/servers/gateway.py` (PR #18, `a319044`). Implemented and reviewed (`/pr-review 18`: no blocking findings); the merge is T002. Verified: identical 34-tool list on 2.14.5, and the same 34 names on 3.4.7 and 4.0.10. On 2.14.5 unprefixed names now reach the last-mounted server until the pin moves (PR #18 description). Principle V waiver in plan.md Complexity Tracking.
- [X] T002 Get PR #18 reviewed (`/pr-review 18`) and merged to `main` by merge commit. Then remove `.worktrees/fix-gateway-mount-tool-names` and its local branch (ADR-PRG-001 §3.4).
- [X] T003 Open the spec PR from `feature/015-fastmcp-4-upgrade` to `main` (spec, plan, research, contracts, tasks, process record), review it with `/pr-review`, and merge it by merge commit. CLAUDE.md starts implementation branches only after the spec is merged, and T006 reads `specs/015-fastmcp-4-upgrade/contracts/tool-surface-baseline-core.json` from `main`.
- [X] T004 Create the core worktree `.worktrees/implement-015-core` on a new branch `implement/015-fastmcp-4-upgrade-core` from `origin/main` (after T002 and T003). Run `uv sync --extra dev`, and record `fastmcp`/`mcp` versions (quickstart §1; expect 2.14.5 / 1.26.0).
- [ ] T005 [P] Create the edge worktree `edge:.worktrees/implement-015-edge` on a new branch `implement/015-fastmcp-4-upgrade-edge` from edge `origin/main` (after T003, so the baseline it copies is on core `main`). Add `.worktrees/` to `edge:.gitignore` as the branch's first commit; edge lacks the entry that ADR-PRG-001 assumes is org-wide.

---

## Phase 2: Foundational (core, on fastmcp 2.14.5, before any pin change)

**Purpose**: The caller-visible guard that every later core task is checked against

**⚠️ CRITICAL**: T006 must be committed and green on 2.14.5 before T009 raises the pin.

- [X] T006 Write `tests/contract/test_tool_surface.py` (markers `contract`, `unit`; no network). Load `biosciences_mcp.servers.gateway.mcp` in process with `fastmcp.Client`, call `list_tools`, and compare against `specs/015-fastmcp-4-upgrade/contracts/tool-surface-baseline-core.json` (path resolved from the repository root), implementing all six invariants in `contracts/tool-surface-invariants.md`. Project `list_tools` with the functions from `specs/015-fastmcp-4-upgrade/research/surface-tools/project_surface.py`, copied into a test helper, so test and baseline can't drift.
  1. The name set is equal.
  2. Each parameter's name, `type`, `required`, `default`, and `constraints` are equal.
  3. Every guidance line of the baseline description appears in the current tool description or in one of its parameter descriptions. Every column-0 `Name:` header line is ignored.
  4. Every baseline `Args:` entry's text, and every baseline parameter `description`, appears in that parameter's description or in the tool description.
  5. A call with an undeclared argument (`hgnc_get_gene` with `hgnc_id="HGNC:1100"` plus `bogus_extra=1`; this one is rejected before any network call) is rejected: `CallToolResult.isError` is true. Record the message text, which FR-007 lists, but don't assert it (FR-003; research R5).
  6. The dereferenced output schema (with `description`/`title` keys removed), `wrap_result`, `annotations`, and `meta.tags` are equal.

  Add the self-test from the invariants contract: a scratch change that removes `x-fastmcp-wrap-result`, edits one IUPHAR `Field(description=…)`, or changes one constraint must fail.

  Read schema fields version-tolerantly (`inputSchema`, else `input_schema`) so the same test runs on 2.14.5, 3.4.7, and a later 4.x. On failure, the test names the tool and the missing line.
- [X] T007 Run `uv run pytest tests/contract/test_tool_surface.py -v` on 2.14.5. It must pass for all 34 tools. Commit T006 alone, message citing FR-001, FR-002, FR-006, and AGE-718 Step 1.

**Checkpoint**: The guard is in place on the current version; the pin can now move.

---

## Phase 3: User Story 1: Agent callers are unaffected by the core upgrade (Priority: P1) 🎯 MVP

**Goal**: Core runs on fastmcp `>=3.4.7,<3.5` with identical tool names, parameters, and wire contract, and no lost description guidance.

**Independent Test**: In the core worktree, quickstart §2 passes:
- `tests/contract/test_tool_surface.py` is green.
- `contract and unit` is green (104 cases plus the new tool-surface cases).
- `contract and integration` shows no failure beyond the 2.14.5 baseline.
- No Pydantic serializer warnings appear.

### Tests for User Story 1

- [ ] T008 [US1] Record the 2.14.5 baseline in the core worktree before the pin change. Run quickstart §2's four commands and save the outputs under `specs/015-fastmcp-4-upgrade/evidence/core-2.14.5/` (unit, contract-unit, gateway, contract-integration logs). This is the comparison set for FR-012. Expected on 2026-09-30: 11 contract-integration failures, all Ensembl 500 or IUPHAR 401 (IUPHAR is tracked separately as AGE-734).

### Implementation for User Story 1

- [ ] T009 [US1] Raise the pin in `pyproject.toml` to `"fastmcp>=3.4.7,<3.5",`. Add a reason comment on the preceding line: floor = version verified in spec 015; ceiling = minor ceiling, with 4.x not yet supported under ADR-009 (FR-018, FR-020). Run `uv lock` and `uv sync --extra dev`. Record the resolved `fastmcp` and `mcp` versions (expect 3.4.7 and `mcp` 1.x; `mcp` must stay below 2.0).
- [ ] T010 [P] [US1] In `tests/integration/test_gateway.py`, replace `await mcp.get_tools()` (removed in 3.x) with `await mcp.list_tools()`. Keep the dict/list handling and all assertions unchanged.
- [ ] T011 [P] [US1] Restructure the tool docstrings in `src/biosciences_mcp/servers/hgnc.py` (`search_genes`, `get_gene`) and `src/biosciences_mcp/servers/uniprot.py` (`search_proteins`, `get_protein`).
  - Move every line of the `Returns:`, `Examples:`, `Error Codes:`, `Note:`, and response-shape blocks into the leading prose section, above `Args:`, **unchanged**. Delete only the section header lines themselves: every column-0 `Name:` line except `Args:` (in the baseline: `Returns:`, `Example:`, `Examples:`, `Error Codes:`, `Errors:`, `Note:`, `Use cases:`, `Workflow:`). Keeping any of them makes 3.4.7 drop that line and everything after it (simulated 2026-10-01: 24 lines lost when `Example:` was kept; 0 with all headers deleted). Don't add bullets, merge lines, or reword: invariant 3 matches each line after whitespace normalisation only.
  - Leave `Args:` in place.
- [ ] T012 [P] [US1] Same restructuring as T011 in `src/biosciences_mcp/servers/chembl.py` (`search_compounds`, `get_compound`, `get_compounds_batch`) and `src/biosciences_mcp/servers/opentargets.py` (`search_targets`, `get_target`, `get_associations`).
- [ ] T013 [P] [US1] Same restructuring as T011 in `src/biosciences_mcp/servers/string.py` (`search_proteins`, `get_interactions`, `get_network_image_url`) and `src/biosciences_mcp/servers/biogrid.py` (`search_genes`, `get_interactions`).
- [ ] T014 [P] [US1] Same restructuring as T011 in `src/biosciences_mcp/servers/ensembl.py` (`search_genes`, `get_gene`, `get_transcript`) and `src/biosciences_mcp/servers/entrez.py` (`search_genes`, `get_gene`, `get_pubmed_links`).
- [ ] T015 [P] [US1] Same restructuring as T011 in `src/biosciences_mcp/servers/pubchem.py` (`search_compounds`, `get_compound`), `src/biosciences_mcp/servers/wikipathways.py` (`search_pathways`, `get_pathway`, `get_pathways_for_gene`, `get_pathway_components`), and `src/biosciences_mcp/servers/clinicaltrials.py` (`search_trials`, `get_trial`, `get_trial_locations`). That completes 30 tools across T011 to T015. The 4 IUPHAR tools have no `Args:` section and need no change.
- [ ] T016 [US1] Run `uv run pytest tests/contract/test_tool_surface.py -v` on 3.4.7. It must pass for all 34 tools, with invariant 3 proving no guidance was lost (FR-006). Fix any reported missing line in its server file and rerun.
- [ ] T017 [US1] Run quickstart §2 on 3.4.7 and save the outputs under `specs/015-fastmcp-4-upgrade/evidence/core-3.4.7/`. Confirm:
  - unit and contract+unit all pass
  - `test_gateway.py` passes
  - contract-integration failures are a subset of T008's, with persistent upstream failures rerun once after 10 seconds per FR-012
  - `grep -c PydanticSerializationUnexpectedValue` on the logs returns 0 (none were seen at 3.4.7 in research; they're a 4.x issue)
  - the server log shows the new 3.4.7 traceback noise for rejected gateway calls only as expected (research R5); record it, don't fix it
- [ ] T018 [US1] Core wire capture through the gateway (FR-003, FR-004, FR-005; data model "Representative call set"). Write `specs/015-fastmcp-4-upgrade/research/core-capture/core_capture.py`, modelled on `research/edge-capture/edge_capture.py`. It calls `biosciences_mcp.servers.gateway.mcp` in process through `fastmcp.Client.call_tool_mcp` and records `content`, `structuredContent`, `isError`, and `meta`. Cases, all network-free:
  - every strict lookup tool with free text (13 on 2026-10-01)
  - `hgnc_get_gene` with an undeclared argument, a missing argument, and a wrong type
  - a simulated upstream 500 and 429 for each httpx-based server, via a patched transport (record ChEMBL's SDK path as not simulated)

  Run it on 2.14.5 and 3.4.7 in the same session: 2.14.5 via `PYTHONPATH=src uv run --no-project --with fastmcp==2.14.5 …` from this worktree, and 3.4.7 in the worktree environment. Diff the two. Every difference must be a row of the allowed-changes table (result `_meta`, gateway validation text). Save the diff summary to `specs/015-fastmcp-4-upgrade/evidence/core-3.4.7/wire-diff.md`.
- [ ] T019 [US1] Verify the telemetry. biosciences-otel-stack's `fastmcp-gateway` service hard-codes `build.context: ../biosciences-mcp` (the primary checkout, on `main`), so build from the worktree with an override. Write `<scratch>/compose.015.yml` with `services: {fastmcp-gateway: {build: {context: /home/donbr/open-biosciences/biosciences-mcp/.worktrees/implement-015-core}, image: biosciences-mcp-gateway:otel-015}}`. From `biosciences-otel-stack/`, run `docker compose -f docker-compose.yml -f <scratch>/compose.015.yml --profile mcp up -d --build`. Confirm the container's version with `docker compose -f docker-compose.yml -f <scratch>/compose.015.yml run --rm fastmcp-gateway python -c "import importlib.metadata as m; print(m.version('fastmcp'))"` (expect 3.4.7). Then call three tools and confirm in Phoenix:
  - tool-level spans appear (`gen_ai.tool.name`, `fastmcp.server.name`; these arrived in 3.x): this is AGE-718's acceptance criterion
  - the `opentelemetry-instrument` wrapper still starts (FR-019)
  - with no collector running, the server still serves `list_tools` (graceful degradation)

  Record the in-container fastmcp version, the span names, and a screenshot path in `specs/015-fastmcp-4-upgrade/evidence/core-3.4.7/telemetry.md`.
- [ ] T020 [US1] Write the core PR's "User-visible contract" section from the allowed-changes table in `contracts/tool-surface-invariants.md`, with the observed counts from T016 and T017, and its effect on biosciences-deepagents, biosciences-temporal, and Claude Code plugin users (FR-007). Include the gateway validation-message change (research R5).

**Checkpoint**: The core upgrade is complete and verified locally. Open the core PR.

---

## Phase 4: User Story 2: The upgraded core is deployable to the hosting platform (Priority: P2)

**Goal**: The core PR's head runs on a Horizon preview deployment with no host-validation rejections; then production is updated with a timed rollback path.

**Independent Test**: Quickstart §4 checks 4.1 to 4.5 and 4.7 pass against the preview URL, and check 4.8 (temporal, local) passes against the upgrade worktree.

- [ ] T021 [US2] Create a Horizon preview deployment from `implement/015-fastmcp-4-upgrade-core`. Use entrypoint `src/biosciences_mcp/servers/gateway.py:mcp` and the same secrets as production (`BIOGRID_API_KEY`, `NCBI_API_KEY`), under a non-production server name. Leave every `FASTMCP_HTTP_*` variable unset (research R2). This needs Horizon web UI access, so it's a repository-owner action.
- [ ] T022 [US2] Run quickstart §4 checks 4.1 (Host accepted), 4.2 (34 names equal to the baseline keys), 4.3 (one success call per server; upstream failures per FR-012, IUPHAR expected to fail until AGE-734), and 4.4 (`hgnc_get_gene` free text returns `UNRESOLVED_ENTITY`) against the preview URL. Record the results in `specs/015-fastmcp-4-upgrade/evidence/core-preview.md`.
- [ ] T023 [US2] Run quickstart check 4.5 (a raw sessionless JSON-RPC `tools/call`, as `biosciences-deepagents` `apps/api/shared/mcp.py:69-143` sends it) against the preview URL, and record the result. "400 Missing session ID" means No-Go until Horizon's session mode is resolved (research R12).
- [ ] T024 [US2] Run quickstart check 4.8 (biosciences-temporal, SC-003). Temporal launches core's gateway over stdio from the sibling checkout (`src/biosciences_temporal/agents/base.py:20-61`, `GATEWAY_SERVER = "src/biosciences_mcp/servers/gateway.py"`), so it moves to 3.4.7 as soon as that checkout updates after merge. With `BIOSCIENCES_MCP_PATH=/home/donbr/open-biosciences/biosciences-mcp/.worktrees/implement-015-core`, use temporal's `create_mcp_client()` to list tools (expect 34) and call `hgnc_search_genes` and `hgnc_get_gene`. Then run one temporal agent workflow end to end if its LLM key is configured. Record the results in `specs/015-fastmcp-4-upgrade/evidence/core-preview.md`. A failure is a No-Go input for T026.
- [ ] T025 [US2] Run quickstart check 4.7: redeploy the preview from the pre-upgrade `main` commit, and time it until check 4.2 passes on 2.14.5. Record the time against SC-005 (under 15 minutes). Then redeploy the upgrade head.
- [ ] T026 [US2] Record the decision (Go or No-Go, date, decider) in `specs/015-fastmcp-4-upgrade/evidence/core-preview.md` and in the core PR description (FR-011). A No-Go stops here: leave the pin on the branch, and file the blocker.
- [ ] T027 [US2] On Go: merge the core PR by merge commit and redeploy production. Run quickstart §5 (checks 4.1, 4.2, and 4.5 against `https://biosciences-mcp.fastmcp.app/mcp`, plus `FASTMCP_CLOUD_ENDPOINT=https://biosciences-mcp.fastmcp.app/mcp uv run pytest -m e2e -v`), and record the results. Delete the preview deployment.

**Checkpoint**: Core runs FastMCP 3.4.7 in production.

---

## Phase 5: User Story 3: Edge is upgraded under the same guarantees (Priority: P3)

**Goal**: Edge runs fastmcp `>=3.4.7,<3.5` with identical tool names, parameters, and wire responses, no lost description guidance, and no imports from core.

**Independent Test**: In the edge worktree:
- `uv run pytest -m unit` is green, including the new tool-surface test.
- The research C wire capture matches its 3.0.2 baseline.
- Quickstart §4 checks 4.1 to 4.4 and 4.7 pass on an edge preview deployment.

### Tests for User Story 3

- [ ] T028 [US3] Copy `specs/015-fastmcp-4-upgrade/contracts/tool-surface-baseline-edge.json` (core) to `edge:tests/fixtures/tool-surface-baseline.json`. Write `edge:tests/unit/test_tool_surface.py` (marker `unit`), implementing the same five invariants as T006 against `biosciences_mcp_edge.server.mcp` in process (invariant 5 on `get_mechanism` with `chembl_id="CHEMBL:25"` plus `bogus_extra=1`). Run it on 3.0.2; it must pass. Commit before T029.

### Implementation for User Story 3

- [ ] T029 [US3] In `edge:pyproject.toml`, replace `"fastmcp>=2.0,<3.4.3"` with `"fastmcp>=3.4.7,<3.5",`, with a reason comment as in T009. The `<3.4.3` Host-guard reason is obsolete since 3.4.4 (research R2). Run `uv lock` (this also clears finding F7, the lock/pyproject drift) and `uv sync --extra dev`, and record the resolved versions.
- [ ] T030 [P] [US3] In `edge:src/biosciences_mcp_edge/server.py`, restructure the `get_orcs_essentiality` and `get_mechanism` docstrings as in T011: move the `Returns:` text into the leading section, above `Args:`.
  - Don't change parameter types, hint text, or error mapping. Those belong to AGE-735 and AGE-733 (FR-014).
- [ ] T031 [US3] Run `uv run pytest -m unit -v`; it must pass, including `test_tool_surface.py`. Then compare wire payloads, with both versions captured in the same session so upstream data changes can't masquerade as framework changes:
  - The script is `/home/donbr/open-biosciences/biosciences-mcp/specs/015-fastmcp-4-upgrade/research/edge-capture/edge_capture.py`, versioned in core since T003. Run `git -C /home/donbr/open-biosciences/biosciences-mcp pull --ff-only` first, so the primary core checkout (on `main`) has it.
  - 3.0.2: create a temporary detached edge worktree at the commit T005 branched from (`git -C /home/donbr/open-biosciences/biosciences-mcp-edge worktree add --detach .worktrees/edge-baseline-015 <base-sha>`), run `uv run python <script> 3.0.2 <scratch-out-dir>` there, then remove it. `uv` may relock there because of finding F7; that's harmless in a throwaway worktree.
  - 3.4.7: immediately afterwards, run `uv run python <script> 3.4.7 <scratch-out-dir>` in the implement worktree.
  - Diff `C-wire_edge_3.0.2.json` with `C-wire_edge_3.4.7.json`: payloads, including `structuredContent`, must be identical (FR-004, FR-014). The only allowed difference is the result `_meta` row of the allowed-changes table. Export `BIOGRID_API_KEY` first: the script refuses to run without it, because the live ORCS case would be vacuous. Use `specs/015-fastmcp-4-upgrade/research/edge-capture/wire_edge_3.0.2.json` (captured 2026-09-30) only as a reference for the payload's shape. The script redacts the real BioGRID key and uses a fake one for error cases. Edge was never captured at 3.4.7 in research, so this is the first wire evidence for it (research R9). Save the diff summary to `specs/015-fastmcp-4-upgrade/evidence/edge-3.4.7.md` (core repository; committed per Path Conventions → Evidence).
- [ ] T032 [US3] Confirm FR-013 with `grep -rn "biosciences_mcp\b" edge:src edge:tests | grep -v biosciences_mcp_edge`: no output.
- [ ] T033 [US3] Write the edge PR's "User-visible contract" section (FR-007), following T020. List the description changes from T030, the auto-generated `title` annotations, the unchanged `additionalProperties: false` (edge already had it on 3.0.2), and the undeclared-argument message text from invariant 5, with the effect on Claude Code plugin users (the edge tools' callers). Copy it into `specs/015-fastmcp-4-upgrade/evidence/edge-3.4.7.md`.
- [ ] T034 [P] [US3] In `edge:docs/adr/README.md`:
  - Add a row for ADR-008 (not yet adopted; it isn't implemented in core either).
  - Add a row for ADR-009 (adopted via `tests/unit/test_framework_version_policy.py`; status "proposed" until T045).
  - Don't change the other rows; AGE-735 and AGE-736 own those corrections.
- [ ] T035 [P] [US3] Update `edge:CLAUDE.md`: the framework version line, the removal of the `<3.4.3` rationale, and a note that tool descriptions keep only the first docstring section, so return and error guidance goes above `Args:`.
- [ ] T036 [US3] Edge preview, decision, evidence, then merge, in this order (after T042 and T043):
  1. Run quickstart §4 checks 4.1 to 4.4 and 4.7 on an edge preview deployment (no `FASTMCP_HTTP_*` variables).
  2. Record the results and the Go or No-Go decision (date, decider) in `specs/015-fastmcp-4-upgrade/evidence/edge-preview.md`.
  3. Commit all edge evidence (`edge-3.4.7.md` from T031, T033 and T043, plus `edge-preview.md`) to core on a branch `docs/015-edge-evidence`, open the PR, and merge it. This records the evidence in the feature's artifacts before edge's pin reaches edge `main` (FR-011).
  4. On Go: merge the edge PR by merge commit, redeploy production, and repeat 4.1 and 4.2 against the production edge URL. Those production results go into T045's PR. On No-Go: stop, leave the pin on the branch, and file the blocker.

**Checkpoint**: Core and edge run the same framework major (SC-006, partial; US4 completes it).

---

## Phase 6: User Story 4: One framework version policy governs every connector repository (Priority: P4)

**Goal**: ADR-009 is written, and both repositories fail their own checks when outside it.

**Independent Test**: Quickstart §3. Setting a known-bad version in a scratch copy fails the policy test with a message naming ADR-009, in both repositories, and CI runs it on pull requests.

**Placement**: T037 to T041 ship in the **core PR**, after T009. T042 and T043 ship in the **edge PR**, after T029.

- [ ] T037 [US4] Write `docs/adr/proposed/adr-009-v0.1.md` (core). Create `docs/adr/proposed/`, and fill in every section required by `contracts/version-policy.md`:
  - scope and consumers
  - the supported range with the reason for each bound
  - the known-bad table (`==3.4.3`)
  - the mount usage rule
  - the change procedure
  - the divergence window
  - the Host-guard deployment rule
  - section 2a: 4.x not yet supported, with FR-020's evidence list and the known 4.x work
  - section 5a: each consumer's status at acceptance (psychology-mcp's interim divergence and its expiry)

  Adopt AGE-718's pin convention (`>=X.Y.Z,<X.(Y+1)`, exact known-good floor, minor ceiling) as the rule for dependency bounds. Record biosciences-memory (`fastmcp>=2.13.3,<3`) as an open question: in scope or not.
- [ ] T038 [US4] Write `tests/unit/test_framework_version_policy.py` (core; marker `unit`; no network) per `contracts/version-policy.md` "Policy test contract":
  - constants `SUPPORTED = ">=3.4.7,<3.5"` and `KNOWN_BAD`, with a comment citing ADR-009 v0.1. Because the range excludes 4.x, a 4.x lock fails check 2 with a message naming FR-020's gate.
  - check 1: the `pyproject.toml` specifier is within the range and excludes known-bad versions
  - check 2: the `uv.lock` version
  - check 3: the reason comment on the upper bound

  Failure messages name ADR-009 and the incident. Use `packaging.specifiers`, and add `packaging` to the dev extras if it isn't already available. Cite ADR-009 by its file version in a comment (`v0.1` until acceptance; T045 updates it).
- [ ] T039 [US4] Add a self-check test in the same file (SC-007). It writes known-bad copies to `tmp_path` and asserts each check fails with the ADR-009 message: a `uv.lock` locking `fastmcp` 3.4.3 (check 2), a `pyproject.toml` whose specifier admits 3.4.3 or 4.x (check 1), and a `pyproject.toml` whose upper bound has **no reason comment** (check 3, which doesn't depend on the version).
- [ ] T040 [P] [US4] Create `.github/workflows/ci.yml` (core): on `pull_request` and `push` to `main`, set up uv on Python 3.12, run `uv sync --extra dev`, then `uv run pytest -m unit -q`. Unit only: no secrets, no network.
- [ ] T041 [US4] Run quickstart §3 by hand in the core worktree (set `fastmcp==3.4.3` in a scratch copy and run the policy test), and record the expected failure output in `specs/015-fastmcp-4-upgrade/evidence/core-3.4.7/policy-selfcheck.md`.
- [ ] T042 [P] [US4] Write `edge:tests/unit/test_framework_version_policy.py` (a copy of T038 and T039 with edge paths; the constants are a local copy per FR-013, with a comment citing ADR-009 v0.1 and the core path), and `edge:.github/workflows/ci.yml` (as T040).
- [ ] T043 [US4] Run quickstart §3 in the edge worktree, and record the result in `specs/015-fastmcp-4-upgrade/evidence/edge-3.4.7.md`.
- [ ] T044 [P] [US4] File a Linear issue (project "Open-Biosciences Platform v1.1 — dogfooding + Synapse alignment"): psychology-mcp adopts ADR-009. It means raising `fastmcp>=2.14.1,<3.0` (locked 2.14.7) to the ADR-009 range, adding the policy test and the tool-surface test, and doing a preview deployment. As part of the same issue, record the interim divergence row in psychology-mcp's `docs/adr/README.md` (ADR-009 section 5a), expiring when this issue closes. Link it to AGE-718.
- [ ] T045 [US4] After both PRs merge and production runs inside the range: move `docs/adr/proposed/adr-009-v0.1.md` to `docs/adr/accepted/adr-009-v1.0.md` with status Accepted, in a core docs PR. The same PR appends edge's production results (T036 step 4) to `specs/015-fastmcp-4-upgrade/evidence/edge-preview.md`. In a separate biosciences-program PR, add an ADR-009 row to the "Where things are" table in `biosciences-program/docs/adr/README.md`. Update edge's ADR-009 row (T034) to "adopted", and change the "ADR-009 v0.1" comments in core's and edge's policy tests to v1.0.

**Checkpoint**: The policy is accepted and enforced in core and edge (SC-006, SC-007).

---

## Phase 7: Polish & Cross-Cutting Concerns

- [ ] T046 [P] Update core `CLAUDE.md` in the core PR:
  - framework versions in the deployment section: state FastMCP 3.4.7, and replace "There is no `fastmcp deploy` or `fastmcp auth` CLI command in FastMCP 2.x" with what 3.4.7's CLI actually offers (check `uv run fastmcp --help`; `fastmcp login`/`whoami` arrived in 4.0, research A). Deployment stays web-UI.
  - a Known Issues entry saying tool descriptions keep only the first docstring section, so return and error guidance goes above `Args:`, enforced by `tests/contract/test_tool_surface.py`
  - a Known Issues entry for the mount usage rule
  - the new test counts from T017
- [ ] T047 Append rows to `docs/speckit-process-record.md`, each in the PR that carries the artifact: `/speckit-tasks` (this file), `/speckit-implement` (core PR, edge PR), and `/speckit-converge` (T048).
- [ ] T048 Run `/speckit-converge` with `SPECIFY_FEATURE_DIRECTORY=specs/015-fastmcp-4-upgrade` after the core PR's code is complete. It appends a Convergence phase to this file. Re-grade any constitution-derived CRITICAL item against accepted-ADR precedence before acting on it (CLAUDE.md, Spec Kit). Converge sees only core's code, so record edge's evidence (T031, T032, T036, T043) by hand in the edge PR.
- [ ] T049 [P] When the core PR opens, link it from AGE-718 and set AGE-718 to In Progress. Its 3.4.7 target and title already match. Link the edge PR when it opens.
- [ ] T050 Clean up per ADR-PRG-001 §3.4 after each merge: remove `.worktrees/implement-015-core`, `edge:.worktrees/implement-015-edge`, and the research scratch worktrees `.worktrees/scratch-015-core` and `_audits/fastmcp-4-2026-09-30/worktrees/edge` (each holds only unpushed research commits), plus the feature worktree `.worktrees/feature-015-fastmcp-4-upgrade` once the spec PR merges. Delete the matching local branches.
- [ ] T051 Set `spec.md` **Status** to Implemented once T045 is done, and close AGE-718.
- [ ] T052 [P] File the 4.x follow-up in Linear (project "Open-Biosciences Platform v1.1 — dogfooding + Synapse alignment", related to AGE-718): "Widen ADR-009 to FastMCP 4.x", gated by spec 015 FR-020. Carry the recorded 4.x work: the `fastmcp.tools.tool` → `fastmcp.tools.base` import in `tests/contract/test_serialization_unit.py`; `PaginationEnvelope[Item].create` at 22 core sites (13 client files) and 2 edge sites (`server.py:56`, `:97`) to clear 4.x serializer warnings; `mcp` 2.x; upstream issue #5213. Also carry the edge `title` annotations that 4.0.10 adds (allowed-changes table note), and rebasing `tests/contract/test_serialization_unit.py` onto 4.x's return-annotation `TypeAdapter` path (version-policy section 2a). Attach research R1, R8, and R13.
- [ ] T053 [P] File Linear issues for the follow-ups this feature triggers (project "Open-Biosciences Platform v1.1 — dogfooding + Synapse alignment", related to AGE-718):
  1. Reconcile ADR-008 with FastMCP's native tool spans, which arrive with 3.4.7. ADR-008 §2(a) and §2(c) name `mcp.tool_call` and `mcp.tool.name`; FastMCP emits `gen_ai.tool.name`; a custom parent span would duplicate the native one. Decide on an amendment or a `propagation_only` posture.
  2. Core recovery hints name unprefixed tools that don't exist on the gateway (research F9). Relate it to AGE-735 so core and edge share one hint policy.
  3. `OmitNoneModel` entities render as empty output schemas (research F10).

  Record the issue IDs in research.md's findings table.

---

## Dependencies & Execution Order

### Phase dependencies

```text
T001 (done) → T002 → T003 → T004 ─┬→ Phase 2 (T006–T007) → US1 (T008–T020) ─┬→ US2 (T021–T027)
                           │                                          └→ US4-core (T037–T041, same PR, after T009)
T003 → T005 ───────────────┴→ US3 (T028–T036) → US4-edge (T042–T043)
US2 + US3 merged → T045 → T051
```

- **US1** depends on Phase 2: T006 must be green on 2.14.5 before T009.
- **US2** depends on US1: the core PR head is what gets deployed.
- **US3** is independent of US1 and US2 in code, since edge has no imports from core. It's sequenced after core in production by plan.md's delivery order, so a Horizon problem shows up first on the larger caller base, with one rollback.
- **US4** tasks split across both PRs. T045 (acceptance) waits for both merges.

### Within the core PR (commit order)

T006 → T008 → T009 → T010 → (T011–T015) → T016 → T017 → T018 → T019 → T037–T041 → T046 → T020 (PR text)

### Within the edge PR (commit order)

T005 (.gitignore) → T028 → T029 → T030 → T031 → T032 → T033 → T034, T035 → T042 → T043 → T036 (preview → core evidence PR → merge)

### Parallel opportunities

- T004 and T005 (different repositories).
- T011 to T015: five disjoint groups of server files. The [P] markers allow five concurrent agents, each taking one group, with T016 as the join.
- T034 and T035 (different edge files); T040 and T042 (different repositories); T044 and T049 (Linear only).

### Parallel example: US1 docstrings

```text
Agent A: T011  servers/hgnc.py, servers/uniprot.py
Agent B: T012  servers/chembl.py, servers/opentargets.py
Agent C: T013  servers/string.py, servers/biogrid.py
Agent D: T014  servers/ensembl.py, servers/entrez.py
Agent E: T015  servers/pubchem.py, servers/wikipathways.py, servers/clinicaltrials.py
Join:    T016  uv run pytest tests/contract/test_tool_surface.py -v
```

Per ADR-005, parallel agents each work in their own worktree on a sub-branch of `implement/015-fastmcp-4-upgrade-core`, and the joins are merged before T016.

---

## Implementation Strategy

### MVP (US1)

Phase 1 → Phase 2 → US1 gives a core branch on FastMCP 3.4.7 that is provably caller-identical locally: names, parameters, description guidance, and wire contract. This is the slice where review effort pays off most. It doesn't ship until US2's preview gate passes.

### Incremental delivery

1. Core PR (US1 plus US4-core) → preview (US2) → Go → production.
2. Edge PR (US3 plus US4-edge) → preview → Go → production.
3. ADR-009 acceptance (T045), then the psychology-mcp follow-up (T044, its own repository).
4. FastMCP 4.x as its own later feature (T052), gated by FR-020.

### Out of scope here (tracked elsewhere)

AGE-733 (edge key leak: fix before or alongside the edge PR, never inside it), AGE-734 (IUPHAR API key), AGE-735 and AGE-736 (edge compliance), AGE-737 (argument-name drift), AGE-738 (deploy-cloud skill), and AGE-698 (ADR-007 base client).
