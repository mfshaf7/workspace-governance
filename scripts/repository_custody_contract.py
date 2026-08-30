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

    lifecycle = contract.get("repository_lifecycle", {})
    lifecycle_axes = lifecycle.get("state_axes", {})
    expected_axes = {
        "custody": {"linked", "provisioned"},
        "provider": {"active", "archived", "unavailable"},
        "workspace_record": {"active", "retired"},
    }
    for axis_id, expected_states in expected_axes.items():
        actual_states = set(lifecycle_axes.get(axis_id, {}).get("states", []))
        if actual_states != expected_states:
            issues.append(
                f"repository_lifecycle.state_axes.{axis_id} must define: "
                + ", ".join(sorted(expected_states))
            )

    expected_lifecycle_actions = {
        "transfer-workspace-custody",
        "archive-provider",
        "unarchive-provider",
        "retire-workspace-record",
        "restore-workspace-record",
    }
    lifecycle_actions = lifecycle.get("actions", {})
    if set(lifecycle_actions) != expected_lifecycle_actions:
        issues.append("repository_lifecycle.actions must define the bounded v1 action set")

    provider_actions = {"archive-provider", "unarchive-provider"}
    for action_id, action in lifecycle_actions.items():
        expected_provider_mutation = action_id in provider_actions
        if action.get("provider_mutation") is not expected_provider_mutation:
            issues.append(
                f"repository lifecycle action {action_id!r} has the wrong provider mutation boundary"
            )
        if action.get("required_provider_readback") is not expected_provider_mutation:
            issues.append(
                f"repository lifecycle action {action_id!r} has the wrong provider readback boundary"
            )

    dispositions = set(
        lifecycle.get("impact_preflight", {}).get("blocker_dispositions", [])
    )
    if dispositions != {"remove", "workaround", "accept-risk", "defer"}:
        issues.append("repository lifecycle blocker dispositions are incomplete")

    if lifecycle.get("audit_projection", {}).get("mutation") is not False:
        issues.append("repository lifecycle audit must remain read-only")

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

    expected_lifecycle_evidence = [
        "repository-lifecycle-request",
        "repository-lifecycle-decision",
        "repository-provider-readback",
        "repository-lifecycle-receipt",
    ]
    actual_lifecycle_evidence = contract.get("evidence_chain", {}).get(
        "lifecycle_ordered_artifacts"
    )
    if actual_lifecycle_evidence != expected_lifecycle_evidence:
        issues.append(
            "evidence_chain.lifecycle_ordered_artifacts must preserve the canonical order"
        )

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

    required_lifecycle_work = {
        "openproject://work_packages/1050",
        "openproject://work_packages/1058",
        "openproject://work_packages/1052",
        "openproject://work_packages/1059",
        "openproject://work_packages/1051",
        "openproject://work_packages/1053",
    }
    if not required_lifecycle_work.issubset(activation_refs):
        issues.append("runtime activation omits required lifecycle work items")

    return issues


def lifecycle_request_issues(request: dict) -> list[str]:
    issues: list[str] = []
    action = request.get("action")
    current = request.get("current_state", {})
    target = request.get("target", {})
    impact = request.get("impact", {})

    finding_count = impact.get("finding_count", 0)
    blocking_count = impact.get("blocking_finding_count", 0)
    if blocking_count > finding_count:
        issues.append("blocking_finding_count cannot exceed finding_count")

    if action == "transfer-workspace-custody":
        if target.get("workspace_owner_ref") == current.get("workspace_owner_ref"):
            issues.append("workspace custody transfer must select a different owner")
        if current.get("workspace_record_state") != "active":
            issues.append("workspace custody transfer requires an active workspace record")
    elif action == "archive-provider" and current.get("provider_lifecycle_state") != "active":
        issues.append("provider archive requires current provider state active")
    elif action == "unarchive-provider" and current.get("provider_lifecycle_state") != "archived":
        issues.append("provider unarchive requires current provider state archived")
    elif action == "retire-workspace-record" and current.get("workspace_record_state") != "active":
        issues.append("workspace retirement requires current workspace record state active")
    elif action == "restore-workspace-record" and current.get("workspace_record_state") != "retired":
        issues.append("workspace restore requires current workspace record state retired")

    return issues


def lifecycle_receipt_issues(receipt: dict) -> list[str]:
    issues: list[str] = []
    action = receipt.get("action")
    outcome = receipt.get("outcome")
    before = receipt.get("before", {})
    after = receipt.get("after", {})
    provider_readback_ref = receipt.get("provider_readback_ref")

    if outcome != "succeeded":
        if before != after:
            issues.append("non-successful lifecycle receipt must preserve its before state")
        return issues

    provider_actions = {"archive-provider", "unarchive-provider"}
    if action in provider_actions and provider_readback_ref is None:
        issues.append("successful provider lifecycle action requires provider readback")
    if action not in provider_actions and provider_readback_ref is not None:
        issues.append("successful workspace-only lifecycle action cannot claim provider readback")

    if before.get("custody_state") != after.get("custody_state"):
        issues.append("lifecycle action cannot change custody origin state")

    if action == "transfer-workspace-custody":
        if before.get("workspace_owner_ref") == after.get("workspace_owner_ref"):
            issues.append("workspace custody transfer must change workspace owner")
        for field in (
            "provider_lifecycle_state",
            "workspace_record_state",
            "provider_version",
        ):
            if before.get(field) != after.get(field):
                issues.append(f"workspace custody transfer cannot change {field}")
    elif action in provider_actions:
        for field in ("workspace_owner_ref", "workspace_record_state"):
            if before.get(field) != after.get(field):
                issues.append(f"provider lifecycle action cannot change {field}")
    elif action in {"retire-workspace-record", "restore-workspace-record"}:
        for field in (
            "workspace_owner_ref",
            "provider_lifecycle_state",
            "provider_version",
        ):
            if before.get(field) != after.get(field):
                issues.append(f"workspace record lifecycle action cannot change {field}")

    return issues
