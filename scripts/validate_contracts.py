#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
import re
import sys

from jsonschema import Draft202012Validator
import yaml

from contracts_lib import (
    REPO_RULES_SCHEMA,
    SCHEMA_FILES,
    active_repo_names,
    load_contracts,
    load_json,
)


BRANCH_LIFECYCLE_TARGET_RE = re.compile(
    r"^repo:(?P<repo>[^:]+):(?P<kind>remote-branch|local-branch|worktree):(?P<value>.+)$"
)
BRANCH_LIFECYCLE_WAIVER_KINDS = {
    "branch-lifecycle-remote-branch": "remote-branch",
    "branch-lifecycle-local-branch": "local-branch",
    "branch-lifecycle-worktree": "worktree",
}


def validate_schema(errors: list[str], instance_path: Path, schema_path: Path) -> None:
    instance = yaml.safe_load(instance_path.read_text()) or {}
    schema = load_json(schema_path)
    validator = Draft202012Validator(schema)
    for error in validator.iter_errors(instance):
        path = ".".join(str(part) for part in error.absolute_path) or "<root>"
        errors.append(f"{instance_path}: {path}: {error.message}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate workspace governance contracts.")
    parser.add_argument(
        "--repo-root",
        default=Path(__file__).resolve().parents[1],
        type=Path,
        help="workspace-governance repository root",
    )
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    errors: list[str] = []

    instance_paths = {
        "version": repo_root / "contracts/version.yaml",
        "lifecycle": repo_root / "contracts/lifecycle.yaml",
        "intake_policy": repo_root / "contracts/intake-policy.yaml",
        "intake_register": repo_root / "contracts/intake-register.yaml",
        "governed_intake_assist": repo_root / "contracts/governed-intake-assist.yaml",
        "developer_integration_policy": repo_root / "contracts/developer-integration-policy.yaml",
        "developer_integration_profiles": repo_root / "contracts/developer-integration-profiles.yaml",
        "delegation_policy": repo_root / "contracts/delegation-policy.yaml",
        "self_improvement_policy": repo_root / "contracts/self-improvement-policy.yaml",
        "work_home_routing": repo_root / "contracts/work-home-routing.yaml",
        "dependency_types": repo_root / "contracts/dependency-types.yaml",
        "repos": repo_root / "contracts/repos.yaml",
        "products": repo_root / "contracts/products.yaml",
        "components": repo_root / "contracts/components.yaml",
        "task_types": repo_root / "contracts/task-types.yaml",
        "change_classes": repo_root / "contracts/change-classes.yaml",
        "failure_taxonomy": repo_root / "contracts/failure-taxonomy.yaml",
        "improvement_triggers": repo_root / "contracts/improvement-triggers.yaml",
        "evidence_obligations": repo_root / "contracts/evidence-obligations.yaml",
        "review_obligations": repo_root / "contracts/review-obligations.yaml",
        "vocabulary": repo_root / "contracts/vocabulary.yaml",
        "exceptions": repo_root / "contracts/exceptions.yaml",
        "validation_matrix": repo_root / "contracts/validation-matrix.yaml",
        "skills": repo_root / "contracts/skills.yaml",
        "governance_engine_foundation": repo_root / "contracts/governance-engine-foundation.yaml",
        "governance_engine_output_manifest": repo_root / "contracts/governance-engine-output-manifest.yaml",
        "governance_engine_boundary_map": repo_root / "contracts/governance-engine-boundary-map.yaml",
        "governance_engine_shadow_parity": repo_root / "contracts/governance-engine-shadow-parity.yaml",
        "governance_engine_extraction_gate": repo_root / "contracts/governance-engine-extraction-gate.yaml",
        "governance_control_fabric_operator_surface": repo_root / "contracts/governance-control-fabric-operator-surface.yaml",
    }

    for key, rel_path in SCHEMA_FILES.items():
        validate_schema(errors, instance_paths[key], repo_root / rel_path)

    repo_rules_schema = repo_root / REPO_RULES_SCHEMA
    for path in sorted((repo_root / "contracts" / "repo-rules").glob("*.yaml")):
        validate_schema(errors, path, repo_rules_schema)

    contracts = load_contracts(repo_root)
    lifecycle_states = set(contracts["lifecycle"]["states"].keys())
    intake_policy = contracts["intake_policy"]
    intake_register = contracts["intake_register"]
    governed_intake_assist = contracts["governed_intake_assist"]["governed_intake_assist"]
    developer_integration_policy = contracts["developer_integration_policy"]
    developer_integration_profiles = contracts["developer_integration_profiles"]
    delegation_policy = contracts["delegation_policy"]
    self_improvement_policy = contracts["self_improvement_policy"]
    work_home_routing = contracts["work_home_routing"]["work_home_routing"]
    intake_statuses = set(intake_policy["statuses"])
    active_repos = set(active_repo_names(contracts))
    intake_repos = set(intake_register["repos"].keys())
    retired_repos = set(contracts["repos"].get("retired_repos", {}).keys())
    product_names = set(contracts["products"]["products"].keys())
    intake_products = set(intake_register["products"].keys())
    change_classes = set(contracts["change_classes"]["change_classes"].keys())
    component_names = set(contracts["components"]["components"].keys())
    intake_components = set(intake_register["components"].keys())
    failure_classes = contracts["failure_taxonomy"]["failure_classes"]
    improvement_triggers = contracts["improvement_triggers"]["triggers"]
    validator_scripts = contracts["validation_matrix"]["validators"]
    registered_skills = contracts["skills"]["skills"]
    governance_engine_foundation = contracts["governance_engine_foundation"][
        "governance_engine_foundation"
    ]
    governance_engine_output_manifest = contracts["governance_engine_output_manifest"][
        "governance_engine_output_manifest"
    ]
    governance_engine_boundary_map = contracts["governance_engine_boundary_map"][
        "governance_engine_boundary_map"
    ]
    governance_engine_shadow_parity = contracts["governance_engine_shadow_parity"][
        "governance_engine_shadow_parity"
    ]
    governance_engine_extraction_gate = contracts["governance_engine_extraction_gate"][
        "governance_engine_extraction_gate"
    ]
    governance_control_fabric_operator_surface = contracts[
        "governance_control_fabric_operator_surface"
    ]["governance_control_fabric_operator_surface"]
    delegation_task_classes = delegation_policy["task_classes"]
    self_improvement_governance = self_improvement_policy["governance"]
    self_improvement_runtime_gate = self_improvement_policy["runtime_gate"]
    self_improvement_signal_catalog = self_improvement_policy["signal_catalog"]
    work_home_classes = work_home_routing["classes"]
    work_home_routing_homes = set(work_home_routing["routing_homes"].keys())

    expected_intake_statuses = {"out-of-scope", "proposed", "admitted"}
    if intake_statuses != expected_intake_statuses:
        errors.append(
            "contracts/intake-policy.yaml: statuses must be exactly out-of-scope, proposed, admitted"
        )
    expected_governed_intake_assist_ref = {
        "repo": "workspace-governance",
        "path": "contracts/governed-intake-assist.yaml",
    }
    actual_governed_intake_assist_ref = intake_policy["ai_suggestions"][
        "governed_intake_assist_contract"
    ]
    if actual_governed_intake_assist_ref != expected_governed_intake_assist_ref:
        errors.append(
            "contracts/intake-policy.yaml: ai_suggestions.governed_intake_assist_contract "
            "must point to workspace-governance/contracts/governed-intake-assist.yaml"
        )
    if governed_intake_assist["owner_repo"] != "workspace-governance":
        errors.append(
            "contracts/governed-intake-assist.yaml: owner_repo must be 'workspace-governance'"
        )
    primary_operator_surface = repo_root / governed_intake_assist["primary_operator_surface"]
    if primary_operator_surface.suffix != ".md" or not primary_operator_surface.exists():
        errors.append(
            "contracts/governed-intake-assist.yaml: primary_operator_surface must point to an existing markdown operator surface"
        )
    governed_intake_consumer = governed_intake_assist["consumer"]
    governed_output_schema_ref = {
        "repo": "workspace-governance",
        "path": "contracts/schemas/intake-ai-suggestion.schema.json",
    }
    if governed_intake_consumer["caller_id"] != "workspace-governance/intake-assist":
        errors.append(
            "contracts/governed-intake-assist.yaml: consumer.caller_id must be workspace-governance/intake-assist"
        )
    if governed_intake_consumer["caller_repo"] != "workspace-governance":
        errors.append(
            "contracts/governed-intake-assist.yaml: consumer.caller_repo must be workspace-governance"
        )
    if governed_intake_consumer["purpose"] != "workspace-intake-assist":
        errors.append(
            "contracts/governed-intake-assist.yaml: consumer.purpose must be workspace-intake-assist"
        )
    if governed_intake_consumer["profile_id"] != "intake-classifier-v1":
        errors.append(
            "contracts/governed-intake-assist.yaml: consumer.profile_id must be intake-classifier-v1"
        )
    if governed_intake_consumer["invocation_path"] != "governed-ai-gateway":
        errors.append(
            "contracts/governed-intake-assist.yaml: consumer.invocation_path must be governed-ai-gateway"
        )
    if governed_intake_consumer["output_schema_ref"] != governed_output_schema_ref:
        errors.append(
            "contracts/governed-intake-assist.yaml: consumer.output_schema_ref must point to contracts/schemas/intake-ai-suggestion.schema.json"
        )
    if not (repo_root / governed_output_schema_ref["path"]).exists():
        errors.append(
            "contracts/governed-intake-assist.yaml: consumer.output_schema_ref path does not exist"
        )
    governed_contract_refs = governed_intake_assist["platform_contract_refs"]
    if (
        governed_contract_refs["profile_registry"]
        != intake_policy["ai_suggestions"]["governed_profile_registry"]
    ):
        errors.append(
            "contracts/governed-intake-assist.yaml: platform_contract_refs.profile_registry must match intake-policy governed_profile_registry"
        )
    expected_required_live_gates = {
        "profile-active",
        "access-plane-live",
        "identity-boundary-live",
        "audit-retention-live",
        "provider-egress-blocked",
        "security-delta-review-current",
    }
    activation_state = governed_intake_assist["activation_state"]
    if activation_state["source_contract_status"] != "source-defined":
        errors.append(
            "contracts/governed-intake-assist.yaml: activation_state.source_contract_status must be source-defined"
        )
    if activation_state["live_consumption_allowed"] is not False:
        errors.append(
            "contracts/governed-intake-assist.yaml: activation_state.live_consumption_allowed must remain false until live gates are proven"
        )
    if set(activation_state["required_live_gates"]) != expected_required_live_gates:
        errors.append(
            "contracts/governed-intake-assist.yaml: activation_state.required_live_gates must match the platform runtime-assist gate ids"
        )
    suggestion_contract = governed_intake_assist["suggestion_contract"]
    if suggestion_contract["authority"] != "suggestion-only":
        errors.append(
            "contracts/governed-intake-assist.yaml: suggestion_contract.authority must be suggestion-only"
        )
    if suggestion_contract["autonomous_mutation_allowed"] is not False:
        errors.append(
            "contracts/governed-intake-assist.yaml: suggestion_contract.autonomous_mutation_allowed must be false"
        )
    if suggestion_contract["structured_output_schema_ref"] != governed_output_schema_ref:
        errors.append(
            "contracts/governed-intake-assist.yaml: suggestion_contract.structured_output_schema_ref must match the consumer output schema"
        )
    if set(suggestion_contract["allowed_decisions"]) != expected_intake_statuses:
        errors.append(
            "contracts/governed-intake-assist.yaml: suggestion_contract.allowed_decisions must match intake-policy statuses"
        )
    for denied_action in (
        "model-output-direct-mutation",
        "direct-provider-client",
        "repo-local-provider-secret",
        "unaudited-operator-acceptance",
        "rejected-suggestion-register-write",
    ):
        if denied_action not in suggestion_contract["denied_actions"]:
            errors.append(
                "contracts/governed-intake-assist.yaml: suggestion_contract.denied_actions "
                f"must include {denied_action!r}"
            )
    operator_acceptance = governed_intake_assist["operator_acceptance"]
    if operator_acceptance["human_approval_required"] is not True:
        errors.append(
            "contracts/governed-intake-assist.yaml: operator_acceptance.human_approval_required must be true"
        )
    if operator_acceptance["acceptance_required_before_workspace_truth_update"] is not True:
        errors.append(
            "contracts/governed-intake-assist.yaml: operator_acceptance.acceptance_required_before_workspace_truth_update must be true"
        )
    if set(operator_acceptance["allowed_acceptance_states_for_truth_update"]) != {
        "accepted",
        "overridden",
    }:
        errors.append(
            "contracts/governed-intake-assist.yaml: operator_acceptance.allowed_acceptance_states_for_truth_update must be exactly accepted and overridden"
        )
    if operator_acceptance["override_requires_reason"] is not True:
        errors.append(
            "contracts/governed-intake-assist.yaml: operator_acceptance.override_requires_reason must be true"
        )
    expected_operator_acceptance_fields = {
        "accepted_by",
        "accepted_at",
        "decision_id",
        "suggested_decision",
        "operator_decision",
        "acceptance_state",
        "audit_ref",
    }
    if set(operator_acceptance["required_fields"]) != expected_operator_acceptance_fields:
        errors.append(
            "contracts/governed-intake-assist.yaml: operator_acceptance.required_fields must be exactly "
            + ", ".join(sorted(expected_operator_acceptance_fields))
        )
    workspace_truth_updates = governed_intake_assist["workspace_truth_updates"]
    if set(workspace_truth_updates["allowed_targets"]) != {"contracts/intake-register.yaml"}:
        errors.append(
            "contracts/governed-intake-assist.yaml: workspace_truth_updates.allowed_targets must be exactly contracts/intake-register.yaml"
        )
    if set(workspace_truth_updates["allowed_decision_sources"]) != {"operator", "ai-suggested"}:
        errors.append(
            "contracts/governed-intake-assist.yaml: workspace_truth_updates.allowed_decision_sources must be exactly operator and ai-suggested"
        )
    if workspace_truth_updates["ai_suggested_requires_active_profile"] is not True:
        errors.append(
            "contracts/governed-intake-assist.yaml: workspace_truth_updates.ai_suggested_requires_active_profile must be true"
        )
    if workspace_truth_updates["ai_suggested_requires_operator_acceptance"] is not True:
        errors.append(
            "contracts/governed-intake-assist.yaml: workspace_truth_updates.ai_suggested_requires_operator_acceptance must be true"
        )
    expected_governed_audit_fields = {
        "event_time",
        "correlation_id",
        "caller_identity",
        "operator_identity",
        "approved_profile_id",
        "invocation_path",
        "purpose",
        "output_schema_ref",
        "policy_decision",
        "outcome",
        "operator_acceptance_state",
        "override_reason",
    }
    if set(governed_intake_assist["audit_contract"]["required_fields"]) != expected_governed_audit_fields:
        errors.append(
            "contracts/governed-intake-assist.yaml: audit_contract.required_fields must match the platform governed-AI audit minimum"
        )

    expected_devint_actions = {"up", "status", "smoke", "down", "reset", "promote_check"}
    lane = developer_integration_policy["lane"]
    profile_lifecycle = developer_integration_policy["profile_lifecycle"]
    request_admission = developer_integration_policy["request_admission"]
    live_miss_escalation = developer_integration_policy["live_miss_escalation"]
    if lane["id"] != "dev-integration":
        errors.append("contracts/developer-integration-policy.yaml: lane.id must be 'dev-integration'")
    for owner_key in ("standard_owner", "runtime_owner"):
        if lane[owner_key] not in active_repos:
            errors.append(
                f"contracts/developer-integration-policy.yaml: {owner_key} {lane[owner_key]!r} is not an active repo"
            )
    expected_devint_statuses = {"proposed", "active", "suspended", "retired"}
    if set(profile_lifecycle["statuses"]) != expected_devint_statuses:
        errors.append(
            "contracts/developer-integration-policy.yaml: profile_lifecycle.statuses must be exactly "
            + ", ".join(sorted(expected_devint_statuses))
        )
    if set(profile_lifecycle["self_serve_statuses"]) != {"active"}:
        errors.append(
            "contracts/developer-integration-policy.yaml: profile_lifecycle.self_serve_statuses must be exactly active"
        )
    if set(profile_lifecycle["platform_acceptance_required_for"]) != {"active", "suspended", "retired"}:
        errors.append(
            "contracts/developer-integration-policy.yaml: profile_lifecycle.platform_acceptance_required_for must be exactly active, retired, suspended"
        )
    adapter_owner = request_admission["current_request_adapter"]["owner_repo"]
    if adapter_owner not in active_repos:
        errors.append(
            "contracts/developer-integration-policy.yaml: request_admission.current_request_adapter.owner_repo "
            f"{adapter_owner!r} is not an active repo"
        )
    if live_miss_escalation["owner_repo"] not in active_repos:
        errors.append(
            "contracts/developer-integration-policy.yaml: live_miss_escalation.owner_repo "
            f"{live_miss_escalation['owner_repo']!r} is not an active repo"
        )
    if set(developer_integration_policy["required_actions"]) != expected_devint_actions:
        errors.append(
            "contracts/developer-integration-policy.yaml: required_actions must be exactly "
            + ", ".join(sorted(expected_devint_actions))
        )
    delegation_governance = delegation_policy["governance"]
    if delegation_governance["policy_owner_repo"] not in active_repos:
        errors.append(
            "contracts/delegation-policy.yaml: governance.policy_owner_repo "
            f"{delegation_governance['policy_owner_repo']!r} is not an active repo"
        )
    if delegation_governance["policy_owner_repo"] != "workspace-governance":
        errors.append(
            "contracts/delegation-policy.yaml: governance.policy_owner_repo must be 'workspace-governance'"
        )
    for skill_name in delegation_governance["required_skills"]:
        if skill_name not in registered_skills:
            errors.append(
                f"contracts/delegation-policy.yaml: governance.required_skills references unknown skill {skill_name!r}"
            )
    if not delegation_governance["operator_surface_path"].endswith(".md"):
        errors.append(
            "contracts/delegation-policy.yaml: governance.operator_surface_path must point to a markdown instruction surface"
        )
    elif not (repo_root / delegation_governance["operator_surface_path"]).exists():
        errors.append(
            "contracts/delegation-policy.yaml: governance.operator_surface_path "
            f"{delegation_governance['operator_surface_path']!r} does not exist"
        )
    if not delegation_governance["journal_root"].startswith("reviews/"):
        errors.append(
            "contracts/delegation-policy.yaml: governance.journal_root must live under reviews/"
        )
    packet_kinds = set(delegation_policy["packet"]["delegate_kinds"])
    expected_packet_kinds = {"exploration", "implementation", "verification"}
    if packet_kinds != expected_packet_kinds:
        errors.append(
            "contracts/delegation-policy.yaml: packet.delegate_kinds must be exactly exploration, implementation, verification"
        )
    required_packet_fields = set(delegation_policy["packet"]["required_fields"])
    expected_packet_fields = {
        "work_item_ref",
        "summary",
        "owner_repo",
        "allowed_write_paths",
        "expected_outputs",
        "proof_expectation",
        "forbidden_actions",
    }
    if required_packet_fields != expected_packet_fields:
        errors.append(
            "contracts/delegation-policy.yaml: packet.required_fields must be exactly "
            + ", ".join(sorted(expected_packet_fields))
        )
    required_journal_fields = set(delegation_policy["audit_journal"]["required_fields"])
    expected_journal_fields = {
        "delegation_id",
        "created_on",
        "owner_repo",
        "work_item_ref",
        "task_class",
        "main_agent",
        "packets",
        "integration_outcome",
    }
    if required_journal_fields != expected_journal_fields:
        errors.append(
            "contracts/delegation-policy.yaml: audit_journal.required_fields must be exactly "
            + ", ".join(sorted(expected_journal_fields))
        )
    if "live-control" not in delegation_task_classes:
        errors.append("contracts/delegation-policy.yaml: task_classes must define 'live-control'")
    for task_class, payload in delegation_task_classes.items():
        if payload["max_sub_agents"] == 0 and payload["allows_delegated_write"]:
            errors.append(
                f"contracts/delegation-policy.yaml: task_class {task_class!r} cannot allow delegated write with max_sub_agents=0"
            )
    if delegation_task_classes.get("live-control", {}).get("max_sub_agents") != 0:
        errors.append("contracts/delegation-policy.yaml: task_class 'live-control' must keep max_sub_agents=0")
    if delegation_task_classes.get("live-control", {}).get("allows_delegated_write") is not False:
        errors.append("contracts/delegation-policy.yaml: task_class 'live-control' must not allow delegated write")
    if delegation_policy["future_enforcement_boundary"]["parked_architecture_ref"] != "openproject://work_packages/77":
        errors.append(
            "contracts/delegation-policy.yaml: future_enforcement_boundary.parked_architecture_ref must point to openproject://work_packages/77"
        )
    if work_home_routing["owner_repo"] != "workspace-governance":
        errors.append("contracts/work-home-routing.yaml: owner_repo must be 'workspace-governance'")
    expected_work_home_classes = set(work_home_classes.keys())
    if set(work_home_routing["classification_order"]) != expected_work_home_classes:
        errors.append(
            "contracts/work-home-routing.yaml: classification_order must list every class exactly once"
        )
    for class_id, payload in work_home_classes.items():
        if payload["routing_home"] not in work_home_routing_homes:
            errors.append(
                "contracts/work-home-routing.yaml: class "
                f"{class_id!r} references unknown routing_home {payload['routing_home']!r}"
            )
    for example in work_home_routing["examples"]:
        if example["class"] not in work_home_classes:
            errors.append(
                "contracts/work-home-routing.yaml: example scenario "
                f"{example['scenario']!r} references unknown class {example['class']!r}"
            )
        if example["owner_repo"] not in active_repos:
            errors.append(
                "contracts/work-home-routing.yaml: example scenario "
                f"{example['scenario']!r} references inactive owner_repo {example['owner_repo']!r}"
            )
    if governance_engine_foundation["owner_repo"] != "workspace-governance":
        errors.append(
            "contracts/governance-engine-foundation.yaml: owner_repo must be 'workspace-governance'"
        )
    expected_source_layers = {
        "workspace-root",
        "contracts",
        "skills",
        "scripts",
        "generated",
    }
    actual_source_layers = {
        entry["id"] for entry in governance_engine_foundation["source_of_truth_layers"]
    }
    if actual_source_layers != expected_source_layers:
        errors.append(
            "contracts/governance-engine-foundation.yaml: source_of_truth_layers must be exactly "
            + ", ".join(sorted(expected_source_layers))
        )
    expected_tenant_surfaces = {
        "intake-register",
        "developer-integration-profiles",
        "exceptions",
        "owner-repo-template-records",
        "owner-repo-workflows",
        "security-review-outputs",
    }
    actual_tenant_surfaces = {
        entry["id"] for entry in governance_engine_foundation["tenant_instance_surfaces"]
    }
    if actual_tenant_surfaces != expected_tenant_surfaces:
        errors.append(
            "contracts/governance-engine-foundation.yaml: tenant_instance_surfaces must be exactly "
            + ", ".join(sorted(expected_tenant_surfaces))
        )
    if (
        governance_engine_foundation["compatibility_boundary"]["boundary_map_ref"]
        != "contracts/governance-engine-boundary-map.yaml"
    ):
        errors.append(
            "contracts/governance-engine-foundation.yaml: compatibility_boundary.boundary_map_ref must point to contracts/governance-engine-boundary-map.yaml"
        )
    expected_stable_entrypoints = {
        "workspace-root/AGENTS.md",
        "workspace-root/README.md",
        "workspace-root/ARCHITECTURE.md",
        "scripts/sync_workspace_root.py",
        "scripts/install_skills.py",
        "scripts/validate_contracts.py",
        "scripts/audit_workspace_layout.py",
    }
    actual_stable_entrypoints = set(
        governance_engine_foundation["compatibility_boundary"]["stable_entrypoints"]
    )
    if actual_stable_entrypoints != expected_stable_entrypoints:
        errors.append(
            "contracts/governance-engine-foundation.yaml: compatibility_boundary.stable_entrypoints must be exactly "
            + ", ".join(sorted(expected_stable_entrypoints))
        )
    if (
        governance_engine_foundation["shadow_parity"]["contract_ref"]
        != "contracts/governance-engine-shadow-parity.yaml"
    ):
        errors.append(
            "contracts/governance-engine-foundation.yaml: shadow_parity.contract_ref must point to contracts/governance-engine-shadow-parity.yaml"
        )
    if governance_engine_foundation["packaging_model"]["central_repo"] != "workspace-governance":
        errors.append(
            "contracts/governance-engine-foundation.yaml: packaging_model.central_repo must be 'workspace-governance'"
        )
    if (
        governance_engine_foundation["packaging_model"]["output_manifest_ref"]
        != "contracts/governance-engine-output-manifest.yaml"
    ):
        errors.append(
            "contracts/governance-engine-foundation.yaml: packaging_model.output_manifest_ref must point to contracts/governance-engine-output-manifest.yaml"
        )
    expected_allowed_seams = {
        "product runtime behavior",
        "component interface contracts",
        "packaging and build-tooling constraints",
        "repo-local protocol or artifact formats",
    }
    actual_allowed_seams = set(
        governance_engine_foundation["packaging_model"]["custom_validation_allowed_seams"]
    )
    if actual_allowed_seams != expected_allowed_seams:
        errors.append(
            "contracts/governance-engine-foundation.yaml: packaging_model.custom_validation_allowed_seams must be exactly "
            + ", ".join(sorted(expected_allowed_seams))
        )
    expected_forbidden_validation_classes = {
        "central owner and routing truth",
        "central lifecycle and intake semantics",
        "governed AI model policy",
        "cross-repo evidence and review obligations",
    }
    actual_forbidden_validation_classes = set(
        governance_engine_foundation["packaging_model"]["custom_validation_forbidden_classes"]
    )
    if actual_forbidden_validation_classes != expected_forbidden_validation_classes:
        errors.append(
            "contracts/governance-engine-foundation.yaml: packaging_model.custom_validation_forbidden_classes must be exactly "
            + ", ".join(sorted(expected_forbidden_validation_classes))
        )
    if governance_engine_output_manifest["owner_repo"] != "workspace-governance":
        errors.append(
            "contracts/governance-engine-output-manifest.yaml: owner_repo must be 'workspace-governance'"
        )
    manifest_families = {
        entry["id"]: entry for entry in governance_engine_output_manifest["emission_families"]
    }
    expected_manifest_family_ids = {
        "workspace-root-sync",
        "installed-skills",
        "generated-governance-artifacts",
    }
    if set(manifest_families) != expected_manifest_family_ids:
        errors.append(
            "contracts/governance-engine-output-manifest.yaml: emission_families must be exactly "
            + ", ".join(sorted(expected_manifest_family_ids))
        )
    foundation_source_layers = actual_source_layers
    for family_id, payload in manifest_families.items():
        source_layers = set(payload["source_layers"])
        if not source_layers.issubset(foundation_source_layers):
            errors.append(
                "contracts/governance-engine-output-manifest.yaml: "
                f"{family_id} source_layers must stay within governance-engine source_of_truth_layers"
            )
        emitter_path = repo_root / payload["emitter"]
        if not emitter_path.exists():
            errors.append(
                "contracts/governance-engine-output-manifest.yaml: "
                f"{family_id} emitter path {payload['emitter']!r} does not exist"
            )
    workspace_root_family = manifest_families.get("workspace-root-sync")
    if workspace_root_family:
        expected_sync_outputs = {
            ("workspace-root/ARCHITECTURE.md", "ARCHITECTURE.md", "text"),
            ("workspace-root/README.md", "README.md", "text"),
            ("workspace-root/AGENTS.md", "AGENTS.md", "text"),
            ("scripts/audit_workspace_layout.py", "_workspace_tools/audit_workspace_layout.py", "text"),
        }
        actual_sync_outputs = {
            (entry.get("source_path"), entry.get("emitted_path"), entry.get("format"))
            for entry in workspace_root_family.get("outputs", [])
        }
        if actual_sync_outputs != expected_sync_outputs:
            errors.append(
                "contracts/governance-engine-output-manifest.yaml: workspace-root-sync outputs must match the current canonical workspace-root materialization set"
            )
    installed_skills_family = manifest_families.get("installed-skills")
    if installed_skills_family:
        if installed_skills_family["source_contract"] != "contracts/skills.yaml":
            errors.append(
                "contracts/governance-engine-output-manifest.yaml: installed-skills.source_contract must be contracts/skills.yaml"
            )
        if installed_skills_family["managed_manifest_filename"] != ".workspace-governance-skills.json":
            errors.append(
                "contracts/governance-engine-output-manifest.yaml: installed-skills.managed_manifest_filename must be .workspace-governance-skills.json"
            )
        if installed_skills_family["target_root_default"] != "~/.codex/skills":
            errors.append(
                "contracts/governance-engine-output-manifest.yaml: installed-skills.target_root_default must be ~/.codex/skills"
            )
    generated_artifacts_family = manifest_families.get("generated-governance-artifacts")
    if generated_artifacts_family:
        expected_generated_outputs = {
            ("system_map", "generated/system-map.yaml", "yaml"),
            ("resolved_owner_map", "generated/resolved-owner-map.json", "json"),
            ("resolved_dependency_graph", "generated/resolved-dependency-graph.json", "json"),
            ("stale_content_rules", "generated/stale-content-rules.json", "json"),
            ("governance_engine_boundary_map", "generated/governance-engine-boundary-map.json", "json"),
        }
        actual_generated_outputs = {
            (entry["id"], entry.get("emitted_path"), entry.get("format"))
            for entry in generated_artifacts_family.get("outputs", [])
        }
        if actual_generated_outputs != expected_generated_outputs:
            errors.append(
                "contracts/governance-engine-output-manifest.yaml: generated-governance-artifacts outputs must match the current generated artifact set"
            )
    if governance_engine_boundary_map["owner_repo"] != "workspace-governance":
        errors.append(
            "contracts/governance-engine-boundary-map.yaml: owner_repo must be 'workspace-governance'"
        )
    if set(governance_engine_boundary_map["authoring_paths"]) != {
        "workspace-root/",
        "contracts/",
        "skills-src/",
        "scripts/",
    }:
        errors.append(
            "contracts/governance-engine-boundary-map.yaml: authoring_paths must be exactly workspace-root/, contracts/, skills-src/, scripts/"
        )
    if set(governance_engine_boundary_map["generated_paths"]) != {"generated/"}:
        errors.append(
            "contracts/governance-engine-boundary-map.yaml: generated_paths must be exactly generated/"
        )
    expected_tenant_instance_paths = {
        "contracts/intake-register.yaml",
        "contracts/developer-integration-profiles.yaml",
        "contracts/exceptions.yaml",
    }
    if set(governance_engine_boundary_map["tenant_instance_paths"]) != expected_tenant_instance_paths:
        errors.append(
            "contracts/governance-engine-boundary-map.yaml: tenant_instance_paths must be exactly "
            + ", ".join(sorted(expected_tenant_instance_paths))
        )
    if set(governance_engine_boundary_map["external_instance_surfaces"]) != {
        "owner-repo primary operator surfaces",
        "owner-repo template records",
        "security-architecture review artifacts",
    }:
        errors.append(
            "contracts/governance-engine-boundary-map.yaml: external_instance_surfaces must be exactly owner-repo primary operator surfaces, owner-repo template records, security-architecture review artifacts"
        )
    expected_live_materialized_outputs = {
        "ARCHITECTURE.md",
        "README.md",
        "AGENTS.md",
        "_workspace_tools/audit_workspace_layout.py",
        "~/.codex/skills/",
    }
    if set(governance_engine_boundary_map["live_materialized_outputs"]) != expected_live_materialized_outputs:
        errors.append(
            "contracts/governance-engine-boundary-map.yaml: live_materialized_outputs must be exactly "
            + ", ".join(sorted(expected_live_materialized_outputs))
        )
    expected_current_coupling_points = {
        "workspace-root-live-materialization": {
            "description": "workspace bootstrap files are still materialized directly from this repo into the live workspace root",
            "impacted_surfaces": {
                "workspace-root/ARCHITECTURE.md",
                "workspace-root/README.md",
                "workspace-root/AGENTS.md",
                "scripts/sync_workspace_root.py",
            },
        },
        "live-skill-installation": {
            "description": "managed skills are still installed directly from this repo into the live Codex skill root",
            "impacted_surfaces": {
                "skills-src/",
                "contracts/skills.yaml",
                "scripts/install_skills.py",
            },
        },
        "contract-driven-generated-artifacts": {
            "description": "generated ownership, dependency, stale-content, and boundary artifacts are emitted from this repo and consumed across the workspace",
            "impacted_surfaces": {
                "generated/",
                "contracts/governance-engine-output-manifest.yaml",
                "scripts/validate_cross_repo_truth.py",
            },
        },
        "external-review-and-operator-surfaces": {
            "description": "extraction decisions still depend on external owner-repo operator surfaces and security review artifacts that remain outside generated copies",
            "impacted_surfaces": {
                "owner-repo primary operator surfaces",
                "security-architecture review artifacts",
                "contracts/governance-engine-extraction-gate.yaml",
            },
        },
        "owner-repo-template-record-surfaces": {
            "description": "validation planning must consume repo-owned TEMPLATE.* records without turning them into generated workspace copies",
            "impacted_surfaces": {
                "owner-repo TEMPLATE.* records",
                "contracts/repo-rules/",
                "docs/governance-engine-foundation.md",
            },
        },
    }
    actual_current_coupling_points = {
        entry["coupling_id"]: {
            "description": entry["description"],
            "impacted_surfaces": set(entry["impacted_surfaces"]),
        }
        for entry in governance_engine_boundary_map["current_coupling_points"]
    }
    if set(actual_current_coupling_points) != set(expected_current_coupling_points):
        errors.append(
            "contracts/governance-engine-boundary-map.yaml: current_coupling_points must define the current workspace-root-live-materialization, live-skill-installation, contract-driven-generated-artifacts, external-review-and-operator-surfaces, and owner-repo-template-record-surfaces entries"
        )
    else:
        for coupling_id, expected in expected_current_coupling_points.items():
            actual = actual_current_coupling_points[coupling_id]
            if actual["description"] != expected["description"]:
                errors.append(
                    f"contracts/governance-engine-boundary-map.yaml: current_coupling_points[{coupling_id}].description must be {expected['description']!r}"
                )
            if actual["impacted_surfaces"] != expected["impacted_surfaces"]:
                errors.append(
                    "contracts/governance-engine-boundary-map.yaml: "
                    f"current_coupling_points[{coupling_id}].impacted_surfaces must be exactly "
                    + ", ".join(sorted(expected["impacted_surfaces"]))
                )
    expected_standalone_packaging_prerequisites = {
        "package-identity-and-versioning": {
            "threshold": "standalone package identity, versioning authority, and release contract are explicit before extraction starts",
            "evidence_surfaces": {
                "contracts/governance-engine-extraction-gate.yaml",
                "contracts/governance-engine-output-manifest.yaml",
            },
        },
        "install-and-materialization-surface": {
            "threshold": "installation can materialize workspace-root files, live skills, and generated artifacts without relying on repo-local convenience",
            "evidence_surfaces": {
                "scripts/materialize_governance_engine_outputs.py",
                "contracts/governance-engine-output-manifest.yaml",
            },
        },
        "tenant-consumption-contract": {
            "threshold": "tenant-instance consumers can declare required inputs and compatibility expectations without redefining engine-owned truth",
            "evidence_surfaces": {
                "contracts/governance-engine-boundary-map.yaml",
                "docs/governance-engine-foundation.md",
            },
        },
        "compatibility-shim-plan": {
            "threshold": "stable operator entrypoints keep working or have explicit compatibility shims during extraction",
            "evidence_surfaces": {
                "contracts/governance-engine-foundation.yaml",
                "docs/governance-engine-foundation.md",
            },
        },
        "security-delta-refresh": {
            "threshold": "a fresh security delta review is scheduled for the actual extraction package and trust-boundary change",
            "evidence_surfaces": {
                "security-architecture review artifacts",
            },
        },
        "template-family-consumption-contract": {
            "threshold": "record-template family ownership, expected shape, unknown-template handling, and validation-planner consumption rules are explicit before runtime extraction",
            "evidence_surfaces": {
                "contracts/repo-rules/",
                "docs/governance-engine-foundation.md",
            },
        },
    }
    actual_standalone_packaging_prerequisites = {
        entry["prerequisite_id"]: {
            "threshold": entry["threshold"],
            "evidence_surfaces": set(entry["evidence_surfaces"]),
        }
        for entry in governance_engine_boundary_map["standalone_packaging_prerequisites"]
    }
    if set(actual_standalone_packaging_prerequisites) != set(expected_standalone_packaging_prerequisites):
        errors.append(
            "contracts/governance-engine-boundary-map.yaml: standalone_packaging_prerequisites must define the current package-identity-and-versioning, install-and-materialization-surface, tenant-consumption-contract, compatibility-shim-plan, security-delta-refresh, and template-family-consumption-contract entries"
        )
    else:
        for prerequisite_id, expected in expected_standalone_packaging_prerequisites.items():
            actual = actual_standalone_packaging_prerequisites[prerequisite_id]
            if actual["threshold"] != expected["threshold"]:
                errors.append(
                    f"contracts/governance-engine-boundary-map.yaml: standalone_packaging_prerequisites[{prerequisite_id}].threshold must be {expected['threshold']!r}"
                )
            if actual["evidence_surfaces"] != expected["evidence_surfaces"]:
                errors.append(
                    "contracts/governance-engine-boundary-map.yaml: "
                    f"standalone_packaging_prerequisites[{prerequisite_id}].evidence_surfaces must be exactly "
                    + ", ".join(sorted(expected["evidence_surfaces"]))
                )
    projection = governance_engine_boundary_map["generated_projection"]
    if projection["output_id"] != "governance_engine_boundary_map":
        errors.append(
            "contracts/governance-engine-boundary-map.yaml: generated_projection.output_id must be governance_engine_boundary_map"
        )
    if projection["path"] != "generated/governance-engine-boundary-map.json":
        errors.append(
            "contracts/governance-engine-boundary-map.yaml: generated_projection.path must be generated/governance-engine-boundary-map.json"
        )
    if projection["emitter"] != "scripts/validate_cross_repo_truth.py":
        errors.append(
            "contracts/governance-engine-boundary-map.yaml: generated_projection.emitter must be scripts/validate_cross_repo_truth.py"
        )
    if governance_engine_shadow_parity["owner_repo"] != "workspace-governance":
        errors.append(
            "contracts/governance-engine-shadow-parity.yaml: owner_repo must be 'workspace-governance'"
        )
    expected_shadow_parity_refs = {
        "foundation_ref": "contracts/governance-engine-foundation.yaml",
        "boundary_map_ref": "contracts/governance-engine-boundary-map.yaml",
        "output_manifest_ref": "contracts/governance-engine-output-manifest.yaml",
        "validator_script": "scripts/validate_governance_engine_shadow_parity.py",
        "primary_surface_path": "docs/governance-engine-foundation.md",
    }
    for key, expected in expected_shadow_parity_refs.items():
        if governance_engine_shadow_parity[key] != expected:
            errors.append(
                f"contracts/governance-engine-shadow-parity.yaml: {key} must be {expected!r}"
            )
    expected_shadow_check_commands = {
        "workspace-root-sync": "python3 scripts/materialize_governance_engine_outputs.py workspace-root --check",
        "installed-skills": "python3 scripts/materialize_governance_engine_outputs.py skills --check",
        "generated-governance-artifacts": "python3 scripts/materialize_governance_engine_outputs.py generated --check",
        "compatibility-entrypoints": "python3 scripts/validate_governance_engine_shadow_parity.py",
    }
    actual_shadow_checks = {
        entry["id"]: entry["command"]
        for entry in governance_engine_shadow_parity["required_checks"]
    }
    if actual_shadow_checks != expected_shadow_check_commands:
        errors.append(
            "contracts/governance-engine-shadow-parity.yaml: required_checks must define the current workspace-root, installed-skills, generated-governance-artifacts, and compatibility-entrypoints commands"
        )
    expected_cutover_checks = {
        "workspace-root-sync",
        "installed-skills",
        "generated-governance-artifacts",
        "compatibility-entrypoints",
    }
    if set(governance_engine_shadow_parity["cutover_gate"]["required_clean_checks"]) != expected_cutover_checks:
        errors.append(
            "contracts/governance-engine-shadow-parity.yaml: cutover_gate.required_clean_checks must be exactly "
            + ", ".join(sorted(expected_cutover_checks))
        )
    expected_forbidden_conditions = {
        "duplicated workspace control-plane truth in repo-local copies",
        "stale live skill installs or missing managed skill manifest",
        "stale generated boundary projection",
        "missing stable compatibility entrypoints",
    }
    if set(governance_engine_shadow_parity["cutover_gate"]["forbidden_conditions"]) != expected_forbidden_conditions:
        errors.append(
            "contracts/governance-engine-shadow-parity.yaml: cutover_gate.forbidden_conditions must be exactly "
            + ", ".join(sorted(expected_forbidden_conditions))
        )
    if governance_engine_extraction_gate["owner_repo"] != "workspace-governance":
        errors.append(
            "contracts/governance-engine-extraction-gate.yaml: owner_repo must be 'workspace-governance'"
        )
    expected_extraction_refs = {
        "foundation_ref": "contracts/governance-engine-foundation.yaml",
        "shadow_parity_ref": "contracts/governance-engine-shadow-parity.yaml",
        "boundary_map_ref": "contracts/governance-engine-boundary-map.yaml",
        "primary_surface_path": "docs/governance-engine-foundation.md",
        "security_review_ref": "security-architecture/docs/reviews/platform/2026-04-25-governance-engine-parity-extraction-and-runtime-readiness.md",
    }
    for key, expected in expected_extraction_refs.items():
        if governance_engine_extraction_gate[key] != expected:
            errors.append(
                f"contracts/governance-engine-extraction-gate.yaml: {key} must be {expected!r}"
            )
    expected_extraction_decision = {
        "default_outcome": "retain-integrated-governance-engine",
        "approved_outcome": "approve-standalone-governance-engine-extraction",
        "hard_gate_mode": "all_must_pass",
        "extraction_need_signal_threshold": "all_listed_signals_required",
    }
    extraction_decision = governance_engine_extraction_gate["extraction_decision"]
    for key, expected in expected_extraction_decision.items():
        if extraction_decision[key] != expected:
            errors.append(
                f"contracts/governance-engine-extraction-gate.yaml: extraction_decision.{key} must be {expected!r}"
            )
    expected_decision_record_requirements = {
        "record the retain-versus-extract outcome on the PI objective before extraction work begins",
        "cite the current parity and security evidence in the decision record",
        "keep bounded runtime activation deferred to epic #251 even when extraction is approved",
    }
    if set(extraction_decision["decision_record_requirements"]) != expected_decision_record_requirements:
        errors.append(
            "contracts/governance-engine-extraction-gate.yaml: extraction_decision.decision_record_requirements must be exactly "
            + ", ".join(sorted(expected_decision_record_requirements))
        )
    current_decision = governance_engine_extraction_gate["current_decision"]
    recorded_on = current_decision["recorded_on"]
    if isinstance(recorded_on, date):
        recorded_on_value = recorded_on.isoformat()
    elif isinstance(recorded_on, str):
        recorded_on_value = recorded_on
    else:
        recorded_on_value = None
    if recorded_on_value is None:
        errors.append(
            "contracts/governance-engine-extraction-gate.yaml: current_decision.recorded_on must be an ISO date"
        )
    else:
        try:
            date.fromisoformat(recorded_on_value)
        except ValueError:
            errors.append(
                "contracts/governance-engine-extraction-gate.yaml: current_decision.recorded_on must be an ISO date"
            )
    expected_current_decision_refs = {
        "recorded_by_work_item_ref": "openproject://work_packages/338",
        "recorded_from_feature_ref": "openproject://work_packages/339",
    }
    for key, expected in expected_current_decision_refs.items():
        if current_decision[key] != expected:
            errors.append(
                f"contracts/governance-engine-extraction-gate.yaml: current_decision.{key} must be {expected!r}"
            )
    allowed_current_outcomes = {
        extraction_decision["default_outcome"],
        extraction_decision["approved_outcome"],
    }
    if current_decision["outcome"] not in allowed_current_outcomes:
        errors.append(
            "contracts/governance-engine-extraction-gate.yaml: current_decision.outcome must be one of "
            + ", ".join(sorted(allowed_current_outcomes))
        )
    expected_hard_gate_checks = {
        "shadow-parity-clean": {
            "threshold": "active workspace shadow parity validator reads clean and required generated outputs are current",
            "evidence_sources": {
                "contracts/governance-engine-shadow-parity.yaml",
                "scripts/validate_governance_engine_shadow_parity.py",
            },
        },
        "boundary-projection-current": {
            "threshold": "generated boundary projection matches the current engine-versus-tenant split",
            "evidence_sources": {
                "contracts/governance-engine-boundary-map.yaml",
                "generated/governance-engine-boundary-map.json",
                "scripts/validate_cross_repo_truth.py",
            },
        },
        "stable-operator-entrypoints": {
            "threshold": "stable operator entrypoints remain unchanged or explicitly compatibility-shimmed",
            "evidence_sources": {
                "contracts/governance-engine-foundation.yaml",
                "docs/governance-engine-foundation.md",
                "scripts/validate_contracts.py",
            },
        },
        "security-delta-review-current": {
            "threshold": "current security review explicitly covers the parity boundary and proposed extraction delta",
            "evidence_sources": {
                "security-architecture/docs/reviews/platform/2026-04-25-governance-engine-parity-extraction-and-runtime-readiness.md",
            },
        },
        "governed-policy-stays-central": {
            "threshold": "repo-local validators and wiring do not redefine governed AI model-access policy",
            "evidence_sources": {
                "contracts/governance-engine-foundation.yaml",
                "scripts/validate_contracts.py",
            },
        },
    }
    actual_hard_gate_checks = {
        entry["gate_id"]: {
            "threshold": entry["threshold"],
            "evidence_sources": set(entry["evidence_sources"]),
        }
        for entry in governance_engine_extraction_gate["hard_gate_checks"]
    }
    if set(actual_hard_gate_checks) != set(expected_hard_gate_checks):
        errors.append(
            "contracts/governance-engine-extraction-gate.yaml: hard_gate_checks must define the current shadow-parity-clean, boundary-projection-current, stable-operator-entrypoints, security-delta-review-current, and governed-policy-stays-central checks"
        )
    else:
        for gate_id, expected in expected_hard_gate_checks.items():
            actual = actual_hard_gate_checks[gate_id]
            if actual["threshold"] != expected["threshold"]:
                errors.append(
                    f"contracts/governance-engine-extraction-gate.yaml: hard_gate_checks[{gate_id}].threshold must be {expected['threshold']!r}"
                )
            if actual["evidence_sources"] != expected["evidence_sources"]:
                errors.append(
                    "contracts/governance-engine-extraction-gate.yaml: "
                    f"hard_gate_checks[{gate_id}].evidence_sources must be exactly "
                    + ", ".join(sorted(expected["evidence_sources"]))
                )
    actual_current_hard_gate_results = {
        entry["gate_id"]: entry["status"]
        for entry in current_decision["hard_gate_results"]
    }
    if set(actual_current_hard_gate_results) != set(expected_hard_gate_checks):
        errors.append(
            "contracts/governance-engine-extraction-gate.yaml: current_decision.hard_gate_results must define the current shadow-parity-clean, boundary-projection-current, stable-operator-entrypoints, security-delta-review-current, and governed-policy-stays-central results"
        )
    else:
        invalid_hard_gate_statuses = {
            gate_id: status
            for gate_id, status in actual_current_hard_gate_results.items()
            if status not in {"passed", "failed"}
        }
        for gate_id, status in invalid_hard_gate_statuses.items():
            errors.append(
                "contracts/governance-engine-extraction-gate.yaml: "
                f"current_decision.hard_gate_results[{gate_id}].status must be 'passed' or 'failed', got {status!r}"
            )
    expected_extraction_need_signals = {
        "multi-instance-consumer-demand": {
            "threshold": "more than one governed workspace or tenant-instance consumer requires the same engine authoring layer",
            "evidence_sources": {
                "contracts/governance-engine-foundation.yaml",
                "contracts/governance-engine-boundary-map.yaml",
            },
        },
        "standalone-release-versioning-need": {
            "threshold": "standalone versioning or release cadence is required beyond the integrated workspace-governance repo",
            "evidence_sources": {
                "docs/governance-engine-foundation.md",
                "contracts/governance-engine-output-manifest.yaml",
            },
        },
        "bounded-package-and-consumption-contract-ready": {
            "threshold": "package installation and tenant-consumption contracts can be expressed without breaking stable operator entrypoints",
            "evidence_sources": {
                "contracts/governance-engine-output-manifest.yaml",
                "contracts/governance-engine-boundary-map.yaml",
            },
        },
    }
    actual_extraction_need_signals = {
        entry["signal_id"]: {
            "threshold": entry["threshold"],
            "evidence_sources": set(entry["evidence_sources"]),
        }
        for entry in governance_engine_extraction_gate["extraction_need_signals"]
    }
    if set(actual_extraction_need_signals) != set(expected_extraction_need_signals):
        errors.append(
            "contracts/governance-engine-extraction-gate.yaml: extraction_need_signals must define the current multi-instance-consumer-demand, standalone-release-versioning-need, and bounded-package-and-consumption-contract-ready signals"
        )
    else:
        for signal_id, expected in expected_extraction_need_signals.items():
            actual = actual_extraction_need_signals[signal_id]
            if actual["threshold"] != expected["threshold"]:
                errors.append(
                    f"contracts/governance-engine-extraction-gate.yaml: extraction_need_signals[{signal_id}].threshold must be {expected['threshold']!r}"
                )
            if actual["evidence_sources"] != expected["evidence_sources"]:
                errors.append(
                    "contracts/governance-engine-extraction-gate.yaml: "
                    f"extraction_need_signals[{signal_id}].evidence_sources must be exactly "
                    + ", ".join(sorted(expected["evidence_sources"]))
                )
    actual_current_signal_results = {
        entry["signal_id"]: {
            "status": entry["status"],
            "rationale": entry["rationale"],
        }
        for entry in current_decision["extraction_need_signal_results"]
    }
    if set(actual_current_signal_results) != set(expected_extraction_need_signals):
        errors.append(
            "contracts/governance-engine-extraction-gate.yaml: current_decision.extraction_need_signal_results must define the current multi-instance-consumer-demand, standalone-release-versioning-need, and bounded-package-and-consumption-contract-ready results"
        )
    else:
        invalid_signal_statuses = {
            signal_id: entry["status"]
            for signal_id, entry in actual_current_signal_results.items()
            if entry["status"] not in {"met", "not_met"}
        }
        for signal_id, status in invalid_signal_statuses.items():
            errors.append(
                "contracts/governance-engine-extraction-gate.yaml: "
                f"current_decision.extraction_need_signal_results[{signal_id}].status must be 'met' or 'not_met', got {status!r}"
            )
        empty_signal_rationales = [
            signal_id
            for signal_id, entry in actual_current_signal_results.items()
            if not entry["rationale"].strip()
        ]
        for signal_id in empty_signal_rationales:
            errors.append(
                "contracts/governance-engine-extraction-gate.yaml: "
                f"current_decision.extraction_need_signal_results[{signal_id}].rationale must be non-empty"
            )
    if not current_decision["rationale"].strip():
        errors.append(
            "contracts/governance-engine-extraction-gate.yaml: current_decision.rationale must be non-empty"
        )
    if not current_decision["deferred_follow_on_action"].strip():
        errors.append(
            "contracts/governance-engine-extraction-gate.yaml: current_decision.deferred_follow_on_action must be non-empty"
        )
    current_hard_gate_statuses = set(actual_current_hard_gate_results.values())
    current_signal_statuses = {entry["status"] for entry in actual_current_signal_results.values()}
    if (
        current_decision["outcome"] == extraction_decision["approved_outcome"]
        and (current_hard_gate_statuses != {"passed"} or current_signal_statuses != {"met"})
    ):
        errors.append(
            "contracts/governance-engine-extraction-gate.yaml: current_decision cannot approve standalone extraction unless every hard gate passes and every extraction-need signal is met"
        )
    if (
        current_decision["outcome"] == extraction_decision["default_outcome"]
        and current_hard_gate_statuses == {"passed"}
        and current_signal_statuses == {"met"}
    ):
        errors.append(
            "contracts/governance-engine-extraction-gate.yaml: current_decision cannot retain the integrated engine once every hard gate passes and every extraction-need signal is met"
        )
    if set(governance_engine_extraction_gate["deferred_follow_on_refs"]) != {
        "openproject://work_packages/247",
        "openproject://work_packages/251",
    }:
        errors.append(
            "contracts/governance-engine-extraction-gate.yaml: deferred_follow_on_refs must be exactly openproject://work_packages/247 and openproject://work_packages/251"
        )
    if (
        governance_engine_foundation["runtime_foundation"]["extraction_gate_ref"]
        != "contracts/governance-engine-extraction-gate.yaml"
    ):
        errors.append(
            "contracts/governance-engine-foundation.yaml: runtime_foundation.extraction_gate_ref must point to contracts/governance-engine-extraction-gate.yaml"
        )
    expected_instruction_bundle_authoring = {
        "AGENTS.md",
        "skills-src/",
        "contracts/skills.yaml",
        "contracts/repo-rules/",
    }
    actual_instruction_bundle_authoring = set(
        governance_engine_foundation["runtime_foundation"]["instruction_bundle_authoring"]
    )
    if actual_instruction_bundle_authoring != expected_instruction_bundle_authoring:
        errors.append(
            "contracts/governance-engine-foundation.yaml: runtime_foundation.instruction_bundle_authoring must be exactly "
            + ", ".join(sorted(expected_instruction_bundle_authoring))
        )
    model_access_and_audit = governance_engine_foundation["runtime_foundation"][
        "model_access_and_audit"
    ]
    if (
        model_access_and_audit["governed_intake_assist_contract_ref"]
        != "workspace-governance/contracts/governed-intake-assist.yaml"
    ):
        errors.append(
            "contracts/governance-engine-foundation.yaml: runtime_foundation.model_access_and_audit.governed_intake_assist_contract_ref must point to workspace-governance/contracts/governed-intake-assist.yaml"
        )
    expected_required_controls = {
        "approved profile plus governed invocation path",
        "workspace consumer contract before intake-assist use",
        "workload caller identity distinct from operator acceptance identity",
        "structured output contract for governance assistance",
        "human approval for governance decisions",
        "attributable audit emission",
        "no direct provider credentials in governed workloads",
    }
    if set(model_access_and_audit["required_controls"]) != expected_required_controls:
        errors.append(
            "contracts/governance-engine-foundation.yaml: runtime_foundation.model_access_and_audit.required_controls must be exactly "
            + ", ".join(sorted(expected_required_controls))
        )
    expected_required_audit_fields = {
        "caller_id",
        "operator_identity_or_acceptance_ref",
        "profile_id",
        "invocation_path",
        "decision_id",
        "event_time",
        "outcome",
        "override_reason_when_present",
    }
    if set(model_access_and_audit["required_audit_fields"]) != expected_required_audit_fields:
        errors.append(
            "contracts/governance-engine-foundation.yaml: runtime_foundation.model_access_and_audit.required_audit_fields must be exactly "
            + ", ".join(sorted(expected_required_audit_fields))
        )
    expected_sequencing_prerequisites = {
        "governance-engine boundary explicit",
        "compatibility boundary explicit",
        "shadow parity path explicit",
        "packaging model explicit",
        "governed model-access and audit contract reviewed",
        "governed intake-assist consumer contract explicit",
        "control-fabric operator workflow explicit",
    }
    actual_sequencing_prerequisites = set(
        governance_engine_foundation["runtime_foundation"]["sequencing_prerequisites"]
    )
    if actual_sequencing_prerequisites != expected_sequencing_prerequisites:
        errors.append(
            "contracts/governance-engine-foundation.yaml: runtime_foundation.sequencing_prerequisites must be exactly "
            + ", ".join(sorted(expected_sequencing_prerequisites))
        )
    if governance_control_fabric_operator_surface["owner_repo"] != "workspace-governance":
        errors.append(
            "contracts/governance-control-fabric-operator-surface.yaml: owner_repo must be 'workspace-governance'"
        )
    if (
        governance_control_fabric_operator_surface["runtime_repo"]
        != "workspace-governance-control-fabric"
    ):
        errors.append(
            "contracts/governance-control-fabric-operator-surface.yaml: runtime_repo must be 'workspace-governance-control-fabric'"
        )
    if (
        governance_control_fabric_operator_surface["foundation_ref"]
        != "contracts/governance-engine-foundation.yaml"
    ):
        errors.append(
            "contracts/governance-control-fabric-operator-surface.yaml: foundation_ref must point to contracts/governance-engine-foundation.yaml"
        )
    if (
        repo_root
        / governance_control_fabric_operator_surface["governance_surface_path"]
    ).suffix != ".md" or not (
        repo_root
        / governance_control_fabric_operator_surface["governance_surface_path"]
    ).exists():
        errors.append(
            "contracts/governance-control-fabric-operator-surface.yaml: governance_surface_path must point to an existing workspace-governance markdown surface"
        )
    expected_cli_command_ids = {
        "status",
        "sources-snapshot",
        "plan",
        "run",
        "inspect",
        "readiness",
        "ledger-tail",
        "explain",
    }
    actual_cli_command_ids = {
        entry["command_id"]
        for entry in governance_control_fabric_operator_surface["minimum_cli_surface"][
            "commands"
        ]
    }
    if not expected_cli_command_ids.issubset(actual_cli_command_ids):
        errors.append(
            "contracts/governance-control-fabric-operator-surface.yaml: minimum_cli_surface.commands must include "
            + ", ".join(sorted(expected_cli_command_ids))
        )
    expected_api_endpoint_ids = {
        "healthz",
        "readyz",
        "status",
        "source-snapshots-create",
        "validation-plans-create",
        "validation-runs-create",
        "receipts-get",
        "readiness-evaluate",
        "ledger-events-list",
        "decisions-explain",
    }
    actual_api_endpoint_ids = {
        entry["endpoint_id"]
        for entry in governance_control_fabric_operator_surface["minimum_api_surface"][
            "endpoints"
        ]
    }
    if not expected_api_endpoint_ids.issubset(actual_api_endpoint_ids):
        errors.append(
            "contracts/governance-control-fabric-operator-surface.yaml: minimum_api_surface.endpoints must include "
            + ", ".join(sorted(expected_api_endpoint_ids))
        )
    expected_record_ids = {
        "source-snapshot",
        "validation-plan",
        "validation-run",
        "control-receipt",
        "readiness-decision",
        "ledger-event",
        "authority-reference",
        "escalation-record",
    }
    actual_record_ids = {
        entry["record_id"]
        for entry in governance_control_fabric_operator_surface["record_contracts"]
    }
    if not expected_record_ids.issubset(actual_record_ids):
        errors.append(
            "contracts/governance-control-fabric-operator-surface.yaml: record_contracts must include "
            + ", ".join(sorted(expected_record_ids))
        )
    expected_profile_ids = {"local-read-only", "dev-integration", "governed-stage"}
    actual_profile_ids = {
        entry["profile_id"]
        for entry in governance_control_fabric_operator_surface["profiles"]
    }
    if not expected_profile_ids.issubset(actual_profile_ids):
        errors.append(
            "contracts/governance-control-fabric-operator-surface.yaml: profiles must include local-read-only, dev-integration, and governed-stage"
        )
    expected_blocker_triggers = {
        "unknown-authority-source",
        "stale-source-snapshot",
        "shadow-parity-failed",
        "missing-owner-boundary",
        "security-delta-required",
        "platform-release-gate-required",
    }
    actual_blocker_triggers = {
        entry["trigger_id"]
        for entry in governance_control_fabric_operator_surface["blocker_triggers"]
    }
    if not expected_blocker_triggers.issubset(actual_blocker_triggers):
        errors.append(
            "contracts/governance-control-fabric-operator-surface.yaml: blocker_triggers must include "
            + ", ".join(sorted(expected_blocker_triggers))
        )
    expected_denied_actions = {
        "mutate-workspace-governance-contracts",
        "mutate-platform-approved-deployment-state",
        "make-security-acceptance-decision",
        "mutate-delivery-art-directly",
        "execute-ai-autonomous-governance-decision",
        "hide-raw-validation-output-in-chat-only",
    }
    actual_denied_actions = set(
        governance_control_fabric_operator_surface["denied_actions"]
    )
    if not expected_denied_actions.issubset(actual_denied_actions):
        errors.append(
            "contracts/governance-control-fabric-operator-surface.yaml: denied_actions must include "
            + ", ".join(sorted(expected_denied_actions))
        )
    fabric_phase_ids = {
        entry["phase_id"]
        for entry in governance_control_fabric_operator_surface["operator_workflow"][
            "phases"
        ]
    }
    fabric_record_ids = actual_record_ids
    fabric_entrypoint_ids = actual_cli_command_ids | actual_api_endpoint_ids
    for phase in governance_control_fabric_operator_surface["operator_workflow"][
        "phases"
    ]:
        unknown_entrypoints = set(phase["entrypoint_ids"]) - fabric_entrypoint_ids
        if unknown_entrypoints:
            errors.append(
                "contracts/governance-control-fabric-operator-surface.yaml: "
                f"operator_workflow phase {phase['phase_id']!r} references unknown entrypoints "
                + ", ".join(sorted(unknown_entrypoints))
            )
        unknown_records = set(phase["produced_record_ids"]) - fabric_record_ids
        if unknown_records:
            errors.append(
                "contracts/governance-control-fabric-operator-surface.yaml: "
                f"operator_workflow phase {phase['phase_id']!r} references unknown record ids "
                + ", ".join(sorted(unknown_records))
            )
    for command in governance_control_fabric_operator_surface["minimum_cli_surface"][
        "commands"
    ]:
        if command["phase_id"] not in fabric_phase_ids:
            errors.append(
                "contracts/governance-control-fabric-operator-surface.yaml: "
                f"CLI command {command['command_id']!r} references unknown phase_id {command['phase_id']!r}"
            )
        if command["mutates_authority"] is not False:
            errors.append(
                "contracts/governance-control-fabric-operator-surface.yaml: "
                f"CLI command {command['command_id']!r} must not mutate authority"
            )
    for endpoint in governance_control_fabric_operator_surface["minimum_api_surface"][
        "endpoints"
    ]:
        if endpoint["phase_id"] not in fabric_phase_ids:
            errors.append(
                "contracts/governance-control-fabric-operator-surface.yaml: "
                f"API endpoint {endpoint['endpoint_id']!r} references unknown phase_id {endpoint['phase_id']!r}"
            )
        if endpoint["response_record_id"] not in fabric_record_ids:
            errors.append(
                "contracts/governance-control-fabric-operator-surface.yaml: "
                f"API endpoint {endpoint['endpoint_id']!r} references unknown response_record_id {endpoint['response_record_id']!r}"
            )
        if endpoint["mutates_authority"] is not False:
            errors.append(
                "contracts/governance-control-fabric-operator-surface.yaml: "
                f"API endpoint {endpoint['endpoint_id']!r} must not mutate authority"
            )
    workspace_root = repo_root.parent
    workspace_has_sibling_repos = any(
        (workspace_root / repo_name).exists()
        for repo_name in active_repos
        if repo_name != "workspace-governance"
    )
    required_cross_repo_refs = {
        model_access_and_audit["profile_registry_ref"],
        model_access_and_audit["governed_intake_assist_contract_ref"],
        *model_access_and_audit["standards_refs"],
        governance_engine_extraction_gate["security_review_ref"],
        governance_control_fabric_operator_surface[
            "runtime_primary_operator_surface_ref"
        ],
    }
    for ref in governed_contract_refs.values():
        required_cross_repo_refs.add(f"{ref['repo']}/{ref['path']}")
    if workspace_has_sibling_repos:
        for rel_path in sorted(required_cross_repo_refs):
            if not (workspace_root / rel_path).exists():
                errors.append(
                    "contracts/governance-engine-foundation.yaml: referenced path does not exist: "
                    + rel_path
                )
    if self_improvement_governance["policy_owner_repo"] not in active_repos:
        errors.append(
            "contracts/self-improvement-policy.yaml: governance.policy_owner_repo "
            f"{self_improvement_governance['policy_owner_repo']!r} is not an active repo"
        )
    if self_improvement_governance["policy_owner_repo"] != "workspace-governance":
        errors.append(
            "contracts/self-improvement-policy.yaml: governance.policy_owner_repo must be 'workspace-governance'"
        )
    if not self_improvement_governance["operator_surface_path"].endswith(".md"):
        errors.append(
            "contracts/self-improvement-policy.yaml: governance.operator_surface_path must point to a markdown instruction surface"
        )
    elif not (repo_root / self_improvement_governance["operator_surface_path"]).exists():
        errors.append(
            "contracts/self-improvement-policy.yaml: governance.operator_surface_path "
            f"{self_improvement_governance['operator_surface_path']!r} does not exist"
        )
    for skill_name in self_improvement_governance["required_skills"]:
        if skill_name not in registered_skills:
            errors.append(
                "contracts/self-improvement-policy.yaml: governance.required_skills references unknown "
                f"skill {skill_name!r}"
            )
    for signal_name in self_improvement_runtime_gate["require_candidate_before_continue_for"]:
        if signal_name not in self_improvement_signal_catalog:
            errors.append(
                "contracts/self-improvement-policy.yaml: runtime_gate.require_candidate_before_continue_for "
                f"references unknown signal {signal_name!r}"
            )
    for signal_name, payload in self_improvement_signal_catalog.items():
        if payload["default_trigger"] not in improvement_triggers:
            errors.append(
                "contracts/self-improvement-policy.yaml: signal_catalog "
                f"{signal_name!r} references unknown trigger {payload['default_trigger']!r}"
            )
        for failure_class in payload["default_failure_classes"]:
            if failure_class not in failure_classes:
                errors.append(
                    "contracts/self-improvement-policy.yaml: signal_catalog "
                    f"{signal_name!r} references unknown failure class {failure_class!r}"
                )
    for profile_name, payload in developer_integration_profiles["profiles"].items():
        if payload["lifecycle"] not in profile_lifecycle["statuses"]:
            errors.append(
                f"contracts/developer-integration-profiles.yaml: {profile_name} lifecycle {payload['lifecycle']!r} is not in the declared profile lifecycle set"
            )
        if payload["owner_repo"] not in active_repos:
            errors.append(
                f"contracts/developer-integration-profiles.yaml: {profile_name} owner_repo {payload['owner_repo']!r} is not an active repo"
            )
        for owner_key in ("runtime_owner", "security_owner"):
            if payload[owner_key] not in active_repos:
                errors.append(
                    f"contracts/developer-integration-profiles.yaml: {profile_name} {owner_key} {payload[owner_key]!r} is not an active repo"
                )
        for repo_ref in payload["shared_dependencies"] + payload["source_repos"]:
            if repo_ref not in active_repos:
                errors.append(
                    f"contracts/developer-integration-profiles.yaml: {profile_name} references unknown repo {repo_ref!r}"
                )
        if payload["stage_handoff"]["owner_repo"] not in active_repos:
            errors.append(
                f"contracts/developer-integration-profiles.yaml: {profile_name} stage_handoff owner_repo {payload['stage_handoff']['owner_repo']!r} is not an active repo"
            )
        required_checks = payload["stage_handoff"].get("required_checks") or []
        if not required_checks:
            errors.append(
                f"contracts/developer-integration-profiles.yaml: {profile_name} stage_handoff.required_checks must not be empty"
            )
        elif len(required_checks) != len(set(required_checks)):
            errors.append(
                f"contracts/developer-integration-profiles.yaml: {profile_name} stage_handoff.required_checks must be unique"
            )
        missing_actions = sorted(expected_devint_actions - set(payload["actions"]))
        if missing_actions:
            errors.append(
                f"contracts/developer-integration-profiles.yaml: {profile_name} actions must include required_actions; missing {', '.join(missing_actions)}"
            )
        if profile_lifecycle["request_record_required"]:
            request_record = payload.get("request_record") or {}
            if not request_record.get("system") or not request_record.get("ref"):
                errors.append(
                    f"contracts/developer-integration-profiles.yaml: {profile_name} is missing request_record.system or request_record.ref"
                )
        admission = payload.get("admission") or {}
        if payload["lifecycle"] in set(profile_lifecycle["platform_acceptance_required_for"]):
            for key in ("approved_by", "approved_on", "platform_acceptance_ref"):
                if not admission.get(key):
                    errors.append(
                        f"contracts/developer-integration-profiles.yaml: {profile_name} lifecycle {payload['lifecycle']!r} requires admission.{key}"
                    )
        if admission.get("security_review_required"):
            refs = admission.get("security_review_refs") or []
            if not refs and profile_lifecycle["security_review_ref_required_when_flagged"]:
                errors.append(
                    f"contracts/developer-integration-profiles.yaml: {profile_name} requires at least one admission.security_review_ref"
                )
            for ref in refs:
                if ref["repo"] not in active_repos:
                    errors.append(
                        f"contracts/developer-integration-profiles.yaml: {profile_name} security review repo {ref['repo']!r} is not an active repo"
                    )

    for repo_name, payload in contracts["repos"]["repos"].items():
        if payload["lifecycle"] not in lifecycle_states:
            errors.append(f"contracts/repos.yaml: {repo_name} uses unknown lifecycle {payload['lifecycle']!r}")
        for ref in payload["allowed_authoritative_refs"]:
            if ref not in active_repos:
                errors.append(f"contracts/repos.yaml: {repo_name} references unknown repo {ref!r}")
        if payload.get("security_review_subject") and "security-architecture" not in payload["allowed_authoritative_refs"]:
            errors.append(
                f"contracts/repos.yaml: {repo_name} sets security_review_subject but does not allow security-architecture as an authoritative ref"
            )

    for repo_name, payload in contracts["repos"].get("retired_repos", {}).items():
        if payload["lifecycle"] not in lifecycle_states:
            errors.append(f"contracts/repos.yaml: retired repo {repo_name} uses unknown lifecycle {payload['lifecycle']!r}")
        for replacement in payload["replaced_by"].values():
            if replacement not in active_repos:
                errors.append(f"contracts/repos.yaml: retired repo {repo_name} replacement {replacement!r} is not an active repo")

    repo_rules = contracts["repo_rules"]
    missing_rules = sorted(active_repos - set(repo_rules.keys()))
    if missing_rules:
        errors.append("contracts/repo-rules: missing active repo rules for " + ", ".join(missing_rules))
    for repo_name, rule in repo_rules.items():
        if repo_name not in active_repos:
            errors.append(f"contracts/repo-rules/{repo_name}.yaml: repo is not in active repos")
            continue
        repo_payload = contracts["repos"]["repos"][repo_name]
        if rule["lifecycle"] != repo_payload["lifecycle"]:
            errors.append(f"contracts/repo-rules/{repo_name}.yaml: lifecycle does not match repos.yaml")
        for ref in rule["required_repo_refs"]:
            if ref not in active_repos:
                errors.append(f"contracts/repo-rules/{repo_name}.yaml: unknown required_repo_ref {ref!r}")
        security_requirements = rule.get("security_requirements")
        security_change_record_requirements = rule.get("security_change_record_requirements")
        if repo_payload["requires_security_bindings"] and not security_requirements:
            errors.append(
                f"contracts/repo-rules/{repo_name}.yaml: missing security_requirements for repo requiring security bindings"
            )
        operator_workflow_requirements = rule.get("operator_workflow_requirements")
        if operator_workflow_requirements:
            seen_workflow_ids: set[str] = set()
            for workflow in operator_workflow_requirements["workflows"]:
                workflow_id = workflow["id"]
                if workflow_id in seen_workflow_ids:
                    errors.append(
                        f"contracts/repo-rules/{repo_name}.yaml: duplicate operator workflow id {workflow_id!r}"
                    )
                seen_workflow_ids.add(workflow_id)
                primary_surface_path = workflow["primary_surface_path"]
                if primary_surface_path.startswith("/"):
                    errors.append(
                        f"contracts/repo-rules/{repo_name}.yaml: operator workflow {workflow_id!r} primary_surface_path must be repo-relative"
                    )
                if "/" not in primary_surface_path:
                    errors.append(
                        f"contracts/repo-rules/{repo_name}.yaml: operator workflow {workflow_id!r} primary_surface_path should name a concrete repo path"
                    )
                if not primary_surface_path.endswith(".md"):
                    errors.append(
                        f"contracts/repo-rules/{repo_name}.yaml: operator workflow {workflow_id!r} primary_surface_path should point to a markdown instruction surface"
                    )
        if not security_requirements:
            continue
        if security_requirements["security_owner"] not in active_repos:
            errors.append(
                f"contracts/repo-rules/{repo_name}.yaml: security_owner {security_requirements['security_owner']!r} is not an active repo"
            )
        elif security_requirements["security_owner"] not in repo_payload["allowed_authoritative_refs"]:
            errors.append(
                f"contracts/repo-rules/{repo_name}.yaml: security_owner {security_requirements['security_owner']!r} is not an allowed authoritative ref"
            )
        for artifact in security_requirements["required_artifacts"]:
            unknown_areas = sorted(
                set(artifact["review_areas"])
                - set(contracts["review_obligations"]["review_obligations"])
            )
            if unknown_areas:
                errors.append(
                    f"contracts/repo-rules/{repo_name}.yaml: security artifact {artifact['id']} uses unknown review areas {', '.join(unknown_areas)}"
                )
        seen_trigger_ids: set[str] = set()
        for trigger in security_requirements["delta_review_triggers"]:
            trigger_id = trigger["id"]
            if trigger_id in seen_trigger_ids:
                errors.append(
                    f"contracts/repo-rules/{repo_name}.yaml: duplicate security delta review trigger id {trigger_id!r}"
                )
            seen_trigger_ids.add(trigger_id)
            unknown_areas = sorted(
                set(trigger["review_areas"])
                - set(contracts["review_obligations"]["review_obligations"])
            )
            if unknown_areas:
                errors.append(
                    f"contracts/repo-rules/{repo_name}.yaml: security delta review trigger {trigger_id!r} uses unknown review areas {', '.join(unknown_areas)}"
                )
            for subject in trigger["review_subjects"]:
                inventory_section = subject["inventory_section"]
                subject_name = subject["name"]
                if inventory_section == "repos" and subject_name not in active_repos:
                    errors.append(
                        f"contracts/repo-rules/{repo_name}.yaml: security delta review trigger {trigger_id!r} references unknown repo subject {subject_name!r}"
                    )
                elif inventory_section == "components" and subject_name not in component_names:
                    errors.append(
                        f"contracts/repo-rules/{repo_name}.yaml: security delta review trigger {trigger_id!r} references unknown component subject {subject_name!r}"
                    )
                elif inventory_section == "products" and subject_name not in product_names:
                    errors.append(
                        f"contracts/repo-rules/{repo_name}.yaml: security delta review trigger {trigger_id!r} references unknown product subject {subject_name!r}"
                    )
        if security_change_record_requirements and not security_requirements:
            errors.append(
                f"contracts/repo-rules/{repo_name}.yaml: security_change_record_requirements require security_requirements"
            )

    for product_name, payload in contracts["products"]["products"].items():
        if payload["lifecycle"] not in lifecycle_states:
            errors.append(f"contracts/products.yaml: {product_name} uses unknown lifecycle {payload['lifecycle']!r}")
        for owner_key in ("platform_owner", "security_owner", "runtime_owner"):
            if payload[owner_key] not in active_repos:
                errors.append(f"contracts/products.yaml: {product_name} {owner_key} {payload[owner_key]!r} is not an active repo")
        for repo_name in payload["source_owners"]:
            if repo_name not in active_repos:
                errors.append(f"contracts/products.yaml: {product_name} source owner {repo_name!r} is not an active repo")

    for component_name, payload in contracts["components"]["components"].items():
        if payload["lifecycle"] not in lifecycle_states:
            errors.append(f"contracts/components.yaml: {component_name} uses unknown lifecycle {payload['lifecycle']!r}")
        if payload["owner_repo"] not in active_repos:
            errors.append(f"contracts/components.yaml: {component_name} owner_repo {payload['owner_repo']!r} is not an active repo")
        if payload["security_owner"] not in active_repos:
            errors.append(f"contracts/components.yaml: {component_name} security_owner {payload['security_owner']!r} is not an active repo")
        if payload["product"] is not None and payload["product"] not in product_names:
            errors.append(f"contracts/components.yaml: {component_name} product {payload['product']!r} is not declared in products.yaml")

    duplicate_repos = sorted((active_repos | set(contracts["repos"].get("retired_repos", {}).keys())) & intake_repos)
    if duplicate_repos:
        errors.append(
            "contracts/intake-register.yaml: repos must not overlap repos.yaml or retired_repos: "
            + ", ".join(duplicate_repos)
        )
    duplicate_products = sorted(product_names & intake_products)
    if duplicate_products:
        errors.append(
            "contracts/intake-register.yaml: products must not overlap products.yaml: "
            + ", ".join(duplicate_products)
        )
    duplicate_components = sorted(component_names & intake_components)
    if duplicate_components:
        errors.append(
            "contracts/intake-register.yaml: components must not overlap components.yaml: "
            + ", ".join(duplicate_components)
        )

    in_scope_statuses = {"proposed", "admitted"}
    admissible_repo_refs = active_repos | intake_repos
    admissible_product_refs = product_names | intake_products

    for repo_name, payload in intake_register["repos"].items():
        if payload["status"] not in intake_statuses:
            errors.append(
                f"contracts/intake-register.yaml: repo {repo_name} uses unknown status {payload['status']!r}"
            )
        if payload["decision_source"] not in {"operator", "ai-suggested"}:
            errors.append(
                f"contracts/intake-register.yaml: repo {repo_name} decision_source must be operator or ai-suggested"
            )
        if payload["status"] in in_scope_statuses:
            if not payload["repo_class"]:
                errors.append(
                    f"contracts/intake-register.yaml: repo {repo_name} in scope must declare repo_class"
                )
            if payload["requires_security_bindings"] is None:
                errors.append(
                    f"contracts/intake-register.yaml: repo {repo_name} in scope must declare requires_security_bindings"
                )
            if payload["requires_security_bindings"]:
                if not payload["security_owner"]:
                    errors.append(
                        f"contracts/intake-register.yaml: repo {repo_name} requires security bindings but has no security_owner"
                    )
                elif payload["security_owner"] not in active_repos:
                    errors.append(
                        f"contracts/intake-register.yaml: repo {repo_name} security_owner {payload['security_owner']!r} is not an active repo"
                    )
        elif payload["security_owner"] is not None and payload["security_owner"] not in active_repos:
            errors.append(
                f"contracts/intake-register.yaml: repo {repo_name} security_owner {payload['security_owner']!r} is not an active repo"
            )

    for product_name, payload in intake_register["products"].items():
        if payload["status"] not in intake_statuses:
            errors.append(
                f"contracts/intake-register.yaml: product {product_name} uses unknown status {payload['status']!r}"
            )
        if payload["decision_source"] not in {"operator", "ai-suggested"}:
            errors.append(
                f"contracts/intake-register.yaml: product {product_name} decision_source must be operator or ai-suggested"
            )
        if payload["status"] in in_scope_statuses and intake_policy["products"]["require_owner_metadata_when_in_scope"]:
            for owner_key in ("platform_owner", "security_owner", "runtime_owner"):
                if not payload[owner_key]:
                    errors.append(
                        f"contracts/intake-register.yaml: product {product_name} in scope must declare {owner_key}"
                    )
                elif payload[owner_key] not in active_repos:
                    errors.append(
                        f"contracts/intake-register.yaml: product {product_name} {owner_key} {payload[owner_key]!r} is not an active repo"
                    )
            if not payload["source_owners"]:
                errors.append(
                    f"contracts/intake-register.yaml: product {product_name} in scope must declare source_owners"
                )
            for repo_name in payload["source_owners"]:
                if repo_name not in admissible_repo_refs:
                    errors.append(
                        f"contracts/intake-register.yaml: product {product_name} source owner {repo_name!r} is not an active or intake-classified repo"
                    )
            if not payload["intended_endpoint"]:
                errors.append(
                    f"contracts/intake-register.yaml: product {product_name} in scope must declare intended_endpoint"
                )

    for component_name, payload in intake_register["components"].items():
        if payload["status"] not in intake_statuses:
            errors.append(
                f"contracts/intake-register.yaml: component {component_name} uses unknown status {payload['status']!r}"
            )
        if payload["decision_source"] not in {"operator", "ai-suggested"}:
            errors.append(
                f"contracts/intake-register.yaml: component {component_name} decision_source must be operator or ai-suggested"
            )
        if payload["status"] in in_scope_statuses and intake_policy["components"]["require_owner_metadata_when_in_scope"]:
            if not payload["component_class"]:
                errors.append(
                    f"contracts/intake-register.yaml: component {component_name} in scope must declare component_class"
                )
            if not payload["owner_repo"]:
                errors.append(
                    f"contracts/intake-register.yaml: component {component_name} in scope must declare owner_repo"
                )
            elif payload["owner_repo"] not in admissible_repo_refs:
                errors.append(
                    f"contracts/intake-register.yaml: component {component_name} owner_repo {payload['owner_repo']!r} is not an active or intake-classified repo"
                )
            if not payload["security_owner"]:
                errors.append(
                    f"contracts/intake-register.yaml: component {component_name} in scope must declare security_owner"
                )
            elif payload["security_owner"] not in active_repos:
                errors.append(
                    f"contracts/intake-register.yaml: component {component_name} security_owner {payload['security_owner']!r} is not an active repo"
                )
            if payload["product"] is not None and payload["product"] not in admissible_product_refs:
                errors.append(
                    f"contracts/intake-register.yaml: component {component_name} product {payload['product']!r} is not an active or intake-classified product"
                )

    for task_type, payload in contracts["task_types"]["task_types"].items():
        if payload["primary_repo"] not in active_repos:
            errors.append(f"contracts/task-types.yaml: {task_type} primary_repo {payload['primary_repo']!r} is not an active repo")
        if payload["change_class"] not in change_classes:
            errors.append(f"contracts/task-types.yaml: {task_type} change_class {payload['change_class']!r} is not declared")

    evidence_keys = set(contracts["evidence_obligations"]["evidence_by_change_class"].keys())
    if evidence_keys != change_classes:
        errors.append("contracts/evidence-obligations.yaml: change-class coverage does not match contracts/change-classes.yaml")

    if not failure_classes:
        errors.append("contracts/failure-taxonomy.yaml: failure_classes must not be empty")
    if not improvement_triggers:
        errors.append("contracts/improvement-triggers.yaml: triggers must not be empty")

    for validator_name, payload in validator_scripts.items():
        script_path = repo_root / payload["script"]
        if not script_path.exists():
            errors.append(f"contracts/validation-matrix.yaml: validator {validator_name} references missing script {payload['script']}")
        for rel_path in payload.get("generated_outputs", []):
            if not (repo_root / rel_path).exists():
                errors.append(f"contracts/validation-matrix.yaml: validator {validator_name} expects missing generated artifact {rel_path}")

    for entry in contracts["exceptions"]["exceptions"]:
        if entry["owner"] not in active_repos:
            errors.append(f"contracts/exceptions.yaml: exception {entry['id']} owner {entry['owner']!r} is not an active repo")
        branch_lifecycle_waivers = [
            waiver for waiver in entry["waives"] if waiver in BRANCH_LIFECYCLE_WAIVER_KINDS
        ]
        if branch_lifecycle_waivers:
            target_match = BRANCH_LIFECYCLE_TARGET_RE.fullmatch(entry["target"])
            if not target_match:
                errors.append(
                    f"contracts/exceptions.yaml: exception {entry['id']} target must match "
                    "'repo:<repo>:<kind>:<value>' for branch-lifecycle waivers"
                )
            else:
                known_repo_refs = active_repos | intake_repos | retired_repos
                target_repo = target_match.group("repo")
                target_kind = target_match.group("kind")
                if target_repo not in known_repo_refs:
                    errors.append(
                        f"contracts/exceptions.yaml: exception {entry['id']} references unknown repo {target_repo!r}"
                    )
                for waiver in branch_lifecycle_waivers:
                    expected_kind = BRANCH_LIFECYCLE_WAIVER_KINDS[waiver]
                    if target_kind != expected_kind:
                        errors.append(
                            f"contracts/exceptions.yaml: exception {entry['id']} waiver {waiver!r} "
                            f"requires target kind {expected_kind!r}, got {target_kind!r}"
                        )
        try:
            expires_on = date.fromisoformat(entry["expires_on"])
        except ValueError:
            errors.append(
                f"contracts/exceptions.yaml: exception {entry['id']} has invalid expires_on {entry['expires_on']!r}"
            )
            continue
        if expires_on < date.today():
            errors.append(
                f"contracts/exceptions.yaml: exception {entry['id']} expired on {entry['expires_on']}"
            )

    for skill_name, payload in registered_skills.items():
        if payload["owner_repo"] not in active_repos:
            errors.append(
                f"contracts/skills.yaml: {skill_name} owner_repo {payload['owner_repo']!r} is not an active repo"
            )
        if Path(payload["source_path"]).name != skill_name:
            errors.append(
                f"contracts/skills.yaml: {skill_name} source_path must end in the skill name"
            )

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print(
        "contract model valid: "
        f"active_repos={len(active_repos)} "
        f"intake_repos={len(intake_repos)} "
        f"products={len(product_names)} "
        f"intake_products={len(intake_products)} "
        f"components={len(contracts['components']['components'])} "
        f"intake_components={len(intake_components)} "
        f"repo_rules={len(repo_rules)} "
        f"skills={len(registered_skills)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
