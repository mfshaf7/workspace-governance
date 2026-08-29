from __future__ import annotations

from collections.abc import Iterable


def contract_issues(contract: dict, active_repo_names: Iterable[str]) -> list[str]:
    issues: list[str] = []
    active_repos = set(active_repo_names)
    custody_states = set(contract.get("custody_states", {}))

    for role_id, role in contract.get("authority_roles", {}).items():
        owner_repo = role.get("owner_repo")
        if owner_repo and owner_repo not in active_repos:
            issues.append(
                f"authority role {role_id!r} references inactive owner_repo {owner_repo!r}"
            )

    for action_id, action in contract.get("actions", {}).items():
        for field in ("allowed_from", "allowed_to"):
            unknown = set(action.get(field, [])) - custody_states
            if unknown:
                issues.append(
                    f"action {action_id!r} {field} references unknown custody states: "
                    + ", ".join(sorted(unknown))
                )

    for handoff_id, handoff in contract.get("downstream_handoffs", {}).items():
        owner_repo = handoff.get("owner_repo")
        if owner_repo and owner_repo not in active_repos:
            issues.append(
                f"downstream handoff {handoff_id!r} references inactive owner_repo {owner_repo!r}"
            )

    expected_evidence = [
        "repository-custody-request",
        "repository-custody-decision",
        "repository-provider-readback",
        "repository-custody-receipt",
    ]
    actual_evidence = contract.get("evidence_chain", {}).get("ordered_artifacts")
    if actual_evidence != expected_evidence:
        issues.append("evidence_chain.ordered_artifacts must preserve the canonical order")

    if contract.get("runtime_activation", {}).get("enabled") is not False:
        issues.append("runtime activation must remain disabled while maturity is contract-only")

    provisioning = contract.get("provisioning_controls", {})
    first_scope = provisioning.get("first_provider_scope", {})
    if (
        first_scope.get("provider") != "github"
        or first_scope.get("provider_host") != "github.com"
        or first_scope.get("owner_scope") != "organization"
    ):
        issues.append(
            "provisioning_controls.first_provider_scope must remain GitHub organization-only"
        )

    expected_request_controls = {
        "organization-owner",
        "repository-name",
        "description",
        "visibility",
        "initialize-with-readme",
        "feature-toggles",
        "merge-policy",
        "exact-operator-approval",
        "credential-binding",
        "idempotency-binding",
    }
    actual_request_controls = set(provisioning.get("required_request_controls", []))
    missing_request_controls = expected_request_controls - actual_request_controls
    if missing_request_controls:
        issues.append(
            "provisioning_controls.required_request_controls is missing: "
            + ", ".join(sorted(missing_request_controls))
        )

    settings = provisioning.get("settings", {})
    expected_features = {"issues", "projects", "wiki", "discussions"}
    expected_merge_policy = {
        "allow_squash_merge",
        "allow_merge_commit",
        "allow_rebase_merge",
        "delete_branch_on_merge",
    }
    if set(settings.get("features", {}).get("fields", [])) != expected_features:
        issues.append("provisioning_controls.settings.features fields are incomplete")
    if set(settings.get("merge_policy", {}).get("fields", [])) != expected_merge_policy:
        issues.append("provisioning_controls.settings.merge_policy fields are incomplete")
    if settings.get("initialization", {}).get("initialize_with_readme") is not True:
        issues.append("provisioning must initialize the repository with a README")

    required_provisioning_work = {
        "openproject://work_packages/1054",
        "openproject://work_packages/1055",
        "openproject://work_packages/1046",
        "openproject://work_packages/1047",
        "openproject://work_packages/1048",
        "openproject://work_packages/1049",
    }
    activation_refs = set(
        contract.get("runtime_activation", {}).get("required_work_item_refs", [])
    )
    if not required_provisioning_work.issubset(activation_refs):
        issues.append("runtime activation omits required provisioning work items")

    return issues
