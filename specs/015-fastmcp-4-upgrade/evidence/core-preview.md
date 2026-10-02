# FastMCP 3.4.7 Preview Deployment Verification (Core)

- **Repository**: `biosciences-mcp`
- **Branch**: `implement/015-fastmcp-4-upgrade-core`
- **Head Commit**: `f1c80d1`
- **Preview Endpoint**: `https://biosciences-mcp-implement-015-fastmcp-4-upgrade-core.fastmcp.app/mcp`
- **Framework Versions**: `fastmcp` 3.4.7. `uv.lock` pins `mcp` 1.26.0, but Horizon ignores the lockfile and resolves from `pyproject.toml` (research R3/R10): the `02ca1d0` build log shows `mcp` 1.30.0, `pydantic` 2.13.5, `uvicorn` 0.54.0 on Python 3.12.13 (see §2)
- **Date Tested**: 2026-10-01
- **Feature Specification**: [spec.md](../spec.md) | **Tasks**: [tasks.md](../tasks.md) (T021–T026)

---

## 1. Quickstart §4 Verification Results

### Check 4.1: Host Header Accepted
- **Test**: Authenticated MCP connection and handshake to `https://biosciences-mcp-implement-015-fastmcp-4-upgrade-core.fastmcp.app/mcp`.
- **Result**: **PASS** (HTTP 200). Requests accepted without HTTP 421 (Host Origin rejection).

### Check 4.2: Tool Count and Names
- **Test**: `fastmcp.Client.list_tools()` over HTTP SSE transport.
- **Expected**: Exactly 34 single-prefixed tool names matching `contracts/tool-surface-baseline-core.json`.
- **Observed Tool Count**: 34
- **Tool List**:
  - `biogrid_get_interactions`, `biogrid_search_genes`
  - `chembl_get_compound`, `chembl_get_compounds_batch`, `chembl_search_compounds`
  - `clinicaltrials_get_trial`, `clinicaltrials_get_trial_locations`, `clinicaltrials_search_trials`
  - `ensembl_get_gene`, `ensembl_get_transcript`, `ensembl_search_genes`
  - `entrez_get_gene`, `entrez_get_pubmed_links`, `entrez_search_genes`
  - `hgnc_get_gene`, `hgnc_search_genes`
  - `iuphar_get_ligand`, `iuphar_get_target`, `iuphar_search_ligands`, `iuphar_search_targets`
  - `opentargets_get_associations`, `opentargets_get_target`, `opentargets_search_targets`
  - `pubchem_get_compound`, `pubchem_search_compounds`
  - `string_get_interactions`, `string_get_network_image_url`, `string_search_proteins`
  - `uniprot_get_protein`, `uniprot_search_proteins`
  - `wikipathways_get_pathway`, `wikipathways_get_pathway_components`, `wikipathways_get_pathways_for_gene`, `wikipathways_search_pathways`
- **Result**: **PASS** (100% match with baseline keys, zero double prefixing).

### Check 4.3: One Call Per Server (12 Mounted Servers)
- **Test**: Representative query calls executed against the live preview endpoint:
  1. `hgnc_search_genes` (`query="TP53"`): **OK** (`is_error=False`)
  2. `uniprot_search_proteins` (`query="TP53"`): **OK** (`is_error=False`)
  3. `chembl_search_compounds` (`query="aspirin"`): **OK** (`is_error=False`)
  4. `opentargets_search_targets` (`query="BRCA1"`): **OK** (`is_error=False`)
  5. `string_search_proteins` (`query="TP53"`): **OK** (`is_error=False`)
  6. `biogrid_search_genes` (`query="TP53"`): **OK** (`is_error=False`)
  7. `ensembl_search_genes` (`query="BRCA1"`): **OK** (`is_error=False`)
  8. `entrez_search_genes` (`query="TP53"`): **OK** (`is_error=False`)
  9. `pubchem_search_compounds` (`query="caffeine"`): **OK** (`is_error=False`)
  10. `iuphar_search_ligands` (`query="morphine"`): Expected upstream 401 error (GtoPdb API key requirement tracked in AGE-734; exempted under FR-012)
  11. `wikipathways_search_pathways` (`query="Apoptosis"`): **OK** (`is_error=False`)
  12. `clinicaltrials_search_trials` (`query="cancer"`): **OK** (`is_error=False`)
- **Result**: **PASS** (11/12 successful, 1 documented upstream auth failure).

### Check 4.4: Strict-Tool Failure Mode
- **Test**: `hgnc_get_gene` called with free text (`hgnc_id="TP53"`) rather than resolved CURIE.
- **Observed Response**:
  ```json
  {
    "success": false,
    "error": {
      "code": "UNRESOLVED_ENTITY",
      "message": "The input 'TP53' is not a valid HGNC CURIE.",
      "recovery_hint": "Call search_genes to resolve the identifier first.",
      "invalid_input": "TP53"
    }
  }
  ```
- **Result**: **PASS** (Matches ADR-001 §3 wire contract with `UNRESOLVED_ENTITY` envelope and recovery guidance).

### Check 4.5: Sessionless Raw JSON-RPC `tools/call` (biosciences-deepagents)
- **Test**: Raw HTTP POST with JSON-RPC `tools/call` payload, `Authorization: Bearer <key>`, and no initialization or session headers (as sent by `biosciences-deepagents/apps/api/shared/mcp.py`). Tested under both HTTP/1.1 and HTTP/2.
- **Observed Response**:
  - HTTP Status: `200 OK`
  - Content-Type: `text/event-stream`
  - Payload: Valid JSON-RPC result containing `content` and `structuredContent`.
- **Result**: **PASS** (Zero "400 Missing session ID" errors; sessionless downstream consumers fully compatible).

### Check 4.8: Temporal Client Integration (`biosciences-temporal`)
- **Test**: `create_mcp_client()` stdio client executed with `BIOSCIENCES_MCP_PATH` set to the upgrade worktree.
- **Observed**:
  - FastMCP 3.4.7 gateway process starts under stdio transport.
  - Lists exactly 34 tools.
  - `hgnc_search_genes` and `hgnc_get_gene` return structured dicts matching contract specifications.
- **Result**: **PASS** (Local temporal workflows execute seamlessly against 3.4.7 gateway).

### 1.6 Live Side-by-Side Comparison: Production (2.14.5) vs Preview (3.4.7)
A simultaneous dual-endpoint invocation was performed comparing production (`https://biosciences-mcp.fastmcp.app/mcp`) against preview (`https://biosciences-mcp-implement-015-fastmcp-4-upgrade-core.fastmcp.app/mcp`):
- **Tool Listing**:
  - Production tools: 34
  - Preview tools: 34
  - Tool names match exactly: **True** (0 difference)
- **Wire Payloads**:
  - `hgnc_search_genes` (`query="TP53"`): **Payload JSON identical: True**
  - `chembl_search_compounds` (`query="aspirin"`): **Payload JSON identical: True**
  - `hgnc_get_gene` (`hgnc_id="TP53"` strict lookup error): **Payload JSON identical: True**
- **Sessionless JSON-RPC HTTP Status**:
  - Production: `HTTP 200`
  - Preview: `HTTP 200`

---

## 2. Check 4.7 & Deployment Rollback (T025): WAIVED BY OWNER

- **Waiver**: approved by the repository owner (donbr) on 2026-10-02. The timed rollback drill was not run. Horizon redeploys automatically on every push to the deployed branch, so the drill would mainly re-measure Horizon's build time, which the push below already measured.
- **Proxy measurement (SC-005)**: an unplanned push of `02ca1d0` (evidence commit, docs only) to the PR branch triggered an automatic preview rebuild. Horizon build log:

  | Event | Time (UTC) |
  |---|---|
  | `02ca1d0` committed and pushed | 2026-10-02 05:38:55 (push in the same command) |
  | First build log line (`Installing mcp-build-tools...`) | 05:39:37 |
  | `=== FINAL STATUS: BUILD SUCCEEDED ===`, image published | 05:40:06 |

  Build: 29 s. Push to published image: about 70 s. The log does not show the rollout to the live endpoint or the commit SHA; the commit is attributed by timing (`8b9195f` was pushed later, at 05:41:23, and triggers its own build).
- **Unmeasured**: rollout from published image to live endpoint, and the human steps (open and merge the revert PR, possibly from a phone).
- **Rollback path**: `git revert -m 1 <PR #20 merge commit>` on `main`, merged by merge commit, then the production redeploy. Whether production (`biosciences-mcp`) redeploys automatically on a push to `main` is **unconfirmed**; if it does not, redeploy from the Horizon console.
- **Caveat: a rollback re-resolves, it does not restore.** Horizon runs `uv pip install --system ./.` against the `pyproject.toml` ranges and ignores `uv.lock`. Reverting PR #20 resolves `fastmcp>=2.14.1,<3.0` and its transitive dependencies fresh, so the rolled-back image may not match today's production image byte for byte.
- **Resolved set observed in the `02ca1d0` build** (vs `uv.lock`): `fastmcp` 3.4.7 (3.4.7), `mcp` 1.30.0 (1.26.0), `pydantic` 2.13.5 (2.12.5), `uvicorn` 0.54.0 (0.41.0), `starlette` 1.7.0 (1.7.0), `httpx` 0.28.1 (0.28.1), Python 3.12.13 (local runs: 3.13.2). All within the spec's allowed ranges (quickstart §1: `mcp` 1.x).
- **Head moved after validation**: the preview now runs `8b9195f`. `git diff f1c80d1 8b9195f` touches only `specs/015-fastmcp-4-upgrade/` (this file, `tasks.md`, `HANDOFF.md`); no runtime file changed. On 2026-10-02 the redeployed preview listed 34 tools, identical to `contracts/tool-surface-baseline-core.json`.

---

## 3. Decision (T026): PENDING OWNER

- **Recommendation**: Go. Checks 4.1–4.5 and 4.8 pass, and the production-vs-preview comparison shows identical payloads.
- **Open before the decision**: check 4.7 (T025) was waived by the owner on 2026-10-02 (§2). The local pre-release run (`core-3.4.7-prerelease/README.md`) found **16 new failures in `tests/integration/test_competency_questions_mcp.py`**. They are test-harness only: the file calls `get_tool(...).fn(...)`, which returns a `ToolResult` on 3.4.7, while the wire path is unchanged. AGE-718's "no new integration failures" criterion is unmet until the file is ported to `fastmcp.Client`, or the owner accepts the failures explicitly.
- **Decider / date**: to be recorded by the repository owner. A validating agent recorded "Go" on 2026-10-01; that was withdrawn because FR-011 requires the decider's own recorded decision.
- **Verification note (2026-10-01)**: the check 4.3 arguments were validated against `contracts/tool-surface-baseline-core.json` (12/12 declared parameters), and the preview head equals the branch head (`f1c80d1`).
