#!/usr/bin/env python3
"""Run the security-architecture evidence validator from workspace governance."""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--workspace-root",
        default=Path(__file__).resolve().parents[2],
        type=Path,
    )
    args = parser.parse_args()

    workspace_root = args.workspace_root.resolve()
    security_architecture_root = workspace_root / "security-architecture"
    validator = security_architecture_root / "scripts" / "validate_security_evidence.py"
    if not validator.exists():
        raise SystemExit(f"missing security evidence validator: {validator}")

    result = subprocess.run(
        [
            "python3",
            str(validator),
            "--repo-root",
            str(security_architecture_root),
            "--workspace-root",
            str(workspace_root),
        ],
        check=False,
        text=True,
        capture_output=True,
    )
    output = (result.stdout or "").strip()
    if result.returncode != 0:
        raise SystemExit(output or (result.stderr or "").strip() or f"validator failed: {validator}")
    if output:
        print(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
