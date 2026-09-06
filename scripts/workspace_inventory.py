#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from contracts_lib import dump_json, load_json, load_yaml
from workspace_intake import canonical_digest


ARTIFACT_SCHEMAS = {
    "workspace-inventory-promotion-request": "workspace-inventory-promotion-request.schema.json",
    "workspace-inventory-promotion-readiness": "workspace-inventory-promotion-readiness.schema.json",
    "workspace-inventory-promotion-mutation": "workspace-inventory-promotion-mutation.schema.json",
    "workspace-inventory-promotion-readback": "workspace-inventory-promotion-readback.schema.json",
    "workspace-inventory-promotion-receipt": "workspace-inventory-promotion-receipt.schema.json",
    "workspace-inventory-lifecycle-request": "workspace-inventory-lifecycle-request.schema.json",
    "workspace-inventory-lifecycle-readiness": "workspace-inventory-lifecycle-readiness.schema.json",
    "workspace-inventory-lifecycle-mutation": "workspace-inventory-lifecycle-mutation.schema.json",
    "workspace-inventory-lifecycle-readback": "workspace-inventory-lifecycle-readback.schema.json",
    "workspace-inventory-lifecycle-receipt": "workspace-inventory-lifecycle-receipt.schema.json",
}
DIGEST_FIELDS = {
    "workspace-inventory-promotion-request": "request_digest",
    "workspace-inventory-promotion-readiness": "readiness_digest",
    "workspace-inventory-promotion-mutation": "mutation_digest",
    "workspace-inventory-promotion-readback": "readback_digest",
    "workspace-inventory-promotion-receipt": "receipt_digest",
    "workspace-inventory-lifecycle-request": "request_digest",
    "workspace-inventory-lifecycle-readiness": "readiness_digest",
    "workspace-inventory-lifecycle-mutation": "mutation_digest",
    "workspace-inventory-lifecycle-readback": "readback_digest",
    "workspace-inventory-lifecycle-receipt": "receipt_digest",
}
COLLECTIONS = {"repo": "repos", "product": "products", "component": "components"}
INVENTORY_FILES = {kind: f"contracts/{collection}.yaml" for kind, collection in COLLECTIONS.items()}
DEFAULT_BRANCHES = {"main", "master"}
HISTORY_FILE = "contracts/workspace-inventory-history.yaml"
LIFECYCLE_TRANSITIONS = {
    "update": {"active": "active", "suspended": "suspended"},
    "suspend": {"active": "suspended"},
    "restore": {"suspended": "active", "retired": "active"},
    "retire": {"active": "retired", "suspended": "retired"},
}


class WorkspaceInventoryError(RuntimeError):
    pass


def artifact_digest(payload: dict[str, Any], digest_field: str) -> str:
    projection = copy.deepcopy(payload)
    projection.pop(digest_field, None)
    return canonical_digest(projection)


def bind_artifact_digest(payload: dict[str, Any]) -> dict[str, Any]:
    artifact_type = str(payload.get("artifact_type"))
    digest_field = DIGEST_FIELDS.get(artifact_type)
    if digest_field is None:
        raise WorkspaceInventoryError(f"unsupported promotion artifact type: {artifact_type!r}")
    result = copy.deepcopy(payload)
    result[digest_field] = artifact_digest(result, digest_field)
    return result


def validate_artifact(repo_root: Path, payload: dict[str, Any]) -> None:
    artifact_type = str(payload.get("artifact_type"))
    schema_name = ARTIFACT_SCHEMAS.get(artifact_type)
    if schema_name is None:
        raise WorkspaceInventoryError(f"unsupported promotion artifact type: {artifact_type!r}")
    schema = load_json(repo_root / "contracts" / "schemas" / schema_name)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = [
        f"{'.'.join(str(part) for part in error.path) or '$'}: {error.message}"
        for error in sorted(validator.iter_errors(payload), key=lambda error: list(error.path))
    ]
    if errors:
        raise WorkspaceInventoryError("artifact schema validation failed: " + "; ".join(errors))
    digest_field = DIGEST_FIELDS[artifact_type]
    expected = artifact_digest(payload, digest_field)
    if payload[digest_field] != expected:
        raise WorkspaceInventoryError(
            f"{digest_field} does not match {artifact_type} canonical content: "
            f"expected {expected}, got {payload[digest_field]}"
        )


def current_branch(repo_root: Path) -> str:
    result = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    branch = result.stdout.strip()
    if not branch:
        raise WorkspaceInventoryError("inventory mutation is denied on a detached Git head")
    return branch


def _validate_source_branch(branch: str) -> None:
    if branch in DEFAULT_BRANCHES:
        raise WorkspaceInventoryError(
            f"inventory mutation is denied on default branch {branch!r}; use a review branch"
        )


def _load_inventory(repo_root: Path, kind: str) -> dict[str, Any]:
    return load_yaml(repo_root / INVENTORY_FILES[kind])


def _inventory_record(inventory: dict[str, Any], kind: str, name: str) -> dict[str, Any] | None:
    record = inventory.get(COLLECTIONS[kind], {}).get(name)
    if record is not None:
        return record
    if kind == "repo":
        return inventory.get("retired_repos", {}).get(name)
    return None


def current_state(repo_root: Path, kind: str, name: str) -> dict[str, Any]:
    intake = load_yaml(repo_root / "contracts" / "intake-register.yaml")
    inventory = _load_inventory(repo_root, kind)
    intake_entry = intake.get(COLLECTIONS[kind], {}).get(name)
    active_record = _inventory_record(inventory, kind, name)
    return {
        "target": {"kind": kind, "name": name, "record_id": f"{kind}:{name}"},
        "intake_register_digest": canonical_digest(intake),
        "active_inventory_digest": canonical_digest(inventory),
        "intake_entry_version": intake_entry.get("record", {}).get("version") if intake_entry else None,
        "intake_entry_digest": canonical_digest(intake_entry) if intake_entry else None,
        "active_record_version": active_record.get("record", {}).get("version") if active_record else None,
        "active_record_digest": canonical_digest(active_record) if active_record else None,
    }


def current_lifecycle_state(repo_root: Path, kind: str, name: str) -> dict[str, Any]:
    inventory = _load_inventory(repo_root, kind)
    record = _inventory_record(inventory, kind, name)
    if record is None:
        raise WorkspaceInventoryError("lifecycle target is missing from active inventory")
    history = load_yaml(repo_root / HISTORY_FILE)
    return {
        "target": {"kind": kind, "name": name, "record_id": f"{kind}:{name}"},
        "active_inventory_digest": canonical_digest(inventory),
        "history_digest": canonical_digest(history),
        "record_version": record["record"]["version"],
        "record_digest": canonical_digest(record),
        "posture": record["posture"],
    }


def _validate_contract(repo_root: Path, path: str, payload: dict[str, Any]) -> None:
    schema = load_json(repo_root / "contracts" / "schemas" / f"{Path(path).stem}.schema.json")
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = [
        f"{'.'.join(str(part) for part in error.path) or '$'}: {error.message}"
        for error in sorted(validator.iter_errors(payload), key=lambda error: list(error.path))
    ]
    if errors:
        raise WorkspaceInventoryError(f"{path} validation failed: " + "; ".join(errors))


def _validate_compatibility_alias(kind: str, entry: dict[str, Any]) -> None:
    if kind == "product":
        if entry.get("lifecycle") != entry.get("maturity"):
            raise WorkspaceInventoryError("product lifecycle compatibility alias must equal maturity")
    elif entry.get("lifecycle") != entry.get("posture"):
        raise WorkspaceInventoryError(f"{kind} lifecycle compatibility alias must equal posture")


def _validate_request_bindings(
    request: dict[str, Any],
    readiness: dict[str, Any],
    state: dict[str, Any],
    intake_entry: dict[str, Any],
) -> None:
    target = request["target"]
    if target["record_id"] != f"{target['kind']}:{target['name']}":
        raise WorkspaceInventoryError("promotion target record_id does not match kind and name")
    if readiness["request_ref"] != {
        "id": request["request_id"],
        "digest": request["request_digest"],
    }:
        raise WorkspaceInventoryError("readiness does not bind the supplied promotion request")
    if readiness["target"] != target:
        raise WorkspaceInventoryError("readiness target does not match the promotion request")
    if readiness["outcome"] != "ready":
        raise WorkspaceInventoryError(f"promotion requires ready outcome, got {readiness['outcome']!r}")
    expected = request["expected_state"]
    for field in ("intake_register_digest", "active_inventory_digest"):
        if expected[field] != state[field]:
            raise WorkspaceInventoryError(f"stale {field.replace('_', ' ')}")
    if expected["active_record_version"] is not None:
        raise WorkspaceInventoryError("new promotion must expect no active record version")
    if expected["intake_entry_version"] != state["intake_entry_version"]:
        raise WorkspaceInventoryError("stale intake entry version")
    if expected["intake_entry_digest"] != state["intake_entry_digest"]:
        raise WorkspaceInventoryError("stale intake entry digest")
    if intake_entry.get("status") != "admitted":
        raise WorkspaceInventoryError("only an admitted intake entry can be promoted")
    if request["intake_entry_ref"] != {
        "id": intake_entry["record"]["id"],
        "version": intake_entry["record"]["version"],
        "digest": state["intake_entry_digest"],
    }:
        raise WorkspaceInventoryError("promotion intake_entry_ref does not bind canonical intake truth")
    if readiness["observed_state"] != expected:
        raise WorkspaceInventoryError("readiness observed_state does not bind the requested source versions")
    if request["active_record"]["kind"] != target["kind"]:
        raise WorkspaceInventoryError("active_record kind does not match promotion target")
    if request["active_record"]["id"] != target["record_id"]:
        raise WorkspaceInventoryError("active_record id does not match promotion target")
    _validate_compatibility_alias(target["kind"], request["active_record"]["value"])


def _record_from_request(
    request: dict[str, Any], readiness: dict[str, Any], applied_at: str
) -> dict[str, Any]:
    target = request["target"]
    value = copy.deepcopy(request["active_record"]["value"])
    value["record"] = {
        "id": target["record_id"],
        "version": 1,
        "lineage": {
            "source": "workspace-intake",
            "source_ref": request["intake_entry_ref"]["id"],
            "source_digest": request["intake_entry_ref"]["digest"],
            "intake_entry_version": request["intake_entry_ref"]["version"],
        },
        "last_mutation": {
            "id": f"workspace-inventory-mutation:{request['idempotency_key']}",
            "action": "promote",
            "idempotency_key": request["idempotency_key"],
            "request_ref": request["request_id"],
            "request_digest": request["request_digest"],
            "readiness_ref": readiness["readiness_id"],
            "readiness_digest": readiness["readiness_digest"],
            "applied_at": applied_at,
        },
    }
    return value


def _write_yaml_temp(path: Path, payload: dict[str, Any]) -> Path:
    import yaml

    handle = tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False
    )
    try:
        yaml.safe_dump(payload, handle, sort_keys=False)
        handle.flush()
        os.fsync(handle.fileno())
        return Path(handle.name)
    finally:
        handle.close()


@contextmanager
def _authority_lock(repo_root: Path):
    lock_path = repo_root / ".art" / "locks" / "workspace-inventory.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _write_pair_atomically(
    intake_path: Path,
    intake: dict[str, Any],
    inventory_path: Path,
    inventory: dict[str, Any],
) -> None:
    original_intake = intake_path.read_bytes()
    original_inventory = inventory_path.read_bytes()
    intake_temp = _write_yaml_temp(intake_path, intake)
    inventory_temp = _write_yaml_temp(inventory_path, inventory)
    inventory_replaced = False
    intake_replaced = False
    try:
        os.replace(inventory_temp, inventory_path)
        inventory_replaced = True
        os.replace(intake_temp, intake_path)
        intake_replaced = True
    except BaseException:
        if inventory_replaced:
            inventory_path.write_bytes(original_inventory)
        if intake_replaced:
            intake_path.write_bytes(original_intake)
        raise
    finally:
        intake_temp.unlink(missing_ok=True)
        inventory_temp.unlink(missing_ok=True)


def _build_artifacts(
    request: dict[str, Any],
    readiness: dict[str, Any],
    record: dict[str, Any],
    intake: dict[str, Any],
    inventory: dict[str, Any],
    source_branch: str,
    completed_at: str,
    outcome: str,
) -> dict[str, dict[str, Any]]:
    target = request["target"]
    suffix = "replay" if outcome == "replayed" else "review-branch"
    mutation = bind_artifact_digest({
        "schema_version": 1,
        "artifact_type": "workspace-inventory-promotion-mutation",
        "mutation_id": f"workspace-inventory-mutation:{request['idempotency_key']}:{suffix}",
        "request_ref": {"id": request["request_id"], "digest": request["request_digest"]},
        "readiness_ref": {"id": readiness["readiness_id"], "digest": readiness["readiness_digest"]},
        "target": target,
        "source_branch": source_branch,
        "applied_at": completed_at,
        "changes": {
            "intake_entry_removed": True,
            "active_record_added": True,
            "active_record_version": record["record"]["version"],
        },
    })
    readback = bind_artifact_digest({
        "schema_version": 1,
        "artifact_type": "workspace-inventory-promotion-readback",
        "readback_id": f"workspace-inventory-readback:{request['idempotency_key']}:{suffix}",
        "mutation_ref": {"id": mutation["mutation_id"], "digest": mutation["mutation_digest"]},
        "target": target,
        "authority_state": "review-branch",
        "source_branch": source_branch,
        "observed_at": completed_at,
        "intake_register_digest": canonical_digest(intake),
        "active_inventory_digest": canonical_digest(inventory),
        "intake_entry_present": False,
        "active_record": record,
    })
    receipt = bind_artifact_digest({
        "schema_version": 1,
        "artifact_type": "workspace-inventory-promotion-receipt",
        "receipt_id": f"workspace-inventory-receipt:{request['idempotency_key']}:{suffix}",
        "request_ref": {"id": request["request_id"], "digest": request["request_digest"]},
        "readiness_ref": {"id": readiness["readiness_id"], "digest": readiness["readiness_digest"]},
        "mutation_ref": {"id": mutation["mutation_id"], "digest": mutation["mutation_digest"]},
        "readback_ref": {"id": readback["readback_id"], "digest": readback["readback_digest"]},
        "target": target,
        "operator_ref": request["operator_ref"],
        "correlation_ref": request["correlation_ref"],
        "idempotency_key": request["idempotency_key"],
        "completed_at": completed_at,
        "phase": "review-branch",
        "outcome": outcome,
    })
    return {"mutation": mutation, "readback": readback, "receipt": receipt}


def apply_promotion(
    repo_root: Path,
    request: dict[str, Any],
    readiness: dict[str, Any],
    output_dir: Path,
    source_branch: str,
    completed_at: str | None = None,
) -> dict[str, dict[str, Any]]:
    _validate_source_branch(source_branch)
    validate_artifact(repo_root, request)
    validate_artifact(repo_root, readiness)
    completed_at = completed_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    target = request["target"]
    kind = target["kind"]
    name = target["name"]

    with _authority_lock(repo_root):
        intake_path = repo_root / "contracts" / "intake-register.yaml"
        inventory_path = repo_root / INVENTORY_FILES[kind]
        intake = load_yaml(intake_path)
        inventory = load_yaml(inventory_path)
        state = current_state(repo_root, kind, name)
        existing = _inventory_record(inventory, kind, name)
        if existing is not None:
            last_mutation = existing.get("record", {}).get("last_mutation", {})
            if (
                last_mutation.get("idempotency_key") == request["idempotency_key"]
                and last_mutation.get("request_digest") == request["request_digest"]
                and last_mutation.get("readiness_digest") == readiness["readiness_digest"]
            ):
                artifacts = _build_artifacts(
                    request, readiness, existing, intake, inventory, source_branch, completed_at, "replayed"
                )
                _write_artifacts(repo_root, output_dir, artifacts)
                return artifacts
            raise WorkspaceInventoryError("active inventory identity already exists")
        intake_entry = intake.get(COLLECTIONS[kind], {}).get(name)
        if intake_entry is None:
            raise WorkspaceInventoryError("promotion target is missing from Workspace Intake")
        _validate_request_bindings(request, readiness, state, intake_entry)
        record = _record_from_request(request, readiness, completed_at)
        del intake[COLLECTIONS[kind]][name]
        inventory.setdefault(COLLECTIONS[kind], {})[name] = record
        _validate_contract(repo_root, "intake-register.yaml", intake)
        _validate_contract(repo_root, f"{COLLECTIONS[kind]}.yaml", inventory)
        _write_pair_atomically(intake_path, intake, inventory_path, inventory)
        artifacts = _build_artifacts(
            request, readiness, record, intake, inventory, source_branch, completed_at, "prepared"
        )
        _write_artifacts(repo_root, output_dir, artifacts)
        return artifacts


def history_event_digest(event: dict[str, Any]) -> str:
    projection = copy.deepcopy(event)
    projection.pop("event_digest", None)
    return canonical_digest(projection)


def bind_history_event_digest(event: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(event)
    result["event_digest"] = history_event_digest(result)
    return result


def _target_history(history: dict[str, Any], record_id: str) -> list[dict[str, Any]]:
    return [event for event in history.get("events", []) if event["target"]["record_id"] == record_id]


def _validate_history(repo_root: Path, history: dict[str, Any]) -> None:
    _validate_contract(repo_root, "workspace-inventory-history.yaml", history)
    seen_ids: set[str] = set()
    by_target: dict[str, list[dict[str, Any]]] = {}
    for event in history["events"]:
        if event["event_id"] in seen_ids:
            raise WorkspaceInventoryError(f"duplicate history event identity: {event['event_id']}")
        seen_ids.add(event["event_id"])
        if event["event_digest"] != history_event_digest(event):
            raise WorkspaceInventoryError(
                f"history event digest does not match canonical content: {event['event_id']}"
            )
        by_target.setdefault(event["target"]["record_id"], []).append(event)
    for record_id, events in by_target.items():
        for index, event in enumerate(events, start=1):
            if event["sequence"] != index:
                raise WorkspaceInventoryError(
                    f"history sequence for {record_id} must be contiguous from 1"
                )
            expected_previous = None
            if index > 1:
                previous = events[index - 2]
                expected_previous = {
                    "id": previous["event_id"],
                    "digest": previous["event_digest"],
                }
                if event["before"] != previous["after"]:
                    raise WorkspaceInventoryError(
                        f"history before state for {event['event_id']} does not match the previous after state"
                    )
            if event["previous_event_ref"] != expected_previous:
                raise WorkspaceInventoryError(
                    f"history previous_event_ref is invalid for {event['event_id']}"
                )


def _validate_lifecycle_bindings(
    request: dict[str, Any],
    readiness: dict[str, Any],
    state: dict[str, Any],
    record: dict[str, Any],
    history: dict[str, Any],
) -> str:
    target = request["target"]
    if target["record_id"] != f"{target['kind']}:{target['name']}":
        raise WorkspaceInventoryError("lifecycle target record_id does not match kind and name")
    if readiness["request_ref"] != {
        "id": request["request_id"],
        "digest": request["request_digest"],
    }:
        raise WorkspaceInventoryError("readiness does not bind the supplied lifecycle request")
    if readiness["target"] != target or readiness["action"] != request["action"]:
        raise WorkspaceInventoryError("readiness target or action does not match the lifecycle request")
    if readiness["outcome"] != "ready":
        raise WorkspaceInventoryError(
            f"lifecycle mutation requires ready outcome, got {readiness['outcome']!r}"
        )
    if readiness["observed_state"] != request["expected_state"]:
        raise WorkspaceInventoryError("readiness observed_state does not bind the requested source versions")
    for field in (
        "active_inventory_digest",
        "history_digest",
        "record_version",
        "record_digest",
        "posture",
    ):
        if request["expected_state"][field] != state[field]:
            raise WorkspaceInventoryError(f"stale lifecycle {field.replace('_', ' ')}")
    action = request["action"]
    current_posture = record["posture"]
    next_posture = LIFECYCLE_TRANSITIONS.get(action, {}).get(current_posture)
    if next_posture is None:
        raise WorkspaceInventoryError(
            f"illegal inventory transition: {action} from {current_posture}"
        )
    if action == "update":
        requested_value = request["requested_value"]
        if "record" in requested_value:
            raise WorkspaceInventoryError("requested_value must not replace the record envelope")
        if requested_value.get("posture") != current_posture:
            raise WorkspaceInventoryError("update must preserve inventory posture")
        _validate_compatibility_alias(target["kind"], requested_value)
    if action == "restore":
        prior_events = _target_history(history, target["record_id"])
        if not prior_events:
            raise WorkspaceInventoryError("restore requires a prior suspension or retirement history event")
        latest = prior_events[-1]
        expected_ref = {"id": latest["event_id"], "digest": latest["event_digest"]}
        if request["prior_event_ref"] != expected_ref:
            raise WorkspaceInventoryError("restore prior_event_ref does not bind the latest lifecycle event")
        if latest["action"] not in {"suspend", "retire"}:
            raise WorkspaceInventoryError("restore requires the latest event to be suspension or retirement")
    return next_posture


def _lifecycle_record_after(
    request: dict[str, Any],
    readiness: dict[str, Any],
    record: dict[str, Any],
    next_posture: str,
    applied_at: str,
) -> dict[str, Any]:
    kind = request["target"]["kind"]
    if request["action"] == "update":
        result = copy.deepcopy(request["requested_value"])
    else:
        result = copy.deepcopy(record)
        result.pop("record", None)
        if kind == "repo" and next_posture == "active":
            result.pop("replaced_by", None)
        result["posture"] = next_posture
        if kind != "product":
            result["lifecycle"] = next_posture
    result["record"] = copy.deepcopy(record["record"])
    result["record"]["version"] += 1
    result["record"]["last_mutation"] = {
        "id": f"workspace-inventory-lifecycle:{request['idempotency_key']}",
        "action": request["action"],
        "idempotency_key": request["idempotency_key"],
        "request_ref": request["request_id"],
        "request_digest": request["request_digest"],
        "readiness_ref": readiness["readiness_id"],
        "readiness_digest": readiness["readiness_digest"],
        "applied_at": applied_at,
    }
    return result


def _replace_inventory_record(
    inventory: dict[str, Any], kind: str, name: str, record: dict[str, Any]
) -> None:
    collection = COLLECTIONS[kind]
    if kind != "repo":
        inventory[collection][name] = record
        return
    inventory.setdefault("repos", {}).pop(name, None)
    inventory.setdefault("retired_repos", {}).pop(name, None)
    destination = "retired_repos" if record["posture"] == "retired" else "repos"
    inventory[destination][name] = record


def _build_history_event(
    request: dict[str, Any],
    readiness: dict[str, Any],
    before: dict[str, Any],
    after: dict[str, Any],
    history: dict[str, Any],
    applied_at: str,
) -> dict[str, Any]:
    target = request["target"]
    prior_events = _target_history(history, target["record_id"])
    previous = prior_events[-1] if prior_events else None
    event = {
        "event_id": f"workspace-inventory-event:{target['kind']}:{target['name']}:{after['record']['version']}",
        "event_digest": "sha256:" + "0" * 64,
        "sequence": len(prior_events) + 1,
        "target": copy.deepcopy(target),
        "action": request["action"],
        "idempotency_key": request["idempotency_key"],
        "before": {
            "record_version": before["record"]["version"],
            "record_digest": canonical_digest(before),
            "posture": before["posture"],
        },
        "after": {
            "record_version": after["record"]["version"],
            "record_digest": canonical_digest(after),
            "posture": after["posture"],
        },
        "request_ref": {"id": request["request_id"], "digest": request["request_digest"]},
        "readiness_ref": {
            "id": readiness["readiness_id"],
            "digest": readiness["readiness_digest"],
        },
        "previous_event_ref": (
            {"id": previous["event_id"], "digest": previous["event_digest"]}
            if previous
            else None
        ),
        "operator_ref": request["operator_ref"],
        "applied_at": applied_at,
    }
    return bind_history_event_digest(event)


def _build_lifecycle_artifacts(
    request: dict[str, Any],
    readiness: dict[str, Any],
    before: dict[str, Any],
    after: dict[str, Any],
    event: dict[str, Any],
    inventory: dict[str, Any],
    history: dict[str, Any],
    source_branch: str,
    completed_at: str,
    outcome: str,
) -> dict[str, dict[str, Any]]:
    target = request["target"]
    suffix = "replay" if outcome == "replayed" else "review-branch"
    mutation = bind_artifact_digest({
        "schema_version": 1,
        "artifact_type": "workspace-inventory-lifecycle-mutation",
        "mutation_id": f"workspace-inventory-lifecycle-mutation:{request['idempotency_key']}:{suffix}",
        "request_ref": {"id": request["request_id"], "digest": request["request_digest"]},
        "readiness_ref": {"id": readiness["readiness_id"], "digest": readiness["readiness_digest"]},
        "target": copy.deepcopy(target),
        "action": request["action"],
        "source_branch": source_branch,
        "applied_at": completed_at,
        "changes": {
            "before_version": before["record"]["version"],
            "after_version": after["record"]["version"],
            "before_posture": before["posture"],
            "after_posture": after["posture"],
            "history_event_appended": outcome != "replayed",
        },
    })
    readback = bind_artifact_digest({
        "schema_version": 1,
        "artifact_type": "workspace-inventory-lifecycle-readback",
        "readback_id": f"workspace-inventory-lifecycle-readback:{request['idempotency_key']}:{suffix}",
        "mutation_ref": {"id": mutation["mutation_id"], "digest": mutation["mutation_digest"]},
        "target": copy.deepcopy(target),
        "action": request["action"],
        "authority_state": "review-branch",
        "source_branch": source_branch,
        "observed_at": completed_at,
        "active_inventory_digest": canonical_digest(inventory),
        "history_digest": canonical_digest(history),
        "record": copy.deepcopy(after),
        "history_event_ref": {"id": event["event_id"], "digest": event["event_digest"]},
    })
    receipt = bind_artifact_digest({
        "schema_version": 1,
        "artifact_type": "workspace-inventory-lifecycle-receipt",
        "receipt_id": f"workspace-inventory-lifecycle-receipt:{request['idempotency_key']}:{suffix}",
        "request_ref": {"id": request["request_id"], "digest": request["request_digest"]},
        "readiness_ref": {"id": readiness["readiness_id"], "digest": readiness["readiness_digest"]},
        "mutation_ref": {"id": mutation["mutation_id"], "digest": mutation["mutation_digest"]},
        "readback_ref": {"id": readback["readback_id"], "digest": readback["readback_digest"]},
        "target": copy.deepcopy(target),
        "action": request["action"],
        "operator_ref": request["operator_ref"],
        "correlation_ref": request["correlation_ref"],
        "idempotency_key": request["idempotency_key"],
        "completed_at": completed_at,
        "phase": "review-branch",
        "outcome": outcome,
    })
    return {"mutation": mutation, "readback": readback, "receipt": receipt}


def apply_lifecycle(
    repo_root: Path,
    request: dict[str, Any],
    readiness: dict[str, Any],
    output_dir: Path,
    source_branch: str,
    completed_at: str | None = None,
) -> dict[str, dict[str, Any]]:
    _validate_source_branch(source_branch)
    validate_artifact(repo_root, request)
    validate_artifact(repo_root, readiness)
    completed_at = completed_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    target = request["target"]
    kind = target["kind"]
    name = target["name"]

    with _authority_lock(repo_root):
        inventory_path = repo_root / INVENTORY_FILES[kind]
        history_path = repo_root / HISTORY_FILE
        inventory = _load_inventory(repo_root, kind)
        history = load_yaml(history_path)
        _validate_history(repo_root, history)
        record = _inventory_record(inventory, kind, name)
        if record is None:
            raise WorkspaceInventoryError("lifecycle target is missing from active inventory")
        target_events = _target_history(history, target["record_id"])
        matching_events = [
            event
            for event in target_events
            if event["idempotency_key"] == request["idempotency_key"]
            or event["request_ref"]["id"] == request["request_id"]
        ]
        if matching_events:
            event = matching_events[-1]
            if (
                event["idempotency_key"] != request["idempotency_key"]
                or event["request_ref"]
                != {"id": request["request_id"], "digest": request["request_digest"]}
                or event["readiness_ref"]
                != {"id": readiness["readiness_id"], "digest": readiness["readiness_digest"]}
            ):
                raise WorkspaceInventoryError(
                    "lifecycle request identity or idempotency key was reused with different evidence"
                )
            if event is not target_events[-1] or canonical_digest(record) != event["after"]["record_digest"]:
                raise WorkspaceInventoryError(
                    "lifecycle replay is superseded by a later canonical mutation"
                )
            artifacts = _build_lifecycle_artifacts(
                request,
                readiness,
                {"record": {"version": event["before"]["record_version"]}, "posture": event["before"]["posture"]},
                record,
                event,
                inventory,
                history,
                source_branch,
                completed_at,
                "replayed",
            )
            _write_artifacts(repo_root, output_dir, artifacts)
            return artifacts
        state = current_lifecycle_state(repo_root, kind, name)
        next_posture = _validate_lifecycle_bindings(request, readiness, state, record, history)
        updated = _lifecycle_record_after(request, readiness, record, next_posture, completed_at)
        _replace_inventory_record(inventory, kind, name, updated)
        event = _build_history_event(request, readiness, record, updated, history, completed_at)
        history["events"].append(event)
        _validate_contract(repo_root, f"{COLLECTIONS[kind]}.yaml", inventory)
        _validate_history(repo_root, history)
        _write_pair_atomically(inventory_path, inventory, history_path, history)
        artifacts = _build_lifecycle_artifacts(
            request,
            readiness,
            record,
            updated,
            event,
            inventory,
            history,
            source_branch,
            completed_at,
            "prepared",
        )
        _write_artifacts(repo_root, output_dir, artifacts)
        return artifacts


def _write_artifacts(repo_root: Path, output_dir: Path, artifacts: dict[str, dict[str, Any]]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, payload in artifacts.items():
        validate_artifact(repo_root, payload)
        dump_json(output_dir / f"{name}.json", payload)


def migrate_inventory(
    repo_root: Path,
    source_ref: str,
    recorded_at: str,
) -> dict[str, Any]:
    report: dict[str, Any] = {"schema_version": 1, "source_ref": source_ref, "inventories": {}}
    pending: dict[Path, dict[str, Any]] = {}
    for kind, collection in COLLECTIONS.items():
        path = repo_root / INVENTORY_FILES[kind]
        payload = load_yaml(path)
        if payload.get("schema_version") == 2:
            report["inventories"][kind] = {"status": "already-migrated", "count": len(payload[collection])}
            continue
        if payload.get("schema_version") != 1:
            raise WorkspaceInventoryError(f"unsupported {kind} inventory schema version")
        migrated = copy.deepcopy(payload)
        migrated["schema_version"] = 2
        groups = [migrated[collection]]
        if kind == "repo":
            groups.append(migrated.get("retired_repos", {}))
        count = 0
        for group in groups:
            for name, entry in group.items():
                legacy = copy.deepcopy(entry)
                if kind == "product":
                    entry["maturity"] = (
                        entry["lifecycle"]
                        if entry["lifecycle"] in {"platform-integrated", "fully-governed"}
                        else "owner-managed"
                    )
                    entry["posture"] = "active"
                else:
                    entry["posture"] = entry["lifecycle"]
                entry["record"] = {
                    "id": f"{kind}:{name}",
                    "version": 1,
                    "lineage": {
                        "source": "legacy-migration",
                        "source_ref": source_ref,
                        "source_digest": canonical_digest(legacy),
                        "intake_entry_version": None,
                    },
                    "last_mutation": {
                        "id": f"workspace-inventory-migration:{kind}:{name}:v1-v2",
                        "action": "migrate",
                        "idempotency_key": f"workspace-inventory-migration:{kind}:{name}:v1-v2",
                        "request_ref": None,
                        "request_digest": None,
                        "readiness_ref": None,
                        "readiness_digest": None,
                        "applied_at": recorded_at,
                    },
                }
                count += 1
        _validate_contract(repo_root, f"{collection}.yaml", migrated)
        pending[path] = migrated
        report["inventories"][kind] = {
            "status": "migrated",
            "count": count,
            "digest": canonical_digest(migrated),
        }
    originals = {path: path.read_bytes() for path in pending}
    temporary = {path: _write_yaml_temp(path, payload) for path, payload in pending.items()}
    replaced: list[Path] = []
    try:
        for path, temp in temporary.items():
            os.replace(temp, path)
            replaced.append(path)
    except BaseException:
        for path in replaced:
            path.write_bytes(originals[path])
        raise
    finally:
        for temp in temporary.values():
            temp.unlink(missing_ok=True)
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage reviewed Workspace active-inventory source changes")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    subparsers = parser.add_subparsers(dest="command", required=True)
    state_parser = subparsers.add_parser("state", help="print promotion concurrency bindings")
    state_parser.add_argument("--kind", choices=tuple(COLLECTIONS), required=True)
    state_parser.add_argument("--name", required=True)
    lifecycle_state_parser = subparsers.add_parser(
        "lifecycle-state", help="print lifecycle concurrency and history bindings"
    )
    lifecycle_state_parser.add_argument("--kind", choices=tuple(COLLECTIONS), required=True)
    lifecycle_state_parser.add_argument("--name", required=True)
    apply_parser = subparsers.add_parser("apply", help="prepare one reviewed intake-to-inventory promotion")
    apply_parser.add_argument("--request", type=Path, required=True)
    apply_parser.add_argument("--readiness", type=Path, required=True)
    apply_parser.add_argument("--output-dir", type=Path, required=True)
    lifecycle_parser = subparsers.add_parser(
        "lifecycle", help="prepare one reviewed active-inventory lifecycle change"
    )
    lifecycle_parser.add_argument("--request", type=Path, required=True)
    lifecycle_parser.add_argument("--readiness", type=Path, required=True)
    lifecycle_parser.add_argument("--output-dir", type=Path, required=True)
    migrate_parser = subparsers.add_parser("migrate", help="migrate v1 inventories to the v2 envelope")
    migrate_parser.add_argument("--source-ref", required=True)
    migrate_parser.add_argument("--recorded-at", required=True)
    migrate_parser.add_argument("--output", type=Path, required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    repo_root = args.repo_root.resolve()
    try:
        if args.command == "state":
            print(json.dumps(current_state(repo_root, args.kind, args.name), indent=2, sort_keys=True))
            return 0
        if args.command == "lifecycle-state":
            print(
                json.dumps(
                    current_lifecycle_state(repo_root, args.kind, args.name),
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0
        if args.command == "migrate":
            report = migrate_inventory(repo_root, args.source_ref, args.recorded_at)
            dump_json(args.output.resolve(), report)
            print(f"workspace inventory migrated: {sum(item['count'] for item in report['inventories'].values())} records")
            return 0
        if args.command == "lifecycle":
            artifacts = apply_lifecycle(
                repo_root=repo_root,
                request=load_json(args.request.resolve()),
                readiness=load_json(args.readiness.resolve()),
                output_dir=args.output_dir.resolve(),
                source_branch=current_branch(repo_root),
            )
        else:
            artifacts = apply_promotion(
                repo_root=repo_root,
                request=load_json(args.request.resolve()),
                readiness=load_json(args.readiness.resolve()),
                output_dir=args.output_dir.resolve(),
                source_branch=current_branch(repo_root),
            )
    except (OSError, subprocess.CalledProcessError, WorkspaceInventoryError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    receipt = artifacts["receipt"]
    print(
        f"workspace inventory {receipt['outcome']}: "
        f"{receipt['target']['record_id']} receipt={receipt['receipt_id']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
