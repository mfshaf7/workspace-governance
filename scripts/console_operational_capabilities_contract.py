from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
import re
from typing import Any


REQUIRED_DIMENSIONS = {
    "contract_state": ["missing", "defined"],
    "implementation_state": ["absent", "planned", "implemented"],
    "runtime_state": ["unavailable", "degraded", "available"],
    "evidence_state": ["unproven", "validated"],
    "demonstration_source": [
        "none",
        "fixture",
        "disconnected-preview",
        "live-authority",
    ],
}
REQUIRED_PROFILES = {
    "planned": {
        "contract_state": "defined",
        "implementation_state": "planned",
        "runtime_state": "unavailable",
        "evidence_state": "unproven",
        "demonstration_source": "none",
    },
    "implemented-uncommissioned": {
        "contract_state": "defined",
        "implementation_state": "implemented",
        "runtime_state": "unavailable",
        "evidence_state": "validated",
        "demonstration_source": "none",
    },
    "fixture-demonstration": {
        "contract_state": "defined",
        "implementation_state": "implemented",
        "runtime_state": "unavailable",
        "evidence_state": "validated",
        "demonstration_source": "fixture",
    },
    "disconnected-preview": {
        "contract_state": "defined",
        "implementation_state": "implemented",
        "runtime_state": "unavailable",
        "evidence_state": "validated",
        "demonstration_source": "disconnected-preview",
    },
    "degraded-live": {
        "contract_state": "defined",
        "implementation_state": "implemented",
        "runtime_state": "degraded",
        "evidence_state": "validated",
        "demonstration_source": "live-authority",
    },
    "operational-live": {
        "contract_state": "defined",
        "implementation_state": "implemented",
        "runtime_state": "available",
        "evidence_state": "validated",
        "demonstration_source": "live-authority",
    },
}
REQUIRED_STAGES = [
    "idea-and-proposal",
    "prototype-incubation",
    "delivery-planning",
    "architecture-decision",
    "repository-custody",
    "source-realization",
    "human-review",
    "security-acceptance",
    "source-merge",
    "workspace-intake-and-inventory",
    "runtime-and-release",
    "product-portfolio",
    "interruption-recovery-and-audit",
]
REQUIRED_PROOF_CLASSES = {"positive", "negative", "terminal"}
REQUIRED_CAPABILITY_FIELDS = {
    "id",
    "journey_order",
    "journey_stage",
    "canonical_authority_ref",
    "workflow_owner_repo",
    "read_model_id",
    "operator_intent_ids",
    "lifecycle_state_ids",
    "failure_state_ids",
    "recovery_action_ids",
    "proof_classes",
    "activation_work_item_refs",
    "authority_refs",
    "observed_status",
}
WORK_ITEM_REF = re.compile(r"^openproject://work_packages/[1-9][0-9]*$")


def capability_model(contract: Mapping[str, Any]) -> Mapping[str, Any]:
    model = contract.get("console_operational_capabilities", {})
    return model if isinstance(model, Mapping) else {}


def _duplicates(values: list[Any]) -> list[Any]:
    seen: set[Any] = set()
    duplicates: set[Any] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return sorted(duplicates)


def contract_issues(
    contract: Mapping[str, Any],
    *,
    known_repos: set[str],
    repo_root: Path | None = None,
) -> list[str]:
    model = capability_model(contract)
    issues: list[str] = []

    for field in ("owner_repo", "console_adapter_repo", "orchestration_owner_repo"):
        if model.get(field) not in known_repos:
            issues.append(f"{field} references unknown repo {model.get(field)!r}")
    if model.get("console_adapter_repo") != "governance-operations-console":
        issues.append("console_adapter_repo must remain governance-operations-console")
    if model.get("orchestration_owner_repo") != "operator-orchestration-service":
        issues.append("orchestration_owner_repo must remain operator-orchestration-service")

    if model.get("status_dimensions") != REQUIRED_DIMENSIONS:
        issues.append("status_dimensions must preserve the five independent truth dimensions")
    if model.get("status_profiles") != REQUIRED_PROFILES:
        issues.append("status_profiles must preserve truthful planned, preview, degraded, and live profiles")

    operating_truth = model.get("operating_truth", {})
    if operating_truth.get("observation_scope") != "local-dev-integration":
        issues.append("operating truth must remain scoped to local-dev-integration")
    if operating_truth.get("reuse_requires_profile") != "operational-live":
        issues.append("capability reuse must require the operational-live profile")
    if operating_truth.get("fresh_evidence_required") is not True:
        issues.append("capability reuse must require fresh evidence")
    if operating_truth.get("stale_or_missing_behavior") != "not-reusable":
        issues.append("stale or missing operating truth must not be reusable")
    if not operating_truth.get("source_ref"):
        issues.append("operating truth must cite its exact observation source")

    fixture = model.get("fixture_boundary", {})
    if fixture.get("live_mode_source") != "live-authority":
        issues.append("live mode must use live-authority data")
    if fixture.get("live_owner_unavailable_behavior") != "fail-closed-visible":
        issues.append("live owner unavailability must fail closed visibly")
    if fixture.get("fixture_completion_evidence_allowed") is not False:
        issues.append("fixture evidence cannot prove completion")
    if fixture.get("fixture_live_fallback_allowed") is not False:
        issues.append("fixture fallback cannot be enabled in live mode")

    completeness = model.get("plan_completeness", {})
    if set(completeness.get("required_capability_fields", [])) != REQUIRED_CAPABILITY_FIELDS:
        issues.append("plan completeness must require owner, intent, state, recovery, and proof fields")
    if set(completeness.get("required_proof_classes", [])) != REQUIRED_PROOF_CLASSES:
        issues.append("plan completeness must require positive, negative, and terminal proof")
    if completeness.get("required_journey_stages") != REQUIRED_STAGES:
        issues.append("plan completeness must preserve the complete ordered idea-to-product journey")
    if completeness.get("terminal_completion_profile") != "operational-live":
        issues.append("terminal completion must require the operational-live profile")
    if completeness.get("hidden_cli_state_transition_allowed") is not False:
        issues.append("hidden CLI state transitions must remain prohibited")
    if completeness.get("console_owned_canonical_state_allowed") is not False:
        issues.append("Console-owned canonical lifecycle state must remain prohibited")

    capabilities = model.get("capabilities", [])
    ids = [entry.get("id") for entry in capabilities if isinstance(entry, Mapping)]
    orders = [entry.get("journey_order") for entry in capabilities if isinstance(entry, Mapping)]
    stages = [entry.get("journey_stage") for entry in capabilities if isinstance(entry, Mapping)]
    if _duplicates(ids):
        issues.append(f"capability ids must be unique: {_duplicates(ids)}")
    if _duplicates(orders):
        issues.append(f"journey orders must be unique: {_duplicates(orders)}")
    if orders != list(range(1, len(REQUIRED_STAGES) + 1)):
        issues.append(
            f"capability journey_order must be contiguous from 1 through {len(REQUIRED_STAGES)}"
        )
    if stages != REQUIRED_STAGES:
        issues.append("capabilities must cover each required journey stage exactly once and in order")

    for index, capability in enumerate(capabilities, start=1):
        if not isinstance(capability, Mapping):
            issues.append(f"capability {index} must be an object")
            continue
        label = f"capability {capability.get('id', index)!r}"
        missing = REQUIRED_CAPABILITY_FIELDS - set(capability)
        if missing:
            issues.append(f"{label} is missing required fields: {', '.join(sorted(missing))}")
        owner_repo = capability.get("workflow_owner_repo")
        if owner_repo not in known_repos:
            issues.append(f"{label} references unknown workflow owner {owner_repo!r}")
        if owner_repo == model.get("console_adapter_repo"):
            issues.append(f"{label} cannot assign canonical workflow ownership to the Console adapter")
        for field in (
            "operator_intent_ids",
            "lifecycle_state_ids",
            "failure_state_ids",
            "recovery_action_ids",
            "activation_work_item_refs",
            "authority_refs",
        ):
            values = capability.get(field, [])
            if not values:
                issues.append(f"{label} must declare at least one {field}")
            elif _duplicates(list(values)):
                issues.append(f"{label} contains duplicate {field}")
        if set(capability.get("proof_classes", [])) != REQUIRED_PROOF_CLASSES:
            issues.append(f"{label} must require positive, negative, and terminal proof")
        observed_status = capability.get("observed_status", {})
        profile_name = observed_status.get("profile")
        profile = REQUIRED_PROFILES.get(profile_name)
        if profile is None:
            issues.append(f"{label} has unknown observed status profile {profile_name!r}")
        elif {
            key: observed_status.get(key)
            for key in REQUIRED_DIMENSIONS
        } != profile:
            issues.append(f"{label} observed status must exactly match profile {profile_name!r}")
        for ref in capability.get("activation_work_item_refs", []):
            if not isinstance(ref, str) or not WORK_ITEM_REF.fullmatch(ref):
                issues.append(f"{label} has invalid activation work item ref {ref!r}")
        for ref in capability.get("authority_refs", []):
            if not isinstance(ref, str) or ref.startswith("/") or ".." in ref.split("/"):
                issues.append(f"{label} has unsafe authority ref {ref!r}")
            elif repo_root is not None and not (repo_root / ref).is_file():
                issues.append(f"{label} references missing authority file {ref!r}")

    return issues


def generated_view(contract: Mapping[str, Any]) -> dict[str, Any]:
    model = capability_model(contract)
    return {
        "schema_version": contract.get("schema_version"),
        "contract_id": model.get("contract_id"),
        "target_scope": model.get("target_scope"),
        "target_outcome": model.get("target_outcome"),
        "terminal_completion_profile": model.get("plan_completeness", {}).get(
            "terminal_completion_profile"
        ),
        "truth_dimensions": list(model.get("status_dimensions", {}).keys()),
        "operating_truth": model.get("operating_truth"),
        "fixture_boundary": model.get("fixture_boundary"),
        "capabilities": [
            {
                "id": capability.get("id"),
                "journey_order": capability.get("journey_order"),
                "journey_stage": capability.get("journey_stage"),
                "canonical_authority_ref": capability.get("canonical_authority_ref"),
                "workflow_owner_repo": capability.get("workflow_owner_repo"),
                "read_model_id": capability.get("read_model_id"),
                "operator_intent_ids": capability.get("operator_intent_ids"),
                "lifecycle_state_ids": capability.get("lifecycle_state_ids"),
                "failure_state_ids": capability.get("failure_state_ids"),
                "recovery_action_ids": capability.get("recovery_action_ids"),
                "proof_classes": capability.get("proof_classes"),
                "activation_work_item_refs": capability.get("activation_work_item_refs"),
                "authority_refs": capability.get("authority_refs"),
                "observed_status": capability.get("observed_status"),
                "observed_profile_qualifies_for_reuse": capability.get(
                    "observed_status", {}
                ).get("profile")
                == model.get("operating_truth", {}).get("reuse_requires_profile"),
            }
            for capability in model.get("capabilities", [])
        ],
    }
