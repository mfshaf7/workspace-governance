from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = REPO_ROOT / "scripts"
VALIDATOR_PATH = SCRIPTS_ROOT / "validate_contracts.py"


def load_validator():
    if str(SCRIPTS_ROOT) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_ROOT))
    spec = importlib.util.spec_from_file_location(
        "validate_contracts_skill_commands", VALIDATOR_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {VALIDATOR_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SkillCommandReferenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.validator = load_validator()

    def test_registered_skill_command_must_resolve_in_owner_repo(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            owner_root = workspace_root / "workspace-governance"
            skill_root = owner_root / "skills-src" / "example"
            script_root = owner_root / "scripts"
            skill_root.mkdir(parents=True)
            script_root.mkdir(parents=True)
            (skill_root / "SKILL.md").write_text(
                "Run `python3 scripts/missing.py`.\n", encoding="utf-8"
            )
            skills = {
                "example": {
                    "owner_repo": "workspace-governance",
                    "source_path": "skills-src/example",
                }
            }

            issues = self.validator.registered_skill_command_reference_issues(
                workspace_root, skills
            )

            self.assertEqual(len(issues), 1)
            self.assertIn("scripts/missing.py", issues[0])

            (script_root / "missing.py").write_text("pass\n", encoding="utf-8")
            self.assertEqual(
                self.validator.registered_skill_command_reference_issues(
                    workspace_root, skills
                ),
                [],
            )


if __name__ == "__main__":
    unittest.main()
