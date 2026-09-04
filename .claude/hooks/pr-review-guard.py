#!/usr/bin/env python3
"""PreToolUse guard for the pr-review team.

Two roles, selected by --role:

  reviewer      (default) the three read-only reviewer agents. Denies any
                Bash command that would change git state, the pull request,
                or GitHub; allows reads, diffs, tests, lint, GET requests, and
                writing files under the session scratchpad.
  orchestrator  the /pr-review skill. Skill hooks persist for the rest of
                the session, so this role leaves git alone and denies only
                the GitHub actions the team must never take: gh pr review,
                merge, close, ready; gh api with PUT/PATCH/DELETE, the merge
                endpoint, or a review whose event is not COMMENT.

What this guard is: defence in depth behind the agents' prompts and their
tool allow-lists. It matches commands at command position after stripping
heredoc bodies, line continuations, leading VAR=value assignments, wrapper
commands, and git global options.

What it is not: a sandbox. Interpreter indirection (python -c that shells
out, string-assembled command names) is out of scope by design; the prompts
and the reviewers' tool lists remain part of the contract.

Input: the PreToolUse JSON on stdin (https://code.claude.com/docs/en/hooks).
Output: a hookSpecificOutput deny decision on stdout, or nothing to allow.
Exit code is always 0 for hook input; the JSON carries the decision.
Malformed input is allowed but reported on stderr so it is visible.

Self-test (exits 1 on any mismatch):
    .claude/hooks/pr-review-guard.py --self-test
"""

from __future__ import annotations

import json
import re
import shlex
import sys
from collections.abc import Iterable

# ---------------------------------------------------------------------------
# Command normalisation
# ---------------------------------------------------------------------------

_HEREDOC = re.compile(r"<<-?\s*(['\"]?)(\w+)\1")
_SEPARATORS = re.compile(r"\|\||&&|\|&|;|\||&|\n")
_ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=\S*$")
_WRAPPERS = {"command", "env", "exec", "nohup", "time", "nice", "timeout", "sudo", "builtin"}
_NESTERS = {"sh", "bash", "zsh", "dash", "ksh", "xargs", "eval", "find"}
_GIT_GLOBAL_WITH_ARG = {
    "-C",
    "-c",
    "--git-dir",
    "--work-tree",
    "--namespace",
    "--exec-path",
    "--super-prefix",
}


def _strip_heredocs(text: str) -> str:
    """Remove heredoc bodies so quoted report text is never matched."""
    lines = text.split("\n")
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        m = _HEREDOC.search(line)
        out.append(line)
        i += 1
        if m:
            tag = m.group(2)
            while i < len(lines) and lines[i].strip() != tag:
                i += 1
            i += 1  # skip the terminator
    return "\n".join(out)


def _segments(command: str) -> Iterable[list[str]]:
    """Yield each simple command as a token list, at command position."""
    text = command.replace("\\\n", " ")
    text = _strip_heredocs(text)
    for raw in _SEPARATORS.split(text):
        raw = raw.strip()
        if not raw:
            continue
        # Drop parentheses and braces used for grouping.
        raw = raw.strip("(){} ")
        try:
            tokens = shlex.split(raw, posix=True)
        except ValueError:
            tokens = raw.split()
        if tokens:
            yield tokens


def _unwrap(tokens: list[str]) -> list[str]:
    """Strip leading assignments and wrapper commands (env, command, ...)."""
    while tokens:
        head = tokens[0]
        if _ASSIGNMENT.match(head):
            tokens = tokens[1:]
            continue
        if head in _WRAPPERS:
            tokens = tokens[1:]
            # skip wrapper options such as `timeout 30` or `env -i`
            while tokens and (
                tokens[0].startswith("-") or (head == "timeout" and tokens[0][:1].isdigit())
            ):
                tokens = tokens[1:]
            continue
        break
    return tokens


def _basename(token: str) -> str:
    return token.rsplit("/", 1)[-1].lstrip("\\")


# ---------------------------------------------------------------------------
# Policy
# ---------------------------------------------------------------------------

GIT_READ_ONLY = {
    "diff",
    "show",
    "log",
    "status",
    "ls-files",
    "ls-tree",
    "rev-parse",
    "rev-list",
    "merge-base",
    "cat-file",
    "blame",
    "grep",
    "describe",
    "name-rev",
    "shortlog",
    "diff-tree",
    "diff-index",
    "count-objects",
    "var",
    "help",
    "version",
    "--version",
    "check-ignore",
    "check-attr",
    "archive",
    "for-each-ref",
    "show-ref",
    "reflog",
    "whatchanged",
    "cherry",
    "range-diff",
    "verify-commit",
    "ls-remote",
}
GIT_READ_ONLY_WITH_FLAGS = {
    # verb: flags that keep it read-only; any positional argument denies
    "branch": {
        "-a",
        "-r",
        "-l",
        "--list",
        "--show-current",
        "--contains",
        "--merged",
        "--no-merged",
        "-v",
        "-vv",
        "--all",
    },
    "tag": {"-l", "--list", "-n"},
    "remote": {"-v", "show", "get-url"},
    "config": {"--get", "--get-all", "--get-regexp", "--list", "-l"},
    "stash": {"list", "show"},
    "worktree": {"list"},
    "notes": {"list", "show"},
}
# verbs from the table above whose bare form (no arguments) mutates
GIT_BARE_MUTATING = {"stash"}

GH_ORCHESTRATOR_DENY = {
    ("pr", "review"),
    ("pr", "merge"),
    ("pr", "close"),
    ("pr", "ready"),
    ("repo", "delete"),
    ("release", "delete"),
}

GH_READ_ONLY = {
    ("pr", "view"),
    ("pr", "diff"),
    ("pr", "checks"),
    ("pr", "list"),
    ("pr", "status"),
    ("issue", "view"),
    ("issue", "list"),
    ("run", "view"),
    ("run", "list"),
    ("release", "view"),
    ("release", "list"),
    ("repo", "view"),
    ("auth", "status"),
    ("search", "*"),
    ("label", "list"),
    ("workflow", "list"),
    ("workflow", "view"),
}
GH_API_MUTATING_FLAGS = {"-f", "-F", "--field", "--raw-field", "--input", "--method", "-X"}
CURL_MUTATING_FLAGS = {
    "-X",
    "--request",
    "-d",
    "--data",
    "--data-raw",
    "--data-binary",
    "--data-urlencode",
    "-F",
    "--form",
    "-T",
    "--upload-file",
    "--json",
}


def _deny(reason: str) -> str:
    return reason


def _check_git(args: list[str]) -> str | None:
    # strip global options
    i = 0
    while i < len(args) and args[i].startswith("-"):
        opt = args[i]
        name = opt.split("=", 1)[0]
        if name in _GIT_GLOBAL_WITH_ARG and "=" not in opt:
            i += 2
        else:
            i += 1
    rest = args[i:]
    if not rest:
        return None
    verb = rest[0]
    if verb in GIT_READ_ONLY:
        return None
    if verb in GIT_READ_ONLY_WITH_FLAGS:
        allowed = GIT_READ_ONLY_WITH_FLAGS[verb]
        extras = rest[1:]
        if not extras and verb in GIT_BARE_MUTATING:
            return _deny(f"bare git {verb} changes repository state")
        if all(
            a in allowed or (a.startswith("-") and a.split("=", 1)[0] in allowed) for a in extras
        ):
            # positional refs are fine for --contains/--merged style queries only when a flag precedes them
            return None
        if (
            extras
            and extras[0] in allowed
            and all(not a.startswith("-") for a in extras[1:])
            and extras[0]
            in {
                "--contains",
                "--merged",
                "--no-merged",
                "show",
                "get-url",
                "--get",
                "--get-all",
                "--get-regexp",
                "list",
            }
        ):
            return None
        return _deny(f"git {verb} with arguments {extras!r} is not read-only")
    return _deny(f"git {verb} changes repository state; reviewers are read-only")


def _check_gh(args: list[str], role: str) -> str | None:
    if not args:
        return None
    if args[0] in {"--version", "version", "help"}:
        return None
    if args[0] == "api":
        rest = args[1:]
        method = None
        for j, a in enumerate(rest):
            if a in {"-X", "--method"} and j + 1 < len(rest):
                method = rest[j + 1].upper()
            elif a.startswith("--method=") or a.startswith("-X"):
                method = a.split("=", 1)[-1].upper() if "=" in a else a[2:].upper()
        endpoint = next((a for a in rest if not a.startswith("-")), "")
        if "graphql" in endpoint:
            return _deny("gh api graphql is always a POST")
        has_mutating_flag = any(
            a in GH_API_MUTATING_FLAGS or a.split("=", 1)[0] in GH_API_MUTATING_FLAGS for a in rest
        )
        if method in (None, "GET") and not has_mutating_flag:
            return None
        if (
            method in (None, "GET")
            and has_mutating_flag
            and not any(
                a in {"-f", "-F", "--field", "--raw-field", "--input"}
                or a.split("=", 1)[0] in {"-f", "-F", "--field", "--raw-field", "--input"}
                for a in rest
            )
        ):
            return None  # explicit GET with no body
        if role == "orchestrator":
            if method in {"PUT", "PATCH", "DELETE"} or endpoint.rstrip("/").endswith("/merge"):
                return _deny("orchestrator never merges or edits PR state")
            if re.search(r"/pulls/\d+/reviews$", endpoint):
                body = _review_body(rest)
                if body is None:
                    return _deny(
                        "orchestrator may post an inline review only from an --input file it can read"
                    )
                if body.get("event") != "COMMENT":
                    return _deny("orchestrator may post reviews with event COMMENT only")
            return None
        return _deny("gh api mutation is not allowed")
    verb = tuple(args[:2])
    if role == "orchestrator":
        if verb in GH_ORCHESTRATOR_DENY:
            return _deny(f"orchestrator never runs gh {' '.join(args[:2])}")
        return None
    if verb in GH_READ_ONLY or (verb[0], "*") in GH_READ_ONLY:
        return None
    return _deny(f"gh {' '.join(args[:2])} is not a read-only command")


def _review_body(rest: list[str]) -> dict | None:
    path = None
    for j, a in enumerate(rest):
        if a == "--input" and j + 1 < len(rest):
            path = rest[j + 1]
        elif a.startswith("--input="):
            path = a.split("=", 1)[1]
    if not path or path == "-":
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _check_curl(args: list[str]) -> str | None:
    for a in args:
        name = a.split("=", 1)[0]
        if name in CURL_MUTATING_FLAGS:
            if name in {"-X", "--request"}:
                idx = args.index(a)
                val = (
                    a.split("=", 1)[1]
                    if "=" in a
                    else (args[idx + 1] if idx + 1 < len(args) else "")
                ).upper()
                if val in {"GET", "HEAD"}:
                    continue
            return _deny("curl/wget with a mutating flag is not allowed")
    return None


def check_command(command: str, role: str = "reviewer") -> str | None:
    """Return a deny reason, or None to allow."""
    for tokens in _segments(command):
        tokens = _unwrap(tokens)
        if not tokens:
            continue
        head = _basename(tokens[0])
        args = tokens[1:]
        if head in _NESTERS:
            joined = " ".join(args)
            nested = r"\bgh\b" if role == "orchestrator" else r"\b(git|gh)\b"
            if re.search(nested, joined):
                return _deny(f"{head} nesting a git/gh command is not allowed")
            continue
        if head == "git":
            reason = None if role == "orchestrator" else _check_git(args)
        elif head == "gh":
            reason = _check_gh(args, role)
        elif head in {"curl", "wget"}:
            reason = _check_curl(args)
        else:
            reason = None
        if reason:
            return reason
    return None


def check_write(file_path: str) -> str | None:
    if "/scratchpad/" in file_path or file_path.startswith("/tmp/"):
        return None
    return _deny("reviewers may write only under the session scratchpad or /tmp")


# ---------------------------------------------------------------------------
# Hook entry point
# ---------------------------------------------------------------------------


def _emit_deny(reason: str) -> None:
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


def run_hook(role: str) -> int:
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except ValueError:
        print("pr-review-guard: stdin was not JSON; allowing", file=sys.stderr)
        return 0
    if not isinstance(payload, dict):
        print("pr-review-guard: unexpected payload shape; allowing", file=sys.stderr)
        return 0
    tool = payload.get("tool_name")
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return 0
    if tool == "Bash":
        command = tool_input.get("command")
        if not isinstance(command, str):
            print("pr-review-guard: command was not a string; allowing", file=sys.stderr)
            return 0
        reason = check_command(command, role)
    elif tool in {"Write", "Edit", "NotebookEdit"} and role == "reviewer":
        path = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
        reason = check_write(str(path))
    else:
        reason = None
    if reason:
        _emit_deny(reason)
    return 0


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

SELF_TEST: list[tuple[str, str, bool]] = [
    # (role, command, expect_denied)
    ("reviewer", "git push origin main", True),
    ("reviewer", "git -C /tmp/x push origin main", True),
    ("reviewer", "git --no-pager push", True),
    ("reviewer", "git -c user.name=x commit -m x", True),
    ("reviewer", "git --git-dir=/x/.git commit -m x", True),
    ("reviewer", "git checkout main", True),
    ("reviewer", "git branch feature", True),
    ("reviewer", "git branch --delete feature", True),
    ("reviewer", "git update-ref refs/heads/main abc", True),
    ("reviewer", "git apply p.diff", True),
    ("reviewer", "git am p.mbox", True),
    ("reviewer", "git symbolic-ref HEAD refs/heads/x", True),
    ("reviewer", "git remote add x y", True),
    ("reviewer", "git config user.name x", True),
    ("reviewer", "git worktree add /tmp/w HEAD", True),
    ("reviewer", "git tag v1", True),
    ("reviewer", "git stash", True),
    ("reviewer", "git fetch origin pull/1/head", True),
    ("reviewer", "command git push", True),
    ("reviewer", "\\git push", True),
    ("reviewer", "env git push", True),
    ("reviewer", "/usr/bin/git push", True),
    ("reviewer", "FOO=1 git push", True),
    ("reviewer", "xargs git push", True),
    ("reviewer", "sh -c 'git push'", True),
    ("reviewer", 'bash -c "gh pr review 1 --approve"', True),
    ("reviewer", "ls\ngit push", True),
    ("reviewer", "gh pr review 1 --approve", True),
    ("reviewer", "gh pr comment 1 --body hi", True),
    ("reviewer", "gh pr create --title x", True),
    ("reviewer", "gh pr merge 1", True),
    ("reviewer", "gh issue comment 1 --body hi", True),
    ("reviewer", "gh alias set x 'pr review'", True),
    ("reviewer", "gh secret set X", True),
    ("reviewer", "gh workflow run x", True),
    ("reviewer", "gh api -X POST repos/o/r/issues/1/comments", True),
    ("reviewer", "gh api -XPOST repos/o/r/issues/1/comments", True),
    ("reviewer", "gh api --method=POST repos/o/r/issues", True),
    ("reviewer", "gh api repos/o/r/issues/1/comments -f body=hi", True),
    ("reviewer", "gh api repos/o/r/pulls/1/reviews -F event=APPROVE", True),
    ("reviewer", "gh api repos/o/r/pulls/1/reviews --input body.json", True),
    ("reviewer", "gh api graphql -f query='mutation { x }'", True),
    ("reviewer", "gh api repos/o/r/issues/1/comments \\\n  -X POST -f body=hi", True),
    ("reviewer", "curl -X POST https://api.github.com/x", True),
    ("reviewer", "curl -d '{}' https://api.github.com/x", True),
    ("orchestrator", "gh api repos/o/r/pulls/1/merge -X PUT", True),
    ("orchestrator", "gh api repos/o/r/pulls/1/reviews -F event=APPROVE", True),
    ("orchestrator", "gh pr review 1 --approve", True),
    ("orchestrator", "gh pr merge 1", True),
    ("orchestrator", "gh pr close 1", True),
    ("orchestrator", "gh api -X PATCH repos/o/r/pulls/1 -f state=closed", True),
    ("orchestrator", "gh api repos/o/r/pulls/1/reviews -f event=APPROVE", True),
    ("orchestrator", "bash -c 'gh pr merge 1'", True),
    # allowed
    ("reviewer", "git diff 29e0cfa..0ff828f -- src/", False),
    ("reviewer", "git show 0ff828f:CLAUDE.md | sed -n '1,5p'", False),
    ("reviewer", "git merge-base origin/main FETCH_HEAD", False),
    ("reviewer", "git log --oneline -5", False),
    ("reviewer", "git ls-tree HEAD .claude/hooks/", False),
    ("reviewer", "git branch --show-current", False),
    ("reviewer", "git branch -a", False),
    ("reviewer", "git tag -l", False),
    ("reviewer", "git worktree list", False),
    ("reviewer", "git config --get user.name", False),
    ("reviewer", "git status --porcelain", False),
    ("reviewer", "gh pr view 10 --json files", False),
    ("reviewer", "gh pr diff 10", False),
    ("reviewer", "gh pr checks 10", False),
    ("reviewer", "gh api repos/o/r/pulls/10/files", False),
    ("reviewer", "gh api -X GET repos/o/r/pulls/10", False),
    ("reviewer", "gh api --method GET repos/o/r/pulls/10", False),
    ("reviewer", "cd /tmp/x && uv run pytest -m unit -q", False),
    ("reviewer", "uv run ruff check src/", False),
    ("reviewer", "uv run python -c 'print(1)'", False),
    ("reviewer", "curl https://rest.uniprot.org/uniprotkb/P04637.json", False),
    ("reviewer", "curl -X GET https://rest.uniprot.org/uniprotkb/P04637.json", False),
    ("reviewer", "grep -rn 'git checkout' docs/", False),
    ("reviewer", "echo 'never run gh pr review'", False),
    (
        "reviewer",
        "cat > /tmp/r.md <<'EOF'\n### [Blocking] git checkout bypass\ngh pr review is denied\nEOF",
        False,
    ),
    ("reviewer", "python3 .claude/hooks/pr-review-guard.py --self-test", False),
    ("orchestrator", "git fetch origin pull/11/head", False),
    ("orchestrator", "git worktree add --detach /tmp/x/pr-11 f60e508", False),
    ("orchestrator", "git worktree remove --force /tmp/x/pr-11", False),
    ("orchestrator", "gh pr comment 11 --body-file /tmp/report.md", False),
    ("orchestrator", "git push origin chore/x", False),
    ("orchestrator", "git checkout main", False),
    ("orchestrator", "gh api repos/o/r/issues/11/comments -f body=hi", False),
]


def self_test() -> int:
    import os
    import tempfile

    failures = 0
    # A COMMENT review body the orchestrator may post, and an APPROVE one it may not.
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as ok:
        json.dump({"event": "COMMENT", "comments": []}, ok)
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as bad:
        json.dump({"event": "APPROVE"}, bad)
    cases = [
        *SELF_TEST,
        ("orchestrator", f"gh api repos/o/r/pulls/11/reviews --input {ok.name}", False),
        ("orchestrator", f"gh api repos/o/r/pulls/11/reviews --input {bad.name}", True),
        ("reviewer", f"gh api repos/o/r/pulls/11/reviews --input {ok.name}", True),
    ]
    for role, command, expect_denied in cases:
        reason = check_command(command, role)
        denied = reason is not None
        if denied != expect_denied:
            failures += 1
            print(
                f"FAIL [{role}] {command!r}: expected {'deny' if expect_denied else 'allow'}, got {reason or 'allow'}"
            )
    for path, expect_denied in [
        ("/tmp/claude-1000/x/scratchpad/reports/a.md", False),
        ("/tmp/r.md", False),
        ("/home/u/repo/src/x.py", True),
    ]:
        denied = check_write(path) is not None
        if denied != expect_denied:
            failures += 1
            print(f"FAIL write {path!r}: expected {'deny' if expect_denied else 'allow'}")
    os.unlink(ok.name)
    os.unlink(bad.name)
    total = len(cases) + 3
    print(f"{total - failures}/{total} cases passed")
    return 1 if failures else 0


def main(argv: list[str]) -> int:
    if "--self-test" in argv:
        return self_test()
    role = (
        "orchestrator"
        if "--role" in argv and argv[argv.index("--role") + 1] == "orchestrator"
        else "reviewer"
    )
    return run_hook(role)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
