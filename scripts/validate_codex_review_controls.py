#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

from contracts_lib import active_repo_names, load_contracts


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


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


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate repo-owned Codex review guidance and required GitHub control surfaces."
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

    errors: list[str] = []
    repos_checked = 0
    guidance_files_checked = 0

    for repo_name in active_repo_names(contracts):
        repo_root = workspace_root / repo_name
        if not repo_root.exists():
            errors.append(f"{repo_name}: active repo path missing at {repo_root}")
            continue

        rule = contracts["repo_rules"].get(repo_name) or {}
        requirements = rule.get("review_control_requirements")
        if not requirements:
            errors.append(f"contracts/repo-rules/{repo_name}.yaml: missing review_control_requirements")
            continue

        repos_checked += 1

        for rel_path in requirements["required_github_paths"]:
            target = repo_root / rel_path
            if not target.exists():
                errors.append(f"{repo_name}: missing required GitHub control path {rel_path}")
                continue
            if rel_path.endswith("CODEOWNERS") and "@" not in read_text(target):
                errors.append(f"{repo_name}: CODEOWNERS must declare at least one owner handle")

        for rel_path in requirements["required_validation_paths"]:
            target = repo_root / rel_path
            if not target.exists():
                errors.append(f"{repo_name}: missing required validation path {rel_path}")
                continue
            if rel_path.startswith(".github/workflows/") and "pull_request" not in read_text(target):
                errors.append(f"{repo_name}: validation workflow {rel_path} must run on pull_request")

        pr_template_path = repo_root / requirements["pr_template_path"]
        if not pr_template_path.exists():
            errors.append(f"{repo_name}: missing PR template at {requirements['pr_template_path']}")
        else:
            pr_template_text = read_text(pr_template_path)
            for section in requirements["required_pr_template_sections"]:
                if section not in pr_template_text:
                    errors.append(
                        f"{repo_name}: PR template {requirements['pr_template_path']} missing section {section!r}"
                    )

        for guidance in requirements["guidance_files"]:
            guidance_files_checked += 1
            rel_path = guidance["path"]
            target = repo_root / rel_path
            if not target.exists():
                errors.append(f"{repo_name}: missing review guidance file {rel_path}")
                continue
            section = extract_section(read_text(target), guidance["heading"])
            if section is None:
                errors.append(f"{repo_name}: {rel_path} missing section {guidance['heading']!r}")
                continue
            lowered = section.lower()
            for term in guidance["required_terms"]:
                if term.lower() not in lowered:
                    errors.append(
                        f"{repo_name}: {rel_path} review guidance missing required term {term!r}"
                    )

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print(
        "codex review controls valid:"
        f" repos_checked={repos_checked}"
        f" guidance_files_checked={guidance_files_checked}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
