import importlib.util
from pathlib import Path
import sys
import unittest


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location("workspace_layout_provider_binding", SCRIPTS / "audit_workspace_layout.py")
layout = importlib.util.module_from_spec(spec)
spec.loader.exec_module(layout)


class RepositoryOriginTests(unittest.TestCase):
    def test_legacy_origin_is_unchanged(self):
        self.assertEqual(layout.expected_repository_origin("existing-owner", {}),
                         "git@github.com:mfshaf7/existing-owner.git")

    def test_organization_coordinates_are_canonical_not_inferred_from_local_name(self):
        binding = {"provider": "github", "provider_repository_id": "123456789",
                   "full_name": "example-organization/provider-renamed-owner"}
        self.assertEqual(layout.expected_repository_origin("local-owner", {"provider_repository": binding}),
                         "git@github.com:example-organization/provider-renamed-owner.git")

    def test_present_but_invalid_binding_never_falls_back_to_personal_origin(self):
        for binding in [{}, None, {"provider": "gitlab", "provider_repository_id": "123",
                                  "full_name": "example/owner"},
                        {"provider": "github", "provider_repository_id": "123", "full_name": "../owner"},
                        {"provider": "github", "provider_repository_id": "123", "full_name": "example/.."},
                        {"provider": "github", "provider_repository_id": "0", "full_name": "example/owner"}]:
            with self.subTest(binding=binding), self.assertRaises(ValueError):
                layout.expected_repository_origin("local-owner", {"provider_repository": binding})


if __name__ == "__main__":
    unittest.main()
