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
)
from validate_cross_repo_truth import build_generated_contracts


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fail-closed shadow-parity validation for governance-engine materialization."
    )
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
    parser.add_argument(
        "--skills-root",
        default=Path.home() / ".codex" / "skills",
        type=Path,
        help="live Codex skills root to compare against registered skill sources",
    )
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    workspace_root = args.workspace_root.resolve()
    skills_root = args.skills_root.expanduser().resolve()
    contracts = load_contracts(repo_root)
    foundation = contracts["governance_engine_foundation"]["governance_engine_foundation"]

    errors: list[str] = []
    errors.extend(
        check_workspace_root_outputs(repo_root, workspace_root, contracts=contracts)
    )
    _, skill_errors = install_registered_skills(
        repo_root,
        workspace_root,
        skills_root,
        contracts=contracts,
        check=True,
    )
    errors.extend(skill_errors)
    compiled_outputs = build_generated_contracts(repo_root, contracts)
    errors.extend(
        check_generated_artifacts(repo_root, compiled_outputs, contracts=contracts)
    )

    for rel_path in foundation["compatibility_boundary"]["stable_entrypoints"]:
        path = repo_root / rel_path
        if not path.exists():
            errors.append(f"missing stable compatibility entrypoint: {path}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print("governance-engine shadow parity valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
