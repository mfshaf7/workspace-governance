#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
import subprocess
import sys
from typing import Any

from jsonschema import Draft202012Validator
import yaml

from contracts_lib import AFTER_ACTION_RECORD_SCHEMA, load_json


IMPROVEMENT_CANDIDATE_SCHEMA = "contracts/schemas/improvement-candidate-record.schema.json"


def normalize_for_schema(value: Any) -> Any:
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, list):
        return [normalize_for_schema(item) for item in value]
    if isinstance(value, dict):
        return {key: normalize_for_schema(item) for key, item in value.items()}
    return value


def load_yaml_record(path: Path) -> dict:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if loaded is None:
        return {}
    if not isinstance(loaded, dict):
        raise ValueError(f"{path}: YAML record must be a mapping at the root")
    return loaded


def validate_yaml_schema(path: Path, schema_path: Path) -> list[str]:
    record = load_yaml_record(path)
    schema = load_json(schema_path)
    validator = Draft202012Validator(schema)
    issues: list[str] = []
    for error in validator.iter_errors(normalize_for_schema(record)):
        field_path = ".".join(str(part) for part in error.absolute_path) or "<root>"
        issues.append(f"{path}: {field_path}: {error.message}")
    return issues


def find_repo_root(path: Path, workspace_root: Path) -> Path:
    current = path if path.is_dir() else path.parent
    workspace_root = workspace_root.resolve()
    while current != current.parent:
        if (current / ".git").exists():
            return current.resolve()
        if current.resolve() == workspace_root:
            break
        current = current.parent
    raise ValueError(f"{path}: cannot find owning git repository below {workspace_root}")


def repo_relative(path: Path, repo_root: Path) -> str:
    return path.resolve().relative_to(repo_root.resolve()).as_posix()


def run_validator(command: list[str], cwd: Path) -> int:
    print(f"+ {' '.join(command)}", flush=True)
    completed = subprocess.run(command, cwd=cwd, text=True)
    return completed.returncode


def is_change_record(path: Path, repo_root: Path) -> bool:
    relative = repo_relative(path, repo_root)
    return (
        relative.startswith("docs/records/change-records/")
        and relative.endswith(".md")
        and path.name != "README.md"
    )


def validate_path(path: Path, *, workspace_root: Path, workspace_governance_root: Path) -> int:
    if not path.exists():
        print(f"{path}: path does not exist", file=sys.stderr)
        return 1

    repo_root = find_repo_root(path, workspace_root)
    relative = repo_relative(path, repo_root)
    issues: list[str] = []
    commands: list[tuple[list[str], Path]] = []

    try:
        if repo_root == workspace_governance_root:
            if relative.startswith("reviews/improvement-candidates/") and path.suffix == ".yaml":
                if path.name != "TEMPLATE.yaml":
                    issues.extend(
                        validate_yaml_schema(
                            path,
                            workspace_governance_root / IMPROVEMENT_CANDIDATE_SCHEMA,
                        ),
                    )
                commands.append(
                    (
                        [
                            sys.executable,
                            "scripts/validate_improvement_candidates.py",
                            "--workspace-root",
                            str(workspace_root),
                        ],
                        workspace_governance_root,
                    ),
                )
            elif relative.startswith("reviews/after-action/") and path.suffix == ".yaml":
                if path.name != "TEMPLATE.yaml":
                    issues.extend(
                        validate_yaml_schema(
                            path,
                            workspace_governance_root / AFTER_ACTION_RECORD_SCHEMA,
                        ),
                    )
                commands.append(
                    (
                        [
                            sys.executable,
                            "scripts/validate_learning_closure.py",
                            "--workspace-root",
                            str(workspace_root),
                        ],
                        workspace_governance_root,
                    ),
                )
            elif relative.startswith("reviews/delegation-journal/") and path.suffix == ".yaml":
                load_yaml_record(path)
                commands.append(
                    (
                        [
                            sys.executable,
                            "scripts/validate_delegation_journal.py",
                            "--repo-root",
                            str(workspace_governance_root),
                        ],
                        workspace_governance_root,
                    ),
                )
            elif relative.startswith("contracts/") and path.suffix in {".yaml", ".yml", ".json"}:
                if path.suffix in {".yaml", ".yml"}:
                    load_yaml_record(path)
                commands.append(
                    (
                        [
                            sys.executable,
                            "scripts/validate_contracts.py",
                            "--repo-root",
                            str(workspace_governance_root),
                        ],
                        workspace_governance_root,
                    ),
                )

        if is_change_record(path, repo_root):
            local_validator = repo_root / "scripts" / "validate_governance_docs.py"
            if local_validator.exists():
                commands.append(
                    (
                        [
                            sys.executable,
                            str(local_validator.relative_to(repo_root)),
                            "--repo-root",
                            str(repo_root),
                        ],
                        repo_root,
                    ),
                )
            else:
                issues.append(
                    f"{path}: owning repo has no scripts/validate_governance_docs.py for change-record preflight",
                )
    except (OSError, ValueError, yaml.YAMLError) as error:
        issues.append(str(error))

    if issues:
        for issue in issues:
            print(issue, file=sys.stderr)
        return 1

    if not commands:
        print(f"{path}: no structured-record preflight rule matched", file=sys.stderr)
        return 1

    failed = 0
    seen: set[tuple[tuple[str, ...], Path]] = set()
    for command, cwd in commands:
        key = (tuple(command), cwd.resolve())
        if key in seen:
            continue
        seen.add(key)
        failed |= run_validator(command, cwd)

    if failed:
        return 1

    print(f"structured record valid: {path}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate a touched structured governance record immediately.",
    )
    parser.add_argument("paths", nargs="+", type=Path, help="record path(s) to validate")
    parser.add_argument(
        "--workspace-root",
        default=Path(__file__).resolve().parents[2],
        type=Path,
        help="workspace root containing the active repos",
    )
    parser.add_argument(
        "--repo-root",
        default=Path(__file__).resolve().parents[1],
        type=Path,
        help="workspace-governance repository root",
    )
    args = parser.parse_args()

    workspace_root = args.workspace_root.resolve()
    workspace_governance_root = args.repo_root.resolve()
    exit_code = 0
    for raw_path in args.paths:
        path = raw_path if raw_path.is_absolute() else Path.cwd() / raw_path
        exit_code |= validate_path(
            path.resolve(),
            workspace_governance_root=workspace_governance_root,
            workspace_root=workspace_root,
        )
    return 1 if exit_code else 0


if __name__ == "__main__":
    sys.exit(main())
