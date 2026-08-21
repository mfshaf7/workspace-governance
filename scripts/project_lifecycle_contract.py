from __future__ import annotations

from collections.abc import Mapping
from typing import Any


EXPECTED_AXES = {
    "project-phase",
    "publication-posture",
    "release-posture",
    "runtime-environment",
    "source-custody",
}
ALLOWED_DYNAMIC_OWNERS = {"project-owner-repo"}
IMPLEMENTATION_MATURITY = {
    "contract-only": 0,
    "locally-proven": 1,
    "dev-integration": 2,
    "governed": 3,
}


def lifecycle_model(contract: Mapping[str, Any]) -> Mapping[str, Any]:
    model = contract.get("project_lifecycle", {})
    return model if isinstance(model, Mapping) else {}


def _state_reference_issues(
    axes: Mapping[str, Any],
    reference: Mapping[str, Any],
    label: str,
    *,
    states_key: str,
) -> list[str]:
    issues: list[str] = []
    axis_id = reference.get("axis")
    if axis_id not in axes:
        return [f"{label} references unknown axis {axis_id!r}"]
    known_states = set(axes[axis_id]["states"])
    unknown_states = sorted(set(reference.get(states_key, [])) - known_states)
    if unknown_states:
        issues.append(
            f"{label} references unknown {axis_id} states: {', '.join(unknown_states)}"
        )
    return issues


def contract_issues(
    contract: Mapping[str, Any],
    *,
    known_repos: set[str],
) -> list[str]:
    model = lifecycle_model(contract)
    axes = model.get("axes", {})
    roles = model.get("ownership_roles", {})
    evidence_types = model.get("evidence_types", {})
    envelopes = model.get("envelopes", {})
    recovery = model.get("recovery_contract", {})
    transitions = model.get("transitions", {})
    issues: list[str] = []
    model_maturity = model.get("implementation_posture")

    if model_maturity not in IMPLEMENTATION_MATURITY:
        issues.append(f"unknown lifecycle implementation posture {model_maturity!r}")

    if set(model.get("axis_order", [])) != EXPECTED_AXES:
        issues.append("axis_order must contain the five lifecycle axes exactly once")
    if set(axes) != EXPECTED_AXES:
        issues.append("axes must define project-phase, source-custody, runtime-environment, release-posture, and publication-posture")

    responsibility_owners: dict[str, str] = {}
    for role_id, role in roles.items():
        owner_kind = role.get("owner_kind")
        owner_ref = role.get("owner_ref")
        if owner_kind == "repo" and owner_ref not in known_repos:
            issues.append(f"ownership role {role_id} references unknown repo {owner_ref!r}")
        if owner_kind == "dynamic" and owner_ref not in ALLOWED_DYNAMIC_OWNERS:
            issues.append(f"ownership role {role_id} references unsupported dynamic owner {owner_ref!r}")
        if role.get("mode") == "projection" and role.get("responsibilities", []):
            authority_responsibilities = [
                item
                for item in role["responsibilities"]
                if item.endswith("-record") or item.endswith("-authority")
            ]
            if authority_responsibilities:
                issues.append(
                    f"projection role {role_id} cannot own authority responsibilities: "
                    + ", ".join(authority_responsibilities)
                )
        for responsibility in role.get("responsibilities", []):
            previous = responsibility_owners.get(responsibility)
            if previous is not None:
                issues.append(
                    f"responsibility {responsibility!r} has contradictory owners {previous!r} and {role_id!r}"
                )
            else:
                responsibility_owners[responsibility] = role_id

    for axis_id, axis in axes.items():
        responsibility = axis.get("responsibility")
        if responsibility not in responsibility_owners:
            issues.append(f"axis {axis_id} has no owner for responsibility {responsibility!r}")
        authority_roles = set(axis.get("authority_roles", []))
        unknown_roles = sorted(authority_roles - set(roles))
        if unknown_roles:
            issues.append(f"axis {axis_id} references unknown authority roles: {', '.join(unknown_roles)}")
        projection_roles = sorted(
            role_id for role_id in authority_roles if roles.get(role_id, {}).get("mode") != "authority"
        )
        if projection_roles:
            issues.append(f"axis {axis_id} uses non-authority roles: {', '.join(projection_roles)}")

    for evidence_id, evidence in evidence_types.items():
        if evidence.get("owner_role") not in roles:
            issues.append(
                f"evidence type {evidence_id} references unknown owner role {evidence.get('owner_role')!r}"
            )

    allowed_recovery = set(recovery.get("allowed_decisions", []))
    if allowed_recovery != {"remove", "workaround", "accept-risk", "defer"}:
        issues.append("recovery decisions must be exactly remove, workaround, accept-risk, and defer")
    if set(recovery.get("requirements", {})) != allowed_recovery:
        issues.append("recovery requirements must cover every allowed recovery decision exactly")

    for transition_id, transition in transitions.items():
        axis_id = transition.get("axis")
        if axis_id not in axes:
            issues.append(f"transition {transition_id} references unknown axis {axis_id!r}")
            continue
        known_states = set(axes[axis_id]["states"])
        transition_maturity = transition.get("implementation_maturity")
        if transition_maturity not in IMPLEMENTATION_MATURITY:
            issues.append(
                f"transition {transition_id} has unknown implementation maturity {transition_maturity!r}"
            )
        elif model_maturity in IMPLEMENTATION_MATURITY and (
            IMPLEMENTATION_MATURITY[transition_maturity]
            > IMPLEMENTATION_MATURITY[model_maturity]
        ):
            issues.append(
                f"transition {transition_id} maturity {transition_maturity!r} exceeds lifecycle posture {model_maturity!r}"
            )
        for field in ("from_states", "to_states"):
            unknown_states = sorted(set(transition.get(field, [])) - known_states)
            if unknown_states:
                issues.append(
                    f"transition {transition_id} has unknown {field}: {', '.join(unknown_states)}"
                )
        source_role = transition.get("source_authority_role")
        target_role = transition.get("target_owner_role")
        if source_role not in roles:
            issues.append(f"transition {transition_id} references unknown source authority {source_role!r}")
        elif roles[source_role].get("mode") != "authority":
            issues.append(f"transition {transition_id} source role {source_role!r} is not an authority")
        if target_role not in roles:
            issues.append(f"transition {transition_id} references unknown target owner {target_role!r}")
        elif roles[target_role].get("mode") != "authority":
            issues.append(f"transition {transition_id} target role {target_role!r} is not an authority")
        if transition.get("required_envelope") not in envelopes:
            issues.append(
                f"transition {transition_id} references unknown envelope {transition.get('required_envelope')!r}"
            )
        unknown_evidence = sorted(set(transition.get("required_evidence", [])) - set(evidence_types))
        if unknown_evidence:
            issues.append(
                f"transition {transition_id} references unknown evidence: {', '.join(unknown_evidence)}"
            )
        transition_recovery = set(transition.get("allowed_recovery_decisions", []))
        if not transition_recovery or not transition_recovery <= allowed_recovery:
            issues.append(f"transition {transition_id} has invalid recovery decisions")
        for index, precondition in enumerate(transition.get("preconditions", [])):
            issues.extend(
                _state_reference_issues(
                    axes,
                    precondition,
                    f"transition {transition_id} precondition {index}",
                    states_key="allowed_states",
                )
            )

    invariant_ids: set[str] = set()
    for invariant in model.get("state_invariants", []):
        invariant_id = invariant.get("invariant_id")
        if invariant_id in invariant_ids:
            issues.append(f"duplicate state invariant {invariant_id!r}")
        invariant_ids.add(invariant_id)
        issues.extend(
            _state_reference_issues(
                axes,
                invariant.get("when", {}),
                f"invariant {invariant_id} when",
                states_key="states",
            )
        )
        for index, requirement in enumerate(invariant.get("requires", [])):
            issues.extend(
                _state_reference_issues(
                    axes,
                    requirement,
                    f"invariant {invariant_id} requirement {index}",
                    states_key="states",
                )
            )

    return issues


def state_vector_issues(
    contract: Mapping[str, Any],
    state_vector: Mapping[str, str],
) -> list[str]:
    model = lifecycle_model(contract)
    axes = model.get("axes", {})
    issues: list[str] = []
    if set(state_vector) != set(axes):
        missing = sorted(set(axes) - set(state_vector))
        extra = sorted(set(state_vector) - set(axes))
        if missing:
            issues.append("state vector missing axes: " + ", ".join(missing))
        if extra:
            issues.append("state vector has unknown axes: " + ", ".join(extra))
        return issues

    for axis_id, state_id in state_vector.items():
        if state_id not in axes[axis_id]["states"]:
            issues.append(f"state vector has unknown {axis_id} state {state_id!r}")
    if issues:
        return issues

    for invariant in model.get("state_invariants", []):
        condition = invariant["when"]
        if state_vector[condition["axis"]] not in condition["states"]:
            continue
        for requirement in invariant["requires"]:
            if state_vector[requirement["axis"]] not in requirement["states"]:
                issues.append(
                    f"state vector violates {invariant['invariant_id']}: "
                    f"{requirement['axis']} must be one of {', '.join(requirement['states'])}"
                )
    return issues


def transition_request_issues(
    contract: Mapping[str, Any],
    request: Mapping[str, Any],
) -> list[str]:
    model = lifecycle_model(contract)
    transitions = model.get("transitions", {})
    transition_id = request.get("transition_id")
    transition = transitions.get(transition_id)
    if transition is None:
        return [f"unsupported transition {transition_id!r}"]

    current_state = request.get("current_state", {})
    requested_state = request.get("requested_state", {})
    issues = state_vector_issues(contract, current_state)
    issues.extend(state_vector_issues(contract, requested_state))
    if issues:
        return issues

    changed_axes = {
        axis_id
        for axis_id in model["axes"]
        if current_state[axis_id] != requested_state[axis_id]
    }
    axis_id = transition["axis"]
    if changed_axes != {axis_id}:
        issues.append(
            f"transition {transition_id} must change only {axis_id}; changed axes were {', '.join(sorted(changed_axes)) or 'none'}"
        )
    if current_state[axis_id] not in transition["from_states"]:
        issues.append(
            f"transition {transition_id} does not allow source state {current_state[axis_id]!r}"
        )
    if requested_state[axis_id] not in transition["to_states"]:
        issues.append(
            f"transition {transition_id} does not allow target state {requested_state[axis_id]!r}"
        )
    if request.get("source_authority_role") != transition["source_authority_role"]:
        issues.append(
            f"transition {transition_id} requires source authority {transition['source_authority_role']!r}"
        )
    if request.get("target_owner_role") != transition["target_owner_role"]:
        issues.append(
            f"transition {transition_id} requires target owner {transition['target_owner_role']!r}"
        )
    claimed_maturity = request.get("implementation_maturity")
    transition_maturity = transition["implementation_maturity"]
    if claimed_maturity not in IMPLEMENTATION_MATURITY:
        issues.append(
            f"transition {transition_id} requires a recognized implementation maturity claim"
        )
    elif IMPLEMENTATION_MATURITY[claimed_maturity] > IMPLEMENTATION_MATURITY[transition_maturity]:
        issues.append(
            f"transition {transition_id} maturity claim {claimed_maturity!r} exceeds contract maturity {transition_maturity!r}"
        )
    if request.get("envelope_type") != transition["required_envelope"]:
        issues.append(
            f"transition {transition_id} requires envelope {transition['required_envelope']!r}"
        )
    envelope = request.get("envelope")
    if not isinstance(envelope, Mapping):
        issues.append(f"transition {transition_id} requires a structured envelope")
    else:
        required_fields = model["envelopes"][transition["required_envelope"]][
            "required_fields"
        ]
        missing_fields = sorted(
            field
            for field in required_fields
            if field not in envelope
            or (field != "recovery" and not envelope.get(field))
        )
        if missing_fields:
            issues.append(
                f"transition {transition_id} envelope is missing fields: {', '.join(missing_fields)}"
            )
        if envelope.get("transition_id") != transition_id:
            issues.append(
                f"transition {transition_id} envelope transition_id does not match the request"
            )
    missing_evidence = sorted(
        set(transition["required_evidence"]) - set(request.get("evidence_types", []))
    )
    if missing_evidence:
        issues.append(
            f"transition {transition_id} is missing evidence: {', '.join(missing_evidence)}"
        )
    for precondition in transition.get("preconditions", []):
        if current_state[precondition["axis"]] not in precondition["allowed_states"]:
            issues.append(
                f"transition {transition_id} precondition failed: {precondition['axis']} must be one of "
                + ", ".join(precondition["allowed_states"])
            )

    recovery = request.get("recovery")
    if recovery is not None:
        decision = recovery.get("decision")
        if decision not in transition["allowed_recovery_decisions"]:
            issues.append(f"transition {transition_id} does not allow recovery decision {decision!r}")
        else:
            required_fields = model["recovery_contract"]["requirements"][decision]
            missing_fields = sorted(
                field for field in required_fields if not recovery.get(field)
            )
            if missing_fields:
                issues.append(
                    f"recovery decision {decision!r} is missing fields: {', '.join(missing_fields)}"
                )

    return issues
