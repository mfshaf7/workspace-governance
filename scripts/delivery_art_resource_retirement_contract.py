from __future__ import annotations

import copy
import json
from pathlib import Path, PurePosixPath
import re
from typing import Any, Mapping

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError


RESOURCE_MANIFEST_SCHEMA = Path(
    "contracts/schemas/delivery-art-work-session-resource-manifest.schema.json"
)
CLEANUP_RECEIPT_SCHEMA = Path(
    "contracts/schemas/delivery-art-work-session-cleanup-receipt.schema.json"
)
RESOURCE_MANIFEST_FIXTURE = Path(
    "contracts/fixtures/delivery-art-workflow/work-session-resource-manifest.valid.json"
)
CLEANUP_RECEIPT_FIXTURE = Path(
    "contracts/fixtures/delivery-art-workflow/work-session-cleanup-receipt.valid.json"
)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _schema_errors(schema: Mapping[str, Any], payload: Mapping[str, Any]) -> list[str]:
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    return [
        f"{'.'.join(str(part) for part in error.absolute_path) or '<root>'}: {error.message}"
        for error in sorted(
            validator.iter_errors(payload),
            key=lambda error: list(error.absolute_path),
        )
    ]


def _relative_path_issue(value: object) -> str | None:
    if not isinstance(value, str) or not value:
        return "must be a non-empty relative path"
    if value.startswith(("/", "\\")) or re.match(r"^[A-Za-z]:[\\/]", value):
        return "must not be absolute"
    if "\\" in value:
        return "must use workspace-relative POSIX separators"
    if ".." in PurePosixPath(value).parts:
        return "must not contain parent traversal"
    return None


def resource_manifest_semantic_issues(payload: Mapping[str, Any]) -> list[str]:
    issues: list[str] = []
    session_id = payload.get("session_id")
    expected_session_id = f"work-session:{payload.get('delivery_id')}:{payload.get('landing_unit_id')}"
    if session_id != expected_session_id:
        issues.append("session_id must bind delivery_id and landing_unit_id")

    cleanup = payload.get("cleanup")
    if isinstance(cleanup, Mapping):
        cleanup_state = cleanup.get("state")
        if cleanup_state != "not-required" and cleanup.get("close_intent") is not True:
            issues.append("cleanup beyond not-required requires explicit close intent")
    else:
        cleanup_state = None

    resource_ids: set[str] = set()
    outcomes: list[object] = []
    for index, resource in enumerate(payload.get("resources", [])):
        if not isinstance(resource, Mapping):
            continue
        label = f"resources[{index}]"
        resource_id = resource.get("resource_id")
        if isinstance(resource_id, str):
            if resource_id in resource_ids:
                issues.append(f"{label}.resource_id must be unique")
            resource_ids.add(resource_id)

        locator = resource.get("locator")
        if isinstance(locator, Mapping):
            if locator.get("ownership_marker") != session_id:
                issues.append(f"{label}.locator ownership_marker must match session_id")
            for path_field in ("workspace_relative_path", "relative_path"):
                if path_field in locator:
                    path_issue = _relative_path_issue(locator.get(path_field))
                    if path_issue:
                        issues.append(f"{label}.locator.{path_field} {path_issue}")

        provenance = resource.get("ownership_provenance")
        retention = resource.get("retention_class")
        outcome = resource.get("outcome")
        outcomes.append(outcome)
        if provenance != "session-created":
            if retention == "retire-on-terminal-close":
                issues.append(f"{label} unowned resources cannot be marked for retirement")
            if outcome in {"eligible", "removed"}:
                issues.append(f"{label} unowned resources cannot be eligible or removed")
        if outcome == "blocked" and not resource.get("last_error"):
            issues.append(f"{label} blocked outcome requires last_error")
        if outcome != "blocked" and resource.get("last_error") is not None:
            issues.append(f"{label} last_error is only valid for a blocked outcome")

    if cleanup_state == "blocked" and "blocked" not in outcomes:
        issues.append("blocked cleanup state requires at least one blocked resource")
    if cleanup_state == "complete" and any(
        outcome not in {"removed", "retained"} for outcome in outcomes
    ):
        issues.append("complete cleanup state requires terminal resource outcomes")
    return issues


def cleanup_receipt_semantic_issues(payload: Mapping[str, Any]) -> list[str]:
    issues: list[str] = []
    session_id = payload.get("session_id")
    expected_session_id = f"work-session:{payload.get('delivery_id')}:{payload.get('landing_unit_id')}"
    if session_id != expected_session_id:
        issues.append("session_id must bind delivery_id and landing_unit_id")
    if payload.get("receipt_id") != f"cleanup-receipt:{session_id}":
        issues.append("receipt_id must be derived from session_id")

    resource_ids: set[str] = set()
    retained_count = 0
    for index, resource in enumerate(payload.get("resources", [])):
        if not isinstance(resource, Mapping):
            continue
        label = f"resources[{index}]"
        resource_id = resource.get("resource_id")
        if isinstance(resource_id, str):
            if resource_id in resource_ids:
                issues.append(f"{label}.resource_id must be unique")
            resource_ids.add(resource_id)
        outcome = resource.get("outcome")
        if outcome == "retained":
            retained_count += 1
        if resource.get("ownership_provenance") != "session-created" and outcome == "removed":
            issues.append(f"{label} cannot report removal of an unowned resource")
        if (
            resource.get("retention_class") == "retire-on-terminal-close"
            and outcome == "retained"
        ):
            issues.append(f"{label} retirement-required resource cannot be terminally retained")

    if payload.get("outcome") == "complete" and retained_count:
        issues.append("complete receipt cannot contain retained resources")
    if payload.get("outcome") == "complete-with-retained-resources" and not retained_count:
        issues.append("complete-with-retained-resources requires a retained resource")
    return issues


def manifest_receipt_pair_issues(
    manifest: Mapping[str, Any], receipt: Mapping[str, Any]
) -> list[str]:
    issues: list[str] = []
    for field in ("session_id", "delivery_id", "landing_unit_id"):
        if manifest.get(field) != receipt.get(field):
            issues.append(f"cleanup receipt {field} must match the final manifest")
    receipt_manifest = receipt.get("manifest")
    if not isinstance(receipt_manifest, Mapping) or receipt_manifest.get(
        "generation"
    ) != manifest.get("generation"):
        issues.append("cleanup receipt must bind the final manifest generation")
    cleanup = manifest.get("cleanup")
    if not isinstance(cleanup, Mapping) or cleanup.get("state") != "complete":
        issues.append("cleanup receipt requires a complete final manifest")

    manifest_resources = {
        resource.get("resource_id"): resource
        for resource in manifest.get("resources", [])
        if isinstance(resource, Mapping) and isinstance(resource.get("resource_id"), str)
    }
    receipt_resources = {
        resource.get("resource_id"): resource
        for resource in receipt.get("resources", [])
        if isinstance(resource, Mapping) and isinstance(resource.get("resource_id"), str)
    }
    if set(manifest_resources) != set(receipt_resources):
        issues.append("cleanup receipt must cover the final manifest resource set exactly")
    for resource_id in sorted(set(manifest_resources) & set(receipt_resources)):
        manifest_resource = manifest_resources[resource_id]
        receipt_resource = receipt_resources[resource_id]
        for field in (
            "resource_type",
            "ownership_provenance",
            "retention_class",
            "outcome",
        ):
            if manifest_resource.get(field) != receipt_resource.get(field):
                issues.append(
                    f"cleanup receipt resource {resource_id} {field} must match the final manifest"
                )
    return issues


def resource_retirement_definition_issues(retirement: Mapping[str, Any]) -> list[str]:
    issues: list[str] = []
    if retirement.get("state") != "contract-ready-pending-owner-implementation":
        issues.append("resource retirement must remain pending owner implementation before activation")
    sequence = retirement.get("activation_sequence")
    if not isinstance(sequence, Mapping) or sequence != {
        "implementation_work_item_ref": "openproject://work_packages/968",
        "security_work_item_ref": "openproject://work_packages/969",
        "custody_projection_work_item_ref": "openproject://work_packages/971",
        "activation_work_item_ref": "openproject://work_packages/970",
    }:
        issues.append("resource retirement activation sequence differs from the approved ART order")
    exclusions = set(retirement.get("scope_exclusions", []))
    if exclusions != {"docker-resources", "unrelated-historical-residue"}:
        issues.append("resource retirement scope exclusions must preserve Docker and unrelated residue boundaries")
    return issues


def contract_fixture_issues(repo_root: Path) -> list[str]:
    issues: list[str] = []
    loaded: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}
    for label, schema_ref, fixture_ref in (
        ("resource manifest", RESOURCE_MANIFEST_SCHEMA, RESOURCE_MANIFEST_FIXTURE),
        ("cleanup receipt", CLEANUP_RECEIPT_SCHEMA, CLEANUP_RECEIPT_FIXTURE),
    ):
        schema_path = repo_root / schema_ref
        fixture_path = repo_root / fixture_ref
        if not schema_path.exists():
            issues.append(f"{schema_ref}: schema is missing")
            continue
        if not fixture_path.exists():
            issues.append(f"{fixture_ref}: fixture is missing")
            continue
        schema = _load_json(schema_path)
        try:
            Draft202012Validator.check_schema(schema)
        except SchemaError as exc:
            issues.append(f"{schema_ref}: invalid JSON Schema: {exc.message}")
            continue
        fixture = _load_json(fixture_path)
        for error in _schema_errors(schema, fixture):
            issues.append(f"{fixture_ref}: {error}")
        loaded[label] = (schema, fixture)

    manifest_pair = loaded.get("resource manifest")
    if manifest_pair:
        manifest_schema, manifest = manifest_pair
        issues.extend(
            f"{RESOURCE_MANIFEST_FIXTURE}: semantic invariant: {issue}"
            for issue in resource_manifest_semantic_issues(manifest)
        )
        absolute_path = copy.deepcopy(manifest)
        absolute_path["resources"][0]["locator"]["workspace_relative_path"] = "/tmp/unowned"
        if not resource_manifest_semantic_issues(absolute_path):
            issues.append("resource manifest negative case must reject absolute paths")
        wrong_marker = copy.deepcopy(manifest)
        wrong_marker["resources"][0]["locator"]["ownership_marker"] = (
            "work-session:delivery-999:delivery-999-work-item-999"
        )
        if not resource_manifest_semantic_issues(wrong_marker):
            issues.append("resource manifest negative case must reject ownership-marker mismatch")
        invalid_provenance = copy.deepcopy(manifest)
        invalid_provenance["resources"][-1]["outcome"] = "eligible"
        if not resource_manifest_semantic_issues(invalid_provenance):
            issues.append("resource manifest negative case must retain pre-existing resources")
        if _schema_errors(manifest_schema, manifest):
            issues.append("resource manifest positive case must remain schema-valid")

    receipt_pair = loaded.get("cleanup receipt")
    if receipt_pair:
        receipt_schema, receipt = receipt_pair
        issues.extend(
            f"{CLEANUP_RECEIPT_FIXTURE}: semantic invariant: {issue}"
            for issue in cleanup_receipt_semantic_issues(receipt)
        )
        blocked_outcome = copy.deepcopy(receipt)
        blocked_outcome["resources"][0]["outcome"] = "blocked"
        if not _schema_errors(receipt_schema, blocked_outcome):
            issues.append("cleanup receipt negative case must reject nonterminal outcomes")
        false_complete = copy.deepcopy(receipt)
        false_complete["outcome"] = "complete"
        if not cleanup_receipt_semantic_issues(false_complete):
            issues.append("cleanup receipt negative case must reject retained resources under complete")
        removed_preexisting = copy.deepcopy(receipt)
        removed_preexisting["resources"][-1]["outcome"] = "removed"
        removed_preexisting["resources"][-1]["reason"] = None
        if not cleanup_receipt_semantic_issues(removed_preexisting):
            issues.append("cleanup receipt negative case must reject removal of pre-existing resources")
    if manifest_pair and receipt_pair:
        manifest = manifest_pair[1]
        receipt = receipt_pair[1]
        issues.extend(
            f"resource manifest/cleanup receipt pair: {issue}"
            for issue in manifest_receipt_pair_issues(manifest, receipt)
        )
        missing_resource = copy.deepcopy(receipt)
        missing_resource["resources"].pop()
        if not manifest_receipt_pair_issues(manifest, missing_resource):
            issues.append("cleanup receipt negative case must cover every manifest resource")
    return issues
