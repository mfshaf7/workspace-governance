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

from product_publication_contract import (  # noqa: E402
    canonical_digest,
    contract_issues,
    manifest_issues,
    packet_issues,
    packet_request_digest,
    receipt_issues,
    replay_issues,
)


CONTRACT_PATH = REPO_ROOT / "contracts/product-publication.yaml"
PRODUCTS_PATH = REPO_ROOT / "contracts/products.yaml"
FIXTURE_ROOT = REPO_ROOT / "contracts/fixtures/product-publication"
SCHEMA_ROOT = REPO_ROOT / "contracts/schemas"


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class ProductPublicationContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = load_yaml(CONTRACT_PATH)
        self.products = load_yaml(PRODUCTS_PATH)
        self.manifest = load_json(FIXTURE_ROOT / "manifest.valid.json")
        self.packet = load_json(FIXTURE_ROOT / "packet.valid.json")
        self.receipt = load_json(FIXTURE_ROOT / "receipt.valid.json")
        self.schemas = {
            artifact: load_json(SCHEMA_ROOT / f"product-publication-{artifact}.schema.json")
            for artifact in ("manifest", "packet", "receipt")
        }

    def schema_issues(self, artifact: str, payload: dict) -> list[str]:
        validator = Draft202012Validator(
            self.schemas[artifact],
            format_checker=FormatChecker(),
        )
        return [error.message for error in validator.iter_errors(payload)]

    def restore_artifacts(self) -> tuple[dict, dict, dict, dict]:
        products = copy.deepcopy(self.products)
        product = products["products"]["governance-operations-console"]
        product["record"]["version"] = 3
        product["record"]["last_mutation"].update(
            {
                "id": "workspace-inventory-event:product:governance-operations-console:3",
                "action": "restore",
                "idempotency_key": "restore-governance-operations-console-3",
            }
        )
        lifecycle_receipt_ref = {
            "id": "workspace-inventory-lifecycle-receipt:restore-console:1",
            "digest": "sha256:" + "b" * 64,
        }
        history_event_ref = {
            "id": "workspace-inventory-event:product:governance-operations-console:1",
            "digest": "sha256:" + "c" * 64,
            "sequence": 3,
        }
        manifest = copy.deepcopy(self.manifest)
        manifest.update(
            {
                "schema_version": 2,
                "manifest_id": "product-publication-manifest:governance-operations-console:2",
                "product_record_ref": "workspace-governance://products/governance-operations-console/v3",
                "product_record_version": 3,
                "inventory_lifecycle_binding": {
                    "action": "restore",
                    "receipt_ref": lifecycle_receipt_ref,
                    "history_event_ref": history_event_ref,
                    "previous_event_ref": {
                        "id": "workspace-inventory-event:product:governance-operations-console:2",
                        "digest": "sha256:" + "d" * 64,
                    },
                    "after": {
                        "record_version": 3,
                        "record_digest": canonical_digest(product),
                        "posture": "active",
                    },
                },
            }
        )
        manifest["lifecycle_evidence"]["publication_posture"] = "unlisted"
        manifest["lifecycle_evidence"]["evidence_refs"].extend(
            [lifecycle_receipt_ref["id"], history_event_ref["id"]]
        )

        previous_receipt = {
            "receipt_id": "product-publication-receipt:governance-operations-console:2",
            "receipt_digest": "sha256:" + "e" * 64,
            "publication_version": 2,
            "publication_posture": "archived",
        }
        lifecycle_history_binding = {
            "inventory_lifecycle_receipt_ref": lifecycle_receipt_ref,
            "inventory_history_event_ref": history_event_ref,
        }
        packet = copy.deepcopy(self.packet)
        packet.update(
            {
                "schema_version": 2,
                "packet_id": "product-publication-packet:governance-operations-console:3",
                "request_id": "product-publication-request:governance-operations-console:3",
                "idempotency_key": "product-publication:governance-operations-console:restore:3",
                "expected_publication_version": 2,
                "action": "restore",
                "current_publication_posture": "archived",
                "target_publication": {
                    "posture": "unlisted",
                    "listing_scope": None,
                    "audience": None,
                    "access_class": None,
                },
                "previous_receipt": previous_receipt,
                "lifecycle_history_binding": copy.deepcopy(lifecycle_history_binding),
            }
        )
        packet["manifest_binding"].update(
            {
                "manifest_id": manifest["manifest_id"],
                "manifest_digest": canonical_digest(manifest),
            }
        )
        packet["request_digest"] = packet_request_digest(packet)

        receipt = copy.deepcopy(self.receipt)
        receipt.update(
            {
                "schema_version": 2,
                "receipt_id": "product-publication-receipt:governance-operations-console:3",
                "packet_id": packet["packet_id"],
                "request_id": packet["request_id"],
                "request_digest": packet["request_digest"],
                "manifest_digest": packet["manifest_binding"]["manifest_digest"],
                "publication_version": 3,
                "publication_posture": "unlisted",
                "previous_receipt": previous_receipt,
                "lifecycle_history_binding": copy.deepcopy(lifecycle_history_binding),
            }
        )
        return products, manifest, packet, receipt

    def test_canonical_contract_and_artifacts_are_valid(self) -> None:
        known_repos = {
            "workspace-governance",
            "workspace-governance-control-fabric",
            "operator-orchestration-service",
            "governance-operations-console",
            "security-architecture",
            "platform-engineering",
        }
        self.assertEqual(contract_issues(self.contract, known_repos=known_repos), [])
        self.assertEqual(self.schema_issues("manifest", self.manifest), [])
        self.assertEqual(self.schema_issues("packet", self.packet), [])
        self.assertEqual(self.schema_issues("receipt", self.receipt), [])
        self.assertEqual(manifest_issues(self.contract, self.manifest, self.products), [])
        self.assertEqual(packet_issues(self.contract, self.packet, self.manifest), [])
        self.assertEqual(receipt_issues(self.receipt, self.packet), [])
        self.assertEqual(
            self.packet["manifest_binding"]["manifest_digest"],
            canonical_digest(self.manifest),
        )
        self.assertEqual(self.packet["request_digest"], packet_request_digest(self.packet))
        obligations = self.contract["product_publication"]["manifest_obligations"]
        self.assertEqual(obligations["owner_revision_semantics"], "product-source-snapshot")
        self.assertEqual(
            obligations["manifest_custody_binding"],
            {
                "owner": "readiness-evaluation",
                "manifest_revision_location": "readiness-receipt",
                "manifest_revision_must_descend_from_owner_revision": True,
                "committed_manifest_digest_must_match_submitted_manifest": True,
            },
        )

    def test_missing_authority_evidence_is_rejected(self) -> None:
        invalid = copy.deepcopy(self.packet)
        del invalid["authority_refs"]["security_decision_ref"]

        self.assertTrue(self.schema_issues("packet", invalid))

    def test_schema_v2_restore_preserves_owner_and_publication_history(self) -> None:
        products, manifest, packet, receipt = self.restore_artifacts()

        self.assertEqual(self.schema_issues("manifest", manifest), [])
        self.assertEqual(self.schema_issues("packet", packet), [])
        self.assertEqual(self.schema_issues("receipt", receipt), [])
        self.assertEqual(manifest_issues(self.contract, manifest, products), [])
        self.assertEqual(packet_issues(self.contract, packet, manifest), [])
        self.assertEqual(receipt_issues(receipt, packet), [])

    def test_restore_rejects_listed_target_and_missing_archived_receipt(self) -> None:
        _, manifest, packet, _ = self.restore_artifacts()
        packet["target_publication"] = {
            "posture": "internal",
            "listing_scope": "workspace-portfolio",
            "audience": "workspace-operators",
            "access_class": "workspace-authenticated",
        }
        packet["previous_receipt"]["publication_posture"] = "internal"
        packet["request_digest"] = packet_request_digest(packet)

        schema_issues = self.schema_issues("packet", packet)
        semantic_issues = packet_issues(self.contract, packet, manifest)

        self.assertTrue(schema_issues)
        self.assertTrue(
            any("target publication posture must be unlisted" in issue for issue in semantic_issues),
            semantic_issues,
        )
        self.assertTrue(
            any("exact archived publication receipt" in issue for issue in semantic_issues),
            semantic_issues,
        )

    def test_restore_rejects_mismatched_owner_lifecycle_history(self) -> None:
        _, manifest, packet, receipt = self.restore_artifacts()
        packet["lifecycle_history_binding"]["inventory_history_event_ref"]["digest"] = (
            "sha256:" + "f" * 64
        )
        packet["request_digest"] = packet_request_digest(packet)
        receipt["request_digest"] = packet["request_digest"]

        issues = packet_issues(self.contract, packet, manifest)

        self.assertTrue(any("history event does not match" in issue for issue in issues), issues)

    def test_schema_v1_cannot_claim_restore(self) -> None:
        invalid = copy.deepcopy(self.packet)
        invalid["action"] = "restore"
        invalid["request_digest"] = packet_request_digest(invalid)

        self.assertTrue(self.schema_issues("packet", invalid))

    def test_unsupported_publication_values_are_rejected(self) -> None:
        invalid = copy.deepcopy(self.packet)
        invalid["target_publication"]["access_class"] = "anyone-with-link"

        self.assertTrue(self.schema_issues("packet", invalid))

    def test_contradictory_lifecycle_state_is_rejected(self) -> None:
        invalid = copy.deepcopy(self.manifest)
        invalid["lifecycle_state"] = "suspended"
        invalid["lifecycle_evidence"]["publication_posture"] = "internal"

        issues = manifest_issues(self.contract, invalid, self.products)

        self.assertTrue(any("lifecycle state does not match" in issue for issue in issues), issues)
        self.assertTrue(any("contradicts publication posture" in issue for issue in issues), issues)

    def test_manifest_must_bind_exact_inventory_owner_and_revision(self) -> None:
        invalid = copy.deepcopy(self.manifest)
        invalid["owner_repo"] = "platform-engineering"

        issues = manifest_issues(self.contract, invalid, self.products)

        self.assertTrue(any("runtime owner" in issue for issue in issues), issues)
        self.assertTrue(any("exact owner revision" in issue for issue in issues), issues)

    def test_stale_owner_revision_is_rejected_against_observed_source(self) -> None:
        issues = manifest_issues(
            self.contract,
            self.manifest,
            self.products,
            observed_owner_revision="b" * 40,
        )

        self.assertEqual(
            issues,
            ["manifest owner revision is stale against observed owner source"],
        )

    def test_target_posture_rechecks_lifecycle_eligibility(self) -> None:
        invalid_manifest = copy.deepcopy(self.manifest)
        invalid_manifest["lifecycle_evidence"]["project_phase"] = "delivery-governed"

        issues = packet_issues(self.contract, self.packet, invalid_manifest)

        self.assertTrue(any("target listed posture requires an operational" in issue for issue in issues), issues)

    def test_packet_rejects_mismatched_manifest_digest(self) -> None:
        invalid = copy.deepcopy(self.packet)
        invalid["manifest_binding"]["manifest_digest"] = "sha256:" + "f" * 64
        invalid["request_digest"] = packet_request_digest(invalid)

        issues = packet_issues(self.contract, invalid, self.manifest)

        self.assertTrue(any("manifest binding manifest_digest" in issue for issue in issues), issues)

    def test_posture_audience_scope_and_access_are_one_binding(self) -> None:
        invalid = copy.deepcopy(self.packet)
        invalid["target_publication"]["audience"] = "public"
        invalid["request_digest"] = packet_request_digest(invalid)

        issues = packet_issues(self.contract, invalid, self.manifest)

        self.assertTrue(any("audience contradicts" in issue for issue in issues), issues)

    def test_cross_boundary_authority_grant_is_rejected(self) -> None:
        invalid = copy.deepcopy(self.packet)
        invalid["grants"]["runtime_authority"] = True
        invalid["request_digest"] = packet_request_digest(invalid)

        self.assertTrue(self.schema_issues("packet", invalid))
        self.assertTrue(
            any("cross-boundary authority" in issue for issue in packet_issues(self.contract, invalid, self.manifest))
        )

    def test_idempotency_key_conflict_is_rejected(self) -> None:
        candidate = copy.deepcopy(self.packet)
        candidate["target_publication"] = {
            "posture": "client",
            "listing_scope": "client-portfolio",
            "audience": "authorized-clients",
            "access_class": "client-authorized",
        }
        candidate["request_digest"] = packet_request_digest(candidate)

        self.assertEqual(
            replay_issues(self.packet, candidate),
            ["idempotency key replay conflicts with different request content"],
        )

    def test_receipt_cannot_claim_a_different_manifest_or_version(self) -> None:
        invalid = copy.deepcopy(self.receipt)
        invalid["manifest_digest"] = "sha256:" + "b" * 64
        invalid["publication_version"] = 3

        issues = receipt_issues(invalid, self.packet)

        self.assertTrue(any("manifest_digest" in issue for issue in issues), issues)
        self.assertTrue(any("advance exactly once" in issue for issue in issues), issues)


if __name__ == "__main__":
    unittest.main()
