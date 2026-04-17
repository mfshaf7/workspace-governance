#!/usr/bin/env python3
import argparse
import subprocess
from pathlib import Path

from contracts_lib import active_repo_names, load_contracts


def run(cmd: list[str], *, cwd: Path | None = None) -> str:
    result = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        check=True,
        text=True,
        capture_output=True,
    )
    return result.stdout.strip()


def compare_files(expected: Path, actual: Path, errors: list[str]) -> None:
    if not actual.exists():
        errors.append(f"missing synced workspace file: {actual}")
        return
    if expected.read_text() != actual.read_text():
        errors.append(f"workspace file out of sync: {actual} != {expected}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit the local multi-repo workspace layout and workspace-root guidance coverage."
    )
    parser.add_argument(
        "--workspace-root",
        default=Path(__file__).resolve().parents[1],
        type=Path,
        help="workspace root containing the active repos",
    )
    parser.add_argument(
        "--check-clean",
        action="store_true",
        help="also fail if a required repo has a dirty git worktree",
    )
    args = parser.parse_args()

    workspace_root = args.workspace_root.resolve()
    workspace_governance_root = workspace_root / "workspace-governance"
    contracts = load_contracts(workspace_governance_root)
    required_repos = tuple(active_repo_names(contracts))
    errors: list[str] = []
    dirty_repos: list[str] = []

    for repo_name in required_repos:
        repo_root = workspace_root / repo_name
        if not repo_root.exists():
            errors.append(f"missing repo: {repo_root}")
            continue

        for required_file in ("README.md", "AGENTS.md"):
            if not (repo_root / required_file).exists():
                errors.append(f"{repo_root}: missing {required_file}")

        expected_origin = f"git@github.com:mfshaf7/{repo_name}.git"
        origin = run(["git", "-C", str(repo_root), "remote", "get-url", "origin"])
        if origin != expected_origin:
            errors.append(f"{repo_root}: expected origin {expected_origin!r}, got {origin!r}")

        status = run(["git", "-C", str(repo_root), "status", "--short"])
        if status:
            dirty_repos.append(repo_name)

    if workspace_governance_root.exists():
        compare_files(
            workspace_governance_root / "workspace-root" / "README.md",
            workspace_root / "README.md",
            errors,
        )
        compare_files(
            workspace_governance_root / "workspace-root" / "AGENTS.md",
            workspace_root / "AGENTS.md",
            errors,
        )
        compare_files(
            workspace_governance_root / "scripts" / "audit_workspace_layout.py",
            workspace_root / "_workspace_tools" / "audit_workspace_layout.py",
            errors,
        )
    else:
        errors.append(f"missing workspace governance repo: {workspace_governance_root}")

    contract_validator = workspace_governance_root / "scripts" / "validate_contracts.py"
    cross_repo_validator = workspace_governance_root / "scripts" / "validate_cross_repo_truth.py"
    security_binding_validator = (
        workspace_governance_root / "scripts" / "validate_security_bindings.py"
    )
    review_coverage_validator = (
        workspace_governance_root / "scripts" / "validate_review_coverage.py"
    )
    security_evidence_validator = (
        workspace_governance_root / "scripts" / "validate_security_evidence.py"
    )
    component_contract_validator = (
        workspace_governance_root / "scripts" / "validate_component_contracts.py"
    )
    learning_closure_validator = (
        workspace_governance_root / "scripts" / "validate_learning_closure.py"
    )
    try:
        output = run(["python3", str(contract_validator), "--repo-root", str(workspace_governance_root)])
    except subprocess.CalledProcessError as exc:
        errors.append(exc.stdout.strip() or exc.stderr.strip() or str(exc))
    else:
        print(output)

    try:
        output = run(
            [
                "python3",
                str(security_evidence_validator),
                "--workspace-root",
                str(workspace_root),
            ]
        )
    except subprocess.CalledProcessError as exc:
        errors.append(exc.stdout.strip() or exc.stderr.strip() or str(exc))
    else:
        print(output)

    try:
        output = run(
            [
                "python3",
                str(review_coverage_validator),
                "--workspace-root",
                str(workspace_root),
            ]
        )
    except subprocess.CalledProcessError as exc:
        errors.append(exc.stdout.strip() or exc.stderr.strip() or str(exc))
    else:
        print(output)

    try:
        output = run(
            [
                "python3",
                str(security_binding_validator),
                "--workspace-root",
                str(workspace_root),
            ]
        )
    except subprocess.CalledProcessError as exc:
        errors.append(exc.stdout.strip() or exc.stderr.strip() or str(exc))
    else:
        print(output)

    try:
        output = run(
            [
                "python3",
                str(cross_repo_validator),
                "--workspace-root",
                str(workspace_root),
                "--check-generated",
            ]
        )
    except subprocess.CalledProcessError as exc:
        errors.append(exc.stdout.strip() or exc.stderr.strip() or str(exc))
    else:
        print(output)

    try:
        output = run(
            [
                "python3",
                str(component_contract_validator),
                "--workspace-root",
                str(workspace_root),
            ]
        )
    except subprocess.CalledProcessError as exc:
        errors.append(exc.stdout.strip() or exc.stderr.strip() or str(exc))
    else:
        print(output)

    try:
        output = run(
            [
                "python3",
                str(learning_closure_validator),
                "--workspace-root",
                str(workspace_root),
            ]
        )
    except subprocess.CalledProcessError as exc:
        errors.append(exc.stdout.strip() or exc.stderr.strip() or str(exc))
    else:
        print(output)

    platform_validator = (
        workspace_root / "platform-engineering" / "scripts" / "validate_repo_structure.py"
    )
    if not platform_validator.exists():
        errors.append(f"missing platform structure validator: {platform_validator}")
    else:
        try:
            output = run(
                [
                    "python3",
                    str(platform_validator),
                    "--repo-root",
                    str(workspace_root / "platform-engineering"),
                ]
            )
        except subprocess.CalledProcessError as exc:
            errors.append(exc.stdout.strip() or exc.stderr.strip() or str(exc))
        else:
            print(output)

    if args.check_clean and dirty_repos:
        errors.append("dirty repos: " + ", ".join(sorted(dirty_repos)))
    elif dirty_repos:
        print("workspace note: dirty repos present (not failing): " + ", ".join(sorted(dirty_repos)))

    if errors:
        raise SystemExit("\n".join(errors))

    print(
        "workspace layout valid: "
        f"repos={len(required_repos)} "
        f"repo_guidance={len(required_repos)} "
        "git_auth=ssh "
        "root_sync=ok"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
