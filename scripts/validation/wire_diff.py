"""Diff two snapshot directories produced by wire_probe.py.

usage: python scripts/validation/wire_diff.py <before_dir> <after_dir>
"""

import json
import sys
from collections.abc import Iterator
from pathlib import Path


def xrefs(obj: object) -> Iterator[tuple[object, dict]]:
    if isinstance(obj, dict):
        if "cross_references" in obj:
            yield obj.get("id"), obj["cross_references"]
        for value in obj.values():
            yield from xrefs(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from xrefs(value)


def main() -> None:
    a_dir, b_dir = Path(sys.argv[1]), Path(sys.argv[2])
    for path in sorted(a_dir.glob("*.json")):
        other = b_dir / path.name
        if not other.exists():
            print(f"{path.name}: missing in {b_dir}")
            continue
        a = json.loads(path.read_text())
        b = json.loads(other.read_text())
        if a == b:
            print(f"{path.name}: identical")
            continue
        xa, xb = dict(xrefs(a)), dict(xrefs(b))
        lines = []
        for eid in sorted(set(xa) | set(xb), key=str):
            ra, rb = xa.get(eid) or {}, xb.get(eid) or {}
            for k in sorted(set(ra) | set(rb)):
                if ra.get(k) != rb.get(k):
                    lines.append(
                        f"    {eid!s:28} {k:20} {json.dumps(ra.get(k))[:50]} -> {json.dumps(rb.get(k))[:50]}"
                    )
        top = sorted(set(a) ^ set(b)) if isinstance(a, dict) and isinstance(b, dict) else []
        suffix = f"; top-level keys {top}" if top else ""
        print(f"{path.name}: differs ({len(lines)} cross_reference changes{suffix})")
        for line in lines[:12]:
            print(line)


if __name__ == "__main__":
    main()
