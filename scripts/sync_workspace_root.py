#!/usr/bin/env python3
import argparse
import shutil
from pathlib import Path


SYNC_MAP = (
    ("workspace-root/README.md", "README.md"),
    ("workspace-root/AGENTS.md", "AGENTS.md"),
    ("scripts/audit_workspace_layout.py", "_workspace_tools/audit_workspace_layout.py"),
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sync canonical workspace-governance files into the live workspace root."
    )
    parser.add_argument(
        "--repo-root",
        default=Path(__file__).resolve().parents[1],
        type=Path,
        help="workspace-governance repository root",
    )
    parser.add_argument(
        "--workspace-root",
        default=Path(__file__).resolve().parents[2],
        type=Path,
        help="workspace root that receives the synced files",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail if the live workspace files differ from the canonical copies",
    )
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    workspace_root = args.workspace_root.resolve()
    mismatches: list[str] = []

    for src_rel, dest_rel in SYNC_MAP:
        src = repo_root / src_rel
        dest = workspace_root / dest_rel
        if args.check:
            if not dest.exists():
                mismatches.append(f"missing synced file: {dest}")
                continue
            if src.read_text() != dest.read_text():
                mismatches.append(f"out of sync: {dest} != {src}")
            continue

        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        print(f"synced {src} -> {dest}")

    if mismatches:
        raise SystemExit("\n".join(mismatches))

    if args.check:
        print("workspace root sync valid")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
