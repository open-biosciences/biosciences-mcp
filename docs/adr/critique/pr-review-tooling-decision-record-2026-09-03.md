# Decision record: should `pr-merge-order` join the scope of PR #11?

| | |
|---|---|
| Status | Proposed (team analysis complete; awaiting maintainer decision). See the update note below: PR #11 merged after the analysis. |
| Date | 2026-09-03 |
| Repo state | `main` @ `f6ced95` (#10, #8, #9 merged during the analysis); PR #11 @ `f60e508` is the only open PR |
| Subject | `.claude/workflows/pr-merge-order.js` + `scripts/pr_merge_sim.py` (both untracked) vs PR #11 "chore(review): add the /pr-review team, guard hook, REVIEW.md, and PR template" |
| Evidence files | `pr-review-tooling-2026-09-03/references.md`, `adversary-round1.md`, `adversary-round2.md` (session scratchpad paths redacted) |
| Method | Three-role team: docs-grounding researcher, scope designer, adversarial reviewer (two rounds). Every claim below carries a source tag: `[docs]` official Claude Code documentation, `[diff]` read from the PR or the tool source, `[harness]` reproduced in a throwaway clone, `[hook]` piped through PR #11's guard hook, `[sim]` produced by the simulator against this repo |

> **Update, later on 2026-09-03.** PR #11 merged as `734b817` and PR #12 (`fix/cq-diff-envelope-shape`) as `b155b8a` after this analysis was written; the repository state in the header is the state the team examined. The decision stands with one consequence: step 1 ("keep it local until #11 lands") has expired, so the independent tool PR (step 2) is gated only on its own prerequisites in §5 and §7, and the guarded assessor add-on (step 3) is no longer blocked. Whether #11 landed with its four blockers fixed was not re-verified here.

## 1. Decision

**Do not fold the tool into PR #11.** Split it in three:

1. **Now: keep it local (option D).** Both files stay untracked while PR #11's four blockers are worked. With one open PR there is nothing to order, so there is no evidence run to attach to any PR today.
2. **Next: ship the mechanical tool as its own PR (option C).** `scripts/pr_merge_sim.py` plus the Discover → Order → Verify → Report → Cleanup phases reference nothing in #11. They need no `pr-review-standard`, no guard hook, and carry their own trust statement (§4). Blocking defects found by the adversary are fixed in the working tree already (§6); the remaining prerequisites are a fixture-repo test suite and one recorded run.
3. **Later, optional: a guarded Assess add-on that depends on #11 (option B).** The only part of the workflow that would reuse #11 is a `merge-readiness-assessor` subagent preloading `pr-review-standard` and running under the fixed `pr-review-guard.py`. Until #11 lands, the Assess phase is a second, weaker `/pr-review` and should either be dropped from the shipped workflow or be clearly labelled as advisory.

The designer proposed D → B; the adversary agreed on D and argued C for everything except the assessor. This record adopts the adversary's split because the dependency inventory supports it: the simulator and the non-Assess phases have no import, prompt, or file reference into PR #11 `[diff]`.

## 2. Why not option A (fold into #11)

- **Two trust models in one PR.** PR #11 says "read-only" in its body, its `CLAUDE.md` section, each reviewer prompt, and the hook docstring ("a prompt is advisory; this hook is the enforcement") `[diff]`. The simulator writes `refs/pr/<N>`, creates and removes detached worktrees, and makes scratch commits (the original version also ran `git worktree prune`; the hardened version does not). It never touches `origin`, but it is not read-only. A single PR body cannot carry both promises honestly, and the review standard #11 introduces says bundling unrelated changes is itself a finding (`pr-review-standard/SKILL.md` "Prefer small, self-contained PRs"; PR template "One coherent change per PR") `[diff]`.
- **The guard cannot see the simulator.** Piped through `pr-review-guard.py` at `f60e508`: `python3 scripts/pr_merge_sim.py discover|sequence|cleanup` → allow; `git worktree add`, `git merge --squash`, `git reset --hard`, `git rebase --onto`, `git merge-base` → deny; `git fetch`, `git -c user.name=… commit`, `git update-ref -d` → allow `[hook]`. Shipping the two together would mean a package whose guard denies every primitive its own tool is built from, passable only through interpreter indirection, the exact bypass #11's own review comments list.
- **Blocker coupling.** All four #11 blockers sit in the hook and report-path plumbing (heredoc report writes denied and no `Write` tool; `git merge-base` denied; mutating shapes such as `git -C x push`, `gh api -F event=APPROVE`, `gh issue comment` allowed; reports written inside the worktree that step 6 force-removes) `[diff][hook]`. Adding ~640 lines in two more languages and two new top-level surfaces (`scripts/`, `.claude/workflows/`) to a PR under request-changes raises the review burden from 827 to ~1,470 lines and gives reviewers a moving target.
- **The motivating condition is gone for now.** `gh pr list --state open` returns only #11 `[sim]`.

## 3. Fit analysis

| Dimension | PR #11 `/pr-review` | `pr-merge-order` | Fit |
|---|---|---|---|
| Question answered | Is this one diff acceptable against the ADRs? | In what order do all open PRs land, and does squash vs merge matter? | Adjacent; the tool consumes review verdicts, it does not produce ADR findings |
| Primitive | Skill + three `Agent` calls, turn by turn | Workflow script: deterministic phases, N+5 to N+7 agents per run `[diff]` | Different feature; the docs position workflows, subagents, and skills as separate tools ([workflows › When to use a workflow](https://code.claude.com/docs/en/workflows#when-to-use-a-workflow)) |
| Local side effects | None by contract | Refs, worktrees, scratch commits | Incompatible with one shared trust statement |
| Outputs | Report files + optional PR comment | Structured JSON per phase, markdown returned as the workflow result; no files, no comments `[diff]` | Tool avoids #11 blocker 4 by construction |
| Hook interaction | Hook in three agents' frontmatter only; orchestrator unguarded | Default workflow subagents: no hook fires. `agentType` could attach one, but whether frontmatter hooks and `skills:` apply through `agentType` is **unverified** (§7) | Neither package currently guards the thing it claims to guard |
| Runtime requirements | `gh`, `git`, `uv` | `gh` (authenticated), `git ≥ 2.24` for `merge --no-verify` `[harness]`, Python matching the repo floor (`>=3.11`), and the Workflow tool: paid plans, off by default on Pro, disableable per org, stripped from subagents, inert on `-p`/CI keyword routes ([workflows](https://code.claude.com/docs/en/workflows), [sub-agents](https://code.claude.com/docs/en/sub-agents)) | Tool has the harder requirement set |
| Test surface | `claude plugin validate` (structure only) | None shipped yet; helper is unit-testable with a fixture repo | Tool needs tests #11 does not |

## 4. Trust boundary for the tool (what the independent PR must state)

Verbatim for the PR body and `docs/pr-merge-order.md`:

> `pr_merge_sim.py` mutates local repository state only: it fetches `refs/pull/<N>/head` into `refs/pr/<N>`, creates detached worktrees under `--root`, makes commits inside a scratch worktree, and on `cleanup` removes only the worktrees and refs recorded in `<root>/.pr-merge-sim-manifest.json`. It never pushes, never merges or comments on GitHub. It refuses a `--root` that is non-empty without its manifest, that is the repository root, or that is a direct child of it (feature worktrees live there per ADR-005, `docs/adr/accepted/adr-005-v1.0.md`).

Why the default root matters: ADR-005 makes `.worktrees/<name>` the canonical home for feature worktrees and says nothing about removal `[diff]`. The original `cleanup` deleted every child of `--root`; in the harness it destroyed a foreign worktree with uncommitted work and a user data directory, and a one-level typo (`--root .worktrees`) deleted a feature worktree `[harness]`. That is fixed (§6), and the direct-child refusal exists so the typo cannot recur.

## 5. Packaging design for the independent PR

**File layout**

```
.claude/workflows/pr-merge-order.js     # entry point; a saved project workflow runs as /pr-merge-order
scripts/pr_merge_sim.py                 # helper: discover | sequence | cleanup
tests/unit/test_pr_merge_sim.py         # fixture-repo tests, marker `unit`, git binary only
docs/pr-merge-order.md                  # trust statement + runbook (written; see below)
docs/adr/critique/pr-review-tooling-decision-record-2026-09-03.md   # this record
```

**Entry point: workflow only, no wrapper skill.** A script saved under `.claude/workflows/` is "shared with everyone who clones the repo" and "runs as `/<name>` in future sessions" ([workflows › Save the workflow for reuse](https://code.claude.com/docs/en/workflows#save-the-workflow-for-reuse); [claude-directory › File reference](https://code.claude.com/docs/en/claude-directory#file-reference)). A wrapper skill would add nothing that is documented to reach the workflow's agents: a skill's `allowed-tools` grant "clears when you send your next message" ([skills › Frontmatter reference](https://code.claude.com/docs/en/skills#frontmatter-reference)), while "the subagents the workflow spawns use your permission rules" ([workflows › Approve the plan before it runs](https://code.claude.com/docs/en/workflows#approve-the-plan-before-it-runs)). Whether a skill and a workflow sharing one name collide is undocumented (the skills precedence list never mentions workflows), so avoid the situation by construction.

**Permissions.** For interactive use the user approves the workflow once; "Yes, and don't ask again for `<name>`" is offered for saved workflows by name ([workflows › Approve the plan](https://code.claude.com/docs/en/workflows#approve-the-plan-before-it-runs)). For headless runs, add `Workflow(pr-merge-order)` to `permissions.allow`. Bash rules must match every piped subcommand independently: "separators are `&&`, `||`, `;`, `|`, `|&`, `&`, and newlines. A rule must match each subcommand independently" ([permissions › Wildcard patterns](https://code.claude.com/docs/en/permissions#wildcard-patterns)). The Assess prompt pipes into `tail`, `grep`, and `head` and uses `cd`, so an allow list must include those or the prompt must drop the pipes. Project `permissions.allow` applies only after the workspace trust dialog ([permissions › Project allow rules and workspace trust](https://code.claude.com/docs/en/permissions#project-allow-rules-and-workspace-trust)).

**Hook plan.** Discover, Verify, and Cleanup agents each run exactly one helper command and stay on the default workflow subagent, unguarded but documented. If defence-in-depth is wanted, the two documented options are mutually exclusive and neither is verified for workflow agents: a project `.claude/settings.json` PreToolUse hook (fires for every agent and the main session; the hooks page never mentions workflows) or a custom agent via `agentType` whose frontmatter carries the hook ([hooks › Hooks in skills and agents](https://code.claude.com/docs/en/hooks#hooks-in-skills-and-agents); [sub-agents › Supported frontmatter fields](https://code.claude.com/docs/en/sub-agents#supported-frontmatter-fields)). Pick one after the test in §7.

**Assess phase.** Ship it disabled or advisory in the independent PR. When #11 lands, add `.claude/agents/pr-review/merge-readiness-assessor.md` with `skills: pr-review-standard` and the fixed guard hook, and switch the workflow's Assess `agent()` calls to `agentType: 'merge-readiness-assessor'`. The assessor asks merge-readiness questions (PR-body claims vs diff, CI reported vs run log, tests in the worktree, semantic dependencies) and ingests an existing `/pr-review` comment for the same head OID as `[pr-review]` evidence instead of re-reviewing. Do not dispatch the three ADR reviewers per PR from the workflow: that triples the agent count and re-imports #11's report-path blocker.

**Preflight.** `prepare()` now checks `git --version ≥ 2.24`, resolves the default branch from `refs/remotes/origin/HEAD` (falling back to `gh repo view`), fails as JSON on `gh` errors, and refuses unsafe roots. Run the helper through `uv run python` if the Python floor must match the repo's `>=3.11`; the system `python3` on this machine is 3.10.

**Tests** (`tests/unit/test_pr_merge_sim.py`, no network): fixture bare origin with `refs/pull/N/head`, branches `a`, `b`, `stacked-on-a`, a stub `gh` JSON; cases for `detect_strategy`, `try_merge` leaving HEAD untouched, `land` empty-contained under both strategies, `discover` pairwise showing squash-conflict/merge-clean for the stacked pair, `sequence` coverage and duplicate rejection, rebase fallback with `fix_command`, manifest-scoped `cleanup`, and root refusal. The workflow script is not unit-testable; the PR body carries one recorded run.

**Plugin distribution (later, optional).** Plugins may ship `workflows/` and `scripts/` at the plugin root ([plugins-reference › Plugin manifest schema](https://code.claude.com/docs/en/plugins-reference)), but "hooks, mcpServers, and permissionMode are not supported for plugin-shipped agents", so a guarded assessor must stay repo-level.

## 6. Defects found and their status

| Finding (adversary, severity) | Status in working tree |
|---|---|
| `cleanup` deleted every child of `--root`, including foreign worktrees and user files (blocking) | Fixed: manifest-scoped removal; foreign entries left in place; verified `[harness]` |
| `--root` could be the repo root or `.worktrees` (blocking adjacency) | Fixed: refused, verified |
| `sequence` accepted duplicates and silently omitted PRs; holds were simulated as landings (serious) | Fixed: duplicates and missing PRs rejected; workflow passes holds via `--skip`; verified |
| Docstring claimed git ≥ 2.20; `merge --no-verify` needs 2.24 (serious) | Fixed: docstring and runtime check |
| Rebase fallback ran without a git identity (serious) | Fixed: identity passed |
| Every off-nominal path was a traceback with state left behind (serious) | Fixed: JSON `{"error": …}` with a cleanup hint; moved head OID now simulates what was fetched and reports `oid_verified: false` |
| Pairwise `retarget_hazard_files` was empty by construction (serious) | Fixed: computed against the landed tree |
| Hard-coded `main` (serious) | Fixed: default branch detected |
| Workflow skipped Cleanup on exceptions and on the empty-PR early return | Fixed: `try … finally`; empty-PR path cleans up |
| Unquoted `args.root` in agent prompts (minor) | Fixed: sanitised and quoted |
| Assess duplicates `/pr-review` without the standard (serious) | Open: design decision above (advisory now, assessor add-on after #11) |
| `REPO` resolves to the worktree when run from inside one (minor) | Open: document; run from the main checkout |
| Behaviour inside an `EnterWorktree` session (unknown) | Open: must be tested; the command-shape guard "can't be turned off" ([worktrees › How Claude Code enforces isolation](https://code.claude.com/docs/en/worktrees#how-claude-code-enforces-isolation)) and subprocess git would write to the shared `.git` unseen |

The hardened helper was re-run against this repository (one open PR, `discover`, `sequence --order 11`, `cleanup`) and against the safety harness; lint, format, and pyright pass under the repo configuration.

## 7. Unverified claims and the tests that would settle them

1. **Does `agentType` apply an agent's frontmatter hooks and `skills:` inside a workflow?** The bundled `/workflow-authoring` reference says only that the type is "resolved from the same registry as the Agent tool". Test: a one-agent throwaway workflow with `agentType` pointing at an agent whose PreToolUse hook denies `echo`. Needs a user-authorised Workflow run with the agent registered under `.claude/agents/`.
2. **Do project `settings.json` PreToolUse hooks fire in workflow agents?** Documented only by inference (workflow agents are called subagents; settings hooks run inside subagents). Same test with a settings-level hook.
3. **Does the simulator run inside an `EnterWorktree` session, and where do its refs go?** Untested.
4. **Skill vs workflow name precedence.** Undocumented; avoided by shipping no skill.

## 8. What this record does not claim

- That the guard hook allows every simulator command. It allows the `python3` wrapper and denies the git primitives.
- That the tool is read-only. It never pushes to `origin`; it does mutate local refs, worktrees, and objects.
- That a passing `sequence` proves an order beyond what it checks: conflicts, net contribution, and retarget hazards for the PRs listed, under the strategy given.
- That workflows are undocumented. They are documented, plan-gated, version-bound (the authoring skill needs v2.1.248+), unavailable to subagents, and inert on `-p`/CI keyword routes.
- That the tool has been exercised on this repository's current PRs beyond the one open PR. The earlier four-PR run (`main` @ `29e0cfa`) predates the hardening; it correctly found the #8 → #9 squash conflict and the merge-commit landing convention `[sim]`.

## 9. References

Official Claude Code documentation (fetched 2026-09-03; quotations verified by the adversary where marked):

- Workflows: [When to use a workflow](https://code.claude.com/docs/en/workflows#when-to-use-a-workflow) · [Save the workflow for reuse](https://code.claude.com/docs/en/workflows#save-the-workflow-for-reuse) · [Pass input to a saved workflow](https://code.claude.com/docs/en/workflows#pass-input-to-a-saved-workflow) · [Approve the plan before it runs](https://code.claude.com/docs/en/workflows#approve-the-plan-before-it-runs) · [Behavior and limits](https://code.claude.com/docs/en/workflows#behavior-and-limits) · [Turn workflows off](https://code.claude.com/docs/en/workflows#turn-workflows-off) · [Distribute a workflow in a plugin](https://code.claude.com/docs/en/workflows#distribute-a-workflow-in-a-plugin)
- Skills: [Frontmatter reference](https://code.claude.com/docs/en/skills#frontmatter-reference) · [Add supporting files](https://code.claude.com/docs/en/skills#add-supporting-files) · [Pre-approve tools for a skill](https://code.claude.com/docs/en/skills#pre-approve-tools-for-a-skill) · [Control who invokes a skill](https://code.claude.com/docs/en/skills#control-who-invokes-a-skill)
- Subagents: [Supported frontmatter fields](https://code.claude.com/docs/en/sub-agents#supported-frontmatter-fields) · [Permission modes](https://code.claude.com/docs/en/sub-agents#permission-modes)
- Hooks: [PreToolUse](https://code.claude.com/docs/en/hooks#pretooluse) · [Hooks in skills and agents](https://code.claude.com/docs/en/hooks#hooks-in-skills-and-agents)
- Permissions: [Manage permissions](https://code.claude.com/docs/en/permissions#manage-permissions) · [Wildcard patterns](https://code.claude.com/docs/en/permissions#wildcard-patterns) · [Extend permissions with hooks](https://code.claude.com/docs/en/permissions#extend-permissions-with-hooks) · [Project allow rules and workspace trust](https://code.claude.com/docs/en/permissions#project-allow-rules-and-workspace-trust)
- Worktrees: [How Claude Code enforces isolation](https://code.claude.com/docs/en/worktrees#how-claude-code-enforces-isolation) · [Ask Claude to create a worktree](https://code.claude.com/docs/en/worktrees#ask-claude-to-create-a-worktree)
- Plugins and layout: [Plugin manifest schema and Agents](https://code.claude.com/docs/en/plugins-reference) · [.claude directory file reference](https://code.claude.com/docs/en/claude-directory#file-reference) · [Tools reference, Workflow row](https://code.claude.com/docs/en/tools-reference)

Source notes: the platform-docs MCP indexes `platform.claude.com` only and has no Claude Code CLI pages; Context7 mirrors the official site but still cites the retired `slash-commands` page. Neither could corroborate or contradict the official pages above, so all citations point at `code.claude.com`.

Repository references: PR #11 at `f60e508` (`.claude/skills/pr-review/SKILL.md`, `.claude/skills/pr-review-standard/SKILL.md`, `.claude/agents/pr-review/*.md`, `.claude/hooks/pr-review-guard.py`, `REVIEW.md`, `.github/PULL_REQUEST_TEMPLATE.md`); ADR-005 `docs/adr/accepted/adr-005-v1.0.md`; team evidence files in `docs/adr/critique/pr-review-tooling-2026-09-03/` (`references.md`, `adversary-round1.md`, `adversary-round2.md`; the designer's draft is superseded by this record and not kept).
