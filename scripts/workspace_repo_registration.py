"""Pure companion projections for the existing Inventory source transaction.

This does not admit repositories, execute owner commands, grant Security or
runtime authority, or write files. Source-only ownership uses existing record
fields; shared/control owners retain their explicit review/routing boundary.
"""

from __future__ import annotations

import copy
from pathlib import Path
import re
from typing import Any

from contracts_lib import load_contracts
from governance_engine_materializer import render_generated_artifacts

INDEX_START = "<!-- workspace-source-owner-index:start -->"
INDEX_END = "<!-- workspace-source-owner-index:end -->"
GUIDANCE_PATHS = tuple(f"workspace-root/{name}" for name in ("README.md", "AGENTS.md", "ARCHITECTURE.md"))
NAME = re.compile(r"[a-z0-9][a-z0-9._-]*")


class RepositoryRegistrationError(RuntimeError):
    pass


def is_source_owner(name: str, entry: dict[str, Any]) -> bool:
    """An indexed source owner is not an implicit new control-plane owner."""
    envelope = entry.get("record", {})
    lineage = envelope.get("lineage", {})
    validation = entry.get("validation_behavior", {})
    binding = entry.get("provider_repository", {})
    return (
        bool(NAME.fullmatch(name))
        and entry.get("requires_security_bindings") is False
        and entry.get("security_review_subject", False) is False
        and bool(entry.get("owns")) and bool(entry.get("must_not_own"))
        and validation.get("posture") == "covered-by-owner-repo"
        and validation.get("wgcf_graph_role") == "product-runtime-source"
        and envelope.get("id") == f"repo:{name}"
        and lineage.get("source") == "workspace-intake"
        and lineage.get("source_ref") == f"repo:{name}"
        and binding.get("provider") == "github"
        and bool(re.fullmatch(r"[1-9][0-9]*", str(binding.get("provider_repository_id", ""))))
        and bool(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9._-]+", str(binding.get("full_name", ""))))
        and str(binding.get("full_name", "")).split("/")[-1] not in {".", ".."}
        and entry.get("posture") in {"active", "suspended", "retired"}
        and entry.get("lifecycle") == entry.get("posture")
    )


def source_owner_rule(name: str, entry: dict[str, Any]) -> dict[str, Any]:
    if not is_source_owner(name, entry):
        raise RepositoryRegistrationError("Repository requires explicit control-owner or Security-bound registration review.")
    # No invented Security artifact, validation command, workflow or authority
    # claim. Actual owner validation stays in its reviewed base-owned profile.
    return {"schema_version": 1, "repo": name, "lifecycle": entry["posture"],
            "required_repo_refs": list(entry["allowed_authoritative_refs"]),
            "required_patterns": {"readme": [], "agents": []},
            "forbidden_patterns": {"readme": [], "agents": []}}


def source_owner_context(name: str) -> dict[str, Any]:
    return {"repo": name, "owner_repo": name, "declaration_status": "source-owner-consumer",
            "source_classes": ["repo_snapshot", "terminal_output", "ci_logs"],
            "default_projection": "model-safe-packet", "adoption_state": "declared",
            "cgg_role": "Profile-gated context consumer only; source admission does not activate a profile or permit raw projection.",
            "evidence_refs": [f"contracts/repo-rules/{name}.yaml", "docs/context-admission-governance.md"],
            "denied_without_cgg": ["Raw source, validation output, CI logs or client data projected to models without admission and a packet receipt."]}


def source_owner_raw_context(name: str) -> dict[str, Any]:
    return {"entry_id": f"source-owner-{name}", "owner_repo": name, "covered_repos": [name],
            "context_behavior_repo_ref": name, "source_classes": ["repo_snapshot", "terminal_output", "ci_logs"],
            "current_raw_context_path": "Owner-local source and validation artifacts; no raw model projection is admitted.",
            "current_risk": "Future source or diagnostic output may contain sensitive information; source admission is not context acceptance.",
            "target_cgg_path": "Profile-gated CGG model-safe/operator-safe packet and receipt, without activating a new profile.",
            "state": "inventory-only", "retirement_allowed": False,
            "next_action": "Keep raw projection denied; prove applicable packet behavior before declaring adoption, parity or retirement.",
            "rollback_requirement": "Preserve owner source-authority artifacts for operator-only diagnosis; no legacy raw projection is enabled.",
            "evidence_refs": [f"contracts/repo-rules/{name}.yaml", "contracts/context-behavior.yaml"]}


def _update_context_rows(contracts: dict[str, Any], name: str, before_active: bool, after_active: bool) -> None:
    for key, root_key, collection, identity, expected in (
        ("context_behavior", "context_behavior", "repo_declarations", "repo", source_owner_context(name)),
        ("raw_context_retirement", "raw_context_retirement", "inventory_entries", "entry_id", source_owner_raw_context(name)),
    ):
        rows = contracts[key][root_key][collection]
        matches = [row for row in rows if row.get(identity) == expected[identity]]
        if (before_active and matches != [expected]) or (not before_active and matches):
            raise RepositoryRegistrationError("Source-owner context has independent control changes; explicit review is required.")
        rows[:] = [row for row in rows if row.get(identity) != expected[identity]]
        if after_active:
            rows.append(expected)


def source_owner_index(inventory: dict[str, Any]) -> str:
    entries = inventory.get("repos", {})
    rows = [f"- `{name}` — `{entry['posture']}`; owner guidance: `{name}/AGENTS.md`, `{name}/README.md`."
            for name, entry in sorted(entries.items()) if is_source_owner(name, entry)]
    return "\n".join([INDEX_START, *(rows or ["No additional source-only repository owners are registered."]), INDEX_END])


def replace_source_owner_index(text: str, before: dict[str, Any], after: dict[str, Any]) -> str:
    if text.count(INDEX_START) != 1 or text.count(INDEX_END) != 1:
        raise RepositoryRegistrationError("Source-owner guidance index is missing or ambiguous; control review is required.")
    start, end = text.index(INDEX_START), text.index(INDEX_END) + len(INDEX_END)
    if end <= start or text[start:end] != source_owner_index(before):
        raise RepositoryRegistrationError("Source-owner guidance does not match current canonical Inventory.")
    return text[:start] + source_owner_index(after) + text[end:]


def validate_source_owner_guidance_delta(
    previous_text: str, candidate_text: str, before: dict[str, Any], after: dict[str, Any],
) -> None:
    if candidate_text != replace_source_owner_index(previous_text, before, after):
        raise RepositoryRegistrationError("Repository data cannot change workspace instructions outside its exact generated index.")


def inventory_companion_projection(
    repo_root: Path, kind: str, before: dict[str, Any], after: dict[str, Any],
) -> dict[str, str]:
    """Return exact companion bytes before the owner atomically writes any file.

    All inventory kinds refresh the already-declared generated metadata family.
    Only qualified source-owner repository mutations may change routing-index
    data and their deterministic repo rule. No instruction text is rewritten.
    """
    collection = {"repo": "repos", "product": "products", "component": "components"}[kind]
    contracts = load_contracts(repo_root)
    if contracts[collection] != before:
        raise RepositoryRegistrationError("Inventory changed while projecting its source companions.")
    updated = copy.deepcopy(contracts)
    updated[collection] = copy.deepcopy(after)
    return _companion_projection(repo_root, contracts, updated)


def _companion_projection(repo_root: Path, original: dict, contracts: dict) -> dict[str, str]:
    from validate_cross_repo_truth import build_generated_contracts
    import yaml

    original_context = {key: copy.deepcopy(contracts[key]) for key in ("context_behavior", "raw_context_retirement")}
    result: dict[str, str] = {}
    before, after = original["repos"], contracts["repos"]
    if before != after:
        old = {**before.get("repos", {}), **before.get("retired_repos", {})}
        new = {**after.get("repos", {}), **after.get("retired_repos", {})}
        for name in sorted(set(old) | set(new)):
            if old.get(name) == new.get(name):
                continue
            previous, current = old.get(name), new.get(name)
            if previous is not None and not is_source_owner(name, previous):
                if current is None or previous.get("posture") != current.get("posture"):
                    raise RepositoryRegistrationError("Control-owner lifecycle needs explicit reviewed routing and policy changes; routine source-only registration cannot rewrite them.")
                continue  # Existing control-owner metadata retains its explicit boundary.
            if current is None or not is_source_owner(name, current):
                raise RepositoryRegistrationError("New/control-owner registration requires its complete explicit reviewed source change.")
            rule_path = f"contracts/repo-rules/{name}.yaml"
            existing_rule = contracts["repo_rules"].get(name)
            if previous is None and existing_rule is not None:
                raise RepositoryRegistrationError("New source owner must not overwrite an existing repo rule.")
            if previous is not None and existing_rule != source_owner_rule(name, previous):
                raise RepositoryRegistrationError("Existing source-owner rule is not the reviewed deterministic projection.")
            rule = source_owner_rule(name, current)
            contracts["repo_rules"][name] = rule
            result[rule_path] = yaml.safe_dump(rule, sort_keys=False)
            _update_context_rows(contracts, name, name in before.get("repos", {}), name in after.get("repos", {}))
        for key, relative in (("context_behavior", "contracts/context-behavior.yaml"),
                              ("raw_context_retirement", "contracts/raw-context-retirement.yaml")):
            if contracts[key] != original_context[key]:
                result[relative] = yaml.safe_dump(contracts[key], sort_keys=False)
    for relative in GUIDANCE_PATHS:
        value = (repo_root / relative).read_text(encoding="utf-8")
        changed = replace_source_owner_index(value, before, after)
        if changed != value:
            result[relative] = changed
    compiled = build_generated_contracts(repo_root, contracts)
    for target, content in render_generated_artifacts(repo_root, compiled, contracts=contracts).items():
        relative = target.relative_to(repo_root).as_posix()
        if not target.is_file() or target.read_text(encoding="utf-8") != content:
            result[relative] = content
    return result


def validate_registration_companions(previous_root: Path, candidate_root: Path) -> set[str]:
    """Check cumulative routine companions using reviewed code and owner compiler.

    The caller must first freeze every non-data/code path. Candidate code is
    never imported. Core/custom policies remain fixed; list ordering alone in
    context declarations is not policy authority.
    """
    import yaml

    previous = load_contracts(previous_root)
    candidate = load_contracts(candidate_root)
    projected = copy.deepcopy(previous)
    for key in ("repos", "products", "components"):
        projected[key] = copy.deepcopy(candidate[key])
    expected = _companion_projection(previous_root, previous, projected)
    context_paths = {"contracts/context-behavior.yaml": ("context_behavior", "repo_declarations", "repo"),
                     "contracts/raw-context-retirement.yaml": ("raw_context_retirement", "inventory_entries", "entry_id")}
    # Verify complete results, not merely a subset of whichever files changed.
    relevant = set(expected) | set(GUIDANCE_PATHS) | set(context_paths)
    relevant |= {f"contracts/repo-rules/{name}.yaml" for name in set(previous["repo_rules"]) | set(candidate["repo_rules"])}
    from contracts_lib import generated_output_specs
    relevant |= {spec["path"].relative_to(previous_root).as_posix() for spec in generated_output_specs(previous_root, previous).values()}
    for relative in relevant:
        old_path, new_path = previous_root / relative, candidate_root / relative
        text = expected.get(relative, old_path.read_text() if old_path.is_file() else None)
        if text is None or not new_path.is_file() or new_path.is_symlink():
            raise RepositoryRegistrationError("Registration companions are missing or include an unreviewed rule.")
        actual = new_path.read_text()
        if relative in context_paths:
            root, collection, identity = context_paths[relative]
            wanted, observed = yaml.safe_load(text), yaml.safe_load(actual)
            for payload in (wanted, observed):
                rows = payload[root][collection]
                if len({row[identity] for row in rows}) != len(rows):
                    raise RepositoryRegistrationError("Context companion identities must remain unique.")
                payload[root][collection] = sorted(rows, key=lambda row: row[identity])
            if wanted != observed:
                raise RepositoryRegistrationError("Registration cannot change existing context policy or grant raw projection.")
        elif actual != text:
            raise RepositoryRegistrationError("Registration source differs from its exact owner-derived companion projection.")
    return set(expected)
