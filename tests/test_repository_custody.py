from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator, FormatChecker
import yaml

from scripts.repository_custody_contract import (
    contract_issues,
    lifecycle_receipt_issues,
    lifecycle_request_issues,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = REPO_ROOT / "contracts" / "repository-custody.yaml"
SCHEMA_ROOT = REPO_ROOT / "contracts" / "schemas"
FIXTURE_ROOT = REPO_ROOT / "contracts" / "fixtures" / "repository-custody"
FORMAT_CHECKER = FormatChecker()

ARTIFACT_CASES = {
    "request": ("repository-custody-request.schema.json", "request.valid.json"),
    "decision": ("repository-custody-decision.schema.json", "decision.valid.json"),
    "provider_readback": (
        "repository-provider-readback.schema.json",
        "provider-readback.valid.json",
    ),
    "custody_receipt": (
        "repository-custody-receipt.schema.json",
        "receipt.valid.json",
    ),
}

PROVISION_ARTIFACT_CASES = {
    "request": "request.provision.valid.json",
    "decision": "decision.provision.valid.json",
    "provider_readback": "provider-readback.provision.valid.json",
    "custody_receipt": "receipt.provision.valid.json",
}

LIFECYCLE_ARTIFACT_CASES = {
    "request": (
        "repository-lifecycle-request.schema.json",
        "lifecycle-request.archive.valid.json",
    ),
    "decision": (
        "repository-lifecycle-decision.schema.json",
        "lifecycle-decision.archive.valid.json",
    ),
    "provider_readback": (
        "repository-provider-readback.schema.json",
        "provider-readback.archive.valid.json",
    ),
    "receipt": (
        "repository-lifecycle-receipt.schema.json",
        "lifecycle-receipt.archive.valid.json",
    ),
    "audit": (
        "repository-lifecycle-audit.schema.json",
        "lifecycle-audit.valid.json",
    ),
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validator_for(path: Path) -> Draft202012Validator:
    schema = load_json(path)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FORMAT_CHECKER)


class RepositoryCustodyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8"))
        cls.validators = {
            name: validator_for(SCHEMA_ROOT / schema_name)
            for name, (schema_name, _) in ARTIFACT_CASES.items()
        }
        cls.fixtures = {
            name: load_json(FIXTURE_ROOT / fixture_name)
            for name, (_, fixture_name) in ARTIFACT_CASES.items()
        }
        cls.provision_fixtures = {
            name: load_json(FIXTURE_ROOT / fixture_name)
            for name, fixture_name in PROVISION_ARTIFACT_CASES.items()
        }
        cls.lifecycle_validators = {
            name: validator_for(SCHEMA_ROOT / schema_name)
            for name, (schema_name, _) in LIFECYCLE_ARTIFACT_CASES.items()
        }
        cls.lifecycle_fixtures = {
            name: load_json(FIXTURE_ROOT / fixture_name)
            for name, (_, fixture_name) in LIFECYCLE_ARTIFACT_CASES.items()
        }

    def assertValid(self, artifact_name: str, payload: dict) -> None:
        errors = sorted(
            self.validators[artifact_name].iter_errors(payload),
            key=lambda error: list(error.absolute_path),
        )
        self.assertEqual([error.message for error in errors], [])

    def assertInvalid(self, artifact_name: str, payload: dict) -> None:
        self.assertTrue(list(self.validators[artifact_name].iter_errors(payload)))

    def assertLifecycleValid(self, artifact_name: str, payload: dict) -> None:
        errors = sorted(
            self.lifecycle_validators[artifact_name].iter_errors(payload),
            key=lambda error: list(error.absolute_path),
        )
        self.assertEqual([error.message for error in errors], [])

    def assertLifecycleInvalid(self, artifact_name: str, payload: dict) -> None:
        self.assertTrue(
            list(self.lifecycle_validators[artifact_name].iter_errors(payload))
        )

    def test_contract_and_artifact_fixtures_validate(self) -> None:
        contract_validator = validator_for(
            SCHEMA_ROOT / "repository-custody.schema.json"
        )
        self.assertEqual(list(contract_validator.iter_errors(self.contract)), [])
        for name, payload in self.fixtures.items():
            with self.subTest(artifact=name):
                self.assertValid(name, payload)
        for name, payload in self.provision_fixtures.items():
            with self.subTest(artifact=f"provision_{name}"):
                self.assertValid(name, payload)
        for name, payload in self.lifecycle_fixtures.items():
            with self.subTest(artifact=f"lifecycle_{name}"):
                self.assertLifecycleValid(name, payload)
        self.assertEqual(contract_issues(self.contract, self._active_repo_names()), [])

    @staticmethod
    def _active_repo_names() -> set[str]:
        return {
            "workspace-governance",
            "workspace-governance-control-fabric",
            "operator-orchestration-service",
            "platform-engineering",
            "security-architecture",
            "governance-operations-console",
        }

    def test_repository_identity_uses_provider_id_not_coordinates(self) -> None:
        self.assertEqual(
            self.contract["repository_identity"]["immutable_key"]["fields"],
            ["provider", "provider_repository_id"],
        )
        readback = copy.deepcopy(self.fixtures["provider_readback"])
        readback["repository_identity"].pop("provider_repository_id")
        self.assertInvalid("provider_readback", readback)

    def test_github_identity_uses_decimal_rest_repository_id(self) -> None:
        self.assertEqual(
            self.contract["repository_identity"]["provider_id_formats"]["github"][
                "format"
            ],
            "decimal-rest-repository-id",
        )
        for artifact_name, identity_path in (
            ("request", ("target",)),
            ("decision", ("resolved_identity",)),
            ("provider_readback", ("repository_identity",)),
            ("custody_receipt", ("repository_identity",)),
        ):
            with self.subTest(artifact=artifact_name):
                payload = copy.deepcopy(self.fixtures[artifact_name])
                identity = payload
                for key in identity_path:
                    identity = identity[key]
                identity["provider_repository_id"] = "R_kgDOExample"
                self.assertInvalid(artifact_name, payload)

    def test_existing_repository_actions_require_provider_identity(self) -> None:
        request = copy.deepcopy(self.fixtures["request"])
        request["target"]["provider_repository_id"] = None
        self.assertInvalid("request", request)

    def test_provider_mutation_requires_exact_approval(self) -> None:
        request = copy.deepcopy(self.fixtures["request"])
        request["action"] = "archive-provider"
        request["authority"]["approval_ref"] = None
        self.assertInvalid("request", request)

    def test_linking_custody_requires_exact_approval(self) -> None:
        request = copy.deepcopy(self.fixtures["request"])
        request["authority"]["approval_ref"] = None
        self.assertInvalid("request", request)

    def test_successful_link_requires_readback_and_identity(self) -> None:
        receipt = copy.deepcopy(self.fixtures["custody_receipt"])
        receipt["provider_readback_ref"] = None
        self.assertInvalid("custody_receipt", receipt)

        receipt = copy.deepcopy(self.fixtures["custody_receipt"])
        receipt["repository_identity"] = None
        self.assertInvalid("custody_receipt", receipt)

    def test_denied_and_failed_link_receipts_do_not_fabricate_readback(self) -> None:
        for outcome in ("denied", "failed"):
            with self.subTest(outcome=outcome):
                receipt = copy.deepcopy(self.fixtures["custody_receipt"])
                receipt["outcome"] = outcome
                receipt["workflow_status"] = outcome
                receipt["provider_readback_ref"] = None
                receipt["repository_identity"] = None
                receipt["custody"]["after"] = receipt["custody"]["before"]
                self.assertValid("custody_receipt", receipt)

    def test_custody_receipt_does_not_claim_downstream_mutation(self) -> None:
        downstream = self.fixtures["custody_receipt"]["downstream_handoffs"]
        self.assertEqual(downstream["workspace_intake"], "request-available")
        self.assertEqual(downstream["active_inventory"], "separate-action-required")
        self.assertEqual(downstream["delivery_catalog"], "separate-action-required")
        self.assertEqual(downstream["product_admission"], "separate-action-required")

    def test_secret_values_are_rejected_as_unknown_fields(self) -> None:
        request = copy.deepcopy(self.fixtures["request"])
        request["authority"]["token"] = "not-allowed"
        self.assertInvalid("request", request)

    def test_provisioning_requires_organization_scope_and_explicit_settings(self) -> None:
        request = copy.deepcopy(self.provision_fixtures["request"])
        request["target"]["owner_scope"] = "personal"
        self.assertInvalid("request", request)

        request = copy.deepcopy(self.provision_fixtures["request"])
        request.pop("provisioning")
        self.assertInvalid("request", request)

        request = copy.deepcopy(self.provision_fixtures["request"])
        request["provisioning"]["initialize_with_readme"] = False
        self.assertInvalid("request", request)

        request = copy.deepcopy(self.provision_fixtures["request"])
        request["provisioning"]["features"].pop("issues")
        self.assertInvalid("request", request)

    def test_provisioning_decision_binds_exact_target_and_create_action(self) -> None:
        decision = copy.deepcopy(self.provision_fixtures["decision"])
        decision["next_action"] = "read-provider"
        self.assertInvalid("decision", decision)

        decision = copy.deepcopy(self.provision_fixtures["decision"])
        decision["approved_provisioning"] = None
        self.assertInvalid("decision", decision)

        decision = copy.deepcopy(self.provision_fixtures["decision"])
        decision["outcome"] = "requires-action"
        decision["next_action"] = "request-correction"
        self.assertInvalid("decision", decision)

    def test_provisioning_readback_proves_settings_and_initialized_state(self) -> None:
        readback = copy.deepcopy(self.provision_fixtures["provider_readback"])
        readback["applied_provisioning"] = None
        self.assertInvalid("provider_readback", readback)

        readback = copy.deepcopy(self.provision_fixtures["provider_readback"])
        readback["applied_provisioning"]["initialization_state"] = "empty"
        self.assertInvalid("provider_readback", readback)

    def test_successful_provision_receipt_records_provisioned_custody(self) -> None:
        receipt = copy.deepcopy(self.provision_fixtures["custody_receipt"])
        receipt["custody"]["after"] = "linked"
        self.assertInvalid("custody_receipt", receipt)

    def test_lifecycle_contract_separates_state_axes_and_actions(self) -> None:
        lifecycle = self.contract["repository_lifecycle"]
        self.assertEqual(
            set(lifecycle["state_axes"]),
            {"custody", "provider", "workspace_record"},
        )
        self.assertEqual(
            set(lifecycle["actions"]),
            {
                "transfer-workspace-custody",
                "archive-provider",
                "unarchive-provider",
                "retire-workspace-record",
                "restore-workspace-record",
            },
        )
        self.assertNotIn("transfer-custody", self.contract["actions"])

    def test_lifecycle_audit_is_read_only_and_history_backed(self) -> None:
        audit = copy.deepcopy(self.lifecycle_fixtures["audit"])
        self.assertFalse(audit["mutation"])
        self.assertLifecycleValid("audit", audit)

        audit["mutation"] = True
        self.assertLifecycleInvalid("audit", audit)

        audit = copy.deepcopy(self.lifecycle_fixtures["audit"])
        audit["history"][0].pop("receipt_ref")
        self.assertLifecycleInvalid("audit", audit)

    def test_ambiguous_transfer_is_rejected_by_both_protocols(self) -> None:
        custody_request = copy.deepcopy(self.fixtures["request"])
        custody_request["action"] = "transfer-custody"
        self.assertInvalid("request", custody_request)

        lifecycle_request = copy.deepcopy(self.lifecycle_fixtures["request"])
        lifecycle_request["action"] = "transfer-custody"
        self.assertLifecycleInvalid("request", lifecycle_request)

    def test_archive_request_requires_current_provider_state_and_binding(self) -> None:
        request = copy.deepcopy(self.lifecycle_fixtures["request"])
        self.assertEqual(lifecycle_request_issues(request), [])

        request["current_state"]["provider_lifecycle_state"] = "archived"
        self.assertIn(
            "provider archive requires current provider state active",
            lifecycle_request_issues(request),
        )

        request = copy.deepcopy(self.lifecycle_fixtures["request"])
        request["authority"]["provider_credential_binding_ref"] = None
        self.assertLifecycleInvalid("request", request)

    def test_workspace_transfer_is_provider_independent(self) -> None:
        request = copy.deepcopy(self.lifecycle_fixtures["request"])
        request["action"] = "transfer-workspace-custody"
        request["target"] = {
            "workspace_owner_ref": "repo:next-owner",
            "provider_lifecycle_state": None,
            "workspace_record_state": None,
        }
        request["authority"]["source_owner_acceptance_ref"] = {
            "uri": "https://workspace-governance.local/acceptance/source-owner",
            "digest": "sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        }
        request["authority"]["target_owner_acceptance_ref"] = {
            "uri": "https://workspace-governance.local/acceptance/target-owner",
            "digest": "sha256:cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
        }
        request["authority"]["provider_credential_binding_ref"] = None
        self.assertLifecycleValid("request", request)
        self.assertEqual(lifecycle_request_issues(request), [])

        request["target"]["workspace_owner_ref"] = request["current_state"][
            "workspace_owner_ref"
        ]
        self.assertIn(
            "workspace custody transfer must select a different owner",
            lifecycle_request_issues(request),
        )

    def test_reversal_requests_bind_the_receipt_being_reversed(self) -> None:
        request = copy.deepcopy(self.lifecycle_fixtures["request"])
        request["action"] = "unarchive-provider"
        request["current_state"]["provider_lifecycle_state"] = "archived"
        request["target"]["provider_lifecycle_state"] = "active"
        self.assertLifecycleInvalid("request", request)

        request["reversal_of_receipt_ref"] = {
            "uri": "https://oos.local/repository-lifecycle/receipts/example-archive-001",
            "digest": "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        }
        self.assertLifecycleValid("request", request)
        self.assertEqual(lifecycle_request_issues(request), [])

    def test_workspace_retirement_does_not_require_provider_credentials(self) -> None:
        request = copy.deepcopy(self.lifecycle_fixtures["request"])
        request["action"] = "retire-workspace-record"
        request["target"] = {
            "workspace_owner_ref": None,
            "provider_lifecycle_state": None,
            "workspace_record_state": "retired",
        }
        request["authority"]["provider_credential_binding_ref"] = None
        self.assertLifecycleValid("request", request)
        self.assertEqual(lifecycle_request_issues(request), [])

    def test_workspace_restore_requires_retirement_receipt(self) -> None:
        request = copy.deepcopy(self.lifecycle_fixtures["request"])
        request["action"] = "restore-workspace-record"
        request["current_state"]["workspace_record_state"] = "retired"
        request["target"] = {
            "workspace_owner_ref": None,
            "provider_lifecycle_state": None,
            "workspace_record_state": "active",
        }
        request["authority"]["provider_credential_binding_ref"] = None
        self.assertLifecycleInvalid("request", request)

        request["reversal_of_receipt_ref"] = {
            "uri": "https://oos.local/repository-lifecycle/receipts/example-retire-001",
            "digest": "sha256:abababababababababababababababababababababababababababababababab",
        }
        self.assertLifecycleValid("request", request)
        self.assertEqual(lifecycle_request_issues(request), [])

    def test_blocking_impact_requires_explicit_disposition(self) -> None:
        request = copy.deepcopy(self.lifecycle_fixtures["request"])
        request["impact"]["blocking_finding_count"] = 1
        self.assertLifecycleInvalid("request", request)

        request["impact"]["blocker_disposition"] = {
            "decision": "workaround",
            "justification": "The consumer remains readable during archive.",
            "evidence_ref": {
                "uri": "https://wgcf.local/repository-impact/workaround-001",
                "digest": "sha256:dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd",
            },
        }
        self.assertLifecycleValid("request", request)

        request["impact"]["blocking_finding_count"] = 3
        self.assertIn(
            "blocking_finding_count cannot exceed finding_count",
            lifecycle_request_issues(request),
        )

    def test_deferred_impact_cannot_produce_allowed_decision(self) -> None:
        decision = copy.deepcopy(self.lifecycle_fixtures["decision"])
        decision["impact"]["blocking_finding_count"] = 1
        decision["impact"]["blocker_disposition"] = {
            "decision": "defer",
            "justification": "The blocking consumer will be handled later.",
            "evidence_ref": {
                "uri": "https://wgcf.local/repository-impact/defer-001",
                "digest": "sha256:eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
            },
        }
        self.assertLifecycleInvalid("decision", decision)

        decision["outcome"] = "requires-action"
        decision["approved_target"] = None
        decision["next_action"] = "request-correction"
        self.assertLifecycleValid("decision", decision)

    def test_allowed_decision_binds_action_specific_target_and_next_action(self) -> None:
        decision = copy.deepcopy(self.lifecycle_fixtures["decision"])
        decision["approved_target"]["provider_lifecycle_state"] = "active"
        self.assertLifecycleInvalid("decision", decision)

        decision = copy.deepcopy(self.lifecycle_fixtures["decision"])
        decision["action"] = "restore-workspace-record"
        decision["current_state"]["workspace_record_state"] = "retired"
        decision["approved_target"] = {
            "workspace_owner_ref": None,
            "provider_lifecycle_state": None,
            "workspace_record_state": "active",
        }
        decision["required_human_gates"] = ["exact-operator-approval"]
        decision["next_action"] = "restore-workspace-record"
        self.assertLifecycleValid("decision", decision)

    def test_successful_provider_lifecycle_receipt_preserves_other_axes(self) -> None:
        receipt = copy.deepcopy(self.lifecycle_fixtures["receipt"])
        self.assertEqual(lifecycle_receipt_issues(receipt), [])

        receipt["after"]["workspace_record_state"] = "retired"
        self.assertIn(
            "provider lifecycle action cannot change workspace_record_state",
            lifecycle_receipt_issues(receipt),
        )

    def test_successful_workspace_lifecycle_receipt_cannot_claim_readback(self) -> None:
        receipt = copy.deepcopy(self.lifecycle_fixtures["receipt"])
        receipt["action"] = "retire-workspace-record"
        receipt["provider_readback_ref"] = None
        receipt["after"]["provider_lifecycle_state"] = "active"
        receipt["after"]["provider_version"] = receipt["before"]["provider_version"]
        receipt["after"]["workspace_record_state"] = "retired"
        receipt["confirmations"]["provider_credential_binding_ref"] = None
        self.assertLifecycleValid("receipt", receipt)
        self.assertEqual(lifecycle_receipt_issues(receipt), [])

    def test_successful_reversal_receipt_references_prior_history(self) -> None:
        receipt = copy.deepcopy(self.lifecycle_fixtures["receipt"])
        receipt["action"] = "unarchive-provider"
        receipt["before"]["provider_lifecycle_state"] = "archived"
        receipt["after"]["provider_lifecycle_state"] = "active"
        receipt["reversal_of_receipt_ref"] = {
            "uri": "https://oos.local/repository-lifecycle/receipts/example-archive-001",
            "digest": "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        }
        self.assertLifecycleValid("receipt", receipt)
        self.assertEqual(lifecycle_receipt_issues(receipt), [])

        receipt["reversal_of_receipt_ref"] = None
        self.assertLifecycleInvalid("receipt", receipt)

    def test_failed_lifecycle_receipt_cannot_claim_state_change(self) -> None:
        receipt = copy.deepcopy(self.lifecycle_fixtures["receipt"])
        receipt["outcome"] = "failed"
        receipt["workflow_status"] = "failed"
        receipt["provider_readback_ref"] = None
        self.assertIn(
            "non-successful lifecycle receipt must preserve its before state",
            lifecycle_receipt_issues(receipt),
        )


if __name__ == "__main__":
    unittest.main()
