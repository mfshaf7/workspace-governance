#!/usr/bin/env python3
import argparse
import re
import subprocess
from pathlib import Path


REQUIRED_FILES = (
    "README.md",
    "AGENTS.md",
    ".gitignore",
    "requirements.txt",
    ".github/CODEOWNERS",
    ".github/pull_request_template.md",
    ".github/workflows/validate.yaml",
    "docs/codex-github-review-and-automation.md",
    "contracts/README.md",
    "contracts/version.yaml",
    "contracts/repos.yaml",
    "contracts/products.yaml",
    "contracts/components.yaml",
    "contracts/intake-policy.yaml",
    "contracts/intake-register.yaml",
    "contracts/developer-integration-policy.yaml",
    "contracts/developer-integration-profiles.yaml",
    "contracts/delegation-policy.yaml",
    "contracts/task-types.yaml",
    "contracts/lifecycle.yaml",
    "contracts/dependency-types.yaml",
    "contracts/change-classes.yaml",
    "contracts/failure-taxonomy.yaml",
    "contracts/improvement-triggers.yaml",
    "contracts/evidence-obligations.yaml",
    "contracts/review-obligations.yaml",
    "contracts/vocabulary.yaml",
    "contracts/exceptions.yaml",
    "contracts/validation-matrix.yaml",
    "contracts/skills.yaml",
    "contracts/schemas/version.schema.json",
    "contracts/schemas/repos.schema.json",
    "contracts/schemas/products.schema.json",
    "contracts/schemas/components.schema.json",
    "contracts/schemas/intake-policy.schema.json",
    "contracts/schemas/intake-register.schema.json",
    "contracts/schemas/developer-integration-policy.schema.json",
    "contracts/schemas/developer-integration-profiles.schema.json",
    "contracts/schemas/delegation-policy.schema.json",
    "contracts/schemas/delegation-journal-record.schema.json",
    "contracts/schemas/failure-taxonomy.schema.json",
    "contracts/schemas/improvement-triggers.schema.json",
    "contracts/schemas/improvement-candidate-record.schema.json",
    "contracts/schemas/after-action-record.schema.json",
    "contracts/schemas/repo-rules.schema.json",
    "contracts/schemas/skills.schema.json",
    "generated/README.md",
    "docs/delegated-execution.md",
    "reviews/README.md",
    "reviews/delegation-journal/README.md",
    "reviews/delegation-journal/TEMPLATE.yaml",
    "reviews/improvement-candidates/README.md",
    "reviews/improvement-candidates/TEMPLATE.yaml",
    "reviews/after-action/README.md",
    "reviews/after-action/TEMPLATE.yaml",
    "skills-src/README.md",
    "templates/README.md",
    "templates/intake/README.md",
    "templates/dev-integration-profile/README.md",
    "templates/dev-integration-request/README.md",
    "templates/delegation-packet/README.md",
    "templates/delegation-packet/TEMPLATE.yaml",
    "templates/improvement-candidate/README.md",
    "templates/skill/README.md",
    "templates/after-action/README.md",
    "scripts/README.md",
    "scripts/audit_branch_lifecycle.py",
    "scripts/audit_workspace_layout.py",
    "scripts/audit_stale_content.py",
    "scripts/contracts_lib.py",
    "scripts/check_remote_alignment.py",
    "scripts/install_skills.py",
    "scripts/scaffold_intake.py",
    "scripts/validate_delegation_journal.py",
    "scripts/record_after_action.py",
    "scripts/record_improvement_candidate.py",
    "scripts/validate_codex_review_controls.py",
    "scripts/validate_intake.py",
    "scripts/validate_developer_integration.py",
    "scripts/validate_improvement_candidates.py",
    "scripts/validate_structured_record.py",
    "scripts/audit_improvement_signals.py",
    "scripts/validate_learning_closure.py",
    "scripts/validate_component_contracts.py",
    "scripts/validate_security_bindings.py",
    "scripts/validate_review_coverage.py",
    "scripts/validate_security_evidence.py",
    "scripts/validate_security_change_record_lanes.py",
    "scripts/workspace_control_plane_summary.py",
    "scripts/sync_workspace_root.py",
    "scripts/validate_contracts.py",
    "scripts/validate_cross_repo_truth.py",
    "scripts/validate_repo_structure.py",
    "workspace-root/ARCHITECTURE.md",
    "workspace-root/README.md",
    "workspace-root/AGENTS.md",
)


WORKSPACE_ROOT_MARKDOWN_FILES = (
    "workspace-root/ARCHITECTURE.md",
    "workspace-root/README.md",
    "workspace-root/AGENTS.md",
)


REQUIRED_DIRECTORIES = (
    "contracts/repo-rules",
    "contracts/schemas",
    "templates/intake",
    "templates/dev-integration-profile",
    "templates/dev-integration-request",
    "templates/delegation-packet",
    "templates/improvement-candidate",
    "templates/repo-rule",
    "templates/product",
    "templates/component",
    "templates/exception",
    "templates/skill",
    "templates/after-action",
    "generated",
    "reviews/after-action",
    "reviews/delegation-journal",
    "reviews/improvement-candidates",
    "skills-src/workspace-change-router",
    "skills-src/architecture-discussion-gate",
    "skills-src/contract-drift-check",
    "skills-src/done-criteria-enforcer",
    "skills-src/self-improvement-review",
)


GITHUB_REPO_RE = re.compile(
    r"(?:git@|https://|ssh://git@)?github\.com[:/](?P<owner>[^/]+)/(?P<repo>[^/.]+?)(?:\.git)?$"
)


def run(cmd: list[str], *, cwd: Path | None = None) -> str:
    result = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        check=True,
        text=True,
        capture_output=True,
    )
    return result.stdout.strip()


def normalize_repository_url(value: str | None) -> str | None:
    if not value:
        return None
    match = GITHUB_REPO_RE.search(value.strip())
    if match:
        return f"github.com/{match.group('owner')}/{match.group('repo')}"
    return value.strip().removesuffix(".git")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate the workspace-governance repository structure."
    )
    parser.add_argument(
        "--repo-root",
        default=Path(__file__).resolve().parents[1],
        type=Path,
        help="workspace-governance repository root",
    )
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    errors: list[str] = []

    for rel_path in REQUIRED_FILES:
        target = repo_root / rel_path
        if not target.exists():
            errors.append(f"missing required file: {target}")

    for rel_path in REQUIRED_DIRECTORIES:
        target = repo_root / rel_path
        if not target.exists():
            errors.append(f"missing required directory: {target}")

    canonical_note = "Canonical source:"
    for rel_path in ("workspace-root/ARCHITECTURE.md", "workspace-root/README.md", "workspace-root/AGENTS.md"):
        target = repo_root / rel_path
        if target.exists() and canonical_note not in target.read_text():
            errors.append(f"{target}: missing canonical source note")

    link_pattern = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
    for rel_path in WORKSPACE_ROOT_MARKDOWN_FILES:
        target = repo_root / rel_path
        if not target.exists():
            continue
        for match in link_pattern.finditer(target.read_text()):
            link_target = match.group(1)
            if link_target.startswith("#") or "://" in link_target:
                continue
            if not link_target.startswith("/home/mfshaf7/projects/"):
                errors.append(
                    f"{target}: workspace-root links must use absolute /home/mfshaf7/projects paths, got {link_target!r}"
                )

    try:
        origin = run(["git", "-C", str(repo_root), "remote", "get-url", "origin"])
    except subprocess.CalledProcessError as exc:
        errors.append(exc.stdout.strip() or exc.stderr.strip() or str(exc))
    else:
        expected_origin = "git@github.com:mfshaf7/workspace-governance.git"
        if normalize_repository_url(origin) != normalize_repository_url(expected_origin):
            errors.append(f"expected origin {expected_origin!r}, got {origin!r}")

    if errors:
        raise SystemExit("\n".join(errors))

    print("workspace-governance structure valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
