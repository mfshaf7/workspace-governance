from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = REPO_ROOT / "scripts"


def load_module(name: str, path: Path):
    if str(SCRIPTS_ROOT) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_ROOT))
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


intake = load_module("workspace_intake", SCRIPTS_ROOT / "workspace_intake.py")
inventory = load_module("workspace_inventory", SCRIPTS_ROOT / "workspace_inventory.py")


def intake_domain_record(kind: str) -> dict:
    behavior = {
        "posture": "proposed-profile-gated",
        "wgcf_graph_role": "proposed-test-entry",
        "catalog_refs": ["intake-model"],
        "notes": "Test entrant awaits active inventory promotion.",
    }
    if kind == "repo":
        return {
            "kind": "repo",
            "repo_class": "product-source",
            "requires_security_bindings": False,
            "security_owner": "security-architecture",
            "validation_behavior": behavior,
            "notes": "Test repository entrant.",
        }
    if kind == "product":
        return {
            "kind": "product",
            "platform_owner": "platform-engineering",
            "security_owner": "security-architecture",
            "runtime_owner": "workspace-prototype-studio",
            "source_owners": ["workspace-prototype-studio"],
            "intended_endpoint": "owner-repository-local-preview",
            "validation_behavior": behavior,
            "notes": "Test product entrant.",
        }
    return {
        "kind": "component",
        "component_class": "shared-platform",
        "owner_repo": "platform-engineering",
        "security_owner": "security-architecture",
        "product": None,
        "validation_behavior": behavior,
        "notes": "Test component entrant.",
    }


def active_value(kind: str) -> dict:
    behavior = {
        "posture": "covered-by-owner-repo",
        "wgcf_graph_role": "test-active-record",
        "catalog_refs": ["contract-model"],
        "notes": "Test active inventory behavior.",
    }
    if kind == "repo":
        return {
            "posture": "active",
            "lifecycle": "active",
            "repo_class": "product-source",
            "requires_security_bindings": False,
            "security_review_subject": False,
            "owns": ["test source"],
            "must_not_own": ["workspace policy"],
            "allowed_authoritative_refs": ["workspace-governance"],
            "validation_behavior": behavior,
        }
    if kind == "product":
        return {
            "posture": "active",
            "maturity": "owner-managed",
            "lifecycle": "owner-managed",
            "platform_owner": "platform-engineering",
            "security_owner": "security-architecture",
            "runtime_owner": "workspace-prototype-studio",
            "source_owners": ["workspace-prototype-studio"],
            "stage_supported": False,
            "governed_prod_promotion": False,
            "highest_real_endpoint": "owner-repository-local-preview",
            "validation_behavior": behavior,
        }
    return {
        "posture": "active",
        "lifecycle": "active",
        "component_class": "shared-platform",
        "owner_repo": "platform-engineering",
        "product": None,
        "security_owner": "security-architecture",
        "validation_behavior": behavior,
    }


class WorkspaceInventoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.repo_root = Path(self.temporary.name) / "workspace-governance"
        contracts = self.repo_root / "contracts"
        schemas = contracts / "schemas"
        schemas.mkdir(parents=True)
        for name in (
            "intake-register.yaml",
            "intake-policy.yaml",
            "governed-intake-assist.yaml",
            "repos.yaml",
            "products.yaml",
            "components.yaml",
        ):
            shutil.copy2(REPO_ROOT / "contracts" / name, contracts / name)
        for pattern in ("workspace-intake-*.schema.json", "workspace-inventory-*.schema.json"):
            for path in (REPO_ROOT / "contracts" / "schemas").glob(pattern):
                shutil.copy2(path, schemas / path.name)
        for name in ("intake-register.schema.json", "repos.schema.json", "products.schema.json", "components.schema.json"):
            shutil.copy2(REPO_ROOT / "contracts" / "schemas" / name, schemas / name)
        self.output_dir = self.repo_root / ".art" / "workspace-inventory"

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def admit(self, kind: str, name: str, classification: str = "admitted") -> None:
        state = intake.current_state(self.repo_root, kind, name)
        request = {
            "schema_version": 2,
            "artifact_type": "workspace-intake-request",
            "request_id": f"request:intake:{kind}:{name}",
            "requested_at": "2026-09-06T04:00:00Z",
            "requester_ref": "operator:test",
            "source": {
                "class": "direct",
                "ref": f"operator://test/{kind}/{name}",
                "digest": "sha256:" + "a" * 64,
            },
            "target": state["target"],
            "action": "add",
            "requested_classification": classification,
            "owner_route": "workspace-governance",
            "requested_record": intake_domain_record(kind),
            "expected_state": state["expected_state"],
            "idempotency_key": f"intake:{kind}:{name}",
        }
        request = intake.bind_artifact_digest(request)
        decision = {
            "schema_version": 2,
            "artifact_type": "workspace-intake-decision",
            "decision_id": f"decision:intake:{kind}:{name}",
            "decided_at": "2026-09-06T04:01:00Z",
            "request_ref": {"id": request["request_id"], "digest": request["request_digest"]},
            "target": copy.deepcopy(request["target"]),
            "decision_source": "operator",
            "operator_acceptance": {
                "state": "accepted",
                "operator_ref": "operator:test",
                "recorded_at": "2026-09-06T04:01:00Z",
            },
            "outcome": {
                "status": "allowed",
                "classification": classification,
                "owner_route": "workspace-governance",
                "approved_record": copy.deepcopy(request["requested_record"]),
                "findings": [],
            },
        }
        decision = intake.bind_artifact_digest(decision)
        intake.apply_intake(
            repo_root=self.repo_root,
            request=request,
            decision=decision,
            output_dir=self.repo_root / ".art" / "workspace-intake",
            source_branch="feature/test-promotion",
            completed_at="2026-09-06T04:02:00Z",
        )

    def promotion_artifacts(self, kind: str, name: str) -> tuple[dict, dict]:
        state = inventory.current_state(self.repo_root, kind, name)
        target = state.pop("target")
        request = {
            "schema_version": 1,
            "artifact_type": "workspace-inventory-promotion-request",
            "request_id": f"request:promotion:{kind}:{name}",
            "requested_at": "2026-09-06T04:05:00Z",
            "operator_ref": "operator:test",
            "correlation_ref": f"test:{kind}:{name}",
            "idempotency_key": f"promotion:{kind}:{name}",
            "target": target,
            "intake_entry_ref": {
                "id": target["record_id"],
                "version": state["intake_entry_version"],
                "digest": state["intake_entry_digest"],
            },
            "expected_state": state,
            "active_record": {"kind": kind, "id": target["record_id"], "value": active_value(kind)},
            "approval_refs": ["openproject://work_packages/1071"],
        }
        request = inventory.bind_artifact_digest(request)
        readiness = inventory.bind_artifact_digest({
            "schema_version": 1,
            "artifact_type": "workspace-inventory-promotion-readiness",
            "readiness_id": f"readiness:promotion:{kind}:{name}",
            "evaluated_at": "2026-09-06T04:06:00Z",
            "request_ref": {"id": request["request_id"], "digest": request["request_digest"]},
            "target": copy.deepcopy(target),
            "observed_state": copy.deepcopy(state),
            "policy_ref": {"id": "workspace-active-inventory:v1", "digest": "sha256:" + "b" * 64},
            "outcome": "ready",
            "findings": [],
        })
        return request, readiness

    def apply(self, request: dict, readiness: dict):
        return inventory.apply_promotion(
            repo_root=self.repo_root,
            request=request,
            readiness=readiness,
            output_dir=self.output_dir,
            source_branch="feature/test-promotion",
            completed_at="2026-09-06T04:07:00Z",
        )

    def test_promotes_each_kind_without_intake_overlap(self) -> None:
        for kind in ("repo", "product", "component"):
            with self.subTest(kind=kind):
                name = f"test-{kind}"
                self.admit(kind, name)
                request, readiness = self.promotion_artifacts(kind, name)
                artifacts = self.apply(request, readiness)
                state = inventory.current_state(self.repo_root, kind, name)
                self.assertIsNone(state["intake_entry_version"])
                self.assertEqual(state["active_record_version"], 1)
                self.assertEqual(artifacts["receipt"]["outcome"], "prepared")
                self.assertEqual(artifacts["readback"]["active_record"]["posture"], "active")

    def test_exact_replay_does_not_duplicate_or_increment(self) -> None:
        self.admit("component", "test-replay")
        request, readiness = self.promotion_artifacts("component", "test-replay")
        first = self.apply(request, readiness)
        replay = self.apply(request, readiness)
        self.assertEqual(first["readback"]["active_record"]["record"]["version"], 1)
        self.assertEqual(replay["readback"]["active_record"]["record"]["version"], 1)
        self.assertEqual(replay["receipt"]["outcome"], "replayed")

    def test_rejects_stale_source_binding(self) -> None:
        self.admit("repo", "test-stale")
        request, readiness = self.promotion_artifacts("repo", "test-stale")
        request["expected_state"]["active_inventory_digest"] = "sha256:" + "c" * 64
        request = inventory.bind_artifact_digest(request)
        readiness["request_ref"] = {"id": request["request_id"], "digest": request["request_digest"]}
        readiness["observed_state"] = copy.deepcopy(request["expected_state"])
        readiness = inventory.bind_artifact_digest(readiness)
        with self.assertRaisesRegex(inventory.WorkspaceInventoryError, "stale active inventory digest"):
            self.apply(request, readiness)

    def test_rejects_non_admitted_entry(self) -> None:
        self.admit("component", "test-proposed", classification="proposed")
        request, readiness = self.promotion_artifacts("component", "test-proposed")
        with self.assertRaisesRegex(inventory.WorkspaceInventoryError, "only an admitted"):
            self.apply(request, readiness)

    def test_rejects_compatibility_alias_drift(self) -> None:
        self.admit("product", "test-alias")
        request, readiness = self.promotion_artifacts("product", "test-alias")
        request["active_record"]["value"]["lifecycle"] = "fully-governed"
        request = inventory.bind_artifact_digest(request)
        readiness["request_ref"] = {"id": request["request_id"], "digest": request["request_digest"]}
        readiness = inventory.bind_artifact_digest(readiness)
        with self.assertRaisesRegex(inventory.WorkspaceInventoryError, "must equal maturity"):
            self.apply(request, readiness)

    def test_process_failure_restores_both_contracts(self) -> None:
        self.admit("repo", "test-rollback")
        request, readiness = self.promotion_artifacts("repo", "test-rollback")
        intake_path = self.repo_root / "contracts" / "intake-register.yaml"
        inventory_path = self.repo_root / "contracts" / "repos.yaml"
        before = (intake_path.read_bytes(), inventory_path.read_bytes())
        real_replace = inventory.os.replace
        calls = 0

        def fail_second(source, target):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("simulated second replace failure")
            return real_replace(source, target)

        with mock.patch.object(inventory.os, "replace", side_effect=fail_second):
            with self.assertRaisesRegex(OSError, "simulated second replace failure"):
                self.apply(request, readiness)
        self.assertEqual((intake_path.read_bytes(), inventory_path.read_bytes()), before)

    def test_default_branch_is_denied(self) -> None:
        self.admit("repo", "test-main")
        request, readiness = self.promotion_artifacts("repo", "test-main")
        with self.assertRaisesRegex(inventory.WorkspaceInventoryError, "default branch"):
            inventory.apply_promotion(
                repo_root=self.repo_root,
                request=request,
                readiness=readiness,
                output_dir=self.output_dir,
                source_branch="main",
            )

    def test_v2_migration_is_idempotent(self) -> None:
        report = inventory.migrate_inventory(
            self.repo_root,
            source_ref="git://workspace-governance/test",
            recorded_at="2026-09-06T04:00:00Z",
        )
        self.assertEqual(
            {item["status"] for item in report["inventories"].values()},
            {"already-migrated"},
        )


if __name__ == "__main__":
    unittest.main()
