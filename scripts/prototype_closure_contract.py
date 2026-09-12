"""Semantic checks shared by Prototype closure contract fixtures and owners."""

from __future__ import annotations


ACTIONS = {
    "apply-delivery",
    "graduate-source",
    "retire-incubation",
    "reopen-incubation",
}
EVENTS = {
    "apply-delivery": "delivery-accepted",
    "graduate-source": "source-graduated",
    "retire-incubation": "incubation-retired",
    "reopen-incubation": "incubation-reopened",
}


def contract_issues(contract: dict, *, known_repos: set[str]) -> list[str]:
    errors: list[str] = []
    if contract.get("owner_repo") != "workspace-governance":
        errors.append("closure contract must be owned by workspace-governance")
    authority = contract.get("authority", {})
    expected = {
        "incubation_source_and_history": "workspace-prototype-studio",
        "readiness": "workspace-governance-control-fabric",
        "workflow_and_target_reconciliation": "operator-orchestration-service",
        "runtime_and_identity": "platform-engineering",
        "security_review": "security-architecture",
        "operator_projection": "governance-operations-console",
    }
    for role, owner in expected.items():
        if authority.get(role) != owner or owner not in known_repos:
            errors.append(f"{role} must have active owner {owner}")
    actions = contract.get("actions", {})
    if set(actions) != ACTIONS:
        errors.append("closure actions must be apply-delivery, graduate-source, retire-incubation, and reopen-incubation")
    if actions.get("apply-delivery", {}).get("source_custody_effect") != "none":
        errors.append("Delivery application cannot transfer source custody")
    if actions.get("graduate-source", {}).get("project_phase_precondition") != "delivery-governed":
        errors.append("source graduation requires accepted Delivery phase")
    if contract.get("target_routes", {}).get("new-repo", {}).get("maturity") != "blocked-until-repository-custody-activation":
        errors.append("new-repo route must remain blocked until Repository custody activates")
    if contract.get("target_routes", {}).get("portfolio", {}).get("maturity") != "prohibited":
        errors.append("Portfolio cannot be a direct Prototype exit")
    if contract.get("history", {}).get("mode") != "append-only":
        errors.append("closure history must be append-only")
    schema_refs = contract.get("artifact_chain", {})
    for name in ("request", "receipt", "history_event"):
        if not schema_refs.get(name, "").startswith("contracts/schemas/prototype-closure-"):
            errors.append(f"{name} schema reference is missing")
    return errors


def receipt_issues(request: dict, receipt: dict) -> list[str]:
    errors: list[str] = []
    for field in ("prototype_id", "action", "operator_id", "correlation_id", "idempotency_key"):
        if request.get(field) != receipt.get(field):
            errors.append(f"receipt {field} does not match request")
    if receipt.get("request_ref") != request.get("request_id"):
        errors.append("receipt does not bind exact request")
    if receipt.get("source_revision") != request.get("expected_source_revision"):
        errors.append("receipt source revision does not match request")
    if receipt.get("previous_lifecycle") != request.get("expected_lifecycle"):
        errors.append("receipt previous lifecycle does not match expected state")
    if receipt.get("outcome") != "completed":
        if receipt.get("observed_lifecycle") != receipt.get("previous_lifecycle"):
            errors.append("denied or failed closure cannot change lifecycle")
        if receipt.get("observed_source_custody") != receipt.get("previous_source_custody"):
            errors.append("denied or failed closure cannot change source custody")
        return errors
    action = request.get("action")
    if action not in ACTIONS:
        errors.append("unknown closure action")
    if action == "apply-delivery":
        if receipt.get("observed_source_custody") != "incubation-repo":
            errors.append("Delivery application cannot graduate source")
        if receipt.get("accepted_delivery_target_receipt_ref") != request.get("accepted_delivery_target_receipt_ref"):
            errors.append("Delivery acceptance receipt mismatch")
    if action == "graduate-source":
        if receipt.get("observed_source_custody") not in {"dedicated-owner-repo", "shared-owner-repo"}:
            errors.append("source graduation requires durable custody")
        for field in ("accepted_delivery_target_receipt_ref", "durable_owner_acceptance_ref"):
            if receipt.get(field) != request.get(field):
                errors.append(f"source graduation {field} mismatch")
        proof = "source_transfer_receipt_ref" if request.get("source_transfer_receipt_ref") else "already_owned_source_proof_ref"
        if receipt.get(proof) != request.get(proof):
            errors.append("source transfer or already-owned proof mismatch")
    if action == "reopen-incubation" and receipt.get("prior_retirement_receipt_ref") != request.get("prior_retirement_receipt_ref"):
        errors.append("reopen does not bind prior retirement")
    return errors


def history_issues(receipt: dict, event: dict, *, prior_digest: str | None) -> list[str]:
    errors: list[str] = []
    expected_type = EVENTS.get(receipt.get("action")) if receipt.get("outcome") == "completed" else "closure-denied"
    if event.get("event_type") != expected_type:
        errors.append("history event type does not match receipt")
    if event.get("prototype_id") != receipt.get("prototype_id"):
        errors.append("history prototype does not match receipt")
    if event.get("terminal_receipt_ref") != receipt.get("receipt_id"):
        errors.append("history does not bind terminal receipt")
    if event.get("prior_event_digest") != prior_digest:
        errors.append("history does not bind previous event digest")
    return errors
