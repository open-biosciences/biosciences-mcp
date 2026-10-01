# C: biosciences-mcp-edge sandbox, FastMCP 3.0.2 to 4.0.10 (Phase 0, spec 015)

- Worktree: `_audits/fastmcp-4-2026-09-30/worktrees/edge`, detached from `biosciences-mcp-edge` `91f6bab`.
- Local commits (not pushed):
  - `4fa8de0` relocks `uv.lock` so its metadata matches the `<3.4.3` pin. fastmcp stays 3.0.2 (see §0).
  - `90f7bb0` runs `uv add 'fastmcp==4.0.10'`.
- No respx and no other dependency was added. Every simulation monkeypatches `httpx.AsyncClient.send`.
- Core reference: `biosciences-mcp` main `69f403b`, read-only.
- Scripts: `C-edge_capture.py` (surface and wire capture), versioned in this repository as `research/edge-capture/edge_capture.py`; `C-host_probe.sh` (HTTP Host probe) was not committed and remains in the out-of-repo audit folder.
- Labels: **CONFIRMED** means observed in this run, or read directly in code at the cited line. **INFERRED** means reasoned but not executed.

## Decision-relevant summary

1. **The upgrade to 4.0.10 does not change edge's wire output.** CONFIRMED.
   - All 9 captured calls produce identical `structuredContent` and text content at 3.0.2 and 4.0.10 (6,512 leaf paths, 0 differences apart from the version fields).
   - Unit tests pass 11/11 at both versions. They never import fastmcp, so they say nothing about the framework.
2. **The tool surface changes at 4.0.10.** CONFIRMED. outputSchema, annotations (null) and `x-fastmcp-wrap-result` are unchanged. Three things differ:
   - (a) `description` is cut to the docstring's summary line, and the `Returns:` section is dropped completely.
   - (b) The `Args:` text moves into `inputSchema.properties.*.description`.
   - (c) An auto-generated `title` appears: "Get Mechanism", "Get Orcs Essentiality".
   - Any snapshot that compares descriptions will show a diff. Agents lose the prose saying the tool returns "PaginationEnvelope ... or ErrorEnvelope".
3. **4.0.10 logs a new pydantic serializer warning on every successful call.** CONFIRMED. Output is unaffected.
   - Cause: `PaginationEnvelope.create(...)` builds the unparametrised class, while the tool is annotated `PaginationEnvelope[X] | ErrorEnvelope`.
   - Fix: call `PaginationEnvelope[X].create(...)`, which gives 0 warnings in the repro.
   - Core has 21 unparametrised constructions and 0 parametrised ones, so core will probably warn the same way. INFERRED.
4. **The Host guard is not a blocker at 3.4.7 or 4.0.10.** CONFIRMED locally.
   - Only 3.4.3, run as a control, returns 421 for `Host: biosciences-mcp-edge.fastmcp.app`.
   - 3.0.2, 3.4.7 and 4.0.10 return 200, because `http_host_origin_protection` defaults to `False` from 3.4.7 on (3.4.3 defaulted to `True`).
   - At 4.0.10, turning protection on (`FASTMCP_HTTP_HOST_ORIGIN_PROTECTION=true`) brings the 421 back. Adding `FASTMCP_HTTP_ALLOWED_HOSTS=["biosciences-mcp-edge.fastmcp.app"]` restores 200.
   - So the `<3.4.3` pin can be lifted. Whether FastMCP Cloud sets either variable itself is not verified. INFERRED.
5. **4.0.10 brings in a large set of new dependencies.** CONFIRMED.
   - mcp 1.26.0 → **2.2.0** (plus `mcp-types`), starlette 0.52.1 → **1.7.0**.
   - New: `fastmcp-slim`, `httpx2`/`httpcore2`, `griffelib`, `joserfc`.
   - The client API renamed fields to snake_case. `CallToolResult.isError`/`structuredContent` and `Tool.inputSchema`/`outputSchema` still work but emit `FastMCPDeprecationWarning`.
   - `Client.call_tool` no longer takes `task`, `task_id` or `ttl`.
   - Edge's own `httpx` stays at 0.28.1.
6. **There are pre-existing defects that occur at both versions.** All CONFIRMED on the wire unless marked.
   - **SECURITY.** On any ORCS HTTP error other than 429, the `UPSTREAM_ERROR` message contains the full request URL, including `accesskey=<BIOGRID_API_KEY>`. This is `server.py:44` combined with `clients/biogrid_orcs.py:55-60`. It was captured using a fake key.
   - **The departure documented in docs/adr/README.md is not implemented as written.**
     - Free text sent to `get_orcs_essentiality` (`entrez_id: int`, `server.py:23`) gets a raw pydantic validation error with `isError: true`, not an `UNRESOLVED_ENTITY` envelope.
     - Free text sent to `get_mechanism` does return `UNRESOLVED_ENTITY`, but the hint ("Use a search tool to resolve the identifier first.", `models/envelopes.py:44`) names no tool. Core does expose `chembl_search_compounds`, `hgnc_get_gene` and `entrez_get_gene`.
   - `invalid_input` holds the ValueError text rather than the caller's input, and `message` wraps that text a second time (`server.py:75-76`).
   - A missing `BIOGRID_API_KEY` is reported as `UNRESOLVED_ENTITY` (`biogrid_orcs.py:51-53` → `server.py:39-40`).
   - **Nulls on the wire.** `invalid_input: null` appears on RATE_LIMITED and UPSTREAM_ERROR (core omits it), and item fields come through as null: 1,409 nulls in one ORCS response, and `target_name: null` on every ChEMBL mechanism.
   - ORCS returns all 352 screens in one page (about 44 KB of text) while reporting `page_size: 50` and `cursor: null`.
7. **ADR-007 §2(f) is not satisfied in either repo.**
   - Edge opens a new `httpx.AsyncClient` on every call. It has no retry, no backoff and no `Retry-After` handling. ChEMBL has no throttle at all.
   - Core shares a pooled client per connector singleton. But the base-client `_rate_limited_get` from §4 item 1 is not in core main `69f403b`: there are still 9 per-client copies.
   - Edge therefore has no base client to adopt yet.

## 0. Setup and lock drift

- CONFIRMED: the `uv.lock` committed at `91f6bab` records `fastmcp specifier = ">=2.0"`, but `pyproject.toml` (changed in `d4b9502`) says `>=2.0,<3.4.3`.
  - `uv sync` rewrote the lock: the metadata line plus extra caio wheels. The resolved fastmcp 3.0.2 and mcp 1.26.0 did not change.
  - The rewrite is committed separately as `4fa8de0`, before the baseline run.
  - Implication: `uv lock --check` fails on edge main today (INFERRED from the diff).

| Step | fastmcp | mcp | pydantic | httpx | starlette |
|---|---|---|---|---|---|
| baseline | 3.0.2 | 1.26.0 | 2.12.5 | 0.28.1 | 0.52.1 |
| after `uv add 'fastmcp==4.0.10'` | 4.0.10 (+ fastmcp-slim 4.0.10) | 2.2.0 (+ mcp-types 2.2.0) | 2.12.5 | 0.28.1 (+ httpx2 2.13.1) | 1.7.0 |

Other changes from `uv add`: authlib 1.6.9 → 1.8.0, idna 3.11 → 3.20, python-multipart 0.0.22 → 0.0.32. Added: griffelib 2.3.0, joserfc 1.7.5, truststore, uncalled-for, httpx2-jsfetch. Removed: httpx-sse.

## 1. Unit tests

- CONFIRMED: `C-edge-baseline.log` shows 11 passed, 5 deselected. `C-edge-4.0.10.log` shows 11 passed, 5 deselected.
- The tests cover models only (`tests/unit/test_*_models.py`), so these results carry no framework signal.

## 2. Tool surface (`C-tool_surface_edge_{baseline,4.0.10}.json`)

CONFIRMED differences, 4.0.10 compared with 3.0.2, for both tools:

| Field | 3.0.2 | 4.0.10 |
|---|---|---|
| `description` | Full docstring, including `Args:` and `Returns:` | Summary line only, e.g. "Get mechanism-of-action data from ChEMBL." |
| `inputSchema.properties.<arg>.description` | absent | Taken from `Args:`; for example `entrez_id`: "NCBI Entrez gene ID (e.g. 7298 for TYMS, 1723 for DHODH)." |
| `title` | null | "Get Mechanism" / "Get Orcs Essentiality" |
| `outputSchema`, `annotations`, `_meta` | unchanged | unchanged |

- Where it comes from (CONFIRMED in code):
  - `fastmcp/utilities/docstring_parsing.py:40-71`: griffe parses the docstring. When a parameters section is found, only the first text section is kept as the description, so the `Returns:` text is lost.
  - `fastmcp/tools/base.py:62-69`: `_default_title` is applied to every tool.
- `"x-fastmcp-wrap-result": true` is present at both versions, so structured output is `{"result": ...}` at both.

## 3. Wire capture (`C-wire_edge_{baseline,4.0.10}.json`)

- Calls went through an in-process `fastmcp.Client(mcp)` using `call_tool_mcp`, which returns the raw result.
- Simulated upstream statuses replace `httpx.AsyncClient.send`, with `BIOGRID_API_KEY` set to `FAKE-KEY-FOR-CAPTURE`.
- Any occurrence of the real key in a captured string would have been redacted. A grep confirms the real key appears nowhere in research/ or the scratchpad.
- **Diff, baseline compared with 4.0.10: 0 payload differences across all cases.** CONFIRMED.
- Neither live success call hit a 5xx, so no retry ran and no UPSTREAM_FLAKE was recorded.

| Case | Args | Result (identical at both versions) | Nulls in structured content |
|---|---|---|---|
| (a) `orcs_success_live` | `entrez_id=7298` | 352 items, `total_count: 352`, `page_size: 50`, `cursor: null`; text is 44,094 chars | 1,409 (4 always-null fields × 352, plus cursor) |
| (a) `mechanism_success_live` | `CHEMBL:225072` | 3 items (DHFR, TYMS, GART inhibitors) | 4 (`target_name` ×3, plus cursor) |
| (b) `orcs_free_text` | `entrez_id="TYMS"` | `isError: true`; text is a raw pydantic error ("Input should be a valid integer ... input_value='TYMS'"); `structuredContent: null`; **no envelope** | n/a |
| (b) `mechanism_free_text` | `"pemetrexed"` | `UNRESOLVED_ENTITY`, `isError: false`; message "The input 'Invalid ChEMBL identifier: 'pemetrexed'. Expected ...' is not a valid identifier."; `invalid_input` is the ValueError text | 0 |
| (c) `orcs_upstream_500` | simulated 500 | `UPSTREAM_ERROR`; message contains `...orcsws.thebiogrid.org/gene/7298?accesskey=FAKE-KEY-FOR-CAPTURE&format=json&hit=yes...` | 1 (`invalid_input`) |
| (c) `mechanism_upstream_500` | simulated 500 | `UPSTREAM_ERROR` with the ChEMBL URL in the message | 1 (`invalid_input`) |
| extra `mechanism_upstream_429` | simulated 429 | `RATE_LIMITED`, "Retry after a few seconds." | 1 (`invalid_input`) |
| extra `orcs_missing_api_key` | key unset | `UNRESOLVED_ENTITY`, `invalid_input: "BIOGRID_API_KEY environment variable is not set"` | 0 |
| extra `mechanism_not_found_live` | `CHEMBL:1` | `ENTITY_NOT_FOUND`; hint says "Try PubMed literature or DrugBank". The core gateway has no DrugBank tool | 0 |

Notes:

- **Key leak.** Defects 6 and 7 at the end of this section also stem from the plain-`BaseModel` models.
  - CONFIRMED: `server.py:44` passes `str(e)` from `httpx.HTTPStatusError` into `ErrorEnvelope.upstream_error`. httpx includes the request URL in that string.
  - CONFIRMED: `clients/biogrid_orcs.py:55-60` puts the key in the query string.
  - So a 401, 403, 404 or 5xx from ORCS sends the live BioGRID key to the calling agent.
  - Core avoids this: its BioGRID errors use only `e.response.status_code` (core `clients/biogrid.py:227-243`).
- **Serializer warning at 4.0.10 only.** CONFIRMED by a stderr rerun: 0 occurrences at 3.0.2 and 4 at 4.0.10, from the two success calls.
  - The warning is `PydanticSerializationUnexpectedValue(Expected PaginationEnvelope[OrcsScreenResult] ...)`.
  - Repro in `C-envelope-parity.log`: the unparametrised `.create` produces 1 warning, `PaginationEnvelope[OrcsScreenResult].create` produces 0, and both give the same output.
- **Validation failure is logged.** 4.0.10 logs `WARNING Invalid arguments for tool 'get_orcs_essentiality' {'error_types': ['int_parsing']}` (`fastmcp/server/server.py:1509`). 3.0.2 printed a full traceback.
- **slim is a no-op for ORCS.** CONFIRMED in code:
  - `server.py:51-54` sets `phenotype` and `scoring_method` to None, but `biogrid_orcs.py:76-86` always builds them as None, and plain `BaseModel` emits them either way.
  - In `get_mechanism`, slim (`server.py:93-95`) turns `direct_interaction` into an explicit null instead of removing the field.
- **Client deprecations at 4.0.10.** CONFIRMED. `Accessing CallToolResult.isError is deprecated; MCP SDK v2 renamed this field to is_error`, and likewise `structuredContent`, `Tool.inputSchema` and `Tool.outputSchema`. Any test code in core that uses the camelCase names will start warning. INFERRED.

## 4. Recovery hint compared with the core tool list

- CONFIRMED: every `UNRESOLVED_ENTITY` hint from edge is the fixed string "Use a search tool to resolve the identifier first." (`models/envelopes.py:44`). **It names no tool.**
- The tools that `docs/adr/README.md` says the hint should name all exist in core's 34 gateway tools (`tools_before.json`): `chembl_search_compounds`, `hgnc_get_gene`, `entrez_get_gene`, `hgnc_search_genes`, `entrez_search_genes`.
- For ORCS, free text never reaches the envelope at all (§3 case (b)). FastMCP's argument validation rejects it before the tool body runs.
  - This is the failure mode that core's CLAUDE.md "Tool parameter constraints (ADR-001 §3)" warns about for `pattern=`. Here the cause is the `int` type rather than a pattern.
- The fix needs code changes in edge, outside the scope of the version bump:
  - accept `entrez_id: int | str`, or validate in the body;
  - give `unresolved_entity` a tool-specific hint (e.g. "Call chembl_search_compounds ..." / "Call hgnc_get_gene or entrez_get_gene ...");
  - pass the caller's input, not `str(e)`, as `invalid_input`.

## 5. HTTP Host test (`C-host-probe.log`)

- Method: `fastmcp run src/biosciences_mcp_edge/server.py:mcp --transport http --port N --no-banner`, then POST an MCP `initialize` to `/mcp` and `/mcp/` with each Host header. The server process group is killed afterwards. CONFIRMED that every probe port was freed.
- 3.4.x ran in an isolated `uv run --no-project --with fastmcp==X` environment with `PYTHONPATH=src`, so the edge lock was not touched.
- The `fastmcp run --help` flags are the same at 3.0.2 and 4.0.10. 4.0.10 adds `--module/-m`, and its help text changes the default path from `/mcp/` to `/mcp`.

| fastmcp | Env | `/mcp`, Host localhost | `/mcp`, Host `biosciences-mcp-edge.fastmcp.app` | `/mcp/` (both hosts) |
|---|---|---|---|---|
| 3.0.2 | default | 200 | 200 | 307 / 307 |
| 3.4.3 (control) | default | 200 | **421** Misdirected Request | 307 / **421** |
| 3.4.7 | default | 200 | 200 | 307 / 307 |
| 3.4.7 | `FASTMCP_HTTP_ALLOWED_HOSTS=[...]` | 200 | 200 | 307 / 307 |
| 4.0.10 | default | 200 | 200 | 307 / 307 |
| 4.0.10 | `FASTMCP_HTTP_HOST_ORIGIN_PROTECTION=true` | 200 | **421** | 307 / **421** |
| 4.0.10 | protection=true and `ALLOWED_HOSTS=["biosciences-mcp-edge.fastmcp.app"]` | 200 | 200 | 307 / 307 |

- Code that explains the table (CONFIRMED):
  - 3.4.3 `fastmcp/settings.py:323`: `http_host_origin_protection: bool = True`.
  - 3.4.7 `settings.py:343` and 4.0.10 `settings.py:280`: `bool | Literal["auto"] = False`.
  - 3.4.7 `server/http.py:642`: the guard is installed only when protection is not False, so `ALLOWED_HOSTS` alone has no effect.
- The 3.4.3 control reproduces the 421 from `d4b9502`, which shows the probe method detects the guard.
- The 4.0.10 initialize response no longer advertises `"experimental": {}` in capabilities (CONFIRMED). It does advertise `logging`.

## 6. Parity with core

### 6.1 Envelope models: edge `models/envelopes.py` compared with core `models/envelopes.py`

| Item | Edge | Core | Diff |
|---|---|---|---|
| `ErrorCode` | `:14-20`: UNRESOLVED_ENTITY, ENTITY_NOT_FOUND, RATE_LIMITED, UPSTREAM_ERROR | `:18-26`: adds AMBIGUOUS_QUERY and INVALID_CROSS_REFERENCE | Edge is missing 2 codes (it uses neither) |
| `ErrorDetail` base | `:23` `BaseModel` | `:29` `OmitNoneModel` (`models/base.py:22-30`) | **Edge emits `invalid_input: null`; core omits it** |
| `ErrorDetail` fields | `code`, `message`, `recovery_hint`, `invalid_input: str \| None = None` (`:26-29`) | same (`:35-38`) | Same fields and defaults |
| `ErrorEnvelope` | `:32-35` `BaseModel`, `success: bool = False`, `error` | `:41-49` same | same |
| `unresolved_entity(invalid_input)` | `:38-47` generic message, generic hint | `:51-61` hard-coded "not a valid HGNC CURIE" / "Call search_genes ..." | Edge is generic. Core's factory text is HGNC-specific; core clients mostly build `ErrorDetail` directly |
| `entity_not_found` | `:49-60` `(entity_id, recovery_hint=...)` | `:63-73` `(hgnc_id)`, HGNC text, no hint parameter | Signatures differ |
| `ambiguous_query` | absent | `:75-85` | edge lacks it |
| `rate_limited(retry_after)` | `:62-73` "API rate limit exceeded." | `:87-99` "HGNC API rate limit exceeded." | Message text only. Both hints are "Retry after a few seconds."; ADR-007 §2(d) says "Retry with backoff" |
| `upstream_error(status, detail)` | `:75-86` "Upstream API returned error N." | `:101-113` "HGNC API returned error N." | Message and hint text |
| `Pagination` | `:89-94` cursor/total_count nullable, page_size=50 | `:116-121` same | identical |
| `PaginationEnvelope[T]` + `create` | `:97-118` | `:124-149` | identical |
| Item models | `models/orcs.py:6-15` and `models/mechanism.py:6-15` are plain `BaseModel` with optional fields defaulting to None | Core entity models use `OmitNoneModel` (core CLAUDE.md "Serialisation") | **Edge emits nulls for every absent field** |

Wire-shape comparison for the same codes, serialised with `pydantic_core.to_jsonable_python` (`C-envelope-parity.log`, CONFIRMED):

```
core RATE_LIMITED : {"success": false, "error": {"code": "RATE_LIMITED", "message": "HGNC API rate limit exceeded.", "recovery_hint": "Retry after a few seconds."}}
edge RATE_LIMITED : {"success": false, "error": {"code": "RATE_LIMITED", "message": "API rate limit exceeded.", "recovery_hint": "Retry after a few seconds.", "invalid_input": null}}
core UPSTREAM 500 : {... "message": "HGNC API returned error 500.", "recovery_hint": "HGNC API may be temporarily unavailable. Retry later."}}
edge UPSTREAM 500 : {... "message": "Upstream API returned error 500.", "recovery_hint": "The upstream API may be temporarily unavailable. Retry later.", "invalid_input": null}}
```

The live edge captures in §3 match this: `invalid_input: null` appears in `mechanism_upstream_429`, `*_upstream_500`.

### 6.2 Duplicated logic (file:line)

| Concern | Edge | Core | Notes |
|---|---|---|---|
| ChEMBL CURIE parsing | `clients/chembl_mechanism.py:16` `^CHEMBL:(\d+)$` with IGNORECASE; `:19-30` `parse_chembl_curie` also accepts bare `CHEMBLNNNN`; raises ValueError | `clients/chembl.py:42` `^CHEMBL:[0-9]+$`, case-sensitive; `:186-205` `_validate_chembl_curie` returns an `ErrorEnvelope` with `invalid_input=chembl_id` | **The accepted input sets differ.** Edge accepts `chembl:1` and `CHEMBL25`; core rejects both. Edge's ADR README documents the bare form as accepted |
| BioGRID auth | `clients/biogrid_orcs.py:34-35` reads `BIOGRID_API_KEY` from env on every call; `:51-53` raises ValueError when it is missing, which becomes UNRESOLVED_ENTITY; `:55-60` `accesskey` query parameter | `clients/biogrid.py:62-66` reads the env var in `__init__` and raises ValueError, which reaches the caller as a tool exception (INFERRED, not run); `:85` `accesskey` parameter | Same variable and parameter, different hosts: `orcsws.` (edge) and `webservice.` (core). Core maps 401 to UPSTREAM_ERROR with a key hint (`:228-235`) |
| Error mapping | `server.py:39-46` and `:75-82`, duplicated per tool: ValueError → UNRESOLVED_ENTITY, 429 → RATE_LIMITED, other status → UPSTREAM_ERROR(`str(e)`), HTTPError → UPSTREAM_ERROR(0) | Per client: `chembl.py:207-260` `_map_sdk_error` (string matching on "429"/"rate"); `biogrid.py:176-250` | Edge puts `str(e)` in the message, which leaks the URL and key. Core uses only the status code (BioGRID) or text (ChEMBL) |
| Rate limiting | `biogrid_orcs.py:18-31` module-global `asyncio.Lock` with a 0.5 s interval; no retry; ChEMBL has none (`chembl_mechanism.py:5`) | `biogrid.py:49,68-119` per-instance lock, 0.5 s, retries 429/503 with Retry-After; `chembl.py:60-66,93-139,141-184` 10 req/s lock plus exponential backoff (no jitter; retries 429/500/502/503); 9 per-client `_rate_limited_get` copies in core `clients/` | Neither repo follows ADR-007 §2(c) (full jitter, retried set 429/502/503/504) through one base implementation |
| httpx client management | **Per call**: `async with httpx.AsyncClient(timeout=30.0)` at `biogrid_orcs.py:64` and `chembl_mechanism.py:44`; no pooling, no lifecycle | **Shared**: `clients/base.py:41-65` lazily creates one pooled `AsyncClient` per client instance (`Limits` 10, granular `Timeout`), with `close()` at `:67-71`; servers hold module singletons (`servers/biogrid.py:22-30`, `servers/chembl.py:29-41`) | ADR-007 §2(f): "`biosciences-mcp-edge` adopts the same base or a verbatim copy of it." The base does not yet contain the (a)-(d) behaviour (`base.py` has only `_get`, `:73-76`), so adopting it today would gain pooling but not retry policy |

### 6.3 What this means for spec 015 (INFERRED)

- For edge, the FastMCP 4 bump amounts to changing one line in `pyproject` plus the lock.
- The only behaviour visible to agents is the description, schema and title change in §2.
- Lifting `<3.4.3` is safe as long as Cloud does not turn on `FASTMCP_HTTP_HOST_ORIGIN_PROTECTION`.
- Fixing the serializer warning is a two-line change (`server.py:56`, `:97`).
- The key leak, the hint and departure drift, and null omission are independent of the version. They belong in separate work items rather than in the upgrade PR, except that the key leak is serious enough to triage first.
