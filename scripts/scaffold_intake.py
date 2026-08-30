#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys

from jsonschema import Draft202012Validator, FormatChecker

from contracts_lib import load_yaml
import workspace_intake


DEFAULT_SECURITY_OWNER = "security-architecture"
DEFAULT_DECISION_SOURCE = "operator"
INTAKE_STATUS_CHOICES = ("out-of-scope", "proposed", "admitted")
AI_ACCEPTANCE_STATE_CHOICES = ("accepted", "overridden")


def load_intake(repo_root: Path) -> dict:
    return load_yaml(repo_root / "contracts" / "intake-register.yaml")


def load_governed_intake_assist(repo_root: Path) -> dict:
    payload = load_yaml(repo_root / "contracts" / "governed-intake-assist.yaml")
    return payload["governed_intake_assist"]


def load_ai_candidate(repo_root: Path, path: Path) -> dict:
    try:
        artifact = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"AI suggestion candidate is missing: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"AI suggestion candidate is invalid JSON: {path}: {exc}") from exc

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
        ).iter_errors(artifact),
        key=lambda error: list(error.path),
    )
    suggestion_errors = sorted(
        Draft202012Validator(
            suggestion_schema,
            format_checker=FormatChecker(),
        ).iter_errors(artifact.get("suggestion")),
        key=lambda error: list(error.path),
    )
    errors = artifact_errors + suggestion_errors
    if errors:
        raise SystemExit(
            "AI suggestion candidate failed schema validation: "
            + "; ".join(error.message for error in errors)
        )
    return artifact["suggestion"]


def build_ai_suggestion(args: argparse.Namespace) -> dict | None:
    if args.decision_source != "ai-suggested":
        if args.ai_suggestion_file:
            raise SystemExit("--ai-suggestion-file requires --decision-source ai-suggested")
        return None
    if not args.ai_suggestion_file:
        raise SystemExit("--ai-suggestion-file required when --decision-source ai-suggested")
    activation = args.governed_intake_assist.get("activation_state") or {}
    if (
        activation.get("source_contract_status") != "active"
        or activation.get("live_consumption_allowed") is not True
    ):
        raise SystemExit("governed intake-assist is not active for AI-backed truth updates")
    suggestion_candidate = load_ai_candidate(args.repo_root, args.ai_suggestion_file.resolve())
    consumer = args.governed_intake_assist["consumer"]
    suggested_decision = suggestion_candidate["suggested_decision"]
    operator_decision = args.operator_decision
    acceptance_state = args.acceptance_state
    missing = [
        flag
        for flag, value in (
            ("--operator-decision", operator_decision),
            ("--acceptance-state", acceptance_state),
            ("--accepted-by", args.accepted_by),
            ("--accepted-at", args.accepted_at),
        )
        if not value
    ]
    if missing:
        raise SystemExit(" ".join(missing) + " required when --decision-source ai-suggested")
    if acceptance_state == "accepted" and suggested_decision != operator_decision:
        raise SystemExit("accepted AI suggestions require the suggested and operator decisions to match")
    if acceptance_state == "overridden" and suggested_decision == operator_decision:
        raise SystemExit("overridden AI suggestions require the suggested and operator decisions to differ")
    if acceptance_state == "overridden" and not args.override_reason:
        raise SystemExit("--override-reason required when --acceptance-state overridden")
    if operator_decision != args.status:
        raise SystemExit("--operator-decision must match the recorded --status")
    if suggestion_candidate["profile_id"] != consumer["profile_id"]:
        raise SystemExit("AI suggestion candidate profile_id does not match the governed consumer")
    if suggestion_candidate["caller_id"] != consumer["caller_id"]:
        raise SystemExit("AI suggestion candidate caller_id does not match the governed consumer")
    if suggestion_candidate["invocation_path"] != consumer["invocation_path"]:
        raise SystemExit("AI suggestion candidate invocation_path does not match the governed consumer")
    if suggestion_candidate["decision_id"] in args.used_ai_decision_ids:
        raise SystemExit("AI suggestion candidate decision_id has already been applied")
    suggestion = {
        "profile_id": suggestion_candidate["profile_id"],
        "policy_status": suggestion_candidate["policy_status"],
        "decision_id": suggestion_candidate["decision_id"],
        "generated_at": suggestion_candidate["generated_at"],
        "confidence": suggestion_candidate["confidence"],
        "caller_id": suggestion_candidate["caller_id"],
        "invocation_path": suggestion_candidate["invocation_path"],
        "suggested_decision": suggested_decision,
        "operator_decision": operator_decision,
        "acceptance_state": acceptance_state,
        "accepted_by": args.accepted_by,
        "accepted_at": args.accepted_at,
        "audit_ref": suggestion_candidate["audit_ref"],
    }
    if args.override_reason:
        suggestion["override_reason"] = args.override_reason
    return suggestion


def _validation_behavior(args: argparse.Namespace) -> dict | None:
    if args.status == "out-of-scope":
        return None
    missing = [
        flag
        for flag, value in (
            ("--validation-posture", args.validation_posture),
            ("--validation-graph-role", args.validation_graph_role),
            ("--validation-catalog-ref", args.validation_catalog_ref),
            ("--validation-notes", args.validation_notes),
        )
        if not value
    ]
    if missing:
        raise SystemExit(" ".join(missing) + " required for proposed or admitted intake")
    return {
        "posture": args.validation_posture,
        "wgcf_graph_role": args.validation_graph_role,
        "catalog_refs": args.validation_catalog_ref,
        "notes": args.validation_notes,
    }


def _requested_record(args: argparse.Namespace) -> dict:
    in_scope = args.status != "out-of-scope"
    record: dict = {"kind": args.kind}
    if args.kind == "repo":
        if in_scope and not args.repo_class:
            raise SystemExit("--repo-class is required for proposed or admitted repo intake")
        record.update(
            {
                "repo_class": args.repo_class if in_scope else None,
                "requires_security_bindings": args.requires_security_bindings if in_scope else None,
                "security_owner": (
                    args.security_owner
                    if in_scope and args.requires_security_bindings
                    else None
                ),
                "notes": args.notes,
            }
        )
    elif args.kind == "product":
        if in_scope:
            missing = [
                flag
                for flag, value in (
                    ("--runtime-owner", args.runtime_owner),
                    ("--source-owner", args.source_owner),
                    ("--intended-endpoint", args.intended_endpoint),
                )
                if not value
            ]
            if missing:
                raise SystemExit(" ".join(missing) + " required for proposed or admitted product intake")
        record.update(
            {
                "platform_owner": args.platform_owner if in_scope else None,
                "security_owner": args.security_owner if in_scope else None,
                "runtime_owner": args.runtime_owner if in_scope else None,
                "source_owners": args.source_owner if in_scope else [],
                "intended_endpoint": args.intended_endpoint if in_scope else None,
                "notes": args.notes,
            }
        )
    else:
        if in_scope:
            missing = [
                flag
                for flag, value in (
                    ("--component-class", args.component_class),
                    ("--owner-repo", args.owner_repo),
                )
                if not value
            ]
            if missing:
                raise SystemExit(" ".join(missing) + " required for proposed or admitted component intake")
        record.update(
            {
                "component_class": args.component_class if in_scope else None,
                "owner_repo": args.owner_repo if in_scope else None,
                "security_owner": args.security_owner if in_scope else None,
                "product": args.product if in_scope else None,
                "notes": args.notes,
            }
        )
    validation_behavior = _validation_behavior(args)
    if validation_behavior is not None:
        record["validation_behavior"] = validation_behavior
    return record


def add_ai_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--ai-suggestion-file", type=Path)
    parser.add_argument("--operator-decision", choices=INTAKE_STATUS_CHOICES)
    parser.add_argument("--acceptance-state", choices=AI_ACCEPTANCE_STATE_CHOICES)
    parser.add_argument("--override-reason")
    parser.add_argument("--accepted-by")
    parser.add_argument("--accepted-at")


def _add_common_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--name", required=True)
    parser.add_argument("--status", choices=INTAKE_STATUS_CHOICES, default="proposed")
    parser.add_argument(
        "--decision-source",
        choices=("operator", "ai-suggested"),
        default=DEFAULT_DECISION_SOURCE,
    )
    parser.add_argument("--owner-route", required=True)
    parser.add_argument(
        "--source-class",
        choices=("direct", "repository-custody", "prototype", "delivery"),
        required=True,
    )
    parser.add_argument("--source-ref", required=True)
    parser.add_argument("--source-digest", required=True)
    parser.add_argument("--request-id", required=True)
    parser.add_argument("--decision-id", required=True)
    parser.add_argument("--idempotency-key", required=True)
    parser.add_argument("--operator-ref", required=True)
    parser.add_argument("--requested-at")
    parser.add_argument("--decided-at")
    parser.add_argument("--output-dir", type=Path, default=Path(".art/workspace-intake"))
    parser.add_argument("--validation-posture")
    parser.add_argument("--validation-graph-role")
    parser.add_argument("--validation-catalog-ref", action="append", default=[])
    parser.add_argument("--validation-notes")
    parser.add_argument("--notes", required=True)
    add_ai_arguments(parser)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Compatibility front end for adding one Workspace Intake v2 record through the "
            "deterministic, review-branch-only authority engine."
        )
    )
    parser.add_argument(
        "--repo-root",
        default=Path(__file__).resolve().parents[1],
        type=Path,
        help="workspace-governance repository root",
    )
    subparsers = parser.add_subparsers(dest="kind", required=True)

    repo_parser = subparsers.add_parser("repo", help="prepare and apply a repo intake add")
    _add_common_arguments(repo_parser)
    repo_parser.add_argument("--repo-class")
    repo_parser.add_argument("--requires-security-bindings", action="store_true")
    repo_parser.add_argument("--security-owner", default=DEFAULT_SECURITY_OWNER)

    product_parser = subparsers.add_parser("product", help="prepare and apply a product intake add")
    _add_common_arguments(product_parser)
    product_parser.add_argument("--platform-owner", default="platform-engineering")
    product_parser.add_argument("--security-owner", default=DEFAULT_SECURITY_OWNER)
    product_parser.add_argument("--runtime-owner")
    product_parser.add_argument("--source-owner", action="append", default=[])
    product_parser.add_argument("--intended-endpoint")

    component_parser = subparsers.add_parser("component", help="prepare and apply a component intake add")
    _add_common_arguments(component_parser)
    component_parser.add_argument("--component-class")
    component_parser.add_argument("--owner-repo")
    component_parser.add_argument("--security-owner", default=DEFAULT_SECURITY_OWNER)
    component_parser.add_argument("--product")
    return parser


def _timestamp(value: str | None) -> str:
    return value or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def main() -> int:
    args = build_parser().parse_args()
    repo_root = args.repo_root.resolve()
    args.repo_root = repo_root
    args.governed_intake_assist = load_governed_intake_assist(repo_root)
    register = load_intake(repo_root)
    args.used_ai_decision_ids = {
        suggestion["decision_id"]
        for collection_name in ("repos", "products", "components")
        for entry in register[collection_name].values()
        if isinstance((suggestion := entry.get("ai_suggestion")), dict)
        and suggestion.get("decision_id")
    }
    requested_record = _requested_record(args)
    state = workspace_intake.current_state(repo_root, args.kind, args.name)
    requested_at = _timestamp(args.requested_at)
    decided_at = _timestamp(args.decided_at)
    request = workspace_intake.bind_artifact_digest(
        {
            "schema_version": 2,
            "artifact_type": "workspace-intake-request",
            "request_id": args.request_id,
            "requested_at": requested_at,
            "requester_ref": args.operator_ref,
            "source": {
                "class": args.source_class,
                "ref": args.source_ref,
                "digest": args.source_digest,
            },
            "target": state["target"],
            "action": "add",
            "requested_classification": args.status,
            "owner_route": args.owner_route,
            "requested_record": requested_record,
            "expected_state": state["expected_state"],
            "idempotency_key": args.idempotency_key,
        }
    )
    ai_suggestion = build_ai_suggestion(args)
    decision_payload = {
        "schema_version": 2,
        "artifact_type": "workspace-intake-decision",
        "decision_id": args.decision_id,
        "decided_at": decided_at,
        "request_ref": {
            "id": request["request_id"],
            "digest": request["request_digest"],
        },
        "target": request["target"],
        "decision_source": args.decision_source,
        "operator_acceptance": {
            "state": "accepted",
            "operator_ref": args.operator_ref,
            "recorded_at": decided_at,
        },
        "outcome": {
            "status": "allowed",
            "classification": args.status,
            "owner_route": args.owner_route,
            "approved_record": requested_record,
            "findings": [],
        },
    }
    if ai_suggestion is not None:
        decision_payload["ai_suggestion"] = ai_suggestion
    decision = workspace_intake.bind_artifact_digest(decision_payload)
    output_dir = args.output_dir
    if not output_dir.is_absolute():
        output_dir = repo_root / output_dir
    try:
        artifacts = workspace_intake.apply_intake(
            repo_root=repo_root,
            request=request,
            decision=decision,
            output_dir=output_dir,
            source_branch=workspace_intake.current_branch(repo_root),
        )
    except (
        OSError,
        subprocess.CalledProcessError,
        workspace_intake.WorkspaceIntakeError,
    ) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    receipt = artifacts["receipt"]
    print(
        f"workspace intake {receipt['outcome']}: {receipt['target']['record_id']} "
        f"receipt={receipt['receipt_id']}"
    )
    print("next step: validate the source change and submit it through the normal pull-request path")
    return 0


if __name__ == "__main__":
    sys.exit(main())
