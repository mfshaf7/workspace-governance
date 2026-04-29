#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys

from contracts_lib import active_repo_names, load_contracts


STRUCTURED_WORKSPACE_PREFIXES = (
    "contracts/",
    "reviews/after-action/",
    "reviews/delegation-journal/",
    "reviews/improvement-candidates/",
)


def run_git(repo_root: Path, *args: str) -> list[str]:
    proc = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=True,
        text=True,
        capture_output=True,
    )
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def changed_files(repo_root: Path, against_ref: str | None, include_untracked: bool) -> list[str]:
    paths: list[str] = []
    if against_ref:
        paths.extend(run_git(repo_root, "diff", "--name-only", "--diff-filter=ACMR", f"{against_ref}...HEAD"))
    else:
        paths.extend(run_git(repo_root, "diff", "--name-only", "--diff-filter=ACMR"))
        paths.extend(run_git(repo_root, "diff", "--cached", "--name-only", "--diff-filter=ACMR"))
    if include_untracked:
        paths.extend(run_git(repo_root, "ls-files", "--others", "--exclude-standard"))
    return sorted(set(paths))


def is_workspace_structured_record(repo_name: str, rel_path: str) -> bool:
    if repo_name != "workspace-governance":
        return False
    if not rel_path.endswith((".yaml", ".yml", ".json")):
        return False
    if rel_path.endswith("/TEMPLATE.yaml") or rel_path.endswith("/TEMPLATE.yml"):
        return False
    return rel_path.startswith(STRUCTURED_WORKSPACE_PREFIXES)


def is_change_record(rel_path: str) -> bool:
    if not rel_path.startswith("docs/records/change-records/"):
        return False
    if not rel_path.endswith(".md"):
        return False
    return Path(rel_path).name not in {"README.md", "TEMPLATE.md"}


def should_preflight(repo_name: str, rel_path: str) -> bool:
    return is_workspace_structured_record(repo_name, rel_path) or is_change_record(rel_path)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run immediate structured-record preflight for touched governance records.",
    )
    parser.add_argument(
        "--workspace-root",
        default=Path(__file__).resolve().parents[2],
        type=Path,
    )
    parser.add_argument(
        "--repo-root",
        default=Path(__file__).resolve().parents[1],
        type=Path,
        help="workspace-governance repository root",
    )
    parser.add_argument(
        "--against-ref",
        default=None,
        help="Optional git ref to diff against in each repo, for example origin/main.",
    )
    parser.add_argument(
        "--include-untracked",
        action="store_true",
        help="Also validate matching untracked records.",
    )
    parser.add_argument(
        "--path",
        action="append",
        default=[],
        help="Validate an explicit record path instead of scanning changed files.",
    )
    args = parser.parse_args()

    workspace_root = args.workspace_root.resolve()
    repo_root = args.repo_root.resolve()
    validator = repo_root / "scripts" / "validate_structured_record.py"
    if not validator.exists():
        print(f"ERROR: missing validator {validator}", file=sys.stderr)
        return 1

    record_paths: list[Path] = []
    if args.path:
        record_paths = [
            path if path.is_absolute() else (Path.cwd() / path)
            for path in map(Path, args.path)
        ]
    else:
        contracts = load_contracts(repo_root)
        for repo_name in sorted(active_repo_names(contracts)):
            owner_root = workspace_root / repo_name
            if not (owner_root / ".git").exists():
                continue
            try:
                for rel_path in changed_files(owner_root, args.against_ref, args.include_untracked):
                    if should_preflight(repo_name, rel_path):
                        record_paths.append(owner_root / rel_path)
            except subprocess.CalledProcessError as exc:
                print(f"ERROR: failed to inspect {repo_name}: {exc}", file=sys.stderr)
                return 1

    record_paths = sorted({path.resolve() for path in record_paths})
    if not record_paths:
        print("touched structured records valid: none")
        return 0

    failed = 0
    for record_path in record_paths:
        command = [
            sys.executable,
            str(validator),
            str(record_path),
            "--workspace-root",
            str(workspace_root),
        ]
        print("+ " + " ".join(command), flush=True)
        completed = subprocess.run(command, cwd=repo_root, text=True)
        failed |= completed.returncode

    if failed:
        return 1
    print(f"touched structured records valid: records={len(record_paths)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
