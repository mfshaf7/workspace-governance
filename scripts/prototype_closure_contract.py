"""Semantic checks shared by Prototype closure contract fixtures and owners."""

from __future__ import annotations

from datetime import datetime


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
    if contract.get("schema_version") != 2:
        errors.append("closure contract must use causal-order schema v2")
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
    delivery = actions.get("apply-delivery", {})
    if "accepted-delivery-target-receipt" in delivery.get("request_evidence", []):
        errors.append("Delivery request cannot require its future target receipt")
    if "accepted-delivery-target-receipt" not in delivery.get("completion_evidence", []):
        errors.append("Delivery completion must carry accepted target receipt")
    if "merged-studio-readback" not in delivery.get("completion_evidence", []):
        errors.append("Delivery completion must carry merged Studio readback")
    if actions.get("graduate-source", {}).get("project_phase_precondition") != "delivery-governed":
        errors.append("source graduation requires accepted Delivery phase")
    graduation = actions.get("graduate-source", {})
    if "exact-source-transfer-or-already-owned-proof" in graduation.get("request_evidence", []):
        errors.append("source transfer request cannot require its future transfer receipt")
    if "exact-source-transfer-or-already-owned-proof" not in graduation.get("completion_evidence", []):
        errors.append("source graduation completion must prove transfer or already-owned custody")
    if contract.get("target_routes", {}).get("new-repo", {}).get("maturity") != "blocked-until-repository-custody-activation":
        errors.append("new-repo route must remain blocked until Repository custody activates")
    if contract.get("target_routes", {}).get("portfolio", {}).get("maturity") != "prohibited":
        errors.append("Portfolio cannot be a direct Prototype exit")
    if contract.get("history", {}).get("mode") != "append-only":
        errors.append("closure history must be append-only")
    if "closure-denied" in contract.get("history", {}).get("event_types", []):
        errors.append("denial cannot create a Studio transition event")
    schema_refs = contract.get("artifact_chain", {})
    for name in ("request", "history_event", "merged_readback", "receipt"):
        if not schema_refs.get(name, "").startswith("contracts/schemas/prototype-closure-"):
            errors.append(f"{name} schema reference is missing")
    return errors


def history_issues(request: dict, event: dict, *, request_digest: str, prior_digest: str | None) -> list[str]:
    errors: list[str] = []
    if event.get("event_type") != EVENTS.get(request.get("action")):
        errors.append("history event type does not match request action")
    for field in ("prototype_id", "operator_id", "correlation_id", "idempotency_key"):
        if event.get(field) != request.get(field):
            errors.append(f"history {field} does not match request")
    if event.get("request_ref") != request.get("request_id") or event.get("request_digest") != request_digest:
        errors.append("history does not bind exact request")
    if event.get("expected_source_revision") != request.get("expected_source_revision"):
        errors.append("history source revision does not match request")
    if event.get("previous_lifecycle") != request.get("expected_lifecycle"):
        errors.append("history previous lifecycle does not match request")
    if event.get("prior_event_digest") != prior_digest:
        errors.append("history does not bind previous event digest")
    if any(key.startswith("terminal_receipt") for key in event):
        errors.append("source event cannot bind future terminal receipt")
    action = request.get("action")
    if action == "apply-delivery":
        if event.get("accepted_baseline_receipt_ref") != request.get("accepted_baseline_receipt_ref"):
            errors.append("Delivery history baseline receipt mismatch")
        if not event.get("accepted_delivery_target_receipt_ref"):
            errors.append("Delivery history lacks accepted target receipt")
        if event.get("observed_lifecycle") != "graduating" or event.get("observed_source_custody") != "incubation-repo":
            errors.append("Delivery history cannot graduate source")
    elif action == "graduate-source":
        for field in ("accepted_delivery_target_receipt_ref", "durable_owner_acceptance_ref"):
            if event.get(field) != request.get(field):
                errors.append(f"source graduation history {field} mismatch")
        if request.get("transfer_strategy") == "already-owned":
            if event.get("already_owned_source_proof_ref") != request.get("already_owned_source_proof_ref"):
                errors.append("already-owned source history proof mismatch")
        elif request.get("transfer_strategy") == "transfer":
            if not event.get("source_transfer_receipt_ref"):
                errors.append("source transfer history receipt missing")
        if event.get("observed_lifecycle") != "graduated" or event.get("observed_source_custody") not in {"dedicated-owner-repo", "shared-owner-repo"}:
            errors.append("source graduation history requires durable custody")
    elif action == "retire-incubation":
        if event.get("retention_plan_ref") != request.get("retention_plan_ref"):
            errors.append("retirement history retention plan mismatch")
        if not event.get("runtime_disposition_proof_ref"):
            errors.append("retirement history lacks runtime disposition proof")
        if event.get("observed_lifecycle") != "retired":
            errors.append("retirement history lifecycle mismatch")
    elif action == "reopen-incubation":
        if event.get("prior_retirement_receipt_ref") != request.get("prior_retirement_receipt_ref"):
            errors.append("reopen history does not bind prior retirement")
        if not event.get("retained_source_readback_ref"):
            errors.append("reopen history lacks retained source readback")
        if event.get("observed_lifecycle") != "exploring" or event.get("observed_source_custody") != "incubation-repo":
            errors.append("reopen history lifecycle or custody mismatch")
    else:
        errors.append("unknown closure action")
    return errors


def receipt_issues(
    request: dict,
    receipt: dict,
    *,
    request_digest: str,
    event: dict | None = None,
    event_digest: str | None = None,
    readback: dict | None = None,
    readback_digest: str | None = None,
) -> list[str]:
    errors: list[str] = []
    for field in ("prototype_id", "action", "operator_id", "correlation_id", "idempotency_key"):
        if request.get(field) != receipt.get(field):
            errors.append(f"receipt {field} does not match request")
    if receipt.get("request_ref") != request.get("request_id") or receipt.get("request_digest") != request_digest:
        errors.append("receipt does not bind exact request")
    if receipt.get("source_revision") != request.get("expected_source_revision"):
        errors.append("receipt source revision does not match request")
    if receipt.get("previous_lifecycle") != request.get("expected_lifecycle"):
        errors.append("receipt previous lifecycle does not match expected state")
    if receipt.get("outcome") != "completed":
        if receipt.get("outcome") == "failed" and receipt.get("failure_stage") != "pre-merge":
            errors.append("terminal failure must be pre-merge")
        if receipt.get("observed_lifecycle") != receipt.get("previous_lifecycle"):
            errors.append("denied or failed closure cannot change lifecycle")
        if receipt.get("observed_source_custody") != receipt.get("previous_source_custody"):
            errors.append("denied or failed closure cannot change source custody")
        if event is not None or readback is not None or receipt.get("source_event_ref") or receipt.get("merged_studio_readback_ref"):
            errors.append("pre-merge terminal finding cannot claim Studio source mutation")
        return errors
    if event is None or readback is None or not event_digest or not readback_digest:
        errors.append("completed closure requires source event and merged readback evidence")
        return errors
    errors.extend(history_issues(request, event, request_digest=request_digest, prior_digest=event.get("prior_event_digest")))
    if receipt.get("source_event_ref") != event.get("event_id") or receipt.get("source_event_digest") != event_digest:
        errors.append("receipt does not bind exact Studio source event")
    if receipt.get("merged_studio_readback_ref") != readback.get("readback_id") or receipt.get("merged_studio_readback_digest") != readback_digest:
        errors.append("receipt does not bind exact merged Studio readback")
    if readback.get("source_event_ref") != event.get("event_id") or readback.get("source_event_digest") != event_digest:
        errors.append("merged Studio readback does not bind source event")
    if readback.get("prototype_id") != request.get("prototype_id") or event.get("prototype_id") != request.get("prototype_id"):
        errors.append("source event or readback prototype mismatch")
    if receipt.get("merged_source_revision") != readback.get("merged_source_revision"):
        errors.append("receipt merged revision does not match readback")
    if readback.get("merged_source_revision") == request.get("expected_source_revision"):
        errors.append("merged Studio readback must advance source revision")
    for field in ("observed_lifecycle", "observed_source_custody"):
        if receipt.get(field) != event.get(field) or receipt.get(field) != readback.get(field):
            errors.append(f"receipt {field} does not match source event and readback")
    try:
        event_at = datetime.fromisoformat(event["recorded_at"].replace("Z", "+00:00"))
        readback_at = datetime.fromisoformat(readback["observed_at"].replace("Z", "+00:00"))
        receipt_at = datetime.fromisoformat(receipt["recorded_at"].replace("Z", "+00:00"))
        if not event_at <= readback_at <= receipt_at:
            errors.append("source event, merged readback, and terminal receipt are out of order")
    except (KeyError, TypeError, ValueError):
        errors.append("closure chain timestamps are invalid")
    if request.get("action") == "apply-delivery" and receipt.get("accepted_delivery_target_receipt_ref") != event.get("accepted_delivery_target_receipt_ref"):
        errors.append("Delivery receipt does not bind accepted target evidence")
    if request.get("action") == "graduate-source":
        if receipt.get("observed_source_custody") not in {"dedicated-owner-repo", "shared-owner-repo"}:
            errors.append("source graduation requires durable custody")
        for field in ("accepted_delivery_target_receipt_ref", "durable_owner_acceptance_ref"):
            if receipt.get(field) != request.get(field) or receipt.get(field) != event.get(field):
                errors.append(f"source graduation {field} mismatch")
        if request.get("transfer_strategy") == "already-owned":
            if receipt.get("already_owned_source_proof_ref") != request.get("already_owned_source_proof_ref") or receipt.get("already_owned_source_proof_ref") != event.get("already_owned_source_proof_ref"):
                errors.append("already-owned source proof mismatch")
        elif request.get("transfer_strategy") == "transfer":
            if not receipt.get("source_transfer_receipt_ref") or receipt.get("source_transfer_receipt_ref") != event.get("source_transfer_receipt_ref"):
                errors.append("source transfer receipt missing or mismatched")
    if request.get("action") == "reopen-incubation" and receipt.get("prior_retirement_receipt_ref") != request.get("prior_retirement_receipt_ref"):
        errors.append("reopen does not bind prior retirement")
    return errors
