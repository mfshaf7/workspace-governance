#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml


CONTRACT_FILES = {
    "version": "contracts/version.yaml",
    "lifecycle": "contracts/lifecycle.yaml",
    "dependency_types": "contracts/dependency-types.yaml",
    "repos": "contracts/repos.yaml",
    "products": "contracts/products.yaml",
    "components": "contracts/components.yaml",
    "task_types": "contracts/task-types.yaml",
    "change_classes": "contracts/change-classes.yaml",
    "evidence_obligations": "contracts/evidence-obligations.yaml",
    "review_obligations": "contracts/review-obligations.yaml",
    "vocabulary": "contracts/vocabulary.yaml",
    "exceptions": "contracts/exceptions.yaml",
    "validation_matrix": "contracts/validation-matrix.yaml",
}

SCHEMA_FILES = {
    "version": "contracts/schemas/version.schema.json",
    "lifecycle": "contracts/schemas/lifecycle.schema.json",
    "dependency_types": "contracts/schemas/dependency-types.schema.json",
    "repos": "contracts/schemas/repos.schema.json",
    "products": "contracts/schemas/products.schema.json",
    "components": "contracts/schemas/components.schema.json",
    "task_types": "contracts/schemas/task-types.schema.json",
    "change_classes": "contracts/schemas/change-classes.schema.json",
    "evidence_obligations": "contracts/schemas/evidence-obligations.schema.json",
    "review_obligations": "contracts/schemas/review-obligations.schema.json",
    "vocabulary": "contracts/schemas/vocabulary.schema.json",
    "exceptions": "contracts/schemas/exceptions.schema.json",
    "validation_matrix": "contracts/schemas/validation-matrix.schema.json",
}

REPO_RULES_SCHEMA = "contracts/schemas/repo-rules.schema.json"


def load_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text()) or {}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def dump_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def dump_yaml(path: Path, payload: Any) -> None:
    path.write_text(yaml.safe_dump(payload, sort_keys=False))


def load_contracts(repo_root: Path) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    contracts = {
        key: load_yaml(repo_root / rel_path) for key, rel_path in CONTRACT_FILES.items()
    }
    repo_rules_dir = repo_root / "contracts" / "repo-rules"
    contracts["repo_rules"] = {
        path.stem: load_yaml(path)
        for path in sorted(repo_rules_dir.glob("*.yaml"))
    }
    return contracts


def active_repo_names(contracts: dict[str, Any]) -> list[str]:
    return sorted(contracts["repos"]["repos"].keys())


def retired_repo_names(contracts: dict[str, Any]) -> list[str]:
    return sorted(contracts["repos"].get("retired_repos", {}).keys())


def generated_paths(repo_root: Path) -> dict[str, Path]:
    repo_root = repo_root.resolve()
    generated_root = repo_root / "generated"
    return {
        "system_map": generated_root / "system-map.yaml",
        "resolved_owner_map": generated_root / "resolved-owner-map.json",
        "resolved_dependency_graph": generated_root / "resolved-dependency-graph.json",
        "stale_content_rules": generated_root / "stale-content-rules.json",
    }
