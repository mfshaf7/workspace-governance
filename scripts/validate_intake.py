#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

from contracts_lib import active_repo_names, load_contracts, load_yaml, retired_repo_names


def ref_path(workspace_root: Path, ref: dict) -> Path:
    return workspace_root / str(ref.get("repo", "")) / str(ref.get("path", ""))


def ref_value(ref: dict) -> str:
    return f"{ref.get('repo')}/{ref.get('path')}"


def refs_match(left: dict, right: dict) -> bool:
    return left.get("repo") == right.get("repo") and left.get("path") == right.get("path")


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


def load_governed_intake_assist_contract(
    workspace_root: Path,
    intake_policy: dict,
    errors: list[str],
) -> dict:
    ai_policy = intake_policy.get("ai_suggestions") or {}
    contract_ref = ai_policy.get("governed_intake_assist_contract") or {}
    repo = contract_ref.get("repo")
    rel_path = contract_ref.get("path")
    if not isinstance(repo, str) or not repo or not isinstance(rel_path, str) or not rel_path:
        errors.append("contracts/intake-policy.yaml: ai_suggestions.governed_intake_assist_contract must define repo and path")
        return {}
    contract_path = workspace_root / repo / rel_path
    if not contract_path.exists():
        errors.append(
            f"contracts/intake-policy.yaml: governed intake-assist contract is missing: {repo}/{rel_path}"
        )
        return {}
    payload = load_yaml(contract_path)
    contract = payload.get("governed_intake_assist")
    if not isinstance(contract, dict):
        errors.append(
            f"{repo}/{rel_path}: governed_intake_assist must be a mapping for governed intake validation"
        )
        return {}
    return contract


def load_ref_yaml(workspace_root: Path, ref: dict, errors: list[str], *, context: str) -> dict:
    repo = ref.get("repo")
    rel_path = ref.get("path")
    if not isinstance(repo, str) or not repo or not isinstance(rel_path, str) or not rel_path:
        errors.append(f"{context}: reference must define repo and path")
        return {}
    path = workspace_root / repo / rel_path
    if not path.exists():
        errors.append(f"{context}: referenced path is missing: {repo}/{rel_path}")
        return {}
    payload = load_yaml(path)
    if not isinstance(payload, dict):
        errors.append(f"{context}: referenced YAML must be a mapping: {repo}/{rel_path}")
        return {}
    return payload


def validate_governed_intake_assist_contract(
    *,
    workspace_root: Path,
    repo_root: Path,
    intake_policy: dict,
    contract: dict,
    profiles: dict[str, dict],
    errors: list[str],
) -> None:
    if not contract:
        return

    label = "contracts/governed-intake-assist.yaml"
    consumer = contract.get("consumer") or {}
    suggestion_contract = contract.get("suggestion_contract") or {}
    operator_acceptance = contract.get("operator_acceptance") or {}
    workspace_truth_updates = contract.get("workspace_truth_updates") or {}
    activation_state = contract.get("activation_state") or {}
    contract_refs = contract.get("platform_contract_refs") or {}

    primary_surface = repo_root / contract.get("primary_operator_surface", "")
    if not primary_surface.exists():
        errors.append(f"{label}: primary operator surface is missing: {contract.get('primary_operator_surface')!r}")

    profile_id = consumer.get("profile_id")
    profile = profiles.get(profile_id)
    if not isinstance(profile, dict):
        errors.append(f"{label}: consumer.profile_id {profile_id!r} is not present in the governed profile registry")
        profile = {}

    if consumer.get("purpose") not in set(intake_policy["ai_suggestions"]["required_purposes"]):
        errors.append(f"{label}: consumer.purpose must be allowed by intake-policy required_purposes")
    if consumer.get("caller_id") not in profile.get("allowed_callers", []):
        errors.append(f"{label}: consumer.caller_id must be allowed by the governed profile")
    if consumer.get("invocation_path") != profile.get("invocation_path"):
        errors.append(f"{label}: consumer.invocation_path must match the governed profile invocation_path")
    if not refs_match(
        consumer.get("provider_output_schema_ref") or {},
        profile.get("provider_output_schema_ref") or {},
    ):
        errors.append(
            f"{label}: consumer.provider_output_schema_ref must match the governed profile provider_output_schema_ref"
        )
    if not refs_match(
        consumer.get("accepted_record_schema_ref") or {},
        profile.get("accepted_record_schema_ref") or {},
    ):
        errors.append(
            f"{label}: consumer.accepted_record_schema_ref must match the governed profile accepted_record_schema_ref"
        )
    if set(consumer.get("allowed_data_scope") or []) != set(profile.get("allowed_data_scope") or []):
        errors.append(f"{label}: consumer.allowed_data_scope must match the governed profile allowed_data_scope")
    if profile.get("direct_provider_access_allowed") is not False:
        errors.append(f"{label}: governed profile must keep direct_provider_access_allowed=false")
    if profile.get("human_approval_required") is not True:
        errors.append(f"{label}: governed profile must require human approval")

    profile_registry_ref = contract_refs.get("profile_registry") or {}
    if not refs_match(profile_registry_ref, intake_policy["ai_suggestions"]["governed_profile_registry"]):
        errors.append(f"{label}: platform_contract_refs.profile_registry must match intake-policy governed_profile_registry")

    access_plane_payload = load_ref_yaml(
        workspace_root,
        contract_refs.get("access_plane") or {},
        errors,
        context=f"{label}: platform_contract_refs.access_plane",
    )
    access_plane = access_plane_payload.get("access_plane") or {}
    if access_plane:
        if access_plane.get("id") != consumer.get("invocation_path"):
            errors.append(f"{label}: consumer.invocation_path must match access_plane.id")
        if consumer.get("profile_id") not in access_plane.get("allowed_profiles", []):
            errors.append(f"{label}: consumer.profile_id must be allowed by the access plane")
        matching_callers = [
            caller
            for caller in access_plane.get("allowed_callers", [])
            if caller.get("caller_id") == consumer.get("caller_id")
        ]
        if not matching_callers:
            errors.append(f"{label}: consumer.caller_id must be allowlisted by the access plane")
        else:
            caller = matching_callers[0]
            if caller.get("purpose") != consumer.get("purpose"):
                errors.append(f"{label}: access-plane caller purpose must match the consumer purpose")
            if caller.get("required_profile") != consumer.get("profile_id"):
                errors.append(f"{label}: access-plane caller required_profile must match the consumer profile")
            if not refs_match(
                caller.get("required_provider_output_schema_ref") or {},
                consumer.get("provider_output_schema_ref") or {},
            ):
                errors.append(
                    f"{label}: access-plane caller provider output schema must match the consumer provider output schema"
                )
            if not refs_match(
                caller.get("accepted_record_schema_ref") or {},
                consumer.get("accepted_record_schema_ref") or {},
            ):
                errors.append(
                    f"{label}: access-plane caller accepted record schema must match the consumer accepted record schema"
                )
        admission_policy = access_plane.get("admission_policy") or {}
        if admission_policy.get("direct_provider_passthrough_allowed") is not False:
            errors.append(f"{label}: access plane must deny direct provider passthrough")
        if admission_policy.get("require_human_approval_for_governance_decisions") is not True:
            errors.append(f"{label}: access plane must require human approval for governance decisions")
        access_plane_activation = access_plane.get("activation_state") or {}
        if (
            access_plane_activation.get("profile_activation_allowed") is False
            and activation_state.get("live_consumption_allowed") is not False
        ):
            errors.append(f"{label}: live consumption cannot be allowed while the platform access plane blocks activation")
        if (
            activation_state.get("live_consumption_allowed") is True
            and (
                access_plane.get("status") != "active"
                or access_plane_activation.get("profile_activation_allowed") is not True
            )
        ):
            errors.append(f"{label}: live consumption requires an active platform access plane")

    runtime_contract_payload = load_ref_yaml(
        workspace_root,
        contract_refs.get("runtime_assist_contract") or {},
        errors,
        context=f"{label}: platform_contract_refs.runtime_assist_contract",
    )
    runtime_contract = runtime_contract_payload.get("contract") or {}
    if runtime_contract:
        if consumer.get("profile_id") not in runtime_contract.get("model_profiles", []):
            errors.append(f"{label}: consumer.profile_id must be listed in the platform runtime-assist contract")
        allowed_callers = (runtime_contract.get("consumers") or {}).get("allowed_callers", [])
        if consumer.get("caller_id") not in allowed_callers:
            errors.append(f"{label}: consumer.caller_id must be allowed by the platform runtime-assist contract")
        invocation_boundary = runtime_contract.get("invocation_boundary") or {}
        if invocation_boundary.get("required_path") != consumer.get("invocation_path"):
            errors.append(f"{label}: consumer.invocation_path must match the runtime-assist invocation boundary")
        if invocation_boundary.get("direct_provider_access_allowed") is not False:
            errors.append(f"{label}: runtime-assist contract must deny direct provider access")
        approval_boundary = runtime_contract.get("approval_boundary") or {}
        if approval_boundary.get("human_approval_required") is not True:
            errors.append(f"{label}: runtime-assist contract must require human approval")
        if approval_boundary.get("model_output_mutates_canonical_state") is not False:
            errors.append(f"{label}: runtime-assist contract must keep model_output_mutates_canonical_state=false")
        runtime_audit_fields = set((runtime_contract.get("audit_minimum") or {}).get("required_fields") or [])
        contract_audit_fields = set((contract.get("audit_contract") or {}).get("required_fields") or [])
        if contract_audit_fields != runtime_audit_fields:
            errors.append(f"{label}: audit_contract.required_fields must match the runtime-assist audit minimum")
        if (
            runtime_contract.get("status") == "blocked"
            and activation_state.get("live_consumption_allowed") is not False
        ):
            errors.append(f"{label}: live consumption cannot be allowed while the runtime-assist contract is blocked")
        if (
            activation_state.get("live_consumption_allowed") is True
            and runtime_contract.get("status") != "active"
        ):
            errors.append(f"{label}: live consumption requires an active runtime-assist contract")

    security_review_ref = contract_refs.get("security_review") or {}
    security_review_path = ref_path(workspace_root, security_review_ref) if security_review_ref else None
    if security_review_path and not security_review_path.exists():
        errors.append(f"{label}: security review reference is missing: {ref_value(security_review_ref)}")

    required_live_gates = set(activation_state.get("required_live_gates") or [])
    gate_evidence = activation_state.get("gate_evidence") or {}
    if set(gate_evidence) != required_live_gates:
        errors.append(f"{label}: activation_state.gate_evidence must cover every required live gate exactly")
    for gate_id, refs in gate_evidence.items():
        if not isinstance(refs, list) or not refs or not all(isinstance(ref, str) and ref for ref in refs):
            errors.append(f"{label}: activation_state.gate_evidence.{gate_id} must contain evidence references")
    if activation_state.get("live_consumption_allowed") is True:
        if activation_state.get("source_contract_status") != "active":
            errors.append(f"{label}: active live consumption requires source_contract_status active")
        if profile.get("status") != intake_policy["ai_suggestions"]["required_profile_status"]:
            errors.append(f"{label}: live consumption requires the governed profile to be active")

    expected_decisions = set(intake_policy["statuses"])
    if set(suggestion_contract.get("allowed_decisions") or []) != expected_decisions:
        errors.append(f"{label}: suggestion_contract.allowed_decisions must match intake-policy statuses")
    if suggestion_contract.get("authority") != "suggestion-only":
        errors.append(f"{label}: suggestion_contract.authority must be suggestion-only")
    if suggestion_contract.get("autonomous_mutation_allowed") is not False:
        errors.append(f"{label}: suggestion_contract.autonomous_mutation_allowed must be false")
    for field in (
        "provider_output_schema_ref",
        "suggestion_candidate_schema_ref",
        "accepted_record_schema_ref",
    ):
        if not refs_match(suggestion_contract.get(field) or {}, consumer.get(field) or {}):
            errors.append(f"{label}: suggestion_contract.{field} must match consumer.{field}")

    if operator_acceptance.get("human_approval_required") is not True:
        errors.append(f"{label}: operator_acceptance.human_approval_required must be true")
    if operator_acceptance.get("acceptance_required_before_workspace_truth_update") is not True:
        errors.append(f"{label}: operator_acceptance.acceptance_required_before_workspace_truth_update must be true")
    if set(operator_acceptance.get("allowed_acceptance_states_for_truth_update") or []) != {"accepted", "overridden"}:
        errors.append(f"{label}: operator_acceptance must only allow accepted or overridden suggestions into workspace truth")
    if operator_acceptance.get("override_requires_reason") is not True:
        errors.append(f"{label}: operator_acceptance.override_requires_reason must be true")

    if set(workspace_truth_updates.get("allowed_targets") or []) != {"contracts/intake-register.yaml"}:
        errors.append(f"{label}: workspace_truth_updates.allowed_targets must be contracts/intake-register.yaml")
    if set(workspace_truth_updates.get("allowed_decision_sources") or []) != {"operator", "ai-suggested"}:
        errors.append(f"{label}: workspace_truth_updates.allowed_decision_sources must be operator and ai-suggested")
    if workspace_truth_updates.get("ai_suggested_requires_active_profile") is not True:
        errors.append(f"{label}: workspace_truth_updates.ai_suggested_requires_active_profile must be true")
    if workspace_truth_updates.get("ai_suggested_requires_operator_acceptance") is not True:
        errors.append(f"{label}: workspace_truth_updates.ai_suggested_requires_operator_acceptance must be true")


def validate_ai_suggestion(
    *,
    label: str,
    payload: dict,
    intake_policy: dict,
    governed_contract: dict,
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

    if (governed_contract.get("activation_state") or {}).get("live_consumption_allowed") is not True:
        errors.append(
            f"{label}: decision_source ai-suggested is not allowed while governed intake-assist live_consumption_allowed is false"
        )

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

    consumer = governed_contract.get("consumer") or {}
    operator_acceptance = governed_contract.get("operator_acceptance") or {}
    if ai_suggestion.get("caller_id") != consumer.get("caller_id"):
        errors.append(f"{label}: ai_suggestion.caller_id must match governed intake-assist consumer.caller_id")
    if ai_suggestion.get("invocation_path") != consumer.get("invocation_path"):
        errors.append(f"{label}: ai_suggestion.invocation_path must match governed intake-assist consumer.invocation_path")
    if ai_suggestion.get("profile_id") != consumer.get("profile_id"):
        errors.append(f"{label}: ai_suggestion.profile_id must match governed intake-assist consumer.profile_id")

    allowed_decisions = set(intake_policy["statuses"])
    suggested_decision = ai_suggestion.get("suggested_decision")
    operator_decision = ai_suggestion.get("operator_decision")
    if suggested_decision not in allowed_decisions:
        errors.append(f"{label}: ai_suggestion.suggested_decision must be one of intake-policy statuses")
    if operator_decision not in allowed_decisions:
        errors.append(f"{label}: ai_suggestion.operator_decision must be one of intake-policy statuses")
    if operator_decision != payload.get("status"):
        errors.append(f"{label}: ai_suggestion.operator_decision must match the recorded intake status")

    acceptance_state = ai_suggestion.get("acceptance_state")
    allowed_acceptance_states = set(operator_acceptance.get("allowed_acceptance_states_for_truth_update") or [])
    if acceptance_state not in allowed_acceptance_states:
        errors.append(
            f"{label}: ai_suggestion.acceptance_state must be one of the governed truth-update acceptance states"
        )
    if acceptance_state == "accepted" and suggested_decision != operator_decision:
        errors.append(f"{label}: accepted AI suggestions must keep suggested_decision equal to operator_decision")
    if acceptance_state == "overridden":
        if suggested_decision == operator_decision:
            errors.append(f"{label}: overridden AI suggestions must change the suggested decision")
        if operator_acceptance.get("override_requires_reason") and not ai_suggestion.get("override_reason"):
            errors.append(f"{label}: overridden AI suggestions require ai_suggestion.override_reason")
    if intake_policy["ai_suggestions"]["require_human_approval"]:
        for required_field in ("accepted_by", "accepted_at", "audit_ref", "decision_id"):
            if not ai_suggestion.get(required_field):
                errors.append(f"{label}: ai_suggestion.{required_field} is required for operator acceptance")


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
    parser.add_argument(
        "--repo-root",
        type=Path,
        help="workspace-governance checkout to validate; defaults to <workspace-root>/workspace-governance",
    )
    args = parser.parse_args()

    workspace_root = args.workspace_root.resolve()
    repo_root = (
        args.repo_root.resolve()
        if args.repo_root is not None
        else workspace_root / "workspace-governance"
    )
    contracts = load_contracts(repo_root)
    intake_policy = contracts["intake_policy"]
    intake_register = contracts["intake_register"]
    workspace_intake = contracts["workspace_intake"]
    governance_validator_catalog = contracts["governance_validator_catalog"][
        "governance_validator_catalog"
    ]

    errors: list[str] = []

    if intake_policy.get("contract_ref") != {
        "repo": "workspace-governance",
        "path": "contracts/workspace-intake.yaml",
        "schema_version": workspace_intake.get("schema_version"),
    }:
        errors.append(
            "contracts/intake-policy.yaml: contract_ref must bind contracts/workspace-intake.yaml at its exact schema version"
        )

    active_repos = set(active_repo_names(contracts))
    retired_repos = set(retired_repo_names(contracts))
    intake_repos = set(intake_register["repos"].keys())
    allowed_workspace_repos = active_repos | retired_repos | intake_repos
    in_scope_statuses = {"proposed", "admitted"}
    validation_behavior_policy = intake_policy["validation_behavior"]
    catalog_entries = set(governance_validator_catalog["entries"])
    allowed_validation_postures = set(validation_behavior_policy["allowed_postures"])
    allowed_validation_graph_roles = set(validation_behavior_policy["allowed_graph_roles"])
    allowed_validation_graph_roles_by_posture = {
        posture: set(graph_roles)
        for posture, graph_roles in validation_behavior_policy[
            "allowed_graph_roles_by_posture"
        ].items()
    }
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
        posture_graph_roles = allowed_validation_graph_roles_by_posture.get(posture)
        if posture_graph_roles is not None and graph_role not in posture_graph_roles:
            errors.append(
                f"{label}: {posture} posture must use one of these graph roles: "
                + ", ".join(sorted(posture_graph_roles))
            )

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
    governed_intake_assist: dict = {}
    if intake_policy["ai_suggestions"]["enabled"]:
        profiles = load_governed_profiles(workspace_root, intake_policy, errors)
        governed_intake_assist = load_governed_intake_assist_contract(
            workspace_root,
            intake_policy,
            errors,
        )
        validate_governed_intake_assist_contract(
            workspace_root=workspace_root,
            repo_root=repo_root,
            intake_policy=intake_policy,
            contract=governed_intake_assist,
            profiles=profiles,
            errors=errors,
        )

    ai_decision_owners: dict[str, str] = {}
    idempotency_owners: dict[str, str] = {}
    allowed_source_classes = set(workspace_intake["vocabulary"]["source_classes"])
    for collection_name in ("repos", "products", "components"):
        for entry_name, payload in intake_register[collection_name].items():
            label = f"contracts/intake-register.yaml: {collection_name[:-1]} {entry_name}"
            expected_record_id = f"{collection_name[:-1]}:{entry_name}"
            record = payload.get("record") or {}
            if record.get("id") != expected_record_id:
                errors.append(
                    f"{label}: record.id must be {expected_record_id!r}"
                )
            source = record.get("source") or {}
            if source.get("class") not in allowed_source_classes:
                errors.append(
                    f"{label}: record.source.class {source.get('class')!r} is not allowed"
                )
            decision = record.get("decision") or {}
            if decision.get("source") != payload.get("decision_source"):
                errors.append(
                    f"{label}: record.decision.source must match decision_source"
                )
            mutation = record.get("last_mutation") or {}
            idempotency_key = mutation.get("idempotency_key")
            if idempotency_key:
                if idempotency_key in idempotency_owners:
                    errors.append(
                        f"{label}: record.last_mutation.idempotency_key {idempotency_key!r} is already used by {idempotency_owners[idempotency_key]}"
                    )
                else:
                    idempotency_owners[idempotency_key] = label
            if collection_name in {"repos", "products", "components"}:
                scope_policy = validation_behavior_policy[collection_name]
                validate_validation_behavior(
                    label=label,
                    payload=payload,
                    required=(
                        payload["status"] in in_scope_statuses
                        and scope_policy["require_for_in_scope_intake"]
                    ),
                )
            validate_ai_suggestion(
                label=label,
                payload=payload,
                intake_policy=intake_policy,
                governed_contract=governed_intake_assist,
                profiles=profiles,
                errors=errors,
            )
            ai_suggestion = payload.get("ai_suggestion") or {}
            decision_id = ai_suggestion.get("decision_id")
            if decision_id:
                if decision_id in ai_decision_owners:
                    errors.append(
                        f"{label}: ai_suggestion.decision_id {decision_id!r} is already applied by {ai_decision_owners[decision_id]}"
                    )
                else:
                    ai_decision_owners[decision_id] = label

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
