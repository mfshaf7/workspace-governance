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
            "root": {
                "lifecycle": "active",
                "runtime_owner": "platform-engineering",
                "actions": ["up", "status", "down"],
            },
            "provider": {
                "lifecycle": "active",
                "runtime_owner": "platform-engineering",
                "actions": ["up", "status", "down"],
            },
            "outside": {
                "lifecycle": "active",
                "runtime_owner": "platform-engineering",
                "actions": ["up", "status", "down"],
            },
        },
        "runtime_compositions": {
            "example": {
                "lifecycle": "active",
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
                                "address_format": "url",
                                "scheme": "http",
                                "service_name": "provider-api",
                                "service_port": 8080,
                            }
                        ],
                    }
                ],
                "caller_bindings": {
                    "caller": {
                        "owner_repo": "platform-engineering",
                        "purpose": "Bind the caller identity",
                        "caller_id": "root-service",
                        "consumer_profile_id": "root",
                        "provider_profile_id": "provider",
                        "consumer_environment_variable": "CALLER_ID",
                        "provider_environment_variable": "ALLOWED_CALLERS",
                    }
                },
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
                "profile_bindings": {},
                "execution": {
                    "startup_action": "up",
                    "readiness_action": "status",
                    "teardown_action": "down",
                    "startup_order": "dependency-first",
                    "teardown_order": "reverse-startup",
                    "cleanup_owner_repo": "platform-engineering",
                    "rollback_started_profiles_on_failure": True,
                    "preserve_profile_state_on_teardown": True,
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

    def test_refinement_catalog_composition_is_active_and_console_safe(self) -> None:
        registry = yaml.safe_load(
            (REPO_ROOT / "contracts" / "developer-integration-profiles.yaml").read_text(
                encoding="utf-8"
            )
        )
        composition = registry["runtime_compositions"]["refinement-catalog"]
        self.assertEqual(composition["lifecycle"], "active")
        self.assertEqual(
            set(composition["profiles"]),
            {
                "accepted-idea-delivery",
                "context-governance-gateway",
                "governed-ai-gateway",
                "governance-control-fabric",
                "temporal",
            },
        )
        self.assertNotIn("governance-operations-console", composition["profiles"])
        temporal = registry["profiles"]["temporal"]
        self.assertEqual(temporal["lifecycle"], "active")
        self.assertEqual(
            temporal["admission"]["platform_acceptance_ref"],
            "github://mfshaf7/platform-engineering/pull/224",
        )
        self.assertEqual(
            temporal["admission"]["security_review_refs"][0]["path"],
            "docs/reviews/components/2026-08-26-refinement-catalog-dev-integration-boundary.md",
        )
        temporal_projection = next(
            projection
            for dependency in composition["dependencies"]
            if dependency["provider_profile_id"] == "temporal"
            for projection in dependency["endpoint_projections"]
        )
        self.assertEqual(temporal_projection["address_format"], "host-port")
        self.assertEqual(
            composition["profile_bindings"]["refinement-temporal-namespace"],
            {
                "owner_repo": "platform-engineering",
                "purpose": "Bind OOS Refinement execution to the operator-scoped Temporal workflow namespace.",
                "profile_id": "accepted-idea-delivery",
                "environment_variable": "OOS_TEMPORAL_NAMESPACE",
                "source": {
                    "kind": "operator-template",
                    "template": "governance-{operator}",
                },
            },
        )
        namespace_bindings = {
            binding_id: binding
            for binding_id, binding in composition["profile_bindings"].items()
            if binding["source"]["kind"] == "profile-namespace"
        }
        self.assertEqual(
            {
                binding_id: (
                    binding["profile_id"],
                    binding["environment_variable"],
                    binding["source"]["source_profile_id"],
                )
                for binding_id, binding in namespace_bindings.items()
            },
            {
                "temporal-oos-kubernetes-namespace": (
                    "temporal",
                    "DEVINT_TEMPORAL_OOS_KUBERNETES_NAMESPACE",
                    "accepted-idea-delivery",
                ),
                "temporal-wgcf-kubernetes-namespace": (
                    "temporal",
                    "DEVINT_TEMPORAL_WGCF_KUBERNETES_NAMESPACE",
                    "governance-control-fabric",
                ),
                "governed-ai-trusted-consumer-namespace": (
                    "governed-ai-gateway",
                    "DEVINT_GAI_TRUSTED_CONSUMER_NAMESPACE",
                    "accepted-idea-delivery",
                ),
            },
        )
        self.assertEqual(
            composition["execution"],
            {
                "startup_action": "up",
                "readiness_action": "status",
                "teardown_action": "down",
                "startup_order": "dependency-first",
                "teardown_order": "reverse-startup",
                "cleanup_owner_repo": "platform-engineering",
                "rollback_started_profiles_on_failure": True,
                "preserve_profile_state_on_teardown": True,
            },
        )

    def test_refinement_catalog_activation_fails_if_temporal_regresses(self) -> None:
        registry = yaml.safe_load(
            (REPO_ROOT / "contracts" / "developer-integration-profiles.yaml").read_text(
                encoding="utf-8"
            )
        )
        registry["profiles"]["temporal"]["lifecycle"] = "build-admitted"
        self.assertTrue(
            any(
                "refinement-catalog.profiles.temporal requires lifecycle 'active'"
                in issue
                for issue in runtime_composition_issues(
                    registry,
                    active_repos={
                        payload["runtime_owner"]
                        for payload in registry["profiles"].values()
                    },
                    allowed_lifecycles=LIFECYCLES,
                )
            )
        )

    def test_temporal_commissioning_history_is_separate_from_current_runtime(self) -> None:
        registry = yaml.safe_load(
            (REPO_ROOT / "contracts" / "developer-integration-profiles.yaml").read_text(
                encoding="utf-8"
            )
        )
        orchestration = yaml.safe_load(
            (REPO_ROOT / "contracts" / "durable-orchestration.yaml").read_text(
                encoding="utf-8"
            )
        )
        admission = orchestration["durable_orchestration"]["admission"]

        self.assertEqual(
            admission["controlled_proof"]["target"]["profile_lifecycle"],
            "build-admitted",
        )
        self.assertEqual(admission["current_runtime"]["lifecycle"], "active")
        self.assertEqual(registry["profiles"]["temporal"]["lifecycle"], "active")
        self.assertIn("build_admission", registry["profiles"]["temporal"])

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

    def test_active_composition_rejects_profile_lifecycle_mismatch(self) -> None:
        registry = registry_fixture()
        registry["profiles"]["provider"]["lifecycle"] = "build-admitted"
        self.assertTrue(any("requires lifecycle" in issue for issue in issues(registry)))

    def test_proposed_composition_allows_future_active_profile_requirement(self) -> None:
        registry = registry_fixture()
        registry["runtime_compositions"]["example"]["lifecycle"] = "proposed"
        registry["profiles"]["provider"]["lifecycle"] = "build-admitted"
        self.assertEqual(issues(registry), [])

    def test_caller_binding_must_follow_a_declared_dependency(self) -> None:
        registry = registry_fixture()
        registry["runtime_compositions"]["example"]["profiles"]["outside"] = {
            "required_lifecycle": "active"
        }
        binding = registry["runtime_compositions"]["example"]["caller_bindings"][
            "caller"
        ]
        binding["provider_profile_id"] = "outside"
        self.assertTrue(any("does not match a declared dependency" in issue for issue in issues(registry)))

    def test_execution_actions_must_exist_on_every_profile(self) -> None:
        registry = registry_fixture()
        registry["profiles"]["provider"]["actions"].remove("down")
        self.assertTrue(any("teardown_action" in issue for issue in issues(registry)))

    def test_profile_binding_must_be_owned_and_projection_unique(self) -> None:
        registry = registry_fixture()
        registry["runtime_compositions"]["example"]["profile_bindings"] = {
            "duplicate": {
                "owner_repo": "platform-engineering",
                "purpose": "Deliberately duplicate a projected variable",
                "profile_id": "root",
                "environment_variable": "PROVIDER_BASE_URL",
                "source": {"kind": "literal", "value": "true"},
            }
        }
        self.assertTrue(any("repeats projection" in issue for issue in issues(registry)))

    def test_profile_binding_rejects_unknown_namespace_source(self) -> None:
        registry = registry_fixture()
        registry["runtime_compositions"]["example"]["profile_bindings"] = {
            "namespace": {
                "owner_repo": "platform-engineering",
                "purpose": "Project a participant namespace",
                "profile_id": "root",
                "environment_variable": "PROVIDER_NAMESPACE",
                "source": {
                    "kind": "profile-namespace",
                    "source_profile_id": "missing",
                },
            }
        }
        self.assertTrue(
            any(
                "is not a declared composition profile" in issue
                for issue in issues(registry)
            )
        )

    def test_profile_binding_rejects_unbounded_operator_template(self) -> None:
        registry = registry_fixture()
        registry["runtime_compositions"]["example"]["profile_bindings"] = {
            "namespace": {
                "owner_repo": "platform-engineering",
                "purpose": "Project an operator namespace",
                "profile_id": "root",
                "environment_variable": "WORKFLOW_NAMESPACE",
                "source": {
                    "kind": "operator-template",
                    "template": "governance-{operator}-{operator}",
                },
            }
        }
        self.assertTrue(
            any(
                "must contain exactly one {operator} token" in issue
                for issue in issues(registry)
            )
        )

    def test_profile_binding_rejects_unsupported_source_kind(self) -> None:
        registry = registry_fixture()
        registry["runtime_compositions"]["example"]["profile_bindings"] = {
            "namespace": {
                "owner_repo": "platform-engineering",
                "purpose": "Project an unsupported source",
                "profile_id": "root",
                "environment_variable": "WORKFLOW_NAMESPACE",
                "source": {"kind": "environment"},
            }
        }
        self.assertTrue(
            any(
                "source.kind 'environment' is unsupported" in issue
                for issue in issues(registry)
            )
        )

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
