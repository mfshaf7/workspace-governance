#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

from project_lifecycle_contract import state_vector_issues, transition_request_issues


REQUIRED_CAPABILITY_POSTURES = {
    "canonical-lifecycle-contract": "implemented",
    "semantic-transition-validator": "implemented",
    "deterministic-local-simulation": "implemented",
    "transition-backend-adapters": "contract-only",
    "governed-runtime-wiring": "blocked-future-wiring",
    "console-projection-wiring": "blocked-future-wiring",
}


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _digest(payload: Any) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def proof_model(proof_contract: Mapping[str, Any]) -> Mapping[str, Any]:
    model = proof_contract.get("project_lifecycle_proof", {})
    return model if isinstance(model, Mapping) else {}


def _synthetic_envelope_value(
    field: str,
    *,
    project: Mapping[str, Any],
    scenario_id: str,
    step_id: str,
    transition_id: str,
    state_version: int,
    evidence_types: list[str],
    recovery: Mapping[str, Any] | None,
) -> Any:
    values: dict[str, Any] = {
        "transition_id": transition_id,
        "project_ref": project["project_ref"],
        "expected_state_version": state_version,
        "requested_by": project["operator_ref"],
        "source_record_ref": project["source_ref"],
        "source_repo_ref": project["incubation_repo_ref"],
        "target_repo_ref": project["owner_repo_ref"],
        "target_owner_ref": project["owner_repo_ref"],
        "evidence_refs": [
            f"proof://evidence/{scenario_id}/{step_id}/{evidence_type}"
            for evidence_type in evidence_types
        ],
        "artifact_refs": [f"proof://artifact/{scenario_id}/{step_id}"],
        "recovery": recovery,
    }
    if field in values:
        return values[field]
    return f"proof://{field}/{scenario_id}/{step_id}"


def _build_request(
    lifecycle_contract: Mapping[str, Any],
    proof: Mapping[str, Any],
    scenario_id: str,
    step: Mapping[str, Any],
    current_state: Mapping[str, str],
    state_version: int,
) -> dict[str, Any]:
    lifecycle = lifecycle_contract["project_lifecycle"]
    requested_state = dict(current_state)
    requested_state.update(step["state_changes"])
    envelope_type = step["envelope_type"]
    required_fields = lifecycle.get("envelopes", {}).get(envelope_type, {}).get(
        "required_fields", []
    )
    omitted = set(step["omit_envelope_fields"])
    envelope = {
        field: _synthetic_envelope_value(
            field,
            project=proof["representative_project"],
            scenario_id=scenario_id,
            step_id=step["step_id"],
            transition_id=step["transition_id"],
            state_version=state_version,
            evidence_types=step["evidence_types"],
            recovery=step["recovery"],
        )
        for field in required_fields
        if field not in omitted
    }
    return {
        "transition_id": step["transition_id"],
        "current_state": dict(current_state),
        "requested_state": requested_state,
        "source_authority_role": step["source_authority_role"],
        "target_owner_role": step["target_owner_role"],
        "implementation_maturity": step["implementation_maturity"],
        "envelope_type": envelope_type,
        "envelope": envelope,
        "evidence_types": list(step["evidence_types"]),
        "recovery": step["recovery"],
    }


def run_proof(
    lifecycle_contract: Mapping[str, Any],
    proof_contract: Mapping[str, Any],
) -> dict[str, Any]:
    proof = proof_model(proof_contract)
    scenario_results: list[dict[str, Any]] = []

    for scenario in proof.get("scenarios", []):
        state = dict(scenario["initial_state"])
        state_version = 1
        step_results: list[dict[str, Any]] = []
        for step in scenario["steps"]:
            request = _build_request(
                lifecycle_contract,
                proof,
                scenario["scenario_id"],
                step,
                state,
                state_version,
            )
            issues = transition_request_issues(lifecycle_contract, request)
            outcome = "accepted" if not issues else "rejected"
            missing_expected_issues = [
                fragment
                for fragment in step["expected"]["issue_contains"]
                if not any(fragment in issue for issue in issues)
            ]
            passed = (
                outcome == step["expected"]["outcome"]
                and not missing_expected_issues
            )
            if outcome == "accepted":
                state = dict(request["requested_state"])
                state_version += 1
            receipt_payload = {
                "scenario_id": scenario["scenario_id"],
                "step_id": step["step_id"],
                "transition_id": step["transition_id"],
                "outcome": outcome,
                "resulting_state": state,
                "issues": issues,
            }
            step_results.append(
                {
                    **receipt_payload,
                    "expected_outcome": step["expected"]["outcome"],
                    "missing_expected_issues": missing_expected_issues,
                    "passed": passed,
                    "receipt_id": f"lifecycle-proof-receipt:{_digest(receipt_payload)}",
                }
            )

        final_state_matches = state == scenario["expected_final_state"]
        scenario_results.append(
            {
                "scenario_id": scenario["scenario_id"],
                "class": scenario["class"],
                "purpose": scenario["purpose"],
                "passed": all(step["passed"] for step in step_results)
                and final_state_matches,
                "final_state_matches": final_state_matches,
                "resulting_state": state,
                "expected_final_state": scenario["expected_final_state"],
                "steps": step_results,
            }
        )

    passed = bool(scenario_results) and all(
        scenario["passed"] for scenario in scenario_results
    )
    capability_postures = list(proof.get("capability_postures", []))
    return {
        "schema_version": 1,
        "proof_posture": proof.get("proof_posture"),
        "lifecycle_contract_ref": proof.get("lifecycle_contract_ref"),
        "lifecycle_contract_digest": f"sha256:{_digest(lifecycle_contract)}",
        "proof_contract_digest": f"sha256:{_digest(proof_contract)}",
        "representative_project": proof.get("representative_project"),
        "summary": {
            "outcome": "passed" if passed else "failed",
            "scenario_count": len(scenario_results),
            "positive_scenario_count": sum(
                scenario["class"] == "positive" for scenario in scenario_results
            ),
            "negative_scenario_count": sum(
                scenario["class"] == "negative" for scenario in scenario_results
            ),
            "passed_scenario_count": sum(
                scenario["passed"] for scenario in scenario_results
            ),
            "readiness": (
                "ready-for-baseline-review"
                if passed
                else "not-ready-for-baseline-review"
            ),
        },
        "capability_postures": capability_postures,
        "scenarios": scenario_results,
    }


def proof_suite_issues(
    lifecycle_contract: Mapping[str, Any],
    proof_contract: Mapping[str, Any],
) -> list[str]:
    proof = proof_model(proof_contract)
    issues: list[str] = []
    capability_entries = proof.get("capability_postures", [])
    scenario_entries = proof.get("scenarios", [])
    if not isinstance(capability_entries, list):
        return ["capability_postures must be a list"]
    if not isinstance(scenario_entries, list):
        return ["scenarios must be a list"]
    if any(not isinstance(item, Mapping) for item in capability_entries):
        return ["every capability posture must be a mapping"]
    if any(not isinstance(item, Mapping) for item in scenario_entries):
        return ["every proof scenario must be a mapping"]
    capability_postures = {
        item.get("capability_id"): item.get("posture")
        for item in capability_entries
    }
    if len(capability_postures) != len(capability_entries):
        issues.append("capability posture identifiers must be unique")
    for capability_id, expected_posture in REQUIRED_CAPABILITY_POSTURES.items():
        if capability_postures.get(capability_id) != expected_posture:
            issues.append(
                f"capability {capability_id!r} must declare posture {expected_posture!r}"
            )

    scenario_ids: set[str] = set()
    for scenario in scenario_entries:
        scenario_id = scenario.get("scenario_id")
        if scenario_id in scenario_ids:
            issues.append(f"duplicate proof scenario {scenario_id!r}")
        scenario_ids.add(scenario_id)
        state_issues = state_vector_issues(
            lifecycle_contract, scenario.get("initial_state", {})
        )
        issues.extend(
            f"scenario {scenario_id} initial state: {issue}" for issue in state_issues
        )
        step_ids: set[str] = set()
        rejected_steps = 0
        for step in scenario.get("steps", []):
            step_id = step.get("step_id")
            if step_id in step_ids:
                issues.append(f"scenario {scenario_id} has duplicate step {step_id!r}")
            step_ids.add(step_id)
            if step.get("expected", {}).get("outcome") == "rejected":
                rejected_steps += 1
        if scenario.get("class") == "positive" and rejected_steps:
            issues.append(f"positive scenario {scenario_id} cannot expect rejection")
        if scenario.get("class") == "negative" and not rejected_steps:
            issues.append(f"negative scenario {scenario_id} must expect rejection")

    try:
        report = run_proof(lifecycle_contract, proof_contract)
    except (KeyError, TypeError, ValueError) as exc:
        issues.append(f"proof suite cannot execute: {exc}")
        return issues
    for scenario in report["scenarios"]:
        if not scenario["passed"]:
            issues.append(f"proof scenario {scenario['scenario_id']} did not pass")
    return issues


def render_markdown(report: Mapping[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Project Lifecycle Baseline Readiness",
        "",
        "This report is generated by `scripts/project_lifecycle_proof.py` from the canonical lifecycle and proof contracts.",
        "",
        "## Result",
        "",
        f"- Outcome: `{summary['outcome']}`",
        f"- Readiness: `{summary['readiness']}`",
        f"- Scenarios: `{summary['passed_scenario_count']}/{summary['scenario_count']}` passed",
        f"- Lifecycle contract: `{report['lifecycle_contract_digest']}`",
        f"- Proof contract: `{report['proof_contract_digest']}`",
        "",
        "This is deterministic local contract proof. It does not claim that backend adapters, governed runtime promotion, or Console projection wiring are live.",
        "",
        "## Capability Posture",
        "",
        "| Capability | Posture | Reason |",
        "| --- | --- | --- |",
    ]
    for capability in report["capability_postures"]:
        lines.append(
            f"| `{capability['capability_id']}` | `{capability['posture']}` | {capability['reason']} |"
        )
    lines.extend(
        [
            "",
            "## Scenarios",
            "",
            "| Scenario | Class | Result | Steps |",
            "| --- | --- | --- | ---: |",
        ]
    )
    for scenario in report["scenarios"]:
        lines.append(
            f"| `{scenario['scenario_id']}` | `{scenario['class']}` | "
            f"`{'passed' if scenario['passed'] else 'failed'}` | {len(scenario['steps'])} |"
        )
    lines.extend(["", "## Step Receipts", ""])
    for scenario in report["scenarios"]:
        lines.append(f"### `{scenario['scenario_id']}`")
        lines.append("")
        for step in scenario["steps"]:
            lines.append(
                f"- `{step['step_id']}`: `{step['outcome']}`; `{step['receipt_id']}`"
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _expected_outputs(
    repo_root: Path,
) -> tuple[dict[str, Any], dict[Path, str]]:
    lifecycle_contract = _load_yaml(repo_root / "contracts/project-lifecycle.yaml")
    proof_contract = _load_yaml(repo_root / "contracts/project-lifecycle-proof.yaml")
    report = run_proof(lifecycle_contract, proof_contract)
    outputs = proof_model(proof_contract)["report_outputs"]
    rendered = {
        repo_root / outputs["json"]: json.dumps(report, indent=2, sort_keys=True) + "\n",
        repo_root / outputs["markdown"]: render_markdown(report),
    }
    return report, rendered


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run deterministic project-lifecycle scenarios and manage readiness reports."
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true", help="write generated reports")
    mode.add_argument("--check", action="store_true", help="verify generated reports")
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()
    lifecycle_contract = _load_yaml(repo_root / "contracts/project-lifecycle.yaml")
    proof_contract = _load_yaml(repo_root / "contracts/project-lifecycle-proof.yaml")
    issues = proof_suite_issues(lifecycle_contract, proof_contract)
    report, outputs = _expected_outputs(repo_root)
    if issues:
        for issue in issues:
            print(f"ERROR: {issue}")
        return 1
    if args.write:
        for path, content in outputs.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
    elif args.check:
        stale = [
            path
            for path, content in outputs.items()
            if not path.exists() or path.read_text(encoding="utf-8") != content
        ]
        if stale:
            for path in stale:
                print(f"ERROR: generated lifecycle report is stale: {path.relative_to(repo_root)}")
            return 1
    else:
        print(json.dumps(report, indent=2, sort_keys=True))
    print(
        "project lifecycle proof passed: "
        f"scenarios={report['summary']['scenario_count']} "
        f"readiness={report['summary']['readiness']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
