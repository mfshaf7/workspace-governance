#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

from contracts_lib import dump_yaml, load_yaml


DEFAULT_SECURITY_OWNER = "security-architecture"
DEFAULT_DECISION_SOURCE = "operator"
AI_POLICY_STATUS_CHOICES = ("active", "suspended", "retired", "exception")
AI_CONFIDENCE_CHOICES = ("low", "medium", "high")
INTAKE_STATUS_CHOICES = ("out-of-scope", "proposed", "admitted")
AI_ACCEPTANCE_STATE_CHOICES = ("accepted", "overridden")


def load_intake(repo_root: Path) -> dict:
    return load_yaml(repo_root / "contracts" / "intake-register.yaml")


def load_governed_intake_assist(repo_root: Path) -> dict:
    payload = load_yaml(repo_root / "contracts" / "governed-intake-assist.yaml")
    return payload["governed_intake_assist"]


def write_intake(repo_root: Path, payload: dict) -> None:
    dump_yaml(repo_root / "contracts" / "intake-register.yaml", payload)


def build_ai_suggestion(args: argparse.Namespace) -> dict | None:
    if args.decision_source != "ai-suggested":
        return None
    consumer = args.governed_intake_assist["consumer"]
    suggested_decision = args.ai_suggested_decision or args.status
    operator_decision = args.operator_decision or args.status
    acceptance_state = args.acceptance_state
    if acceptance_state is None:
        acceptance_state = "accepted" if suggested_decision == operator_decision else "overridden"
    audit_ref = args.ai_audit_ref or f"intake-register:{args.kind}:{args.name}:{args.ai_decision_id}"
    missing = [
        flag
        for flag, value in (
            ("--ai-profile-id", args.ai_profile_id),
            ("--ai-policy-status", args.ai_policy_status),
            ("--ai-decision-id", args.ai_decision_id),
            ("--ai-generated-at", args.ai_generated_at),
            ("--ai-confidence", args.ai_confidence),
            ("--accepted-by", args.accepted_by),
            ("--accepted-at", args.accepted_at),
        )
        if not value
    ]
    if missing:
        raise SystemExit(" ".join(missing) + " required when --decision-source ai-suggested")
    if acceptance_state == "accepted" and suggested_decision != operator_decision:
        raise SystemExit("accepted AI suggestions require --ai-suggested-decision to match --operator-decision/status")
    if acceptance_state == "overridden" and suggested_decision == operator_decision:
        raise SystemExit("overridden AI suggestions require --ai-suggested-decision to differ from --operator-decision/status")
    if acceptance_state == "overridden" and not args.override_reason:
        raise SystemExit("--override-reason required when --acceptance-state overridden")
    if operator_decision != args.status:
        raise SystemExit("--operator-decision must match the recorded --status for intake-register truth")
    suggestion = {
        "profile_id": args.ai_profile_id,
        "policy_status": args.ai_policy_status,
        "decision_id": args.ai_decision_id,
        "generated_at": args.ai_generated_at,
        "confidence": args.ai_confidence,
        "caller_id": args.ai_caller_id or consumer["caller_id"],
        "invocation_path": args.ai_invocation_path or consumer["invocation_path"],
        "suggested_decision": suggested_decision,
        "operator_decision": operator_decision,
        "acceptance_state": acceptance_state,
        "accepted_by": args.accepted_by,
        "accepted_at": args.accepted_at,
        "audit_ref": audit_ref,
    }
    if args.override_reason:
        suggestion["override_reason"] = args.override_reason
    return {
        key: value
        for key, value in suggestion.items()
        if value is not None
    }


def with_optional_ai_suggestion(entry: dict, args: argparse.Namespace) -> dict:
    ai_suggestion = build_ai_suggestion(args)
    if ai_suggestion is not None:
        entry["ai_suggestion"] = ai_suggestion
    return entry


def add_repo_entry(register: dict, args: argparse.Namespace) -> str:
    repos = register["repos"]
    if args.name in repos:
        raise SystemExit(f"repo intake entry already exists: {args.name}")
    in_scope = args.status != "out-of-scope"
    if in_scope and not args.repo_class:
        raise SystemExit("--repo-class is required when status is proposed or admitted")
    repos[args.name] = with_optional_ai_suggestion({
        "status": args.status,
        "decision_source": args.decision_source,
        "repo_class": args.repo_class if in_scope else None,
        "requires_security_bindings": args.requires_security_bindings if in_scope else None,
        "security_owner": args.security_owner if in_scope and args.requires_security_bindings else None,
        "notes": args.notes,
    }, args)
    return f"repo:{args.name}"


def add_product_entry(register: dict, args: argparse.Namespace) -> str:
    products = register["products"]
    if args.name in products:
        raise SystemExit(f"product intake entry already exists: {args.name}")
    in_scope = args.status != "out-of-scope"
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
            raise SystemExit(
                " ".join(missing) + " required when status is proposed or admitted"
            )
    products[args.name] = with_optional_ai_suggestion({
        "status": args.status,
        "decision_source": args.decision_source,
        "platform_owner": args.platform_owner if in_scope else None,
        "security_owner": args.security_owner if in_scope else None,
        "runtime_owner": args.runtime_owner if in_scope else None,
        "source_owners": args.source_owner if in_scope else [],
        "intended_endpoint": args.intended_endpoint if in_scope else None,
        "notes": args.notes,
    }, args)
    return f"product:{args.name}"


def add_component_entry(register: dict, args: argparse.Namespace) -> str:
    components = register["components"]
    if args.name in components:
        raise SystemExit(f"component intake entry already exists: {args.name}")
    in_scope = args.status != "out-of-scope"
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
            raise SystemExit(
                " ".join(missing) + " required when status is proposed or admitted"
            )
    components[args.name] = with_optional_ai_suggestion({
        "status": args.status,
        "decision_source": args.decision_source,
        "component_class": args.component_class if in_scope else None,
        "owner_repo": args.owner_repo if in_scope else None,
        "security_owner": args.security_owner if in_scope else None,
        "product": args.product if in_scope else None,
        "notes": args.notes,
    }, args)
    return f"component:{args.name}"


def add_ai_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--ai-profile-id")
    parser.add_argument("--ai-policy-status", choices=AI_POLICY_STATUS_CHOICES)
    parser.add_argument("--ai-decision-id")
    parser.add_argument("--ai-generated-at")
    parser.add_argument("--ai-confidence", choices=AI_CONFIDENCE_CHOICES)
    parser.add_argument("--ai-caller-id")
    parser.add_argument("--ai-invocation-path")
    parser.add_argument("--ai-suggested-decision", choices=INTAKE_STATUS_CHOICES)
    parser.add_argument("--operator-decision", choices=INTAKE_STATUS_CHOICES)
    parser.add_argument("--acceptance-state", choices=AI_ACCEPTANCE_STATE_CHOICES)
    parser.add_argument("--override-reason")
    parser.add_argument("--ai-audit-ref")
    parser.add_argument("--accepted-by")
    parser.add_argument("--accepted-at")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create an intake classification entry so a new repo, product, or component is explicitly marked out-of-scope, proposed, or admitted."
    )
    parser.add_argument(
        "--repo-root",
        default=Path(__file__).resolve().parents[1],
        type=Path,
        help="workspace-governance repository root",
    )
    subparsers = parser.add_subparsers(dest="kind", required=True)

    repo_parser = subparsers.add_parser("repo", help="scaffold a repo intake entry")
    repo_parser.add_argument("--name", required=True)
    repo_parser.add_argument("--status", choices=INTAKE_STATUS_CHOICES, default="proposed")
    repo_parser.add_argument("--decision-source", choices=("operator", "ai-suggested"), default=DEFAULT_DECISION_SOURCE)
    repo_parser.add_argument("--repo-class")
    repo_parser.add_argument("--requires-security-bindings", action="store_true")
    repo_parser.add_argument("--security-owner", default=DEFAULT_SECURITY_OWNER)
    repo_parser.add_argument("--notes", required=True)
    add_ai_arguments(repo_parser)
    repo_parser.set_defaults(handler=add_repo_entry)

    product_parser = subparsers.add_parser("product", help="scaffold a product intake entry")
    product_parser.add_argument("--name", required=True)
    product_parser.add_argument("--status", choices=INTAKE_STATUS_CHOICES, default="proposed")
    product_parser.add_argument("--decision-source", choices=("operator", "ai-suggested"), default=DEFAULT_DECISION_SOURCE)
    product_parser.add_argument("--platform-owner", default="platform-engineering")
    product_parser.add_argument("--security-owner", default=DEFAULT_SECURITY_OWNER)
    product_parser.add_argument("--runtime-owner")
    product_parser.add_argument("--source-owner", action="append", default=[])
    product_parser.add_argument("--intended-endpoint")
    product_parser.add_argument("--notes", required=True)
    add_ai_arguments(product_parser)
    product_parser.set_defaults(handler=add_product_entry)

    component_parser = subparsers.add_parser("component", help="scaffold a component intake entry")
    component_parser.add_argument("--name", required=True)
    component_parser.add_argument("--status", choices=INTAKE_STATUS_CHOICES, default="proposed")
    component_parser.add_argument("--decision-source", choices=("operator", "ai-suggested"), default=DEFAULT_DECISION_SOURCE)
    component_parser.add_argument("--component-class")
    component_parser.add_argument("--owner-repo")
    component_parser.add_argument("--security-owner", default=DEFAULT_SECURITY_OWNER)
    component_parser.add_argument("--product")
    component_parser.add_argument("--notes", required=True)
    add_ai_arguments(component_parser)
    component_parser.set_defaults(handler=add_component_entry)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    args.governed_intake_assist = load_governed_intake_assist(repo_root)
    register = load_intake(repo_root)
    entry_id = args.handler(register, args)
    write_intake(repo_root, register)

    print(f"scaffolded intake entry: {entry_id} status={args.status} source={args.decision_source}")
    print(
        "next steps: validate the intake model, then either keep the entrant explicitly out-of-scope or promote it into the governed contracts when the owner surface is ready"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
