# Adversary round 1 — against folding `pr-merge-order` into PR #11, and against the tool as built

Repo: `<workspace>/biosciences-mcp`. Analysis began at main @ 29e0cfa; **main advanced to f6ced95 during the analysis** (merges of #10, #8, #9 in that order). PR #11 (head f60e508) is now the **only open PR** and dry-merges onto f6ced95 cleanly.

Tool under review (both untracked): `.claude/workflows/pr-merge-order.js` (250 lines), `scripts/pr_merge_sim.py` (389 lines). `scripts/` has 0 tracked files today, so it is a new top-level directory.

> **Correction (2026-09-04).** The `scripts/` sentence is wrong. It was true only at `29e0cfa`, where the analysis began; PR #10 (`ec59a1d`) — one of the three merges recorded two paragraphs above — added `scripts/validation/` with five tracked files during the analysis. At `f6ced95`, and at every commit since, `git ls-tree -r --name-only f6ced95 scripts/` returns `scripts/validation/{README.md,cq_diff.py,cq_replay.py,wire_diff.py,wire_probe.py}`. Only `.claude/workflows/` is a genuinely new top-level surface.

All experiments ran in a throwaway harness under this scratchpad: `clone/` (clone of the repo), `origin.git/` (bare fake origin with `refs/pull/{8,9,10,11}/head` at the real PR head OIDs), `fakebin/gh` (stub `gh pr list`). Nothing in the real repo was modified except one aborted `git merge --no-commit` dry run on main (state verified clean afterwards). Hook = PR #11's `.claude/hooks/pr-review-guard.py` at f60e508.

---

## Ranked objections

> **Correction (2026-09-04), applies to objection 1.** The heading "the guard can't see it" and the sentence "the hook allows the simulator wholesale" overstate the finding, as `adversary-round2.md` §1 records and the decision record's §8 carries. The guard **denies** the git primitives textually — the nine `DENY` lines in the evidence block below are the proof — and only the `python3` wrapper passes. The accurate claim is narrower and still holds at today's `main`: the hook matches the outer command verb, so interpreter indirection bypasses it.

PR #11's whole premise is "reviewers are read-only by contract … this hook is the enforcement" (`pr-review-guard.py:4-7`); each reviewer's system prompt repeats "never edit, commit, check out, or push" (`agents/pr-review/*-reviewer.md:20-23`). The simulator is built from exactly the primitives that hook denies, yet the hook allows the simulator wholesale because it only pattern-matches the outer `git`/`gh` verb.

**Evidence** — piped through the hook (`exit 0 + empty stdout = allow`):

```
ALLOW  python3 scripts/pr_merge_sim.py discover --limit 30
ALLOW  python3 scripts/pr_merge_sim.py sequence --order 8,10,9,11 --strategy merge
ALLOW  python3 scripts/pr_merge_sim.py cleanup
ALLOW  python3 scripts/pr_merge_sim.py cleanup --root .worktrees        # see #2
ALLOW  git fetch --quiet origin +refs/pull/11/head:refs/pr/11           # creates refs
ALLOW  git -c user.name=pr-merge-sim commit --quiet --no-verify -m x    # `-c` defeats \bgit\s+commit
ALLOW  git update-ref -d refs/pr/11                                     # deletes refs
ALLOW  python3 -c "import subprocess; subprocess.run([\"git\",\"push\"])"
DENY   git worktree add --detach --quiet /tmp/x f60e508    ← pr_merge_sim.py:64
DENY   git worktree remove --force /tmp/x                  ← :62, :325, :354
DENY   git worktree prune                                  ← :357
DENY   git merge --no-commit --no-ff f60e508               ← :74
DENY   git merge --squash f60e508                          ← :104
DENY   git reset --hard --quiet                            ← :77, :108, :238
DENY   git rebase --onto abc def                           ← :299
DENY   git merge-base main f60e508                         ← :151, :180 (already a #11 blocker)
```

So the package would ship a tool whose every constituent command its own guard forbids, and which is runnable only because the guard can't see through `python3`. Two bad outcomes: either reviewers run it (guard is theatre) or the orchestrator runs it, which requires widening `pr-review/SKILL.md:5 allowed-tools` (today a tight list: `Bash(gh pr view:*) … Bash(git worktree:*) Bash(uv sync:*) Bash(mkdir:*)`) with a `Bash(python3:*)`-class grant that also covers arbitrary scripts. Note also that workflow-spawned `agent()` calls are generic subagents; the guard is attached only via the three pr-review agents' frontmatter (`correctness-reviewer.md:9-14`), so nothing in the workflow's Assess phase is guarded at all.

**What would change my mind:** the simulator is documented as an *orchestrator/human* tool with its own permission story (separate PR), the guard gets a positive allowlist rather than a verb denylist, and `pr-review/SKILL.md` states explicitly that reviewers never call it.

### 2. BLOCKING — `cleanup` destroys things it did not create

`cmd_cleanup` (`pr_merge_sim.py:349-357`) iterates `root.glob("*")`, force-removes anything with a `.git`, then `shutil.rmtree` on **every** child regardless of origin. No marker file, no "did I create this" check, no confirmation. The root is user-controlled (`--root`, `PR_SIM_ROOT`, and `--root ${args.root}` unquoted at `pr-merge-order.js:17`). Default root `.worktrees/pr-merge-sim` sits one level below `.worktrees/`, which is where this repo keeps its real feature worktrees (three existed at the start of this analysis: `process-record`, `speckit-upgrade`, `xref-consistency`).

**Evidence (E4, harness):** placed `user-notes.txt`, `user-dir/data.csv`, and a legitimate worktree `my-feature` (branch `my-feature`, uncommitted `wip.py`) under the default root, then ran `cleanup`:

```
before: my-feature pr-10 pr-8 pr-9 scratch-main user-dir user-notes.txt
removed: ['my-feature', 'pr-10', 'pr-8', 'pr-9', 'scratch-main']
after:  user-notes.txt            # user-dir gone; my-feature gone incl. wip.py; branch left dangling
```
(`user-notes.txt` survived only because `rmtree` on a file raises and `ignore_errors=True` swallows it — an accident, not a safeguard.)

**Evidence (E4b):** `cleanup --root .worktrees` (a one-level typo) deleted a foreign worktree `other-feature` with uncommitted `wip.txt`. **Evidence (E4c):** the guard hook allows that exact command.

**What would change my mind:** cleanup removes only paths listed in a manifest it wrote during `prepare`, refuses roots that contain any non-manifest entry, and refuses to run when `root` is not a strict descendant of a directory it created.

### 3. BLOCKING (scope) — It adds a second review domain to a PR already stuck, for a problem that no longer exists here

- PR #11 is request-changes with 4 reproduced blockers, 827 added lines across 10 files (`git diff --stat origin/main f60e508`). Adding the tool makes it ~1466 lines / 12 files, adds two languages (JS + Python) to a Markdown-and-one-hook PR, a new top-level `scripts/` directory, and a new `.claude/workflows/` surface. The reviewers are currently stuck on hook regexes; they would additionally have to review git plumbing semantics (squash vs merge ancestry, `rebase --onto` upstream choice, `--diff-filter=U`).
- The repo's own standard, shipped *in this PR*, says: "Prefer small, self-contained PRs. If a PR bundles unrelated changes, say so once as a Non-blocking finding" (`pr-review-standard/SKILL.md:153-154`) and the PR template it adds says "One coherent change per PR. If this bundles more than one, list them and say why they travel together" (`PULL_REQUEST_TEMPLATE.md:10-12`). A PR that introduces the rule and breaks it on day one is a bad precedent.
- Reviewing a PR is not ordering PRs. `/pr-review` answers "is this diff correct against the ADRs"; the tool answers "in what order do N PRs land". Different inputs (one PR vs all open PRs), different mutators (none vs worktrees/refs), different invocation (skill vs Workflow tool with plan approval).
- **The motivating condition evaporated during this analysis.** `gh pr list --state open` now returns exactly one PR (#11). With one open PR there is nothing to order; the tool cannot be exercised against the repo it ships in until ≥2 PRs are open again.

**What would change my mind:** the tool arrives as its own PR (#12+) after #11 lands, with a PR body that uses the new template's Scope/Evidence sections, so #11's reviewers can close out their 4 blockers without a moving target.

### 4. SERIOUS — `sequence` does not validate the order; the "verified" order is only as complete as the Order LLM

`cmd_sequence` (`pr_merge_sim.py:274-287`) only rejects a number that is not an open PR. It does not check that every open PR is covered, nor that numbers are unique. The workflow (`pr-merge-order.js:203`) feeds *every* proposal entry into `sequence`, including `action: 'hold'` ones, and treats `all_landed` as the pass/fail signal (`:211`).

**Evidence (E2a):** `sequence --order 11 --strategy squash` with 4 PRs open → `all_landed: true`, 3 PRs silently omitted.
**Evidence (E2b):** `sequence --order 11,11,8` → `all_landed: true`; the duplicate lands as `"empty": true`.
**Evidence (E2d):** `sequence --order 9,8` → #9 lands, #8 then fails (its content is already inside #9's squash). In the real flow a `hold` placed early that conflicts flips `all_landed=false`, consumes one of the two re-plan rounds (`:180`), and the report is told to say the simulation "did not fully land" — for a PR nobody intended to land yet. Holds and failures are indistinguishable in the signal.

Consequences: if the Order agent forgets a PR, or emits duplicate steps, the Verify phase confirms the mistake as "lands cleanly" (`:211`). This is the one place in the pipeline where a deterministic check is cheap and it is absent.

**What would change my mind:** `sequence` errors on duplicates and on any open PR missing from `--order` (unless explicitly `--skip N`), and the workflow simulates only non-hold steps while reporting holds separately.

### 5. SERIOUS — Every off-nominal path is a Python traceback with partial state left behind, and an LLM is the error handler

`git()` defaults to `check=True` (`:39`) and `gh_prs` uses `check_output` (`:52`); there is no try/except anywhere. The workflow copes by asking the Discover agent to "return the error text as the title of a single fake PR numbered -1" (`pr-merge-order.js:115-116`).

**Evidence (harness):**
- **E3 — head OID moved between `gh pr list` and fetch:** `CalledProcessError: git worktree add --detach --quiet …/pr-11 1111…` (`:64`), exit 1, **0 bytes of JSON**, 4 `refs/pr/*` and the scratch worktree left behind. The `oid_verified`/"PR moved during fetch" warning in the workflow (`:121-122`) is therefore effectively unreachable: `cmd_discover` uses `p["headRefOid"]` (`:177`) not `fetched_oid`, and the stale OID is not in the local object store, so the crash comes first.
- **E10 — one PR's `refs/pull/N/head` fails to fetch** (`:162`): traceback after the others fetched; 4 `refs/pr/*` left, no JSON, no cleanup.
- **E6 — origin default branch is not `main`:** traceback at `git fetch --quiet origin main` (`:157`). Hard-coded `main` at `:157-158, :83`.
- **E8 — `gh` fails (unauthenticated, or remote is not github.com):** traceback at `:52`.
- **E5 — CI-like environment with no git identity:** the `rebase` fallback (`:299`) does not pass `SIM_IDENT` though `merge`/`commit` do (`:92, :126`) → `Committer identity unknown`. The report then blames the PR for a conflict that is really an environment error.

**What would change my mind:** a single `try/except` that always emits `{"error": …}` JSON, runs cleanup of what `prepare` created, and exits non-zero; identity passed to every write; base branch detected via `git symbolic-ref refs/remotes/origin/HEAD` or `gh repo view --json defaultBranchRef`.

### 6. SERIOUS — Falsified claim: "Works with git >= 2.20" (`pr_merge_sim.py:21`)

`squash_land` uses `git merge --no-verify` (`:96`). `--no-verify` for `git merge` arrived with the `pre-merge-commit` hook in **Git 2.24** (2.24.0 release notes line 38; `v2.24.0/Documentation/git-merge.txt:13` lists `[--no-verify]`; `v2.20.0/Documentation/git-merge.txt` has **no** `--no-verify`). On 2.20–2.23, every merge-strategy landing exits with "unknown option" → `landed: false` for every step → the tool would report every merge order as failing. The claim is not merely off by a version; it inverts the tool's answer on the versions it claims to support. (This machine has 2.34.1, so nothing local catches it.)

**What would change my mind:** the docstring says `>= 2.24`, or the script checks `git --version` on start.

### 7. SERIOUS — Dead metric: pairwise `retarget_hazard_files` is always empty by construction

`pr_merge_sim.py:248-250`: `gh_extra = github_style_diff_files(scratch, sim_head, B) − B.files`. But `B.files` (`:180-181`) is `diff(merge-base(main, B), B)`, which for a stacked B already contains its parent's files; and after squash-landing A, `merge-base(sim_head, B)` is still the old main (the squash commit is not B's ancestor). Both sets are identical → the difference is empty, always.

**Evidence (E1):** 24 pairwise entries, **0 with non-empty `retarget_hazard_files`**, including the real stacked pair (#9 on #8) that the same run correctly flagged as *conflicting* under squash (`docs/speckit-process-record.md`, `docs/speckit-standard-prompt-v2.md`). The Order prompt (`pr-merge-order.js:189-194`) is told to reason from the pairwise data; this field will never fire. The `sequence` variant (`:327`, diffed against `net_files`) is the one that works.

**What would change my mind:** the pairwise version is removed or recomputed against `net_files` of the landed step, as `sequence` does.

### 8. SERIOUS — The Assess phase is a second, weaker `/pr-review`

`pr-merge-order.js:129-165` asks one generic agent per PR for verdict/blockers/claim-checks/tests — the same deliverable as `/pr-review`'s three specialised reviewers — but:
- it never loads `pr-review-standard` (no reference to it anywhere in the .js), so severity, ADR precedence and the finding format diverge;
- it runs unguarded (see #1) yet is told "Do NOT modify files" while being instructed to run `uv sync`/`pytest`/`ruff` in the worktree (`:156-160`) — creating `.venv`, `.ruff_cache`, potentially rewriting `uv.lock`;
- it mandates reading the complete diff, "Do not sample or truncate" (`:146-148`). #11 alone is 44,038 bytes / 898 lines; #9 was 3,659 additions + 1,748 deletions. That is tokens, per PR, per run — and worktrees are deleted at Cleanup so every rerun pays again;
- the two systems will issue different verdicts for the same PR, and the report explicitly puts an "Internal verdict" column next to GitHub's (`:227-228`).

Cost measured honestly: `uv sync -q --extra dev` is **0.75 s warm** and 139 MB per worktree; `pytest -m unit` is **15 s** (510 passed). So the wall-clock objection is weak; the objection is duplicated LLM review work and calibration drift.

**What would change my mind:** Assess consumes `/pr-review`'s existing report (or invokes the `pr-review` skill) instead of re-deriving verdicts; or Assess is dropped and the tool stays purely mechanical (discover → order → sequence).

### 9. MINOR — Platform gating (not "undocumented", but narrow)

Dynamic workflows and the `.claude/workflows/` project location **are** documented (`code.claude.com/docs/en/workflows`, "Save the workflow for reuse"), so the strongest form of this objection fails. What remains:
- "Dynamic workflows are available on all paid plans … On Pro, turn them on from the Dynamic workflows row in `/config`"; orgs can set `disableWorkflows`.
- The `Workflow` tool is **removed from subagents** (`docs/en/sub-agents`, first-filter list), so `/pr-review` run as a subagent, or any agent-team member, cannot invoke it.
- The trigger keyword "doesn't start a workflow when it reaches the session … a prompt passed with `-p` … a webhook payload or pull request comment" — so CI (`claude-code-review.yml`) and headless runs can't use it without allow rules.
- `/workflow-authoring` requires v2.1.248+ (this machine: 2.1.260). Contributors on older clients see a `.js` file they cannot run or edit with tooling.
- `meta.whenToUse` (`pr-merge-order.js:4`) is not among the documented meta keys (`name`, `description`, `phases`); harmless but unverified.

**What would change my mind:** a README line stating the minimum client version and plan, and that the workflow is interactive-only.

### 10. MINOR — Root discovery is cwd-sensitive and sits next to real worktrees

`REPO = git rev-parse --show-toplevel` (`:34`) resolves to the *worktree* when run from inside one (E7: from `pr-8/` the default root becomes `pr-8/.worktrees/pr-merge-sim`), nesting simulator worktrees inside simulator worktrees. Default root under `.worktrees/` (`:35`) is adjacent to the team's feature worktrees, which is what makes #2 a one-typo accident.

### 11. MINOR — Shell injection surface via `args.root`

`pr-merge-order.js:17` interpolates `args.root` unquoted into a prompt that says "Run exactly: …" (`:112, :206, :244`). `{ root: "/tmp/x; rm -rf …" }` becomes a literal instruction to an agent. Untested, but the pattern is the textbook one.

### Not an objection (credit)

`uv run ruff check`, `ruff format --check`, and `pyright` all pass on `scripts/pr_merge_sim.py` under the repo's own config. `sequence` correctly detected the real #8↔#9 squash conflict and the rebase fallback correctly reported a genuine content conflict (I tested the alternative `merge-base` upstream; it conflicts too, so the fallback's upstream choice is not a bug). `detect_strategy` returned `merge`, which matches how this repo lands PRs.

---

## Steelman: why inclusion might still be right

PR #11 sells "evidence-backed review" but gives reviewers no way to test how open PRs interact; the simulator is the only deterministic instrument in the package, and in one run it found the real squash conflict between #8 and #9 and the retarget hazard that bit this repo this week. It passes the repo's lint and type gates today, it never contacts `origin` for writes, and the merge-order question recurs every time two or more PRs are open — which was the state of this repo until an hour ago and will be again. Landing it alongside `/pr-review` lets one set of reviewers see the whole "review → order → land" story and design the trust boundary once, rather than re-opening the guard hook in a second PR; and the blocking items above are all mechanical fixes (a manifest-scoped cleanup, coverage validation in `sequence`, a `try/except`, a corrected version string) that a reviewer could ask for in the same request-changes round the PR is already in.
