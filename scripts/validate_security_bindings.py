#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
import re
import sys

from contracts_lib import active_repo_names, load_contracts


def build_reference_tokens(security_path: str) -> set[str]:
    return {
        f"security-architecture/{security_path}",
        f"../security-architecture/{security_path}",
        f"https://github.com/mfshaf7/security-architecture/blob/main/{security_path}",
    }


DATED_REVIEW_OUTPUT_PATTERN = re.compile(
    r"^docs/reviews/(platform|components|products)/\d{4}-\d{2}-\d{2}-.+\.md$"
)


def has_active_waiver(
    exceptions: list[dict[str, object]],
    *,
    repo_name: str,
    waiver_id: str,
) -> bool:
    for entry in exceptions:
        if entry["target"] != repo_name:
            continue
        if date.fromisoformat(entry["expires_on"]) < date.today():
            continue
        if waiver_id in set(entry["waives"]):
            return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate repo-level security-architecture bindings across the workspace."
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
    contracts = load_contracts(governance_root)
    security_repo_root = workspace_root / "security-architecture"
    exceptions = contracts["exceptions"]["exceptions"]
    errors: list[str] = []
    repos_checked = 0
    artifacts_checked = 0

    for repo_name in active_repo_names(contracts):
        repo_payload = contracts["repos"]["repos"][repo_name]
        if not repo_payload["requires_security_bindings"]:
            continue

        repos_checked += 1
        repo_rule = contracts["repo_rules"][repo_name]
        security_requirements = repo_rule["security_requirements"]
        review_output_path = security_requirements["review_output_path"]
        if not DATED_REVIEW_OUTPUT_PATTERN.match(review_output_path):
            errors.append(
                "contracts/repo-rules/"
                f"{repo_name}.yaml: review_output_path must point to a concrete dated review artifact, got {review_output_path!r}"
            )
        repo_root = workspace_root / repo_name
        readme_path = repo_root / "README.md"
        agents_path = repo_root / "AGENTS.md"
        readme_text = readme_path.read_text() if readme_path.exists() else ""
        agents_text = agents_path.read_text() if agents_path.exists() else ""
        doc_text = {"readme": readme_text, "agents": agents_text}

        for binding_id, security_path in (
            ("review-checklist", security_requirements["review_checklist_path"]),
            ("review-output", review_output_path),
        ):
            absolute_path = security_repo_root / security_path
            if not absolute_path.exists():
                errors.append(
                    f"contracts/repo-rules/{repo_name}.yaml: security binding {binding_id} references missing path {absolute_path}"
                )
                continue
            tokens = build_reference_tokens(security_path)
            for doc_key in ("readme", "agents"):
                if any(token in doc_text[doc_key] for token in tokens):
                    continue
                waiver_id = f"security-binding:{repo_name}:{binding_id}"
                if has_active_waiver(exceptions, repo_name=repo_name, waiver_id=waiver_id):
                    continue
                target_path = readme_path if doc_key == "readme" else agents_path
                errors.append(
                    f"{target_path}: missing security binding reference for {security_path}"
                )

        for artifact in security_requirements["required_artifacts"]:
            security_path = artifact["path"]
            absolute_path = security_repo_root / security_path
            if not absolute_path.exists():
                errors.append(
                    f"contracts/repo-rules/{repo_name}.yaml: security artifact {artifact['id']} references missing path {absolute_path}"
                )
                continue
            tokens = build_reference_tokens(security_path)
            for doc_key in artifact["required_in_docs"]:
                if any(token in doc_text[doc_key] for token in tokens):
                    continue
                waiver_id = f"security-binding:{repo_name}:artifact:{artifact['id']}"
                if has_active_waiver(exceptions, repo_name=repo_name, waiver_id=waiver_id):
                    continue
                target_path = readme_path if doc_key == "readme" else agents_path
                errors.append(
                    f"{target_path}: missing security artifact reference for {security_path}"
                )
            artifacts_checked += 1

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print(
        "security bindings valid: "
        f"repos_checked={repos_checked} "
        f"artifacts_checked={artifacts_checked}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
