#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

from governance_engine_materializer import install_registered_skills


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
    target_root = args.target_root.expanduser().resolve()
    selected = set(args.skill_names or [])
    skill_names, errors = install_registered_skills(
        repo_root,
        workspace_root,
        target_root,
        selected_skill_names=selected,
        check=args.check,
    )

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print(
        ("skill install check valid: " if args.check else "skills installed: ")
        + ", ".join(skill_names)
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
