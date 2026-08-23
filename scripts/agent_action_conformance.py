#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from typing import Any, Mapping

import yaml


ACTION_CLASSES = ("read", "advise", "draft", "mutate")
EXPECTED_SOURCE_REPOS = {
    "evaluator": "workspace-governance-control-fabric",
    "enforcer": "operator-orchestration-service",
}
EXPECTED_CAPABILITY_POSTURES = {
    "canonical-authority-contract": "implemented",
    "policy-evaluation": "implemented",
    "workflow-enforcement": "implemented",
    "owner-mutation": "synthetic-bounded-proof",
    "shared-runtime-activation": "blocked-future-acceptance",
}
REQUIRED_EXCLUSIONS = {
    "console-agent-mutation",
    "shared-runtime-exposure",
    "stage-execution",
    "production-execution",
    "direct-model-provider-access",
    "canonical-backend-mutation",
}


def _load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256_bytes(payload: bytes) -> str:
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _file_digest(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _git_head(repo_root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def contract_issues(contract: Mapping[str, Any]) -> list[str]:
    issues: list[str] = []
    sources = contract.get("implementation_sources", {})
    for role, expected_repo in EXPECTED_SOURCE_REPOS.items():
        source = sources.get(role, {})
        if source.get("repo") != expected_repo:
            issues.append(f"{role} source must be {expected_repo}")

    postures = {
        entry.get("capability_id"): entry.get("posture")
        for entry in contract.get("capability_postures", [])
        if isinstance(entry, Mapping)
    }
    if len(postures) != len(contract.get("capability_postures", [])):
        issues.append("capability posture identifiers must be unique")
    for capability_id, posture in EXPECTED_CAPABILITY_POSTURES.items():
        if postures.get(capability_id) != posture:
            issues.append(
                f"capability {capability_id!r} must declare posture {posture!r}"
            )

    exclusions = set(contract.get("excluded_capabilities", []))
    missing_exclusions = sorted(REQUIRED_EXCLUSIONS - exclusions)
    if missing_exclusions:
        issues.append(
            "excluded capabilities are incomplete: " + ", ".join(missing_exclusions)
        )

    cases = contract.get("cases", [])
    case_ids = [case.get("case_id") for case in cases if isinstance(case, Mapping)]
    if len(set(case_ids)) != len(case_ids):
        issues.append("case identifiers must be unique")
    for action_class in ACTION_CLASSES:
        classes = {
            case.get("case_class")
            for case in cases
            if isinstance(case, Mapping) and case.get("action_class") == action_class
        }
        if classes != {"positive", "negative"}:
            issues.append(
                f"action class {action_class!r} must have positive and negative cases"
            )
    if not any(case.get("consumed_request_idempotency") for case in cases):
        issues.append("a consumed-idempotency replay case is required")
    failure_injections = {case.get("failure_injection") for case in cases}
    for required in ("receipt-store", "audit"):
        if required not in failure_injections:
            issues.append(f"failure injection {required!r} is required")
    return issues


def _verify_source_contracts(
    repo_root: Path,
    workspace_root: Path,
    contract: Mapping[str, Any],
) -> dict[str, Any]:
    authority_path = repo_root / contract["authority_contract_ref"]
    source_results: dict[str, Any] = {}
    authority_commits: set[str] = set()
    schema_digests: dict[str, set[str]] = {}

    for role, source in contract["implementation_sources"].items():
        source_repo = workspace_root / source["repo"]
        actual_revision = _git_head(source_repo)
        if actual_revision != source["revision"]:
            raise ValueError(
                f"{role} revision mismatch: expected {source['revision']}, got {actual_revision}"
            )
        manifest_path = source_repo / source["manifest_ref"]
        manifest = _load_json(manifest_path)
        authority_commits.add(manifest["source"]["commit"])
        for artifact_type, entry in manifest.get("schemas", {}).items():
            schema_digests.setdefault(artifact_type, set()).add(entry["sha256"])
            workspace_schema = (
                repo_root / "contracts" / "schemas" / Path(entry["path"]).name
            )
            if not workspace_schema.exists():
                raise ValueError(
                    f"{role} manifest references unknown workspace schema {entry['path']}"
                )
            if _file_digest(workspace_schema).removeprefix("sha256:") != entry["sha256"]:
                raise ValueError(
                    f"{role} schema {artifact_type} differs from workspace authority"
                )
        authority = manifest.get("authority")
        if authority:
            if _file_digest(authority_path).removeprefix("sha256:") != authority["sha256"]:
                raise ValueError(f"{role} authority snapshot differs from workspace authority")
        source_results[role] = {
            "repo": source["repo"],
            "revision": actual_revision,
            "manifest_ref": source["manifest_ref"],
            "manifest_digest": _file_digest(manifest_path),
            "authority_source_commit": manifest["source"]["commit"],
        }

    if len(authority_commits) != 1:
        raise ValueError("evaluator and enforcer do not pin the same authority source")
    mismatched_schemas = sorted(
        artifact_type
        for artifact_type, digests in schema_digests.items()
        if len(digests) != 1
    )
    if mismatched_schemas:
        raise ValueError(
            "implementation schema digests disagree: " + ", ".join(mismatched_schemas)
        )
    return source_results


def run_conformance(
    repo_root: Path,
    workspace_root: Path,
    contract: Mapping[str, Any],
) -> dict[str, Any]:
    issues = contract_issues(contract)
    if issues:
        raise ValueError("; ".join(issues))
    sources = _verify_source_contracts(repo_root, workspace_root, contract)

    wgcf_repo = workspace_root / EXPECTED_SOURCE_REPOS["evaluator"]
    with TemporaryDirectory() as temp_dir:
        ledger_path = Path(temp_dir) / "wgcf-agent-action-ledger.jsonl"
        evaluator_input = Path(temp_dir) / "evaluator-input.json"
        evaluator_input.write_text(
            json.dumps(
                {
                    "decision_time": contract["decision_time"],
                    "ledger_path": str(ledger_path),
                    "cases": contract["cases"],
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        evaluator = repo_root / "scripts" / "agent_action_conformance_evaluator.py"
        local_wgcf_python = wgcf_repo / ".venv" / "bin" / "python"
        wgcf_python = local_wgcf_python if local_wgcf_python.exists() else Path(sys.executable)
        evaluation = subprocess.run(
            [str(wgcf_python), str(evaluator), str(evaluator_input), str(wgcf_repo)],
            check=False,
            capture_output=True,
            text=True,
        )
        if evaluation.returncode != 0:
            raise RuntimeError(
                "WGCF conformance evaluator failed: " + evaluation.stderr.strip()
            )
        adapter_cases = json.loads(evaluation.stdout)["cases"]

        adapter_input = Path(temp_dir) / "adapter-input.json"
        adapter_input.write_text(
            json.dumps(
                {
                    "execution_time": contract["execution_time"],
                    "cases": adapter_cases,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        adapter = repo_root / "scripts" / "agent_action_conformance_adapter.mjs"
        oos_repo = workspace_root / EXPECTED_SOURCE_REPOS["enforcer"]
        result = subprocess.run(
            ["node", str(adapter), str(adapter_input), str(oos_repo)],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(
                "OOS conformance adapter failed: " + result.stderr.strip()
            )
        enforcement_results = {
            entry["case_id"]: entry for entry in json.loads(result.stdout)["results"]
        }

    case_results: list[dict[str, Any]] = []
    for case in contract["cases"]:
        actual = enforcement_results[case["case_id"]]
        observed = {
            key: actual[key]
            for key in case["expected"]
        }
        passed = observed == case["expected"]
        case_results.append(
            {
                "case_id": case["case_id"],
                "action_class": case["action_class"],
                "case_class": case["case_class"],
                "passed": passed,
                "expected": copy.deepcopy(case["expected"]),
                "observed": observed,
                "policy_reason_codes": actual["policy_reason_codes"],
                "decision_ref": actual["decision_ref"],
                "action_receipt_ref": actual["action_receipt_ref"],
                "owner_receipt_ref": actual["owner_receipt_ref"],
                "error_code": actual["error_code"],
            }
        )

    passed = bool(case_results) and all(case["passed"] for case in case_results)
    return {
        "schema_version": 1,
        "proof_posture": contract["proof_posture"],
        "work_item_ref": contract["work_item_ref"],
        "authority_contract_ref": contract["authority_contract_ref"],
        "authority_contract_digest": _file_digest(
            repo_root / contract["authority_contract_ref"]
        ),
        "conformance_contract_digest": _file_digest(
            repo_root / "contracts" / "agent-action-conformance.yaml"
        ),
        "implementation_sources": sources,
        "summary": {
            "outcome": "passed" if passed else "failed",
            "case_count": len(case_results),
            "positive_case_count": sum(
                case["case_class"] == "positive" for case in case_results
            ),
            "negative_case_count": sum(
                case["case_class"] == "negative" for case in case_results
            ),
            "passed_case_count": sum(case["passed"] for case in case_results),
            "runtime_activation": "disabled",
        },
        "capability_postures": copy.deepcopy(contract["capability_postures"]),
        "excluded_capabilities": list(contract["excluded_capabilities"]),
        "cases": case_results,
    }


def report_issues(report: Mapping[str, Any]) -> list[str]:
    issues: list[str] = []
    summary = report.get("summary", {})
    cases = report.get("cases", [])
    if summary.get("outcome") != "passed":
        issues.append("conformance summary must pass")
    if summary.get("case_count") != len(cases):
        issues.append("conformance summary case count differs from its case list")
    if summary.get("passed_case_count") != len(cases):
        issues.append("every conformance case must pass")
    if summary.get("runtime_activation") != "disabled":
        issues.append("conformance proof must not activate runtime behavior")
    missing_exclusions = REQUIRED_EXCLUSIONS - set(
        report.get("excluded_capabilities", [])
    )
    if missing_exclusions:
        issues.append("conformance report exclusions are incomplete")
    for case in cases:
        if not case.get("passed"):
            issues.append(f"conformance case {case.get('case_id')} did not pass")
        decision_ref = case.get("decision_ref", {})
        if not str(decision_ref.get("digest", "")).startswith("sha256:"):
            issues.append(
                f"conformance case {case.get('case_id')} lacks a decision digest"
            )
        if case.get("observed", {}).get("terminal_receipts"):
            action_ref = case.get("action_receipt_ref", {})
            if not str(action_ref.get("digest", "")).startswith("sha256:"):
                issues.append(
                    f"conformance case {case.get('case_id')} lacks an action receipt digest"
                )
    serialized = json.dumps(report, sort_keys=True)
    for forbidden in ("raw_context", "raw_model_output", "credentials"):
        if forbidden in serialized:
            issues.append(f"conformance report contains forbidden field {forbidden}")
    return issues


def render_markdown(report: Mapping[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Agent Action Conformance",
        "",
        "This generated report proves the merged WGCF evaluator and OOS enforcer against the workspace-owned action contract.",
        "",
        "## Result",
        "",
        f"- Outcome: `{summary['outcome']}`",
        f"- Cases: `{summary['passed_case_count']}/{summary['case_count']}` passed",
        f"- Positive cases: `{summary['positive_case_count']}`",
        f"- Negative cases: `{summary['negative_case_count']}`",
        f"- Runtime activation: `{summary['runtime_activation']}`",
        f"- Authority contract: `{report['authority_contract_digest']}`",
        f"- Conformance contract: `{report['conformance_contract_digest']}`",
        "",
        "The owner mutation adapter is synthetic. This proof does not mutate a canonical backend or activate shared runtime behavior.",
        "",
        "## Source Revisions",
        "",
        "| Role | Repository | Revision | Manifest |",
        "| --- | --- | --- | --- |",
    ]
    for role in sorted(report["implementation_sources"]):
        source = report["implementation_sources"][role]
        lines.append(
            f"| `{role}` | `{source['repo']}` | `{source['revision']}` | `{source['manifest_digest']}` |"
        )
    lines.extend(
        [
            "",
            "## Cases",
            "",
            "| Case | Class | Action | Policy | Execution | Dispatch | Owner mutation | Terminal receipts | Result |",
            "| --- | --- | --- | --- | --- | ---: | ---: | ---: | --- |",
        ]
    )
    for case in report["cases"]:
        observed = case["observed"]
        lines.append(
            f"| `{case['case_id']}` | `{case['case_class']}` | `{case['action_class']}` | "
            f"`{observed['policy_outcome']}` | `{observed['execution_outcome']}` | "
            f"{observed['execution_invocations']} | {observed['owner_mutation_invocations']} | "
            f"{observed['terminal_receipts']} | `{'passed' if case['passed'] else 'failed'}` |"
        )
    lines.extend(["", "## Excluded Capabilities", ""])
    lines.extend(f"- `{item}`" for item in report["excluded_capabilities"])
    lines.extend(["", "## Receipt References", ""])
    for case in report["cases"]:
        refs = [f"decision `{case['decision_ref']['uri']}`"]
        if case["action_receipt_ref"]:
            refs.append(f"action `{case['action_receipt_ref']['uri']}`")
        if case["owner_receipt_ref"]:
            refs.append(f"owner `{case['owner_receipt_ref']['uri']}`")
        lines.append(f"- `{case['case_id']}`: " + "; ".join(refs))
    return "\n".join(lines).rstrip() + "\n"


def _expected_outputs(
    repo_root: Path,
    workspace_root: Path,
) -> tuple[dict[str, Any], dict[Path, str]]:
    contract = _load_yaml(repo_root / "contracts" / "agent-action-conformance.yaml")
    report = run_conformance(repo_root, workspace_root, contract)
    issues = report_issues(report)
    if issues:
        raise ValueError("; ".join(issues))
    outputs = contract["report_outputs"]
    return report, {
        repo_root / outputs["json"]: json.dumps(report, indent=2, sort_keys=True) + "\n",
        repo_root / outputs["markdown"]: render_markdown(report),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run integrated local agent-action conformance proof."
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    parser.add_argument(
        "--workspace-root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true", help="write generated reports")
    mode.add_argument("--check", action="store_true", help="verify generated reports")
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()
    workspace_root = args.workspace_root.resolve()
    try:
        report, outputs = _expected_outputs(repo_root, workspace_root)
    except (KeyError, RuntimeError, TypeError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"ERROR: {exc}")
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
                print(
                    "ERROR: generated agent-action report is stale: "
                    + str(path.relative_to(repo_root))
                )
            return 1
    else:
        print(json.dumps(report, indent=2, sort_keys=True))
    print(
        "agent-action conformance passed: "
        f"cases={report['summary']['case_count']} "
        f"runtime_activation={report['summary']['runtime_activation']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
