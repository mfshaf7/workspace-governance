"""Pure policy planning for installation-private repository registration.

The caller supplies authenticated operator/custody and current durable state.
This module reads policy only. It never writes a record, invokes a model,
publishes source, issues a credential or grants runtime authority.
"""

from __future__ import annotations

import copy
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Callable

from jsonschema import Draft202012Validator, FormatChecker

from contracts_lib import load_json, load_yaml
from workspace_intake import (
    WorkspaceIntakeError, _build_entry, _validate_ai_decision,
    _validate_decision_bindings, _validate_domain_record, _validate_register,
    artifact_digest, canonical_digest, validate_artifact,
)
from workspace_repo_registration import _source_owner_admission_metadata


class InstancePolicyError(WorkspaceIntakeError):
    pass


def instance_policy_ref(policy_root: Path, revision: str) -> dict:
    return {"repo": "workspace-governance", "revision": revision,
            "contract_digest": "sha256:" + hashlib.sha256(
                (policy_root / "contracts/instance-operational-records.yaml").read_bytes()
            ).hexdigest()}


def plan_repository_intake(
    *, policy_root: Path, policy_revision: str, instance_id: str, request: dict, decision: dict,
    operator_ref: str, current: dict | None, legacy_records: dict,
    now: datetime, owner_readiness_reader: Callable[[str, dict], dict] | None = None,
) -> dict:
    """Plan one accepted change against exact internal state and legacy claims.

    `current` must come from the verified internal store, `legacy_records` from
    the trusted legacy authority, and `owner_readiness_reader` from the runtime's
    existing owner-controls service. None is a browser-selected authority.
    """
    if (now.tzinfo is None or not isinstance(legacy_records, dict)
            or any(not isinstance(entry, dict) for entry in legacy_records.values()) or not operator_ref.strip()):
        raise InstancePolicyError("Current policy, legacy authority and authenticated operator are required.")
    schema = load_json(policy_root / "contracts/schemas/instance-repository-intake-request.schema.json")
    if list(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(request)):
        raise InstancePolicyError("Internal repository request does not match its contract.")
    if request["request_digest"] != artifact_digest(request, "request_digest"):
        raise InstancePolicyError("Internal repository request digest does not match its accepted content.")
    if request["instance_id"] != instance_id:
        raise InstancePolicyError("The accepted registration belongs to another installation.")
    validate_artifact(policy_root, decision)
    _validate_decision_bindings(request, decision)
    _validate_ai_decision(policy_root, decision)
    if request["policy_ref"] != instance_policy_ref(policy_root, policy_revision):
        raise InstancePolicyError("Policy changed; review the current registration decision.")
    acceptance = decision["operator_acceptance"]
    if acceptance["operator_ref"] != operator_ref or request["requester_ref"] != operator_ref:
        raise InstancePolicyError("The accepted decision does not belong to the authenticated operator.")
    times = [datetime.fromisoformat(value.replace("Z", "+00:00")) for value in (
        request["requested_at"], decision["decided_at"], acceptance["recorded_at"],
    )]
    if any(value.tzinfo is None for value in times) or not times[0] <= times[1] <= now or not times[0] <= times[2] <= now:
        raise InstancePolicyError("The accepted request and decision need valid current chronology.")

    target, approved = request["target"], request["requested_record"]
    if target["record_id"] != f"repo:{target['name']}":
        raise InstancePolicyError("The internal repository target is inconsistent.")
    binding = approved["provider_repository"]
    if target["name"] in legacy_records or any(
        isinstance(entry.get("provider_repository"), dict)
        and all(entry["provider_repository"].get(field) == binding[field]
                for field in ("provider", "provider_repository_id"))
        for entry in legacy_records.values()
    ):
        raise InstancePolicyError("Legacy authority already owns this key or provider identity; explicit migration is required.")
    expected = request["expected_state"]
    observed = ({"record_version": current["receipt"]["version"], "record_digest": current["receipt"]["record_digest"]}
                if current is not None else {"record_version": None, "record_digest": None})
    if expected != observed or (request["action"] == "add") != (current is None):
        raise InstancePolicyError("The internal repository changed; review its current version.")
    if current is not None:
        entry = current["record"]
        if entry.get("phase") != "intake" or current["receipt"]["record_id"] != target["record_id"]:
            raise InstancePolicyError("An inventory record cannot be replaced by an intake update.")
        if request["source"] != entry["record"]["source"]:
            raise InstancePolicyError("Preserve the original canonical custody source.")
        if any(binding[field] != entry["provider_repository"][field] for field in ("provider", "provider_repository_id")):
            raise InstancePolicyError("Preserve the original provider repository identity.")

    suggestion = decision.get("ai_suggestion", {}).get("decision_id")
    if suggestion and any(entry.get("ai_suggestion", {}).get("decision_id") == suggestion
                          for entry in legacy_records.values()):
        raise InstancePolicyError("The AI suggestion already belongs to a legacy decision.")

    classification = request["requested_classification"]
    _validate_domain_record(classification, "repo", approved,
                            load_yaml(policy_root / "contracts/intake-policy.yaml"))
    if classification != "out-of-scope" and (
        approved["repo_class"] != "product-source" or approved["security_owner"] is not None
        or not _source_owner_admission_metadata(approved)
    ):
        raise InstancePolicyError("The current internal route covers source-only project repositories; control authority needs its explicit policy review.")
    owner_readiness = None
    if classification == "admitted":
        if not callable(owner_readiness_reader):
            raise InstancePolicyError("Current trusted owner-controls readiness is required before admission.")
        owner_readiness = owner_readiness_reader(target["name"], copy.deepcopy(binding))
        proof_body = copy.deepcopy(owner_readiness) if isinstance(owner_readiness, dict) else {}
        proof_digest = proof_body.pop("receipt_digest", None)
        if (not isinstance(owner_readiness, dict) or proof_digest != canonical_digest(proof_body)
                or owner_readiness.get("schema_version") != 1
                or owner_readiness.get("owner_repo") != target["name"]
                or owner_readiness.get("provider_repository") != binding
                or owner_readiness.get("scope") != "source-owner-controls-readiness"
                or any(not re.fullmatch(r"[0-9a-f]{40}", str(owner_readiness.get(field, "")))
                       for field in ("fetched_base", "canonical_checkout_commit"))
                or not re.fullmatch(r"sha256:[0-9a-f]{64}", str(owner_readiness.get("evidence_profile_digest", "")))
                or not re.fullmatch(r"oos://repository-owner-bootstrap/requests/[^/]+", str(owner_readiness.get("source_request_ref", "")))
                or any(owner_readiness.get(field) is not False
                       for field in ("app_acceptance", "inventory_admission", "runtime_activation"))):
            raise InstancePolicyError("Owner-controls readiness does not bind this exact project repository.")
        proof_revision = owner_readiness.get("source_request_revision")
        if not isinstance(proof_revision, str):
            raise InstancePolicyError("Owner-controls evidence has no valid revision time.")
        proof_at = datetime.fromisoformat(proof_revision.replace("Z", "+00:00"))
        if proof_at.tzinfo is None or proof_at > now:
            raise InstancePolicyError("Owner-controls evidence has an invalid revision time.")

    version = (current["receipt"]["version"] if current is not None else 0) + 1
    at = now.isoformat()
    entry = _build_entry(request, decision, version, at)
    entry["record"]["last_mutation"]["id"] = f"instance-intake:{request['idempotency_key']}"
    entry["record"]["last_mutation"]["request_ref"] = f"instance-repository-intake-request:{request['request_id']}"
    # Validate the same domain entry as source-backed Intake without inventing
    # a Git branch, register digest, review, merge or source receipt.
    _validate_register(policy_root, {"schema_version": 2, "repos": {target["name"]: entry}, "products": {}, "components": {}})
    readiness = {"schema_version": 1, "artifact_type": "instance-repository-intake-readiness",
                 "instance_id": instance_id,
                 "outcome": "allowed", "target": copy.deepcopy(target),
                 "policy_ref": copy.deepcopy(request["policy_ref"]),
                 "expected_state": copy.deepcopy(expected), "operator_ref": operator_ref,
                 "request_ref": {"id": request["request_id"], "digest": request["request_digest"]},
                 "decision_ref": {"id": decision["decision_id"], "digest": decision["decision_digest"]},
                 "evaluated_at": at, "canonical_mutation": False,
                 "owner_readiness": owner_readiness,
                 "obligations": ["durable-internal-readback", "no-runtime-activation", "no-inventory-promotion"]}
    return {"record": {"phase": "intake", **entry}, "readiness": readiness,
            "readiness_digest": canonical_digest(readiness), "decision_digest": decision["decision_digest"],
            "ai_decision_id": decision.get("ai_suggestion", {}).get("decision_id")}



def project_repository_source_authority(*, instance_id: str, name: str, current: dict,
                                        operation: str, policy_ref: dict) -> dict:
    """Project only a verified canonical record; no source effects or model calls."""
    from workspace_repo_registration import (RepositoryRegistrationError, proposed_source_owner_entry,
                                              active_source_owner_entry)
    if operation not in {"bootstrap", "configure-verification", "ordinary-source"}:
        raise InstancePolicyError("Select one supported source operation.")
    if (not isinstance(current, dict) or not isinstance(current.get("record"), dict)
            or not isinstance(current.get("receipt"), dict)):
        raise InstancePolicyError("A current internal repository record is required.")
    value, receipt = current["record"], current["receipt"]
    if (receipt.get("instance_id") != instance_id or receipt.get("record_id") != f"repo:{name}"
            or receipt.get("record_digest") != canonical_digest(value)
            or receipt.get("version") != value.get("record", {}).get("version")):
        raise InstancePolicyError("The source owner does not bind this installation record.")
    try:
        if operation == "bootstrap" and value.get("phase") == "intake":
            projected = proposed_source_owner_entry(name, value, value.get("provider_repository"))
        elif operation != "bootstrap" and value.get("phase") == "inventory":
            projected = active_source_owner_entry(name, value, value.get("provider_repository"))
        else:
            raise InstancePolicyError("This record phase does not allow the selected source operation.")
    except RepositoryRegistrationError as exc:
        raise InstancePolicyError("This repository is not eligible for the selected source operation.") from exc
    return {**projected, "canonical_authority": {"kind": "internal-instance-record", "instance_id": instance_id,
                                               "record_id": receipt["record_id"]},
            "record_ref": {"version": receipt["version"], "digest": receipt["record_digest"]},
            "policy_ref": copy.deepcopy(policy_ref)}


def main() -> int:
    """Finite private runtime bridge; input identity is authenticated upstream."""
    try:
        raw = sys.stdin.buffer.read(262_145)
        if len(raw) > 262_144:
            raise InstancePolicyError("Instance policy input exceeds its read bound.")
        value = json.loads(raw)
        if isinstance(value, dict) and value.get("operation") == "source-authority":
            if set(value) != {"operation", "instance_id", "name", "current", "source_operation", "policy_revision"}:
                raise InstancePolicyError("Internal source projection input is invalid.")
            result = project_repository_source_authority(instance_id=value["instance_id"], name=value["name"],
                current=value["current"], operation=value["source_operation"],
                policy_ref=instance_policy_ref(Path(__file__).resolve().parents[1], value["policy_revision"]))
            print(json.dumps(result, ensure_ascii=False, allow_nan=False, separators=(",", ":")))
            return 0
        if not isinstance(value, dict) or set(value) != {
            "policy_revision", "instance_id", "request", "decision", "operator_ref", "current",
            "legacy_records", "now", "owner_readiness",
        }:
            raise InstancePolicyError("Instance policy bridge input is invalid.")
        proof = value.pop("owner_readiness")
        value["now"] = datetime.fromisoformat(value["now"].replace("Z", "+00:00"))
        result = plan_repository_intake(
            policy_root=Path(__file__).resolve().parents[1], **value,
            owner_readiness_reader=(lambda *args: proof) if proof is not None else None,
        )
        print(json.dumps(result, ensure_ascii=False, allow_nan=False, separators=(",", ":")))
        return 0
    except (OSError, ValueError, KeyError, TypeError, WorkspaceIntakeError):
        # Do not echo project contents, source coordinates or schema values in
        # a worker's stderr/log stream. The authenticated workflow retains input.
        print("Internal repository policy did not authorize the requested transition.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
