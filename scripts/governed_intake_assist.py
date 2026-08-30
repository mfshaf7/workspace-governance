#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import urllib.error
import urllib.parse
import urllib.request
from uuid import uuid4

from jsonschema import Draft202012Validator, FormatChecker

from contracts_lib import load_yaml


DEFAULT_GATEWAY_URL = "http://127.0.0.1:18290"
DEFAULT_TIMEOUT_SECONDS = 60.0
LOCAL_CANDIDATE_ROOT = Path(".art/intake-assist")


class IntakeAssistError(RuntimeError):
    pass


def load_contract(repo_root: Path) -> dict:
    payload = load_yaml(repo_root / "contracts" / "governed-intake-assist.yaml")
    return payload["governed_intake_assist"]


def resolve_repo_ref(workspace_root: Path, reference: dict) -> Path:
    return workspace_root / reference["repo"] / reference["path"]


def validate_gateway_url(value: str) -> str:
    parsed = urllib.parse.urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise IntakeAssistError("gateway URL must be an absolute HTTP or HTTPS URL")
    if parsed.scheme == "http" and parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise IntakeAssistError("unencrypted gateway access is allowed only through loopback")
    return value.rstrip("/")


def resolve_candidate_output(repo_root: Path, value: Path) -> Path:
    candidate_root = (repo_root / LOCAL_CANDIDATE_ROOT).resolve()
    output = value.resolve() if value.is_absolute() else (repo_root / value).resolve()
    if not output.is_relative_to(candidate_root):
        raise IntakeAssistError(f"candidate output must stay under {candidate_root}")
    return output


def validate_live_contracts(repo_root: Path, workspace_root: Path, contract: dict) -> dict:
    activation = contract["activation_state"]
    if activation["live_consumption_allowed"] is not True:
        raise IntakeAssistError("governed intake-assist live consumption is not active")

    refs = contract["platform_contract_refs"]
    registry = load_yaml(resolve_repo_ref(workspace_root, refs["profile_registry"]))
    access_plane = load_yaml(resolve_repo_ref(workspace_root, refs["access_plane"]))["access_plane"]
    runtime_contract = load_yaml(resolve_repo_ref(workspace_root, refs["runtime_assist_contract"]))["contract"]
    consumer = contract["consumer"]
    profile = registry["model_profiles"].get(consumer["profile_id"])

    if not isinstance(profile, dict) or profile.get("status") != "active":
        raise IntakeAssistError("the governed intake model profile is not active")
    if access_plane.get("status") != "active":
        raise IntakeAssistError("the governed AI access plane is not active")
    if runtime_contract.get("status") != "active":
        raise IntakeAssistError("the governed runtime-assist contract is not active")
    if consumer["caller_id"] not in profile.get("allowed_callers", []):
        raise IntakeAssistError("the workspace intake-assist caller is not allowed by the profile")

    allowed_caller = next(
        (
            value
            for value in access_plane.get("allowed_callers", [])
            if value.get("caller_id") == consumer["caller_id"]
        ),
        None,
    )
    if allowed_caller is None:
        raise IntakeAssistError("the workspace intake-assist caller is not allowed by the access plane")

    provider_schema_ref = profile.get("provider_output_schema_ref")
    accepted_record_ref = profile.get("accepted_record_schema_ref")
    if provider_schema_ref != consumer["provider_output_schema_ref"]:
        raise IntakeAssistError("provider output schema differs between the consumer and active profile")
    if accepted_record_ref != consumer["accepted_record_schema_ref"]:
        raise IntakeAssistError("accepted record schema differs between the consumer and active profile")
    if allowed_caller.get("required_provider_output_schema_ref") != provider_schema_ref:
        raise IntakeAssistError("access-plane provider output schema differs from the active profile")
    if allowed_caller.get("accepted_record_schema_ref") != accepted_record_ref:
        raise IntakeAssistError("access-plane accepted record schema differs from the active profile")

    return {
        "access_plane": access_plane,
        "profile": profile,
        "provider_output_schema_ref": provider_schema_ref,
    }


def invoke_gateway(gateway_url: str, payload: dict, timeout_seconds: float) -> dict:
    request = urllib.request.Request(
        f"{gateway_url}/v1/governed-ai/invoke",
        data=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            status = response.status
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            body = json.loads(exc.read().decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            body = {"error": "invalid-gateway-error-response"}
        reasons = body.get("reasons") or [body.get("error", "gateway-denied-request")]
        raise IntakeAssistError(f"gateway denied the request ({exc.code}): {', '.join(reasons)}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise IntakeAssistError(f"gateway is unavailable: {exc}") from exc
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise IntakeAssistError("gateway returned invalid JSON") from exc

    if status != 200 or not isinstance(body, dict):
        raise IntakeAssistError(f"gateway returned unexpected status {status}")
    return body


def validate_suggestion(repo_root: Path, contract: dict, response: dict, correlation_id: str) -> None:
    schema_ref = contract["consumer"]["suggestion_candidate_schema_ref"]
    schema = json.loads((repo_root / schema_ref["path"]).read_text(encoding="utf-8"))
    errors = sorted(
        Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(response),
        key=lambda error: list(error.path),
    )
    if errors:
        detail = "; ".join(error.message for error in errors)
        raise IntakeAssistError(f"gateway suggestion failed schema validation: {detail}")

    consumer = contract["consumer"]
    expected = {
        "caller_id": consumer["caller_id"],
        "decision_id": correlation_id,
        "invocation_path": consumer["invocation_path"],
        "policy_decision": "allow",
        "policy_status": "active",
        "profile_id": consumer["profile_id"],
    }
    mismatches = [key for key, value in expected.items() if response.get(key) != value]
    if mismatches:
        raise IntakeAssistError("gateway suggestion identity mismatch: " + ", ".join(mismatches))


def validate_candidate_artifact(repo_root: Path, candidate: dict) -> None:
    schema_root = repo_root / "contracts" / "schemas"
    artifact_schema = json.loads(
        (schema_root / "intake-ai-suggestion-artifact.schema.json").read_text(encoding="utf-8")
    )
    suggestion_schema = json.loads(
        (schema_root / "intake-ai-suggestion-candidate.schema.json").read_text(encoding="utf-8")
    )
    artifact_errors = sorted(
        Draft202012Validator(
            artifact_schema,
            format_checker=FormatChecker(),
        ).iter_errors(candidate),
        key=lambda error: list(error.path),
    )
    suggestion_errors = sorted(
        Draft202012Validator(
            suggestion_schema,
            format_checker=FormatChecker(),
        ).iter_errors(candidate.get("suggestion")),
        key=lambda error: list(error.path),
    )
    errors = artifact_errors + suggestion_errors
    if errors:
        detail = "; ".join(error.message for error in errors)
        raise IntakeAssistError(f"candidate artifact failed schema validation: {detail}")


def write_candidate(repo_root: Path, path: Path, response: dict, notes: str, operator_id: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    candidate = {
        "schema_version": 1,
        "artifact_type": "governed_intake_suggestion_candidate",
        "status": "awaiting-operator-decision",
        "captured_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "input_digest": "sha256:" + hashlib.sha256(notes.encode("utf-8")).hexdigest(),
        "initiating_operator_id": operator_id,
        "suggestion": response,
    }
    validate_candidate_artifact(repo_root, candidate)
    path.write_text(json.dumps(candidate, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Request a bounded workspace intake suggestion through the governed AI gateway."
    )
    parser.add_argument("--notes", required=True, help="Operator-supplied intake notes admitted by the consumer contract.")
    parser.add_argument("--operator-id", required=True, help="Identity of the operator initiating the suggestion request.")
    parser.add_argument("--output", required=True, type=Path, help="Local candidate artifact path; canonical workspace truth is not changed.")
    parser.add_argument("--correlation-id", help="Stable decision correlation id; generated when omitted.")
    parser.add_argument("--gateway-url", default=DEFAULT_GATEWAY_URL)
    parser.add_argument("--timeout-seconds", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--workspace-root", type=Path, default=Path(__file__).resolve().parents[2])
    return parser


def main() -> int:
    args = build_parser().parse_args()
    repo_root = args.repo_root.resolve()
    workspace_root = args.workspace_root.resolve()
    contract = load_contract(repo_root)
    if args.timeout_seconds <= 0:
        raise IntakeAssistError("timeout must be greater than zero")
    live = validate_live_contracts(repo_root, workspace_root, contract)
    gateway_url = validate_gateway_url(args.gateway_url)
    output = resolve_candidate_output(repo_root, args.output)
    correlation_id = args.correlation_id or f"intake-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}-{uuid4().hex[:8]}"
    consumer = contract["consumer"]
    provider_schema_ref = live["provider_output_schema_ref"]

    payload = {
        "profile_id": consumer["profile_id"],
        "caller_identity": {
            "caller_id": consumer["caller_id"],
            "caller_repo": consumer["caller_repo"],
            "caller_workflow": consumer["caller_workflow"],
            "decision_or_correlation_id": correlation_id,
            "requested_profile_id": consumer["profile_id"],
        },
        "operator_identity": {"operator_id": args.operator_id},
        "operator_acceptance_state": "not-recorded",
        "provider_output_schema_ref": f"{provider_schema_ref['repo']}/{provider_schema_ref['path']}",
        "input": {"operator_supplied_intake_notes": args.notes},
    }
    response = invoke_gateway(gateway_url, payload, args.timeout_seconds)
    validate_suggestion(repo_root, contract, response, correlation_id)
    write_candidate(repo_root, output, response, args.notes, args.operator_id)
    print(f"governed suggestion captured: {output}")
    print(
        f"suggested_decision={response['suggested_decision']} confidence={response['confidence']} "
        f"audit_ref={response['audit_ref']}"
    )
    print("next step: review the candidate, then bind explicit operator acceptance into the Workspace Intake v2 request and decision path")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except IntakeAssistError as exc:
        raise SystemExit(f"ERROR: {exc}") from exc
