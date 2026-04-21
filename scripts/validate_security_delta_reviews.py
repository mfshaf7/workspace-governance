#!/usr/bin/env python3
from __future__ import annotations

import argparse
from fnmatch import fnmatch
from pathlib import Path
import subprocess
import sys

import yaml

from contracts_lib import load_contracts


ALLOWED_DECISIONS = {
    "approved",
    "approved-with-findings",
    "blocked",
    "accepted-risk",
}
REQUIRED_REVIEW_HEADINGS = (
    "## Summary",
    "## Scope Delta",
    "## Review Areas",
    "## Decision",
)


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text()) or {}


def run_git(repo_root: Path, args: list[str]) -> str:
    return subprocess.check_output(
        ["git", *args],
        cwd=repo_root,
        text=True,
        stderr=subprocess.STDOUT,
    )


def changed_files(repo_root: Path, against_ref: str) -> set[str]:
    files: set[str] = set()
    commands = (
        ["diff", "--name-only", "--diff-filter=ACMRDTUXB", f"{against_ref}...HEAD"],
        ["diff", "--name-only", "--diff-filter=ACMRDTUXB"],
        ["diff", "--cached", "--name-only", "--diff-filter=ACMRDTUXB"],
        ["ls-files", "--others", "--exclude-standard"],
    )
    for command in commands:
        output = run_git(repo_root, command)
        for line in output.splitlines():
            line = line.strip()
            if line:
                files.add(line)
    return files


def inventory_entry(inventory: dict, section: str, name: str) -> dict:
    return (((inventory.get("review_inventory") or {}).get(section) or {}).get(name) or {})


def review_signature(review: dict) -> tuple:
    return (
        review.get("path"),
        review.get("reviewed_on"),
        review.get("status"),
        review.get("decision"),
        tuple(sorted(review.get("review_trigger_ids") or [])),
        tuple(sorted(review.get("review_areas") or [])),
    )


def changed_review_inventory_path(security_repo_root: Path, against_ref: str) -> set[str]:
    return changed_files(security_repo_root, against_ref)


def review_has_required_headings(path: Path) -> list[str]:
    text = path.read_text()
    return [heading for heading in REQUIRED_REVIEW_HEADINGS if heading not in text]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate that security-significant repo changes are covered by fresh security delta reviews."
    )
    parser.add_argument(
        "--workspace-root",
        default=Path(__file__).resolve().parents[2],
        type=Path,
        help="workspace root containing the active repos",
    )
    parser.add_argument(
        "--against-ref",
        default="origin/main",
        help="git reference used as the baseline for changed-file detection",
    )
    args = parser.parse_args()

    workspace_root = args.workspace_root.resolve()
    governance_root = Path(__file__).resolve().parents[1]
    security_repo_root = workspace_root / "security-architecture"
    contracts = load_contracts(governance_root)
    current_inventory = load_yaml(security_repo_root / "registers" / "review-inventory.yaml")
    errors: list[str] = []
    repos_with_matched_triggers = 0
    subjects_requiring_refresh = 0

    try:
        base_inventory_text = run_git(
            security_repo_root,
            ["show", f"{args.against_ref}:registers/review-inventory.yaml"],
        )
    except subprocess.CalledProcessError as exc:
        print(exc.output.rstrip())
        print(
            f"ERROR: could not load security-architecture/registers/review-inventory.yaml from {args.against_ref!r}"
        )
        return 1
    base_inventory = yaml.safe_load(base_inventory_text) or {}

    try:
        security_changed_files = changed_review_inventory_path(security_repo_root, args.against_ref)
    except subprocess.CalledProcessError as exc:
        print(exc.output.rstrip())
        print("ERROR: could not determine changed files for security-architecture")
        return 1

    for repo_name, repo_rule in sorted(contracts["repo_rules"].items()):
        security_requirements = repo_rule.get("security_requirements")
        if not security_requirements:
            continue

        repo_root = workspace_root / repo_name
        try:
            repo_changed_files = changed_files(repo_root, args.against_ref)
        except subprocess.CalledProcessError as exc:
            print(exc.output.rstrip())
            print(f"ERROR: could not determine changed files for {repo_name}")
            return 1

        subject_requirements: dict[tuple[str, str], dict[str, set[str]]] = {}
        matched_trigger_ids: set[str] = set()
        for trigger in security_requirements.get("delta_review_triggers") or []:
            path_globs = trigger["path_globs"]
            matched_paths = sorted(
                path
                for path in repo_changed_files
                if any(fnmatch(path, pattern) for pattern in path_globs)
            )
            if not matched_paths:
                continue
            matched_trigger_ids.add(trigger["id"])
            for subject in trigger["review_subjects"]:
                key = (subject["inventory_section"], subject["name"])
                requirement = subject_requirements.setdefault(
                    key,
                    {"trigger_ids": set(), "review_areas": set(), "matched_paths": set()},
                )
                requirement["trigger_ids"].add(trigger["id"])
                requirement["review_areas"].update(trigger["review_areas"])
                requirement["matched_paths"].update(matched_paths)

        if not subject_requirements:
            continue

        repos_with_matched_triggers += 1

        for (inventory_section, subject_name), requirement in sorted(subject_requirements.items()):
            subjects_requiring_refresh += 1
            current_entry = inventory_entry(current_inventory, inventory_section, subject_name)
            base_entry = inventory_entry(base_inventory, inventory_section, subject_name)
            if not current_entry:
                errors.append(
                    f"{repo_name}: missing review-inventory subject {inventory_section}.{subject_name}"
                )
                continue
            latest_current = current_entry.get("latest_change_review") or {}
            latest_base = base_entry.get("latest_change_review") or {}
            latest_path = latest_current.get("path")
            if latest_current.get("status") != "current":
                errors.append(
                    f"{repo_name}: {inventory_section}.{subject_name} must carry latest_change_review.status='current' when security-significant paths changed"
                )
            decision = latest_current.get("decision")
            if decision not in ALLOWED_DECISIONS:
                errors.append(
                    f"{repo_name}: {inventory_section}.{subject_name} latest_change_review.decision must be one of {sorted(ALLOWED_DECISIONS)}"
                )
            review_trigger_ids = set(latest_current.get("review_trigger_ids") or [])
            missing_trigger_ids = sorted(requirement["trigger_ids"] - review_trigger_ids)
            if missing_trigger_ids:
                errors.append(
                    f"{repo_name}: {inventory_section}.{subject_name} latest_change_review missing review_trigger_ids {missing_trigger_ids}"
                )
            review_areas = set(latest_current.get("review_areas") or [])
            missing_review_areas = sorted(requirement["review_areas"] - review_areas)
            if missing_review_areas:
                errors.append(
                    f"{repo_name}: {inventory_section}.{subject_name} latest_change_review missing review_areas {missing_review_areas}"
                )
            if not latest_path:
                errors.append(
                    f"{repo_name}: {inventory_section}.{subject_name} latest_change_review.path is required"
                )
                continue
            review_path = security_repo_root / latest_path
            if not review_path.exists():
                errors.append(
                    f"{repo_name}: {inventory_section}.{subject_name} latest_change_review points to missing artifact {latest_path}"
                )
                continue
            missing_headings = review_has_required_headings(review_path)
            if missing_headings:
                errors.append(
                    f"{repo_name}: {inventory_section}.{subject_name} review artifact {latest_path} is missing required headings {missing_headings}"
                )

            review_artifact_changed = latest_path in security_changed_files
            inventory_changed = review_signature(latest_current) != review_signature(latest_base)
            if not inventory_changed and not review_artifact_changed:
                errors.append(
                    f"{repo_name}: security-significant paths {sorted(requirement['matched_paths'])} require a fresh security delta review update for {inventory_section}.{subject_name}"
                )

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print(
        "security delta reviews valid: "
        f"repos_with_matched_triggers={repos_with_matched_triggers} "
        f"subjects_requiring_refresh={subjects_requiring_refresh}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
