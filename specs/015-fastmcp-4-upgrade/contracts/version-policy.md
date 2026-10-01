# Contract: Connector Framework Version Policy (ADR-009 content)

**Requirements**: FR-015, FR-016, FR-017, FR-018 | **Data model**: [../data-model.md](../data-model.md#version-policy)

This is the content ADR-009 must carry and the behaviour each repository's policy test must enforce. The ADR itself is written during implementation at `docs/adr/proposed/adr-009-v0.1.md`, and moves to `accepted/` once core and edge both run inside the range.

## ADR-009 required sections

1. **Scope**: platform ADR under the placement rule in `biosciences-program/docs/adr/README.md`. Binds `biosciences-mcp`, `biosciences-mcp-edge`, `psychology-mcp`, and future connector repositories by default.
2. **Supported range**: `fastmcp>=4.0.10,<4.1`, with the reason for each bound.
   - *Floor*: 4.0.10 is the version verified in spec 015.
   - *Ceiling*: upstream issue #5213 proposes turning the Host guard back on by default, and 4.1 is unverified.
3. **Known-bad versions**, each with the incident and evidence:

   | Versions | Failure | Evidence |
   |---|---|---|
   | `==3.4.3` | Host guard on by default; HTTP 421 for the Horizon hostname | edge `d4b9502`; upstream PR #4405; default changed in 3.4.4 (PRs #4439, #4472) |

   **Usage rule, not a version exclusion**: never pass `namespace=` (or 2.x/3.x `prefix=`) to `mount()` together with `tool_names` values that already carry the prefix. Every 3.x and 4.x version double-prefixes the names (`hgnc_hgnc_search_genes`); 2.x hid the mistake. Evidence: AGE-182; core `8b112cf`, `e5e19a0`, and PR #18; mount probe 2026-09-30 on 2.14.5, 3.0.2, 3.4.7, 4.0.10. The tool-surface contract test catches it; version bounds cannot.
4. **Change procedure**:
   - A range change is an ADR-009 amendment.
   - The same change window updates each consumer's policy-test values and dependency bounds.
   - Each consumer gets a notice issue.
   - A floor raise requires the tool-surface contract test and a preview deployment in each consumer.
5. **Divergence**: consumers may run different versions inside the range. After a range change, a consumer may stay outside it for at most one release cycle, tracked by its notice issue.
6. **Host-guard deployment rule**: deploy with framework defaults and no host variables set. Any consumer that turns the guard on must verify, on a preview deployment, that Horizon's proxy preserves the public `Host`, because the guard does not read `X-Forwarded-Host`.

## Policy test contract (each consumer)

- **Location**: `tests/unit/test_framework_version_policy.py`, marker `unit`, no network.
- **Inputs**: the repository's own `pyproject.toml` and `uv.lock`; policy values as constants in the test, with a comment citing ADR-009 and its version.
- **Checks**:
  1. The `fastmcp` specifier in `[project.dependencies]` is within `SUPPORTED`, and excludes every `KNOWN_BAD` entry. Checked by testing boundary versions against both specifiers.
  2. The resolved `fastmcp` in `uv.lock` satisfies `SUPPORTED` and matches no `KNOWN_BAD`.
  3. An upper bound on `fastmcp` has a reason comment on the same or the preceding line.
- **Failure message**: names ADR-009 and the failing check, for example `fastmcp 3.4.3 in uv.lock is known-bad under ADR-009 (Host guard 421 on Horizon)`.
- **Self-check (SC-007)**: a test that edits a temporary copy of `pyproject.toml` or `uv.lock` to a known-bad version fails all three checks as expected.
- **CI**: `.github/workflows/ci.yml` runs `uv sync --extra dev` and `uv run pytest -m unit` on pull requests and pushes to `main`.
