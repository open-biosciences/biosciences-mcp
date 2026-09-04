# Review instructions

These instructions tune automated review of pull requests in this
repository. Claude Code Review (the managed product) reads this file; the
`code-review` plugin that `.github/workflows/claude-code-review.yml` runs
reads only `CLAUDE.md`. The full standard, including the ADR decision matrix
and the finding format, lives in `.claude/skills/pr-review-standard/SKILL.md`.
Severity maps as follows: Important here is Blocking there; Nit is Nit; the
standard's Non-blocking level has no counterpart here, so report it as a Nit
with the word "non-blocking" in the first line.

Every automated comment, whether from Code Review, the workflow, or the
`/pr-review` team, is advisory. None of them approves, requests changes, or
merges; the `/pr-review` orchestrator posts only top-level comments and
`COMMENT` reviews, and a guard hook denies the rest.

## What Important means here

Reserve Important for a finding that would change what an agent receives on
the wire or break behaviour in practice: a tool returning something other
than the ADR-001 §8 envelopes, `null` emitted for an absent value, a strict
tool accepting a raw string, a cross-reference key or format outside
`tests/contract/registry.py`, blocking I/O in an async path, a retry loop
that violates ADR-007 §2, a renamed tool or parameter with no compatibility
note, or a real logic bug. Style, naming, and refactoring suggestions are
Nit at most.

## Authority and precedence

Cite the newest applicable accepted ADR under `docs/adr/accepted/` before
anything else. Check the ADR header for status and supersession before
citing a clause. The constitution in `.specify/memory/constitution.md` still
cites ADR-001 v1.2, a 22-key registry, and a fixed 10 req/s limit; the
current authorities are ADR-001 v1.4 (23 keys) and ADR-007 v1.0. Do not
raise findings from those three stale statements. Documents under
`docs/adr/critique/` are non-normative context.

## Verification bar

A behaviour claim needs a `file:line` citation in the source at the PR head,
or the output of a command you ran, not an inference from a name or
docstring. Serialisation claims must account for FastMCP calling
`pydantic_core.to_json`, never `model_dump()`.

## Do not report

- Anything `ruff` or `pyright` reports; mention the counts once at most
- Files under `specs/`, `.specify/`, and `docs/` for style
- Test code that deliberately feeds bad input to exercise an error path
- Pre-existing defects as if the PR introduced them; tag them Pre-existing

## Always check

- Every entity model inherits `OmitNoneModel`; envelopes stay on `BaseModel`
- Every list tool returns `PaginationEnvelope`; every error returns `ErrorEnvelope`
- `tests/contract/registry.py` and ADR-001 Appendix A change together
- `CLAUDE.md` and `tests/README.md` counts and tool names still match the code

## Cap the nits

Report at most five Nits per review and count the rest in the summary. Lead
the summary with "No blocking findings" when that is the case.

## Re-review

After the first review of a PR, post Important findings only unless the
author asks for another full pass.
