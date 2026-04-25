#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path
import sys

import yaml

from contracts_lib import (
    active_repo_names,
    dump_json,
    dump_yaml,
    generated_paths,
    load_contracts,
    load_json,
)


DOC_EXCLUDES = (
    "/.git/",
    "/docs/archive/",
    "/docs/records/change-records/",
    "/docs/decisions/adr/",
)

WORKSPACE_ROOT_REPO_COVERAGE_REQUIREMENTS = {
    "AGENTS.md": (
        "## Current Owner Map",
        "## Routing Rules",
    ),
    "README.md": (
        "## Active Repository Roles",
        "## Start Here",
    ),
    "ARCHITECTURE.md": (
        "## Active Owner Repos",
        "## Read Next By Task",
    ),
}

SECURITY_ARCHITECTURE_COMPONENT_COVERAGE_REQUIREMENTS = {
    "docs/architecture/components/README.md": "({component_name}/README.md)",
    "docs/architecture/platform/component-inventory.md": "../components/{component_name}/README.md",
}

DELIVERY_ART_PLANNING_WORKFLOW_CONTRACT_PATHS = {
    "platform": Path(
        "platform-engineering/products/openproject/delivery-art-planning-workflow.json"
    ),
    "broker": Path("operator-orchestration-service/src/delivery-planning-workflow.json"),
}

DELIVERY_ART_INITIATIVE_REVIEW_WORKFLOW_CONTRACT_PATHS = {
    "platform": Path(
        "platform-engineering/products/openproject/delivery-art-initiative-review-workflow.json"
    ),
    "broker": Path(
        "operator-orchestration-service/src/delivery-initiative-review-workflow.json"
    ),
}

DELIVERY_ART_OPERATOR_PATH_CONTRACT_PATH = Path(
    "workspace-governance/contracts/delivery-art-operator-path.yaml"
)


def gather_active_docs(repo_root: Path) -> list[Path]:
    files: list[Path] = []
    for path in repo_root.rglob("*.md"):
        path_str = str(path)
        if any(marker in path_str for marker in DOC_EXCLUDES):
            continue
        files.append(path)
    return sorted(files)


def extract_section(text: str, heading: str) -> str | None:
    lines = text.splitlines()
    target = heading.strip().lower()
    collecting = False
    collected: list[str] = []

    for line in lines:
        stripped = line.strip()
        if stripped.lower() == target:
            collecting = True
            continue
        if collecting and stripped.startswith("## "):
            break
        if collecting:
            collected.append(line)

    if not collecting:
        return None
    return "\n".join(collected).strip()


def validate_workspace_root_repo_coverage(
    workspace_root_docs: Path,
    active_repos: list[str],
    errors: list[str],
) -> None:
    for filename, headings in WORKSPACE_ROOT_REPO_COVERAGE_REQUIREMENTS.items():
        path = workspace_root_docs / filename
        if not path.exists():
            errors.append(f"{path}: missing workspace-root doc for active repo coverage check")
            continue

        text = path.read_text(encoding="utf-8")
        for heading in headings:
            section = extract_section(text, heading)
            if section is None:
                errors.append(f"{path}: missing section {heading!r} for active repo coverage check")
                continue

            missing_repos = [repo_name for repo_name in active_repos if repo_name not in section]
            if missing_repos:
                missing_text = ", ".join(repr(repo_name) for repo_name in missing_repos)
                errors.append(
                    f"{path}: section {heading!r} missing active repos {missing_text}"
                )


def validate_security_architecture_component_coverage(
    workspace_root: Path,
    contracts: dict[str, object],
    errors: list[str],
) -> None:
    security_repo_root = workspace_root / "security-architecture"
    if not security_repo_root.exists():
        errors.append(f"{security_repo_root}: missing security-architecture repo for component coverage check")
        return

    active_security_components = sorted(
        component_name
        for component_name, payload in contracts["components"]["components"].items()
        if payload["lifecycle"] == "active" and payload["security_owner"] == "security-architecture"
    )

    for component_name in active_security_components:
        component_doc = (
            security_repo_root / "docs" / "architecture" / "components" / component_name / "README.md"
        )
        if not component_doc.exists():
            errors.append(
                f"{component_doc}: missing security component view for active component {component_name!r}"
            )

    for rel_path, pattern in SECURITY_ARCHITECTURE_COMPONENT_COVERAGE_REQUIREMENTS.items():
        path = security_repo_root / rel_path
        if not path.exists():
            errors.append(f"{path}: missing security-architecture component coverage doc")
            continue
        text = path.read_text(encoding="utf-8")
        missing_components = [
            component_name
            for component_name in active_security_components
            if pattern.format(component_name=component_name) not in text
        ]
        if missing_components:
            missing_text = ", ".join(repr(name) for name in missing_components)
            errors.append(f"{path}: missing security component coverage for {missing_text}")


def validate_delivery_art_planning_workflow_contract(
    workspace_root: Path,
    errors: list[str],
) -> None:
    resolved_paths = {
        name: workspace_root / relative_path
        for name, relative_path in DELIVERY_ART_PLANNING_WORKFLOW_CONTRACT_PATHS.items()
    }

    missing = [
        f"{name}={path}"
        for name, path in resolved_paths.items()
        if not path.exists()
    ]
    if missing:
        errors.append(
            "delivery-art planning workflow contract missing: " + ", ".join(missing)
        )
        return

    platform_contract = load_json(resolved_paths["platform"])
    broker_contract = load_json(resolved_paths["broker"])
    if platform_contract != broker_contract:
        errors.append(
            "delivery-art planning workflow drift: "
            f"{resolved_paths['platform']} does not match {resolved_paths['broker']}"
        )


def validate_delivery_art_initiative_review_workflow_contract(
    workspace_root: Path,
    errors: list[str],
) -> None:
    resolved_paths = {
        name: workspace_root / relative_path
        for name, relative_path in DELIVERY_ART_INITIATIVE_REVIEW_WORKFLOW_CONTRACT_PATHS.items()
    }

    missing = [
        f"{name}={path}"
        for name, path in resolved_paths.items()
        if not path.exists()
    ]
    if missing:
        errors.append(
            "delivery-art initiative-review workflow contract missing: "
            + ", ".join(missing)
        )
        return

    platform_contract = load_json(resolved_paths["platform"])
    broker_contract = load_json(resolved_paths["broker"])
    if platform_contract != broker_contract:
        errors.append(
            "delivery-art initiative-review workflow drift: "
            f"{resolved_paths['platform']} does not match {resolved_paths['broker']}"
        )


def validate_delivery_art_operator_path_contract(
    workspace_root: Path,
    repo_root: Path,
    errors: list[str],
) -> None:
    contract_path = workspace_root / DELIVERY_ART_OPERATOR_PATH_CONTRACT_PATH
    if not contract_path.exists():
        errors.append(f"{contract_path}: missing delivery-art operator path contract")
        return

    contract = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    operator_path = contract.get("delivery_art_operator_path") or {}
    canonical_entrypoint = operator_path.get("canonical_entrypoint") or {}
    if canonical_entrypoint.get("command") != "npm run art":
        errors.append(
            f"{contract_path}: canonical entrypoint command must stay 'npm run art'"
        )

    surface_paths = [
        workspace_root / canonical_entrypoint.get("primary_operator_surface", ""),
        workspace_root / operator_path.get("supporting_platform_surfaces", {}).get(
            "workflow_health", ""
        ),
        workspace_root / operator_path.get("supporting_platform_surfaces", {}).get(
            "quality_gate", ""
        ),
        workspace_root / operator_path.get("supporting_platform_surfaces", {}).get(
            "admin_boundary", ""
        ),
        repo_root / operator_path.get("governance_surface", ""),
    ]
    for path in surface_paths:
        if not path.exists():
            errors.append(f"{path}: missing delivery-art operator-path surface")

    primary_surface_path = workspace_root / canonical_entrypoint.get(
        "primary_operator_surface", ""
    )
    if primary_surface_path.exists():
        primary_surface_text = primary_surface_path.read_text(encoding="utf-8")
        for entry in operator_path.get("canonical_read_hierarchy", []):
            cli = entry.get("cli")
            if cli and cli not in primary_surface_text:
                errors.append(
                    f"{primary_surface_path}: missing canonical ART read command {cli!r}"
                )
        for entry in operator_path.get("guided_write_intents", []):
            cli = entry.get("cli")
            if cli and cli != "local helper" and cli not in primary_surface_text:
                errors.append(
                    f"{primary_surface_path}: missing guided ART write command {cli!r}"
                )

    skill_path = repo_root / "skills-src/project-delivery-operator/SKILL.md"
    if skill_path.exists():
        skill_text = skill_path.read_text(encoding="utf-8")
        for required in (
            "npm run art -- bootstrap",
            "npm run art -- workflow-health",
            "npm run art -- initiative planning <delivery-id>",
            "npm run art -- item continuation <work-item-id>",
        ):
            if required not in skill_text:
                errors.append(f"{skill_path}: missing ART operator-path command {required!r}")
        forbidden = "default ART reads and writes to direct\n     top-level `k3s kubectl` broker calls against the active profile namespace"
        if forbidden in skill_text:
            errors.append(
                f"{skill_path}: still teaches direct kubectl broker calls as the normal ART path"
            )
    else:
        errors.append(f"{skill_path}: missing project-delivery-operator skill")


def build_generated_contracts(repo_root: Path, contracts: dict[str, object]) -> dict[str, object]:
    repos = contracts["repos"]["repos"]
    products = contracts["products"]["products"]
    components = contracts["components"]["components"]
    skills = contracts["skills"]["skills"]

    dependency_edges: list[dict[str, str]] = []
    for repo_name, payload in repos.items():
        for target in payload["allowed_authoritative_refs"]:
            dependency_edges.append(
                {"from": repo_name, "to": target, "type": "authoritative-reference"}
            )
    for product_name, payload in products.items():
        dependency_edges.append(
            {"from": product_name, "to": payload["platform_owner"], "type": "authoritative-reference"}
        )
        dependency_edges.append(
            {"from": product_name, "to": payload["security_owner"], "type": "security-reference"}
        )
        dependency_edges.append(
            {"from": product_name, "to": payload["runtime_owner"], "type": "runtime-input"}
        )
        for repo_name in payload["source_owners"]:
            dependency_edges.append(
                {"from": product_name, "to": repo_name, "type": "authoritative-reference"}
            )

    stale_rules: list[dict[str, object]] = []
    for entry in contracts["vocabulary"]["retired_terms"]:
        stale_rules.append(
            {
                "id": entry["id"],
                "pattern": entry["pattern"],
                "repo_names": entry["repo_names"],
                "exclude_paths": entry.get("exclude_paths", []),
                "targets": ["*.md"],
            }
        )
    for repo_name, rule in contracts["repo_rules"].items():
        for target_name, patterns in rule["forbidden_patterns"].items():
            if patterns:
                stale_rules.append(
                    {
                        "id": f"{repo_name}-{target_name}-forbidden",
                        "pattern": "|".join(patterns),
                        "repo_names": [repo_name],
                        "exclude_paths": [],
                        "targets": [f"{target_name.upper()}.md" if target_name == "agents" else "README.md"],
                    }
                )

    return {
        "system_map": {
            "schema_version": contracts["version"]["schema_version"],
            "repos": repos,
            "retired_repos": contracts["repos"].get("retired_repos", {}),
            "products": products,
            "components": components,
            "skills": skills,
        },
        "resolved_owner_map": {
            "repos": repos,
            "products": products,
            "components": components,
            "skills": skills,
        },
        "resolved_dependency_graph": {
            "dependency_types": contracts["dependency_types"]["dependency_types"],
            "edges": dependency_edges,
        },
        "stale_content_rules": stale_rules,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate cross-repo truth against workspace contracts.")
    parser.add_argument(
        "--workspace-root",
        default=Path(__file__).resolve().parents[2],
        type=Path,
        help="workspace root containing the active repos",
    )
    parser.add_argument(
        "--write-generated",
        action="store_true",
        help="write generated contract artifacts under generated/",
    )
    parser.add_argument(
        "--check-generated",
        action="store_true",
        help="fail if generated artifacts do not match the current contracts",
    )
    args = parser.parse_args()

    workspace_root = args.workspace_root.resolve()
    repo_root = Path(__file__).resolve().parents[1]
    contracts = load_contracts(repo_root)
    active_repos = active_repo_names(contracts)
    errors: list[str] = []

    for repo_name in active_repos:
        repo_root_path = workspace_root / repo_name
        if not repo_root_path.exists():
            errors.append(f"missing active repo for cross-repo truth check: {repo_root_path}")
            continue

        readme_path = repo_root_path / "README.md"
        agents_path = repo_root_path / "AGENTS.md"
        if not readme_path.exists() or not agents_path.exists():
            errors.append(f"{repo_root_path}: missing README.md or AGENTS.md")
            continue

        readme_text = readme_path.read_text()
        agents_text = agents_path.read_text()
        combined = readme_text + "\n" + agents_text
        rule = contracts["repo_rules"][repo_name]

        for ref in rule["required_repo_refs"]:
            if ref not in combined:
                errors.append(f"{repo_root_path}: missing required authoritative repo reference {ref!r} in README.md or AGENTS.md")

        for pattern in rule["required_patterns"]["readme"]:
            if not re.search(pattern, readme_text, re.MULTILINE):
                errors.append(f"{readme_path}: missing required ownership pattern {pattern!r}")
        for pattern in rule["required_patterns"]["agents"]:
            if not re.search(pattern, agents_text, re.MULTILINE):
                errors.append(f"{agents_path}: missing required routing pattern {pattern!r}")
        for pattern in rule["forbidden_patterns"]["readme"]:
            if pattern and re.search(pattern, readme_text, re.MULTILINE):
                errors.append(f"{readme_path}: found forbidden ownership pattern {pattern!r}")
        for pattern in rule["forbidden_patterns"]["agents"]:
            if pattern and re.search(pattern, agents_text, re.MULTILINE):
                errors.append(f"{agents_path}: found forbidden routing pattern {pattern!r}")

    validate_workspace_root_repo_coverage(repo_root / "workspace-root", active_repos, errors)
    validate_security_architecture_component_coverage(workspace_root, contracts, errors)
    validate_delivery_art_planning_workflow_contract(workspace_root, errors)
    validate_delivery_art_initiative_review_workflow_contract(workspace_root, errors)
    validate_delivery_art_operator_path_contract(workspace_root, repo_root, errors)

    for product_name in contracts["products"]["products"]:
        product_readme = workspace_root / "platform-engineering" / "products" / product_name / "README.md"
        if not product_readme.exists():
            errors.append(f"platform-engineering product missing README for declared product {product_name}: {product_readme}")

    for component_name, payload in contracts["components"]["components"].items():
        interface_contract = payload.get("interface_contract")
        if not interface_contract:
            continue
        contract_path = workspace_root / payload["owner_repo"] / interface_contract["path"]
        if not contract_path.exists():
            errors.append(
                f"contracts/components.yaml: {component_name} interface contract path is missing in owner repo {payload['owner_repo']}: {contract_path}"
            )

    for skill_name, payload in contracts["skills"]["skills"].items():
        skill_path = workspace_root / payload["owner_repo"] / payload["source_path"]
        if not skill_path.exists():
            errors.append(
                f"contracts/skills.yaml: {skill_name} source path is missing in owner repo {payload['owner_repo']}: {skill_path}"
            )
            continue
        if not (skill_path / "SKILL.md").exists():
            errors.append(f"{skill_path}: missing SKILL.md for registered skill {skill_name}")

    compiled = build_generated_contracts(repo_root, contracts)
    paths = generated_paths(repo_root)

    if args.write_generated:
        dump_yaml(paths["system_map"], compiled["system_map"])
        dump_json(paths["resolved_owner_map"], compiled["resolved_owner_map"])
        dump_json(paths["resolved_dependency_graph"], compiled["resolved_dependency_graph"])
        dump_json(paths["stale_content_rules"], compiled["stale_content_rules"])

    if args.check_generated:
        if not paths["system_map"].exists():
            errors.append(f"{paths['system_map']}: missing generated system map")
        elif yaml.safe_load(paths["system_map"].read_text()) != compiled["system_map"]:
            errors.append(f"{paths['system_map']}: generated system map is stale")
        if not paths["resolved_owner_map"].exists():
            errors.append(f"{paths['resolved_owner_map']}: missing generated owner map")
        elif load_json(paths["resolved_owner_map"]) != compiled["resolved_owner_map"]:
            errors.append(f"{paths['resolved_owner_map']}: generated owner map is stale")
        if not paths["resolved_dependency_graph"].exists():
            errors.append(f"{paths['resolved_dependency_graph']}: missing generated dependency graph")
        elif load_json(paths["resolved_dependency_graph"]) != compiled["resolved_dependency_graph"]:
            errors.append(f"{paths['resolved_dependency_graph']}: generated dependency graph is stale")
        if not paths["stale_content_rules"].exists():
            errors.append(f"{paths['stale_content_rules']}: missing generated stale-content rules")
        elif load_json(paths["stale_content_rules"]) != compiled["stale_content_rules"]:
            errors.append(f"{paths['stale_content_rules']}: generated stale-content rules are stale")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print(
        "cross-repo truth valid: "
        f"repos={len(active_repos)} "
        f"products={len(contracts['products']['products'])} "
        f"components={len(contracts['components']['components'])} "
        f"skills={len(contracts['skills']['skills'])}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
