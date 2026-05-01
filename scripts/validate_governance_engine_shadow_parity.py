#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

from contracts_lib import load_contracts
from governance_engine_materializer import (
    check_generated_artifacts,
    check_workspace_root_outputs,
    install_registered_skills,
)
from validate_cross_repo_truth import build_generated_contracts


def validate_cutover_gate(
    *,
    repo_root: Path,
    workspace_root: Path,
    gate: dict,
    errors: list[str],
) -> None:
    expected_evidence = {
        "platform-profile-gates",
        "security-delta-current",
        "receipt-parity",
        "direct-rollback-retained",
        "raw-artifact-deny-by-default",
    }
    if set(gate["required_evidence"]) != expected_evidence:
        errors.append(
            "shadow parity cutover gate missing required platform, security, receipt, rollback, or raw-artifact-deny evidence"
        )

    expected_profile_gates = {
        "devint-shadow",
        "stage-readiness",
        "prod-readiness",
        "break-glass",
    }
    actual_profile_gates = {entry["id"] for entry in gate["profile_gates"]}
    if actual_profile_gates != expected_profile_gates:
        errors.append(
            "shadow parity cutover gate must define devint-shadow, stage-readiness, prod-readiness, and break-glass profile gates"
        )

    expected_scopes = {
        "workspace-governance",
        "delivery-art",
        "platform-runtime",
        "security-review",
    }
    actual_scopes = {entry["id"] for entry in gate["representative_scopes"]}
    if actual_scopes != expected_scopes:
        errors.append(
            "shadow parity cutover gate must cover workspace-governance, delivery-art, platform-runtime, and security-review representative scopes"
        )

    cutover_states = {entry["id"]: entry for entry in gate["cutover_states"]}
    expected_state_ids = {"shadow-only", "limited-cutover", "retirement-eligible"}
    if set(cutover_states) != expected_state_ids:
        errors.append(
            "shadow parity cutover gate must define shadow-only, limited-cutover, and retirement-eligible states"
        )
    elif any(
        state["may_retire_direct"] != (state_id == "retirement-eligible")
        for state_id, state in cutover_states.items()
    ):
        errors.append(
            "only the retirement-eligible cutover state may allow direct validator retirement"
        )

    retirement = gate["retirement_eligibility"]
    if retirement["catalog_ref"] != "contracts/governance-validator-catalog.yaml":
        errors.append("retirement eligibility must point to the validator catalog")
    for required_flag in (
        "requires_register_retirement_allowed",
        "receipt_parity_required",
        "direct_validator_rollback_required",
        "owner_closeout_required",
    ):
        if retirement[required_flag] is not True:
            errors.append(f"retirement eligibility must require {required_flag}")
    if retirement["raw_artifact_custody_default"] != "deny":
        errors.append("retirement eligibility must keep raw artifact custody default deny")

    for ref_key in ("platform_gate_ref", "security_review_ref"):
        repo_name, _, rel_path = gate[ref_key].partition("/")
        if not repo_name or not rel_path:
            errors.append(f"{ref_key} must be a repo-relative cross-repo reference")
            continue
        repo_path = workspace_root / repo_name
        if repo_path.exists() and not (repo_path / rel_path).exists():
            errors.append(f"{ref_key} points to missing file: {gate[ref_key]}")
        if repo_name == repo_root.name and not (repo_root / rel_path).exists():
            errors.append(f"{ref_key} points to missing local file: {gate[ref_key]}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fail-closed shadow-parity validation for governance-engine materialization."
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
        help="workspace root containing the active repos",
    )
    parser.add_argument(
        "--skills-root",
        default=Path.home() / ".codex" / "skills",
        type=Path,
        help="live Codex skills root to compare against registered skill sources",
    )
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    workspace_root = args.workspace_root.resolve()
    skills_root = args.skills_root.expanduser().resolve()
    contracts = load_contracts(repo_root)
    foundation = contracts["governance_engine_foundation"]["governance_engine_foundation"]

    errors: list[str] = []
    errors.extend(
        check_workspace_root_outputs(repo_root, workspace_root, contracts=contracts)
    )
    _, skill_errors = install_registered_skills(
        repo_root,
        workspace_root,
        skills_root,
        contracts=contracts,
        check=True,
    )
    errors.extend(skill_errors)
    compiled_outputs = build_generated_contracts(repo_root, contracts)
    errors.extend(
        check_generated_artifacts(repo_root, compiled_outputs, contracts=contracts)
    )

    for rel_path in foundation["compatibility_boundary"]["stable_entrypoints"]:
        path = repo_root / rel_path
        if not path.exists():
            errors.append(f"missing stable compatibility entrypoint: {path}")

    shadow_parity = contracts["governance_engine_shadow_parity"][
        "governance_engine_shadow_parity"
    ]
    validate_cutover_gate(
        repo_root=repo_root,
        workspace_root=workspace_root,
        gate=shadow_parity["cutover_gate"],
        errors=errors,
    )

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print("governance-engine shadow parity valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
