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
    "testing",
    "source_repos",
    "commands",
    "session",
    "stage_handoff",
}
REQUIRED_RUNTIME_STATE_MODELS = {"disposable", "persistent"}
REQUIRED_PERSISTENT_REQUEST_REQUIREMENTS = {
    "runtime.state_model",
    "testing.smoke.mutation_mode",
    "persistence.justification",
    "persistence.retained_data_scope",
    "persistence.suspend_resume_semantics",
    "persistence.storage_size_or_class",
    "persistence.reset_semantics",
    "persistence.cutover_plan_when_upgrading",
}
REQUIRED_LIVE_MISS_KEYS = {
    "owner_repo",
    "purpose",
    "return_to_dev_integration_when",
    "route_to_platform_or_backend_boundary_when",
    "governed_rehearsal_allowed_when",
    "required_record_fields",
}
REQUIRED_LIVE_MISS_RECORD_FIELDS = {
    "failed_operation",
    "lane_where_seen",
    "local_profile_evidence",
    "live_boundary_evidence",
    "selected_route",
    "owner_repo",
    "follow_up_record",
}
REQUIRED_RUNTIME_LANE_DECISION_KEYS = {
    "required_for_new_repos",
    "decisions",
    "component_inventory_required_repo_classes",
    "dev_integration_required_repo_classes",
    "waiver_decisions",
    "waivers",
}
REQUIRED_RUNTIME_LANE_DECISIONS = {
    "no-runtime",
    "local-only",
    "dev-integration-required",
    "stage-direct",
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
    intake_policy = contracts["intake_policy"]
    governance_validator_catalog = contracts["governance_validator_catalog"][
        "governance_validator_catalog"
    ]

    required_actions = set(policy["required_actions"])
    profile_lifecycle = policy["profile_lifecycle"]
    request_admission = policy["request_admission"]
    testing_policy = policy["testing"]["smoke"]
    live_miss_escalation = policy.get("live_miss_escalation") or {}
    runtime_lane_decision = policy.get("runtime_lane_decision") or {}
    validation_behavior_policy = intake_policy["validation_behavior"]
    catalog_entries = set(governance_validator_catalog["entries"])
    allowed_validation_postures = set(validation_behavior_policy["allowed_postures"])
    allowed_validation_graph_roles = set(validation_behavior_policy["allowed_graph_roles"])
    direct_invocation_postures = set(validation_behavior_policy["direct_invocation_postures"])

    def validate_validation_behavior(label: str, payload: dict, *, required: bool) -> None:
        behavior = payload.get("validation_behavior")
        if behavior is None:
            if required:
                errors.append(f"{label}: missing validation_behavior")
            return
        posture = behavior.get("posture")
        graph_role = behavior.get("wgcf_graph_role")
        catalog_refs = behavior.get("catalog_refs") or []
        if posture not in allowed_validation_postures:
            errors.append(f"{label}: validation_behavior.posture {posture!r} is not allowed")
        if graph_role not in allowed_validation_graph_roles:
            errors.append(
                f"{label}: validation_behavior.wgcf_graph_role {graph_role!r} is not allowed"
            )
        unknown_catalog_refs = sorted(set(catalog_refs) - catalog_entries)
        if unknown_catalog_refs:
            errors.append(
                f"{label}: validation_behavior.catalog_refs references unknown catalog entries "
                + ", ".join(unknown_catalog_refs)
            )
        if (
            validation_behavior_policy["require_catalog_refs_for_direct_invocation"]
            and posture in direct_invocation_postures
            and not catalog_refs
        ):
            errors.append(
                f"{label}: validation_behavior.posture {posture!r} requires at least one catalog_ref"
            )

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
    runtime_state_models = set(policy.get("runtime_state_models") or [])
    if runtime_state_models != REQUIRED_RUNTIME_STATE_MODELS:
        errors.append(
            "contracts/developer-integration-policy.yaml: runtime_state_models must be exactly disposable, persistent"
        )
    persistent_request_requirements = set(
        request_admission.get("persistent_request_requirements") or []
    )
    if persistent_request_requirements != REQUIRED_PERSISTENT_REQUEST_REQUIREMENTS:
        errors.append(
            "contracts/developer-integration-policy.yaml: request_admission.persistent_request_requirements must be exactly "
            + ", ".join(sorted(REQUIRED_PERSISTENT_REQUEST_REQUIREMENTS))
        )
    adapter_owner = request_admission["current_request_adapter"]["owner_repo"]
    if adapter_owner not in active_repos:
        errors.append(
            "contracts/developer-integration-policy.yaml: current_request_adapter.owner_repo must reference an active repo"
        )
    missing_live_miss_keys = sorted(REQUIRED_LIVE_MISS_KEYS - set(live_miss_escalation))
    if missing_live_miss_keys:
        errors.append(
            "contracts/developer-integration-policy.yaml: live_miss_escalation missing keys "
            + ", ".join(missing_live_miss_keys)
        )
    elif live_miss_escalation["owner_repo"] not in active_repos:
        errors.append(
            "contracts/developer-integration-policy.yaml: live_miss_escalation.owner_repo must reference an active repo"
        )
    else:
        for key in (
            "return_to_dev_integration_when",
            "route_to_platform_or_backend_boundary_when",
            "governed_rehearsal_allowed_when",
        ):
            if not isinstance(live_miss_escalation.get(key), list) or not live_miss_escalation[key]:
                errors.append(
                    f"contracts/developer-integration-policy.yaml: live_miss_escalation.{key} must be a non-empty list"
                )
        record_fields = set(live_miss_escalation.get("required_record_fields") or [])
        if record_fields != REQUIRED_LIVE_MISS_RECORD_FIELDS:
            errors.append(
                "contracts/developer-integration-policy.yaml: live_miss_escalation.required_record_fields must be exactly "
                + ", ".join(sorted(REQUIRED_LIVE_MISS_RECORD_FIELDS))
            )
    missing_runtime_lane_keys = sorted(
        REQUIRED_RUNTIME_LANE_DECISION_KEYS - set(runtime_lane_decision)
    )
    if missing_runtime_lane_keys:
        errors.append(
            "contracts/developer-integration-policy.yaml: runtime_lane_decision missing keys "
            + ", ".join(missing_runtime_lane_keys)
        )
    else:
        if runtime_lane_decision["required_for_new_repos"] is not True:
            errors.append(
                "contracts/developer-integration-policy.yaml: runtime_lane_decision.required_for_new_repos must be true"
            )
        decisions = set(runtime_lane_decision.get("decisions") or [])
        if decisions != REQUIRED_RUNTIME_LANE_DECISIONS:
            errors.append(
                "contracts/developer-integration-policy.yaml: runtime_lane_decision.decisions must be exactly "
                + ", ".join(sorted(REQUIRED_RUNTIME_LANE_DECISIONS))
            )
        waiver_decisions = set(runtime_lane_decision.get("waiver_decisions") or [])
        if not waiver_decisions or not waiver_decisions.issubset(decisions):
            errors.append(
                "contracts/developer-integration-policy.yaml: runtime_lane_decision.waiver_decisions must be a non-empty subset of decisions"
            )
        for class_key in (
            "component_inventory_required_repo_classes",
            "dev_integration_required_repo_classes",
        ):
            if not runtime_lane_decision.get(class_key):
                errors.append(
                    f"contracts/developer-integration-policy.yaml: runtime_lane_decision.{class_key} must not be empty"
                )
        for waiver in runtime_lane_decision.get("waivers") or []:
            waiver_repo = waiver.get("repo")
            waiver_decision = waiver.get("decision")
            if waiver_repo not in active_repos:
                errors.append(
                    f"contracts/developer-integration-policy.yaml: runtime lane waiver references unknown repo {waiver_repo!r}"
                )
            if waiver_decision not in waiver_decisions:
                errors.append(
                    f"contracts/developer-integration-policy.yaml: runtime lane waiver for {waiver_repo!r} uses unsupported decision {waiver_decision!r}"
                )
    allowed_smoke_mutation_modes = set(testing_policy["allowed_mutation_modes"])
    persistent_smoke_mutation_mode = testing_policy["persistent_profile_rule"][
        "mutation_mode_must_be"
    ]

    checked_profiles = 0
    profile_testing: dict[str, dict[str, str | None]] = {}
    for profile_name, payload in sorted(registry["profiles"].items()):
        checked_profiles += 1
        lifecycle = payload["lifecycle"]
        if lifecycle not in profile_lifecycle["statuses"]:
            errors.append(
                f"contracts/developer-integration-profiles.yaml: {profile_name} lifecycle {lifecycle!r} is not declared in profile_lifecycle.statuses"
            )
        validate_validation_behavior(
            f"contracts/developer-integration-profiles.yaml: {profile_name}",
            payload,
            required=validation_behavior_policy["runtime_profiles"]["require_for_registered"],
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
        profile_actions = set(payload["actions"])
        missing_registry_actions = sorted(required_actions - profile_actions)
        if missing_registry_actions:
            errors.append(
                f"contracts/developer-integration-profiles.yaml: {profile_name} actions must include required_actions; missing {', '.join(missing_registry_actions)}"
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
        runtime = profile.get("runtime") or {}
        state_model = runtime.get("state_model")
        if state_model not in runtime_state_models:
            errors.append(
                f"{profile_path}: runtime.state_model must be one of {', '.join(sorted(runtime_state_models))}"
            )
        testing = profile.get("testing") or {}
        smoke_testing = testing.get("smoke") or {}
        mutation_mode = smoke_testing.get("mutation_mode")
        companion_profile_id = smoke_testing.get("companion_profile_id")
        if mutation_mode not in allowed_smoke_mutation_modes:
            errors.append(
                f"{profile_path}: testing.smoke.mutation_mode must be one of "
                + ", ".join(sorted(allowed_smoke_mutation_modes))
            )
        if state_model == "persistent" and mutation_mode != persistent_smoke_mutation_mode:
            errors.append(
                f"{profile_path}: persistent profiles must declare testing.smoke.mutation_mode={persistent_smoke_mutation_mode!r}"
            )
        profile_testing[profile_name] = {
            "state_model": state_model,
            "mutation_mode": mutation_mode,
            "companion_profile_id": companion_profile_id,
        }
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
        command_actions = set(profile["commands"].keys())
        missing_command_actions = sorted(required_actions - command_actions)
        if missing_command_actions:
            errors.append(
                f"{profile_path}: commands must include required actions {', '.join(sorted(required_actions))}; missing {', '.join(missing_command_actions)}"
            )
        if command_actions != profile_actions:
            errors.append(
                f"{profile_path}: commands keys must match contracts/developer-integration-profiles.yaml actions"
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

    if not missing_runtime_lane_keys:
        repo_contracts = contracts["repos"]["repos"]
        component_required_classes = set(
            runtime_lane_decision.get("component_inventory_required_repo_classes") or []
        )
        devint_required_classes = set(
            runtime_lane_decision.get("dev_integration_required_repo_classes") or []
        )
        component_owner_repos = {
            payload["owner_repo"]
            for payload in contracts["components"]["components"].values()
            if payload.get("lifecycle") == "active"
        }
        profile_owner_repos = {
            payload["owner_repo"]
            for payload in registry["profiles"].values()
            if payload.get("lifecycle") in profile_lifecycle["statuses"]
        }
        waiver_repos = {
            waiver["repo"]
            for waiver in runtime_lane_decision.get("waivers") or []
            if waiver.get("repo")
        }
        for repo_name, repo_payload in sorted(repo_contracts.items()):
            repo_class = repo_payload.get("repo_class")
            if (
                repo_class in component_required_classes
                and repo_name not in component_owner_repos
            ):
                errors.append(
                    "contracts/components.yaml: active repo "
                    f"{repo_name!r} with repo_class {repo_class!r} must have an active component inventory entry"
                )
            if (
                repo_class in devint_required_classes
                and repo_name not in profile_owner_repos
                and repo_name not in waiver_repos
            ):
                errors.append(
                    "contracts/developer-integration-profiles.yaml: active repo "
                    f"{repo_name!r} with repo_class {repo_class!r} must have a proposed, active, suspended, or retired dev-integration profile entry or a runtime-lane waiver"
                )

    if not checked_profiles:
        errors.append("contracts/developer-integration-profiles.yaml: at least one profile is required")

    for profile_name, testing in sorted(profile_testing.items()):
        companion_profile_id = testing["companion_profile_id"]
        if not companion_profile_id:
            continue
        if companion_profile_id == profile_name:
            errors.append(
                f"contracts/developer-integration-profiles.yaml: {profile_name} testing.smoke.companion_profile_id must not point to itself"
            )
            continue
        companion_testing = profile_testing.get(companion_profile_id)
        if companion_testing is None:
            errors.append(
                f"contracts/developer-integration-profiles.yaml: {profile_name} testing.smoke.companion_profile_id {companion_profile_id!r} is not a registered profile"
            )
            continue
        if testing["state_model"] != "persistent":
            errors.append(
                f"contracts/developer-integration-profiles.yaml: {profile_name} testing.smoke.companion_profile_id is only allowed on persistent profiles"
            )
        if companion_testing["state_model"] != "disposable":
            errors.append(
                f"contracts/developer-integration-profiles.yaml: {profile_name} companion profile {companion_profile_id!r} must be disposable"
            )
        if companion_testing["mutation_mode"] != "mutating":
            errors.append(
                f"contracts/developer-integration-profiles.yaml: {profile_name} companion profile {companion_profile_id!r} must declare testing.smoke.mutation_mode='mutating'"
            )

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
