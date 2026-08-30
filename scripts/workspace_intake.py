#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
import yaml

from contracts_lib import load_json, load_yaml


ARTIFACT_SCHEMAS = {
    "workspace-intake-request": "workspace-intake-request.schema.json",
    "workspace-intake-decision": "workspace-intake-decision.schema.json",
    "workspace-intake-mutation": "workspace-intake-mutation.schema.json",
    "workspace-intake-receipt": "workspace-intake-receipt.schema.json",
    "workspace-intake-readback": "workspace-intake-readback.schema.json",
}
DIGEST_FIELDS = {
    "workspace-intake-request": "request_digest",
    "workspace-intake-decision": "decision_digest",
    "workspace-intake-mutation": "mutation_digest",
    "workspace-intake-receipt": "receipt_digest",
    "workspace-intake-readback": "readback_digest",
}
COLLECTIONS = {
    "repo": "repos",
    "product": "products",
    "component": "components",
}
DEFAULT_BRANCHES = {"main", "master"}


class WorkspaceIntakeError(RuntimeError):
    pass


def _reject_floats(value: Any, path: str = "$") -> None:
    if isinstance(value, float):
        raise WorkspaceIntakeError(
            f"{path}: floating-point values are not allowed by workspace-canonical-json-v1"
        )
    if isinstance(value, dict):
        for key, child in value.items():
            _reject_floats(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_floats(child, f"{path}[{index}]")


def canonical_json(value: Any) -> str:
    _reject_floats(value)
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def canonical_digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def artifact_digest(payload: dict[str, Any], digest_field: str) -> str:
    projection = copy.deepcopy(payload)
    projection.pop(digest_field, None)
    return canonical_digest(projection)


def bind_artifact_digest(payload: dict[str, Any]) -> dict[str, Any]:
    artifact_type = payload.get("artifact_type")
    digest_field = DIGEST_FIELDS.get(str(artifact_type))
    if digest_field is None:
        raise WorkspaceIntakeError(f"unsupported workspace intake artifact type: {artifact_type!r}")
    result = copy.deepcopy(payload)
    result[digest_field] = artifact_digest(result, digest_field)
    return result


def _schema_errors(repo_root: Path, payload: dict[str, Any]) -> list[str]:
    artifact_type = payload.get("artifact_type")
    schema_name = ARTIFACT_SCHEMAS.get(str(artifact_type))
    if schema_name is None:
        return [f"unsupported artifact_type {artifact_type!r}"]
    schema = load_json(repo_root / "contracts" / "schemas" / schema_name)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    return [
        f"{'.'.join(str(part) for part in error.path) or '$'}: {error.message}"
        for error in sorted(validator.iter_errors(payload), key=lambda error: list(error.path))
    ]


def validate_artifact(repo_root: Path, payload: dict[str, Any]) -> None:
    errors = _schema_errors(repo_root, payload)
    if errors:
        raise WorkspaceIntakeError("artifact schema validation failed: " + "; ".join(errors))
    artifact_type = str(payload["artifact_type"])
    digest_field = DIGEST_FIELDS[artifact_type]
    expected = artifact_digest(payload, digest_field)
    if payload[digest_field] != expected:
        raise WorkspaceIntakeError(
            f"{digest_field} does not match {artifact_type} canonical content: "
            f"expected {expected}, got {payload[digest_field]}"
        )


def _record_id(kind: str, name: str) -> str:
    return f"{kind}:{name}"


def _artifact_ref(artifact_id: str, digest: str) -> dict[str, str]:
    return {"id": artifact_id, "digest": digest}


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
        raise WorkspaceIntakeError("workspace intake mutation is denied on a detached Git head")
    return branch


def _validate_source_branch(branch: str) -> None:
    if branch in DEFAULT_BRANCHES:
        raise WorkspaceIntakeError(
            f"workspace intake mutation is denied on default branch {branch!r}; use a review branch"
        )


def _load_register(repo_root: Path) -> dict[str, Any]:
    return load_yaml(repo_root / "contracts" / "intake-register.yaml")


def _validate_register(repo_root: Path, register: dict[str, Any]) -> None:
    schema = load_json(repo_root / "contracts" / "schemas" / "intake-register.schema.json")
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = [
        f"{'.'.join(str(part) for part in error.path) or '$'}: {error.message}"
        for error in sorted(validator.iter_errors(register), key=lambda error: list(error.path))
    ]
    if errors:
        raise WorkspaceIntakeError("intake register validation failed: " + "; ".join(errors))


def _active_inventory_names(repo_root: Path, kind: str) -> set[str]:
    if kind == "repo":
        payload = load_yaml(repo_root / "contracts" / "repos.yaml")
        return set(payload.get("repos", {})) | set(payload.get("retired_repos", {}))
    payload = load_yaml(repo_root / "contracts" / f"{COLLECTIONS[kind]}.yaml")
    return set(payload.get(COLLECTIONS[kind], {}))


def _validate_target_bindings(request: dict[str, Any], decision: dict[str, Any]) -> None:
    target = request["target"]
    expected_id = _record_id(target["kind"], target["name"])
    if target["record_id"] != expected_id:
        raise WorkspaceIntakeError(
            f"request target identity conflict: expected {expected_id!r}, got {target['record_id']!r}"
        )
    if decision["target"] != target:
        raise WorkspaceIntakeError("decision target does not exactly match the request target")
    if request["requested_record"]["kind"] != target["kind"]:
        raise WorkspaceIntakeError("requested_record.kind does not match request target kind")
    approved_record = decision["outcome"].get("approved_record")
    if not isinstance(approved_record, dict) or approved_record.get("kind") != target["kind"]:
        raise WorkspaceIntakeError("approved_record.kind does not match request target kind")
    if approved_record != request["requested_record"]:
        raise WorkspaceIntakeError(
            "approved_record does not exactly match requested_record; revise and re-digest the request before approval"
        )


def _validate_decision_bindings(request: dict[str, Any], decision: dict[str, Any]) -> None:
    if decision["request_ref"] != _artifact_ref(request["request_id"], request["request_digest"]):
        raise WorkspaceIntakeError("decision request_ref does not bind the supplied request")
    outcome = decision["outcome"]
    if outcome["status"] != "allowed":
        raise WorkspaceIntakeError(
            f"workspace intake mutation requires an allowed decision, got {outcome['status']!r}"
        )
    if decision["operator_acceptance"]["state"] != "accepted":
        raise WorkspaceIntakeError("workspace intake mutation requires explicit operator acceptance")
    if outcome["classification"] != request["requested_classification"]:
        raise WorkspaceIntakeError("decision classification does not match the reviewed request")
    if outcome["owner_route"] != request["owner_route"]:
        raise WorkspaceIntakeError("decision owner route does not match the reviewed request")
    _validate_target_bindings(request, decision)


def _validate_ai_decision(repo_root: Path, decision: dict[str, Any]) -> None:
    if decision["decision_source"] != "ai-suggested":
        if "ai_suggestion" in decision:
            raise WorkspaceIntakeError("operator decisions cannot carry ai_suggestion evidence")
        return
    suggestion = decision.get("ai_suggestion")
    if not isinstance(suggestion, dict):
        raise WorkspaceIntakeError("AI-suggested decisions require explicit suggestion evidence")
    assist_payload = load_yaml(repo_root / "contracts" / "governed-intake-assist.yaml")
    assist = assist_payload.get("governed_intake_assist") or {}
    activation = assist.get("activation_state") or {}
    consumer = assist.get("consumer") or {}
    if (
        activation.get("source_contract_status") != "active"
        or activation.get("live_consumption_allowed") is not True
    ):
        raise WorkspaceIntakeError("AI-suggested intake is denied while governed intake assist is inactive")
    if suggestion.get("policy_status") != "active":
        raise WorkspaceIntakeError("AI-suggested intake requires active governed profile evidence")
    for field in ("profile_id", "caller_id", "invocation_path"):
        if suggestion.get(field) != consumer.get(field):
            raise WorkspaceIntakeError(
                f"AI suggestion {field} does not match the governed intake consumer"
            )
    classification = decision["outcome"]["classification"]
    if suggestion["operator_decision"] != classification:
        raise WorkspaceIntakeError("AI operator_decision does not match the approved classification")
    state = suggestion["acceptance_state"]
    if state == "accepted" and suggestion["suggested_decision"] != classification:
        raise WorkspaceIntakeError("accepted AI suggestion does not match the approved classification")
    if state == "overridden":
        if suggestion["suggested_decision"] == classification:
            raise WorkspaceIntakeError("overridden AI suggestion must differ from the approved classification")
        if not suggestion.get("override_reason"):
            raise WorkspaceIntakeError("overridden AI suggestion requires a reason")
    if suggestion["accepted_by"] != decision["operator_acceptance"]["operator_ref"]:
        raise WorkspaceIntakeError("AI acceptance identity does not match decision operator identity")


def _validate_domain_record(
    classification: str,
    kind: str,
    record: dict[str, Any],
    intake_policy: dict[str, Any],
) -> None:
    in_scope = classification in {"proposed", "admitted"}
    if in_scope and intake_policy["validation_behavior"][COLLECTIONS[kind]][
        "require_for_in_scope_intake"
    ] and "validation_behavior" not in record:
        raise WorkspaceIntakeError("in-scope intake records require validation_behavior")
    if not in_scope and "validation_behavior" in record:
        raise WorkspaceIntakeError("out-of-scope intake records cannot carry validation_behavior")

    if kind == "repo":
        if in_scope and not record.get("repo_class"):
            raise WorkspaceIntakeError("in-scope repo intake requires repo_class")
        if in_scope and not isinstance(record.get("requires_security_bindings"), bool):
            raise WorkspaceIntakeError(
                "in-scope repo intake requires an explicit requires_security_bindings boolean"
            )
        if in_scope and record.get("requires_security_bindings") and not record.get("security_owner"):
            raise WorkspaceIntakeError("repo security bindings require security_owner")
        if not in_scope and any(
            record.get(field) is not None
            for field in ("repo_class", "requires_security_bindings", "security_owner")
        ):
            raise WorkspaceIntakeError("out-of-scope repo metadata must remain null")
        return

    if kind == "product":
        required = ("platform_owner", "security_owner", "runtime_owner", "intended_endpoint")
        if in_scope and any(not record.get(field) for field in required):
            raise WorkspaceIntakeError(
                "in-scope product intake requires platform, security, runtime, and endpoint ownership"
            )
        if in_scope and not record.get("source_owners"):
            raise WorkspaceIntakeError("in-scope product intake requires at least one source owner")
        if not in_scope and (
            any(record.get(field) is not None for field in required) or record.get("source_owners")
        ):
            raise WorkspaceIntakeError("out-of-scope product ownership metadata must remain empty")
        return

    required = ("component_class", "owner_repo", "security_owner")
    if in_scope and any(not record.get(field) for field in required):
        raise WorkspaceIntakeError(
            "in-scope component intake requires component_class, owner_repo, and security_owner"
        )
    if not in_scope and any(record.get(field) is not None for field in (*required, "product")):
        raise WorkspaceIntakeError("out-of-scope component ownership metadata must remain null")


def _used_idempotency(
    register: dict[str, Any], idempotency_key: str
) -> tuple[str, dict[str, Any]] | None:
    for collection_name in COLLECTIONS.values():
        for name, entry in register[collection_name].items():
            mutation = (entry.get("record") or {}).get("last_mutation") or {}
            if mutation.get("idempotency_key") == idempotency_key:
                return f"{collection_name[:-1]}:{name}", entry
    return None


def _used_ai_decision(register: dict[str, Any], decision_id: str) -> str | None:
    for collection_name in COLLECTIONS.values():
        for name, entry in register[collection_name].items():
            suggestion = entry.get("ai_suggestion") or {}
            if suggestion.get("decision_id") == decision_id:
                return f"{collection_name[:-1]}:{name}"
    return None


def _build_entry(
    request: dict[str, Any],
    decision: dict[str, Any],
    version: int,
    applied_at: str,
) -> dict[str, Any]:
    target = request["target"]
    approved_record = copy.deepcopy(decision["outcome"]["approved_record"])
    approved_record.pop("kind")
    entry: dict[str, Any] = {
        "status": decision["outcome"]["classification"],
        "decision_source": decision["decision_source"],
        "owner_route": decision["outcome"]["owner_route"],
        "record": {
            "id": target["record_id"],
            "version": version,
            "source": copy.deepcopy(request["source"]),
            "decision": {
                "id": decision["decision_id"],
                "ref": f"workspace-intake-decision:{decision['decision_id']}",
                "digest": decision["decision_digest"],
                "source": decision["decision_source"],
                "operator_ref": decision["operator_acceptance"]["operator_ref"],
                "decided_at": decision["decided_at"],
            },
            "last_mutation": {
                "id": f"workspace-intake-mutation:{request['idempotency_key']}:apply",
                "idempotency_key": request["idempotency_key"],
                "request_ref": f"workspace-intake-request:{request['request_id']}",
                "request_digest": request["request_digest"],
                "decision_ref": f"workspace-intake-decision:{decision['decision_id']}",
                "decision_digest": decision["decision_digest"],
                "applied_at": applied_at,
            },
        },
    }
    entry.update(approved_record)
    if decision["decision_source"] == "ai-suggested":
        entry["ai_suggestion"] = copy.deepcopy(decision["ai_suggestion"])
    return entry


def _build_artifacts(
    *,
    request: dict[str, Any],
    decision: dict[str, Any],
    entry: dict[str, Any],
    source_branch: str,
    outcome: str,
    completed_at: str,
    before_register_digest: str,
    before_record_version: int | None,
    before_record_digest: str | None,
    after_register_digest: str,
) -> dict[str, dict[str, Any]]:
    target = request["target"]
    record_digest = canonical_digest(entry)
    register_token = after_register_digest.removeprefix("sha256:")
    evidence_suffix = (
        "source-preparation"
        if outcome == "applied"
        else f"source-replay:{register_token}"
    )
    mutation_suffix = "apply" if outcome == "applied" else f"replay:{register_token}"
    request_ref = _artifact_ref(request["request_id"], request["request_digest"])
    decision_ref = _artifact_ref(decision["decision_id"], decision["decision_digest"])
    mutation = bind_artifact_digest(
        {
            "schema_version": 2,
            "artifact_type": "workspace-intake-mutation",
            "mutation_id": f"workspace-intake-mutation:{request['idempotency_key']}:{mutation_suffix}",
            "created_at": completed_at,
            "request_ref": request_ref,
            "decision_ref": decision_ref,
            "target": copy.deepcopy(target),
            "action": request["action"],
            "result": outcome,
            "idempotency_key": request["idempotency_key"],
            "source_branch": source_branch,
            "before": {
                "register_digest": before_register_digest,
                "record_version": before_record_version,
                "record_digest": before_record_digest,
            },
            "after": {
                "register_digest": after_register_digest,
                "record_version": entry["record"]["version"],
                "record_digest": record_digest,
            },
        }
    )
    mutation_ref = _artifact_ref(mutation["mutation_id"], mutation["mutation_digest"])
    readback = bind_artifact_digest(
        {
            "schema_version": 2,
            "artifact_type": "workspace-intake-readback",
            "readback_id": f"workspace-intake-readback:{request['idempotency_key']}:{evidence_suffix}",
            "observed_at": completed_at,
            "target": copy.deepcopy(target),
            "mutation_ref": mutation_ref,
            "authority_state": "review-branch",
            "source_branch": source_branch,
            "register_digest": after_register_digest,
            "record_digest": record_digest,
            "record": copy.deepcopy(entry),
        }
    )
    readback_ref = _artifact_ref(readback["readback_id"], readback["readback_digest"])
    receipt = bind_artifact_digest(
        {
            "schema_version": 2,
            "artifact_type": "workspace-intake-receipt",
            "receipt_id": f"workspace-intake-receipt:{request['idempotency_key']}:{evidence_suffix}",
            "completed_at": completed_at,
            "request_ref": request_ref,
            "decision_ref": decision_ref,
            "mutation_ref": mutation_ref,
            "readback_ref": readback_ref,
            "target": copy.deepcopy(target),
            "phase": "source-preparation" if outcome == "applied" else "source-replay",
            "outcome": "prepared" if outcome == "applied" else "replayed",
            "idempotency_key": request["idempotency_key"],
            "canonical_authority": {
                "repo": "workspace-governance",
                "path": "contracts/intake-register.yaml",
                "branch": source_branch,
            },
        }
    )
    return {"mutation": mutation, "readback": readback, "receipt": receipt}


def _write_yaml_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        temporary = Path(handle.name)
        yaml.safe_dump(payload, handle, sort_keys=False)
        handle.flush()
        os.fsync(handle.fileno())
    try:
        os.replace(temporary, path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def _write_artifacts(output_dir: Path, artifacts: dict[str, dict[str, Any]]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, payload in artifacts.items():
        path = output_dir / f"{name}.json"
        temporary = output_dir / f".{name}.json.tmp"
        temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(temporary, path)


@contextmanager
def _authority_lock(repo_root: Path):
    lock_path = repo_root / ".art" / "locks" / "workspace-intake.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def apply_intake(
    *,
    repo_root: Path,
    request: dict[str, Any],
    decision: dict[str, Any],
    output_dir: Path,
    source_branch: str,
    completed_at: str | None = None,
) -> dict[str, dict[str, Any]]:
    repo_root = repo_root.resolve()
    _validate_source_branch(source_branch)
    validate_artifact(repo_root, request)
    validate_artifact(repo_root, decision)
    _validate_decision_bindings(request, decision)
    _validate_ai_decision(repo_root, decision)

    with _authority_lock(repo_root):
        return _apply_intake_locked(
            repo_root=repo_root,
            request=request,
            decision=decision,
            output_dir=output_dir,
            source_branch=source_branch,
            completed_at=completed_at,
        )


def _apply_intake_locked(
    *,
    repo_root: Path,
    request: dict[str, Any],
    decision: dict[str, Any],
    output_dir: Path,
    source_branch: str,
    completed_at: str | None,
) -> dict[str, dict[str, Any]]:
    register = _load_register(repo_root)
    _validate_register(repo_root, register)
    target = request["target"]
    kind = target["kind"]
    name = target["name"]
    collection_name = COLLECTIONS[kind]
    collection = register[collection_name]
    current_entry = collection.get(name)
    current_register_digest = canonical_digest(register)
    current_record_version = (
        current_entry["record"]["version"] if isinstance(current_entry, dict) else None
    )
    current_record_digest = canonical_digest(current_entry) if current_entry is not None else None

    used_key = _used_idempotency(register, request["idempotency_key"])
    if used_key is not None:
        used_target, used_entry = used_key
        used_mutation = used_entry["record"]["last_mutation"]
        if (
            used_target != target["record_id"]
            or used_mutation["request_digest"] != request["request_digest"]
            or used_mutation["decision_digest"] != decision["decision_digest"]
        ):
            raise WorkspaceIntakeError(
                f"idempotency conflict: {request['idempotency_key']!r} is already bound to {used_target}"
            )
        replayed_at = used_mutation["applied_at"]
        artifacts = _build_artifacts(
            request=request,
            decision=decision,
            entry=used_entry,
            source_branch=source_branch,
            outcome="replayed",
            completed_at=replayed_at,
            before_register_digest=current_register_digest,
            before_record_version=current_record_version,
            before_record_digest=current_record_digest,
            after_register_digest=current_register_digest,
        )
        for payload in artifacts.values():
            validate_artifact(repo_root, payload)
        _write_artifacts(output_dir, artifacts)
        return artifacts

    expected = request["expected_state"]
    if expected["register_digest"] != current_register_digest:
        raise WorkspaceIntakeError(
            f"stale register digest: expected {expected['register_digest']}, got {current_register_digest}"
        )
    if request["action"] == "add":
        if current_entry is not None:
            raise WorkspaceIntakeError(f"intake record already exists: {target['record_id']}")
        if expected["record_version"] is not None or expected["record_digest"] is not None:
            raise WorkspaceIntakeError("add requires null expected record version and digest")
        next_version = 1
    else:
        if current_entry is None:
            raise WorkspaceIntakeError(f"intake record does not exist for update: {target['record_id']}")
        if expected["record_version"] != current_record_version:
            raise WorkspaceIntakeError(
                f"stale record version: expected {expected['record_version']}, got {current_record_version}"
            )
        if expected["record_digest"] != current_record_digest:
            raise WorkspaceIntakeError(
                f"stale record digest: expected {expected['record_digest']}, got {current_record_digest}"
            )
        if request["source"] != current_entry["record"]["source"]:
            raise WorkspaceIntakeError(
                "intake source identity is immutable; update must preserve the original source binding"
            )
        next_version = current_record_version + 1

    if name in _active_inventory_names(repo_root, kind):
        raise WorkspaceIntakeError(
            f"intake and active inventory overlap is denied for {target['record_id']}"
        )
    if decision["decision_source"] == "ai-suggested":
        ai_decision_id = decision["ai_suggestion"]["decision_id"]
        used_by = _used_ai_decision(register, ai_decision_id)
        if used_by is not None:
            raise WorkspaceIntakeError(
                f"AI suggestion decision {ai_decision_id!r} is already applied by {used_by}"
            )

    policy = load_yaml(repo_root / "contracts" / "intake-policy.yaml")
    _validate_domain_record(
        decision["outcome"]["classification"],
        kind,
        decision["outcome"]["approved_record"],
        policy,
    )
    applied_at = completed_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    entry = _build_entry(request, decision, next_version, applied_at)
    updated_register = copy.deepcopy(register)
    updated_register[collection_name][name] = entry
    _validate_register(repo_root, updated_register)
    after_register_digest = canonical_digest(updated_register)
    artifacts = _build_artifacts(
        request=request,
        decision=decision,
        entry=entry,
        source_branch=source_branch,
        outcome="applied",
        completed_at=applied_at,
        before_register_digest=current_register_digest,
        before_record_version=current_record_version,
        before_record_digest=current_record_digest,
        after_register_digest=after_register_digest,
    )
    for payload in artifacts.values():
        validate_artifact(repo_root, payload)

    output_dir.mkdir(parents=True, exist_ok=True)
    _write_yaml_atomic(repo_root / "contracts" / "intake-register.yaml", updated_register)
    _write_artifacts(output_dir, artifacts)
    return artifacts


def current_state(repo_root: Path, kind: str, name: str) -> dict[str, Any]:
    register = _load_register(repo_root)
    _validate_register(repo_root, register)
    entry = register[COLLECTIONS[kind]].get(name)
    return {
        "target": {
            "kind": kind,
            "name": name,
            "record_id": _record_id(kind, name),
        },
        "expected_state": {
            "register_digest": canonical_digest(register),
            "record_version": entry["record"]["version"] if entry is not None else None,
            "record_digest": canonical_digest(entry) if entry is not None else None,
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Inspect or deterministically apply the Workspace Intake v2 authority contract."
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="workspace-governance repository root",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    state_parser = subparsers.add_parser("state", help="print current optimistic-concurrency bindings")
    state_parser.add_argument("--kind", choices=tuple(COLLECTIONS), required=True)
    state_parser.add_argument("--name", required=True)

    apply_parser = subparsers.add_parser("apply", help="apply one reviewed intake request and decision")
    apply_parser.add_argument("--request", type=Path, required=True)
    apply_parser.add_argument("--decision", type=Path, required=True)
    apply_parser.add_argument("--output-dir", type=Path, required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    repo_root = args.repo_root.resolve()
    try:
        if args.command == "state":
            print(json.dumps(current_state(repo_root, args.kind, args.name), indent=2, sort_keys=True))
            return 0
        request = load_json(args.request.resolve())
        decision = load_json(args.decision.resolve())
        artifacts = apply_intake(
            repo_root=repo_root,
            request=request,
            decision=decision,
            output_dir=args.output_dir.resolve(),
            source_branch=current_branch(repo_root),
        )
    except (OSError, subprocess.CalledProcessError, WorkspaceIntakeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    receipt = artifacts["receipt"]
    print(
        f"workspace intake {receipt['outcome']}: {receipt['target']['record_id']} "
        f"receipt={receipt['receipt_id']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
