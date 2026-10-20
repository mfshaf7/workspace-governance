"""Allocate inert test bindings without borrowing identities from copied records."""
from pathlib import Path

import yaml


def unused_provider_repository(repo_root: Path) -> dict[str, str]:
    ids, names = set(), set()
    for filename in ("intake-register.yaml", "repos.yaml"):
        document = yaml.safe_load((repo_root / "contracts" / filename).read_text())
        for section in ("repos", "retired_repos"):
            for entry in document.get(section, {}).values():
                binding = entry.get("provider_repository", {})
                if binding.get("provider") == "github":
                    ids.add(str(binding["provider_repository_id"]))
                    names.add(binding["full_name"].casefold())
    # Valid REST-id shape, deliberately synthetic. Scan independently of the
    # production conflict function whose positive/negative behavior we test.
    number = 9_000_000_000_000_000
    while str(number) in ids:
        number += 1
    name, suffix = "synthetic-fixtures/sample-source", 1
    while name.casefold() in names:
        suffix += 1
        name = f"synthetic-fixtures/sample-source-{suffix}"
    return {"provider": "github", "provider_repository_id": str(number), "full_name": name}
