#!/usr/bin/env python3
import argparse
import re
import subprocess
from pathlib import Path


REQUIRED_FILES = (
    "README.md",
    "AGENTS.md",
    ".gitignore",
    ".github/CODEOWNERS",
    ".github/workflows/validate.yaml",
    "scripts/README.md",
    "scripts/audit_workspace_layout.py",
    "scripts/sync_workspace_root.py",
    "scripts/validate_repo_structure.py",
    "workspace-root/README.md",
    "workspace-root/AGENTS.md",
)


WORKSPACE_ROOT_MARKDOWN_FILES = (
    "workspace-root/README.md",
    "workspace-root/AGENTS.md",
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

    canonical_note = "Canonical source:"
    for rel_path in ("workspace-root/README.md", "workspace-root/AGENTS.md"):
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
        if origin != expected_origin:
            errors.append(f"expected origin {expected_origin!r}, got {origin!r}")

    if errors:
        raise SystemExit("\n".join(errors))

    print("workspace-governance structure valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
