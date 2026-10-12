#!/usr/bin/env python3
"""Semantic checks for the governed product-publication contract and artifacts."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
import sys
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
import yaml


EXPECTED_AUTHORITIES = {
    "publication-contract": ("repo", "workspace-governance"),
    "owner-manifest": ("dynamic", "product-owner-repo"),
    "readiness-evaluation": ("repo", "workspace-governance-control-fabric"),
    "workflow-orchestration": ("repo", "operator-orchestration-service"),
    "operator-projection": ("repo", "governance-operations-console"),
    "security-acceptance": ("repo", "security-architecture"),
    "runtime-activation": ("repo", "platform-engineering"),
}
EXPECTED_VOCABULARY = {
    "product_classifications": {"owner-managed", "platform-integrated", "fully-governed"},
    "product_lifecycle_states": {"active", "suspended", "retired"},
    "publication_postures": {"unlisted", "internal", "client", "public", "archived"},
    "listing_scopes": {"workspace-portfolio", "client-portfolio", "public-catalog", "historical-archive"},
    "audiences": {"workspace-operators", "authorized-clients", "public", "historical"},
    "access_classes": {"workspace-authenticated", "client-authorized", "public-anonymous", "historical-read-only"},
    "publication_actions": {"publish", "update", "unpublish", "archive"},
}
EXPECTED_ARTIFACT_SCHEMAS = {
    "owner_manifest": "contracts/schemas/product-publication-manifest.schema.json",
    "publication_packet": "contracts/schemas/product-publication-packet.schema.json",
    "terminal_receipt": "contracts/schemas/product-publication-receipt.schema.json",
}
EXPECTED_ARTIFACT_AUTHORITIES = {
    "owner_manifest": "owner-manifest",
    "publication_packet": "publication-contract",
    "terminal_receipt": "workflow-orchestration",
}
EXPECTED_CROSS_BOUNDARY_GRANTS = {
    "source_authority": False,
    "runtime_authority": False,
    "release_authority": False,
    "security_acceptance": False,
    "lifecycle_mutation": False,
}


def canonical_digest(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def packet_request_digest(packet: Mapping[str, Any]) -> str:
    subject = copy.deepcopy(dict(packet))
    subject.pop("request_digest", None)
    return canonical_digest(subject)


def model(contract: Mapping[str, Any]) -> Mapping[str, Any]:
    value = contract.get("product_publication", {})
    return value if isinstance(value, Mapping) else {}


def contract_issues(contract: Mapping[str, Any], *, known_repos: set[str]) -> list[str]:
    publication = model(contract)
    issues: list[str] = []
    if publication.get("implementation_posture") != "contract-ready":
        issues.append("implementation posture must remain contract-ready")
    if publication.get("primary_operator_surface") != "docs/product-publication.md":
        issues.append("primary operator surface must be docs/product-publication.md")
    if publication.get("product_inventory_ref") != "contracts/products.yaml":
        issues.append("product inventory must bind contracts/products.yaml")
    if publication.get("lifecycle_contract_ref") != "contracts/project-lifecycle.yaml":
        issues.append("lifecycle contract must bind contracts/project-lifecycle.yaml")

    authorities = publication.get("authorities", {})
    if set(authorities) != set(EXPECTED_AUTHORITIES):
        issues.append("authority roles must preserve the seven approved owner boundaries")
    responsibility_owners: dict[str, str] = {}
    for role, (expected_kind, expected_ref) in EXPECTED_AUTHORITIES.items():
        authority = authorities.get(role, {})
        if (authority.get("owner_kind"), authority.get("owner_ref")) != (
            expected_kind,
            expected_ref,
        ):
            issues.append(f"authority {role} must remain owned by {expected_ref}")
        if expected_kind == "repo" and expected_ref not in known_repos:
            issues.append(f"authority {role} references unknown repo {expected_ref!r}")
        for responsibility in authority.get("responsibilities", []):
            prior = responsibility_owners.get(responsibility)
            if prior is not None:
                issues.append(
                    f"responsibility {responsibility!r} has contradictory owners {prior!r} and {role!r}"
                )
            responsibility_owners[responsibility] = role

    vocabulary = publication.get("vocabulary", {})
    if set(vocabulary) != set(EXPECTED_VOCABULARY):
        issues.append("vocabulary must contain only the canonical publication dimensions")
    for key, expected in EXPECTED_VOCABULARY.items():
        if set(vocabulary.get(key, [])) != expected:
            issues.append(f"vocabulary {key} must match the canonical values exactly")

    posture_bindings = publication.get("posture_bindings", {})
    if set(posture_bindings) != EXPECTED_VOCABULARY["publication_postures"]:
        issues.append("posture bindings must cover every publication posture exactly")
    for posture, binding in posture_bindings.items():
        unknown_lifecycle = set(binding.get("allowed_lifecycle_states", [])) - EXPECTED_VOCABULARY[
            "product_lifecycle_states"
        ]
        if unknown_lifecycle:
            issues.append(f"posture {posture} references unsupported lifecycle states")

    action_bindings = publication.get("action_bindings", {})
    if set(action_bindings) != EXPECTED_VOCABULARY["publication_actions"]:
        issues.append("action bindings must cover every publication action exactly")
    known_postures = EXPECTED_VOCABULARY["publication_postures"]
    for action, binding in action_bindings.items():
        referenced = set(binding.get("allowed_source_postures", [])) | set(
            binding.get("allowed_target_postures", [])
        )
        if referenced - known_postures:
            issues.append(f"action {action} references unsupported publication postures")

    artifact_contracts = publication.get("artifact_contracts", {})
    if set(artifact_contracts) != set(EXPECTED_ARTIFACT_SCHEMAS):
        issues.append("artifact contracts must define manifest, packet, and terminal receipt exactly")
    for artifact, schema_ref in EXPECTED_ARTIFACT_SCHEMAS.items():
        artifact_contract = artifact_contracts.get(artifact, {})
        if artifact_contract.get("schema_ref") != schema_ref:
            issues.append(f"artifact {artifact} must reference {schema_ref}")
        if artifact_contract.get("authority_role") != EXPECTED_ARTIFACT_AUTHORITIES[artifact]:
            issues.append(f"artifact {artifact} has the wrong authority role")

    manifest_obligations = publication.get("manifest_obligations", {})
    if set(manifest_obligations.get("required_inventory_bindings", [])) != {
        "product_id",
        "product_record_ref",
        "product_record_version",
        "product_classification",
        "lifecycle_state",
        "owner_repo",
        "owner_role",
    }:
        issues.append("manifest obligations must preserve every inventory binding")
    if set(manifest_obligations.get("required_source_bindings", [])) != {
        "owner_revision",
        "source_refs",
    }:
        issues.append("manifest obligations must preserve exact source bindings")
    if set(manifest_obligations.get("required_lifecycle_axes", [])) != {
        "project-phase",
        "source-custody",
        "runtime-environment",
        "release-posture",
        "publication-posture",
    }:
        issues.append("manifest obligations must bind all five lifecycle axes")
    if manifest_obligations.get("owner_revision_format") != "full-git-commit":
        issues.append("manifest owner revision must remain a full Git commit")

    packet_obligations = publication.get("packet_obligations", {})
    if set(packet_obligations.get("required_authority_refs", [])) != {
        "operator_decision_ref",
        "readiness_receipt_ref",
        "security_decision_ref",
    }:
        issues.append("packet obligations must preserve all authority references")
    if set(packet_obligations.get("required_manifest_bindings", [])) != {
        "manifest_id",
        "manifest_digest",
        "owner_repo",
        "owner_revision",
    }:
        issues.append("packet obligations must preserve exact manifest bindings")
    replay_binding = packet_obligations.get("replay_binding", {})
    if set(replay_binding.get("identity_fields", [])) != {"request_id", "idempotency_key"}:
        issues.append("packet replay binding must preserve request and idempotency identity")
    if replay_binding.get("conflict_rule") != (
        "same-idempotency-key-requires-identical-request-digest"
    ):
        issues.append("packet replay binding must reject conflicting request content")
    if replay_binding.get("version_rule") != (
        "expected-publication-version-must-match-current-version"
    ):
        issues.append("packet replay binding must preserve publication version concurrency")
    grants = packet_obligations.get("cross_boundary_grants")
    if grants != EXPECTED_CROSS_BOUNDARY_GRANTS:
        issues.append("publication packets must deny every cross-boundary authority grant")
    return issues


def _product_name(product_id: Any) -> str | None:
    if not isinstance(product_id, str) or not product_id.startswith("product:"):
        return None
    return product_id.removeprefix("product:")


def manifest_issues(
    contract: Mapping[str, Any],
    manifest: Mapping[str, Any],
    products_contract: Mapping[str, Any],
    *,
    observed_owner_revision: str | None = None,
) -> list[str]:
    issues: list[str] = []
    product_name = _product_name(manifest.get("product_id"))
    products = products_contract.get("products", {})
    product = products.get(product_name) if product_name else None
    if not isinstance(product, Mapping):
        return ["manifest product must exist in the active product inventory"]

    expected_record = product.get("record", {})
    expected_ref = f"workspace-governance://products/{product_name}/v{expected_record.get('version')}"
    if manifest.get("product_record_ref") != expected_ref:
        issues.append("manifest product record reference does not match active inventory")
    if manifest.get("product_record_version") != expected_record.get("version"):
        issues.append("manifest product record version does not match active inventory")
    if manifest.get("product_classification") != product.get("maturity"):
        issues.append("manifest product classification does not match active inventory")
    if manifest.get("lifecycle_state") != product.get("posture"):
        issues.append("manifest lifecycle state does not match active inventory")

    owner_role = manifest.get("owner_role")
    owner_repo = manifest.get("owner_repo")
    if owner_role == "runtime-owner" and owner_repo != product.get("runtime_owner"):
        issues.append("manifest runtime owner does not match active inventory")
    if owner_role == "source-owner" and owner_repo not in product.get("source_owners", []):
        issues.append("manifest source owner does not match active inventory")
    if not any(
        source.get("repo") == owner_repo and source.get("revision") == manifest.get("owner_revision")
        for source in manifest.get("source_refs", [])
        if isinstance(source, Mapping)
    ):
        issues.append("manifest source refs must bind the owner repo and exact owner revision")
    if (
        observed_owner_revision is not None
        and manifest.get("owner_revision") != observed_owner_revision
    ):
        issues.append("manifest owner revision is stale against observed owner source")

    evidence = manifest.get("lifecycle_evidence", {})
    posture = evidence.get("publication_posture")
    binding = model(contract).get("posture_bindings", {}).get(posture)
    if not isinstance(binding, Mapping):
        issues.append("manifest references unsupported publication posture")
        return issues
    if manifest.get("lifecycle_state") not in binding.get("allowed_lifecycle_states", []):
        issues.append("manifest lifecycle state contradicts publication posture")
    if posture in {"internal", "client", "public"}:
        if evidence.get("project_phase") != "operational":
            issues.append("listed publication posture requires an operational project")
        if evidence.get("source_custody") not in {
            "dedicated-owner-repo",
            "shared-owner-repo",
        }:
            issues.append("listed publication posture requires durable source custody")
        if evidence.get("release_posture") not in {"not-applicable", "released"}:
            issues.append("listed publication posture requires a non-deployed or released result")
    if posture == "archived" and evidence.get("project_phase") != "retired":
        issues.append("archived publication posture requires a retired project")
    return issues


def packet_issues(
    contract: Mapping[str, Any],
    packet: Mapping[str, Any],
    manifest: Mapping[str, Any],
) -> list[str]:
    issues: list[str] = []
    binding = packet.get("manifest_binding", {})
    expected_manifest_digest = canonical_digest(manifest)
    expected_bindings = {
        "manifest_id": manifest.get("manifest_id"),
        "manifest_digest": expected_manifest_digest,
        "owner_repo": manifest.get("owner_repo"),
        "owner_revision": manifest.get("owner_revision"),
    }
    for key, expected in expected_bindings.items():
        if binding.get(key) != expected:
            issues.append(f"packet manifest binding {key} does not match the exact owner manifest")
    if packet.get("product_id") != manifest.get("product_id"):
        issues.append("packet product identity does not match the owner manifest")
    if packet.get("request_digest") != packet_request_digest(packet):
        issues.append("packet request digest does not bind the canonical packet content")

    publication = model(contract)
    action = packet.get("action")
    action_binding = publication.get("action_bindings", {}).get(action)
    if not isinstance(action_binding, Mapping):
        issues.append("packet uses unsupported publication action")
    else:
        if packet.get("current_publication_posture") not in action_binding.get(
            "allowed_source_postures", []
        ):
            issues.append("packet action is invalid for the current publication posture")
        target_posture = packet.get("target_publication", {}).get("posture")
        if target_posture not in action_binding.get("allowed_target_postures", []):
            issues.append("packet action is invalid for the target publication posture")

    target = packet.get("target_publication", {})
    posture_binding = publication.get("posture_bindings", {}).get(target.get("posture"))
    if isinstance(posture_binding, Mapping):
        for key in ("listing_scope", "audience", "access_class"):
            if target.get(key) != posture_binding.get(key):
                issues.append(f"target publication {key} contradicts its posture")
    else:
        issues.append("target publication posture is unsupported")

    evidence = manifest.get("lifecycle_evidence", {})
    if isinstance(posture_binding, Mapping):
        if manifest.get("lifecycle_state") not in posture_binding.get(
            "allowed_lifecycle_states", []
        ):
            issues.append("target publication posture contradicts manifest lifecycle state")
        if target.get("posture") in {"internal", "client", "public"}:
            if evidence.get("project_phase") != "operational":
                issues.append("target listed posture requires an operational project")
            if evidence.get("source_custody") not in {
                "dedicated-owner-repo",
                "shared-owner-repo",
            }:
                issues.append("target listed posture requires durable source custody")
            if evidence.get("release_posture") not in {"not-applicable", "released"}:
                issues.append("target listed posture requires a non-deployed or released result")
        if target.get("posture") == "archived" and evidence.get("project_phase") != "retired":
            issues.append("target archived posture requires a retired project")

    manifest_posture = manifest.get("lifecycle_evidence", {}).get("publication_posture")
    if packet.get("current_publication_posture") != manifest_posture:
        issues.append("packet current posture does not match owner lifecycle evidence")
    if packet.get("grants") != EXPECTED_CROSS_BOUNDARY_GRANTS:
        issues.append("publication packet attempts to grant cross-boundary authority")

    previous = packet.get("previous_receipt")
    expected_version = packet.get("expected_publication_version")
    if expected_version == 0 and previous is not None:
        issues.append("initial publication version cannot bind a previous receipt")
    if expected_version and (
        not isinstance(previous, Mapping)
        or previous.get("publication_version") != expected_version
    ):
        issues.append("packet expected publication version must match the previous receipt")
    return issues


def replay_issues(previous: Mapping[str, Any], candidate: Mapping[str, Any]) -> list[str]:
    if previous.get("idempotency_key") != candidate.get("idempotency_key"):
        return []
    if previous.get("request_digest") != candidate.get("request_digest"):
        return ["idempotency key replay conflicts with different request content"]
    if previous.get("request_id") != candidate.get("request_id"):
        return ["idempotent replay must preserve request identity"]
    return []


def receipt_issues(
    receipt: Mapping[str, Any],
    packet: Mapping[str, Any],
) -> list[str]:
    issues: list[str] = []
    expected = {
        "packet_id": packet.get("packet_id"),
        "request_id": packet.get("request_id"),
        "request_digest": packet.get("request_digest"),
        "manifest_digest": packet.get("manifest_binding", {}).get("manifest_digest"),
        "product_id": packet.get("product_id"),
    }
    for key, value in expected.items():
        if receipt.get(key) != value:
            issues.append(f"receipt {key} does not match the exact publication packet")
    if receipt.get("outcome") in {"applied", "replayed"}:
        if receipt.get("publication_version") != packet.get("expected_publication_version", 0) + 1:
            issues.append("successful receipt publication version must advance exactly once")
        if receipt.get("publication_posture") != packet.get("target_publication", {}).get("posture"):
            issues.append("successful receipt posture must match the packet target")
    elif receipt.get("publication_version") is not None or receipt.get("publication_posture") is not None:
        issues.append("unsuccessful receipt cannot claim an applied version or posture")
    return issues


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: artifact must be a JSON object")
    return payload


def _schema_issues(schema_path: Path, payload: Mapping[str, Any]) -> list[str]:
    schema = _load_json(schema_path)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    return [
        f"{'.'.join(str(part) for part in error.absolute_path) or '<root>'}: {error.message}"
        for error in sorted(validator.iter_errors(payload), key=lambda item: list(item.absolute_path))
    ]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate product-publication owner evidence and request artifacts.",
    )
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument(
        "--observed-owner-revision",
        required=True,
        help="Current full Git commit observed from the manifest owner repository.",
    )
    parser.add_argument("--packet", type=Path)
    parser.add_argument("--receipt", type=Path)
    parser.add_argument(
        "--repo-root",
        default=Path(__file__).resolve().parents[1],
        type=Path,
    )
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()
    try:
        contract = yaml.safe_load(
            (repo_root / "contracts/product-publication.yaml").read_text(encoding="utf-8")
        )
        products = yaml.safe_load(
            (repo_root / "contracts/products.yaml").read_text(encoding="utf-8")
        )
        manifest = _load_json(args.manifest)
        packet = _load_json(args.packet) if args.packet else None
        receipt = _load_json(args.receipt) if args.receipt else None
    except (OSError, ValueError, json.JSONDecodeError, yaml.YAMLError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    issues = _schema_issues(
        repo_root / EXPECTED_ARTIFACT_SCHEMAS["owner_manifest"], manifest
    )
    issues.extend(
        manifest_issues(
            contract,
            manifest,
            products,
            observed_owner_revision=args.observed_owner_revision,
        )
    )
    if packet is not None:
        issues.extend(
            _schema_issues(
                repo_root / EXPECTED_ARTIFACT_SCHEMAS["publication_packet"], packet
            )
        )
        issues.extend(packet_issues(contract, packet, manifest))
    if receipt is not None:
        if packet is None:
            issues.append("--receipt requires --packet so exact request bindings can be checked")
        else:
            issues.extend(
                _schema_issues(
                    repo_root / EXPECTED_ARTIFACT_SCHEMAS["terminal_receipt"], receipt
                )
            )
            issues.extend(receipt_issues(receipt, packet))

    if issues:
        for issue in issues:
            print(f"ERROR: {issue}")
        return 1
    validated = ["manifest"]
    if packet is not None:
        validated.append("packet")
    if receipt is not None:
        validated.append("receipt")
    print(f"product publication artifacts valid: {', '.join(validated)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
