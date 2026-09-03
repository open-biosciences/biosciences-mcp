## Purpose

<!-- One or two sentences. What does this change do and why now? -->

## Linked work

- Issue: AGE-
- Spec / plan / tasks (if non-trivial): `specs/...` or "not applicable because ..."

## Scope

<!-- One coherent change per PR. If this bundles more than one, list them and say why they travel together. -->

## Applicable decisions

<!-- Tick what this PR touches and name the clauses you relied on. Delete rows that do not apply. -->

- [ ] ADR-001 §3 Fuzzy-to-Fact (search / strict tools)
- [ ] ADR-001 §4 / §7 / §8 wire shape (models, envelopes, cross-references)
- [ ] ADR-001 Appendix A registry (`tests/contract/registry.py` updated in the same commit)
- [ ] ADR-004 lifecycle
- [ ] ADR-007 retry and rate behaviour
- [ ] New or amended ADR proposed in `docs/adr/`

Intentional divergences from the above, with the waiver or rationale:

## User-visible contract

<!-- Tool names, parameters, `id` formats, envelope fields. State "unchanged" or list every change and its compatibility for biosciences-deepagents, biosciences-temporal, and biosciences-research. -->

## Evidence

<!-- Paste the summary line of each command you ran. -->

- `uv run pytest -m unit -q`:
- `uv run pytest -m "contract and unit" -q`:
- `uv run pytest -m "contract and integration and <server>" -q` (if wire behaviour changed):
- `uv run ruff check . && uv run pyright` (error counts, base vs head):

## Rollout and recovery

<!-- Anything a consumer must do, and how to revert if this is wrong in production. "None" is a valid answer. -->

## Documentation

- [ ] `CLAUDE.md`, `tests/README.md`, and ADR README statements this PR affects are updated, or none are affected
