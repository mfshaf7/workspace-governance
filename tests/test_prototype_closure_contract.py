from __future__ import annotations

import json
import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from jsonschema import Draft202012Validator, FormatChecker
import yaml


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from prototype_closure_contract import contract_issues, history_issues, receipt_issues  # noqa: E402


REQUEST_DIGEST = "sha256:" + "a" * 64
EVENT_DIGEST = "sha256:" + "b" * 64
READBACK_DIGEST = "sha256:" + "c" * 64


def schema(name: str) -> Draft202012Validator:
    path = ROOT / "contracts/schemas" / f"prototype-closure-{name}.schema.json"
    return Draft202012Validator(json.loads(path.read_text()), format_checker=FormatChecker())


def request(action: str) -> dict:
    values = {
        "schema_version": 2,
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
        values.update(accepted_baseline_receipt_ref="baseline:1", target_kind="new-delivery-epic")
    elif action == "graduate-source":
        values.update(accepted_delivery_target_receipt_ref="delivery:1", durable_owner_ref="owner:1", durable_repo_ref="repo:1", durable_owner_acceptance_ref="owner-accepted:1", transfer_strategy="transfer")
    elif action == "retire-incubation":
        values.update(retirement_reason="not-viable", retention_plan_ref="retention:1", runtime_disposition_plan_ref="runtime-plan:1")
    else:
        values["prior_retirement_receipt_ref"] = "retirement:1"
    return values


def source_event(req: dict) -> dict:
    action = req["action"]
    values = {
        "schema_version": 2,
        "artifact_type": "prototype-closure-history-event",
        "event_id": "closure-history:prototype-1:1",
        "request_ref": req["request_id"],
        "request_digest": REQUEST_DIGEST,
        "prototype_id": req["prototype_id"],
        "event_type": {
            "apply-delivery": "delivery-accepted",
            "graduate-source": "source-graduated",
            "retire-incubation": "incubation-retired",
            "reopen-incubation": "incubation-reopened",
        }[action],
        "expected_source_revision": req["expected_source_revision"],
        "previous_lifecycle": req["expected_lifecycle"],
        "observed_lifecycle": {
            "apply-delivery": "graduating",
            "graduate-source": "graduated",
            "retire-incubation": "retired",
            "reopen-incubation": "exploring",
        }[action],
        "previous_source_custody": "incubation-repo",
        "observed_source_custody": "dedicated-owner-repo" if action == "graduate-source" else "incubation-repo",
        "operator_id": req["operator_id"],
        "correlation_id": req["correlation_id"],
        "idempotency_key": req["idempotency_key"],
        "prior_event_digest": None,
        "recorded_at": "2026-09-12T03:20:00Z",
    }
    if action == "apply-delivery":
        values.update(accepted_baseline_receipt_ref=req["accepted_baseline_receipt_ref"], accepted_delivery_target_receipt_ref="delivery:1")
    elif action == "graduate-source":
        values.update(accepted_delivery_target_receipt_ref=req["accepted_delivery_target_receipt_ref"], durable_owner_acceptance_ref=req["durable_owner_acceptance_ref"])
        if req["transfer_strategy"] == "transfer":
            values["source_transfer_receipt_ref"] = "transfer:1"
        else:
            values["already_owned_source_proof_ref"] = req["already_owned_source_proof_ref"]
    elif action == "retire-incubation":
        values.update(retention_plan_ref=req["retention_plan_ref"], runtime_disposition_proof_ref="runtime-disposition:1")
    else:
        values.update(prior_retirement_receipt_ref=req["prior_retirement_receipt_ref"], retained_source_readback_ref="retained-source:1")
    return values


def studio_readback(event: dict) -> dict:
    return {
        "schema_version": 2,
        "artifact_type": "prototype-closure-studio-readback",
        "readback_id": "studio-readback:1",
        "prototype_id": event["prototype_id"],
        "source_event_ref": event["event_id"],
        "source_event_digest": EVENT_DIGEST,
        "merged_source_revision": "b" * 40,
        "observed_lifecycle": event["observed_lifecycle"],
        "observed_source_custody": event["observed_source_custody"],
        "observed_at": "2026-09-12T03:25:00Z",
    }


def receipt(req: dict) -> dict:
    event = source_event(req)
    readback = studio_readback(event)
    values = {
        "schema_version": 2,
        "artifact_type": "prototype-closure-receipt",
        "receipt_id": "closure-receipt:prototype-1:1",
        "request_ref": req["request_id"],
        "request_digest": REQUEST_DIGEST,
        "prototype_id": req["prototype_id"],
        "action": req["action"],
        "outcome": "completed",
        "previous_lifecycle": req["expected_lifecycle"],
        "observed_lifecycle": event["observed_lifecycle"],
        "previous_source_custody": event["previous_source_custody"],
        "observed_source_custody": event["observed_source_custody"],
        "source_revision": req["expected_source_revision"],
        "merged_source_revision": readback["merged_source_revision"],
        "operator_id": req["operator_id"],
        "correlation_id": req["correlation_id"],
        "idempotency_key": req["idempotency_key"],
        "recorded_at": "2026-09-12T03:30:00Z",
        "evidence_refs": ["evidence:1"],
        "source_event_ref": event["event_id"],
        "source_event_digest": EVENT_DIGEST,
        "merged_studio_readback_ref": readback["readback_id"],
        "merged_studio_readback_digest": READBACK_DIGEST,
    }
    for field in ("accepted_delivery_target_receipt_ref", "durable_owner_acceptance_ref", "source_transfer_receipt_ref", "already_owned_source_proof_ref", "prior_retirement_receipt_ref"):
        if field in event:
            values[field] = event[field]
    return values


def receipt_chain_issues(req: dict, result: dict, *, event: dict | None = None, readback: dict | None = None) -> list[str]:
    source = source_event(req) if event is None else event
    merged = studio_readback(source) if readback is None else readback
    return receipt_issues(req, result, request_digest=REQUEST_DIGEST, event=source, event_digest=EVENT_DIGEST, readback=merged, readback_digest=READBACK_DIGEST)


class PrototypeClosureContractTests(unittest.TestCase):
    def test_real_git_event_merge_readback_receipt_order(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)

            def git(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
                return subprocess.run(["git", *args], cwd=repo, text=True, capture_output=True, check=check)

            git("init", "-b", "main")
            git("config", "user.name", "Closure Contract Test")
            git("config", "user.email", "closure-test@example.invalid")
            (repo / "prototype.json").write_text('{"lifecycle":"baseline-approved"}\n')
            git("add", "prototype.json")
            git("commit", "-m", "Initial prototype state")
            base = git("rev-parse", "HEAD").stdout.strip()

            req = request("apply-delivery")
            req["expected_source_revision"] = base
            request_digest = "sha256:" + hashlib.sha256(json.dumps(req, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            event = source_event(req)
            event["request_digest"] = request_digest
            event_digest = "sha256:" + hashlib.sha256(json.dumps(event, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            git("checkout", "-b", "review")
            (repo / "closure-event.json").write_text(json.dumps(event, sort_keys=True) + "\n")
            git("add", "closure-event.json")
            git("commit", "-m", "Record accepted Closure source event")
            reviewed_head = git("rev-parse", "HEAD").stdout.strip()

            self.assertNotEqual(git("show", "main:closure-event.json", check=False).returncode, 0)
            self.assertIn(
                "completed closure requires source event and merged readback evidence",
                receipt_issues(req, receipt(req), request_digest=request_digest),
            )
            stale_event = {**event, "expected_source_revision": "f" * 40}
            self.assertIn(
                "history source revision does not match request",
                history_issues(req, stale_event, request_digest=request_digest, prior_digest=None),
            )

            git("checkout", "main")
            git("merge", "--no-ff", "review", "-m", "Merge accepted Closure event")
            merged_head = git("rev-parse", "HEAD").stdout.strip()
            self.assertEqual(git("merge-base", "--is-ancestor", reviewed_head, merged_head).returncode, 0)
            self.assertEqual(json.loads(git("show", "HEAD:closure-event.json").stdout), event)

            readback = studio_readback(event)
            readback["source_event_digest"] = event_digest
            readback["merged_source_revision"] = merged_head
            readback_digest = "sha256:" + hashlib.sha256(json.dumps(readback, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            result = receipt(req)
            result.update(
                request_digest=request_digest,
                source_event_digest=event_digest,
                merged_studio_readback_digest=readback_digest,
                merged_source_revision=merged_head,
            )
            self.assertEqual(list(schema("studio-readback").iter_errors(readback)), [])
            self.assertEqual(
                receipt_issues(
                    req, result, request_digest=request_digest,
                    event=event, event_digest=event_digest,
                    readback=readback, readback_digest=readback_digest,
                ),
                [],
            )

    def test_contract_owner_and_exit_boundaries(self) -> None:
        contract = yaml.safe_load((ROOT / "contracts/prototype-closure.yaml").read_text())
        known = set(contract["authority"].values()) | {"workspace-governance"}
        self.assertEqual(contract_issues(contract, known_repos=known), [])
        contract["target_routes"]["portfolio"]["maturity"] = "active"
        self.assertIn("Portfolio cannot be a direct Prototype exit", contract_issues(contract, known_repos=known))

    def test_each_action_has_acyclic_typed_evidence(self) -> None:
        for action in ("apply-delivery", "graduate-source", "retire-incubation", "reopen-incubation"):
            with self.subTest(action=action):
                req = request(action)
                event = source_event(req)
                readback = studio_readback(event)
                result = receipt(req)
                for name, artifact in (("request", req), ("history-event", event), ("studio-readback", readback), ("receipt", result)):
                    self.assertEqual(list(schema(name).iter_errors(artifact)), [], name)
                self.assertEqual(history_issues(req, event, request_digest=REQUEST_DIGEST, prior_digest=None), [])
                self.assertEqual(receipt_chain_issues(req, result), [])

    def test_delivery_acceptance_cannot_graduate_source(self) -> None:
        req = request("apply-delivery")
        event = source_event(req)
        event["observed_source_custody"] = "dedicated-owner-repo"
        self.assertTrue(list(schema("history-event").iter_errors(event)))
        self.assertIn("Delivery history cannot graduate source", history_issues(req, event, request_digest=REQUEST_DIGEST, prior_digest=None))

    def test_delivery_request_cannot_claim_its_future_target_receipt(self) -> None:
        req = request("apply-delivery")
        req["accepted_delivery_target_receipt_ref"] = "delivery:1"
        self.assertTrue(list(schema("request").iter_errors(req)))

    def test_transfer_receipt_is_output_not_request_input(self) -> None:
        req = request("graduate-source")
        req["transfer_strategy"] = "already-owned"
        self.assertTrue(list(schema("request").iter_errors(req)))
        req["already_owned_source_proof_ref"] = "already-owned:1"
        self.assertEqual(list(schema("request").iter_errors(req)), [])
        event = source_event(req)
        self.assertEqual(list(schema("history-event").iter_errors(event)), [])
        result = receipt(req)
        self.assertEqual(receipt_chain_issues(req, result), [])

    def test_completed_receipt_requires_both_merged_proofs(self) -> None:
        req = request("apply-delivery")
        result = receipt(req)
        del result["source_event_digest"]
        self.assertTrue(list(schema("receipt").iter_errors(result)))
        result = receipt(req)
        del result["merged_studio_readback_ref"]
        self.assertTrue(list(schema("receipt").iter_errors(result)))
        self.assertIn("completed closure requires source event and merged readback evidence", receipt_issues(req, receipt(req), request_digest=REQUEST_DIGEST))

    def test_stale_request_or_source_digest_is_rejected(self) -> None:
        req = request("apply-delivery")
        result = receipt(req)
        result["source_revision"] = "b" * 40
        self.assertIn("receipt source revision does not match request", receipt_chain_issues(req, result))
        result = receipt(req)
        result["source_event_digest"] = READBACK_DIGEST
        self.assertIn("receipt does not bind exact Studio source event", receipt_chain_issues(req, result))
        event = source_event(req)
        event["request_digest"] = EVENT_DIGEST
        self.assertIn("history does not bind exact request", history_issues(req, event, request_digest=REQUEST_DIGEST, prior_digest=None))

    def test_readback_must_bind_event_and_observed_state(self) -> None:
        req = request("retire-incubation")
        result = receipt(req)
        readback = studio_readback(source_event(req))
        readback["source_event_digest"] = REQUEST_DIGEST
        self.assertIn("merged Studio readback does not bind source event", receipt_chain_issues(req, result, readback=readback))
        readback = studio_readback(source_event(req))
        readback["observed_lifecycle"] = "exploring"
        self.assertIn("receipt observed_lifecycle does not match source event and readback", receipt_chain_issues(req, result, readback=readback))
        event = source_event(req)
        event["event_type"] = "delivery-accepted"
        self.assertIn("history event type does not match request action", receipt_chain_issues(req, result, event=event))
        readback = studio_readback(source_event(req))
        readback["observed_at"] = "2026-09-12T03:10:00Z"
        self.assertIn("source event, merged readback, and terminal receipt are out of order", receipt_chain_issues(req, result, readback=readback))
        readback = studio_readback(source_event(req))
        readback["merged_source_revision"] = req["expected_source_revision"]
        self.assertIn("merged Studio readback must advance source revision", receipt_chain_issues(req, result, readback=readback))

    def test_denial_preserves_source_and_has_no_history_event(self) -> None:
        req = request("graduate-source")
        result = receipt(req)
        for field in ("source_event_ref", "source_event_digest", "merged_studio_readback_ref", "merged_studio_readback_digest", "merged_source_revision"):
            del result[field]
        result.update(outcome="denied", observed_lifecycle=result["previous_lifecycle"], observed_source_custody=result["previous_source_custody"], finding_code="owner-missing", next_action="select-owner")
        self.assertEqual(list(schema("receipt").iter_errors(result)), [])
        self.assertEqual(receipt_issues(req, result, request_digest=REQUEST_DIGEST), [])
        result["observed_lifecycle"] = "graduated"
        self.assertIn("denied or failed closure cannot change lifecycle", receipt_issues(req, result, request_digest=REQUEST_DIGEST))
        result["source_event_ref"] = "closure-history:prototype-1:1"
        self.assertTrue(list(schema("receipt").iter_errors(result)))

    def test_terminal_failure_is_pre_merge_only(self) -> None:
        req = request("retire-incubation")
        result = receipt(req)
        for field in ("source_event_ref", "source_event_digest", "merged_studio_readback_ref", "merged_studio_readback_digest", "merged_source_revision"):
            del result[field]
        result.update(outcome="failed", observed_lifecycle=result["previous_lifecycle"], finding_code="merge-not-started", next_action="retry", failure_stage="pre-merge")
        self.assertEqual(list(schema("receipt").iter_errors(result)), [])
        self.assertEqual(receipt_issues(req, result, request_digest=REQUEST_DIGEST), [])
        del result["failure_stage"]
        self.assertTrue(list(schema("receipt").iter_errors(result)))
        self.assertIn("terminal failure must be pre-merge", receipt_issues(req, result, request_digest=REQUEST_DIGEST))

    def test_history_never_binds_future_receipt(self) -> None:
        req = request("retire-incubation")
        event = source_event(req)
        event["terminal_receipt_ref"] = "future:1"
        self.assertTrue(list(schema("history-event").iter_errors(event)))
        self.assertIn("source event cannot bind future terminal receipt", history_issues(req, event, request_digest=REQUEST_DIGEST, prior_digest=None))
        del event["terminal_receipt_ref"]
        self.assertIn("history does not bind previous event digest", history_issues(req, event, request_digest=REQUEST_DIGEST, prior_digest=EVENT_DIGEST))


if __name__ == "__main__":
    unittest.main()
