"""Diff two cq_replay.py outputs: entity ids, envelope shape, and cross_references.

usage: python scripts/validation/cq_diff.py <before.json> <after.json>
"""

import json
import sys
from collections.abc import Iterator
from pathlib import Path


def walk_entities(obj: object, path: str = "$") -> Iterator[tuple[str, dict]]:
    """Yield (key, dict) for every dict carrying an 'id' or 'cross_references'.

    The key is the entity id when present (so reordering between runs does not
    hide a change) and the JSON path otherwise.
    """
    if isinstance(obj, dict):
        if "id" in obj or "cross_references" in obj:
            yield (f"id:{obj['id']}" if "id" in obj else path), obj
        for key, value in obj.items():
            yield from walk_entities(value, f"{path}.{key}")
    elif isinstance(obj, list):
        for i, value in enumerate(obj):
            yield from walk_entities(value, f"{path}[{i}]")


def shape(result: dict) -> tuple:
    """Classify a wire payload and summarise the fields that must not drift.

    Error envelope: ("error", code). Pagination envelope (ADR-001 §8):
    ("list", item count, pagination.total_count, pagination.page_size,
    has-next-cursor). Anything else is a single entity: ("entity", id).
    """
    if result.get("success") is False:
        return ("error", (result.get("error") or {}).get("code"))
    if "items" in result:
        page = result.get("pagination") or {}
        return (
            "list",
            len(result.get("items", [])),
            page.get("total_count"),
            page.get("page_size"),
            page.get("cursor") is not None,
        )
    return ("entity", result.get("id"))


def main() -> None:
    before = json.loads(Path(sys.argv[1]).read_text())
    after = json.loads(Path(sys.argv[2]).read_text())
    if len(before) != len(after):
        raise SystemExit(f"call count differs: {len(before)} vs {len(after)}")

    changed_xref, changed_ids, changed_shape, errors = [], [], [], []
    for b, a in zip(before, after, strict=True):
        key = f"{b['cq_id']} {b['tool']}({b.get('args')})"
        rb, ra = b.get("result"), a.get("result")
        if rb is None or ra is None:
            errors.append(
                (
                    key,
                    b.get("error") or b.get("raw", "")[:80],
                    a.get("error") or a.get("raw", "")[:80],
                )
            )
            continue
        ents_b = dict(walk_entities(rb))
        ents_a = dict(walk_entities(ra))
        ids_b = sorted(e["id"] for e in ents_b.values() if "id" in e)
        ids_a = sorted(e["id"] for e in ents_a.values() if "id" in e)
        if ids_b != ids_a:
            changed_ids.append((key, len(ids_b), len(ids_a), sorted(set(ids_b) ^ set(ids_a))[:5]))
        if shape(rb) != shape(ra):
            changed_shape.append((key, shape(rb), shape(ra)))
        for path in ents_b.keys() & ents_a.keys():
            xb = ents_b[path].get("cross_references") or {}
            xa = ents_a[path].get("cross_references") or {}
            for k in sorted(set(xb) | set(xa)):
                if xb.get(k) != xa.get(k):
                    changed_xref.append((key, ents_b[path].get("id"), k, xb.get(k), xa.get(k)))

    print(f"calls compared: {len(before)}; errors/unavailable: {len(errors)}")
    print(f"\nENTITY ID CHANGES ({len(changed_ids)}):")
    for row in changed_ids:
        print("  ", row)
    print(f"\nENVELOPE SHAPE CHANGES ({len(changed_shape)}):")
    for row in changed_shape:
        print("  ", row)
    print(f"\nCROSS_REFERENCE VALUE CHANGES ({len(changed_xref)}):")
    for key, eid, k, vb, va in changed_xref:
        print(f"  {key[:60]:60} {eid!s:22} {k:20} {json.dumps(vb)[:60]} -> {json.dumps(va)[:60]}")
    print(f"\nERRORS/UNAVAILABLE ({len(errors)}):")
    for row in errors:
        print("  ", row)


if __name__ == "__main__":
    main()
