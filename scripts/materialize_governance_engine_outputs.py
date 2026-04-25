#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

from contracts_lib import load_contracts
from governance_engine_materializer import (
    check_generated_artifacts,
    check_workspace_root_outputs,
    install_registered_skills,
    sync_workspace_root_outputs,
    write_generated_artifacts,
)
from validate_cross_repo_truth import build_generated_contracts


def _common_parser(description: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "--repo-root",
        default=Path(__file__).resolve().parents[1],
        type=Path,
        help="workspace-governance repository root",
    )
    parser.add_argument(
        "--workspace-root",
        default=Path(__file__).resolve().parents[2],
        type=Path,
        help="workspace root containing the active repos",
    )
    return parser


def main() -> int:
    parser = _common_parser(
        "Materialize governance-engine output families declared in the output manifest."
    )
    subparsers = parser.add_subparsers(dest="family", required=True)

    workspace_parser = subparsers.add_parser(
        "workspace-root",
        parents=[_common_parser("")],
        add_help=False,
        help="sync or verify live workspace-root outputs",
    )
    workspace_parser.add_argument(
        "--check",
        action="store_true",
        help="only verify that the live workspace-root outputs match the canonical copies",
    )

    skills_parser = subparsers.add_parser(
        "skills",
        parents=[_common_parser("")],
        add_help=False,
        help="install or verify managed live skills",
    )
    skills_parser.add_argument(
        "--target-root",
        default=Path.home() / ".codex" / "skills",
        type=Path,
        help="target Codex skill root",
    )
    skills_parser.add_argument(
        "--skill-name",
        action="append",
        dest="skill_names",
        help="install or verify only one or more named skills",
    )
    skills_parser.add_argument(
        "--check",
        action="store_true",
        help="only verify that installed skills match the source directories",
    )

    generated_parser = subparsers.add_parser(
        "generated",
        parents=[_common_parser("")],
        add_help=False,
        help="materialize or verify generated governance artifacts",
    )
    generated_parser.add_argument(
        "--check",
        action="store_true",
        help="only verify that generated artifacts match the compiled governance outputs",
    )

    args = parser.parse_args()
    repo_root = args.repo_root.resolve()
    workspace_root = args.workspace_root.resolve()
    contracts = load_contracts(repo_root)

    if args.family == "workspace-root":
        if args.check:
            mismatches = check_workspace_root_outputs(
                repo_root, workspace_root, contracts=contracts
            )
            if mismatches:
                raise SystemExit("\n".join(mismatches))
            print("workspace-root materialization valid")
            return 0
        for line in sync_workspace_root_outputs(
            repo_root, workspace_root, contracts=contracts
        ):
            print(f"synced {line}")
        return 0

    if args.family == "skills":
        selected = set(args.skill_names or [])
        skill_names, errors = install_registered_skills(
            repo_root,
            workspace_root,
            args.target_root,
            contracts=contracts,
            selected_skill_names=selected,
            check=args.check,
        )
        if errors:
            for error in errors:
                print(f"ERROR: {error}")
            return 1
        print(
            ("skill materialization valid: " if args.check else "skills materialized: ")
            + ", ".join(skill_names)
        )
        return 0

    compiled = build_generated_contracts(repo_root, contracts)
    if args.check:
        errors = check_generated_artifacts(repo_root, compiled, contracts=contracts)
        if errors:
            raise SystemExit("\n".join(errors))
        print("generated artifact materialization valid")
        return 0
    written = write_generated_artifacts(repo_root, compiled, contracts=contracts)
    print(
        "generated artifacts materialized: "
        + ", ".join(str(path.relative_to(repo_root)) for path in written)
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
