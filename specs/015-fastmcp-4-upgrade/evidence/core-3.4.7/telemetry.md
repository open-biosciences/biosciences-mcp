# Telemetry on 3.4.7 (spec 015 T019; FR-019; AGE-718 acceptance)

Run on 2026-10-01 with biosciences-otel-stack `c78e01c`. The `fastmcp-gateway` image was built from the upgrade worktree through a compose override:
- `build.context` set to the worktree, with an absolute `dockerfile`
- an isolated project (`-p bos-015`), with Phoenix on 6016 and the gateway on 8020, to avoid clashing with the stacks already running
- only `phoenix` and `fastmcp-gateway` started, then torn down with `down -v --rmi local`

| Check | Result |
|---|---|
| fastmcp version inside the container | `in-container fastmcp 3.4.7 mcp 1.26.0` |
| `opentelemetry-instrument` wrapper starts and serves | yes: 34 tools listed over HTTP; `hgnc_search_genes`, `hgnc_get_gene`, and `uniprot_get_protein` all returned `isError: false` |
| Tool-level spans in Phoenix (project `biosciences-mcp-gateway`) | yes, for example span `tools/call uniprot_get_protein` with `gen_ai.tool.name=uniprot_get_protein` and `fastmcp.server.name=Biosciences MCP Gateway`. Tool-level attribute keys seen: `gen_ai.tool.name`, `fastmcp.server.name`, `fastmcp.component.key`, `fastmcp.component.type`, `fastmcp.provider.type`, `mcp.method.name`, `mcp.session.id`. Span names include `tools/list` and `tools/call <tool>`, alongside the Starlette and httpx spans. |
| No-collector degradation | Phoenix stopped; the gateway still listed 34 tools and served `hgnc_get_gene` (`isError: false`). Its log shows only OTLP export errors. |

On 2.14.5 the same profile produced only Starlette and httpx spans, with no tool-level span (biosciences-otel-stack `README.md:113-114`). This delivers AGE-718's telemetry motivation. ADR-008 names its attributes differently (`mcp.tool.name`); reconciling the two is the follow-up filed by T053.
