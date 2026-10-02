# Spec 015 handoff (2026-10-01)

For the next session continuing spec 015 (FastMCP 3.4.7 upgrade, gated path to 4.x, and the ADR-009 version policy). `tasks.md` is the source of truth. This page is orientation only; if the two disagree, `tasks.md` wins.

## Kickoff prompt

> Continue spec 015 from `specs/015-fastmcp-4-upgrade/tasks.md` on branch `implement/015-fastmcp-4-upgrade-core` (worktree `biosciences-mcp/.worktrees/implement-015-core`). Read `HANDOFF.md`, `spec.md`, `plan.md` and `tasks.md` first. Check PR #20's state and the T025/T026 decision before doing anything else. Then run `/speckit-implement` for the next open tasks with `SPECIFY_FEATURE_DIRECTORY=specs/015-fastmcp-4-upgrade`.

Prime the session first (workspace CLAUDE.md: Graphiti priming namespace `open-biosciences-migration-2026-priming`).

## Where things stand

| Item | State |
|---|---|
| PR #18 (gateway mounts use `tool_names` only) | Merged `f99cb51` |
| PR #19 (spec, plan, tasks) | Merged `0430e52` |
| **PR #20, core upgrade** | **Draft**, head `02ca1d0`, CI `unit` passing. Must not merge before T025/T026 (FR-011) |
| Horizon preview | `https://biosciences-mcp-implement-015-fastmcp-4-upgrade-core.fastmcp.app/mcp`: checks 4.1–4.5 and 4.8 passed at `f1c80d1` (`evidence/core-preview.md`) |
| Production | Still FastMCP 2.14.5 at `https://biosciences-mcp.fastmcp.app/mcp` |
| AGE-718 (tracking issue) | In Progress; PRs #18–#20 linked |
| Edge (`biosciences-mcp-edge`) | Not started (US3) |

Core tasks done: T001–T024, T037–T041, T046, T048, T049, T054, T055.

## Open tasks, in order

1. **T025 (owner):** timed rollback on Horizon (quickstart check 4.7), or an explicit owner waiver recorded in `evidence/core-preview.md`.
2. **T026 (owner):** Go/No-Go recorded with decider and date, in `evidence/core-preview.md` and the PR #20 description. A validating agent's "Go" was withdrawn; only the owner records it.
3. **T027 (owner, then agent):** the owner marks PR #20 ready and merges it on GitHub (merge commit) and redeploys production. The agent then runs quickstart §5: checks 4.1, 4.2 and 4.5 against production, plus `FASTMCP_CLOUD_ENDPOINT=https://biosciences-mcp.fastmcp.app/mcp uv run pytest -m e2e -v`.
4. **US3, edge (T005, T028–T036), and the edge half of US4 (T042, T043).** Separate repository and PR. Do T005 first: add `.worktrees/` to edge's `.gitignore`.
   - **AGE-733** (edge leaks the BioGRID key in errors, urgent) must be fixed before or alongside the edge PR, never inside it.
   - **T031:** compare 3.0.2 and 3.4.7 wire captures taken in the same session (3.0.2 from a throwaway detached worktree). Export `BIOGRID_API_KEY`; the capture script refuses to run without it.
   - **T036:** commit edge evidence to core in a docs PR **before** merging the edge PR (FR-011).
5. **Linear filings (any time):**
   - T044: psychology-mcp adopts ADR-009, plus the interim-divergence row in its `docs/adr/README.md`
   - T052: the 4.x follow-up, gated by FR-020
   - T053: ADR-008 vs native tool spans; gateway recovery hints (F9); empty entity output schemas (F10)
6. **After both merges:**
   - T045: accept ADR-009 (move to `accepted/adr-009-v1.0.md`; add the program README row; bump the policy-test comments to v1.0)
   - T047: process-record rows
   - T050: cleanup
   - T051: mark the spec Implemented and close AGE-718

## Worktrees on disk

| Path | Purpose | Remove when |
|---|---|---|
| `biosciences-mcp/.worktrees/implement-015-core` | PR #20 branch | after PR #20 merges (T050) |
| `biosciences-mcp/.worktrees/scratch-015-core` | research only, unpushed commits | anytime (T050) |
| `_audits/fastmcp-4-2026-09-30/worktrees/edge` | research only, unpushed commits | anytime (T050) |

Other worktrees (`curie-hook`, `speckit-upgrade`, `xref-consistency`) predate this work; leave them.

## Things that will bite

- **Merges.** A session that has run `/pr-review` can't run `gh pr merge` for the rest of that session (by design). The owner merges, from GitHub web or mobile if no terminal is handy.
- **Never hand-write tool or parameter names.** Derive them from `tests/contract/conftest.py` `SERVERS`, the baselines in `contracts/`, or a live `list_tools`.
- **`*.log` is gitignored.** Save evidence logs as `.txt`, and strip absolute home paths before committing (AGE-697).
- **Docstring rule (measured on 3.4.7 and 4.0.10).** With an `Args:` section present, a column-0 line ending in `:` that is followed by an indented block starts a section, and that section and everything after it are dropped from the tool description. Keep guidance above `Args:`. `tests/contract/test_tool_surface.py` guards the 34 gateway tools (DrugBank is not mounted).
- **Upstream noise is expected.** IUPHAR returns 401 (AGE-734); Ensembl sometimes returns 500 (re-run once after 10 s, per FR-012); the IUPHAR 429 path deadlocks (AGE-704); importing the package fetches the ChEMBL schema from EBI (AGE-703).
- **otel stack.** Port 6006 is taken by another Phoenix. Use an isolated compose project with port overrides and an override that builds from the worktree (`evidence/core-3.4.7/telemetry.md` has the recipe).
- **Renumbering scripts.** Read a file fully *before* opening it for write; one renumber pass truncated two files.

## Key files

- Spec artifacts: `spec.md`, `plan.md`, `research.md`, `data-model.md`, `quickstart.md`, `tasks.md`
- Contracts: `contracts/tool-surface-invariants.md` (the allowed-changes table), `contracts/version-policy.md`, and both baselines
- Evidence: `evidence/core-2.14.5/`, `evidence/core-3.4.7/` (test logs, `wire-diff.md`, `telemetry.md`, `policy-selfcheck.md`), `evidence/core-preview.md`
- Tools:
  - `research/surface-tools/project_surface.py` (baseline generator)
  - `research/core-capture/core_capture.py`
  - `research/edge-capture/edge_capture.py`
- ADR-009 draft: `docs/adr/proposed/adr-009-v0.1.md`
- Process log: `docs/speckit-process-record.md`
