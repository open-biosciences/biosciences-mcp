# Local pre-release test results: core on FastMCP 3.4.7 (2026-10-02)

Requested by the repository owner before production deployment (T027): local unit and integration tiers, reported by layer. Run at PR #20 head `8b9195f`; its runtime code is identical to the preview-validated `f1c80d1` (the later commits touch `specs/` only).

## Verdict

- **Unit tier: green.** 706 passed, 0 failed, on both the locked set and Horizon's resolved set.
- **Integration tier: one new failure group caused by the upgrade, test-harness only.** `tests/integration/test_competency_questions_mcp.py` has **16 new failures** on 3.4.7. The other 65 failures are upstream outages or flakes, or pre-existing failures that also fail on 2.14.5. Details in the triage below.
- **Wire contract: unchanged.** Every contract failure is IUPHAR 401 (AGE-734) or an Ensembl timeout, and the same tests fail on 2.14.5. The T018 wire diff (`../core-3.4.7/wire-diff.md`) found 39 of 39 calls identical in `isError` and `structuredContent`.
- **Horizon's resolved set behaves like the locked set.** Running 706 unit tests and the MCP-layer integration subset on the exact versions from the `02ca1d0` build log (`mcp` 1.30.0, `pydantic` 2.13.5, `uvicorn` 0.54.0) gave the same pass and failure sets as the locked run. `PydanticSerializationUnexpectedValue` appeared 0 times in every log.

## Follow-up 2026-10-04: the 16 new failures are fixed

`tests/integration/test_competency_questions_mcp.py` now calls each tool through `fastmcp.Client` against the in-process gateway (commit `8f4ce55`), the same path an MCP client uses, instead of `get_tool(...).fn(...)`.

| Run (locked set, live APIs) | Result | Files |
|---|---|---|
| Full file, 04:29 UTC | 10 passed, 10 failed, 3 skipped. The 10 non-ChEMBL tests pass. 7 ChEMBL tests failed during an EBI ChEMBL outage; CQ-6, CQ-7 and CQ-23 fail as on 2.14.5 | `cq-mcp-ported.txt`, `cq-mcp-ported.junit.xml` |
| 7 ChEMBL tests, once EBI returned 200 | 4 passed; CQ-3, CQ-17 and CQ-19 got `UPSTREAM_ERROR` from ChEMBL | `cq-mcp-ported-chembl.txt`, `cq-mcp-ported-chembl.junit.xml` |
| FR-012 re-run of those 3 after 10 s (04:54 UTC) | 3 passed | `cq-mcp-ported-chembl-rerun.junit.xml` |

Net result: every test in the file passes except CQ-6 (IUPHAR 401, AGE-734), CQ-7 and CQ-23 (pathway-count assertions), which fail identically on 2.14.5 (`baseline-2.14.5.txt`). The AGE-718 "no new integration failures" criterion is met for this file.

**EBI outage, 2026-10-04 ~04:08 to ~04:50 UTC.** `chembl_webresource_client` downloads `https://www.ebi.ac.uk/chembl/api/data/spore` at import, with no timeout. While EBI returned 500 or hung, `import biosciences_mcp` failed, and both core production and the PR #20 preview were down (Horizon runtime log 04:10:51: `Error getting schema from url .../spore with status 500`). Edge and psychology-mcp stayed up. Tracked as AGE-703. After recovery, production reported FastMCP **2.14.7** (re-resolved on restart), not the 2.14.5 in `uv.lock`.

## Layers

- **MCP layer** (through FastMCP: in-process `fastmcp.Client` or the gateway): `tests/contract/*`, `tests/unit/test_iuphar_server.py`, `tests/integration/test_gateway.py`, `tests/integration/test_competency_questions_mcp.py`.
- **API layer** (HTTP clients and Pydantic models, no FastMCP): every other test. Unit tests mock HTTP; integration tests call the live upstream APIs.

## Runs

| Run | Environment | Command | Result | Files |
|---|---|---|---|---|
| Unit, locked | Python 3.13.2, `uv.lock` (fastmcp 3.4.7, mcp 1.26.0) | `uv run pytest -m unit` | 706 passed (API 462, MCP 244) | `unit.txt`, `unit.junit.xml` |
| Unit, Horizon set | Python 3.12.9, pins from `horizon-02ca1d0-resolved.txt` | same | 706 passed | `horizon-unit.txt`, `horizon-unit.junit.xml` |
| Integration, locked | as unit, live APIs, keys from `.env` | `uv run pytest -m integration` | 238 passed, 81 failed, 41 skipped, 3 xfailed (16 min) | `integration.txt`, `integration.junit.xml` |
| Re-run after 10 s (FR-012) | locked | the upstream-looking failures (non-IUPHAR, non-CQ-MCP) | 28 passed, 8 failed, 5 skipped | `integration-rerun.*` |
| Baseline, 2.14.5 | `main` `0430e52`, Python 3.13.2, fastmcp 2.14.5 | the same non-IUPHAR failing tests | 54 passed, 12 failed, 11 skipped | `baseline-2.14.5.*` |
| Ensembl A/B | `main` vs upgrade, interleaved, 2 rounds | `TestSearchGenes`, `TestFuzzyToFactWorkflow` | main 3 and 3 failed; upgrade 4 and 1 failed | `ensembl-ab.txt` |
| MCP-layer integration, Horizon set | Horizon pins | `-m integration tests/contract tests/integration/test_gateway.py tests/integration/test_competency_questions_mcp.py` | 53 passed, 29 failed, 8 skipped, 2 xfailed; same failure set as locked | `horizon-mcp-integration.*` |

Versions and timestamps: `versions.txt`. Logs are `.txt` because `*.log` is gitignored. All files were scanned for the three API key values before commit (0 hits).

## Triage of the 81 integration failures (locked full run)

| Group | Count | Layer | Cause | New with 3.4.7? |
|---|---|---|---|---|
| IUPHAR/GtoPdb `401` | 50 | API 41, MCP 9 | GtoPdb now requires an API key (AGE-734): 40 `test_iuphar_api.py`, 8 contract, CQ-6 in both CQ files | No. The 8 contract cases fail identically on 2.14.5 (`../core-2.14.5/contract-integration.failed.txt`, `baseline-2.14.5.txt`); the 40 client cases call the HTTP client directly, with no FastMCP involved |
| **`get_tool(...).fn(...)` returns `ToolResult`** | **16** | **MCP** | `test_competency_questions_mcp.py` calls `mcp.get_tool(name).fn(...)` on the gateway. On 3.4.7, mounted tools are `TransformedTool` objects, and `.fn` returns a `ToolResult` instead of the server's model, so the test's `to_dict(...)["items"]` raises `KeyError`/`TypeError`. CQ-1 to 5, 9, 10, 12 to 15, 17 to 20, 22. | **Yes** |
| Pre-existing CQ failures | 5 | API 2, MCP 3 | CQ-7, CQ-11, CQ-23 (MCP); CQ-11, CQ-23 (client). CQ-23 expects more than 100 BRCA1 pathways and gets 20; CQ-11 is Ensembl | No, fail on 2.14.5 |
| Ensembl timeouts | 6 | API 5, MCP 1 | `UPSTREAM_ERROR: Request to Ensembl API timed out` in `TestSearchGenes`, `TestFuzzyToFactWorkflow`, and contract `ensembl.search_genes`. Clients and models are unchanged from `main`; the A/B shows failures on both versions | No, upstream |
| `test_get_protein_performance` | 1 | API | Cold-start `get_protein` took 3.08 s against a 2 s budget | No, fails on 2.14.5 |
| Passed on re-run | 3 | API | `test_search_genes_empty_results` (NCBI timeout), `test_concurrent_search_performance` (5.09 s vs 5 s), `test_get_compound_sc002` (ChEMBL 12.8 s outlier) | No, flakes |

### The 16 new failures

- **Mechanism, measured on both versions:**

  | | 2.14.5 | 3.4.7 |
  |---|---|---|
  | `type(await gateway.mcp.get_tool("hgnc_search_genes"))` | `FunctionTool` | `TransformedTool` |
  | `.fn(query="TP53")` returns | `PaginationEnvelope` | `ToolResult` |
  | `Client(gateway.mcp).call_tool(...)` `structuredContent` keys | `["result"]` | `["result"]` |

- **Callers are not affected.** The wire path is identical, and no downstream repository (`biosciences-deepagents`, `-temporal`, `-research`, `-mcp-edge`, `-evaluation`) and nothing in `src/` calls `get_tool(...).fn(...)`. This test file is the only user.
- **Why earlier evidence missed it.** Quickstart §2 and T016–T018 ran the unit tier, contract unit, `test_gateway.py`, and contract integration. They did not run the full integration tier, so this file never ran on 3.4.7 until now.
- **Fix (not applied):** port the file from `mcp.get_tool(name).fn(**args)` to `fastmcp.Client(mcp).call_tool(name, args)`, as `tests/contract/conftest.py` `wire_call` does. That tests what a caller receives rather than a framework-internal attribute. Test-only; no runtime change.
- **Acceptance impact:** AGE-718 requires "no new failures" in `integration and not contract`. These 16 count as new until the file is ported.

### Integration tier, locked set (full run)

| Layer | File | passed | failed | error | skipped | xfail |
|---|---|---|---|---|---|---|
| API | `tests/integration/test_biogrid_api.py` | 13 | 0 | 0 | 0 | 0 |
| API | `tests/integration/test_biogrid_performance.py` | 2 | 0 | 0 | 0 | 0 |
| API | `tests/integration/test_chembl_api.py` | 20 | 0 | 0 | 0 | 1 |
| API | `tests/integration/test_clinicaltrials_api.py` | 0 | 0 | 0 | 15 | 0 |
| API | `tests/integration/test_competency_questions_client.py` | 17 | 3 | 0 | 3 | 0 |
| API | `tests/integration/test_concurrency.py` | 3 | 0 | 0 | 0 | 0 |
| API | `tests/integration/test_drugbank_api.py` | 0 | 0 | 0 | 7 | 0 |
| API | `tests/integration/test_ensembl_api.py` | 15 | 5 | 0 | 4 | 0 |
| API | `tests/integration/test_entrez_api.py` | 19 | 1 | 0 | 0 | 0 |
| API | `tests/integration/test_entrez_performance.py` | 4 | 0 | 0 | 0 | 0 |
| API | `tests/integration/test_error_recovery.py` | 6 | 0 | 0 | 4 | 0 |
| API | `tests/integration/test_hgnc_api.py` | 7 | 0 | 0 | 0 | 0 |
| API | `tests/integration/test_iuphar_api.py` | 6 | 40 | 0 | 0 | 0 |
| API | `tests/integration/test_opentargets_api.py` | 9 | 0 | 0 | 0 | 0 |
| API | `tests/integration/test_performance.py` | 4 | 3 | 0 | 0 | 0 |
| API | `tests/integration/test_pubchem_api.py` | 19 | 0 | 0 | 0 | 0 |
| API | `tests/integration/test_string_api.py` | 11 | 0 | 0 | 0 | 0 |
| API | `tests/integration/test_string_performance.py` | 1 | 0 | 0 | 0 | 0 |
| API | `tests/integration/test_uniprot_api.py` | 12 | 0 | 0 | 0 | 0 |
| API | `tests/integration/test_wikipathways_api.py` | 17 | 0 | 0 | 0 | 0 |
| MCP | `tests/contract/test_wire_contracts.py` | 53 | 9 | 0 | 5 | 2 |
| MCP | `tests/integration/test_competency_questions_mcp.py` | 0 | 20 | 0 | 3 | 0 |
| **API total** | | **185** | **52** | **0** | **33** | **1** |
| **MCP total** | | **53** | **29** | **0** | **8** | **2** |

Per-test failure IDs: see the triage above and the JUnit XML files in this folder.
