from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = REPO_ROOT / "scripts"
VALIDATOR_PATH = SCRIPTS_ROOT / "validate_cross_repo_truth.py"


def load_validator():
    if str(SCRIPTS_ROOT) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_ROOT))
    spec = importlib.util.spec_from_file_location(
        "validate_cross_repo_truth_lifecycle_parity",
        VALIDATOR_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {VALIDATOR_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def capability_manifest() -> dict:
    capability_specs = [
        ("scoped-art-snapshot", "implemented", 2, True),
        ("historical-material-freshness", "implemented", 2, True),
        ("persistent-work-session", "implemented", 2, True),
        ("process-restart-reconstruction", "implemented", 2, True),
        ("worktree-relocation-reconstruction", "implemented", 2, True),
        ("exact-next-action", "implemented", 2, True),
        ("architecture-decision", "human-gated", 1, True),
        ("architecture-packet-persistence", "implemented", 1, True),
        ("architecture-packet-v3-adoption", "implemented", 3, False),
        ("transition-specific-human-gate-derivation", "implemented", 3, False),
        ("work-start-authoring", "implemented", 1, True),
        ("work-start-persistence", "implemented", 1, True),
        ("authoritative-review-evidence-projection", "implemented", 1, True),
        ("review-packet-v2-authoring", "implemented", 2, True),
        ("review-packet-merge-readiness", "implemented", 2, True),
        ("work-session-source-merge", "implemented", 1, True),
        ("operating-readiness", "implemented", 2, True),
        ("review-packet-finalization", "implemented", 2, True),
        ("art-closeout", "implemented", 2, True),
        ("work-session-resource-retirement", "human-gated", 1, True),
        ("resumable-lifecycle-reconciliation", "compatibility", 1, False),
        ("review-packet-v1-compatibility", "compatibility", 1, False),
        ("temporal-lifecycle-adapter", "planned", 1, False),
    ]
    capabilities = [
        {
            "id": capability_id,
            "state": state,
            "contract_version": version,
            "normal_path": normal_path,
        }
        for capability_id, state, version, normal_path in capability_specs
    ]
    next(
        capability
        for capability in capabilities
        if capability["id"] == "work-session-resource-retirement"
    )["activation_work_item_id"] = "work-item-970"
    return {
        "schema_version": 2,
        "contract_id": "operator-orchestration-service.delivery-art-lifecycle.v2",
        "owner_repo": "operator-orchestration-service",
        "normal_operator_surface": {
            "session_artifact_type": "delivery_art_work_session",
            "start_command": "npm run art -- work start <work-item-id>",
            "status_command": "npm run art -- work status <work-item-id>",
            "continue_command": "npm run art -- work continue <work-item-id>",
            "merge_command": "npm run art -- work merge <work-item-id>",
            "close_command": "npm run art -- work close <work-item-id>",
            "help_command": "npm run art -- work --help",
        },
        "target_operator_surface": {
            "primary_adapter": "governance-operations-console",
            "workflow_semantics_owner": "operator-orchestration-service",
            "cli_posture": "transitional-engineering-recovery-diagnostics",
            "shared_api_required": True,
            "adapter_local_state_machine_allowed": False,
        },
        "compatibility_operator_surface": {
            "plan_artifact_type": "delivery_art_lifecycle_plan",
            "status_command": "npm run art -- lifecycle status <plan.json>",
            "reconcile_command": "npm run art -- lifecycle reconcile <plan.json>",
        },
        "state_store": {
            "classification": "reconstructable-operator-coordination",
            "default_root": "${XDG_STATE_HOME:-${HOME}/.local/state}/operator-orchestration-service/delivery-art/work",
            "override_environment_variable": "OOS_ART_WORK_STATE_ROOT",
            "atomic_replace": True,
            "absolute_worktree_paths": False,
            "secrets": False,
        },
        "human_gates": [
            "architecture-decision",
            "landing-unit-decision",
            "exception-or-risk-acceptance",
            "pull-request-review",
            "source-merge",
            "security-acceptance",
            "art-closeout",
        ],
        "capabilities": capabilities,
    }


class DeliveryArtLifecycleParityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.validator = load_validator()
        contract = yaml.safe_load(
            (REPO_ROOT / "contracts/delivery-art-operator-path.yaml").read_text(
                encoding="utf-8"
            )
        )
        cls.operator_path = contract["delivery_art_operator_path"]
        cls.work_session_contract = cls.operator_path["work_session_lifecycle"]

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace_root = Path(self.temp_dir.name)
        self.owner_repo = self.workspace_root / "operator-orchestration-service"
        self.manifest_path = (
            self.owner_repo
            / "contracts"
            / "delivery-art-lifecycle"
            / "capabilities.json"
        )
        self.manifest_path.parent.mkdir(parents=True)
        self.manifest = capability_manifest()
        self.manifest_path.write_text(
            json.dumps(self.manifest, indent=2) + "\n",
            encoding="utf-8",
        )
        self.manifest_digest = "sha256:" + hashlib.sha256(
            self.manifest_path.read_bytes()
        ).hexdigest()
        subprocess.run(["git", "init", "--quiet", str(self.owner_repo)], check=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.invalid"],
            cwd=self.owner_repo,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Lifecycle Parity Test"],
            cwd=self.owner_repo,
            check=True,
        )
        subprocess.run(["git", "add", "."], cwd=self.owner_repo, check=True)
        subprocess.run(
            ["git", "commit", "--quiet", "-m", "Add lifecycle manifest"],
            cwd=self.owner_repo,
            check=True,
        )
        self.commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=self.owner_repo,
            text=True,
            capture_output=True,
            check=True,
        ).stdout.strip()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def activation(self) -> dict:
        return {
            "capability_source": {
                "repo": "operator-orchestration-service",
                "manifest_path": "contracts/delivery-art-lifecycle/capabilities.json",
                "manifest_digest": self.manifest_digest,
                "activated_at_commit": self.commit,
            },
            "capability_projection": copy.deepcopy(self.manifest),
        }

    def test_exact_owner_manifest_projection_passes(self) -> None:
        errors = self.validator.delivery_art_lifecycle_capability_parity_errors(
            self.workspace_root,
            self.activation(),
        )

        self.assertEqual(errors, [])

    def test_active_work_session_contract_passes(self) -> None:
        errors = self.validator.delivery_art_work_session_contract_errors(
            copy.deepcopy(self.work_session_contract)
        )

        self.assertEqual(errors, [])

    def test_architecture_v3_is_the_activated_normal_packet(self) -> None:
        architecture_contract = self.operator_path["artifact_contracts"][
            "architecture_packet"
        ]
        activation_packet = self.operator_path["contract_activation"][
            "activation_evidence"
        ]["architecture_packet"]
        readiness_rules = self.operator_path["readiness_model"]["rules"]

        self.assertEqual(architecture_contract["schema_version"], 3)
        self.assertEqual(
            architecture_contract["compatibility_schema_versions"], [1, 2]
        )
        self.assertEqual(activation_packet["schema_version"], 3)
        self.assertEqual(
            activation_packet["artifact_id"],
            "architecture-packet:delivery-892-v1",
        )
        self.assertEqual(
            activation_packet["artifact_ref"].rsplit("/", 1)[-1],
            activation_packet["content_digest"].removeprefix("sha256:"),
        )
        self.assertTrue(
            readiness_rules[
                "architecture_v3_start_and_close_schedule_is_satisfiable"
            ]
        )
        self.assertTrue(
            readiness_rules[
                "architecture_v3_gate_evidence_precedes_authority_close"
            ]
        )

    def test_work_session_cannot_downgrade_after_activation(self) -> None:
        work_session = copy.deepcopy(self.work_session_contract)
        work_session["state"] = "implemented-pending-activation"

        errors = self.validator.delivery_art_work_session_contract_errors(
            work_session
        )

        self.assertIn(
            "work-session lifecycle must remain active in dev-integration after governed activation",
            errors,
        )

    def test_work_session_command_drift_fails(self) -> None:
        work_session = copy.deepcopy(self.work_session_contract)
        work_session["commands"]["continue"] = (
            "npm run art -- work reconcile <work-item-id>"
        )

        errors = self.validator.delivery_art_work_session_contract_errors(
            work_session
        )

        self.assertIn(
            "work-session lifecycle command family differs from the approved contract",
            errors,
        )

    def test_active_work_session_is_owner_manifest_normal_surface(self) -> None:
        active_commands = self.manifest["normal_operator_surface"]
        work_session_commands = self.work_session_contract["commands"]

        self.assertEqual(
            active_commands,
            {
                "session_artifact_type": "delivery_art_work_session",
                "start_command": work_session_commands["start"],
                "status_command": work_session_commands["status"],
                "continue_command": work_session_commands["continue"],
                "merge_command": work_session_commands["merge"],
                "close_command": work_session_commands["close"],
                "help_command": work_session_commands["help"],
            },
        )

    def test_projection_drift_fails(self) -> None:
        activation = self.activation()
        activation["capability_projection"]["normal_operator_surface"][
            "continue_command"
        ] = "npm run art -- work reconcile <work-item-id>"

        errors = self.validator.delivery_art_lifecycle_capability_parity_errors(
            self.workspace_root,
            activation,
        )

        self.assertIn(
            "capability projection differs from the OOS lifecycle source manifest",
            errors,
        )

    def test_manifest_change_requires_refreshed_activation_commit(self) -> None:
        changed_manifest = copy.deepcopy(self.manifest)
        changed_manifest["capabilities"][-1]["contract_version"] = 2
        self.manifest_path.write_text(
            json.dumps(changed_manifest, indent=2) + "\n",
            encoding="utf-8",
        )
        activation = self.activation()
        activation["capability_projection"] = changed_manifest

        errors = self.validator.delivery_art_lifecycle_capability_parity_errors(
            self.workspace_root,
            activation,
        )

        self.assertIn(
            "owner lifecycle manifest differs from the activation commit; activation evidence must be refreshed",
            errors,
        )

    def test_shallow_checkout_cannot_skip_missing_activation_commit(self) -> None:
        (self.owner_repo / "README.md").write_text(
            "Unrelated owner-repo change.\n",
            encoding="utf-8",
        )
        subprocess.run(["git", "add", "README.md"], cwd=self.owner_repo, check=True)
        subprocess.run(
            ["git", "commit", "--quiet", "-m", "Add unrelated owner change"],
            cwd=self.owner_repo,
            check=True,
        )
        validation_workspace = self.workspace_root / "validation-workspace"
        validation_workspace.mkdir()
        shallow_owner_repo = validation_workspace / "operator-orchestration-service"
        subprocess.run(
            [
                "git",
                "clone",
                "--quiet",
                "--depth",
                "1",
                self.owner_repo.as_uri(),
                str(shallow_owner_repo),
            ],
            check=True,
        )

        errors = self.validator.delivery_art_lifecycle_capability_parity_errors(
            validation_workspace,
            self.activation(),
        )

        self.assertIn(
            "capability activation commit is absent from the OOS repository",
            errors,
        )


if __name__ == "__main__":
    unittest.main()
