#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from jsonschema import Draft202012Validator

from contracts_lib import load_json
from validate_contracts import (
    CONTRACT_FORMAT_CHECKER,
    DELIVERY_ART_ARTIFACT_CASES,
    delivery_art_artifact_integrity_errors,
    delivery_art_artifact_semantic_errors,
)


ARTIFACT_CASE_BY_TYPE = {
    "delivery_art_architecture_packet": "architecture_packet",
    "delivery_art_work_start_record": "work_start_record",
    "art_review_packet": "review_packet",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate one operator-supplied Delivery ART artifact."
    )
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    artifact_path = args.artifact.resolve()
    try:
        payload = json.loads(artifact_path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        print(f"delivery ART artifact invalid: {exc}", file=sys.stderr)
        return 1

    artifact_type = payload.get("artifact_type") if isinstance(payload, dict) else None
    case_name = ARTIFACT_CASE_BY_TYPE.get(artifact_type)
    if case_name is None:
        print(
            f"delivery ART artifact invalid: unsupported artifact_type {artifact_type!r}",
            file=sys.stderr,
        )
        return 1

    schema_ref = DELIVERY_ART_ARTIFACT_CASES[case_name][0]
    schema = load_json(repo_root / schema_ref)
    validator = Draft202012Validator(
        schema,
        format_checker=CONTRACT_FORMAT_CHECKER,
    )
    errors = [
        f"{'.'.join(str(part) for part in error.absolute_path) or '<root>'}: {error.message}"
        for error in sorted(
            validator.iter_errors(payload),
            key=lambda error: list(error.absolute_path),
        )
    ]
    errors.extend(
        f"semantic invariant: {error}"
        for error in delivery_art_artifact_semantic_errors(payload)
    )
    errors.extend(
        f"integrity invariant: {error}"
        for error in delivery_art_artifact_integrity_errors(payload)
    )
    if errors:
        for error in errors:
            print(f"delivery ART artifact invalid: {error}", file=sys.stderr)
        return 1

    print(
        f"delivery ART artifact valid: type={artifact_type} path={artifact_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
