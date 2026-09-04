#!/usr/bin/env python3
"""Deterministic PR merge simulation helper used by .claude/workflows/pr-merge-order.js.

Sub-commands (all print one JSON object to stdout; errors print {"error": ...} and exit non-zero):

  discover [--root DIR] [--limit N]
      gh pr list -> fetch exact refs/pull/N/head -> verify headRefOid -> detached
      worktree per PR at the exact head OID -> full changed-file list vs merge-base
      -> real merge test of each PR onto origin/<default branch> -> pairwise
      "land A, then merge B" simulation under both squash and merge-commit strategies.

  sequence --order 8,10,9,11 [--skip 12] [--strategy auto|squash|merge] [--root DIR]
      Lands PRs in that order on a scratch copy of the default branch. Every open PR
      must appear in --order or --skip; duplicates are rejected. Per step: conflicted
      files, net diffstat, and the GitHub-style PR diff the PR would show if merely
      retargeted (files there but absent from the net contribution mean the PR needs
      a rebase or merge-forward, not a retarget). A stacked PR whose parent was
      squash-landed gets one `git rebase --onto` attempt and a fix_command.

  cleanup [--root DIR]
      Removes ONLY the worktrees and refs recorded in <root>/.pr-merge-sim-manifest.json.

Trust statement: this script mutates LOCAL state only -- refs under refs/pr/<N>,
detached worktrees under --root, and scratch commits inside a scratch worktree.
It never pushes, never merges on GitHub, never comments. --root must be empty,
absent, or already carry this tool's manifest; it may not be the repository root
or a direct child of it (feature worktrees live there).

Requires git >= 2.24 (`git merge --no-verify`) and an authenticated `gh`.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import NoReturn

REPO = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip())
DEFAULT_ROOT = os.environ.get("PR_SIM_ROOT") or str(REPO / ".worktrees" / "pr-merge-sim")
SIM_IDENT = ["-c", "user.name=pr-merge-sim", "-c", "user.email=pr-merge-sim@localhost"]
MANIFEST = ".pr-merge-sim-manifest.json"
MIN_GIT = (2, 24)


# ----------------------------------------------------------------------------- plumbing
def fail(msg: str, code: int = 2) -> NoReturn:
    json.dump({"error": msg}, sys.stdout)
    print()
    sys.exit(code)


def git(*a: str, cwd: Path | str = REPO, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *a], cwd=str(cwd), text=True, capture_output=True, check=check)


def out(*a: str, cwd: Path | str = REPO) -> str:
    return git(*a, cwd=cwd).stdout.strip()


def check_git_version() -> None:
    v = subprocess.check_output(["git", "--version"], text=True).split()[2]
    parts = tuple(int(x) for x in v.split(".")[:2])
    if parts < MIN_GIT:
        fail(f"git {v} is too old; need >= {MIN_GIT[0]}.{MIN_GIT[1]} (git merge --no-verify)")


def default_branch() -> str:
    r = git("symbolic-ref", "--short", "refs/remotes/origin/HEAD", check=False)
    if r.returncode == 0 and "/" in r.stdout:
        return r.stdout.strip().split("/", 1)[1]
    r = subprocess.run(
        ["gh", "repo", "view", "--json", "defaultBranchRef", "--jq", ".defaultBranchRef.name"],
        cwd=REPO,
        text=True,
        capture_output=True,
    )
    return r.stdout.strip() or "main"


def gh_prs(limit: int) -> list[dict]:
    fields = (
        "number,title,headRefName,baseRefName,headRefOid,baseRefOid,isDraft,mergeable,"
        "mergeStateStatus,reviewDecision,reviews,comments,statusCheckRollup,additions,deletions,url"
    )
    r = subprocess.run(
        ["gh", "pr", "list", "--state", "open", "--limit", str(limit), "--json", fields],
        cwd=REPO,
        text=True,
        capture_output=True,
    )
    if r.returncode != 0:
        fail(f"gh pr list failed: {r.stderr.strip()[-300:]}")
    return json.loads(r.stdout)


# ----------------------------------------------------------------------------- manifest / root
def load_manifest(root: Path) -> dict:
    f = root / MANIFEST
    return json.loads(f.read_text()) if f.exists() else {"worktrees": [], "refs": []}


def save_manifest(root: Path, m: dict) -> None:
    (root / MANIFEST).write_text(json.dumps(m, indent=1))


def ensure_root(root: Path) -> None:
    """Refuse a root that is not ours: it must be empty, absent, or carry our manifest."""
    resolved = root.resolve()
    repo = REPO.resolve()
    if resolved == repo or resolved.parent == repo:
        fail(f"--root {root} must not be the repository root or a direct child of it")
    if root.exists():
        entries = [e.name for e in root.iterdir()]
        if entries and MANIFEST not in entries:
            fail(f"--root {root} is not empty and has no {MANIFEST}; refusing to touch it")
    root.mkdir(parents=True, exist_ok=True)
    if not (root / MANIFEST).exists():
        save_manifest(root, {"worktrees": [], "refs": []})


def add_worktree(root: Path, path: Path, oid: str) -> None:
    m = load_manifest(root)
    if path.exists():
        if str(path) not in m["worktrees"]:
            fail(f"{path} exists but is not in {MANIFEST}; refusing to replace it")
        git("worktree", "remove", "--force", str(path), check=False)
        shutil.rmtree(path, ignore_errors=True)
    git("worktree", "add", "--detach", "--quiet", str(path), oid)
    if str(path) not in m["worktrees"]:
        m["worktrees"].append(str(path))
    save_manifest(root, m)


def remove_worktree(root: Path, path: Path) -> None:
    git("worktree", "remove", "--force", str(path), check=False)
    shutil.rmtree(path, ignore_errors=True)
    m = load_manifest(root)
    m["worktrees"] = [w for w in m["worktrees"] if w != str(path)]
    save_manifest(root, m)


# ----------------------------------------------------------------------------- git simulation
def conflicted(cwd: Path) -> list[str]:
    o = out("diff", "--name-only", "--diff-filter=U", cwd=cwd)
    return sorted(o.splitlines()) if o else []


def try_merge(scratch: Path, oid: str) -> dict:
    """Real merge (no commit) of oid onto scratch HEAD; report conflicts; leave HEAD untouched."""
    r = git("merge", "--no-commit", "--no-ff", oid, cwd=scratch, check=False)
    files = conflicted(scratch)
    git("merge", "--abort", cwd=scratch, check=False)
    git("reset", "--hard", "--quiet", cwd=scratch, check=False)
    return {"clean": r.returncode == 0 and not files, "conflicted_files": files}


def detect_strategy(base: str) -> str:
    """'merge' if any of the last five landings on the default branch was a merge commit."""
    last = out("log", "--first-parent", "-5", "--format=%P", f"origin/{base}").splitlines()
    return "merge" if any(len(p.split()) > 1 for p in last) else "squash"


def land(scratch: Path, oid: str, label: str, strategy: str) -> dict:
    """Land oid onto scratch HEAD (local only) using the given strategy; return a step report."""
    before = out("rev-parse", "HEAD", cwd=scratch)
    if strategy == "merge":
        r = git(
            *SIM_IDENT,
            "merge",
            "--no-ff",
            "--no-edit",
            "--no-verify",
            "-m",
            f"sim merge {label}",
            oid,
            cwd=scratch,
            check=False,
        )
    else:
        r = git("merge", "--squash", oid, cwd=scratch, check=False)
    files = conflicted(scratch)
    if r.returncode != 0 or files:
        git("merge", "--abort", cwd=scratch, check=False)
        git("reset", "--hard", "--quiet", before, cwd=scratch, check=False)
        return {
            "landed": False,
            "strategy": strategy,
            "conflicted_files": files,
            "stderr": r.stderr.strip()[-400:],
        }
    if strategy == "squash":
        if not out("status", "--porcelain", cwd=scratch):  # already contained
            return {
                "landed": True,
                "strategy": strategy,
                "empty": True,
                "net_files": [],
                "net_stat": "",
            }
        git(
            *SIM_IDENT, "commit", "--quiet", "--no-verify", "-m", f"sim squash {label}", cwd=scratch
        )
    elif out("rev-parse", "HEAD", cwd=scratch) == before:
        return {
            "landed": True,
            "strategy": strategy,
            "empty": True,
            "net_files": [],
            "net_stat": "",
        }
    after = out("rev-parse", "HEAD", cwd=scratch)
    net_files = sorted(out("diff", "--name-only", before, after, cwd=scratch).splitlines())
    net_stat = out("diff", "--shortstat", before, after, cwd=scratch)
    return {
        "landed": True,
        "strategy": strategy,
        "empty": False,
        "net_files": net_files,
        "net_stat": net_stat,
        "sim_head": after,
    }


def github_style_diff_files(scratch: Path, sim_head: str, pr_oid: str) -> list[str]:
    """Files GitHub would show for the PR if its base were sim_head (merge-base...head)."""
    mb = out("merge-base", sim_head, pr_oid, cwd=scratch)
    return sorted(out("diff", "--name-only", mb, pr_oid, cwd=scratch).splitlines())


def prepare(root: Path, limit: int) -> tuple[list[dict], Path, str, str]:
    check_git_version()
    ensure_root(root)
    base = default_branch()
    git("fetch", "--quiet", "origin", base)
    main_oid = out("rev-parse", f"origin/{base}")
    prs = gh_prs(limit)
    m = load_manifest(root)
    for p in prs:
        n = p["number"]
        ref = f"refs/pr/{n}"
        if ref not in m["refs"]:
            m["refs"].append(ref)
        save_manifest(root, m)
        git("fetch", "--quiet", "origin", f"+refs/pull/{n}/head:{ref}")
        local = out("rev-parse", ref)
        p["fetched_oid"] = local
        p["oid_verified"] = local == p["headRefOid"]
        if not p["oid_verified"]:
            # GitHub's headRefOid moved between list and fetch: simulate what we actually fetched.
            p["headRefOid"] = local
    scratch = root / "scratch-main"
    add_worktree(root, scratch, main_oid)
    return prs, scratch, main_oid, base


# ----------------------------------------------------------------------------- commands
def cmd_discover(args: argparse.Namespace) -> dict:
    root = Path(args.root)
    prs, scratch, main_oid, base = prepare(root, args.limit)
    if len(prs) >= args.limit:
        sys.stderr.write(f"warning: --limit {args.limit} reached; some open PRs may be missing\n")
    by_head = {p["headRefName"]: p["number"] for p in prs}
    result_prs = []
    for p in prs:
        n, oid = p["number"], p["headRefOid"]
        wt = root / f"pr-{n}"
        add_worktree(root, wt, oid)
        mb = out("merge-base", main_oid, oid)
        files = sorted(out("diff", "--name-only", mb, oid).splitlines())
        result_prs.append(
            {
                "number": n,
                "title": p["title"],
                "url": p["url"],
                "head": p["headRefName"],
                "base": p["baseRefName"],
                "head_oid": oid,
                "base_oid": p["baseRefOid"],
                "oid_verified": p["oid_verified"],
                "merge_base_with_main": mb,
                "stacked_on_pr": by_head.get(p["baseRefName"]),
                "is_draft": p["isDraft"],
                "mergeable": p["mergeable"],
                "merge_state": p["mergeStateStatus"],
                "github_review_decision": p["reviewDecision"] or "none",
                "github_reviews": [
                    {
                        "author": r.get("author", {}).get("login"),
                        "state": r.get("state"),
                        "at": r.get("submittedAt"),
                    }
                    for r in p.get("reviews", [])
                ],
                "issue_comments": [
                    {
                        "author": c.get("author", {}).get("login"),
                        "at": c.get("createdAt"),
                        "head": (c.get("body") or "")[:120],
                    }
                    for c in p.get("comments", [])
                ],
                "checks": [
                    {
                        "name": c.get("name") or c.get("context"),
                        "status": c.get("status"),
                        "conclusion": c.get("conclusion") or c.get("state"),
                        "details_url": c.get("detailsUrl") or c.get("targetUrl"),
                    }
                    for c in p.get("statusCheckRollup", [])
                ],
                "additions": p["additions"],
                "deletions": p["deletions"],
                "files": files,
                "worktree": str(wt),
                "merge_onto_main": try_merge(scratch, oid),
            }
        )
    pairwise = []
    for strategy in ("squash", "merge"):
        for a in result_prs:
            git("reset", "--hard", "--quiet", main_oid, cwd=scratch)
            if not land(scratch, a["head_oid"], f"#{a['number']}", strategy)["landed"]:
                continue
            sim_head = out("rev-parse", "HEAD", cwd=scratch)
            for b in result_prs:
                if a["number"] == b["number"]:
                    continue
                m = try_merge(scratch, b["head_oid"])
                # Retarget hazard: files GitHub would show in B's diff against the landed tree that B
                # does not actually change relative to that tree, i.e. A's content re-appearing in B.
                b_net = set(
                    out("diff", "--name-only", sim_head, b["head_oid"], cwd=scratch).splitlines()
                )
                hazard = sorted(
                    set(github_style_diff_files(scratch, sim_head, b["head_oid"])) - b_net
                )
                pairwise.append(
                    {
                        "land_strategy_for_first": strategy,
                        "after": a["number"],
                        "then": b["number"],
                        "shared_files": sorted(set(a["files"]) & set(b["files"])),
                        "clean": m["clean"],
                        "conflicted_files": m["conflicted_files"],
                        "retarget_hazard_files": hazard,
                    }
                )
    git("reset", "--hard", "--quiet", main_oid, cwd=scratch)
    return {
        "main_oid": main_oid,
        "default_branch": base,
        "repo_landing_convention": detect_strategy(base),
        "root": str(root),
        "prs": result_prs,
        "pairwise": pairwise,
    }


def cmd_sequence(args: argparse.Namespace) -> dict:
    root = Path(args.root)
    order = [int(x) for x in args.order.split(",") if x.strip()]
    skip = {int(x) for x in (args.skip or "").split(",") if x.strip()}
    if len(set(order)) != len(order):
        fail(f"--order contains duplicates: {order}")
    if set(order) & skip:
        fail(f"PRs listed in both --order and --skip: {sorted(set(order) & skip)}")
    prs, scratch, main_oid, base = prepare(root, args.limit)
    strategy = detect_strategy(base) if args.strategy == "auto" else args.strategy
    by_num = {p["number"]: p for p in prs}
    by_head = {p["headRefName"]: p for p in prs}
    missing = sorted(set(by_num) - set(order) - skip)
    if missing:
        fail(f"open PRs missing from --order (add them or list them in --skip): {missing}")
    unknown = sorted((set(order) | skip) - set(by_num))
    if unknown:
        fail(f"not open PRs: {unknown}")
    landed_nums: set[int] = set()
    steps = []
    ok = True
    for n in order:
        p = by_num[n]
        pre = out("rev-parse", "HEAD", cwd=scratch)
        gh_files = github_style_diff_files(scratch, pre, p["headRefOid"])
        step = land(scratch, p["headRefOid"], f"#{n}", strategy)
        step["pr"] = n
        step["head_oid"] = p["headRefOid"]
        parent = by_head.get(p["baseRefName"])
        if not step["landed"] and parent and parent["number"] in landed_nums:
            # Stacked PR whose parent already landed: simulate the real fix,
            # `git rebase --onto <new main> <parent head> <pr head>`, then land the rebased tip.
            rb = root / "scratch-rebase"
            add_worktree(root, rb, p["headRefOid"])
            r = git(*SIM_IDENT, "rebase", "--onto", pre, parent["headRefOid"], cwd=rb, check=False)
            if r.returncode == 0:
                tip = out("rev-parse", "HEAD", cwd=rb)
                step2 = land(scratch, tip, f"#{n} (rebased)", strategy)
                step2.update(
                    {
                        "pr": n,
                        "head_oid": p["headRefOid"],
                        "rebased_tip": tip,
                        "landed_after_rebase": step2["landed"],
                        "first_attempt_conflicts": step["conflicted_files"],
                        "fix_command": (
                            f"git rebase --onto origin/{base} {parent['headRefOid'][:12]} "
                            f"{p['headRefName']} && git push --force-with-lease"
                        ),
                    }
                )
                if step2["landed"]:
                    gh_files = github_style_diff_files(scratch, pre, tip)
                step = step2
            else:
                rb_conf = conflicted(rb)
                git("rebase", "--abort", cwd=rb, check=False)
                step["rebase_attempt"] = {
                    "ok": False,
                    "conflicted_files": rb_conf,
                    "stderr": r.stderr.strip()[-300:],
                }
            remove_worktree(root, rb)
        if step["landed"]:
            extra = sorted(set(gh_files) - set(step["net_files"]))
            step["github_style_diff_files"] = gh_files
            step["retarget_hazard_files"] = extra
            step["needs_rebase_before_merge"] = bool(extra)
            landed_nums.add(n)
        else:
            ok = False
        steps.append(step)
        if not step["landed"]:
            break
    final = out("rev-parse", "HEAD", cwd=scratch)
    git("reset", "--hard", "--quiet", main_oid, cwd=scratch)
    return {
        "main_oid": main_oid,
        "default_branch": base,
        "strategy": strategy,
        "order": order,
        "skipped": sorted(skip),
        "all_landed": ok,
        "steps": steps,
        "final_sim_head": final,
    }


def cmd_cleanup(args: argparse.Namespace) -> dict:
    """Remove ONLY what this tool recorded in <root>/MANIFEST; never touch anything else."""
    root = Path(args.root)
    if not (root / MANIFEST).exists():
        return {
            "removed": [],
            "refs_deleted": [],
            "note": f"no {MANIFEST} under {root}; nothing to do",
        }
    m = load_manifest(root)
    removed, refs_deleted = [], []
    for wt in m["worktrees"]:
        if Path(wt).exists():
            git("worktree", "remove", "--force", wt, check=False)
            shutil.rmtree(wt, ignore_errors=True)
            removed.append(wt)
    for ref in m["refs"]:
        if git("show-ref", "--verify", "--quiet", ref, check=False).returncode == 0:
            git("update-ref", "-d", ref, check=False)
            refs_deleted.append(ref)
    (root / MANIFEST).unlink()
    leftovers = [e.name for e in root.iterdir()]
    if not leftovers:
        root.rmdir()
    return {"removed": removed, "refs_deleted": refs_deleted, "left_in_place": leftovers}


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("discover", "sequence", "cleanup"):
        s = sub.add_parser(name)
        s.add_argument("--root", default=DEFAULT_ROOT)
        s.add_argument("--limit", type=int, default=30)
        if name == "sequence":
            s.add_argument(
                "--order", required=True, help="comma-separated PR numbers in landing order"
            )
            s.add_argument(
                "--skip", default="", help="comma-separated open PRs deliberately excluded (holds)"
            )
            s.add_argument(
                "--strategy",
                choices=("auto", "squash", "merge"),
                default="auto",
                help="how PRs land on the default branch; auto = detect from recent history",
            )
    args = ap.parse_args()
    fn = {"discover": cmd_discover, "sequence": cmd_sequence, "cleanup": cmd_cleanup}[args.cmd]
    try:
        result = fn(args)
    except subprocess.CalledProcessError as e:
        fail(
            f"{' '.join(e.cmd)} failed ({e.returncode}): {(e.stderr or '').strip()[-400:]} "
            f"-- run `cleanup --root {args.root}` to remove partial state",
            1,
        )
    json.dump(result, sys.stdout, indent=1)
    print()


if __name__ == "__main__":
    main()
