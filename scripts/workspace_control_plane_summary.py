#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path
import sys


def run_check(cmd: list[str], *, cwd: Path) -> tuple[bool, str]:
    result = subprocess.run(
        cmd,
        cwd=str(cwd),
        check=False,
        text=True,
        capture_output=True,
    )
    output = (result.stdout or "").strip()
    stderr = (result.stderr or "").strip()
    combined = "\n".join(part for part in (output, stderr) if part).strip()
    return result.returncode == 0, combined


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run a read-only workspace control-plane summary."
    )
    parser.add_argument(
        "--workspace-root",
        default=Path(__file__).resolve().parents[2],
        type=Path,
        help="workspace root containing the active repos",
    )
    parser.add_argument(
        "--refresh-remote",
        action="store_true",
        help="refresh origin/main before running the remote-freshness preflight",
    )
    args = parser.parse_args()

    workspace_root = args.workspace_root.resolve()
    repo_root = Path(__file__).resolve().parents[1]

    remote_cmd = [
        "python3",
        "scripts/check_remote_alignment.py",
        "--workspace-root",
        str(workspace_root),
        "--repo-name",
        "workspace-governance",
    ]
    if args.refresh_remote:
        remote_cmd.append("--refresh-remote")

    checks = [
        ("remote freshness", remote_cmd),
        (
            "workspace-root sync check",
            [
                "python3",
                "scripts/sync_workspace_root.py",
                "--workspace-root",
                str(workspace_root),
                "--check",
            ],
        ),
        (
            "live skill install check",
            [
                "python3",
                "scripts/install_skills.py",
                "--workspace-root",
                str(workspace_root),
                "--check",
            ],
        ),
        (
            "Codex review-control compliance",
            [
                "python3",
                "scripts/validate_codex_review_controls.py",
                "--workspace-root",
                str(workspace_root),
            ],
        ),
        (
            "stale-content audit",
            [
                "python3",
                "scripts/audit_stale_content.py",
                "--workspace-root",
                str(workspace_root),
            ],
        ),
        (
            "workspace audit",
            [
                "python3",
                "scripts/audit_workspace_layout.py",
                "--workspace-root",
                str(workspace_root),
            ],
        ),
        (
            "deterministic improvement-signal audit",
            [
                "python3",
                "scripts/audit_improvement_signals.py",
                "--workspace-root",
                str(workspace_root),
            ],
        ),
        (
            "improvement-candidate validation",
            [
                "python3",
                "scripts/validate_improvement_candidates.py",
                "--workspace-root",
                str(workspace_root),
            ],
        ),
        (
            "learning-closure validation",
            [
                "python3",
                "scripts/validate_learning_closure.py",
                "--workspace-root",
                str(workspace_root),
            ],
        ),
    ]

    failures = 0
    for label, cmd in checks:
        ok, output = run_check(cmd, cwd=repo_root)
        prefix = "OK" if ok else "ERROR"
        print(f"[{prefix}] {label}")
        if output:
            for line in output.splitlines():
                print(f"  {line}")
        if not ok:
            failures += 1

    print(f"workspace control-plane summary: checks={len(checks)} failures={failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
