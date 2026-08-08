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
    delivery_art_artifact_reference_errors,
    delivery_art_artifact_semantic_errors,
    strict_delivery_art_object,
)


ARTIFACT_CASE_BY_TYPE = {
    "delivery_art_architecture_packet": "architecture_packet",
    "delivery_art_work_start_record": "work_start_record",
    "art_review_packet": "review_packet",
    "delivery_art_readiness_receipt": "readiness_receipt",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate one operator-supplied Delivery ART artifact."
    )
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--dependency-artifact",
        action="append",
        default=[],
        type=Path,
        help="Artifact required to resolve architecture, work-start, receipt-subject, predecessor, or readiness-receipt references; repeat until the dependency closure is complete.",
    )
    return parser.parse_args()


def _artifact_errors(payload: object, repo_root: Path) -> list[str]:
    artifact_type = payload.get("artifact_type") if isinstance(payload, dict) else None
    case_name = ARTIFACT_CASE_BY_TYPE.get(artifact_type)
    if case_name is None:
        return [f"unsupported artifact_type {artifact_type!r}"]
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
    return errors


def _load_artifact(path: Path | None) -> object:
    raw_payload = path.read_text() if path else sys.stdin.read()
    return json.loads(raw_payload, object_pairs_hook=strict_delivery_art_object)


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    artifact_path = args.artifact.resolve() if args.artifact != Path("-") else None
    artifact_label = str(artifact_path) if artifact_path else "<stdin>"
    try:
        payload = _load_artifact(artifact_path)
    except (OSError, ValueError) as exc:
        print(f"delivery ART artifact invalid: {exc}", file=sys.stderr)
        return 1

    dependency_artifacts = []
    dependency_errors = []
    for dependency_path_arg in args.dependency_artifact:
        dependency_path = dependency_path_arg.resolve()
        try:
            dependency = _load_artifact(dependency_path)
        except (OSError, ValueError) as exc:
            dependency_errors.append(f"{dependency_path}: {exc}")
            continue
        if not isinstance(dependency, dict):
            dependency_errors.append(
                f"{dependency_path}: dependency artifact must be a JSON object"
            )
            continue
        dependency_artifacts.append(dependency)
        dependency_errors.extend(
            f"{dependency_path}: {error}"
            for error in _artifact_errors(dependency, repo_root)
        )

    errors = _artifact_errors(payload, repo_root)
    if isinstance(payload, dict):
        errors.extend(
            f"reference invariant: {error}"
            for error in delivery_art_artifact_reference_errors(
                payload, dependency_artifacts
            )
        )
    for dependency in dependency_artifacts:
        if isinstance(dependency, dict):
            dependency_errors.extend(
                f"dependency reference invariant: {error}"
                for error in delivery_art_artifact_reference_errors(
                    dependency, [payload, *dependency_artifacts]
                )
            )
    errors.extend(dependency_errors)
    if errors:
        for error in errors:
            print(f"delivery ART artifact invalid: {error}", file=sys.stderr)
        return 1

    artifact_type = payload.get("artifact_type") if isinstance(payload, dict) else None
    print(f"delivery ART artifact valid: type={artifact_type} path={artifact_label}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
