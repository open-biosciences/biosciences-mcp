#!/usr/bin/env python3
"""PreToolUse guard for the pr-review reviewer agents.

Reviewers are read-only by contract. Their prompts say so, but a prompt is
advisory; this hook is the enforcement. It denies any Bash command that would
change git state, the pull request, or GitHub, and lets everything else
through: reads, diffs, tests, lint, and writing the report file.

Input: the PreToolUse JSON on stdin (https://code.claude.com/docs/en/hooks).
Output: a hookSpecificOutput deny decision on stdout, or nothing to allow.
Exit code is always 0; the JSON carries the decision.

Test it with a fixture:
    echo '{"tool_name":"Bash","tool_input":{"command":"git push"}}' | .claude/hooks/pr-review-guard.py
"""

from __future__ import annotations

import json
import re
import sys

DENY: list[tuple[str, str]] = [
    (
        r"\bgit\s+(checkout|switch|commit|push|pull|reset|rebase|merge|cherry-pick|revert"
        r"|stash|add|rm|mv|restore|clean|tag|branch\s+-[dDm]|worktree\s+(add|remove|prune))\b",
        "reviewers are read-only: git state changes are not allowed",
    ),
    (
        r"\bgh\s+pr\s+(checkout|merge|review|close|reopen|edit|comment|ready)\b",
        "reviewers never act on the PR; the orchestrator posts with --comment",
    ),
    (
        r"\bgh\s+api\b.*(-X|--method)\s*(POST|PUT|PATCH|DELETE)\b",
        "reviewers never mutate GitHub state",
    ),
    (r"\bgh\s+api\b.*--input\b", "reviewers never mutate GitHub state"),
    (
        r"\bgh\s+(issue|release|repo)\s+(create|edit|delete|close)\b",
        "reviewers never mutate GitHub state",
    ),
]


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    if payload.get("tool_name") != "Bash":
        return 0
    command = (payload.get("tool_input") or {}).get("command") or ""
    for pattern, reason in DENY:
        if re.search(pattern, command):
            print(
                json.dumps(
                    {
                        "hookSpecificOutput": {
                            "hookEventName": "PreToolUse",
                            "permissionDecision": "deny",
                            "permissionDecisionReason": f"pr-review-guard: {reason}",
                        }
                    }
                )
            )
            return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
