#!/usr/bin/env python3
from __future__ import annotations

import argparse
import filecmp
from pathlib import Path
import shutil
import sys

from contracts_lib import load_contracts


def directories_match(left: Path, right: Path) -> bool:
    if not left.exists() or not right.exists():
        return False
    comparison = filecmp.dircmp(left, right)
    if comparison.left_only or comparison.right_only or comparison.diff_files or comparison.funny_files:
        return False
    return all(
        directories_match(left / subdir, right / subdir) for subdir in comparison.common_dirs
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Install registered workspace skills into a Codex skill directory.")
    parser.add_argument(
        "--repo-root",
        default=Path(__file__).resolve().parents[1],
        type=Path,
        help="workspace-governance repository root",
    )
    parser.add_argument(
        "--target-root",
        default=Path.home() / ".codex" / "skills",
        type=Path,
        help="target Codex skill root",
    )
    parser.add_argument(
        "--skill-name",
        action="append",
        dest="skill_names",
        help="install only one or more named skills",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="only verify that installed skills match the source directories",
    )
    parser.add_argument(
        "--workspace-root",
        default=Path(__file__).resolve().parents[2],
        type=Path,
        help="workspace root containing the active repos",
    )
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    workspace_root = args.workspace_root.resolve()
    contracts = load_contracts(repo_root)
    target_root = args.target_root.expanduser().resolve()
    selected = set(args.skill_names or [])
    registered_skills = contracts["skills"]["skills"]
    errors: list[str] = []

    unknown = sorted(selected - set(registered_skills))
    if unknown:
        for name in unknown:
            errors.append(f"unknown registered skill: {name}")
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    for skill_name, payload in sorted(registered_skills.items()):
        if selected and skill_name not in selected:
            continue
        source_dir = workspace_root / payload["owner_repo"] / payload["source_path"]
        target_dir = target_root / source_dir.name
        if not source_dir.exists():
            errors.append(f"missing skill source: {source_dir}")
            continue
        if not (source_dir / "SKILL.md").exists():
            errors.append(f"missing skill definition: {source_dir / 'SKILL.md'}")
            continue
        if args.check:
            if not directories_match(source_dir, target_dir):
                errors.append(f"skill out of sync: {target_dir}")
            continue
        if target_dir.exists():
            shutil.rmtree(target_dir)
        shutil.copytree(source_dir, target_dir)

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print(
        ("skill install check valid: " if args.check else "skills installed: ")
        + ", ".join(sorted(selected or registered_skills.keys()))
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
