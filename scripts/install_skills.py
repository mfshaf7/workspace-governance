#!/usr/bin/env python3
from __future__ import annotations

import argparse
import filecmp
from pathlib import Path
import shutil
import sys


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
    parser = argparse.ArgumentParser(description="Install workspace-governance skills into a Codex skill directory.")
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
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    source_root = repo_root / "skills-src"
    target_root = args.target_root.expanduser().resolve()
    selected = set(args.skill_names or [])

    source_dirs = sorted(path for path in source_root.iterdir() if path.is_dir())
    errors: list[str] = []

    for source_dir in source_dirs:
        if selected and source_dir.name not in selected:
            continue
        target_dir = target_root / source_dir.name
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
        + ", ".join(sorted(selected or [path.name for path in source_dirs]))
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
