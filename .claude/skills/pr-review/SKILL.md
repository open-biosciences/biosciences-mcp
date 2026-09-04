---
name: pr-review
description: Review a biosciences-mcp pull request with the three-reviewer team (ADR compliance, wire contract, correctness), verify and merge their findings into one evidence-backed report, and optionally post it to the PR. Use when asked to review a PR, a branch, or the current changes against the ADRs.
argument-hint: [pr-number | branch | base...head] [--comment]
allowed-tools: Read Grep Glob Agent Bash(gh pr view:*) Bash(gh pr diff:*) Bash(gh pr comment:*) Bash(gh api:*) Bash(git fetch:*) Bash(git diff:*) Bash(git show:*) Bash(git merge-base:*) Bash(git rev-parse:*) Bash(git worktree:*) Bash(git log:*) Bash(uv sync:*) Bash(mkdir:*)
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/pr-review-guard.py --role orchestrator"
---

# /pr-review

Run the review team on `$ARGUMENTS`. You are the orchestrator: you scope the
change, brief three specialist reviewers, run them in parallel, verify what
they return, and write one report. You do not review the diff yourself; the
reviewers' contexts hold the diff so yours stays small. Load the
`pr-review-standard` skill for the precedence order, severity levels, and
finding format before you start.

Never approve, request changes, or merge on GitHub. The team informs a human
decision; it does not make it. The `hooks` entry above registers the guard in
orchestrator mode, which denies `gh pr review`, `gh pr merge`, and any
`gh api` call that approves, requests changes, merges, or otherwise mutates;
it leaves git alone. Skill hooks persist for the rest of the session, so
those GitHub actions stay blocked for Claude until the session ends. Hooks
declared in project frontmatter run only after the workspace is trusted and
are skipped in `-p` sessions; a headless run relies on the prompts alone.

## 1. Resolve the target

Parse `$ARGUMENTS`:

- A number, `#N`, or a PR URL: review pull request N.
- A branch name: review `origin/main...<branch>`.
- `base...head`: review that range.
- Nothing: review the current branch against `origin/main`, including
  uncommitted changes, and say so.
- `--comment`: post the merged report to the PR when finished (PR targets
  only).

For a PR target:

```
gh pr view N --json title,body,baseRefName,headRefName,files,isDraft,url
git fetch origin pull/N/head
git rev-parse FETCH_HEAD                          # HEAD_SHA
git merge-base origin/<baseRefName> FETCH_HEAD    # BASE_SHA
```

Run these as plain, separate commands and carry the SHAs forward as
literals. A worktree-isolated session refuses git commands wrapped in
`$(...)`, loops, or heredocs, so do not compose them.

For a branch or range, compute `BASE_SHA` and `HEAD_SHA` with
`git merge-base` and `git rev-parse`. Skip a draft PR unless the user asked
for it explicitly, and say that you skipped it.

## 2. Build the scratch tree

Create a detached worktree at `HEAD_SHA` under the session scratchpad so
reviewers can read head files and run tests without touching the working
tree:

```
git worktree add --detach <scratchpad>/pr-review/<target> <HEAD_SHA>
uv sync --extra dev -q --project <scratchpad>/pr-review/<target>
mkdir -p <scratchpad>/pr-review/<target>-reports
```

Reports go in the sibling `<target>-reports` directory, never inside the
worktree, because the worktree is deleted at the end. If `git worktree add`
is refused, fall back to `git show HEAD_SHA:path` for head files and tell the
reviewers that tests cannot run on the head.

## 3. Classify the change

From the changed file list and `git diff --stat BASE_SHA..HEAD_SHA`, decide
which reviewers run. Use behaviour, not just paths, and err toward running
a reviewer when unsure.

| Reviewer | Runs when |
|---|---|
| `adr-compliance-reviewer` | Always |
| `wire-contract-reviewer` | Any file under `src/biosciences_mcp/models/`, `src/biosciences_mcp/servers/`, `src/biosciences_mcp/clients/`, or `tests/contract/` changed, or the PR body mentions tools, envelopes, cross-references, or CURIEs |
| `correctness-reviewer` | Any `.py`, `.sh`, `.yml`, `.yaml`, or `.toml` file changed |

A docs-only PR therefore gets the ADR compliance reviewer alone. Say which
reviewers you dispatched and why.

## 4. Brief and dispatch

Write one brief and send the same brief to every reviewer you dispatch, in
a single message with multiple `Agent` calls so they run concurrently. Use
the agent names above as `subagent_type`. The brief contains:

```
PR: <number and URL, or range>
Title: <title>
BASE_SHA: <sha>
HEAD_SHA: <sha>
PR_TREE: <path>   (dependencies synced; run uv commands from here)
REPORT_PATH: <scratchpad>/pr-review/<target>-reports/<reviewer-name>.md
Changed files (<count>):
<one path per line, with +/- counts>
PR body:
<verbatim body>
Focus: <one or two sentences on what this PR claims to do and any area you want the reviewer to weigh>
```

Do not include your conversation history. Do not pre-judge findings in the
brief.

Give each reviewer its own `REPORT_PATH` (one file per reviewer) and tell it
to reply with only the path and its `Recommendation:` line.

## 5. Verify and merge

When all reviewers return, read each `REPORT_PATH` with the Read tool.
The reviewer's final message is only a pointer; the file is the report,
and messages longer than a few paragraphs are truncated in transit.

1. **De-duplicate.** Two findings at the same `path:line` with the same
   claim become one, keeping the higher severity and citing both reviewers.
2. **Verify every Blocking finding yourself.** Open the cited line with the
   Read tool on `<PR_TREE>/path` (use `offset` and `limit`) and confirm the
   quoted observation matches. If it does not, downgrade or drop it and say so.
   If a Blocking finding rests on a command result, confirm the reviewer
   reported the command's summary line.
3. **Apply the evidence bar.** Drop any Blocking or Non-blocking finding
   without a `path:line`, without an authority or executable evidence, or
   with confidence under 80.
4. **Cap nits at five.** Keep the five most useful; report the rest as a
   count.
5. **Collect governance notes** from all reviewers into one list and
   de-duplicate against section 2 of the standard.
6. **Decide the recommendation** from the surviving findings: any Blocking
   finding means `request changes`; only Non-blocking or nits means
   `approve with non-blocking`; nothing means `approve`. The reviewers'
   own recommendations inform this but do not override it.

## 6. Report

Write the report in this order. Keep it short by leaving things out.

```
# PR review: <title> (#N)

<One-line tally: N blocking, N non-blocking, N nits, N pre-existing. Lead with "No blocking findings" when true.>

Recommendation: <approve | approve with non-blocking | request changes>. <one sentence>

## Blocking
<finding blocks, or "None">

## Non-blocking
<finding blocks, or "None">

## Nits
<up to five, one line each, plus "and N more" if capped>

## Pre-existing
<finding blocks, or "None">

## Governance notes
<bullets, or "None">

## Coverage
Reviewers: <names>
Examined: <merged list>
Not examined: <merged list with reasons>
Commands run: <command and summary line, one per line>
```

Print the report in the conversation. Then remove the scratch worktree you
created in step 2, with its literal path:
`git worktree remove --force <scratchpad>/pr-review/<target>`. Remove only
that worktree; other sessions may hold worktrees of the same branch, and
they are not yours to clean up. The reports directory stays.

## 7. Post to the PR (only with `--comment`)

Post the report as one top-level comment:

```
gh pr comment N --body-file <report path>
```

For each Blocking and Non-blocking finding that cites a line inside the
diff, also post an inline review comment. Write a JSON body to a scratch
file with `event: "COMMENT"` and a `comments` array of
`{path, line, side: "RIGHT", body}` entries, then:

```
gh api repos/{owner}/{repo}/pulls/N/reviews --input <json path>
```

Never use `APPROVE` or `REQUEST_CHANGES` as the event. If an inline comment
is rejected because the line is outside the diff, keep it in the top-level
comment and say so. Without `--comment`, post nothing.
