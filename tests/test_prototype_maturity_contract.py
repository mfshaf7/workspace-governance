from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import unittest

from jsonschema import Draft202012Validator, FormatChecker
import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = REPO_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from prototype_maturity_contract import (  # noqa: E402
    artifact_chain_issues,
    contract_issues,
    decision_issues,
    packet_issues,
    readiness_issues,
)


DIGEST_A = "sha256:" + "a" * 64
DIGEST_B = "sha256:" + "b" * 64
DIGEST_C = "sha256:" + "c" * 64
NOW = "2026-09-08T18:00:00Z"
SCHEMAS = {
    "prototype-maturity-request": "prototype-maturity-request.schema.json",
    "prototype-maturity-packet": "prototype-maturity-packet.schema.json",
    "prototype-maturity-readiness": "prototype-maturity-readiness.schema.json",
    "prototype-maturity-decision": "prototype-maturity-decision.schema.json",
    "prototype-maturity-readback": "prototype-maturity-readback.schema.json",
    "prototype-maturity-receipt": "prototype-maturity-receipt.schema.json",
}
CHECKS = [
    "request-integrity",
    "lifecycle-source-state",
    "source-version-freshness",
    "packet-integrity",
    "required-evidence",
    "boundary-coherence",
    "security-trigger-disposition",
    "open-issue-disposition",
]


def ref(artifact_id: str, digest: str) -> dict[str, str]:
    return {"id": artifact_id, "digest": digest}


def valid_artifacts(transition: str = "candidate-promotion") -> dict[str, dict]:
    baseline = transition == "baseline-promotion"
    source = "candidate" if baseline else "exploring"
    target = "baseline-approved" if baseline else "candidate"
    decision_value = "approve-baseline" if baseline else "promote-candidate"
    packet_kind = "baseline-packet" if baseline else "candidate-evidence-packet"
    section_ids = (
        ["definition", "design-and-workflow", "evidence", "boundaries", "issues-and-risk-disposition"]
        if baseline
        else ["candidate-brief", "scope-and-non-goals", "boundaries-and-risks"]
    )
    suffix = "baseline" if baseline else "candidate"
    state = {"source_revision": "abc123", "record_digest": DIGEST_A, "lifecycle": source}
    request = {
        "schema_version": 1,
        "artifact_type": "prototype-maturity-request",
        "request_id": f"prototype-maturity-request:sample-{suffix}:1",
        "requested_at": NOW,
        "operator_ref": "operator:workspace-owner",
        "prototype_id": "prototype:sample",
        "transition": transition,
        "source_lifecycle": source,
        "target_lifecycle": target,
        "expected_state": state,
        "inputs": {
            "source_refs": ["record://prototype/sample"],
            "editable_values": {"statement": "A bounded and reviewable maturity decision."},
        },
        "correlation_id": f"prototype-maturity:sample:{suffix}:1",
        "idempotency_key": f"prototype-maturity:sample:{suffix}:1",
        "request_digest": DIGEST_A,
    }
    packet = {
        "schema_version": 1,
        "artifact_type": "prototype-maturity-packet",
        "packet_id": f"prototype-maturity-packet:sample-{suffix}:1",
        "assembled_at": NOW,
        "request_ref": ref(request["request_id"], DIGEST_A),
        "prototype_id": "prototype:sample",
        "transition": transition,
        "packet_kind": packet_kind,
        "sections": [
            {"id": section, "state": "ready", "evidence_refs": [f"proof://{section}"]}
            for section in section_ids
        ],
        "packet_digest": DIGEST_B,
    }
    readiness = {
        "schema_version": 1,
        "artifact_type": "prototype-maturity-readiness",
        "readiness_id": f"prototype-maturity-readiness:sample-{suffix}:1",
        "evaluated_at": NOW,
        "request_ref": ref(request["request_id"], DIGEST_A),
        "packet_ref": ref(packet["packet_id"], DIGEST_B),
        "prototype_id": "prototype:sample",
        "transition": transition,
        "observed_state": state,
        "outcome": "ready",
        "checks": [
            {"id": check, "state": "ready", "evidence_refs": [f"proof://{check}"]}
            for check in CHECKS
        ],
        "findings": [],
        "readiness_digest": DIGEST_C,
    }
    decision = {
        "schema_version": 1,
        "artifact_type": "prototype-maturity-decision",
        "decision_id": f"prototype-maturity-decision:sample-{suffix}:1",
        "decided_at": NOW,
        "request_ref": ref(request["request_id"], DIGEST_A),
        "packet_ref": ref(packet["packet_id"], DIGEST_B),
        "readiness_ref": ref(readiness["readiness_id"], DIGEST_C),
        "prototype_id": "prototype:sample",
        "transition": transition,
        "decision": decision_value,
        "operator_ref": "operator:workspace-owner",
        "expected_state": state,
        "source_branch": f"feature/sample-{suffix}-promotion",
        "blocker": None,
        "correlation_id": request["correlation_id"],
        "idempotency_key": request["idempotency_key"],
        "decision_digest": DIGEST_A,
    }
    readback = {
        "schema_version": 1,
        "artifact_type": "prototype-maturity-readback",
        "readback_id": f"prototype-maturity-readback:sample-{suffix}:1",
        "observed_at": NOW,
        "decision_ref": ref(decision["decision_id"], DIGEST_A),
        "prototype_id": "prototype:sample",
        "transition": transition,
        "decision": decision_value,
        "authority_state": "merged-authority",
        "source_revision": "def456",
        "record_digest": DIGEST_B,
        "observed_lifecycle": target,
        "record_ref": "record://prototype/sample",
        "readback_digest": DIGEST_B,
    }
    receipt = {
        "schema_version": 1,
        "artifact_type": "prototype-maturity-receipt",
        "receipt_id": f"prototype-maturity-receipt:sample-{suffix}:1",
        "completed_at": NOW,
        "request_ref": ref(request["request_id"], DIGEST_A),
        "packet_ref": ref(packet["packet_id"], DIGEST_B),
        "readiness_ref": ref(readiness["readiness_id"], DIGEST_C),
        "decision_ref": ref(decision["decision_id"], DIGEST_A),
        "readback_ref": ref(readback["readback_id"], DIGEST_B),
        "prototype_id": "prototype:sample",
        "transition": transition,
        "decision": decision_value,
        "outcome": "succeeded",
        "resulting_lifecycle": target,
        "next_action": {
            "code": "baseline-promotion" if not baseline else "continue-incubation-or-prepare-transition",
            "owner_ref": "workspace-prototype-studio",
        },
        "correlation_id": request["correlation_id"],
        "idempotency_key": request["idempotency_key"],
        "receipt_digest": DIGEST_C,
    }
    return {item["artifact_type"]: item for item in (request, packet, readiness, decision, readback, receipt)}


class PrototypeMaturityContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = yaml.safe_load((REPO_ROOT / "contracts/prototype-maturity.yaml").read_text())

    def validate_artifact(self, artifact: dict) -> list[str]:
        schema = json.loads((REPO_ROOT / "contracts/schemas" / SCHEMAS[artifact["artifact_type"]]).read_text())
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        return [error.message for error in validator.iter_errors(artifact)]

    def test_contract_and_both_transition_chains_are_valid(self) -> None:
        known_repos = {
            value["owner_repo"]
            for value in self.contract["scope_boundaries"].values()
            if "owner_repo" in value
        }
        self.assertEqual(contract_issues(self.contract, known_repos=known_repos), [])
        for transition in ("candidate-promotion", "baseline-promotion"):
            artifacts = valid_artifacts(transition)
            for artifact in artifacts.values():
                self.assertEqual(self.validate_artifact(artifact), [], artifact["artifact_type"])
            self.assertEqual(artifact_chain_issues(artifacts), [])

    def test_candidate_packet_requires_exact_sections(self) -> None:
        packet = valid_artifacts()["prototype-maturity-packet"]
        packet["sections"].pop()
        self.assertIn(
            "candidate-promotion packet must contain every required section exactly once",
            packet_issues(packet),
        )

    def test_ready_outcome_rejects_non_ready_check(self) -> None:
        readiness = valid_artifacts()["prototype-maturity-readiness"]
        readiness["checks"][0]["state"] = "blocked"
        self.assertIn(
            "ready outcome requires every maturity check to be ready",
            readiness_issues(readiness),
        )

    def test_block_decision_requires_visible_owned_fix(self) -> None:
        decision = valid_artifacts()["prototype-maturity-decision"]
        decision["decision"] = "block-promotion"
        self.assertTrue(self.validate_artifact(decision))
        self.assertIn(
            "a block decision requires an issue ref, owner, and required fix",
            decision_issues(decision),
        )

    def test_promotion_is_denied_when_readiness_is_blocked(self) -> None:
        artifacts = valid_artifacts()
        readiness = artifacts["prototype-maturity-readiness"]
        readiness["outcome"] = "blocked"
        readiness["checks"][0]["state"] = "blocked"
        self.assertIn(
            "promote and approve decisions require ready maturity evidence",
            artifact_chain_issues(artifacts),
        )

    def test_success_requires_merged_target_readback(self) -> None:
        artifacts = valid_artifacts("baseline-promotion")
        artifacts["prototype-maturity-readback"]["observed_lifecycle"] = "candidate"
        self.assertIn(
            "successful promotion requires merged readback at the target lifecycle",
            artifact_chain_issues(artifacts),
        )

    def test_route_closeout_preserves_current_lifecycle(self) -> None:
        artifacts = valid_artifacts()
        decision = artifacts["prototype-maturity-decision"]
        readback = artifacts["prototype-maturity-readback"]
        receipt = artifacts["prototype-maturity-receipt"]
        decision["decision"] = "route-closeout"
        readback.update({
            "decision": "route-closeout",
            "authority_state": "unchanged-authority",
            "source_revision": decision["expected_state"]["source_revision"],
            "record_digest": decision["expected_state"]["record_digest"],
            "observed_lifecycle": "exploring",
        })
        receipt.update({
            "decision": "route-closeout",
            "outcome": "routed-closeout",
            "resulting_lifecycle": "exploring",
            "next_action": {"code": "prototype-closeout", "owner_ref": "workspace-prototype-studio"},
        })
        self.assertEqual(artifact_chain_issues(artifacts), [])

    def test_baseline_approval_does_not_claim_cross_domain_authority(self) -> None:
        boundary = self.contract["approval_boundary"]
        self.assertIn("local-design-accepted", boundary["baseline_approved_means"])
        self.assertEqual(
            set(boundary["baseline_approved_does_not_mean"]),
            {
                "delivery-admitted",
                "delivery-art-created",
                "source-graduated",
                "runtime-admitted",
                "release-approved",
                "security-accepted",
                "client-exposed",
                "portfolio-published",
            },
        )


if __name__ == "__main__":
    unittest.main()
