#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
import sys
from typing import Any

from jsonschema import Draft202012Validator
import yaml

from contracts_lib import load_contracts, load_json


IMPROVEMENT_CANDIDATE_SCHEMA = "contracts/schemas/improvement-candidate-record.schema.json"


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def normalize_for_schema(value: Any) -> Any:
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, list):
        return [normalize_for_schema(item) for item in value]
    if isinstance(value, dict):
        return {key: normalize_for_schema(item) for key, item in value.items()}
    return value


def validate_schema(errors: list[str], record_path: Path, schema_path: Path) -> dict:
    instance = load_yaml(record_path)
    schema = load_json(schema_path)
    validator = Draft202012Validator(schema)
    for error in validator.iter_errors(normalize_for_schema(instance)):
        path = ".".join(str(part) for part in error.absolute_path) or "<root>"
        errors.append(f"{record_path}: {path}: {error.message}")
    return instance


def parse_iso_date(raw: object, *, field_name: str, record_path: Path, errors: list[str]) -> date | None:
    if isinstance(raw, date):
        return raw
    if not isinstance(raw, str):
        errors.append(f"{record_path}: invalid {field_name} {raw!r}")
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        errors.append(f"{record_path}: invalid {field_name} {raw!r}")
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate improvement candidate records for workspace-governance.")
    parser.add_argument(
        "--repo-root",
        default=Path(__file__).resolve().parents[1],
        type=Path,
        help="workspace-governance repository root",
    )
    parser.add_argument(
        "--workspace-root",
        default=Path(__file__).resolve().parents[2],
        type=Path,
        help="workspace root containing the active repos",
    )
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    workspace_root = args.workspace_root.resolve()
    contracts = load_contracts(repo_root)
    active_repos = set(contracts["repos"]["repos"].keys())
    product_names = set(contracts["products"]["products"].keys())
    component_names = set(contracts["components"]["components"].keys())
    change_classes = set(contracts["change_classes"]["change_classes"].keys())
    failure_classes = contracts["failure_taxonomy"]["failure_classes"]
    triggers = contracts["improvement_triggers"]["triggers"]
    candidate_dir = repo_root / "reviews" / "improvement-candidates"
    schema_path = repo_root / IMPROVEMENT_CANDIDATE_SCHEMA
    errors: list[str] = []
    record_count = 0
    open_candidates = 0
    closed_candidates = 0

    for record_path in sorted(path for path in candidate_dir.glob("*.yaml") if path.name != "TEMPLATE.yaml"):
        record_count += 1
        record = validate_schema(errors, record_path, schema_path)
        if record.get("id") != record_path.stem:
            errors.append(f"{record_path}: id must match filename stem")

        if record.get("owner_repo") not in active_repos:
            errors.append(f"{record_path}: owner_repo {record.get('owner_repo')!r} is not an active repo")

        for repo_name in record.get("scope", {}).get("related_repos", []):
            if repo_name not in active_repos:
                errors.append(f"{record_path}: related_repos includes unknown repo {repo_name!r}")
        for product_name in record.get("scope", {}).get("related_products", []):
            if product_name not in product_names:
                errors.append(f"{record_path}: related_products includes unknown product {product_name!r}")
        for component_name in record.get("scope", {}).get("related_components", []):
            if component_name not in component_names:
                errors.append(f"{record_path}: related_components includes unknown component {component_name!r}")
        for change_class in record.get("scope", {}).get("change_classes", []):
            if change_class not in change_classes:
                errors.append(f"{record_path}: change_classes includes unknown class {change_class!r}")

        parse_iso_date(record["recorded_on"], field_name="recorded_on", record_path=record_path, errors=errors)

        seen_signal_ids: set[str] = set()
        for signal in record.get("signals", []):
            signal_id = signal["id"]
            if signal_id in seen_signal_ids:
                errors.append(f"{record_path}: duplicate signal id {signal_id!r}")
            seen_signal_ids.add(signal_id)
            if signal["trigger"] not in triggers:
                errors.append(f"{record_path}: signal {signal_id} uses unknown trigger {signal['trigger']!r}")
            for failure_class in signal["failure_classes"]:
                if failure_class not in failure_classes:
                    errors.append(
                        f"{record_path}: signal {signal_id} uses unknown failure_class {failure_class!r}"
                    )

        resolution = record.get("resolution") or {}
        after_action_ref = resolution.get("after_action_ref")
        control_refs = resolution.get("control_refs") or []
        resolution_note = resolution.get("note")
        for control in control_refs:
            owner_repo = control["owner_repo"]
            path = control["path"]
            if owner_repo not in active_repos:
                errors.append(f"{record_path}: control owner_repo {owner_repo!r} is not an active repo")
            if path.startswith("/"):
                errors.append(f"{record_path}: control path must be workspace-relative, got {path!r}")
            if not path.startswith(f"{owner_repo}/"):
                errors.append(f"{record_path}: control path {path!r} must start with {owner_repo!r}/")
            if not (workspace_root / path).exists():
                errors.append(f"{record_path}: references missing control path {path!r}")

        if after_action_ref:
            if after_action_ref.startswith("/"):
                errors.append(f"{record_path}: after_action_ref must be workspace-relative, got {after_action_ref!r}")
            if not after_action_ref.startswith("workspace-governance/reviews/after-action/"):
                errors.append(
                    f"{record_path}: after_action_ref must stay under workspace-governance/reviews/after-action/, got {after_action_ref!r}"
                )
            elif not (workspace_root / after_action_ref).exists():
                errors.append(f"{record_path}: references missing after_action_ref {after_action_ref!r}")

        status = record["status"]
        follow_up = record.get("follow_up") or {}
        if status in {"new", "triaged", "accepted"}:
            open_candidates += 1
            follow_up_owner = follow_up.get("owner_repo")
            follow_up_due_on = follow_up.get("due_on")
            follow_up_note = follow_up.get("note")
            if follow_up_owner not in active_repos:
                errors.append(f"{record_path}: status {status!r} needs a valid follow_up.owner_repo")
            if not follow_up_due_on:
                errors.append(f"{record_path}: status {status!r} needs follow_up.due_on")
            else:
                parsed_due_on = parse_iso_date(
                    follow_up_due_on,
                    field_name="follow_up.due_on",
                    record_path=record_path,
                    errors=errors,
                )
                if parsed_due_on and parsed_due_on < date.today():
                    errors.append(f"{record_path}: follow_up.due_on {follow_up_due_on} is in the past")
            if not follow_up_note:
                errors.append(f"{record_path}: status {status!r} needs follow_up.note")
        else:
            closed_candidates += 1
            if any(follow_up.get(field) not in (None, "") for field in ("owner_repo", "due_on", "note")):
                errors.append(f"{record_path}: status {status!r} must not keep follow_up fields")
            if status == "dismissed" and not resolution_note:
                errors.append(f"{record_path}: dismissed candidate needs resolution.note")
            if status == "closed" and not (after_action_ref or control_refs or resolution_note):
                errors.append(
                    f"{record_path}: closed candidate needs an after_action_ref, control_refs, or resolution.note"
                )

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print(
        "improvement candidates valid: "
        f"records={record_count} "
        f"open_candidates={open_candidates} "
        f"closed_candidates={closed_candidates}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
