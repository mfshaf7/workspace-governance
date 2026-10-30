import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/validate_repo_structure.py"
SPEC = importlib.util.spec_from_file_location("repo_structure_origin", SCRIPT)
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class RepositoryOriginTests(unittest.TestCase):
    def test_only_exact_resolved_checkout_is_trusted_and_ambient_git_is_removed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            alias = root / "alias"
            alias.symlink_to(root, target_is_directory=True)
            with patch.dict(os.environ, {"GIT_DIR": "/untrusted", "GIT_CONFIG_COUNT": "1",
                 "GIT_CONFIG_KEY_0": "safe.directory", "GIT_CONFIG_VALUE_0": "*"}), patch.object(
                     module.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "expected\n")
                 ) as execute:
                self.assertEqual(module.repository_origin(alias), "expected")
            command = execute.call_args.args[0]
            self.assertIn(f"safe.directory={root.resolve()}", command)
            self.assertNotIn("safe.directory=*", command)
            self.assertIn(f"core.hooksPath={os.devnull}", command)
            environment = execute.call_args.kwargs["env"]
            self.assertEqual({key for key in environment if key.startswith("GIT_")},
                             {"GIT_CONFIG_GLOBAL", "GIT_CONFIG_NOSYSTEM"})
            self.assertEqual(environment["GIT_CONFIG_GLOBAL"], os.devnull)

    def test_real_origin_is_preserved_and_missing_origin_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            with self.assertRaises(subprocess.CalledProcessError):
                module.repository_origin(root)
            unexpected = "https://github.com/example/unexpected.git"
            subprocess.run(["git", "-C", str(root), "remote", "add", "origin", unexpected], check=True)
            self.assertEqual(module.repository_origin(root), unexpected)
            self.assertNotEqual(module.normalize_repository_url(unexpected),
                                module.normalize_repository_url("git@github.com:mfshaf7/workspace-governance.git"))
