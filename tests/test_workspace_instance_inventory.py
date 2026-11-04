from __future__ import annotations
import copy
from datetime import datetime, timezone
from pathlib import Path
import sys
from unittest import TestCase

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from workspace_instance_inventory import plan_repository_inventory
from workspace_instance_records import InstancePolicyError, instance_policy_ref, project_repository_source_authority
from workspace_intake import canonical_digest
import test_workspace_instance_records as intake_fixtures


class InstanceInventoryPolicyTests(TestCase):
    def setUp(self):
        initial = intake_fixtures.InstanceRepositoryPolicyTests()
        self.current = initial.current()
        self.current["record"]["status"] = "admitted"
        self.current["receipt"].update(instance_id="installation-a", record_digest=canonical_digest(self.current["record"]),
            receipt_digest=canonical_digest("synthetic-admitted-receipt"), action="intake.update")
        self.now = datetime(2026, 11, 4, 0, 3, tzinfo=timezone.utc)

    def value(self):
        entry = self.current["record"]
        return {"posture": "active", "lifecycle": "active", "repo_class": "product-source", "requires_security_bindings": False,
            "security_review_subject": False, "provider_repository": copy.deepcopy(entry["provider_repository"]),
            "owns": ["Project source and owner checks"], "must_not_own": ["Shared runtime and Security policy"],
            "allowed_authoritative_refs": ["workspace-governance"], "validation_behavior": copy.deepcopy(entry["validation_behavior"])}

    def request(self, action="promote", current=None, value=None):
        current = current or self.current
        result = {"schema_version": 1, "artifact_type": "instance-repository-inventory-request", "instance_id": "installation-a",
            "request_id": f"synthetic-inventory:{action}", "requested_at": "2026-11-04T00:02:00Z", "operator_ref": "operator:test",
            "correlation_ref": f"console://inventory/{action}", "idempotency_key": f"synthetic-inventory:{action}",
            "action": action, "target": {"kind": "repo", "name": "synthetic-project", "record_id": "repo:synthetic-project"},
            "expected_state": {"record_version": current["receipt"]["version"], "record_digest": current["receipt"]["record_digest"]},
            "requested_value": (value or self.value()) if action in {"promote", "update"} else None,
            "prior_receipt_digest": current["receipt"]["receipt_digest"] if action == "restore" else None,
            "reason": None if action == "promote" else "Operator-reviewed project lifecycle change",
            "impact_acknowledgements": [] if action == "promote" else ["Source references follow the reviewed posture"],
            "approval_refs": ["console://inventory/acceptance"],
            "operator_acceptance": {"state": "accepted", "operator_ref": "operator:test", "recorded_at": "2026-11-04T00:02:00Z"},
            "policy_ref": instance_policy_ref(ROOT, "a" * 40)}
        result["request_digest"] = canonical_digest(result)
        return result

    def plan(self, request=None, current=None, **kwargs):
        return plan_repository_inventory(policy_root=ROOT, policy_revision="a" * 40, instance_id="installation-a",
            request=request or self.request(), operator_ref="operator:test", current=current or self.current,
            legacy_records=kwargs.get("legacy_records", {}), now=self.now)

    def accepted(self, action="promote", current=None):
        current = current or self.current
        plan = self.plan(self.request(action, current), current)
        return {"record": plan["record"], "receipt": {"instance_id": "installation-a", "record_id": "repo:synthetic-project",
            "version": current["receipt"]["version"] + 1, "record_digest": canonical_digest(plan["record"]),
            "receipt_digest": canonical_digest(f"synthetic-{action}"), "action": f"inventory.{action}"}}

    def test_promotion_moves_the_same_aggregate_and_preserves_real_intake_lineage(self):
        result = self.accepted()
        self.assertEqual(result["record"]["phase"], "inventory")
        self.assertEqual(result["record"]["record"]["version"], 2)
        self.assertEqual(result["record"]["record"]["lineage"]["source_digest"], self.current["receipt"]["record_digest"])
        source = project_repository_source_authority(instance_id="installation-a", name="synthetic-project", current=result,
            operation="ordinary-source", policy_ref=instance_policy_ref(ROOT, "a" * 40))
        self.assertTrue(source["ordinary_source_eligible"])
        self.assertFalse(source["model_writes_allowed"])
        self.assertNotIn("merge_commit", str(result))

    def test_proposed_intake_or_changed_identity_cannot_be_promoted(self):
        for change in [lambda v: v["record"].update(status="proposed"),
                       lambda v: v["record"].update(repo_class="shared-control")]:
            current = copy.deepcopy(self.current); change(current)
            current["receipt"]["record_digest"] = canonical_digest(current["record"])
            with self.assertRaises(InstancePolicyError):
                self.plan(self.request(current=current), current)
        request = self.request(); request["requested_value"]["provider_repository"]["provider_repository_id"] = "999"
        request["request_digest"] = canonical_digest({k:v for k,v in request.items() if k != "request_digest"})
        with self.assertRaises(InstancePolicyError): self.plan(request)

    def test_suspend_and_retire_deny_source_and_restore_binds_the_latest_receipt(self):
        active = self.accepted()
        for action in ["suspend", "retire"]:
            stopped = self.accepted(action, active)
            self.assertEqual(stopped["record"]["record"]["version"], 3)
            with self.assertRaises(InstancePolicyError):
                project_repository_source_authority(instance_id="installation-a", name="synthetic-project", current=stopped,
                    operation="ordinary-source", policy_ref=instance_policy_ref(ROOT, "a" * 40))
            restored = self.accepted("restore", stopped)
            self.assertEqual(restored["record"]["posture"], "active")
            self.assertEqual(restored["record"]["record"]["version"], 4)
            wrong = self.request("restore", stopped); wrong["prior_receipt_digest"] = canonical_digest("old")
            wrong["request_digest"] = canonical_digest({k:v for k,v in wrong.items() if k != "request_digest"})
            with self.assertRaises(InstancePolicyError): self.plan(wrong, stopped)

    def test_updates_cannot_replace_envelopes_change_posture_or_escalate_control_authority(self):
        active = self.accepted()
        for change in [lambda v: v.update(record={}), lambda v: v.update(posture="suspended"),
                       lambda v: v.update(requires_security_bindings=True), lambda v: v.update(repo_class="governance")]:
            value = self.value(); change(value)
            with self.assertRaises(InstancePolicyError): self.plan(self.request("update", active, value), active)
        value = self.value(); value["owns"] = ["Updated project source responsibility"]
        result = self.plan(self.request("update", active, value), active)
        self.assertEqual(result["record"]["owns"], value["owns"])
        self.assertEqual(result["record"]["record"]["lineage"], active["record"]["record"]["lineage"])

    def test_stale_or_cross_installation_acceptance_and_legacy_overlap_are_denied(self):
        for change in [lambda r: r.update(instance_id="installation-b"),
                       lambda r: r["expected_state"].update(record_version=9),
                       lambda r: r["operator_acceptance"].update(operator_ref="other"),
                       lambda r: r["policy_ref"].update(revision="b" * 40)]:
            request = self.request(); change(request)
            request["request_digest"] = canonical_digest({k:v for k,v in request.items() if k != "request_digest"})
            with self.assertRaises(InstancePolicyError): self.plan(request)
        with self.assertRaises(InstancePolicyError): self.plan(legacy_records={"synthetic-project": self.current["record"]})
