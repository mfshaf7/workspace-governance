#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

import yaml

from contracts_lib import active_repo_names, load_contracts


REQUIRED_ACTIONS = {
    "up",
    "status",
    "smoke",
    "down",
    "reset",
    "promote_check",
}
REQUIRED_PROFILE_KEYS = {
    "schema_version",
    "profile_id",
    "summary",
    "runtime",
    "source_repos",
    "commands",
    "session",
    "stage_handoff",
}


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text()) or {}


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def validate(repo_root: Path, workspace_root: Path) -> list[str]:
    errors: list[str] = []
    contracts = load_contracts(repo_root)
    active_repos = set(active_repo_names(contracts))
    policy = contracts["developer_integration_policy"]
    registry = contracts["developer_integration_profiles"]

    required_actions = set(policy["required_actions"])
    profile_lifecycle = policy["profile_lifecycle"]
    request_admission = policy["request_admission"]
    if required_actions != REQUIRED_ACTIONS:
        errors.append(
            "contracts/developer-integration-policy.yaml: required_actions must be exactly "
            + ", ".join(sorted(REQUIRED_ACTIONS))
        )

    lane = policy["lane"]
    if lane["id"] != "dev-integration":
        errors.append(
            "contracts/developer-integration-policy.yaml: lane.id must be 'dev-integration'"
        )
    for repo_ref in (lane["standard_owner"], lane["runtime_owner"]):
        if repo_ref not in active_repos:
            errors.append(
                f"contracts/developer-integration-policy.yaml: unknown active repo reference {repo_ref!r}"
            )
    if set(profile_lifecycle["statuses"]) != {"proposed", "active", "suspended", "retired"}:
        errors.append(
            "contracts/developer-integration-policy.yaml: profile_lifecycle.statuses must be exactly active, proposed, retired, suspended"
        )
    if set(profile_lifecycle["self_serve_statuses"]) != {"active"}:
        errors.append(
            "contracts/developer-integration-policy.yaml: profile_lifecycle.self_serve_statuses must be exactly active"
        )
    adapter_owner = request_admission["current_request_adapter"]["owner_repo"]
    if adapter_owner not in active_repos:
        errors.append(
            "contracts/developer-integration-policy.yaml: current_request_adapter.owner_repo must reference an active repo"
        )

    checked_profiles = 0
    for profile_name, payload in sorted(registry["profiles"].items()):
        checked_profiles += 1
        lifecycle = payload["lifecycle"]
        if lifecycle not in profile_lifecycle["statuses"]:
            errors.append(
                f"contracts/developer-integration-profiles.yaml: {profile_name} lifecycle {lifecycle!r} is not declared in profile_lifecycle.statuses"
            )
        if payload["owner_repo"] not in active_repos:
            errors.append(
                f"contracts/developer-integration-profiles.yaml: {profile_name} owner_repo {payload['owner_repo']!r} is not active"
            )
        for key in ("runtime_owner", "security_owner"):
            if payload[key] not in active_repos:
                errors.append(
                    f"contracts/developer-integration-profiles.yaml: {profile_name} {key} {payload[key]!r} is not active"
                )
        for repo_ref in payload["shared_dependencies"] + payload["source_repos"]:
            if repo_ref not in active_repos:
                errors.append(
                    f"contracts/developer-integration-profiles.yaml: {profile_name} references unknown repo {repo_ref!r}"
                )
        stage_owner = payload["stage_handoff"]["owner_repo"]
        if stage_owner not in active_repos:
            errors.append(
                f"contracts/developer-integration-profiles.yaml: {profile_name} stage_handoff owner_repo {stage_owner!r} is not active"
            )
        registry_required_checks = payload["stage_handoff"].get("required_checks") or []
        if not registry_required_checks:
            errors.append(
                f"contracts/developer-integration-profiles.yaml: {profile_name} stage_handoff.required_checks must not be empty"
            )
        elif len(registry_required_checks) != len(set(registry_required_checks)):
            errors.append(
                f"contracts/developer-integration-profiles.yaml: {profile_name} stage_handoff.required_checks must be unique"
            )
        if set(payload["actions"]) != required_actions:
            errors.append(
                f"contracts/developer-integration-profiles.yaml: {profile_name} actions must match required_actions"
            )
        request_record = payload.get("request_record") or {}
        if profile_lifecycle["request_record_required"]:
            for key in ("system", "ref"):
                if not request_record.get(key):
                    errors.append(
                        f"contracts/developer-integration-profiles.yaml: {profile_name} is missing request_record.{key}"
                    )
        admission = payload.get("admission") or {}
        if lifecycle in set(profile_lifecycle["platform_acceptance_required_for"]):
            for key in ("approved_by", "approved_on", "platform_acceptance_ref"):
                if not admission.get(key):
                    errors.append(
                        f"contracts/developer-integration-profiles.yaml: {profile_name} lifecycle {lifecycle!r} requires admission.{key}"
                    )
        if admission.get("security_review_required"):
            refs = admission.get("security_review_refs") or []
            if not refs and profile_lifecycle["security_review_ref_required_when_flagged"]:
                errors.append(
                    f"contracts/developer-integration-profiles.yaml: {profile_name} requires at least one admission.security_review_ref"
                )
            for ref in refs:
                review_repo = ref["repo"]
                if review_repo not in active_repos:
                    errors.append(
                        f"contracts/developer-integration-profiles.yaml: {profile_name} security review repo {review_repo!r} is not active"
                    )
                review_path = workspace_root / review_repo / ref["path"]
                if not review_path.exists():
                    errors.append(
                        f"contracts/developer-integration-profiles.yaml: {profile_name} security review path missing: {review_path}"
                    )

        profile_path = workspace_root / payload["owner_repo"] / payload["profile_path"]
        if not profile_path.exists():
            errors.append(
                f"contracts/developer-integration-profiles.yaml: {profile_name} profile path missing: {profile_path}"
            )
            continue

        profile = load_yaml(profile_path)
        missing_keys = sorted(REQUIRED_PROFILE_KEYS - set(profile))
        if missing_keys:
            errors.append(
                f"{profile_path}: missing required keys {', '.join(missing_keys)}"
            )
            continue
        if profile["profile_id"] != profile_name:
            errors.append(
                f"{profile_path}: profile_id {profile['profile_id']!r} must match registry name {profile_name!r}"
            )
        profile_stage_handoff = profile.get("stage_handoff") or {}
        for key in ("owner_repo", "governed_surface"):
            if profile_stage_handoff.get(key) != payload["stage_handoff"][key]:
                errors.append(
                    f"{profile_path}: stage_handoff.{key} must match contracts/developer-integration-profiles.yaml"
                )
        profile_required_checks = profile_stage_handoff.get("required_checks") or []
        if not profile_required_checks:
            errors.append(f"{profile_path}: stage_handoff.required_checks must not be empty")
        elif len(profile_required_checks) != len(set(profile_required_checks)):
            errors.append(f"{profile_path}: stage_handoff.required_checks must be unique")
        if profile_required_checks != registry_required_checks:
            errors.append(
                f"{profile_path}: stage_handoff.required_checks must match contracts/developer-integration-profiles.yaml"
            )
        source_repos = {
            entry["repo"] if isinstance(entry, dict) else entry
            for entry in profile["source_repos"]
        }
        if source_repos != set(payload["source_repos"]):
            errors.append(
                f"{profile_path}: source_repos must match contracts/developer-integration-profiles.yaml"
            )
        if set(profile["commands"].keys()) != required_actions:
            errors.append(
                f"{profile_path}: commands must define exactly {', '.join(sorted(required_actions))}"
            )
        for action, rel_path in profile["commands"].items():
            command_path = workspace_root / payload["owner_repo"] / rel_path
            if not command_path.exists():
                errors.append(
                    f"{profile_path}: command path missing for {action}: {command_path}"
                )
        readme_path = profile_path.parent / "README.md"
        if not readme_path.exists():
            errors.append(f"{profile_path}: missing profile README: {readme_path}")
        else:
            readme_text = load_text(readme_path)
            if "## Stage Handoff Checks" not in readme_text:
                errors.append(
                    f"{readme_path}: missing '## Stage Handoff Checks' heading for profile-owned governed checks"
                )
            for check_name in profile_required_checks:
                if check_name not in readme_text:
                    errors.append(
                        f"{readme_path}: stage handoff check {check_name!r} must be documented"
                    )
        if lifecycle not in profile_lifecycle["self_serve_statuses"]:
            continue

    if not checked_profiles:
        errors.append("contracts/developer-integration-profiles.yaml: at least one profile is required")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate developer-integration lane contracts and registered profile files."
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
        help="workspace root containing active repos",
    )
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    workspace_root = args.workspace_root.resolve()
    errors = validate(repo_root, workspace_root)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    checked = len(load_contracts(repo_root)["developer_integration_profiles"]["profiles"])
    print(f"developer-integration profiles valid: checked={checked}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
