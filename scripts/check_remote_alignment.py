#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path
import sys

from contracts_lib import active_repo_names, load_contracts


def run(cmd: list[str], *, cwd: Path) -> str:
    result = subprocess.run(
        cmd,
        cwd=str(cwd),
        check=True,
        text=True,
        capture_output=True,
    )
    return result.stdout.strip()


def try_run(cmd: list[str], *, cwd: Path) -> tuple[bool, str]:
    result = subprocess.run(
        cmd,
        cwd=str(cwd),
        check=False,
        text=True,
        capture_output=True,
    )
    output = result.stdout.strip() or result.stderr.strip()
    return result.returncode == 0, output


def classify_alignment(repo_root: Path, *, refresh_remote: bool) -> tuple[str, str]:
    if refresh_remote:
        ok, output = try_run(
            [
                "git",
                "fetch",
                "origin",
                "refs/heads/main:refs/remotes/origin/main",
                "--quiet",
            ],
            cwd=repo_root,
        )
        if not ok:
            return "fetch_failed", output or "git fetch origin main failed"

    ok, branch = try_run(["git", "symbolic-ref", "--short", "HEAD"], cwd=repo_root)
    if not ok:
        branch = "DETACHED"

    try:
        head_sha = run(["git", "rev-parse", "HEAD"], cwd=repo_root)
        upstream_sha = run(["git", "rev-parse", "origin/main"], cwd=repo_root)
    except subprocess.CalledProcessError as exc:
        message = exc.stdout.strip() or exc.stderr.strip() or str(exc)
        return "missing_upstream", message

    if head_sha == upstream_sha:
        return "aligned", f"{repo_root.name}: aligned with origin/main at {head_sha[:12]} (branch {branch})"

    head_ancestor, _ = try_run(["git", "merge-base", "--is-ancestor", "HEAD", "origin/main"], cwd=repo_root)
    upstream_ancestor, _ = try_run(
        ["git", "merge-base", "--is-ancestor", "origin/main", "HEAD"],
        cwd=repo_root,
    )

    if upstream_ancestor:
        return "ahead", f"{repo_root.name}: ahead of origin/main at {head_sha[:12]} (branch {branch})"
    if head_ancestor:
        return "behind", f"{repo_root.name}: behind origin/main; local {head_sha[:12]}, remote {upstream_sha[:12]} (branch {branch})"
    return "diverged", f"{repo_root.name}: diverged from origin/main; local {head_sha[:12]}, remote {upstream_sha[:12]} (branch {branch})"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check whether local active repos are aligned with origin/main."
    )
    parser.add_argument(
        "--workspace-root",
        default=Path(__file__).resolve().parents[2],
        type=Path,
        help="workspace root containing the active repos",
    )
    parser.add_argument(
        "--repo-name",
        action="append",
        dest="repo_names",
        help="limit the check to one or more repo names; defaults to all active repos",
    )
    parser.add_argument(
        "--refresh-remote",
        action="store_true",
        help="refresh origin/main before comparing local state",
    )
    args = parser.parse_args()

    workspace_root = args.workspace_root.resolve()
    governance_root = Path(__file__).resolve().parents[1]
    contracts = load_contracts(governance_root)
    repo_names = sorted(set(args.repo_names or active_repo_names(contracts)))

    statuses: list[tuple[str, str]] = []
    missing_repos = 0
    for repo_name in repo_names:
        repo_root = workspace_root / repo_name
        if not repo_root.exists():
            statuses.append(("missing_repo", f"{repo_name}: repo path missing at {repo_root}"))
            missing_repos += 1
            continue
        statuses.append(classify_alignment(repo_root, refresh_remote=args.refresh_remote))

    exit_status = 0
    for status, message in statuses:
        prefix = {
            "aligned": "OK",
            "ahead": "WARN",
            "behind": "ERROR",
            "diverged": "ERROR",
            "missing_upstream": "ERROR",
            "fetch_failed": "ERROR",
            "missing_repo": "ERROR",
        }[status]
        print(f"{prefix}: {message}")
        if status in {"behind", "diverged", "missing_upstream", "fetch_failed", "missing_repo"}:
            exit_status = 1

    print(
        "remote alignment summary:"
        f" repos_checked={len(statuses)}"
        f" missing_repos={missing_repos}"
        f" failures={sum(1 for status, _ in statuses if status in {'behind', 'diverged', 'missing_upstream', 'fetch_failed', 'missing_repo'})}"
    )
    return exit_status


if __name__ == "__main__":
    sys.exit(main())
