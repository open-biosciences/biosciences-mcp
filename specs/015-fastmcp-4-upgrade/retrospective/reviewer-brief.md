# Spec 015 retrospective — shared brief for reviewer agents (2026-10-02)

## Goal
Capture lessons learned from the spec 015 upgrade (biosciences-mcp core: FastMCP 2.14.5 → 3.4.7, gated path to 4.x, ADR-009 version policy) from its start on 2026-10-01 through 2026-10-02, and prioritize continuous-improvement actions. Every lesson must be tied to evidence and to a concrete change (constitution/template edit, quickstart check, hook, CLAUDE.md rule, skill, Linear issue, Spec Kit extension).

## Hard constraints (all agents)
- READ-ONLY. Do not edit repo files, do not commit, do not push, do not install plugins/extensions (`specify extension add`, `/plugin install` are forbidden — read extension source via `gh api` instead). No writes to Graphiti, Linear, GitHub, or any external service.
- Write your report ONLY to the output file named in your prompt (in this scratchpad folder). Keep your final chat reply to a 5-line summary plus the file path.
- Cite evidence precisely: `path:line`, commit SHA, PR number, transcript session id + timestamp, or a documentation URL. Mark anything inferred as **Inference**. Never present a guess as fact.
- Refer to people by role ("the owner"), not by name.

## Locations
- Main checkout (main = `0430e52`, FastMCP 2.14.5): `~/open-biosciences/biosciences-mcp`
- PR #20 worktree (branch `implement/015-fastmcp-4-upgrade-core`, local head `d07ffba`, origin head `8b9195f`): `~/open-biosciences/biosciences-mcp/.worktrees/implement-015-core`
- Spec folder (in worktree): `specs/015-fastmcp-4-upgrade/` — `spec.md`, `plan.md`, `research.md`, `tasks.md`, `quickstart.md`, `HANDOFF.md`, `contracts/`, `evidence/` (incl. `core-preview.md`, `core-3.4.7/`, `core-3.4.7-prerelease/README.md`)
- Process log: `docs/speckit-process-record.md`; intended process: `docs/speckit-standard-prompt-v2.md`; constitution `.specify/memory/constitution.md`; ADR-009 draft `docs/adr/proposed/adr-009-v0.1.md`
- Repo CLAUDE.md (worktree and main), workspace `~/open-biosciences/CLAUDE.md`, user memory dir `~/.claude/projects/-home-donbr-open-biosciences-biosciences-mcp/memory/`
- Session transcripts (JSONL): `~/.claude/projects/-home-donbr-open-biosciences-biosciences-mcp/`
  - `b10d4503-f44c-4318-86bb-c652dcff1883.jsonl` — the main 015 session (2026-10-01 02:47Z → 2026-10-02 05:45Z, ~3600 rows, ended at context limit)
  - `5ec7f1e1-a625-4a9d-a23e-90abfb7c2935.jsonl` — current session (status review, T025 waiver, pre-release tests). Still being written.
  - Parse with python `json`; user prompts are rows with `type=="user"` and string content; tool calls are `assistant` rows with `tool_use` blocks.
- PRs: #18 (gateway tool_names, merged), #19 (spec/plan/tasks, merged), #20 (core upgrade, draft). Use `gh pr view N --json ...`.
- Linear: AGE-718 (tracking), AGE-733, AGE-734, AGE-703, AGE-704, AGE-688 (read via the Linear MCP `get_issue` only if needed).

## Seed observations (verify each; add what you find; drop what evidence does not support)
1. The upgrade began as a hand-crafted audit prompt; the owner asked "why are we doing these changes via prompt engineering instead of … specifications and plans" and the work moved to `/speckit-specify`.
2. The first spec missed existing tracking issue AGE-718 (target 3.4.7, not 4.x) and had to be amended ("option B").
3. `/speckit-analyze` ran twice with remediation rounds (H1–H5, F4/C3/F5/F6/C4); PR #19 review N1–N9.
4. A validating agent hand-wrote tool arguments (an earlier mistake the owner had caught) and recorded "Go" (T026) itself; the next session withdrew it per FR-011 and unchecked T026. T025 (timed rollback) was claimed but never measured.
5. The owner tried to merge from a phone and could not run `!` commands; merges had to happen in GitHub web/mobile. A session that ran `/pr-review` is barred from merging.
6. Agent sessions pushed docs-only commits to the PR branch without being asked; each push auto-redeployed the Horizon preview. The owner noticed an unrequested deployment and had to investigate scope.
7. Spec check 4.7 (timed rollback by manual redeploy) assumed manual deploys; Horizon auto-deploys per push, so the drill was waived with a proxy (29 s build, ~70 s push→image).
8. Horizon ignores `uv.lock` (`uv pip install --system ./.`): deployed set had mcp 1.30.0 vs locked 1.26.0, Python 3.12 vs local 3.13. Known in research R3/R10 but local tests still ran only the lock set until 2026-10-02. A rollback re-resolves rather than restores.
9. Quickstart §2 / T016–T018 ran unit, contract-unit, `test_gateway.py`, contract-integration — not the full integration tier. The 2026-10-02 full run found 16 new failures in `tests/integration/test_competency_questions_mcp.py` (gateway `get_tool().fn()` returns `ToolResult` on 3.4.7; wire unchanged). AGE-718 acceptance requires no new integration failures.
10. Session `b10d4503` hit the context limit (auto-compact off) right after writing `HANDOFF.md`; the handoff misstated PR head.
11. Upstream noise (IUPHAR 401/AGE-734, Ensembl timeouts, ChEMBL 500s) makes "no new failures" hard to judge without a same-day baseline on main; the 2026-10-02 run needed a 2.14.5 baseline and A/B to separate regressions from flakes.
12. Good practices worth keeping: tool-surface guard committed before upgrade (T006), baselines derived from contracts not hand-written, wire diff 39/39, `.txt` logs + key scrub, evidence folder per phase, process record.

## Report format (each agent)
Markdown with: (1) Scope & sources consulted (with URLs/paths); (2) Findings table: id, observation, evidence, root cause, lesson; (3) Recommendations table: id, change, type (template/constitution/quickstart/hook/CLAUDE.md/skill/extension/issue), owner (Platform Architect/MCP Platform Engineer/Quality & Skills Engineer/repo owner), effort (S/M/L), impact (H/M/L), grounding (doc URL or evidence); (4) Open questions. Keep it under ~400 lines.
