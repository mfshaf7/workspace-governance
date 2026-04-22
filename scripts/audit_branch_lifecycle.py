#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from contracts_lib import load_contracts


GITHUB_REPO_RE = re.compile(
    r"(?:git@|https://|ssh://git@)?github\.com[:/](?P<owner>[^/]+)/(?P<repo>[^/.]+?)(?:\.git)?$"
)
EXCEPTION_TARGET_RE = re.compile(
    r"^repo:(?P<repo>[^:]+):(?P<kind>remote-branch|local-branch|worktree):(?P<value>.+)$"
)
REMOTE_WAIVER = "branch-lifecycle-remote-branch"
LOCAL_WAIVER = "branch-lifecycle-local-branch"
WORKTREE_WAIVER = "branch-lifecycle-worktree"


@dataclass(frozen=True)
class WorktreeRecord:
    path: Path
    branch: str | None
    is_main: bool


def run(
    cmd: list[str], *, cwd: Path | None = None, check: bool = True
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        check=check,
        text=True,
        capture_output=True,
    )


def git_output(repo_root: Path, args: list[str]) -> str:
    return run(["git", "-C", str(repo_root), *args]).stdout.strip()


def discover_repos(workspace_root: Path) -> list[Path]:
    return sorted(
        path for path in workspace_root.iterdir() if path.is_dir() and (path / ".git").exists()
    )


def parse_worktrees(repo_root: Path) -> list[WorktreeRecord]:
    output = git_output(repo_root, ["worktree", "list", "--porcelain"])
    if not output:
        return []
    records: list[WorktreeRecord] = []
    block: dict[str, str] = {}
    repo_root = repo_root.resolve()

    def flush() -> None:
        nonlocal block
        if not block:
            return
        path = Path(block["worktree"]).resolve()
        branch = block.get("branch")
        if branch and branch.startswith("refs/heads/"):
            branch = branch.removeprefix("refs/heads/")
        records.append(WorktreeRecord(path=path, branch=branch, is_main=path == repo_root))
        block = {}

    for line in output.splitlines():
        if not line.strip():
            flush()
            continue
        key, _, value = line.partition(" ")
        block[key] = value
    flush()
    return records


def list_local_branches(repo_root: Path) -> set[str]:
    output = git_output(repo_root, ["for-each-ref", "--format=%(refname:short)", "refs/heads"])
    return {line.strip() for line in output.splitlines() if line.strip()}


def github_repo_name(repo_root: Path) -> str:
    origin = git_output(repo_root, ["remote", "get-url", "origin"])
    match = GITHUB_REPO_RE.search(origin)
    if not match:
        raise RuntimeError(f"{repo_root.name}: unsupported GitHub origin {origin!r}")
    return f"{match.group('owner')}/{match.group('repo')}"


def list_remote_branches(repo_root: Path) -> set[str]:
    result = run(["git", "ls-remote", "--heads", "origin"], cwd=repo_root, check=False)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip() or "git ls-remote failed"
        raise RuntimeError(f"{repo_root.name}: unable to query origin heads: {detail}")
    branches: set[str] = set()
    for line in result.stdout.splitlines():
        _, _, ref = line.partition("\t")
        if ref.startswith("refs/heads/"):
            branches.add(ref.removeprefix("refs/heads/"))
    return branches


def list_open_pr_branches(repo_root: Path) -> set[str]:
    repo_name = github_repo_name(repo_root)
    result = run(
        [
            "gh",
            "pr",
            "list",
            "--repo",
            repo_name,
            "--state",
            "open",
            "--limit",
            "500",
            "--json",
            "headRefName",
        ],
        cwd=repo_root,
        check=False,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip() or "gh pr list failed"
        raise RuntimeError(f"{repo_root.name}: unable to query open PR branches: {detail}")
    payload = json.loads(result.stdout or "[]")
    return {entry["headRefName"] for entry in payload if entry.get("headRefName")}


def load_waivers(governance_root: Path) -> dict[str, dict[str, set[str]]]:
    waivers: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    contracts = load_contracts(governance_root)
    for entry in contracts["exceptions"]["exceptions"]:
        match = EXCEPTION_TARGET_RE.fullmatch(entry["target"])
        if not match:
            continue
        repo_name = match.group("repo")
        kind = match.group("kind")
        value = match.group("value")
        if kind == "remote-branch" and REMOTE_WAIVER in entry["waives"]:
            waivers[REMOTE_WAIVER][repo_name].add(value)
        if kind == "local-branch" and LOCAL_WAIVER in entry["waives"]:
            waivers[LOCAL_WAIVER][repo_name].add(value)
        if kind == "worktree" and WORKTREE_WAIVER in entry["waives"]:
            waivers[WORKTREE_WAIVER][repo_name].add(value)
    return waivers


def is_waived(
    waivers: dict[str, dict[str, set[str]]], waiver: str, repo_name: str, value: str
) -> bool:
    return value in waivers.get(waiver, {}).get(repo_name, set())


def format_worktree(record: WorktreeRecord) -> str:
    branch = record.branch or "detached-head"
    return f"{record.path} [{branch}]"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit workspace branch and worktree lifecycle residue."
    )
    parser.add_argument(
        "--workspace-root",
        default=Path(__file__).resolve().parents[2],
        type=Path,
        help="workspace root containing the local Git repositories",
    )
    parser.add_argument(
        "--include-remote",
        action="store_true",
        help="also audit remote branches against open PRs using gh",
    )
    parser.add_argument(
        "--check-clean",
        action="store_true",
        help="also fail if active local branch/worktree state remains instead of only stale residue",
    )
    args = parser.parse_args()

    workspace_root = args.workspace_root.resolve()
    governance_root = workspace_root / "workspace-governance"
    waivers = load_waivers(governance_root)
    errors: list[str] = []
    notes: list[str] = []
    summary = {
        "repos": 0,
        "stale_local_branches": 0,
        "active_non_main_branches": 0,
        "extra_worktrees": 0,
        "missing_worktrees": 0,
        "stale_remote_branches": 0,
    }

    for repo_root in discover_repos(workspace_root):
        repo_name = repo_root.name
        summary["repos"] += 1
        worktrees = parse_worktrees(repo_root)
        if not worktrees:
            errors.append(f"{repo_name}: no git worktree records found")
            continue

        main_worktrees = [record for record in worktrees if record.is_main]
        if len(main_worktrees) != 1:
            errors.append(f"{repo_name}: expected exactly one primary worktree, found {len(main_worktrees)}")
            continue

        main_worktree = main_worktrees[0]
        extra_worktrees = sorted(
            (record for record in worktrees if not record.is_main),
            key=lambda record: str(record.path),
        )
        summary["extra_worktrees"] += len(extra_worktrees)
        summary["active_non_main_branches"] += int(main_worktree.branch not in (None, "main"))

        extra_worktree_waivers = {
            str(record.path.resolve()): is_waived(
                waivers,
                WORKTREE_WAIVER,
                repo_name,
                str(record.path.resolve()),
            )
            for record in extra_worktrees
        }
        missing_worktrees = [
            record
            for record in extra_worktrees
            if not record.path.exists() and not extra_worktree_waivers[str(record.path.resolve())]
        ]
        if missing_worktrees:
            summary["missing_worktrees"] += len(missing_worktrees)
            errors.append(
                f"{repo_name}: missing worktree paths without exception: "
                + ", ".join(format_worktree(record) for record in missing_worktrees)
            )

        active_branch_names = {record.branch for record in worktrees if record.branch}
        local_branches = list_local_branches(repo_root)
        stale_local_branches = sorted(
            branch
            for branch in local_branches
            if branch != "main"
            and branch not in active_branch_names
            and not is_waived(waivers, LOCAL_WAIVER, repo_name, branch)
        )
        if stale_local_branches:
            summary["stale_local_branches"] += len(stale_local_branches)
            errors.append(
                f"{repo_name}: stale local branches without active worktree or exception: "
                + ", ".join(stale_local_branches)
            )

        if args.check_clean:
            non_main_local_branches = sorted(
                branch
                for branch in local_branches
                if branch != "main" and not is_waived(waivers, LOCAL_WAIVER, repo_name, branch)
            )
            if non_main_local_branches:
                errors.append(
                    f"{repo_name}: local non-main branches present in clean mode: "
                    + ", ".join(non_main_local_branches)
                )
            clean_mode_worktrees = [
                record
                for record in extra_worktrees
                if record.path.exists() and not extra_worktree_waivers[str(record.path.resolve())]
            ]
            if clean_mode_worktrees:
                errors.append(
                    f"{repo_name}: extra worktrees present in clean mode: "
                    + ", ".join(format_worktree(record) for record in clean_mode_worktrees)
                )
            if main_worktree.branch is None:
                errors.append(f"{repo_name}: primary worktree is detached HEAD in clean mode")
        else:
            if main_worktree.branch is None:
                notes.append(f"{repo_name}: primary worktree is detached HEAD")
            elif main_worktree.branch != "main":
                notes.append(f"{repo_name}: active non-main branch {main_worktree.branch}")
            live_extra_worktrees = [record for record in extra_worktrees if record.path.exists()]
            if live_extra_worktrees:
                notes.append(
                    f"{repo_name}: active extra worktrees "
                    + ", ".join(format_worktree(record) for record in live_extra_worktrees)
                )

        if args.include_remote:
            remote_branches = sorted(branch for branch in list_remote_branches(repo_root) if branch != "main")
            if remote_branches:
                open_pr_branches = list_open_pr_branches(repo_root)
                stale_remote_branches = [
                    branch
                    for branch in remote_branches
                    if branch not in open_pr_branches
                    and not is_waived(waivers, REMOTE_WAIVER, repo_name, branch)
                ]
                if stale_remote_branches:
                    summary["stale_remote_branches"] += len(stale_remote_branches)
                    errors.append(
                        f"{repo_name}: remote branches without open PR or exception: "
                        + ", ".join(stale_remote_branches)
                    )

    for note in notes:
        print(f"workspace note: {note}")

    if errors:
        raise SystemExit("\n".join(errors))

    clean_mode = "strict" if args.check_clean else "residue-only"
    remote_mode = "enabled" if args.include_remote else "disabled"
    print(
        "branch lifecycle valid: "
        f"repos={summary['repos']} "
        f"stale_local_branches={summary['stale_local_branches']} "
        f"active_non_main_branches={summary['active_non_main_branches']} "
        f"extra_worktrees={summary['extra_worktrees']} "
        f"missing_worktrees={summary['missing_worktrees']} "
        f"stale_remote_branches={summary['stale_remote_branches']} "
        f"clean_mode={clean_mode} "
        f"remote_mode={remote_mode}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
