from __future__ import annotations

import importlib.util
import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = REPO_ROOT / "scripts"
CATALOG_PATH = REPO_ROOT / "contracts" / "governance-validator-catalog.yaml"
LAYOUT_AUDIT_PATH = REPO_ROOT / "scripts" / "audit_workspace_layout.py"
BRANCH_AUDIT_PATH = REPO_ROOT / "scripts" / "audit_branch_lifecycle.py"
DEV_INTEGRATION_VALIDATOR_PATH = REPO_ROOT / "scripts" / "validate_developer_integration.py"


def load_catalog() -> dict:
    return yaml.safe_load(CATALOG_PATH.read_text())["governance_validator_catalog"]


def load_script_module(name: str, path: Path):
    if str(SCRIPTS_ROOT) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_ROOT))
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class ValidationModeContractTests(unittest.TestCase):
    def test_modes_keep_distinct_source_and_scope_boundaries(self) -> None:
        modes = load_catalog()["validation_modes"]
        self.assertEqual(
            modes,
            {
                "owner-smoke": {
                    "description": modes["owner-smoke"]["description"],
                    "source_binding": "exact-active-worktree",
                    "invocation_authority": "owner-repo-direct",
                    "catalog_tier": "smoke",
                    "remote_reads_allowed": False,
                    "clean_workspace_required": False,
                    "cross_repo_scope": "none",
                },
                "landing-unit": {
                    "description": modes["landing-unit"]["description"],
                    "source_binding": "exact-pr-head-and-base",
                    "invocation_authority": "owner-repo-ci-equivalent",
                    "catalog_tier": "scoped",
                    "remote_reads_allowed": True,
                    "clean_workspace_required": False,
                    "cross_repo_scope": "affected-only",
                },
                "workspace-clean-state": {
                    "description": modes["workspace-clean-state"]["description"],
                    "source_binding": "canonical-workspace-heads",
                    "invocation_authority": "wgcf-catalog",
                    "catalog_tier": "scoped",
                    "remote_reads_allowed": True,
                    "clean_workspace_required": True,
                    "cross_repo_scope": "source-state-only",
                },
                "release": {
                    "description": modes["release"]["description"],
                    "source_binding": "reviewed-release-heads",
                    "invocation_authority": "wgcf-catalog-and-owner",
                    "catalog_tier": "release",
                    "remote_reads_allowed": True,
                    "clean_workspace_required": False,
                    "cross_repo_scope": "all-declared",
                },
            },
        )

    def test_component_smoke_selects_only_fast_owner_checks(self) -> None:
        entries = load_catalog()["entries"]
        selected = {
            entry_id
            for entry_id, payload in entries.items()
            if (invocation := payload.get("wgcf_invocation"))
            and invocation["enabled"]
            and invocation["validation_tier"] == "smoke"
            and "component:workspace-governance" in invocation["scopes"]
        }
        self.assertEqual(
            selected,
            {
                "repo-structure",
                "contract-model",
            },
        )

    def test_shadow_parity_is_scoped_cross_repo_proof(self) -> None:
        shadow = load_catalog()["entries"]["governance-engine-shadow-parity"]
        invocation = shadow["wgcf_invocation"]

        self.assertEqual(shadow["scope"], "workspace-cross-repo")
        self.assertEqual(shadow["safety_class"], "workspace-cross-repo-read")
        self.assertTrue(shadow["requires_workspace_root"])
        self.assertEqual(invocation["validation_tier"], "scoped")
        self.assertEqual(
            invocation["scopes"],
            ["component:workspace-governance", "authority:workspace-clean-state"],
        )

    def test_clean_state_scope_owns_branch_hygiene(self) -> None:
        entries = load_catalog()["entries"]
        branch = entries["branch-lifecycle"]["wgcf_invocation"]
        layout = entries["workspace-layout"]["wgcf_invocation"]

        self.assertEqual(branch["scopes"], ["authority:workspace-clean-state"])
        self.assertIn("--include-remote", branch["command"])
        self.assertIn("--check-clean", branch["command"])
        self.assertNotIn("--check-clean", layout["command"])


class AuditBoundaryTests(unittest.TestCase):
    def test_workspace_layout_audit_does_not_orchestrate_other_controls(self) -> None:
        source = LAYOUT_AUDIT_PATH.read_text()
        forbidden = (
            "--check-clean",
            "audit_branch_lifecycle.py",
            "validate_contracts.py",
            "validate_cross_repo_truth.py",
            "validate_intake.py",
            "validate_security_bindings.py",
            "validate_review_coverage.py",
            "validate_learning_closure.py",
            "install_skills.py",
        )
        for token in forbidden:
            with self.subTest(token=token):
                self.assertNotIn(token, source)

    def test_branch_clean_state_detects_dirty_worktree(self) -> None:
        branch_audit = load_script_module("audit_branch_lifecycle", BRANCH_AUDIT_PATH)
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            subprocess.run(
                ["git", "init", "--quiet", str(repo_root)],
                check=True,
                text=True,
                capture_output=True,
            )
            self.assertFalse(branch_audit.worktree_is_dirty(repo_root))
            (repo_root / "untracked.txt").write_text("dirty\n")
            self.assertTrue(branch_audit.worktree_is_dirty(repo_root))


class SecurityReviewRefTests(unittest.TestCase):
    def setUp(self) -> None:
        self.validator = load_script_module(
            "validate_developer_integration",
            DEV_INTEGRATION_VALIDATOR_PATH,
        )

    def test_pinned_review_ref_uses_declared_commit_content(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            subprocess.run(["git", "init", "--quiet", str(repo_root)], check=True)
            subprocess.run(
                ["git", "config", "user.email", "validation@example.invalid"],
                cwd=repo_root,
                check=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "Validation Test"],
                cwd=repo_root,
                check=True,
            )
            review_path = Path("docs/review.md")
            absolute_review_path = repo_root / review_path
            absolute_review_path.parent.mkdir(parents=True)
            committed_content = b"approved review\n"
            absolute_review_path.write_bytes(committed_content)
            subprocess.run(["git", "add", str(review_path)], cwd=repo_root, check=True)
            subprocess.run(
                ["git", "commit", "--quiet", "-m", "Add review"],
                cwd=repo_root,
                check=True,
            )
            source_commit = subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                cwd=repo_root,
                text=True,
            ).strip()
            ref = {
                "path": review_path.as_posix(),
                "source_commit": source_commit,
                "content_sha256": hashlib.sha256(committed_content).hexdigest(),
            }

            absolute_review_path.write_text("mutable checkout changed\n")

            self.assertEqual(
                self.validator.validate_security_review_ref(repo_root, ref),
                [],
            )

    def test_pinned_review_ref_rejects_digest_for_other_content(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            subprocess.run(["git", "init", "--quiet", str(repo_root)], check=True)
            subprocess.run(
                ["git", "config", "user.email", "validation@example.invalid"],
                cwd=repo_root,
                check=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "Validation Test"],
                cwd=repo_root,
                check=True,
            )
            review_path = Path("docs/review.md")
            absolute_review_path = repo_root / review_path
            absolute_review_path.parent.mkdir(parents=True)
            absolute_review_path.write_text("approved review\n")
            subprocess.run(["git", "add", str(review_path)], cwd=repo_root, check=True)
            subprocess.run(
                ["git", "commit", "--quiet", "-m", "Add review"],
                cwd=repo_root,
                check=True,
            )
            source_commit = subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                cwd=repo_root,
                text=True,
            ).strip()
            ref = {
                "path": review_path.as_posix(),
                "source_commit": source_commit,
                "content_sha256": hashlib.sha256(b"different review\n").hexdigest(),
            }

            errors = self.validator.validate_security_review_ref(repo_root, ref)

            self.assertEqual(len(errors), 1)
            self.assertIn("security review digest mismatch", errors[0])

    def test_pinned_review_ref_reports_missing_checkout(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            missing_repo = Path(temp_dir) / "security-architecture"
            ref = {
                "path": "docs/review.md",
                "source_commit": "a" * 40,
                "content_sha256": "b" * 64,
            }

            errors = self.validator.validate_security_review_ref(missing_repo, ref)

            self.assertEqual(
                errors,
                [f"security review repo checkout missing: {missing_repo}"],
            )


if __name__ == "__main__":
    unittest.main()
