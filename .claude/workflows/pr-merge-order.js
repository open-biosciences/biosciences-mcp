export const meta = {
  name: 'pr-merge-order',
  description: 'Assess open PRs at exact head OIDs in detached worktrees, simulate real merges, and recommend a verified merge order',
  whenToUse: 'When several PRs are open and you want an evidence-backed status board plus a merge sequence that has actually been simulated',
  phases: [
    { title: 'Discover', detail: 'scripts/pr_merge_sim.py discover: fetch exact heads, worktrees, pairwise merge sims' },
    { title: 'Assess', detail: 'one agent per PR: full diff, PR-body claims vs diff, real check logs, tests in worktree' },
    { title: 'Order', detail: 'propose landing order + strategy from assessments and simulations' },
    { title: 'Verify', detail: 'scripts/pr_merge_sim.py sequence: land the proposed order on a scratch main' },
    { title: 'Report', detail: 'status board + commands, every claim tagged with its evidence source' },
    { title: 'Cleanup', detail: 'remove simulator worktrees' },
  ],
}

// args: { root?: string, limit?: number, keep?: boolean }
const limit = (args && args.limit) || 30
const rootFlag = args && args.root ? `--root '${String(args.root).replace(/[^A-Za-z0-9_./-]/g, '')}'` : ''
const HELPER = `python3 scripts/pr_merge_sim.py`

const DISCOVER_SCHEMA = {
  type: 'object',
  properties: {
    main_oid: { type: 'string' },
    repo_landing_convention: { type: 'string', enum: ['merge', 'squash'] },
    root: { type: 'string' },
    prs: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          number: { type: 'integer' }, title: { type: 'string' }, url: { type: 'string' },
          head: { type: 'string' }, base: { type: 'string' }, head_oid: { type: 'string' }, base_oid: { type: 'string' },
          oid_verified: { type: 'boolean' }, merge_base_with_main: { type: 'string' },
          stacked_on_pr: { type: ['integer', 'null'] }, is_draft: { type: 'boolean' },
          mergeable: { type: 'string' }, merge_state: { type: 'string' },
          github_review_decision: { type: 'string' },
          github_reviews: { type: 'array', items: { type: 'object' } },
          issue_comments: { type: 'array', items: { type: 'object' } },
          checks: { type: 'array', items: { type: 'object' } },
          additions: { type: 'integer' }, deletions: { type: 'integer' },
          files: { type: 'array', items: { type: 'string' } },
          worktree: { type: 'string' },
          merge_onto_main: { type: 'object' },
        },
        required: ['number', 'title', 'head', 'base', 'head_oid', 'oid_verified', 'merge_base_with_main', 'stacked_on_pr',
          'merge_state', 'github_review_decision', 'github_reviews', 'issue_comments', 'checks', 'files', 'worktree', 'merge_onto_main'],
      },
    },
    pairwise: { type: 'array', items: { type: 'object' } },
  },
  required: ['main_oid', 'repo_landing_convention', 'root', 'prs', 'pairwise'],
}

const ASSESS_SCHEMA = {
  type: 'object',
  properties: {
    number: { type: 'integer' },
    head_oid: { type: 'string', description: 'the exact commit you assessed' },
    verdict: { type: 'string', enum: ['approve', 'approve-with-nits', 'request-changes', 'blocked'] },
    risk: { type: 'string', enum: ['low', 'medium', 'high'] },
    scope: { type: 'string', description: 'one line: what the diff actually does' },
    blockers: { type: 'array', items: { type: 'string' }, description: 'each with file:line or command evidence' },
    concerns: { type: 'array', items: { type: 'string' } },
    claim_checks: { type: 'array', items: { type: 'object', properties: {
      claim: { type: 'string' }, holds: { type: 'boolean' }, evidence: { type: 'string' } }, required: ['claim', 'holds', 'evidence'] },
      description: 'PR-body / docs claims verified against the diff or by running commands' },
    checks_verified: { type: 'array', items: { type: 'object', properties: {
      name: { type: 'string' }, reported: { type: 'string' }, actual: { type: 'string' } }, required: ['name', 'reported', 'actual'] },
      description: 'per CI check: what GitHub reports vs what the run log shows' },
    tests_run: { type: 'array', items: { type: 'object', properties: {
      command: { type: 'string' }, result: { type: 'string' } }, required: ['command', 'result'] } },
    semantic_depends_on: { type: 'array', items: { type: 'integer' },
      description: 'PRs this should land AFTER for content reasons (e.g. it documents problems another PR fixes)' },
    github_review_decision: { type: 'string' },
    notes: { type: 'string' },
  },
  required: ['number', 'head_oid', 'verdict', 'risk', 'scope', 'blockers', 'concerns', 'claim_checks', 'checks_verified',
    'tests_run', 'semantic_depends_on', 'github_review_decision'],
}

const ORDER_SCHEMA = {
  type: 'object',
  properties: {
    strategy: { type: 'string', enum: ['merge', 'squash'], description: 'landing strategy to simulate and recommend' },
    order: { type: 'array', items: { type: 'object', properties: {
      step: { type: 'integer' }, number: { type: 'integer' },
      action: { type: 'string', enum: ['merge', 'rebase-then-merge', 'merge-forward-then-merge', 'retarget-then-merge', 'hold'] },
      why: { type: 'string' } }, required: ['step', 'number', 'action', 'why'] } },
    rationale: { type: 'string' },
  },
  required: ['strategy', 'order', 'rationale'],
}

const SEQ_SCHEMA = {
  type: 'object',
  properties: {
    strategy: { type: 'string' }, all_landed: { type: 'boolean' },
    steps: { type: 'array', items: { type: 'object' } },
  },
  required: ['strategy', 'all_landed', 'steps'],
}

const REPORT_SCHEMA = {
  type: 'object',
  properties: { summary: { type: 'string', description: 'markdown, ready to show the user' } },
  required: ['summary'],
}

// ---------------------------------------------------------------- Discover
phase('Discover')
const disc = await agent(
`Run exactly: ${HELPER} discover ${rootFlag} --limit ${limit}
It fetches refs/pull/N/head for every open PR, verifies the head OID against GitHub, creates one detached
worktree per PR at that OID, and runs real merge simulations. It prints one JSON object; return that object
verbatim as structured output (do not summarise, do not drop fields). If it fails, return the error text as
the title of a single fake PR numbered -1.`,
  { label: 'discover:simulate', phase: 'Discover', schema: DISCOVER_SCHEMA, effort: 'low' },
)
const prs = ((disc && disc.prs) || []).filter(p => p.number > 0)
if (!prs.length) {
  // prepare() already created scratch-main and refs; do not leave them behind
  if (disc && disc.root && !(args && args.keep)) {
    await agent(`Run exactly: ${HELPER} cleanup ${rootFlag}  and return its JSON output as text.`,
      { label: 'cleanup', phase: 'Cleanup', effort: 'low' })
  }
  return { summary: 'No open PRs (or discover failed).', discover: disc }
}
const unverified = prs.filter(p => !p.oid_verified).map(p => '#' + p.number)
if (unverified.length) log(`WARNING: head OID mismatch vs GitHub for ${unverified.join(', ')} — PR moved during fetch`)
log(`${prs.length} open PR(s): ${prs.map(p => '#' + p.number + '@' + p.head_oid.slice(0, 7)).join(', ')}; landing convention on main: ${disc.repo_landing_convention}`)
const pairwiseFor = n => disc.pairwise.filter(x => x.after === n || x.then === n)

// ---------------------------------------------------------------- Assess
let assessed = [], proposal = null, seq = null, report = null
try {
phase('Assess')
assessed = (await pipeline(prs, p => agent(
`Assess PR #${p.number} "${p.title}" for merge readiness. Return structured output only. Do NOT modify files,
push, comment, approve, or merge. Work only inside the detached worktree; the checkout there is the exact PR head.

Facts from the simulator (trust these; they were computed by git, not inferred):
  head_oid=${p.head_oid} (verified against GitHub: ${p.oid_verified})  base=${p.base}  stacked_on_pr=${p.stacked_on_pr}
  merge_base_with_main=${p.merge_base_with_main}  merge_state=${p.merge_state}  mergeable=${p.mergeable}
  worktree=${p.worktree}
  files (${p.files.length}, complete): ${JSON.stringify(p.files)}
  merge onto main: ${JSON.stringify(p.merge_onto_main)}
  pairwise simulations involving this PR: ${JSON.stringify(pairwiseFor(p.number))}
  GitHub formal review decision: ${p.github_review_decision}; formal reviews: ${JSON.stringify(p.github_reviews)}
  issue comments (NOT reviews): ${JSON.stringify(p.issue_comments)}
  CI checks as reported: ${JSON.stringify(p.checks)}

Required procedure:
1. cd ${p.worktree}. Read the PR body and every comment: gh pr view ${p.number} --comments. Keep formal reviews and
   issue comments distinct in your output; never call a comment a review.
2. Read the COMPLETE diff: git diff ${p.merge_base_with_main} ${p.head_oid}. If it exceeds ~2500 lines, read it
   per file (git diff ${p.merge_base_with_main} ${p.head_oid} -- <path>) until every changed file has been read.
   Do not sample or truncate.
3. Verify claims. For each substantive claim in the PR body, docs, or process records added by the PR, decide
   whether it holds and cite evidence. In particular check: commands described as "run" that are actually
   reconstructed; references to tables/sections/counts that exist only in another open PR; task lists or
   checklists with unchecked or contradictory items that downstream tooling could execute; validation or
   comparison scripts that do not measure what the PR says (read the script and check field paths against the
   models it compares); stale counts in CLAUDE.md or README.
4. Verify every CI check: for each check with a details_url, run gh run view <run-id> --log 2>/dev/null | grep -iE "skipping|validation|error|failed" | head. A SUCCESS whose log says the action skipped itself is NOT a pass — report reported vs actual.
5. If the PR touches src/ or tests/: in the worktree run
     uv sync -q --extra dev && uv run pytest -m unit -q -p no:cacheprovider 2>&1 | tail -3
     uv run pytest -m "contract and unit" -q -p no:cacheprovider 2>&1 | tail -3
     uv run ruff check . 2>&1 | tail -2
   Record exact commands and results in tests_run. Compare ruff errors to main if any (git stash is NOT allowed; use the main repo checkout read-only).
6. semantic_depends_on: PRs this one should land AFTER for content reasons — e.g. it records a backlog or
   converge notes that another open PR already resolves, or it documents counts another PR changes.
7. verdict: approve / approve-with-nits / request-changes / blocked. Any false claim presented as evidence,
   contradictory executable task list, or invalid validation script is request-changes. Unresolved formal
   change-requests or a required secret/API missing is blocked.`,
  { label: `assess:#${p.number}`, phase: 'Assess', schema: ASSESS_SCHEMA },
))).filter(Boolean)
log(`assessed ${assessed.length}/${prs.length}: ${assessed.map(a => '#' + a.number + '=' + a.verdict).join(', ')}`)

// ---------------------------------------------------------------- Order + Verify (loop ≤ 2)
const context = {
  main_oid: disc.main_oid,
  repo_landing_convention: disc.repo_landing_convention,
  prs: prs.map(p => ({ number: p.number, title: p.title, head: p.head, base: p.base, head_oid: p.head_oid,
    stacked_on_pr: p.stacked_on_pr, files: p.files.length, merge_state: p.merge_state })),
  pairwise: disc.pairwise,
  assessed,
}
let feedback = ''
for (let round = 1; round <= 2; round++) {
  phase('Order')
  proposal = await agent(
`Propose a landing order for these open PRs. Return structured output only.

${JSON.stringify(context, null, 1)}
${feedback ? `\nPREVIOUS PROPOSAL FAILED SIMULATION:\n${feedback}\nFix the order/strategy/actions so the sequence lands.` : ''}

Rules:
- strategy: default to repo_landing_convention. Pairwise entries are keyed by land_strategy_for_first; a pair that
  conflicts under squash but not merge means squash-landing the first PR breaks the second — say so.
- Git ancestry: squash or rebase landing does NOT make the PR's commits ancestors of main. A PR whose branch
  contains another PR's commits (stacked, or merged it in) will then show that PR's changes in its own diff and
  may conflict; it needs rebase-then-merge or merge-forward-then-merge, not retarget-then-merge. Never recommend
  deleting a parent branch before its dependants are re-based and their diffs re-verified.
- Honour semantic_depends_on from the assessments even when git says both orders are clean.
- Land small, low-risk, non-overlapping PRs first; the widest-overlap PR gets exactly one merge-forward.
- Include EVERY PR in "order" (holds too, with action=hold, placed where they would land once fixed) so the whole
  sequence can be simulated.
- Every "why" must cite the concrete simulator fact or assessment finding it rests on.`,
    { label: `order:round${round}`, phase: 'Order', schema: ORDER_SCHEMA },
  )
  if (!proposal) break
  const sorted = proposal.order.slice().sort((a, b) => a.step - b.step)
  const seqOrder = sorted.filter(o => o.action !== 'hold').map(o => o.number).join(',')
  const skipList = sorted.filter(o => o.action === 'hold').map(o => o.number).join(',')
  const skipFlag = skipList ? `--skip ${skipList}` : ''
  phase('Verify')
  seq = await agent(
`Run exactly: ${HELPER} sequence --order ${seqOrder || '0'} ${skipFlag} --strategy ${proposal.strategy} ${rootFlag} --limit ${limit}
It lands the PRs in that order on a scratch copy of origin/main (never touching origin) and prints one JSON
object. Return it verbatim as structured output.`,
    { label: `verify:${seqOrder}`, phase: 'Verify', schema: SEQ_SCHEMA, effort: 'low' },
  )
  if (seq && seq.all_landed) { log(`sequence ${seqOrder} (${seq.strategy}) lands cleanly${skipList ? '; holds skipped: ' + skipList : ''}`); break }
  feedback = JSON.stringify(seq, null, 1)
  log(`sequence ${seqOrder} (${proposal.strategy}) did NOT land cleanly — re-planning (round ${round})`)
}

// ---------------------------------------------------------------- Report
phase('Report')
report = await agent(
`Write the final markdown report for the user. Return structured output only ({summary}).

Inputs:
proposal=${JSON.stringify(proposal, null, 1)}
simulation=${JSON.stringify(seq, null, 1)}
context=${JSON.stringify(context, null, 1)}

Format (≤ 80 lines):
1. "## Open PR status (main @ <short oid>)" — table: PR | Title | CI (reported → actual) | GitHub review | Internal verdict | Risk.
   "GitHub review" is the formal reviewDecision; "Internal verdict" is this workflow's assessment. Never conflate them.
2. "## Simulated landing sequence" — strategy, whether every step landed, per-step conflicts / retarget hazards / net stat.
   If the simulation did not fully land, say so in the first line and do not present commands as safe.
3. "## Recommended order" — numbered steps with exact gh/git commands consistent with the strategy
   (gh pr merge N --merge vs --squash; rebase/merge-forward commands where the action requires them; never
   --delete-branch on a PR that other open PRs' branches contain until those are re-verified).
   Preface each step with what must be fixed first if the verdict is request-changes/blocked.
4. "## Holds and required fixes" — per PR: blockers with evidence.
5. "## Watch-outs" — semantic dependencies, wire-shape changes, stale counts, hollow CI checks.
Tag non-obvious claims with their source in brackets: [sim], [diff], [run log], [tests], [GitHub API].`,
  { label: 'report', phase: 'Report', schema: REPORT_SCHEMA },
)

} finally {
  // ---------------------------------------------------------------- Cleanup (always)
  if (!(args && args.keep)) {
    phase('Cleanup')
    await agent(`Run exactly: ${HELPER} cleanup ${rootFlag}  and return its JSON output as text.`,
      { label: 'cleanup', phase: 'Cleanup', effort: 'low' })
  } else {
    log(`keeping worktrees under ${disc.root}`)
  }
}

return { main_oid: disc.main_oid, convention: disc.repo_landing_convention, assessed, proposal, simulation: seq, ...report }
