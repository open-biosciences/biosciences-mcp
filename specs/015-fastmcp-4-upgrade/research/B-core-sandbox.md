# B — biosciences-mcp (core) FastMCP upgrade sandbox

Run: 2026-09-30 21:07–21:23 PDT. Scratch worktree `.worktrees/scratch-015-core`, detached at `a319044` (PR #18 head: gateway mounts use `tool_names` only, with no `prefix` or `as_proxy`). Local-only commits: `c82f81f` (fastmcp==3.4.7) and `2239aaf` (fastmcp==4.0.10). Nothing was pushed. Python 3.13, pydantic 2.12.5.

Labels: **CONFIRMED** means observed in this run. **INFERRED** means reasoned from the code or the evidence but not directly tested.

## Decision-relevant summary

1. **4.0.10 breaks two test-side imports. No product code fails.** CONFIRMED.
   - `tests/contract/test_serialization_unit.py:27` imports `fastmcp.tools.tool.default_serializer`. That module no longer exists in 4.x; the function is now `fastmcp.tools.base.default_serializer`. The ImportError happens at collection time and aborts **every** tier that collects `tests/contract/`: unit, contract+unit and contract+integration all exit 2.
   - `tests/integration/test_gateway.py:9` calls `mcp.get_tools()`, which was removed in **3.x** and is also gone in 4.0.10. The replacement is `list_tools()`.
   - After a one-line import shim (diagnostic only, no repo edit), 4.0.10 passes **562/562 unit** and **104/104 contract+unit**. Contract+integration shows the same 11-test failure set as baseline, all upstream. No new behavioural failure appears.
2. **The tool surface shifts at 3.x, and 3.4.7 and 4.0.10 are byte-identical.** CONFIRMED. All 34 names are unchanged. Docstring parsing now moves `Args:` text into per-parameter `inputSchema` descriptions (11 parameters had descriptions before, 104/104 have them now) and **drops everything after the first docstring section from the tool description**. That covers `Returns:` and also `Examples:`, `Error Codes:`, `Note:` and the `Success response structure:` blocks. The dropped text appears nowhere in the surface for 30/34 tools. The exception is the 4 IUPHAR tools, which have no `Args:` section and keep their full description.
3. **Argument handling is unchanged in kind.** Every probe case returns a `CallToolResult` with `is_error=true` in all three versions, and the high-level `Client.call_tool` raises `ToolError`. The **message text changes at 3.x for missing and undeclared arguments, through the gateway only.** CONFIRMED.
4. **The Host header is not enforced.** POST `/mcp` returns 200 for `Host: localhost:<p>`, `Host: biosciences-mcp.fastmcp.app` and `Host: 127.0.0.1:<p>` on all three versions. CONFIRMED (local `fastmcp run --transport http`).
5. **Null omission holds on the wire on all versions.** CONFIRMED. 4.0.10 adds **new Pydantic serializer UserWarnings** on union-typed returns (`PaginationEnvelope[...] | ErrorEnvelope`). These are noise, not failures, and are not seen at 2.14.5 or 3.4.7.
6. **mcp SDK:** 2.14.5 and 3.4.7 both resolve `mcp==1.26.0`. 4.0.10 pulls **`mcp==2.2.0`** plus `mcp-types==2.2.0`, `httpx2` and `httpcore2`. 3.4.7 introduces `fastmcp-slim` and `starlette 1.7.0` (up from 0.52.1). CONFIRMED.

## Versions × test tiers

| Step | fastmcp / mcp | unit | contract+unit | test_gateway.py | contract+integration (network) |
|---|---|---|---|---|---|
| baseline | 2.14.5 / 1.26.0 | 562 passed | 104 passed | 1 passed | 51 passed, 11 failed, 5 skipped, 2 xfailed; rerun: 9 still fail (all upstream) |
| bump 1 | 3.4.7 / 1.26.0 | 562 passed | 104 passed | **1 failed (NEW)** | 51 passed, 11 failed (same set); rerun: 10 still fail (all upstream) |
| bump 2 | 4.0.10 / 2.2.0 | **collection error, exit 2 (NEW)** | **collection error, exit 2 (NEW)** | **1 failed (NEW, same as 3.4.7)** | **collection error, exit 2 (NEW)**. Diagnostic with the module ignored: 51 passed, 11 failed (same set); rerun: 11 still fail (all upstream) |
| 4.0.10 diagnostic (shim, not a tier result) | | 562 passed, 3 warnings | 104 passed, 3 warnings | | |

The 11 baseline network failures are the same set at every step, so none is a regression:
- **Ensembl** (`ensembl.search_genes`, `ensembl.get_gene` ×2): `UPSTREAM_ERROR: Ensembl API returned error 500`. Classed as **UPSTREAM_FLAKE**; some of these passed on rerun at 2.14.5 and 3.4.7.
- **IUPHAR** (8 tests across `search_ligands`, `search_targets`, `get_ligand`, `get_target`): `API error: 401` on every call, at every version. This is a persistent upstream 401, which is outside the 5xx/403 flake definition, but it is identical at baseline, so it counts as a **BASELINE_FAILURE**, not a regression. Side note (pre-existing, not upgrade-related): the IUPHAR client raises `ValueError` on a 401, so the tool returns a bare `Error calling tool ...` text instead of an ADR-001 `ErrorEnvelope`.
- **Coverage gap** (INFERRED): because of these upstream failures, the null-omission and xref contract checks for IUPHAR and Ensembl entities were **not exercised** at any version.

Logs: `B-core-<step>.log`, `B-core-<step>-contract-integration.log`, `B-core-4.0.10-diagnostic.log`.

## NEW failures versus baseline (with traces)

### N1. `test_gateway_tools_exposed`: `FastMCP.get_tools` removed (3.4.7 and 4.0.10)
```
tests/integration/test_gateway.py:9
>       tools = await mcp.get_tools()
E       AttributeError: 'FastMCP' object has no attribute 'get_tools'. Did you mean: 'get_tool'?
```
On 3.4.7 the tool-related public methods are `add_tool, add_tool_transformation, call_tool, get_app_tool, get_tool, get_tool_by_hash, list_tools, remove_tool, remove_tool_transformation, tool` (CONFIRMED). The fix is test-only: use `await mcp.list_tools()`, which returns a list of tools. INFERRED: `list_tools()` returns Tool objects with `.name`, which the test's list branch already handles.

### N2. Contract module ImportError (4.0.10): aborts unit, contract+unit and contract+integration
```
ERROR collecting tests/contract/test_serialization_unit.py
tests/contract/test_serialization_unit.py:27: in <module>
    from fastmcp.tools.tool import default_serializer
E   ModuleNotFoundError: No module named 'fastmcp.tools.tool'
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
371 deselected, 1 error in 1.76s   (exit 2)
```
In 4.0.10, `fastmcp/tools/` contains `base.py, function_parsing.py, function_tool.py, tool_transform.py`, and `default_serializer` lives at `fastmcp/tools/base.py:72` as `_JSONABLE_ADAPTER.dump_json(data, fallback=str).decode()` (CONFIRMED). With `sys.modules["fastmcp.tools.tool"] = fastmcp.tools.base` injected through a scratchpad pytest plugin, all 104 contract-unit tests pass (CONFIRMED). The fix is test-only: change the import, ideally to `from fastmcp.tools.base import default_serializer`, guarded by version if 2.x support must remain.

### New warnings at 4.0.10 (not failures)
- Contract-unit: `PydanticSerializationUnexpectedValue(Expected 'datetime' ... field_name='timestamp', input_value='x')` from `models/base.py:27` for the `provenance.*` fixtures. CONFIRMED that it appears only at 4.0.10. INFERRED cause: 4.x `default_serializer` goes through a `TypeAdapter` with serializer warnings on, and the test fixture's `'x'` timestamp triggers it.
- Contract+integration: 20 warnings on `hgnc.search_genes`, `entrez.search_genes`, `biogrid.search_genes`, `string.search_proteins` and `opentargets.get_target`, for example `Expected 'PaginationEnvelope[SearchCandidate]'` / `Expected 'ErrorEnvelope'` with `input_type=PaginationEnvelope`. These are raised from `pydantic/type_adapter.py:605` and `models/base.py:27`. INFERRED cause: 4.x builds `structured_content` with `get_cached_typeadapter(<return annotation>).dump_python(...)` (`tools/base.py:88`), while clients return an unparametrised `PaginationEnvelope(...)` against a `PaginationEnvelope[X] | ErrorEnvelope` annotation. Output is still correct, since the tests pass.
- Behavioural noise (CONFIRMED at 3.4.7): argument errors through the gateway log a full rich traceback at ERROR (`tool_transform.py:745 in _forward  TypeError: Missing required argument(s): hgnc_id`). At 2.14.5 the same errors were plain validation results.

## Tool-surface diff (`B-tool_surface_core_<step>.json`)

| Field | 2.14.5 → 3.4.7 | 2.14.5 → 4.0.10 | 3.4.7 → 4.0.10 |
|---|---|---|---|
| names | identical (34/34) | identical (34/34) | identical |
| description | 30 differ | 30 differ | 0 |
| inputSchema | 34 differ | 34 differ | 0 |
| outputSchema | 27 differ | 27 differ | 0 |
| annotations | 0 (all `None`) | 0 | 0 |

All CONFIRMED.

- **description**: the text from the first docstring section onward is removed. The 4 unchanged descriptions are the IUPHAR tools, which use `Annotated[..., Field(description=...)]` parameters and have no `Args:` section. Example, `hgnc_get_gene`: before, the description ended with `...Args:\n    hgnc_id: HGNC CURIE ...\n\nReturns:\n    Gene record with cross_references, or ErrorEnvelope on failure.`; after, it is only `Get complete gene record by HGNC CURIE.\n\nReturns full Agentic Biolink entity with cross-references.\nRequires resolved CURIE from search_genes.`
- **inputSchema**: every difference is accounted for by (a) `"additionalProperties": false` now on all 34 tools and (b) per-parameter `description` taken from `Args:`. After removing those two, 34/34 schemas are equal. Example, `biogrid_search_genes.slim`: `"description": "Token budgeting (Constitution Principle IV). No behavior change\nsince search candidates are already minimal (~30 tokens)."`. Minor quality point: 34 parameter descriptions keep the docstring's continuation-line indentation, for example in `clinicaltrials_search_trials.condition`: `"...\"lung cancer\").\n       Optional - narrows results..."`.
- **outputSchema**: every difference is `$defs` / `$ref` inlining. 27/27 are equal after dereferencing with sibling keys merged. The `x-fastmcp-wrap-result: true` wrapper is unchanged. Pre-existing, unchanged: entity models built on `OmitNoneModel` render as an empty schema `{}` (for example, `Gene` inside the `result` `anyOf`), in 7 tools. INFERRED: this is a side effect of the wrap-mode `model_serializer`.

## `Returns:` and `Args:` at 4.0.10

- **Returns:** 34/34 tools have a `Returns:` section at 2.14.5. At 4.0.10 that text is in the **tool description for 4 tools (IUPHAR only)** and **nowhere for 30 tools**: not in the description, not in `inputSchema`, and not in `outputSchema` (whose descriptions come from the Pydantic model docstrings, for example the `ErrorEnvelope` class docstring). CONFIRMED by substring search of each tool's first `Returns:` line across all three fields.
- **Args:** 0 parameters lost. Every `Args:` entry in the 30 docstrings that have one maps to an `inputSchema.properties[<name>].description` with matching text (CONFIRMED). This is a net gain for agents, since parameter descriptions went from 11 to 104.
- **Also lost (CONFIRMED):** other sections after the first one are removed for the same 30 tools: `Examples:` (14), `Error Codes:` (4), `Example:` (6), `Note:` (1), `Error responses:` (2) and `Success response structure:` (2). The `Examples:` doctest snippets (for example `>>> search_genes("TP53")`) are absent from the whole 4.0.10 surface. Agent-facing guidance on error codes and response shapes is therefore no longer advertised. For the `clinicaltrials_*` tools, the full JSON success-response example lived under `Returns:` and is gone.
- INFERRED rule: when a docstring has a parseable `Args:` section, 3.x and later keep only the summary before the first section. IUPHAR tools have no `Args:` section and keep their full docstring.

## Argument handling (in-process `fastmcp.Client`, gateway tools)

The raw path uses `call_tool_mcp`. The high-level path uses `call_tool`, which raised `fastmcp.exceptions.ToolError` with the same text in every `is_error=true` case at every version.

| Case | 2.14.5 | 3.4.7 | 4.0.10 |
|---|---|---|---|
| `hgnc_get_gene {}` (missing required) | is_error, `1 validation error for call[get_gene]\nhgnc_id\n  Missing required argument [type=missing_argument, ...]` | is_error, **`Error calling tool 'hgnc_get_gene': Missing required argument(s): hgnc_id`** | same as 3.4.7 |
| `hgnc_search_genes {}` | is_error, `...call[search_genes]\nquery\n  Missing required argument...` | is_error, **`Error calling tool 'hgnc_search_genes': Missing required argument(s): query`** | same as 3.4.7 |
| `hgnc_get_gene {"hgnc_id": 1100}` (int for str) | is_error, `1 validation error for call[get_gene]\nhgnc_id\n  Input should be a valid string [type=string_type, input_value=1100, input_type=int]` | identical | identical |
| `hgnc_search_genes page_size="abc"` | is_error, `...page_size\n  Input should be a valid integer, unable to parse string as an integer [type=int_parsing...]` | identical | identical |
| `hgnc_search_genes page_size="5"` (coercible) | success (lax coercion) | success | success |
| `hgnc_get_gene {"hgnc_id":"BRCA1","bogus":1}` (undeclared extra) | is_error, `...call[get_gene]\nbogus\n  Unexpected keyword argument [type=unexpected_keyword_argument...]` | is_error, **`Error calling tool 'hgnc_get_gene': Got unexpected keyword argument(s): bogus`** | same as 3.4.7 |
| `hgnc_get_gene {"hgnc_id":"BRCA1"}` (free-text CURIE) | **not** is_error; body is `ErrorEnvelope` `{"success":false,"error":{"code":"UNRESOLVED_ENTITY","message":"The input 'BRCA1' is not a valid HGNC CURIE.","recovery_hint":"Call search_genes to resolve the identifier first.","invalid_input":"BRCA1"}}` | identical | identical |

All CONFIRMED. The change for missing and extra arguments comes from the gateway's `tool_names` mount, which in 3.x and later is a tool transform that checks arguments in `tool_transform.py:_forward` before Pydantic validation runs. Calling the un-mounted `hgnc` server directly at 4.0.10 still returns the Pydantic text `1 validation error for call[get_gene] ... Missing required argument` (CONFIRMED). Wrong-type errors still leak the inner tool name `call[get_gene]` rather than `hgnc_get_gene` (CONFIRMED, at all versions). Extra arguments were already rejected at 2.14.5. 3.x and later now advertise this in the schema with `additionalProperties:false`. Raw results: `B-args-<step>.json`.

## Host header (local `fastmcp run src/biosciences_mcp/servers/gateway.py --transport http --port <p>`, MCP `initialize` POST)

| Request | 2.14.5 | 3.4.7 | 4.0.10 |
|---|---|---|---|
| POST `/mcp`, `Host: localhost:<p>` | 200 | 200 | 200 |
| POST `/mcp`, `Host: biosciences-mcp.fastmcp.app` | 200 | 200 | 200 |
| POST `/mcp`, `Host: 127.0.0.1:<p>` | 200 | 200 | 200 |
| POST `/mcp/` (any of the three hosts) | 307 | 307 | 307 |

All CONFIRMED. No DNS-rebinding or Host allow-list rejection occurred at any version, including 4.0.10 with mcp 2.2.0, and every 200 body was a valid `initialize` result with `protocolVersion 2025-06-18`. The default path in `--help` changed from `/mcp/` (2.14.5, 3.4.7) to `/mcp` (4.0.10), but the bare `/mcp` POST works on all three. Servers were killed and the ports confirmed free. Files: `B-host-<step>.txt`, `B-host-<step>-server.log`. INFERRED: this tests only local `fastmcp run` binding to 127.0.0.1. FastMCP Cloud/Horizon fronting is not covered.

## Null-omission observations

- `hgnc_get_gene HGNC:1100`, `hgnc_search_genes`, and the `ErrorEnvelope` path: 0 occurrences of `null` in the text block or in `structuredContent` at all three versions. `structuredContent` is wrapped as `{"result": ...}` at all three. CONFIRMED.
- Contract-integration no-null and envelope tests pass for every server that answered (HGNC, UniProt, ChEMBL, Open Targets, STRING, BioGRID, Entrez, PubChem, WikiPathways and others; 51 passed) at all three versions. IUPHAR and Ensembl were not evaluated because of upstream 401 and 500 responses. CONFIRMED.
- The serialisation contract (104 tests, including text- and structured-path null omission for every `OmitNoneModel`) passes at 4.0.10 once the import is shimmed. The `OmitNoneModel` wrap serializer still reaches 4.x's new `TypeAdapter`-based `structured_content` path (CONFIRMED), with the serializer warnings noted above.
- `default: null` for optional parameters in `inputSchema` is pre-existing and unchanged. It is schema, not data. CONFIRMED.
