from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


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


def domain_record(kind: str) -> dict:
    validation_behavior = {
        "posture": "proposed-profile-gated",
        "wgcf_graph_role": "proposed-shared-platform-component",
        "catalog_refs": ["intake-model"],
        "notes": "Test readiness remains proposed until downstream admission completes.",
    }
    if kind == "repo":
        return {
            "kind": "repo",
            "repo_class": "product-source",
            "requires_security_bindings": True,
            "security_owner": "security-architecture",
            "validation_behavior": validation_behavior,
            "notes": "Test repository intake record.",
        }
    if kind == "product":
        return {
            "kind": "product",
            "platform_owner": "platform-engineering",
            "security_owner": "security-architecture",
            "runtime_owner": "test-product-owner",
            "source_owners": ["test-product-owner"],
            "intended_endpoint": "owner-repository-local-preview",
            "validation_behavior": validation_behavior,
            "notes": "Test product intake record.",
        }
    return {
        "kind": "component",
        "component_class": "shared-platform",
        "owner_repo": "platform-engineering",
        "security_owner": "security-architecture",
        "product": None,
        "validation_behavior": validation_behavior,
        "notes": "Test component intake record.",
    }


def request_for(repo_root: Path, kind: str, name: str, *, action: str = "add", key: str = "intake:test") -> dict:
    state = intake.current_state(repo_root, kind, name)
    request = {
        "schema_version": 2,
        "artifact_type": "workspace-intake-request",
        "request_id": f"request:{kind}:{name}:{action}",
        "requested_at": "2026-08-30T09:00:00Z",
        "requester_ref": "operator:test",
        "source": {
            "class": "direct",
            "ref": f"operator://test/{kind}/{name}",
            "digest": "sha256:" + "a" * 64,
        },
        "target": state["target"],
        "action": action,
        "requested_classification": "proposed",
        "owner_route": "platform-engineering",
        "requested_record": domain_record(kind),
        "expected_state": state["expected_state"],
        "idempotency_key": key,
    }
    return intake.bind_artifact_digest(request)


def decision_for(request: dict, *, decision_id: str = "decision:test") -> dict:
    decision = {
        "schema_version": 2,
        "artifact_type": "workspace-intake-decision",
        "decision_id": decision_id,
        "decided_at": "2026-08-30T09:05:00Z",
        "request_ref": {
            "id": request["request_id"],
            "digest": request["request_digest"],
        },
        "target": copy.deepcopy(request["target"]),
        "decision_source": "operator",
        "operator_acceptance": {
            "state": "accepted",
            "operator_ref": "operator:test",
            "recorded_at": "2026-08-30T09:05:00Z",
        },
        "outcome": {
            "status": "allowed",
            "classification": request["requested_classification"],
            "owner_route": request["owner_route"],
            "approved_record": copy.deepcopy(request["requested_record"]),
            "findings": [],
        },
    }
    return intake.bind_artifact_digest(decision)


class WorkspaceIntakeTests(unittest.TestCase):
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
        for path in (REPO_ROOT / "contracts" / "schemas").glob("workspace-intake-*.schema.json"):
            shutil.copy2(path, schemas / path.name)
        shutil.copy2(
            REPO_ROOT / "contracts" / "schemas" / "intake-register.schema.json",
            schemas / "intake-register.schema.json",
        )
        self.output_dir = self.repo_root / ".art" / "workspace-intake"

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def apply(self, request: dict, decision: dict):
        return intake.apply_intake(
            repo_root=self.repo_root,
            request=request,
            decision=decision,
            output_dir=self.output_dir,
            source_branch="feature/test-intake",
            completed_at="2026-08-30T09:10:00Z",
        )

    def test_adds_each_entrant_kind_with_versioned_evidence(self) -> None:
        for kind in ("repo", "product", "component"):
            with self.subTest(kind=kind):
                name = f"test-{kind}"
                request = request_for(
                    self.repo_root,
                    kind,
                    name,
                    key=f"intake:{kind}:{name}",
                )
                artifacts = self.apply(request, decision_for(request, decision_id=f"decision:{kind}"))
                entry = artifacts["readback"]["record"]
                self.assertEqual(entry["record"]["id"], f"{kind}:{name}")
                self.assertEqual(entry["record"]["version"], 1)
                self.assertEqual(artifacts["receipt"]["outcome"], "prepared")
                self.assertEqual(artifacts["readback"]["authority_state"], "review-branch")

    def test_temporal_migration_preserves_v1_truth_and_digest(self) -> None:
        legacy = json.loads(
            (
                REPO_ROOT
                / "contracts"
                / "fixtures"
                / "workspace-intake"
                / "temporal-v1-entry.json"
            ).read_text(encoding="utf-8")
        )
        register = intake.load_yaml(REPO_ROOT / "contracts" / "intake-register.yaml")
        migrated = register["components"]["temporal"]
        digest = intake.canonical_digest(legacy)

        for key, value in legacy.items():
            self.assertEqual(migrated[key], value)
        self.assertEqual(
            digest,
            "sha256:0dff18db9c5149c2165e1ecf9f331fb59a3ef4613942838f69188a4c6b249de8",
        )
        self.assertEqual(migrated["record"]["source"]["digest"], digest)
        self.assertEqual(migrated["record"]["decision"]["digest"], digest)
        self.assertEqual(migrated["record"]["last_mutation"]["request_digest"], digest)

    def test_exact_replay_does_not_increment_record_version(self) -> None:
        request = request_for(self.repo_root, "component", "test-replay")
        decision = decision_for(request)
        first = self.apply(request, decision)
        replay = self.apply(request, decision)
        repeated_replay = self.apply(request, decision)

        self.assertEqual(first["readback"]["record"]["record"]["version"], 1)
        self.assertEqual(replay["readback"]["record"]["record"]["version"], 1)
        self.assertEqual(replay["receipt"]["outcome"], "replayed")
        self.assertNotEqual(first["mutation"]["mutation_id"], replay["mutation"]["mutation_id"])
        self.assertEqual(replay, repeated_replay)

    def test_merged_readback_can_close_with_terminal_success_receipt(self) -> None:
        request = request_for(self.repo_root, "component", "test-merged", key="intake:merged")
        artifacts = self.apply(request, decision_for(request, decision_id="decision:merged"))
        merged_readback = copy.deepcopy(artifacts["readback"])
        merged_readback["observed_at"] = "2026-08-30T09:20:00Z"
        merged_readback["readback_id"] = "workspace-intake-readback:intake:merged:merged-authority"
        merged_readback["authority_state"] = "merged-authority"
        merged_readback["source_branch"] = "main"
        merged_readback = intake.bind_artifact_digest(merged_readback)
        intake.validate_artifact(self.repo_root, merged_readback)

        succeeded = copy.deepcopy(artifacts["receipt"])
        succeeded["completed_at"] = "2026-08-30T09:20:00Z"
        succeeded["receipt_id"] = "workspace-intake-receipt:intake:merged:merged-authority"
        succeeded["phase"] = "merged-authority"
        succeeded["outcome"] = "succeeded"
        succeeded["readback_ref"] = {
            "id": merged_readback["readback_id"],
            "digest": merged_readback["readback_digest"],
        }
        succeeded["canonical_authority"]["branch"] = "main"
        succeeded = intake.bind_artifact_digest(succeeded)
        intake.validate_artifact(self.repo_root, succeeded)

    def test_update_increments_version_and_rejects_stale_record_binding(self) -> None:
        first_request = request_for(self.repo_root, "component", "test-update", key="intake:update:add")
        self.apply(first_request, decision_for(first_request, decision_id="decision:update:add"))

        update_request = request_for(
            self.repo_root,
            "component",
            "test-update",
            action="update",
            key="intake:update:change",
        )
        update_request["requested_record"]["notes"] = "Updated reviewed component intake record."
        update_request = intake.bind_artifact_digest(update_request)
        updated = self.apply(update_request, decision_for(update_request, decision_id="decision:update:change"))
        self.assertEqual(updated["readback"]["record"]["record"]["version"], 2)

        stale_request = copy.deepcopy(update_request)
        stale_request["idempotency_key"] = "intake:update:stale"
        stale_request = intake.bind_artifact_digest(stale_request)
        with self.assertRaisesRegex(intake.WorkspaceIntakeError, "stale register digest"):
            self.apply(stale_request, decision_for(stale_request, decision_id="decision:update:stale"))

    def test_rejects_idempotency_key_rebound_to_changed_request(self) -> None:
        request = request_for(self.repo_root, "component", "test-conflict")
        self.apply(request, decision_for(request))

        changed = copy.deepcopy(request)
        changed["source"]["ref"] = "operator://test/component/changed"
        changed = intake.bind_artifact_digest(changed)
        with self.assertRaisesRegex(intake.WorkspaceIntakeError, "idempotency conflict"):
            self.apply(changed, decision_for(changed, decision_id="decision:changed"))

    def test_update_cannot_replace_original_source_identity(self) -> None:
        first_request = request_for(
            self.repo_root,
            "component",
            "test-source-identity",
            key="intake:source:add",
        )
        self.apply(first_request, decision_for(first_request, decision_id="decision:source:add"))
        update = request_for(
            self.repo_root,
            "component",
            "test-source-identity",
            action="update",
            key="intake:source:update",
        )
        update["source"]["ref"] = "operator://different-source"
        update = intake.bind_artifact_digest(update)
        with self.assertRaisesRegex(intake.WorkspaceIntakeError, "source identity is immutable"):
            self.apply(update, decision_for(update, decision_id="decision:source:update"))

    def test_rejects_stale_register_digest(self) -> None:
        request = request_for(self.repo_root, "component", "test-stale", key="intake:stale")
        request["expected_state"]["register_digest"] = "sha256:" + "b" * 64
        request = intake.bind_artifact_digest(request)
        with self.assertRaisesRegex(intake.WorkspaceIntakeError, "stale register digest"):
            self.apply(request, decision_for(request))

    def test_rejects_tampered_artifact_digest(self) -> None:
        request = request_for(self.repo_root, "component", "test-tamper", key="intake:tamper")
        request["owner_route"] = "different-owner"
        with self.assertRaisesRegex(intake.WorkspaceIntakeError, "request_digest"):
            self.apply(request, decision_for(request))

    def test_rejects_hard_delete_action(self) -> None:
        request = request_for(self.repo_root, "component", "test-delete", key="intake:delete")
        request["action"] = "delete"
        request = intake.bind_artifact_digest(request)
        with self.assertRaisesRegex(intake.WorkspaceIntakeError, "artifact schema validation"):
            self.apply(request, decision_for(request))

    def test_rejects_non_allowed_decision(self) -> None:
        request = request_for(self.repo_root, "component", "test-denied", key="intake:denied")
        decision = decision_for(request)
        decision["operator_acceptance"]["state"] = "rejected"
        decision["outcome"] = {
            "status": "denied",
            "classification": None,
            "owner_route": None,
            "approved_record": None,
            "findings": [
                {
                    "code": "operator-denied",
                    "severity": "info",
                    "message": "The operator denied this intake request.",
                    "disposition": None,
                    "justification": None,
                    "owner_ref": None,
                    "review_due_on": None,
                    "evidence_refs": [],
                    "security_evidence_refs": [],
                }
            ],
        }
        decision = intake.bind_artifact_digest(decision)
        with self.assertRaisesRegex(intake.WorkspaceIntakeError, "allowed decision"):
            self.apply(request, decision)

    def test_deferred_blocker_cannot_allow_mutation(self) -> None:
        request = request_for(self.repo_root, "component", "test-deferred", key="intake:deferred")
        decision = decision_for(request)
        decision["outcome"]["findings"] = [
            {
                "code": "owner-route-unresolved",
                "severity": "blocking",
                "message": "The owner route is not yet proven.",
                "disposition": "defer",
                "justification": "Owner review is pending.",
                "owner_ref": "owner:platform-engineering",
                "review_due_on": "2026-09-15",
                "evidence_refs": ["openproject://work_packages/1062"],
                "security_evidence_refs": [],
            }
        ]
        decision = intake.bind_artifact_digest(decision)
        with self.assertRaisesRegex(intake.WorkspaceIntakeError, "artifact schema validation"):
            self.apply(request, decision)

    def test_workaround_requires_owner_and_review_date(self) -> None:
        request = request_for(self.repo_root, "component", "test-workaround", key="intake:workaround")
        decision = decision_for(request)
        decision["outcome"]["findings"] = [
            {
                "code": "temporary-owner-route",
                "severity": "blocking",
                "message": "A temporary owner route is in use.",
                "disposition": "workaround",
                "justification": "The durable owner transition is tracked.",
                "owner_ref": None,
                "review_due_on": None,
                "evidence_refs": ["openproject://work_packages/1062"],
                "security_evidence_refs": [],
            }
        ]
        decision = intake.bind_artifact_digest(decision)
        with self.assertRaisesRegex(intake.WorkspaceIntakeError, "artifact schema validation"):
            self.apply(request, decision)

    def test_accept_risk_requires_security_evidence(self) -> None:
        request = request_for(self.repo_root, "component", "test-risk", key="intake:risk")
        decision = decision_for(request)
        decision["outcome"]["findings"] = [
            {
                "code": "accepted-trust-risk",
                "severity": "blocking",
                "message": "A reviewed trust-boundary risk remains.",
                "disposition": "accept-risk",
                "justification": "The operator accepts the bounded residual risk.",
                "owner_ref": None,
                "review_due_on": None,
                "evidence_refs": ["openproject://work_packages/1062"],
                "security_evidence_refs": [],
            }
        ]
        decision = intake.bind_artifact_digest(decision)
        with self.assertRaisesRegex(intake.WorkspaceIntakeError, "artifact schema validation"):
            self.apply(request, decision)

        decision["outcome"]["findings"][0]["security_evidence_refs"] = [
            "security-review://workspace-intake/test-risk"
        ]
        decision = intake.bind_artifact_digest(decision)
        artifacts = self.apply(request, decision)
        self.assertEqual(artifacts["receipt"]["outcome"], "prepared")

    def test_allowed_workaround_binds_owner_and_review_date(self) -> None:
        request = request_for(
            self.repo_root,
            "component",
            "test-reviewed-workaround",
            key="intake:reviewed-workaround",
        )
        decision = decision_for(request)
        decision["outcome"]["findings"] = [
            {
                "code": "temporary-owner-route",
                "severity": "blocking",
                "message": "A temporary owner route is in use.",
                "disposition": "workaround",
                "justification": "The durable owner transition is tracked.",
                "owner_ref": "owner:platform-engineering",
                "review_due_on": "2026-09-15",
                "evidence_refs": ["openproject://work_packages/1062"],
                "security_evidence_refs": [],
            }
        ]
        decision = intake.bind_artifact_digest(decision)
        artifacts = self.apply(request, decision)
        self.assertEqual(artifacts["receipt"]["outcome"], "prepared")

    def test_rejects_active_inventory_overlap(self) -> None:
        request = request_for(self.repo_root, "component", "argo-cd", key="intake:overlap")
        with self.assertRaisesRegex(intake.WorkspaceIntakeError, "active inventory overlap"):
            self.apply(request, decision_for(request))

    def test_rejects_conflicting_target_identity(self) -> None:
        request = request_for(self.repo_root, "component", "test-identity", key="intake:identity")
        request["target"]["record_id"] = "component:different"
        request = intake.bind_artifact_digest(request)
        with self.assertRaisesRegex(intake.WorkspaceIntakeError, "identity conflict"):
            self.apply(request, decision_for(request))

    def test_rejects_implicit_ai_decision(self) -> None:
        request = request_for(self.repo_root, "component", "test-ai", key="intake:ai")
        decision = decision_for(request)
        decision["decision_source"] = "ai-suggested"
        decision = intake.bind_artifact_digest(decision)
        with self.assertRaisesRegex(intake.WorkspaceIntakeError, "ai_suggestion"):
            self.apply(request, decision)

    def test_applies_explicitly_accepted_governed_ai_decision(self) -> None:
        request = request_for(self.repo_root, "component", "test-ai-accepted", key="intake:ai:accepted")
        decision = decision_for(request, decision_id="decision:ai:accepted")
        decision["decision_source"] = "ai-suggested"
        decision["ai_suggestion"] = {
            "profile_id": "intake-classifier-v1",
            "policy_status": "active",
            "decision_id": "suggestion:ai:accepted",
            "generated_at": "2026-08-30T09:02:00Z",
            "confidence": "medium",
            "caller_id": "workspace-governance/intake-assist",
            "invocation_path": "governed-ai-gateway",
            "suggested_decision": "proposed",
            "operator_decision": "proposed",
            "acceptance_state": "accepted",
            "accepted_by": "operator:test",
            "accepted_at": "2026-08-30T09:05:00Z",
            "audit_ref": "local-ledger:test-ai-accepted",
        }
        decision = intake.bind_artifact_digest(decision)

        artifacts = self.apply(request, decision)

        self.assertEqual(artifacts["receipt"]["outcome"], "prepared")
        self.assertEqual(
            artifacts["readback"]["record"]["ai_suggestion"]["decision_id"],
            "suggestion:ai:accepted",
        )

    def test_rejects_default_branch_mutation(self) -> None:
        request = request_for(self.repo_root, "component", "test-main", key="intake:main")
        with self.assertRaisesRegex(intake.WorkspaceIntakeError, "default branch"):
            intake.apply_intake(
                repo_root=self.repo_root,
                request=request,
                decision=decision_for(request),
                output_dir=self.output_dir,
                source_branch="main",
                completed_at="2026-08-30T09:10:00Z",
            )

    def test_compatibility_scaffolder_delegates_to_v2_engine(self) -> None:
        subprocess.run(
            ["git", "init", "-b", "feature/test-intake"],
            cwd=self.repo_root,
            check=True,
            capture_output=True,
        )
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS_ROOT / "scaffold_intake.py"),
                "--repo-root",
                str(self.repo_root),
                "component",
                "--name",
                "compatibility-component",
                "--status",
                "proposed",
                "--owner-route",
                "platform-engineering",
                "--source-class",
                "direct",
                "--source-ref",
                "operator://test/component/compatibility-component",
                "--source-digest",
                "sha256:" + "a" * 64,
                "--request-id",
                "request:compatibility-component",
                "--decision-id",
                "decision:compatibility-component",
                "--idempotency-key",
                "intake:compatibility-component",
                "--operator-ref",
                "operator:test",
                "--component-class",
                "shared-platform",
                "--owner-repo",
                "platform-engineering",
                "--validation-posture",
                "proposed-profile-gated",
                "--validation-graph-role",
                "proposed-shared-platform-component",
                "--validation-catalog-ref",
                "intake-model",
                "--validation-notes",
                "Compatibility path test readiness remains proposed.",
                "--notes",
                "Compatibility path test intake record.",
            ],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        register = intake.load_yaml(self.repo_root / "contracts" / "intake-register.yaml")
        entry = register["components"]["compatibility-component"]
        self.assertEqual(entry["record"]["version"], 1)
        self.assertTrue((self.output_dir / "receipt.json").exists())


if __name__ == "__main__":
    unittest.main()
