#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shlex
import subprocess
from pathlib import Path
import sys

from contracts_lib import load_contracts


def run(cmd: list[str], *, cwd: Path | None = None) -> str:
    result = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        check=True,
        text=True,
        capture_output=True,
    )
    output = (result.stdout or "").strip()
    if output:
        return output
    return (result.stderr or "").strip()


def prepare_node_dependencies(repo_root: Path) -> None:
    package_lock = repo_root / "package-lock.json"
    if not package_lock.exists():
        return
    node_modules = repo_root / "node_modules"
    if node_modules.exists():
        return
    subprocess.run(
        ["npm", "ci"],
        cwd=str(repo_root),
        check=True,
        text=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Execute declared component interface validation commands across the workspace."
    )
    parser.add_argument(
        "--workspace-root",
        default=Path(__file__).resolve().parents[2],
        type=Path,
        help="workspace root containing the active repos",
    )
    parser.add_argument(
        "--component",
        action="append",
        default=[],
        help="limit validation to one or more component ids from contracts/components.yaml",
    )
    parser.add_argument(
        "--prepare-node-deps",
        action="store_true",
        help="run npm ci in component owner repos that have a package-lock.json and no node_modules yet",
    )
    args = parser.parse_args()

    workspace_root = args.workspace_root.resolve()
    repo_root = Path(__file__).resolve().parents[1]
    contracts = load_contracts(repo_root)
    selected_components = set(args.component)
    errors: list[str] = []
    checked: list[str] = []
    prepared_node_repos: set[Path] = set()

    for component_name, payload in sorted(contracts["components"]["components"].items()):
        interface_contract = payload.get("interface_contract")
        if not interface_contract:
            continue
        if selected_components and component_name not in selected_components:
            continue

        owner_repo_root = workspace_root / payload["owner_repo"]
        contract_path = owner_repo_root / interface_contract["path"]
        validation_command = interface_contract["validation_command"]

        if not owner_repo_root.exists():
            errors.append(
                f"{component_name}: owner repo is missing from workspace: {owner_repo_root}"
            )
            continue
        if not contract_path.exists():
            errors.append(
                f"{component_name}: declared interface contract path is missing: {contract_path}"
            )
            continue

        if args.prepare_node_deps and owner_repo_root not in prepared_node_repos:
            try:
                prepare_node_dependencies(owner_repo_root)
            except subprocess.CalledProcessError as exc:
                errors.append(
                    f"{component_name}: failed to prepare node dependencies in {owner_repo_root}: "
                    f"{(exc.stdout or '').strip() or (exc.stderr or '').strip() or str(exc)}"
                )
                continue
            prepared_node_repos.add(owner_repo_root)

        try:
            output = run(shlex.split(validation_command), cwd=owner_repo_root)
        except subprocess.CalledProcessError as exc:
            failure_output = (exc.stdout or "").strip() or (exc.stderr or "").strip() or str(exc)
            errors.append(
                f"{component_name}: validation command failed ({validation_command!r})\n{failure_output}"
            )
            continue

        checked.append(component_name)
        if output:
            print(f"[{component_name}] {output}")

    if selected_components:
        unknown_components = sorted(
            selected_components - set(contracts["components"]["components"].keys())
        )
        for component_name in unknown_components:
            errors.append(f"unknown component id: {component_name}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print(f"component interface contracts valid: checked={len(checked)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
