# FastMCP 3.4.7 Preview Deployment Verification (Core)

- **Repository**: `biosciences-mcp`
- **Branch**: `implement/015-fastmcp-4-upgrade-core`
- **Head Commit**: `f1c80d1`
- **Preview Endpoint**: `https://biosciences-mcp-implement-015-fastmcp-4-upgrade-core.fastmcp.app/mcp`
- **Framework Versions**: `fastmcp` 3.4.7, `mcp` 1.26.0
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

## 2. Check 4.7 & Deployment Rollback (T025): NOT RUN

- The timed rollback (redeploy the preview from the pre-upgrade `main` commit, and time it until check 4.2 passes on 2.14.5) has **not been performed**. SC-005's under-15-minute target is unmeasured.
- Planned recovery path: revert the PR #20 merge commit and redeploy from Horizon.

---

## 3. Decision (T026): PENDING OWNER

- **Recommendation**: Go. Checks 4.1–4.5 and 4.8 pass, and the production-vs-preview comparison shows identical payloads.
- **Open before the decision**: check 4.7 (T025), or an explicit waiver of it by the owner.
- **Decider / date**: to be recorded by the repository owner. A validating agent recorded "Go" on 2026-10-01; that was withdrawn because FR-011 requires the decider's own recorded decision.
- **Verification note (2026-10-01)**: the check 4.3 arguments were validated against `contracts/tool-surface-baseline-core.json` (12/12 declared parameters), and the preview head equals the branch head (`f1c80d1`).
