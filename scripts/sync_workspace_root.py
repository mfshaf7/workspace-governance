#!/usr/bin/env python3
import argparse
from pathlib import Path

from contracts_lib import load_contracts
from governance_engine_materializer import (
    check_workspace_root_outputs,
    sync_workspace_root_outputs,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sync canonical workspace-governance files into the live workspace root."
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
        help="workspace root that receives the synced files",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail if the live workspace files differ from the canonical copies",
    )
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    workspace_root = args.workspace_root.resolve()
    contracts = load_contracts(repo_root)

    if args.check:
        mismatches = check_workspace_root_outputs(
            repo_root, workspace_root, contracts=contracts
        )
        if mismatches:
            raise SystemExit("\n".join(mismatches))
        print("workspace root sync valid")
        return 0

    for line in sync_workspace_root_outputs(
        repo_root, workspace_root, contracts=contracts
    ):
        print(f"synced {line}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
