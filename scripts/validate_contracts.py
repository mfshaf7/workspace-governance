#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
from datetime import date, datetime
import hashlib
import json
from pathlib import Path
import re
import shlex
import sys

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError
import yaml

from contracts_lib import (
    REPO_RULES_SCHEMA,
    SCHEMA_FILES,
    active_repo_names,
    load_contracts,
    load_json,
)


CONTRACT_FORMAT_CHECKER = FormatChecker()


@CONTRACT_FORMAT_CHECKER.checks("date-time")
def is_rfc3339_timestamp(value: object) -> bool:
    if not isinstance(value, str) or not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}[Tt]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:[Zz]|[+-]\d{2}:\d{2})",
        value,
    ):
        return False
    normalized = value
    if value.endswith(("Z", "z")):
        normalized = value[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


BRANCH_LIFECYCLE_TARGET_RE = re.compile(
    r"^repo:(?P<repo>[^:]+):(?P<kind>remote-branch|local-branch|worktree):(?P<value>.+)$"
)
BRANCH_LIFECYCLE_WAIVER_KINDS = {
    "branch-lifecycle-remote-branch": "remote-branch",
    "branch-lifecycle-local-branch": "local-branch",
    "branch-lifecycle-worktree": "worktree",
}
WGCF_PLANNER_SCOPE_PREFIXES = (
    "authority:",
    "component:",
    "projection:",
    "profile:",
    "repo:",
    "validator:",
    "art:",
    "release:",
    "changed-file:",
)
WGCF_COMMAND_TEMPLATE_FIELDS = {
    "art_delivery_id",
    "target_id",
    "target_scope",
    "target_type",
}
CONTROLLED_PROOF_SCHEMA_REF = (
    "contracts/schemas/controlled-runtime-proof-authorization.schema.json"
)
CONTROLLED_PROOF_RESULT_SCHEMA_REF = (
    "contracts/schemas/controlled-runtime-proof-result.schema.json"
)
DELIVERY_ART_ARTIFACT_CASES = {
    "architecture_packet": (
        "contracts/schemas/delivery-art-architecture-packet.schema.json",
        ("contracts/fixtures/delivery-art-workflow/architecture-packet.valid.json",),
    ),
    "work_start_record": (
        "contracts/schemas/delivery-art-work-start-record.schema.json",
        ("contracts/fixtures/delivery-art-workflow/work-start-record.valid.json",),
    ),
    "review_packet": (
        "contracts/schemas/delivery-art-review-packet.schema.json",
        (
            "contracts/fixtures/delivery-art-workflow/review-packet-merge-ready.valid.json",
            "contracts/fixtures/delivery-art-workflow/review-packet-finalized.valid.json",
        ),
    ),
    "custody_receipt": (
        "contracts/schemas/delivery-art-custody-receipt.schema.json",
        (
            "contracts/fixtures/delivery-art-workflow/architecture-custody-receipt.valid.json",
            "contracts/fixtures/delivery-art-workflow/work-start-custody-receipt.valid.json",
            "contracts/fixtures/delivery-art-workflow/merge-ready-custody-receipt.valid.json",
            "contracts/fixtures/delivery-art-workflow/finalized-custody-receipt.valid.json",
        ),
    ),
    "readiness_receipt": (
        "contracts/schemas/delivery-art-readiness-receipt.schema.json",
        ("contracts/fixtures/delivery-art-workflow/readiness-receipt.valid.json",),
    ),
}

DELIVERY_ART_PROOF_CLAIM_ROOTS = (
    "readiness_model.rules",
    "work_start_gate",
    "evidence_integrity",
    "initiative_architecture_preflight",
)
CONTROLLED_PROOF_REQUIRED_SECTIONS = {
    "schema_version",
    "authorization_id",
    "authority_type",
    "drill_type",
    "target",
    "scope",
    "commissioning_session",
    "permit_issuer",
    "executor",
    "approvals",
    "window",
    "evidence",
    "baseline_and_restore",
    "exception_handling",
    "stop_conditions",
}
CONTROLLED_PROOF_REQUIRED_SESSION_FIELDS = {
    "commissioning_session_id",
    "consumption_mode",
    "consume_before_first_mutation",
    "duplicate_consumption_denied",
    "scenario_executions",
}
CONTROLLED_PROOF_REQUIRED_SCOPE_FIELDS = {
    "allowed_definitions",
    "source_revisions",
    "runtime_artifacts",
    "runtime_images",
    "target_namespaces",
    "runtime_identities",
    "task_queues",
    "permitted_actions",
}
CONTROLLED_PROOF_REQUIRED_EXECUTOR_FIELDS = {
    "owner_repo",
    "implementation_ref",
    "source_revision",
    "review_packet_ref",
}
CONTROLLED_PROOF_REQUIRED_APPROVAL_FIELDS = {
    "issued_by",
    "canonicalization",
    "canonical_claims_projection",
    "canonical_claims_digest",
    "operator_approval_ref",
    "operator_approval_digest",
    "security_authorization_ref",
    "security_authorization_digest",
}
CONTROLLED_PROOF_REQUIRED_WINDOW_FIELDS = {"issued_at", "expires_at"}
CONTROLLED_PROOF_REQUIRED_EVIDENCE_FIELDS = {
    "owner_repo",
    "verification_pack_ref",
}
CONTROLLED_PROOF_REQUIRED_RESTORE_FIELDS = {
    "baseline_snapshot_ref",
    "baseline_snapshot_digest",
    "restore_mode",
    "restore_scope",
    "terminal_cleanup_authority",
}
CONTROLLED_PROOF_RESULT_REQUIRED_SECTIONS = {
    "schema_version",
    "result_id",
    "authorization",
    "commissioning_session",
    "outcome",
    "scenario_outcomes",
    "owner_receipts",
    "baseline_restore",
    "completed_at",
}
CONTROLLED_PROOF_RESULT_REQUIRED_AUTHORIZATION_FIELDS = {
    "authorization_id",
    "authorization_digest",
    "canonical_claims_digest",
}
CONTROLLED_PROOF_RESULT_REQUIRED_SESSION_FIELDS = {
    "commissioning_session_id",
    "scenario_execution_count",
    "authorization_consumed_at",
    "started_at",
}
CONTROLLED_PROOF_RESULT_REQUIRED_SCENARIO_OUTCOME_FIELDS = {
    "scenario_id",
    "scenario_execution_id",
    "status",
    "evidence_refs",
    "started_at",
    "completed_at",
}
CONTROLLED_PROOF_RESULT_REQUIRED_RECEIPT_FIELDS = {
    "owner_repo",
    "authorization_id",
    "authorization_digest",
    "commissioning_session_id",
    "scenario_id",
    "scenario_execution_id",
    "owner_execution",
    "owner_result",
    "evidence_refs",
    "receipt_ref",
    "receipt_digest",
    "recorded_at",
}
CONTROLLED_PROOF_RESULT_REQUIRED_OWNER_EXECUTION_FIELDS = {
    "execution_type",
    "execution_id",
}
CONTROLLED_PROOF_RESULT_REQUIRED_EVIDENCE_FIELDS = {
    "artifact_ref",
    "artifact_digest",
}
CONTROLLED_PROOF_RESULT_REQUIRED_RESTORE_FIELDS = {
    "baseline_snapshot_ref",
    "baseline_snapshot_digest",
    "status",
    "evidence_ref",
    "evidence_digest",
}
CONTROLLED_PROOF_REQUIRED_TERMINAL_CLEANUP_FIELDS = {
    "mode",
    "applies_to",
    "trigger_scope",
    "scope_binding",
    "new_proof_actions_denied",
    "scope_expansion_denied",
    "runtime_retention_denied",
    "permitted_actions",
    "termination_conditions",
}
CONTROLLED_PROOF_TERMINAL_CLEANUP_ACTIONS = [
    "remove-scoped-runtime",
    "restore-exact-baseline",
    "record-restore-evidence",
    "record-governed-exception",
]
CONTROLLED_PROOF_TERMINAL_CLEANUP_TERMINATION_CONDITIONS = [
    "exact-baseline-restored",
    "governed-exception-recorded",
]
CONTROLLED_PROOF_REQUIRED_EXCEPTION_FIELDS = {
    "allowed_decisions",
    "record_ref_required",
}
CONTROLLED_PROOF_REQUIRED_SCENARIO_ORDER = [
    "nominal-completion",
    "workflow-worker-restart",
    "temporal-runtime-restart",
    "deterministic-replay",
    "duplicate-suppression",
    "cancellation",
    "unavailable-dependency",
    "identity-denial",
    "payload-boundary",
    "backup-restore",
    "exact-baseline-restore",
]
CONTROLLED_PROOF_REQUIRED_SCENARIOS = set(CONTROLLED_PROOF_REQUIRED_SCENARIO_ORDER)
CONTROLLED_PROOF_REQUIRED_RECEIPT_OWNER_ORDER = [
    "platform-engineering",
    "operator-orchestration-service",
    "workspace-governance-control-fabric",
]
CONTROLLED_PROOF_REQUIRED_RECEIPT_OWNERS = set(
    CONTROLLED_PROOF_REQUIRED_RECEIPT_OWNER_ORDER
)
CONTROLLED_PROOF_PERMITTED_ACTIONS = {
    "install-scoped-runtime",
    "start-validation-readiness-run",
    "restart-oos-workflow-worker",
    "restart-wgcf-activity-worker",
    "restart-temporal-runtime",
    "cancel-validation-readiness-run",
    "simulate-unavailable-dependency",
    "verify-identity-denial",
    "capture-backup",
    "restore-exact-baseline",
    "remove-scoped-runtime",
}
CONTROLLED_PROOF_REQUIRED_STOP_CONDITIONS = {
    "authorization-expired",
    "source-or-artifact-digest-mismatch",
    "target-scope-mismatch",
    "identity-or-queue-denial-failure",
    "baseline-snapshot-unavailable",
    "unexpected-side-effect",
    "evidence-custody-failure",
    "restore-failure",
}


def _is_wgcf_planner_scope(value: str) -> bool:
    scope = str(value or "").strip()
    if scope == "workspace":
        return True
    return any(
        scope.startswith(prefix) and scope.removeprefix(prefix).strip()
        for prefix in WGCF_PLANNER_SCOPE_PREFIXES
    )


def _has_shell_control_token(command: str) -> bool:
    if "$(" in command:
        return True
    try:
        parts = shlex.split(command)
    except ValueError:
        return True
    return any(part in {"&&", "||", "|", ";"} for part in parts)


def _command_template_fields(command: str) -> set[str]:
    if command.count("{") != command.count("}"):
        return {"<unbalanced-braces>"}
    fields = set(re.findall(r"{([^{}]+)}", command))
    stripped = re.sub(r"{[^{}]+}", "", command)
    if "{" in stripped or "}" in stripped:
        fields.add("<malformed-braces>")
    return fields


def validate_schema(errors: list[str], instance_path: Path, schema_path: Path) -> None:
    instance = yaml.safe_load(instance_path.read_text()) or {}
    schema = load_json(schema_path)
    validator = Draft202012Validator(schema, format_checker=CONTRACT_FORMAT_CHECKER)
    for error in validator.iter_errors(instance):
        path = ".".join(str(part) for part in error.absolute_path) or "<root>"
        errors.append(f"{instance_path}: {path}: {error.message}")


DELIVERY_ART_EVIDENCE_SECTIONS = (
    "changed_surfaces",
    "tests",
    "validations",
    "runtime_and_live",
    "security_and_trust",
)
DELIVERY_ART_SOURCE_BACKED_DECISIONS = {
    "feature_single_landing_unit",
    "child_isolated_landing_unit",
}
DELIVERY_ART_WORK_START_INVALIDATION_INPUTS = {
    "art-descendant-or-dependency-change",
    "owner-or-rollback-boundary-change",
    "base-ref-or-commit-change",
    "architecture-decision-or-digest-change",
    "validation-or-security-obligation-change",
}
DELIVERY_ART_PROTOCOL_CONFORMANCE_DIMENSIONS = {
    "command-and-acknowledgement-semantics",
    "deterministic-identities-and-idempotency",
    "state-mutation-ordering",
    "retry-cancel-replay-and-recovery-semantics",
    "bounded-failure-mapping",
    "authorization-integrity-and-replay-resistance",
    "session-scenario-and-execution-binding",
    "result-and-owner-receipt-completeness",
    "immutable-baseline-and-restore-evidence",
    "lifecycle-state-matrix",
    "cross-artifact-timeline-ordering",
    "shared-validator-compatibility",
}
DELIVERY_ART_READINESS_RANK = {
    "merge-ready": 1,
    "operating-ready": 2,
}


def _artifact_object(value: object) -> dict:
    return value if isinstance(value, dict) else {}


def _artifact_object_list(value: object) -> list[dict]:
    if not isinstance(value, list):
        return []
    return [entry for entry in value if isinstance(entry, dict)]


def _artifact_string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [entry for entry in value if isinstance(entry, str)]


def _delivery_art_openproject_id(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    match = re.fullmatch(r"openproject://work_packages/([1-9][0-9]*)", value)
    return match.group(1) if match else None


def _delivery_art_entity_number(value: object, prefix: str) -> str | None:
    if not isinstance(value, str):
        return None
    match = re.fullmatch(rf"{re.escape(prefix)}-([1-9][0-9]*)", value)
    return match.group(1) if match else None


def _delivery_art_ref_digest_errors(
    ref: object,
    digest: object,
    label: str,
) -> list[str]:
    if not isinstance(ref, str) or not isinstance(digest, str):
        return []
    digest_hex = digest.removeprefix("sha256:")
    if digest_hex not in ref:
        return [f"{label} must include its declared content digest"]
    return []


def _delivery_art_identifier_scoped_to(
    value: object,
    artifact_prefix: str,
    delivery_id: object,
) -> bool:
    if not isinstance(value, str) or not isinstance(delivery_id, str):
        return False
    return bool(
        re.match(
            rf"^{re.escape(artifact_prefix)}:{re.escape(delivery_id)}(?:$|[-:.])",
            value,
        )
    )


def _delivery_art_edge_precedence(edge: dict) -> tuple[str, str] | None:
    """Return the work-item order implied by one dependency relation."""
    source = edge.get("from")
    target = edge.get("to")
    relation = edge.get("relation")
    if not isinstance(source, str) or not isinstance(target, str):
        return None
    if relation == "depends_on":
        return target, source
    if relation in {"blocks", "must_merge_before"}:
        return source, target
    return None


def _artifact_timestamp(value: object) -> datetime | None:
    if not is_rfc3339_timestamp(value):
        return None
    normalized = value[:-1] + "+00:00" if value.endswith(("Z", "z")) else value
    return datetime.fromisoformat(normalized)


def _require_artifact_time_order(
    errors: list[str],
    earlier_name: str,
    earlier_value: object,
    later_name: str,
    later_value: object,
) -> None:
    earlier = _artifact_timestamp(earlier_value)
    later = _artifact_timestamp(later_value)
    if earlier is not None and later is not None and earlier > later:
        errors.append(f"{earlier_name} must not be later than {later_name}")


def _require_strict_artifact_time_order(
    errors: list[str],
    earlier_name: str,
    earlier_value: object,
    later_name: str,
    later_value: object,
) -> None:
    earlier = _artifact_timestamp(earlier_value)
    later = _artifact_timestamp(later_value)
    if earlier is not None and later is not None and earlier >= later:
        errors.append(f"{earlier_name} must be earlier than {later_name}")


def _delivery_art_canonical_bytes(value: object) -> bytes:
    """Serialize the integer-only RFC 8785 subset accepted by ART artifacts."""
    if value is None:
        return b"null"
    if value is True:
        return b"true"
    if value is False:
        return b"false"
    if isinstance(value, int):
        return str(value).encode("ascii")
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode(
            "utf-8"
        )
    if isinstance(value, list):
        return b"[" + b",".join(
            _delivery_art_canonical_bytes(entry) for entry in value
        ) + b"]"
    if isinstance(value, dict):
        entries = []
        for key in sorted(value, key=lambda item: item.encode("utf-16be")):
            entries.append(
                _delivery_art_canonical_bytes(key)
                + b":"
                + _delivery_art_canonical_bytes(value[key])
            )
        return b"{" + b",".join(entries) + b"}"
    raise TypeError(f"unsupported canonical JSON value {type(value).__name__}")


def _delivery_art_projection_digest(projection: object) -> str:
    return "sha256:" + hashlib.sha256(
        _delivery_art_canonical_bytes(projection)
    ).hexdigest()


def _delivery_art_projection_digest_if_canonical(
    projection: object,
) -> str | None:
    if _artifact_canonicalization_errors(projection):
        return None
    return _delivery_art_projection_digest(projection)


def _delivery_art_content_digest_projection(payload: dict) -> dict:
    projection = copy.deepcopy(payload)
    custody = _artifact_object(projection.pop("custody", None))
    supersedes = _artifact_object(custody.get("supersedes"))
    if supersedes:
        projection["custody"] = {"supersedes": supersedes}
    _artifact_object(projection.get("integrity")).pop("content_digest", None)
    return projection


def _architecture_scope_projection(payload: dict) -> dict:
    decision = _artifact_object(payload.get("decision"))
    return {
        "schema_version": payload.get("schema_version"),
        "artifact_type": payload.get("artifact_type"),
        "delivery_id": payload.get("delivery_id"),
        "covered_work_item_ids": payload.get("covered_work_item_ids"),
        "source_snapshot": payload.get("source_snapshot"),
        "architecture": payload.get("architecture"),
        "conformance_plan": payload.get("conformance_plan"),
        "decision_status": decision.get("status"),
    }


def _work_start_scope_projection(payload: dict) -> dict:
    return {
        "schema_version": payload.get("schema_version"),
        "artifact_type": payload.get("artifact_type"),
        "delivery_id": payload.get("delivery_id"),
        "covered_work_item_ids": payload.get("covered_work_item_ids"),
        "landing_unit": payload.get("landing_unit"),
        "architecture": payload.get("architecture"),
        "source_snapshot": payload.get("source_snapshot"),
        "invalidation_inputs": payload.get("invalidation_inputs"),
    }


def _review_packet_readiness_subject_projection(payload: dict) -> dict:
    projection = copy.deepcopy(payload)
    projection.pop("custody", None)
    projection.pop("integrity", None)
    projection.pop("finalized_at", None)
    readiness = _artifact_object(projection.get("readiness"))
    readiness.pop("evaluated_at", None)
    readiness.pop("receipt_refs", None)
    readiness.pop("subject_digest", None)
    return projection


def delivery_art_review_packet_readiness_subject_digest(payload: dict) -> str:
    return _delivery_art_projection_digest(
        _review_packet_readiness_subject_projection(payload)
    )


def _review_packet_predecessor_continuity_errors(
    finalized: dict,
    merge_ready: dict,
) -> list[str]:
    errors: list[str] = []
    for field in (
        "packet_id",
        "delivery_id",
        "covered_work_item_ids",
        "created_at",
        "operator",
        "work_start",
    ):
        if finalized.get(field) != merge_ready.get(field):
            errors.append(
                f"finalized Review Packet must preserve merge-ready {field}"
            )

    final_landing = _artifact_object(finalized.get("landing_unit"))
    prior_landing = _artifact_object(merge_ready.get("landing_unit"))
    for field in ("decision", "rollback_boundary"):
        if final_landing.get(field) != prior_landing.get(field):
            errors.append(
                f"finalized Review Packet must preserve merge-ready landing_unit.{field}"
            )
    expected_final_kind = {
        "open_pr": "merged_pr",
        "approved_direct_land": "approved_direct_land",
    }.get(prior_landing.get("evidence_kind"))
    if expected_final_kind is None or final_landing.get("evidence_kind") != expected_final_kind:
        errors.append(
            "finalized source Review Packet evidence kind must advance from its merge-ready predecessor"
        )

    prior_repos = {
        repo.get("repo_name"): repo
        for repo in _artifact_object_list(prior_landing.get("repos"))
        if isinstance(repo.get("repo_name"), str)
    }
    final_repos = {
        repo.get("repo_name"): repo
        for repo in _artifact_object_list(final_landing.get("repos"))
        if isinstance(repo.get("repo_name"), str)
    }
    if set(prior_repos) != set(final_repos):
        errors.append(
            "finalized Review Packet repos must match its merge-ready predecessor"
        )
    stable_repo_fields = (
        "branch",
        "base_ref",
        "base_commit",
        "head_commit",
        "pr_url",
        "changed_files",
        "change_record_refs",
    )
    for repo_name, prior_repo in prior_repos.items():
        final_repo = final_repos.get(repo_name)
        if final_repo is None:
            continue
        for field in stable_repo_fields:
            if final_repo.get(field) != prior_repo.get(field):
                errors.append(
                    f"finalized Review Packet must preserve merge-ready {repo_name}.{field}"
                )

    prior_evidence = _artifact_object(merge_ready.get("evidence"))
    final_evidence = _artifact_object(finalized.get("evidence"))
    for section in (
        "changed_surfaces",
        "tests",
        "validations",
        "runtime_and_live",
        "security_and_trust",
    ):
        final_entries = _artifact_object_list(final_evidence.get(section))
        for prior_entry in _artifact_object_list(prior_evidence.get(section)):
            if prior_entry not in final_entries:
                errors.append(
                    f"finalized Review Packet must preserve merge-ready evidence {prior_entry.get('id')}"
                )

    final_mappings = {
        mapping.get("work_item_id"): mapping
        for mapping in _artifact_object_list(final_evidence.get("acceptance_mapping"))
        if isinstance(mapping.get("work_item_id"), str)
    }
    for prior_mapping in _artifact_object_list(
        prior_evidence.get("acceptance_mapping")
    ):
        work_item_id = prior_mapping.get("work_item_id")
        final_mapping = final_mappings.get(work_item_id)
        if final_mapping is None:
            errors.append(
                f"finalized Review Packet must preserve merge-ready acceptance mapping for {work_item_id}"
            )
            continue
        if final_mapping.get("acceptance_ref") != prior_mapping.get(
            "acceptance_ref"
        ) or final_mapping.get("summary") != prior_mapping.get("summary") or not set(
            _artifact_string_list(prior_mapping.get("evidence_ids"))
        ).issubset(_artifact_string_list(final_mapping.get("evidence_ids"))):
            errors.append(
                f"finalized Review Packet must preserve merge-ready acceptance evidence for {work_item_id}"
            )

    if merge_ready.get("rollback") is not None and finalized.get(
        "rollback"
    ) != merge_ready.get("rollback"):
        errors.append("finalized Review Packet must preserve merge-ready rollback evidence")

    final_exceptions = _artifact_object_list(finalized.get("exceptions"))
    for prior_exception in _artifact_object_list(merge_ready.get("exceptions")):
        if prior_exception not in final_exceptions:
            errors.append(
                f"finalized Review Packet must preserve merge-ready exception {prior_exception.get('id')}"
            )
    return errors


def _artifact_canonicalization_errors(
    value: object,
    path: str = "<root>",
) -> list[str]:
    """Restrict artifacts to the RFC 8785 domain used by this contract."""
    errors: list[str] = []
    if isinstance(value, str):
        if any(0xD800 <= ord(character) <= 0xDFFF for character in value):
            errors.append(f"{path} contains a lone UTF-16 surrogate")
    elif isinstance(value, float):
        errors.append(
            f"{path} uses a floating-point value; Delivery ART artifacts require integral numbers"
        )
    elif isinstance(value, int) and not isinstance(value, bool):
        if abs(value) > 9_007_199_254_740_991:
            errors.append(f"{path} exceeds the RFC 8785 safe integer range")
    elif isinstance(value, list):
        for index, entry in enumerate(value):
            errors.extend(
                _artifact_canonicalization_errors(entry, f"{path}[{index}]")
            )
    elif isinstance(value, dict):
        for key, entry in value.items():
            if not isinstance(key, str):
                errors.append(f"{path} contains a non-string object key")
                continue
            errors.extend(_artifact_canonicalization_errors(key, f"{path} key"))
            errors.extend(
                _artifact_canonicalization_errors(entry, f"{path}[{key!r}]")
            )
    elif value is not None and not isinstance(value, bool):
        errors.append(f"{path} contains an unsupported canonical JSON value")
    return errors


def strict_delivery_art_object(pairs: list[tuple[str, object]]) -> dict:
    artifact_object = {}
    for key, value in pairs:
        if key in artifact_object:
            raise ValueError(f"duplicate JSON object key {key!r}")
        artifact_object[key] = value
    return artifact_object


def delivery_art_artifact_semantic_errors(payload: dict) -> list[str]:
    """Validate cross-field invariants that JSON Schema cannot express."""
    errors: list[str] = []
    artifact_type = payload.get("artifact_type")
    delivery_id = payload.get("delivery_id")
    delivery_number = _delivery_art_entity_number(delivery_id, "delivery")
    custody = _artifact_object(payload.get("custody"))
    if (
        custody.get("state") == "durable"
        and custody.get("backend") == "wgcf-artifact-registry"
    ):
        if not re.fullmatch(
            r"wgcf://artifacts/delivery-art/sha256/[0-9a-f]{64}",
            str(custody.get("uri", "")),
        ):
            errors.append(
                "durable custody URI must be an opaque Delivery ART reference from the WGCF artifact registry"
            )
        custody_receipt = _artifact_object(custody.get("receipt_ref"))
        errors.extend(
            _delivery_art_ref_digest_errors(
                custody_receipt.get("uri"),
                custody_receipt.get("digest"),
                "custody.receipt_ref.uri",
            )
        )
    supersedes = _artifact_object(custody.get("supersedes"))
    errors.extend(
        _delivery_art_ref_digest_errors(
            supersedes.get("uri"),
            supersedes.get("digest"),
            "custody.supersedes.uri",
        )
    )

    if artifact_type == "delivery_art_architecture_packet":
        artifact_id = payload.get("artifact_id")
        if isinstance(delivery_id, str) and not _delivery_art_identifier_scoped_to(
            artifact_id, "architecture-packet", delivery_id
        ):
            errors.append("artifact_id must be scoped to delivery_id")
        expected_scope_fingerprint = _delivery_art_projection_digest_if_canonical(
            _architecture_scope_projection(payload)
        )
        if (
            expected_scope_fingerprint is not None
            and payload.get("scope_fingerprint") != expected_scope_fingerprint
        ):
            errors.append(
                "scope_fingerprint must equal the deterministic architecture scope projection "
                + expected_scope_fingerprint
            )
        covered_work_items = set(
            _artifact_string_list(payload.get("covered_work_item_ids"))
        )
        architecture = _artifact_object(payload.get("architecture"))
        owner_map = _artifact_object_list(architecture.get("descendant_owner_map"))
        dag = _artifact_object(architecture.get("dependency_merge_dag"))
        owner_map_ids = [
            entry.get("work_item_id")
            for entry in owner_map
            if isinstance(entry.get("work_item_id"), str)
        ]
        owner_by_work_item = {
            entry.get("work_item_id"): entry.get("owner_repo")
            for entry in owner_map
            if isinstance(entry.get("work_item_id"), str)
            and isinstance(entry.get("owner_repo"), str)
        }
        dag_nodes = set(_artifact_string_list(dag.get("nodes")))

        if len(owner_map_ids) != len(set(owner_map_ids)):
            errors.append(
                "architecture.descendant_owner_map must contain one entry per work item"
            )
        if set(owner_map_ids) != covered_work_items:
            errors.append(
                "architecture.descendant_owner_map must exactly cover covered_work_item_ids"
            )
        if dag_nodes != covered_work_items:
            errors.append(
                "architecture.dependency_merge_dag.nodes must exactly cover covered_work_item_ids"
            )

        parent_by_work_item = {}
        root_work_items = []
        for entry in owner_map:
            work_item_id = entry.get("work_item_id")
            parent = entry.get("parent_work_item_id")
            if isinstance(work_item_id, str):
                parent_by_work_item[work_item_id] = parent
                if parent is None:
                    root_work_items.append(work_item_id)
            if isinstance(parent, str) and parent not in dag_nodes:
                errors.append(
                    f"architecture descendant {work_item_id} references unknown parent {parent}"
                )
        if owner_map_ids and not root_work_items:
            errors.append(
                "architecture.descendant_owner_map must contain at least one root"
            )

        parent_cycle_nodes = set()
        parent_walk_complete = set()
        for start in parent_by_work_item:
            chain = []
            chain_positions = {}
            current = start
            while isinstance(current, str) and current in parent_by_work_item:
                if current in chain_positions:
                    parent_cycle_nodes.update(chain[chain_positions[current] :])
                    break
                if current in parent_walk_complete:
                    break
                chain_positions[current] = len(chain)
                chain.append(current)
                current = parent_by_work_item[current]
            parent_walk_complete.update(chain)
        if parent_cycle_nodes:
            errors.append(
                "architecture.descendant_owner_map parent links must be acyclic; cycle includes: "
                + ", ".join(sorted(parent_cycle_nodes))
            )

        adjacency = {node: [] for node in dag_nodes}
        indegree = {node: 0 for node in dag_nodes}
        precedence_edges = []
        for edge in _artifact_object_list(dag.get("edges")):
            source = edge.get("from")
            target = edge.get("to")
            if not isinstance(source, str) or not isinstance(target, str):
                continue
            unknown_endpoints = {source, target} - dag_nodes
            if unknown_endpoints:
                errors.append(
                    "architecture dependency edge references unknown nodes: "
                    + ", ".join(sorted(str(node) for node in unknown_endpoints))
                )
                continue
            precedence = _delivery_art_edge_precedence(edge)
            if precedence is None:
                continue
            before, after = precedence
            precedence_edges.append(precedence)
            adjacency[before].append(after)
            indegree[after] += 1

        ready = [node for node, degree in indegree.items() if degree == 0]
        visited_count = 0
        while ready:
            node = ready.pop()
            visited_count += 1
            for target in adjacency[node]:
                indegree[target] -= 1
                if indegree[target] == 0:
                    ready.append(target)
        if visited_count != len(dag_nodes):
            errors.append("architecture.dependency_merge_dag must be acyclic")

        owner_repos = {
            entry.get("owner_repo")
            for entry in owner_map
            if isinstance(entry.get("owner_repo"), str)
        }
        merge_order = _artifact_string_list(dag.get("merge_order"))
        if set(merge_order) != owner_repos:
            errors.append(
                "architecture.dependency_merge_dag.merge_order must exactly cover descendant owner repos"
            )
        else:
            merge_positions = {
                repo: position for position, repo in enumerate(merge_order)
            }
            for before, after in precedence_edges:
                before_repo = owner_by_work_item.get(before)
                after_repo = owner_by_work_item.get(after)
                if (
                    before_repo is not None
                    and after_repo is not None
                    and before_repo != after_repo
                    and merge_positions[before_repo] >= merge_positions[after_repo]
                ):
                    errors.append(
                        "architecture.dependency_merge_dag.merge_order violates "
                        f"{before} before {after}: {before_repo} must precede {after_repo}"
                    )

        source_snapshot = _artifact_object(payload.get("source_snapshot"))
        if (
            delivery_number is not None
            and _delivery_art_openproject_id(source_snapshot.get("art_ref"))
            != delivery_number
        ):
            errors.append(
                "architecture source_snapshot.art_ref must reference its declared Delivery initiative"
            )
        repo_revisions = _artifact_object_list(source_snapshot.get("repo_revisions"))
        revision_repos = [
            entry.get("repo")
            for entry in repo_revisions
            if isinstance(entry.get("repo"), str)
        ]
        if len(revision_repos) != len(set(revision_repos)):
            errors.append(
                "source_snapshot.repo_revisions must contain one entry per owner repo"
            )
        if set(revision_repos) != owner_repos:
            errors.append(
                "source_snapshot.repo_revisions must exactly cover descendant owner repos"
            )

        lifecycle = _artifact_object(architecture.get("lifecycle_state_model"))
        lifecycle_states = set(_artifact_string_list(lifecycle.get("states")))
        for transition in _artifact_object_list(lifecycle.get("transitions")):
            endpoints = {
                endpoint
                for endpoint in (transition.get("from"), transition.get("to"))
                if isinstance(endpoint, str)
            }
            unknown_states = endpoints - lifecycle_states
            if unknown_states:
                errors.append(
                    "architecture lifecycle transition references undeclared states: "
                    + ", ".join(sorted(unknown_states))
                )

        conformance_plan = _artifact_object(payload.get("conformance_plan"))
        conformance_dimensions = set(
            _artifact_string_list(conformance_plan.get("dimensions"))
        )
        applicability_rows = _artifact_object_list(
            conformance_plan.get("work_item_dimension_applicability")
        )
        applicability_items = [
            row.get("work_item_id")
            for row in applicability_rows
            if isinstance(row.get("work_item_id"), str)
        ]
        applicability_by_work_item = {
            row.get("work_item_id"): set(
                _artifact_string_list(row.get("dimension_ids"))
            )
            for row in applicability_rows
            if isinstance(row.get("work_item_id"), str)
        }
        if len(applicability_items) != len(set(applicability_items)):
            errors.append(
                "conformance_plan.work_item_dimension_applicability must contain one row per work item"
            )
        if set(applicability_items) != covered_work_items:
            errors.append(
                "conformance_plan.work_item_dimension_applicability must exactly cover covered_work_item_ids"
            )
        applicable_dimensions = set().union(
            *applicability_by_work_item.values()
        ) if applicability_by_work_item else set()
        if applicable_dimensions != conformance_dimensions:
            errors.append(
                "work-item dimension applicability must exactly cover declared conformance dimensions"
            )
        for work_item_id, dimensions in applicability_by_work_item.items():
            unknown_dimensions = dimensions - conformance_dimensions
            if unknown_dimensions:
                errors.append(
                    f"work-item dimension applicability for {work_item_id} references undeclared dimensions: "
                    + ", ".join(sorted(unknown_dimensions))
                )
        protocol_applicability = _artifact_object(
            conformance_plan.get("protocol_applicability")
        )
        if protocol_applicability.get("applies") is True:
            missing_dimensions = (
                DELIVERY_ART_PROTOCOL_CONFORMANCE_DIMENSIONS
                - conformance_dimensions
            )
            if missing_dimensions:
                errors.append(
                    "protocol conformance plan is missing required dimensions: "
                    + ", ".join(sorted(missing_dimensions))
                )
        conformance_cases = _artifact_object_list(conformance_plan.get("cases"))
        conformance_case_ids = [
            case.get("id")
            for case in conformance_cases
            if isinstance(case.get("id"), str)
        ]
        if len(conformance_case_ids) != len(set(conformance_case_ids)):
            errors.append("conformance_plan.cases must contain unique case ids")
        conformance_items = set()
        executable_dimensions = set()
        polarities_by_work_item = {
            work_item_id: set() for work_item_id in covered_work_items
        }
        merge_ready_polarities_by_dimension = {
            dimension: set() for dimension in conformance_dimensions
        }
        merge_ready_polarities_by_work_item = {
            work_item_id: set() for work_item_id in covered_work_items
        }
        merge_ready_polarities_by_pair = {
            (work_item_id, dimension): set()
            for work_item_id, dimensions in applicability_by_work_item.items()
            for dimension in dimensions
        }
        for case in conformance_cases:
            case_id = case.get("id")
            applicability = set(
                _artifact_string_list(case.get("applies_to_work_item_ids"))
            )
            case_dimensions = set(
                _artifact_string_list(case.get("dimension_ids"))
            )
            conformance_items.update(applicability)
            executable_dimensions.update(case_dimensions)
            for work_item_id in applicability.intersection(covered_work_items):
                polarity = case.get("polarity")
                if isinstance(polarity, str):
                    polarities_by_work_item[work_item_id].add(polarity)
            if case.get("target_readiness") == "merge-ready":
                polarity = case.get("polarity")
                for work_item_id in applicability.intersection(covered_work_items):
                    if isinstance(polarity, str):
                        merge_ready_polarities_by_work_item[work_item_id].add(
                            polarity
                        )
                for dimension in case_dimensions.intersection(
                    conformance_dimensions
                ):
                    if isinstance(polarity, str):
                        merge_ready_polarities_by_dimension[dimension].add(
                            polarity
                        )
                for work_item_id in applicability.intersection(covered_work_items):
                    for dimension in case_dimensions.intersection(
                        applicability_by_work_item.get(work_item_id, set())
                    ):
                        if isinstance(polarity, str):
                            merge_ready_polarities_by_pair[
                                (work_item_id, dimension)
                            ].add(polarity)
            unknown_items = applicability - covered_work_items
            if unknown_items:
                errors.append(
                    f"conformance case {case_id} applies to undeclared work items: "
                    + ", ".join(sorted(unknown_items))
                )
            unknown_dimensions = case_dimensions - conformance_dimensions
            if unknown_dimensions:
                errors.append(
                    f"conformance case {case_id} references undeclared dimensions: "
                    + ", ".join(sorted(unknown_dimensions))
                )
            for work_item_id in applicability.intersection(covered_work_items):
                inapplicable_dimensions = case_dimensions - applicability_by_work_item.get(
                    work_item_id, set()
                )
                if inapplicable_dimensions:
                    errors.append(
                        f"conformance case {case_id} references dimensions not applicable to {work_item_id}: "
                        + ", ".join(sorted(inapplicable_dimensions))
                    )
        if conformance_plan.get("required") is True:
            if conformance_items != covered_work_items:
                errors.append(
                    "required conformance plan must exactly cover covered_work_item_ids"
                )
            if executable_dimensions != conformance_dimensions:
                errors.append(
                    "required conformance cases must exactly cover declared dimensions"
                )
            for work_item_id, polarities in polarities_by_work_item.items():
                if polarities != {"positive", "negative"}:
                    errors.append(
                        f"required conformance plan must include positive and negative cases for {work_item_id}"
                    )
        if protocol_applicability.get("applies") is True:
            for work_item_id, polarities in (
                merge_ready_polarities_by_work_item.items()
            ):
                if polarities != {"positive", "negative"}:
                    errors.append(
                        "required protocol work item must have positive and negative merge-ready cases: "
                        + work_item_id
                    )
            for dimension in DELIVERY_ART_PROTOCOL_CONFORMANCE_DIMENSIONS:
                if merge_ready_polarities_by_dimension.get(dimension) != {
                    "positive",
                    "negative",
                }:
                    errors.append(
                        "required protocol dimension must have positive and negative merge-ready cases: "
                        + dimension
                    )
            for (work_item_id, dimension), polarities in (
                merge_ready_polarities_by_pair.items()
            ):
                if polarities != {"positive", "negative"}:
                    errors.append(
                        "required work-item/dimension pair must have positive and negative merge-ready cases: "
                        f"{work_item_id}/{dimension}"
                    )

        git_causality = _artifact_object(conformance_plan.get("git_causality"))
        git_claims = _artifact_object_list(git_causality.get("claims"))
        git_claim_ids = [
            claim.get("id")
            for claim in git_claims
            if isinstance(claim.get("id"), str)
        ]
        if len(git_claim_ids) != len(set(git_claim_ids)):
            errors.append("conformance_plan.git_causality claims must have unique ids")
        for claim in git_claims:
            claim_id = claim.get("id")
            claim_items = set(
                _artifact_string_list(claim.get("applies_to_work_item_ids"))
            )
            claim_dimensions = set(
                _artifact_string_list(claim.get("dimension_ids"))
            )
            for work_item_id in claim_items:
                if work_item_id not in covered_work_items:
                    errors.append(
                        f"Git-causality claim {claim_id} references undeclared work item {work_item_id}"
                    )
                    continue
                outside_dimensions = claim_dimensions - applicability_by_work_item.get(
                    work_item_id, set()
                )
                if outside_dimensions:
                    errors.append(
                        f"Git-causality claim {claim_id} is outside declared applicability for {work_item_id}: "
                        + ", ".join(sorted(outside_dimensions))
                    )
                for dimension in claim_dimensions.intersection(
                    applicability_by_work_item.get(work_item_id, set())
                ):
                    real_git_polarities = {
                        case.get("polarity")
                        for case in conformance_cases
                        if case.get("target_readiness") == "merge-ready"
                        and case.get("fidelity") == "real-git"
                        and work_item_id
                        in _artifact_string_list(
                            case.get("applies_to_work_item_ids")
                        )
                        and dimension
                        in _artifact_string_list(case.get("dimension_ids"))
                    }
                    if real_git_polarities != {"positive", "negative"}:
                        errors.append(
                            "Git-causality claim requires positive and negative real-git merge-ready cases: "
                            f"{work_item_id}/{dimension}"
                        )

        decision = _artifact_object(payload.get("decision"))
        if decision.get("status") == "blocked-pending-architecture-decision":
            open_decisions = [
                entry
                for entry in _artifact_object_list(
                    architecture.get("contradictions_open_decisions")
                )
                if entry.get("status") == "open"
            ]
            if not open_decisions:
                errors.append(
                    "blocked architecture decision must identify at least one open decision"
                )
        if decision.get("status") != "draft":
            _require_artifact_time_order(
                errors,
                "created_at",
                payload.get("created_at"),
                "decision.decided_at",
                decision.get("decided_at"),
            )
            _require_artifact_time_order(
                errors,
                "source_snapshot.captured_at",
                source_snapshot.get("captured_at"),
                "decision.decided_at",
                decision.get("decided_at"),
            )
            if (
                custody.get("state") == "durable"
                and custody.get("backend") == "wgcf-artifact-registry"
            ):
                _require_artifact_time_order(
                    errors,
                    "decision.decided_at",
                    decision.get("decided_at"),
                    "custody.persisted_at",
                    custody.get("persisted_at"),
                )

    if artifact_type == "delivery_art_work_start_record":
        artifact_id = payload.get("artifact_id")
        if isinstance(delivery_id, str) and not _delivery_art_identifier_scoped_to(
            artifact_id, "work-start", delivery_id
        ):
            errors.append("artifact_id must be scoped to delivery_id")
        expected_scope_fingerprint = _delivery_art_projection_digest_if_canonical(
            _work_start_scope_projection(payload)
        )
        if (
            expected_scope_fingerprint is not None
            and payload.get("scope_fingerprint") != expected_scope_fingerprint
        ):
            errors.append(
                "scope_fingerprint must equal the deterministic work-start scope projection "
                + expected_scope_fingerprint
            )
        source_snapshot = _artifact_object(payload.get("source_snapshot"))
        source_art_id = _delivery_art_openproject_id(source_snapshot.get("art_ref"))
        allowed_source_ids = {
            item_number
            for item_number in (
                _delivery_art_entity_number(item, "work-item")
                for item in _artifact_string_list(payload.get("covered_work_item_ids"))
            )
            if item_number is not None
        }
        if delivery_number is not None:
            allowed_source_ids.add(delivery_number)
        if source_art_id not in allowed_source_ids:
            errors.append(
                "work-start source_snapshot.art_ref must reference its Delivery initiative or a covered work item"
            )
        architecture_state = _artifact_object(payload.get("architecture"))
        errors.extend(
            _delivery_art_ref_digest_errors(
                architecture_state.get("packet_ref"),
                architecture_state.get("packet_digest"),
                "architecture.packet_ref",
            )
        )
        landing_unit = _artifact_object(payload.get("landing_unit"))
        invalidation_inputs = set(
            _artifact_string_list(payload.get("invalidation_inputs"))
        )
        if invalidation_inputs != DELIVERY_ART_WORK_START_INVALIDATION_INPUTS:
            missing_inputs = (
                DELIVERY_ART_WORK_START_INVALIDATION_INPUTS - invalidation_inputs
            )
            unexpected_inputs = (
                invalidation_inputs - DELIVERY_ART_WORK_START_INVALIDATION_INPUTS
            )
            details = []
            if missing_inputs:
                details.append("missing " + ", ".join(sorted(missing_inputs)))
            if unexpected_inputs:
                details.append(
                    "unexpected " + ", ".join(sorted(unexpected_inputs))
                )
            errors.append(
                "work-start invalidation_inputs must contain the complete declared set"
                + (": " + "; ".join(details) if details else "")
            )
        if landing_unit.get("decision") in DELIVERY_ART_SOURCE_BACKED_DECISIONS:
            owner_repos = _artifact_string_list(landing_unit.get("owner_repos"))
            branch_plan = _artifact_object_list(landing_unit.get("branch_plan"))
            repo_revisions = _artifact_object_list(
                source_snapshot.get("repo_revisions")
            )
            branch_repos = [
                entry.get("repo")
                for entry in branch_plan
                if isinstance(entry.get("repo"), str)
            ]
            revision_repos = [
                entry.get("repo")
                for entry in repo_revisions
                if isinstance(entry.get("repo"), str)
            ]

            if len(branch_repos) != len(set(branch_repos)):
                errors.append("landing_unit.branch_plan must contain one entry per repo")
            if len(revision_repos) != len(set(revision_repos)):
                errors.append(
                    "source_snapshot.repo_revisions must contain one entry per repo"
                )
            if set(owner_repos) != set(branch_repos):
                errors.append(
                    "landing_unit.owner_repos must exactly match landing_unit.branch_plan repos"
                )
            if set(owner_repos) != set(revision_repos):
                errors.append(
                    "landing_unit.owner_repos must exactly match source_snapshot.repo_revisions repos"
                )

            revisions_by_repo = {
                entry.get("repo"): entry
                for entry in repo_revisions
                if isinstance(entry.get("repo"), str)
            }
            for entry in branch_plan:
                repo = entry.get("repo")
                if not isinstance(repo, str):
                    continue
                revision = revisions_by_repo.get(repo)
                if revision is None:
                    continue
                if entry.get("base_ref") != revision.get("base_ref"):
                    errors.append(
                        f"landing_unit.branch_plan base_ref for {repo} must match the source snapshot"
                    )
                if entry.get("base_commit") != revision.get("commit"):
                    errors.append(
                        f"landing_unit.branch_plan base_commit for {repo} must match the source snapshot"
                    )

        readiness = _artifact_object(payload.get("readiness"))
        if readiness.get("level") != "draft":
            source_snapshot = _artifact_object(payload.get("source_snapshot"))
            custody = _artifact_object(payload.get("custody"))
            _require_artifact_time_order(
                errors,
                "created_at",
                payload.get("created_at"),
                "readiness.evaluated_at",
                readiness.get("evaluated_at"),
            )
            _require_artifact_time_order(
                errors,
                "source_snapshot.captured_at",
                source_snapshot.get("captured_at"),
                "readiness.evaluated_at",
                readiness.get("evaluated_at"),
            )
            _require_artifact_time_order(
                errors,
                "readiness.evaluated_at",
                readiness.get("evaluated_at"),
                "custody.persisted_at",
                custody.get("persisted_at"),
            )

    if artifact_type == "art_review_packet" and payload.get("schema_version") == 2:
        packet_id = payload.get("packet_id")
        if isinstance(delivery_id, str) and not _delivery_art_identifier_scoped_to(
            packet_id, "review-packet", delivery_id
        ):
            errors.append("packet_id must be scoped to delivery_id")
        work_start_ref = _artifact_object(payload.get("work_start"))
        errors.extend(
            _delivery_art_ref_digest_errors(
                work_start_ref.get("artifact_ref"),
                work_start_ref.get("artifact_digest"),
                "work_start.artifact_ref",
            )
        )
        covered_work_items = _artifact_string_list(
            payload.get("covered_work_item_ids")
        )
        evidence = _artifact_object(payload.get("evidence"))
        landing_unit = _artifact_object(payload.get("landing_unit"))
        landing_decision = landing_unit.get("decision")
        evidence_kind = landing_unit.get("evidence_kind")
        repo_evidence = _artifact_object_list(landing_unit.get("repos"))
        repo_names = [
            entry.get("repo_name")
            for entry in repo_evidence
            if isinstance(entry.get("repo_name"), str)
        ]
        if landing_decision == "non_source_child":
            if evidence_kind not in {"pending", "non_source_evidence"}:
                errors.append(
                    "non_source_child Landing Units may use only pending or non_source_evidence"
                )
            if repo_evidence:
                errors.append(
                    "non_source_child Landing Units must not declare source repository evidence"
                )
            if _artifact_object_list(evidence.get("changed_surfaces")):
                errors.append(
                    "non_source_child Landing Units must not declare changed source surfaces"
                )
        elif (
            landing_decision in DELIVERY_ART_SOURCE_BACKED_DECISIONS
            and evidence_kind == "non_source_evidence"
        ):
            errors.append(
                "source-backed Landing Units must not use non_source_evidence"
            )
        if len(repo_names) != len(set(repo_names)):
            errors.append("landing_unit.repos must contain one entry per repo")

        mappings = _artifact_object_list(evidence.get("acceptance_mapping"))
        mapped_work_items = [
            entry.get("work_item_id")
            for entry in mappings
            if isinstance(entry.get("work_item_id"), str)
        ]

        if len(mapped_work_items) != len(set(mapped_work_items)):
            errors.append(
                "evidence.acceptance_mapping must contain one entry per work item"
            )
        if set(mapped_work_items) != set(covered_work_items):
            errors.append(
                "evidence.acceptance_mapping must exactly cover covered_work_item_ids"
            )

        evidence_ids = [
            entry.get("id")
            for section in DELIVERY_ART_EVIDENCE_SECTIONS
            for entry in _artifact_object_list(evidence.get(section))
            if isinstance(entry.get("id"), str)
        ]
        if len(evidence_ids) != len(set(evidence_ids)):
            errors.append("evidence ids must be unique across all evidence sections")
        known_evidence_ids = set(evidence_ids)
        for mapping in mappings:
            work_item_id = mapping.get("work_item_id")
            expected_art_id = _delivery_art_entity_number(work_item_id, "work-item")
            if (
                expected_art_id is not None
                and _delivery_art_openproject_id(mapping.get("acceptance_ref"))
                != expected_art_id
            ):
                errors.append(
                    f"acceptance mapping for {work_item_id} must reference the same OpenProject work item"
                )
            unknown_ids = set(
                _artifact_string_list(mapping.get("evidence_ids"))
            ) - known_evidence_ids
            if unknown_ids:
                errors.append(
                    f"acceptance mapping for {mapping.get('work_item_id')} references unknown evidence ids: "
                    + ", ".join(sorted(unknown_ids))
                )

        if landing_decision in DELIVERY_ART_SOURCE_BACKED_DECISIONS:
            changed_files_by_repo = {
                entry.get("repo_name"): set(
                    _artifact_string_list(entry.get("changed_files"))
                )
                for entry in repo_evidence
                if isinstance(entry.get("repo_name"), str)
            }
            for changed_surface in _artifact_object_list(
                evidence.get("changed_surfaces")
            ):
                repo = changed_surface.get("repo")
                path = changed_surface.get("path")
                if not isinstance(repo, str) or not isinstance(path, str):
                    continue
                if repo not in changed_files_by_repo:
                    errors.append(
                        f"changed surface {path} references undeclared landing repo {repo}"
                    )
                elif path not in changed_files_by_repo[repo]:
                    errors.append(
                        f"changed surface {repo}/{path} is absent from landing_unit.repos changed_files"
                    )

        expected_source_revisions = {
            (entry.get("repo_name"), entry.get("head_commit"))
            for entry in repo_evidence
            if isinstance(entry.get("repo_name"), str)
            and isinstance(entry.get("head_commit"), str)
        }
        for section in (
            "tests",
            "validations",
            "runtime_and_live",
            "security_and_trust",
        ):
            for result in _artifact_object_list(evidence.get(section)):
                revisions = _artifact_object_list(result.get("source_revisions"))
                revision_repos = [
                    revision.get("repo")
                    for revision in revisions
                    if isinstance(revision.get("repo"), str)
                ]
                if len(revision_repos) != len(set(revision_repos)):
                    errors.append(
                        f"evidence result {result.get('id')} must contain one source revision per repo"
                    )
                declared_revisions = {
                    (revision.get("repo"), revision.get("commit"))
                    for revision in revisions
                    if isinstance(revision.get("repo"), str)
                    and isinstance(revision.get("commit"), str)
                }
                if (
                    landing_decision in DELIVERY_ART_SOURCE_BACKED_DECISIONS
                    and result.get("result") == "pass"
                    and declared_revisions != expected_source_revisions
                ):
                    errors.append(
                        f"passing evidence result {result.get('id')} must bind the exact landing-unit source heads"
                    )
                if (
                    landing_decision == "non_source_child"
                    and declared_revisions
                ):
                    errors.append(
                        f"non-source evidence result {result.get('id')} must not declare source revisions"
                    )

        readiness = _artifact_object(payload.get("readiness"))
        custody = _artifact_object(payload.get("custody"))
        _require_artifact_time_order(
            errors,
            "created_at",
            payload.get("created_at"),
            "readiness.evaluated_at",
            readiness.get("evaluated_at"),
        )
        if payload.get("status") == "finalized":
            subject_projection = _review_packet_readiness_subject_projection(
                payload
            )
            expected_subject_digest = _delivery_art_projection_digest_if_canonical(
                subject_projection
            )
            if (
                expected_subject_digest is not None
                and readiness.get("subject_digest") != expected_subject_digest
            ):
                errors.append(
                    "readiness.subject_digest must equal the canonical Review Packet readiness-subject projection "
                    + expected_subject_digest
                )
            _require_artifact_time_order(
                errors,
                "readiness.evaluated_at",
                readiness.get("evaluated_at"),
                "finalized_at",
                payload.get("finalized_at"),
            )
            _require_artifact_time_order(
                errors,
                "finalized_at",
                payload.get("finalized_at"),
                "custody.persisted_at",
                custody.get("persisted_at"),
            )
        if evidence_kind == "approved_direct_land":
            authority_cutoffs = [
                cutoff
                for cutoff in (
                    _artifact_timestamp(readiness.get("evaluated_at")),
                    _artifact_timestamp(payload.get("finalized_at")),
                )
                if cutoff is not None
            ]
            authority_cutoff = max(authority_cutoffs) if authority_cutoffs else None
            valid_direct_land_authority = any(
                authority_cutoff is not None
                and (expires_at := _artifact_timestamp(exception.get("expires_at")))
                is not None
                and expires_at > authority_cutoff
                for exception in _artifact_object_list(payload.get("exceptions"))
                if exception.get("kind") == "direct-land"
            )
            if not valid_direct_land_authority:
                errors.append(
                    "approved_direct_land requires a direct-land exception valid through readiness evaluation and finalization"
                )

    if artifact_type == "delivery_art_readiness_receipt":
        subject = _artifact_object(payload.get("subject"))
        subject_prefixes = {
            "delivery_art_architecture_packet": "architecture-packet",
            "delivery_art_work_start_record": "work-start",
            "art_review_packet": "review-packet",
        }
        subject_prefix = subject_prefixes.get(subject.get("artifact_type"))
        if (
            isinstance(delivery_id, str)
            and isinstance(subject_prefix, str)
            and not _delivery_art_identifier_scoped_to(
                subject.get("artifact_id"), subject_prefix, delivery_id
            )
        ):
            errors.append("readiness receipt subject.artifact_id must be scoped to delivery_id")
        receipt_id = payload.get("receipt_id")
        receipt_token = (
            receipt_id.split(":", 1)[1]
            if isinstance(receipt_id, str) and ":" in receipt_id
            else None
        )
        if receipt_token is not None and (
            f"art-readiness-receipt-{receipt_token}-"
            not in str(custody.get("uri", ""))
        ):
            errors.append("readiness receipt custody URI must include its receipt id")
        readiness = _artifact_object(payload.get("readiness"))
        if delivery_number is not None and readiness.get("target_scope") != (
            f"art:delivery-{delivery_number}"
        ):
            errors.append(
                "readiness receipt target_scope must match its declared Delivery initiative"
            )
        findings = _artifact_object_list(payload.get("findings"))
        finding_ids = [
            finding.get("id")
            for finding in findings
            if isinstance(finding.get("id"), str)
        ]
        if len(finding_ids) != len(set(finding_ids)):
            errors.append("readiness receipt finding ids must be unique")
        if readiness.get("outcome") == "ready" and any(
            finding.get("severity") in {"blocker", "error"}
            for finding in findings
        ):
            errors.append(
                "ready readiness receipt must not contain blocker or error findings"
            )
        if readiness.get("outcome") != "ready" and not findings:
            errors.append("non-ready readiness receipt must identify at least one finding")
        if readiness.get("outcome") == "blocked" and not any(
            finding.get("severity") in {"blocker", "error"}
            for finding in findings
        ):
            errors.append(
                "blocked readiness receipt must identify a blocker or error finding"
            )
        _require_artifact_time_order(
            errors,
            "readiness.evaluated_at",
            readiness.get("evaluated_at"),
            "custody.persisted_at",
            custody.get("persisted_at"),
        )

    if artifact_type == "delivery_art_custody_receipt":
        receipt_id = payload.get("receipt_id")
        if isinstance(receipt_id, str) and receipt_id.removeprefix(
            "artifact-custody-receipt:"
        ) not in str(custody.get("uri", "")):
            errors.append("custody receipt URI must include receipt_id")
        subject = _artifact_object(payload.get("subject"))
        errors.extend(
            _delivery_art_ref_digest_errors(
                subject.get("registry_uri"),
                subject.get("content_digest"),
                "subject.registry_uri",
            )
        )
        storage = _artifact_object(payload.get("storage"))
        _require_strict_artifact_time_order(
            errors,
            "storage.persisted_at",
            storage.get("persisted_at"),
            "custody.persisted_at",
            custody.get("persisted_at"),
        )

    return errors


def delivery_art_artifact_reference_errors(
    payload: dict,
    dependency_artifacts: list[dict],
) -> list[str]:
    """Resolve and compare the immutable artifact chain behind readiness."""
    errors: list[str] = []
    artifacts_by_ref: dict[str, list[dict]] = {}
    all_artifacts = []
    seen_artifact_objects = set()
    for artifact in [payload, *dependency_artifacts]:
        if not isinstance(artifact, dict):
            continue
        if id(artifact) in seen_artifact_objects:
            continue
        seen_artifact_objects.add(id(artifact))
        all_artifacts.append(artifact)
    for artifact in all_artifacts:
        custody = _artifact_object(artifact.get("custody"))
        uri = custody.get("uri")
        if isinstance(uri, str):
            artifacts_by_ref.setdefault(uri, []).append(artifact)

    for uri, artifacts in artifacts_by_ref.items():
        if len(artifacts) > 1:
            errors.append(f"dependency artifact ref {uri} resolves ambiguously")

    def resolve(
        ref: object,
        digest: object,
        label: str,
        expected_type: str,
    ) -> dict | None:
        if not isinstance(ref, str) or not isinstance(digest, str):
            return None
        candidates = artifacts_by_ref.get(ref, [])
        if not candidates:
            errors.append(f"{label} does not resolve to a supplied dependency artifact")
            return None
        if len(candidates) != 1:
            return None
        artifact = candidates[0]
        if artifact.get("artifact_type") != expected_type:
            errors.append(f"{label} resolves to the wrong artifact type")
            return None
        actual_digest = _artifact_object(artifact.get("integrity")).get(
            "content_digest"
        )
        if actual_digest != digest:
            errors.append(f"{label} digest does not match the resolved artifact")
            return None
        return artifact

    def resolve_architecture(work_start: dict) -> dict | None:
        architecture_state = _artifact_object(work_start.get("architecture"))
        if architecture_state.get("readiness") != "architecture-ready":
            return None
        architecture_packet = resolve(
            architecture_state.get("packet_ref"),
            architecture_state.get("packet_digest"),
            "architecture.packet_ref",
            "delivery_art_architecture_packet",
        )
        if architecture_packet is None:
            return None
        architecture_custody = _artifact_object(
            architecture_packet.get("custody")
        )
        if (
            architecture_custody.get("state") != "durable"
            or architecture_custody.get("backend")
            != "wgcf-artifact-registry"
        ):
            errors.append(
                "architecture.packet_ref must resolve to a durable WGCF artifact"
            )
            return None
        if architecture_packet.get("delivery_id") != work_start.get("delivery_id"):
            errors.append(
                "resolved architecture packet delivery_id must match the work-start record"
            )
        if (
            _artifact_object(architecture_packet.get("decision")).get("status")
            != "architecture-ready"
        ):
            errors.append(
                "resolved architecture packet must carry an architecture-ready decision"
            )
        work_start_cutoff = _artifact_object(work_start.get("readiness")).get(
            "evaluated_at"
        ) or work_start.get("created_at")
        _require_artifact_time_order(
            errors,
            "resolved architecture decision.decided_at",
            _artifact_object(architecture_packet.get("decision")).get(
                "decided_at"
            ),
            "work-start evaluation",
            work_start_cutoff,
        )
        _require_artifact_time_order(
            errors,
            "resolved architecture custody.persisted_at",
            _artifact_object(architecture_packet.get("custody")).get(
                "persisted_at"
            ),
            "work-start evaluation",
            work_start_cutoff,
        )
        covered_work_items = set(
            _artifact_string_list(work_start.get("covered_work_item_ids"))
        )
        architecture_items = set(
            _artifact_string_list(
                architecture_packet.get("covered_work_item_ids")
            )
        )
        if not covered_work_items.issubset(architecture_items):
            errors.append(
                "work-start covered_work_item_ids must be covered by the resolved architecture packet"
            )
        owner_map = _artifact_object_list(
            _artifact_object(architecture_packet.get("architecture")).get(
                "descendant_owner_map"
            )
        )
        architecture_owners = {
            entry.get("owner_repo")
            for entry in owner_map
            if entry.get("work_item_id") in covered_work_items
            and isinstance(entry.get("owner_repo"), str)
        }
        landing_owners = set(
            _artifact_string_list(
                _artifact_object(work_start.get("landing_unit")).get("owner_repos")
            )
        )
        if architecture_owners != landing_owners:
            errors.append(
                "work-start owner repos must match the resolved architecture owner map for covered work items"
            )
        return architecture_packet

    def artifact_identifier(artifact: dict) -> object:
        if artifact.get("artifact_type") == "art_review_packet":
            return artifact.get("packet_id")
        if artifact.get("artifact_type") == "delivery_art_custody_receipt":
            return artifact.get("receipt_id")
        return artifact.get("artifact_id")

    def validate_custody_receipt_binding(
        source_artifact: dict,
        receipt: dict,
        label: str,
    ) -> None:
        source_type = source_artifact.get("artifact_type")
        source_custody = _artifact_object(source_artifact.get("custody"))
        receipt_subject = _artifact_object(receipt.get("subject"))
        expected_identifier = artifact_identifier(source_artifact)
        expected_digest = _artifact_object(source_artifact.get("integrity")).get(
            "content_digest"
        )
        expected_values = {
            "artifact_type": source_type,
            "artifact_id": expected_identifier,
            "delivery_id": source_artifact.get("delivery_id"),
            "content_digest": expected_digest,
            "registry_uri": source_custody.get("uri"),
        }
        for field, expected in expected_values.items():
            if receipt_subject.get(field) != expected:
                errors.append(f"{label} subject.{field} must match the source artifact")
        receipt_custody = _artifact_object(receipt.get("custody"))
        _require_strict_artifact_time_order(
            errors,
            f"{label} custody.persisted_at",
            receipt_custody.get("persisted_at"),
            "source artifact custody.persisted_at",
            source_custody.get("persisted_at"),
        )

    def receipt_subject_digest(artifact: dict, digest_kind: object) -> object:
        if digest_kind == "artifact-content":
            return _artifact_object(artifact.get("integrity")).get(
                "content_digest"
            )
        if (
            digest_kind == "readiness-subject"
            and artifact.get("artifact_type") == "art_review_packet"
        ):
            return _delivery_art_projection_digest_if_canonical(
                _review_packet_readiness_subject_projection(artifact)
            )
        return None

    artifact_type = payload.get("artifact_type")

    if artifact_type in {
        "delivery_art_architecture_packet",
        "delivery_art_work_start_record",
        "art_review_packet",
    }:
        payload_custody = _artifact_object(payload.get("custody"))
        if (
            payload_custody.get("state") == "durable"
            and payload_custody.get("backend") == "wgcf-artifact-registry"
        ):
            custody_receipt_ref = _artifact_object(
                payload_custody.get("receipt_ref")
            )
            custody_receipt = resolve(
                custody_receipt_ref.get("uri"),
                custody_receipt_ref.get("digest"),
                "custody.receipt_ref.uri",
                "delivery_art_custody_receipt",
            )
            if custody_receipt is not None:
                validate_custody_receipt_binding(
                    payload,
                    custody_receipt,
                    "custody receipt",
                )

    if artifact_type == "delivery_art_custody_receipt":
        subject = _artifact_object(payload.get("subject"))
        subject_candidates = [
            artifact
            for artifact in all_artifacts
            if artifact is not payload
            and artifact.get("artifact_type") == subject.get("artifact_type")
            and artifact_identifier(artifact) == subject.get("artifact_id")
            and _artifact_object(artifact.get("integrity")).get("content_digest")
            == subject.get("content_digest")
            and _artifact_object(artifact.get("custody")).get("uri")
            == subject.get("registry_uri")
        ]
        if not subject_candidates:
            errors.append(
                "custody receipt subject does not resolve to the declared source artifact"
            )
        elif len(subject_candidates) > 1:
            errors.append("custody receipt subject resolves ambiguously")
        else:
            validate_custody_receipt_binding(
                subject_candidates[0],
                payload,
                "custody receipt",
            )

    current_artifact = payload
    current_uri = _artifact_object(payload.get("custody")).get("uri")
    visited_supersession_uris = {current_uri} if isinstance(current_uri, str) else set()
    supersession_cycle_reported = False
    while True:
        current_custody = _artifact_object(current_artifact.get("custody"))
        supersedes = _artifact_object(current_custody.get("supersedes"))
        if not supersedes:
            break
        prior_uri = supersedes.get("uri")
        prior_artifact = resolve(
            prior_uri,
            supersedes.get("digest"),
            "custody.supersedes.uri",
            str(artifact_type),
        )
        if prior_artifact is None:
            break
        if prior_uri in visited_supersession_uris:
            errors.append("custody.supersedes chain must be acyclic")
            supersession_cycle_reported = True
            break
        if artifact_type == "delivery_art_custody_receipt":
            replacement_subject = _artifact_object(payload.get("subject"))
            prior_subject = _artifact_object(prior_artifact.get("subject"))
            for field in ("delivery_id", "artifact_type", "artifact_id"):
                if prior_subject.get(field) != replacement_subject.get(field):
                    errors.append(
                        "superseded custody receipt "
                        f"subject.{field} must match the replacement receipt"
                    )
        elif prior_artifact.get("delivery_id") != payload.get("delivery_id"):
            errors.append(
                "superseded artifact delivery_id must match the replacement artifact"
            )
        prior_custody = _artifact_object(prior_artifact.get("custody"))
        if prior_custody.get("state") != "durable":
            errors.append("custody.supersedes must resolve a durable artifact")
        _require_strict_artifact_time_order(
            errors,
            "superseded artifact custody.persisted_at",
            prior_custody.get("persisted_at"),
            "replacement artifact custody.persisted_at",
            current_custody.get("persisted_at"),
        )
        if isinstance(prior_uri, str):
            visited_supersession_uris.add(prior_uri)
        current_artifact = prior_artifact
    if supersession_cycle_reported:
        return errors

    if artifact_type == "delivery_art_work_start_record":
        resolve_architecture(payload)

    if artifact_type == "delivery_art_readiness_receipt":
        subject = _artifact_object(payload.get("subject"))
        subject_candidates = [
            artifact
            for artifact in all_artifacts
            if artifact is not payload
            and artifact.get("artifact_type") == subject.get("artifact_type")
            and artifact_identifier(artifact) == subject.get("artifact_id")
            and receipt_subject_digest(artifact, subject.get("digest_kind"))
            == subject.get("digest")
        ]
        if not subject_candidates:
            errors.append(
                "readiness receipt subject does not resolve to a supplied artifact with the declared id and digest"
            )
        elif len(subject_candidates) > 1:
            errors.append("readiness receipt subject resolves ambiguously")
        else:
            subject_artifact = subject_candidates[0]
            if subject_artifact.get("delivery_id") != payload.get("delivery_id"):
                errors.append(
                    "readiness receipt subject delivery_id must match the receipt"
                )
            if set(
                _artifact_string_list(subject_artifact.get("covered_work_item_ids"))
            ) != set(_artifact_string_list(payload.get("covered_work_item_ids"))):
                errors.append(
                    "readiness receipt coverage must match its resolved subject artifact"
                )

            receipt_readiness = _artifact_object(payload.get("readiness"))
            readiness_level = receipt_readiness.get("level")
            expected_ready_subjects = {
                "architecture-ready": (
                    "delivery_art_architecture_packet",
                    _artifact_object(subject_artifact.get("decision")).get("status"),
                    "architecture-ready",
                ),
                "implementation-ready": (
                    "delivery_art_work_start_record",
                    _artifact_object(subject_artifact.get("readiness")).get("level"),
                    "implementation-ready",
                ),
                "merge-ready": (
                    "art_review_packet",
                    (
                        subject_artifact.get("status"),
                        _artifact_object(subject_artifact.get("readiness")).get(
                            "level"
                        ),
                    ),
                    ("merge-ready", "merge-ready"),
                ),
                "operating-ready": (
                    "art_review_packet",
                    (
                        subject_artifact.get("status"),
                        _artifact_object(subject_artifact.get("readiness")).get(
                            "level"
                        ),
                    ),
                    ("finalized", "operating-ready"),
                ),
            }
            expected_subject = expected_ready_subjects.get(readiness_level)
            if expected_subject is not None:
                expected_type, actual_state, expected_state = expected_subject
                if subject_artifact.get("artifact_type") != expected_type:
                    errors.append(
                        "readiness receipt level resolves the wrong subject artifact type"
                    )
                if (
                    receipt_readiness.get("outcome") == "ready"
                    and actual_state != expected_state
                ):
                    errors.append(
                        "ready readiness receipt subject has not reached the declared readiness level"
                    )

            subject_state_time = None
            if readiness_level == "architecture-ready":
                subject_state_time = _artifact_object(
                    subject_artifact.get("decision")
                ).get("decided_at")
            elif readiness_level in {
                "implementation-ready",
                "merge-ready",
                "operating-ready",
            }:
                subject_state_time = _artifact_object(
                    subject_artifact.get("readiness")
                ).get("evaluated_at")
            _require_artifact_time_order(
                errors,
                "readiness receipt subject decision",
                subject_state_time,
                "readiness receipt evaluation",
                receipt_readiness.get("evaluated_at"),
            )

            if subject.get("digest_kind") == "artifact-content":
                subject_custody = _artifact_object(subject_artifact.get("custody"))
                if subject_custody.get("state") != "durable":
                    errors.append(
                        "artifact-content readiness receipt must resolve a durable subject artifact"
                    )
                _require_artifact_time_order(
                    errors,
                    "readiness receipt subject custody.persisted_at",
                    subject_custody.get("persisted_at"),
                    "readiness receipt evaluation",
                    receipt_readiness.get("evaluated_at"),
                )
            elif (
                readiness_level == "operating-ready"
                and _artifact_object(subject_artifact.get("readiness")).get(
                    "evaluated_at"
                )
                != receipt_readiness.get("evaluated_at")
            ):
                errors.append(
                    "operating-readiness receipt evaluation time must match its Review Packet subject"
                )

    if artifact_type == "art_review_packet" and payload.get("schema_version") == 2:
        work_start_ref = _artifact_object(payload.get("work_start"))
        work_start = resolve(
            work_start_ref.get("artifact_ref"),
            work_start_ref.get("artifact_digest"),
            "work_start.artifact_ref",
            "delivery_art_work_start_record",
        )
        if work_start is None:
            return errors

        if work_start.get("delivery_id") != payload.get("delivery_id"):
            errors.append(
                "Review Packet delivery_id must match the resolved work-start record"
            )
        if set(_artifact_string_list(work_start.get("covered_work_item_ids"))) != set(
            _artifact_string_list(payload.get("covered_work_item_ids"))
        ):
            errors.append(
                "Review Packet covered_work_item_ids must match the resolved work-start record"
            )
        if work_start.get("scope_fingerprint") != work_start_ref.get(
            "scope_fingerprint"
        ):
            errors.append(
                "Review Packet scope_fingerprint must match the resolved work-start record"
            )
        if (
            _artifact_object(work_start.get("readiness")).get("level")
            != "implementation-ready"
        ):
            errors.append(
                "Review Packet must resolve an implementation-ready work-start record"
            )
        _require_artifact_time_order(
            errors,
            "resolved work-start readiness.evaluated_at",
            _artifact_object(work_start.get("readiness")).get("evaluated_at"),
            "Review Packet created_at",
            payload.get("created_at"),
        )
        _require_artifact_time_order(
            errors,
            "resolved work-start custody.persisted_at",
            _artifact_object(work_start.get("custody")).get("persisted_at"),
            "Review Packet created_at",
            payload.get("created_at"),
        )

        work_landing = _artifact_object(work_start.get("landing_unit"))
        packet_landing = _artifact_object(payload.get("landing_unit"))
        if work_landing.get("decision") != packet_landing.get("decision"):
            errors.append(
                "Review Packet Landing Unit decision must match the resolved work-start record"
            )

        if work_landing.get("decision") in DELIVERY_ART_SOURCE_BACKED_DECISIONS:
            branch_plan = {
                entry.get("repo"): entry
                for entry in _artifact_object_list(work_landing.get("branch_plan"))
                if isinstance(entry.get("repo"), str)
            }
            repo_evidence = {
                entry.get("repo_name"): entry
                for entry in _artifact_object_list(packet_landing.get("repos"))
                if isinstance(entry.get("repo_name"), str)
            }
            owner_repos = set(_artifact_string_list(work_landing.get("owner_repos")))
            if set(repo_evidence) != owner_repos:
                errors.append(
                    "Review Packet repos must exactly match the resolved work-start owner repos"
                )
            for repo, branch in branch_plan.items():
                evidence = repo_evidence.get(repo)
                if evidence is None:
                    continue
                for packet_field, work_field in (
                    ("branch", "branch"),
                    ("base_ref", "base_ref"),
                    ("base_commit", "base_commit"),
                ):
                    if evidence.get(packet_field) != branch.get(work_field):
                        errors.append(
                            f"Review Packet {packet_field} for {repo} must match the resolved work-start branch plan"
                        )

        architecture_packet = resolve_architecture(work_start)
        if architecture_packet is not None:
            conformance_plan = _artifact_object(
                architecture_packet.get("conformance_plan")
            )
            if conformance_plan.get("required") is True:
                packet_items = set(
                    _artifact_string_list(payload.get("covered_work_item_ids"))
                )
                packet_rank = DELIVERY_ART_READINESS_RANK.get(
                    _artifact_object(payload.get("readiness")).get("level"), 0
                )
                cases = {
                    case.get("id"): case
                    for case in _artifact_object_list(conformance_plan.get("cases"))
                    if isinstance(case.get("id"), str)
                }
                applicable_cases = {
                    case_id: case
                    for case_id, case in cases.items()
                    if packet_items.intersection(
                        _artifact_string_list(
                            case.get("applies_to_work_item_ids")
                        )
                    )
                    and DELIVERY_ART_READINESS_RANK.get(
                        case.get("target_readiness"), 99
                    )
                    <= packet_rank
                }
                evidence = _artifact_object(payload.get("evidence"))
                case_results: dict[str, list[dict]] = {}
                for section in (
                    "tests",
                    "validations",
                    "runtime_and_live",
                    "security_and_trust",
                ):
                    for result in _artifact_object_list(evidence.get(section)):
                        for case_id in _artifact_string_list(
                            result.get("conformance_case_ids")
                        ):
                            case_results.setdefault(case_id, []).append(result)

                unknown_case_ids = set(case_results) - set(cases)
                if unknown_case_ids:
                    errors.append(
                        "Review Packet evidence references unknown conformance cases: "
                        + ", ".join(sorted(unknown_case_ids))
                    )
                premature_case_ids = set(case_results) - set(applicable_cases)
                if premature_case_ids:
                    errors.append(
                        "Review Packet evidence binds conformance cases outside its work-item or readiness scope: "
                        + ", ".join(sorted(premature_case_ids))
                    )
                missing_case_ids = set(applicable_cases) - set(case_results)
                if missing_case_ids:
                    errors.append(
                        "Review Packet is missing applicable conformance case results: "
                        + ", ".join(sorted(missing_case_ids))
                    )
                for case_id, results in case_results.items():
                    case = applicable_cases.get(case_id)
                    if case is None:
                        continue
                    for result in results:
                        if result.get("result") != "pass":
                            errors.append(
                                f"conformance case {case_id} must have a passing result"
                            )
                        if result.get("fidelity") != case.get("fidelity"):
                            errors.append(
                                f"conformance case {case_id} must use planned fidelity {case.get('fidelity')}"
                            )

        if payload.get("status") == "finalized":
            packet_landing = _artifact_object(payload.get("landing_unit"))
            if packet_landing.get("decision") in DELIVERY_ART_SOURCE_BACKED_DECISIONS:
                supersedes = _artifact_object(
                    _artifact_object(payload.get("custody")).get("supersedes")
                )
                merge_ready_predecessor = resolve(
                    supersedes.get("uri"),
                    supersedes.get("digest"),
                    "custody.supersedes.uri",
                    "art_review_packet",
                )
                if merge_ready_predecessor is not None:
                    if merge_ready_predecessor.get("status") != "merge-ready":
                        errors.append(
                            "finalized source Review Packet must supersede a merge-ready Review Packet"
                        )
                    errors.extend(
                        _review_packet_predecessor_continuity_errors(
                            payload, merge_ready_predecessor
                        )
                    )

            readiness = _artifact_object(payload.get("readiness"))
            for receipt_ref in _artifact_object_list(readiness.get("receipt_refs")):
                receipt = resolve(
                    receipt_ref.get("uri"),
                    receipt_ref.get("digest"),
                    "readiness.receipt_refs.uri",
                    "delivery_art_readiness_receipt",
                )
                if receipt is None:
                    continue
                if receipt.get("delivery_id") != payload.get("delivery_id"):
                    errors.append(
                        "resolved readiness receipt delivery_id must match the Review Packet"
                    )
                if set(
                    _artifact_string_list(receipt.get("covered_work_item_ids"))
                ) != set(_artifact_string_list(payload.get("covered_work_item_ids"))):
                    errors.append(
                        "resolved readiness receipt coverage must match the Review Packet"
                    )
                receipt_subject = _artifact_object(receipt.get("subject"))
                if receipt_subject.get("artifact_id") != payload.get("packet_id"):
                    errors.append(
                        "resolved readiness receipt artifact_id must match the Review Packet"
                    )
                if receipt_subject.get("digest_kind") != "readiness-subject":
                    errors.append(
                        "finalized Review Packet requires a readiness-subject receipt"
                    )
                if receipt_subject.get("digest") != readiness.get("subject_digest"):
                    errors.append(
                        "resolved readiness receipt subject digest must match the Review Packet"
                    )
                receipt_readiness = _artifact_object(receipt.get("readiness"))
                if receipt_readiness.get("level") != readiness.get("level"):
                    errors.append(
                        "resolved readiness receipt level must match the Review Packet"
                    )
                if receipt_readiness.get("outcome") != "ready" or receipt_readiness.get(
                    "mutation_allowed"
                ) is not True:
                    errors.append(
                        "finalized Review Packet requires a ready receipt that permits mutation"
                    )
                if receipt_readiness.get("evaluated_at") != readiness.get(
                    "evaluated_at"
                ):
                    errors.append(
                        "resolved readiness receipt evaluation time must match the Review Packet"
                    )
                _require_artifact_time_order(
                    errors,
                    "resolved readiness receipt custody.persisted_at",
                    _artifact_object(receipt.get("custody")).get("persisted_at"),
                    "Review Packet finalized_at",
                    payload.get("finalized_at"),
                )
                _require_artifact_time_order(
                    errors,
                    "resolved readiness receipt custody.persisted_at",
                    _artifact_object(receipt.get("custody")).get("persisted_at"),
                    "Review Packet custody.persisted_at",
                    _artifact_object(payload.get("custody")).get("persisted_at"),
                )

    return errors


def delivery_art_artifact_integrity_errors(payload: dict) -> list[str]:
    """Validate the declared content digest and durable content-addressed URI."""
    canonicalization_errors = _artifact_canonicalization_errors(payload)
    if canonicalization_errors:
        return canonicalization_errors
    digest_projection = _delivery_art_content_digest_projection(payload)
    expected_digest = _delivery_art_projection_digest(digest_projection)
    actual_digest = _artifact_object(payload.get("integrity")).get("content_digest")
    errors = []
    if actual_digest != expected_digest:
        errors.append(
            f"integrity.content_digest must equal canonical content digest {expected_digest}"
        )
    custody = _artifact_object(payload.get("custody"))
    if custody.get("state") == "durable":
        digest_hex = expected_digest.removeprefix("sha256:")
        if digest_hex not in str(custody.get("uri", "")):
            errors.append("durable custody URI must include the full content digest")
    return errors


def validate_delivery_art_artifact_contracts(
    errors: list[str],
    repo_root: Path,
) -> set[str]:
    validators: dict[str, Draft202012Validator] = {}
    fixtures: dict[str, dict] = {}
    executed_proof_cases: set[str] = set()

    for artifact_name, (schema_ref, fixture_refs) in DELIVERY_ART_ARTIFACT_CASES.items():
        schema_path = repo_root / schema_ref
        if not schema_path.exists():
            errors.append(f"{schema_ref}: Delivery ART artifact schema is missing")
            continue
        schema = load_json(schema_path)
        try:
            Draft202012Validator.check_schema(schema)
        except SchemaError as exc:
            errors.append(f"{schema_ref}: invalid JSON Schema: {exc.message}")
            continue

        validator = Draft202012Validator(
            schema,
            format_checker=CONTRACT_FORMAT_CHECKER,
        )
        validators[artifact_name] = validator
        for fixture_ref in fixture_refs:
            fixture_path = repo_root / fixture_ref
            if not fixture_path.exists():
                errors.append(f"{fixture_ref}: Delivery ART artifact fixture is missing")
                continue
            fixture = load_json(fixture_path)
            fixture_errors = sorted(
                validator.iter_errors(fixture),
                key=lambda error: list(error.absolute_path),
            )
            for error in fixture_errors:
                path = ".".join(str(part) for part in error.absolute_path) or "<root>"
                errors.append(f"{fixture_ref}: {path}: {error.message}")
            if isinstance(fixture, dict):
                for error in delivery_art_artifact_semantic_errors(fixture):
                    errors.append(f"{fixture_ref}: semantic invariant: {error}")
                for error in delivery_art_artifact_integrity_errors(fixture):
                    errors.append(f"{fixture_ref}: integrity invariant: {error}")
                fixtures[Path(fixture_ref).name] = fixture

    if "architecture-packet.valid.json" in fixtures:
        executed_proof_cases.update(
            {"architecture-structure-valid", "architecture-conformance-valid"}
        )
    if "work-start-record.valid.json" in fixtures:
        executed_proof_cases.add("work-start-valid")
    if "review-packet-merge-ready.valid.json" in fixtures:
        executed_proof_cases.add("review-evidence-valid")
    if "readiness-receipt.valid.json" in fixtures:
        executed_proof_cases.add("readiness-receipt-valid")
    if fixtures:
        executed_proof_cases.add("canonical-integrity-valid")

    fixture_dependencies = list(fixtures.values())
    for fixture_name, fixture in fixtures.items():
        for error in delivery_art_artifact_reference_errors(
            fixture, fixture_dependencies
        ):
            errors.append(f"{fixture_name}: reference invariant: {error}")
    if {
        "architecture-packet.valid.json",
        "work-start-record.valid.json",
        "review-packet-merge-ready.valid.json",
        "review-packet-finalized.valid.json",
        "readiness-receipt.valid.json",
        "architecture-custody-receipt.valid.json",
        "work-start-custody-receipt.valid.json",
        "merge-ready-custody-receipt.valid.json",
        "finalized-custody-receipt.valid.json",
    }.issubset(fixtures):
        executed_proof_cases.add("reference-chain-valid")

    def require_rejected(
        validator_name: str,
        payload: dict,
        case_name: str,
        proof_case_id: str | None = None,
        expected_fragment: str | None = None,
    ) -> None:
        validator = validators.get(validator_name)
        schema_errors = list(validator.iter_errors(payload)) if validator else []
        semantic_errors = delivery_art_artifact_semantic_errors(payload)
        if validator is not None and not schema_errors and not semantic_errors:
            errors.append(
                f"Delivery ART contract negative case {case_name!r} must be rejected"
            )
        if expected_fragment is not None:
            observed = [error.message for error in schema_errors] + semantic_errors
            if not any(expected_fragment in error for error in observed):
                errors.append(
                    f"Delivery ART contract negative case {case_name!r} must report {expected_fragment!r}"
                )
        if proof_case_id:
            executed_proof_cases.add(proof_case_id)

    def require_accepted(
        validator_name: str,
        payload: dict,
        case_name: str,
        proof_case_id: str | None = None,
    ) -> None:
        validator = validators.get(validator_name)
        schema_errors = list(validator.iter_errors(payload)) if validator else []
        semantic_errors = delivery_art_artifact_semantic_errors(payload)
        if schema_errors or semantic_errors:
            details = [error.message for error in schema_errors] + semantic_errors
            errors.append(
                f"Delivery ART contract positive case {case_name!r} must be accepted: "
                + "; ".join(details)
            )
        if proof_case_id:
            executed_proof_cases.add(proof_case_id)

    def require_integrity_error(
        payload: dict,
        case_name: str,
        expected_fragment: str,
        proof_case_id: str | None = None,
    ) -> None:
        integrity_errors = delivery_art_artifact_integrity_errors(payload)
        if not any(expected_fragment in error for error in integrity_errors):
            errors.append(
                f"Delivery ART integrity case {case_name!r} must report {expected_fragment!r}"
            )
        if proof_case_id:
            executed_proof_cases.add(proof_case_id)

    def require_reference_rejected(
        payload: dict,
        case_name: str,
        expected_fragment: str,
        dependencies: list[dict] | None = None,
        proof_case_id: str | None = None,
    ) -> None:
        reference_errors = delivery_art_artifact_reference_errors(
            payload,
            dependencies if dependencies is not None else fixture_dependencies,
        )
        if not any(expected_fragment in error for error in reference_errors):
            errors.append(
                f"Delivery ART reference case {case_name!r} must report {expected_fragment!r}"
            )
        if proof_case_id:
            executed_proof_cases.add(proof_case_id)

    def require_reference_accepted(
        payload: dict,
        case_name: str,
        dependencies: list[dict] | None = None,
    ) -> None:
        reference_errors = delivery_art_artifact_reference_errors(
            payload,
            dependencies if dependencies is not None else fixture_dependencies,
        )
        if reference_errors:
            errors.append(
                f"Delivery ART reference positive case {case_name!r} must be accepted: "
                + "; ".join(reference_errors)
            )

    def require_fully_accepted(
        validator_name: str,
        payload: dict,
        case_name: str,
        dependencies: list[dict] | None = None,
    ) -> None:
        validator = validators.get(validator_name)
        schema_errors = list(validator.iter_errors(payload)) if validator else []
        observed = [error.message for error in schema_errors]
        observed.extend(delivery_art_artifact_semantic_errors(payload))
        observed.extend(delivery_art_artifact_integrity_errors(payload))
        observed.extend(
            delivery_art_artifact_reference_errors(
                payload,
                dependencies if dependencies is not None else fixture_dependencies,
            )
        )
        if observed:
            errors.append(
                f"Delivery ART full-contract positive case {case_name!r} must be accepted: "
                + "; ".join(observed)
            )

    try:
        json.loads(
            '{"artifact_type":"first","artifact_type":"second"}',
            object_pairs_hook=strict_delivery_art_object,
        )
    except ValueError as exc:
        if "duplicate JSON object key" not in str(exc):
            errors.append(
                "Delivery ART duplicate-key case must identify the duplicate key"
            )
    else:
        errors.append("Delivery ART duplicate JSON object keys must be rejected")
    executed_proof_cases.add("canonical-integrity-invalid")

    architecture = fixtures.get("architecture-packet.valid.json")
    architecture_custody_receipt = fixtures.get(
        "architecture-custody-receipt.valid.json"
    )
    work_start_custody_receipt = fixtures.get(
        "work-start-custody-receipt.valid.json"
    )
    merge_ready_custody_receipt = fixtures.get(
        "merge-ready-custody-receipt.valid.json"
    )
    finalized_custody_receipt = fixtures.get(
        "finalized-custody-receipt.valid.json"
    )
    if architecture:
        legacy_attachment_custody = copy.deepcopy(architecture)
        legacy_attachment_custody["custody"]["backend"] = (
            "openproject-attachment"
        )
        legacy_attachment_custody["custody"]["uri"] = (
            "openproject://work_packages/698/attachments/architecture.json"
        )
        require_rejected(
            "architecture_packet",
            legacy_attachment_custody,
            "legacy OpenProject attachment custody",
        )

        missing_custody_receipt = copy.deepcopy(architecture)
        missing_custody_receipt["custody"].pop("receipt_ref")
        require_rejected(
            "architecture_packet",
            missing_custody_receipt,
            "durable WGCF artifact without a custody receipt reference",
        )

        mismatched_custody_receipt_digest = copy.deepcopy(architecture)
        mismatched_custody_receipt_digest["custody"]["receipt_ref"]["digest"] = (
            "sha256:" + "b" * 64
        )
        require_rejected(
            "architecture_packet",
            mismatched_custody_receipt_digest,
            "custody receipt reference whose URI does not bind its digest",
            expected_fragment="custody.receipt_ref.uri must include its declared content digest",
        )

        if architecture_custody_receipt:
            wrong_custody_subject = copy.deepcopy(
                architecture_custody_receipt
            )
            wrong_custody_subject["subject"]["artifact_id"] = (
                "architecture-packet:delivery-698-wrong"
            )
            require_reference_rejected(
                architecture,
                "source artifact whose custody receipt binds another subject",
                "custody receipt subject.artifact_id must match the source artifact",
                [wrong_custody_subject],
            )

            wrong_storage_owner = copy.deepcopy(architecture_custody_receipt)
            wrong_storage_owner["storage"]["runtime_owner"] = (
                "operator-orchestration-service"
            )
            require_rejected(
                "custody_receipt",
                wrong_storage_owner,
                "custody receipt claiming the wrong physical storage owner",
            )

            def custody_receipt_variant(
                receipt_token: str,
                subject_overrides: dict | None = None,
                supersedes: dict | None = None,
                storage_persisted_at: str = "2026-08-08T10:05:56+08:00",
                custody_persisted_at: str = "2026-08-08T10:05:57+08:00",
            ) -> dict:
                receipt = copy.deepcopy(architecture_custody_receipt)
                receipt["receipt_id"] = (
                    f"artifact-custody-receipt:{receipt_token}"
                )
                receipt["subject"].update(subject_overrides or {})
                receipt["storage"]["persisted_at"] = storage_persisted_at
                receipt["custody"]["persisted_at"] = custody_persisted_at
                receipt["custody"]["supersedes"] = copy.deepcopy(supersedes)
                digest_projection = _delivery_art_content_digest_projection(
                    receipt
                )
                content_digest = _delivery_art_projection_digest(
                    digest_projection
                )
                receipt["integrity"]["content_digest"] = content_digest
                receipt["custody"]["uri"] = (
                    "wgcf://receipts/artifact-custody/"
                    f"{receipt_token}-"
                    f"{content_digest.removeprefix('sha256:')}.json"
                )
                return receipt

            prior_same_subject = custody_receipt_variant("e" * 24)
            replacement_receipt = custody_receipt_variant(
                "f" * 24,
                supersedes={
                    "uri": prior_same_subject["custody"]["uri"],
                    "digest": prior_same_subject["integrity"][
                        "content_digest"
                    ],
                },
                storage_persisted_at="2026-08-08T10:05:58+08:00",
                custody_persisted_at="2026-08-08T10:05:59+08:00",
            )
            require_fully_accepted(
                "custody_receipt",
                replacement_receipt,
                "corrected custody receipt superseding the same subject",
                [architecture, prior_same_subject],
            )

            redirected_supersession = copy.deepcopy(replacement_receipt)
            redirected_supersession["custody"]["supersedes"]["digest"] = (
                "sha256:" + "9" * 64
            )
            require_integrity_error(
                redirected_supersession,
                "custody receipt with redirected supersession metadata",
                "integrity.content_digest must equal canonical content digest",
            )

            unrelated_subject_values = {
                "delivery_id": "delivery-699",
                "artifact_type": "delivery_art_work_start_record",
                "artifact_id": "architecture-packet:delivery-698-unrelated",
            }
            for index, (field, value) in enumerate(
                unrelated_subject_values.items()
            ):
                unrelated_prior_receipt = custody_receipt_variant(
                    str(index + 1) * 24,
                    {field: value},
                )
                replacement_receipt = custody_receipt_variant(
                    "f" * 24,
                    supersedes={
                        "uri": unrelated_prior_receipt["custody"]["uri"],
                        "digest": unrelated_prior_receipt["integrity"][
                            "content_digest"
                        ],
                    },
                    storage_persisted_at="2026-08-08T10:05:58+08:00",
                    custody_persisted_at="2026-08-08T10:05:59+08:00",
                )
                require_reference_rejected(
                    replacement_receipt,
                    "custody receipt superseding an unrelated subject "
                    f"by {field}",
                    "superseded custody receipt "
                    f"subject.{field} must match the replacement receipt",
                    [architecture, unrelated_prior_receipt],
                )

        stale_decision = copy.deepcopy(architecture)
        stale_decision["decision"]["status"] = "ready-for-child-implementation"
        require_rejected(
            "architecture_packet",
            stale_decision,
            "legacy architecture decision vocabulary",
        )

        overlapping_delivery_identifier = copy.deepcopy(architecture)
        overlapping_delivery_identifier["artifact_id"] = (
            "architecture-packet:delivery-6980-v1"
        )
        require_rejected(
            "architecture_packet",
            overlapping_delivery_identifier,
            "architecture artifact id with only a delivery-id prefix overlap",
        )

        unresolved_decision = copy.deepcopy(architecture)
        unresolved_decision["architecture"]["contradictions_open_decisions"][0][
            "status"
        ] = "open"
        unresolved_decision["architecture"]["contradictions_open_decisions"][0][
            "resolution"
        ] = None
        require_rejected(
            "architecture_packet",
            unresolved_decision,
            "architecture-ready packet with an open contradiction",
        )

        architecture_ready_without_required_conformance = copy.deepcopy(
            architecture
        )
        architecture_ready_without_required_conformance["conformance_plan"][
            "required"
        ] = False
        require_rejected(
            "architecture_packet",
            architecture_ready_without_required_conformance,
            "architecture-ready packet without a required conformance plan",
        )

        missing_protocol_applicability = copy.deepcopy(architecture)
        del missing_protocol_applicability["conformance_plan"][
            "protocol_applicability"
        ]
        require_rejected(
            "architecture_packet",
            missing_protocol_applicability,
            "architecture packet without an explicit protocol applicability decision",
        )

        incomplete_protocol_dimensions = copy.deepcopy(architecture)
        incomplete_protocol_dimensions["conformance_plan"]["dimensions"].pop()
        require_rejected(
            "architecture_packet",
            incomplete_protocol_dimensions,
            "applicable protocol conformance plan missing a mandated dimension",
            "architecture-conformance-invalid",
        )

        case_without_dimensions = copy.deepcopy(architecture)
        del case_without_dimensions["conformance_plan"]["cases"][0][
            "dimension_ids"
        ]
        require_rejected(
            "architecture_packet",
            case_without_dimensions,
            "architecture conformance case without dimension bindings",
        )

        untested_protocol_dimension = copy.deepcopy(architecture)
        for case in untested_protocol_dimension["conformance_plan"]["cases"]:
            case["dimension_ids"] = [
                dimension
                for dimension in case["dimension_ids"]
                if dimension != "shared-validator-compatibility"
            ]
        require_rejected(
            "architecture_packet",
            untested_protocol_dimension,
            "protocol conformance plan with a declared but untested dimension",
        )

        protocol_dimension_deferred_past_merge = copy.deepcopy(architecture)
        for case in protocol_dimension_deferred_past_merge["conformance_plan"][
            "cases"
        ]:
            if "shared-validator-compatibility" in case["dimension_ids"]:
                case["target_readiness"] = "operating-ready"
        require_rejected(
            "architecture_packet",
            protocol_dimension_deferred_past_merge,
            "protocol dimension without positive and negative merge-ready cases",
        )

        protocol_work_item_deferred_past_merge = copy.deepcopy(architecture)
        original_cases = protocol_work_item_deferred_past_merge[
            "conformance_plan"
        ]["cases"]
        deferred_cases = []
        for case in original_cases:
            case["applies_to_work_item_ids"] = ["work-item-801"]
            deferred_case = copy.deepcopy(case)
            deferred_case["id"] = f"{case['id']}-deferred-work-item-802"
            deferred_case["applies_to_work_item_ids"] = ["work-item-802"]
            deferred_case["target_readiness"] = "operating-ready"
            deferred_cases.append(deferred_case)
        original_cases.extend(deferred_cases)
        require_rejected(
            "architecture_packet",
            protocol_work_item_deferred_past_merge,
            "protocol work item without positive and negative merge-ready cases",
        )

        conformance_case_with_undeclared_dimension = copy.deepcopy(architecture)
        conformance_case_with_undeclared_dimension["conformance_plan"]["cases"][
            0
        ]["dimension_ids"].append("undeclared-protocol-dimension")
        require_rejected(
            "architecture_packet",
            conformance_case_with_undeclared_dimension,
            "architecture conformance case referencing an undeclared dimension",
        )

        non_protocol_conformance = copy.deepcopy(architecture)
        non_protocol_conformance["conformance_plan"]["protocol_applicability"] = {
            "applies": False,
            "rationale": "The architecture decision is local and does not change a cross-repo protocol.",
        }
        non_protocol_conformance["conformance_plan"]["dimensions"] = [
            "local-architecture-regression"
        ]
        non_protocol_conformance["conformance_plan"][
            "work_item_dimension_applicability"
        ] = [
            {
                "work_item_id": work_item_id,
                "dimension_ids": ["local-architecture-regression"],
            }
            for work_item_id in non_protocol_conformance[
                "covered_work_item_ids"
            ]
        ]
        non_protocol_conformance["conformance_plan"]["git_causality"] = {
            "applies": False,
            "rationale": "The scoped local regression claim does not depend on Git-history causality.",
            "claims": [],
        }
        for case in non_protocol_conformance["conformance_plan"]["cases"]:
            case["dimension_ids"] = ["local-architecture-regression"]
        non_protocol_conformance["scope_fingerprint"] = (
            _delivery_art_projection_digest(
                _architecture_scope_projection(non_protocol_conformance)
            )
        )
        require_accepted(
            "architecture_packet",
            non_protocol_conformance,
            "non-protocol architecture packet with a scoped conformance dimension",
        )

        resolved_without_resolution = copy.deepcopy(architecture)
        resolved_without_resolution["architecture"][
            "contradictions_open_decisions"
        ][0]["resolution"] = None
        require_rejected(
            "architecture_packet",
            resolved_without_resolution,
            "resolved architecture decision without a resolution",
        )

        unknown_dag_endpoint = copy.deepcopy(architecture)
        unknown_dag_endpoint["architecture"]["dependency_merge_dag"]["edges"][0][
            "to"
        ] = "work-item-999"
        require_rejected(
            "architecture_packet",
            unknown_dag_endpoint,
            "architecture dependency edge with an unknown endpoint",
        )

        cyclic_dag = copy.deepcopy(architecture)
        cyclic_dag["architecture"]["dependency_merge_dag"]["edges"].append(
            {
                "from": "work-item-802",
                "to": "work-item-801",
                "relation": "must_merge_before",
            }
        )
        require_rejected(
            "architecture_packet",
            cyclic_dag,
            "cyclic architecture dependency graph",
            "architecture-structure-invalid",
        )

        cyclic_parent_map = copy.deepcopy(architecture)
        cyclic_parent_map["architecture"]["descendant_owner_map"][0][
            "parent_work_item_id"
        ] = "work-item-802"
        require_rejected(
            "architecture_packet",
            cyclic_parent_map,
            "cyclic architecture descendant parent map without a root",
        )

        reversed_merge_order = copy.deepcopy(architecture)
        reversed_merge_order["architecture"]["dependency_merge_dag"][
            "merge_order"
        ].reverse()
        require_rejected(
            "architecture_packet",
            reversed_merge_order,
            "architecture merge order that violates cross-repo dependency precedence",
        )

        valid_depends_on_order = copy.deepcopy(architecture)
        valid_depends_on_order["architecture"]["dependency_merge_dag"]["edges"] = [
            {
                "from": "work-item-802",
                "to": "work-item-801",
                "relation": "depends_on",
            }
        ]
        valid_depends_on_order["scope_fingerprint"] = (
            _delivery_art_projection_digest(
                _architecture_scope_projection(valid_depends_on_order)
            )
        )
        require_accepted(
            "architecture_packet",
            valid_depends_on_order,
            "depends_on relation with dependency owner first in merge order",
        )

        invalid_depends_on_order = copy.deepcopy(architecture)
        invalid_depends_on_order["architecture"]["dependency_merge_dag"]["edges"] = [
            {
                "from": "work-item-801",
                "to": "work-item-802",
                "relation": "depends_on",
            }
        ]
        require_rejected(
            "architecture_packet",
            invalid_depends_on_order,
            "depends_on relation with dependent owner first in merge order",
        )

        unrelated_source_snapshot = copy.deepcopy(architecture)
        unrelated_source_snapshot["source_snapshot"]["repo_revisions"] = [
            {
                "repo": "unrelated-repo",
                "base_ref": "origin/main",
                "commit": "3" * 40,
            }
        ]
        require_rejected(
            "architecture_packet",
            unrelated_source_snapshot,
            "architecture source snapshot that omits declared owner repos",
        )

        duplicate_snapshot_owner = copy.deepcopy(architecture)
        duplicate_snapshot_owner["source_snapshot"]["repo_revisions"].append(
            {
                "repo": "workspace-governance",
                "base_ref": "origin/release",
                "commit": "4" * 40,
            }
        )
        require_rejected(
            "architecture_packet",
            duplicate_snapshot_owner,
            "architecture source snapshot with duplicate owner repo revisions",
        )

        undeclared_lifecycle_state = copy.deepcopy(architecture)
        undeclared_lifecycle_state["architecture"]["lifecycle_state_model"][
            "transitions"
        ][0]["to"] = "untracked-state"
        require_rejected(
            "architecture_packet",
            undeclared_lifecycle_state,
            "architecture lifecycle transition with an undeclared endpoint",
        )

        decision_before_snapshot = copy.deepcopy(architecture)
        decision_before_snapshot["decision"]["decided_at"] = (
            "2026-08-08T09:50:00+08:00"
        )
        require_rejected(
            "architecture_packet",
            decision_before_snapshot,
            "architecture decision recorded before its source snapshot",
        )

        missing_architecture_persistence_time = copy.deepcopy(architecture)
        missing_architecture_persistence_time["custody"]["persisted_at"] = None
        require_rejected(
            "architecture_packet",
            missing_architecture_persistence_time,
            "durable architecture packet without a persistence timestamp",
        )

        duplicate_conformance_case = copy.deepcopy(architecture)
        duplicate_conformance_case["conformance_plan"]["cases"][1]["id"] = (
            duplicate_conformance_case["conformance_plan"]["cases"][0]["id"]
        )
        require_rejected(
            "architecture_packet",
            duplicate_conformance_case,
            "architecture conformance plan with duplicate case ids",
        )

        unscoped_conformance_case = copy.deepcopy(architecture)
        unscoped_conformance_case["conformance_plan"]["cases"][0][
            "applies_to_work_item_ids"
        ] = ["work-item-999"]
        require_rejected(
            "architecture_packet",
            unscoped_conformance_case,
            "architecture conformance case scoped outside packet coverage",
        )

        incomplete_conformance_coverage = copy.deepcopy(architecture)
        for case in incomplete_conformance_coverage["conformance_plan"]["cases"]:
            case["applies_to_work_item_ids"] = ["work-item-801"]
        require_rejected(
            "architecture_packet",
            incomplete_conformance_coverage,
            "required conformance plan that omits a covered work item",
        )

        arbitrary_architecture_fingerprint = copy.deepcopy(architecture)
        arbitrary_architecture_fingerprint["scope_fingerprint"] = (
            "sha256:" + "9" * 64
        )
        require_rejected(
            "architecture_packet",
            arbitrary_architecture_fingerprint,
            "architecture packet with an arbitrary scope fingerprint",
            expected_fragment="deterministic architecture scope projection",
        )

        missing_work_item_dimension_polarity = copy.deepcopy(architecture)
        for case in missing_work_item_dimension_polarity["conformance_plan"][
            "cases"
        ]:
            if (
                case["polarity"] == "negative"
                and "shared-validator-compatibility" in case["dimension_ids"]
            ):
                case["dimension_ids"].remove("shared-validator-compatibility")
        require_rejected(
            "architecture_packet",
            missing_work_item_dimension_polarity,
            "conformance plan missing one work-item/dimension polarity",
            expected_fragment="work-item/dimension pair",
        )

        synthetic_git_causality = copy.deepcopy(architecture)
        for case in synthetic_git_causality["conformance_plan"]["cases"]:
            if case["id"].startswith("case:real-git"):
                case["fidelity"] = "filesystem"
        require_rejected(
            "architecture_packet",
            synthetic_git_causality,
            "Git-causality claim backed only by synthetic filesystem cases",
            expected_fragment="real-git merge-ready cases",
        )

        duplicate_git_claim_id = copy.deepcopy(architecture)
        duplicate_git_claim_id["conformance_plan"]["git_causality"][
            "claims"
        ].append(
            copy.deepcopy(
                duplicate_git_claim_id["conformance_plan"]["git_causality"][
                    "claims"
                ][0]
            )
        )
        require_rejected(
            "architecture_packet",
            duplicate_git_claim_id,
            "duplicate Git-causality claim ids",
            expected_fragment="unique ids",
        )

        draft_architecture = copy.deepcopy(architecture)
        draft_architecture["decision"]["status"] = "draft"
        draft_architecture["decision"]["decided_by"] = None
        draft_architecture["decision"]["decided_at"] = None
        draft_architecture["custody"] = {
            "state": "local-draft",
            "backend": "local-filesystem",
            "uri": ".art/drafts/architecture-packet-delivery-698-v1.json",
            "receipt_ref": None,
            "persisted_at": None,
            "supersedes": None,
        }
        draft_architecture["scope_fingerprint"] = (
            _delivery_art_projection_digest(
                _architecture_scope_projection(draft_architecture)
            )
        )
        require_accepted(
            "architecture_packet",
            draft_architecture,
            "local architecture draft without durable persistence claims",
        )

        approved_architecture_candidate = copy.deepcopy(architecture)
        approved_architecture_candidate["custody"] = {
            "state": "local-draft",
            "backend": "local-filesystem",
            "uri": ".art/drafts/architecture-packet-delivery-698-approved.json",
            "receipt_ref": None,
            "persisted_at": None,
            "supersedes": None,
        }
        require_accepted(
            "architecture_packet",
            approved_architecture_candidate,
            "approved local architecture candidate before durable persistence",
        )

        approved_candidate_with_persistence = copy.deepcopy(
            approved_architecture_candidate
        )
        approved_candidate_with_persistence["custody"]["persisted_at"] = (
            "2026-08-08T10:06:00+08:00"
        )
        require_rejected(
            "architecture_packet",
            approved_candidate_with_persistence,
            "approved local architecture candidate claiming persistence",
        )

        draft_architecture_with_persistence = copy.deepcopy(draft_architecture)
        draft_architecture_with_persistence["custody"]["persisted_at"] = (
            "2026-08-08T10:06:00+08:00"
        )
        require_rejected(
            "architecture_packet",
            draft_architecture_with_persistence,
            "local architecture draft claiming a persistence timestamp",
        )

        unresolved_supersedes = copy.deepcopy(architecture)
        unresolved_supersedes["custody"]["supersedes"] = {
            "uri": "wgcf://artifacts/delivery-art/sha256/" + "9" * 64,
            "digest": "sha256:" + "9" * 64,
        }
        require_reference_rejected(
            unresolved_supersedes,
            "architecture correction with an unresolved superseded artifact",
            "custody.supersedes.uri does not resolve",
            [],
            "reference-chain-invalid",
        )

    work_start = fixtures.get("work-start-record.valid.json")
    if work_start and architecture:
        local_dependency = copy.deepcopy(approved_architecture_candidate)
        local_dependency_digest = _artifact_object(
            local_dependency.get("integrity")
        ).get("content_digest")
        local_dependency["custody"]["uri"] = (
            "local://delivery-art/sha256/"
            + str(local_dependency_digest).removeprefix("sha256:")
            + "/architecture.json"
        )
        work_start_with_local_architecture = copy.deepcopy(work_start)
        work_start_with_local_architecture["architecture"]["packet_ref"] = (
            local_dependency["custody"]["uri"]
        )
        work_start_with_local_architecture["architecture"]["packet_digest"] = (
            local_dependency_digest
        )
        require_reference_rejected(
            work_start_with_local_architecture,
            "work-start record resolving an approved but unpersisted architecture candidate",
            "must resolve to a durable WGCF artifact",
            [local_dependency],
        )

        missing_split_reason = copy.deepcopy(work_start)
        missing_split_reason["landing_unit"]["split_reason"] = None
        require_rejected(
            "work_start_record",
            missing_split_reason,
            "isolated Landing Unit without a split reason",
            "work-start-invalid",
        )

        inexact_base = copy.deepcopy(work_start)
        inexact_base["landing_unit"]["branch_plan"][0]["base_commit"] = "main"
        require_rejected(
            "work_start_record",
            inexact_base,
            "work-start record without an exact base commit",
        )

        mismatched_owner = copy.deepcopy(work_start)
        mismatched_owner["landing_unit"]["owner_repos"] = ["unrelated-repo"]
        require_rejected(
            "work_start_record",
            mismatched_owner,
            "work-start owner repo not represented by branch and snapshot truth",
        )

        mismatched_base_ref = copy.deepcopy(work_start)
        mismatched_base_ref["landing_unit"]["branch_plan"][0][
            "base_ref"
        ] = "origin/release"
        require_rejected(
            "work_start_record",
            mismatched_base_ref,
            "work-start branch base ref that differs from its source snapshot",
        )

        mismatched_base_commit = copy.deepcopy(work_start)
        mismatched_base_commit["landing_unit"]["branch_plan"][0][
            "base_commit"
        ] = "2" * 40
        require_rejected(
            "work_start_record",
            mismatched_base_commit,
            "work-start branch base commit that differs from its source snapshot",
        )

        missing_persistence_time = copy.deepcopy(work_start)
        missing_persistence_time["custody"]["persisted_at"] = None
        require_rejected(
            "work_start_record",
            missing_persistence_time,
            "durable work-start record without a persistence timestamp",
        )

        incomplete_invalidation_set = copy.deepcopy(work_start)
        incomplete_invalidation_set["invalidation_inputs"].pop()
        require_rejected(
            "work_start_record",
            incomplete_invalidation_set,
            "implementation-ready work-start record with an incomplete invalidation set",
        )

        arbitrary_work_start_fingerprint = copy.deepcopy(work_start)
        arbitrary_work_start_fingerprint["scope_fingerprint"] = (
            "sha256:" + "9" * 64
        )
        require_rejected(
            "work_start_record",
            arbitrary_work_start_fingerprint,
            "work-start record with an arbitrary scope fingerprint",
            expected_fragment="deterministic work-start scope projection",
        )

        blocked_architecture = copy.deepcopy(work_start)
        blocked_architecture["landing_unit"]["decision"] = "defer_decision_blocked"
        blocked_architecture["landing_unit"]["branch_plan"] = []
        blocked_architecture["landing_unit"]["planned_review_packet_ref"] = None
        blocked_architecture["architecture"] = {
            "required": True,
            "packet_ref": None,
            "packet_digest": None,
            "readiness": "blocked",
        }
        blocked_architecture["readiness"] = {
            "level": "blocked",
            "evaluated_at": "2026-08-08T10:10:00+08:00",
            "blockers": ["Architecture decision remains unresolved."],
        }
        blocked_architecture["scope_fingerprint"] = (
            _delivery_art_projection_digest(
                _work_start_scope_projection(blocked_architecture)
            )
        )
        require_accepted(
            "work_start_record",
            blocked_architecture,
            "required architecture represented as a durable blocked work-start record",
        )

        blocked_without_persistence_time = copy.deepcopy(blocked_architecture)
        blocked_without_persistence_time["custody"]["persisted_at"] = None
        require_rejected(
            "work_start_record",
            blocked_without_persistence_time,
            "durable blocked work-start record without a persistence timestamp",
        )

        blocked_without_reason = copy.deepcopy(blocked_architecture)
        blocked_without_reason["readiness"]["blockers"] = []
        require_rejected(
            "work_start_record",
            blocked_without_reason,
            "blocked work-start record without an identified blocker",
        )

        blocked_architecture_with_invented_refs = copy.deepcopy(
            blocked_architecture
        )
        blocked_architecture_with_invented_refs["architecture"]["packet_ref"] = (
            "wgcf://artifacts/delivery-art/sha256/" + "7" * 64
        )
        blocked_architecture_with_invented_refs["architecture"][
            "packet_digest"
        ] = "sha256:" + "7" * 64
        require_rejected(
            "work_start_record",
            blocked_architecture_with_invented_refs,
            "blocked architecture substate with invented packet references",
        )

        unrelated_blocker_after_architecture_ready = copy.deepcopy(work_start)
        unrelated_blocker_after_architecture_ready["readiness"] = {
            "level": "blocked",
            "evaluated_at": "2026-08-08T10:10:00+08:00",
            "blockers": ["Operator approval remains pending."],
        }
        require_accepted(
            "work_start_record",
            unrelated_blocker_after_architecture_ready,
            "overall blocked record retaining exact architecture-ready refs",
        )

        architecture_ready_without_refs = copy.deepcopy(
            unrelated_blocker_after_architecture_ready
        )
        architecture_ready_without_refs["architecture"]["packet_ref"] = None
        architecture_ready_without_refs["architecture"]["packet_digest"] = None
        require_rejected(
            "work_start_record",
            architecture_ready_without_refs,
            "architecture-ready substate without packet references",
        )

        evaluation_before_snapshot = copy.deepcopy(work_start)
        evaluation_before_snapshot["readiness"]["evaluated_at"] = (
            "2026-08-08T10:08:00+08:00"
        )
        require_rejected(
            "work_start_record",
            evaluation_before_snapshot,
            "work-start evaluation recorded before its source snapshot",
        )

        require_reference_rejected(
            work_start,
            "work-start record without its referenced architecture packet",
            "does not resolve",
            [],
        )

        future_architecture = copy.deepcopy(architecture)
        future_architecture["decision"]["decided_at"] = (
            "2026-08-08T10:20:00+08:00"
        )
        future_architecture["custody"]["persisted_at"] = (
            "2026-08-08T10:21:00+08:00"
        )
        require_reference_rejected(
            work_start,
            "work-start record depending on a future architecture decision",
            "resolved architecture decision.decided_at must not be later",
            [future_architecture],
        )

        deferred_with_source_plan = copy.deepcopy(blocked_architecture)
        deferred_with_source_plan["landing_unit"]["branch_plan"] = copy.deepcopy(
            work_start["landing_unit"]["branch_plan"]
        )
        require_rejected(
            "work_start_record",
            deferred_with_source_plan,
            "deferred Landing Unit decision with a source branch plan",
        )

    merge_ready = fixtures.get("review-packet-merge-ready.valid.json")
    if merge_ready and work_start and architecture:
        failed_test = copy.deepcopy(merge_ready)
        failed_test["evidence"]["tests"][0]["result"] = "fail"
        require_rejected(
            "review_packet",
            failed_test,
            "merge-ready Review Packet with failed evidence",
            "review-evidence-invalid",
        )

        prose_result = copy.deepcopy(merge_ready)
        prose_result["evidence"]["tests"] = [
            "PASS: a result prefix is not structured evidence"
        ]
        require_rejected(
            "review_packet",
            prose_result,
            "Review Packet with prose result strings",
        )

        missing_mapping = copy.deepcopy(merge_ready)
        missing_mapping["evidence"]["acceptance_mapping"] = []
        require_rejected(
            "review_packet",
            missing_mapping,
            "Review Packet without item acceptance mapping",
        )

        partial_mapping = copy.deepcopy(merge_ready)
        partial_mapping["covered_work_item_ids"].append("work-item-802")
        require_rejected(
            "review_packet",
            partial_mapping,
            "Review Packet whose acceptance mapping covers only some work items",
        )

        unknown_evidence = copy.deepcopy(merge_ready)
        unknown_evidence["evidence"]["acceptance_mapping"][0][
            "evidence_ids"
        ].append("evidence:missing")
        require_rejected(
            "review_packet",
            unknown_evidence,
            "Review Packet acceptance mapping with an unknown evidence reference",
        )

        duplicate_evidence_id = copy.deepcopy(merge_ready)
        duplicate_evidence_id["evidence"]["validations"][0]["id"] = (
            duplicate_evidence_id["evidence"]["tests"][0]["id"]
        )
        require_rejected(
            "review_packet",
            duplicate_evidence_id,
            "Review Packet with duplicate ids across evidence sections",
        )

        unexplained_not_applicable = copy.deepcopy(merge_ready)
        unexplained_not_applicable["evidence"]["security_and_trust"][0][
            "authority_ref"
        ] = None
        require_rejected(
            "review_packet",
            unexplained_not_applicable,
            "not-applicable evidence without an authority ref",
        )

        mismatched_review_base = copy.deepcopy(merge_ready)
        mismatched_review_base["landing_unit"]["repos"][0]["base_commit"] = (
            "9" * 40
        )
        require_reference_rejected(
            mismatched_review_base,
            "Review Packet base commit diverging from work-start truth",
            "base_commit",
        )

        mismatched_review_decision = copy.deepcopy(merge_ready)
        mismatched_review_decision["landing_unit"]["decision"] = (
            "feature_single_landing_unit"
        )
        require_reference_rejected(
            mismatched_review_decision,
            "Review Packet Landing Unit decision diverging from work-start truth",
            "Landing Unit decision",
        )

        mismatched_review_coverage = copy.deepcopy(merge_ready)
        mismatched_review_coverage["covered_work_item_ids"].append(
            "work-item-802"
        )
        mismatched_review_coverage["evidence"]["acceptance_mapping"].append(
            {
                "work_item_id": "work-item-802",
                "acceptance_ref": "openproject://work_packages/802",
                "evidence_ids": ["evidence:contract-model"],
                "summary": "Synthetic complete mapping used to exercise reference continuity.",
            }
        )
        require_reference_rejected(
            mismatched_review_coverage,
            "Review Packet coverage diverging from work-start truth",
            "covered_work_item_ids",
        )

        mismatched_scope_fingerprint = copy.deepcopy(merge_ready)
        mismatched_scope_fingerprint["work_start"]["scope_fingerprint"] = (
            "sha256:" + "9" * 64
        )
        require_reference_rejected(
            mismatched_scope_fingerprint,
            "Review Packet scope diverging from work-start truth",
            "scope_fingerprint",
        )

        future_work_start_persistence = copy.deepcopy(work_start)
        future_work_start_persistence["custody"]["persisted_at"] = (
            "2026-08-08T11:10:00+08:00"
        )
        require_reference_rejected(
            merge_ready,
            "Review Packet depending on a work-start record persisted in the future",
            "resolved work-start custody.persisted_at must not be later",
            [architecture, future_work_start_persistence],
        )

        missing_conformance_results = copy.deepcopy(merge_ready)
        missing_conformance_results["evidence"]["tests"][0][
            "conformance_case_ids"
        ] = []
        require_reference_rejected(
            missing_conformance_results,
            "Review Packet without applicable architecture conformance results",
            "missing applicable conformance case results",
        )

        wrong_conformance_fidelity = copy.deepcopy(merge_ready)
        wrong_conformance_fidelity["evidence"]["tests"][0]["fidelity"] = (
            "pure-unit"
        )
        require_reference_rejected(
            wrong_conformance_fidelity,
            "Review Packet conformance result below planned fidelity",
            "planned fidelity",
        )

        out_of_scope_conformance_case = copy.deepcopy(merge_ready)
        out_of_scope_conformance_case["evidence"]["validations"][0][
            "conformance_case_ids"
        ] = ["case:real-git-positive"]
        require_reference_rejected(
            out_of_scope_conformance_case,
            "Review Packet claiming a different work item's conformance case",
            "outside its work-item or readiness scope",
        )

        stale_evidence_source_head = copy.deepcopy(merge_ready)
        stale_evidence_source_head["evidence"]["tests"][0]["source_revisions"][
            0
        ]["commit"] = "2" * 40
        require_rejected(
            "review_packet",
            stale_evidence_source_head,
            "passing evidence bound to a stale source head",
            expected_fragment="exact landing-unit source heads",
        )

        valid_merge_ready_direct_land = copy.deepcopy(merge_ready)
        valid_merge_ready_direct_land["landing_unit"]["evidence_kind"] = (
            "approved_direct_land"
        )
        valid_merge_ready_direct_land["landing_unit"]["repos"][0]["pr_url"] = None
        valid_merge_ready_direct_land["exceptions"] = [
            {
                "id": "exception:direct-land-work-item-801",
                "kind": "direct-land",
                "authority_ref": "openproject://work_packages/801",
                "rationale": "The operator approved this bounded source landing without a pull request.",
                "expires_at": "2026-08-08T12:00:00+08:00",
            }
        ]
        require_accepted(
            "review_packet",
            valid_merge_ready_direct_land,
            "merge-ready direct-land Review Packet with current exception authority",
        )

        direct_land_with_pr = copy.deepcopy(valid_merge_ready_direct_land)
        direct_land_with_pr["landing_unit"]["repos"][0]["pr_url"] = (
            "https://github.com/mfshaf7/workspace-governance/pull/136"
        )
        require_rejected(
            "review_packet",
            direct_land_with_pr,
            "direct-land Review Packet that also claims pull-request evidence",
        )

        local_packet_with_persistence = copy.deepcopy(merge_ready)
        local_packet_with_persistence["custody"]["state"] = "local-draft"
        local_packet_with_persistence["custody"]["backend"] = "local-filesystem"
        local_packet_with_persistence["custody"]["uri"] = (
            ".art/review-packet-merge-ready.json"
        )
        local_packet_with_persistence["custody"]["persisted_at"] = (
            "2026-08-08T11:16:00+08:00"
        )
        require_rejected(
            "review_packet",
            local_packet_with_persistence,
            "local Review Packet claiming a persistence timestamp",
        )

    readiness_receipt = fixtures.get("readiness-receipt.valid.json")
    if readiness_receipt:
        def readiness_receipt_for(
            subject_artifact: dict,
            level: str,
            evaluated_at: str,
            persisted_at: str,
        ) -> dict:
            receipt = copy.deepcopy(readiness_receipt)
            subject_artifact_type = subject_artifact.get("artifact_type")
            subject_artifact_id = (
                subject_artifact.get("packet_id")
                if subject_artifact_type == "art_review_packet"
                else subject_artifact.get("artifact_id")
            )
            receipt["covered_work_item_ids"] = copy.deepcopy(
                subject_artifact.get("covered_work_item_ids")
            )
            receipt["subject"] = {
                "artifact_type": subject_artifact_type,
                "artifact_id": subject_artifact_id,
                "digest_kind": "artifact-content",
                "digest": _artifact_object(subject_artifact.get("integrity")).get(
                    "content_digest"
                ),
            }
            receipt["readiness"]["level"] = level
            receipt["readiness"]["outcome"] = "ready"
            receipt["readiness"]["mutation_allowed"] = True
            receipt["readiness"]["evaluated_at"] = evaluated_at
            receipt["findings"] = []
            receipt["custody"]["persisted_at"] = persisted_at

            digest_projection = _delivery_art_content_digest_projection(receipt)
            content_digest = _delivery_art_projection_digest(digest_projection)
            receipt["integrity"]["content_digest"] = content_digest
            receipt_token = receipt["receipt_id"].split(":", 1)[1]
            receipt["custody"]["uri"] = (
                "wgcf://receipts/art-readiness/art-readiness-receipt-"
                f"{receipt_token}-{content_digest.removeprefix('sha256:')}.json"
            )
            return receipt

        receipt_level_cases = []
        if architecture:
            receipt_level_cases.append(
                (
                    "architecture-ready",
                    readiness_receipt_for(
                        architecture,
                        "architecture-ready",
                        "2026-08-08T10:07:00+08:00",
                        "2026-08-08T10:08:00+08:00",
                    ),
                    architecture,
                )
            )
        if work_start:
            receipt_level_cases.append(
                (
                    "implementation-ready",
                    readiness_receipt_for(
                        work_start,
                        "implementation-ready",
                        "2026-08-08T10:12:00+08:00",
                        "2026-08-08T10:13:00+08:00",
                    ),
                    work_start,
                )
            )
        if merge_ready:
            receipt_level_cases.append(
                (
                    "merge-ready",
                    readiness_receipt_for(
                        merge_ready,
                        "merge-ready",
                        "2026-08-08T11:17:00+08:00",
                        "2026-08-08T11:18:00+08:00",
                    ),
                    merge_ready,
                )
            )
        for level, receipt_case, subject_artifact in receipt_level_cases:
            require_fully_accepted(
                "readiness_receipt",
                receipt_case,
                f"{level} receipt bound to its exact durable subject",
                [subject_artifact],
            )

        if architecture:
            wrong_level_subject = readiness_receipt_for(
                architecture,
                "architecture-ready",
                "2026-08-08T10:07:00+08:00",
                "2026-08-08T10:08:00+08:00",
            )
            wrong_level_subject["readiness"]["level"] = "implementation-ready"
            require_rejected(
                "readiness_receipt",
                wrong_level_subject,
                "receipt readiness level paired with the wrong artifact type",
            )

            mismatched_receipt_coverage = readiness_receipt_for(
                architecture,
                "architecture-ready",
                "2026-08-08T10:07:00+08:00",
                "2026-08-08T10:08:00+08:00",
            )
            mismatched_receipt_coverage["covered_work_item_ids"] = [
                "work-item-801"
            ]
            require_reference_rejected(
                mismatched_receipt_coverage,
                "readiness receipt with partial subject coverage",
                "coverage must match",
                [architecture],
            )

            premature_receipt = readiness_receipt_for(
                architecture,
                "architecture-ready",
                "2026-08-08T10:05:30+08:00",
                "2026-08-08T10:08:00+08:00",
            )
            require_reference_rejected(
                premature_receipt,
                "readiness receipt evaluated before durable subject custody",
                "must not be later than readiness receipt evaluation",
                [architecture],
            )

        source_artifact_claimed_as_receipt = copy.deepcopy(readiness_receipt)
        source_artifact_claimed_as_receipt["artifact_type"] = (
            "art_review_packet"
        )
        require_rejected(
            "readiness_receipt",
            source_artifact_claimed_as_receipt,
            "WGCF receipt custody claiming a source artifact type",
            "readiness-receipt-invalid",
        )

        ready_receipt_with_error = copy.deepcopy(readiness_receipt)
        ready_receipt_with_error["findings"] = [
            {
                "id": "finding:unexpected-error",
                "severity": "error",
                "summary": "A required readiness check failed.",
                "authority_ref": "openproject://work_packages/803",
            }
        ]
        require_rejected(
            "readiness_receipt",
            ready_receipt_with_error,
            "ready receipt containing an error finding",
            expected_fragment="must not contain blocker or error findings",
        )

        blocked_receipt_without_finding = copy.deepcopy(readiness_receipt)
        blocked_receipt_without_finding["readiness"]["outcome"] = "blocked"
        blocked_receipt_without_finding["readiness"]["mutation_allowed"] = False
        require_rejected(
            "readiness_receipt",
            blocked_receipt_without_finding,
            "blocked receipt without an actionable finding",
            expected_fragment="must identify at least one finding",
        )

        duplicate_finding_ids = copy.deepcopy(blocked_receipt_without_finding)
        duplicate_finding_ids["findings"] = [
            {
                "id": "finding:duplicate",
                "severity": "blocker",
                "summary": "The first readiness condition failed.",
                "authority_ref": "openproject://work_packages/803",
            },
            {
                "id": "finding:duplicate",
                "severity": "warning",
                "summary": "A second condition uses the same identifier.",
                "authority_ref": "openproject://work_packages/805",
            },
        ]
        require_rejected(
            "readiness_receipt",
            duplicate_finding_ids,
            "readiness receipt with ambiguous finding ids",
            expected_fragment="finding ids must be unique",
        )

        blocked_with_warning_only = copy.deepcopy(blocked_receipt_without_finding)
        blocked_with_warning_only["findings"] = [
            {
                "id": "finding:warning-only",
                "severity": "warning",
                "summary": "The evaluation produced only an advisory warning.",
                "authority_ref": "openproject://work_packages/803",
            }
        ]
        require_rejected(
            "readiness_receipt",
            blocked_with_warning_only,
            "blocked receipt supported only by an advisory warning",
            expected_fragment="blocker or error finding",
        )

    finalized = fixtures.get("review-packet-finalized.valid.json")
    if (
        finalized
        and architecture
        and work_start
        and merge_ready
        and readiness_receipt
    ):
        readiness_subject_digest = (
            delivery_art_review_packet_readiness_subject_digest(finalized)
        )
        terminal_time_variant = copy.deepcopy(finalized)
        terminal_time_variant["readiness"]["evaluated_at"] = (
            "2026-08-08T11:31:00+08:00"
        )
        terminal_time_variant["finalized_at"] = "2026-08-08T11:34:00+08:00"
        if (
            delivery_art_review_packet_readiness_subject_digest(
                terminal_time_variant
            )
            != readiness_subject_digest
        ):
            errors.append(
                "Review Packet readiness-subject digest must exclude terminal timestamps"
            )

        semantic_variant = copy.deepcopy(finalized)
        semantic_variant["landing_unit"]["rollback_boundary"] = (
            "A materially different rollback boundary."
        )
        if (
            delivery_art_review_packet_readiness_subject_digest(semantic_variant)
            == readiness_subject_digest
        ):
            errors.append(
                "Review Packet readiness-subject digest must bind final semantic content"
            )

        malformed_receipt_subject = copy.deepcopy(finalized)
        malformed_receipt_subject["schema_version"] = 2.0
        require_reference_rejected(
            readiness_receipt,
            "readiness receipt with a non-canonical subject artifact",
            "subject does not resolve",
            [malformed_receipt_subject],
        )

        require_reference_rejected(
            finalized,
            "finalized Review Packet without its readiness receipt dependency",
            "readiness.receipt_refs.uri does not resolve",
            [architecture, work_start, merge_ready],
        )

        require_reference_rejected(
            finalized,
            "finalized source Review Packet without its merge-ready predecessor",
            "custody.supersedes.uri does not resolve",
            [architecture, work_start, readiness_receipt],
        )

        rewritten_final_evidence = copy.deepcopy(finalized)
        rewritten_final_evidence["evidence"]["tests"][0]["summary"] = (
            "Rewritten after merge instead of preserving reviewed evidence."
        )
        require_reference_rejected(
            rewritten_final_evidence,
            "finalized Review Packet that rewrites merge-ready evidence",
            "must preserve merge-ready evidence",
        )

        mismatched_receipt_subject = copy.deepcopy(readiness_receipt)
        mismatched_receipt_subject["subject"]["digest"] = (
            "sha256:" + "9" * 64
        )
        require_reference_rejected(
            finalized,
            "finalized Review Packet with a receipt for another subject",
            "subject digest must match",
            [architecture, work_start, merge_ready, mismatched_receipt_subject],
        )

        non_ready_receipt = copy.deepcopy(readiness_receipt)
        non_ready_receipt["readiness"]["outcome"] = "blocked"
        non_ready_receipt["readiness"]["mutation_allowed"] = False
        non_ready_receipt["findings"] = [
            {
                "id": "finding:blocked",
                "severity": "blocker",
                "summary": "Operating readiness remains blocked.",
                "authority_ref": "openproject://work_packages/803",
            }
        ]
        require_reference_rejected(
            finalized,
            "finalized Review Packet with a non-ready receipt",
            "requires a ready receipt",
            [architecture, work_start, merge_ready, non_ready_receipt],
        )

        late_readiness_receipt = copy.deepcopy(readiness_receipt)
        late_readiness_receipt["custody"]["persisted_at"] = (
            "2026-08-08T11:32:01+08:00"
        )
        require_reference_rejected(
            finalized,
            "finalized Review Packet whose readiness receipt was persisted later",
            "must not be later than Review Packet finalized_at",
            [architecture, work_start, merge_ready, late_readiness_receipt],
        )

        cyclic_merge_ready = copy.deepcopy(merge_ready)
        cyclic_merge_ready["custody"]["supersedes"] = {
            "uri": finalized["custody"]["uri"],
            "digest": finalized["integrity"]["content_digest"],
        }
        require_reference_rejected(
            finalized,
            "cyclic Review Packet supersession chain",
            "must be acyclic",
            [architecture, work_start, cyclic_merge_ready, readiness_receipt],
        )

        redirected_final_predecessor = copy.deepcopy(finalized)
        redirected_final_predecessor["custody"]["supersedes"]["digest"] = (
            "sha256:" + "9" * 64
        )
        require_integrity_error(
            redirected_final_predecessor,
            "finalized Review Packet with redirected predecessor metadata",
            "integrity.content_digest must equal canonical content digest",
        )

        local_final = copy.deepcopy(finalized)
        local_final["custody"]["state"] = "local-draft"
        local_final["custody"]["backend"] = "local-filesystem"
        require_rejected(
            "review_packet",
            local_final,
            "finalized Review Packet without durable custody",
        )

        missing_source_tests = copy.deepcopy(finalized)
        missing_source_tests["evidence"]["tests"] = []
        require_rejected(
            "review_packet",
            missing_source_tests,
            "source-backed finalized Review Packet without tests",
        )

        missing_readiness_receipt = copy.deepcopy(finalized)
        missing_readiness_receipt["readiness"]["receipt_refs"] = []
        require_rejected(
            "review_packet",
            missing_readiness_receipt,
            "finalized Review Packet without a readiness receipt",
        )

        valid_direct_land = copy.deepcopy(finalized)
        valid_direct_land["landing_unit"]["evidence_kind"] = (
            "approved_direct_land"
        )
        valid_direct_land["landing_unit"]["repos"][0]["pr_url"] = None
        valid_direct_land["exceptions"] = [
            {
                "id": "exception:direct-land-work-item-801",
                "kind": "direct-land",
                "authority_ref": "openproject://work_packages/801",
                "rationale": "The operator approved this bounded source landing without a pull request.",
                "expires_at": "2026-08-08T12:00:00+08:00",
            }
        ]
        valid_direct_land["readiness"]["subject_digest"] = (
            delivery_art_review_packet_readiness_subject_digest(valid_direct_land)
        )
        require_accepted(
            "review_packet",
            valid_direct_land,
            "finalized direct-land Review Packet with current exception authority",
        )

        direct_land_predecessor = copy.deepcopy(merge_ready)
        direct_land_predecessor["landing_unit"]["evidence_kind"] = (
            "approved_direct_land"
        )
        direct_land_predecessor["landing_unit"]["repos"][0]["pr_url"] = None
        direct_land_predecessor["exceptions"] = copy.deepcopy(
            valid_direct_land["exceptions"]
        )
        direct_land_receipt = copy.deepcopy(readiness_receipt)
        direct_land_receipt["subject"]["digest"] = valid_direct_land[
            "readiness"
        ]["subject_digest"]
        require_reference_accepted(
            valid_direct_land,
            "finalized direct-land packet preserving its merge-ready predecessor",
            [
                architecture,
                architecture_custody_receipt,
                work_start,
                work_start_custody_receipt,
                direct_land_predecessor,
                merge_ready_custody_receipt,
                direct_land_receipt,
                finalized_custody_receipt,
            ],
        )

        expired_direct_land = copy.deepcopy(valid_direct_land)
        expired_direct_land["exceptions"][0]["expires_at"] = (
            "2026-08-08T11:29:59+08:00"
        )
        expired_direct_land["readiness"]["subject_digest"] = (
            delivery_art_review_packet_readiness_subject_digest(expired_direct_land)
        )
        require_rejected(
            "review_packet",
            expired_direct_land,
            "finalized direct-land Review Packet with expired exception authority",
        )

        non_expiring_direct_land = copy.deepcopy(valid_direct_land)
        non_expiring_direct_land["exceptions"][0]["expires_at"] = None
        non_expiring_direct_land["readiness"]["subject_digest"] = (
            delivery_art_review_packet_readiness_subject_digest(
                non_expiring_direct_land
            )
        )
        require_rejected(
            "review_packet",
            non_expiring_direct_land,
            "finalized direct-land Review Packet without time-bound exception authority",
        )

        impossible_finalization_timeline = copy.deepcopy(finalized)
        impossible_finalization_timeline["created_at"] = (
            "2026-08-08T12:00:00+08:00"
        )
        require_rejected(
            "review_packet",
            impossible_finalization_timeline,
            "Review Packet created after evaluation and finalization",
        )

        floating_schema_version = copy.deepcopy(finalized)
        floating_schema_version["schema_version"] = 2.0
        require_integrity_error(
            floating_schema_version,
            "floating-point schema version",
            "floating-point value",
            "canonical-integrity-invalid",
        )

        lone_surrogate = copy.deepcopy(finalized)
        lone_surrogate["operator"]["id"] = "\ud800"
        require_integrity_error(
            lone_surrogate,
            "lone surrogate in operator identity",
            "lone UTF-16 surrogate",
        )

        non_source_with_source_evidence = copy.deepcopy(finalized)
        non_source_with_source_evidence["landing_unit"]["decision"] = (
            "non_source_child"
        )
        require_rejected(
            "review_packet",
            non_source_with_source_evidence,
            "non-source Review Packet with source landing evidence",
        )

        valid_non_source_packet = copy.deepcopy(finalized)
        valid_non_source_packet["landing_unit"]["decision"] = "non_source_child"
        valid_non_source_packet["landing_unit"]["evidence_kind"] = (
            "non_source_evidence"
        )
        valid_non_source_packet["landing_unit"]["repos"] = []
        valid_non_source_packet["evidence"]["changed_surfaces"] = []
        valid_non_source_packet["custody"]["supersedes"] = None
        valid_non_source_packet["evidence"]["acceptance_mapping"][0][
            "evidence_ids"
        ] = ["evidence:schema-negative-cases"]
        for section in (
            "tests",
            "validations",
            "runtime_and_live",
            "security_and_trust",
        ):
            for result in valid_non_source_packet["evidence"][section]:
                result["source_revisions"] = []
        valid_non_source_packet["readiness"]["subject_digest"] = (
            delivery_art_review_packet_readiness_subject_digest(
                valid_non_source_packet
            )
        )
        require_accepted(
            "review_packet",
            valid_non_source_packet,
            "finalized non-source Review Packet without source landing evidence",
        )

        duplicate_landing_repo = copy.deepcopy(finalized)
        duplicate_repo_entry = copy.deepcopy(
            duplicate_landing_repo["landing_unit"]["repos"][0]
        )
        duplicate_repo_entry["branch"] = "codex/duplicate-repo-entry"
        duplicate_landing_repo["landing_unit"]["repos"].append(
            duplicate_repo_entry
        )
        require_rejected(
            "review_packet",
            duplicate_landing_repo,
            "source Review Packet with duplicate repo evidence",
        )

        unbound_changed_surface = copy.deepcopy(finalized)
        unbound_changed_surface["evidence"]["changed_surfaces"][0][
            "path"
        ] = "contracts/unreported-surface.yaml"
        require_rejected(
            "review_packet",
            unbound_changed_surface,
            "changed surface absent from exact landing-unit changed files",
        )

    return executed_proof_cases


def validate_contract_format_checker(errors: list[str]) -> None:
    schema = {"type": "string", "format": "date-time"}
    validator = Draft202012Validator(
        schema,
        format_checker=CONTRACT_FORMAT_CHECKER,
    )
    for value in (
        "2026-08-01T00:00:00Z",
        "2026-08-01T08:00:00+08:00",
    ):
        if list(validator.iter_errors(value)):
            errors.append(
                f"shared date-time format checker must accept RFC 3339 timestamp {value!r}"
            )
    for value in (
        "2026-13-40T25:61:00Z",
        "2026-08-01T08:00:00",
    ):
        if not list(validator.iter_errors(value)):
            errors.append(
                f"shared date-time format checker must reject invalid timestamp {value!r}"
            )


def _delivery_art_true_claim_refs(operator_path: dict) -> set[str]:
    true_claims: set[str] = set()

    def walk(value: object, path: str) -> None:
        if value is True:
            true_claims.add(path)
        elif isinstance(value, dict):
            for key, entry in value.items():
                walk(entry, f"{path}.{key}")

    for root in DELIVERY_ART_PROOF_CLAIM_ROOTS:
        value: object = operator_path
        for part in root.split("."):
            if not isinstance(value, dict) or part not in value:
                value = None
                break
            value = value[part]
        if value is not None:
            walk(value, root)
    return true_claims


def delivery_art_proof_obligation_errors(
    operator_path: dict,
    executed_case_ids: set[str],
) -> list[str]:
    errors: list[str] = []
    proof_contract = _artifact_object(operator_path.get("proof_obligations"))
    declared_roots = tuple(
        _artifact_string_list(proof_contract.get("governed_claim_roots"))
    )
    if declared_roots != DELIVERY_ART_PROOF_CLAIM_ROOTS:
        errors.append("proof obligations must govern the canonical claim roots")

    obligations = _artifact_object_list(proof_contract.get("obligations"))
    obligation_ids = [
        obligation.get("id")
        for obligation in obligations
        if isinstance(obligation.get("id"), str)
    ]
    if len(obligation_ids) != len(set(obligation_ids)):
        errors.append("proof obligation ids must be unique")

    claims_to_obligations: dict[str, list[str]] = {}
    activation_targets = set(
        _artifact_string_list(
            _artifact_object(operator_path.get("contract_activation")).get(
                "target_art_items"
            )
        )
    )
    for obligation in obligations:
        obligation_id = str(obligation.get("id"))
        for claim_ref in _artifact_string_list(obligation.get("claim_refs")):
            claims_to_obligations.setdefault(claim_ref, []).append(obligation_id)
        state = obligation.get("enforcement_state")
        positive_cases = set(
            _artifact_string_list(obligation.get("positive_case_ids"))
        )
        negative_cases = set(
            _artifact_string_list(obligation.get("negative_case_ids"))
        )
        target_refs = set(
            _artifact_string_list(obligation.get("target_art_refs"))
        )
        if state == "active-local":
            missing_cases = (positive_cases | negative_cases) - executed_case_ids
            if missing_cases:
                errors.append(
                    f"proof obligation {obligation_id} references unexecuted validation cases: "
                    + ", ".join(sorted(missing_cases))
                )
            if not positive_cases or not negative_cases:
                errors.append(
                    f"proof obligation {obligation_id} requires positive and negative validation cases"
                )
        elif state == "pending-owner":
            if not target_refs:
                errors.append(
                    f"pending-owner proof obligation {obligation_id} requires target ART refs"
                )
            unknown_targets = target_refs - activation_targets
            if unknown_targets:
                errors.append(
                    f"pending-owner proof obligation {obligation_id} references targets outside contract activation: "
                    + ", ".join(sorted(unknown_targets))
                )
            if positive_cases or negative_cases:
                errors.append(
                    f"pending-owner proof obligation {obligation_id} must not claim local validation cases"
                )
        elif state == "doctrine" and (positive_cases or negative_cases or target_refs):
            errors.append(
                f"doctrine proof obligation {obligation_id} must not claim execution or target artifacts"
            )

    true_claims = _delivery_art_true_claim_refs(operator_path)
    mapped_claims = set(claims_to_obligations)
    missing_claims = true_claims - mapped_claims
    if missing_claims:
        errors.append(
            "proof obligations leave true claims unmapped: "
            + ", ".join(sorted(missing_claims))
        )
    unknown_claims = mapped_claims - true_claims
    if unknown_claims:
        errors.append(
            "proof obligations reference claims that are absent or not true: "
            + ", ".join(sorted(unknown_claims))
        )
    multiply_mapped = {
        claim_ref: obligation_ids
        for claim_ref, obligation_ids in claims_to_obligations.items()
        if len(obligation_ids) != 1
    }
    if multiply_mapped:
        errors.append(
            "proof claims must be mapped exactly once: "
            + ", ".join(sorted(multiply_mapped))
        )
    return errors


def validate_delivery_art_proof_obligations(
    errors: list[str],
    operator_path: dict,
    executed_case_ids: set[str],
) -> None:
    for error in delivery_art_proof_obligation_errors(
        operator_path, executed_case_ids
    ):
        errors.append(f"delivery-art-operator-path proof invariant: {error}")

    proof_contract = _artifact_object(operator_path.get("proof_obligations"))
    obligations = _artifact_object_list(proof_contract.get("obligations"))
    if len(obligations) < 2:
        return

    unmapped = copy.deepcopy(operator_path)
    unmapped["proof_obligations"]["obligations"][0]["claim_refs"].pop()
    if not any(
        "unmapped" in error
        for error in delivery_art_proof_obligation_errors(
            unmapped, executed_case_ids
        )
    ):
        errors.append("Delivery ART proof registry must reject an unmapped true claim")

    duplicate = copy.deepcopy(operator_path)
    duplicated_claim = duplicate["proof_obligations"]["obligations"][0][
        "claim_refs"
    ][0]
    duplicate["proof_obligations"]["obligations"][1]["claim_refs"].append(
        duplicated_claim
    )
    if not any(
        "mapped exactly once" in error
        for error in delivery_art_proof_obligation_errors(
            duplicate, executed_case_ids
        )
    ):
        errors.append(
            "Delivery ART proof registry must reject a multiply mapped true claim"
        )

    unexecuted = copy.deepcopy(operator_path)
    active_obligation = next(
        obligation
        for obligation in unexecuted["proof_obligations"]["obligations"]
        if obligation["enforcement_state"] == "active-local"
    )
    active_obligation["positive_case_ids"].append("case-never-executed")
    if not any(
        "unexecuted validation cases" in error
        for error in delivery_art_proof_obligation_errors(
            unexecuted, executed_case_ids
        )
    ):
        errors.append(
            "Delivery ART proof registry must reject an unexecuted validation case"
        )


def controlled_proof_authorization_fixture() -> dict:
    digest = "sha256:" + "a" * 64
    source_revision = "b" * 40
    scenario_executions = [
        {
            "scenario_id": scenario_id,
            "scenario_execution_id": f"scenario-execution:{index:02d}:{scenario_id}",
            "required_receipt_owners": CONTROLLED_PROOF_REQUIRED_RECEIPT_OWNER_ORDER,
        }
        for index, scenario_id in enumerate(
            CONTROLLED_PROOF_REQUIRED_SCENARIO_ORDER,
            start=1,
        )
    ]
    reviewed_source = {
        "owner_repo": "platform-engineering",
        "implementation_ref": "artifact://controlled-proof/source/permit-issuer",
        "source_revision": source_revision,
        "review_packet_ref": "artifact://review-packets/platform-source",
    }
    return {
        "schema_version": 3,
        "authorization_id": "artifact://controlled-proof/authorizations/validation-run",
        "authority_type": "runtime-drill",
        "drill_type": "component-commissioning-proof",
        "target": {
            "profile_id": "temporal-dev-integration",
            "profile_lifecycle": "build-admitted",
            "environment": "dev-integration",
        },
        "scope": {
            "allowed_definitions": [
                {
                    "definition_id": "validation-readiness-run",
                    "definition_version": 1,
                }
            ],
            "source_revisions": [
                {
                    "repo": "platform-engineering",
                    "commit": source_revision,
                }
            ],
            "runtime_artifacts": [
                {
                    "artifact_id": "temporal-runtime-contract",
                    "digest": digest,
                }
            ],
            "runtime_images": [
                {
                    "image_ref": "temporal-runtime",
                    "digest": digest,
                }
            ],
            "target_namespaces": ["devint-temporal"],
            "runtime_identities": [
                {
                    "role": "workflow-worker",
                    "identity": "oos-validation-readiness-worker",
                }
            ],
            "task_queues": [
                {
                    "owner_repo": "operator-orchestration-service",
                    "queue_name": "validation-readiness-run",
                }
            ],
            "permitted_actions": sorted(CONTROLLED_PROOF_PERMITTED_ACTIONS),
        },
        "commissioning_session": {
            "commissioning_session_id": "controlled-proof-validation-session",
            "consumption_mode": "atomic-single-use",
            "consume_before_first_mutation": True,
            "duplicate_consumption_denied": True,
            "scenario_executions": scenario_executions,
        },
        "permit_issuer": reviewed_source,
        "executor": {
            **reviewed_source,
            "implementation_ref": "artifact://controlled-proof/source/executor",
        },
        "approvals": {
            "issued_by": "platform-engineering",
            "canonicalization": "rfc8785",
            "canonical_claims_projection": "all-authorization-fields-except-approvals",
            "canonical_claims_digest": digest,
            "operator_approval_ref": "artifact://controlled-proof/approvals/operator",
            "operator_approval_digest": digest,
            "security_authorization_ref": "artifact://controlled-proof/approvals/security",
            "security_authorization_digest": digest,
        },
        "window": {
            "issued_at": "2026-08-01T00:00:00Z",
            "expires_at": "2026-08-01T01:00:00Z",
        },
        "evidence": {
            "owner_repo": "platform-engineering",
            "verification_pack_ref": "artifact://controlled-proof/evidence/validation-run",
        },
        "baseline_and_restore": {
            "baseline_snapshot_ref": "artifact://controlled-proof/baselines/pre-run",
            "baseline_snapshot_digest": digest,
            "restore_mode": "exact-baseline",
            "restore_scope": ["temporal-runtime", "oos-worker", "wgcf-worker"],
            "terminal_cleanup_authority": {
                "mode": "exact-baseline-restore-only",
                "applies_to": "already-started-commissioning-session",
                "trigger_scope": "any-triggered-stop-condition",
                "scope_binding": "exact-captured-restore-scope",
                "new_proof_actions_denied": True,
                "scope_expansion_denied": True,
                "runtime_retention_denied": True,
                "permitted_actions": CONTROLLED_PROOF_TERMINAL_CLEANUP_ACTIONS,
                "termination_conditions": (
                    CONTROLLED_PROOF_TERMINAL_CLEANUP_TERMINATION_CONDITIONS
                ),
            },
        },
        "exception_handling": {
            "allowed_decisions": ["remove", "workaround", "accept-risk", "defer"],
            "record_ref_required": True,
        },
        "stop_conditions": sorted(CONTROLLED_PROOF_REQUIRED_STOP_CONDITIONS),
    }


def controlled_proof_authorization_binding_errors(
    authorization: dict,
) -> list[str]:
    binding_errors: list[str] = []
    semantic_keys = {
        "source_revisions": "repo",
        "runtime_artifacts": "artifact_id",
        "runtime_images": "image_ref",
    }
    for collection_name, key_name in semantic_keys.items():
        values = [
            item[key_name] for item in authorization["scope"][collection_name]
        ]
        if len(values) != len(set(values)):
            binding_errors.append(
                f"scope.{collection_name} contains duplicate {key_name} bindings"
            )

    scenario_executions = authorization["commissioning_session"][
        "scenario_executions"
    ]
    scenario_ids = [item["scenario_id"] for item in scenario_executions]
    if scenario_ids != CONTROLLED_PROOF_REQUIRED_SCENARIO_ORDER:
        binding_errors.append(
            "scenario executions do not preserve the exact authorized scenario order"
        )
    scenario_execution_ids = [
        item["scenario_execution_id"] for item in scenario_executions
    ]
    if len(scenario_execution_ids) != len(set(scenario_execution_ids)):
        binding_errors.append("scenario execution ids are not unique")
    declared_receipt_owners = {
        owner
        for item in scenario_executions
        for owner in item["required_receipt_owners"]
    }
    if declared_receipt_owners != CONTROLLED_PROOF_REQUIRED_RECEIPT_OWNERS:
        binding_errors.append(
            "scenario executions do not collectively cover every proof receipt owner"
        )

    issued_at = datetime.fromisoformat(
        authorization["window"]["issued_at"].replace("Z", "+00:00")
    )
    expires_at = datetime.fromisoformat(
        authorization["window"]["expires_at"].replace("Z", "+00:00")
    )
    if issued_at >= expires_at:
        binding_errors.append("authorization issue time does not precede expiry")
    return binding_errors


def validate_controlled_proof_authorization_invariants(
    errors: list[str], schema: dict
) -> None:
    validator = Draft202012Validator(schema, format_checker=CONTRACT_FORMAT_CHECKER)
    valid_authorization = controlled_proof_authorization_fixture()
    if validation_errors := list(validator.iter_errors(valid_authorization)):
        errors.append(
            f"{CONTROLLED_PROOF_SCHEMA_REF}: valid bounded authorization was rejected: "
            f"{validation_errors[0].message}"
        )
    if binding_errors := controlled_proof_authorization_binding_errors(
        valid_authorization
    ):
        errors.append(
            f"{CONTROLLED_PROOF_SCHEMA_REF}: valid authorization semantics were rejected: "
            f"{binding_errors[0]}"
        )
    valid_sha256_revision = copy.deepcopy(valid_authorization)
    valid_sha256_revision["permit_issuer"]["source_revision"] = "c" * 64
    valid_sha256_revision["executor"]["source_revision"] = "c" * 64
    valid_sha256_revision["scope"]["source_revisions"][0]["commit"] = "c" * 64
    if validation_errors := list(validator.iter_errors(valid_sha256_revision)):
        errors.append(
            f"{CONTROLLED_PROOF_SCHEMA_REF}: valid 64-character source revisions "
            f"were rejected: {validation_errors[0].message}"
        )

    invalid_cases: dict[str, dict] = {}
    invalid_digest = copy.deepcopy(valid_authorization)
    invalid_digest["approvals"]["operator_approval_digest"] = "sha256:not-a-digest"
    invalid_cases["malformed approval digest"] = invalid_digest

    invalid_source_revision = copy.deepcopy(valid_authorization)
    invalid_source_revision["permit_issuer"]["source_revision"] = "a" * 41
    invalid_cases["non-exact reviewed-source revision"] = invalid_source_revision

    invalid_scope_revision = copy.deepcopy(valid_authorization)
    invalid_scope_revision["scope"]["source_revisions"][0]["commit"] = "a" * 63
    invalid_cases["non-exact scoped source revision"] = invalid_scope_revision

    invalid_timestamp = copy.deepcopy(valid_authorization)
    invalid_timestamp["window"]["expires_at"] = "2026-13-40T25:61:00Z"
    invalid_cases["invalid RFC 3339 expiry timestamp"] = invalid_timestamp

    for label, instance in invalid_cases.items():
        if not list(validator.iter_errors(instance)):
            errors.append(f"{CONTROLLED_PROOF_SCHEMA_REF}: must reject {label}")

    invalid_binding_cases: dict[str, dict] = {}
    duplicate_source_repo = copy.deepcopy(valid_authorization)
    duplicate_source_repo["scope"]["source_revisions"].append(
        {
            "repo": "platform-engineering",
            "commit": "c" * 40,
        }
    )
    invalid_binding_cases["duplicate semantic source-revision key"] = (
        duplicate_source_repo
    )

    duplicate_scenario_execution = copy.deepcopy(valid_authorization)
    duplicate_scenario_execution["commissioning_session"]["scenario_executions"][1][
        "scenario_execution_id"
    ] = duplicate_scenario_execution["commissioning_session"][
        "scenario_executions"
    ][0]["scenario_execution_id"]
    invalid_binding_cases["duplicate scenario execution id"] = (
        duplicate_scenario_execution
    )

    incomplete_owner_coverage = copy.deepcopy(valid_authorization)
    for scenario_execution in incomplete_owner_coverage["commissioning_session"][
        "scenario_executions"
    ]:
        scenario_execution["required_receipt_owners"] = ["platform-engineering"]
    invalid_binding_cases["authorization omitting proof owner coverage"] = (
        incomplete_owner_coverage
    )

    invalid_window = copy.deepcopy(valid_authorization)
    invalid_window["window"]["issued_at"] = "2026-08-01T02:00:00Z"
    invalid_binding_cases["authorization issued after expiry"] = invalid_window

    for label, instance in invalid_binding_cases.items():
        if not controlled_proof_authorization_binding_errors(instance):
            errors.append(
                f"{CONTROLLED_PROOF_SCHEMA_REF}: semantic validation must reject {label}"
            )


def controlled_proof_result_fixture() -> dict:
    digest = "sha256:" + "a" * 64
    authorization = controlled_proof_authorization_fixture()
    scenario_executions = authorization["commissioning_session"][
        "scenario_executions"
    ]
    scenario_outcomes = [
        {
            "scenario_id": scenario_execution["scenario_id"],
            "scenario_execution_id": scenario_execution["scenario_execution_id"],
            "status": "passed",
            "evidence_refs": [
                {
                    "artifact_ref": (
                        "artifact://controlled-proof/scenarios/"
                        f"{scenario_execution['scenario_execution_id']}"
                    ),
                    "artifact_digest": digest,
                }
            ],
            "started_at": "2026-08-01T00:00:02Z",
            "completed_at": "2026-08-01T00:00:03Z",
        }
        for scenario_execution in scenario_executions
    ]
    owner_execution_types = {
        "platform-engineering": "platform-action",
        "operator-orchestration-service": "workflow",
        "workspace-governance-control-fabric": "activity",
    }
    owner_receipts = [
        {
            "owner_repo": owner_repo,
            "authorization_id": authorization["authorization_id"],
            "authorization_digest": digest,
            "commissioning_session_id": authorization["commissioning_session"][
                "commissioning_session_id"
            ],
            "scenario_id": scenario_execution["scenario_id"],
            "scenario_execution_id": scenario_execution["scenario_execution_id"],
            "owner_execution": {
                "execution_type": owner_execution_types[owner_repo],
                "execution_id": (
                    f"{owner_execution_types[owner_repo]}:"
                    f"{scenario_execution['scenario_execution_id']}"
                ),
            },
            "owner_result": "passed",
            "evidence_refs": [
                {
                    "artifact_ref": (
                        "artifact://controlled-proof/owner-evidence/"
                        f"{owner_repo}/{scenario_execution['scenario_execution_id']}"
                    ),
                    "artifact_digest": digest,
                }
            ],
            "receipt_ref": (
                "artifact://controlled-proof/receipts/"
                f"{owner_repo}/{scenario_execution['scenario_execution_id']}"
            ),
            "receipt_digest": digest,
            "recorded_at": "2026-08-01T00:00:04Z",
        }
        for scenario_execution in scenario_executions
        for owner_repo in scenario_execution["required_receipt_owners"]
    ]
    return {
        "schema_version": 2,
        "result_id": "artifact://controlled-proof/results/validation-run",
        "authorization": {
            "authorization_id": authorization["authorization_id"],
            "authorization_digest": digest,
            "canonical_claims_digest": digest,
        },
        "commissioning_session": {
            "commissioning_session_id": authorization["commissioning_session"][
                "commissioning_session_id"
            ],
            "scenario_execution_count": len(scenario_executions),
            "authorization_consumed_at": "2026-08-01T00:00:00Z",
            "started_at": "2026-08-01T00:00:01Z",
        },
        "outcome": "passed",
        "scenario_outcomes": scenario_outcomes,
        "owner_receipts": owner_receipts,
        "baseline_restore": {
            "baseline_snapshot_ref": "artifact://controlled-proof/baselines/pre-run",
            "baseline_snapshot_digest": digest,
            "status": "exact-baseline-restored",
            "evidence_ref": "artifact://controlled-proof/restore/exact-baseline",
            "evidence_digest": digest,
        },
        "completed_at": "2026-08-01T00:10:00Z",
    }


def controlled_proof_result_binding_errors(
    authorization: dict,
    authorization_artifact_digest: str,
    result: dict,
) -> list[str]:
    binding_errors: list[str] = []
    comparisons = (
        (
            "authorization id",
            result["authorization"]["authorization_id"],
            authorization["authorization_id"],
        ),
        (
            "authorization artifact digest",
            result["authorization"]["authorization_digest"],
            authorization_artifact_digest,
        ),
        (
            "canonical claims digest",
            result["authorization"]["canonical_claims_digest"],
            authorization["approvals"]["canonical_claims_digest"],
        ),
        (
            "commissioning session id",
            result["commissioning_session"]["commissioning_session_id"],
            authorization["commissioning_session"]["commissioning_session_id"],
        ),
        (
            "baseline snapshot reference",
            result["baseline_restore"]["baseline_snapshot_ref"],
            authorization["baseline_and_restore"]["baseline_snapshot_ref"],
        ),
        (
            "baseline snapshot digest",
            result["baseline_restore"]["baseline_snapshot_digest"],
            authorization["baseline_and_restore"]["baseline_snapshot_digest"],
        ),
    )
    for label, actual, expected in comparisons:
        if actual != expected:
            binding_errors.append(f"{label} does not match the consumed authorization")

    authorized_scenarios = {
        item["scenario_execution_id"]: item
        for item in authorization["commissioning_session"]["scenario_executions"]
    }
    outcome_execution_ids = [
        item["scenario_execution_id"] for item in result["scenario_outcomes"]
    ]
    if len(outcome_execution_ids) != len(set(outcome_execution_ids)):
        binding_errors.append("scenario outcome execution ids are not unique")
    if set(outcome_execution_ids) != set(authorized_scenarios):
        binding_errors.append(
            "scenario outcomes do not exactly match the authorized execution set"
        )
    outcome_by_execution_id = {
        item["scenario_execution_id"]: item for item in result["scenario_outcomes"]
    }
    for scenario_execution_id, outcome in outcome_by_execution_id.items():
        authorized = authorized_scenarios.get(scenario_execution_id)
        if authorized and outcome["scenario_id"] != authorized["scenario_id"]:
            binding_errors.append(
                f"scenario outcome {scenario_execution_id} changes its authorized scenario id"
            )

    expected_receipt_pairs = {
        (item["scenario_execution_id"], owner_repo)
        for item in authorized_scenarios.values()
        for owner_repo in item["required_receipt_owners"]
    }
    actual_receipt_pairs: set[tuple[str, str]] = set()
    expected_owner_execution_types = {
        "platform-engineering": "platform-action",
        "operator-orchestration-service": "workflow",
        "workspace-governance-control-fabric": "activity",
    }
    for receipt in result["owner_receipts"]:
        owner_repo = receipt["owner_repo"]
        scenario_execution_id = receipt["scenario_execution_id"]
        receipt_pair = (scenario_execution_id, owner_repo)
        if receipt_pair in actual_receipt_pairs:
            binding_errors.append(
                f"owner receipt pair {scenario_execution_id}/{owner_repo} is duplicated"
            )
        actual_receipt_pairs.add(receipt_pair)
        authorized = authorized_scenarios.get(scenario_execution_id)
        if not authorized or owner_repo not in authorized["required_receipt_owners"]:
            binding_errors.append(
                f"owner receipt pair {scenario_execution_id}/{owner_repo} is not authorized"
            )
        elif receipt["scenario_id"] != authorized["scenario_id"]:
            binding_errors.append(
                f"{owner_repo} receipt changes the authorized scenario id"
            )
        receipt_bindings = (
            (
                "authorization id",
                receipt["authorization_id"],
                result["authorization"]["authorization_id"],
            ),
            (
                "authorization digest",
                receipt["authorization_digest"],
                result["authorization"]["authorization_digest"],
            ),
            (
                "commissioning session id",
                receipt["commissioning_session_id"],
                result["commissioning_session"]["commissioning_session_id"],
            ),
        )
        for label, actual, expected in receipt_bindings:
            if actual != expected:
                binding_errors.append(
                    f"{owner_repo} receipt {label} does not match the result binding"
                )
        expected_execution_type = expected_owner_execution_types.get(owner_repo)
        if receipt["owner_execution"]["execution_type"] != expected_execution_type:
            binding_errors.append(
                f"{owner_repo} receipt uses the wrong owner execution type"
            )
    if result["outcome"] == "passed" and actual_receipt_pairs != expected_receipt_pairs:
        binding_errors.append(
            "passing result receipts do not exactly match the authorized owner/execution pairs"
        )
    if result["outcome"] == "passed" and any(
        receipt["owner_result"] != "passed" for receipt in result["owner_receipts"]
    ):
        binding_errors.append("passing result contains a non-passing owner receipt")

    issued_at = datetime.fromisoformat(
        authorization["window"]["issued_at"].replace("Z", "+00:00")
    )
    expires_at = datetime.fromisoformat(
        authorization["window"]["expires_at"].replace("Z", "+00:00")
    )
    consumed_at = datetime.fromisoformat(
        result["commissioning_session"]["authorization_consumed_at"].replace(
            "Z", "+00:00"
        )
    )
    session_started_at = datetime.fromisoformat(
        result["commissioning_session"]["started_at"].replace("Z", "+00:00")
    )
    completed_at = datetime.fromisoformat(
        result["completed_at"].replace("Z", "+00:00")
    )
    if issued_at >= expires_at:
        binding_errors.append("authorization issue time does not precede expiry")
    if consumed_at < issued_at or consumed_at >= expires_at:
        binding_errors.append("permit consumption is outside the authorization window")
    if consumed_at > session_started_at:
        binding_errors.append("commissioning session started before permit consumption")
    if session_started_at >= expires_at:
        binding_errors.append(
            "commissioning session started at or after authorization expiry"
        )
    scenario_completed_at: list[datetime] = []
    for outcome in result["scenario_outcomes"]:
        scenario_started_at = datetime.fromisoformat(
            outcome["started_at"].replace("Z", "+00:00")
        )
        scenario_finished_at = datetime.fromisoformat(
            outcome["completed_at"].replace("Z", "+00:00")
        )
        if scenario_started_at < session_started_at:
            binding_errors.append(
                f"scenario {outcome['scenario_execution_id']} started before its session"
            )
        if scenario_started_at >= expires_at:
            binding_errors.append(
                f"scenario {outcome['scenario_execution_id']} started at or after authorization expiry"
            )
        if scenario_finished_at < scenario_started_at:
            binding_errors.append(
                f"scenario {outcome['scenario_execution_id']} completed before it started"
            )
        scenario_completed_at.append(scenario_finished_at)
    if scenario_completed_at and max(scenario_completed_at) > completed_at:
        binding_errors.append("result completion precedes a scenario completion")

    for receipt in result["owner_receipts"]:
        recorded_at = datetime.fromisoformat(
            receipt["recorded_at"].replace("Z", "+00:00")
        )
        outcome = outcome_by_execution_id.get(receipt["scenario_execution_id"])
        if outcome:
            scenario_started_at = datetime.fromisoformat(
                outcome["started_at"].replace("Z", "+00:00")
            )
            if recorded_at < scenario_started_at or recorded_at > completed_at:
                binding_errors.append(
                    f"{receipt['owner_repo']} receipt timestamp is outside its result timeline"
                )
    if result["outcome"] == "passed" and completed_at >= expires_at:
        binding_errors.append("passing result completed after authorization expiry")
    return binding_errors


def validate_controlled_proof_result_invariants(errors: list[str], schema: dict) -> None:
    validator = Draft202012Validator(schema, format_checker=CONTRACT_FORMAT_CHECKER)
    valid_authorization = controlled_proof_authorization_fixture()
    authorization_artifact_digest = "sha256:" + "a" * 64
    valid_passed = controlled_proof_result_fixture()
    if validation_errors := list(validator.iter_errors(valid_passed)):
        errors.append(
            f"{CONTROLLED_PROOF_RESULT_SCHEMA_REF}: valid all-passing result was rejected: "
            f"{validation_errors[0].message}"
        )
    if binding_errors := controlled_proof_result_binding_errors(
        valid_authorization,
        authorization_artifact_digest,
        valid_passed,
    ):
        errors.append(
            f"{CONTROLLED_PROOF_RESULT_SCHEMA_REF}: valid result-to-authorization binding "
            f"was rejected: {binding_errors[0]}"
        )

    valid_stopped = copy.deepcopy(valid_passed)
    valid_stopped["outcome"] = "stopped"
    valid_stopped["scenario_outcomes"][-1]["status"] = "failed"
    valid_stopped["scenario_outcomes"][-1]["completed_at"] = (
        "2026-08-01T01:05:00Z"
    )
    for receipt in valid_stopped["owner_receipts"]:
        if receipt["scenario_id"] == "exact-baseline-restore":
            receipt["owner_result"] = "failed"
            receipt["recorded_at"] = "2026-08-01T01:06:00Z"
    valid_stopped["baseline_restore"]["status"] = "governed-exception-recorded"
    valid_stopped["completed_at"] = "2026-08-01T01:10:00Z"
    valid_stopped["exception"] = {
        "decision": "defer",
        "record_ref": "artifact://controlled-proof/exceptions/restore",
        "record_digest": "sha256:" + "b" * 64,
    }
    if validation_errors := list(validator.iter_errors(valid_stopped)):
        errors.append(
            f"{CONTROLLED_PROOF_RESULT_SCHEMA_REF}: valid stopped exception result was rejected: "
            f"{validation_errors[0].message}"
        )
    if binding_errors := controlled_proof_result_binding_errors(
        valid_authorization,
        authorization_artifact_digest,
        valid_stopped,
    ):
        errors.append(
            f"{CONTROLLED_PROOF_RESULT_SCHEMA_REF}: valid stopped cleanup after expiry "
            f"was rejected: {binding_errors[0]}"
        )

    invalid_cases: dict[str, dict] = {}
    failed_scenario = copy.deepcopy(valid_passed)
    failed_scenario["scenario_outcomes"][8]["status"] = "failed"
    invalid_cases["passed result with a non-passing scenario"] = failed_scenario

    restore_exception = copy.deepcopy(valid_passed)
    restore_exception["baseline_restore"]["status"] = "governed-exception-recorded"
    restore_exception["exception"] = copy.deepcopy(valid_stopped["exception"])
    invalid_cases["passed result with a restore exception"] = restore_exception

    unexpected_exception = copy.deepcopy(valid_passed)
    unexpected_exception["exception"] = copy.deepcopy(valid_stopped["exception"])
    invalid_cases["passed result carrying any exception"] = unexpected_exception

    unrelated_owner_receipt = copy.deepcopy(valid_passed)
    unrelated_owner_receipt["owner_receipts"][0]["owner_repo"] = "unrelated-owner"
    invalid_cases["result carrying an unrelated owner receipt"] = (
        unrelated_owner_receipt
    )

    for label, instance in invalid_cases.items():
        if not list(validator.iter_errors(instance)):
            errors.append(
                f"{CONTROLLED_PROOF_RESULT_SCHEMA_REF}: must reject {label}"
            )

    invalid_binding_cases: dict[str, dict] = {}
    mismatched_authorization_digest = copy.deepcopy(valid_passed)
    mismatched_authorization_digest["authorization"]["authorization_digest"] = (
        "sha256:" + "e" * 64
    )
    invalid_binding_cases["incorrect complete authorization digest"] = (
        mismatched_authorization_digest
    )

    mismatched_baseline_ref = copy.deepcopy(valid_passed)
    mismatched_baseline_ref["baseline_restore"]["baseline_snapshot_ref"] = (
        "artifact://controlled-proof/baselines/different"
    )
    invalid_binding_cases["unauthorized baseline snapshot reference"] = (
        mismatched_baseline_ref
    )

    mismatched_baseline_digest = copy.deepcopy(valid_passed)
    mismatched_baseline_digest["baseline_restore"]["baseline_snapshot_digest"] = (
        "sha256:" + "c" * 64
    )
    invalid_binding_cases["unauthorized baseline snapshot digest"] = (
        mismatched_baseline_digest
    )

    started_before_consumption = copy.deepcopy(valid_passed)
    started_before_consumption["commissioning_session"]["started_at"] = (
        "2026-07-31T23:59:59Z"
    )
    invalid_binding_cases["session start before permit consumption"] = (
        started_before_consumption
    )

    consumed_before_issue = copy.deepcopy(valid_passed)
    consumed_before_issue["commissioning_session"]["authorization_consumed_at"] = (
        "2026-07-31T23:59:59Z"
    )
    invalid_binding_cases["permit consumption before issuance"] = consumed_before_issue

    consumed_after_expiry = copy.deepcopy(valid_passed)
    consumed_after_expiry["commissioning_session"]["authorization_consumed_at"] = (
        "2026-08-01T01:00:01Z"
    )
    consumed_after_expiry["commissioning_session"]["started_at"] = (
        "2026-08-01T01:00:02Z"
    )
    consumed_after_expiry["completed_at"] = "2026-08-01T01:00:03Z"
    invalid_binding_cases["permit consumption after expiry"] = consumed_after_expiry

    consumed_at_expiry = copy.deepcopy(valid_passed)
    consumed_at_expiry["commissioning_session"]["authorization_consumed_at"] = (
        "2026-08-01T01:00:00Z"
    )
    consumed_at_expiry["commissioning_session"]["started_at"] = (
        "2026-08-01T01:00:00Z"
    )
    consumed_at_expiry["completed_at"] = "2026-08-01T01:00:00Z"
    invalid_binding_cases["permit consumption at expiry"] = consumed_at_expiry

    completion_before_start = copy.deepcopy(valid_passed)
    completion_before_start["completed_at"] = "2026-08-01T00:00:00Z"
    invalid_binding_cases["result completion before scenario completion"] = (
        completion_before_start
    )

    passing_after_expiry = copy.deepcopy(valid_passed)
    passing_after_expiry["completed_at"] = "2026-08-01T01:00:01Z"
    invalid_binding_cases["passing result completed after expiry"] = (
        passing_after_expiry
    )

    passing_at_expiry = copy.deepcopy(valid_passed)
    passing_at_expiry["completed_at"] = "2026-08-01T01:00:00Z"
    invalid_binding_cases["passing result completed at expiry"] = passing_at_expiry

    stopped_starting_at_expiry = copy.deepcopy(valid_stopped)
    stopped_starting_at_expiry["commissioning_session"][
        "authorization_consumed_at"
    ] = "2026-08-01T00:59:59Z"
    stopped_starting_at_expiry["commissioning_session"]["started_at"] = (
        "2026-08-01T01:00:00Z"
    )
    invalid_binding_cases["stopped session starting at expiry"] = (
        stopped_starting_at_expiry
    )

    stale_owner_receipt = copy.deepcopy(valid_passed)
    stale_owner_receipt["owner_receipts"][1]["commissioning_session_id"] = (
        "historical-session"
    )
    invalid_binding_cases["owner receipt bound to a different session"] = (
        stale_owner_receipt
    )

    stale_owner_authorization = copy.deepcopy(valid_passed)
    stale_owner_authorization["owner_receipts"][0]["authorization_digest"] = (
        "sha256:" + "f" * 64
    )
    invalid_binding_cases["owner receipt bound to a different authorization"] = (
        stale_owner_authorization
    )

    missing_owner_receipt = copy.deepcopy(valid_passed)
    missing_owner_receipt["owner_receipts"].pop()
    invalid_binding_cases["passing result missing an authorized owner receipt"] = (
        missing_owner_receipt
    )

    duplicate_owner_pair = copy.deepcopy(valid_passed)
    duplicate_owner_pair["owner_receipts"][-1]["owner_repo"] = (
        duplicate_owner_pair["owner_receipts"][-2]["owner_repo"]
    )
    invalid_binding_cases["duplicate owner/scenario execution receipt pair"] = (
        duplicate_owner_pair
    )

    mismatched_scenario_execution = copy.deepcopy(valid_passed)
    mismatched_scenario_execution["owner_receipts"][0]["scenario_execution_id"] = (
        "scenario-execution:unrelated"
    )
    invalid_binding_cases["owner receipt bound to an unauthorized execution"] = (
        mismatched_scenario_execution
    )

    wrong_owner_execution_type = copy.deepcopy(valid_passed)
    wrong_owner_execution_type["owner_receipts"][0]["owner_execution"][
        "execution_type"
    ] = "activity"
    invalid_binding_cases["owner receipt using another owner's execution type"] = (
        wrong_owner_execution_type
    )

    duplicate_scenario_outcome = copy.deepcopy(valid_passed)
    duplicate_scenario_outcome["scenario_outcomes"][1]["scenario_execution_id"] = (
        duplicate_scenario_outcome["scenario_outcomes"][0]["scenario_execution_id"]
    )
    invalid_binding_cases["duplicate scenario outcome execution id"] = (
        duplicate_scenario_outcome
    )

    scenario_started_after_expiry = copy.deepcopy(valid_passed)
    scenario_started_after_expiry["scenario_outcomes"][0]["started_at"] = (
        "2026-08-01T01:00:00Z"
    )
    scenario_started_after_expiry["scenario_outcomes"][0]["completed_at"] = (
        "2026-08-01T01:00:01Z"
    )
    scenario_started_after_expiry["completed_at"] = "2026-08-01T01:00:02Z"
    invalid_binding_cases["scenario starting at authorization expiry"] = (
        scenario_started_after_expiry
    )

    scenario_completed_before_start = copy.deepcopy(valid_passed)
    scenario_completed_before_start["scenario_outcomes"][0]["completed_at"] = (
        "2026-08-01T00:00:01Z"
    )
    invalid_binding_cases["scenario completion before scenario start"] = (
        scenario_completed_before_start
    )

    for label, instance in invalid_binding_cases.items():
        if not controlled_proof_result_binding_errors(
            valid_authorization,
            authorization_artifact_digest,
            instance,
        ):
            errors.append(
                f"{CONTROLLED_PROOF_RESULT_SCHEMA_REF}: result acceptance must reject {label}"
            )

    invalid_authorization_window = copy.deepcopy(valid_authorization)
    invalid_authorization_window["window"]["issued_at"] = "2026-08-01T02:00:00Z"
    if not controlled_proof_result_binding_errors(
        invalid_authorization_window,
        authorization_artifact_digest,
        valid_passed,
    ):
        errors.append(
            f"{CONTROLLED_PROOF_RESULT_SCHEMA_REF}: result acceptance must reject an authorization issued after expiry"
        )


def has_required_scalar(payload: dict, key: str) -> bool:
    if key not in payload:
        return False
    value = payload[key]
    if value is None:
        return False
    if isinstance(value, str) and not value.strip():
        return False
    if isinstance(value, list) and not value:
        return False
    return True


def unadmitted_definition_uses_admitted_state(definition: dict) -> bool:
    return not definition["admitted"] and (
        definition["qualification"] == "admitted-durable"
        or definition["definition_state"] in {"active", "suspended", "retired"}
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate workspace governance contracts.")
    parser.add_argument(
        "--repo-root",
        default=Path(__file__).resolve().parents[1],
        type=Path,
        help="workspace-governance repository root",
    )
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    errors: list[str] = []
    validate_contract_format_checker(errors)

    instance_paths = {
        "version": repo_root / "contracts/version.yaml",
        "lifecycle": repo_root / "contracts/lifecycle.yaml",
        "intake_policy": repo_root / "contracts/intake-policy.yaml",
        "intake_register": repo_root / "contracts/intake-register.yaml",
        "governed_intake_assist": repo_root / "contracts/governed-intake-assist.yaml",
        "developer_integration_policy": repo_root / "contracts/developer-integration-policy.yaml",
        "developer_integration_profiles": repo_root / "contracts/developer-integration-profiles.yaml",
        "durable_orchestration": repo_root / "contracts/durable-orchestration.yaml",
        "delegation_policy": repo_root / "contracts/delegation-policy.yaml",
        "self_improvement_policy": repo_root / "contracts/self-improvement-policy.yaml",
        "work_home_routing": repo_root / "contracts/work-home-routing.yaml",
        "dependency_types": repo_root / "contracts/dependency-types.yaml",
        "repos": repo_root / "contracts/repos.yaml",
        "products": repo_root / "contracts/products.yaml",
        "components": repo_root / "contracts/components.yaml",
        "task_types": repo_root / "contracts/task-types.yaml",
        "change_classes": repo_root / "contracts/change-classes.yaml",
        "failure_taxonomy": repo_root / "contracts/failure-taxonomy.yaml",
        "improvement_triggers": repo_root / "contracts/improvement-triggers.yaml",
        "evidence_obligations": repo_root / "contracts/evidence-obligations.yaml",
        "review_obligations": repo_root / "contracts/review-obligations.yaml",
        "vocabulary": repo_root / "contracts/vocabulary.yaml",
        "exceptions": repo_root / "contracts/exceptions.yaml",
        "validation_matrix": repo_root / "contracts/validation-matrix.yaml",
        "skills": repo_root / "contracts/skills.yaml",
        "governance_engine_foundation": repo_root / "contracts/governance-engine-foundation.yaml",
        "governance_engine_output_manifest": repo_root / "contracts/governance-engine-output-manifest.yaml",
        "governance_engine_boundary_map": repo_root / "contracts/governance-engine-boundary-map.yaml",
        "governance_engine_shadow_parity": repo_root / "contracts/governance-engine-shadow-parity.yaml",
        "governance_engine_extraction_gate": repo_root / "contracts/governance-engine-extraction-gate.yaml",
        "governance_control_fabric_operator_surface": repo_root / "contracts/governance-control-fabric-operator-surface.yaml",
        "governance_validator_catalog": repo_root / "contracts/governance-validator-catalog.yaml",
        "context_behavior": repo_root / "contracts/context-behavior.yaml",
        "raw_context_retirement": repo_root / "contracts/raw-context-retirement.yaml",
        "delivery_art_operator_path": repo_root / "contracts/delivery-art-operator-path.yaml",
    }

    for key, rel_path in SCHEMA_FILES.items():
        validate_schema(errors, instance_paths[key], repo_root / rel_path)

    delivery_art_proof_cases = validate_delivery_art_artifact_contracts(
        errors, repo_root
    )
    delivery_art_contract = yaml.safe_load(
        instance_paths["delivery_art_operator_path"].read_text()
    ) or {}
    validate_delivery_art_proof_obligations(
        errors,
        _artifact_object(delivery_art_contract.get("delivery_art_operator_path")),
        delivery_art_proof_cases,
    )

    controlled_proof_schema_path = repo_root / CONTROLLED_PROOF_SCHEMA_REF
    controlled_proof_schema: dict = {}
    if not controlled_proof_schema_path.exists():
        errors.append(
            f"{CONTROLLED_PROOF_SCHEMA_REF}: controlled proof authorization schema is missing"
        )
    else:
        controlled_proof_schema = load_json(controlled_proof_schema_path)
        try:
            Draft202012Validator.check_schema(controlled_proof_schema)
        except SchemaError as exc:
            errors.append(
                f"{CONTROLLED_PROOF_SCHEMA_REF}: invalid JSON Schema: {exc.message}"
            )

    controlled_proof_result_schema_path = repo_root / CONTROLLED_PROOF_RESULT_SCHEMA_REF
    controlled_proof_result_schema: dict = {}
    if not controlled_proof_result_schema_path.exists():
        errors.append(
            f"{CONTROLLED_PROOF_RESULT_SCHEMA_REF}: controlled proof result schema is missing"
        )
    else:
        controlled_proof_result_schema = load_json(controlled_proof_result_schema_path)
        try:
            Draft202012Validator.check_schema(controlled_proof_result_schema)
        except SchemaError as exc:
            errors.append(
                f"{CONTROLLED_PROOF_RESULT_SCHEMA_REF}: invalid JSON Schema: {exc.message}"
            )

    repo_rules_schema = repo_root / REPO_RULES_SCHEMA
    for path in sorted((repo_root / "contracts" / "repo-rules").glob("*.yaml")):
        validate_schema(errors, path, repo_rules_schema)

    contracts = load_contracts(repo_root)
    supported_schema_versions = set(
        contracts["version"]["compatibility"]["supported_schema_versions"]
    )
    for contract_name, contract_payload in contracts.items():
        if contract_name == "repo_rules":
            for repo_name, repo_rule in contract_payload.items():
                if repo_rule.get("schema_version") not in supported_schema_versions:
                    errors.append(
                        f"contracts/repo-rules/{repo_name}.yaml: schema_version is not supported by contracts/version.yaml"
                    )
            continue
        if (
            isinstance(contract_payload, dict)
            and contract_payload.get("schema_version") not in supported_schema_versions
        ):
            errors.append(
                f"{instance_paths[contract_name]}: schema_version is not supported by contracts/version.yaml"
            )
    lifecycle_states = set(contracts["lifecycle"]["states"].keys())
    intake_policy = contracts["intake_policy"]
    intake_register = contracts["intake_register"]
    governed_intake_assist = contracts["governed_intake_assist"]["governed_intake_assist"]
    developer_integration_policy = contracts["developer_integration_policy"]
    developer_integration_profiles = contracts["developer_integration_profiles"]
    durable_orchestration = contracts["durable_orchestration"]["durable_orchestration"]
    delegation_policy = contracts["delegation_policy"]
    self_improvement_policy = contracts["self_improvement_policy"]
    work_home_routing = contracts["work_home_routing"]["work_home_routing"]
    intake_statuses = set(intake_policy["statuses"])
    active_repos = set(active_repo_names(contracts))
    intake_repos = set(intake_register["repos"].keys())
    retired_repos = set(contracts["repos"].get("retired_repos", {}).keys())
    product_names = set(contracts["products"]["products"].keys())
    intake_products = set(intake_register["products"].keys())
    change_classes = set(contracts["change_classes"]["change_classes"].keys())
    component_names = set(contracts["components"]["components"].keys())
    intake_components = set(intake_register["components"].keys())
    failure_classes = contracts["failure_taxonomy"]["failure_classes"]
    improvement_triggers = contracts["improvement_triggers"]["triggers"]
    validator_scripts = contracts["validation_matrix"]["validators"]
    registered_skills = contracts["skills"]["skills"]
    governance_engine_foundation = contracts["governance_engine_foundation"][
        "governance_engine_foundation"
    ]
    governance_engine_output_manifest = contracts["governance_engine_output_manifest"][
        "governance_engine_output_manifest"
    ]
    governance_engine_boundary_map = contracts["governance_engine_boundary_map"][
        "governance_engine_boundary_map"
    ]
    governance_engine_shadow_parity = contracts["governance_engine_shadow_parity"][
        "governance_engine_shadow_parity"
    ]
    governance_engine_extraction_gate = contracts["governance_engine_extraction_gate"][
        "governance_engine_extraction_gate"
    ]
    governance_control_fabric_operator_surface = contracts[
        "governance_control_fabric_operator_surface"
    ]["governance_control_fabric_operator_surface"]
    governance_validator_catalog = contracts["governance_validator_catalog"][
        "governance_validator_catalog"
    ]
    context_behavior = contracts["context_behavior"]["context_behavior"]
    raw_context_retirement = contracts["raw_context_retirement"][
        "raw_context_retirement"
    ]
    delegation_task_classes = delegation_policy["task_classes"]
    self_improvement_governance = self_improvement_policy["governance"]
    self_improvement_runtime_gate = self_improvement_policy["runtime_gate"]
    self_improvement_signal_catalog = self_improvement_policy["signal_catalog"]
    work_home_classes = work_home_routing["classes"]
    work_home_routing_homes = set(work_home_routing["routing_homes"].keys())

    durable_label = "contracts/durable-orchestration.yaml"
    durable_operator_surface = repo_root / durable_orchestration["primary_operator_surface"]
    if not durable_operator_surface.exists() or durable_operator_surface.suffix != ".md":
        errors.append(
            f"{durable_label}: primary_operator_surface must point to an existing markdown surface"
        )
    expected_durable_authority = {
        "contract_owner": "workspace-governance",
        "aggregate_orchestrator": "operator-orchestration-service",
        "durable_runtime_owner": "platform-engineering",
        "durable_runtime_adapter": "temporal",
        "security_acceptance_owner": "security-architecture",
        "operator_cockpit_owner": "governance-operations-console",
    }
    durable_authority = durable_orchestration["authority"]
    for field, expected in expected_durable_authority.items():
        if durable_authority[field] != expected:
            errors.append(f"{durable_label}: authority.{field} must be {expected!r}")
    if durable_authority["direct_console_runtime_access_allowed"]:
        errors.append(
            f"{durable_label}: direct Console-to-runtime access must remain denied"
        )
    if not durable_authority["domain_business_authority_preserved"]:
        errors.append(
            f"{durable_label}: domain business authority must remain preserved"
        )
    referenced_durable_repos = {
        durable_authority["contract_owner"],
        durable_authority["aggregate_orchestrator"],
        durable_authority["durable_runtime_owner"],
        durable_authority["security_acceptance_owner"],
        durable_authority["operator_cockpit_owner"],
        *durable_authority["activity_owners"].keys(),
    }
    unknown_durable_repos = sorted(referenced_durable_repos - active_repos)
    if unknown_durable_repos:
        errors.append(
            f"{durable_label}: authority references inactive repos: "
            + ", ".join(unknown_durable_repos)
        )
    expected_qualification_classes = [
        "synchronous",
        "conditional",
        "durable-candidate",
        "admitted-durable",
    ]
    if durable_orchestration["qualification"]["classifications"] != expected_qualification_classes:
        errors.append(
            f"{durable_label}: qualification.classifications must preserve the canonical order"
        )
    expected_definition_lifecycle = [
        "candidate",
        "qualified",
        "definition-ready",
        "implementation-requested",
        "admission-review",
        "active",
        "suspended",
        "retired",
    ]
    if durable_orchestration["definition_contract"]["lifecycle"] != expected_definition_lifecycle:
        errors.append(
            f"{durable_label}: definition_contract.lifecycle must preserve the canonical lifecycle"
        )
    expected_definition_fields = {
        "definition_id",
        "definition_version",
        "title",
        "purpose",
        "source_domain",
        "source_record_type",
        "business_owner",
        "implementation_repo",
        "execution_owner",
        "execution_node_owners",
        "trigger",
        "approval_requirements",
        "source_version_refs",
        "idempotency_strategy",
        "lock_strategy",
        "execution_graph",
        "wait_and_signal_contract",
        "retry_and_timeout_contract",
        "compensation_strategy",
        "cancellation_boundary",
        "completion_condition",
        "expected_receipt",
        "return_projection",
        "evidence_and_retention",
        "security_requirements",
        "rollout_and_rollback",
    }
    if set(durable_orchestration["definition_contract"]["required_fields"]) != expected_definition_fields:
        errors.append(
            f"{durable_label}: definition_contract.required_fields must preserve the complete definition contract"
        )
    expected_run_lifecycle = [
        "queued",
        "running",
        "waiting",
        "blocked",
        "failed",
        "completed",
        "cancelled",
    ]
    if durable_orchestration["run_contract"]["lifecycle"] != expected_run_lifecycle:
        errors.append(
            f"{durable_label}: run_contract.lifecycle must preserve the canonical lifecycle"
        )
    durable_admission = durable_orchestration["admission"]
    runtime_posture = durable_admission["current_runtime"]
    allowed_runtime_lifecycles = {
        "source-defined-runtime-not-admitted": {"not-admitted"},
        "runtime-admission-review": {"proposed", "build-admitted"},
        "runtime-admitted": {"active", "suspended", "retired"},
    }
    contract_status = durable_orchestration["contract_status"]
    if runtime_posture["lifecycle"] not in allowed_runtime_lifecycles[contract_status]:
        errors.append(
            f"{durable_label}: contract_status {contract_status!r} is incompatible with "
            f"current_runtime.lifecycle {runtime_posture['lifecycle']!r}"
        )
    if runtime_posture["lifecycle"] == "not-admitted":
        if runtime_posture["dev_integration_profile"] is not None:
            errors.append(
                f"{durable_label}: a not-admitted runtime must not name a dev-integration profile"
            )
    elif not runtime_posture["dev_integration_profile"]:
        errors.append(
            f"{durable_label}: an admitted-review or admitted runtime must name its dev-integration profile"
        )
    if runtime_posture["lifecycle"] in {"not-admitted", "proposed", "build-admitted"}:
        for field in (
            "shared_runtime_allowed",
            "governed_stage_allowed",
            "production_allowed",
        ):
            if runtime_posture[field]:
                errors.append(
                    f"{durable_label}: current_runtime.{field} must remain false before admission"
                )
    initial_definitions = durable_orchestration["initial_definitions"]
    if not unadmitted_definition_uses_admitted_state(
        {
            "admitted": False,
            "qualification": "durable-candidate",
            "definition_state": "retired",
        }
    ):
        errors.append(
            f"{durable_label}: semantic validation must reject retired state for an unadmitted definition"
        )
    initial_definition_ids = [item["definition_id"] for item in initial_definitions]
    if len(initial_definition_ids) != len(set(initial_definition_ids)):
        errors.append(f"{durable_label}: initial definition ids must be unique")
    definition_roles = [item["role"] for item in initial_definitions]
    if len(definition_roles) != len(set(definition_roles)):
        errors.append(f"{durable_label}: initial definition roles must be unique")
    for definition in initial_definitions:
        definition_id = definition["definition_id"]
        admitted = definition["admitted"]
        admitted_qualification = definition["qualification"] == "admitted-durable"
        admitted_state = definition["definition_state"] in {
            "active",
            "suspended",
            "retired",
        }
        if admitted and (not admitted_qualification or not admitted_state):
            errors.append(
                f"{durable_label}: admitted definition {definition_id!r} must use "
                "qualification=admitted-durable and an active, suspended, or retired state"
            )
        if admitted and (
            contract_status != "runtime-admitted"
            or runtime_posture["lifecycle"] not in {"active", "suspended", "retired"}
        ):
            errors.append(
                f"{durable_label}: admitted definition {definition_id!r} requires "
                "an admitted runtime contract and lifecycle"
            )
        if unadmitted_definition_uses_admitted_state(definition):
            errors.append(
                f"{durable_label}: unadmitted definition {definition_id!r} cannot use "
                "admitted-durable qualification or an active, suspended, or retired state"
            )
        if definition["definition_state"] == "active" and (
            contract_status != "runtime-admitted"
            or runtime_posture["lifecycle"] != "active"
        ):
            errors.append(
                f"{durable_label}: active definition {definition_id!r} requires "
                "contract_status=runtime-admitted and current_runtime.lifecycle=active"
            )
        definition_repos = {
            definition["implementation_repo"],
            definition["execution_owner"],
            *definition["activity_owners"],
        }
        unknown_definition_repos = sorted(definition_repos - active_repos)
        if unknown_definition_repos:
            errors.append(
                f"{durable_label}: definition {definition['definition_id']} references inactive repos: "
                + ", ".join(unknown_definition_repos)
            )
    definitions_by_role = {item["role"]: item for item in initial_definitions}
    safe_definition = definitions_by_role.get("safe-runtime-proof")
    business_definition = definitions_by_role.get("first-business-workflow")
    if not safe_definition or safe_definition["definition_id"] != "validation-readiness-run":
        errors.append(
            f"{durable_label}: validation-readiness-run must remain the safe runtime proof"
        )
    if not business_definition or business_definition["definition_id"] != "delivery.refinement.apply":
        errors.append(
            f"{durable_label}: delivery.refinement.apply must remain the first business workflow"
        )
    controlled_proof_policy = developer_integration_policy["controlled_proof"]
    controlled_proof = durable_admission["controlled_proof"]
    permit_contract = controlled_proof_policy["permit"]
    if controlled_proof_policy["authority_type"] != "runtime-drill":
        errors.append(
            "contracts/developer-integration-policy.yaml: controlled_proof.authority_type "
            "must remain runtime-drill"
        )
    if controlled_proof_policy["drill_type"] != controlled_proof["proof_classification"]:
        errors.append(
            f"{durable_label}: controlled proof classification must match the dev-integration policy"
        )
    if set(controlled_proof_policy["eligible_profile_statuses"]) != {"build-admitted"}:
        errors.append(
            "contracts/developer-integration-policy.yaml: controlled proofs must be limited "
            "to build-admitted profiles"
        )
    for field, expected in (
        ("changes_profile_lifecycle", False),
        ("self_serve_launch_allowed", False),
        ("normal_profile_launch_remains_denied", True),
    ):
        if controlled_proof_policy[field] is not expected:
            errors.append(
                "contracts/developer-integration-policy.yaml: "
                f"controlled_proof.{field} must be {expected!r}"
            )
    if permit_contract["schema_ref"] != CONTROLLED_PROOF_SCHEMA_REF:
        errors.append(
            "contracts/developer-integration-policy.yaml: controlled_proof.permit.schema_ref "
            f"must be {CONTROLLED_PROOF_SCHEMA_REF!r}"
        )
    if controlled_proof["permit_schema_ref"] != permit_contract["schema_ref"]:
        errors.append(
            f"{durable_label}: controlled proof permit schema must match the dev-integration policy"
        )
    if (
        permit_contract.get("permit_issuer_binding_required") is not True
        or permit_contract.get("executor_binding_required") is not True
    ):
        errors.append(
            "contracts/developer-integration-policy.yaml: controlled proof permits must bind the reviewed issuer and executor"
        )
    expected_semantic_validation = {
        "unique_binding_keys": {
            "source_revisions": "repo",
            "runtime_artifacts": "artifact_id",
            "runtime_images": "image_ref",
        },
        "canonical_claims": {
            "canonicalization": "rfc8785",
            "projection": "all-authorization-fields-except-approvals",
            "approvals_bind_complete_claims": True,
            "approval_artifact_digests_required": True,
        },
        "session_consumption": {
            "mode": "atomic-single-use",
            "keyed_by": "authorization_id",
            "consume_before_first_mutation": True,
            "duplicate_consumption_denied": True,
        },
        "scenario_execution_binding": {
            "exact_authorized_set_required": True,
            "scenario_ids_must_be_unique": True,
            "scenario_execution_ids_must_be_unique": True,
            "required_receipt_owners_declared_per_execution": True,
        },
        "window_validation": {
            "issued_before_expiry": True,
            "acceptance_time_within_window": True,
        },
        "immutable_baseline_digest_required": True,
    }
    if permit_contract.get("semantic_validation") != expected_semantic_validation:
        errors.append(
            "contracts/developer-integration-policy.yaml: controlled proof permit semantic validation "
            "must preserve unique logical bindings, RFC 8785 approval binding, atomic single-use "
            "consumption, and immutable baseline digest verification"
        )
    result_contract = controlled_proof_policy.get("result", {})
    expected_result_contract = {
        "schema_ref": CONTROLLED_PROOF_RESULT_SCHEMA_REF,
        "schema_version": 2,
        "authorization_binding_required": True,
        "authorization_artifact_digest_canonicalization": "rfc8785",
        "authorization_artifact_digest_projection": "complete-authorization",
        "authorization_artifact_digest_must_match_consumed_permit": True,
        "commissioning_session_binding_required": True,
        "scenario_outcomes_required": True,
        "scenario_outcomes_bind_execution_id": True,
        "scenario_ids_must_be_unique": True,
        "scenario_execution_ids_must_be_unique": True,
        "scenario_ids_must_exactly_match_authorization": True,
        "owner_receipts_required": True,
        "owner_receipt_pairs_must_be_unique": True,
        "passed_receipt_pairs_must_exactly_match_authorization": True,
        "owner_receipts_bind_authorization_session_execution_and_result": True,
        "timeline_validation": {
            "consumption_within_authorization_window": True,
            "consumed_before_session_start": True,
            "session_start_within_authorization_window": True,
            "scenario_start_within_authorization_window": True,
            "scenario_completion_not_before_start": True,
            "result_completion_not_before_scenarios": True,
            "passed_completion_before_expiry": True,
        },
        "exact_baseline_evidence_required": True,
        "baseline_snapshot_must_match_authorization": True,
    }
    if result_contract != expected_result_contract:
        errors.append(
            "contracts/developer-integration-policy.yaml: controlled proof result must preserve "
            "authorization, commissioning-session, scenario-execution, owner-receipt, and exact-baseline evidence bindings"
        )
    if set(permit_contract["required_sections"]) != CONTROLLED_PROOF_REQUIRED_SECTIONS:
        errors.append(
            "contracts/developer-integration-policy.yaml: controlled_proof.permit.required_sections "
            "must preserve the complete authorization envelope"
        )
    if set(controlled_proof_schema.get("required") or []) != CONTROLLED_PROOF_REQUIRED_SECTIONS:
        errors.append(
            f"{CONTROLLED_PROOF_SCHEMA_REF}: required sections must preserve the complete authorization envelope"
        )
    controlled_proof_schema_properties = controlled_proof_schema.get("properties", {})
    controlled_proof_schema_boundaries = {
        "target": {"profile_id", "profile_lifecycle", "environment"},
        "scope": CONTROLLED_PROOF_REQUIRED_SCOPE_FIELDS,
        "commissioning_session": CONTROLLED_PROOF_REQUIRED_SESSION_FIELDS,
        "approvals": CONTROLLED_PROOF_REQUIRED_APPROVAL_FIELDS,
        "window": CONTROLLED_PROOF_REQUIRED_WINDOW_FIELDS,
        "evidence": CONTROLLED_PROOF_REQUIRED_EVIDENCE_FIELDS,
        "baseline_and_restore": CONTROLLED_PROOF_REQUIRED_RESTORE_FIELDS,
        "exception_handling": CONTROLLED_PROOF_REQUIRED_EXCEPTION_FIELDS,
    }
    for boundary_name, required_fields in controlled_proof_schema_boundaries.items():
        boundary_schema = controlled_proof_schema_properties.get(boundary_name, {})
        if set(boundary_schema.get("required") or []) != required_fields:
            errors.append(
                f"{CONTROLLED_PROOF_SCHEMA_REF}: {boundary_name}.required must preserve "
                "the complete bounded-proof scope"
            )
        if boundary_schema.get("additionalProperties") is not False:
            errors.append(
                f"{CONTROLLED_PROOF_SCHEMA_REF}: {boundary_name} must reject additional properties"
            )
    scope_schema_properties = controlled_proof_schema_properties.get("scope", {}).get(
        "properties", {}
    )
    session_schema_properties = controlled_proof_schema_properties.get(
        "commissioning_session", {}
    ).get("properties", {})
    expected_session_constants = {
        "consumption_mode": "atomic-single-use",
        "consume_before_first_mutation": True,
        "duplicate_consumption_denied": True,
    }
    for field, expected in expected_session_constants.items():
        if session_schema_properties.get(field, {}).get("const") != expected:
            errors.append(
                f"{CONTROLLED_PROOF_SCHEMA_REF}: commissioning_session.{field} must remain {expected!r}"
            )
    for digest_collection in ("runtime_artifacts", "runtime_images"):
        collection_schema = scope_schema_properties.get(digest_collection, {})
        item_schema = collection_schema.get("items", {})
        if collection_schema.get("minItems") != 1 or "digest" not in set(
            item_schema.get("required") or []
        ):
            errors.append(
                f"{CONTROLLED_PROOF_SCHEMA_REF}: scope.{digest_collection} must require at least one immutable digest"
            )
    scenario_executions_schema = session_schema_properties.get(
        "scenario_executions", {}
    )
    scenario_execution_refs = [
        item.get("$ref")
        for item in scenario_executions_schema.get("prefixItems", [])
    ]
    expected_scenario_execution_refs = [
        "#/$defs/nominalCompletionExecution",
        "#/$defs/workflowWorkerRestartExecution",
        "#/$defs/temporalRuntimeRestartExecution",
        "#/$defs/deterministicReplayExecution",
        "#/$defs/duplicateSuppressionExecution",
        "#/$defs/cancellationExecution",
        "#/$defs/unavailableDependencyExecution",
        "#/$defs/identityDenialExecution",
        "#/$defs/payloadBoundaryExecution",
        "#/$defs/backupRestoreExecution",
        "#/$defs/exactBaselineRestoreExecution",
    ]
    if (
        scenario_execution_refs != expected_scenario_execution_refs
        or scenario_executions_schema.get("items") is not False
        or scenario_executions_schema.get("uniqueItems") is not True
        or scenario_executions_schema.get("minItems")
        != len(CONTROLLED_PROOF_REQUIRED_SCENARIO_ORDER)
        or scenario_executions_schema.get("maxItems")
        != len(CONTROLLED_PROOF_REQUIRED_SCENARIO_ORDER)
    ):
        errors.append(
            f"{CONTROLLED_PROOF_SCHEMA_REF}: commissioning_session.scenario_executions must preserve the exact scenario set"
        )
    scenario_execution_definition = (controlled_proof_schema.get("$defs") or {}).get(
        "scenarioExecution", {}
    )
    if (
        set(scenario_execution_definition.get("required") or [])
        != {"scenario_id", "scenario_execution_id", "required_receipt_owners"}
        or scenario_execution_definition.get("additionalProperties") is not False
    ):
        errors.append(
            f"{CONTROLLED_PROOF_SCHEMA_REF}: every scenario execution must bind its id and required receipt owners"
        )
    receipt_owner_definition = (controlled_proof_schema.get("$defs") or {}).get(
        "receiptOwnerList", {}
    )
    if (
        set((receipt_owner_definition.get("items") or {}).get("enum") or [])
        != CONTROLLED_PROOF_REQUIRED_RECEIPT_OWNERS
        or receipt_owner_definition.get("uniqueItems") is not True
    ):
        errors.append(
            f"{CONTROLLED_PROOF_SCHEMA_REF}: per-execution receipt owners must be limited to the proof-owner set"
        )
    target_schema_properties = controlled_proof_schema_properties.get("target", {}).get(
        "properties", {}
    )
    if (
        target_schema_properties.get("profile_lifecycle", {}).get("const")
        != "build-admitted"
        or target_schema_properties.get("environment", {}).get("const")
        != "dev-integration"
    ):
        errors.append(
            f"{CONTROLLED_PROOF_SCHEMA_REF}: target must remain build-admitted dev-integration"
        )
    approval_schema_properties = controlled_proof_schema_properties.get(
        "approvals", {}
    ).get("properties", {})
    if approval_schema_properties.get("issued_by", {}).get("const") != "platform-engineering":
        errors.append(
            f"{CONTROLLED_PROOF_SCHEMA_REF}: approvals.issued_by must remain platform-engineering"
        )
    if approval_schema_properties.get("canonicalization", {}).get("const") != "rfc8785":
        errors.append(
            f"{CONTROLLED_PROOF_SCHEMA_REF}: approvals.canonicalization must remain rfc8785"
        )
    if (
        approval_schema_properties.get("canonical_claims_projection", {}).get("const")
        != "all-authorization-fields-except-approvals"
    ):
        errors.append(
            f"{CONTROLLED_PROOF_SCHEMA_REF}: approvals must bind every authorization field outside the approval envelope"
        )
    reviewed_source_schema = (controlled_proof_schema.get("$defs") or {}).get(
        "reviewedPlatformSource", {}
    )
    if (
        set(reviewed_source_schema.get("required") or [])
        != CONTROLLED_PROOF_REQUIRED_EXECUTOR_FIELDS
        or reviewed_source_schema.get("additionalProperties") is not False
    ):
        errors.append(
            f"{CONTROLLED_PROOF_SCHEMA_REF}: reviewed Platform source binding must preserve the complete closed schema"
        )
    reviewed_source_properties = reviewed_source_schema.get("properties", {})
    if reviewed_source_properties.get("owner_repo", {}).get("const") != "platform-engineering":
        errors.append(
            f"{CONTROLLED_PROOF_SCHEMA_REF}: reviewed source owner_repo must remain platform-engineering"
        )
    expected_source_ref = "#/$defs/reviewedPlatformSource"
    for field in ("permit_issuer", "executor"):
        if controlled_proof_schema_properties.get(field, {}).get("$ref") != expected_source_ref:
            errors.append(
                f"{CONTROLLED_PROOF_SCHEMA_REF}: {field} must use the reviewed Platform source binding"
            )
    restore_schema_properties = controlled_proof_schema_properties.get(
        "baseline_and_restore", {}
    ).get("properties", {})
    if restore_schema_properties.get("restore_mode", {}).get("const") != "exact-baseline":
        errors.append(
            f"{CONTROLLED_PROOF_SCHEMA_REF}: baseline_and_restore.restore_mode must remain exact-baseline"
        )
    if (
        restore_schema_properties.get("baseline_snapshot_digest", {}).get("$ref")
        != "#/$defs/digest"
    ):
        errors.append(
            f"{CONTROLLED_PROOF_SCHEMA_REF}: baseline_and_restore must bind an immutable snapshot digest"
        )
    terminal_cleanup_schema = restore_schema_properties.get(
        "terminal_cleanup_authority", {}
    )
    if (
        set(terminal_cleanup_schema.get("required") or [])
        != CONTROLLED_PROOF_REQUIRED_TERMINAL_CLEANUP_FIELDS
    ):
        errors.append(
            f"{CONTROLLED_PROOF_SCHEMA_REF}: terminal cleanup authority must preserve the complete restore-only boundary"
        )
    if terminal_cleanup_schema.get("additionalProperties") is not False:
        errors.append(
            f"{CONTROLLED_PROOF_SCHEMA_REF}: terminal cleanup authority must reject additional properties"
        )
    terminal_cleanup_properties = terminal_cleanup_schema.get("properties", {})
    expected_terminal_cleanup_constants = {
        "mode": "exact-baseline-restore-only",
        "applies_to": "already-started-commissioning-session",
        "trigger_scope": "any-triggered-stop-condition",
        "scope_binding": "exact-captured-restore-scope",
        "new_proof_actions_denied": True,
        "scope_expansion_denied": True,
        "runtime_retention_denied": True,
    }
    for field, expected in expected_terminal_cleanup_constants.items():
        if terminal_cleanup_properties.get(field, {}).get("const") != expected:
            errors.append(
                f"{CONTROLLED_PROOF_SCHEMA_REF}: terminal cleanup {field} must remain {expected!r}"
            )
    for field, expected in (
        ("permitted_actions", CONTROLLED_PROOF_TERMINAL_CLEANUP_ACTIONS),
        (
            "termination_conditions",
            CONTROLLED_PROOF_TERMINAL_CLEANUP_TERMINATION_CONDITIONS,
        ),
    ):
        actual = [
            item.get("const")
            for item in terminal_cleanup_properties.get(field, {}).get("prefixItems", [])
        ]
        if actual != expected:
            errors.append(
                f"{CONTROLLED_PROOF_SCHEMA_REF}: terminal cleanup {field} must remain {expected!r}"
            )
    if controlled_proof_schema_properties.get("authority_type", {}).get("const") != "runtime-drill":
        errors.append(
            f"{CONTROLLED_PROOF_SCHEMA_REF}: authority_type must remain runtime-drill"
        )
    if (
        controlled_proof_schema_properties.get("drill_type", {}).get("const")
        != "component-commissioning-proof"
    ):
        errors.append(
            f"{CONTROLLED_PROOF_SCHEMA_REF}: drill_type must remain component-commissioning-proof"
        )
    schema_version_contract = (
        controlled_proof_schema.get("properties", {})
        .get("schema_version", {})
        .get("const")
    )
    if schema_version_contract != permit_contract["schema_version"]:
        errors.append(
            "contracts/developer-integration-policy.yaml: controlled proof permit schema_version "
            "must match the authorization schema"
        )
    validate_controlled_proof_authorization_invariants(
        errors,
        controlled_proof_schema,
    )
    if controlled_proof.get("result_schema_ref") != CONTROLLED_PROOF_RESULT_SCHEMA_REF:
        errors.append(
            f"{durable_label}: controlled proof result schema must remain {CONTROLLED_PROOF_RESULT_SCHEMA_REF!r}"
        )
    if result_contract.get("schema_ref") != controlled_proof.get("result_schema_ref"):
        errors.append(
            f"{durable_label}: controlled proof result schema must match the dev-integration policy"
        )
    if (
        set(controlled_proof_result_schema.get("required") or [])
        != CONTROLLED_PROOF_RESULT_REQUIRED_SECTIONS
        or controlled_proof_result_schema.get("additionalProperties") is not False
    ):
        errors.append(
            f"{CONTROLLED_PROOF_RESULT_SCHEMA_REF}: result envelope must preserve the complete closed schema"
        )
    result_schema_properties = controlled_proof_result_schema.get("properties", {})
    result_schema_boundaries = {
        "authorization": CONTROLLED_PROOF_RESULT_REQUIRED_AUTHORIZATION_FIELDS,
        "commissioning_session": CONTROLLED_PROOF_RESULT_REQUIRED_SESSION_FIELDS,
        "baseline_restore": CONTROLLED_PROOF_RESULT_REQUIRED_RESTORE_FIELDS,
    }
    for boundary_name, required_fields in result_schema_boundaries.items():
        boundary_schema = result_schema_properties.get(boundary_name, {})
        if (
            set(boundary_schema.get("required") or []) != required_fields
            or boundary_schema.get("additionalProperties") is not False
        ):
            errors.append(
                f"{CONTROLLED_PROOF_RESULT_SCHEMA_REF}: {boundary_name} must preserve its complete closed binding"
            )
    scenario_outcomes_schema = result_schema_properties.get("scenario_outcomes", {})
    expected_scenario_outcome_refs = [
        ref.replace("Execution", "Outcome")
        for ref in expected_scenario_execution_refs
    ]
    if (
        scenario_outcomes_schema.get("type") != "array"
        or [
            item.get("$ref")
            for item in scenario_outcomes_schema.get("prefixItems", [])
        ]
        != expected_scenario_outcome_refs
        or scenario_outcomes_schema.get("items") is not False
        or scenario_outcomes_schema.get("uniqueItems") is not True
        or scenario_outcomes_schema.get("minItems")
        != len(CONTROLLED_PROOF_REQUIRED_SCENARIO_ORDER)
        or scenario_outcomes_schema.get("maxItems")
        != len(CONTROLLED_PROOF_REQUIRED_SCENARIO_ORDER)
    ):
        errors.append(
            f"{CONTROLLED_PROOF_RESULT_SCHEMA_REF}: scenario outcomes must exactly cover every authorized scenario execution"
        )
    scenario_outcome_definition = (controlled_proof_result_schema.get("$defs") or {}).get(
        "scenarioOutcome", {}
    )
    if (
        set(scenario_outcome_definition.get("required") or [])
        != CONTROLLED_PROOF_RESULT_REQUIRED_SCENARIO_OUTCOME_FIELDS
        or scenario_outcome_definition.get("additionalProperties") is not False
    ):
        errors.append(
            f"{CONTROLLED_PROOF_RESULT_SCHEMA_REF}: each scenario outcome must preserve complete machine-readable evidence"
        )
    owner_receipts_schema = result_schema_properties.get("owner_receipts", {})
    if (
        owner_receipts_schema.get("type") != "array"
        or owner_receipts_schema.get("minItems") != 1
        or owner_receipts_schema.get("uniqueItems") is not True
        or (owner_receipts_schema.get("items") or {}).get("$ref")
        != "#/$defs/ownerReceipt"
    ):
        errors.append(
            f"{CONTROLLED_PROOF_RESULT_SCHEMA_REF}: owner receipts must use the closed per-execution receipt schema"
        )
    owner_receipt_definition = (controlled_proof_result_schema.get("$defs") or {}).get(
        "ownerReceipt", {}
    )
    if (
        set(owner_receipt_definition.get("required") or [])
        != CONTROLLED_PROOF_RESULT_REQUIRED_RECEIPT_FIELDS
        or owner_receipt_definition.get("additionalProperties") is not False
    ):
        errors.append(
            f"{CONTROLLED_PROOF_RESULT_SCHEMA_REF}: each owner receipt must preserve complete machine-readable evidence"
        )
    owner_execution_definition = owner_receipt_definition.get("properties", {}).get(
        "owner_execution", {}
    )
    if (
        set(owner_execution_definition.get("required") or [])
        != CONTROLLED_PROOF_RESULT_REQUIRED_OWNER_EXECUTION_FIELDS
        or owner_execution_definition.get("additionalProperties") is not False
    ):
        errors.append(
            f"{CONTROLLED_PROOF_RESULT_SCHEMA_REF}: each owner receipt must bind one typed owner execution"
        )
    evidence_pointer_definition = (
        controlled_proof_result_schema.get("$defs") or {}
    ).get("evidencePointer", {})
    if (
        set(evidence_pointer_definition.get("required") or [])
        != CONTROLLED_PROOF_RESULT_REQUIRED_EVIDENCE_FIELDS
        or evidence_pointer_definition.get("additionalProperties") is not False
    ):
        errors.append(
            f"{CONTROLLED_PROOF_RESULT_SCHEMA_REF}: evidence pointers must bind immutable artifact refs and digests"
        )
    if result_schema_properties.get("commissioning_session", {}).get(
        "properties", {}
    ).get("scenario_execution_count", {}).get("const") != len(
        CONTROLLED_PROOF_REQUIRED_SCENARIO_ORDER
    ):
        errors.append(
            f"{CONTROLLED_PROOF_RESULT_SCHEMA_REF}: commissioning session count must match the authorized scenario set"
        )
    if result_schema_properties.get("schema_version", {}).get("const") != result_contract.get(
        "schema_version"
    ):
        errors.append(
            "contracts/developer-integration-policy.yaml: controlled proof result schema_version "
            "must match the result schema"
        )
    validate_controlled_proof_result_invariants(
        errors,
        controlled_proof_result_schema,
    )
    proof_authorities = controlled_proof_policy["authorities"]
    expected_proof_authorities = {
        "issuer": durable_authority["durable_runtime_owner"],
        "executor_owner": durable_authority["durable_runtime_owner"],
        "security_authorizer": durable_authority["security_acceptance_owner"],
    }
    for field, expected in expected_proof_authorities.items():
        if proof_authorities[field] != expected:
            errors.append(
                "contracts/developer-integration-policy.yaml: "
                f"controlled_proof.authorities.{field} must be {expected!r}"
            )
    if not proof_authorities["operator_approval_required"]:
        errors.append(
            "contracts/developer-integration-policy.yaml: controlled proofs require operator approval"
        )
    if (
        proof_authorities.get("permit_issuer_source_review_required") is not True
        or proof_authorities.get("executor_source_review_required") is not True
    ):
        errors.append(
            "contracts/developer-integration-policy.yaml: controlled proof issuer and executor source review is required"
        )
    proof_owner_surfaces = controlled_proof_policy.get("owner_surfaces", {})
    expected_proof_owner_surfaces = {
        "platform_operator": {
            "repo": "platform-engineering",
            "path": "docs/components/temporal/operations.md",
        },
        "platform_profile": {
            "repo": "platform-engineering",
            "path": "environments/shared/runtime-drills/temporal-component-commissioning-proof.yaml",
        },
        "security_contract_review": {
            "repo": "security-architecture",
            "path": "docs/reviews/components/2026-08-01-temporal-controlled-commissioning-proof-contract.md",
        },
    }
    if proof_owner_surfaces != expected_proof_owner_surfaces:
        errors.append(
            "contracts/developer-integration-policy.yaml: controlled proof owner surfaces must bind the Platform runbook/profile and Security contract review"
        )
    proof_completion = controlled_proof_policy["completion"]
    if (
        proof_completion["restore_mode"] != "exact-baseline"
        or not proof_completion["restore_required_before_completion"]
        or proof_completion.get("terminal_cleanup_authority_mode")
        != "exact-baseline-restore-only"
        or proof_completion.get("terminal_cleanup_bound_to_started_session")
        is not True
        or proof_completion.get("terminal_cleanup_trigger_scope")
        != "any-triggered-stop-condition"
        or proof_completion.get("new_proof_actions_allowed_after_stop") is not False
        or not proof_completion["post_proof_security_review_required"]
        or proof_completion["pre_run_authorization_reusable_as_activation_evidence"]
    ):
        errors.append(
            "contracts/developer-integration-policy.yaml: controlled proof completion must "
            "require exact-baseline restore and separate post-proof Security review"
        )
    required_policy_denials = {
        "build-admitted profile became active",
        "controlled proof became a self-serve launch path",
        "pre-run authorization satisfied post-run activation evidence",
        "local proof became governed stage or production evidence",
        "post-proof runtime state was retained without governed reclassification",
    }
    if not required_policy_denials.issubset(
        set(controlled_proof_policy["forbidden_claims"])
    ):
        errors.append(
            "contracts/developer-integration-policy.yaml: controlled_proof.forbidden_claims "
            "must preserve every maturity and restoration boundary"
        )
    proof_target = controlled_proof["target"]
    if proof_target["profile_id"] != runtime_posture["dev_integration_profile"]:
        errors.append(
            f"{durable_label}: controlled proof target profile must match current_runtime.dev_integration_profile"
        )
    if proof_target["profile_lifecycle"] != runtime_posture["lifecycle"]:
        errors.append(
            f"{durable_label}: controlled proof target lifecycle must match current_runtime.lifecycle"
        )
    if proof_target["profile_lifecycle"] not in set(
        controlled_proof_policy["eligible_profile_statuses"]
    ):
        errors.append(
            f"{durable_label}: controlled proof target lifecycle is not eligible under the dev-integration policy"
        )
    profile_id = proof_target["profile_id"]
    profile_payload = developer_integration_profiles["profiles"].get(profile_id)
    if profile_payload is None:
        errors.append(
            f"{durable_label}: controlled proof references unknown dev-integration profile {profile_id!r}"
        )
    else:
        if profile_payload["lifecycle"] != runtime_posture["lifecycle"]:
            errors.append(
                f"{durable_label}: current runtime lifecycle must match profile {profile_id!r} registry lifecycle"
            )
        if profile_payload.get("build_admission", {}).get("self_serve_launch_allowed") is not False:
            errors.append(
                f"{durable_label}: controlled proof profile must keep build_admission.self_serve_launch_allowed=false"
            )
    if proof_target["profile_lifecycle"] in set(
        developer_integration_policy["profile_lifecycle"]["self_serve_statuses"]
    ):
        errors.append(
            f"{durable_label}: controlled proof cannot use a self-serve profile lifecycle"
        )
    proof_allowlist = {
        (item["definition_id"], item["definition_version"])
        for item in controlled_proof["definition_allowlist"]
    }
    expected_proof_allowlist = {
        (safe_definition["definition_id"], safe_definition["definition_version"])
    } if safe_definition else set()
    if proof_allowlist != expected_proof_allowlist:
        errors.append(
            f"{durable_label}: controlled proof definition allowlist must contain only the safe runtime proof"
        )
    if set(controlled_proof["required_scenarios"]) != CONTROLLED_PROOF_REQUIRED_SCENARIOS:
        errors.append(
            f"{durable_label}: controlled proof required_scenarios must preserve the complete commissioning set"
        )
    expected_session_contract = {
        "authorization_consumption": "atomic-single-use",
        "one_session_per_authorization": True,
        "exact_scenario_execution_set_required": True,
        "scenario_execution_ids_unique": True,
        "required_receipt_owners_declared_per_execution": True,
        "retries_cancels_replays_and_dedup_bound_to_session_and_execution": True,
    }
    if controlled_proof.get("commissioning_session") != expected_session_contract:
        errors.append(
            f"{durable_label}: controlled proof must bind one consumed commissioning session and its exact executions"
        )
    if controlled_proof.get("receipt_owners") != (
        CONTROLLED_PROOF_REQUIRED_RECEIPT_OWNER_ORDER
    ):
        errors.append(
            f"{durable_label}: controlled proof receipt owners must preserve the complete owner set"
        )
    if set(controlled_proof["permitted_action_allowlist"]) != CONTROLLED_PROOF_PERMITTED_ACTIONS:
        errors.append(
            f"{durable_label}: controlled proof permitted_action_allowlist must preserve the bounded action set"
        )
    if set(controlled_proof["required_stop_conditions"]) != CONTROLLED_PROOF_REQUIRED_STOP_CONDITIONS:
        errors.append(
            f"{durable_label}: controlled proof required_stop_conditions must preserve every fail-stop boundary"
        )
    for source_role in ("permit_issuer", "executor"):
        reviewed_source = controlled_proof.get(source_role, {})
        if (
            reviewed_source.get("owner_repo") != "platform-engineering"
            or reviewed_source.get("source_review_work_item_ref")
            != "openproject://work_packages/792"
            or reviewed_source.get(
                "merged_source_required_before_security_authorization"
            )
            is not True
        ):
            errors.append(
                f"{durable_label}: controlled proof {source_role.replace('_', ' ')} "
                "must bind Platform source review #792 before Security authorization"
            )
    terminal_cleanup = controlled_proof.get("terminal_cleanup_authority", {})
    if (
        terminal_cleanup.get("mode") != "exact-baseline-restore-only"
        or terminal_cleanup.get("applies_to")
        != "already-started-commissioning-session"
        or terminal_cleanup.get("trigger_scope")
        != "any-triggered-stop-condition"
        or terminal_cleanup.get("scope_binding") != "exact-captured-restore-scope"
        or terminal_cleanup.get("new_proof_actions_denied") is not True
        or terminal_cleanup.get("scope_expansion_denied") is not True
        or terminal_cleanup.get("runtime_retention_denied") is not True
        or terminal_cleanup.get("permitted_actions")
        != CONTROLLED_PROOF_TERMINAL_CLEANUP_ACTIONS
        or terminal_cleanup.get("termination_conditions")
        != CONTROLLED_PROOF_TERMINAL_CLEANUP_TERMINATION_CONDITIONS
    ):
        errors.append(
            f"{durable_label}: every controlled-proof stop condition must preserve only session-bound exact-baseline cleanup authority"
        )
    pre_run_evidence = controlled_proof["evidence_phases"]["pre_run_authorization"]
    post_run_evidence = controlled_proof["evidence_phases"]["post_run_activation_review"]
    if (
        pre_run_evidence["grants_profile_activation"]
        or pre_run_evidence["grants_definition_activation"]
        or pre_run_evidence["reusable_as_post_run_activation_evidence"]
    ):
        errors.append(
            f"{durable_label}: pre-run proof authorization cannot grant or substitute for activation"
        )
    if (
        not post_run_evidence[
            "authorization_artifact_digest_must_match_consumed_permit"
        ]
        or not post_run_evidence[
            "passed_receipt_pairs_must_match_authorization"
        ]
        or not post_run_evidence[
            "owner_receipts_bind_authorization_session_execution_and_result"
        ]
        or not post_run_evidence["permit_timeline_must_validate"]
        or not post_run_evidence["exact_baseline_restore_required"]
        or not post_run_evidence["baseline_snapshot_must_match_authorization"]
        or not post_run_evidence["security_acceptance_required"]
        or post_run_evidence.get("schema_ref") != CONTROLLED_PROOF_RESULT_SCHEMA_REF
        or post_run_evidence["profile_activation_allowed_before_acceptance"]
        or post_run_evidence["definition_activation_allowed_before_acceptance"]
    ):
        errors.append(
            f"{durable_label}: post-run activation review must require restore and Security acceptance before activation"
        )
    required_controlled_proof_denials = {
        "business workflow execution",
        "normal self-serve profile launch",
        "active profile projection during proof",
        "active definition projection during proof",
        "governed stage or production evidence claim",
        "retained runtime state without governed reclassification",
    }
    if not required_controlled_proof_denials.issubset(
        set(controlled_proof["denied_outcomes"])
    ):
        errors.append(
            f"{durable_label}: controlled proof denied_outcomes must preserve every maturity and scope boundary"
        )
    implementation_order = durable_orchestration["implementation_order"]
    if implementation_order["safe_runtime_proof"] != ["validation-readiness-run"]:
        errors.append(
            f"{durable_label}: implementation_order.safe_runtime_proof must start with validation-readiness-run"
        )
    if (
        not implementation_order["business_definitions"]
        or implementation_order["business_definitions"][0] != "delivery.refinement.apply"
    ):
        errors.append(
            f"{durable_label}: implementation_order.business_definitions must start with delivery.refinement.apply"
        )
    required_denied_claims = {
        "WGCF owns aggregate orchestration",
        "OOS is only an activity adapter",
        "Governance Operations Console calls Temporal directly",
        "Temporal owns business workflow policy",
        "a definition is active without admission evidence",
        "a local dev-integration run is governed stage or production evidence",
    }
    if not required_denied_claims.issubset(
        set(durable_orchestration["denied_authority_claims"])
    ):
        errors.append(
            f"{durable_label}: denied_authority_claims must preserve every authority and maturity guard"
        )

    expected_intake_statuses = {"out-of-scope", "proposed", "admitted"}
    if intake_statuses != expected_intake_statuses:
        errors.append(
            "contracts/intake-policy.yaml: statuses must be exactly out-of-scope, proposed, admitted"
        )
    expected_governed_intake_assist_ref = {
        "repo": "workspace-governance",
        "path": "contracts/governed-intake-assist.yaml",
    }
    actual_governed_intake_assist_ref = intake_policy["ai_suggestions"][
        "governed_intake_assist_contract"
    ]
    if actual_governed_intake_assist_ref != expected_governed_intake_assist_ref:
        errors.append(
            "contracts/intake-policy.yaml: ai_suggestions.governed_intake_assist_contract "
            "must point to workspace-governance/contracts/governed-intake-assist.yaml"
        )
    if governed_intake_assist["owner_repo"] != "workspace-governance":
        errors.append(
            "contracts/governed-intake-assist.yaml: owner_repo must be 'workspace-governance'"
        )
    primary_operator_surface = repo_root / governed_intake_assist["primary_operator_surface"]
    if primary_operator_surface.suffix != ".md" or not primary_operator_surface.exists():
        errors.append(
            "contracts/governed-intake-assist.yaml: primary_operator_surface must point to an existing markdown operator surface"
        )
    governed_intake_consumer = governed_intake_assist["consumer"]
    governed_output_schema_ref = {
        "repo": "workspace-governance",
        "path": "contracts/schemas/intake-ai-suggestion.schema.json",
    }
    if governed_intake_consumer["caller_id"] != "workspace-governance/intake-assist":
        errors.append(
            "contracts/governed-intake-assist.yaml: consumer.caller_id must be workspace-governance/intake-assist"
        )
    if governed_intake_consumer["caller_repo"] != "workspace-governance":
        errors.append(
            "contracts/governed-intake-assist.yaml: consumer.caller_repo must be workspace-governance"
        )
    if governed_intake_consumer["purpose"] != "workspace-intake-assist":
        errors.append(
            "contracts/governed-intake-assist.yaml: consumer.purpose must be workspace-intake-assist"
        )
    if governed_intake_consumer["profile_id"] != "intake-classifier-v1":
        errors.append(
            "contracts/governed-intake-assist.yaml: consumer.profile_id must be intake-classifier-v1"
        )
    if governed_intake_consumer["invocation_path"] != "governed-ai-gateway":
        errors.append(
            "contracts/governed-intake-assist.yaml: consumer.invocation_path must be governed-ai-gateway"
        )
    if governed_intake_consumer["output_schema_ref"] != governed_output_schema_ref:
        errors.append(
            "contracts/governed-intake-assist.yaml: consumer.output_schema_ref must point to contracts/schemas/intake-ai-suggestion.schema.json"
        )
    if not (repo_root / governed_output_schema_ref["path"]).exists():
        errors.append(
            "contracts/governed-intake-assist.yaml: consumer.output_schema_ref path does not exist"
        )
    governed_contract_refs = governed_intake_assist["platform_contract_refs"]
    if (
        governed_contract_refs["profile_registry"]
        != intake_policy["ai_suggestions"]["governed_profile_registry"]
    ):
        errors.append(
            "contracts/governed-intake-assist.yaml: platform_contract_refs.profile_registry must match intake-policy governed_profile_registry"
        )
    expected_required_live_gates = {
        "profile-active",
        "access-plane-live",
        "identity-boundary-live",
        "audit-retention-live",
        "provider-egress-blocked",
        "security-delta-review-current",
    }
    activation_state = governed_intake_assist["activation_state"]
    if activation_state["source_contract_status"] != "source-defined":
        errors.append(
            "contracts/governed-intake-assist.yaml: activation_state.source_contract_status must be source-defined"
        )
    if activation_state["live_consumption_allowed"] is not False:
        errors.append(
            "contracts/governed-intake-assist.yaml: activation_state.live_consumption_allowed must remain false until live gates are proven"
        )
    if set(activation_state["required_live_gates"]) != expected_required_live_gates:
        errors.append(
            "contracts/governed-intake-assist.yaml: activation_state.required_live_gates must match the platform runtime-assist gate ids"
        )
    suggestion_contract = governed_intake_assist["suggestion_contract"]
    if suggestion_contract["authority"] != "suggestion-only":
        errors.append(
            "contracts/governed-intake-assist.yaml: suggestion_contract.authority must be suggestion-only"
        )
    if suggestion_contract["autonomous_mutation_allowed"] is not False:
        errors.append(
            "contracts/governed-intake-assist.yaml: suggestion_contract.autonomous_mutation_allowed must be false"
        )
    if suggestion_contract["structured_output_schema_ref"] != governed_output_schema_ref:
        errors.append(
            "contracts/governed-intake-assist.yaml: suggestion_contract.structured_output_schema_ref must match the consumer output schema"
        )
    if set(suggestion_contract["allowed_decisions"]) != expected_intake_statuses:
        errors.append(
            "contracts/governed-intake-assist.yaml: suggestion_contract.allowed_decisions must match intake-policy statuses"
        )
    for denied_action in (
        "model-output-direct-mutation",
        "direct-provider-client",
        "repo-local-provider-secret",
        "unaudited-operator-acceptance",
        "rejected-suggestion-register-write",
    ):
        if denied_action not in suggestion_contract["denied_actions"]:
            errors.append(
                "contracts/governed-intake-assist.yaml: suggestion_contract.denied_actions "
                f"must include {denied_action!r}"
            )
    operator_acceptance = governed_intake_assist["operator_acceptance"]
    if operator_acceptance["human_approval_required"] is not True:
        errors.append(
            "contracts/governed-intake-assist.yaml: operator_acceptance.human_approval_required must be true"
        )
    if operator_acceptance["acceptance_required_before_workspace_truth_update"] is not True:
        errors.append(
            "contracts/governed-intake-assist.yaml: operator_acceptance.acceptance_required_before_workspace_truth_update must be true"
        )
    if set(operator_acceptance["allowed_acceptance_states_for_truth_update"]) != {
        "accepted",
        "overridden",
    }:
        errors.append(
            "contracts/governed-intake-assist.yaml: operator_acceptance.allowed_acceptance_states_for_truth_update must be exactly accepted and overridden"
        )
    if operator_acceptance["override_requires_reason"] is not True:
        errors.append(
            "contracts/governed-intake-assist.yaml: operator_acceptance.override_requires_reason must be true"
        )
    expected_operator_acceptance_fields = {
        "accepted_by",
        "accepted_at",
        "decision_id",
        "suggested_decision",
        "operator_decision",
        "acceptance_state",
        "audit_ref",
    }
    if set(operator_acceptance["required_fields"]) != expected_operator_acceptance_fields:
        errors.append(
            "contracts/governed-intake-assist.yaml: operator_acceptance.required_fields must be exactly "
            + ", ".join(sorted(expected_operator_acceptance_fields))
        )
    workspace_truth_updates = governed_intake_assist["workspace_truth_updates"]
    if set(workspace_truth_updates["allowed_targets"]) != {"contracts/intake-register.yaml"}:
        errors.append(
            "contracts/governed-intake-assist.yaml: workspace_truth_updates.allowed_targets must be exactly contracts/intake-register.yaml"
        )
    if set(workspace_truth_updates["allowed_decision_sources"]) != {"operator", "ai-suggested"}:
        errors.append(
            "contracts/governed-intake-assist.yaml: workspace_truth_updates.allowed_decision_sources must be exactly operator and ai-suggested"
        )
    if workspace_truth_updates["ai_suggested_requires_active_profile"] is not True:
        errors.append(
            "contracts/governed-intake-assist.yaml: workspace_truth_updates.ai_suggested_requires_active_profile must be true"
        )
    if workspace_truth_updates["ai_suggested_requires_operator_acceptance"] is not True:
        errors.append(
            "contracts/governed-intake-assist.yaml: workspace_truth_updates.ai_suggested_requires_operator_acceptance must be true"
        )
    expected_governed_audit_fields = {
        "event_time",
        "correlation_id",
        "caller_identity",
        "operator_identity",
        "approved_profile_id",
        "invocation_path",
        "purpose",
        "output_schema_ref",
        "policy_decision",
        "outcome",
        "operator_acceptance_state",
        "override_reason",
    }
    if set(governed_intake_assist["audit_contract"]["required_fields"]) != expected_governed_audit_fields:
        errors.append(
            "contracts/governed-intake-assist.yaml: audit_contract.required_fields must match the platform governed-AI audit minimum"
        )

    expected_devint_actions = {"up", "status", "smoke", "down", "reset", "promote_check"}
    lane = developer_integration_policy["lane"]
    profile_lifecycle = developer_integration_policy["profile_lifecycle"]
    request_admission = developer_integration_policy["request_admission"]
    live_miss_escalation = developer_integration_policy["live_miss_escalation"]
    if lane["id"] != "dev-integration":
        errors.append("contracts/developer-integration-policy.yaml: lane.id must be 'dev-integration'")
    for owner_key in ("standard_owner", "runtime_owner"):
        if lane[owner_key] not in active_repos:
            errors.append(
                f"contracts/developer-integration-policy.yaml: {owner_key} {lane[owner_key]!r} is not an active repo"
            )
    expected_devint_statuses = {
        "proposed",
        "build-admitted",
        "active",
        "suspended",
        "retired",
    }
    if set(profile_lifecycle["statuses"]) != expected_devint_statuses:
        errors.append(
            "contracts/developer-integration-policy.yaml: profile_lifecycle.statuses must be exactly "
            + ", ".join(sorted(expected_devint_statuses))
        )
    if set(profile_lifecycle["implementation_statuses"]) != {"build-admitted", "active"}:
        errors.append(
            "contracts/developer-integration-policy.yaml: profile_lifecycle.implementation_statuses must be exactly active, build-admitted"
        )
    if set(profile_lifecycle["self_serve_statuses"]) != {"active"}:
        errors.append(
            "contracts/developer-integration-policy.yaml: profile_lifecycle.self_serve_statuses must be exactly active"
        )
    if set(profile_lifecycle["build_admission_required_for"]) != {"build-admitted"}:
        errors.append(
            "contracts/developer-integration-policy.yaml: profile_lifecycle.build_admission_required_for must be exactly build-admitted"
        )
    expected_platform_acceptance_statuses = {
        "build-admitted",
        "active",
        "suspended",
        "retired",
    }
    if set(profile_lifecycle["platform_acceptance_required_for"]) != expected_platform_acceptance_statuses:
        errors.append(
            "contracts/developer-integration-policy.yaml: profile_lifecycle.platform_acceptance_required_for must be exactly "
            + ", ".join(sorted(expected_platform_acceptance_statuses))
        )
    adapter_owner = request_admission["current_request_adapter"]["owner_repo"]
    if adapter_owner not in active_repos:
        errors.append(
            "contracts/developer-integration-policy.yaml: request_admission.current_request_adapter.owner_repo "
            f"{adapter_owner!r} is not an active repo"
        )
    if live_miss_escalation["owner_repo"] not in active_repos:
        errors.append(
            "contracts/developer-integration-policy.yaml: live_miss_escalation.owner_repo "
            f"{live_miss_escalation['owner_repo']!r} is not an active repo"
        )
    if set(developer_integration_policy["required_actions"]) != expected_devint_actions:
        errors.append(
            "contracts/developer-integration-policy.yaml: required_actions must be exactly "
            + ", ".join(sorted(expected_devint_actions))
        )
    delegation_governance = delegation_policy["governance"]
    if delegation_governance["policy_owner_repo"] not in active_repos:
        errors.append(
            "contracts/delegation-policy.yaml: governance.policy_owner_repo "
            f"{delegation_governance['policy_owner_repo']!r} is not an active repo"
        )
    if delegation_governance["policy_owner_repo"] != "workspace-governance":
        errors.append(
            "contracts/delegation-policy.yaml: governance.policy_owner_repo must be 'workspace-governance'"
        )
    for skill_name in delegation_governance["required_skills"]:
        if skill_name not in registered_skills:
            errors.append(
                f"contracts/delegation-policy.yaml: governance.required_skills references unknown skill {skill_name!r}"
            )
    if not delegation_governance["operator_surface_path"].endswith(".md"):
        errors.append(
            "contracts/delegation-policy.yaml: governance.operator_surface_path must point to a markdown instruction surface"
        )
    elif not (repo_root / delegation_governance["operator_surface_path"]).exists():
        errors.append(
            "contracts/delegation-policy.yaml: governance.operator_surface_path "
            f"{delegation_governance['operator_surface_path']!r} does not exist"
        )
    if not delegation_governance["journal_root"].startswith("reviews/"):
        errors.append(
            "contracts/delegation-policy.yaml: governance.journal_root must live under reviews/"
        )
    packet_kinds = set(delegation_policy["packet"]["delegate_kinds"])
    expected_packet_kinds = {"exploration", "implementation", "verification"}
    if packet_kinds != expected_packet_kinds:
        errors.append(
            "contracts/delegation-policy.yaml: packet.delegate_kinds must be exactly exploration, implementation, verification"
        )
    required_packet_fields = set(delegation_policy["packet"]["required_fields"])
    expected_packet_fields = {
        "work_item_ref",
        "summary",
        "owner_repo",
        "allowed_write_paths",
        "expected_outputs",
        "proof_expectation",
        "forbidden_actions",
    }
    if required_packet_fields != expected_packet_fields:
        errors.append(
            "contracts/delegation-policy.yaml: packet.required_fields must be exactly "
            + ", ".join(sorted(expected_packet_fields))
        )
    required_journal_fields = set(delegation_policy["audit_journal"]["required_fields"])
    expected_journal_fields = {
        "delegation_id",
        "created_on",
        "owner_repo",
        "work_item_ref",
        "task_class",
        "main_agent",
        "packets",
        "integration_outcome",
    }
    if required_journal_fields != expected_journal_fields:
        errors.append(
            "contracts/delegation-policy.yaml: audit_journal.required_fields must be exactly "
            + ", ".join(sorted(expected_journal_fields))
        )
    if "live-control" not in delegation_task_classes:
        errors.append("contracts/delegation-policy.yaml: task_classes must define 'live-control'")
    for task_class, payload in delegation_task_classes.items():
        if payload["max_sub_agents"] == 0 and payload["allows_delegated_write"]:
            errors.append(
                f"contracts/delegation-policy.yaml: task_class {task_class!r} cannot allow delegated write with max_sub_agents=0"
            )
    if delegation_task_classes.get("live-control", {}).get("max_sub_agents") != 0:
        errors.append("contracts/delegation-policy.yaml: task_class 'live-control' must keep max_sub_agents=0")
    if delegation_task_classes.get("live-control", {}).get("allows_delegated_write") is not False:
        errors.append("contracts/delegation-policy.yaml: task_class 'live-control' must not allow delegated write")
    if delegation_policy["future_enforcement_boundary"]["parked_architecture_ref"] != "openproject://work_packages/77":
        errors.append(
            "contracts/delegation-policy.yaml: future_enforcement_boundary.parked_architecture_ref must point to openproject://work_packages/77"
        )
    if work_home_routing["owner_repo"] != "workspace-governance":
        errors.append("contracts/work-home-routing.yaml: owner_repo must be 'workspace-governance'")
    expected_work_home_classes = set(work_home_classes.keys())
    if set(work_home_routing["classification_order"]) != expected_work_home_classes:
        errors.append(
            "contracts/work-home-routing.yaml: classification_order must list every class exactly once"
        )
    for class_id, payload in work_home_classes.items():
        if payload["routing_home"] not in work_home_routing_homes:
            errors.append(
                "contracts/work-home-routing.yaml: class "
                f"{class_id!r} references unknown routing_home {payload['routing_home']!r}"
            )
    for example in work_home_routing["examples"]:
        if example["class"] not in work_home_classes:
            errors.append(
                "contracts/work-home-routing.yaml: example scenario "
                f"{example['scenario']!r} references unknown class {example['class']!r}"
            )
        if example["owner_repo"] not in active_repos:
            errors.append(
                "contracts/work-home-routing.yaml: example scenario "
                f"{example['scenario']!r} references inactive owner_repo {example['owner_repo']!r}"
            )
    if governance_engine_foundation["owner_repo"] != "workspace-governance":
        errors.append(
            "contracts/governance-engine-foundation.yaml: owner_repo must be 'workspace-governance'"
        )
    expected_source_layers = {
        "workspace-root",
        "contracts",
        "skills",
        "scripts",
        "generated",
    }
    actual_source_layers = {
        entry["id"] for entry in governance_engine_foundation["source_of_truth_layers"]
    }
    if actual_source_layers != expected_source_layers:
        errors.append(
            "contracts/governance-engine-foundation.yaml: source_of_truth_layers must be exactly "
            + ", ".join(sorted(expected_source_layers))
        )
    expected_tenant_surfaces = {
        "intake-register",
        "developer-integration-profiles",
        "exceptions",
        "owner-repo-template-records",
        "owner-repo-workflows",
        "security-review-outputs",
    }
    actual_tenant_surfaces = {
        entry["id"] for entry in governance_engine_foundation["tenant_instance_surfaces"]
    }
    if actual_tenant_surfaces != expected_tenant_surfaces:
        errors.append(
            "contracts/governance-engine-foundation.yaml: tenant_instance_surfaces must be exactly "
            + ", ".join(sorted(expected_tenant_surfaces))
        )
    if (
        governance_engine_foundation["compatibility_boundary"]["boundary_map_ref"]
        != "contracts/governance-engine-boundary-map.yaml"
    ):
        errors.append(
            "contracts/governance-engine-foundation.yaml: compatibility_boundary.boundary_map_ref must point to contracts/governance-engine-boundary-map.yaml"
        )
    expected_stable_entrypoints = {
        "workspace-root/AGENTS.md",
        "workspace-root/README.md",
        "workspace-root/ARCHITECTURE.md",
        "scripts/sync_workspace_root.py",
        "scripts/install_skills.py",
        "scripts/validate_contracts.py",
        "scripts/audit_workspace_layout.py",
    }
    actual_stable_entrypoints = set(
        governance_engine_foundation["compatibility_boundary"]["stable_entrypoints"]
    )
    if actual_stable_entrypoints != expected_stable_entrypoints:
        errors.append(
            "contracts/governance-engine-foundation.yaml: compatibility_boundary.stable_entrypoints must be exactly "
            + ", ".join(sorted(expected_stable_entrypoints))
        )
    if (
        governance_engine_foundation["shadow_parity"]["contract_ref"]
        != "contracts/governance-engine-shadow-parity.yaml"
    ):
        errors.append(
            "contracts/governance-engine-foundation.yaml: shadow_parity.contract_ref must point to contracts/governance-engine-shadow-parity.yaml"
        )
    if governance_engine_foundation["packaging_model"]["central_repo"] != "workspace-governance":
        errors.append(
            "contracts/governance-engine-foundation.yaml: packaging_model.central_repo must be 'workspace-governance'"
        )
    if (
        governance_engine_foundation["packaging_model"]["output_manifest_ref"]
        != "contracts/governance-engine-output-manifest.yaml"
    ):
        errors.append(
            "contracts/governance-engine-foundation.yaml: packaging_model.output_manifest_ref must point to contracts/governance-engine-output-manifest.yaml"
        )
    expected_allowed_seams = {
        "product runtime behavior",
        "component interface contracts",
        "packaging and build-tooling constraints",
        "repo-local protocol or artifact formats",
    }
    actual_allowed_seams = set(
        governance_engine_foundation["packaging_model"]["custom_validation_allowed_seams"]
    )
    if actual_allowed_seams != expected_allowed_seams:
        errors.append(
            "contracts/governance-engine-foundation.yaml: packaging_model.custom_validation_allowed_seams must be exactly "
            + ", ".join(sorted(expected_allowed_seams))
        )
    expected_forbidden_validation_classes = {
        "central owner and routing truth",
        "central lifecycle and intake semantics",
        "governed AI model policy",
        "cross-repo evidence and review obligations",
    }
    actual_forbidden_validation_classes = set(
        governance_engine_foundation["packaging_model"]["custom_validation_forbidden_classes"]
    )
    if actual_forbidden_validation_classes != expected_forbidden_validation_classes:
        errors.append(
            "contracts/governance-engine-foundation.yaml: packaging_model.custom_validation_forbidden_classes must be exactly "
            + ", ".join(sorted(expected_forbidden_validation_classes))
        )
    if governance_engine_output_manifest["owner_repo"] != "workspace-governance":
        errors.append(
            "contracts/governance-engine-output-manifest.yaml: owner_repo must be 'workspace-governance'"
        )
    compatibility_controls = governance_engine_output_manifest["compatibility_controls"]
    if compatibility_controls["materialization_default"] != "check-first":
        errors.append(
            "contracts/governance-engine-output-manifest.yaml: compatibility_controls.materialization_default must be 'check-first'"
        )
    if compatibility_controls["wgcf_detection_mode"] != "plan-before-materialize":
        errors.append(
            "contracts/governance-engine-output-manifest.yaml: compatibility_controls.wgcf_detection_mode must be 'plan-before-materialize'"
        )
    for required_flag in (
        "require_explicit_family",
        "require_manifest_output_match",
        "require_check_before_write",
    ):
        if compatibility_controls[required_flag] is not True:
            errors.append(
                "contracts/governance-engine-output-manifest.yaml: "
                f"compatibility_controls.{required_flag} must be true"
            )
    if set(compatibility_controls["allowed_write_profiles"]) != {"break-glass"}:
        errors.append(
            "contracts/governance-engine-output-manifest.yaml: compatibility_controls.allowed_write_profiles must be exactly break-glass"
        )
    expected_denied_without_profile = {
        "implicit generated artifact materialization",
        "broad all-output writes without selected family",
        "WGCF materialization outside check mode",
    }
    if set(compatibility_controls["denied_without_profile"]) != expected_denied_without_profile:
        errors.append(
            "contracts/governance-engine-output-manifest.yaml: compatibility_controls.denied_without_profile must be exactly "
            + ", ".join(sorted(expected_denied_without_profile))
        )
    manifest_families = {
        entry["id"]: entry for entry in governance_engine_output_manifest["emission_families"]
    }
    expected_manifest_family_ids = {
        "workspace-root-sync",
        "installed-skills",
        "generated-governance-artifacts",
    }
    if set(manifest_families) != expected_manifest_family_ids:
        errors.append(
            "contracts/governance-engine-output-manifest.yaml: emission_families must be exactly "
            + ", ".join(sorted(expected_manifest_family_ids))
        )
    foundation_source_layers = actual_source_layers
    for family_id, payload in manifest_families.items():
        source_layers = set(payload["source_layers"])
        if not source_layers.issubset(foundation_source_layers):
            errors.append(
                "contracts/governance-engine-output-manifest.yaml: "
                f"{family_id} source_layers must stay within governance-engine source_of_truth_layers"
            )
        emitter_path = repo_root / payload["emitter"]
        if not emitter_path.exists():
            errors.append(
                "contracts/governance-engine-output-manifest.yaml: "
                f"{family_id} emitter path {payload['emitter']!r} does not exist"
            )
    workspace_root_family = manifest_families.get("workspace-root-sync")
    if workspace_root_family:
        expected_sync_outputs = {
            ("workspace-root/ARCHITECTURE.md", "ARCHITECTURE.md", "text"),
            ("workspace-root/README.md", "README.md", "text"),
            ("workspace-root/AGENTS.md", "AGENTS.md", "text"),
            ("scripts/audit_workspace_layout.py", "_workspace_tools/audit_workspace_layout.py", "text"),
        }
        actual_sync_outputs = {
            (entry.get("source_path"), entry.get("emitted_path"), entry.get("format"))
            for entry in workspace_root_family.get("outputs", [])
        }
        if actual_sync_outputs != expected_sync_outputs:
            errors.append(
                "contracts/governance-engine-output-manifest.yaml: workspace-root-sync outputs must match the current canonical workspace-root materialization set"
            )
    installed_skills_family = manifest_families.get("installed-skills")
    if installed_skills_family:
        if installed_skills_family["source_contract"] != "contracts/skills.yaml":
            errors.append(
                "contracts/governance-engine-output-manifest.yaml: installed-skills.source_contract must be contracts/skills.yaml"
            )
        if installed_skills_family["managed_manifest_filename"] != ".workspace-governance-skills.json":
            errors.append(
                "contracts/governance-engine-output-manifest.yaml: installed-skills.managed_manifest_filename must be .workspace-governance-skills.json"
            )
        if installed_skills_family["target_root_default"] != "~/.codex/skills":
            errors.append(
                "contracts/governance-engine-output-manifest.yaml: installed-skills.target_root_default must be ~/.codex/skills"
            )
    generated_artifacts_family = manifest_families.get("generated-governance-artifacts")
    if generated_artifacts_family:
        expected_generated_outputs = {
            ("system_map", "generated/system-map.yaml", "yaml"),
            ("resolved_owner_map", "generated/resolved-owner-map.json", "json"),
            ("resolved_dependency_graph", "generated/resolved-dependency-graph.json", "json"),
            ("stale_content_rules", "generated/stale-content-rules.json", "json"),
            ("governance_engine_boundary_map", "generated/governance-engine-boundary-map.json", "json"),
        }
        actual_generated_outputs = {
            (entry["id"], entry.get("emitted_path"), entry.get("format"))
            for entry in generated_artifacts_family.get("outputs", [])
        }
        if actual_generated_outputs != expected_generated_outputs:
            errors.append(
                "contracts/governance-engine-output-manifest.yaml: generated-governance-artifacts outputs must match the current generated artifact set"
            )
    if governance_engine_boundary_map["owner_repo"] != "workspace-governance":
        errors.append(
            "contracts/governance-engine-boundary-map.yaml: owner_repo must be 'workspace-governance'"
        )
    if set(governance_engine_boundary_map["authoring_paths"]) != {
        "workspace-root/",
        "contracts/",
        "skills-src/",
        "scripts/",
    }:
        errors.append(
            "contracts/governance-engine-boundary-map.yaml: authoring_paths must be exactly workspace-root/, contracts/, skills-src/, scripts/"
        )
    if set(governance_engine_boundary_map["generated_paths"]) != {"generated/"}:
        errors.append(
            "contracts/governance-engine-boundary-map.yaml: generated_paths must be exactly generated/"
        )
    expected_tenant_instance_paths = {
        "contracts/intake-register.yaml",
        "contracts/developer-integration-profiles.yaml",
        "contracts/exceptions.yaml",
    }
    if set(governance_engine_boundary_map["tenant_instance_paths"]) != expected_tenant_instance_paths:
        errors.append(
            "contracts/governance-engine-boundary-map.yaml: tenant_instance_paths must be exactly "
            + ", ".join(sorted(expected_tenant_instance_paths))
        )
    if set(governance_engine_boundary_map["external_instance_surfaces"]) != {
        "owner-repo primary operator surfaces",
        "owner-repo template records",
        "security-architecture review artifacts",
    }:
        errors.append(
            "contracts/governance-engine-boundary-map.yaml: external_instance_surfaces must be exactly owner-repo primary operator surfaces, owner-repo template records, security-architecture review artifacts"
        )
    expected_live_materialized_outputs = {
        "ARCHITECTURE.md",
        "README.md",
        "AGENTS.md",
        "_workspace_tools/audit_workspace_layout.py",
        "~/.codex/skills/",
    }
    if set(governance_engine_boundary_map["live_materialized_outputs"]) != expected_live_materialized_outputs:
        errors.append(
            "contracts/governance-engine-boundary-map.yaml: live_materialized_outputs must be exactly "
            + ", ".join(sorted(expected_live_materialized_outputs))
        )
    expected_current_coupling_points = {
        "workspace-root-live-materialization": {
            "description": "workspace bootstrap files are still materialized directly from this repo into the live workspace root",
            "impacted_surfaces": {
                "workspace-root/ARCHITECTURE.md",
                "workspace-root/README.md",
                "workspace-root/AGENTS.md",
                "scripts/sync_workspace_root.py",
            },
        },
        "live-skill-installation": {
            "description": "managed skills are still installed directly from this repo into the live Codex skill root",
            "impacted_surfaces": {
                "skills-src/",
                "contracts/skills.yaml",
                "scripts/install_skills.py",
            },
        },
        "contract-driven-generated-artifacts": {
            "description": "generated ownership, dependency, stale-content, and boundary artifacts are emitted from this repo and consumed across the workspace",
            "impacted_surfaces": {
                "generated/",
                "contracts/governance-engine-output-manifest.yaml",
                "scripts/validate_cross_repo_truth.py",
            },
        },
        "external-review-and-operator-surfaces": {
            "description": "extraction decisions still depend on external owner-repo operator surfaces and security review artifacts that remain outside generated copies",
            "impacted_surfaces": {
                "owner-repo primary operator surfaces",
                "security-architecture review artifacts",
                "contracts/governance-engine-extraction-gate.yaml",
            },
        },
        "owner-repo-template-record-surfaces": {
            "description": "validation planning must consume repo-owned TEMPLATE.* records without turning them into generated workspace copies",
            "impacted_surfaces": {
                "owner-repo TEMPLATE.* records",
                "contracts/repo-rules/",
                "docs/governance-engine-foundation.md",
            },
        },
    }
    actual_current_coupling_points = {
        entry["coupling_id"]: {
            "description": entry["description"],
            "impacted_surfaces": set(entry["impacted_surfaces"]),
        }
        for entry in governance_engine_boundary_map["current_coupling_points"]
    }
    if set(actual_current_coupling_points) != set(expected_current_coupling_points):
        errors.append(
            "contracts/governance-engine-boundary-map.yaml: current_coupling_points must define the current workspace-root-live-materialization, live-skill-installation, contract-driven-generated-artifacts, external-review-and-operator-surfaces, and owner-repo-template-record-surfaces entries"
        )
    else:
        for coupling_id, expected in expected_current_coupling_points.items():
            actual = actual_current_coupling_points[coupling_id]
            if actual["description"] != expected["description"]:
                errors.append(
                    f"contracts/governance-engine-boundary-map.yaml: current_coupling_points[{coupling_id}].description must be {expected['description']!r}"
                )
            if actual["impacted_surfaces"] != expected["impacted_surfaces"]:
                errors.append(
                    "contracts/governance-engine-boundary-map.yaml: "
                    f"current_coupling_points[{coupling_id}].impacted_surfaces must be exactly "
                    + ", ".join(sorted(expected["impacted_surfaces"]))
                )
    expected_standalone_packaging_prerequisites = {
        "package-identity-and-versioning": {
            "threshold": "standalone package identity, versioning authority, and release contract are explicit before extraction starts",
            "evidence_surfaces": {
                "contracts/governance-engine-extraction-gate.yaml",
                "contracts/governance-engine-output-manifest.yaml",
            },
        },
        "install-and-materialization-surface": {
            "threshold": "installation can materialize workspace-root files, live skills, and generated artifacts without relying on repo-local convenience",
            "evidence_surfaces": {
                "scripts/materialize_governance_engine_outputs.py",
                "contracts/governance-engine-output-manifest.yaml",
            },
        },
        "tenant-consumption-contract": {
            "threshold": "tenant-instance consumers can declare required inputs and compatibility expectations without redefining engine-owned truth",
            "evidence_surfaces": {
                "contracts/governance-engine-boundary-map.yaml",
                "docs/governance-engine-foundation.md",
            },
        },
        "compatibility-shim-plan": {
            "threshold": "stable operator entrypoints keep working or have explicit compatibility shims during extraction",
            "evidence_surfaces": {
                "contracts/governance-engine-foundation.yaml",
                "docs/governance-engine-foundation.md",
            },
        },
        "security-delta-refresh": {
            "threshold": "a fresh security delta review is scheduled for the actual extraction package and trust-boundary change",
            "evidence_surfaces": {
                "security-architecture review artifacts",
            },
        },
        "template-family-consumption-contract": {
            "threshold": "record-template family ownership, expected shape, unknown-template handling, and validation-planner consumption rules are explicit before runtime extraction",
            "evidence_surfaces": {
                "contracts/repo-rules/",
                "docs/governance-engine-foundation.md",
            },
        },
    }
    actual_standalone_packaging_prerequisites = {
        entry["prerequisite_id"]: {
            "threshold": entry["threshold"],
            "evidence_surfaces": set(entry["evidence_surfaces"]),
        }
        for entry in governance_engine_boundary_map["standalone_packaging_prerequisites"]
    }
    if set(actual_standalone_packaging_prerequisites) != set(expected_standalone_packaging_prerequisites):
        errors.append(
            "contracts/governance-engine-boundary-map.yaml: standalone_packaging_prerequisites must define the current package-identity-and-versioning, install-and-materialization-surface, tenant-consumption-contract, compatibility-shim-plan, security-delta-refresh, and template-family-consumption-contract entries"
        )
    else:
        for prerequisite_id, expected in expected_standalone_packaging_prerequisites.items():
            actual = actual_standalone_packaging_prerequisites[prerequisite_id]
            if actual["threshold"] != expected["threshold"]:
                errors.append(
                    f"contracts/governance-engine-boundary-map.yaml: standalone_packaging_prerequisites[{prerequisite_id}].threshold must be {expected['threshold']!r}"
                )
            if actual["evidence_surfaces"] != expected["evidence_surfaces"]:
                errors.append(
                    "contracts/governance-engine-boundary-map.yaml: "
                    f"standalone_packaging_prerequisites[{prerequisite_id}].evidence_surfaces must be exactly "
                    + ", ".join(sorted(expected["evidence_surfaces"]))
                )
    projection = governance_engine_boundary_map["generated_projection"]
    if projection["output_id"] != "governance_engine_boundary_map":
        errors.append(
            "contracts/governance-engine-boundary-map.yaml: generated_projection.output_id must be governance_engine_boundary_map"
        )
    if projection["path"] != "generated/governance-engine-boundary-map.json":
        errors.append(
            "contracts/governance-engine-boundary-map.yaml: generated_projection.path must be generated/governance-engine-boundary-map.json"
        )
    if projection["emitter"] != "scripts/validate_cross_repo_truth.py":
        errors.append(
            "contracts/governance-engine-boundary-map.yaml: generated_projection.emitter must be scripts/validate_cross_repo_truth.py"
        )
    if governance_engine_shadow_parity["owner_repo"] != "workspace-governance":
        errors.append(
            "contracts/governance-engine-shadow-parity.yaml: owner_repo must be 'workspace-governance'"
        )
    expected_shadow_parity_refs = {
        "foundation_ref": "contracts/governance-engine-foundation.yaml",
        "boundary_map_ref": "contracts/governance-engine-boundary-map.yaml",
        "output_manifest_ref": "contracts/governance-engine-output-manifest.yaml",
        "validator_script": "scripts/validate_governance_engine_shadow_parity.py",
        "primary_surface_path": "docs/governance-engine-foundation.md",
    }
    for key, expected in expected_shadow_parity_refs.items():
        if governance_engine_shadow_parity[key] != expected:
            errors.append(
                f"contracts/governance-engine-shadow-parity.yaml: {key} must be {expected!r}"
            )
    expected_shadow_check_commands = {
        "workspace-root-sync": "python3 scripts/materialize_governance_engine_outputs.py workspace-root --check",
        "installed-skills": "python3 scripts/materialize_governance_engine_outputs.py skills --check",
        "generated-governance-artifacts": "python3 scripts/materialize_governance_engine_outputs.py generated --check",
        "compatibility-entrypoints": "python3 scripts/validate_governance_engine_shadow_parity.py",
    }
    actual_shadow_checks = {
        entry["id"]: entry["command"]
        for entry in governance_engine_shadow_parity["required_checks"]
    }
    if actual_shadow_checks != expected_shadow_check_commands:
        errors.append(
            "contracts/governance-engine-shadow-parity.yaml: required_checks must define the current workspace-root, installed-skills, generated-governance-artifacts, and compatibility-entrypoints commands"
        )
    expected_cutover_checks = {
        "workspace-root-sync",
        "installed-skills",
        "generated-governance-artifacts",
        "compatibility-entrypoints",
    }
    if set(governance_engine_shadow_parity["cutover_gate"]["required_clean_checks"]) != expected_cutover_checks:
        errors.append(
            "contracts/governance-engine-shadow-parity.yaml: cutover_gate.required_clean_checks must be exactly "
            + ", ".join(sorted(expected_cutover_checks))
        )
    if (
        governance_engine_shadow_parity["cutover_gate"]["platform_gate_ref"]
        != "platform-engineering/docs/components/workspace-governance-control-fabric/validator-invocation-gates.md"
    ):
        errors.append(
            "contracts/governance-engine-shadow-parity.yaml: cutover_gate.platform_gate_ref must point to the platform WGCF validator invocation gates"
        )
    if (
        governance_engine_shadow_parity["cutover_gate"]["security_review_ref"]
        != "security-architecture/docs/reviews/components/2026-05-01-wgcf-validator-invocation-and-artifact-custody.md"
    ):
        errors.append(
            "contracts/governance-engine-shadow-parity.yaml: cutover_gate.security_review_ref must point to the current WGCF validator invocation security delta"
        )
    expected_required_evidence = {
        "platform-profile-gates",
        "security-delta-current",
        "receipt-parity",
        "direct-rollback-retained",
        "raw-artifact-deny-by-default",
    }
    if set(governance_engine_shadow_parity["cutover_gate"]["required_evidence"]) != expected_required_evidence:
        errors.append(
            "contracts/governance-engine-shadow-parity.yaml: cutover_gate.required_evidence must be exactly "
            + ", ".join(sorted(expected_required_evidence))
        )
    expected_forbidden_conditions = {
        "duplicated workspace control-plane truth in repo-local copies",
        "stale live skill installs or missing managed skill manifest",
        "stale generated boundary projection",
        "missing stable compatibility entrypoints",
        "WGCF receipt parity missing for the target scope",
        "raw artifact custody enabled without security approval",
        "direct validator rollback removed before retirement eligibility",
        "WGCF mutation of ART, platform release, security acceptance, or workspace contracts",
    }
    if set(governance_engine_shadow_parity["cutover_gate"]["forbidden_conditions"]) != expected_forbidden_conditions:
        errors.append(
            "contracts/governance-engine-shadow-parity.yaml: cutover_gate.forbidden_conditions must be exactly "
            + ", ".join(sorted(expected_forbidden_conditions))
        )
    expected_profile_gates = {
        "devint-shadow",
        "stage-readiness",
        "prod-readiness",
        "break-glass",
    }
    actual_profile_gates = {
        entry["id"] for entry in governance_engine_shadow_parity["cutover_gate"]["profile_gates"]
    }
    if actual_profile_gates != expected_profile_gates:
        errors.append(
            "contracts/governance-engine-shadow-parity.yaml: cutover_gate.profile_gates must define devint-shadow, stage-readiness, prod-readiness, and break-glass"
        )
    expected_representative_scopes = {
        "workspace-governance",
        "delivery-art",
        "platform-runtime",
        "security-review",
    }
    actual_representative_scopes = {
        entry["id"]
        for entry in governance_engine_shadow_parity["cutover_gate"]["representative_scopes"]
    }
    if actual_representative_scopes != expected_representative_scopes:
        errors.append(
            "contracts/governance-engine-shadow-parity.yaml: cutover_gate.representative_scopes must define workspace-governance, delivery-art, platform-runtime, and security-review"
        )
    expected_cutover_states = {
        "shadow-only": False,
        "limited-cutover": False,
        "retirement-eligible": True,
    }
    actual_cutover_states = {
        entry["id"]: entry["may_retire_direct"]
        for entry in governance_engine_shadow_parity["cutover_gate"]["cutover_states"]
    }
    if actual_cutover_states != expected_cutover_states:
        errors.append(
            "contracts/governance-engine-shadow-parity.yaml: cutover_gate.cutover_states must define shadow-only, limited-cutover, and retirement-eligible with only retirement-eligible able to retire direct validators"
        )
    expected_retirement_eligibility = {
        "catalog_ref": "contracts/governance-validator-catalog.yaml",
        "requires_register_retirement_allowed": True,
        "receipt_parity_required": True,
        "direct_validator_rollback_required": True,
        "owner_closeout_required": True,
        "raw_artifact_custody_default": "deny",
    }
    if governance_engine_shadow_parity["cutover_gate"]["retirement_eligibility"] != expected_retirement_eligibility:
        errors.append(
            "contracts/governance-engine-shadow-parity.yaml: cutover_gate.retirement_eligibility must require catalog retirement allowance, receipt parity, rollback, owner closeout, and raw artifact custody default deny"
        )
    if governance_engine_extraction_gate["owner_repo"] != "workspace-governance":
        errors.append(
            "contracts/governance-engine-extraction-gate.yaml: owner_repo must be 'workspace-governance'"
        )
    expected_extraction_refs = {
        "foundation_ref": "contracts/governance-engine-foundation.yaml",
        "shadow_parity_ref": "contracts/governance-engine-shadow-parity.yaml",
        "boundary_map_ref": "contracts/governance-engine-boundary-map.yaml",
        "primary_surface_path": "docs/governance-engine-foundation.md",
        "security_review_ref": "security-architecture/docs/reviews/platform/2026-04-25-governance-engine-parity-extraction-and-runtime-readiness.md",
    }
    for key, expected in expected_extraction_refs.items():
        if governance_engine_extraction_gate[key] != expected:
            errors.append(
                f"contracts/governance-engine-extraction-gate.yaml: {key} must be {expected!r}"
            )
    expected_extraction_decision = {
        "default_outcome": "retain-integrated-governance-engine",
        "approved_outcome": "approve-standalone-governance-engine-extraction",
        "hard_gate_mode": "all_must_pass",
        "extraction_need_signal_threshold": "all_listed_signals_required",
    }
    extraction_decision = governance_engine_extraction_gate["extraction_decision"]
    for key, expected in expected_extraction_decision.items():
        if extraction_decision[key] != expected:
            errors.append(
                f"contracts/governance-engine-extraction-gate.yaml: extraction_decision.{key} must be {expected!r}"
            )
    expected_decision_record_requirements = {
        "record the retain-versus-extract outcome on the PI objective before extraction work begins",
        "cite the current parity and security evidence in the decision record",
        "keep bounded runtime activation deferred to epic #251 even when extraction is approved",
    }
    if set(extraction_decision["decision_record_requirements"]) != expected_decision_record_requirements:
        errors.append(
            "contracts/governance-engine-extraction-gate.yaml: extraction_decision.decision_record_requirements must be exactly "
            + ", ".join(sorted(expected_decision_record_requirements))
        )
    current_decision = governance_engine_extraction_gate["current_decision"]
    recorded_on = current_decision["recorded_on"]
    if isinstance(recorded_on, date):
        recorded_on_value = recorded_on.isoformat()
    elif isinstance(recorded_on, str):
        recorded_on_value = recorded_on
    else:
        recorded_on_value = None
    if recorded_on_value is None:
        errors.append(
            "contracts/governance-engine-extraction-gate.yaml: current_decision.recorded_on must be an ISO date"
        )
    else:
        try:
            date.fromisoformat(recorded_on_value)
        except ValueError:
            errors.append(
                "contracts/governance-engine-extraction-gate.yaml: current_decision.recorded_on must be an ISO date"
            )
    expected_current_decision_refs = {
        "recorded_by_work_item_ref": "openproject://work_packages/338",
        "recorded_from_feature_ref": "openproject://work_packages/339",
    }
    for key, expected in expected_current_decision_refs.items():
        if current_decision[key] != expected:
            errors.append(
                f"contracts/governance-engine-extraction-gate.yaml: current_decision.{key} must be {expected!r}"
            )
    allowed_current_outcomes = {
        extraction_decision["default_outcome"],
        extraction_decision["approved_outcome"],
    }
    if current_decision["outcome"] not in allowed_current_outcomes:
        errors.append(
            "contracts/governance-engine-extraction-gate.yaml: current_decision.outcome must be one of "
            + ", ".join(sorted(allowed_current_outcomes))
        )
    expected_hard_gate_checks = {
        "shadow-parity-clean": {
            "threshold": "active workspace shadow parity validator reads clean and required generated outputs are current",
            "evidence_sources": {
                "contracts/governance-engine-shadow-parity.yaml",
                "scripts/validate_governance_engine_shadow_parity.py",
            },
        },
        "boundary-projection-current": {
            "threshold": "generated boundary projection matches the current engine-versus-tenant split",
            "evidence_sources": {
                "contracts/governance-engine-boundary-map.yaml",
                "generated/governance-engine-boundary-map.json",
                "scripts/validate_cross_repo_truth.py",
            },
        },
        "stable-operator-entrypoints": {
            "threshold": "stable operator entrypoints remain unchanged or explicitly compatibility-shimmed",
            "evidence_sources": {
                "contracts/governance-engine-foundation.yaml",
                "docs/governance-engine-foundation.md",
                "scripts/validate_contracts.py",
            },
        },
        "security-delta-review-current": {
            "threshold": "current security review explicitly covers the parity boundary and proposed extraction delta",
            "evidence_sources": {
                "security-architecture/docs/reviews/platform/2026-04-25-governance-engine-parity-extraction-and-runtime-readiness.md",
            },
        },
        "governed-policy-stays-central": {
            "threshold": "repo-local validators and wiring do not redefine governed AI model-access policy",
            "evidence_sources": {
                "contracts/governance-engine-foundation.yaml",
                "scripts/validate_contracts.py",
            },
        },
    }
    actual_hard_gate_checks = {
        entry["gate_id"]: {
            "threshold": entry["threshold"],
            "evidence_sources": set(entry["evidence_sources"]),
        }
        for entry in governance_engine_extraction_gate["hard_gate_checks"]
    }
    if set(actual_hard_gate_checks) != set(expected_hard_gate_checks):
        errors.append(
            "contracts/governance-engine-extraction-gate.yaml: hard_gate_checks must define the current shadow-parity-clean, boundary-projection-current, stable-operator-entrypoints, security-delta-review-current, and governed-policy-stays-central checks"
        )
    else:
        for gate_id, expected in expected_hard_gate_checks.items():
            actual = actual_hard_gate_checks[gate_id]
            if actual["threshold"] != expected["threshold"]:
                errors.append(
                    f"contracts/governance-engine-extraction-gate.yaml: hard_gate_checks[{gate_id}].threshold must be {expected['threshold']!r}"
                )
            if actual["evidence_sources"] != expected["evidence_sources"]:
                errors.append(
                    "contracts/governance-engine-extraction-gate.yaml: "
                    f"hard_gate_checks[{gate_id}].evidence_sources must be exactly "
                    + ", ".join(sorted(expected["evidence_sources"]))
                )
    actual_current_hard_gate_results = {
        entry["gate_id"]: entry["status"]
        for entry in current_decision["hard_gate_results"]
    }
    if set(actual_current_hard_gate_results) != set(expected_hard_gate_checks):
        errors.append(
            "contracts/governance-engine-extraction-gate.yaml: current_decision.hard_gate_results must define the current shadow-parity-clean, boundary-projection-current, stable-operator-entrypoints, security-delta-review-current, and governed-policy-stays-central results"
        )
    else:
        invalid_hard_gate_statuses = {
            gate_id: status
            for gate_id, status in actual_current_hard_gate_results.items()
            if status not in {"passed", "failed"}
        }
        for gate_id, status in invalid_hard_gate_statuses.items():
            errors.append(
                "contracts/governance-engine-extraction-gate.yaml: "
                f"current_decision.hard_gate_results[{gate_id}].status must be 'passed' or 'failed', got {status!r}"
            )
    expected_extraction_need_signals = {
        "multi-instance-consumer-demand": {
            "threshold": "more than one governed workspace or tenant-instance consumer requires the same engine authoring layer",
            "evidence_sources": {
                "contracts/governance-engine-foundation.yaml",
                "contracts/governance-engine-boundary-map.yaml",
            },
        },
        "standalone-release-versioning-need": {
            "threshold": "standalone versioning or release cadence is required beyond the integrated workspace-governance repo",
            "evidence_sources": {
                "docs/governance-engine-foundation.md",
                "contracts/governance-engine-output-manifest.yaml",
            },
        },
        "bounded-package-and-consumption-contract-ready": {
            "threshold": "package installation and tenant-consumption contracts can be expressed without breaking stable operator entrypoints",
            "evidence_sources": {
                "contracts/governance-engine-output-manifest.yaml",
                "contracts/governance-engine-boundary-map.yaml",
            },
        },
    }
    actual_extraction_need_signals = {
        entry["signal_id"]: {
            "threshold": entry["threshold"],
            "evidence_sources": set(entry["evidence_sources"]),
        }
        for entry in governance_engine_extraction_gate["extraction_need_signals"]
    }
    if set(actual_extraction_need_signals) != set(expected_extraction_need_signals):
        errors.append(
            "contracts/governance-engine-extraction-gate.yaml: extraction_need_signals must define the current multi-instance-consumer-demand, standalone-release-versioning-need, and bounded-package-and-consumption-contract-ready signals"
        )
    else:
        for signal_id, expected in expected_extraction_need_signals.items():
            actual = actual_extraction_need_signals[signal_id]
            if actual["threshold"] != expected["threshold"]:
                errors.append(
                    f"contracts/governance-engine-extraction-gate.yaml: extraction_need_signals[{signal_id}].threshold must be {expected['threshold']!r}"
                )
            if actual["evidence_sources"] != expected["evidence_sources"]:
                errors.append(
                    "contracts/governance-engine-extraction-gate.yaml: "
                    f"extraction_need_signals[{signal_id}].evidence_sources must be exactly "
                    + ", ".join(sorted(expected["evidence_sources"]))
                )
    actual_current_signal_results = {
        entry["signal_id"]: {
            "status": entry["status"],
            "rationale": entry["rationale"],
        }
        for entry in current_decision["extraction_need_signal_results"]
    }
    if set(actual_current_signal_results) != set(expected_extraction_need_signals):
        errors.append(
            "contracts/governance-engine-extraction-gate.yaml: current_decision.extraction_need_signal_results must define the current multi-instance-consumer-demand, standalone-release-versioning-need, and bounded-package-and-consumption-contract-ready results"
        )
    else:
        invalid_signal_statuses = {
            signal_id: entry["status"]
            for signal_id, entry in actual_current_signal_results.items()
            if entry["status"] not in {"met", "not_met"}
        }
        for signal_id, status in invalid_signal_statuses.items():
            errors.append(
                "contracts/governance-engine-extraction-gate.yaml: "
                f"current_decision.extraction_need_signal_results[{signal_id}].status must be 'met' or 'not_met', got {status!r}"
            )
        empty_signal_rationales = [
            signal_id
            for signal_id, entry in actual_current_signal_results.items()
            if not entry["rationale"].strip()
        ]
        for signal_id in empty_signal_rationales:
            errors.append(
                "contracts/governance-engine-extraction-gate.yaml: "
                f"current_decision.extraction_need_signal_results[{signal_id}].rationale must be non-empty"
            )
    if not current_decision["rationale"].strip():
        errors.append(
            "contracts/governance-engine-extraction-gate.yaml: current_decision.rationale must be non-empty"
        )
    if not current_decision["deferred_follow_on_action"].strip():
        errors.append(
            "contracts/governance-engine-extraction-gate.yaml: current_decision.deferred_follow_on_action must be non-empty"
        )
    current_hard_gate_statuses = set(actual_current_hard_gate_results.values())
    current_signal_statuses = {entry["status"] for entry in actual_current_signal_results.values()}
    if (
        current_decision["outcome"] == extraction_decision["approved_outcome"]
        and (current_hard_gate_statuses != {"passed"} or current_signal_statuses != {"met"})
    ):
        errors.append(
            "contracts/governance-engine-extraction-gate.yaml: current_decision cannot approve standalone extraction unless every hard gate passes and every extraction-need signal is met"
        )
    if (
        current_decision["outcome"] == extraction_decision["default_outcome"]
        and current_hard_gate_statuses == {"passed"}
        and current_signal_statuses == {"met"}
    ):
        errors.append(
            "contracts/governance-engine-extraction-gate.yaml: current_decision cannot retain the integrated engine once every hard gate passes and every extraction-need signal is met"
        )
    if set(governance_engine_extraction_gate["deferred_follow_on_refs"]) != {
        "openproject://work_packages/247",
        "openproject://work_packages/251",
    }:
        errors.append(
            "contracts/governance-engine-extraction-gate.yaml: deferred_follow_on_refs must be exactly openproject://work_packages/247 and openproject://work_packages/251"
        )
    if (
        governance_engine_foundation["runtime_foundation"]["extraction_gate_ref"]
        != "contracts/governance-engine-extraction-gate.yaml"
    ):
        errors.append(
            "contracts/governance-engine-foundation.yaml: runtime_foundation.extraction_gate_ref must point to contracts/governance-engine-extraction-gate.yaml"
        )
    expected_instruction_bundle_authoring = {
        "AGENTS.md",
        "skills-src/",
        "contracts/skills.yaml",
        "contracts/repo-rules/",
    }
    actual_instruction_bundle_authoring = set(
        governance_engine_foundation["runtime_foundation"]["instruction_bundle_authoring"]
    )
    if actual_instruction_bundle_authoring != expected_instruction_bundle_authoring:
        errors.append(
            "contracts/governance-engine-foundation.yaml: runtime_foundation.instruction_bundle_authoring must be exactly "
            + ", ".join(sorted(expected_instruction_bundle_authoring))
        )
    model_access_and_audit = governance_engine_foundation["runtime_foundation"][
        "model_access_and_audit"
    ]
    if (
        model_access_and_audit["governed_intake_assist_contract_ref"]
        != "workspace-governance/contracts/governed-intake-assist.yaml"
    ):
        errors.append(
            "contracts/governance-engine-foundation.yaml: runtime_foundation.model_access_and_audit.governed_intake_assist_contract_ref must point to workspace-governance/contracts/governed-intake-assist.yaml"
        )
    expected_required_controls = {
        "approved profile plus governed invocation path",
        "workspace consumer contract before intake-assist use",
        "workload caller identity distinct from operator acceptance identity",
        "structured output contract for governance assistance",
        "human approval for governance decisions",
        "attributable audit emission",
        "no direct provider credentials in governed workloads",
    }
    if set(model_access_and_audit["required_controls"]) != expected_required_controls:
        errors.append(
            "contracts/governance-engine-foundation.yaml: runtime_foundation.model_access_and_audit.required_controls must be exactly "
            + ", ".join(sorted(expected_required_controls))
        )
    expected_required_audit_fields = {
        "caller_id",
        "operator_identity_or_acceptance_ref",
        "profile_id",
        "invocation_path",
        "decision_id",
        "event_time",
        "outcome",
        "override_reason_when_present",
    }
    if set(model_access_and_audit["required_audit_fields"]) != expected_required_audit_fields:
        errors.append(
            "contracts/governance-engine-foundation.yaml: runtime_foundation.model_access_and_audit.required_audit_fields must be exactly "
            + ", ".join(sorted(expected_required_audit_fields))
        )
    expected_sequencing_prerequisites = {
        "governance-engine boundary explicit",
        "compatibility boundary explicit",
        "shadow parity path explicit",
        "packaging model explicit",
        "governed model-access and audit contract reviewed",
        "governed intake-assist consumer contract explicit",
        "control-fabric operator workflow explicit",
    }
    actual_sequencing_prerequisites = set(
        governance_engine_foundation["runtime_foundation"]["sequencing_prerequisites"]
    )
    if actual_sequencing_prerequisites != expected_sequencing_prerequisites:
        errors.append(
            "contracts/governance-engine-foundation.yaml: runtime_foundation.sequencing_prerequisites must be exactly "
            + ", ".join(sorted(expected_sequencing_prerequisites))
        )
    if governance_control_fabric_operator_surface["owner_repo"] != "workspace-governance":
        errors.append(
            "contracts/governance-control-fabric-operator-surface.yaml: owner_repo must be 'workspace-governance'"
        )
    if (
        governance_control_fabric_operator_surface["runtime_repo"]
        != "workspace-governance-control-fabric"
    ):
        errors.append(
            "contracts/governance-control-fabric-operator-surface.yaml: runtime_repo must be 'workspace-governance-control-fabric'"
        )
    if (
        governance_control_fabric_operator_surface["foundation_ref"]
        != "contracts/governance-engine-foundation.yaml"
    ):
        errors.append(
            "contracts/governance-control-fabric-operator-surface.yaml: foundation_ref must point to contracts/governance-engine-foundation.yaml"
        )
    if (
        repo_root
        / governance_control_fabric_operator_surface["governance_surface_path"]
    ).suffix != ".md" or not (
        repo_root
        / governance_control_fabric_operator_surface["governance_surface_path"]
    ).exists():
        errors.append(
            "contracts/governance-control-fabric-operator-surface.yaml: governance_surface_path must point to an existing workspace-governance markdown surface"
        )
    expected_cli_command_ids = {
        "status",
        "sources-snapshot",
        "plan",
        "run",
        "inspect",
        "readiness",
        "ledger-tail",
        "explain",
    }
    actual_cli_command_ids = {
        entry["command_id"]
        for entry in governance_control_fabric_operator_surface["minimum_cli_surface"][
            "commands"
        ]
    }
    if not expected_cli_command_ids.issubset(actual_cli_command_ids):
        errors.append(
            "contracts/governance-control-fabric-operator-surface.yaml: minimum_cli_surface.commands must include "
            + ", ".join(sorted(expected_cli_command_ids))
        )
    expected_api_endpoint_ids = {
        "healthz",
        "readyz",
        "status",
        "source-snapshots-create",
        "validation-plans-create",
        "validation-runs-create",
        "receipts-get",
        "readiness-evaluate",
        "ledger-events-list",
        "decisions-explain",
    }
    actual_api_endpoint_ids = {
        entry["endpoint_id"]
        for entry in governance_control_fabric_operator_surface["minimum_api_surface"][
            "endpoints"
        ]
    }
    if not expected_api_endpoint_ids.issubset(actual_api_endpoint_ids):
        errors.append(
            "contracts/governance-control-fabric-operator-surface.yaml: minimum_api_surface.endpoints must include "
            + ", ".join(sorted(expected_api_endpoint_ids))
        )
    expected_record_ids = {
        "source-snapshot",
        "validation-plan",
        "validation-run",
        "control-receipt",
        "readiness-decision",
        "ledger-event",
        "authority-reference",
        "escalation-record",
    }
    actual_record_ids = {
        entry["record_id"]
        for entry in governance_control_fabric_operator_surface["record_contracts"]
    }
    if not expected_record_ids.issubset(actual_record_ids):
        errors.append(
            "contracts/governance-control-fabric-operator-surface.yaml: record_contracts must include "
            + ", ".join(sorted(expected_record_ids))
        )
    expected_profile_ids = {"local-read-only", "dev-integration", "governed-stage"}
    actual_profile_ids = {
        entry["profile_id"]
        for entry in governance_control_fabric_operator_surface["profiles"]
    }
    if not expected_profile_ids.issubset(actual_profile_ids):
        errors.append(
            "contracts/governance-control-fabric-operator-surface.yaml: profiles must include local-read-only, dev-integration, and governed-stage"
        )
    expected_blocker_triggers = {
        "unknown-authority-source",
        "stale-source-snapshot",
        "shadow-parity-failed",
        "missing-owner-boundary",
        "security-delta-required",
        "platform-release-gate-required",
    }
    actual_blocker_triggers = {
        entry["trigger_id"]
        for entry in governance_control_fabric_operator_surface["blocker_triggers"]
    }
    if not expected_blocker_triggers.issubset(actual_blocker_triggers):
        errors.append(
            "contracts/governance-control-fabric-operator-surface.yaml: blocker_triggers must include "
            + ", ".join(sorted(expected_blocker_triggers))
        )
    expected_denied_actions = {
        "mutate-workspace-governance-contracts",
        "mutate-platform-approved-deployment-state",
        "make-security-acceptance-decision",
        "mutate-delivery-art-directly",
        "execute-ai-autonomous-governance-decision",
        "hide-raw-validation-output-in-chat-only",
    }
    actual_denied_actions = set(
        governance_control_fabric_operator_surface["denied_actions"]
    )
    if not expected_denied_actions.issubset(actual_denied_actions):
        errors.append(
            "contracts/governance-control-fabric-operator-surface.yaml: denied_actions must include "
            + ", ".join(sorted(expected_denied_actions))
        )
    fabric_phase_ids = {
        entry["phase_id"]
        for entry in governance_control_fabric_operator_surface["operator_workflow"][
            "phases"
        ]
    }
    fabric_record_ids = actual_record_ids
    fabric_entrypoint_ids = actual_cli_command_ids | actual_api_endpoint_ids
    for phase in governance_control_fabric_operator_surface["operator_workflow"][
        "phases"
    ]:
        unknown_entrypoints = set(phase["entrypoint_ids"]) - fabric_entrypoint_ids
        if unknown_entrypoints:
            errors.append(
                "contracts/governance-control-fabric-operator-surface.yaml: "
                f"operator_workflow phase {phase['phase_id']!r} references unknown entrypoints "
                + ", ".join(sorted(unknown_entrypoints))
            )
        unknown_records = set(phase["produced_record_ids"]) - fabric_record_ids
        if unknown_records:
            errors.append(
                "contracts/governance-control-fabric-operator-surface.yaml: "
                f"operator_workflow phase {phase['phase_id']!r} references unknown record ids "
                + ", ".join(sorted(unknown_records))
            )
    for command in governance_control_fabric_operator_surface["minimum_cli_surface"][
        "commands"
    ]:
        if command["phase_id"] not in fabric_phase_ids:
            errors.append(
                "contracts/governance-control-fabric-operator-surface.yaml: "
                f"CLI command {command['command_id']!r} references unknown phase_id {command['phase_id']!r}"
            )
        if command["mutates_authority"] is not False:
            errors.append(
                "contracts/governance-control-fabric-operator-surface.yaml: "
                f"CLI command {command['command_id']!r} must not mutate authority"
            )
    for endpoint in governance_control_fabric_operator_surface["minimum_api_surface"][
        "endpoints"
    ]:
        if endpoint["phase_id"] not in fabric_phase_ids:
            errors.append(
                "contracts/governance-control-fabric-operator-surface.yaml: "
                f"API endpoint {endpoint['endpoint_id']!r} references unknown phase_id {endpoint['phase_id']!r}"
            )
        if endpoint["response_record_id"] not in fabric_record_ids:
            errors.append(
                "contracts/governance-control-fabric-operator-surface.yaml: "
                f"API endpoint {endpoint['endpoint_id']!r} references unknown response_record_id {endpoint['response_record_id']!r}"
            )
        if endpoint["mutates_authority"] is not False:
            errors.append(
                "contracts/governance-control-fabric-operator-surface.yaml: "
                f"API endpoint {endpoint['endpoint_id']!r} must not mutate authority"
            )
    if governance_validator_catalog["owner_repo"] != "workspace-governance":
        errors.append(
            "contracts/governance-validator-catalog.yaml: owner_repo must be 'workspace-governance'"
        )
    if governance_validator_catalog["runtime_repo"] != "workspace-governance-control-fabric":
        errors.append(
            "contracts/governance-validator-catalog.yaml: runtime_repo must be 'workspace-governance-control-fabric'"
        )
    if governance_validator_catalog["runtime_repo"] not in active_repos:
        errors.append(
            "contracts/governance-validator-catalog.yaml: runtime_repo must be an active repo"
        )
    if governance_validator_catalog["defining_epic_ref"] != "openproject://work_packages/498":
        errors.append(
            "contracts/governance-validator-catalog.yaml: defining_epic_ref must point to openproject://work_packages/498"
        )
    if governance_validator_catalog["defining_feature_ref"] != "openproject://work_packages/500":
        errors.append(
            "contracts/governance-validator-catalog.yaml: defining_feature_ref must point to openproject://work_packages/500"
        )
    if governance_validator_catalog["inventory_work_item_ref"] != "openproject://work_packages/501":
        errors.append(
            "contracts/governance-validator-catalog.yaml: inventory_work_item_ref must point to openproject://work_packages/501"
        )
    validator_catalog_surface = repo_root / governance_validator_catalog["primary_surface_path"]
    if validator_catalog_surface.suffix != ".md" or not validator_catalog_surface.exists():
        errors.append(
            "contracts/governance-validator-catalog.yaml: primary_surface_path must point to an existing markdown surface"
        )
    expected_catalog_profiles = {
        "local-read-only",
        "dev-integration",
        "governed-stage",
        "break-glass",
    }
    catalog_profiles = set(governance_validator_catalog["profiles"])
    if catalog_profiles != expected_catalog_profiles:
        errors.append(
            "contracts/governance-validator-catalog.yaml: profiles must be exactly "
            + ", ".join(sorted(expected_catalog_profiles))
        )
    expected_safety_classes = {
        "local-read-only",
        "workspace-cross-repo-read",
        "remote-read",
        "live-runtime-read",
        "materialized-output-write",
        "structured-record-write",
        "authority-mutation",
    }
    catalog_safety_classes = set(governance_validator_catalog["safety_classes"])
    if catalog_safety_classes != expected_safety_classes:
        errors.append(
            "contracts/governance-validator-catalog.yaml: safety_classes must be exactly "
            + ", ".join(sorted(expected_safety_classes))
        )
    catalog_surfaces = governance_validator_catalog["command_surfaces"]
    surface_ids = [surface["surface_id"] for surface in catalog_surfaces]
    duplicate_surface_ids = sorted(
        surface_id for surface_id in set(surface_ids) if surface_ids.count(surface_id) > 1
    )
    if duplicate_surface_ids:
        errors.append(
            "contracts/governance-validator-catalog.yaml: duplicate command surface ids: "
            + ", ".join(duplicate_surface_ids)
        )
    expected_surface_ids = {
        "workspace-governance-python-scripts",
        "workspace-delivery-art-broker",
        "oos-api-probe",
        "platform-openproject-make",
        "platform-devint-runner",
        "github-cli",
        "k3s-kubectl",
        "wgcf-runtime",
    }
    if set(surface_ids) != expected_surface_ids:
        errors.append(
            "contracts/governance-validator-catalog.yaml: command_surfaces must define "
            + ", ".join(sorted(expected_surface_ids))
        )
    for surface in catalog_surfaces:
        if surface["owner_repo"] not in active_repos:
            errors.append(
                "contracts/governance-validator-catalog.yaml: command surface "
                f"{surface['surface_id']!r} owner_repo {surface['owner_repo']!r} is not an active repo"
            )
        if surface["safety_class"] not in catalog_safety_classes:
            errors.append(
                "contracts/governance-validator-catalog.yaml: command surface "
                f"{surface['surface_id']!r} references unknown safety_class {surface['safety_class']!r}"
            )
    representative_scopes = governance_validator_catalog["representative_scopes"]
    representative_scope_ids = [scope["scope_id"] for scope in representative_scopes]
    duplicate_representative_scope_ids = sorted(
        scope_id
        for scope_id in set(representative_scope_ids)
        if representative_scope_ids.count(scope_id) > 1
    )
    if duplicate_representative_scope_ids:
        errors.append(
            "contracts/governance-validator-catalog.yaml: duplicate representative scope ids: "
            + ", ".join(duplicate_representative_scope_ids)
        )
    shadow_parity_scope_ids = {
        scope["id"]
        for scope in governance_engine_shadow_parity["cutover_gate"]["representative_scopes"]
    }
    if set(representative_scope_ids) != shadow_parity_scope_ids:
        errors.append(
            "contracts/governance-validator-catalog.yaml: representative_scopes must match shadow-parity representative scopes "
            + ", ".join(sorted(shadow_parity_scope_ids))
        )
    representative_planner_scopes = {scope["planner_scope"] for scope in representative_scopes}
    for scope in representative_scopes:
        if scope["owner_repo"] not in active_repos:
            errors.append(
                "contracts/governance-validator-catalog.yaml: representative scope "
                f"{scope['scope_id']!r} owner_repo {scope['owner_repo']!r} is not an active repo"
            )
        if scope["parity_contract_scope_ref"] != scope["scope_id"]:
            errors.append(
                "contracts/governance-validator-catalog.yaml: representative scope "
                f"{scope['scope_id']!r} must keep parity_contract_scope_ref equal to scope_id"
            )
        if not _is_wgcf_planner_scope(scope["planner_scope"]):
            errors.append(
                "contracts/governance-validator-catalog.yaml: representative scope "
                f"{scope['scope_id']!r} has invalid planner_scope {scope['planner_scope']!r}"
            )
    catalog_entries = governance_validator_catalog["entries"]
    retirement_register = governance_validator_catalog["retirement_register"]
    surface_id_set = set(surface_ids)
    validation_matrix_ids = set(validator_scripts)
    catalog_validation_matrix_ids = {
        entry_id
        for entry_id, payload in catalog_entries.items()
        if payload["included_in_validation_matrix"]
    }
    missing_catalog_matrix_entries = sorted(validation_matrix_ids - catalog_validation_matrix_ids)
    if missing_catalog_matrix_entries:
        errors.append(
            "contracts/governance-validator-catalog.yaml: validation-matrix validators missing from catalog or not marked included: "
            + ", ".join(missing_catalog_matrix_entries)
        )
    extra_catalog_matrix_entries = sorted(catalog_validation_matrix_ids - validation_matrix_ids)
    if extra_catalog_matrix_entries:
        errors.append(
            "contracts/governance-validator-catalog.yaml: catalog entries marked included_in_validation_matrix but absent from validation-matrix: "
            + ", ".join(extra_catalog_matrix_entries)
        )
    for entry_id, payload in catalog_entries.items():
        if payload["owner_repo"] not in active_repos:
            errors.append(
                "contracts/governance-validator-catalog.yaml: entry "
                f"{entry_id!r} owner_repo {payload['owner_repo']!r} is not an active repo"
            )
        if payload["surface_id"] not in surface_id_set:
            errors.append(
                "contracts/governance-validator-catalog.yaml: entry "
                f"{entry_id!r} references unknown surface_id {payload['surface_id']!r}"
            )
        if payload["safety_class"] not in catalog_safety_classes:
            errors.append(
                "contracts/governance-validator-catalog.yaml: entry "
                f"{entry_id!r} references unknown safety_class {payload['safety_class']!r}"
            )
        unknown_profiles = sorted(set(payload["allowed_profiles"]) - catalog_profiles)
        if unknown_profiles:
            errors.append(
                "contracts/governance-validator-catalog.yaml: entry "
                f"{entry_id!r} references unknown allowed_profiles "
                + ", ".join(unknown_profiles)
            )
        executable_path = payload.get("executable_path")
        if executable_path and not (repo_root / executable_path).exists():
            errors.append(
                "contracts/governance-validator-catalog.yaml: entry "
                f"{entry_id!r} references missing executable_path {executable_path!r}"
            )
        for rel_path in payload.get("generated_outputs", []):
            if not (repo_root / rel_path).exists():
                errors.append(
                    "contracts/governance-validator-catalog.yaml: entry "
                    f"{entry_id!r} expects missing generated artifact {rel_path}"
                )
        invocation = payload.get("wgcf_invocation")
        if invocation:
            if invocation["working_directory_repo"] not in active_repos:
                errors.append(
                    "contracts/governance-validator-catalog.yaml: entry "
                    f"{entry_id!r} wgcf_invocation.working_directory_repo "
                    f"{invocation['working_directory_repo']!r} is not an active repo"
                )
            invocation_scopes = set(invocation["scopes"])
            invalid_invocation_scopes = sorted(
                scope
                for scope in invocation_scopes
                if not _is_wgcf_planner_scope(scope)
            )
            if invalid_invocation_scopes:
                errors.append(
                    "contracts/governance-validator-catalog.yaml: entry "
                    f"{entry_id!r} has invalid wgcf_invocation.scopes "
                    + ", ".join(invalid_invocation_scopes)
                )
            has_art_target_scope = any(scope.startswith("art:") for scope in invocation_scopes)
            has_authority_scope = any(
                scope.startswith("authority:") for scope in invocation_scopes
            )
            if not (
                invocation_scopes & (representative_planner_scopes | {"workspace"})
                or has_art_target_scope
                or has_authority_scope
            ):
                errors.append(
                    "contracts/governance-validator-catalog.yaml: entry "
                    f"{entry_id!r} wgcf_invocation must include workspace, one representative planner_scope, an authority scope, or an ART target scope"
                )
            effective_command = invocation.get("command_template") or invocation.get("command") or payload["command"]
            template_fields = _command_template_fields(effective_command)
            invalid_template_fields = sorted(template_fields - WGCF_COMMAND_TEMPLATE_FIELDS)
            if invalid_template_fields:
                errors.append(
                    "contracts/governance-validator-catalog.yaml: entry "
                    f"{entry_id!r} wgcf_invocation effective command contains unsupported template fields "
                    + ", ".join(invalid_template_fields)
                )
            if "art_delivery_id" in template_fields and not has_art_target_scope:
                errors.append(
                    "contracts/governance-validator-catalog.yaml: entry "
                    f"{entry_id!r} wgcf_invocation command_template uses art_delivery_id without an art:* scope"
                )
            if "<" in effective_command or ">" in effective_command:
                errors.append(
                    "contracts/governance-validator-catalog.yaml: entry "
                    f"{entry_id!r} wgcf_invocation effective command must not contain unresolved placeholders"
                )
            if _has_shell_control_token(effective_command):
                errors.append(
                    "contracts/governance-validator-catalog.yaml: entry "
                    f"{entry_id!r} wgcf_invocation effective command must not require shell control operators"
                )
            if invocation["enabled"] and payload["kind"] == "support-library":
                errors.append(
                    "contracts/governance-validator-catalog.yaml: entry "
                    f"{entry_id!r} support libraries cannot be WGCF invocation targets"
                )
            if invocation["enabled"] and (payload["mutates_authority"] or payload["writes_materialized_outputs"]):
                errors.append(
                    "contracts/governance-validator-catalog.yaml: entry "
                    f"{entry_id!r} mutating or materializing entries cannot be enabled for WGCF invocation"
                )
        if payload["included_in_validation_matrix"]:
            matrix_payload = validator_scripts.get(entry_id)
            if matrix_payload:
                matrix_script = matrix_payload["script"]
                if executable_path != matrix_script:
                    errors.append(
                        "contracts/governance-validator-catalog.yaml: entry "
                        f"{entry_id!r} executable_path must match validation-matrix script {matrix_script!r}"
                    )
                matrix_outputs = set(matrix_payload.get("generated_outputs", []))
                catalog_outputs = set(payload.get("generated_outputs", []))
                if matrix_outputs != catalog_outputs:
                    errors.append(
                        "contracts/governance-validator-catalog.yaml: entry "
                        f"{entry_id!r} generated_outputs must match validation-matrix"
                    )
        if payload["mutates_authority"] and "local-read-only" in payload["allowed_profiles"]:
            errors.append(
                "contracts/governance-validator-catalog.yaml: entry "
                f"{entry_id!r} mutates authority but allows local-read-only profile"
            )
        if payload["writes_materialized_outputs"] and payload["safety_class"] != "materialized-output-write":
            errors.append(
                "contracts/governance-validator-catalog.yaml: entry "
                f"{entry_id!r} writes materialized outputs but is not materialized-output-write"
            )
    retirement_register_ids = [
        entry["register_id"] for entry in retirement_register
    ]
    duplicate_retirement_register_ids = sorted(
        register_id
        for register_id in set(retirement_register_ids)
        if retirement_register_ids.count(register_id) > 1
    )
    if duplicate_retirement_register_ids:
        errors.append(
            "contracts/governance-validator-catalog.yaml: duplicate retirement register ids: "
            + ", ".join(duplicate_retirement_register_ids)
        )
    covered_retirement_refs: set[str] = set()
    for retirement_entry in retirement_register:
        if retirement_entry["owner_repo"] not in active_repos:
            errors.append(
                "contracts/governance-validator-catalog.yaml: retirement register "
                f"{retirement_entry['register_id']!r} owner_repo {retirement_entry['owner_repo']!r} is not an active repo"
            )
        unknown_entry_refs = sorted(
            set(retirement_entry["entry_refs"]) - set(catalog_entries)
        )
        if unknown_entry_refs:
            errors.append(
                "contracts/governance-validator-catalog.yaml: retirement register "
                f"{retirement_entry['register_id']!r} references unknown entries "
                + ", ".join(unknown_entry_refs)
            )
        covered_retirement_refs.update(retirement_entry["entry_refs"])
        if retirement_entry["retirement_allowed"] and "shadow parity" not in retirement_entry["retirement_gate"].lower():
            errors.append(
                "contracts/governance-validator-catalog.yaml: retirement register "
                f"{retirement_entry['register_id']!r} allows retirement but does not require shadow parity"
            )
        if not retirement_entry["rollback_requirement"].strip():
            errors.append(
                "contracts/governance-validator-catalog.yaml: retirement register "
                f"{retirement_entry['register_id']!r} must include rollback_requirement"
            )
    missing_retirement_coverage = sorted(set(catalog_entries) - covered_retirement_refs)
    if missing_retirement_coverage:
        errors.append(
            "contracts/governance-validator-catalog.yaml: entries missing retirement register coverage: "
            + ", ".join(missing_retirement_coverage)
        )
    validation_behavior_policy = intake_policy["validation_behavior"]
    context_behavior_policy = intake_policy["context_behavior"]
    if validation_behavior_policy["enabled"] is not True:
        errors.append("contracts/intake-policy.yaml: validation_behavior.enabled must remain true")
    if validation_behavior_policy["defining_work_item_ref"] != "openproject://work_packages/504":
        errors.append(
            "contracts/intake-policy.yaml: validation_behavior.defining_work_item_ref must point to openproject://work_packages/504"
        )
    expected_validation_catalog_ref = {
        "repo": "workspace-governance",
        "path": "contracts/governance-validator-catalog.yaml",
    }
    if validation_behavior_policy["catalog_ref"] != expected_validation_catalog_ref:
        errors.append(
            "contracts/intake-policy.yaml: validation_behavior.catalog_ref must point to workspace-governance/contracts/governance-validator-catalog.yaml"
        )
    allowed_validation_postures = set(validation_behavior_policy["allowed_postures"])
    expected_validation_postures = {
        "catalog-owner",
        "runtime-consumer",
        "profile-gated-external-owner",
        "covered-by-owner-repo",
        "interface-contract-backed",
        "proposed-profile-gated",
        "build-admitted-profile-gated",
    }
    if allowed_validation_postures != expected_validation_postures:
        errors.append(
            "contracts/intake-policy.yaml: validation_behavior.allowed_postures must be exactly "
            + ", ".join(sorted(expected_validation_postures))
        )
    allowed_validation_graph_roles = set(validation_behavior_policy["allowed_graph_roles"])
    expected_validation_graph_roles = {
        "catalog-authority-source",
        "wgcf-runtime-source",
        "platform-authority-source",
        "security-authority-source",
        "product-runtime-source",
        "runtime-enforcement-source",
        "product-channel-source",
        "operator-workflow-source",
        "shared-platform-component",
        "shared-governance-runtime-component",
        "product-runtime-component",
        "product-channel-component",
        "product-plugin-component",
        "operator-workflow-component",
        "product-readiness-aggregate",
        "dev-integration-profile",
        "context-packet-provider",
        "proposed-shared-platform-component",
    }
    if allowed_validation_graph_roles != expected_validation_graph_roles:
        errors.append(
            "contracts/intake-policy.yaml: validation_behavior.allowed_graph_roles must be exactly "
            + ", ".join(sorted(expected_validation_graph_roles))
        )
    allowed_validation_graph_roles_by_posture = {
        posture: set(graph_roles)
        for posture, graph_roles in validation_behavior_policy[
            "allowed_graph_roles_by_posture"
        ].items()
    }
    expected_validation_graph_roles_by_posture = {
        "proposed-profile-gated": {
            "proposed-shared-platform-component",
            "context-packet-provider",
        },
        "build-admitted-profile-gated": {
            "shared-platform-component",
            "context-packet-provider",
        },
    }
    if (
        allowed_validation_graph_roles_by_posture
        != expected_validation_graph_roles_by_posture
    ):
        errors.append(
            "contracts/intake-policy.yaml: validation_behavior.allowed_graph_roles_by_posture "
            "must declare the exact proposed and build-admitted profile role sets"
        )
    direct_invocation_postures = set(validation_behavior_policy["direct_invocation_postures"])
    expected_direct_invocation_postures = {
        "catalog-owner",
        "profile-gated-external-owner",
        "interface-contract-backed",
    }
    if direct_invocation_postures != expected_direct_invocation_postures:
        errors.append(
            "contracts/intake-policy.yaml: validation_behavior.direct_invocation_postures must be exactly "
            + ", ".join(sorted(expected_direct_invocation_postures))
        )
    admission_contract = governance_validator_catalog["admission_contract"]
    if admission_contract["work_item_ref"] != "openproject://work_packages/504":
        errors.append(
            "contracts/governance-validator-catalog.yaml: admission_contract.work_item_ref must point to openproject://work_packages/504"
        )
    expected_admission_refs = {
        "intake_policy_ref": "contracts/intake-policy.yaml",
        "active_repo_inventory_ref": "contracts/repos.yaml",
        "active_product_inventory_ref": "contracts/products.yaml",
        "active_component_inventory_ref": "contracts/components.yaml",
        "runtime_profile_registry_ref": "contracts/developer-integration-profiles.yaml",
        "intake_register_ref": "contracts/intake-register.yaml",
    }
    for key, rel_path in expected_admission_refs.items():
        if admission_contract[key] != rel_path:
            errors.append(
                f"contracts/governance-validator-catalog.yaml: admission_contract.{key} must be {rel_path!r}"
            )
        if not (repo_root / rel_path).exists():
            errors.append(
                f"contracts/governance-validator-catalog.yaml: admission_contract.{key} references missing path {rel_path!r}"
            )
    expected_behavior_fields = {"posture", "wgcf_graph_role", "catalog_refs", "notes"}
    if set(admission_contract["required_behavior_fields"]) != expected_behavior_fields:
        errors.append(
            "contracts/governance-validator-catalog.yaml: admission_contract.required_behavior_fields must be posture, wgcf_graph_role, catalog_refs, notes"
        )
    if context_behavior_policy["enabled"] is not True:
        errors.append("contracts/intake-policy.yaml: context_behavior.enabled must remain true")
    if context_behavior_policy["defining_work_item_ref"] != "openproject://work_packages/606":
        errors.append(
            "contracts/intake-policy.yaml: context_behavior.defining_work_item_ref must point to openproject://work_packages/606"
        )
    expected_context_contract_ref = {
        "repo": "workspace-governance",
        "path": "contracts/context-behavior.yaml",
    }
    expected_raw_context_retirement_ref = {
        "repo": "workspace-governance",
        "path": "contracts/raw-context-retirement.yaml",
    }
    if context_behavior_policy["contract_ref"] != expected_context_contract_ref:
        errors.append(
            "contracts/intake-policy.yaml: context_behavior.contract_ref must point to workspace-governance/contracts/context-behavior.yaml"
        )
    if context_behavior_policy["raw_context_retirement_ref"] != expected_raw_context_retirement_ref:
        errors.append(
            "contracts/intake-policy.yaml: context_behavior.raw_context_retirement_ref must point to workspace-governance/contracts/raw-context-retirement.yaml"
        )
    if context_behavior_policy["default_model_projection"] != "deny-raw-project-model-safe-packet":
        errors.append(
            "contracts/intake-policy.yaml: context_behavior.default_model_projection must be deny-raw-project-model-safe-packet"
        )

    if context_behavior["owner_repo"] != "workspace-governance":
        errors.append("contracts/context-behavior.yaml: owner_repo must be 'workspace-governance'")
    if context_behavior["implementation_repo"] != "context-governance-gateway":
        errors.append(
            "contracts/context-behavior.yaml: implementation_repo must be 'context-governance-gateway'"
        )
    expected_context_refs = {
        "defining_epic_ref": "openproject://work_packages/583",
        "defining_feature_ref": "openproject://work_packages/605",
        "declaration_work_item_ref": "openproject://work_packages/606",
    }
    for key, expected in expected_context_refs.items():
        if context_behavior[key] != expected:
            errors.append(f"contracts/context-behavior.yaml: {key} must be {expected!r}")
    context_operator_surface = repo_root / context_behavior["primary_operator_surface"]
    if context_operator_surface.suffix != ".md" or not context_operator_surface.exists():
        errors.append(
            "contracts/context-behavior.yaml: primary_operator_surface must point to an existing markdown surface"
        )
    if context_behavior["default_policy"]["raw_model_projection"] != "deny":
        errors.append(
            "contracts/context-behavior.yaml: default_policy.raw_model_projection must be deny"
        )
    if "deny" not in context_behavior["default_policy"]["uncertain_detection"]:
        errors.append(
            "contracts/context-behavior.yaml: default_policy.uncertain_detection must fail closed for raw projection"
        )
    context_source_classes = set(context_behavior["source_classes"])
    expected_context_source_classes = {
        "terminal_output",
        "ci_logs",
        "repo_snapshot",
        "art_work_item_context",
        "platform_runtime_logs",
        "operator_workflow_payload",
        "security_review_context",
    }
    if context_source_classes != expected_context_source_classes:
        errors.append(
            "contracts/context-behavior.yaml: source_classes must be exactly "
            + ", ".join(sorted(expected_context_source_classes))
        )
    context_adoption_states = [
        entry["state"] for entry in context_behavior["adoption_states"]
    ]
    duplicate_context_states = sorted(
        state for state in set(context_adoption_states) if context_adoption_states.count(state) > 1
    )
    if duplicate_context_states:
        errors.append(
            "contracts/context-behavior.yaml: duplicate adoption states: "
            + ", ".join(duplicate_context_states)
        )
    expected_context_states = {
        "declared",
        "native-provider",
        "packet-consumer",
        "parity-required",
        "retirement-eligible",
        "not-required",
    }
    if set(context_adoption_states) != expected_context_states:
        errors.append(
            "contracts/context-behavior.yaml: adoption_states must be exactly "
            + ", ".join(sorted(expected_context_states))
        )
    context_declaration_repos = [
        entry["repo"] for entry in context_behavior["repo_declarations"]
    ]
    duplicate_context_repos = sorted(
        repo for repo in set(context_declaration_repos) if context_declaration_repos.count(repo) > 1
    )
    if duplicate_context_repos:
        errors.append(
            "contracts/context-behavior.yaml: duplicate repo declarations: "
            + ", ".join(duplicate_context_repos)
        )
    if context_behavior_policy["repos"]["require_for_active"]:
        missing_context_repos = sorted(active_repos - set(context_declaration_repos))
        if missing_context_repos:
            errors.append(
                "contracts/context-behavior.yaml: missing active repo declarations: "
                + ", ".join(missing_context_repos)
            )
    allowed_context_projections = set(
        context_behavior["declaration_contract"]["allowed_default_projections"]
    )
    for entry in context_behavior["repo_declarations"]:
        label = f"contracts/context-behavior.yaml: repo_declarations[{entry['repo']}]"
        if entry["repo"] not in active_repos:
            errors.append(f"{label}: repo is not active")
        if entry["owner_repo"] not in active_repos:
            errors.append(f"{label}: owner_repo {entry['owner_repo']!r} is not active")
        unknown_sources = sorted(set(entry["source_classes"]) - context_source_classes)
        if unknown_sources:
            errors.append(
                f"{label}: source_classes references unknown classes "
                + ", ".join(unknown_sources)
            )
        if entry["default_projection"] not in allowed_context_projections:
            errors.append(
                f"{label}: default_projection {entry['default_projection']!r} is not allowed"
            )
        if entry["adoption_state"] not in set(context_adoption_states):
            errors.append(
                f"{label}: adoption_state {entry['adoption_state']!r} is not declared"
            )
        for rel_path in entry["evidence_refs"]:
            if rel_path.startswith(("contracts/", "docs/")) and not (repo_root / rel_path).exists():
                errors.append(f"{label}: evidence_ref {rel_path!r} does not exist")
    context_intake = context_behavior["intake_integration"]
    if context_intake["intake_policy_ref"] != "contracts/intake-policy.yaml":
        errors.append(
            "contracts/context-behavior.yaml: intake_integration.intake_policy_ref must be contracts/intake-policy.yaml"
        )
    if context_intake["raw_context_retirement_ref"] != "contracts/raw-context-retirement.yaml":
        errors.append(
            "contracts/context-behavior.yaml: intake_integration.raw_context_retirement_ref must be contracts/raw-context-retirement.yaml"
        )
    required_context_decision_fields = {
        "context_behavior_required",
        "source_classes",
        "default_projection",
        "cgg_role",
        "adoption_state",
        "denied_without_cgg",
    }
    if set(context_intake["required_decision_fields"]) != required_context_decision_fields:
        errors.append(
            "contracts/context-behavior.yaml: intake_integration.required_decision_fields must be exactly "
            + ", ".join(sorted(required_context_decision_fields))
        )

    if raw_context_retirement["owner_repo"] != "workspace-governance":
        errors.append("contracts/raw-context-retirement.yaml: owner_repo must be 'workspace-governance'")
    if raw_context_retirement["implementation_repo"] != "context-governance-gateway":
        errors.append(
            "contracts/raw-context-retirement.yaml: implementation_repo must be 'context-governance-gateway'"
        )
    expected_raw_refs = {
        "defining_epic_ref": "openproject://work_packages/583",
        "inventory_feature_ref": "openproject://work_packages/608",
        "inventory_work_item_ref": "openproject://work_packages/609",
        "playbook_work_item_ref": "openproject://work_packages/610",
    }
    for key, expected in expected_raw_refs.items():
        if raw_context_retirement[key] != expected:
            errors.append(f"contracts/raw-context-retirement.yaml: {key} must be {expected!r}")
    if raw_context_retirement["primary_operator_surface"] != context_behavior["primary_operator_surface"]:
        errors.append(
            "contracts/raw-context-retirement.yaml: primary_operator_surface must match context-behavior primary_operator_surface"
        )
    raw_policy = raw_context_retirement["default_retirement_policy"]
    if raw_policy["legacy_fallback_after_retirement"] != "denied":
        errors.append(
            "contracts/raw-context-retirement.yaml: default_retirement_policy.legacy_fallback_after_retirement must be denied"
        )
    if raw_policy["raw_projection_default"] != "deny":
        errors.append(
            "contracts/raw-context-retirement.yaml: default_retirement_policy.raw_projection_default must be deny"
        )
    raw_states = [entry["state"] for entry in raw_context_retirement["states"]]
    duplicate_raw_states = sorted(
        state for state in set(raw_states) if raw_states.count(state) > 1
    )
    if duplicate_raw_states:
        errors.append(
            "contracts/raw-context-retirement.yaml: duplicate states: "
            + ", ".join(duplicate_raw_states)
        )
    expected_raw_states = {
        "inventory-only",
        "declaration-required",
        "parity-required",
        "migrated",
        "retirement-eligible",
        "retired",
        "not-applicable",
    }
    if set(raw_states) != expected_raw_states:
        errors.append(
            "contracts/raw-context-retirement.yaml: states must be exactly "
            + ", ".join(sorted(expected_raw_states))
        )
    raw_entry_ids = [
        entry["entry_id"] for entry in raw_context_retirement["inventory_entries"]
    ]
    duplicate_raw_entry_ids = sorted(
        entry_id for entry_id in set(raw_entry_ids) if raw_entry_ids.count(entry_id) > 1
    )
    if duplicate_raw_entry_ids:
        errors.append(
            "contracts/raw-context-retirement.yaml: duplicate inventory entries: "
            + ", ".join(duplicate_raw_entry_ids)
        )
    declared_context_repos = set(context_declaration_repos)
    raw_inventory_covered_repos: set[str] = set()
    for entry in raw_context_retirement["inventory_entries"]:
        label = f"contracts/raw-context-retirement.yaml: inventory_entries[{entry['entry_id']}]"
        if entry["owner_repo"] not in active_repos:
            errors.append(f"{label}: owner_repo {entry['owner_repo']!r} is not active")
        unknown_covered = sorted(set(entry["covered_repos"]) - active_repos)
        if unknown_covered:
            errors.append(
                f"{label}: covered_repos references inactive repos "
                + ", ".join(unknown_covered)
            )
        raw_inventory_covered_repos.update(entry["covered_repos"])
        if entry["context_behavior_repo_ref"] not in declared_context_repos:
            errors.append(
                f"{label}: context_behavior_repo_ref {entry['context_behavior_repo_ref']!r} has no context-behavior declaration"
            )
        unknown_sources = sorted(set(entry["source_classes"]) - context_source_classes)
        if unknown_sources:
            errors.append(
                f"{label}: source_classes references unknown classes "
                + ", ".join(unknown_sources)
            )
        if entry["state"] not in set(raw_states):
            errors.append(f"{label}: state {entry['state']!r} is not declared")
        if entry["retirement_allowed"] and "rollback" not in entry["rollback_requirement"].lower():
            errors.append(f"{label}: retirement_allowed entries must declare rollback_requirement")
        for rel_path in entry["evidence_refs"]:
            if rel_path.startswith(("contracts/", "docs/")) and not (repo_root / rel_path).exists():
                errors.append(f"{label}: evidence_ref {rel_path!r} does not exist")
    missing_raw_inventory_repos = sorted(active_repos - raw_inventory_covered_repos)
    if missing_raw_inventory_repos:
        errors.append(
            "contracts/raw-context-retirement.yaml: inventory_entries do not cover active repos: "
            + ", ".join(missing_raw_inventory_repos)
        )
    for playbook in raw_context_retirement["migration_playbooks"]:
        unknown_states = sorted(set(playbook["applies_to_states"]) - set(raw_states))
        if unknown_states:
            errors.append(
                "contracts/raw-context-retirement.yaml: migration_playbook "
                f"{playbook['playbook_id']!r} references unknown states "
                + ", ".join(unknown_states)
            )

    def validate_validation_behavior(label: str, payload: dict, *, required: bool) -> None:
        behavior = payload.get("validation_behavior")
        if behavior is None:
            if required:
                errors.append(f"{label}: missing validation_behavior")
            return
        posture = behavior["posture"]
        graph_role = behavior["wgcf_graph_role"]
        catalog_refs = behavior["catalog_refs"]
        if posture not in allowed_validation_postures:
            errors.append(f"{label}: validation_behavior.posture {posture!r} is not allowed")
        if graph_role not in allowed_validation_graph_roles:
            errors.append(
                f"{label}: validation_behavior.wgcf_graph_role {graph_role!r} is not allowed"
            )
        unknown_catalog_refs = sorted(set(catalog_refs) - set(catalog_entries))
        if unknown_catalog_refs:
            errors.append(
                f"{label}: validation_behavior.catalog_refs references unknown catalog entries "
                + ", ".join(unknown_catalog_refs)
            )
        if (
            validation_behavior_policy["require_catalog_refs_for_direct_invocation"]
            and posture in direct_invocation_postures
            and not catalog_refs
        ):
            errors.append(
                f"{label}: validation_behavior.posture {posture!r} requires at least one catalog_ref"
            )
        posture_graph_roles = allowed_validation_graph_roles_by_posture.get(posture)
        if posture_graph_roles is not None and graph_role not in posture_graph_roles:
            errors.append(
                f"{label}: {posture} posture must use one of these graph roles: "
                + ", ".join(sorted(posture_graph_roles))
            )

    workspace_root = repo_root.parent
    workspace_has_sibling_repos = any(
        (workspace_root / repo_name).exists()
        for repo_name in active_repos
        if repo_name != "workspace-governance"
    )
    required_cross_repo_refs = {
        model_access_and_audit["profile_registry_ref"],
        model_access_and_audit["governed_intake_assist_contract_ref"],
        *model_access_and_audit["standards_refs"],
        governance_engine_extraction_gate["security_review_ref"],
        governance_control_fabric_operator_surface[
            "runtime_primary_operator_surface_ref"
        ],
    }
    for owner_surface in controlled_proof_policy.get("owner_surfaces", {}).values():
        required_cross_repo_refs.add(
            f"{owner_surface['repo']}/{owner_surface['path']}"
        )
    for ref in governed_contract_refs.values():
        required_cross_repo_refs.add(f"{ref['repo']}/{ref['path']}")
    if workspace_has_sibling_repos:
        for rel_path in sorted(required_cross_repo_refs):
            if not (workspace_root / rel_path).exists():
                errors.append(
                    "cross-repo contract reference does not exist: "
                    + rel_path
                )
    if self_improvement_governance["policy_owner_repo"] not in active_repos:
        errors.append(
            "contracts/self-improvement-policy.yaml: governance.policy_owner_repo "
            f"{self_improvement_governance['policy_owner_repo']!r} is not an active repo"
        )
    if self_improvement_governance["policy_owner_repo"] != "workspace-governance":
        errors.append(
            "contracts/self-improvement-policy.yaml: governance.policy_owner_repo must be 'workspace-governance'"
        )
    if not self_improvement_governance["operator_surface_path"].endswith(".md"):
        errors.append(
            "contracts/self-improvement-policy.yaml: governance.operator_surface_path must point to a markdown instruction surface"
        )
    elif not (repo_root / self_improvement_governance["operator_surface_path"]).exists():
        errors.append(
            "contracts/self-improvement-policy.yaml: governance.operator_surface_path "
            f"{self_improvement_governance['operator_surface_path']!r} does not exist"
        )
    for skill_name in self_improvement_governance["required_skills"]:
        if skill_name not in registered_skills:
            errors.append(
                "contracts/self-improvement-policy.yaml: governance.required_skills references unknown "
                f"skill {skill_name!r}"
            )
    for signal_name in self_improvement_runtime_gate["require_candidate_before_continue_for"]:
        if signal_name not in self_improvement_signal_catalog:
            errors.append(
                "contracts/self-improvement-policy.yaml: runtime_gate.require_candidate_before_continue_for "
                f"references unknown signal {signal_name!r}"
            )
    for signal_name, payload in self_improvement_signal_catalog.items():
        if payload["default_trigger"] not in improvement_triggers:
            errors.append(
                "contracts/self-improvement-policy.yaml: signal_catalog "
                f"{signal_name!r} references unknown trigger {payload['default_trigger']!r}"
            )
        for failure_class in payload["default_failure_classes"]:
            if failure_class not in failure_classes:
                errors.append(
                    "contracts/self-improvement-policy.yaml: signal_catalog "
                    f"{signal_name!r} references unknown failure class {failure_class!r}"
                )
    for profile_name, payload in developer_integration_profiles["profiles"].items():
        if payload["lifecycle"] not in profile_lifecycle["statuses"]:
            errors.append(
                f"contracts/developer-integration-profiles.yaml: {profile_name} lifecycle {payload['lifecycle']!r} is not in the declared profile lifecycle set"
            )
        validate_validation_behavior(
            f"contracts/developer-integration-profiles.yaml: {profile_name}",
            payload,
            required=validation_behavior_policy["runtime_profiles"]["require_for_registered"],
        )
        if payload["owner_repo"] not in active_repos:
            errors.append(
                f"contracts/developer-integration-profiles.yaml: {profile_name} owner_repo {payload['owner_repo']!r} is not an active repo"
            )
        for owner_key in ("runtime_owner", "security_owner"):
            if payload[owner_key] not in active_repos:
                errors.append(
                    f"contracts/developer-integration-profiles.yaml: {profile_name} {owner_key} {payload[owner_key]!r} is not an active repo"
                )
        for repo_ref in payload["shared_dependencies"] + payload["source_repos"]:
            if repo_ref not in active_repos:
                errors.append(
                    f"contracts/developer-integration-profiles.yaml: {profile_name} references unknown repo {repo_ref!r}"
                )
        if payload["stage_handoff"]["owner_repo"] not in active_repos:
            errors.append(
                f"contracts/developer-integration-profiles.yaml: {profile_name} stage_handoff owner_repo {payload['stage_handoff']['owner_repo']!r} is not an active repo"
            )
        required_checks = payload["stage_handoff"].get("required_checks") or []
        if not required_checks:
            errors.append(
                f"contracts/developer-integration-profiles.yaml: {profile_name} stage_handoff.required_checks must not be empty"
            )
        elif len(required_checks) != len(set(required_checks)):
            errors.append(
                f"contracts/developer-integration-profiles.yaml: {profile_name} stage_handoff.required_checks must be unique"
            )
        missing_actions = sorted(expected_devint_actions - set(payload["actions"]))
        if missing_actions:
            errors.append(
                f"contracts/developer-integration-profiles.yaml: {profile_name} actions must include required_actions; missing {', '.join(missing_actions)}"
            )
        if profile_lifecycle["request_record_required"]:
            request_record = payload.get("request_record") or {}
            if not request_record.get("system") or not request_record.get("ref"):
                errors.append(
                    f"contracts/developer-integration-profiles.yaml: {profile_name} is missing request_record.system or request_record.ref"
                )
        admission = payload.get("admission") or {}
        build_admission = payload.get("build_admission") or {}
        if payload["lifecycle"] in set(profile_lifecycle["build_admission_required_for"]):
            for key in (
                "approved_by",
                "approved_on",
                "platform_acceptance_ref",
                "security_review_required",
                "security_review_refs",
                "implementation_allowed",
                "self_serve_launch_allowed",
                "work_item_ref",
            ):
                if not has_required_scalar(build_admission, key):
                    errors.append(
                        f"contracts/developer-integration-profiles.yaml: {profile_name} lifecycle {payload['lifecycle']!r} requires build_admission.{key}"
                    )
            if build_admission.get("implementation_allowed") is not True:
                errors.append(
                    f"contracts/developer-integration-profiles.yaml: {profile_name} build_admission.implementation_allowed must be true"
                )
            if build_admission.get("self_serve_launch_allowed") is not False:
                errors.append(
                    f"contracts/developer-integration-profiles.yaml: {profile_name} build_admission.self_serve_launch_allowed must be false"
                )
        active_admission_statuses = (
            set(profile_lifecycle["platform_acceptance_required_for"])
            - set(profile_lifecycle["build_admission_required_for"])
        )
        if payload["lifecycle"] in active_admission_statuses:
            for key in ("approved_by", "approved_on", "platform_acceptance_ref"):
                if not admission.get(key):
                    errors.append(
                        f"contracts/developer-integration-profiles.yaml: {profile_name} lifecycle {payload['lifecycle']!r} requires admission.{key}"
                    )
        security_payloads = []
        if admission.get("security_review_required"):
            security_payloads.append(("admission", admission))
        if build_admission.get("security_review_required"):
            security_payloads.append(("build_admission", build_admission))
        for payload_name, security_payload in security_payloads:
            refs = security_payload.get("security_review_refs") or []
            if not refs and profile_lifecycle["security_review_ref_required_when_flagged"]:
                errors.append(
                    f"contracts/developer-integration-profiles.yaml: {profile_name} requires at least one {payload_name}.security_review_ref"
                )
            for ref in refs:
                if ref["repo"] not in active_repos:
                    errors.append(
                        f"contracts/developer-integration-profiles.yaml: {profile_name} security review repo {ref['repo']!r} is not an active repo"
                    )

    for repo_name, payload in contracts["repos"]["repos"].items():
        if payload["lifecycle"] not in lifecycle_states:
            errors.append(f"contracts/repos.yaml: {repo_name} uses unknown lifecycle {payload['lifecycle']!r}")
        validate_validation_behavior(
            f"contracts/repos.yaml: {repo_name}",
            payload,
            required=validation_behavior_policy["repos"]["require_for_active"],
        )
        for ref in payload["allowed_authoritative_refs"]:
            if ref not in active_repos:
                errors.append(f"contracts/repos.yaml: {repo_name} references unknown repo {ref!r}")
        if payload.get("security_review_subject") and "security-architecture" not in payload["allowed_authoritative_refs"]:
            errors.append(
                f"contracts/repos.yaml: {repo_name} sets security_review_subject but does not allow security-architecture as an authoritative ref"
            )

    for repo_name, payload in contracts["repos"].get("retired_repos", {}).items():
        if payload["lifecycle"] not in lifecycle_states:
            errors.append(f"contracts/repos.yaml: retired repo {repo_name} uses unknown lifecycle {payload['lifecycle']!r}")
        for replacement in payload["replaced_by"].values():
            if replacement not in active_repos:
                errors.append(f"contracts/repos.yaml: retired repo {repo_name} replacement {replacement!r} is not an active repo")

    repo_rules = contracts["repo_rules"]
    missing_rules = sorted(active_repos - set(repo_rules.keys()))
    if missing_rules:
        errors.append("contracts/repo-rules: missing active repo rules for " + ", ".join(missing_rules))
    for repo_name, rule in repo_rules.items():
        if repo_name not in active_repos:
            errors.append(f"contracts/repo-rules/{repo_name}.yaml: repo is not in active repos")
            continue
        repo_payload = contracts["repos"]["repos"][repo_name]
        if rule["lifecycle"] != repo_payload["lifecycle"]:
            errors.append(f"contracts/repo-rules/{repo_name}.yaml: lifecycle does not match repos.yaml")
        for ref in rule["required_repo_refs"]:
            if ref not in active_repos:
                errors.append(f"contracts/repo-rules/{repo_name}.yaml: unknown required_repo_ref {ref!r}")
        security_requirements = rule.get("security_requirements")
        security_change_record_requirements = rule.get("security_change_record_requirements")
        if repo_payload["requires_security_bindings"] and not security_requirements:
            errors.append(
                f"contracts/repo-rules/{repo_name}.yaml: missing security_requirements for repo requiring security bindings"
            )
        operator_workflow_requirements = rule.get("operator_workflow_requirements")
        if operator_workflow_requirements:
            seen_workflow_ids: set[str] = set()
            for workflow in operator_workflow_requirements["workflows"]:
                workflow_id = workflow["id"]
                if workflow_id in seen_workflow_ids:
                    errors.append(
                        f"contracts/repo-rules/{repo_name}.yaml: duplicate operator workflow id {workflow_id!r}"
                    )
                seen_workflow_ids.add(workflow_id)
                primary_surface_path = workflow["primary_surface_path"]
                if primary_surface_path.startswith("/"):
                    errors.append(
                        f"contracts/repo-rules/{repo_name}.yaml: operator workflow {workflow_id!r} primary_surface_path must be repo-relative"
                    )
                if "/" not in primary_surface_path:
                    errors.append(
                        f"contracts/repo-rules/{repo_name}.yaml: operator workflow {workflow_id!r} primary_surface_path should name a concrete repo path"
                    )
                if not primary_surface_path.endswith(".md"):
                    errors.append(
                        f"contracts/repo-rules/{repo_name}.yaml: operator workflow {workflow_id!r} primary_surface_path should point to a markdown instruction surface"
                    )
        if not security_requirements:
            continue
        if security_requirements["security_owner"] not in active_repos:
            errors.append(
                f"contracts/repo-rules/{repo_name}.yaml: security_owner {security_requirements['security_owner']!r} is not an active repo"
            )
        elif security_requirements["security_owner"] not in repo_payload["allowed_authoritative_refs"]:
            errors.append(
                f"contracts/repo-rules/{repo_name}.yaml: security_owner {security_requirements['security_owner']!r} is not an allowed authoritative ref"
            )
        for artifact in security_requirements["required_artifacts"]:
            unknown_areas = sorted(
                set(artifact["review_areas"])
                - set(contracts["review_obligations"]["review_obligations"])
            )
            if unknown_areas:
                errors.append(
                    f"contracts/repo-rules/{repo_name}.yaml: security artifact {artifact['id']} uses unknown review areas {', '.join(unknown_areas)}"
                )
        seen_trigger_ids: set[str] = set()
        for trigger in security_requirements["delta_review_triggers"]:
            trigger_id = trigger["id"]
            if trigger_id in seen_trigger_ids:
                errors.append(
                    f"contracts/repo-rules/{repo_name}.yaml: duplicate security delta review trigger id {trigger_id!r}"
                )
            seen_trigger_ids.add(trigger_id)
            unknown_areas = sorted(
                set(trigger["review_areas"])
                - set(contracts["review_obligations"]["review_obligations"])
            )
            if unknown_areas:
                errors.append(
                    f"contracts/repo-rules/{repo_name}.yaml: security delta review trigger {trigger_id!r} uses unknown review areas {', '.join(unknown_areas)}"
                )
            for subject in trigger["review_subjects"]:
                inventory_section = subject["inventory_section"]
                subject_name = subject["name"]
                if inventory_section == "repos" and subject_name not in active_repos:
                    errors.append(
                        f"contracts/repo-rules/{repo_name}.yaml: security delta review trigger {trigger_id!r} references unknown repo subject {subject_name!r}"
                    )
                elif inventory_section == "components" and subject_name not in component_names:
                    errors.append(
                        f"contracts/repo-rules/{repo_name}.yaml: security delta review trigger {trigger_id!r} references unknown component subject {subject_name!r}"
                    )
                elif inventory_section == "products" and subject_name not in product_names:
                    errors.append(
                        f"contracts/repo-rules/{repo_name}.yaml: security delta review trigger {trigger_id!r} references unknown product subject {subject_name!r}"
                    )
        if security_change_record_requirements and not security_requirements:
            errors.append(
                f"contracts/repo-rules/{repo_name}.yaml: security_change_record_requirements require security_requirements"
            )

    for product_name, payload in contracts["products"]["products"].items():
        if payload["lifecycle"] not in lifecycle_states:
            errors.append(f"contracts/products.yaml: {product_name} uses unknown lifecycle {payload['lifecycle']!r}")
        validate_validation_behavior(
            f"contracts/products.yaml: {product_name}",
            payload,
            required=validation_behavior_policy["products"]["require_for_active"],
        )
        for owner_key in ("platform_owner", "security_owner", "runtime_owner"):
            if payload[owner_key] not in active_repos:
                errors.append(f"contracts/products.yaml: {product_name} {owner_key} {payload[owner_key]!r} is not an active repo")
        for repo_name in payload["source_owners"]:
            if repo_name not in active_repos:
                errors.append(f"contracts/products.yaml: {product_name} source owner {repo_name!r} is not an active repo")

    for component_name, payload in contracts["components"]["components"].items():
        if payload["lifecycle"] not in lifecycle_states:
            errors.append(f"contracts/components.yaml: {component_name} uses unknown lifecycle {payload['lifecycle']!r}")
        validate_validation_behavior(
            f"contracts/components.yaml: {component_name}",
            payload,
            required=validation_behavior_policy["components"]["require_for_active"],
        )
        if payload["owner_repo"] not in active_repos:
            errors.append(f"contracts/components.yaml: {component_name} owner_repo {payload['owner_repo']!r} is not an active repo")
        if payload["security_owner"] not in active_repos:
            errors.append(f"contracts/components.yaml: {component_name} security_owner {payload['security_owner']!r} is not an active repo")
        if payload["product"] is not None and payload["product"] not in product_names:
            errors.append(f"contracts/components.yaml: {component_name} product {payload['product']!r} is not declared in products.yaml")

    duplicate_repos = sorted((active_repos | set(contracts["repos"].get("retired_repos", {}).keys())) & intake_repos)
    if duplicate_repos:
        errors.append(
            "contracts/intake-register.yaml: repos must not overlap repos.yaml or retired_repos: "
            + ", ".join(duplicate_repos)
        )
    duplicate_products = sorted(product_names & intake_products)
    if duplicate_products:
        errors.append(
            "contracts/intake-register.yaml: products must not overlap products.yaml: "
            + ", ".join(duplicate_products)
        )
    duplicate_components = sorted(component_names & intake_components)
    if duplicate_components:
        errors.append(
            "contracts/intake-register.yaml: components must not overlap components.yaml: "
            + ", ".join(duplicate_components)
        )

    in_scope_statuses = {"proposed", "admitted"}
    admissible_repo_refs = active_repos | intake_repos
    admissible_product_refs = product_names | intake_products

    for repo_name, payload in intake_register["repos"].items():
        if payload["status"] not in intake_statuses:
            errors.append(
                f"contracts/intake-register.yaml: repo {repo_name} uses unknown status {payload['status']!r}"
            )
        validate_validation_behavior(
            f"contracts/intake-register.yaml: repo {repo_name}",
            payload,
            required=(
                payload["status"] in in_scope_statuses
                and validation_behavior_policy["repos"]["require_for_in_scope_intake"]
            ),
        )
        if payload["decision_source"] not in {"operator", "ai-suggested"}:
            errors.append(
                f"contracts/intake-register.yaml: repo {repo_name} decision_source must be operator or ai-suggested"
            )
        if payload["status"] in in_scope_statuses:
            if not payload["repo_class"]:
                errors.append(
                    f"contracts/intake-register.yaml: repo {repo_name} in scope must declare repo_class"
                )
            if payload["requires_security_bindings"] is None:
                errors.append(
                    f"contracts/intake-register.yaml: repo {repo_name} in scope must declare requires_security_bindings"
                )
            if payload["requires_security_bindings"]:
                if not payload["security_owner"]:
                    errors.append(
                        f"contracts/intake-register.yaml: repo {repo_name} requires security bindings but has no security_owner"
                    )
                elif payload["security_owner"] not in active_repos:
                    errors.append(
                        f"contracts/intake-register.yaml: repo {repo_name} security_owner {payload['security_owner']!r} is not an active repo"
                    )
        elif payload["security_owner"] is not None and payload["security_owner"] not in active_repos:
            errors.append(
                f"contracts/intake-register.yaml: repo {repo_name} security_owner {payload['security_owner']!r} is not an active repo"
            )

    for product_name, payload in intake_register["products"].items():
        if payload["status"] not in intake_statuses:
            errors.append(
                f"contracts/intake-register.yaml: product {product_name} uses unknown status {payload['status']!r}"
            )
        validate_validation_behavior(
            f"contracts/intake-register.yaml: product {product_name}",
            payload,
            required=(
                payload["status"] in in_scope_statuses
                and validation_behavior_policy["products"]["require_for_in_scope_intake"]
            ),
        )
        if payload["decision_source"] not in {"operator", "ai-suggested"}:
            errors.append(
                f"contracts/intake-register.yaml: product {product_name} decision_source must be operator or ai-suggested"
            )
        if payload["status"] in in_scope_statuses and intake_policy["products"]["require_owner_metadata_when_in_scope"]:
            for owner_key in ("platform_owner", "security_owner", "runtime_owner"):
                if not payload[owner_key]:
                    errors.append(
                        f"contracts/intake-register.yaml: product {product_name} in scope must declare {owner_key}"
                    )
                elif payload[owner_key] not in active_repos:
                    errors.append(
                        f"contracts/intake-register.yaml: product {product_name} {owner_key} {payload[owner_key]!r} is not an active repo"
                    )
            if not payload["source_owners"]:
                errors.append(
                    f"contracts/intake-register.yaml: product {product_name} in scope must declare source_owners"
                )
            for repo_name in payload["source_owners"]:
                if repo_name not in admissible_repo_refs:
                    errors.append(
                        f"contracts/intake-register.yaml: product {product_name} source owner {repo_name!r} is not an active or intake-classified repo"
                    )
            if not payload["intended_endpoint"]:
                errors.append(
                    f"contracts/intake-register.yaml: product {product_name} in scope must declare intended_endpoint"
                )

    for component_name, payload in intake_register["components"].items():
        if payload["status"] not in intake_statuses:
            errors.append(
                f"contracts/intake-register.yaml: component {component_name} uses unknown status {payload['status']!r}"
            )
        validate_validation_behavior(
            f"contracts/intake-register.yaml: component {component_name}",
            payload,
            required=(
                payload["status"] in in_scope_statuses
                and validation_behavior_policy["components"]["require_for_in_scope_intake"]
            ),
        )
        if payload["decision_source"] not in {"operator", "ai-suggested"}:
            errors.append(
                f"contracts/intake-register.yaml: component {component_name} decision_source must be operator or ai-suggested"
            )
        if payload["status"] in in_scope_statuses and intake_policy["components"]["require_owner_metadata_when_in_scope"]:
            if not payload["component_class"]:
                errors.append(
                    f"contracts/intake-register.yaml: component {component_name} in scope must declare component_class"
                )
            if not payload["owner_repo"]:
                errors.append(
                    f"contracts/intake-register.yaml: component {component_name} in scope must declare owner_repo"
                )
            elif payload["owner_repo"] not in admissible_repo_refs:
                errors.append(
                    f"contracts/intake-register.yaml: component {component_name} owner_repo {payload['owner_repo']!r} is not an active or intake-classified repo"
                )
            if not payload["security_owner"]:
                errors.append(
                    f"contracts/intake-register.yaml: component {component_name} in scope must declare security_owner"
                )
            elif payload["security_owner"] not in active_repos:
                errors.append(
                    f"contracts/intake-register.yaml: component {component_name} security_owner {payload['security_owner']!r} is not an active repo"
                )
            if payload["product"] is not None and payload["product"] not in admissible_product_refs:
                errors.append(
                    f"contracts/intake-register.yaml: component {component_name} product {payload['product']!r} is not an active or intake-classified product"
                )

    for task_type, payload in contracts["task_types"]["task_types"].items():
        if payload["primary_repo"] not in active_repos:
            errors.append(f"contracts/task-types.yaml: {task_type} primary_repo {payload['primary_repo']!r} is not an active repo")
        if payload["change_class"] not in change_classes:
            errors.append(f"contracts/task-types.yaml: {task_type} change_class {payload['change_class']!r} is not declared")

    evidence_keys = set(contracts["evidence_obligations"]["evidence_by_change_class"].keys())
    if evidence_keys != change_classes:
        errors.append("contracts/evidence-obligations.yaml: change-class coverage does not match contracts/change-classes.yaml")

    if not failure_classes:
        errors.append("contracts/failure-taxonomy.yaml: failure_classes must not be empty")
    if not improvement_triggers:
        errors.append("contracts/improvement-triggers.yaml: triggers must not be empty")

    for validator_name, payload in validator_scripts.items():
        script_path = repo_root / payload["script"]
        if not script_path.exists():
            errors.append(f"contracts/validation-matrix.yaml: validator {validator_name} references missing script {payload['script']}")
        for rel_path in payload.get("generated_outputs", []):
            if not (repo_root / rel_path).exists():
                errors.append(f"contracts/validation-matrix.yaml: validator {validator_name} expects missing generated artifact {rel_path}")

    for entry in contracts["exceptions"]["exceptions"]:
        if entry["owner"] not in active_repos:
            errors.append(f"contracts/exceptions.yaml: exception {entry['id']} owner {entry['owner']!r} is not an active repo")
        branch_lifecycle_waivers = [
            waiver for waiver in entry["waives"] if waiver in BRANCH_LIFECYCLE_WAIVER_KINDS
        ]
        if branch_lifecycle_waivers:
            target_match = BRANCH_LIFECYCLE_TARGET_RE.fullmatch(entry["target"])
            if not target_match:
                errors.append(
                    f"contracts/exceptions.yaml: exception {entry['id']} target must match "
                    "'repo:<repo>:<kind>:<value>' for branch-lifecycle waivers"
                )
            else:
                known_repo_refs = active_repos | intake_repos | retired_repos
                target_repo = target_match.group("repo")
                target_kind = target_match.group("kind")
                if target_repo not in known_repo_refs:
                    errors.append(
                        f"contracts/exceptions.yaml: exception {entry['id']} references unknown repo {target_repo!r}"
                    )
                for waiver in branch_lifecycle_waivers:
                    expected_kind = BRANCH_LIFECYCLE_WAIVER_KINDS[waiver]
                    if target_kind != expected_kind:
                        errors.append(
                            f"contracts/exceptions.yaml: exception {entry['id']} waiver {waiver!r} "
                            f"requires target kind {expected_kind!r}, got {target_kind!r}"
                        )
        try:
            expires_on = date.fromisoformat(entry["expires_on"])
        except ValueError:
            errors.append(
                f"contracts/exceptions.yaml: exception {entry['id']} has invalid expires_on {entry['expires_on']!r}"
            )
            continue
        if expires_on < date.today():
            errors.append(
                f"contracts/exceptions.yaml: exception {entry['id']} expired on {entry['expires_on']}"
            )

    for skill_name, payload in registered_skills.items():
        if payload["owner_repo"] not in active_repos:
            errors.append(
                f"contracts/skills.yaml: {skill_name} owner_repo {payload['owner_repo']!r} is not an active repo"
            )
        if Path(payload["source_path"]).name != skill_name:
            errors.append(
                f"contracts/skills.yaml: {skill_name} source_path must end in the skill name"
            )

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print(
        "contract model valid: "
        f"active_repos={len(active_repos)} "
        f"intake_repos={len(intake_repos)} "
        f"products={len(product_names)} "
        f"intake_products={len(intake_products)} "
        f"components={len(contracts['components']['components'])} "
        f"intake_components={len(intake_components)} "
        f"repo_rules={len(repo_rules)} "
        f"skills={len(registered_skills)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
