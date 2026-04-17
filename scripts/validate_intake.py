#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

from contracts_lib import active_repo_names, load_contracts, load_yaml, retired_repo_names


def git_repo_names(workspace_root: Path) -> set[str]:
    names: set[str] = set()
    for child in workspace_root.iterdir():
        if child.is_dir() and (child / ".git").exists():
            names.add(child.name)
    return names


def load_governed_profiles(workspace_root: Path, intake_policy: dict, errors: list[str]) -> dict[str, dict]:
    ai_policy = intake_policy.get("ai_suggestions") or {}
    registry_ref = ai_policy.get("governed_profile_registry") or {}
    repo = registry_ref.get("repo")
    rel_path = registry_ref.get("path")
    if not isinstance(repo, str) or not repo or not isinstance(rel_path, str) or not rel_path:
        errors.append("contracts/intake-policy.yaml: ai_suggestions.governed_profile_registry must define repo and path")
        return {}
    registry_path = workspace_root / repo / rel_path
    if not registry_path.exists():
        errors.append(
            f"contracts/intake-policy.yaml: governed profile registry is missing: {repo}/{rel_path}"
        )
        return {}
    payload = load_yaml(registry_path)
    profiles = payload.get("model_profiles")
    if not isinstance(profiles, dict):
        errors.append(
            f"{repo}/{rel_path}: model_profiles must be a mapping for governed intake validation"
        )
        return {}
    return profiles


def validate_ai_suggestion(
    *,
    label: str,
    payload: dict,
    intake_policy: dict,
    profiles: dict[str, dict],
    errors: list[str],
) -> None:
    ai_suggestion = payload.get("ai_suggestion")
    if payload["decision_source"] != "ai-suggested":
        if ai_suggestion is not None:
            errors.append(f"{label}: ai_suggestion must only be present when decision_source is ai-suggested")
        return

    if not isinstance(ai_suggestion, dict):
        errors.append(f"{label}: ai_suggestion is required when decision_source is ai-suggested")
        return

    profile_id = ai_suggestion.get("profile_id")
    if not isinstance(profile_id, str) or not profile_id:
        errors.append(f"{label}: ai_suggestion.profile_id must be a non-empty string")
        return

    profile = profiles.get(profile_id)
    if not isinstance(profile, dict):
        errors.append(f"{label}: ai_suggestion.profile_id {profile_id!r} is not present in the governed profile registry")
        return

    required_status = intake_policy["ai_suggestions"]["required_profile_status"]
    actual_status = profile.get("status")
    if actual_status != required_status:
        errors.append(
            f"{label}: governed profile {profile_id!r} must be {required_status!r}, got {actual_status!r}"
        )
    if ai_suggestion.get("policy_status") != actual_status:
        errors.append(
            f"{label}: ai_suggestion.policy_status must match governed profile status {actual_status!r}"
        )
    required_purposes = set(intake_policy["ai_suggestions"]["required_purposes"])
    if profile.get("purpose") not in required_purposes:
        errors.append(
            f"{label}: governed profile {profile_id!r} purpose {profile.get('purpose')!r} is not allowed for intake"
        )
    if intake_policy["ai_suggestions"]["require_human_approval"] and not profile.get("human_approval_required"):
        errors.append(
            f"{label}: governed profile {profile_id!r} must require human approval for intake use"
        )


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

    profiles: dict[str, dict] = {}
    if any(
        payload.get("decision_source") == "ai-suggested"
        for collection in ("repos", "products", "components")
        for payload in intake_register[collection].values()
    ):
        profiles = load_governed_profiles(workspace_root, intake_policy, errors)

    for collection_name in ("repos", "products", "components"):
        for entry_name, payload in intake_register[collection_name].items():
            validate_ai_suggestion(
                label=f"contracts/intake-register.yaml: {collection_name[:-1]} {entry_name}",
                payload=payload,
                intake_policy=intake_policy,
                profiles=profiles,
                errors=errors,
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
