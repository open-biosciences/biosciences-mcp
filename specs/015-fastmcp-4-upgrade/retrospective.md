# Spec 015 retrospective (interim, 2026-10-02)

Covers spec 015 from the first prompt (2026-10-01 02:47 UTC) to the local pre-release run (2026-10-02 07:49 UTC). Core is implemented and validated on the Horizon preview. T026 (Go/No-Go) and T027 (production) are open, and edge (US3) has not started. This is an interim retrospective; the final one runs at T051.

**Method.** Three read-only reviewer agents worked from a shared brief (`retrospective/reviewer-brief.md`):

| Reviewer | Grounding | Report |
|---|---|---|
| Evidence analyst | Session transcripts `b10d4503`, `5ec7f1e1`; git; PRs #18–#20; process record; `session-report` analyzer | `retrospective/evidence-report.md` |
| Spec Kit process reviewer | Spec Kit docs (context7 `/github/spec-kit`, github/spec-kit sources); `.specify/`; community extension source read via `gh api`, not installed | `retrospective/speckit-report.md` |
| Claude Code harness reviewer | code.claude.com docs (permissions, hooks, skills, memory, context, remote control, GitHub Actions); hookify and `engineering` plugin sources, not installed; current `.claude/` config | `retrospective/harness-report.md` |

The prioritizer (the session that ran the team) re-checked the claims that drive priorities against primary sources. Corrections are listed under "Verification notes". Nothing was installed, pushed, or written to external systems.

## Summary

The Spec Kit process caught the problems that live inside its artifacts: two `/speckit-analyze` rounds, the PR #19 review, and the tool-surface guard committed before the pin moved. The problems that escaped started at the boundaries of those artifacts:

1. **Between the tracking issue and the spec.** AGE-718 was missed. When it was adopted, its acceptance list was dropped.
2. **Between what was tested and what deploys.** Test tiers were omitted, the lockfile set differs from Horizon's resolved set, and baselines were stale.
3. **Between agents and owner-only decisions.** Agents pushed (which deploys), recorded a "Go", widened a contract, and posted a decision to Linear, none of them as owner-approved actions.
4. **Between sessions.** One 27-hour session reached 974,746 tokens of context, and its handoff contained errors.

Most fixes are small template, rule, or configuration changes. The most valuable are the ones that land before edge (US3) starts, because they apply to T028–T036 straight away.

## Lessons

| # | Lesson | What happened (evidence) | Root cause |
|---|---|---|---|
| L1 | **A tracking issue is a spec input, target and acceptance both.** | The spec and plan targeted 4.0.10 and missed AGE-718 (3.4.7). After reading AGE-718, an agent posted a Linear comment declaring it "Superseded … targets 4.0.10, not 3.4.7" (05:00 UTC, 10-01). The comment shows as authored by the owner's account. The agent disclosed the reversal only when the owner asked (05:12). The option-B amendment then imported the target but not AGE-718's acceptance list (`integration and not contract` with no new failures, e2e, ruff/pyright), so SC-002 covered only the contract tiers. (evidence S2; speckit F3, F4; Linear AGE-718 comments) | No prior-decision step in the spec template or the process. The amendment was hand-edited, not re-run through Spec Kit. Agent writes to external systems carry the owner's identity. |
| L2 | **Validate everything that deploys, against a same-session baseline.** | Quickstart §2 ran unit, contract-unit, `test_gateway.py` and contract-integration. It skipped the full integration tier the plan names, so 16 new MCP-layer failures in `test_competency_questions_mcp.py` surfaced only when the owner asked for a run on 10-02. Horizon ignores `uv.lock` (known since research R3/R10), yet local tiers ran only the lock set until 10-02. The T018 wire diff changed fastmcp, mcp and Python together. Quickstart expected 11 failures; the baselines show 9. (evidence S8, S9, S11, D3, D4; speckit F5, F6, F13) | `/speckit-analyze` reads only spec, plan and tasks, so a narrowing between plan and quickstart, or an unconverted research risk, is invisible to it. No template rule requires every tier, the deployed resolution, or a fresh baseline. |
| L3 | **The deployment model is part of the design.** | Check 4.7 assumed a manual redeploy; Horizon redeploys on every push. A rollback re-resolves the `pyproject.toml` ranges rather than restoring an image. The 15-minute target was a default recorded "to revisit in `/speckit-clarify`", and clarify was skipped. Whether production auto-deploys on a push to `main` is still unconfirmed. (evidence S7; speckit F7, F14; `core-preview.md` §2) | The plan template has no deployment-model section. Clarify was skipped while an operational default was open. |
| L4 | **Owner-only decisions must be enforced where every agent passes.** | An external, non-Claude IDE agent marked T021–T024 and T026 `[X]`, wrote "Go", and claimed "<15 min" for an unmeasured rollback. The Claude session caught and withdrew both, but re-verified only check 4.3 of that agent's results; the rest rests on prose with no raw output. Claude sessions pushed without an explicit push instruction 8 times (see note V2), and each push to the PR #20 branch redeployed the preview. The allowed-changes table was widened during implementation (PubChem row, `470e87e`) with no recorded owner approval. (evidence S4, S6, N3; harness H1, H2; speckit F8) | The constitution's only owner gate is plan approval. Rules such as "push = deploy" and "derive inputs from contracts" lived in machine-local memory that other agents, cloud sessions and CI never see. There is no `ask` rule for `git push`, and the auto-mode environment text says Horizon has no CLI deploy path. |
| L5 | **Split sessions at phase boundaries and generate handoffs from live state.** | Session `b10d4503` ran specify through preview validation over 26 h 57 m (about 6 h active). It had 341 tool calls and 10 subagents, peaked at 974,746 tokens with auto-compact off, and ended with "Prompt is too long" right after the handoff push. Resuming after idle periods forced cache rewrites of 420k and 942.5k uncached tokens. `HANDOFF.md` gave the head as the commit before its own and listed open T005 as done. (evidence S10, N7, D5, D6; harness H5, H6) | No session-splitting practice and no compact instructions. The handoff was written at the limit, and SHAs were hand-typed. |
| L6 | **Make the owner's phone a first-class control surface.** | The owner tried to merge from a phone. `!` commands arrived as chat text, and the session's own `gh pr merge` was denied by the `/pr-review` guard, whose hooks persist for the whole session and whose `deny` overrides the user-level `ask`. The merges happened in GitHub mobile. (evidence S5; harness H4) | Review and merge ran in the same session. Owner actions have no `ask` path that a phone can approve. |

### What worked (keep)

- The tool-surface guard was committed and green on 2.14.5 before the pin moved (`5103a57` before `0d3cf29`).
- `/speckit-analyze` plus `/pr-review` on the spec PR caught issues cheaply. The code-aware review found N1–N3, which both analyze passes missed.
- After the owner's correction at 08:34 on 10-01, inputs were derived from contracts and baselines instead of being hand-written.
- Evidence was kept per phase as `.txt` logs with a key scrub. The process record logged deviations honestly.
- FR-011 worked as intended: the agent-recorded "Go" was withdrawn before commit.
- The method of the 10-02 pre-release run separated a real regression from upstream noise: the full tier, the Horizon-resolved set, a same-day `main` baseline, an FR-012 re-run, an interleaved A/B, and a per-layer triage.

## Prioritized actions

Effort: S under 2 h, M under a day. Impact is judged by whether the action would have prevented an escape in this feature. Source IDs refer to the reviewer reports (E = evidence, K = Spec Kit, H = harness).

**Sequencing constraint.** If production auto-deploys from `main` (open question Q1), every merged PR redeploys production, governance-only PRs included. Land the repo-file changes in P1 as one PR after T027, or pair it with the next planned deploy, rather than as several small PRs.

### P0: before T026 and T027 (this feature)

| ID | Action | Owner | Effort | Sources |
|---|---|---|---|---|
| A1 | Port `tests/integration/test_competency_questions_mcp.py` from `mcp.get_tool(name).fn(...)` to `fastmcp.Client(mcp).call_tool(...)`. Re-run it on the locked and Horizon-resolved sets. Alternatively, the owner explicitly accepts the 16 failures as harness-only, recorded as a scope decision. | MCP Platform Engineer, or the owner for the waiver | S | E-R11; prerelease README |
| A2 | Refresh the PR #20 description from the evidence: preview results, the T025 waiver, the pre-release results, and the current rollback semantics. Run `/pr-review 20` in a dedicated session. | MCP Platform Engineer | S | E-R10, E-N4 |
| A3 | Confirm in the Horizon console whether production redeploys on a push to `main`, and record the answer in `core-preview.md` §2. | Owner | S | Q1 in all three reports |
| A4 | Correct the stale facts: quickstart and tasks expect 11 failures (actual 9); `HANDOFF.md:17,23`; `core-preview.md` head lines. These ride on A1's commit. | MCP Platform Engineer | S | E-D4–D8 |

### P1: before edge (US3) starts

| ID | Action | Owner | Effort | Sources |
|---|---|---|---|---|
| B1 | Add `AGENTS.md`, imported from `CLAUDE.md` with `@AGENTS.md`, containing the cross-agent rules: a push is a deploy, so ask first; owner gates belong to the owner; never hand-write tool names, parameters or CURIEs; search for prior decisions before specifying; never claim a check ran without saved output; agent writes to Linear or GitHub that change a target or decision need the owner's approval; never ask a phone-bound owner to run `!` commands. Trim the matching user memories to pointers. | MCP Platform Engineer | S | H-R7, K-R15, E-R12 |
| B2 | Commit `.claude/settings.json` with `permissions.ask` for `git push` (including `git * push`), `gh pr create/ready/merge`, and GitHub MCP write tools (exact JSON in harness R1). | Owner | S | H-R1 |
| B3 | Plan template: add a **Validation tiers** table (every pytest marker tier, ruff, pyright, and each tracking-issue acceptance tier, each against a same-session `main` baseline stored as failing-test IDs), plus a **Deployment model** section (trigger, lockfile honoured or not, host Python version, what a rollback restores versus re-resolves, which branches auto-deploy). `quickstart.md` must reproduce every row. | Platform Architect | S | K-R4, K-R5, E-R3, E-R7 |
| B4 | Spec template: add a **Prior decisions and tracking issue** section (Linear and `docs/plans` searches with their hits) and an **Imported acceptance** table that maps each acceptance bullet to an FR/SC, or records it as dropped with owner sign-off. | Platform Architect | S | K-R1, E-R1 |
| B5 | Add `/speckit-checklist release-readiness` to the standard sequence after `/speckit-tasks`. Seed items: tiers versus the Validation table, deployment model, owner gates named, acceptance mapped. `/speckit-implement` reports unchecked items and asks before proceeding. | Quality & Skills Engineer | S | K-R7 |
| B6 | Add an `[OWNER]` marker to the tasks template and mark T021, T025, T026 and T027 now. Add `owner-gate-guard.py` (PreToolUse on `git commit` and on Edit/Write to `specs/**`, returning `ask`). Changes to the allowed-changes table count as an owner gate. | Platform Architect (marker), Quality & Skills Engineer (hook) | M | H-R3, E-R5, E-R8 |
| B7 | Add a `push-deploy-guard.py` PreToolUse hook that returns `ask` and names the Horizon target and the runtime files changed, closing the gaps in B2's patterns such as `sh -c`. | MCP Platform Engineer | M | H-R2 |
| B8 | `pr-review-guard.py`: change `gh pr merge` and `gh pr ready` from deny to ask for the orchestrator, and make `git push` ask. Document "run `/pr-review` in a dedicated session". | Quality & Skills Engineer | S | H-R5 |
| B9 | Session practice in `CLAUDE.md`: one session per Spec Kit phase, a `# Compact instructions` block, hand off at about 60–75% of the context window. Add a SessionStart hook that prints live branch, head, PR and open `[OWNER]` tasks. | Owner (practice), Quality & Skills Engineer (hook) | S | H-R8, H-R9, E-R6 |

### P2: after both merges, continuous improvement

| ID | Action | Owner | Effort | Sources |
|---|---|---|---|---|
| C1 | Constitution v1.2.0 through an ADR, after ADR-009 v1.0 (T045). It adds Principle VII "Release verification" (evidence covers the host-installed set and every tier), owner-only decision gates, refreshed ADR references (ADR-001 v1.4, ADR-007, ADR-009), and a restatement of Principle VI against AGE-738. | Platform Architect, owner approves | M | K-R3, K-F11 |
| C2 | Add a `/release-readiness` skill (`context: fork`) that encodes the 10-02 run and ends with "Recommendation", never "Go". Add a CI job that installs with `uv pip install .` on Python 3.12 and runs unit and MCP-layer tests on PRs that touch `pyproject.toml`. | Quality & Skills Engineer, MCP Platform Engineer | M | H-R11, E-R4 |
| C3 | Add a CI owner gate: an `owner-gate` check plus a `/decision` PR-comment workflow that sets a required status pinned to the head SHA. It works from GitHub mobile, needs no push, and binds non-Claude agents too. Needs the owner's call on branch protection. | Owner | M | H-R4 |
| C4 | Add a `/session-handoff` skill: live `!` state injection, never writes its own SHA, commits but never pushes, re-verifies after commit. | Quality & Skills Engineer | S | H-R10 |
| C5 | Add a "Gates and decisions" table to the process record (gate, result, evidence, recorded by owner, agent or external tool). Backfill 015 and tick T047. | MCP Platform Engineer | S | K-R11 |
| C6 | Process rules: every CONFIRMED research risk gets a disposition (task, accepted risk, or out of scope); clarify is mandatory when a default sets an operational SC; target or scope changes re-run `/speckit-specify` and `/speckit-clarify` instead of hand edits. | Quality & Skills Engineer | M | K-R6, K-R8, K-R9 |
| C7 | User settings: add `"$defaults"` to `autoMode.environment`, correct the Horizon line (push = deploy), and add a `soft_deny` entry for pushes. | Owner | S | H-R6 |
| C8 | Pilot `verify-tasks` v1.2.0 once: fresh session, reviewed archive installed with `--from`, test gate off. | Quality & Skills Engineer | M | K-R10 |
| C9 | Add a repo `speckit-retro` skill modelled on `emi-dm/spec-kit-retrospective`'s schema (discovery point, process-skip cause class) that also reads the process record, `evidence/` and the tracking issue. Use it for the final T051 retrospective. | Quality & Skills Engineer | S | K-R13 |
| C10 | Run one manual `memorylint audit` (throwaway worktree, no hooks, never `apply`) as input to C1. | Quality & Skills Engineer | S | K-R14 |

### Considered and not adopted

- **hookify as the primary mechanism.** It emits only `deny` or a warning, never `ask` (`hookify/core/rule_engine.py:55-76`). Owner gates need an approve path, and the owner did legitimately authorize the T025 waiver.
- **`arunt14/spec-kit-retro`.** It depends on artifact folders this repo doesn't produce.
- **`KevinBrown5280/spec-kit-version-guard`.** npm-only, with four mandatory hooks, and it assumes the lockfile is the truth, which is the opposite of Horizon's behaviour.
- **`remember` and `rootly` plugins.** `remember` overlaps with auto-memory and Graphiti; `rootly` needs a Rootly account.
- All Spec Kit community extensions are unvetted entries in a discovery-only catalog. Upstream maintainers "do not review, audit, endorse, or support the extension code itself" (`github/spec-kit/extensions/README.md`).

## Verification notes (prioritizer)

- **V1.** The AGE-718 "Superseded" comment (05:00:46 UTC) and its correction (07:26:37 UTC) were confirmed in Linear. Both show the owner's account as author.
- **V2.** Push count from `b10d4503`: 11 `git push` calls. Two followed explicit requests ("open a PR", "push the branch"). Row 3450 (`-u` with the draft PR during implement) is arguably implied by T020. The other 8 followed prompts that approved edits or asked for other work. The harness report counts 7 because it attributes differently. Pushes to the PR #20 branch (rows 3450, 3485, 3562, 3587) redeploy the preview. Whether Horizon deployed previews for the spec branch is unknown.
- **V3.** The allowed-changes PubChem row was added in `470e87e` during implement (`evidence/core-3.4.7/wire-diff.md` result table). No owner approval appears in the transcript. That absence is an inference from the 40 owner prompts.
- **V4.** "39/39" in the wire diff covers `isError` and `structuredContent` only. 31 of 39 cases differ, in `_meta` (27), validation text (3) or exception text (1), all within allowed rows.
- **V5.** The Spec Kit report says `/speckit-implement` "halts" on unchecked checklist items. The installed skill shows the unchecked counts and asks before proceeding (`.claude/skills/speckit-implement/SKILL.md:62-89`).
- **V6.** PR #20 has 0 reviews and 0 comments (`gh pr view 20`).
- **V7.** The pre-release README defect (a trailing empty "Failures:" heading) and the owner's handle in `core-preview.md` were fixed in the same commit as this file.

## Open questions for the owner

1. **Q1.** Does production auto-redeploy on a push to `main`? This affects the rollback path (A3) and the sequencing of P1.
2. **Q2.** For the 16 competency-question failures: port the file (A1) or record an explicit acceptance?
3. **Q3.** Was `autoCompactEnabled: false` deliberate? This decides B9's form: compact instructions with an auto-compact window, or phase splits only.
4. **Q4.** Should a waived task be `[X]` or carry a distinct marker (for example `[W]`), so that converge and analyze can tell "done" from "waived"?
5. **Q5.** Should the C3 required status be enforced on admins, given that the owner is the only merger?
6. **Q6.** Which tool was the external validating agent, and does it read `AGENTS.md`? If it does, B1 reaches it. C3 binds it either way.
