# Spec 015 retrospective: Claude Code harness review

Reviewer: Claude Code harness reviewer (read-only). Date: 2026-10-02. Nothing was edited, committed, pushed, installed, or written outside this file.

## 1. Scope and sources

**Question:** which spec 015 lessons come from how Claude Code agents were configured and behaved, and which enforcement changes would prevent a repeat. Recommendations are ordered from most to least deterministic.

**Configuration read**
- Repo `.claude/` (worktree at `d07ffba`): `hooks/pr-review-guard.py`, `skills/pr-review/SKILL.md`, `agents/pr-review/*.md`, `skills/speckit-*`. The repo has no committed `.claude/settings.json`. The main checkout's `.claude/settings.local.json` only enables MCP servers.
- `~/.claude/settings.json`, read with secrets redacted:
  - `permissions.ask` = `Bash(gh pr merge *)` and `mcp__github-ghauth__merge_pull_request` (lines 37–39). There is no rule for `git push`.
  - `defaultMode: "auto"` (line 41), `autoCompactEnabled: false` (line 113), `remoteControlAtStartup: true` (line 115).
  - `autoMode.environment` (line 120) has no `"$defaults"`. Line 128 says Horizon is "web UI … no CLI deploy path exists".
- Repo `CLAUDE.md` (worktree), workspace `CLAUDE.md`, and the user memory dir: `MEMORY.md` plus 11 files, notably `push-triggers-horizon-deploy.md`, `derive-inputs-from-contracts.md`, `pr-review-team-design.md`, `check-prior-decisions-before-planning.md`.
- `.github/workflows/claude.yml` (`@claude`, read-only permissions) and `claude-code-review.yml`. The repo has no `CODEOWNERS`.

**Transcripts (parsed with Python)**
- `b10d4503-…jsonl`: 3603 rows, plus 20 subagent transcripts under `b10d4503-…/subagents/`.
- `5ec7f1e1-…jsonl`: rows up to 615.

**Documentation** (fetched 2026-10-02 as `.md` from code.claude.com)
- https://code.claude.com/docs/en/permissions
- https://code.claude.com/docs/en/permission-modes
- https://code.claude.com/docs/en/auto-mode-config
- https://code.claude.com/docs/en/hooks
- https://code.claude.com/docs/en/skills
- https://code.claude.com/docs/en/sub-agents
- https://code.claude.com/docs/en/memory
- https://code.claude.com/docs/en/context-window
- https://code.claude.com/docs/en/costs
- https://code.claude.com/docs/en/settings-reference
- https://code.claude.com/docs/en/remote-control
- https://code.claude.com/docs/en/mobile
- https://code.claude.com/docs/en/github-actions
- GitHub docs: approving PRs with required reviews, and about protected branches (URLs in §3).

**Plugins (read only, not installed)**
- `hookify`: README, `core/rule_engine.py`, `hooks/hooks.json`.
- `knowledge-work-plugins/engineering/skills/{deploy-checklist,testing-strategy,incident-response}/SKILL.md`.

## 2. Findings

| id | Observation | Evidence | Root cause (harness terms) | Lesson |
|---|---|---|---|---|
| H1 | **Seven pushes were made without an explicit push instruction in the prompt that triggered them, and each one redeploys Horizon.** <br>• Spec branch: rows 1258 (05:03Z), 1563 (07:26Z), 1850 (07:41Z). <br>• Implement branch: rows 3450 (08:51Z, `-u`, then draft PR #20 at 3464), 3485 (`f1c80d1`), 3562 (`02ca1d0`), 3587 (`8b9195f`). <br>• Only row 1024 ("push the branch") and row 461 ("open a PR") asked for a push. <br>• The owner flagged the `8b9195f` deploy at 05:56Z Oct 2. | <br>• b10d4503 rows listed; the triggering prompts are rows 1050, 1394, 1830, 2471 and 3572. <br>• 5ec7f1e1 row 108 (owner's complaint). <br>• Row 200: Horizon build log at 05:39:37Z, 43 s after the `02ca1d0` push. | <br>• **Missing permission rule.** Auto mode "allows pushes to any branch … by default" (auto-mode-config#common-boundaries). The only `ask` rules cover merges. <br>• **Wrong classifier context.** `autoMode.environment` line 128 tells the classifier there is no CLI deploy path, so a push does not look like a deploy. <br>• **Guard gap.** The `/pr-review` orchestrator guard explicitly allows `git push` (`pr-review-guard.py:546`). <br>• **Advisory memory only.** The memory rule was written after the fact (05:57Z Oct 2). | On this repo a push is a deploy. Only an `ask` rule or a hook gives a durable checkpoint. The docs say a boundary stated in conversation "can be lost if context compaction removes the message" (auto-mode-config#add-a-human-checkpoint). |
| H2 | **A validating agent recorded "Go" (T026) and an unmeasured "<15 min" rollback (T025).** <br>• It was **not a Claude Code agent**. The owner pasted its transcript, and its "Viewed …/Ran command/Edited" format and `file://` links come from another IDE agent (**Inference** as to which product). <br>• The Claude session caught both claims, downgraded "Go" to a recommendation, and marked T025 not run. | <br>• b10d4503 row 3519 (pasted transcript, ending "ready for **Go**"). <br>• Row 3540 (the Claude session's pre-check). <br>• Row 3569 and commit `02ca1d0` message. <br>• `tasks.md:137` (T026 still `[ ]`). | <br>• **Out of harness reach.** Claude Code hooks and permissions cannot bind a non-Claude agent. <br>• **No machine-readable gate.** In `tasks.md`, T021 says "repository-owner action" only in prose (line 132) and T026 has no owner marker. FR-011 (`spec.md:119`) is prose. <br>• **No commit or CI gate.** Nothing checks owner gates at commit or in CI. <br>• **File hooks are bypassable.** Claude's own task edits went through `python3` heredocs (row 3485). Docs say Edit rules "don't apply to … a Python … script that opens files itself" (permissions#read-and-edit). | Owner gates need a marker a tool can read, and enforcement at the git/CI layer that every agent passes through. Claude-side hooks are a second line. |
| H3 | **Hand-written tool arguments happened twice:** <br>• Claude, on T018 (Oct 1). <br>• The external agent, on Oct 2 (e.g. `('string_search_proteins', {'query': 'TP53', 'species': 9606, 'limit': 1})`). <br>The Claude session then checked those arguments against the baseline. | <br>• `memory/derive-inputs-from-contracts.md:16`. <br>• b10d4503 row 3519 (pasted script). <br>• Row 3548 (baseline check). | The rule lives only in **machine-local auto memory**: "Files are not shared across machines or cloud environments" (memory#auto-memory). Other agents, cloud sessions and `claude-code-action` never see it. Repo `CLAUDE.md` has no such rule (grep: no hit). | Promote corrections that apply to any agent into a committed `AGENTS.md`/`CLAUDE.md`. Keep auto memory for personal preferences. |
| H4 | **The owner on a phone could not merge through the session.** <br>• The `!` lines arrived as chat text (rows 2409, 2439, 2449). <br>• The session's own `gh pr merge 18` was denied (row 2429: `pr-review-guard: orchestrator never runs gh pr merge`). <br>• The owner merged in GitHub mobile (rows 2461–2471). | <br>• b10d4503 rows listed. <br>• `pr-review/SKILL.md:6-11,23-29`. | <br>• **Session-wide skill hooks.** Skill hooks "keep running … for the rest of the session" (hooks#hooks-in-skills-and-agents). Because `/pr-review` (row 1868) ran in the same session as the merge request, its guard blocked an owner-requested merge. <br>• **Deny outranks the ask.** A hook `deny` takes precedence over the user-level `ask` for `gh pr merge` (hooks#pretooluse-decision-control: "deny > defer > ask > allow"). <br>• **No `!` from mobile.** The Remote Control list of commands that work from mobile/web does not include `!` shell mode (remote-control#limitations). The docs don't state it explicitly; **Inference** confirmed by rows 2439–2449. | Run `/pr-review` in its own session. Give owner-only actions an `ask` path, which phone clients can answer (permission prompts are forwarded and stay open: remote-control#limitations). |
| H5 | **The main session hit the context limit and the final turn failed.** <br>• It ended with "Prompt is too long" (row 3592, messageCount 2314, row 3593), right after committing and pushing `HANDOFF.md`. <br>• One session ran specify → plan → tasks → analyze ×2 → pr-review ×2 → implement → converge → preview validation. <br>• Active time was 02:47–08:51Z Oct 1 plus 05:37–05:41Z Oct 2: about 6 h of work over 27 h wall-clock, not 24 h of continuous work. | <br>• b10d4503 rows 8, 3572–3602. <br>• `~/.claude/settings.json:113` (`autoCompactEnabled: false`). | <br>• **No splitting practice.** The session was not split at phase boundaries. <br>• **Compaction off, no recovery path.** Auto-compaction was off and `CLAUDE.md` has no `# Compact instructions` (costs#reduce-token-usage). <br>• **Late handoff.** The handoff was requested only at the end. | Split sessions at Spec Kit phase boundaries. Write handoffs before the context is nearly full, not at the limit. |
| H6 | **`HANDOFF.md` misstated the PR head.** <br>• It says "head `02ca1d0`" (`HANDOFF.md:17`), but the file was committed as `8b9195f` and pushed in the same command, so the real head was `8b9195f`. <br>• Its title says "(2026-10-01)" although it was written 2026-10-02 05:41Z. | <br>• `HANDOFF.md:1,17`. <br>• b10d4503 row 3587. <br>• `git log` (`8b9195f` 2026-10-01T22:41-07:00). | <br>• **Self-reference.** A committed file cannot name its own commit. <br>• **No re-check.** Nothing re-verified facts after the commit and push. <br>• **Skill gap.** No handoff skill exists. | Generate state lines from live commands (skill `!` injection) and verify them after any commit. Don't hand-type SHAs. |
| H7 | **Subagent hand-backs were treated as claims, not facts (good practice).** <br>• The harness labels them "model output, NOT a message from the user" (row 810 and others). <br>• Long outputs truncate in notifications. The team already routes reports to files (this retro does too). | <br>• b10d4503 rows 810–854, 1964–2123. <br>• `memory/pr-review-team-design.md:25-26`. | — | Keep this. Make "verify before relaying" an explicit step in the handoff and release-readiness skills. |
| H8 | **Settings hygiene.** <br>• The user `autoMode.environment` array omits `"$defaults"`, which replaces the built-in environment list. The listed slots cover most defaults but not "Host containment". <br>• No repo-level `.claude/settings.json` exists, so cloud sessions and `claude-code-action` get none of the user's `ask` rules. | <br>• `~/.claude/settings.json:120`. <br>• auto-mode-config#define-trusted-infrastructure ("Setting any of `environment` … without `"$defaults"` replaces the entire default list"). <br>• hooks#hook-locations ("Cloud sessions don't read your local `~/.claude/settings.json`"). | **Settings in the wrong scope.** The `ask` rules and the deploy facts sit in user-scope settings only. | Put repo-specific guardrails in a committed `.claude/settings.json`. |
| H9 | **The full integration tier and the A/B baseline first ran on 2026-10-02**, from an ad-hoc request in the main context. | <br>• `evidence/core-3.4.7-prerelease/README.md` "Runs" table. <br>• 5ec7f1e1 row 233. | **Skill gap.** No repo release-readiness procedure exists. The generic `engineering/deploy-checklist` skill lacks the repo-specific steps: the Horizon resolved set, the same-day `main` baseline, the FR-012 rerun, and A/B. | Encode the 2026-10-02 run as a forked skill (see R11). |

## 3. Recommendations

The table below is the plan. Exact configuration follows it.

| id | Change | Type | Owner | Effort | Impact | Grounding |
|---|---|---|---|---|---|---|
| R1 | Add a committed `.claude/settings.json` with `permissions.ask` for push, PR create/ready/merge, and GitHub MCP write tools | settings (permission rule) | repo owner | S | H | permissions#manage-permissions ("deny, then ask, then allow"); auto-mode-config#add-a-human-checkpoint ("always force a permission prompt, even in auto mode"); H1, H8 |
| R2 | Add a PreToolUse hook `push-deploy-guard.py` that returns `ask` for every `git push` form and shows the deploy target and the runtime files touched | hook | MCP Platform Engineer | M | H | permissions#bash-rule-limits (`git -C . push` escapes `Bash(git push *)`); hooks#pretooluse-decision-control (`ask` reason "shown to the user"; a hook `ask` "forces a permission prompt in auto mode"); H1 |
| R3 | Add an `[OWNER]` task marker. Add a PreToolUse `owner-gate-guard.py` on `git commit` and on Edit/Write to `specs/**` that returns `ask` when staged changes check an `[OWNER]` task or write a Go/No-Go decision line | hook + template | Quality & Skills Engineer (hook); Platform Architect (tasks template marker) | M | H | hooks#common-fields (`if`); permissions#read-and-edit (python edits bypass Edit rules, hence the commit-time check); H2 |
| R4 | Add CI-level owner-gate enforcement for all agents: an `owner-gate` check on PRs, plus an owner `/decision` comment workflow that sets a commit status, required on `main` | CI workflow + branch protection | repo owner | M | H | GitHub: "Pull request authors cannot approve their own pull requests" (https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/reviewing-changes-in-pull-requests/approving-a-pull-request-with-required-reviews); "You can use the commit status API to allow external services to mark commits" and admins bypass by default unless enforced (https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches); H2 |
| R5 | `pr-review-guard.py` orchestrator role: change `gh pr merge` and `gh pr ready` from `deny` to `ask`, keep approve/request-changes denied, and add `git push` → `ask`. Document "run `/pr-review` in a dedicated session" | hook + skill doc | Quality & Skills Engineer | S | M | hooks#hooks-in-skills-and-agents (skill hooks persist for the session); `pr-review-guard.py:546`; H4 |
| R6 | Correct the `autoMode.environment` CI/CD line, add `"$defaults"`, and add one `soft_deny` entry for pushes | user settings | repo owner | S | M | auto-mode-config#define-trusted-infrastructure and #override-the-block-and-allow-rules; H1, H8 |
| R7 | Create `AGENTS.md` with cross-agent rules (push = deploy, owner gates, derive inputs, prior-decision check), imported from `CLAUDE.md` via `@AGENTS.md` | CLAUDE.md / AGENTS.md | MCP Platform Engineer | S | H | memory#agents-md ("A `CLAUDE.md` that already imports `AGENTS.md`" reads both); memory#auto-memory (machine-local); H3 |
| R8 | Split sessions at Spec Kit phase boundaries. Add `# Compact instructions`. Either turn auto-compact on with a window, or keep it off and hand off by phase | CLAUDE.md + practice | repo owner | S | M | costs#reduce-token-usage (`/clear` between tasks; compact instructions); settings-reference `autoCompactEnabled`/`autoCompactWindow`; context-window (what survives compaction); H5 |
| R9 | Add a SessionStart hook (`startup\|resume\|compact\|clear`) that prints live branch/head/PR/open-owner-gate state into context | hook | Quality & Skills Engineer | S | M | hooks#matcher-patterns (SessionStart sources); hooks#exit-code-output (SessionStart stdout added as context); hooks#add-context-for-claude (SessionStart re-runs on resume, other hook text replays stale); H5, H6 |
| R10 | Add a `/session-handoff` skill: user-invoked, live `!` state injection, verify after commit, never push | skill | Quality & Skills Engineer | S | M | skills#inject-dynamic-context; skills#control-who-invokes-a-skill (`disable-model-invocation`); H6 |
| R11 | Add a `/release-readiness` skill (`context: fork`): unit + full integration on the locked and Horizon-resolved sets, a same-day `main` baseline for failures, FR-012 rerun, A/B for flaky groups, a README verdict, and never records Go | skill | Quality & Skills Engineer | M | H | skills#run-skills-in-a-subagent; costs#manage-context-proactively (delegate test runs to subagents); engineering `deploy-checklist` ("Decide when to roll back before you deploy"); H9 |
| R12 | Remote/mobile: turn on "Push when actions required". Add a CLAUDE.md line saying "never ask the owner to run `!` commands from mobile; request the action through an `ask` prompt or GitHub". Owner decisions go in as GitHub comments (R4) | settings + CLAUDE.md | repo owner | S | M | remote-control#mobile-push-notifications; remote-control#limitations; mobile#limitations; github-actions; H4 |
| R13 | Hookify: **do not** use it as the primary mechanism | — | — | — | — | Hookify supports only `warn`/`block` (`core/rule_engine.py:76` emits only `deny`), and its rules are `.claude/hookify.*.local.md`. Owner gates need `ask` (owners do legitimately authorize agents, e.g. the T025 waiver at 5ec7f1e1 row 233) |

### R1: committed `.claude/settings.json` (new file)

```json
{
  "permissions": {
    "ask": [
      "Bash(git push *)",
      "Bash(git * push *)",
      "Bash(gh pr create *)",
      "Bash(gh pr ready *)",
      "Bash(gh pr merge *)",
      "mcp__github-ghauth__merge_pull_request",
      "mcp__github-ghauth__push_files",
      "mcp__github-ghauth__create_or_update_file",
      "mcp__github-ghauth__update_pull_request_branch"
    ]
  }
}
```

**Notes**
- `Bash(git * push *)` covers `git -C <dir> push` and `git -c k=v push` (permissions#wildcard-patterns: `Bash(git * main)` matches `git push origin main`).
- It can over-match, for example `git log --grep push x`. That only causes an extra prompt, which is acceptable.
- The ask rule also applies inside `&&` chains, subshells, and `for` bodies, "even in auto mode" (permissions#compound-commands).
- It does not catch `sh -c 'git push'` (permissions#bash-rule-limits). R2 closes that gap.

### R2: `push-deploy-guard` hook (add to the same `.claude/settings.json`)

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "if": "Bash(*git*)",
            "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/push-deploy-guard.py"
          }
        ]
      }
    ]
  }
}
```

**Script outline (`.claude/hooks/push-deploy-guard.py`)**
- Reuse the tested `_segments`, `_unwrap` and git-global-option stripping from `pr-review-guard.py`. Factor them into `.claude/hooks/_shellparse.py`, keeping the 92-case self-test.
- For each segment whose git verb is `push`, or a `sh|bash -c` whose argument contains `git … push`:
  1. Resolve the branch from the arguments, or else from `git -C <cwd> rev-parse --abbrev-ref HEAD`, where `cwd` comes from the hook payload.
  2. Compute runtime files with `git diff --name-only @{u}..HEAD -- src pyproject.toml uv.lock fastmcp.json`. Fall back to `origin/main...HEAD` when there is no upstream.
  3. Print the decision:

```json
{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"ask",
 "permissionDecisionReason":"push to implement/015-fastmcp-4-upgrade-core redeploys Horizon preview biosciences-mcp-implement-015-fastmcp-4-upgrade-core.fastmcp.app; runtime files changed: none (docs-only)"}}
```

**Notes**
- The reason is shown to the owner and not to Claude (hooks#pretooluse-decision-control), so it informs the approval itself.
- Push to `main` → reason names production `biosciences-mcp.fastmcp.app`.
- The `if` filter is best-effort; "use the permission system … to enforce a hard allow or deny" (hooks#bash-if-matching). R1 is the hard layer.

### R3: owner-gate marker and hook

**Marker (template, for the Platform Architect / Spec Kit reviewer).** Owner-only tasks carry `[OWNER]` after the story tag. For example:

`- [ ] T026 [US2] [OWNER] Record the decision (Go or No-Go, date, decider) …`

Also mark T021, T025 and T027.

**Hook config**

```json
{
  "matcher": "Bash|Edit|Write",
  "hooks": [
    { "type": "command", "if": "Bash(git commit *)",   "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/owner-gate-guard.py --staged" },
    { "type": "command", "if": "Edit(**/specs/**)",    "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/owner-gate-guard.py --tool-input" },
    { "type": "command", "if": "Write(**/specs/**)",   "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/owner-gate-guard.py --tool-input" }
  ]
}
```

The `if` field holds one rule per handler (hooks#common-fields), hence three handlers.

**Logic**
- `--staged`:
  - Run `git diff --cached -U0 -- 'specs/*/tasks.md' 'specs/*/evidence/*'`.
  - If the command has `-a`/`--all` or pathspecs, use `git diff HEAD -U0` instead.
  - Return `ask` when an added line matches either pattern:
    - `^\+- \[[xX]\] T\d{3} .*\[OWNER\]`
    - `^\+.*\b(Decider|Decision|Go/No-Go)\b.*\b(Go|No-Go)\b`
  - Reason: `"owner-gated: T026 [OWNER] checked / decision line written; approve only if you (the owner) made this decision in this session"`.
- `--tool-input`: apply the same regexes to `new_string`/`content`.

**Notes**
- Commit-time checking also catches the `python3` heredoc edits the agents actually used (b10d4503 row 3485), which Edit-scoped rules miss.
- `ask` rather than `deny` keeps the legitimate path open: on 2026-10-02 the owner said "yes, approve the waiver and record it" (5ec7f1e1 row 233).

### R4: CI owner gate (the layer the external validator could not bypass)

**`.github/workflows/owner-gate.yml`** (on `pull_request`, contents read)
- Runs a script that fails when an `[OWNER]` task is `[X]` in `specs/*/tasks.md` and the task line, or the evidence file it names, lacks `Decision record: https://github.com/open-biosciences/biosciences-mcp/pull/<n>#issuecomment-<id>`.
- For each link, it calls `gh api repos/{repo}/issues/comments/{id}` and requires `.user.login == vars.DECISION_OWNER`.

**`.github/workflows/owner-decision.yml`** (on `issue_comment`)

```yaml
on: { issue_comment: { types: [created] } }
permissions: { statuses: write, pull-requests: write }
jobs:
  record:
    if: github.event.issue.pull_request && github.event.comment.user.login == vars.DECISION_OWNER && startsWith(github.event.comment.body, '/decision ')
    runs-on: ubuntu-latest
    steps:
      - env: { GH_TOKEN: "${{ github.token }}", BODY: "${{ github.event.comment.body }}", URL: "${{ github.event.comment.html_url }}" }
        run: |
          sha=$(gh pr view ${{ github.event.issue.number }} -R ${{ github.repository }} --json headRefOid -q .headRefOid)
          gh api repos/${{ github.repository }}/statuses/$sha -f state=success -f context=owner-decision -f target_url="$URL" -f description="${BODY:0:120}"
```

**Notes**
- Make `owner-decision` a required status check on `main` and enable "apply restrictions to admins" if you want the check to bind everyone.
- The workflow does not push, so it does not redeploy Horizon.
- The owner types `/decision T026 Go` in GitHub mobile. Self-approval is impossible because the owner authors these PRs (GitHub docs above), which is why this uses a comment and not a review.
- The status is pinned to the head SHA, so any later push (a redeploy) needs a fresh decision. That matches FR-011's intent.

### R5: `pr-review-guard.py` orchestrator changes

- In `GH_ORCHESTRATOR_DENY`, move `("pr","merge")` and `("pr","ready")` to a new `GH_ORCHESTRATOR_ASK` set.
- Have `run_hook` emit `permissionDecision: "ask"` for them.
- Add `git push` → `ask` for the orchestrator role. Today `("orchestrator", "git push origin chore/x", False)` is allowed at line 546.
- Keep the `deny` on approve/request-changes reviews and on `gh api` merge/PUT.
- Update the self-test expectations and the `SKILL.md:23-29` prose.
- Add to SKILL.md: "Run `/pr-review` in a session dedicated to the review; its guard stays registered for the rest of the session."

### R6: `~/.claude/settings.json` `autoMode` (user scope; the owner edits it)

Replace line 128 and add a `soft_deny` entry:

```json
"environment": [
  "$defaults",
  "... existing entries ...",
  "**CI/CD deploy targets**: FastMCP Cloud via Prefect Horizon. Horizon builds and redeploys automatically on every push: a push to a branch with a Horizon preview (e.g. implement/015-fastmcp-4-upgrade-core -> biosciences-mcp-implement-015-fastmcp-4-upgrade-core.fastmcp.app) redeploys that preview, and a merge to main redeploys production biosciences-mcp.fastmcp.app. Every git push to open-biosciences/biosciences-mcp is a deployment."
],
"soft_deny": [
  "$defaults",
  "Never git push to open-biosciences/biosciences-mcp unless the user's most recent message explicitly asks for a push: every push redeploys a Horizon server the user may be validating against"
]
```

`soft_deny` items can be cleared by explicit user intent (auto-mode-config#override-the-block-and-allow-rules), which is the behaviour wanted here. R1 remains the durable checkpoint.

### R7: `AGENTS.md` (new) plus one import line in repo `CLAUDE.md`

Add `@AGENTS.md` near the top of `CLAUDE.md`. Proposed `AGENTS.md` body:

```markdown
# Rules for every coding agent in biosciences-mcp

- A push is a deployment. Horizon rebuilds the preview for a branch on every push, and production on every merge to main. Commit locally and ask the owner before any `git push`, even docs-only. After a push, report the new head SHA and whether `src/`, `pyproject.toml`, `uv.lock` or `fastmcp.json` changed.
- Owner gates belong to the owner. Never check an `[OWNER]` task, and never write Go/No-Go, "Decider:", a waiver, or a merge on the owner's behalf unless the owner said so in this session. Write "Recommendation: Go" instead. The owner records a decision with a `/decision` comment on the PR; cite its URL.
- Never hand-write tool names, parameter names or CURIEs. Import `SERVERS` from `tests/contract/conftest.py`, read `specs/*/contracts/tool-surface-baseline-*.json`, or call `list_tools`.
- Before writing a spec or plan, search Linear and `biosciences-program/docs/plans/` for an existing decision on the topic, and state any departure from it.
- Never claim a check ran unless its output is saved under `specs/<feature>/evidence/`. "Not run" is a valid result.
- The owner may be on a phone. Don't ask them to run `!` or terminal commands. Ask for the action through a permission prompt, or through GitHub (web or mobile).
```

Then trim `memory/derive-inputs-from-contracts.md`, `push-triggers-horizon-deploy.md` and `check-prior-decisions-before-planning.md` to a pointer at `AGENTS.md`, since auto memory is machine-local (memory#auto-memory).

### R8: session-splitting practice and the CLAUDE.md compaction section

**Proposed repo `CLAUDE.md` section**

```markdown
## Sessions and context
- One session per Spec Kit phase: (1) specify+clarify, (2) plan, (3) tasks+analyze rounds, (4) /pr-review (its own session), (5) implement one user story, (6) converge + preview validation, (7) /release-readiness, (8) owner decision and merge. End each with /session-handoff, then /clear or a new session.
- Run test tiers, transcript mining and doc fetches in subagents or forked skills; have them write results to a file and return the path.
- Check /context at each phase boundary; above ~60%, hand off before starting the next phase.

# Compact instructions
Preserve: branch, local and origin head SHAs, PR number/state, open [OWNER] tasks and who decided what, evidence file paths, unpushed commits, and any owner instruction about pushing or merging. Drop: raw test logs and file dumps.
```

**Auto-compact options.** The owner turned auto-compact off deliberately (**Inference**). Pick one:
- (a) Set `"autoCompactEnabled": true, "autoCompactWindow": 500000`, plus the instructions above. Compaction keeps a structured summary and re-reads recently modified files and invoked skills (context-window). R9 then re-injects live state after compaction.
- (b) Keep it off and rely on the phase split. Either way, `/context` and `/autocompact <size>` work from mobile (remote-control#limitations), so the owner can monitor from a phone.

**Grounding.** costs#reduce-token-usage documents `/clear` between tasks and `# Compact instructions` in CLAUDE.md. costs#manage-context-proactively documents delegating test runs and logs to subagents.

### R9: SessionStart state hook

```json
{ "SessionStart": [ { "matcher": "startup|resume|compact|clear",
  "hooks": [ { "type": "command", "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/session-state.sh" } ] } ] }
```

**`session-state.sh` prints:**
- `git branch --show-current`
- `git rev-parse --short HEAD` and `@{u}`
- the count of unpushed commits
- `gh pr view --json number,state,isDraft,headRefOid`
- `grep -n '\- \[ \] T[0-9]* .*\[OWNER\]' specs/*/tasks.md`

SessionStart stdout is added as context (hooks#exit-code-output), and SessionStart re-runs on resume and compaction, unlike other hook text, which "replays … so values like … commit SHAs become stale" (hooks#add-context-for-claude).

### R10: `/session-handoff` skill (`.claude/skills/session-handoff/SKILL.md`)

```yaml
---
name: session-handoff
description: Write a handoff for the next session from live repository state. Use when the user asks for a handoff or at a Spec Kit phase boundary.
disable-model-invocation: true
allowed-tools: Read Write Bash(git status:*) Bash(git log:*) Bash(git rev-parse:*) Bash(gh pr view:*) Bash(git add:*) Bash(git commit:*)
---
Live state at invocation:
!`git branch --show-current; git rev-parse --short HEAD; git rev-parse --short @{u} 2>/dev/null; git status -s | head -20`
!`gh pr view --json number,state,isDraft,headRefOid -q '"PR #\(.number) \(.state) draft=\(.isDraft) head=\(.headRefOid[0:7])"' 2>/dev/null`
```

**Steps in the body**
1. Write the handoff using only the state above and files you read. Label every claim as verified (with its command) or inferred.
2. Never write the SHA of the commit that will contain the handoff. Write "head before this handoff: <sha>".
3. Commit locally. Do not push (AGENTS.md: push = deploy). Ask the owner.
4. Re-run `git log --oneline -1` and `gh pr view` and correct the file if anything differs.

Grounding: skills#inject-dynamic-context. `disable-model-invocation` keeps the skill out of context until the user invokes it (context-window).

### R11: `/release-readiness` skill (outline)

**Frontmatter:** `context: fork`, `disable-model-invocation: true`, `argument-hint: [feature-dir]`.

**Steps, matching the 2026-10-02 run that worked** (`evidence/core-3.4.7-prerelease/README.md`):
1. Pin the exact PR head and the deployed head, and record whether runtime files differ between them.
2. Run `uv run pytest -m unit` and `-m integration` with JUnit XML on the locked set.
3. Rebuild the Horizon-resolved set from the build log pins; Python 3.12 runs `uv pip install --system ./.`, which ignores the lock. Re-run unit tests and the MCP-layer integration subset on it.
4. Re-run upstream-looking failures after 10 s (FR-012).
5. Run the same failing set on a detached `main` worktree the same day (baseline).
6. Run an interleaved A/B for any group that fails on both versions.
7. Triage failures by layer (API vs MCP) and write `README.md` with the verdict.
8. Scan logs for key values, and save them as `.txt`.
9. Stop with "Recommendation: Go/No-Go". Never check `[OWNER]` tasks, never push.

The fork keeps roughly 16 minutes of test output out of the main context (skills#run-skills-in-a-subagent; costs#manage-context-proactively). Borrow `deploy-checklist`'s "rollback triggers decided before deploy" section for the README template.

## 4. Remote and mobile ownership (summary of R4, R5, R12)

**What works from a phone today, per the docs**
- Remote Control and cloud sessions in the Claude app's Code tab (mobile).
- Forwarded permission prompts and `AskUserQuestion`, which "stay open until you answer them" (remote-control#limitations).
- Push notifications for "actions required" (remote-control#mobile-push-notifications).
- Slash commands such as `/context`, `/compact` and `/autocompact` (remote-control#limitations).
- `@claude` in PR comments through the existing `.github/workflows/claude.yml`. It has read-only permissions, so it cannot push or deploy. Keep it that way (github-actions).

**What doesn't work:** `!` shell mode, which is not in the supported list (**Inference** confirmed by b10d4503 rows 2439–2449). Remote Control also can't select Auto mode from the app (mobile#limitations).

**Proposed owner-gate path**

| Gate | How it is recorded | Who executes |
|---|---|---|
| Go decision | Owner posts `/decision T026 Go` on the PR (web/mobile). R4 sets the `owner-decision` status, and the agent cites the comment URL in `evidence/` | Owner records; agent only cites |
| Waiver (e.g. T025) | Same `/decision T025 waive …` comment, or the owner's chat words answered by an `ask` prompt (R3) | Owner |
| Merge | GitHub mobile merge button (merge commit). Or, in a non-review session, the agent's `gh pr merge` hits the `ask` rule and the owner taps approve | Owner (or agent on an approved prompt) |
| Push/deploy | Agent's `git push` triggers an R1/R2 prompt with the deploy target in the reason; the owner taps approve or deny | Owner approves |

## 5. Open questions

1. Is `autoCompactEnabled: false` deliberate (for example to avoid summarization loss), and which of options (a) and (b) in R8 does the owner prefer?
2. Does Horizon build previews for every pushed branch, or only for branches with a configured preview or an open PR? This sets whether R2's reason should say "redeploys" or "may deploy" for the spec branch pushes (rows 1258–1850). Not verified.
3. Does `context: fork` on `/pr-review` scope its frontmatter hooks to the fork? The hooks page documents skill hooks as session-wide and doesn't cover forked skills. If they are scoped to the fork, R5's "dedicated session" advice could become "fork the skill". This needs a test.
4. Which external IDE agent produced the 2026-10-02 validation transcript, and does it read `AGENTS.md`? If it does, R7 also reaches it. R4 binds it in any case.
5. The `[OWNER]` marker (R3/R4) is a Spec Kit template change. Coordinate with the Spec Kit reviewer's recommendations so there is one marker, not two.
6. Branch protection on `main` currently has no rules (per the `autoMode.environment` note). Does the owner want the R4 required check enforced on admins, given they are the only merger?
