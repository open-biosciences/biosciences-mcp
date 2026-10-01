# Contract: Tool-Surface Invariants

**Applies to**: core gateway (34 tools) and edge (2 tools) | **Requirements**: FR-001, FR-002, FR-006, FR-007

The tool surface is the interface these repositories expose to agent callers. This contract states what the FastMCP 4 upgrade may and may not change in it, and how the tool-surface test checks it. The baselines are the JSON files next to this document.

## Invariants (MUST hold; a test failure blocks merge)

1. **Names.** The set of tool names equals the baseline's key set exactly.
2. **Parameters.** For each tool, the parameter names, `type`, `required`, and `default` equal the baseline's `params`.
3. **Guidance preserved.** Take each baseline `description` and drop section-header lines (`Args:`, `Returns:`, `Examples:`, `Error Codes:`, `Raises:`, `Note:`). Also drop blank lines and the per-parameter lines of `Args:`; those are checked separately against parameter descriptions. Every remaining line must appear, after whitespace normalisation, in either the tool's current `description` or one of its parameter `description`s.

   *Why line-level*: FastMCP 3.2.4+ keeps only the first text section of a docstring as the description (research R6). The test proves nothing a caller could read on 2.14.5 has disappeared, without fixing where in the docstring it lives.
4. **Per-parameter guidance.** Each baseline `Args:` entry's text appears in that parameter's `description` on 3.4.7 (FastMCP 3.2.4+ moves `Args:` text there).
5. **Undeclared arguments stay rejected** (FR-003). A call with one undeclared argument returns `isError: true`. The message text may differ between versions; it is recorded for FR-007, not asserted. The test uses a call that is rejected before any network access.

## Allowed changes (MUST be listed in the upgrade PR under "User-visible contract")

| Change | Observed | Caller effect |
|---|---|---|
| `additionalProperties: false` added to every input schema | core 34/34; edge already had it on 3.0.2 | None. Undeclared arguments were already rejected (R5). |
| Parameter `description`s added from `Args:` | core 11 → 104 | More guidance per parameter |
| Output schema `$defs`/`$ref` inlined | core 27/34 | None; same shape |
| `title` annotation added | edge 2/2 | Display only |
| Description text reorganised (leading section now carries return and error guidance) | core 30/34, edge 2/2 | Same information, different position (invariant 3) |
| Gateway validation messages use FastMCP text (`Missing required argument(s): …`) | core, through the gateway only | No downstream parser (research D) |

Any change not in this table is a contract change and needs its own decision.

## Test shape

- Core: `tests/contract/test_tool_surface.py`, marked `contract` and `unit` (no network). It loads the gateway in process with `fastmcp.Client`, calls `list_tools`, and compares against `contracts/tool-surface-baseline-core.json`. The baseline path is read relative to the repository root, so the test works from any worktree.
- Edge: `tests/unit/test_tool_surface.py`, marked `unit`. It does the same against a copy of `tool-surface-baseline-edge.json` placed in edge's `tests/fixtures/`, because edge cannot read core's files (FR-013).
- The test reads schema fields version-tolerantly: `inputSchema`/`outputSchema` on 2.x and 3.x (mcp 1.x types), and `input_schema`/`output_schema` on a later 4.x (mcp 2.x, which deprecates the camelCase names). The same test then serves the 4.x follow-up unchanged.
