from __future__ import annotations

import copy
from pathlib import Path
import sys
import unittest

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = REPO_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from developer_integration_runtime_composition import runtime_composition_issues


ACTIVE_REPOS = {"platform-engineering", "root-owner", "provider-owner"}
LIFECYCLES = {"proposed", "build-admitted", "active", "suspended", "retired"}


def registry_fixture() -> dict:
    return {
        "profiles": {
            "root": {"lifecycle": "active", "runtime_owner": "platform-engineering"},
            "provider": {
                "lifecycle": "active",
                "runtime_owner": "platform-engineering",
            },
            "outside": {
                "lifecycle": "active",
                "runtime_owner": "platform-engineering",
            },
        },
        "runtime_compositions": {
            "example": {
                "owner_repo": "platform-engineering",
                "summary": "Example composition",
                "root_profile_id": "root",
                "profiles": {
                    "root": {"required_lifecycle": "active"},
                    "provider": {"required_lifecycle": "active"},
                },
                "dependencies": [
                    {
                        "consumer_profile_id": "root",
                        "provider_profile_id": "provider",
                        "endpoint_projections": [
                            {
                                "environment_variable": "PROVIDER_BASE_URL",
                                "scheme": "http",
                                "service_name": "provider-api",
                                "service_port": 8080,
                            }
                        ],
                    }
                ],
                "credential_bindings": {
                    "caller": {
                        "owner_repo": "platform-engineering",
                        "purpose": "Authenticate the caller",
                        "value_source": "runtime-generated",
                        "retention": "composition-lifetime",
                        "projections": [
                            {
                                "profile_id": "root",
                                "environment_variable": "CALLER_SECRET",
                            },
                            {
                                "profile_id": "provider",
                                "environment_variable": "SHARED_SECRET",
                            },
                        ],
                    }
                },
            }
        },
    }


def issues(registry: dict) -> list[str]:
    return runtime_composition_issues(
        registry,
        active_repos=ACTIVE_REPOS,
        allowed_lifecycles=LIFECYCLES,
    )


class RuntimeCompositionContractTests(unittest.TestCase):
    def test_workspace_registry_is_valid(self) -> None:
        registry = yaml.safe_load(
            (REPO_ROOT / "contracts" / "developer-integration-profiles.yaml").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            runtime_composition_issues(
                registry,
                active_repos={
                    payload["runtime_owner"]
                    for payload in registry["profiles"].values()
                },
                allowed_lifecycles=LIFECYCLES,
            ),
            [],
        )

    def test_unknown_profile_is_rejected(self) -> None:
        registry = registry_fixture()
        registry["runtime_compositions"]["example"]["profiles"]["missing"] = {
            "required_lifecycle": "active"
        }
        self.assertTrue(any("unknown profile 'missing'" in issue for issue in issues(registry)))

    def test_cycle_is_rejected(self) -> None:
        registry = registry_fixture()
        registry["runtime_compositions"]["example"]["dependencies"].append(
            {
                "consumer_profile_id": "provider",
                "provider_profile_id": "root",
            }
        )
        self.assertTrue(any("contains cycle" in issue for issue in issues(registry)))

    def test_duplicate_projection_is_rejected(self) -> None:
        registry = registry_fixture()
        binding = registry["runtime_compositions"]["example"]["credential_bindings"][
            "caller"
        ]
        binding["projections"].append(copy.deepcopy(binding["projections"][0]))
        self.assertTrue(any("repeats projection" in issue for issue in issues(registry)))

    def test_undeclared_consumer_is_rejected(self) -> None:
        registry = registry_fixture()
        registry["runtime_compositions"]["example"]["dependencies"].append(
            {
                "consumer_profile_id": "outside",
                "provider_profile_id": "provider",
            }
        )
        self.assertTrue(
            any("consumer 'outside' is not a declared" in issue for issue in issues(registry))
        )

    def test_ambiguous_runtime_owner_is_rejected(self) -> None:
        registry = registry_fixture()
        registry["profiles"]["provider"]["runtime_owner"] = "provider-owner"
        self.assertTrue(any("ambiguous runtime ownership" in issue for issue in issues(registry)))

    def test_tracked_credential_value_is_rejected(self) -> None:
        registry = registry_fixture()
        registry["runtime_compositions"]["example"]["credential_bindings"]["caller"][
            "secret_value"
        ] = "must-not-land"
        self.assertTrue(
            any("forbidden tracked credential value" in issue for issue in issues(registry))
        )


if __name__ == "__main__":
    unittest.main()
