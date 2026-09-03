---
name: pr-review-standard
description: Shared review standard for biosciences-mcp pull requests. Decision precedence, ADR decision matrix, severity levels, evidence bar, and the finding format every reviewer emits. Reference material preloaded into the pr-review agents; it is not a task.
user-invocable: false
---

# biosciences-mcp Pull Request Review Standard

This file is the single source of truth for how a pull request is judged in
this repository. The `/pr-review` skill and the three reviewer agents under
`.claude/agents/pr-review/` all load it. Change it here, not in the agents.

Review behaviour against explicit decisions and executable contracts. Treat
ADR status, scope, and supersession as first-class evidence. ADRs constrain a
review; they must not become a source of stale or opinionated objections.

## 1. Precedence of authority

When two sources disagree, the higher one wins. Cite the source you relied on.

1. Newest applicable **accepted** ADR under `docs/adr/accepted/`
2. An explicit, scoped adaptation or waiver recorded in the ADR itself or in
   `docs/adr/README.md` where that file exists (it does not in this
   repository as of 2026-09-03; ADR-007 names it as the place for
   repository-scoped divergences, so expect it to appear)
3. `.specify/memory/constitution.md`, only where it does not conflict with a
   newer accepted ADR
4. Executable contracts: `tests/contract/registry.py`,
   `tests/contract/test_wire_contracts.py`, `tests/contract/test_serialization_unit.py`
5. The established local pattern in neighbouring code
6. Drafts, critiques (`docs/adr/critique/`), rationale documents, and
   `CLAUDE.md` as context only; never as a merge requirement on their own

Before citing an ADR clause, check its header: `Status`, `Scope`,
`Supersedes`, `Amends`. A clause that a newer accepted ADR supersedes is not
evidence.

## 2. Known governance drift (verified 2026-09-03)

Do not cite these constitution statements as authority; cite the ADR instead.

| Constitution says | Current authority | Consequence for review |
|---|---|---|
| Cites ADR-001 **v1.2** | `docs/adr/accepted/adr-001-v1.4.md` is the accepted text | Cite v1.4 section numbers |
| Cross-reference registry has **22** keys | ADR-001 v1.4 Appendix A and `tests/contract/registry.py` hold **23** | Use the registry file as the count |
| Fixed **10 req/s** client-side rate limit | ADR-007 v1.0 makes the rate posture discoverable or measured, with full-jitter backoff and `Retry-After` precedence | Do not demand a 10 req/s constant |
| ADR-006 says each client owns its own rate limiting | ADR-007 requires one implementation in the base client | Duplicated per-client retry logic is a non-blocking finding pointing at ADR-007, not a requirement |
| ADR-003 sits under `accepted/` but its header says `Status: Draft` | Treat the SpecKit workflow as established practice (Constitution Principle V), not as an ADR-backed MUST | Missing spec artefacts are non-blocking unless the PR itself claims SpecKit compliance |
| Constitution Principle V and ADR-005 examples name dotted `/speckit.*` commands | Spec Kit v1.0.4 (PR #9) installs them as skills named `/speckit-*` | Do not flag either spelling; a constitution PATCH is owed after PR #9 merges |
| Constitution says "All PRs MUST pass `/analyze` validation" | Unenforced in practice; `/speckit-converge` (PR #9) is the nearest gate and it grades against the stale constitution | Treat convergence CRITICAL items that cite the constitution as needing re-grading against the precedence above before they become work items |

The critique under `docs/adr/critique/` is explicitly non-normative. It is
useful context for ADR-001 v1.5 discussions and nothing more.

## 3. Decision matrix

Identify applicable clauses from the **behaviour** the PR changes, not from
file names alone. A docstring edit in `clients/base.py` does not trigger the
ADR-007 row; a change to backoff arithmetic in any file does.

| Change area | Governing evidence | Expected proof in the PR | How to verify |
|---|---|---|---|
| Modern API client (anything except ChEMBL) | ADR-001 §2; Constitution I | Async `httpx`, pooled client via `LifeSciencesClient`, no blocking I/O in async paths | Read the diff; grep for `requests.`, `time.sleep`, sync SDK calls |
| ChEMBL client | ADR-001 §2 | SDK calls wrapped in `run_in_executor`; batch tool present and bounded | Read the diff |
| Search / lookup tools | ADR-001 §3 | Fuzzy tool returns ranked candidates with CURIEs; strict tool rejects raw strings with `UNRESOLVED_ENTITY` and a `recovery_hint` that names the resolve tool | `uv run pytest -m "unit and <server>"`; wire tier if network is available |
| Entity and list responses | ADR-001 §§4, 7, 8 | Flat records, registered `cross_references` keys, `PaginationEnvelope` on every list tool, `ErrorEnvelope` on every error, `slim` honoured, `page_size` default 50 | `uv run pytest -m "contract and unit"`; read `tests/contract/test_wire_contracts.py` |
| Pydantic entity models | ADR-001 §4 and `models/base.py` | Model inherits `OmitNoneModel`; no `model_dump` override, no `exclude_none` config; envelopes stay on `BaseModel` | `uv run pytest -m "contract and unit"` |
| Shared or domain types | ADR-001 §9 | Shared protocol types (`cross_references.py`, `envelopes.py`) import no domain model | grep imports |
| Cross-reference registry | ADR-001 Appendix A; `tests/contract/registry.py` | Registry table and ADR amended in the same commit; deviation-table entries removed only with wire evidence | Read `registry.py` diff and deviation table diff |
| Server lifecycle | ADR-004 | Module-level singleton client; no `@mcp.on_event` | grep `on_event` |
| Retry and rate behaviour | ADR-007 v1.0 | Implemented once in the base client; full-jitter backoff; `Retry-After` honoured first; exact retry status set; exhausted 429 returns the `RATE_LIMITED` envelope | Read the diff against ADR-007 §2 clause by clause |
| Live integration tests | ADR-007 §2(e) | Module-scoped single fetch; skip only on an exhausted 429, never on a first 429 | Read test fixtures |
| Package ownership, parallel work | ADR-005, ADR-006 | One PR touches one server's files, or coordinates shared-file edits explicitly | Read the file list |
| Public tool surface (names, parameters, `id` formats) | ADR-001 §3, §7; downstream consumers | Any rename or parameter change is stated as breaking or shown compatible | Compare `@mcp.tool` signatures at base and head |
| New architectural direction | Governance section of the constitution | A proposed ADR with context, alternatives, consequences, migration | Check `docs/adr/` in the diff |
| Docs that describe behaviour (`CLAUDE.md`, `tests/README.md`, ADR README) | Consistency | Counts, tool names, and rules updated when the PR changes what they describe | Compare stated numbers with the diff |

## 4. Severity

| Level | Meaning | Gate |
|---|---|---|
| **Blocking** | Correctness bug, security or data-integrity risk, wire-compatibility break, or an applicable unwaived MUST from an accepted ADR | Must be fixed or explicitly waived before merge |
| **Non-blocking** | Meaningful maintainability or design improvement that can safely follow in another PR | Approve with the comment left open |
| **Nit** | Preference, naming, clarification, or a learning-oriented note | Never blocks; cap at five per review, count the rest |
| **Pre-existing** | A real defect the PR did not introduce | Report separately, never against the author |
| **Governance note** | Drift between governing documents surfaced by this PR | Report in the summary, not as a finding on the author |

A passing test suite supports approval but does not replace design review.
Approve with unresolved comments only when every remaining comment is
explicitly non-blocking or a nit.

## 5. Evidence bar

- Every **Blocking** finding cites `path:line` at the PR head and states the
  observed behaviour in the code, not an inference from a name or docstring.
- A behaviour claim about upstream APIs or serialisation needs either a test
  you ran, a citation to the executable contract, or a citation to an
  accepted ADR clause.
- Rate your confidence 0 to 100 that the finding is real and will be hit in
  practice. Report Blocking and Non-blocking findings at 80 or above. Below
  that, either verify further or drop it. A nit needs no score.
- Verify before you assert: run the command in the matrix's last column when
  it exists and report the output line you relied on.
- Say what you examined and what you did not. A review that silently skips
  half the diff is worse than one that says so.

## 6. Finding format

Emit every finding in this exact shape so the orchestrator can merge and
de-duplicate them. One block per finding.

```
### [SEVERITY] short claim (<= 12 words)
- Where: path/to/file.py:LINE (at HEAD_SHA)
- Authority: ADR-007 §2(c)   (or: executable contract / local pattern / none)
- Confidence: 90
- Observed: what the code does, quoting the relevant line or expression
- Consequence: who or what breaks, and when
- Requested: the outcome, not necessarily the exact patch
- Validation: the command or test that would show it is fixed
```

Close the report with:

```
## Examined
- files or areas read in full
## Not examined
- files or areas skipped, and why
## Governance notes
- drift surfaced by this PR, if any
```

## 7. Do not report

- Anything `ruff` or `pyright` will catch. Run them on the changed files and
  report the counts once as a single nit if they are non-zero.
- Style preferences that no accepted ADR or local pattern states.
- Test-only code that deliberately violates production rules to exercise an
  error path.
- The same defect twice. If a pattern repeats across files, report it once
  with the list of locations.
- Requests to refactor code the PR did not touch, unless the PR makes the
  untouched code wrong.

## 8. Writing the comment

Address the code, explain why, and balance identifying the problem with
prescribing a fix. Supply the authority, the concrete evidence, the impact,
and a verifiable completion condition. This is better than "use the standard
pattern" because the author can act on it without a round trip.

Prefer small, self-contained PRs. If a PR bundles unrelated changes, say so
once as a Non-blocking finding and review each part on its own merits.
