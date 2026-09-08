from __future__ import annotations

from collections.abc import Mapping
from typing import Any


TRANSITIONS = {
    "candidate-promotion": {
        "source": "exploring",
        "target": "candidate",
        "packet_kind": "candidate-evidence-packet",
        "sections": {
            "candidate-brief",
            "scope-and-non-goals",
            "boundaries-and-risks",
        },
        "decisions": {"promote-candidate", "block-promotion", "route-closeout"},
        "promotion_decision": "promote-candidate",
    },
    "baseline-promotion": {
        "source": "candidate",
        "target": "baseline-approved",
        "packet_kind": "baseline-packet",
        "sections": {
            "definition",
            "design-and-workflow",
            "evidence",
            "boundaries",
            "issues-and-risk-disposition",
        },
        "decisions": {"approve-baseline", "block-baseline", "route-closeout"},
        "promotion_decision": "approve-baseline",
    },
}
COMMON_CHECKS = {
    "request-integrity",
    "lifecycle-source-state",
    "source-version-freshness",
    "packet-integrity",
    "required-evidence",
    "boundary-coherence",
    "security-trigger-disposition",
    "open-issue-disposition",
}
ARTIFACT_CHAIN = [
    "prototype-maturity-request",
    "prototype-maturity-packet",
    "prototype-maturity-readiness",
    "prototype-maturity-decision",
    "prototype-maturity-readback",
    "prototype-maturity-receipt",
]
SCHEMA_REFS = {
    "request": "contracts/schemas/prototype-maturity-request.schema.json",
    "packet": "contracts/schemas/prototype-maturity-packet.schema.json",
    "readiness": "contracts/schemas/prototype-maturity-readiness.schema.json",
    "decision": "contracts/schemas/prototype-maturity-decision.schema.json",
    "readback": "contracts/schemas/prototype-maturity-readback.schema.json",
    "receipt": "contracts/schemas/prototype-maturity-receipt.schema.json",
}
OWNER_REPOS = {
    "contract_authority": "workspace-governance",
    "source_authority": "workspace-prototype-studio",
    "readiness_authority": "workspace-governance-control-fabric",
    "workflow_authority": "operator-orchestration-service",
    "security_authority": "security-architecture",
    "operator_projection": "governance-operations-console",
}


def _ref_matches(value: Any, artifact_id: Any, digest: Any) -> bool:
    return (
        isinstance(value, Mapping)
        and value.get("id") == artifact_id
        and value.get("digest") == digest
    )


def packet_issues(packet: Mapping[str, Any]) -> list[str]:
    issues: list[str] = []
    transition = packet.get("transition")
    profile = TRANSITIONS.get(transition)
    if profile is None:
        return [f"unknown Prototype maturity transition {transition}"]
    if packet.get("packet_kind") != profile["packet_kind"]:
        issues.append(f"{transition} requires {profile['packet_kind']}")
    sections = packet.get("sections", [])
    section_ids = [section.get("id") for section in sections if isinstance(section, Mapping)]
    if len(section_ids) != len(set(section_ids)):
        issues.append("maturity packet sections must be unique")
    if set(section_ids) != profile["sections"]:
        issues.append(f"{transition} packet must contain every required section exactly once")
    return issues


def readiness_issues(readiness: Mapping[str, Any]) -> list[str]:
    issues: list[str] = []
    checks = readiness.get("checks", [])
    check_ids = [check.get("id") for check in checks if isinstance(check, Mapping)]
    if len(check_ids) != len(set(check_ids)) or set(check_ids) != COMMON_CHECKS:
        issues.append("readiness must report every maturity check exactly once")
    states = {check.get("state") for check in checks if isinstance(check, Mapping)}
    outcome = readiness.get("outcome")
    if outcome == "ready" and states != {"ready"}:
        issues.append("ready outcome requires every maturity check to be ready")
    if outcome == "blocked" and "blocked" not in states:
        issues.append("blocked outcome requires at least one blocked check")
    if outcome == "stale" and "stale" not in states:
        issues.append("stale outcome requires at least one stale check")
    findings = readiness.get("findings", [])
    if outcome == "ready" and any(
        finding.get("severity") == "blocking"
        for finding in findings
        if isinstance(finding, Mapping)
    ):
        issues.append("ready outcome cannot contain a blocking finding")
    return issues


def decision_issues(decision: Mapping[str, Any]) -> list[str]:
    issues: list[str] = []
    transition = decision.get("transition")
    profile = TRANSITIONS.get(transition)
    if profile is None:
        return [f"unknown Prototype maturity transition {transition}"]
    action = decision.get("decision")
    if action not in profile["decisions"]:
        issues.append(f"{action} is not valid for {transition}")
    is_block = action in {"block-promotion", "block-baseline"}
    blocker = decision.get("blocker")
    if is_block:
        if not isinstance(blocker, Mapping) or not all(
            blocker.get(field) for field in ("issue_ref", "owner_ref", "required_fix")
        ):
            issues.append("a block decision requires an issue ref, owner, and required fix")
    elif blocker is not None:
        issues.append("non-block decisions cannot carry blocker metadata")
    return issues


def artifact_chain_issues(artifacts: Mapping[str, Mapping[str, Any]]) -> list[str]:
    missing = [kind for kind in ARTIFACT_CHAIN if kind not in artifacts]
    if missing:
        return ["artifact chain is missing: " + ", ".join(missing)]

    request = artifacts["prototype-maturity-request"]
    packet = artifacts["prototype-maturity-packet"]
    readiness = artifacts["prototype-maturity-readiness"]
    decision = artifacts["prototype-maturity-decision"]
    readback = artifacts["prototype-maturity-readback"]
    receipt = artifacts["prototype-maturity-receipt"]
    issues = packet_issues(packet) + readiness_issues(readiness) + decision_issues(decision)

    transition = request.get("transition")
    profile = TRANSITIONS.get(transition)
    if profile is None:
        issues.append(f"unknown Prototype maturity transition {transition}")
        return issues

    if request.get("source_lifecycle") != profile["source"] or request.get("target_lifecycle") != profile["target"]:
        issues.append("request lifecycle pair must match its transition")
    expected_state = request.get("expected_state", {})
    if expected_state.get("lifecycle") != profile["source"]:
        issues.append("request expected lifecycle must match the transition source")

    for artifact in (packet, readiness, decision, readback, receipt):
        if artifact.get("prototype_id") != request.get("prototype_id"):
            issues.append("every maturity artifact must bind one Prototype identity")
            break
        if artifact.get("transition") != transition:
            issues.append("every maturity artifact must bind one transition")
            break

    bindings = (
        (packet.get("request_ref"), request.get("request_id"), request.get("request_digest"), "packet request"),
        (readiness.get("request_ref"), request.get("request_id"), request.get("request_digest"), "readiness request"),
        (readiness.get("packet_ref"), packet.get("packet_id"), packet.get("packet_digest"), "readiness packet"),
        (decision.get("request_ref"), request.get("request_id"), request.get("request_digest"), "decision request"),
        (decision.get("packet_ref"), packet.get("packet_id"), packet.get("packet_digest"), "decision packet"),
        (decision.get("readiness_ref"), readiness.get("readiness_id"), readiness.get("readiness_digest"), "decision readiness"),
        (readback.get("decision_ref"), decision.get("decision_id"), decision.get("decision_digest"), "readback decision"),
        (receipt.get("request_ref"), request.get("request_id"), request.get("request_digest"), "receipt request"),
        (receipt.get("packet_ref"), packet.get("packet_id"), packet.get("packet_digest"), "receipt packet"),
        (receipt.get("readiness_ref"), readiness.get("readiness_id"), readiness.get("readiness_digest"), "receipt readiness"),
        (receipt.get("decision_ref"), decision.get("decision_id"), decision.get("decision_digest"), "receipt decision"),
        (receipt.get("readback_ref"), readback.get("readback_id"), readback.get("readback_digest"), "receipt readback"),
    )
    for value, artifact_id, digest, label in bindings:
        if not _ref_matches(value, artifact_id, digest):
            issues.append(f"{label} must bind the exact artifact id and digest")

    if readiness.get("observed_state") != expected_state or decision.get("expected_state") != expected_state:
        issues.append("readiness and decision must bind the request expected source state")
    if decision.get("decision") in {"promote-candidate", "approve-baseline"} and readiness.get("outcome") != "ready":
        issues.append("promote and approve decisions require ready maturity evidence")

    action = decision.get("decision")
    if action == profile["promotion_decision"]:
        if readback.get("authority_state") != "merged-authority" or readback.get("observed_lifecycle") != profile["target"]:
            issues.append("successful promotion requires merged readback at the target lifecycle")
        if receipt.get("outcome") != "succeeded" or receipt.get("resulting_lifecycle") != profile["target"]:
            issues.append("successful promotion receipt must report the target lifecycle")
    else:
        expected_outcome = "blocked" if action in {"block-promotion", "block-baseline"} else "routed-closeout"
        if readback.get("authority_state") != "unchanged-authority" or readback.get("observed_lifecycle") != profile["source"]:
            issues.append("non-promotion decisions must preserve source lifecycle")
        if receipt.get("outcome") != expected_outcome or receipt.get("resulting_lifecycle") != profile["source"]:
            issues.append("non-promotion receipt must preserve source lifecycle and report its decision outcome")

    correlation_ids = {request.get("correlation_id"), decision.get("correlation_id"), receipt.get("correlation_id")}
    if len(correlation_ids) != 1:
        issues.append("request, decision, and receipt must share one correlation id")
    idempotency_keys = {request.get("idempotency_key"), decision.get("idempotency_key"), receipt.get("idempotency_key")}
    if len(idempotency_keys) != 1:
        issues.append("request, decision, and receipt must share one idempotency key")
    return issues


def contract_issues(contract: Mapping[str, Any], *, known_repos: set[str]) -> list[str]:
    issues: list[str] = []
    owners = contract.get("scope_boundaries", {})
    expected_roles = set(OWNER_REPOS) | {"decision_authority"}
    if set(owners) != expected_roles:
        issues.append("scope_boundaries must define every maturity authority exactly once")
    for role, repo in OWNER_REPOS.items():
        if owners.get(role, {}).get("owner_repo") != repo:
            issues.append(f"{role} must be owned by {repo}")
        if repo not in known_repos:
            issues.append(f"{role} references unknown repo {repo}")
    decision_owner = owners.get("decision_authority", {})
    if decision_owner.get("owner_kind") != "dynamic" or decision_owner.get("owner_ref") != "explicit-operator":
        issues.append("decision_authority must bind the explicit operator")
    if owners.get("operator_projection", {}).get("mode") != "projection-only":
        issues.append("operator_projection must remain projection-only")

    transitions = contract.get("prototype_lifecycle", {}).get("transitions", {})
    if set(transitions) != set(TRANSITIONS):
        issues.append("Prototype maturity transitions must be candidate-promotion and baseline-promotion")
    for name, expected in TRANSITIONS.items():
        actual = transitions.get(name, {})
        if actual.get("source") != expected["source"] or actual.get("target") != expected["target"]:
            issues.append(f"{name} lifecycle pair is invalid")
        profile = contract.get("transition_profiles", {}).get(name, {})
        if profile.get("packet_kind") != expected["packet_kind"]:
            issues.append(f"{name} packet kind is invalid")
        if set(profile.get("required_sections", [])) != expected["sections"]:
            issues.append(f"{name} required sections are invalid")
        if set(profile.get("decisions", [])) != expected["decisions"]:
            issues.append(f"{name} decisions are invalid")

    if contract.get("schema_refs") != SCHEMA_REFS:
        issues.append("schema_refs must bind every Prototype maturity artifact schema")
    if contract.get("artifact_chain", {}).get("ordered_artifacts") != ARTIFACT_CHAIN:
        issues.append("artifact_chain must preserve the authoritative maturity order")
    if set(contract.get("readiness", {}).get("common_checks", [])) != COMMON_CHECKS:
        issues.append("readiness checks do not match the maturity contract")

    denials = set(contract.get("denied_shortcuts", []))
    required_denials = {
        "candidate-without-landing",
        "baseline-without-candidate",
        "no-op-keep-current-receipt",
        "baseline-as-delivery-admission",
        "baseline-as-runtime-or-security-acceptance",
        "baseline-as-source-graduation",
        "success-before-merged-readback",
    }
    missing = sorted(required_denials - denials)
    if missing:
        issues.append("denied_shortcuts is missing: " + ", ".join(missing))
    return issues
