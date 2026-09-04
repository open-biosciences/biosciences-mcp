# Adversary round 2 — design draft and references

Context refresh: main @ f6ced95 (#10, #8, #9 merged during round 1); #11 (f60e508) is the only open PR and dry-merges cleanly. Harness under this scratchpad (`clone/`, `origin.git/`, `fakebin/gh`) reused; repo untouched. Corrections folded in: the guard hook DENIES the git primitives textually and only the `python3` wrapper passes; the cleanup finding stands and is being fixed regardless.

## 1. Verdict on "D now → B later"

**D now: agree, and it is stronger than the draft says** — with one open PR the tool has nothing to order, so "use it today for #8–#11" (draft §3) is no longer available as B's evidence run; B's PR body will need a fixture-repo run instead.

**B later: agree only for the part that actually depends on #11; argue C for the rest.** Inventory of hard dependencies on #11: (a) the `pr-review-standard` skill the assessor would preload (`skills:` frontmatter) exists only in #11; (b) the fixed `pr-review-guard.py` for the assessor. Both attach to the **Assess** phase alone. `pr_merge_sim.py` and the Discover/Order/Verify/Report/Cleanup phases reference nothing in #11 (js has no mention of `pr-review-standard`; py imports only git/gh). The `[pr-review]` comment-ingestion link is a runtime nicety, not a dependency (it works whether or not #11 is merged — it just finds no comment). So: ship the mechanical tool as **C (independent)** once round-1 blockers 2, 4, 5, 6 are fixed, and treat the guarded assessor as a **B add-on** — or drop Assess entirely (round-1 #8: it is a second, weaker `/pr-review`). "Never" is not warranted: `sequence` found the real #8↔#9 squash conflict.

## 2. §4 packaging claims

| Claim (draft §4) | Status | Evidence |
|---|---|---|
| "already runs as `/pr-merge-order`" | HOLDS | This session's skill list shows `pr-merge-order`; claude-directory row: "each file becomes a `/<name>` command" |
| skill `allowed-tools` covers only the invoking turn | HOLDS | skills.md: "The grant clears when you send your next message" (frontmatter row + §Pre-approve) |
| "subagents the workflow spawns use your permission rules" | HOLDS | workflows.md §Approve the plan, verbatim |
| therefore a wrapper skill cannot pre-approve workflow agents' Bash | UNVERIFIED (plausible) | Docs scope the grant to the turn and route subagent permissions through rules/modes (sub-agents.md §Permission modes); no doc says skill grants propagate. Not testable here: running a Workflow needs the user's opt-in |
| skill/workflow same-name precedence undocumented | HOLDS | skills.md "When skills share the same name" lists enterprise/personal/project, bundled, commands, synced — never workflows; workflows.md covers only project-vs-personal workflow. Untestable without adding a skill dir to the session's project |
| `permissions.allow` makes interactive and `-p` runs work; "Nothing else in the script needs Bash" | HOLDS for `Workflow(pr-merge-order)`; **FALSE** for the Bash list | workflows.md: `-p`/SDK need `Workflow`/`Workflow(<name>)` allow rules. But permissions.md: separators are "`&&`, `\|\|`, `;`, `\|`, `\|&`, `&`, and newlines. A rule must match each subcommand independently" — the Assess prompt (js:155-159) pipes into `tail` (×3), `grep`, `head`, and `cd`s; none are in the draft's list. Also project allow rules apply "only after you accept the workspace trust dialog" |
| Discover/Verify/Cleanup on the default workflow subagent → no hook fires | HOLDS today | Hook exists only in the three agents' frontmatter; no `.claude/settings.json` on main (only `settings.local.json` with `enabledMcpjsonServers`) nor in #11 (`.claude/`: agents commands hooks skills) |
| would a `settings.json` PreToolUse hook fire in workflow agents? | UNVERIFIED (documented inference) | hooks.md + sub-agents.md: settings hooks "run inside subagents … before every tool a subagent uses"; workflows.md calls workflow agents "subagents". hooks.md never says "workflow". Not testable here |
| "Add a small dedicated PreToolUse hook only for the three helper-running agents" | **FALSE as written** | A frontmatter hook needs a custom agent (`agentType`), which the same paragraph says these agents don't use; a settings hook fires for every agent and the main session. Pick one |
| `agentType: 'merge-readiness-assessor'` applies its frontmatter hook + `skills:` preload | UNVERIFIED | workflow-authoring skill: agentType is "resolved from the same registry as the Agent tool; composes with schema (the custom agent's system prompt gets a StructuredOutput instruction appended)" — silent on hooks/skills. sub-agents.md: frontmatter hooks run "while that subagent is running" and need workspace trust. Cannot test: the pr-review agents are not registered in this session (they live under `.claude/worktrees/pr-review-team/.claude/agents/`, absent from the Agent tool's type list) and a Workflow run needs user opt-in |
| `agent()` null drops a PR; an exception skips Cleanup | HOLDS, plus an unlisted leak | js:167 `.filter(Boolean)`; no try/finally. Also js:120 `return` on empty `prs` skips Cleanup although `prepare()` already created `scratch-main` (py:166-167); after a discover crash (round-1 E3/E10) worktrees and `refs/pr/*` remain |
| `sequence` must refuse a dirty scratch at start | MOOT | `add_worktree` recreates scratch on every `prepare` (py:60-64,166); residue is `refs/pr/*` and `pr-N` worktrees, not a dirty scratch |
| cleanup must delete only refs it fetched | HOLDS as a need | py:358-359 deletes every `refs/pr/*` |
| pairwise is O(2n²) | HOLDS | 2·n·(n−1); E1: n=4 → 24 entries |
| git ≥ 2.24 | HOLDS | v2.20.0 `git-merge.txt` has no `--no-verify`; v2.24.0 line 13 does |
| python3 ≥ 3.10 | UNVERIFIED / inconsistent | repo `requires-python = ">=3.11"` (pyproject:6); the script is run as system `python3` (3.10.12 here), outside the uv env. Declare one floor |
| `tests/unit/test_pr_merge_sim.py`, marker `unit` | HOLDS layout; doc gap | `tests/unit/` exists, markers at pyproject:35-39; CLAUDE.md's "557 unit" count changes — not in §5 |
| "~730 lines, 2 files"; "≈ N+4 agents, 8 for 4 PRs" | **FALSE** | 389+250 = 639. Agents: 1 + N + (1..2) + (1..2) + 1 + 1 = N+5..N+7 → 9–11 for 4 PRs (js:111,130,184,210,223,250) |
| `claude plugin validate` as #11's test surface | HOLDS, weak | `claude plugin validate .claude/worktrees/pr-review-team` → "✔ Validation passed" — on a PR with 4 blockers, so it validates structure only |
| §2 "hook allows every simulator command" | **FALSE as worded** | Round-1 table: wrapper allowed, primitives denied |
| Outputs: no files, no PR comments | HOLDS | js has no Write and no `gh pr comment` |
| `.worktrees/` gitignored line 210 | HOLDS | `.gitignore:209-210` |

## 3. §6 open questions

1. **Skill vs workflow name collision** — still undocumented (see table). Avoid by construction (workflow-only), as the draft does; don't claim which wins.
2. **agentType hooks/skills** — UNVERIFIED (table). Cheapest test: a one-agent throwaway workflow with `agentType` pointing at an agent whose PreToolUse hook denies `echo`; needs the user to authorise a Workflow run.
3. **ADR-005** — it lives at `biosciences-mcp/docs/adr/accepted/adr-005-v1.0.md` (CLAUDE.md's `biosciences-program/docs/adr/accepted/` does not exist). It makes `.worktrees/<name>` the canonical home for per-agent feature worktrees (lines 59, 108-113). *(Correction 2026-09-04: this originally read "and says nothing about removal". ADR-005 does address removal — a `# Cleanup` block at `:184-187` prescribes `git worktree remove .worktrees/<name>` per worktree, and Consequence 5 at `:257` says "worktrees are disposable after merge". It contemplates removal only one named worktree at a time, which strengthens rather than weakens the point below.)* So the tool's default root sits inside ADR-sanctioned, actively used space — that is the cleanup adjacency. "Local mutation, never origin" is compatible with ADR-005's shared-history model; force-removal is not something ADR-005 contemplated. Recommend default root outside `.worktrees/` (any path works for git) or a manifest-scoped cleanup.
4. **Depend on #11?** Only the assessor does (§1). C is honest for the simulator + non-Assess workflow.
5. **Repo-specific?** Only js:156-165 (uv/pytest markers/ruff, verdict rules) is; py and the other phases are generic (git + gh only). A split is documented-feasible: plugins may ship `workflows/` and `scripts/` at the plugin root (plugins-reference) — but plugin-shipped agents cannot carry `hooks`/`permissionMode`, so a guarded assessor must stay repo-level.
6. **EnterWorktree session** — cannot test from this session. worktrees.md: the shape check "refuses shell constructs it can't trace" and the git-redirect check looks for textual `git -C`/`GIT_DIR`; `python3 scripts/pr_merge_sim.py discover` is a plain command, so it would likely run — and then write refs/worktrees into the shared `.git` unseen, with `REPO` resolving to the worktree (round-1 E7) so roots nest under it. Must be tested before shipping.
7. **`git worktree prune`** — tested: a registered worktree whose directory exists survives (`keepme` kept). A worktree whose directory is momentarily absent (moved/unmounted) is unregistered and its checkout orphaned. Acceptable, but it is a repo-global side effect; state it.
8. **Scratch commits** — tested: after `sequence` the `final_sim_head` is reachable only via the scratch worktree's HEAD reflog; after `cleanup` it is unreachable (harness: 96 unreachable commits), contained in no ref (`for-each-ref --contains` = 0), so it can never be pushed; `git gc --prune=now` removes it (default expiry ≈ 2 weeks). No audit concern; but the report's `sim_head` OIDs dangle — don't cite them as durable.

## 4. Reference spot-check (13 rows, live fetch or saved page dump)

> **Resolved 2026-09-04.** The three rows below marked NOT VERBATIM / Paraphrase / misquoted have been corrected in `references.md` itself, which now carries the verbatim text re-fetched from the live pages. This table stays as the record of what the round-2 check found.

| Ref | Result |
|---|---|
| skills §Pre-approve: "Workspace trust doesn't gate this field" | CONFIRMED verbatim |
| skills frontmatter `allowed-tools` row: "The grant clears when you send your next message" | CONFIRMED |
| skills §Add supporting files: "helper.py (utility script - executed, not loaded)" | CONFIRMED |
| skills §Restrict: "`Skill(name)` … `Skill(name *)`" | CONFIRMED |
| sub-agents hooks: "Project-level frontmatter hooks require accepting workspace trust dialog for folder containing agent file" | **NOT VERBATIM** — actual: "To let a project-level subagent's frontmatter hooks run, accept the workspace trust dialog for the folder that contains the agent file." Also the ref's "Events: PreToolUse, PostToolUse, Stop" is narrower than hooks.md: "All hook events are supported" (Stop → SubagentStop) |
| sub-agents §Permission modes quote | Paraphrase — actual: "If the parent uses `bypassPermissions` or `acceptEdits`, this takes precedence and can't be overridden." |
| permissions §Extend with hooks (both sentences), §Wildcards `:*`, `safe-cmd && other-cmd`, "deny, then ask, then allow" | CONFIRMED; the separator sentence also names `\|` — worth adding, it drives the Bash-allow-list gap above |
| worktrees Note "`${CLAUDE_PROJECT_DIR}` stays put … `cwd` follows Claude" | CONFIRMED, under §Ask Claude to create a worktree |
| plugins-reference "hooks, mcpServers, and permissionMode are not supported for plugin-shipped agents"; root-dir list incl. `workflows/` | CONFIRMED. `workflows` manifest row is misquoted: actual "Custom workflow script files or directories (replaces default `workflows/`)" |
| claude-directory `workflows/*.js` row | CONFIRMED verbatim |
| tools-reference `Workflow` row, "Permission: Yes" | CONFIRMED (page has no subagent-availability statement; that lives in sub-agents.md) |
| hooks "Exit 2 means a blocking error…" | CONFIRMED; fuller text adds "even a JSON `permissionDecision` of "allow" can't override it" |
| Gap 4 ("neither states explicitly that settings hooks apply to workflow agents") | CONFIRMED: hooks.md contains no "workflow"; the inference via "workflow agents are subagents" is documented but indirect |

## 5. The final document must NOT claim

- that the guard hook "allows every simulator command" — it allows the `python3` wrapper and denies the primitives;
- that the tool is "read-only" or side-effect-free — it writes `refs/pr/*`, worktrees, commits, and runs a repo-global `worktree prune`; "never pushes to origin" is the honest sentence;
- "works with git ≥ 2.20" (needs 2.24), or "python3 ≥ 3.10" while the repo requires ≥ 3.11;
- that the head OID is "verified against GitHub" as a safety property — a moved head crashes before the check is reported;
- that a `sequence` pass "verifies the order" without saying it checks neither coverage nor duplicates;
- that workflows are undocumented — say plan-gated, version-bound, unavailable to subagents and to `-p`/CI keyword routes;
- that `settings.json` hooks fire in workflow agents, or that `agentType` applies frontmatter hooks/skills — untested;
- "~730 lines" or "N+4 agents";
- that ADR-005 lives in `biosciences-program`; it is `biosciences-mcp/docs/adr/accepted/adr-005-v1.0.md`;
- that `claude plugin validate` passing says anything about the hook's correctness;
- that the tool has been run against this repo's real PRs — only a stub-`gh` harness has run it, and only one PR is open now;
- any sentence from the sub-agents page quoted as verbatim where the reference list paraphrased (two cases above).
