# Quickstart §3 policy self-check (spec 015 T040), 2026-10-01T08:41Z

Scratch edit: pyproject fastmcp pinned to ==3.4.3 and uv.lock fastmcp version set to 3.4.3; restored afterwards.

```
E       AssertionError: assert ['pyproject f...09-v0.1.md))'] == []
E         
E         Left contains 2 more items, first extra item: 'pyproject fastmcp ==3.4.3 excludes the supported floor 3.4.7 (ADR-009 v0.1 (docs/adr/proposed/adr-009-v0.1.md))'
E         Use -v to get more diff
E       AssertionError: assert ['fastmcp 3.4...09-v0.1.md))'] == []
E         
E         Left contains 2 more items, first extra item: 'fastmcp 3.4.3 in uv.lock is known-bad: Host guard on by default; HTTP 421 for the Horizon hostname (edge d4b9502) (ADR-009 v0.1 (docs/adr/proposed/adr-009-v0.1.md)
E         Use -v to get more diff
FAILED tests/unit/test_framework_version_policy.py::test_pyproject_specifier_within_policy
FAILED tests/unit/test_framework_version_policy.py::test_locked_version_within_policy
2 failed, 4 passed in 0.06s
```
