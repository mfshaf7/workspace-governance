from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest

from jsonschema import Draft202012Validator, FormatChecker
import yaml


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from prototype_closure_contract import contract_issues, history_issues, receipt_issues  # noqa: E402


def schema(name: str) -> Draft202012Validator:
    path = ROOT / "contracts/schemas" / f"prototype-closure-{name}.schema.json"
    return Draft202012Validator(json.loads(path.read_text()), format_checker=FormatChecker())


def request(action: str) -> dict:
    values = {
        "schema_version": 1,
        "artifact_type": "prototype-closure-request",
        "request_id": "closure-request:prototype-1:1",
        "prototype_id": "prototype-1",
        "action": action,
        "expected_lifecycle": {
            "apply-delivery": "baseline-approved",
            "graduate-source": "graduating",
            "retire-incubation": "candidate",
            "reopen-incubation": "retired",
        }[action],
        "expected_source_revision": "a" * 40,
        "operator_id": "operator:workspace-owner",
        "correlation_id": "closure:prototype-1:1",
        "idempotency_key": "closure:prototype-1:1",
    }
    if action == "apply-delivery":
        values.update(accepted_baseline_receipt_ref="baseline:1", accepted_delivery_target_receipt_ref="delivery:1")
    elif action == "graduate-source":
        values.update(accepted_delivery_target_receipt_ref="delivery:1", durable_owner_ref="owner:1", durable_repo_ref="repo:1", durable_owner_acceptance_ref="owner-accepted:1", source_transfer_receipt_ref="transfer:1")
    elif action == "retire-incubation":
        values.update(retirement_reason="not-viable", retention_plan_ref="retention:1", runtime_disposition_ref="runtime:none")
    else:
        values["prior_retirement_receipt_ref"] = "retirement:1"
    return values


def receipt(req: dict) -> dict:
    action = req["action"]
    values = {
        "schema_version": 1,
        "artifact_type": "prototype-closure-receipt",
        "receipt_id": "closure-receipt:prototype-1:1",
        "request_ref": req["request_id"],
        "prototype_id": req["prototype_id"],
        "action": action,
        "outcome": "completed",
        "previous_lifecycle": req["expected_lifecycle"],
        "observed_lifecycle": {
            "apply-delivery": "graduating",
            "graduate-source": "graduated",
            "retire-incubation": "retired",
            "reopen-incubation": "exploring",
        }[action],
        "previous_source_custody": "incubation-repo",
        "observed_source_custody": "dedicated-owner-repo" if action == "graduate-source" else "incubation-repo",
        "source_revision": req["expected_source_revision"],
        "operator_id": req["operator_id"],
        "correlation_id": req["correlation_id"],
        "idempotency_key": req["idempotency_key"],
        "recorded_at": "2026-09-12T03:30:00Z",
        "evidence_refs": ["evidence:1"],
    }
    for field in ("accepted_delivery_target_receipt_ref", "durable_owner_acceptance_ref", "source_transfer_receipt_ref", "prior_retirement_receipt_ref"):
        if field in req:
            values[field] = req[field]
    if action != "apply-delivery":
        values["merged_studio_readback_ref"] = "studio-readback:1"
    return values


class PrototypeClosureContractTests(unittest.TestCase):
    def test_contract_owner_and_exit_boundaries(self) -> None:
        contract = yaml.safe_load((ROOT / "contracts/prototype-closure.yaml").read_text())
        known = set(contract["authority"].values()) | {"workspace-governance"}
        self.assertEqual(contract_issues(contract, known_repos=known), [])
        contract["target_routes"]["portfolio"]["maturity"] = "active"
        self.assertIn("Portfolio cannot be a direct Prototype exit", contract_issues(contract, known_repos=known))

    def test_each_action_requires_typed_evidence(self) -> None:
        for action in ("apply-delivery", "graduate-source", "retire-incubation", "reopen-incubation"):
            with self.subTest(action=action):
                req = request(action)
                result = receipt(req)
                self.assertEqual(list(schema("request").iter_errors(req)), [])
                self.assertEqual(list(schema("receipt").iter_errors(result)), [])
                self.assertEqual(receipt_issues(req, result), [])

    def test_delivery_acceptance_cannot_graduate_source(self) -> None:
        req = request("apply-delivery")
        result = receipt(req)
        result["observed_source_custody"] = "dedicated-owner-repo"
        self.assertTrue(list(schema("receipt").iter_errors(result)))
        self.assertIn("Delivery application cannot graduate source", receipt_issues(req, result))

    def test_receipt_rejects_stale_source_revision(self) -> None:
        req = request("apply-delivery")
        result = receipt(req)
        result["source_revision"] = "b" * 40
        self.assertIn("receipt source revision does not match request", receipt_issues(req, result))

    def test_graduation_needs_exact_transfer_or_already_owned_proof(self) -> None:
        req = request("graduate-source")
        del req["source_transfer_receipt_ref"]
        self.assertTrue(list(schema("request").iter_errors(req)))
        req["already_owned_source_proof_ref"] = "already-owned:1"
        self.assertEqual(list(schema("request").iter_errors(req)), [])
        result = receipt(req)
        result["already_owned_source_proof_ref"] = req["already_owned_source_proof_ref"]
        self.assertEqual(list(schema("receipt").iter_errors(result)), [])

    def test_denial_preserves_state(self) -> None:
        req = request("graduate-source")
        result = receipt(req)
        result.update(outcome="denied", observed_lifecycle="graduated", finding_code="owner-missing", next_action="select-owner")
        self.assertIn("denied or failed closure cannot change lifecycle", receipt_issues(req, result))

    def test_history_binds_receipt_and_previous_event(self) -> None:
        req = request("retire-incubation")
        result = receipt(req)
        event = {
            "schema_version": 1,
            "artifact_type": "prototype-closure-history-event",
            "event_id": "closure-history:prototype-1:1",
            "prototype_id": req["prototype_id"],
            "event_type": "incubation-retired",
            "terminal_receipt_ref": result["receipt_id"],
            "terminal_receipt_digest": "sha256:" + "a" * 64,
            "prior_event_digest": None,
            "recorded_at": result["recorded_at"],
        }
        self.assertEqual(list(schema("history-event").iter_errors(event)), [])
        self.assertEqual(history_issues(result, event, prior_digest=None), [])
        self.assertIn("history does not bind previous event digest", history_issues(result, event, prior_digest="sha256:" + "b" * 64))


if __name__ == "__main__":
    unittest.main()
