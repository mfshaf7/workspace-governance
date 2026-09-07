from __future__ import annotations

from collections.abc import Mapping
from typing import Any


EXPECTED_INGRESS_CLASSES = {
    "direct",
    "proposal-routed",
    "existing-source",
    "imported",
}
EXPECTED_SUPPORT_PROFILES = {
    "simple",
    "interactive",
    "local-runtime",
    "external-dependency",
    "existing-source-review",
    "custom",
}
EXPECTED_SUPPORT_DIMENSIONS = {
    "source",
    "studio-home",
    "interface",
    "runtime",
    "data",
    "integration",
    "tooling",
    "evidence",
    "visibility",
    "recovery",
}
EXPECTED_SUPPORT_STATES = {
    "unknown",
    "not-needed",
    "needed",
    "ready",
    "blocked",
}
EXPECTED_WORKFLOW_STATES = {
    "captured",
    "configuring",
    "ready",
    "applying",
    "landed",
    "blocked",
}
EXPECTED_ARTIFACT_CHAIN = [
    "prototype-entry-packet",
    "prototype-landing-request",
    "prototype-landing-plan",
    "prototype-landing-readiness",
    "prototype-landing-apply",
    "prototype-landing-readback",
    "prototype-landing-receipt",
]
EXPECTED_SCHEMA_REFS = {
    "entry_packet": "contracts/schemas/prototype-landing-entry-packet.schema.json",
    "request": "contracts/schemas/prototype-landing-request.schema.json",
    "plan": "contracts/schemas/prototype-landing-plan.schema.json",
    "readiness": "contracts/schemas/prototype-landing-readiness.schema.json",
    "apply": "contracts/schemas/prototype-landing-apply.schema.json",
    "readback": "contracts/schemas/prototype-landing-readback.schema.json",
    "receipt": "contracts/schemas/prototype-landing-receipt.schema.json",
}
EXPECTED_OWNER_REPOS = {
    "contract_authority": "workspace-governance",
    "source_authority": "workspace-prototype-studio",
    "readiness_authority": "workspace-governance-control-fabric",
    "workflow_authority": "operator-orchestration-service",
    "runtime_authority": "platform-engineering",
    "security_authority": "security-architecture",
    "operator_projection": "governance-operations-console",
}
EXPECTED_DYNAMIC_OWNERS = {
    "referenced_source_authority": "project-source-owner",
}
EXPECTED_CUSTODY_POSTURES = {
    "create-studio-source": ("incubation-repo", "create"),
    "use-existing-studio-source": ("incubation-repo", "update"),
    "reference-dedicated-owner-source": ("dedicated-owner-repo", "reference-only"),
    "reference-shared-owner-source": ("shared-owner-repo", "reference-only"),
    "import-to-studio": ("incubation-repo", "import"),
}
EXPECTED_TRANSITIONS = {
    "captured": ["configuring"],
    "configuring": ["ready", "blocked"],
    "ready": ["applying", "blocked"],
    "applying": ["landed", "blocked"],
    "blocked": ["configuring"],
}


def request_issues(request: Mapping[str, Any]) -> list[str]:
    issues: list[str] = []
    setup = request.get("setup", {})
    rows = setup.get("support_rows", [])
    dimensions = [row.get("dimension") for row in rows if isinstance(row, Mapping)]
    if len(dimensions) != len(set(dimensions)):
        issues.append("support rows must contain each dimension exactly once")
    if set(dimensions) != EXPECTED_SUPPORT_DIMENSIONS:
        issues.append("support rows must cover every authoritative support dimension")

    profile = setup.get("support_profile")
    expected_generated = profile != "custom"
    if any(row.get("generated") is not expected_generated for row in rows):
        mode = "generated" if expected_generated else "operator-defined"
        issues.append(f"{profile} support rows must all be {mode}")

    source_plan = request.get("source_plan", {})
    posture = source_plan.get("posture")
    if not source_plan.get("source_ref"):
        issues.append(f"{posture} requires an exact planned or existing source reference")
    if posture == "import-to-studio" and (
        not source_plan.get("origin_digest")
        or not source_plan.get("imported_content_digest")
    ):
        issues.append("import-to-studio requires origin and imported content digests")
    if posture in {
        "use-existing-studio-source",
        "reference-dedicated-owner-source",
        "reference-shared-owner-source",
    } and (not source_plan.get("source_ref") or not source_plan.get("source_revision")):
        issues.append(f"{posture} requires an exact source reference and revision")
    return issues


def readiness_issues(readiness: Mapping[str, Any]) -> list[str]:
    issues: list[str] = []
    expected_checks = {
        "entry-integrity",
        "identity-availability",
        "required-metadata",
        "support-profile-integrity",
        "support-row-readiness",
        "source-custody-coherence",
        "source-version-freshness",
        "data-and-mutation-boundary",
        "visibility-and-exposure",
        "security-trigger-disposition",
        "expected-mutation-set",
    }
    checks = readiness.get("checks", [])
    check_ids = [check.get("id") for check in checks if isinstance(check, Mapping)]
    if len(check_ids) != len(set(check_ids)) or set(check_ids) != expected_checks:
        issues.append("readiness must report every authoritative check exactly once")

    states = {check.get("state") for check in checks if isinstance(check, Mapping)}
    outcome = readiness.get("outcome")
    if outcome == "ready" and states != {"ready"}:
        issues.append("ready outcome requires every check to be ready")
    if outcome == "blocked" and "blocked" not in states:
        issues.append("blocked outcome requires at least one blocked check")
    if outcome == "stale" and "stale" not in states:
        issues.append("stale outcome requires at least one stale check")
    if any(finding.get("severity") == "blocking" for finding in readiness.get("findings", [])) and outcome == "ready":
        issues.append("ready outcome cannot contain a blocking finding")
    return issues


def artifact_chain_issues(artifacts: Mapping[str, Mapping[str, Any]]) -> list[str]:
    issues: list[str] = []
    missing = [artifact for artifact in EXPECTED_ARTIFACT_CHAIN if artifact not in artifacts]
    if missing:
        return ["artifact chain is missing: " + ", ".join(missing)]

    entry = artifacts["prototype-entry-packet"]
    request = artifacts["prototype-landing-request"]
    plan = artifacts["prototype-landing-plan"]
    readiness = artifacts["prototype-landing-readiness"]
    apply = artifacts["prototype-landing-apply"]
    readback = artifacts["prototype-landing-readback"]
    receipt = artifacts["prototype-landing-receipt"]
    issues.extend(request_issues(request))
    issues.extend(readiness_issues(readiness))

    bindings = (
        (request.get("entry_packet_ref"), entry.get("entry_id"), entry.get("packet_digest"), "request entry packet"),
        (plan.get("request_ref"), request.get("request_id"), request.get("request_digest"), "plan request"),
        (readiness.get("request_ref"), request.get("request_id"), request.get("request_digest"), "readiness request"),
        (readiness.get("plan_ref"), plan.get("plan_id"), plan.get("plan_digest"), "readiness plan"),
        (apply.get("request_ref"), request.get("request_id"), request.get("request_digest"), "apply request"),
        (apply.get("plan_ref"), plan.get("plan_id"), plan.get("plan_digest"), "apply plan"),
        (apply.get("readiness_ref"), readiness.get("readiness_id"), readiness.get("readiness_digest"), "apply readiness"),
        (readback.get("apply_ref"), apply.get("apply_id"), apply.get("apply_digest"), "readback apply"),
        (receipt.get("entry_packet_ref"), entry.get("entry_id"), entry.get("packet_digest"), "receipt entry packet"),
        (receipt.get("request_ref"), request.get("request_id"), request.get("request_digest"), "receipt request"),
        (receipt.get("plan_ref"), plan.get("plan_id"), plan.get("plan_digest"), "receipt plan"),
        (receipt.get("readiness_ref"), readiness.get("readiness_id"), readiness.get("readiness_digest"), "receipt readiness"),
        (receipt.get("apply_ref"), apply.get("apply_id"), apply.get("apply_digest"), "receipt apply"),
        (receipt.get("readback_ref"), readback.get("readback_id"), readback.get("readback_digest"), "receipt readback"),
    )
    for artifact_ref, expected_id, expected_digest, label in bindings:
        if not isinstance(artifact_ref, Mapping) or artifact_ref.get("id") != expected_id or artifact_ref.get("digest") != expected_digest:
            issues.append(f"{label} must bind the exact artifact id and digest")

    prototype_ids = {
        request.get("prototype", {}).get("id"),
        plan.get("prototype_id"),
        apply.get("prototype_id"),
        readback.get("prototype_id"),
        readback.get("record", {}).get("id"),
        receipt.get("prototype_id"),
    }
    if len(prototype_ids) != 1:
        issues.append("every Landing artifact must bind one Prototype identity")
    if plan.get("source_plan") != request.get("source_plan"):
        issues.append("plan source posture must match the accepted request")
    output_kinds = {
        output.get("kind")
        for output in plan.get("expected_outputs", [])
        if isinstance(output, Mapping)
    }
    if output_kinds != set(plan.get("mutation_set", [])):
        issues.append("plan expected outputs must cover the exact mutation set")
    if readback.get("record", {}).get("setup") != request.get("setup"):
        issues.append("readback setup must match the accepted request")
    request_source = request.get("source_plan", {})
    readback_source = readback.get("record", {}).get("source", {})
    expected_custody = EXPECTED_CUSTODY_POSTURES.get(
        request_source.get("posture"), (None, None)
    )[0]
    if (
        readback_source.get("posture") != request_source.get("posture")
        or readback_source.get("ref") != request_source.get("source_ref")
        or readback_source.get("custody") != expected_custody
    ):
        issues.append("readback source must match the accepted source plan and custody mapping")
    correlation_ids = {
        request.get("correlation_id"),
        apply.get("correlation_id"),
        receipt.get("correlation_id"),
    }
    if len(correlation_ids) != 1:
        issues.append("request, apply, and receipt must share one correlation id")
    idempotency_keys = {
        request.get("idempotency_key"),
        apply.get("idempotency_key"),
        receipt.get("idempotency_key"),
    }
    if len(idempotency_keys) != 1:
        issues.append("request, apply, and receipt must share one idempotency key")

    if readiness.get("outcome") != "ready" and apply:
        issues.append("apply requires a ready readiness outcome")
    if receipt.get("outcome") == "succeeded":
        if readback.get("authority_state") != "merged-authority":
            issues.append("succeeded receipt requires merged-authority readback")
    return issues


def contract_issues(
    contract: Mapping[str, Any], *, known_repos: set[str]
) -> list[str]:
    issues: list[str] = []

    owners = contract.get("scope_boundaries", {})
    expected_owner_roles = set(EXPECTED_OWNER_REPOS) | set(EXPECTED_DYNAMIC_OWNERS)
    if set(owners) != expected_owner_roles:
        issues.append("scope_boundaries must define the authoritative owner roles exactly once")
    for role, expected_repo in EXPECTED_OWNER_REPOS.items():
        owner = owners.get(role, {})
        if owner.get("owner_repo") != expected_repo:
            issues.append(f"{role} must be owned by {expected_repo}")
        if expected_repo not in known_repos:
            issues.append(f"{role} references unknown repo {expected_repo}")
    for role, expected_owner in EXPECTED_DYNAMIC_OWNERS.items():
        owner = owners.get(role, {})
        if owner.get("owner_kind") != "dynamic" or owner.get("owner_ref") != expected_owner:
            issues.append(f"{role} must bind dynamic owner {expected_owner}")
    if owners.get("operator_projection", {}).get("mode") != "projection-only":
        issues.append("operator_projection must remain projection-only")

    ingress_classes = set(contract.get("ingress", {}).get("classes", {}))
    if ingress_classes != EXPECTED_INGRESS_CLASSES:
        issues.append("ingress classes must be exactly direct, proposal-routed, existing-source, and imported")

    support = contract.get("support_model", {})
    if set(support.get("profiles", {})) != EXPECTED_SUPPORT_PROFILES:
        issues.append("support profiles do not match the Prototype Landing contract")
    if support.get("profiles", {}).get("custom") != "operator-defined":
        issues.append("custom support profile must be operator-defined")
    if any(
        mode != "generated"
        for profile, mode in support.get("profiles", {}).items()
        if profile != "custom"
    ):
        issues.append("named support profiles must be generated")
    if set(support.get("row_states", [])) != EXPECTED_SUPPORT_STATES:
        issues.append("support row states do not match the Prototype Landing contract")
    if set(support.get("dimensions", [])) != EXPECTED_SUPPORT_DIMENSIONS:
        issues.append("support dimensions do not match the Prototype Landing contract")

    custody = contract.get("source_custody", {}).get("postures", {})
    if set(custody) != set(EXPECTED_CUSTODY_POSTURES):
        issues.append("source custody postures do not match the Prototype Landing contract")
    for posture, definition in custody.items():
        if definition.get("resulting_axis_state") not in {
            "incubation-repo",
            "dedicated-owner-repo",
            "shared-owner-repo",
        }:
            issues.append(f"source custody posture {posture} has an invalid project-lifecycle axis state")
        if definition.get("source_mutation") == "reference-only" and definition.get(
            "resulting_axis_state"
        ) == "incubation-repo":
            issues.append(f"source custody posture {posture} cannot claim incubation custody for a reference-only source")
        expected = EXPECTED_CUSTODY_POSTURES.get(posture)
        actual = (definition.get("resulting_axis_state"), definition.get("source_mutation"))
        if expected is not None and actual != expected:
            issues.append(f"source custody posture {posture} does not match its authoritative custody mapping")

    state_model = contract.get("state_model", {})
    if set(state_model.get("states", [])) != EXPECTED_WORKFLOW_STATES:
        issues.append("Landing workflow states do not match the authoritative state model")
    if state_model.get("terminal_states") != ["landed"]:
        issues.append("landed must be the only terminal Landing workflow state")
    if state_model.get("transitions") != EXPECTED_TRANSITIONS:
        issues.append("Landing transitions do not match the authoritative state model")
    result = state_model.get("project_result", {})
    if result != {
        "project_phase": "incubating",
        "prototype_lifecycle": "exploring",
        "next_action": "candidate-promotion",
    }:
        issues.append("Landing result must enter incubation as exploring with candidate-promotion next")

    if contract.get("schema_refs") != EXPECTED_SCHEMA_REFS:
        issues.append("schema_refs must bind every canonical Prototype Landing artifact schema")
    if contract.get("artifact_chain", {}).get("ordered_artifacts") != EXPECTED_ARTIFACT_CHAIN:
        issues.append("artifact_chain does not preserve the authoritative Landing order")

    denied = set(contract.get("denied_shortcuts", []))
    required_denials = {
        "direct-main-mutation",
        "console-owned-prototype-truth",
        "runtime-activation-by-landing",
        "security-acceptance-by-landing",
        "candidate-or-baseline-promotion-by-landing",
        "portfolio-publication-by-landing",
        "success-before-merged-readback",
        "source-mutation-on-failure",
    }
    missing_denials = sorted(required_denials - denied)
    if missing_denials:
        issues.append("denied_shortcuts is missing: " + ", ".join(missing_denials))

    return issues
