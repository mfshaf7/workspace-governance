#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

import yaml

from contracts_lib import load_contracts


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit deterministic improvement signals across active repos."
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
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    workspace_root = args.workspace_root.resolve()
    contracts = load_contracts(repo_root)
    errors: list[str] = []
    workflow_count = 0
    profile_count = 0

    for repo_name, rule in sorted(contracts["repo_rules"].items()):
        workflow_requirements = rule.get("operator_workflow_requirements")
        if not workflow_requirements:
            continue
        repo_path = workspace_root / repo_name
        if not repo_path.exists():
            errors.append(f"{repo_name}: active repo path missing at {repo_path}")
            continue
        readme_path = repo_path / "README.md"
        agents_path = repo_path / "AGENTS.md"
        readme_text = read_text(readme_path) if readme_path.exists() else ""
        agents_text = read_text(agents_path) if agents_path.exists() else ""

        seen_ids: set[str] = set()
        for workflow in workflow_requirements.get("workflows", []):
            workflow_count += 1
            workflow_id = workflow["id"]
            if workflow_id in seen_ids:
                errors.append(
                    f"contracts/repo-rules/{repo_name}.yaml: duplicate operator workflow id {workflow_id!r}"
                )
            seen_ids.add(workflow_id)

            primary_surface_path = workflow["primary_surface_path"]
            surface = repo_path / primary_surface_path
            if not surface.exists():
                errors.append(f"{repo_name}: operator workflow {workflow_id!r} is missing {primary_surface_path}")
                continue

            surface_text = read_text(surface).lower()
            if "primary operator" not in surface_text:
                errors.append(
                    f"{repo_name}: operator workflow {workflow_id!r} primary surface {primary_surface_path!r} "
                    "must identify itself as a primary operator surface"
                )

            for target in workflow["required_in_docs"]:
                target_text = readme_text if target == "readme" else agents_text
                if primary_surface_path not in target_text:
                    errors.append(
                        f"{repo_name}: {target} must reference operator workflow {workflow_id!r} "
                        f"primary surface {primary_surface_path!r}"
                    )

    for profile_name, payload in sorted(contracts["developer_integration_profiles"]["profiles"].items()):
        if payload["lifecycle"] != "active":
            continue
        profile_count += 1
        profile_path = workspace_root / payload["owner_repo"] / payload["profile_path"]
        if not profile_path.exists():
            errors.append(f"{profile_name}: active profile file missing at {profile_path}")
            continue
        profile = load_yaml(profile_path)
        registry_checks = payload["stage_handoff"].get("required_checks") or []
        profile_checks = (profile.get("stage_handoff") or {}).get("required_checks") or []
        if registry_checks != profile_checks:
            errors.append(
                f"{profile_name}: active profile stage_handoff.required_checks drift between registry and profile file"
            )
        if not profile_checks:
            errors.append(f"{profile_name}: active profile must declare non-empty stage_handoff.required_checks")
            continue
        readme_path = profile_path.parent / "README.md"
        if not readme_path.exists():
            errors.append(f"{profile_name}: active profile README missing at {readme_path}")
            continue
        readme_text = read_text(readme_path)
        if "## Stage Handoff Checks" not in readme_text:
            errors.append(
                f"{profile_name}: active profile README must contain '## Stage Handoff Checks'"
            )
        for check_name in profile_checks:
            if check_name not in readme_text:
                errors.append(
                    f"{profile_name}: active profile README is missing stage handoff check {check_name!r}"
                )

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print(
        "improvement signals clean: "
        f"operator_workflows_checked={workflow_count} "
        f"active_devint_profiles_checked={profile_count}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
