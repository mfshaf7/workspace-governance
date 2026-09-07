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

from prototype_landing_contract import (  # noqa: E402
    artifact_chain_issues,
    contract_issues,
    readiness_issues,
    request_issues,
)


DIGEST_A = "sha256:" + "a" * 64
DIGEST_B = "sha256:" + "b" * 64
DIGEST_C = "sha256:" + "c" * 64
NOW = "2026-09-07T05:00:00Z"
SCHEMA_BY_ARTIFACT = {
    "prototype-entry-packet": "prototype-landing-entry-packet.schema.json",
    "prototype-landing-request": "prototype-landing-request.schema.json",
    "prototype-landing-plan": "prototype-landing-plan.schema.json",
    "prototype-landing-readiness": "prototype-landing-readiness.schema.json",
    "prototype-landing-apply": "prototype-landing-apply.schema.json",
    "prototype-landing-readback": "prototype-landing-readback.schema.json",
    "prototype-landing-receipt": "prototype-landing-receipt.schema.json",
}
SUPPORT_DIMENSIONS = [
    "source",
    "studio-home",
    "interface",
    "runtime",
    "data",
    "integration",
    "tooling",
    "evidence",
    "visibility",
    "recovery",
]
READINESS_CHECKS = [
    "entry-integrity",
    "identity-availability",
    "required-metadata",
    "support-profile-integrity",
    "support-row-readiness",
    "source-custody-coherence",
    "source-version-freshness",
    "data-and-mutation-boundary",
    "visibility-and-exposure",
    "security-trigger-disposition",
    "expected-mutation-set",
]


def ref(artifact_id: str, digest: str = DIGEST_A) -> dict[str, str]:
    return {"id": artifact_id, "digest": digest}


def valid_artifacts() -> dict[str, dict]:
    entry = {
        "schema_version": 1,
        "artifact_type": "prototype-entry-packet",
        "entry_id": "prototype-entry:proposal-routed:proposal-42",
        "captured_at": NOW,
        "ingress_class": "proposal-routed",
        "source": {
            "authority": "workspace-proposals",
            "ref": "openproject://work_packages/42",
            "digest": DIGEST_A,
            "revision": "42:3",
        },
        "suggestions": {
            "name": "Initial name",
            "objective": "Prove a bounded operator workflow.",
            "support_profile": "interactive",
        },
        "constraints": [
            {"code": "mock-data-only", "detail": "Use only mock or synthetic data."}
        ],
        "requested_by": "operator:workspace-owner",
        "packet_digest": DIGEST_A,
    }
    request = {
        "schema_version": 1,
        "artifact_type": "prototype-landing-request",
        "request_id": "prototype-landing-request:sample:1",
        "requested_at": NOW,
        "operator_ref": "operator:workspace-owner",
        "entry_packet_ref": ref(entry["entry_id"], DIGEST_A),
        "prototype": {
            "id": "prototype:sample",
            "name": "Renamed prototype",
            "objective": "Prove a bounded operator workflow.",
        },
        "setup": {
            "support_profile": "interactive",
            "support_rows": [
                {"dimension": dimension, "state": "ready", "generated": True, "detail": f"{dimension} is resolved"}
                for dimension in SUPPORT_DIMENSIONS
            ],
            "scaffold_profile": "vite-react",
            "preview_mode": "local-dev-server",
            "data_mode": "synthetic",
            "mutation_boundary": "local-only",
            "visibility": "operator-review",
        },
        "source_plan": {
            "posture": "create-studio-source",
            "source_ref": "docs/prototypes/sample",
            "source_revision": None,
            "origin_digest": None,
            "imported_content_digest": None,
        },
        "starting_lifecycle": "exploring",
        "expected_state": {
            "registry_digest": DIGEST_A,
            "record_present": False,
            "record_digest": None,
            "source_revision": None,
        },
        "operator_accepted": True,
        "correlation_id": "prototype-landing:sample:1",
        "idempotency_key": "prototype-landing:sample:1",
        "request_digest": DIGEST_B,
    }
    plan = {
        "schema_version": 1,
        "artifact_type": "prototype-landing-plan",
        "plan_id": "prototype-landing-plan:sample:1",
        "planned_at": NOW,
        "request_ref": ref(request["request_id"], DIGEST_B),
        "prototype_id": "prototype:sample",
        "source_plan": request["source_plan"],
        "mutation_set": ["registry-record", "prototype-docs", "prototype-source", "validation-plan"],
        "expected_outputs": [
            {"kind": "registry-record", "target_ref": "prototypes.yaml#sample", "required": True},
            {"kind": "prototype-docs", "target_ref": "docs/prototypes/sample", "required": True},
            {"kind": "prototype-source", "target_ref": "docs/prototypes/sample", "required": True},
            {"kind": "validation-plan", "target_ref": "validation://prototype/sample", "required": True},
        ],
        "next_action": "candidate-promotion",
        "plan_digest": DIGEST_C,
    }
    readiness = {
        "schema_version": 1,
        "artifact_type": "prototype-landing-readiness",
        "readiness_id": "prototype-landing-readiness:sample:1",
        "evaluated_at": NOW,
        "request_ref": ref(request["request_id"], DIGEST_B),
        "plan_ref": ref(plan["plan_id"], DIGEST_C),
        "observed_state": {"registry_digest": DIGEST_A, "record_present": False, "source_revision": None},
        "outcome": "ready",
        "checks": [{"id": check, "state": "ready", "evidence_refs": [f"proof://{check}"]} for check in READINESS_CHECKS],
        "findings": [],
        "security_trigger_refs": [],
        "readiness_digest": DIGEST_A,
    }
    apply = {
        "schema_version": 1,
        "artifact_type": "prototype-landing-apply",
        "apply_id": "prototype-landing-apply:sample:1",
        "requested_at": NOW,
        "request_ref": ref(request["request_id"], DIGEST_B),
        "plan_ref": ref(plan["plan_id"], DIGEST_C),
        "readiness_ref": ref(readiness["readiness_id"], DIGEST_A),
        "prototype_id": "prototype:sample",
        "expected_state": readiness["observed_state"],
        "operator_approval_ref": "approval://prototype-landing/sample/1",
        "source_branch": "feature/prototype-sample",
        "correlation_id": request["correlation_id"],
        "idempotency_key": request["idempotency_key"],
        "apply_digest": DIGEST_B,
    }
    readback = {
        "schema_version": 1,
        "artifact_type": "prototype-landing-readback",
        "readback_id": "prototype-landing-readback:sample:1",
        "apply_ref": ref(apply["apply_id"], DIGEST_B),
        "prototype_id": "prototype:sample",
        "authority_state": "merged-authority",
        "source_branch": "main",
        "source_revision": "abc123",
        "registry_digest": DIGEST_B,
        "record_digest": DIGEST_C,
        "record": {
            "id": "prototype:sample",
            "entry_ref": ref(entry["entry_id"], DIGEST_A),
            "name": "Renamed prototype",
            "objective": "Prove a bounded operator workflow.",
            "ingress_class": "proposal-routed",
            "lifecycle": "exploring",
            "project_phase": "incubating",
            "setup": request["setup"],
            "source": {
                "posture": "create-studio-source",
                "custody": "incubation-repo",
                "ref": "docs/prototypes/sample",
                "revision": "abc123",
            },
            "next_action": "candidate-promotion",
        },
        "observed_at": NOW,
        "readback_digest": DIGEST_C,
    }
    receipt = {
        "schema_version": 1,
        "artifact_type": "prototype-landing-receipt",
        "receipt_id": "prototype-landing-receipt:sample:1",
        "completed_at": NOW,
        "entry_packet_ref": ref(entry["entry_id"], DIGEST_A),
        "request_ref": ref(request["request_id"], DIGEST_B),
        "plan_ref": ref(plan["plan_id"], DIGEST_C),
        "readiness_ref": ref(readiness["readiness_id"], DIGEST_A),
        "apply_ref": ref(apply["apply_id"], DIGEST_B),
        "readback_ref": ref(readback["readback_id"], DIGEST_C),
        "prototype_id": "prototype:sample",
        "phase": "merged-authority",
        "outcome": "succeeded",
        "source_result": {"repo": "workspace-prototype-studio", "branch": "main", "revision": "abc123", "registry_digest": DIGEST_B, "record_digest": DIGEST_C},
        "next_action": {"code": "candidate-promotion", "owner_ref": "workspace-prototype-studio"},
        "correlation_id": request["correlation_id"],
        "idempotency_key": request["idempotency_key"],
        "receipt_digest": DIGEST_A,
    }
    return {item["artifact_type"]: item for item in (entry, request, plan, readiness, apply, readback, receipt)}


class PrototypeLandingContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = yaml.safe_load((REPO_ROOT / "contracts/prototype-landing.yaml").read_text())
        self.artifacts = valid_artifacts()

    def validate_artifact(self, artifact: dict) -> list[str]:
        schema = json.loads((REPO_ROOT / "contracts/schemas" / SCHEMA_BY_ARTIFACT[artifact["artifact_type"]]).read_text())
        return [error.message for error in Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(artifact)]

    def test_contract_and_complete_artifact_chain_are_valid(self) -> None:
        known_repos = {
            value["owner_repo"]
            for value in self.contract["scope_boundaries"].values()
            if "owner_repo" in value
        }
        self.assertEqual(contract_issues(self.contract, known_repos=known_repos), [])
        for artifact in self.artifacts.values():
            self.assertEqual(self.validate_artifact(artifact), [], artifact["artifact_type"])
        self.assertEqual(artifact_chain_issues(self.artifacts), [])

    def test_upstream_name_is_editable_without_changing_identity(self) -> None:
        entry = self.artifacts["prototype-entry-packet"]
        request = self.artifacts["prototype-landing-request"]
        self.assertNotEqual(entry["suggestions"]["name"], request["prototype"]["name"])
        self.assertEqual(request["prototype"]["id"], "prototype:sample")

    def test_duplicate_support_dimension_is_rejected(self) -> None:
        request = copy.deepcopy(self.artifacts["prototype-landing-request"])
        request["setup"]["support_rows"][-1]["dimension"] = "source"
        self.assertIn("support rows must contain each dimension exactly once", request_issues(request))

    def test_named_profile_cannot_claim_operator_defined_rows(self) -> None:
        request = copy.deepcopy(self.artifacts["prototype-landing-request"])
        request["setup"]["support_rows"][0]["generated"] = False
        self.assertTrue(self.validate_artifact(request))
        self.assertIn("interactive support rows must all be generated", request_issues(request))

    def test_import_requires_both_content_digests(self) -> None:
        request = copy.deepcopy(self.artifacts["prototype-landing-request"])
        request["source_plan"]["posture"] = "import-to-studio"
        self.assertIn("import-to-studio requires origin and imported content digests", request_issues(request))

    def test_ready_outcome_rejects_a_blocked_check(self) -> None:
        readiness = copy.deepcopy(self.artifacts["prototype-landing-readiness"])
        readiness["checks"][0]["state"] = "blocked"
        self.assertIn("ready outcome requires every check to be ready", readiness_issues(readiness))

    def test_blocked_readiness_can_report_an_identity_collision(self) -> None:
        readiness = copy.deepcopy(self.artifacts["prototype-landing-readiness"])
        readiness["observed_state"]["record_present"] = True
        readiness["outcome"] = "blocked"
        readiness["checks"][1]["state"] = "blocked"
        readiness["findings"] = [{
            "code": "prototype-identity-unavailable",
            "severity": "blocking",
            "message": "The Prototype identity already exists.",
            "owner_ref": "workspace-prototype-studio",
            "next_action": "Choose another stable identity.",
        }]

        self.assertEqual(self.validate_artifact(readiness), [])
        self.assertEqual(readiness_issues(readiness), [])

    def test_apply_is_rejected_when_readiness_is_not_ready(self) -> None:
        artifacts = copy.deepcopy(self.artifacts)
        artifacts["prototype-landing-readiness"]["outcome"] = "blocked"
        artifacts["prototype-landing-readiness"]["checks"][0]["state"] = "blocked"
        self.assertIn("apply requires a ready readiness outcome", artifact_chain_issues(artifacts))

    def test_cross_artifact_digest_drift_is_rejected(self) -> None:
        artifacts = copy.deepcopy(self.artifacts)
        artifacts["prototype-landing-plan"]["request_ref"]["digest"] = DIGEST_C
        self.assertIn(
            "plan request must bind the exact artifact id and digest",
            artifact_chain_issues(artifacts),
        )

    def test_readback_custody_must_match_source_plan(self) -> None:
        artifacts = copy.deepcopy(self.artifacts)
        artifacts["prototype-landing-readback"]["record"]["source"]["custody"] = "shared-owner-repo"
        self.assertIn(
            "readback source must match the accepted source plan and custody mapping",
            artifact_chain_issues(artifacts),
        )

    def test_success_is_rejected_before_merged_readback(self) -> None:
        artifacts = copy.deepcopy(self.artifacts)
        artifacts["prototype-landing-readback"]["authority_state"] = "review-branch"
        artifacts["prototype-landing-readback"]["source_branch"] = "feature/prototype-sample"
        self.assertIn("succeeded receipt requires merged-authority readback", artifact_chain_issues(artifacts))

    def test_reference_only_source_cannot_claim_incubation_custody(self) -> None:
        contract = copy.deepcopy(self.contract)
        contract["source_custody"]["postures"]["reference-dedicated-owner-source"]["resulting_axis_state"] = "incubation-repo"
        known_repos = {
            value["owner_repo"]
            for value in contract["scope_boundaries"].values()
            if "owner_repo" in value
        }
        self.assertTrue(any("reference-only source" in issue for issue in contract_issues(contract, known_repos=known_repos)))


if __name__ == "__main__":
    unittest.main()
