# Phase 0 Research: FastMCP 4 Upgrade and Connector Version Policy

**Feature**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md) | **Date**: 2026-09-30

Four research tracks ran in parallel on 2026-09-30, each in a scratch environment: no primary checkout was modified and nothing was pushed. Their full reports are in [`research/`](research/):

| Track | Report | Ran against |
|---|---|---|
| A. Framework source, Host guard, 4.0 breaking changes | [A-framework-host-guard.md](research/A-framework-host-guard.md) | fastmcp 3.4.2, 3.4.3, 3.4.7, 4.0.10 source; PrefectHQ/fastmcp issues and upgrade guides |
| B. Core test matrix and tool surface | [B-core-sandbox.md](research/B-core-sandbox.md) | Core at `a319044` (PR #18 head) on 2.14.5, 3.4.7, 4.0.10 |
| C. Edge test matrix, wire capture, parity | [C-edge-sandbox.md](research/C-edge-sandbox.md) | Edge at `91f6bab` on 3.0.2 and 4.0.10 (Host probe also on 3.4.3 and 3.4.7) |
| D. Downstream callers, CI, deployment docs | [D-downstream-and-policy.md](research/D-downstream-and-policy.md) | Every workspace repo, read-only |

Raw logs, JSON captures, and probe scripts stay outside the repository in `_audits/fastmcp-4-2026-09-30/research/`. The two compact baselines needed for implementation are committed under [`contracts/`](contracts/).

The input protocol was `_audits/fastmcp-4-2026-09-30/PROMPT.md`. Two of its premises turned out wrong, and are corrected here: the Host guard is not a blocker (R2), and the 3.x/4.x schema change to undeclared arguments does not change behaviour (R5).

Labels: **CONFIRMED** means observed in a run or read in source or docs. **INFERRED** means reasoned from evidence without direct observation.

---

## R1. Upgrade path for core: direct 2.14.5 → 4.0.10

- **Decision**: Upgrade core directly to `fastmcp>=4.0.10,<4.1`. Do not ship an intermediate 3.x release.
- **Rationale**: CONFIRMED (B):
  - The 3.4.7 and 4.0.10 tool surfaces are byte-identical. A 3.x release would expose callers to the same description and schema changes as 4.x, with no separate benefit.
  - Every new failure at either version has a known, test-only fix (R7).
  - 3.4.7 (2026-08-10) is the latest 3.x release; there have been no 3.x releases since 4.0.0 on 2026-08-31 (CONFIRMED, PyPI).
- **Alternatives considered**:
  - 2→3→4 in two releases: rejected. It doubles deployment and verification work for an identical caller-visible result.
  - Stay on 2.x: rejected. Core and edge stay split across framework majors, which is the problem the spec exists to fix.

## R2. Host guard: not a blocker; set nothing; guard against it coming back

- **Decision**:
  - Deploy with the framework defaults: host-origin protection off. Set none of the host variables.
  - Bound core and edge to `<4.1`.
  - Add a post-deploy check that sends a request with the public hostname as `Host` and expects success.
  - Remove edge's `<3.4.3` bound, which is now obsolete.
- **Rationale**:
  - CONFIRMED (A): the 421 came from FastMCP's own `HostOriginGuardMiddleware`, added in 3.4.3 (PR #4405). It was on by default and allowed only loopback hosts. 3.4.4 turned the default off (PRs #4439, #4472), and 4.0 kept it off (PR #4474).
  - CONFIRMED (B, C): with defaults, local servers on 3.4.7 and 4.0.10 return 200 for `Host: biosciences-mcp.fastmcp.app` and `Host: biosciences-mcp-edge.fastmcp.app`. 3.4.3, as a control, returns 421.
  - CONFIRMED (A): the controls are `FASTMCP_HTTP_HOST_ORIGIN_PROTECTION`, `FASTMCP_HTTP_ALLOWED_HOSTS`, `FASTMCP_HTTP_ALLOWED_ORIGINS`, and the matching `run()`/`http_app()` keyword arguments. There is no constructor argument and no `fastmcp.json` field. Setting `ALLOWED_HOSTS` alone does nothing. `fastmcp.json` `deployment.env` cannot set these, because settings load at import. The `auto` mode returns 421 on loopback sockets. When the guard is on, it reads only the raw `Host` header (no `X-Forwarded-Host`, issue #4468).
  - INFERRED (A): open issue #5213 proposes turning the guard back on by default. A `<4.1` bound and the post-deploy Host check protect against that.
- **Alternatives considered**:
  - Turn the guard on with an explicit allow-list: rejected for now. Whether Horizon's proxy rewrites `Host` is unknown, and the guard ignores forwarded headers, so it could reintroduce the 421.
  - Keep edge's `<3.4.3` bound: rejected. It blocks the upgrade for a cause that no longer exists.

## R3. Hosting platform support for FastMCP 4

- **Decision**: Treat Horizon support as likely but unverified. The preview deployment (FR-009) is the gate.
- **Rationale**:
  - INFERRED, strong (A): there is no published version matrix. Horizon installs the repository's own `fastmcp` version on Python 3.12 (issue #3184, CONFIRMED for 3.0rc1). The 4.x docs describe Horizon without version caveats, 4.0 adds `fastmcp login`/`whoami` for Horizon, and no issue reports 4.x or 421 failures there.
  - CONFIRMED (D): no document in the workspace names Horizon's Python or FastMCP version. The program docs list it as an open question.
  - CONFIRMED (D, from the edge pin commit and repo docs): Horizon resolves from `pyproject.toml`, and versions can float on redeploy. So the dependency range, not only the lockfile, determines what runs (see R10).
- **Alternatives considered**: none. This can only be settled by deploying.

## R4. Tool names and parameters: unchanged

- **Decision**: No caller-visible name or parameter changes are expected. A committed baseline enforces this.
- **Rationale**: CONFIRMED (B, C):
  - All 34 core names and both edge names are identical on 4.0.10.
  - For every tool, parameter names, required flags, types, and defaults are identical to the baseline (checked field by field on 2026-09-30).
  - The gateway naming fix that makes this hold is PR #18 (`a319044`).
- **Alternatives considered**: none needed.

## R5. Argument validation behaviour: unchanged, except message text through the gateway

- **Decision**: Accept the behaviour as is. List the changed message text as a caller-visible difference under FR-007.
- **Rationale**: CONFIRMED (A, B):
  - Validation errors are a `CallToolResult` with `isError=true` on 2.14.5, 3.4.7, and 4.0.10, over HTTP and in memory.
  - Undeclared arguments were already rejected on 2.14.5, so `additionalProperties: false` only documents existing behaviour.
  - Free text passed to a strict tool still returns `UNRESOLVED_ENTITY` with `isError=false`.
  - From 3.x, missing or undeclared arguments sent through the gateway get FastMCP's text (for example `Missing required argument(s): hgnc_id`) instead of Pydantic's. This comes from the `tool_names` mount; a server called directly still gives the Pydantic text.
  - CONFIRMED (D): no downstream repository parses these messages.
- **Alternatives considered**: wrapping validation errors in the ADR-001 error envelope. Rejected for this feature: it would be a deliberate contract change, not a stability guarantee.

## R6. Tool descriptions lose return and error guidance (FR-006)

- **Decision**:
  - Restructure each affected tool docstring so the guidance callers need sits in the leading prose section, which is the only part 3.2.4+ keeps in the description. That guidance is what the tool returns, its error codes, and its examples.
  - Leave `Args:` sections as they are; they now become per-parameter descriptions.
  - Add a contract test that compares each tool's 4.x description and parameter descriptions with the committed 2.14.5 description baseline.
- **Rationale**:
  - CONFIRMED (A): since 3.2.4 (PR #3872), the description keeps only the first text section. `Args:` moves into parameter descriptions. `Returns:` is dropped entirely; it does not move to the output schema.
  - CONFIRMED (B): for 30 of 34 core tools, `Returns:`, `Examples:`, `Error Codes:`, and response-shape blocks disappear from the surface. Parameter descriptions grow from 11 to 104, and no `Args:` information is lost. The 4 IUPHAR tools, which have no `Args:` section, keep their full docstring.
  - CONFIRMED (C): both edge tools lose `Returns:` and gain auto-generated titles.
  - CONFIRMED (D): no downstream code asserts on descriptions, but live LLM callers (Claude Code plugins, PydanticAI in temporal) read them to choose and call tools.
- **Alternatives considered**:
  - An explicit `description=` on each `@mcp.tool`: rejected. It duplicates every docstring and the two copies would drift.
  - Accept the loss: rejected by FR-006.
  - Keep a pre-3.2.4 parser: there is no such option in 4.x (A).

## R7. Breaks in core's own tests: test-only, two sites

- **Decision**: Fix both in the upgrade change:
  - `tests/integration/test_gateway.py` uses `mcp.get_tools()`, which was removed in 3.x; switch to `list_tools()`.
  - `tests/contract/test_serialization_unit.py` imports `fastmcp.tools.tool`, which doesn't exist in 4.x; switch to the 4.x module.
- **Rationale**: CONFIRMED (B):
  - On 4.0.10 the import error aborts the unit, contract+unit, and network contract tiers with exit 2.
  - With the import aliased in a scratch-only plugin: 562/562 unit and 104/104 contract+unit pass, and the network contract tier shows the same 11 failures as on 2.14.5.
  - Those 11 baseline failures are Ensembl upstream 500s and IUPHAR 401s, identical at every version, so they are not regressions.
- **Alternatives considered**: none.

## R8. Pydantic serializer warnings on 4.x

- **Decision**: Build envelopes with the parameterized type (`PaginationEnvelope[Item].create(...)`) wherever a tool returns `PaginationEnvelope[...] | ErrorEnvelope`: 21 sites in core and 2 in edge.
- **Rationale**: CONFIRMED (B, C): on 4.0.10, successful calls log Pydantic serializer warnings. The output is correct and null omission still holds, but the warnings flood logs and could hide real ones.
- **Alternatives considered**: filtering the warnings. Rejected, because it would also suppress the useful ones.

## R9. Null omission and the wire contract

- **Decision**: No change needed in core. Edge's existing `null` output stays out of scope (FR-014).
- **Rationale**:
  - CONFIRMED (B): contract+unit (104) passes on 4.0.10, and null omission holds. The output schema changes are only `$defs`/`$ref` inlining.
  - CONFIRMED (C): all 9 edge wire captures are byte-identical between 3.0.2 and 4.0.10, including the `null` fields edge already emits.
- **Alternatives considered**: fixing edge's nulls in this feature. Rejected, because it mixes framework migration with compliance work; it goes into the separate findings list below.

## R10. Version policy: ADR-009 plus a test and CI in each repository

- **Decision**:
  - Record the policy as a new platform ADR-009, "Connector framework version baseline". Draft it at `docs/adr/proposed/adr-009-v0.1.md`, and move it to `accepted/` on approval. It is not an amendment to ADR-004, which covers lifecycle.
  - Enforce the policy in core and edge with a no-network `unit` test. The test checks both the `pyproject.toml` range and the `uv.lock` version against the policy's supported range and known-bad list.
  - Add a minimal CI workflow that runs `pytest -m unit` in each repository. Neither has a test CI today.
- **Rationale**:
  - CONFIRMED (D): only psychology-mcp runs tests in CI. Core has only the Claude review workflows, and edge has no `.github/`. A policy test that nobody runs would not meet SC-007.
  - CONFIRMED (D): Horizon installs from the dependency range (R3), so checking only the lockfile is not enough.
  - CONFIRMED (D): the platform-skills scaffolds write no `pyproject.toml`, so there is no scaffold to fix.
  - Edge must not import core (FR-013), so each repository's test carries its own copy of the policy values. ADR-009's change procedure requires updating every listed consumer in the same change window.
- **Alternatives considered**:
  - A shared machine-readable policy fetched at test time: rejected, because unit tests must not use the network.
  - A shared package: rejected under edge's no-import decision.
  - Renovate-style automation: deferred. It manages bumps but doesn't express known-bad versions with reasons.

## R11. Telemetry (FR-019)

- **Decision**: The only telemetry today is biosciences-otel-stack wrapping the server in `opentelemetry-instrument`. Verify that wrapper still starts and emits on 4.0.10. Reconciling ADR-008 with FastMCP 4's native telemetry is a follow-up for ADR-008.
- **Rationale**:
  - CONFIRMED (D): ADR-008 is not implemented anywhere: no `trace_tool`, no `telemetry/`.
  - CONFIRMED (A, D): FastMCP 4 has its own tool spans, trace propagation, and a `telemetry_mode` setting, which overlap ADR-008's design.
- **Alternatives considered**: implementing ADR-008 inside this feature. Rejected as scope creep.

## R12. Downstream exposure and the sessionless caller

- **Decision**:
  - The callers that matter are deepagents (34 alias wrappers in `apps/api/shared/mcp.py:224-467`) and temporal (agent prompts, plus it runs core's gateway from the sibling checkout).
  - Add a check to the preview deployment that deepagents' raw sessionless `tools/call` still works.
  - Correct the spec: biosciences-research makes no MCP calls.
- **Rationale**:
  - CONFIRMED (D): deepagents sends JSON-RPC `tools/call` with no `initialize` and no session header (`mcp.py:69-143`). That works only if the hosted server runs stateless, which is a Horizon setting, not a FastMCP version property. A session-keeping server returns "400 Missing session ID" in both mcp 1.x and 2.2.0.
  - CONFIRMED (D): FastMCP 4.0.10 still sends the text content block that deepagents parses (`tools/base.py:415-429`).
  - CONFIRMED (D): protocol negotiation is compatible. mcp 2.2.0 accepts 2024-11-05 through 2025-11-25, and downstream clients use mcp 1.26.
  - CONFIRMED (D): temporal runs `uv run fastmcp run gateway.py` inside the sibling core checkout (`agents/base.py:42,61,83-86`), so it picks up core's lock as soon as that checkout moves.
- **Alternatives considered**: none.

---

## Phase 0 decision gate

The highest achievable outcome without a live deployment is **Conditional Go** (`PROMPT.md`). The outcomes are Conditional Go, Undetermined, and No-Go.

| Criterion | Core | Edge |
|---|---|---|
| Host guard configurable, setting confirmed in source | Yes: off by default since 3.4.4; controls named in R2 | Yes: same |
| Tool names unchanged | Yes: 34/34 (R4) | Yes: 2/2 |
| Parameters unchanged | Yes (R4) | Yes |
| Wire contract unchanged | Yes: contract+unit passes; network failures identical to baseline (R7, R9) | Yes: 9/9 captures identical (R9) |
| Every new failure maps to a known fix | Yes: 2 test-only sites (R7) | Yes: none found |
| Caller-visible differences with a fix path | Descriptions (R6), gateway validation text (R5) | Descriptions (R6), titles added |
| Unverified | Horizon runtime on 4.x (R3), sessionless calls (R12), Host on Horizon (R2) | Horizon runtime (R3), Host on Horizon (R2) |

- **Core: Conditional Go.** Final Go depends on the preview deployment checks in [quickstart.md](quickstart.md).
- **Edge: Conditional Go.** Same condition.

---

## Findings outside this feature's scope

These were found during research. They are not upgrade regressions, and FR-014 keeps edge's own deviations out of this feature. Each needs its own issue.

| # | Finding | Repo | Severity | Evidence |
|---|---|---|---|---|
| F1 | Any ORCS HTTP error other than 429 returns the full request URL to the agent, including `accesskey=<BIOGRID_API_KEY>` | edge | **High (credential exposure)** | C §6: `server.py:44` with `biogrid_orcs.py:55-60`. Reproduced with a fake key. Present on 3.0.2 and 4.0.10. |
| F2 | `get_orcs_essentiality` with free text returns a raw validation error, not `UNRESOLVED_ENTITY` (the parameter is typed `int`). The `get_mechanism` hint names no tool. `invalid_input` holds exception text. A missing key is reported as `UNRESOLVED_ENTITY`. | edge | Medium (contradicts edge's ADR README) | C §4 |
| F3 | Error envelopes carry `invalid_input: null`, item fields are sent as `null` (1,409 in one ORCS response), and ORCS returns all 352 screens while reporting `page_size: 50` | edge | Medium (ADR-001 §4, §7) | C §3, §6 |
| F4 | Edge opens an HTTP client per call with no retry or backoff. Core's base client also lacks the ADR-007 retry logic (9 per-client copies remain). | edge, core | Medium (ADR-007) | C §6 |
| F5 | Argument names already wrong in 4 mirrored skill trees and in deepagents docstrings (`gene_id`, `ligand_id`, `cid`, `species`, `organism`, `ensembl_id` for `opentargets_get_associations`) | skills, deepagents | Medium (callers send rejected calls today) | D §1 |
| F6 | IUPHAR returns 401 on every call in the network contract tier | core | Medium (one server unusable live, if this reflects production) | B, baseline logs |
| F7 | The committed edge `uv.lock` at `91f6bab` no longer matched the `<3.4.3` range in `pyproject.toml` | edge | Low | C §10 |
| F8 | Constitution principle VI names a `deploy-cloud` skill, but none exists in platform-skills or the marketplace | program | Low | plan.md Constitution Check |
