"""Pure internal Inventory policy using existing source-only domain semantics."""
from __future__ import annotations

import copy
from datetime import datetime
import json
from pathlib import Path
import sys

from jsonschema import Draft202012Validator, FormatChecker
from contracts_lib import load_json
from workspace_intake import canonical_digest
from workspace_instance_records import InstancePolicyError, instance_policy_ref
from workspace_inventory import LIFECYCLE_TRANSITIONS, _record_from_request, _lifecycle_record_after
from workspace_repo_registration import _source_owner_admission_metadata, is_source_owner


def plan_repository_inventory(*, policy_root: Path, policy_revision: str, instance_id: str,
                              request: dict, operator_ref: str, current: dict | None,
                              legacy_records: dict, now: datetime) -> dict:
    schema = load_json(policy_root / "contracts/schemas/instance-repository-inventory-request.schema.json")
    if list(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(request)):
        raise InstancePolicyError("Internal inventory request does not match its contract.")
    original = {key: value for key, value in request.items() if key != "request_digest"}
    if (request["request_digest"] != canonical_digest(original) or request["instance_id"] != instance_id
            or request["policy_ref"] != instance_policy_ref(policy_root, policy_revision)
            or request["operator_ref"] != operator_ref or request["operator_acceptance"]["operator_ref"] != operator_ref):
        raise InstancePolicyError("Inventory decision does not bind its installation, policy and authenticated operator.")
    times = [datetime.fromisoformat(request[key].replace("Z", "+00:00")) for key in ("requested_at",)]
    times.append(datetime.fromisoformat(request["operator_acceptance"]["recorded_at"].replace("Z", "+00:00")))
    if now.tzinfo is None or any(value.tzinfo is None for value in times) or not times[0] <= times[1] <= now:
        raise InstancePolicyError("Inventory acceptance requires valid current chronology.")
    target, action = request["target"], request["action"]
    name = target["name"]
    if target["kind"] != "repo" or target["record_id"] != f"repo:{name}" or not isinstance(current, dict):
        raise InstancePolicyError("An existing internal repository registration is required.")
    before, receipt = current["record"], current["receipt"]
    if (receipt["record_id"] != target["record_id"] or receipt["instance_id"] != instance_id
            or canonical_digest(before) != receipt["record_digest"]
            or request["expected_state"] != {"record_version": receipt["version"], "record_digest": receipt["record_digest"]}):
        raise InstancePolicyError("Inventory changed; review the exact current record.")
    binding = before.get("provider_repository")
    if name in legacy_records or any(isinstance(entry.get("provider_repository"), dict) and isinstance(binding, dict)
            and all(entry["provider_repository"].get(key) == binding.get(key) for key in ("provider", "provider_repository_id"))
            for entry in legacy_records.values()):
        raise InstancePolicyError("Legacy authority already owns this identity; explicit migration is required.")
    value = request["requested_value"]
    if isinstance(value, dict) and ("record" in value or "phase" in value):
        raise InstancePolicyError("Inventory metadata cannot replace its canonical record envelope.")
    if action == "promote":
        if before.get("phase") != "intake" or before.get("status") != "admitted" or not _source_owner_admission_metadata(before):
            raise InstancePolicyError("Promote only the current admitted source-only registration.")
        if (value.get("posture") != "active" or value.get("lifecycle") != "active" or value.get("repo_class") != before["repo_class"]
                or value.get("requires_security_bindings") != before["requires_security_bindings"]
                or value.get("provider_repository") != binding):
            raise InstancePolicyError("Promotion must preserve admitted classification and provider identity.")
    else:
        if before.get("phase") != "inventory" or not is_source_owner(name, before):
            raise InstancePolicyError("Routine lifecycle changes require an existing source-only inventory owner.")
        next_posture = LIFECYCLE_TRANSITIONS.get(action, {}).get(before.get("posture"))
        if next_posture is None:
            raise InstancePolicyError("The requested transition is not allowed in the current posture.")
        if action == "restore" and (request["prior_receipt_digest"] != receipt["receipt_digest"]
                or receipt["action"] not in {"inventory.suspend", "inventory.retire"}):
            raise InstancePolicyError("Restore must bind the latest suspension or retirement receipt.")
        if action == "update":
            provider = value.get("provider_repository")
            if (value.get("posture") != before["posture"] or value.get("lifecycle") != before["posture"]
                    or not isinstance(provider, dict) or any(provider.get(key) != binding.get(key) for key in ("provider", "provider_repository_id"))):
                raise InstancePolicyError("Update must preserve current posture and physical repository identity.")
    decision_digest = canonical_digest({"request_ref": {"id": request["request_id"], "digest": request["request_digest"]},
                                       "operator_acceptance": request["operator_acceptance"]})
    readiness = {"schema_version": 1, "artifact_type": "instance-repository-inventory-readiness",
        "instance_id": instance_id, "outcome": "allowed", "target": copy.deepcopy(target), "action": action,
        "request_ref": {"id": request["request_id"], "digest": request["request_digest"]},
        "policy_ref": copy.deepcopy(request["policy_ref"]), "expected_state": copy.deepcopy(request["expected_state"]),
        "operator_ref": operator_ref, "evaluated_at": now.isoformat(), "canonical_mutation": False}
    readiness_digest = canonical_digest(readiness)
    # Reuse the canonical domain producers. Internal readiness is real evaluated
    # data; no Git commit, global-register digest or merge receipt is invented.
    producer_readiness = {"readiness_id": f"instance-inventory-readiness:{request['request_id']}", "readiness_digest": readiness_digest}
    if action == "promote":
        record = _record_from_request({**request, "active_record": {"value": value}, "intake_entry_ref": {
            "id": target["record_id"], "version": receipt["version"], "digest": receipt["record_digest"]}}, producer_readiness, now.isoformat())
        record["record"]["version"] = receipt["version"] + 1
    else:
        domain_before = {key: val for key, val in before.items() if key != "phase"}
        record = _lifecycle_record_after(request, producer_readiness, domain_before, next_posture, now.isoformat())
    record["record"]["last_mutation"]["id"] = f"instance-inventory:{request['idempotency_key']}"
    if record.get("repo_class") != "product-source" or not is_source_owner(name, record):
        raise InstancePolicyError("Routine registration cannot create control or Security-bound authority.")
    repository_schema = load_json(policy_root / "contracts/schemas/repos.schema.json")
    collection = "retired_repos" if record["posture"] == "retired" else "repos"
    entry_schema = {**repository_schema["properties"][collection]["additionalProperties"], "$defs": repository_schema["$defs"]}
    if list(Draft202012Validator(entry_schema, format_checker=FormatChecker()).iter_errors(record)):
        raise InstancePolicyError("The resulting repository metadata does not satisfy its domain contract.")
    return {"record": {"phase": "inventory", **record}, "readiness": readiness, "readiness_digest": readiness_digest,
            "decision_digest": decision_digest, "ai_decision_id": None}


def main() -> int:
    try:
        raw = sys.stdin.buffer.read(262145)
        if len(raw) > 262144:
            raise InstancePolicyError("Inventory policy input exceeds its bound.")
        value = json.loads(raw)
        if not isinstance(value, dict) or set(value) != {"policy_revision", "instance_id", "request", "operator_ref", "current", "legacy_records", "now"}:
            raise InstancePolicyError("Inventory policy bridge input is invalid.")
        value["now"] = datetime.fromisoformat(value["now"].replace("Z", "+00:00"))
        result = plan_repository_inventory(policy_root=Path(__file__).resolve().parents[1], **value)
        print(json.dumps(result, ensure_ascii=False, allow_nan=False, separators=(",", ":")))
        return 0
    except (OSError, ValueError, KeyError, TypeError, InstancePolicyError):
        print("Internal inventory policy did not authorize the transition.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
