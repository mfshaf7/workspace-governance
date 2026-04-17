#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

from contracts_lib import active_repo_names, load_contracts, retired_repo_names


def git_repo_names(workspace_root: Path) -> set[str]:
    names: set[str] = set()
    for child in workspace_root.iterdir():
        if child.is_dir() and (child / ".git").exists():
            names.add(child.name)
    return names


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate the workspace intake layer so new repos, products, and components are classified before they become governed surfaces."
    )
    parser.add_argument(
        "--workspace-root",
        default=Path(__file__).resolve().parents[2],
        type=Path,
        help="workspace root containing workspace-governance and the governed repos",
    )
    args = parser.parse_args()

    workspace_root = args.workspace_root.resolve()
    repo_root = workspace_root / "workspace-governance"
    contracts = load_contracts(repo_root)
    intake_policy = contracts["intake_policy"]
    intake_register = contracts["intake_register"]

    errors: list[str] = []

    active_repos = set(active_repo_names(contracts))
    retired_repos = set(retired_repo_names(contracts))
    intake_repos = set(intake_register["repos"].keys())
    allowed_workspace_repos = active_repos | retired_repos | intake_repos

    if intake_policy["workspace_inventory"]["scan_workspace_root_git_repos"]:
        discovered_git_repos = git_repo_names(workspace_root)
        unclassified_git_repos = sorted(discovered_git_repos - allowed_workspace_repos)
        if unclassified_git_repos and not intake_policy["workspace_inventory"]["allow_unclassified_git_repos"]:
            errors.append(
                "workspace root contains git repos not declared in repos.yaml, retired_repos, or intake-register.yaml: "
                + ", ".join(unclassified_git_repos)
            )

    required_files = tuple(intake_policy["repos"]["admitted_required_files"])
    for repo_name, payload in intake_register["repos"].items():
        repo_path = workspace_root / repo_name
        if payload["status"] != "admitted":
            continue
        if intake_policy["repos"]["admitted_requires_physical_repo"] and not repo_path.exists():
            errors.append(
                f"contracts/intake-register.yaml: admitted repo {repo_name} is missing from workspace root"
            )
            continue
        if not repo_path.exists():
            continue
        for rel_path in required_files:
            if not (repo_path / rel_path).exists():
                errors.append(
                    f"contracts/intake-register.yaml: admitted repo {repo_name} is missing required file {rel_path}"
                )

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print(
        "intake model valid: "
        f"intake_repos={len(intake_register['repos'])} "
        f"intake_products={len(intake_register['products'])} "
        f"intake_components={len(intake_register['components'])}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
