#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml


CONTRACT_FILES = {
    "version": "contracts/version.yaml",
    "lifecycle": "contracts/lifecycle.yaml",
    "intake_policy": "contracts/intake-policy.yaml",
    "intake_register": "contracts/intake-register.yaml",
    "governed_intake_assist": "contracts/governed-intake-assist.yaml",
    "developer_integration_policy": "contracts/developer-integration-policy.yaml",
    "developer_integration_profiles": "contracts/developer-integration-profiles.yaml",
    "delegation_policy": "contracts/delegation-policy.yaml",
    "self_improvement_policy": "contracts/self-improvement-policy.yaml",
    "work_home_routing": "contracts/work-home-routing.yaml",
    "dependency_types": "contracts/dependency-types.yaml",
    "repos": "contracts/repos.yaml",
    "products": "contracts/products.yaml",
    "components": "contracts/components.yaml",
    "task_types": "contracts/task-types.yaml",
    "change_classes": "contracts/change-classes.yaml",
    "failure_taxonomy": "contracts/failure-taxonomy.yaml",
    "improvement_triggers": "contracts/improvement-triggers.yaml",
    "evidence_obligations": "contracts/evidence-obligations.yaml",
    "review_obligations": "contracts/review-obligations.yaml",
    "vocabulary": "contracts/vocabulary.yaml",
    "exceptions": "contracts/exceptions.yaml",
    "validation_matrix": "contracts/validation-matrix.yaml",
    "skills": "contracts/skills.yaml",
    "governance_engine_foundation": "contracts/governance-engine-foundation.yaml",
    "governance_engine_output_manifest": "contracts/governance-engine-output-manifest.yaml",
    "governance_engine_boundary_map": "contracts/governance-engine-boundary-map.yaml",
    "governance_engine_shadow_parity": "contracts/governance-engine-shadow-parity.yaml",
    "governance_engine_extraction_gate": "contracts/governance-engine-extraction-gate.yaml",
}

SCHEMA_FILES = {
    "version": "contracts/schemas/version.schema.json",
    "lifecycle": "contracts/schemas/lifecycle.schema.json",
    "intake_policy": "contracts/schemas/intake-policy.schema.json",
    "intake_register": "contracts/schemas/intake-register.schema.json",
    "governed_intake_assist": "contracts/schemas/governed-intake-assist.schema.json",
    "developer_integration_policy": "contracts/schemas/developer-integration-policy.schema.json",
    "developer_integration_profiles": "contracts/schemas/developer-integration-profiles.schema.json",
    "delegation_policy": "contracts/schemas/delegation-policy.schema.json",
    "self_improvement_policy": "contracts/schemas/self-improvement-policy.schema.json",
    "work_home_routing": "contracts/schemas/work-home-routing.schema.json",
    "dependency_types": "contracts/schemas/dependency-types.schema.json",
    "repos": "contracts/schemas/repos.schema.json",
    "products": "contracts/schemas/products.schema.json",
    "components": "contracts/schemas/components.schema.json",
    "task_types": "contracts/schemas/task-types.schema.json",
    "change_classes": "contracts/schemas/change-classes.schema.json",
    "failure_taxonomy": "contracts/schemas/failure-taxonomy.schema.json",
    "improvement_triggers": "contracts/schemas/improvement-triggers.schema.json",
    "evidence_obligations": "contracts/schemas/evidence-obligations.schema.json",
    "review_obligations": "contracts/schemas/review-obligations.schema.json",
    "vocabulary": "contracts/schemas/vocabulary.schema.json",
    "exceptions": "contracts/schemas/exceptions.schema.json",
    "validation_matrix": "contracts/schemas/validation-matrix.schema.json",
    "skills": "contracts/schemas/skills.schema.json",
    "governance_engine_foundation": "contracts/schemas/governance-engine-foundation.schema.json",
    "governance_engine_output_manifest": "contracts/schemas/governance-engine-output-manifest.schema.json",
    "governance_engine_boundary_map": "contracts/schemas/governance-engine-boundary-map.schema.json",
    "governance_engine_shadow_parity": "contracts/schemas/governance-engine-shadow-parity.schema.json",
    "governance_engine_extraction_gate": "contracts/schemas/governance-engine-extraction-gate.schema.json",
}

REPO_RULES_SCHEMA = "contracts/schemas/repo-rules.schema.json"
AFTER_ACTION_RECORD_SCHEMA = "contracts/schemas/after-action-record.schema.json"


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


def intake_repo_names(contracts: dict[str, Any]) -> list[str]:
    return sorted(contracts["intake_register"]["repos"].keys())


def retired_repo_names(contracts: dict[str, Any]) -> list[str]:
    return sorted(contracts["repos"].get("retired_repos", {}).keys())


def output_manifest_families(contracts: dict[str, Any]) -> dict[str, dict[str, Any]]:
    manifest = contracts["governance_engine_output_manifest"][
        "governance_engine_output_manifest"
    ]
    return {
        family["id"]: family
        for family in manifest["emission_families"]
    }


def output_manifest_family(
    contracts: dict[str, Any], family_id: str
) -> dict[str, Any]:
    families = output_manifest_families(contracts)
    try:
        return families[family_id]
    except KeyError as exc:
        raise KeyError(f"unknown governance-engine output family: {family_id}") from exc


def workspace_root_sync_map(contracts: dict[str, Any]) -> tuple[tuple[str, str], ...]:
    family = output_manifest_family(contracts, "workspace-root-sync")
    return tuple(
        (entry["source_path"], entry["emitted_path"])
        for entry in family["outputs"]
    )


def skill_install_manifest_name(contracts: dict[str, Any]) -> str:
    family = output_manifest_family(contracts, "installed-skills")
    return family["managed_manifest_filename"]


def generated_output_specs(
    repo_root: Path, contracts: dict[str, Any] | None = None
) -> dict[str, dict[str, Any]]:
    repo_root = repo_root.resolve()
    if contracts is None:
        contracts = load_contracts(repo_root)
    family = output_manifest_family(contracts, "generated-governance-artifacts")
    return {
        entry["id"]: {
            "path": repo_root / entry["emitted_path"],
            "format": entry["format"],
        }
        for entry in family["outputs"]
    }


def generated_paths(repo_root: Path, contracts: dict[str, Any] | None = None) -> dict[str, Path]:
    return {
        output_id: payload["path"]
        for output_id, payload in generated_output_specs(repo_root, contracts).items()
    }
