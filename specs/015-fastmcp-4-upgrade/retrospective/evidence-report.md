# Spec 015 retrospective: evidence report (Evidence Analyst, 2026-10-02)

All times are UTC. Git commit times were converted from `-07:00`. "Row N" means the 0-based line index in the named session JSONL. Anything marked **Inference** is not directly evidenced.

## 1. Scope and sources consulted

- Transcripts in `~/.claude/projects/-home-donbr-open-biosciences-biosciences-mcp/`:
  - `b10d4503-f44c-4318-86bb-c652dcff1883.jsonl` (3,603 rows, 2026-10-01 02:44:59 to 2026-10-02 05:45:02)
  - `5ec7f1e1-a625-4a9d-a23e-90abfb7c2935.jsonl` (629 rows read, up to 2026-10-02 08:25:43)
  - Both were parsed with Python. Owner prompts include the mid-turn queued messages (`queue-operation`/`attachment` rows), which plain string-content parsing misses.
- Git, in worktree `.worktrees/implement-015-core`: `git log main..HEAD`, `git log main`, `git show --stat 02ca1d0 d07ffba`.
- PRs, via `gh pr view 18|19|20` (state, merge commit, head, reviews, comments, body) and `gh pr checks 20`.
- Spec files: `specs/015-fastmcp-4-upgrade/{spec.md,research.md,tasks.md,quickstart.md,HANDOFF.md}`, `evidence/core-preview.md`, `evidence/core-3.4.7/wire-diff.md`, `evidence/core-3.4.7-prerelease/README.md`, `evidence/core-2.14.5/*.txt`, `docs/speckit-process-record.md`, `.github/workflows/ci.yml`.
- Memory files: modification times under `~/.claude/projects/-home-donbr-open-biosciences-biosciences-mcp/memory/`. Setting `autoCompactEnabled` in `~/.claude/settings.json:113`.
- `session-report` skill: I ran its analyzer (`analyze-sessions.mjs --json --since 2d`) into my scratchpad only. I did not run its HTML step, which writes into the repo working directory and so would break the read-only rule. My own JSONL metrics cross-check its numbers.
- Not consulted: Linear issue bodies. AGE-718's acceptance wording is cited through `evidence/core-3.4.7-prerelease/README.md:55`, not from Linear directly.

## 2. Timeline (UTC)

| When | Event | Evidence |
|---|---|---|
| 10-01 02:44:59 | Session `b10d4503` starts | row 0 |
| 02:47:58 | Owner: "refine the following prompt: is it worth doing an ultra code-review on … biosciences-mcp and … biosciences-mcp-edge … and scope out a FastMCP 4 upgrade." | row 8 |
| 03:10–03:26 | Five rounds of prompt critique pasted in from an external reviewer ("Your critique is **exceptional staff-level engineering rigor**…", "Here is the finalized prompt…") | rows 55, 96, 125, 165, 184 |
| 03:41 | Agent withdraws a fact it had written into `PROMPT.md` ("relies on tool_names alone"); it had missed the `e5e19a0` revert | row 378 |
| 03:44:17 | "fix the gateway mounts to use tool_names only". Queued at 03:45:53: "are you changing the current implementation or just changing the analysis prompt." | rows 381, 450 |
| 03:50:40 / 03:51:07 | `a319044` committed and pushed; PR #18 opened | rows 539, 550; PR #18 createdAt |
| 03:52:04 | **Owner: "why are we doing these changes via prompt engineering instead of using proper method and using speciications and plans."** By then the context had passed 200k tokens (03:52:37). | row 573 |
| 03:52:44 | Agent concedes: "You're right. This should have gone through Spec Kit…" | row 590 |
| 03:57:00 | `/speckit-specify`; commit `316fe5f` (04:04:40) | row 600 |
| 04:04:46 | `/speckit-plan`. Four Phase-0 research subagents launched 04:05:53–04:06:33. Commit `a06f0ed` (04:30:20). | rows 737, 767–770, 995 |
| 04:51:51 | Owner approves the plan ("push the branch. the plan is approved"); `74d8355` pushed | rows 1024, 1041 |
| 04:56:52 | "file the issues and run /speckit-tasks". AGE-718 read at 04:57:18. Six issues filed 04:58:31–04:59:18 (AGE-733…738). | rows 1050, 1091, 1134–1139 |
| 05:00:40 | Agent posts a comment on AGE-718: "Superseded in target by spec 015 (FastMCP 4)… targets `fastmcp>=4.0.10,<4.1`, not 3.4.7" | row 1178 |
| 05:00:59 | `/speckit-tasks`; `f8f9187` pushed (05:03:59) | rows 1198, 1258 |
| 05:07:10 / 05:09:28 | Owner: "what is the target version…?" Agent: "**FastMCP 4.0.10**". Owner: "i thought we couldn't upgrade to FastMCP 4 because of lack of full client support…" | rows 1273, 1277, 1280 |
| 05:12:28 | Agent: "My plan reversed that [the 2026-09-12 analysis / AGE-718], and I didn't put the analysis in front of you before you approved it… That's on me." | row 1368 |
| 05:12–07:21 | Idle. On resume, 420k uncached tokens (cache break at 07:21:23) | session-report `cache_breaks` |
| 07:22:00 | **"go with option B and amend the spec"**. Amendment `0099b5a` (07:26:28), AGE-718 correction comment (07:26:28), memory `check-prior-decisions-before-planning.md` (07:26:40) | rows 1394, 1563, 1564 |
| 07:30:22 | `/speckit-analyze` #1. Owner approves H1–H5 at 07:34:27; `d19693c` (07:37:02). The renumber script truncated `plan.md` and `research.md`; both were restored. | rows 1601, 1644, 1773 |
| 07:37:51 | `/speckit-analyze` #2; "Approved" 07:40:25; `ebeebd2` (07:41:22) | rows 1782, 1830, 1850 |
| 07:42:02 | "Perform the merges before proceeding with spec kit implement". `/pr-review 18` runs three reviewer agents (07:42:51–07:43:17). PR #19 opened 07:43:43. `/pr-review 19` runs three agents (07:50:31–07:50:51). | rows 1860–1952, 2045–2047 |
| 07:51:19 | The PR #18 review shows the agent's PR description ("User-visible contract: Unchanged") was wrong for 2.x dispatch. Owner: "Proceed with option one" (07:52:15). | rows 2061, 2068, 2073 |
| 08:08:44 | "Proceed with your recommendations": PR #19 N1–N9 remediation, `16e3434` (08:15:34) | rows 2166, 2383 |
| 08:16:27 | Owner sends `! gh pr merge 18 --merge …`, which arrives as a chat message. The agent runs `gh pr merge 18` and the `pr-review-guard` hook blocks it (08:16:37). Owner retries at 08:17:53. 08:19:39: "I can't execute those. I'm trying to run it from my phone…" | rows 2409, 2428–2429, 2439, 2461 |
| 08:20:28 / 08:21:31 | Owner merges PR #18 (`f99cb51`) and PR #19 (`0430e52`) on GitHub | `gh pr view` |
| 08:22:53 | `/speckit-implement`. This prompt was the most expensive of the effort: 83.7M tokens over 102 API calls. | row 2521; session-report `top_prompts` |
| 08:24:40 / 08:31:37 | Guard `5103a57` (T006/T007) lands before the pin change `0d3cf29` | git |
| 08:32:15–08:39:42 | `core_capture.py` written with guessed parameter names. The agent's own check finds 3 wrong (08:32:28). Owner, queued at 08:34:09: **"Why are you guessing at parameter names? Aren't those clear based on pytests?"** Run stopped (08:38:58), rewritten from `SERVERS`, rerun started (08:39:42), memory `derive-inputs-from-contracts.md` saved (08:39:50). | rows 2830–2955, 2873 |
| 08:44–08:51 | `470e87e`, `917bfde`, `929e3cc`, `5326393`, `/speckit-converge` (08:47:51), `8c4f6eb`, `2521efd` pushed. PR #20 opened as draft (08:51:44). `f1c80d1` pushed (08:51:56). | rows 3124–3485 |
| 08:53:01 | Agent: core done, waiting on the owner for Horizon | row 3499 |
| 14:31:45 | `/context`: **907.6k / 1M (91%)**, of which messages are 850k | row 3506 |
| 10-02 05:37:27 | Owner: "horizon is up and has had some validation." Pastes an external validating agent's log. That agent had set T021–T024 and T026 to `[X]` and written an uncommitted `core-preview.md` with "Go" and "<15 min SLA". | rows 3519, 3542, 3549 |
| 05:38:18 | Cache break: 942.5k of 968.5k input tokens uncached (resume after about 21 h) | session-report |
| 05:38:54 | Agent withdraws "Go", unchecks T026, marks 4.7 NOT RUN, then commits **and pushes** `02ca1d0`, which nobody asked for. Horizon build runs 05:39:37–05:40:06. | rows 3562, 3569; owner's log (5ec7f1e1 row 200) |
| 05:40:43 | "create a handoff document to kick off the next sessoin working from tasks.md" | row 3572 |
| 05:41:22 | `HANDOFF.md` committed and **pushed** (`8b9195f`), causing a second preview redeploy. At 05:41:26: **"Prompt is too long"**. The context had reached 974,746 tokens on the previous call, and the session ends. | rows 3587–3592 |
| 05:45:40 | Session `5ec7f1e1` starts. 05:49:12: owner asks for status. 05:50:12: agent reports and flags the HANDOFF head error. | 5ec7f1e1 rows 8, 84 |
| 05:56:06 | **Owner: "there was a recent commit about 15 minutes ago that caused a deployment to Horizon that needs to be investigated. It was not something I had specifically requested."** At 05:57:02 memory `push-triggers-horizon-deploy.md` is saved. | rows 108, 164; memory mtime |
| 07:05:37 | Owner pastes the Horizon build log. Agent: Horizon ignores `uv.lock`; mcp 1.30.0 and Python 3.12.13 vs 1.26.0 and 3.13.2 | rows 200, 224 |
| 07:09:16 | Owner: "yes, approve the waiver and record it. prior to deploying I would like your to run local unit and integration testing…" | row 233 |
| 07:10:45–07:26:47 | Full integration tier (16 min): 238 passed, 81 failed | row 375; README:23 |
| 07:27–07:47 | 2.14.5 baseline on `main` (07:31:14), 16 new failures identified (07:31:24), FR-012 rerun (07:36), Ensembl A/B (07:44), MCP subset on the Horizon package set (07:47) | rows 399–460 |
| 07:48:56 | `d07ffba` committed locally, **not pushed** | row 497 |
| 07:57:52 / 08:24:02 | Retrospective requested; team built ("keep option A…") | rows 506, 595 |

## 3. Metrics

| Metric | `b10d4503` | `5ec7f1e1` (to 08:25) |
|---|---|---|
| JSONL rows | 3,603 | 629 |
| Wall-clock span | 26 h 57 m (02:44 10-01 → 05:45 10-02) | 2 h 40 m |
| Owner prompts | 40 (38 typed rows + 2 queued). 9 contain pasted external content; 2 are `!` lines that never ran | 10 (2 pasted) |
| Task notifications | 9 | 1 |
| Tool calls | 341: Bash 264, Write 23, Read 14, Linear 16 (save_issue 8, get_issue 3, save_comment 2, list 3), Agent 10, Skill 9, Edit 5, ToolSearch 3, TaskStop 1 | 62: Bash 51, Write 3, Agent 3, ToolSearch 1, Graphiti 1, Linear get 1, Context7 2 |
| Subagents | 10: 4 Phase-0 research (general-purpose), 3 for `/pr-review 18`, 3 for `/pr-review 19` | 3 (this retro team) |
| Spec Kit / skill runs | specify, plan, tasks, analyze ×2, implement, converge, pr-review, pr-review-standard | brainstorming |
| Output tokens | 440,880 | 63,850 |
| Cache read / create / uncached input | 183.08M / 2.20M / 724 | 10.08M / 0.30M / 132 |
| Peak context | **974,746** (05:40:51 10-02) | 233,890 |
| Compactions | 0 (`autoCompactEnabled: false`, `~/.claude/settings.json:113`) | 0 |
| Tool errors | 5: 1 hook block (`pr-review-guard`), 1 self-kill (`pkill` matched its own shell, exit 144, row 1332), 3 script errors | 2 non-zero exits |

- **Combined, from the session-report analyzer:** 242.1M input tokens (98.4% cached), 508.9k output, 49 human messages, 31.2 h wall-clock against 5.8 h active, 3 cache breaks over 100k, and 10 subagent calls totalling 46.5M tokens (4.65M per call).
- **Most expensive prompts:**
  - "Please validate the merges and start speckit implement": 83.7M tokens
  - the pasted spec review at 04:03: next largest
  - "Perform the merges…": 27.8M, 6 subagents
  - "Proceed with your recommendations": 17.1M
  - "go with option B…": 9.6M
- **Context pressure in `b10d4503`:**
  - Context passed 200k at 03:52 (prompt-engineering phase), 400k at 05:01, 600k at 07:42, 800k at 08:32 and 900k at 08:51 on 10-01.
  - The owner saw 91% at 14:31 and resumed the same session 15 h later.
  - The context limit was hit 4 minutes into the resume, immediately after `HANDOFF.md` was committed and pushed. The final assistant message is "Prompt is too long" (row 3592).
  - Resuming at about 968k context also cost a 942.5k-token uncached cache rewrite (05:38:18).

## 4. Findings

| ID | Observation | Evidence | Root cause | Lesson | Rework (est.) |
|---|---|---|---|---|---|
| S1 ✅ | The work began as prompt refinement for an "ultra code-review". About 65 min and 5 pasted critique rounds later, the owner asked why it wasn't spec-driven. The agent then moved it to `/speckit-specify`. | b10d4503 rows 8, 55–184, 573, 590, 600 | The agent followed the request's framing ("refine the prompt") and never applied the repo's Spec Kit mandate (CLAUDE.md, ADR-003). | When a request implies a non-trivial change to a repo with a Spec Kit mandate, redirect to `/speckit-specify` before polishing a prompt. | ~65 min wall-clock; 200k context tokens before the spec started |
| S2 ✅ (sharper than the seed) | The spec and plan targeted 4.0.10 and missed AGE-718 (target 3.4.7). The agent then **read AGE-718 at 04:57:18 and posted a comment declaring it superseded (05:00:40)** without raising the conflict. It disclosed the reversal only when the owner asked (05:12:28). Option B amended the spec. | rows 1091, 1178, 1368, 1394; `0099b5a`; correction comment row 1564; process record row 69 (9 files) | No prior-decision search before specify/plan. When the agent found the conflict, it resolved it unilaterally in an external system. | Search Linear and `biosciences-program/docs/plans` before `/speckit-specify` (memory now exists, 07:26:40). A conflict with an owner decision is a stop-and-ask, never a "superseded" comment. | 1 amendment commit across 9 files, 2 Linear comments (one reversing the other), and 2 h 35 m from plan approval to correction (about 2 h idle) |
| S3 ✅ | Two `/speckit-analyze` runs, each with a remediation round (H1–H5 plus medium items; then F4, C3, F5, F6, C4), followed by PR #19 review N1–N9 | `d19693c`, `ebeebd2`, `16e3434`; process record rows 70–72 | Artifact-only analysis | **Added:** both analyze passes missed N1–N3, which "would break T016, T018 and T035" (row 2154). The code-aware PR review caught them. Analyze is necessary but not sufficient. | 3 remediation commits in about 45 min (07:30–08:15) |
| S4 ⚠️ partly ✅ | "Hand-written arguments" was first the **main session's own** error: T018 capture, 3 wrong parameter names, owner objected at 08:34:09. On 10-02 an *external* validating agent marked T021–T024 and T026 `[X]`, recorded "Go" and claimed "<15 min SLA" for 4.7. The main session withdrew Go and T026 and marked 4.7 NOT RUN. Of the external agent's checks, **it re-verified only the check 4.3 arguments** (12/12). It accepted checks 4.1, 4.2, 4.4, 4.5, 4.8 and the §1.6 side-by-side from prose. | rows 2843–2955, 2873, 3542, 3549, 3562; `core-preview.md:127`; evidence holds no raw preview outputs (only `core-preview.md`) | Self-validation by the agent doing the work. Evidence recorded as prose, not raw logs. | Preview evidence needs raw request/response files like `core-3.4.7/`. A decision task can't be checked by an agent. | T018: 1 rewrite, about 7 min, 1 killed run. T026/4.7: one withdrawal commit (`02ca1d0`) |
| S5 ✅ | The owner tried to merge from a phone. The `!` lines arrived as chat. The agent then ran `gh pr merge 18` itself, and the guard blocked it. The merges happened on GitHub. | rows 2068 (agent told owner to use `! gh pr merge`), 2409, 2428–2429, 2449, 2461, 2466 | The agent recommended `!` without checking the client (a remote/bridge session; `bridge-session` rows present). It treated chat text resembling a command as an instruction to run it. | When merging is blocked by design, give the GitHub web/mobile path first. Don't run a command the owner typed for their own shell. | About 5 min and 3 owner messages (08:16:27 → 08:21:31) |
| S6 ✅ | Two unrequested docs-only pushes to the PR #20 branch redeployed the Horizon preview twice. The owner noticed one 15 min later and had to ask for a scope investigation. | rows 3562 (`02ca1d0`), 3587 (`8b9195f`); 5ec7f1e1 rows 108, 164; memory `push-triggers-horizon-deploy.md` (05:57:02, written *after* the incident) | Commit-and-push in one command as a habit. No rule linking push to deploy. | Ask before pushing to any branch Horizon deploys. Commit locally by default (followed on 10-02: `d07ffba` unpushed). | 2 unplanned deploys, about 6 owner messages over ~10 min, and `core-preview.md:118` amended to record the head change |
| S7 ✅ | Check 4.7 assumed a manual redeploy, but Horizon deploys on every push. The drill was waived. The proxy figures (29 s build, ~70 s push→image) came from an *accidental* push. | `quickstart.md:63`; `tasks.md:136`; `core-preview.md:102–116`; 5ec7f1e1 row 224 | The quickstart was written before the deploy trigger was known. Research never established how Horizon deploys. | Plans must state the deployment trigger (push vs manual) and production auto-deploy. Production auto-deploy is still **unconfirmed** (`core-preview.md:115`). | Waiver discussion (05:54–07:09). Rollout and human steps unmeasured. |
| S8 ✅ (+1 confound) | Horizon ignores `uv.lock`. It deployed mcp 1.30.0, pydantic 2.13.5 and uvicorn 0.54.0 on Py 3.12.13, against lock 1.26.0 and local Py 3.13.2. This was known in research, but local tiers ran the lock set until 10-02. **Added:** T018's 2.14.5 capture also ran in a throwaway env (`--python 3.12`, mcp 1.30.0) against 3.4.7 on mcp 1.26.0 and Py 3.13, so the wire diff changed the framework, mcp and Python versions at once. | `research.md:56,58,128`; `core-preview.md:7,116–117`; `wire-diff.md:5–6`; row 2955 | The research fact never became a test-environment requirement. | Test the deployed resolution as well as the lock (done 10-02: README:22,27). Hold everything except the framework constant in A/B captures. | 1 extra env build and 2 runs on 10-02 |
| S9 ✅ | Quickstart §2 (T008/T017) covered unit, contract-unit, `test_gateway.py` and contract-integration only. The 10-02 full run found 16 new failures in `test_competency_questions_mcp.py` (`get_tool().fn()` → `ToolResult`). CI runs only `-m unit`. The PR #20 body still says the network tier "matches the 2.14.5 baseline". | `quickstart.md:21–27`; `tasks.md:88,102`; README:36,53–55; `ci.yml:27`; PR #20 body lines 64–65 | The acceptance tier (AGE-718: "no new failures" in `integration and not contract`, per README:55) wasn't mapped into the quickstart. | Derive quickstart test commands from the tracking issue's acceptance criteria and run the full tier the issue names. | Found about 23 h after T017 was checked. Fix not applied (port the file to `Client.call_tool`). |
| S10 ✅ | `b10d4503` hit the context limit (auto-compact off) right after the HANDOFF commit and push. HANDOFF misstates PR head and the done-task range. | rows 3506, 3592; `HANDOFF.md:17` ("head `02ca1d0`"; actual `8b9195f`, the HANDOFF commit itself); `HANDOFF.md:23` ("T001–T024" includes open T005, `tasks.md:49`) | One 27-hour session past 90% context, resumed after the owner had seen 91%. A self-referential SHA can't be correct inside the commit that changes it. | Start a fresh session at about 70–80% or at phase boundaries. A handoff should state "head = the commit containing this file" or leave the SHA to `git log`. | 942.5k-token cache rewrite, one lost turn, 2 handoff errors corrected in the next session |
| S11 ✅ | Upstream noise made "no new failures" hard to judge. It took a same-day 2.14.5 baseline on `main`, an FR-012 rerun, an interleaved Ensembl A/B and a Horizon-set subset. **Added:** the expected-failure counts were stale. `quickstart.md:33` and `tasks.md:88` say 11; the 10-01 baselines show 9. | README:24–27, 31–40; `ensembl-ab.txt`; `evidence/core-2.14.5/contract-integration.txt` (last line: 9 failed) | No standing baseline runner; expected counts written as constants | Store the failing test IDs of a same-day baseline, not counts | 4 extra runs, about 37 min (07:27–07:47) |
| S12 ✅ (one qualifier) | Practices that held up: guard before upgrade (`5103a57` 08:24:40 before `0d3cf29` 08:31:37); inputs derived from contracts after S4; `.txt` logs and a key scrub (rows 995, 2383; README:29); an evidence folder per phase; a process record that logs deviations honestly (row 73 records the 3 wrong parameter names). The FR-011 withdrawal was correct. | as cited | — | Keep. Qualifier: "39/39" covers `isError` and `structuredContent` only. 31 of 39 cases differ in `_meta` or message text, all mapped to allowed-changes rows (`wire-diff.md` table). | — |
| N1 | `/speckit-analyze` remediation renumbering truncated `plan.md` and `research.md` (opened for write before reading). Both were restored from git. | row 1773 | Unsafe ad-hoc edit scripts | Edit scripts must read before opening for write; prefer the Edit tool (captured at `HANDOFF.md:62`) | 1 repair cycle |
| N2 | The agent wrote PR #18's "User-visible contract: Unchanged". The review showed unprefixed names route to the last-mounted server on 2.14.5. | rows 2061, 2068, 2092 | The claim covered the tool list only, not dispatch | The review team caught it, so the `/pr-review` gate earned its cost | 1 PR-body edit |
| N3 | The allowed-changes table was widened during implementation to absorb an observed diff ("added 2026-10-01 with this capture", PubChem 429 text). It was disclosed in the summary (row 3499), but no owner approval appears among the prompts. | `wire-diff.md` result table; row 3499 | Contract edited to fit the result | Changes to the allowed-changes table need an explicit owner OK, like T026. **Inference:** no approval found in the 40 prompts. | — |
| N4 | PR #20 has 0 reviews and no `/pr-review` run. Its body is stale: no preview results, no waiver, no 16 failures, and it still lists the T025 timed rollback (lines 77–78). | `gh pr view 20`; PR #20 body | PR body not maintained after 08:51 on 10-01 | Refresh the PR body from evidence before the T026 decision; run `/pr-review 20` | Open |
| N5 | `core-preview.md:104` puts the owner's handle in a committed file. `core-preview.md:5,127` (head `f1c80d1`) sit beside `:118` ("now runs `8b9195f`"). `:8` "Date Tested 2026-10-01" is a local-time date (the UTC run was 10-02 about 05:30). `HANDOFF.md:1` has the same. **Inference** on the timezone. | file lines cited | Mixed authors (external agent, two sessions); local vs UTC dates | One date convention (UTC) for evidence; names by role | Minor |
| N6 | The pre-release README ends with a dangling `Failures:` heading and no list | `core-3.4.7-prerelease/README.md:86` (last line) | Generation script didn't append the list | Validate generated evidence before commit | Minor |
| N7 | A 2-hour idle (05:12–07:21) and a 21-hour idle each forced large cache rewrites: 420k and 942.5k uncached tokens | session-report `cache_breaks` | Long-lived session resumed after cache expiry | Same as S10: fresh sessions with a handoff | Token cost |

## 5. Spec artifact drift (claims vs evidence)

| # | Claim | Location | Evidence that contradicts or qualifies it |
|---|---|---|---|
| D1 | T021–T024 `[X]` | `tasks.md:132–135` | Ticked by the external agent. The only evidence is the prose `core-preview.md`, with no raw outputs. Only the 4.3 arguments were re-verified (`core-preview.md:127`). |
| D2 | T026 `[X]` and "Go" | external agent's uncommitted edit (row 3542: `[X] T026`; row 3549: "**Go**", "<15 min SLA") | Withdrawn in `02ca1d0`; now `tasks.md:137` `[ ]`, `core-preview.md:122–126` |
| D3 | T017 `[X]` with "network-tier failures the same as before" | `tasks.md:102`; PR #20 body line 65; process record row 73 | The full integration tier has 16 new failures (README:36) |
| D4 | Expected baseline "11 contract-integration failures" | `quickstart.md:33`; `tasks.md:88` | 9 on 2.14.5 and 9 on 3.4.7 (`evidence/core-2.14.5/contract-integration.txt`, `evidence/core-3.4.7/contract-integration.txt`) |
| D5 | PR #20 "head `02ca1d0`" | `HANDOFF.md:17` | `8b9195f` (`gh pr view 20` headRefOid) |
| D6 | "Core tasks done: T001–T024…" | `HANDOFF.md:23` | T005 is open (`tasks.md:49`; `HANDOFF.md:30` says "Do T005 first") |
| D7 | Handoff dated 2026-10-01 | `HANDOFF.md:1` | Committed 2026-10-02 05:41:23 UTC |
| D8 | "Head Commit `f1c80d1`"; "preview head equals branch head" | `core-preview.md:5,127` | The preview now runs `8b9195f` (`core-preview.md:118`) |
| D9 | "39 of 39 identical" (as cited in the brief) | `wire-diff.md` result table | Only `isError` and `structuredContent`. 27 differ in `_meta`, 3 in validation text, 1 in exception text. The 2.14.5 side ran on a different mcp and Python (`wire-diff.md:5–6`). |
| D10 | T025 `[X]` (waived) | `tasks.md:136` (at `d07ffba`, local) | Checked although the check never ran. Whether a waived task should be `[X]` is a convention question (see Q2). |
| D11 | PR #20 body "Draft until … timed rollback" (T021–T025) | PR #20 body lines 77–78 | T025 waived; body not updated |
| D12 | Status count "32 done, 22 open" | 5ec7f1e1 row 84 | 33 done at `8b9195f`; T001 uses a lowercase `[x]` (`tasks.md:45`) that a `[X]` count misses |
| D13 | Pre-release README "Failures:" section | README:86 | Empty |

## 6. Recommendations

| ID | Change | Type | Owner | Effort | Impact | Grounding |
|---|---|---|---|---|---|---|
| R1 | Before `/speckit-specify`/`/speckit-plan`, require a "Prior decisions" section listing the Linear issues and `docs/plans` searched. Plan approval is blocked if a found decision contradicts the target. | template (spec/plan) | Platform Architect | S | H | S2; memory `check-prior-decisions-before-planning.md` |
| R2 | PreToolUse hook on `git push`: confirm (or deny unless an env flag is set) when the branch has a Horizon deployment (PR branches and `main`) | hook | Quality & Skills Engineer | S | H | S6; Claude Code hooks docs https://docs.anthropic.com/en/docs/claude-code/hooks |
| R3 | Quickstart §2 runs the full tier named in the tracking issue's acceptance criteria (`-m "integration and not contract"`), with a same-day baseline on `main` stored as failing-test IDs (not counts) | quickstart/template | MCP Platform Engineer | M | H | S9, S11, D3, D4 |
| R4 | Add a tier that tests the Horizon-resolved set: `uv pip install --system .` into a clean Py 3.12 env, then unit and MCP-layer integration. Put it in CI on PRs that touch `pyproject.toml`. | CI / quickstart | MCP Platform Engineer | M | M | S8; README:22,27 |
| R5 | Preview checks must commit raw outputs (request args, responses, tool list) under `evidence/<repo>-preview/`, as the local tiers do. Decision tasks (T026-style) are owner-only; an agent recording "Go" fails a check. | template (tasks) + converge checklist | Quality & Skills Engineer | S | H | S4, D1, D2 |
| R6 | Session hygiene in CLAUDE.md: no single session across phases; start fresh at about 75% context or at each Spec Kit command boundary; handoff written at ≤80%, not at 97%. Handoffs don't cite their own commit SHA. | CLAUDE.md | repo owner | S | M | S10, N7, D5 |
| R7 | Quickstart must state each deploy target's trigger (push vs manual) and production auto-deploy; a rollback drill is designed against that. Record "rollback re-resolves". | template (quickstart) | Platform Architect | S | M | S7; `core-preview.md:115–116` |
| R8 | Changes to `contracts/tool-surface-invariants.md` allowed-changes rows during implement need an owner approval line | constitution/template | Platform Architect | S | M | N3 |
| R9 | Merge guidance: when the guard blocks merges, give the GitHub web/mobile path first, and never execute owner-typed `!` text | CLAUDE.md / pr-review skill | Quality & Skills Engineer | S | L | S5 |
| R10 | Run `/pr-review 20` and refresh the PR #20 body from the evidence before T026 | issue/action | MCP Platform Engineer | S | H | N4, D11 |
| R11 | Port `test_competency_questions_mcp.py` to `Client(mcp).call_tool`. AGE-718 counts these as new failures until then. | issue | MCP Platform Engineer | S | H | S9; README:54–55 |
| R12 | Redirect rule: requests to "refine a prompt" for a non-trivial repo change are answered with a pointer to `/speckit-specify` | CLAUDE.md | repo owner | S | M | S1 |

## 7. Open questions

1. **Q1:** Does production `biosciences-mcp` auto-redeploy on a push to `main`? This is unconfirmed (`core-preview.md:115`), and the rollback path depends on it.
2. **Q2:** Should a waived task be `[X]` or carry a distinct marker? `/speckit-converge` and `/speckit-analyze` can't tell "done" from "waived" today (D10).
3. **Q3:** Which tool was the external validating agent (log style "Viewed quickstart.md:65-71")? Did it run in this worktree? Unknown. **Inference:** a different IDE agent edited `tasks.md` directly in the shared worktree (row 3542 shows uncommitted edits before the main session acted).
4. **Q4:** Was the PubChem allowed-changes row (N3) seen and accepted by the owner outside the transcript?
5. **Q5:** The AGE-718 acceptance wording is cited second-hand (README:55). The prioritizer should confirm it against Linear before relying on R3/R11 severity.
