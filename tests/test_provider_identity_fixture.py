from pathlib import Path
import tempfile
import unittest

import yaml

from provider_identity_fixture import unused_provider_repository


class ProviderIdentityFixtureTests(unittest.TestCase):
    def test_avoids_intake_active_and_retired_bindings_without_rewriting_them(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            contracts = root / "contracts"
            contracts.mkdir()
            def binding(offset, suffix):
                return {"provider_repository": {"provider": "github",
                    "provider_repository_id": str(9_000_000_000_000_000 + offset),
                    "full_name": f"SYNTHETIC-FIXTURES/SAMPLE-SOURCE{suffix}"}}
            documents = {
                "intake-register.yaml": {"repos": {"proposed": binding(0, "")}},
                "repos.yaml": {"repos": {"active": binding(1, "-2")},
                               "retired_repos": {"retired": binding(2, "-3")}},
            }
            for filename, value in documents.items():
                (contracts / filename).write_text(yaml.safe_dump(value))
            before = {name: (contracts / name).read_bytes() for name in documents}
            result = unused_provider_repository(root)
            self.assertEqual(result, {"provider": "github",
                "provider_repository_id": "9000000000000003",
                "full_name": "synthetic-fixtures/sample-source-4"})
            self.assertEqual(result, unused_provider_repository(root))
            self.assertEqual(before, {name: (contracts / name).read_bytes() for name in documents})

    def test_unbound_legacy_entries_and_empty_intake_need_no_operator_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "contracts").mkdir()
            (root / "contracts/intake-register.yaml").write_text("repos: {}\n")
            (root / "contracts/repos.yaml").write_text("repos:\n  legacy: {}\n")
            self.assertEqual(unused_provider_repository(root), {"provider": "github",
                "provider_repository_id": "9000000000000000",
                "full_name": "synthetic-fixtures/sample-source"})
