#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
import sys

from jsonschema import Draft202012Validator
import yaml

from contracts_lib import (
    REPO_RULES_SCHEMA,
    SCHEMA_FILES,
    active_repo_names,
    load_contracts,
    load_json,
)


def validate_schema(errors: list[str], instance_path: Path, schema_path: Path) -> None:
    instance = yaml.safe_load(instance_path.read_text()) or {}
    schema = load_json(schema_path)
    validator = Draft202012Validator(schema)
    for error in validator.iter_errors(instance):
        path = ".".join(str(part) for part in error.absolute_path) or "<root>"
        errors.append(f"{instance_path}: {path}: {error.message}")


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

    instance_paths = {
        "version": repo_root / "contracts/version.yaml",
        "lifecycle": repo_root / "contracts/lifecycle.yaml",
        "intake_policy": repo_root / "contracts/intake-policy.yaml",
        "intake_register": repo_root / "contracts/intake-register.yaml",
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
    }

    for key, rel_path in SCHEMA_FILES.items():
        validate_schema(errors, instance_paths[key], repo_root / rel_path)

    repo_rules_schema = repo_root / REPO_RULES_SCHEMA
    for path in sorted((repo_root / "contracts" / "repo-rules").glob("*.yaml")):
        validate_schema(errors, path, repo_rules_schema)

    contracts = load_contracts(repo_root)
    lifecycle_states = set(contracts["lifecycle"]["states"].keys())
    intake_policy = contracts["intake_policy"]
    intake_register = contracts["intake_register"]
    intake_statuses = set(intake_policy["statuses"])
    active_repos = set(active_repo_names(contracts))
    intake_repos = set(intake_register["repos"].keys())
    product_names = set(contracts["products"]["products"].keys())
    intake_products = set(intake_register["products"].keys())
    change_classes = set(contracts["change_classes"]["change_classes"].keys())
    component_names = set(contracts["components"]["components"].keys())
    intake_components = set(intake_register["components"].keys())
    failure_classes = contracts["failure_taxonomy"]["failure_classes"]
    improvement_triggers = contracts["improvement_triggers"]["triggers"]
    validator_scripts = contracts["validation_matrix"]["validators"]
    registered_skills = contracts["skills"]["skills"]

    expected_intake_statuses = {"out-of-scope", "proposed", "admitted"}
    if intake_statuses != expected_intake_statuses:
        errors.append(
            "contracts/intake-policy.yaml: statuses must be exactly out-of-scope, proposed, admitted"
        )

    for repo_name, payload in contracts["repos"]["repos"].items():
        if payload["lifecycle"] not in lifecycle_states:
            errors.append(f"contracts/repos.yaml: {repo_name} uses unknown lifecycle {payload['lifecycle']!r}")
        for ref in payload["allowed_authoritative_refs"]:
            if ref not in active_repos:
                errors.append(f"contracts/repos.yaml: {repo_name} references unknown repo {ref!r}")

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
        if security_change_record_requirements and not security_requirements:
            errors.append(
                f"contracts/repo-rules/{repo_name}.yaml: security_change_record_requirements require security_requirements"
            )

    for product_name, payload in contracts["products"]["products"].items():
        if payload["lifecycle"] not in lifecycle_states:
            errors.append(f"contracts/products.yaml: {product_name} uses unknown lifecycle {payload['lifecycle']!r}")
        for owner_key in ("platform_owner", "security_owner", "runtime_owner"):
            if payload[owner_key] not in active_repos:
                errors.append(f"contracts/products.yaml: {product_name} {owner_key} {payload[owner_key]!r} is not an active repo")
        for repo_name in payload["source_owners"]:
            if repo_name not in active_repos:
                errors.append(f"contracts/products.yaml: {product_name} source owner {repo_name!r} is not an active repo")

    for component_name, payload in contracts["components"]["components"].items():
        if payload["lifecycle"] not in lifecycle_states:
            errors.append(f"contracts/components.yaml: {component_name} uses unknown lifecycle {payload['lifecycle']!r}")
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
