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

    return issues
