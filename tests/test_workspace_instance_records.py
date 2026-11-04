from __future__ import annotations

import copy
from datetime import datetime, timezone
from pathlib import Path
import sys
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from workspace_intake import artifact_digest, canonical_digest, bind_artifact_digest
from workspace_instance_records import InstancePolicyError, instance_policy_ref, plan_repository_intake


class InstanceRepositoryPolicyTests(TestCase):
    def request(self, *, classification="proposed", action="add", current=None):
        value = {"schema_version": 1, "artifact_type": "instance-repository-intake-request", "instance_id": "installation-a", "custody_request_id": "synthetic-custody",
                 "request_id": f"private-request:{action}:{classification}", "requested_at": "2026-11-04T00:00:00Z",
                 "requester_ref": "operator:test", "source": {"class": "repository-custody",
                 "ref": "oos://repository-custody/requests/synthetic-custody/intake/" + "b" * 64,
                 "digest": "sha256:" + "c" * 64},
                 "target": {"kind": "repo", "name": "synthetic-project", "record_id": "repo:synthetic-project"},
                 "action": action, "requested_classification": classification, "owner_route": "synthetic-project",
                 "requested_record": {"kind": "repo", "repo_class": "product-source", "requires_security_bindings": False,
                                      "security_owner": None, "notes": "Synthetic private policy test, no client data",
                                      "provider_repository": {"provider": "github", "provider_repository_id": "123", "full_name": "example-org/synthetic-project"},
                                      "validation_behavior": {"posture": "covered-by-owner-repo", "wgcf_graph_role": "product-runtime-source",
                                                              "catalog_refs": [], "notes": "Actual owner source controls, no runtime authority."}},
                 "expected_state": {"record_version": current["receipt"]["version"] if current else None,
                                    "record_digest": current["receipt"]["record_digest"] if current else None},
                 "idempotency_key": f"synthetic:{action}:{classification}", "policy_ref": instance_policy_ref(ROOT, "a" * 40)}
        value["request_digest"] = artifact_digest(value, "request_digest")
        return value

    def decision(self, request):
        return bind_artifact_digest({"schema_version": 2, "artifact_type": "workspace-intake-decision",
                                    "decision_id": "synthetic-decision", "decided_at": "2026-11-04T00:01:00Z",
                                    "request_ref": {"id": request["request_id"], "digest": request["request_digest"]},
                                    "target": copy.deepcopy(request["target"]), "decision_source": "operator",
                                    "operator_acceptance": {"state": "accepted", "operator_ref": "operator:test", "recorded_at": "2026-11-04T00:01:00Z"},
                                    "outcome": {"status": "allowed", "classification": request["requested_classification"],
                                                "owner_route": request["owner_route"], "approved_record": copy.deepcopy(request["requested_record"]), "findings": []}})

    def plan(self, request=None, *, decision=None, **kwargs):
        request = request or self.request()
        return plan_repository_intake(policy_root=ROOT, policy_revision="a" * 40, instance_id="installation-a", request=request,
                                      decision=decision or self.decision(request), operator_ref="operator:test",
                                      current=kwargs.pop("current", None), legacy_records=kwargs.pop("legacy_records", {}),
                                      now=datetime(2026, 11, 4, 0, 2, tzinfo=timezone.utc), **kwargs)

    def current(self):
        value = self.plan()["record"]
        return {"record": value, "receipt": {"record_id": "repo:synthetic-project", "version": 1, "record_digest": canonical_digest(value)}}

    def test_proposed_registration_reuses_domain_envelope_without_git_or_runtime_claim(self):
        plan = self.plan()
        self.assertEqual(plan["record"]["phase"], "intake")
        self.assertEqual(plan["record"]["status"], "proposed")
        self.assertEqual(plan["record"]["record"]["version"], 1)
        self.assertTrue(plan["record"]["record"]["last_mutation"]["request_ref"].startswith("instance-repository-intake-request:"))
        self.assertFalse(plan["readiness"]["canonical_mutation"])
        self.assertNotIn("merge_commit", plan)
        self.assertNotIn("register_digest", plan["readiness"]["expected_state"])

    def test_reviewed_metadata_update_preserves_original_custody_source(self):
        current = self.current()
        request = self.request(action="update", current=current)
        request["requested_record"]["notes"] = "Updated reviewed project purpose"
        request["request_digest"] = artifact_digest(request, "request_digest")
        plan = self.plan(request, current=current)
        self.assertEqual(plan["record"]["record"]["version"], 2)
        self.assertEqual(plan["record"]["record"]["source"], current["record"]["record"]["source"])

    def test_stale_state_rebound_source_and_inventory_replacement_are_denied(self):
        current = self.current()
        request = self.request(action="update", current=current)
        changed = copy.deepcopy(request)
        changed["expected_state"]["record_version"] = 2
        changed["request_digest"] = artifact_digest(changed, "request_digest")
        with self.assertRaises(InstancePolicyError):
            self.plan(changed, current=current)
        changed = copy.deepcopy(request)
        changed["source"]["digest"] = "sha256:" + "d" * 64
        changed["request_digest"] = artifact_digest(changed, "request_digest")
        with self.assertRaises(InstancePolicyError):
            self.plan(changed, current=current)
        current["record"]["phase"] = "inventory"
        with self.assertRaises(InstancePolicyError):
            self.plan(request, current=current)

    def test_legacy_key_or_immutable_provider_claim_cannot_be_shadowed(self):
        for legacy in ({"synthetic-project": {}}, {"another-key": {"provider_repository": self.request()["requested_record"]["provider_repository"]}}):
            with self.assertRaisesRegex(InstancePolicyError, "Legacy authority"):
                self.plan(legacy_records=legacy)

    def test_policy_change_operator_mismatch_and_unapproved_record_are_denied(self):
        request = self.request()
        request["policy_ref"]["revision"] = "b" * 40
        request["request_digest"] = artifact_digest(request, "request_digest")
        with self.assertRaises(InstancePolicyError):
            self.plan(request)
        request = self.request()
        decision = self.decision(request)
        decision["operator_acceptance"]["operator_ref"] = "another-operator"
        decision = bind_artifact_digest(decision)
        with self.assertRaises(InstancePolicyError):
            self.plan(request, decision=decision)
        request["requested_record"]["notes"] = "Changed after operator accepted"
        with self.assertRaises(InstancePolicyError):
            self.plan(request)

    def test_source_only_route_does_not_register_a_control_owner(self):
        request = self.request()
        request["requested_record"]["repo_class"] = "governance"
        request["request_digest"] = artifact_digest(request, "request_digest")
        with self.assertRaisesRegex(InstancePolicyError, "source-only"):
            self.plan(request)

    def test_accepted_input_cannot_be_replayed_into_another_installation(self):
        request = self.request()
        request["instance_id"] = "installation-b"
        request["request_digest"] = artifact_digest(request, "request_digest")
        with self.assertRaisesRegex(InstancePolicyError, "another installation"):
            self.plan(request)

    def test_admission_requires_full_trusted_current_source_evidence(self):
        request = self.request(classification="admitted")
        with self.assertRaisesRegex(InstancePolicyError, "readiness"):
            self.plan(request)
        proof = {"schema_version": 1, "scope": "source-owner-controls-readiness", "owner_repo": "synthetic-project",
                 "provider_repository": copy.deepcopy(request["requested_record"]["provider_repository"]),
                 "fetched_base": "d" * 40, "canonical_checkout_commit": "e" * 40, "evidence_profile_digest": "sha256:" + "f" * 64,
                 "source_request_ref": "oos://repository-owner-bootstrap/requests/synthetic-proof",
                 "source_request_revision": "2026-11-04T00:01:30Z", "app_acceptance": False, "inventory_admission": False, "runtime_activation": False}
        proof["receipt_digest"] = canonical_digest(proof)
        self.assertEqual(self.plan(request, owner_readiness_reader=lambda *args: proof)["record"]["status"], "admitted")
        proof["app_acceptance"] = True
        with self.assertRaises(InstancePolicyError):
            self.plan(request, owner_readiness_reader=lambda *args: proof)

    def test_out_of_scope_registration_grants_no_source_role(self):
        request = self.request(classification="out-of-scope")
        record = request["requested_record"]
        for field in ("repo_class", "requires_security_bindings", "security_owner"):
            record[field] = None
        record.pop("validation_behavior")
        request["request_digest"] = artifact_digest(request, "request_digest")
        plan = self.plan(request)
        self.assertEqual(plan["record"]["status"], "out-of-scope")
        self.assertNotIn("validation_behavior", plan["record"])
