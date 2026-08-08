#!/usr/bin/env python3
import argparse
import fnmatch
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


def audit_session_handoff_lifecycle(repo_root: Path, errors: list[str]) -> None:
    archive_dir = repo_root / "docs" / "archive"
    if not archive_dir.exists():
        return

    handoffs = sorted(archive_dir.glob("session-handoff-*.md"))
    tracked_files = run(["git", "-C", str(repo_root), "ls-files"]).splitlines()
    tracked_handoffs = sorted(
        path
        for path in tracked_files
        if fnmatch.fnmatch(path, "docs/archive/session-handoff-*.md")
        and (repo_root / path).exists()
    )

    if tracked_handoffs:
        errors.append(
            "session handoffs must be ignored local continuity state, not tracked Git files: "
            + ", ".join(tracked_handoffs)
        )

    if len(handoffs) > 1:
        errors.append(
            "stale session handoffs present; keep zero or one "
            "docs/archive/session-handoff-current.md and remove stale files: "
            + ", ".join(str(path.relative_to(repo_root)) for path in handoffs)
        )

    if handoffs and handoffs[0].name != "session-handoff-current.md":
        errors.append(
            "session handoff must use docs/archive/session-handoff-current.md, got "
            f"{handoffs[0].relative_to(repo_root)}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit workspace repository layout and materialized workspace-root guidance."
    )
    parser.add_argument(
        "--workspace-root",
        default=Path(__file__).resolve().parents[1],
        type=Path,
        help="workspace root containing the active repos",
    )
    args = parser.parse_args()

    workspace_root = args.workspace_root.resolve()
    workspace_governance_root = workspace_root / "workspace-governance"
    contracts = load_contracts(workspace_governance_root)
    required_repos = tuple(active_repo_names(contracts))
    errors: list[str] = []

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

    if workspace_governance_root.exists():
        audit_session_handoff_lifecycle(workspace_governance_root, errors)
        compare_files(
            workspace_governance_root / "workspace-root" / "ARCHITECTURE.md",
            workspace_root / "ARCHITECTURE.md",
            errors,
        )
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
