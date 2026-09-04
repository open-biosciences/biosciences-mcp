# `/pr-merge-order` — simulated landing order for open PRs

Status: draft PR #14 on `feature/pr-merge-order`; not ready to merge (see the checklist in the PR body). See `docs/adr/critique/pr-review-tooling-decision-record-2026-09-03.md` for why it is kept separate from PR #11 and how it should be packaged.

## 1. What it answers, and what it never does

It answers: *in what order should the open PRs land, under which landing strategy, and what will conflict or need a rebase?* It produces a status board, a simulated landing sequence, and the exact `gh`/`git` commands.

Trust statement: `scripts/pr_merge_sim.py` mutates **local** repository state only. It fetches `refs/pull/<N>/head` into `refs/pr/<N>`, creates detached worktrees under `--root`, and makes commits inside a scratch worktree. On `cleanup` it removes only what is recorded in `<root>/.pr-merge-sim-manifest.json`. It never pushes, never merges or comments on GitHub. The workflow itself has no filesystem or shell access; its agents run the helper ([workflows › Behavior and limits](https://code.claude.com/docs/en/workflows#behavior-and-limits)).

It is **not** read-only. Do not run it from a session whose contract is read-only review.

## 2. Requirements

| Requirement | Why |
|---|---|
| `git ≥ 2.24` | `git merge --no-verify` in the merge-commit strategy; checked at start |
| Authenticated `gh` | `gh pr list --json …` with `headRefOid`, `mergeStateStatus`, `reviews`, `comments`, `statusCheckRollup` |
| Python `≥ 3.11` when run via `uv run python`; the script itself only uses the standard library | Repo floor in `pyproject.toml` |
| Workflow tool enabled | Paid plans; on Pro enable from `/config`; orgs may set `disableWorkflows` ([workflows › Turn workflows off](https://code.claude.com/docs/en/workflows#turn-workflows-off)) |
| `/workflow-authoring` skill (Claude Code v2.1.248+) to edit the script | [workflows › Edit a saved script](https://code.claude.com/docs/en/workflows#edit-a-saved-script) |
| `--root` that is empty, absent, or already carries the manifest; never the repo root or a direct child of it | Feature worktrees live in `.worktrees/<name>` (ADR-005); the helper refuses `.worktrees` and the repo root, and refuses any non-empty directory without its manifest |

## 3. Running it

Interactive:

```
/pr-merge-order
```

The Workflow tool asks for approval once per saved workflow; choose "don't ask again for `pr-merge-order`" to skip the prompt next time ([workflows › Approve the plan before it runs](https://code.claude.com/docs/en/workflows#approve-the-plan-before-it-runs)). Arguments reach the script as the `args` global ([workflows › Pass input to a saved workflow](https://code.claude.com/docs/en/workflows#pass-input-to-a-saved-workflow)):

| `args` key | Default | Meaning |
|---|---|---|
| `root` | `.worktrees/pr-merge-sim` (gitignored; allowed because it is one level below the feature-worktree directory) | Where worktrees and the manifest go; `.worktrees` itself and the repo root are refused |
| `limit` | 30 | `gh pr list --limit`; a warning is printed when it is reached |
| `keep` | false | Skip Cleanup and leave the worktrees for inspection |

Headless (`claude -p`, CI): the trigger keyword does not start workflows there; add `Workflow(pr-merge-order)` to `permissions.allow`, plus Bash rules for every piped subcommand the agents use ([permissions › Wildcard patterns](https://code.claude.com/docs/en/permissions#wildcard-patterns)). The Workflow tool is not available to subagents ([sub-agents](https://code.claude.com/docs/en/sub-agents)).

Helper only, without the workflow:

```
python3 scripts/pr_merge_sim.py discover --root <dir>
python3 scripts/pr_merge_sim.py sequence --order 8,10,9 --skip 11 --strategy merge --root <dir>
python3 scripts/pr_merge_sim.py cleanup --root <dir>
```

Every open PR must appear in `--order` or `--skip`; duplicates are rejected.

## 4. Phases and what each may touch

| Phase | Agent type | Side effects |
|---|---|---|
| Discover | default workflow subagent, one helper command | Fetches refs, creates `scratch-main` and `pr-<N>` worktrees, pairwise merge simulations under squash and merge-commit strategies |
| Assess (one per PR) | default workflow subagent today; intended to become a guarded `merge-readiness-assessor` after PR #11 lands | Reads the complete diff in the PR's worktree; runs `uv sync`, `pytest`, `ruff` inside that worktree; opens CI run logs with `gh run view` |
| Order | default | None (LLM proposal) |
| Verify | default, one helper command | `sequence` lands the proposed order on the scratch worktree; holds are passed as `--skip` |
| Report | default | None |
| Cleanup | default, one helper command | Removes manifest-listed worktrees and refs; always runs, even on failure, unless `keep` is set |

## 5. Reading the report

- **GitHub review** is the formal `reviewDecision`. **Internal verdict** is this workflow's assessment. Issue comments are neither; the report keeps the three apart.
- Every non-obvious claim carries a tag: `[sim]` simulator output, `[diff]` read from the diff, `[run log]` a CI log opened with `gh run view`, `[tests]` a command run in the worktree, `[GitHub API]` a field from `gh`.
- **Strategy is load-bearing.** This repository lands PRs with merge commits (`repo_landing_convention` is detected from the last five first-parent commits). A PR whose branch contains another open PR's commits lands cleanly after that PR under merge commits, but conflicts under squash and cannot be fixed by retargeting; on 2026-09-03 this was the #8 → #9 pair.
- A passing `sequence` means: every listed PR landed in that order without conflicts, and no listed PR would show another PR's files in its GitHub diff. It does not review content.
- `sim_head` OIDs in the report are scratch commits; they become unreachable after Cleanup and are garbage-collected. Do not cite them as durable.

## 6. Failure modes and recovery

| Symptom | Cause | Recovery |
|---|---|---|
| `{"error": "--root … is not empty and has no .pr-merge-sim-manifest.json"}` | Root points at a directory the tool did not create | Choose an empty or new directory |
| `{"error": "--root … must not be the repository root or a direct child of it"}` | Root collides with feature-worktree space | Use the default or a path outside the repo |
| `{"error": "open PRs missing from --order …"}` | The Order agent omitted a PR | Add it or list it under `--skip` |
| `oid_verified: false` on a PR | Its head moved between `gh pr list` and fetch | The run assesses what was fetched; rerun to pick up the new head |
| `{"error": "… failed … run cleanup --root …"}` | A git or gh command failed mid-run | Run `cleanup --root <dir>`; the manifest records what was created |
| Report says the sequence did not fully land | Real conflict in the proposed order | Read `steps[].conflicted_files` and any `fix_command` (stacked PR after a squash-landed parent) |
| Workflow unavailable | Plan or org setting | Run the helper commands by hand and read the JSON |

`git worktree prune` is not run by the helper. Removing the tool's own worktrees uses `git worktree remove --force` on manifest paths only.

## 7. Editing the script

Run `/workflow-authoring` for the script API. Keep `export const meta` first and a plain literal, or the `/pr-merge-order` command disappears from autocomplete. `Date.now()`, `Math.random()`, and argless `new Date()` throw inside the script. After editing, run `/reload-skills`. Test with `Workflow({scriptPath, resumeFromRunId})` to replay cached agents ([workflows › Edit a saved script](https://code.claude.com/docs/en/workflows#edit-a-saved-script)).

## 8. Tests

Planned: `tests/unit/test_pr_merge_sim.py` (marker `unit`, git binary only) with a fixture bare origin carrying `refs/pull/N/head`, a stub `gh` JSON, and cases for strategy detection, clean and conflicting merges, empty-contained landings, the stacked-pair squash conflict, sequence validation, the rebase fallback, manifest-scoped cleanup, and root refusal. The workflow script is not unit-testable; record one run's journal path as evidence in the PR body.

## 9. Known gaps

- Whether `agentType` applies an agent's frontmatter hooks and `skills:` inside a workflow, and whether project `settings.json` hooks fire in workflow agents, is untested.
- Behaviour inside an `EnterWorktree` session is untested; `REPO` resolves to the worktree when run from inside one.
- The Assess phase re-derives verdicts without `pr-review-standard`; treat its "Internal verdict" as advisory until the guarded assessor exists.
