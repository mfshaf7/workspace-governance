#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
import sys

import yaml

from contracts_lib import load_contracts


ALLOWED_SCOPES = {"platform", "component", "product"}
ALLOWED_BASELINE_STATUS = {"active", "superseded"}
ALLOWED_LATEST_CHANGE_STATUS = {"current", "baseline-current", "superseded"}
ALLOWED_REVIEW_DECISIONS = {
    "approved",
    "approved-with-findings",
    "blocked",
    "accepted-risk",
}


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text()) or {}


def parse_iso_date(
    value: object,
    *,
    path_label: str,
    field_name: str,
    errors: list[str],
) -> date | None:
    if not value:
        errors.append(f"{path_label}: missing {field_name}")
        return None
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        errors.append(f"{path_label}: invalid {field_name} type {type(value).__name__!r}")
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        errors.append(f"{path_label}: invalid {field_name} {value!r}")
        return None


def review_prefix_for_scope(scope: str) -> str:
    directory = {
        "platform": "platform",
        "component": "components",
        "product": "products",
    }[scope]
    return f"docs/reviews/{directory}/"


def validate_review_ref(
    section_name: str,
    subject_name: str,
    review_kind: str,
    review_payload: dict,
    *,
    scope: str,
    enforce_scope_prefix: bool,
    security_repo_root: Path,
    errors: list[str],
) -> tuple[str | None, date | None]:
    path_label = f"registers/review-inventory.yaml:{section_name}.{subject_name}.{review_kind}"
    review_path = review_payload.get("path")
    if not isinstance(review_path, str) or not review_path:
        errors.append(f"{path_label}: missing path")
        return None, None
    absolute_path = security_repo_root / review_path
    if not absolute_path.exists():
        errors.append(f"{path_label}: review artifact does not exist: {review_path}")
    if enforce_scope_prefix and not review_path.startswith(review_prefix_for_scope(scope)):
        errors.append(
            f"{path_label}: review artifact must live under {review_prefix_for_scope(scope)!r}, got {review_path!r}"
        )
    reviewed_on = parse_iso_date(
        review_payload.get("reviewed_on"),
        path_label=path_label,
        field_name="reviewed_on",
        errors=errors,
    )
    return review_path, reviewed_on


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate security review baseline coverage and freshness across the workspace."
    )
    parser.add_argument(
        "--workspace-root",
        default=Path(__file__).resolve().parents[2],
        type=Path,
        help="workspace root containing the active repos",
    )
    args = parser.parse_args()

    workspace_root = args.workspace_root.resolve()
    governance_root = Path(__file__).resolve().parents[1]
    security_repo_root = workspace_root / "security-architecture"
    inventory_path = security_repo_root / "registers" / "review-inventory.yaml"
    inventory = load_yaml(inventory_path)
    contracts = load_contracts(governance_root)

    errors: list[str] = []
    stale_baselines = 0
    repos_checked = 0
    components_checked = 0
    products_checked = 0

    if inventory.get("schema_version") != 1:
        errors.append("registers/review-inventory.yaml: schema_version must be 1")

    review_inventory = inventory.get("review_inventory")
    if not isinstance(review_inventory, dict):
        errors.append("registers/review-inventory.yaml: review_inventory must be a mapping")
        review_inventory = {}

    inventory_repos = review_inventory.get("repos") or {}
    inventory_components = review_inventory.get("components") or {}
    inventory_products = review_inventory.get("products") or {}

    expected_repos = {
        repo_name: {
            "owner_repo": repo_name,
            "scope": (
                "platform"
                if repo_name == "platform-engineering"
                else "component"
            ),
            "baseline_review_path": (
                contracts["repo_rules"][repo_name].get("security_requirements", {}).get("review_output_path")
            ),
        }
        for repo_name, payload in contracts["repos"]["repos"].items()
        if payload["requires_security_bindings"] or payload.get("security_review_subject")
    }
    for repo_name, payload in (contracts["intake_register"].get("repos") or {}).items():
        if (
            payload.get("status") == "admitted"
            and payload.get("requires_security_bindings")
        ):
            expected_repos[repo_name] = {
                "owner_repo": repo_name,
                "scope": "component",
                "baseline_review_path": None,
            }
    expected_components = {
        component_name: {
            "owner_repo": payload["owner_repo"],
            "scope": "component",
        }
        for component_name, payload in contracts["components"]["components"].items()
        if payload["security_owner"] == "security-architecture" and payload["lifecycle"] == "active"
    }
    for component_name, payload in (contracts["intake_register"].get("components") or {}).items():
        if (
            payload.get("status") == "admitted"
            and payload.get("security_owner") == "security-architecture"
        ):
            expected_components[component_name] = {
                "owner_repo": payload["owner_repo"],
                "scope": "component",
            }
    expected_products = {
        product_name: {
            "owner_repo": payload["platform_owner"],
            "scope": "product",
        }
        for product_name, payload in contracts["products"]["products"].items()
        if payload["security_owner"] == "security-architecture"
    }

    unknown_repos = sorted(set(inventory_repos) - set(expected_repos))
    unknown_components = sorted(set(inventory_components) - set(expected_components))
    unknown_products = sorted(set(inventory_products) - set(expected_products))
    if unknown_repos:
        errors.append("registers/review-inventory.yaml: unknown repo entries: " + ", ".join(unknown_repos))
    if unknown_components:
        errors.append(
            "registers/review-inventory.yaml: unknown component entries: " + ", ".join(unknown_components)
        )
    if unknown_products:
        errors.append(
            "registers/review-inventory.yaml: unknown product entries: " + ", ".join(unknown_products)
        )

    for section_name, expected_entries, inventory_entries in (
        ("repos", expected_repos, inventory_repos),
        ("components", expected_components, inventory_components),
        ("products", expected_products, inventory_products),
    ):
        for subject_name, expected in expected_entries.items():
            entry = inventory_entries.get(subject_name)
            if not isinstance(entry, dict):
                errors.append(f"registers/review-inventory.yaml: missing {section_name} entry for {subject_name}")
                continue

            owner_repo = entry.get("owner_repo")
            if owner_repo != expected["owner_repo"]:
                errors.append(
                    "registers/review-inventory.yaml:"
                    f" {section_name}.{subject_name}.owner_repo expected {expected['owner_repo']!r}, got {owner_repo!r}"
                )

            scope = entry.get("scope")
            if scope not in ALLOWED_SCOPES:
                errors.append(
                    f"registers/review-inventory.yaml: {section_name}.{subject_name}.scope must be one of "
                    + ", ".join(sorted(ALLOWED_SCOPES))
                )
                continue
            if scope != expected["scope"]:
                errors.append(
                    f"registers/review-inventory.yaml: {section_name}.{subject_name}.scope expected {expected['scope']!r}, got {scope!r}"
                )

            baseline_review = entry.get("baseline_review")
            latest_change_review = entry.get("latest_change_review")
            if not isinstance(baseline_review, dict):
                errors.append(
                    f"registers/review-inventory.yaml: {section_name}.{subject_name}.baseline_review must be a mapping"
                )
                continue
            if not isinstance(latest_change_review, dict):
                errors.append(
                    f"registers/review-inventory.yaml: {section_name}.{subject_name}.latest_change_review must be a mapping"
                )
                continue

            baseline_status = baseline_review.get("status")
            if baseline_status not in ALLOWED_BASELINE_STATUS:
                errors.append(
                    f"registers/review-inventory.yaml: {section_name}.{subject_name}.baseline_review.status must be one of "
                    + ", ".join(sorted(ALLOWED_BASELINE_STATUS))
                )
            baseline_decision = baseline_review.get("decision")
            if baseline_decision not in ALLOWED_REVIEW_DECISIONS:
                errors.append(
                    f"registers/review-inventory.yaml: {section_name}.{subject_name}.baseline_review.decision must be one of "
                    + ", ".join(sorted(ALLOWED_REVIEW_DECISIONS))
                )
            baseline_path, baseline_reviewed_on = validate_review_ref(
                section_name,
                subject_name,
                "baseline_review",
                baseline_review,
                scope=scope,
                enforce_scope_prefix=True,
                security_repo_root=security_repo_root,
                errors=errors,
            )
            if section_name == "repos" and expected.get("baseline_review_path") and baseline_path != expected["baseline_review_path"]:
                errors.append(
                    f"registers/review-inventory.yaml: repos.{subject_name}.baseline_review.path must match repo-rules review_output_path"
                )
            review_due_on = parse_iso_date(
                baseline_review.get("review_due_on"),
                path_label=f"registers/review-inventory.yaml:{section_name}.{subject_name}.baseline_review",
                field_name="review_due_on",
                errors=errors,
            )
            if baseline_reviewed_on and review_due_on and review_due_on < baseline_reviewed_on:
                errors.append(
                    f"registers/review-inventory.yaml: {section_name}.{subject_name}.baseline_review.review_due_on cannot be earlier than reviewed_on"
                )
            if review_due_on and review_due_on < date.today():
                stale_baselines += 1
                errors.append(
                    f"registers/review-inventory.yaml: {section_name}.{subject_name} baseline review expired on {review_due_on.isoformat()}"
                )

            latest_status = latest_change_review.get("status")
            if latest_status not in ALLOWED_LATEST_CHANGE_STATUS:
                errors.append(
                    f"registers/review-inventory.yaml: {section_name}.{subject_name}.latest_change_review.status must be one of "
                    + ", ".join(sorted(ALLOWED_LATEST_CHANGE_STATUS))
                )
            latest_decision = latest_change_review.get("decision")
            if latest_decision not in ALLOWED_REVIEW_DECISIONS:
                errors.append(
                    f"registers/review-inventory.yaml: {section_name}.{subject_name}.latest_change_review.decision must be one of "
                    + ", ".join(sorted(ALLOWED_REVIEW_DECISIONS))
                )
            latest_path, _ = validate_review_ref(
                section_name,
                subject_name,
                "latest_change_review",
                latest_change_review,
                scope=scope,
                enforce_scope_prefix=False,
                security_repo_root=security_repo_root,
                errors=errors,
            )
            if latest_status == "baseline-current" and latest_path != baseline_path:
                errors.append(
                    f"registers/review-inventory.yaml: {section_name}.{subject_name}.latest_change_review must match baseline_review when status is baseline-current"
                )
            if latest_status == "baseline-current" and latest_decision != baseline_decision:
                errors.append(
                    f"registers/review-inventory.yaml: {section_name}.{subject_name}.latest_change_review.decision must match baseline_review.decision when status is baseline-current"
                )
            review_trigger_ids = latest_change_review.get("review_trigger_ids")
            if review_trigger_ids is not None:
                if (
                    not isinstance(review_trigger_ids, list)
                    or not review_trigger_ids
                    or any(not isinstance(entry, str) or not entry for entry in review_trigger_ids)
                ):
                    errors.append(
                        f"registers/review-inventory.yaml: {section_name}.{subject_name}.latest_change_review.review_trigger_ids must be a non-empty list of strings when present"
                    )

            if section_name == "repos":
                repos_checked += 1
            elif section_name == "components":
                components_checked += 1
            else:
                products_checked += 1

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print(
        "review coverage valid: "
        f"repos={repos_checked} "
        f"components={components_checked} "
        f"products={products_checked} "
        f"stale_baselines={stale_baselines}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
