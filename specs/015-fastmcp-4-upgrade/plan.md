# Implementation Plan: FastMCP 3.4 Upgrade, Gated Path to 4.x, and Connector Version Policy

**Branch**: `feature/015-fastmcp-4-upgrade` | **Date**: 2026-09-30, amended 2026-10-01 | **Spec**: [spec.md](spec.md)

**Amendment 2026-10-01**: The target changes from `>=4.0.10,<4.1` to `>=3.4.7,<3.5` (owner decision, option B; spec amendment; research R1, R13). Removed as 4.x-only: the `test_serialization_unit.py` import fix (R7) and the envelope parameterization (R8); both are recorded for the 4.x follow-up. Added: FR-020's 4.x gate in ADR-009.

**Input**: Feature specification from `specs/015-fastmcp-4-upgrade/spec.md`

## Summary

Move core (`biosciences-mcp`, FastMCP 2.14.5) and edge (`biosciences-mcp-edge`, 3.0.2) to FastMCP `>=3.4.7,<3.5`, with no caller-visible change to tool names, parameters, or the ADR-001 wire contract. Then record one framework version policy (ADR-009) that enforces the range in both repositories and names the evidence a later move to 4.x must produce (spec FR-020).

Phase 0 research ([research.md](research.md)) ran the full core and edge test matrices on 2.14.5/3.0.2, 3.4.7, and 4.0.10, and read the framework source. Findings:
- The Host guard behind edge's `<3.4.3` pin has been off by default since 3.4.4.
- All 36 tool names and every parameter are unchanged.
- The wire contract holds.
- On 3.4.7, core's only new failure is one test-only site, and the MCP protocol library stays on 1.x.
- The one substantive caller-visible regression is that FastMCP 3.2.4+ drops `Returns:`, `Examples:`, and `Error Codes:` text from tool descriptions (30 of 34 core tools, both edge tools). Restructuring those docstrings is the main code work.

The Phase 0 gate, re-evaluated for 3.4.7, is **Conditional Go** for both repositories. Final Go comes from a Horizon preview deployment. FastMCP 4 is deferred: Python clients work against a 4.0.10 server, but the platform's own clients and Horizon on 4.x are unverified (research R13).

Delivery order:
- **Core first:** PR #18 (done) → upgrade PR → preview deploy → production.
- **Then edge:** upgrade PR → preview deploy → production.
- **Then the policy:** the ADR-009 proposal, plus the policy test and CI workflow in each repository. These ship with each repository's upgrade PR so the gate is in place before the pins move on `main`.

## Technical Context

**Language/Version**: Python >=3.11 (repo floor). Horizon runs Python 3.12 (research R3, CONFIRMED for 3.0rc1).

**Primary Dependencies**:
- From fastmcp 2.14.5 → 3.4.7. `mcp` stays on 1.x (1.26.0 locked; 3.x requires `<2.0`). The upgrade adds fastmcp-slim and moves starlette 0.52.1 → 1.7.0 (research R1, B).
- Pydantic v2 and httpx are unchanged.

**Storage**: N/A

**Testing**: pytest marker tiers (`unit`, `contract and unit`, `contract and integration`, `integration`, `e2e`). New in this feature:
- a tool-surface contract test against `contracts/tool-surface-baseline-*.json`
- a framework-version policy unit test in each repository
- a minimal CI workflow running `pytest -m unit` in each repository

**Target Platform**: FastMCP Cloud / Prefect Horizon, streamable HTTP. Endpoints are `https://biosciences-mcp.fastmcp.app/mcp` and the edge equivalent.

**Project Type**: MCP server (a library of FastMCP servers plus a gateway); two repositories.

**Performance Goals**: No change expected. The spec sets no latency target, and the upgrade touches no client or rate-limiting code.

**Constraints**:
- Tool names, parameters, and wire contract unchanged (spec FR-001 to FR-005).
- No guidance lost from tool descriptions (FR-006).
- Edge imports nothing from core (FR-013).
- Rollback in one revert, in under 15 minutes (SC-005).

**Scale/Scope**:
- Core: 12 mounted servers, 34 tools, 30 docstrings to restructure across 11 server files, and 1 test fix.
- Edge: 2 tools and 2 docstrings.
- Plus 1 ADR, 2 policy tests, and 2 CI workflows.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

The constitution is v1.1.0, which predates ADR-007 and ADR-008. Its items are graded here as written. Where an accepted ADR is more specific, the ADR takes precedence (CLAUDE.md, Spec Kit section).

| Principle | Pre-research | Post-design | Notes |
|---|---|---|---|
| I. Async-First | PASS | PASS | No client code changes. The httpx async clients are untouched. |
| II. Fuzzy-to-Fact | PASS | PASS | Free text to strict tools still returns `UNRESOLVED_ENTITY` on 3.4.7 and 4.0.10 (R5); the contract tier enforces it. Edge's documented departure is unchanged (FR-014), and its gaps are findings F2. |
| III. Schema Determinism | PASS | PASS | Envelopes and null omission hold on 3.4.7 (R9): contract+unit passes 104/104. |
| IV. Token Budgeting | PASS | PASS | `slim` parameters and page-size defaults are unchanged (R4: every parameter identical). |
| V. Specification-Before-Code | **VIOLATION, justified** | **VIOLATION, justified** | PR #18 was opened before this spec and exceeds the trivial-change exception. See Complexity Tracking. All further code waits for approval of this plan (HUMAN GATE). |
| VI. Platform Skill Delegation | PASS with gap | PASS with gap | No platform skill covers framework upgrades. The constitution's `deploy-cloud` skill for deployments doesn't exist (finding F8), so [quickstart.md](quickstart.md) defines the deployment pre-flight and post-deploy checks it would have provided. |
| Forbidden: hardcoded credentials | PASS for this feature | PASS | Edge leaks the BioGRID key in error messages (F1). It's pre-existing and separate, but needs urgent handling outside this feature. |
| Required: human approval gate | Pending | **Approved** | Plan approved by the repository owner on 2026-09-30, before `/speckit-tasks`. Target amendment to 3.4.7 directed by the owner on 2026-10-01 (option B). The amended plan, with the /speckit-analyze remediation, was approved by the owner on 2026-10-01. |

**Result**: Gates pass, with one justified violation and one documented gap. Plan approved 2026-09-30; amended plan approved 2026-10-01.

## Project Structure

### Documentation (this feature)

```text
specs/015-fastmcp-4-upgrade/
├── spec.md
├── plan.md                 # This file
├── research.md             # Phase 0 decisions, decision gate, out-of-scope findings
├── research/               # Full reports from the four research tracks (A–D)
├── data-model.md           # Phase 1: tool surface, wire response, version policy, evidence record
├── quickstart.md           # Phase 1: validation and preview-deployment runbook
├── contracts/
│   ├── tool-surface-baseline-core.json   # 34 tools: params + 2.14.5 descriptions
│   ├── tool-surface-baseline-edge.json   # 2 tools: params + 3.0.2 descriptions
│   ├── tool-surface-invariants.md        # What may and may not change, and how the test compares
│   └── version-policy.md                 # ADR-009 policy content and the policy-test contract
├── checklists/requirements.md
└── tasks.md                # Phase 2 (/speckit-tasks; not created by this command)
```

### Source Code

```text
biosciences-mcp/                                  # core
├── pyproject.toml, uv.lock                       # fastmcp>=3.4.7,<3.5 with a reason comment (FR-018)
├── src/biosciences_mcp/servers/*.py              # 30 docstrings restructured across 11 server files (R6)
├── tests/integration/test_gateway.py             # get_tools() → list_tools() (R7)
├── tests/contract/test_tool_surface.py           # NEW: names, params, description guidance vs baseline (FR-001/002/006)
├── tests/unit/test_framework_version_policy.py   # NEW: pyproject range + uv.lock vs policy (FR-017)
├── .github/workflows/ci.yml                      # NEW: pytest -m unit on PRs (SC-007)
├── docs/adr/proposed/adr-009-v0.1.md             # NEW: version policy and the 4.x gate (FR-015/016/020)
└── CLAUDE.md                                     # FastMCP version statements, deployment notes

biosciences-mcp-edge/                             # edge (separate repository and PR)
├── pyproject.toml, uv.lock                       # drop <3.4.3; fastmcp>=3.4.7,<3.5 with reason
├── src/biosciences_mcp_edge/server.py            # 2 docstrings (R6)
├── tests/unit/test_framework_version_policy.py   # NEW: local copy of policy values (FR-013, FR-017)
├── tests/unit/test_tool_surface.py               # NEW: in-process surface check vs edge baseline
├── .github/workflows/ci.yml                      # NEW
├── docs/adr/README.md                            # Reference ADR-009
└── CLAUDE.md
```

**Structure Decision**: Two repositories, two upgrade PRs, one spec. Edge's work is in this spec's tasks, but its code ships from its own repository with no imports from core (FR-013). ADR-009 lives in core, under the platform-ADR placement rule in `biosciences-program/docs/adr/README.md`.

## Phase 0 decision gate (from research.md)

| Outcome | Core | Edge |
|---|---|---|
| **Conditional Go** | ✅ | ✅ |
| Condition for final Go | Preview deployment on 3.4.7 passes the quickstart checks, including Host, 34 tools, one call per server, and deepagents' sessionless `tools/call` (R12) | Local capture at 3.4.7 matches the 3.0.2 baseline (T030); the preview passes Host, 2 tools, and both calls |
| What would make it No-Go | Horizon rejects the public `Host`, or Horizon runs with sessions in a way deepagents can't use and that can't be configured | Horizon rejects the public `Host` |

## Delivery sequence and rollback

1. **Done:** PR #18, the gateway mounts use `tool_names` only. It's safe on 2.14.5 and doesn't depend on the rest of the feature.
2. **Core upgrade PR (implement branch):** these land together, since the pin change without them breaks the tests:
   - the pin and lock change
   - the R7 test fix
   - the R6 docstring restructuring
   - the tool-surface contract test
   - the policy test and CI workflow
   - ADR-009 as proposed
   - CLAUDE.md updates
3. **Core preview deployment:** run quickstart §4, record the results in the evidence record, then make the go/no-go decision (FR-011).
4. **Core production:** merge, then redeploy. Rollback is a revert of the upgrade PR's merge commit plus a redeploy. Time it during the preview to check SC-005.
5. **Edge upgrade PR,** then preview, then production, following the same pattern.
6. **ADR-009 acceptance:** move it to `accepted/` once both repositories run inside the policy. File the psychology-mcp follow-up issue.
7. **4.x follow-up:** file a Linear issue for a later feature that moves the range to 4.x, gated by FR-020. It carries the deferred R7 import fix and the R8 envelope parameterization.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Principle V: PR #18 (`a319044`, 28 lines in `servers/gateway.py`) was opened before this spec existed. It exceeds the "<3 lines, single-file, obvious fix" exception. | It was the prerequisite that made the research possible: without it, the gateway fails at import on 4.x and double-prefixes names on 3.x, so no 3.x/4.x tool-surface or test evidence could be collected. Its effect is zero caller-visible change on the deployed version: the 2.14.5 tool surface is byte-identical before and after (34 tools; names, descriptions, schemas, annotations). It was verified on 2.14.5, 3.4.7, and 4.0.10. | Converting it to draft until plan approval adds churn without lowering risk: the change is already verified and has no effect on 2.14.5. Folding it into the upgrade PR would hide a separately verifiable fix inside a large change, and it would re-break research reproducibility from `main`. **Waiver**: recorded here and in `docs/speckit-process-record.md`. PR #18 becomes task T001 in `tasks.md`, marked complete. |
