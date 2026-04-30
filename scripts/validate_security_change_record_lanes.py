#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path
import sys

from contracts_lib import active_repo_names, load_contracts


CHANGE_RECORD_REQUIRED_HEADINGS = {
    "## Summary",
    "## Classification",
    "## Ownership",
    "## Root Cause",
    "## Source Changes",
    "## Artifact And Deployment Evidence",
    "## Live Verification",
    "## Follow-Up",
}


def build_reference_tokens(rel_path: str) -> set[str]:
    return {
        rel_path,
        f"./{rel_path}",
    }


def run(cmd: list[str], *, cwd: Path) -> str:
    result = subprocess.run(
        cmd,
        cwd=str(cwd),
        check=True,
        text=True,
        capture_output=True,
    )
    return result.stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate repo-level security change-record lanes declared in workspace contracts."
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

    for repo_name in active_repo_names(contracts):
        rule = contracts["repo_rules"].get(repo_name) or {}
        requirements = rule.get("security_change_record_requirements")
        if not requirements:
            continue
        repos_checked += 1
        repo_root = workspace_root / repo_name
        readme_path = repo_root / "README.md"
        agents_path = repo_root / "AGENTS.md"
        readme_text = readme_path.read_text() if readme_path.exists() else ""
        agents_text = agents_path.read_text() if agents_path.exists() else ""
        doc_text = {"readme": readme_text, "agents": agents_text}

        for key in (
            "change_record_readme_path",
            "policy_path",
            "validator_script_path",
            "workflow_path",
            "pr_template_path",
        ):
            rel_path = requirements[key]
            absolute_path = repo_root / rel_path
            if not absolute_path.exists():
                errors.append(
                    f"contracts/repo-rules/{repo_name}.yaml: {key} references missing path {repo_name}/{rel_path}"
                )

        template_path = repo_root / Path(requirements["change_record_readme_path"]).parent / "TEMPLATE.md"
        if not template_path.exists():
            errors.append(
                f"contracts/repo-rules/{repo_name}.yaml: change-record lane missing template {template_path.relative_to(workspace_root)}"
            )
        else:
            template_text = template_path.read_text(encoding="utf-8")
            missing_template_headings = sorted(
                heading
                for heading in CHANGE_RECORD_REQUIRED_HEADINGS
                if heading not in template_text
            )
            if missing_template_headings:
                errors.append(
                    f"{template_path}: missing change-record template headings: {', '.join(missing_template_headings)}"
                )

        tokens = build_reference_tokens(requirements["change_record_readme_path"])
        for doc_key in requirements["required_in_docs"]:
            if any(token in doc_text[doc_key] for token in tokens):
                continue
            target_path = readme_path if doc_key == "readme" else agents_path
            errors.append(
                f"{target_path}: missing change-record lane reference for {requirements['change_record_readme_path']}"
            )

        validator_path = repo_root / requirements["validator_script_path"]
        if validator_path.exists():
            try:
                output = run(
                    [
                        "python3",
                        str(validator_path),
                        "--repo-root",
                        str(repo_root),
                        "--against-ref",
                        "origin/main",
                    ],
                    cwd=repo_root,
                )
            except subprocess.CalledProcessError as exc:
                errors.append(exc.stdout.strip() or exc.stderr.strip() or str(exc))
            else:
                print(f"[{repo_name}] {output}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print(f"security change-record lanes valid: repos_checked={repos_checked}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
