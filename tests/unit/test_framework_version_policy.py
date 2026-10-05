"""Framework version policy (ADR-009 v0.1, docs/adr/proposed/adr-009-v0.1.md).

Fails when this repository's FastMCP dependency range or lock falls outside the
platform policy, or when an upper bound has no recorded reason (spec 015 FR-017,
FR-018). The policy values are a local copy of ADR-009; change them only with a new
ADR-009 version. No network.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest
from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.version import Version

pytestmark = pytest.mark.unit

ADR = "ADR-009 v0.1 (docs/adr/proposed/adr-009-v0.1.md)"
SUPPORTED = SpecifierSet(">=3.4.7,<3.5")
KNOWN_BAD = {"3.4.3": "Host guard on by default; HTTP 421 for the Horizon hostname (edge d4b9502)"}
# Versions a compliant specifier must not admit: known-bad, below the floor, and above
# the ceiling (4.x is not yet supported; ADR-009 section 2.2).
PROBES = ("2.14.5", "3.0.2", "3.4.3", "3.4.6", "3.5.0", "4.0.0", "4.0.10")

ROOT = Path(__file__).resolve().parents[2]


def fastmcp_requirement(pyproject_text: str) -> tuple[Requirement, int]:
    """The fastmcp requirement from [project].dependencies and its line index."""
    deps = tomllib.loads(pyproject_text)["project"]["dependencies"]
    req = next(Requirement(d) for d in deps if Requirement(d).name == "fastmcp")
    lines = pyproject_text.splitlines()
    index = next(i for i, line in enumerate(lines) if re.match(r'\s*"fastmcp[<>=!~ ]', line))
    return req, index


def check_specifier(pyproject_text: str) -> list[str]:
    req, _ = fastmcp_requirement(pyproject_text)
    errors = []
    if not req.specifier.contains("3.4.7"):
        errors.append(
            f"pyproject fastmcp {req.specifier} excludes the supported floor 3.4.7 ({ADR})"
        )
    for probe in PROBES:
        if req.specifier.contains(probe):
            reason = KNOWN_BAD.get(probe, f"outside the supported range {SUPPORTED}")
            errors.append(f"pyproject fastmcp {req.specifier} admits {probe}: {reason} ({ADR})")
    return errors


def check_lock(lock_text: str) -> list[str]:
    packages = tomllib.loads(lock_text).get("package", [])
    locked = next((p["version"] for p in packages if p["name"] == "fastmcp"), None)
    if locked is None:
        return [f"uv.lock has no fastmcp package ({ADR})"]
    errors = []
    if locked in KNOWN_BAD:
        errors.append(f"fastmcp {locked} in uv.lock is known-bad: {KNOWN_BAD[locked]} ({ADR})")
    if Version(locked) not in SUPPORTED:
        errors.append(
            f"fastmcp {locked} in uv.lock is outside the supported range {SUPPORTED} ({ADR})"
        )
    return errors


def check_reason_comment(pyproject_text: str) -> list[str]:
    req, index = fastmcp_requirement(pyproject_text)
    if not any(spec.operator in ("<", "<=") for spec in req.specifier):
        return []
    lines = pyproject_text.splitlines()
    has_comment = "#" in lines[index] or (index > 0 and lines[index - 1].strip().startswith("#"))
    if has_comment:
        return []
    return [
        f"fastmcp upper bound in pyproject has no reason comment on the same or preceding line ({ADR})"
    ]


def test_pyproject_specifier_within_policy():
    assert check_specifier((ROOT / "pyproject.toml").read_text()) == []


def test_locked_version_within_policy():
    assert check_lock((ROOT / "uv.lock").read_text()) == []


def test_upper_bound_has_reason_comment():
    assert check_reason_comment((ROOT / "pyproject.toml").read_text()) == []


# Self-check (SC-007): each check must fail on a known-bad copy.

PYPROJECT_BAD_RANGE = """[project]
name = "x"
dependencies = [
    # reason: test fixture
    "fastmcp>=3.4.3,<5",
]
"""

PYPROJECT_NO_REASON = """[project]
name = "x"
dependencies = [
    "fastmcp>=3.4.7,<3.5",
]
"""

LOCK_KNOWN_BAD = """version = 1
[[package]]
name = "fastmcp"
version = "3.4.3"
"""


def test_self_check_specifier_rejects_known_bad_and_4x():
    errors = check_specifier(PYPROJECT_BAD_RANGE)
    assert any("3.4.3" in e and "ADR-009" in e for e in errors)
    assert any("4.0.0" in e for e in errors)


def test_self_check_lock_rejects_known_bad():
    errors = check_lock(LOCK_KNOWN_BAD)
    assert any("known-bad" in e and "ADR-009" in e for e in errors)


def test_self_check_reason_comment_required():
    errors = check_reason_comment(PYPROJECT_NO_REASON)
    assert errors and "ADR-009" in errors[0]
