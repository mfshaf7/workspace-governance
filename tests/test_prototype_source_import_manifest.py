from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]


def example() -> dict:
    """Synthetic schema input, never a live source/ownership receipt."""
    return {
        "schema_version": 1,
        "artifact_type": "prototype-source-import-manifest",
        "prototype_id": "example-prototype",
        "owner_repo": "example-owner",
        "provider_repository": {
            "provider": "github", "provider_repository_id": "123",
            "full_name": "example-workspace/example-owner",
        },
        "delivery_target_ref": "openproject://work_packages/123",
        "delivery_packet_ref": "record://delivery-packets/example-packet",
        "accepted_delivery_target_receipt_ref": "oos://receipts/prototype-delivery-application/" + "a" * 64,
        "prototype_source_revision": "b" * 40,
        "requested_custody": "dedicated-owner-repo",
        "transfer_strategy": "already-owned",
        "file_mappings": [{
            "source_path": "prototypes/example-prototype/app.mjs",
            "owner_path": "app/app.mjs", "sha256": "sha256:" + "c" * 64,
        }],
    }


class PrototypeSourceImportSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        schema = json.loads((ROOT / "contracts/schemas/prototype-source-import-manifest.schema.json").read_text())
        Draft202012Validator.check_schema(schema)
        cls.validator = Draft202012Validator(schema)

    def test_both_existing_transfer_strategies_and_owner_shapes(self):
        for strategy in ("transfer", "already-owned"):
            for custody in ("dedicated-owner-repo", "shared-owner-repo"):
                with self.subTest(strategy=strategy, custody=custody):
                    data = example()
                    data.update(transfer_strategy=strategy, requested_custody=custody)
                    self.assertEqual(list(self.validator.iter_errors(data)), [])

    def test_source_metadata_cannot_claim_future_ownership_or_approval(self):
        for key, value in (
            ("owner_revision", "d" * 40),
            ("owner_merge_commit", "d" * 40),
            ("human_approval", "approved"),
            ("receipt", "receipt://invented"),
            ("runtime_activation", True),
            ("authority_grants", {"source": True}),
        ):
            with self.subTest(field=key):
                data = example()
                data[key] = value
                self.assertFalse(self.validator.is_valid(data))

    def test_every_binding_is_required(self):
        for key in example():
            with self.subTest(field=key):
                data = example()
                del data[key]
                self.assertFalse(self.validator.is_valid(data))

    def test_unsafe_and_unbounded_paths_are_not_source_selectors(self):
        for value in ("/etc/passwd", "../app.js", "app/../app.js", "./app.js",
                      "app//x.js", ".git/config", "app/.git/config", "app\\x.js",
                      "app/x.js\x00", "https://example.test/x", "x" * 513):
            for field in ("source_path", "owner_path"):
                with self.subTest(path=value, field=field):
                    data = example()
                    data["file_mappings"][0][field] = value
                    self.assertFalse(self.validator.is_valid(data))

    def test_no_empty_oversized_or_identically_duplicated_mapping(self):
        for mappings in ([], [example()["file_mappings"][0]] * 2,
                         [dict(example()["file_mappings"][0], owner_path=f"app/{i}.mjs") for i in range(129)]):
            with self.subTest(length=len(mappings)):
                data = example()
                data["file_mappings"] = mappings
                self.assertFalse(self.validator.is_valid(data))

    def test_reference_provider_and_commit_shapes_are_closed(self):
        mutations = [
            ("prototype_source_revision", "main"),
            ("delivery_target_ref", "openproject://work_packages/0"),
            ("delivery_packet_ref", "record://other/example-packet"),
            ("accepted_delivery_target_receipt_ref", "receipt://unverified"),
            ("requested_custody", "incubation-repo"),
            ("transfer_strategy", "copy-and-claim"),
        ]
        for key, value in mutations:
            with self.subTest(field=key):
                data = example()
                data[key] = value
                self.assertFalse(self.validator.is_valid(data))
        for field, value in (("provider", "other"), ("provider_repository_id", "0"),
                             ("full_name", "https://github.com/example/repo")):
            data = copy.deepcopy(example())
            data["provider_repository"][field] = value
            self.assertFalse(self.validator.is_valid(data))


if __name__ == "__main__":
    unittest.main()
