#!/usr/bin/env python3
from __future__ import annotations

import filecmp
import json
from pathlib import Path
import shutil
from typing import Any

import yaml

from contracts_lib import (
    generated_output_specs,
    load_contracts,
    skill_install_manifest_name,
    workspace_root_sync_map,
)


def directories_match(left: Path, right: Path) -> bool:
    if not left.exists() or not right.exists():
        return False
    comparison = filecmp.dircmp(left, right)
    if (
        comparison.left_only
        or comparison.right_only
        or comparison.diff_files
        or comparison.funny_files
    ):
        return False
    return all(
        directories_match(left / subdir, right / subdir)
        for subdir in comparison.common_dirs
    )


def load_skill_manifest(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def write_skill_manifest(
    path: Path, *, skill_dirs: list[str], registry_names: list[str]
) -> None:
    path.write_text(
        json.dumps(
            {
                "managed_skill_dirs": skill_dirs,
                "registered_skill_names": registry_names,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )


def sync_workspace_root_outputs(
    repo_root: Path,
    workspace_root: Path,
    *,
    contracts: dict[str, Any] | None = None,
) -> list[str]:
    repo_root = repo_root.resolve()
    workspace_root = workspace_root.resolve()
    if contracts is None:
        contracts = load_contracts(repo_root)
    synced: list[str] = []
    for src_rel, dest_rel in workspace_root_sync_map(contracts):
        src = repo_root / src_rel
        dest = workspace_root / dest_rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        synced.append(f"{src} -> {dest}")
    return synced


def check_workspace_root_outputs(
    repo_root: Path,
    workspace_root: Path,
    *,
    contracts: dict[str, Any] | None = None,
) -> list[str]:
    repo_root = repo_root.resolve()
    workspace_root = workspace_root.resolve()
    if contracts is None:
        contracts = load_contracts(repo_root)
    mismatches: list[str] = []
    for src_rel, dest_rel in workspace_root_sync_map(contracts):
        src = repo_root / src_rel
        dest = workspace_root / dest_rel
        if not dest.exists():
            mismatches.append(f"missing synced file: {dest}")
            continue
        if src.read_text() != dest.read_text():
            mismatches.append(f"out of sync: {dest} != {src}")
    return mismatches


def install_registered_skills(
    repo_root: Path,
    workspace_root: Path,
    target_root: Path,
    *,
    contracts: dict[str, Any] | None = None,
    selected_skill_names: set[str] | None = None,
    check: bool = False,
) -> tuple[list[str], list[str]]:
    repo_root = repo_root.resolve()
    workspace_root = workspace_root.resolve()
    target_root = target_root.expanduser().resolve()
    if contracts is None:
        contracts = load_contracts(repo_root)
    selected = set(selected_skill_names or [])
    manifest_name = skill_install_manifest_name(contracts)
    manifest_path = target_root / manifest_name
    registered_skills = contracts["skills"]["skills"]
    errors: list[str] = []

    unknown = sorted(selected - set(registered_skills))
    if unknown:
        return (
            [],
            [f"unknown registered skill: {name}" for name in unknown],
        )

    current_skill_dirs: list[str] = []

    for skill_name, payload in sorted(registered_skills.items()):
        if selected and skill_name not in selected:
            continue
        source_dir = workspace_root / payload["owner_repo"] / payload["source_path"]
        target_dir = target_root / source_dir.name
        current_skill_dirs.append(source_dir.name)
        if not source_dir.exists():
            errors.append(f"missing skill source: {source_dir}")
            continue
        if not (source_dir / "SKILL.md").exists():
            errors.append(f"missing skill definition: {source_dir / 'SKILL.md'}")
            continue
        if check:
            if not directories_match(source_dir, target_dir):
                errors.append(f"skill out of sync: {target_dir}")
            continue
        target_root.mkdir(parents=True, exist_ok=True)
        if target_dir.exists():
            shutil.rmtree(target_dir)
        shutil.copytree(source_dir, target_dir)

    if check and not selected:
        manifest = load_skill_manifest(manifest_path)
        managed_dirs = manifest.get("managed_skill_dirs")
        if not isinstance(managed_dirs, list):
            errors.append(f"missing or invalid skill manifest: {manifest_path}")
        else:
            stale_dirs = sorted(set(managed_dirs) - set(current_skill_dirs))
            for directory_name in stale_dirs:
                stale_dir = target_root / directory_name
                if stale_dir.exists():
                    errors.append(f"stale managed skill still installed: {stale_dir}")
    elif not check and not selected:
        previous_manifest = load_skill_manifest(manifest_path)
        previous_dirs = previous_manifest.get("managed_skill_dirs", [])
        if isinstance(previous_dirs, list):
            stale_dirs = sorted(set(previous_dirs) - set(current_skill_dirs))
            for directory_name in stale_dirs:
                stale_dir = target_root / directory_name
                if stale_dir.exists():
                    shutil.rmtree(stale_dir)
        write_skill_manifest(
            manifest_path,
            skill_dirs=sorted(current_skill_dirs),
            registry_names=sorted(registered_skills.keys()),
        )

    return (sorted(selected or registered_skills.keys()), errors)


def _write_structured_output(path: Path, payload: Any, output_format: str) -> None:
    if output_format == "json":
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        return
    if output_format == "yaml":
        path.write_text(yaml.safe_dump(payload, sort_keys=False))
        return
    raise ValueError(f"unsupported generated output format: {output_format}")


def _read_structured_output(path: Path, output_format: str) -> Any:
    if output_format == "json":
        return json.loads(path.read_text())
    if output_format == "yaml":
        return yaml.safe_load(path.read_text())
    raise ValueError(f"unsupported generated output format: {output_format}")


def write_generated_artifacts(
    repo_root: Path,
    compiled_outputs: dict[str, Any],
    *,
    contracts: dict[str, Any] | None = None,
) -> list[Path]:
    specs = generated_output_specs(repo_root, contracts)
    written: list[Path] = []
    for output_id, payload in compiled_outputs.items():
        spec = specs[output_id]
        path = spec["path"]
        _write_structured_output(path, payload, spec["format"])
        written.append(path)
    return written


def check_generated_artifacts(
    repo_root: Path,
    compiled_outputs: dict[str, Any],
    *,
    contracts: dict[str, Any] | None = None,
) -> list[str]:
    specs = generated_output_specs(repo_root, contracts)
    errors: list[str] = []
    for output_id, expected_payload in compiled_outputs.items():
        spec = specs[output_id]
        path = spec["path"]
        label = output_id.replace("_", " ")
        if not path.exists():
            errors.append(f"{path}: missing generated {label}")
            continue
        actual_payload = _read_structured_output(path, spec["format"])
        if actual_payload != expected_payload:
            errors.append(f"{path}: generated {label} is stale")
    return errors
