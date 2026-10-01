# Feature Specification: FastMCP 3.4 Upgrade, Gated Path to 4.x, and Connector Version Policy

**Feature Branch**: `feature/015-fastmcp-4-upgrade`

**Created**: 2026-09-30

**Status**: Draft (amended 2026-10-01)

**Amendment 2026-10-01**: The target changes from FastMCP 4.0.10 to **3.4.7**, by decision of the repository owner (option B). FastMCP 4.x becomes a gated follow-up (FR-020). This restores the decision in `biosciences-program/docs/plans/2026-09-12-interface-version-tradeoff-analysis.md` and AGE-718. The directory and branch keep the `fastmcp-4-upgrade` name for traceability.

**Input**: User description: "Upgrade biosciences-mcp (core, 12 mounted servers + gateway, fastmcp 2.14.5) and biosciences-mcp-edge (2 tools, fastmcp 3.0.2) to FastMCP 4.x while staying deployable on FastMCP Cloud / Prefect Horizon, and record a single FastMCP version policy for connector repos." Amended 2026-10-01: "go with option B" (3.4.7 now, 4.x later).

## Context

Core runs FastMCP 2.14.5, held below 3.0 by a pin added on 2026-02-25 after 3.0.2 double-prefixed every gateway tool name (AGE-182). Edge was created five days later without that pin, resolved 3.0.2, and was later pinned below 3.4.3 because 3.4.3's host validation rejected the hosting platform's requests with HTTP 421. Neither decision was recorded outside a commit message, so the two repositories drifted onto different framework majors. FastMCP 4.0.0 was released 2026-08-31.

The 2026-09-12 interface analysis chose 3.4.7 and declined FastMCP 4 for now. The 3.x line keeps the MCP protocol library on 1.x, and 3.x is the only major already proven on the hosting platform (edge runs 3.0.2 there in production). FastMCP 4 also brings the MCP protocol library 2.x, whose behaviour with the platform's own clients (Claude Code, the claude.ai connector, Claude Desktop) and with biosciences-temporal's client has not been verified. Phase 0 research (2026-09-30) and a client check (2026-10-01) narrowed but did not close that gap (research R13), so this feature upgrades to 3.4.7 and records what a later move to 4.x must prove.

The callers of these servers are AI agents: the LangGraph supervisor (biosciences-deepagents), Temporal agents (biosciences-temporal), and Claude Code plugin users. biosciences-research names the tools in documentation and an evaluation dataset but makes no MCP calls (research D). They bind to tool names, parameter names, and the ADR-001 wire contract. A framework upgrade that changes any of these breaks them without a code change on their side, which makes caller-visible stability the central requirement of this feature.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Agent callers are unaffected by the core upgrade (Priority: P1)

An agent that calls the core gateway today (for example, it searches for a gene, resolves the CURIE, then fetches the record) keeps working unchanged after core moves to FastMCP 3.4.x. It sees the same tool names, sends the same arguments, receives the same envelopes and error codes, and gets the same recovery guidance.

**Why this priority**: Every downstream repository depends on this surface. Without it, the upgrade is a breaking change for the whole platform, and no other story is worth delivering.

**Independent Test**: Capture the complete tool surface and the wire responses for a fixed set of calls on the current release, repeat on the upgraded release, and compare. Run the existing serialisation and wire-contract test tiers on the upgraded release.

**Acceptance Scenarios**:

1. **Given** the gateway's tool list on the current release, **When** the same list is taken on the upgraded release, **Then** the set of tool names is identical (34 tools today, none renamed, added, or removed).
2. **Given** a call that succeeds today with a given set of arguments, **When** the same call is made on the upgraded release, **Then** it is accepted and returns a response of the same envelope shape.
3. **Given** a strict lookup tool called with free text instead of a resolved identifier, **When** the upgraded release handles it, **Then** the caller receives the same `UNRESOLVED_ENTITY` error envelope with a recovery hint, not a framework validation message.
4. **Given** an entity with optional fields that are absent, **When** it is returned on the upgraded release, **Then** absent fields are omitted from the payload exactly as today, not sent as `null`.

---

### User Story 2 - The upgraded core is deployable to the hosting platform (Priority: P2)

The platform operator deploys the upgraded core to FastMCP Cloud / Prefect Horizon, and authenticated clients reach it on its public hostname without requests being rejected. The operator verifies this on a non-production deployment before production changes.

**Why this priority**: A release that passes every local test but is rejected at the hosting boundary delivers nothing. This already happened once (Edge, FastMCP 3.4.3, HTTP 421).

**Independent Test**: Deploy the upgraded release to a separate preview deployment, connect with the standard authenticated client configuration, list tools, and make one call per server.

**Acceptance Scenarios**:

1. **Given** the upgraded release on a preview deployment, **When** an authenticated client connects through the platform's public hostname, **Then** the connection succeeds and no request is rejected for host validation.
2. **Given** the preview deployment is verified, **When** production is updated, **Then** production behaves the same, and the operator can return to the previous release in one revert.

---

### User Story 3 - Edge is upgraded under the same guarantees (Priority: P3)

Edge's two tools (CRISPR screen essentiality, mechanism of action) move to the same framework major as core, with the same caller-visible stability and deployability guarantees, while Edge stays a standalone server with no imports from core.

**Why this priority**: Edge is small and has few callers, but leaving it on a different major is how the drift in the Context section began. It can ship after core.

**Independent Test**: Capture Edge's tool surface and wire responses (success, unresolved free text, upstream failure) before and after, compare, and repeat User Story 2's preview check for Edge.

**Acceptance Scenarios**:

1. **Given** Edge on its current release, **When** it is upgraded, **Then** its tool names, parameters, and response envelopes are unchanged.
2. **Given** free text passed to either Edge tool, **When** the upgraded release handles it, **Then** the response is the same as on 3.0.2. For `get_mechanism`, that is `UNRESOLVED_ENTITY` whose hint names no tool. For `get_orcs_essentiality`, it is a framework validation error, because its parameter is typed `int`. The stronger behaviour, a hint naming an existing core tool, is AGE-735's (FR-014). (Amended 2026-10-01 after the PR #19 review: the earlier wording contradicted the committed 3.0.2 capture.)
3. **Given** the upgraded Edge, **When** its dependencies are inspected, **Then** it still imports nothing from core.

---

### User Story 4 - One framework version policy governs every connector repository (Priority: P4)

A maintainer creating or updating any connector repository (core, Edge, psychology-mcp, or a future one) can find the supported framework version range, the versions known to be broken and why, and how a version change is approved. A repository whose locked version falls outside the policy fails its own checks.

**Why this priority**: It prevents a repeat of the drift but delivers no direct caller value, so it ranks after the upgrade itself.

**Independent Test**: Read the policy and confirm it answers the three questions above with evidence. Change a repository's locked framework version to a known-bad version and confirm its checks fail.

**Acceptance Scenarios**:

1. **Given** the published policy, **When** a maintainer looks up a framework version, **Then** they can tell whether it is supported and, if not, which incident ruled it out.
2. **Given** a connector repository locked to a version outside the policy, **When** its checks run, **Then** they fail with a message naming the policy.
3. **Given** any upper bound on the framework in a repository's dependency declaration, **When** a maintainer reads it, **Then** the reason is stated next to it.

---

### Edge Cases

- A caller sends an argument the tool does not declare. Observed 2026-09-30 on `hgnc_get_gene`: 2.14.5, 3.4.7, and 4.0.10 all reject the call with a framework error (`isError: true`), not an ADR-001 error envelope; only the message text differs between versions. The newer framework's `additionalProperties: false` in the input schema documents this existing behaviour rather than changing it.
- The upgraded framework moves the `Args:` and `Returns:` sections of a tool's docstring out of its description. Information an agent relied on for tool selection could disappear from the description even though the tool itself is unchanged.
- An upstream API (ChEMBL, ClinicalTrials.gov, BioGRID) fails or rate-limits during before/after comparison. Its known instability must not be counted as an upgrade regression.
- The hosting platform rejects requests for its own public hostname because of the framework's host validation (this happened on 3.4.3, HTTP 421). The upgrade must then stop before production. The framework default on 3.4.4 and later leaves host-origin protection off (research R2). Turning it on, or changing how it is configured, is a separate decision that needs its own preview evidence, because the guard reads only the raw `Host` header and Horizon's proxy behaviour is unknown.
- Core and Edge reach the target major at different times. The version policy must say whether a temporary divergence is allowed and for how long.
- A downstream repository pins or caches tool schemas. A schema change that is harmless to live callers could still invalidate a stored copy.
- Telemetry. The only telemetry today is biosciences-otel-stack's `opentelemetry-instrument` wrapper; ADR-008 is not implemented. The wrapper must keep working after the upgrade, or degrade silently when no collector is configured. FastMCP 3.x adds its own tool spans, whose attribute names differ from ADR-008 §2(c). Reconciling the two is a follow-up this feature triggers, not a 4.x one.

## Requirements *(mandatory)*

### Functional Requirements

**Caller-visible stability (core and Edge)**

- **FR-001**: The upgraded servers MUST expose exactly the same set of tool names as the current release.
- **FR-002**: For every tool, the upgraded release MUST keep each parameter's name, required status, accepted types, and defaults unchanged.
- **FR-003**: The upgraded release MUST accept every call the current release accepts, and MUST reject every call the current release rejects. Calls with undeclared arguments are rejected today and must stay rejected; a change in the rejection message text is a caller-visible difference covered by FR-007.
- **FR-004**: The upgraded release MUST return the ADR-001 envelopes (pagination and error) with the same fields, error codes, and recovery hints as today, and MUST omit absent optional fields rather than send `null`.
- **FR-005**: Strict tools given an unresolved identifier MUST continue to return the `UNRESOLVED_ENTITY` error envelope produced by the tool, not a framework-level validation error.
- **FR-006**: Every piece of guidance in a tool's current description and parameter documentation MUST remain available to callers after the upgrade, whether in the tool description or in parameter descriptions.
- **FR-007**: Any caller-visible difference that does remain after FR-001 to FR-006 MUST be listed with its effect on biosciences-deepagents, biosciences-temporal, and Claude Code plugin users before release.

**Deployability**

- **FR-008**: The upgraded core and Edge MUST accept authenticated requests addressed to their hosting-platform hostnames with no host-validation rejections. Host-origin protection MUST stay at the framework default (off on 3.4.4 and later), with no `FASTMCP_HTTP_*` host settings. The servers are reachable only through the hosting platform's authenticated ingress. Enabling the protection requires a preview deployment showing that the platform preserves the public `Host` header (research R2). (Amended 2026-10-01, /speckit-analyze H1: the earlier wording, "without disabling host validation entirely", contradicted the plan's use of the default.)
- **FR-009**: Each upgraded server MUST be verified on a non-production deployment of the hosting platform before its production deployment changes.
- **FR-010**: Each upgrade MUST be reversible to the previous release by reverting a single change.

**Decision gate**

- **FR-011**: The framework version constraint of a repository MUST NOT be raised on its default branch until evidence for FR-001 to FR-008 for that repository is recorded in this feature's artifacts and a go / no-go decision is recorded.
- **FR-012**: Upstream API failures during before/after comparisons MUST be retried once and, if they persist, recorded as upstream failures and excluded from the regression comparison.

**Edge boundaries**

- **FR-013**: Edge MUST remain a standalone server with no imports from core after the upgrade.
- **FR-014**: The upgrade MUST NOT make Edge's existing deviations from core worse (its documented Fuzzy-to-Fact departure, its local envelope copies, any `null` fields it emits today). Bringing Edge's serialisation into line with core is out of scope (see Assumptions).

**Version policy**

- **FR-015**: A single framework version policy MUST be recorded as a platform decision, stating the supported version range, each known-bad version with the incident and commit that ruled it out, the procedure for changing the range, and whether and for how long connector repositories may diverge.
- **FR-016**: The policy MUST apply to core, Edge, and psychology-mcp, and to future connector repositories by default.
- **FR-017**: Core and Edge MUST each fail their automated checks when their locked framework version is outside the policy.
- **FR-018**: Every upper bound on the framework in core's and Edge's dependency declarations MUST state its reason next to it.

**Telemetry**

- **FR-019**: The existing telemetry path, biosciences-otel-stack's `opentelemetry-instrument` wrapper, MUST keep working after the upgrade, including its no-collector degradation. ADR-008 is not implemented today. The reconciliation of its span design with FastMCP's native tool spans, which arrive with 3.4.7, MUST be filed as a follow-up. (Amended 2026-10-01 after the PR #19 review.)

**Path to FastMCP 4.x**

- **FR-020**: The version policy MUST mark FastMCP 4.x as not yet supported, and name the evidence required before its range may include 4.x: a preview deployment of each repository on 4.x passing the same checks as FR-008 and FR-009; the platform's own clients (Claude Code, the claude.ai connector, Claude Desktop) and biosciences-temporal's client completing list and call against that preview; and the research already gathered on 4.x (research R1, R13). This feature does not upgrade to 4.x.

### Key Entities

- **Tool surface**: The complete, caller-visible description of a server's tools: names, descriptions, parameter definitions, output definitions, and annotations. The unit of before/after comparison.
- **Wire response**: The exact payload a caller receives for a tool call, success or error. Compared per error code and per representative call.
- **Version policy**: The platform decision listing supported framework versions, known-bad versions with evidence, and the change procedure. Referenced by every connector repository.
- **Upgrade evidence record**: The per-repository collection of tool-surface comparisons, wire comparisons, test results, and deployment checks that FR-011's gate reads.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of the tools available today (34 on core, 2 on Edge) are available under the same names after the upgrade.
- **SC-002**: Zero calls that succeed on the current release fail on the upgraded release, across the representative call set and the full existing contract test tiers.
- **SC-003**: Zero downstream repositories (biosciences-deepagents, biosciences-temporal) need a code change to keep working after the upgrade.
- **SC-004**: The upgraded core and Edge each serve authenticated clients on a preview deployment with zero host-validation rejections before production is touched.
- **SC-005**: Returning to the previous release takes one revert and under 15 minutes, including redeployment.
- **SC-006**: Core and Edge both enforce the same version policy and run on the same framework major at completion. The policy names psychology-mcp as a consumer (FR-016); psychology-mcp's own adoption is the follow-up in the Assumptions. (Amended 2026-10-01, /speckit-analyze H3.)
- **SC-007**: A deliberate change to a known-bad framework version is caught by automated checks in 100% of attempts on core and Edge.

## Assumptions

- **Target version**: FastMCP 3.4.7, the latest 3.x release (2026-08-10); no 3.x release has shipped since 4.0.0. The plan may select a later 3.4.x patch if one is released before implementation. Both core and edge move to it, so they share a major again (SC-006).
- **Upgrade path**: Core moves directly from 2.14.5 to 3.4.7; edge moves from 3.0.2 to 3.4.7. The move to 4.x is a separate, later feature gated by FR-020.
- **Client support**: Python MCP clients on protocol library 1.26 (what biosciences-deepagents and the tests use) were verified against a 4.0.10 server on 2026-10-01. The platform's own clients were not, which is the main reason for stopping at 3.x (research R13).
- **Prerequisite opened, reviewed, merge pending**: biosciences-mcp PR #18 (`a319044`) removes the gateway mount arguments that double-prefix tool names on 3.x and fail on 4.x. It leaves the tool list on 2.14.5 byte-identical, and the same 34 names were observed on 3.4.7 and 4.0.10. On 2.14.5 it also lets unprefixed tool names reach the last-mounted server until the pin moves (PR #18 review). It was opened before this specification. The plan records it as task T001 (implemented and reviewed), with the merge as T002.
- **Preview deployments**: The hosting platform allows a second, non-production deployment of each server, which this feature uses for FR-009.
- **Edge serialisation**: Edge's models do not use the null-omitting base class core relies on, and Edge has no contract test tier. Fixing that is a separate compliance item; this feature only guarantees no regression (FR-014).
- **psychology-mcp**: The policy covers it (FR-016), but changing its dependency declarations or checks is a follow-up in that repository, not part of this feature.
- **Decision records**: The version policy becomes ADR-009 (ADR-008 is taken).
- **Existing research**: The verified facts and research protocol in `_audits/fastmcp-4-2026-09-30/PROMPT.md` (outside the repository) are inputs to `/speckit-plan`'s Phase 0 research, not a separate deliverable.
