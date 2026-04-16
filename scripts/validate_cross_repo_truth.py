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


def gather_active_docs(repo_root: Path) -> list[Path]:
    files: list[Path] = []
    for path in repo_root.rglob("*.md"):
        path_str = str(path)
        if any(marker in path_str for marker in DOC_EXCLUDES):
            continue
        files.append(path)
    return sorted(files)


def build_generated_contracts(repo_root: Path, contracts: dict[str, object]) -> dict[str, object]:
    repos = contracts["repos"]["repos"]
    products = contracts["products"]["products"]
    components = contracts["components"]["components"]

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
        },
        "resolved_owner_map": {
            "repos": repos,
            "products": products,
            "components": components,
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
    errors: list[str] = []

    for repo_name in active_repo_names(contracts):
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
        f"repos={len(active_repo_names(contracts))} "
        f"products={len(contracts['products']['products'])} "
        f"components={len(contracts['components']['components'])}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
