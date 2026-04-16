#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
import sys
from typing import Any

from jsonschema import Draft202012Validator
import yaml

from contracts_lib import AFTER_ACTION_RECORD_SCHEMA, load_contracts, load_json


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
    parser = argparse.ArgumentParser(description="Validate after-action learning closure for workspace-governance.")
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
    after_action_dir = repo_root / "reviews" / "after-action"
    schema_path = repo_root / AFTER_ACTION_RECORD_SCHEMA
    errors: list[str] = []
    record_count = 0
    open_lessons = 0
    closed_lessons = 0

    for record_path in sorted(path for path in after_action_dir.glob("*.yaml") if path.name != "TEMPLATE.yaml"):
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

        for lesson in record.get("lessons", []):
            failure_class = lesson["failure_class"]
            trigger = lesson["trigger"]
            expected_control_types = set(lesson.get("expected_control_types") or [])
            control_refs = lesson.get("control_refs") or []
            follow_up = lesson.get("follow_up") or {}

            if failure_class not in failure_classes:
                errors.append(f"{record_path}: lesson {lesson['id']} uses unknown failure_class {failure_class!r}")
                failure_recommended = set()
            else:
                failure_recommended = set(failure_classes[failure_class]["recommended_control_types"])

            if trigger not in triggers:
                errors.append(f"{record_path}: lesson {lesson['id']} uses unknown trigger {trigger!r}")
                trigger_recommended = set()
            else:
                trigger_recommended = set(triggers[trigger]["recommended_control_types"])

            if expected_control_types and failure_recommended and expected_control_types.isdisjoint(failure_recommended):
                errors.append(
                    f"{record_path}: lesson {lesson['id']} expected_control_types do not overlap the failure taxonomy recommendations"
                )

            if expected_control_types and trigger_recommended and expected_control_types.isdisjoint(trigger_recommended):
                errors.append(
                    f"{record_path}: lesson {lesson['id']} expected_control_types do not overlap the trigger recommendations"
                )

            matched_control_types: set[str] = set()
            for control in control_refs:
                owner_repo = control["owner_repo"]
                path = control["path"]
                matched_control_types.add(control["type"])
                if owner_repo not in active_repos:
                    errors.append(f"{record_path}: lesson {lesson['id']} control owner_repo {owner_repo!r} is not an active repo")
                if path.startswith("/"):
                    errors.append(f"{record_path}: lesson {lesson['id']} control path must be workspace-relative, got {path!r}")
                if not path.startswith(f"{owner_repo}/"):
                    errors.append(
                        f"{record_path}: lesson {lesson['id']} control path {path!r} must start with {owner_repo!r}/"
                    )
                if not (workspace_root / path).exists():
                    errors.append(f"{record_path}: lesson {lesson['id']} references missing control path {path!r}")

            if lesson["status"] == "closed":
                closed_lessons += 1
                if not control_refs:
                    errors.append(f"{record_path}: lesson {lesson['id']} is closed but has no control_refs")
                if expected_control_types and matched_control_types and expected_control_types.isdisjoint(matched_control_types):
                    errors.append(
                        f"{record_path}: lesson {lesson['id']} closed with control types that do not satisfy expected_control_types"
                    )
                if any(follow_up.get(field) not in (None, "") for field in ("owner_repo", "due_on", "note")):
                    errors.append(f"{record_path}: lesson {lesson['id']} is closed but still carries follow_up fields")
            else:
                open_lessons += 1
                follow_up_owner = follow_up.get("owner_repo")
                follow_up_due_on = follow_up.get("due_on")
                follow_up_note = follow_up.get("note")
                if follow_up_owner not in active_repos:
                    errors.append(f"{record_path}: lesson {lesson['id']} is open and needs a valid follow_up.owner_repo")
                if not follow_up_due_on:
                    errors.append(f"{record_path}: lesson {lesson['id']} is open and needs follow_up.due_on")
                else:
                    parsed_due_on = parse_iso_date(
                        follow_up_due_on,
                        field_name=f"lesson {lesson['id']} follow_up.due_on",
                        record_path=record_path,
                        errors=errors,
                    )
                    if parsed_due_on and parsed_due_on < date.today():
                        errors.append(
                            f"{record_path}: lesson {lesson['id']} follow_up.due_on {follow_up_due_on} is in the past"
                        )
                if not follow_up_note:
                    errors.append(f"{record_path}: lesson {lesson['id']} is open and needs follow_up.note")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print(
        "learning closure valid: "
        f"records={record_count} "
        f"open_lessons={open_lessons} "
        f"closed_lessons={closed_lessons}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
