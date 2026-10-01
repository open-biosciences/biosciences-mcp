# Core wire capture through the gateway: 2.14.5 vs 3.4.7 (spec 015 T018)

Captured 2026-10-01 in one session with `specs/015-fastmcp-4-upgrade/research/core-capture/core_capture.py`. The cases come from `tests/contract/conftest.py` `SERVERS`. All outbound HTTP was intercepted (httpx and requests), and backoff sleeps were stubbed. Raw captures: `core_wire_2.14.5.json`, `core_wire_3.4.7.json`.

- 2.14.5 run: fastmcp 2.14.5 in a throwaway environment, which resolved `mcp` 1.30.0 (the locked version is 1.26.0). Source is the upgrade branch, including the restructured docstrings.
- 3.4.7 run: the worktree environment, fastmcp 3.4.7 with `mcp` 1.26.0.
- 39 cases:
  - 15 strict tools with their raw-string input
  - 3 argument-validation cases
  - 11 tools under a simulated upstream 500, and the same 11 under a simulated 429
  - ChEMBL recorded as not simulated (it uses an SDK, not httpx)
- `drugbank_get_drug` is not on the gateway, so it was skipped.

## Result

| Comparison | Cases | Allowed-changes row |
|---|---|---|
| Identical in `isError`, content and `structuredContent` | 39 of 39 for `isError` and `structuredContent` | — |
| Differ only in result `_meta` (`{"fastmcp": {"wrap_result": true}}` on 3.4.7) | 27 | "Call results carry `_meta`…" |
| Validation message text (undeclared, missing, wrong-type argument through the gateway) | 3 | "Gateway validation messages use FastMCP text" |
| Unhandled upstream exception text (`pubchem_get_compound` under 429) | 1 | "Unhandled upstream exceptions get FastMCP's error text", added 2026-10-01 with this capture |
| Identical, including a timeout on both | `upstream_429:iuphar_get_ligand` times out (>60 s) on both versions | Pre-existing IUPHAR retry deadlock (AGE-704) |

No difference falls outside the allowed-changes table. The PubChem row was added for this result.

- **PubChem 429 on 2.14.5:** the unmapped `httpx.HTTPStatusError` reaches the caller as text containing the request URL ("Client error '429 Too Many Requests' for url …").
- **PubChem 429 on 3.4.7:** FastMCP replaces it with "Rate limited by upstream API, please retry later".
- **Both versions:** `isError` is true.
- **Root cause:** PubChem does not map 429 to the `RATE_LIMITED` envelope, a pre-existing gap tracked in AGE-698. The 3.4.7 text is the better of the two, because it no longer echoes a URL.
