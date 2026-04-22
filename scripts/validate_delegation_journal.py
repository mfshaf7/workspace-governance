#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from contracts_lib import load_contracts, load_json


JOURNAL_SCHEMA = "contracts/schemas/delegation-journal-record.schema.json"


def normalize_rel_path(path: str) -> str:
    return path.strip().strip("/")


def path_contains(parent: str, child: str) -> bool:
    parent_norm = normalize_rel_path(parent)
    child_norm = normalize_rel_path(child)
    return child_norm == parent_norm or child_norm.startswith(parent_norm + "/")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate delegated execution journal records.")
    parser.add_argument(
        "--workspace-root",
        default=Path("/home/mfshaf7/projects"),
        type=Path,
        help="workspace root that contains workspace-governance",
    )
    args = parser.parse_args()

    workspace_root = args.workspace_root.resolve()
    repo_root = workspace_root / "workspace-governance"
    journal_root = repo_root / "reviews" / "delegation-journal"
    schema_path = repo_root / JOURNAL_SCHEMA
    schema = load_json(schema_path)
    validator = Draft202012Validator(schema)

    contracts = load_contracts(repo_root)
    active_repos = set(contracts["repos"]["repos"].keys())
    policy = contracts["delegation_policy"]
    task_classes = policy["task_classes"]
    main_agent_only_actions = set(policy["main_agent_only_actions"])
    packet_delegate_kinds = set(policy["packet"]["delegate_kinds"])

    errors: list[str] = []
    delegation_ids: set[str] = set()

    for path in sorted(journal_root.glob("*.yaml")):
        if path.name == "TEMPLATE.yaml":
          continue
        payload = yaml.safe_load(path.read_text()) or {}
        for error in validator.iter_errors(payload):
            pointer = ".".join(str(part) for part in error.absolute_path) or "<root>"
            errors.append(f"{path}: {pointer}: {error.message}")
        if not payload:
            continue

        delegation_id = payload["delegation_id"]
        if delegation_id in delegation_ids:
            errors.append(f"{path}: duplicate delegation_id {delegation_id!r}")
        delegation_ids.add(delegation_id)

        owner_repo = payload["owner_repo"]
        if owner_repo not in active_repos:
            errors.append(f"{path}: owner_repo {owner_repo!r} is not an active repo")

        task_class = payload["task_class"]
        if task_class not in task_classes:
            errors.append(f"{path}: unknown task_class {task_class!r}")
            continue

        class_policy = task_classes[task_class]
        packets = payload["packets"]
        if len(packets) > class_policy["max_sub_agents"]:
            errors.append(
                f"{path}: task_class {task_class!r} allows at most {class_policy['max_sub_agents']} delegated packets"
            )

        retained_actions = set(payload["main_agent"]["retained_actions"])
        missing_retained = sorted(main_agent_only_actions - retained_actions)
        if missing_retained:
            errors.append(
                f"{path}: main_agent.retained_actions missing required actions {', '.join(missing_retained)}"
            )

        packet_paths: list[tuple[str, str, str]] = []
        packet_ids: set[str] = set()
        for packet in packets:
            packet_id = packet["packet_id"]
            if packet_id in packet_ids:
                errors.append(f"{path}: duplicate packet_id {packet_id!r}")
            packet_ids.add(packet_id)

            if packet["delegate_kind"] not in packet_delegate_kinds:
                errors.append(
                    f"{path}: packet {packet_id!r} uses unsupported delegate_kind {packet['delegate_kind']!r}"
                )
            target_repo = packet["target_repo"]
            if target_repo not in active_repos:
                errors.append(f"{path}: packet {packet_id!r} target_repo {target_repo!r} is not an active repo")

            forbidden_actions = set(packet["forbidden_actions"])
            missing_forbidden = sorted(main_agent_only_actions - forbidden_actions)
            if missing_forbidden:
                errors.append(
                    f"{path}: packet {packet_id!r} forbidden_actions missing main-agent-only actions {', '.join(missing_forbidden)}"
                )

            if class_policy["requires_disjoint_write_scope"] and not packet["allowed_write_paths"]:
                errors.append(f"{path}: packet {packet_id!r} requires allowed_write_paths for this task class")

            for changed_path in packet["changed_paths"]:
                if packet["allowed_write_paths"] and not any(
                    path_contains(allowed_path, changed_path) for allowed_path in packet["allowed_write_paths"]
                ):
                    errors.append(
                        f"{path}: packet {packet_id!r} changed_path {changed_path!r} is outside declared allowed_write_paths"
                    )

            for allowed_path in packet["allowed_write_paths"]:
                packet_paths.append((packet_id, target_repo, normalize_rel_path(allowed_path)))

        for index, (packet_id, target_repo, allowed_path) in enumerate(packet_paths):
            for other_packet_id, other_target_repo, other_allowed_path in packet_paths[index + 1 :]:
                if target_repo != other_target_repo:
                    continue
                if path_contains(allowed_path, other_allowed_path) or path_contains(other_allowed_path, allowed_path):
                    errors.append(
                        f"{path}: overlapping allowed_write_paths between packet {packet_id!r} and {other_packet_id!r} in repo {target_repo!r}"
                    )

        security_review_ref = payload["integration_outcome"]["security_review_ref"]
        if class_policy["requires_security_delta_review"] and not security_review_ref:
            errors.append(
                f"{path}: task_class {task_class!r} requires integration_outcome.security_review_ref"
            )

    if errors:
        raise SystemExit("\n".join(errors))

    print("delegation journal valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
