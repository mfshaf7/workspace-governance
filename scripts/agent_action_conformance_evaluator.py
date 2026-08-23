#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
from typing import Any, Mapping


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def prepare_request(
    base_request: Mapping[str, Any],
    case: Mapping[str, Any],
    canonical_digest: Any,
) -> dict[str, Any]:
    request = copy.deepcopy(base_request)
    action_class = case["action_class"]
    case_id = case["case_id"]
    request["request_id"] = f"agent-action-request:conformance-{case_id}"
    request["action_class"] = action_class
    request["workflow"]["execution_id"] = f"workflow-execution:conformance-{case_id}"
    request["correlation"] = {
        "correlation_id": f"correlation:conformance-{case_id}",
        "causation_id": f"causation:conformance-{case_id}",
    }
    request["idempotency_key"] = f"agent-action:conformance-{case_id}"
    if action_class == "read":
        request["model_invocation_ref"] = None
        request["context"] = {"packet_ref": None, "receipt_ref": None}
        request["authority"]["approval_ref"] = None
    elif action_class in {"advise", "draft"}:
        request["authority"]["approval_ref"] = None
    else:
        request["model_invocation_ref"] = None
    request["integrity"].pop("content_digest", None)
    request["integrity"]["content_digest"] = canonical_digest(request)
    return request


def current_for(
    base_current: Mapping[str, Any],
    request: Mapping[str, Any],
    case: Mapping[str, Any],
) -> dict[str, Any]:
    current = copy.deepcopy(base_current)
    current.update(
        {
            "operator_principal_id": request["operator"]["principal_id"],
            "operator_session_ref": request["operator"]["session_ref"],
            "operator_acceptance_ref": request["operator"]["acceptance_ref"],
            "caller_workload_id": request["caller"]["workload_id"],
            "caller_credential_binding_ref": request["caller"][
                "credential_binding_ref"
            ],
            "agent_instance_id": request["agent"]["instance_id"],
            "model_invocation_ref": request["model_invocation_ref"],
            "workflow_id": request["workflow"]["workflow_id"],
            "workflow_version": request["workflow"]["workflow_version"],
            "admitted_commands": [request["workflow"]["command"]],
            "target_owner_repo": request["target"]["owner_repo"],
            "target_resource_id": request["target"]["resource_id"],
            "source_version": request["target"]["source_version"],
            "context_packet_ref": request["context"]["packet_ref"],
            "context_receipt_ref": request["context"]["receipt_ref"],
            "delegation_ref": request["authority"]["delegation_ref"],
            "policy_profile_ref": request["authority"]["policy_profile_ref"],
            "approval_ref": request["authority"]["approval_ref"],
            "consumed_idempotency": [],
        }
    )
    current.update(copy.deepcopy(case["current_overrides"]))
    if case["consumed_request_idempotency"]:
        current["consumed_idempotency"] = [
            {
                "idempotency_key": request["idempotency_key"],
                "intent_digest": request["intent"]["digest"],
            }
        ]
    return current


def main() -> int:
    if len(sys.argv) != 3:
        raise ValueError(
            "usage: agent_action_conformance_evaluator.py <input.json> <wgcf-repo>"
        )
    input_payload = load_json(Path(sys.argv[1]))
    wgcf_repo = Path(sys.argv[2]).resolve()
    sys.path.insert(
        0, str(wgcf_repo / "packages" / "control_fabric_core" / "src")
    )
    from control_fabric_core import run_agent_action_evaluation
    from control_fabric_core.canonical_json import canonical_digest

    fixture_root = wgcf_repo / "contracts" / "agent-action" / "fixtures"
    base_request = load_json(fixture_root / "request.valid.json")
    base_current = load_json(fixture_root / "current.valid.json")
    ledger_path = Path(input_payload["ledger_path"])
    results = []
    for case in input_payload["cases"]:
        request = prepare_request(base_request, case, canonical_digest)
        current = current_for(base_current, request, case)
        evaluation = run_agent_action_evaluation(
            request,
            actor="operator-orchestration-service",
            current=current,
            ledger_path=ledger_path,
            now=input_payload["decision_time"],
        )
        results.append(
            {
                "case_id": case["case_id"],
                "request": request,
                "current": current,
                "decision": evaluation.decision.to_record(),
                "ledger_event": evaluation.ledger_event.to_record(),
                "failure_injection": case["failure_injection"],
            }
        )
    print(json.dumps({"cases": results}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
