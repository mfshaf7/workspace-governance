from __future__ import annotations

import json
from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
PROFILE_PATH = (
    REPO_ROOT
    / "contracts"
    / "delivery-art-work-session"
    / "evidence-profile.json"
)


class DeliveryArtEvidenceProfileTests(unittest.TestCase):
    def test_matching_commands_cover_supported_architecture_fidelities(self) -> None:
        profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
        matching_fidelities = {
            command["fidelity"]
            for command in profile["commands"]
            if command["conformance_binding"] == "matching-fidelity"
        }

        self.assertEqual(matching_fidelities, {"filesystem", "real-git"})


if __name__ == "__main__":
    unittest.main()
