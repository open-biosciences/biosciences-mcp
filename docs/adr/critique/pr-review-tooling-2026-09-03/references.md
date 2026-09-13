# References

Collected 2026-09-03 for the PR #11 scope decision (add `.claude/workflows/pr-merge-order.js` + `scripts/pr_merge_sim.py`?).
Sources: **official** = https://code.claude.com/docs/en/… (fetched live); **platform-docs** = `mcp__claude_ai_platform-docs` (Anthropic source, 1603 docs — all `platform.claude.com`, no Claude Code CLI pages); **context7** = `/websites/code_claude` and `/llmstxt/code_claude_llms_txt` (mirrors of the official site); **bundled skill** = the `/workflow-authoring` skill text loaded locally in this session (v2.1.248+).

> **Quotation accuracy (corrected 2026-09-04).** Four entries below were originally compressed paraphrases presented as `>` blockquotes; `adversary-round2.md` §4 flagged them and they are now replaced with the verbatim text from the live pages, each marked *(verbatim, re-fetched 2026-09-04)*. The remainder were spot-checked as CONFIRMED by the adversary or are marked as unverified where they were not checked. Lift quotations from this file only where a verbatim marker or a round-2 CONFIRMED verdict backs them.

## Skills

- **Extend Claude with skills → intro note (commands merged)** — https://code.claude.com/docs/en/skills (source: official). Slash commands and skills are one mechanism; `.claude/commands/` is legacy.
  > "**Custom commands have been merged into skills.** A file at `.claude/commands/deploy.md` and a skill at `.claude/skills/deploy/SKILL.md` both create `/deploy` and work the same way."
- **Where skills live** — https://code.claude.com/docs/en/skills#where-skills-live (source: official). Project path is `.claude/skills/<skill-name>/SKILL.md`; plugin skills are namespaced.
  > "Plugin skills use a `plugin-name:skill-name` namespace, so they can't conflict with other levels."
  > "Add a `.claude-plugin/plugin.json` to a skill folder and it loads as a plugin named `<name>@skills-dir`, so it can bundle agents, hooks, and MCP servers."
- **Frontmatter reference** — https://code.claude.com/docs/en/skills#frontmatter-reference (source: official; context7 agrees). Verbatim field names: `name`, `description`, `when_to_use`, `argument-hint`, `arguments`, `disable-model-invocation`, `user-invocable`, `allowed-tools`, `disallowed-tools`, `model`, `effort`, `context`, `agent`, `background`, `hooks`, `paths`, `shell`, `metadata`, `license`, `compatibility`.
  > "`allowed-tools` … Tools Claude can use without asking permission during the turn that invokes this skill. The grant clears when you send your next message."
  > "`context` … Set to `fork` to run in a forked subagent context." / "`agent` … Which subagent type to use when `context: fork` is set."
- **Add supporting files** — https://code.claude.com/docs/en/skills#add-supporting-files (source: official). A skill directory may carry `scripts/` that are executed, not loaded — the natural home for a helper like `pr_merge_sim.py`.
  > "scripts/ └── helper.py (utility script - executed, not loaded)"
- **Control who invokes a skill** — https://code.claude.com/docs/en/skills#control-who-invokes-a-skill (source: official).
  > "`disable-model-invocation: true`: Only you can invoke the skill. Use this for workflows with side effects or that you want to control timing, like `/commit`, `/deploy`…"
- **Pre-approve tools for a skill** — https://code.claude.com/docs/en/skills#pre-approve-tools-for-a-skill (source: official). Security-relevant: skill `allowed-tools` is NOT gated by workspace trust.
  > "Workspace trust doesn't gate this field. … A skill can grant itself broad tool access, so review the `allowed-tools` of skills checked into a repository before you run Claude Code there."
  > Example: `allowed-tools: Bash(git add *) Bash(git commit *) Bash(git status *)`
- **Run skills in a subagent** — https://code.claude.com/docs/en/skills#run-skills-in-a-subagent (source: official). `context: fork` + `agent:` is the skill-side way to spawn one subagent; backgrounded forks get the narrower background tool set.
  > "Add `context: fork` to your frontmatter when you want a skill to run in isolation. The skill content becomes the prompt that drives the subagent."
- **Restrict Claude's skill access** — https://code.claude.com/docs/en/skills#restrict-claudes-skill-access (source: official).
  > "Permission syntax: `Skill(name)` for exact match, `Skill(name *)` for prefix match with any arguments."

## Subagents

- **Supported frontmatter fields** — https://code.claude.com/docs/en/sub-agents#supported-frontmatter-fields (source: official; context7 agrees). Verbatim: `name`, `description`, `tools`, `disallowedTools`, `model`, `permissionMode`, `maxTurns`, `skills`, `mcpServers`, `hooks`, `memory`, `background`, `isolation`, `color`, `initialPrompt`, `experimental`.
  > "`permissionMode` … `default`, `acceptEdits`, `auto`, `dontAsk`, `bypassPermissions`, `plan`, or `manual`" / "`isolation` … Set to `worktree` to run in temporary git worktree"
- **Subagent file locations** — https://code.claude.com/docs/en/sub-agents (section "Subagent file locations"; source: official). Priority: managed → `--agents` → `.claude/agents/` → `~/.claude/agents/` → plugin `agents/`.
  > "Both scopes scan recursively for subfolder organization like `agents/review/`." (so `.claude/agents/pr-review/*.md` is a documented layout)
- **Tools restriction** — https://code.claude.com/docs/en/sub-agents (section "Tools"; source: official).
  > "`disallowedTools` applied first, then `tools` resolved against remaining pool." / "`tools: Agent(worker, researcher), Read, Bash` — allowlist of subagent types only `worker` and `researcher` can spawn."
- **Hooks in subagent frontmatter** — https://code.claude.com/docs/en/sub-agents (section "Hooks in Subagent Frontmatter"; canonical format at https://code.claude.com/docs/en/hooks#hooks-in-skills-and-agents) (source: official; context7 agrees). *(verbatim, re-fetched 2026-09-04)*
  > "All [hook events](/docs/en/hooks#hook-events) are supported. The most common events for subagents are:" — followed by a table of `PreToolUse`, `PostToolUse`, and `Stop` ("converted to `SubagentStop` at runtime"). Note that *all* events are supported; these three are only the most common. (`sub-agents.md:724-730`)
  > "To let a project-level subagent's frontmatter hooks run, accept the [workspace trust dialog](/docs/en/permissions#project-allow-rules-and-workspace-trust) for the folder that contains the agent file. Hooks from user-level subagents in `~/.claude/agents/` and from definitions you pass with `--agents` run without this step." (`sub-agents.md:720`)
  > "Hooks from [settings files, managed policy settings, and plugins](/docs/en/hooks#hook-locations) all apply inside subagents, so a `PreToolUse` hook in `settings.json` also runs before every tool a subagent uses." (`sub-agents.md:710`)
- **Permission modes (subagents)** — https://code.claude.com/docs/en/sub-agents#permission-modes (source: official). *(verbatim, re-fetched 2026-09-04)*
  > "If the parent uses `bypassPermissions` or `acceptEdits`, this takes precedence and can't be overridden. If the parent uses [auto mode](/docs/en/permission-modes#eliminate-prompts-with-auto-mode), the subagent inherits auto mode and any `permissionMode` in its frontmatter is ignored: the classifier evaluates the subagent's tool calls with the same block and allow rules as the parent session." (`sub-agents.md:560`)

## Hooks

- **PreToolUse input** — https://code.claude.com/docs/en/hooks#pretooluse (source: official; context7 `/llmstxt` agrees). Verbatim stdin keys: `session_id`, `prompt_id`, `transcript_path`, `cwd`, `permission_mode`, `hook_event_name`, `tool_name`, `tool_input`, `tool_use_id`.
- **PreToolUse decision control** — https://code.claude.com/docs/en/hooks#pretooluse (source: official). Verbatim output keys: `hookSpecificOutput.hookEventName`, `permissionDecision` (`"allow"` | `"deny"` | `"ask"`), `permissionDecisionReason`, `updatedInput`, `systemMessage`, `additionalContext`.
- **Exit codes** — https://code.claude.com/docs/en/hooks (section "Exit code"; source: official).
  > "Exit 2 means a blocking error. On events that can block, exit 2 blocks whether or not you print JSON." (0 = JSON parsed as decision; other = non-blocking error)
- **Where hooks can be configured** — https://code.claude.com/docs/en/hooks (section "Hook configuration locations"; source: official). Locations: `~/.claude/settings.json`, `.claude/settings.json`, `.claude/settings.local.json`, plugin `hooks/hooks.json`, skill frontmatter ("rest of session"), subagent frontmatter ("while subagent runs"), managed policy. Path placeholders `${CLAUDE_PROJECT_DIR}`, `${CLAUDE_PLUGIN_ROOT}`, `${CLAUDE_PLUGIN_DATA}`. Hook types: `command`, `http`, `mcp_tool`, `prompt`, `agent`. Common fields: `if` (permission-rule syntax, e.g. `"Bash(git *)"`), `timeout`, `once` (skills only).
- **Matchers** — https://code.claude.com/docs/en/hooks (section "Matcher"; source: official). Exact `"Bash"`, alternation `"Edit|Write"`, regex `"mcp__memory__.*"`; plugin MCP tools are `mcp__plugin_<plugin-name>_<server-name>__<tool>`.
- **Extend permissions with hooks** — https://code.claude.com/docs/en/permissions#extend-permissions-with-hooks (source: official). Order of evaluation matters for a guard hook.
  > "Hook decisions don't bypass permission rules. Claude Code evaluates deny and ask rules regardless of what a PreToolUse hook returns"
  > "A hook that exits with code 2 stops the tool call before permission rules are evaluated, so the block applies even when an allow rule would otherwise let the call proceed."
- **Hook paths don't follow the worktree** — https://code.claude.com/docs/en/worktrees#ask-claude-to-create-a-worktree (Note block; source: official). Directly affects a guard hook running while the merge-sim uses worktrees.
  > "`${CLAUDE_PROJECT_DIR}` stays put: it still points at the project root where the session started … `cwd` follows Claude: the `cwd` field in the hook's input JSON is the worktree root"

## Plugins and packaging

- **Plugin manifest schema** — https://code.claude.com/docs/en/plugins-reference (section "Plugin manifest schema"; source: official). Verbatim component-path fields: `skills`, `commands`, `agents`, `workflows`, `hooks`, `mcpServers`, `lspServers`, `outputStyles`.
  > "The manifest is optional. If omitted, Claude Code auto-discovers components in default locations and derives the plugin name from the directory name."
  > "| `workflows` | string\|array | Custom [workflow](/docs/en/workflows) script files or directories (replaces default `workflows/`) | `\"./custom/workflows/\"` |" *(verbatim, re-fetched 2026-09-04; `plugins-reference.md:544`)*
- **File locations reference / directory layout** — https://code.claude.com/docs/en/plugins-reference (section "Plugin directory structure"; source: official). Defaults: `skills/`, `commands/`, `agents/`, `workflows/`, `hooks/hooks.json`, `.mcp.json`, plus `scripts/` and `bin/` at plugin root.
  > "All other directories (commands/, agents/, skills/, workflows/, output-styles/, themes/, monitors/, hooks/) must be at the plugin root, not inside `.claude-plugin/`."
- **Plugin-shipped agents: unsupported fields** — https://code.claude.com/docs/en/plugins-reference (section "Agents"; source: official; context7 agrees). Matters if PR #11's reviewer agents ever move into `marketplace`.
  > "For security reasons, `hooks`, `mcpServers`, and `permissionMode` are not supported for plugin-shipped agents."
  > "Agents appear in the @-mention typeahead under their scoped name, such as `my-plugin:code-reviewer`, once the plugin is enabled."
- **Distribute a workflow in a plugin** — https://code.claude.com/docs/en/workflows#distribute-a-workflow-in-a-plugin (source: official).
  > "Place the script in a `workflows/` directory at the plugin root, or point to a different location with the `workflows` manifest field."
  > "A plugin called `acme-tools` containing a script whose `meta.name` is `release-audit` runs as `/acme-tools:release-audit`."
- **Explore the .claude directory → File reference** — https://code.claude.com/docs/en/claude-directory#file-reference (source: official). `workflows/*.js` is a first-class, commit-able project entry alongside `skills/`, `agents/`, `settings.json`.
  > "`workflows/*.js` | Project and global | ✓ | Dynamic workflow scripts written by Claude and saved from `/workflows`; each file becomes a `/<name>` command"

## Permissions / allowed-tools

- **Manage permissions (rule order)** — https://code.claude.com/docs/en/permissions#manage-permissions (source: official).
  > "Rules are evaluated in order: deny, then ask, then allow. The first match in that order determines the outcome, and rule specificity doesn't change the order."
- **Wildcard patterns (Bash prefix matching)** — https://code.claude.com/docs/en/permissions#wildcard-patterns (source: official). Same syntax is used by skill `allowed-tools` and hook `if`.
  > "Claude Code matches everything before the first `*` as written … `Bash(git log *)` allows only `git log` commands, and `Bash(git *)` allows every git command."
  > "The `:*` suffix is an equivalent way to write a trailing wildcard, so `Bash(ls:*)` matches the same commands as `Bash(ls *)`."
  > Compound commands: "a rule like `Bash(safe-cmd *)` won't give it permission to run the command `safe-cmd && other-cmd`… A rule must match each subcommand independently."
- **Match by input parameter / Agent rules** — https://code.claude.com/docs/en/permissions#match-by-input-parameter and https://code.claude.com/docs/en/permissions#agent-subagents (source: official).
  > "`Agent(isolation:worktree)` | Agent calls that request a git worktree" / "`Agent(my-custom-agent)` matches a custom subagent named `my-custom-agent`"
- **Workflow tool permission** — https://code.claude.com/docs/en/tools-reference (Workflow row; source: official) and https://code.claude.com/docs/en/workflows#approve-the-plan-before-it-runs.
  > tools-reference: "`Workflow` | Runs a dynamic workflow: a script that orchestrates many subagents in the background and returns one consolidated result | Permission: Yes"
  > workflows: "**Permission rule**: `Workflow` in your allow rules approves every workflow, and `Workflow(<name>)` approves one saved workflow by name."
  > "**Yes, and don't ask again for `<name>` in `<path>`** … Claude Code offers this option when you run a bundled, saved, or plugin workflow by name, not for a script Claude wrote for the current task."
- **Project allow rules and workspace trust** — https://code.claude.com/docs/en/permissions#project-allow-rules-and-workspace-trust (source: official).
  > "`permissions.allow` rules and `permissions.additionalDirectories` entries in a project's `.claude/settings.json` grant capability, so Claude Code applies them only after you accept the workspace trust dialog"

## Worktrees

- **Start Claude in a worktree** — https://code.claude.com/docs/en/worktrees#start-claude-in-a-worktree (source: official).
  > "By default, the worktree is created under `.claude/worktrees/<name>/` at your repository root, on a new branch named `worktree-<name>`" / "Add `.claude/worktrees/` to your `.gitignore`"
- **Ask Claude to create a worktree (EnterWorktree)** — https://code.claude.com/docs/en/worktrees#ask-claude-to-create-a-worktree and https://code.claude.com/docs/en/tools-reference (EnterWorktree/ExitWorktree rows; source: official).
  > "`EnterWorktree` … Creates isolated git worktree and switches into it. Pass `path` to switch into existing worktree. Prompts for approval on paths outside `.claude/worktrees/`. Permission: Yes"
  > "`ExitWorktree` … Not available to subagents with `isolation: worktree`"
- **How Claude Code enforces isolation** — https://code.claude.com/docs/en/worktrees#how-claude-code-enforces-isolation (source: official). Explains why `git` inside `$(...)`/heredocs is refused in worktree sessions (see memory note); relevant to how `pr_merge_sim.py` must be invoked.
  > "Command shape: Claude Code blocks a Bash or Monitor command it can't verify stays inside the worktree… refuses shell constructs it can't trace without running them, such as brace expansion and heredocs with unquoted delimiters… You can't turn this check off."
- **Isolate subagents with worktrees** — https://code.claude.com/docs/en/worktrees#isolate-subagents-with-worktrees (source: official; context7 agrees).
  > "Subagent worktrees use the same base branch as `--worktree`, so they branch from your repository's default branch unless `worktree.baseRef` is set to `\"head\"`."
- **What worktrees share with the main checkout** — https://code.claude.com/docs/en/worktrees#what-worktrees-share-with-the-main-checkout (source: official). Permission approvals and project-scope plugins carry across worktrees.
  > "choosing \"Yes, and don't ask again\" for a Bash command in a worktree session saves the rule to the main checkout's `.claude/settings.local.json`"

## Workflows (documented or not)

**Finding: dynamic workflows, the `Workflow` tool, and `.claude/workflows/` ARE officially documented** — page https://code.claude.com/docs/en/workflows ("Orchestrate subagents at scale with dynamic workflows"), listed in https://code.claude.com/docs/llms.txt under "Agents and Parallel Work", plus rows in `tools-reference`, `claude-directory`, and `plugins-reference`. The public page documents the *user surface* fully but only a subset of the *script API*; the rest lives in the bundled `/workflow-authoring` skill.

- **Availability note** — https://code.claude.com/docs/en/workflows (top Note; source: official).
  > "Dynamic workflows are available on all paid plans, with Anthropic API access, and on Amazon Bedrock, Google Cloud's Agent Platform, and Microsoft Foundry. On Pro, turn them on from the Dynamic workflows row in `/config`."
- **When to use a workflow (comparison table)** — https://code.claude.com/docs/en/workflows#when-to-use-a-workflow (source: official). Positions workflows vs subagents vs skills vs agent teams.
  > "Workflows | What it is: A script the runtime executes | Who decides what runs next: The script | What's repeatable: The orchestration itself | Scale: Dozens to hundreds of agents per run"
- **Save the workflow for reuse** — https://code.claude.com/docs/en/workflows#save-the-workflow-for-reuse (source: official; claude-directory agrees).
  > "`.claude/workflows/` in your project: shared with everyone who clones the repo" / "The workflow runs as `/<name>` in future sessions from either location." / "If a project workflow and a personal workflow share a name, the project one runs."
  > Symlink guard (v2.1.216+): "Project location: Claude Code refuses if `.claude`, `.claude/workflows`, or the target file is a symlink."
- **What the saved script looks like / Edit a saved script** — https://code.claude.com/docs/en/workflows#what-the-saved-script-looks-like and #edit-a-saved-script (source: official; context7 agrees). Public API surface: `export const meta` (`name`, `description`, `phases`), `agent()`, `pipeline()`, `parallel()`, `phase()`, `log()`, `args`; `schema` and `label` options on `agent()`.
  > "keep `export const meta` as the first statement, and keep it a plain object literal with a `name` and a `description`. If it contains anything other than literal values… Claude Code drops `/<name>` from `/` autocomplete."
  > "Claude Code makes `Date.now()`, `Math.random()`, and a no-argument `new Date()` throw inside the script"
  > "run the `/workflow-authoring` bundled skill to load the script-writing reference Claude works from. The skill requires Claude Code v2.1.248 or later." / "run `/reload-skills` to re-read the workflow directories"
- **Pass input to a saved workflow** — https://code.claude.com/docs/en/workflows#pass-input-to-a-saved-workflow (source: official).
  > "A saved workflow can accept input through the `args` parameter. The script reads it as a global named `args`."
- **Behavior and limits** — https://code.claude.com/docs/en/workflows#behavior-and-limits (source: official). Why the Python helper must be run *by an agent*, not by the script.
  > "No direct filesystem or shell access from the workflow itself | Agents read, write, and run commands. The script coordinates the agents"
  > "No module loading: a script that contains `import()` fails before the run starts" / "Up to 16 concurrent agents" / "1,000 agents total per run"
- **Approve the plan before it runs (permission-mode table; -p/SDK)** — https://code.claude.com/docs/en/workflows#approve-the-plan-before-it-runs (source: official).
  > "The subagents the workflow spawns use your permission rules, and Claude Code picks their permission mode by the rules under which permission mode a subagent runs in. To avoid prompts on a long run, add the tools the agents need to your allow rules before starting."
- **Turn workflows off** — https://code.claude.com/docs/en/workflows#turn-workflows-off (source: official). An org or user can disable the feature entirely — the tool needs a documented fallback.
  > "Set `\"disableWorkflows\": true` … Set `CLAUDE_CODE_DISABLE_WORKFLOWS=1`" / "When workflows are disabled, the bundled workflow commands and the `/workflow-authoring` skill are unavailable"
- **`/workflow-authoring` bundled skill (script API not on the public page)** — local skill text, invoked via `Skill("workflow-authoring")` (source: bundled skill, Claude Code ≥2.1.248). Documents the extended `agent()` options and extra globals:
  > "agent(prompt: string, opts?: {label?: string, phase?: string, schema?: object, model?: string, effort?: string, isolation?: 'worktree', agentType?: string})"
  > "opts.agentType uses a custom subagent type (e.g. 'general-purpose', 'code-reviewer') instead of the default workflow subagent — resolved from the same registry as the Agent tool"
  > meta: "Required fields: `name`, `description`. Optional: `whenToUse` (shown in the workflow list), `phases`." Also `budget`, `workflow(nameOrRef, args)` (one level of nesting), and resume via `Workflow({scriptPath, resumeFromRunId})`.

## Gaps

1. **Script-API surface split between public docs and a bundled skill.** `agent()` options `model`, `effort`, `isolation`, `agentType`, `meta.whenToUse`, the `budget` global, `workflow()` nesting, and `resumeFromRunId` appear only in the `/workflow-authoring` skill, not on https://code.claude.com/docs/en/workflows. The existing `.claude/workflows/pr-merge-order.js` already uses `whenToUse` and `effort: 'low'` (lines 4, 117, 209, 245), i.e. it depends on the skill-only surface. Cite the skill, not the web page, for those.
2. **`Workflow` tool input schema is not retrievable from public docs.** workflows.md defers to "its entry in the Agent SDK reference (/docs/en/agent-sdk/typescript#workflow)"; the fetched page truncated before any Workflow entry and Context7 (`/websites/code_claude`) has no snippet for it. Treat `script` / `scriptPath` / `name` / `args` / `resumeFromRunId` as documented only by the in-session tool schema and the bundled skill.
3. **Can a workflow `agentType` resolve a project `.claude/agents/` subagent (e.g. the PR #11 `pr-review/*` agents)?** The bundled skill says "resolved from the same registry as the Agent tool"; the public docs are silent, and `pr-merge-order.js` currently does not use `agentType` at all — so the workflow would not reuse the three reviewer agents unless changed and verified.
4. **Do project `settings.json` PreToolUse hooks (e.g. `.claude/hooks/pr-review-guard.py`) fire inside workflow-spawned agents?** workflows.md says workflow subagents "use your permission rules"; hooks.md scopes settings hooks to the project; neither states explicitly that settings-level hooks apply to workflow agents. Agent-frontmatter hooks apply only if the workflow uses `agentType` pointing at that agent.
5. **Plugin packaging constraint.** If the reviewer agents are ever shipped via `marketplace`, plugin agents cannot carry `hooks`, `mcpServers`, or `permissionMode` (plugins-reference "Agents"); the guard must move to `hooks/hooks.json`. Repo-level `.claude/agents/` has no such restriction.
6. **Workspace trust asymmetry.** Project `permissions.allow` and project agent-frontmatter hooks require the trust dialog; skill `allowed-tools` does *not* ("Workspace trust doesn't gate this field") — a repo-shipped skill can silently pre-approve `Bash(...)` prefixes. Deny rules still win.
7. **Worktree hook path semantics.** `${CLAUDE_PROJECT_DIR}` stays at the launch root while `cwd` follows the worktree (worktrees.md Note). A guard hook that inspects paths must read `cwd` from stdin JSON, not assume `${CLAUDE_PROJECT_DIR}`.
8. **Worktree Bash "command shape" guard cannot be disabled** (worktrees.md). `pr_merge_sim.py` invocations from an isolated session must be plain commands (no `$(...)`, heredocs, brace expansion) — consistent with the memory note `worktree-guard-plain-git-commands.md`.
9. **Feature gating / versions.** Workflows can be disabled per user or org (`disableWorkflows`, `CLAUDE_CODE_DISABLE_WORKFLOWS=1`), are off by default on Pro, and several behaviors are version-gated (nested `.claude/workflows/` v2.1.178; symlink refusal v2.1.216; size guideline v2.1.219; `/workflow-authoring` v2.1.248). A workflow-based tool needs a non-workflow fallback (skill + Agent tool, or the Python helper run directly).
10. **Approval UX differs from skills.** `Workflow` requires permission (tools-reference); "don't ask again" is offered only for a *saved/bundled/plugin* workflow by name, and `-p`/SDK runs never prompt — they need `Workflow` or `Workflow(pr-merge-order)` in `permissions.allow`.
11. **platform-docs MCP has no Claude Code CLI documentation.** Its `Anthropic` source (1603 docs) is `platform.claude.com` only: Agent Skills spec (`name`/`description`/`license`/`compatibility` overlap with SKILL.md), Managed Agents, Messages API. Every query for subagent frontmatter, PreToolUse JSON, plugin manifest, workflows, or worktrees returned unrelated pages — it cannot corroborate or contradict the official CLI docs.
12. **Context7 staleness.** `/websites/code_claude` returns snippets attributed to `https://code.claude.com/docs/en/slash-commands`, a page no longer in `llms.txt` (commands were merged into skills). Content matched the live skills page, but cite the live URL.
13. **Minor doc inconsistency (hooks).** The sub-agents page example passes `$TOOL_INPUT` as a CLI argument (`"./scripts/validate-command.sh $TOOL_INPUT"`), whereas the hooks reference specifies the hook receives JSON on **stdin**. Build the guard on stdin JSON per hooks.md.
