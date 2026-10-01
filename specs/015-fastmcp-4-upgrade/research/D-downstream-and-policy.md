# D: Downstream consumers, version policy, ADR-008, deployment (spec 015, Phase 0)

Read-only research, 2026-09-30. Each repo was read at the checked-out HEAD: core worktree `feature/015-fastmcp-4-upgrade` @ 316fe5f, edge `main` @ 91f6bab, psychology-mcp `main` @ 12623eb, deepagents `main` @ 0947ba9, temporal `main` @ a87b97d, research `main` @ a6d5be1, marketplace `main` @ c664df8, open-biosciences-plugins `main` @ be68f5a, biosciences-skills `main` @ 6afa940, platform-skills `main` @ be24b9b, biosciences-education `main` @ 19be1cf, biosciences-otel-stack @ c78e01c. Library-source claims come from the scratchpad venvs (`envs/v4.0.10`, `envs/v3.4.7`, `envs/v2.14.5`).

Labels: **CONFIRMED** means read directly in the cited file or installed source. **INFERRED** means reasoned from that evidence and not executed.

---

## Decision-relevant summary

1. **No downstream repo caches tool schemas, snapshots `tools/list`, quotes tool descriptions, asserts on descriptions, or filters tools by description.** CONFIRMED by grep for `inputSchema|input_schema|tools/list|list_tools|additionalProperties|outputSchema|structuredContent` (zero hits) and by grepping the first line of all 33 core tool descriptions across the 8 repos (zero hits). The FastMCP 3/4 description change (`Args:`/`Returns:` stripped) and `additionalProperties:false` reach only **live LLM clients**: Claude Code plugin users and PydanticAI in temporal. Expect soft behaviour drift there, not breakage.
2. **Tool names are hard-coded in exactly two places that execute.** (a) deepagents `apps/api/shared/mcp.py:224-467`: 34 alias wrappers plus a rate-limit prefix map at `:43-63`. (b) temporal agent instructions in `agents/*.py`, which are prompt text, not code. Every other reference is skill or doc prose, mirrored about 4 times (biosciences-skills, marketplace/domain-skills, deepagents/.deepagents/skills, open-biosciences-plugins/bio-research). The upgrade must therefore preserve all **34 names byte-for-byte**. The double-prefix hazard (`hgnc_hgnc_search_genes`) is the only realistic way to break downstream.
3. **deepagents does not speak MCP to the gateway.** It POSTs raw JSON-RPC `tools/call`, with no `initialize` and no `Mcp-Session-Id` (`mcp.py:69-143`). That works only if the deployed server accepts sessionless requests (stateless HTTP). The repo does not set stateless mode (`gateway.py:48`, `fastmcp.json`), and no doc says Horizon does. **The upgrade must verify that a raw sessionless `tools/call` still succeeds on the preview deployment.** In both mcp 1.x and 2.2.0, a stateful transport returns `400 Missing session ID` (`mcp/server/streamable_http.py:913` in the 4.0.10 env, `:890` in the 2.14.5 env). The risk is therefore a Horizon setting, not a FastMCP version difference (INFERRED). deepagents reads only `result.content[].type=="text"`. FastMCP 4.0.10 still emits a TextContent block alongside `structured_content` (`fastmcp/tools/base.py:415-429`, CONFIRMED), so the parser keeps working.
4. **Protocol negotiation is not a blocker.** FastMCP 4.0.10 ships `mcp` 2.2.0. Its `HANDSHAKE_PROTOCOL_VERSIONS` still contains `2024-11-05` through `2025-11-25` (`mcp_types/version.py:33-38`). Downstream clients pin `mcp` 1.26.0 (temporal, deepagents), whose `LATEST_PROTOCOL_VERSION` is `2025-11-25`. Requests with no `MCP-Protocol-Version` header take the legacy path (`mcp/server/streamable_http.py:896-898`). CONFIRMED in source; not exercised end-to-end.
5. **temporal is coupled to core's lockfile, not its own.** It spawns `uv run fastmcp run src/biosciences_mcp/servers/gateway.py` with `cwd` set to the **sibling `biosciences-mcp` checkout** (`agents/base.py:42,61,83-86`). Merging the upgrade to core's main checkout upgrades temporal's server at the same moment. Temporal's own `fastmcp==3.0.2` (pulled in by `pydantic-ai-slim[fastmcp]`) is not used on that path (INFERRED from `MCPServerStdio` in `base.py:13`).
6. **Pre-existing argument-name drift, unrelated to the upgrade.** Several docs pass argument names the server already rejects: `gene_id`, `ligand_id`, `cid`, `ensembl_id` for `opentargets_get_associations`, `species` for `string_get_interactions`, and `organism` for `uniprot_search_proteins`. They sit in 4 mirrored skill trees and in deepagents' alias docstrings (§1.3). The upgrade neither causes nor fixes this. File it separately; do not let it be mistaken for an upgrade regression during preview testing.
7. **ADR-008 is not implemented anywhere.** There is no `telemetry/` package, no `trace_tool`, and no OpenTelemetry import in core, edge or psychology-mcp. biosciences-otel-stack instruments **externally** with `opentelemetry-instrument`. FastMCP 4 has native tool spans and W3C `traceparent` propagation through `_meta` (`fastmcp/server/telemetry.py:124-152`, `fastmcp/telemetry.py:173-300`). It also has a `telemetry_mode` setting (`native|propagation_only|off`, `fastmcp/settings.py:154-175`). That overlaps ADR-008 §2(a)/(b), but with different span names and attributes (`gen_ai.tool.name`, not `mcp.tool.name`). FR-019's phrase "where implemented" currently covers only the external otel-stack path.
8. **Version-policy enforcement has nowhere to run in core or edge.** Core has only Claude review workflows. Edge has no `.github/` directory at all. Only psychology-mcp has a blocking CI (`ci.yml`). **Repo docs say Horizon resolves dependencies from `pyproject.toml`, and the edge pin commit says the version "floats" on redeploy.** A policy check that reads only `uv.lock` would therefore miss what production installs. Check the `pyproject.toml` specifier **and** the lock.
9. **platform-skills scaffolds do not generate a `pyproject.toml` and write no fastmcp pin.** They scaffold a server module into the existing `biosciences_mcp` package. No repo has a scaffold that creates a new connector repo, so connector repos are hand-made today.
10. **Deployment: no doc in these repos names a Horizon Python runtime or a FastMCP version Horizon uses.** The program docs state this explicitly as an open question (`interface-version-tradeoff-analysis.md:60,244`). Documented facts:
    - Horizon redeploys on every push to `main`.
    - Horizon reads dependencies from `pyproject.toml`.
    - `fastmcp.json` is "not confirmed to be read by Horizon".
    - FastMCP 3.4.3's Host guard returned 421 on `*.fastmcp.app` (edge commit d4b9502), with the documented remedy `FASTMCP_HTTP_ALLOWED_HOSTS`.
11. **Correction to spec 015 context (spec.md:15).** biosciences-research is described there as running "graph-builder workflows" against the tools. At HEAD it has **no MCP runtime usage**: no `mcp`/`fastmcp` dependency, no endpoint, and its LangGraph graphs are RAG retrievers (`langgraph.json:7-12`). It only names tools in docs and in an evaluation dataset. CONFIRMED.

---

## 1. Downstream consumers

### 1.1 Table

Legend for the last two columns: **HARD** means code or config fails. **SOFT** means an LLM-facing doc or prompt goes stale or behaviour may drift. **No** means not affected.

| Repo | file:line | Depends on | Breaks if names change? | Breaks if descriptions/schemas change? |
|---|---|---|---|---|
| biosciences-deepagents | `apps/api/shared/mcp.py:192` (`BIOSCIENCES_MCP_URL` default `https://biosciences-mcp.fastmcp.app/mcp`), `.env.example:20`, `CLAUDE.md:50,86-87` | endpoint | n/a | n/a |
| biosciences-deepagents | `apps/api/shared/mcp.py:69-143` (`HTTPMCPClient`: raw `tools/call` POST, Bearer auth, no `initialize`, no session header, parses SSE `data:` or JSON `result.content[type=text]`) | endpoint + transport behaviour | n/a | **HARD if** the server stops accepting sessionless POSTs or stops emitting a text content block. Text block CONFIRMED still emitted in 4.0.10 (`fastmcp/tools/base.py:415-429`). Stateless acceptance is unverified (summary item 3). |
| biosciences-deepagents | `apps/api/shared/mcp.py:224-263` (`BIOSCIENCES_ALIAS_TOOL_NAMES`, 34 names), `:266-467` (34 `@tool` wrappers calling `_call_biosciences_alias("<name>")`) | **name** (hard-coded string per tool) | **HARD**: the call returns `"Error from MCP server: ..."` as a string. No exception, so agents see an error string. | **No** for descriptions: each wrapper carries its own docstring and its own `(query, tool_args)` schema. The core description never reaches the LLM (CONFIRMED). Schema: `tool_args` is passed through verbatim, so `additionalProperties:false` adds nothing, because undeclared args are already rejected. |
| biosciences-deepagents | `apps/api/shared/mcp.py:43-63` (`get_service_from_tool`: rate-limit bucket by `string_`/`chembl_`/... prefix) | name prefix | SOFT: unknown prefixes fall to the `default` bucket (0.1 s) | No |
| biosciences-deepagents | `apps/api/biosciences.py:30-67` (imports the 34 wrappers), `:310-345+` (per-subagent tool lists) | name (Python identifiers mirror tool names) | HARD only if renamed in `mcp.py` too; the import is local | No |
| biosciences-deepagents | `apps/api/shared/prompts.py:22-23,30-32,38-39,61-64,92-94,122-124,158,186-193` ("Available: hgnc_search_genes, ...") | name (prompt text) | SOFT | No |
| biosciences-deepagents | `apps/api/shared/mcp.py:310,334,394,406,424` (docstring argument hints `gene_id`, `species`, `ligand_id`, `target_id`, `ensembl_id`) | **parameter names** | n/a | **Already broken today**: these names are not in the core schemas (`entrez_id`, `iuphar_id`, `target_id`; `string_get_interactions` has no `species`). Not caused by the upgrade. |
| biosciences-deepagents | `.mcp.json:3-9` (`biosciences-mcp` http + Bearer) | endpoint (Claude Code dev use) | SOFT (prose only) | SOFT (live LLM) |
| biosciences-deepagents | `.deepagents/skills/*/SKILL.md` (e.g. `biosciences-genomics/SKILL.md:38`, `biosciences-graph-builder/SKILL.md:67-68,635`) | name + parameter examples + endpoint | SOFT | SOFT; contains pre-existing argument drift (§1.3) |
| biosciences-temporal | `src/biosciences_temporal/agents/base.py:13,42,58,61,83-86,200` (`MCPServerStdio('uv', ['run','fastmcp','run', GATEWAY_SERVER], cwd=<sibling biosciences-mcp>)`, `toolsets=[mcp]`) | **core source tree + core's venv/lock** via stdio; `fastmcp run <path.py>` CLI | HARD only through agent prompts below | SOFT: PydanticAI forwards the live description and `inputSchema` to `openai:gpt-4.1-mini` (`base.py:64`), so description loss may shift tool choice. Also HARD **if** `fastmcp run <file>.py` stops defaulting to stdio. In 4.0.10 a `.py` spec does not read `fastmcp.json`, and transport falls back to `settings.transport` (`fastmcp/cli/run.py:175-200,247-255`), so stdio is kept (INFERRED). |
| biosciences-temporal | `agents/resolve.py:14-15`, `enrich.py:14`, `drugs.py:14-16`, `trials.py:14`, `expand.py:14-16`, `validate.py:14,20,32,39-41` (instructions such as `hgnc_get_gene(hgnc_id=...)`, `biogrid_get_interactions(max_results=100)`) | name + parameter names (prompt text) | SOFT, but the agent will call non-existent tools | No. All cited parameter names match current schemas (CONFIRMED against `tools_before.json`). |
| biosciences-temporal | `.env.example:10-14` (mentions `biosciences-mcp.fastmcp.app` as an alternative) | endpoint (comment) | No | No |
| biosciences-temporal | `docs/validation/cq14-temporal-workflow-design.md:156`, `docs/validation/cq14-graph-payload.json` | name (docs and data) | SOFT (stale docs) | No |
| biosciences-research | `docs/competency-questions-catalog.md:74-78,106-109,139-142,164-167,190-193,217`; `data/interim/competency_questions_sample.json` (`workflow_steps`); `data/interim/dataset_card_README.md` | name (eval dataset and docs) | SOFT: gold workflows go stale. No runtime connection. | No |
| marketplace | `{biogrid,chembl,clinicaltrials,ensembl,entrez,hgnc,iuphar,opentargets,pubchem,string,uniprot,wikipathways}/.mcp.json:3-8`: **each of the 12 per-server plugins points at the full gateway** `https://biosciences-mcp.fastmcp.app/mcp` with Bearer auth | endpoint | No (no tool filter in config) | SOFT (live LLM) |
| marketplace | `README.md:23-34,67`, `CONNECTORS.md:22,33+`, `CLAUDE.md:26`, `CONTRIBUTING.md:37,100` | name + endpoint (docs) | SOFT | No |
| marketplace | `domain-skills/skills/*/SKILL.md` (e.g. `biosciences-genomics/SKILL.md:32`, `biosciences-graph-builder/SKILL.md`, 34 distinct names) | name (both bare and `mcp__biosciences-mcp__<name>`) + parameter examples | SOFT | SOFT; pre-existing argument drift (§1.3) |
| marketplace | `platform-tools/commands/scaffold-fastmcp*.md` (copy of platform-skills) | generated docstrings use `Args:`/`Returns:` | No | Generated servers lose `Args:` from descriptions on 3/4.x (cosmetic) |
| open-biosciences-plugins | `bio-research/.mcp.json:3-16` (`biosciences-mcp` and `biosciences-mcp-edge` http + Bearer) | endpoint (core + edge) | No | SOFT (live LLM) |
| open-biosciences-plugins | `bio-research/skills/biosciences-crispr/SKILL.md:14-15` (`mcp__biosciences-mcp-edge__get_orcs_essentiality(entrez_id=N, hit_only=...)`); `biosciences-pharmacology/SKILL.md:85,220` (`get_mechanism(chembl_id=...)`) | **edge** name + parameters | SOFT | SOFT. Parameter names match edge's signature (CONFIRMED via `docs/adr/README.md` in edge). |
| open-biosciences-plugins | `bio-research/skills/biosciences-cq-runner/SKILL.md:160-176` (preflight lists required tools by name), `:780` (`curl https://biosciences-mcp.fastmcp.app/health`) | name + endpoint | SOFT; the preflight is LLM-evaluated | No. `/health` is not defined by core or edge (`grep custom_route|/health` in `src/` finds nothing), so that hint is already wrong. |
| open-biosciences-plugins | `bio-research/references/fuzzy-to-fact.md:14,18`, `token-budgeting.md:21-22`, `commands/ob-research.md:54`, `commands/ob-review.md:71`, `skills/biosciences-graph-builder/SKILL.md`, `skills/biosciences-publication-pipeline/references/agent-prompts.md` | name + parameter examples | SOFT | SOFT |
| open-biosciences-plugins | `docs/research/connectors/DECISION.md:104` (records the live scoped form `mcp__plugin_bio-research_biosciences-mcp__*`) | name format | SOFT | No |
| open-biosciences-plugins | `psychology-research/.mcp.json:3-8` (`psychology-mcp.fastmcp.app`) | psychology-mcp endpoint (not core) | n/a | n/a |
| biosciences-skills | `.mcp.json:3-8`, `.env.example:1,12` | endpoint | No | SOFT |
| biosciences-skills | `CLAUDE.md:96-106+`: documents the gateway's `mount(..., prefix="hgnc", as_proxy=False, tool_names={...})` and the 34-row name table | name + **core implementation detail** | SOFT | No. Goes stale when the gateway mount changes (`prefix` to `namespace`, `as_proxy` and `tool_names` removed per backlog N6). |
| biosciences-skills | `.claude/skills/*/SKILL.md` (source of the mirrored skills; e.g. `biosciences-genomics/SKILL.md:32,201,216`, `biosciences-proteomics/SKILL.md:53,121,175`) | name + parameter examples | SOFT | SOFT; pre-existing argument drift (§1.3) |
| platform-skills | `.mcp.json:3-8` | endpoint | No | SOFT |
| platform-skills | `.claude/commands/scaffold-fastmcp-v2.md:68-133`, `scaffold-fastmcp.md:66-120` | FastMCP API used by generated code (`FastMCP(name)`, bare `@mcp.tool`, docstring `Args:`) | No | No (see §4) |
| biosciences-education | `CLAUDE.md:11,24,37,50`, `README.md:32-38,58` | none concrete: planned tutorials only, no names, no URLs | No | No |

Outside the named scope but found on the way (all CONFIRMED):
- `open-biosciences-spark-plugins/skills/ob-target-dossier/SKILL.md:15` and others name tools. Its `cloud-run/Dockerfile:4-31` plus `deploy.sh` build **core** with `uv sync --frozen` and run it on Cloud Run under `opentelemetry-instrument`. This is a second deployment of the gateway that the upgrade will reach.
- `knowledge-work-plugins/bio-research/.mcp.json:23-25` and `biosciences-rag-pipeline/.mcp.json:5` point at the core endpoint.

### 1.2 What is not depended on (CONFIRMED)

- **Tool descriptions as data**: no repo quotes, asserts or filters on them. The only "Strict Phase 2 / Fuzzy Phase 1" strings downstream are in `biosciences-research/docs/prior-art-api-patterns.md:53-54`, an API-pattern table, not a quote of a tool description.
- **Cached schemas**: nothing persisted. PydanticAI and Claude Code fetch `tools/list` live per session.
- **Claude Code `allowed-tools` pinning**: no skill or command frontmatter names MCP tools. The only `tools:` key is `marketplace/speckit/commands/speckit.taskstoissues.md:3`, for GitHub. So a name change would not silently de-permission anything.
- **FastMCP `Client` usage downstream**: none. deepagents uses raw httpx for the gateway and `mcp.ClientSession` only for a local stdio PubMed server (`mcp.py:146-172`). `langchain-mcp-adapters` is declared (`pyproject.toml:23`) but never imported. temporal uses `pydantic_ai.mcp.MCPServerStdio`, which is built on the `mcp` SDK.

### 1.3 Pre-existing argument-name drift (already rejected today; independent of the upgrade)

These examples pass names that are not in the current core `inputSchema`. The caller confirmed that undeclared arguments are already rejected on today's version, so all of these fail today. Each appears in all 4 skill mirrors unless noted:

| Tool | Wrong argument | Schema has | Example location |
|---|---|---|---|
| `biogrid_get_interactions` | `gene_id` | `gene_symbol` | `biosciences-skills/.claude/skills/biosciences-proteomics/SKILL.md:175` |
| `string_get_interactions` | `species` | `string_id, required_score, limit` | `.../biosciences-proteomics/SKILL.md:121`, `.../biosciences-graph-builder/SKILL.md:301`; deepagents `mcp.py:334` |
| `uniprot_search_proteins` | `organism` | `query, slim, cursor, page_size` | `.../biosciences-proteomics/SKILL.md:53` |
| `entrez_get_gene` | `gene_id` | `entrez_id` | `.../biosciences-genomics/SKILL.md:201` |
| `entrez_get_pubmed_links` | `gene_id` | `entrez_id` | `.../biosciences-genomics/SKILL.md:216`; deepagents `mcp.py:310` |
| `pubchem_get_compound` | `cid` | `pubchem_id` | `.../biosciences-pharmacology/SKILL.md:181` |
| `iuphar_get_ligand` | `ligand_id` | `iuphar_id` | `.../biosciences-pharmacology/SKILL.md:213`; deepagents `mcp.py:394` |
| `iuphar_get_target` | `target_id` | `iuphar_id` | deepagents `mcp.py:406` |
| `opentargets_get_associations` | `ensembl_id` | `target_id` | 16 locations, e.g. `marketplace/domain-skills/skills/biosciences-clinical/SKILL.md:70`; deepagents `mcp.py:424` |

Method: a regex over `Call \`tool\` with: {...}` and `tool(k=v)` forms, compared against `tools_before.json` properties. Prose-form `tool(k=...)` examples in temporal, research and bio-research all matched the schema.

---

## 2. Downstream fastmcp/mcp pins and client-version relevance

| Repo | pyproject pin (file:line) | Lock (file:line) | Runs an MCP client against core/edge? | Version-sensitive? |
|---|---|---|---|---|
| biosciences-mcp (core) | `fastmcp>=2.14.1,<3.0` (`pyproject.toml:10`) | fastmcp 2.14.5 (`uv.lock:532-533`), mcp 1.26.0 (`:825-826`) | Its own e2e tests use `fastmcp.Client` against Cloud | Yes, but internal to core |
| biosciences-mcp-edge | `fastmcp>=2.0,<3.4.3` (`pyproject.toml:12`); `.python-version` = 3.11 (tracked) | fastmcp 3.0.2 (`uv.lock:361-362`), mcp 1.26.0 (`:593-594`) | n/a | n/a |
| psychology-mcp | `fastmcp>=2.14.1,<3.0` (`pyproject.toml:8`) | fastmcp 2.14.7 (`uv.lock:403-404`), mcp 1.29.0 (`:706-707`) | n/a | n/a |
| biosciences-deepagents | `mcp>=1.25.0` (`pyproject.toml:22`), `langchain-mcp-adapters>=0.2.1` (`:23`), no fastmcp | mcp 1.26.0 (`uv.lock:1357-1358`), langchain-mcp-adapters 0.2.1 (`:1116-1117`) | **Yes, raw httpx JSON-RPC** (no SDK) to the core endpoint | Not SDK-version-sensitive. Sensitive to server session mode and response shape (summary item 3). |
| biosciences-temporal | none direct; `pydantic-ai[temporal]>=1.42.0` (`pyproject.toml:9`) | pydantic-ai 1.63.0 (`uv.lock:2001-2002`), fastmcp 3.0.2 (`:726-727`, via `pydantic-ai-slim[fastmcp]`), mcp 1.26.0 (`:1409-1410`) | **Yes, stdio**; `mcp` 1.26 `ClientSession` via PydanticAI; the server process uses **core's** env | Client offers `2025-11-25`. The 4.0.10 server (mcp 2.2.0) supports it in `HANDSHAKE_PROTOCOL_VERSIONS` (`mcp_types/version.py:33-38`), so negotiation succeeds (CONFIRMED in source; INFERRED end to end). |
| biosciences-research | none | none | No | No |
| marketplace, open-biosciences-plugins (bio-research), biosciences-skills, platform-skills | none (no Python project for bio-research) | none | Yes, **Claude Code** over HTTP; client version lives outside these repos | Handshake path retained in mcp 2.2.0, so any client up to `2025-11-25` works (INFERRED) |
| biosciences-education | none | none | No | No |
| biosciences-memory (aside) | `fastmcp>=2.13.3,<3` (`pyproject.toml:12`) | `uv.lock:119` | It is a server, not a core consumer | Out of scope; listed because N7 counts it in the org pin table |

Protocol notes (CONFIRMED from installed source):
- `mcp` 2.2.0 (bundled with 4.0.10) adds `MODERN_PROTOCOL_VERSIONS = ("2026-07-28",)`, a "stateless per-request envelope", while keeping all four handshake versions (`mcp_types/version.py:24-44`).
- Era routing is header-only. A request whose `MCP-Protocol-Version` is absent, or is in the handshake set, reaches the legacy transport (`mcp/server/streamable_http_manager.py:187-194`; `mcp/server/streamable_http.py:895-898`).
- Session validation in that legacy transport is unchanged from mcp 1.x: `400 Missing session ID` when sessions are enabled and the header is absent (`streamable_http.py:900-915`).

---

## 3. ADR-008: implementation status and what an upgrade must keep working

ADR-008 (`biosciences-mcp/docs/adr/accepted/adr-008-v1.0.md`, accepted 2026-09-24) mandates the following. Each item is checked against the code.

| ADR-008 item | Status | Evidence |
|---|---|---|
| §4.1 `biosciences_mcp/telemetry/tracer.py` with `get_tracer()` and `@trace_tool` | **Not implemented** | `src/biosciences_mcp/` contains only `__init__.py, clients/, models/, servers/`; `grep trace_tool\|get_tracer\|opentelemetry` over core `src/` and `tests/` finds nothing (CONFIRMED) |
| §4.2 spans in `LifeSciencesClient._rate_limited_get` (`http.retry_attempt`, etc.) | **Not implemented** | Same grep (CONFIRMED) |
| §4.3 `tests/telemetry/test_trace_contract.py` | **Not present** | `tests/` has `contract, e2e, fixtures, integration, unit` (CONFIRMED) |
| §3 Negative: adds `opentelemetry-api`/`-sdk` to `pyproject.toml` | **Not done** | Core `pyproject.toml` has no OTel dependency. `opentelemetry-api` 1.39.1 is in `uv.lock` only transitively via `pydocket` (`uv.lock:889`, dependency at `:1144`) (CONFIRMED) |
| Edge, psychology-mcp | **Nothing** | Zero grep hits (CONFIRMED) |
| biosciences-otel-stack | **External instrumentation, not ADR-008** | `Dockerfile.fastmcp:18-47` wraps `fastmcp run` in `opentelemetry-instrument` (python 3.12 image, `uv sync --frozen`), and `docker-compose.yml:69-94` (`mcp` profile) builds `../biosciences-mcp`. `docs/consumers.md:32-44` says to keep OTel packages **out of** the consumer `pyproject.toml` and records that FastMCP 2.x gives only Starlette and httpx spans, while 3.x adds tool spans (`fastmcp.server.name`, `gen_ai.tool.name`, `mcp.session.id`). `README.md:57-60`: without the wrapper every span is a silent no-op. |

What FastMCP 4.0.10 brings natively (CONFIRMED in `envs/v4.0.10`):
- `fastmcp/server/telemetry.py`: a per-request SERVER span opened at the middleware seam (`seam_span`), carrying `mcp.method.name`, `fastmcp.server.name`, `fastmcp.component.*` and `gen_ai.tool.name` (`:124-152`), plus `error.type` on exceptions (`:155-162`).
- `fastmcp/telemetry.py:48-49,173-174,290,300`: W3C `traceparent`/`tracestate` injection and extraction through request `_meta`. This is ADR-008 §2(b), done by the framework.
- `fastmcp/settings.py:154-175`: `telemetry_mode` with values `native` (default), `propagation_only` (for when another layer owns the MCP span hierarchy) and `off`.
- `opentelemetry-api>=1.28.0` is a dependency of `fastmcp-slim[server]`, which `fastmcp` 4.0.10 requires (`fastmcp-4.0.10.dist-info/METADATA`: `fastmcp-slim[client,server]==4.0.10`).

What the upgrade must keep working (FR-019), as INFERRED from the above:
1. **The otel-stack path is the only implemented path, so it is the only regression surface.** After the upgrade, `opentelemetry-instrument fastmcp run src/biosciences_mcp/servers/gateway.py:mcp --transport http` must still start, still produce Starlette and httpx spans, and now also FastMCP tool spans. The `:mcp` entrypoint suffix and the `--transport http --host --port` flags must keep working in the 4.x CLI. `consumers.md:37-44` should gain a 4.x row.
2. **The offline invariant (§2(d))**: with no SDK configured, FastMCP 4's spans are no-ops (`fastmcp/settings.py:160-163` says so). Unit and contract tiers must stay network-free, so assert that no exporter is configured by default.
3. **When ADR-008 is later implemented on 4.x**, its custom `mcp.tool_call` parent span would duplicate FastMCP's native SERVER span. Either set `telemetry_mode=propagation_only` or amend ADR-008 to adopt the native span and attributes (`gen_ai.tool.name` instead of `mcp.tool.name`). This is an ADR decision, not upgrade work, but spec 015 should record it so FR-019 is not read as requiring `@trace_tool`.
4. The spark-plugins Cloud Run image (`open-biosciences-spark-plugins/cloud-run/Dockerfile:18-31`) uses the same `opentelemetry-instrument` wrapper over core's lock and will pick up the upgrade on rebuild.

---

## 4. Version-policy enforcement

### 4.1 CI today (CONFIRMED)

| Repo | Workflows | Runs tests or lint? |
|---|---|---|
| biosciences-mcp | `.github/workflows/claude-code-review.yml` (Claude `/code-review` on PRs), `claude.yml` (`@claude` mentions) | **No.** Neither runs pytest, ruff, pyright or `fastmcp inspect`. No `.pre-commit-config.yaml`. `.claude/hooks/pr-review-guard.py` is a Claude Code hook, not a gate. |
| biosciences-mcp-edge | **no `.github/` directory** | **No.** No pre-commit. |
| psychology-mcp | `.github/workflows/ci.yml:1-86` | **Yes, blocking.** On push to main and on PRs: `uv python install 3.11` (`:28`), `uv sync --extra dev` (`:34`), `ruff check` (`:37`), `ruff format --check` (`:42`), `pyright` (`:45`), `pytest -m unit` (`:51`), `fastmcp inspect fastmcp.json` (`:58`), and a tool-surface assertion via `--format fastmcp -o inspect.json` (`:67-78`). No version-policy check. |

Related backlog, not yet landed (CONFIRMED state):
- `biosciences-program/docs/plans/2026-09-12-backlog-triage-action-list.md:865-967` (N2) proposes porting psychology-mcp's `ci.yml` to core and adding `pytest -m contract` plus a 34-name `fastmcp inspect` assertion.
- `:971+` (N3) asks for an exact 34-name guard. Today `tests/integration/test_gateway.py:6-7,64` is still unmarked and asserts `len(tool_names) >= 30`, so marker-scoped CI would skip it.
- N7 (`:1349-1415`) proposes the `fastmcp>=X.Y.Z,<X.(Y+1)` convention and a tracked `.python-version`.

### 4.2 Where a policy check could live

The key fact for design: repo docs say production installs from **`pyproject.toml`**, not from `uv.lock`.
- `psychology-mcp/docs/DEPLOYMENT.md:40,44-58`: "Dependencies are auto-detected from `pyproject.toml`".
- `backlog-triage-action-list.md:1295-1297`: "`biosciences-mcp.fastmcp.app` resolves its FastMCP major from `pyproject.toml`".
- Edge commit d4b9502: "The unbounded fastmcp floor here floats to 3.4.3 on the next FastMCP Cloud redeploy", although edge's lock says 3.0.2.

A lock-only check therefore does not constrain what Horizon installs (INFERRED from docs; not verified against Horizon). Options, in rough order of leverage:

1. **A pytest unit test in each connector repo.** Mark it `unit` so it rides along with every existing local and CI unit run. It would read `pyproject.toml` with `tomllib` and assert that the `fastmcp` specifier equals or is contained in the policy range. It would also read `uv.lock` and assert the locked `fastmcp` version lies inside that range, and optionally assert `importlib.metadata.version("fastmcp")` matches the lock. It needs no network and works today in all three repos, with or without CI. Weakness: the policy range is duplicated per repo unless fetched from `biosciences-program`. It also gates nothing in core or edge until CI exists, because nothing runs tests on PRs there.
2. **A CI step.** It is natural in psychology-mcp's `ci.yml`, after `uv sync`. In core it would sit in the N2 port. Edge needs a workflow created from scratch. Add `uv lock --check` (fails if the lock is stale against `pyproject.toml`) next to the range assertion. A reusable workflow in `biosciences-program` could hold the single policy range and be called from all three repos, which keeps "one policy" literally single-sourced.
3. **pre-commit**: not used in any of the three repos, so it is new tooling with no enforcement on GitHub.
4. **The `fastmcp inspect` step that already exists in psychology-mcp** (`ci.yml:58-78`) could also print `fastmcp version`, but it does not enforce a range.

### 4.3 platform-skills scaffolds

- `platform-skills/.claude/commands/scaffold-fastmcp.md` (255 lines) and `scaffold-fastmcp-v2.md` (350 lines), mirrored in `marketplace/platform-tools/commands/`, **do not generate a `pyproject.toml` and write no fastmcp pin.** `grep -n pyproject` returns nothing in either (CONFIRMED). They generate:
  - `src/biosciences_mcp/servers/<api>.py`, using `from fastmcp import FastMCP`, `FastMCP("<API_NAME> Server")`, bare `@mcp.tool`, and Google-style `Args:`/`Returns:` docstrings (`scaffold-fastmcp-v2.md:68-133`)
  - a client stub
  - tests, inside the **existing** `biosciences_mcp` package. Step 1 (`scaffold-fastmcp-v2.md:41-44`) aborts if the server already exists in `src/biosciences_mcp/servers/`.
- No repo has a scaffold that creates a new connector repo with its own `pyproject.toml`. psychology-mcp and edge were hand-made (CONFIRMED by the absence of any scaffold that writes a `pyproject`). If spec 015 wants the policy applied to new connector repos, the template has to be written. `biosciences-workspace-template` has no fastmcp references (grep CONFIRMED).
- On 3.x and 4.x, scaffolded tools would have their `Args:` folded into parameter descriptions, the same behaviour as the existing tools. Cosmetic only.

---

## 5. Deployment (only what the repos' docs say)

### 5.1 `fastmcp.json` (CONFIRMED; identical shape in all three repos, schema `https://gofastmcp.com/public/schemas/fastmcp.json/v1.json`)

| Repo | `source.path` : `entrypoint` | `environment` | `deployment` |
|---|---|---|---|
| core | `src/biosciences_mcp/servers/gateway.py` : `mcp` | `python: ">=3.11"`, `project: "."` | `transport: "http"`, `log_level: "INFO"` |
| edge | `src/biosciences_mcp_edge/server.py` : `mcp` | same | same |
| psychology-mcp | `src/psychology_mcp/servers/gateway.py` : `mcp` | same | same |

None declares `env` entries (`psychology-mcp/docs/DEPLOYMENT.md:122-125`). None sets `stateless`.

### 5.2 What the docs say about Horizon

- Core `CLAUDE.md:137-178` and `README.md:70-110`:
  - deployment is through the Prefect Horizon web UI
  - entrypoint is `src/biosciences_mcp/servers/gateway.py:mcp`
  - secrets `BIOGRID_API_KEY` and `NCBI_API_KEY` are set in the console
  - the server name `biosciences-mcp` sets the subdomain
  - the endpoint is `https://biosciences-mcp.fastmcp.app/mcp`
  - Bearer `BIOSCIENCES_API_KEY` is required
  - "There is no `fastmcp deploy` or `fastmcp auth` CLI command in FastMCP 2.x" (`CLAUDE.md:154`, `README.md:73`). The 4.0.10 package does contain `fastmcp/cli/deploy/` (`command.py` "Public Prefect Horizon authentication commands", `horizon_client.py`) (CONFIRMED in the installed package). These two docs lines are explicitly 2.x-scoped and will need updating after the upgrade. This says nothing about how Horizon itself behaves.
- `psychology-mcp/docs/DEPLOYMENT.md`:
  - `:14-20`: Horizon "redeploys on every push to `main`"; no deploy CLI (as of 2.x)
  - `:40-58`: dependencies are auto-detected from `pyproject.toml`, and core and edge deploy with no `requirements.txt`
  - `:126-127`: `fastmcp.json` is "Not confirmed to be read by Horizon … Horizon's deployment page documents four UI fields and does not mention `fastmcp.json`"
  - `:141-143`: the OAuth toggle is a Horizon UI setting.
- Edge commit `d4b9502` (2026-07-06), message only:
  - FastMCP 3.4.3 added a default-on `HostOriginGuardMiddleware` (PrefectHQ/fastmcp#4405)
  - it returns 421 for Hosts outside a localhost allowlist, including `*.fastmcp.app`
  - this happened to hci-canon on 2026-07-06
  - remedy: unpin and set `FASTMCP_HTTP_ALLOWED_HOSTS=["<host>.fastmcp.app"]` on the Cloud app.
- `biosciences-program/docs/plans/2026-09-12-interface-version-tradeoff-analysis.md:60,195,244`: "the [Horizon] deployment docs state no supported version range". Whether Horizon builds FastMCP 4 and honours the v1 `fastmcp.json` schema is an **open question** that "needs a preview deployment or a direct question".
- **Python runtime and FastMCP version on Horizon: not stated in any doc in these repos** (grep for `horizon` combined with `python|version|runtime` across core, edge, psychology-mcp and biosciences-program docs: CONFIRMED absent). The only Python versions written down are local and alternative deployments:
  - `.python-version` 3.11 in edge
  - psychology-mcp CI `uv python install 3.11`
  - python 3.12 base images in `biosciences-otel-stack/Dockerfile.fastmcp:18` and `open-biosciences-spark-plugins/cloud-run/Dockerfile:4`.

### 5.3 Other deployments of core the upgrade reaches (CONFIRMED)

- Local otel-stack container (`biosciences-otel-stack/docker-compose.yml:69-94`, builds from `../biosciences-mcp`, the main checkout, with `uv sync --frozen`).
- Cloud Run via `open-biosciences-spark-plugins/cloud-run/` (`uv sync --frozen` over core's lock, `--allow-unauthenticated`, `*.run.app` host). INFERRED: on 3.4.3 and later, the Host guard would need that host allow-listed too, the same as `*.fastmcp.app`.
- temporal's stdio subprocess (§1.1).
