#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import re
from pathlib import Path
import subprocess
import sys

import yaml

from delivery_art_resource_retirement_contract import (
    resource_retirement_definition_issues,
)

from contracts_lib import (
    active_repo_names,
    generated_paths,
    load_contracts,
    load_json,
)
from governance_engine_materializer import (
    check_generated_artifacts,
    write_generated_artifacts,
)


DOC_EXCLUDES = (
    "/.git/",
    "/docs/archive/",
    "/docs/records/change-records/",
    "/docs/decisions/adr/",
)

WORKSPACE_ROOT_REPO_COVERAGE_REQUIREMENTS = {
    "AGENTS.md": (
        "## Current Owner Map",
        "## Routing Rules",
    ),
    "README.md": (
        "## Active Repository Roles",
        "## Start Here",
    ),
    "ARCHITECTURE.md": (
        "## Active Owner Repos",
        "## Read Next By Task",
    ),
}

SECURITY_ARCHITECTURE_COMPONENT_COVERAGE_REQUIREMENTS = {
    "docs/architecture/components/README.md": "({component_name}/README.md)",
    "docs/architecture/platform/component-inventory.md": "../components/{component_name}/README.md",
}

DELIVERY_ART_PLANNING_WORKFLOW_CONTRACT_PATHS = {
    "platform": Path(
        "platform-engineering/products/openproject/delivery-art-planning-workflow.json"
    ),
    "broker": Path("operator-orchestration-service/src/delivery-planning-workflow.json"),
}

DELIVERY_ART_INITIATIVE_REVIEW_WORKFLOW_CONTRACT_PATHS = {
    "platform": Path(
        "platform-engineering/products/openproject/delivery-art-initiative-review-workflow.json"
    ),
    "broker": Path(
        "operator-orchestration-service/src/delivery-initiative-review-workflow.json"
    ),
}

DELIVERY_ART_BLOCKER_WORKFLOW_CONTRACT_PATHS = {
    "platform": Path(
        "platform-engineering/products/openproject/delivery-art-blocker-workflow.json"
    ),
    "broker": Path("operator-orchestration-service/src/delivery-blocker-workflow.json"),
}

DELIVERY_ART_INITIATIVE_LINEAGE_CONTRACT_PATHS = {
    "platform": Path(
        "platform-engineering/products/openproject/delivery-art-initiative-lineage.json"
    ),
    "broker": Path(
        "operator-orchestration-service/src/delivery-initiative-lineage.json"
    ),
}

DELIVERY_ART_LIFECYCLE_CAPABILITY_PATH = Path(
    "operator-orchestration-service/contracts/delivery-art-lifecycle/capabilities.json"
)

DELIVERY_ART_REQUIRED_NORMAL_CAPABILITIES = {
    "scoped-art-snapshot",
    "historical-material-freshness",
    "persistent-work-session",
    "process-restart-reconstruction",
    "worktree-relocation-reconstruction",
    "exact-next-action",
    "architecture-decision",
    "architecture-packet-persistence",
    "work-start-authoring",
    "work-start-persistence",
    "review-packet-v2-authoring",
    "review-packet-merge-readiness",
    "operating-readiness",
    "review-packet-finalization",
    "art-closeout",
    "work-session-resource-retirement",
}


def gather_active_docs(repo_root: Path) -> list[Path]:
    files: list[Path] = []
    for path in repo_root.rglob("*.md"):
        path_str = str(path)
        if any(marker in path_str for marker in DOC_EXCLUDES):
            continue
        files.append(path)
    return sorted(files)


def extract_section(text: str, heading: str) -> str | None:
    lines = text.splitlines()
    target = heading.strip().lower()
    collecting = False
    collected: list[str] = []

    for line in lines:
        stripped = line.strip()
        if stripped.lower() == target:
            collecting = True
            continue
        if collecting and stripped.startswith("## "):
            break
        if collecting:
            collected.append(line)

    if not collecting:
        return None
    return "\n".join(collected).strip()


def validate_workspace_root_repo_coverage(
    workspace_root_docs: Path,
    active_repos: list[str],
    errors: list[str],
) -> None:
    for filename, headings in WORKSPACE_ROOT_REPO_COVERAGE_REQUIREMENTS.items():
        path = workspace_root_docs / filename
        if not path.exists():
            errors.append(f"{path}: missing workspace-root doc for active repo coverage check")
            continue

        text = path.read_text(encoding="utf-8")
        for heading in headings:
            section = extract_section(text, heading)
            if section is None:
                errors.append(f"{path}: missing section {heading!r} for active repo coverage check")
                continue

            missing_repos = [repo_name for repo_name in active_repos if repo_name not in section]
            if missing_repos:
                missing_text = ", ".join(repr(repo_name) for repo_name in missing_repos)
                errors.append(
                    f"{path}: section {heading!r} missing active repos {missing_text}"
                )


def validate_security_architecture_component_coverage(
    workspace_root: Path,
    contracts: dict[str, object],
    errors: list[str],
) -> None:
    security_repo_root = workspace_root / "security-architecture"
    if not security_repo_root.exists():
        errors.append(f"{security_repo_root}: missing security-architecture repo for component coverage check")
        return

    active_security_components = sorted(
        component_name
        for component_name, payload in contracts["components"]["components"].items()
        if payload["lifecycle"] == "active" and payload["security_owner"] == "security-architecture"
    )

    for component_name in active_security_components:
        component_doc = (
            security_repo_root / "docs" / "architecture" / "components" / component_name / "README.md"
        )
        if not component_doc.exists():
            errors.append(
                f"{component_doc}: missing security component view for active component {component_name!r}"
            )

    for rel_path, pattern in SECURITY_ARCHITECTURE_COMPONENT_COVERAGE_REQUIREMENTS.items():
        path = security_repo_root / rel_path
        if not path.exists():
            errors.append(f"{path}: missing security-architecture component coverage doc")
            continue
        text = path.read_text(encoding="utf-8")
        missing_components = [
            component_name
            for component_name in active_security_components
            if pattern.format(component_name=component_name) not in text
        ]
        if missing_components:
            missing_text = ", ".join(repr(name) for name in missing_components)
            errors.append(f"{path}: missing security component coverage for {missing_text}")


def validate_delivery_art_planning_workflow_contract(
    workspace_root: Path,
    errors: list[str],
) -> None:
    resolved_paths = {
        name: workspace_root / relative_path
        for name, relative_path in DELIVERY_ART_PLANNING_WORKFLOW_CONTRACT_PATHS.items()
    }

    missing = [
        f"{name}={path}"
        for name, path in resolved_paths.items()
        if not path.exists()
    ]
    if missing:
        errors.append(
            "delivery-art planning workflow contract missing: " + ", ".join(missing)
        )
        return

    platform_contract = load_json(resolved_paths["platform"])
    broker_contract = load_json(resolved_paths["broker"])
    if platform_contract != broker_contract:
        errors.append(
            "delivery-art planning workflow drift: "
            f"{resolved_paths['platform']} does not match {resolved_paths['broker']}"
        )


def validate_delivery_art_initiative_review_workflow_contract(
    workspace_root: Path,
    errors: list[str],
) -> None:
    resolved_paths = {
        name: workspace_root / relative_path
        for name, relative_path in DELIVERY_ART_INITIATIVE_REVIEW_WORKFLOW_CONTRACT_PATHS.items()
    }

    missing = [
        f"{name}={path}"
        for name, path in resolved_paths.items()
        if not path.exists()
    ]
    if missing:
        errors.append(
            "delivery-art initiative-review workflow contract missing: "
            + ", ".join(missing)
        )
        return

    platform_contract = load_json(resolved_paths["platform"])
    broker_contract = load_json(resolved_paths["broker"])
    if platform_contract != broker_contract:
        errors.append(
            "delivery-art initiative-review workflow drift: "
            f"{resolved_paths['platform']} does not match {resolved_paths['broker']}"
        )


def validate_delivery_art_blocker_workflow_contract(
    workspace_root: Path,
    errors: list[str],
) -> None:
    resolved_paths = {
        name: workspace_root / relative_path
        for name, relative_path in DELIVERY_ART_BLOCKER_WORKFLOW_CONTRACT_PATHS.items()
    }

    missing = [
        f"{name}={path}"
        for name, path in resolved_paths.items()
        if not path.exists()
    ]
    if missing:
        errors.append(
            "delivery-art blocker workflow contract missing: "
            + ", ".join(missing)
        )
        return

    platform_contract = load_json(resolved_paths["platform"])
    broker_contract = load_json(resolved_paths["broker"])
    if platform_contract != broker_contract:
        errors.append(
            "delivery-art blocker workflow drift: "
            f"{resolved_paths['platform']} does not match {resolved_paths['broker']}"
        )


def validate_delivery_art_initiative_lineage_contract(
    workspace_root: Path,
    errors: list[str],
) -> None:
    resolved_paths = {
        name: workspace_root / relative_path
        for name, relative_path in DELIVERY_ART_INITIATIVE_LINEAGE_CONTRACT_PATHS.items()
    }

    missing = [
        f"{name}={path}"
        for name, path in resolved_paths.items()
        if not path.exists()
    ]
    if missing:
        errors.append(
            "delivery-art initiative-lineage contract missing: "
            + ", ".join(missing)
        )
        return

    platform_contract = load_json(resolved_paths["platform"])
    broker_contract = load_json(resolved_paths["broker"])
    if platform_contract != broker_contract:
        errors.append(
            "delivery-art initiative-lineage drift: "
            f"{resolved_paths['platform']} does not match {resolved_paths['broker']}"
        )


def delivery_art_lifecycle_capability_parity_errors(
    workspace_root: Path,
    activation: dict,
) -> list[str]:
    errors: list[str] = []
    source = activation.get("capability_source") or {}
    projection = activation.get("capability_projection") or {}
    source_repo = source.get("repo")
    manifest_relative = source.get("manifest_path")
    manifest_digest = source.get("manifest_digest")
    activated_at_commit = source.get("activated_at_commit")

    expected_repo = DELIVERY_ART_LIFECYCLE_CAPABILITY_PATH.parts[0]
    expected_relative = Path(*DELIVERY_ART_LIFECYCLE_CAPABILITY_PATH.parts[1:])
    if source_repo != expected_repo or manifest_relative != str(expected_relative):
        errors.append(
            "capability source must resolve to the canonical OOS lifecycle manifest"
        )
        return errors

    source_repo_root = workspace_root / expected_repo
    manifest_path = source_repo_root / expected_relative
    if not manifest_path.exists():
        errors.append(f"missing owner capability manifest {manifest_path}")
        return errors

    try:
        source_manifest = load_json(manifest_path)
    except (OSError, ValueError) as exc:
        errors.append(f"owner capability manifest is unreadable: {exc}")
        return errors
    actual_manifest_digest = "sha256:" + hashlib.sha256(
        manifest_path.read_bytes()
    ).hexdigest()
    if manifest_digest != actual_manifest_digest:
        errors.append("capability source digest differs from the owner manifest")
    if projection != source_manifest:
        errors.append(
            "capability projection differs from the OOS lifecycle source manifest"
        )

    capabilities = source_manifest.get("capabilities") or []
    capability_ids = [entry.get("id") for entry in capabilities]
    if len(capability_ids) != len(set(capability_ids)):
        errors.append("owner lifecycle capability ids must be unique")

    normal_capabilities = {
        entry.get("id") for entry in capabilities if entry.get("normal_path") is True
    }
    if normal_capabilities != DELIVERY_ART_REQUIRED_NORMAL_CAPABILITIES:
        errors.append(
            "owner lifecycle normal capabilities do not match the governed dev-integration path"
        )

    compatibility = next(
        (
            entry
            for entry in capabilities
            if entry.get("id") == "review-packet-v1-compatibility"
        ),
        None,
    )
    if compatibility != {
        "id": "review-packet-v1-compatibility",
        "state": "compatibility",
        "contract_version": 1,
        "normal_path": False,
    }:
        errors.append("Review Packet v1 must remain compatibility-only")

    if not isinstance(activated_at_commit, str) or not re.fullmatch(
        r"[0-9a-f]{40}", activated_at_commit
    ):
        errors.append("capability activation must bind a full source commit")
        return errors

    commit_exists = subprocess.run(
        ["git", "cat-file", "-e", f"{activated_at_commit}^{{commit}}"],
        cwd=source_repo_root,
        text=True,
        capture_output=True,
        check=False,
    )
    if commit_exists.returncode != 0:
        errors.append("capability activation commit is absent from the OOS repository")
        return errors

    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", activated_at_commit, "HEAD"],
        cwd=source_repo_root,
        text=True,
        capture_output=True,
        check=False,
    )
    if ancestor.returncode != 0:
        errors.append("capability activation commit is not an ancestor of OOS HEAD")

    manifest_unchanged = subprocess.run(
        ["git", "diff", "--quiet", activated_at_commit, "--", str(expected_relative)],
        cwd=source_repo_root,
        text=True,
        capture_output=True,
        check=False,
    )
    if manifest_unchanged.returncode != 0:
        errors.append(
            "owner lifecycle manifest differs from the activation commit; activation evidence must be refreshed"
        )

    return errors


def delivery_art_work_session_contract_errors(work_session: dict) -> list[str]:
    errors: list[str] = []
    expected_commands = {
        "start": "npm run art -- work start <work-item-id>",
        "status": "npm run art -- work status <work-item-id>",
        "continue": "npm run art -- work continue <work-item-id>",
        "close": "npm run art -- work close <work-item-id>",
        "help": "npm run art -- work --help",
    }
    if work_session.get("contract_version") != 2:
        errors.append("work-session lifecycle contract version must be 2")
    if work_session.get("state") != "active-dev-integration":
        errors.append(
            "work-session lifecycle must remain active in dev-integration after governed activation"
        )
    if work_session.get("owner_repo") != "operator-orchestration-service":
        errors.append("work-session lifecycle owner must be operator-orchestration-service")
    if work_session.get("commands") != expected_commands:
        errors.append("work-session lifecycle command family differs from the approved contract")

    state_store = work_session.get("state_store") or {}
    if state_store.get("classification") != "reconstructable-operator-coordination":
        errors.append("work-session state must remain reconstructable coordination")
    if state_store.get("default_root") != (
        "${XDG_STATE_HOME:-${HOME}/.local/state}/operator-orchestration-service/delivery-art/work"
    ):
        errors.append("work-session state root differs from the approved contract")
    if state_store.get("override_environment_variable") != "OOS_ART_WORK_STATE_ROOT":
        errors.append("work-session state override differs from the approved contract")
    if state_store.get("worktree_storage") != "prohibited":
        errors.append("work-session state must not be stored in disposable worktrees")
    if state_store.get("write_model") != "atomic-replace":
        errors.append("work-session state writes must use atomic replacement")
    if state_store.get("secret_storage") != "prohibited":
        errors.append("work-session state must not store secrets")
    if set(state_store.get("canonical_sources") or []) != {
        "workspace-delivery-art",
        "owner-repo-git",
        "wgcf-delivery-art-artifacts",
        "review-packets",
    }:
        errors.append("work-session canonical source set differs from the approved contract")

    next_action = work_session.get("next_action") or {}
    if next_action.get("cardinality") != "exactly-one":
        errors.append("work-session results must expose exactly one next action")
    if set(next_action.get("required_fields") or []) != {
        "code",
        "command",
        "reason",
        "authority",
    }:
        errors.append("work-session next action fields differ from the approved contract")
    if next_action.get("no_action_code") != "work-complete":
        errors.append("work-session terminal next-action code must be work-complete")
    if next_action.get("ambiguous_action_result") != "blocked":
        errors.append("ambiguous work-session next actions must fail closed")

    freshness = work_session.get("freshness") or {}
    if freshness.get("architecture_initial_persistence") != "fresh-current-scope-required":
        errors.append("initial architecture persistence must require fresh scoped truth")
    if freshness.get("historical_architecture_consumption") != (
        "immutable-decision-plus-material-semantic-check"
    ):
        errors.append("historical architecture must use immutable evidence plus material semantic checks")
    if freshness.get("transition_candidate") != "fresh-current-scope-required":
        errors.append("each transition candidate must require fresh scoped truth")
    if set(freshness.get("material_change_inputs") or []) != {
        "covered-scope-or-parent-change",
        "owner-or-rollback-boundary-change",
        "dependency-or-merge-order-change",
        "architecture-decision-or-protocol-change",
        "validation-or-security-obligation-change",
    }:
        errors.append("work-session material architecture inputs differ from the approved contract")
    if set(freshness.get("ordinary_progress_inputs") or []) != {
        "lifecycle-status-change",
        "percent-complete-change",
        "work-note-change",
        "evidence-reference-append",
    }:
        errors.append("work-session ordinary progress inputs differ from the approved contract")

    compatibility = work_session.get("compatibility") or {}
    if compatibility != {
        "lifecycle_plan_artifact": "generated-compatibility-projection",
        "lifecycle_status_command": "recovery-only",
        "lifecycle_reconcile_command": "recovery-only",
        "direct_artifact_commands": "recovery-and-contract-verification-only",
        "review_packet_v1": "compatibility-only",
    }:
        errors.append("work-session compatibility boundary differs from the approved contract")

    activation = work_session.get("activation") or {}
    if activation != {
        "activation_work_item_ref": "openproject://work_packages/964",
        "implementation_work_item_ref": "openproject://work_packages/963",
        "security_work_item_ref": "openproject://work_packages/962",
        "target_state": "active-dev-integration",
        "temporal_adapter": "deferred-until-durable-wait-evidence",
    }:
        errors.append("work-session activation boundary differs from the approved sequence")

    errors.extend(
        resource_retirement_definition_issues(
            work_session.get("resource_retirement") or {}
        )
    )

    return errors


def validate_delivery_art_operator_path_contract(
    workspace_root: Path,
    repo_root: Path,
    errors: list[str],
) -> None:
    contract_path = repo_root / "contracts/delivery-art-operator-path.yaml"
    if not contract_path.exists():
        errors.append(f"{contract_path}: missing delivery-art operator path contract")
        return

    contract = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    operator_path = contract.get("delivery_art_operator_path") or {}
    canonical_entrypoint = operator_path.get("canonical_entrypoint") or {}
    if canonical_entrypoint.get("command") != "npm run art":
        errors.append(
            f"{contract_path}: canonical entrypoint command must stay 'npm run art'"
        )

    architecture_preflight = operator_path.get("initiative_architecture_preflight") or {}
    if architecture_preflight.get("required_before_source_implementation") is not True:
        errors.append(
            f"{contract_path}: initiative architecture preflight must run before source implementation"
        )

    required_packet_sections = {
        "descendant-and-owner-map",
        "dependency-and-merge-sequence",
        "lifecycle-and-state-model",
        "authorization-session-and-execution-model",
        "evidence-and-receipt-handoffs",
        "runtime-boundaries-and-prohibited-actions",
        "rollback-cleanup-and-terminal-conditions",
        "contradictions-and-open-decisions",
        "conformance-plan",
    }
    packet_sections = set(architecture_preflight.get("packet_required_sections") or [])
    missing_packet_sections = sorted(required_packet_sections - packet_sections)
    if missing_packet_sections:
        errors.append(
            f"{contract_path}: initiative architecture preflight missing packet sections "
            + ", ".join(missing_packet_sections)
        )

    decision_gate = architecture_preflight.get("decision_gate") or {}
    required_decisions = {
        "architecture-ready",
        "blocked-pending-architecture-decision",
    }
    allowed_decisions = set(decision_gate.get("allowed_results") or [])
    if decision_gate.get("operator_discussion_required") is not True:
        errors.append(
            f"{contract_path}: initiative architecture preflight must require operator discussion"
        )
    if decision_gate.get("execution_sequence_locked_before_child_work") is not True:
        errors.append(
            f"{contract_path}: initiative execution sequence must be locked before child work"
        )
    if allowed_decisions != required_decisions:
        errors.append(
            f"{contract_path}: initiative architecture preflight decisions must be exactly "
            + ", ".join(sorted(required_decisions))
        )

    protocol_preflight = architecture_preflight.get("protocol_conformance_preflight") or {}
    required_protocol_dimensions = {
        "command-and-acknowledgement-semantics",
        "deterministic-identities-and-idempotency",
        "state-mutation-ordering",
        "retry-cancel-replay-and-recovery-semantics",
        "bounded-failure-mapping",
        "authorization-integrity-and-replay-resistance",
        "session-scenario-and-execution-binding",
        "result-and-owner-receipt-completeness",
        "immutable-baseline-and-restore-evidence",
        "lifecycle-state-matrix",
        "cross-artifact-timeline-ordering",
        "shared-validator-compatibility",
    }
    protocol_dimensions = set(protocol_preflight.get("required_dimensions") or [])
    missing_protocol_dimensions = sorted(
        required_protocol_dimensions - protocol_dimensions
    )
    if missing_protocol_dimensions:
        errors.append(
            f"{contract_path}: protocol conformance preflight missing dimensions "
            + ", ".join(missing_protocol_dimensions)
        )
    if set(protocol_preflight.get("executable_cases_required") or []) != {
        "positive-contract-cases",
        "negative-contract-cases",
    }:
        errors.append(
            f"{contract_path}: protocol conformance preflight must require positive and negative cases"
        )
    if protocol_preflight.get("architecture_ready_requires_conformance_plan") is not True:
        errors.append(
            f"{contract_path}: architecture readiness must require a conformance plan"
        )
    if protocol_preflight.get("merge_ready_requires_applicable_cases_pass") is not True:
        errors.append(
            f"{contract_path}: merge readiness must require applicable conformance cases to pass"
        )
    if protocol_preflight.get("fidelity_class_required") is not True:
        errors.append(
            f"{contract_path}: conformance cases must declare a fidelity class"
        )

    activation = operator_path.get("contract_activation") or {}
    if activation.get("state") != "active-dev-integration":
        errors.append(
            f"{contract_path}: Delivery ART lifecycle must declare its active dev-integration scope"
        )
    if activation.get("runtime_enforcement") != "owner-manifest-parity":
        errors.append(
            f"{contract_path}: lifecycle activation must be bound to owner-manifest parity"
        )
    runtime_scope = activation.get("runtime_scope") or {}
    if runtime_scope != {
        "normal_path": "dev-integration",
        "stage_and_prod": "not-activated",
    }:
        errors.append(
            f"{contract_path}: lifecycle activation must not imply stage or production authority"
        )
    compatibility = activation.get("compatibility") or {}
    if (
        compatibility.get("normal_review_packet_schema_version") != 2
        or compatibility.get("work_start_commands_available") is not True
        or compatibility.get("review_packet_v1") != "compatibility-only"
    ):
        errors.append(
            f"{contract_path}: Review Packet v2 and work-start must be normal while v1 remains compatibility-only"
        )
    for parity_error in delivery_art_lifecycle_capability_parity_errors(
        workspace_root, activation
    ):
        errors.append(f"{contract_path}: {parity_error}")

    work_session = operator_path.get("work_session_lifecycle") or {}
    for work_session_error in delivery_art_work_session_contract_errors(
        work_session
    ):
        errors.append(f"{contract_path}: {work_session_error}")

    expected_artifact_schemas = {
        "architecture_packet": "contracts/schemas/delivery-art-architecture-packet.schema.json",
        "work_start_record": "contracts/schemas/delivery-art-work-start-record.schema.json",
        "review_packet": "contracts/schemas/delivery-art-review-packet.schema.json",
    }
    artifact_contracts = operator_path.get("artifact_contracts") or {}
    for artifact_name, schema_ref in expected_artifact_schemas.items():
        artifact_contract = artifact_contracts.get(artifact_name) or {}
        if artifact_contract.get("schema_ref") != schema_ref:
            errors.append(
                f"{contract_path}: {artifact_name} must reference {schema_ref}"
            )
        if not (repo_root / schema_ref).exists():
            errors.append(f"{repo_root / schema_ref}: missing Delivery ART artifact schema")

    readiness = operator_path.get("readiness_model") or {}
    if readiness.get("ordered_levels") != [
        "architecture-ready",
        "implementation-ready",
        "merge-ready",
        "operating-ready",
    ]:
        errors.append(
            f"{contract_path}: readiness levels must preserve architecture, implementation, merge, and operating order"
        )

    governance_surface_path = repo_root / operator_path.get(
        "governance_surface", ""
    )
    surface_paths = [
        workspace_root / canonical_entrypoint.get("primary_operator_surface", ""),
        workspace_root / operator_path.get("supporting_platform_surfaces", {}).get(
            "workflow_health", ""
        ),
        workspace_root / operator_path.get("supporting_platform_surfaces", {}).get(
            "quality_gate", ""
        ),
        workspace_root / operator_path.get("supporting_platform_surfaces", {}).get(
            "admin_boundary", ""
        ),
        governance_surface_path,
    ]
    for path in surface_paths:
        if not path.exists():
            errors.append(f"{path}: missing delivery-art operator-path surface")

    primary_surface_path = workspace_root / canonical_entrypoint.get(
        "primary_operator_surface", ""
    )
    if primary_surface_path.exists():
        primary_surface_text = primary_surface_path.read_text(encoding="utf-8")
        for entry in operator_path.get("canonical_read_hierarchy", []):
            cli = entry.get("cli")
            if cli and cli not in primary_surface_text:
                errors.append(
                    f"{primary_surface_path}: missing canonical ART read command {cli!r}"
                )
        for entry in operator_path.get("guided_write_intents", []):
            cli = entry.get("cli")
            if cli and cli != "local helper" and cli not in primary_surface_text:
                errors.append(
                    f"{primary_surface_path}: missing guided ART write command {cli!r}"
                )

    if governance_surface_path.exists():
        governance_surface_text = governance_surface_path.read_text(encoding="utf-8")
        for command in (work_session.get("commands") or {}).values():
            if command not in governance_surface_text:
                errors.append(
                    f"{governance_surface_path}: missing target work-session command {command!r}"
                )
        for required in (
            "active-dev-integration",
            "reconstructable operator coordination",
            "ordinary lifecycle status",
            "material",
        ):
            if required not in governance_surface_text:
                errors.append(
                    f"{governance_surface_path}: missing work-session transition guidance {required!r}"
                )

    skill_path = repo_root / "skills-src/project-delivery-operator/SKILL.md"
    if skill_path.exists():
        skill_text = skill_path.read_text(encoding="utf-8")
        for required in (
            "npm run art -- bootstrap",
            "npm run art -- workflow-health",
            "npm run art -- initiative planning <delivery-id>",
            "npm run art -- item continuation <work-item-id>",
            "npm run art -- lifecycle status <plan.json>",
            "npm run art -- lifecycle reconcile <plan.json>",
            "npm run art -- work start <work-item-id>",
            "npm run art -- work status <work-item-id>",
            "npm run art -- work continue <work-item-id>",
            "npm run art -- work close <work-item-id>",
            "npm run art -- work --help",
        ):
            if required not in skill_text:
                errors.append(f"{skill_path}: missing ART operator-path command {required!r}")
        for required in ("Initiative Family", "Lineage Role"):
            if required not in skill_text:
                errors.append(
                    f"{skill_path}: missing initiative-lineage reminder {required!r}"
                )
        for required in (
            "Initiative Architecture Preflight",
            "architecture-ready",
            "session and scenario-execution binding",
            "positive and negative contract cases",
        ):
            if required not in skill_text:
                errors.append(
                    f"{skill_path}: missing initiative architecture preflight control {required!r}"
                )
        forbidden = "default ART reads and writes to direct\n     top-level `k3s kubectl` broker calls against the active profile namespace"
        if forbidden in skill_text:
            errors.append(
                f"{skill_path}: still teaches direct kubectl broker calls as the normal ART path"
            )
    else:
        errors.append(f"{skill_path}: missing project-delivery-operator skill")


def build_generated_contracts(repo_root: Path, contracts: dict[str, object]) -> dict[str, object]:
    repos = contracts["repos"]["repos"]
    products = contracts["products"]["products"]
    components = contracts["components"]["components"]
    skills = contracts["skills"]["skills"]
    boundary_map = contracts["governance_engine_boundary_map"][
        "governance_engine_boundary_map"
    ]
    output_manifest = contracts["governance_engine_output_manifest"][
        "governance_engine_output_manifest"
    ]

    dependency_edges: list[dict[str, str]] = []
    for repo_name, payload in repos.items():
        for target in payload["allowed_authoritative_refs"]:
            dependency_edges.append(
                {"from": repo_name, "to": target, "type": "authoritative-reference"}
            )
    for product_name, payload in products.items():
        dependency_edges.append(
            {"from": product_name, "to": payload["platform_owner"], "type": "authoritative-reference"}
        )
        dependency_edges.append(
            {"from": product_name, "to": payload["security_owner"], "type": "security-reference"}
        )
        dependency_edges.append(
            {"from": product_name, "to": payload["runtime_owner"], "type": "runtime-input"}
        )
        for repo_name in payload["source_owners"]:
            dependency_edges.append(
                {"from": product_name, "to": repo_name, "type": "authoritative-reference"}
            )

    stale_rules: list[dict[str, object]] = []
    for entry in contracts["vocabulary"]["retired_terms"]:
        stale_rules.append(
            {
                "id": entry["id"],
                "pattern": entry["pattern"],
                "repo_names": entry["repo_names"],
                "exclude_paths": entry.get("exclude_paths", []),
                "targets": ["*.md"],
            }
        )
    for repo_name, rule in contracts["repo_rules"].items():
        for target_name, patterns in rule["forbidden_patterns"].items():
            if patterns:
                stale_rules.append(
                    {
                        "id": f"{repo_name}-{target_name}-forbidden",
                        "pattern": "|".join(patterns),
                        "repo_names": [repo_name],
                        "exclude_paths": [],
                        "targets": [f"{target_name.upper()}.md" if target_name == "agents" else "README.md"],
                    }
                )

    emitted_outputs: list[dict[str, object]] = []
    for family in output_manifest["emission_families"]:
        outputs = family.get("outputs") or []
        if outputs:
            emitted_outputs.append(
                {
                    "family_id": family["id"],
                    "boundary": family["boundary"],
                    "outputs": [entry["emitted_path"] for entry in outputs],
                }
            )
            continue
        emitted_outputs.append(
            {
                "family_id": family["id"],
                "boundary": family["boundary"],
                "target_root_default": family.get("target_root_default"),
                "emitted_path_template": family.get("emitted_path_template"),
                "managed_manifest_filename": family.get("managed_manifest_filename"),
            }
        )

    return {
        "system_map": {
            "schema_version": contracts["version"]["schema_version"],
            "repos": repos,
            "retired_repos": contracts["repos"].get("retired_repos", {}),
            "products": products,
            "components": components,
            "skills": skills,
        },
        "resolved_owner_map": {
            "repos": repos,
            "products": products,
            "components": components,
            "skills": skills,
        },
        "resolved_dependency_graph": {
            "dependency_types": contracts["dependency_types"]["dependency_types"],
            "edges": dependency_edges,
        },
        "stale_content_rules": stale_rules,
        "governance_engine_boundary_map": {
            "schema_version": contracts["version"]["schema_version"],
            "authoring_paths": boundary_map["authoring_paths"],
            "generated_paths": boundary_map["generated_paths"],
            "tenant_instance_paths": boundary_map["tenant_instance_paths"],
            "external_instance_surfaces": boundary_map["external_instance_surfaces"],
            "live_materialized_outputs": boundary_map["live_materialized_outputs"],
            "current_coupling_points": boundary_map["current_coupling_points"],
            "standalone_packaging_prerequisites": boundary_map[
                "standalone_packaging_prerequisites"
            ],
            "output_manifest_compatibility_controls": output_manifest[
                "compatibility_controls"
            ],
            "emitted_output_families": emitted_outputs,
            "invariants": boundary_map["invariants"],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate cross-repo truth against workspace contracts.")
    parser.add_argument(
        "--workspace-root",
        default=Path(__file__).resolve().parents[2],
        type=Path,
        help="workspace root containing the active repos",
    )
    parser.add_argument(
        "--write-generated",
        action="store_true",
        help="write generated contract artifacts under generated/",
    )
    parser.add_argument(
        "--check-generated",
        action="store_true",
        help="fail if generated artifacts do not match the current contracts",
    )
    args = parser.parse_args()

    workspace_root = args.workspace_root.resolve()
    repo_root = Path(__file__).resolve().parents[1]
    contracts = load_contracts(repo_root)
    active_repos = active_repo_names(contracts)
    errors: list[str] = []

    for repo_name in active_repos:
        repo_root_path = workspace_root / repo_name
        if not repo_root_path.exists():
            errors.append(f"missing active repo for cross-repo truth check: {repo_root_path}")
            continue

        readme_path = repo_root_path / "README.md"
        agents_path = repo_root_path / "AGENTS.md"
        if not readme_path.exists() or not agents_path.exists():
            errors.append(f"{repo_root_path}: missing README.md or AGENTS.md")
            continue

        readme_text = readme_path.read_text()
        agents_text = agents_path.read_text()
        combined = readme_text + "\n" + agents_text
        rule = contracts["repo_rules"][repo_name]

        for ref in rule["required_repo_refs"]:
            if ref not in combined:
                errors.append(f"{repo_root_path}: missing required authoritative repo reference {ref!r} in README.md or AGENTS.md")

        for pattern in rule["required_patterns"]["readme"]:
            if not re.search(pattern, readme_text, re.MULTILINE):
                errors.append(f"{readme_path}: missing required ownership pattern {pattern!r}")
        for pattern in rule["required_patterns"]["agents"]:
            if not re.search(pattern, agents_text, re.MULTILINE):
                errors.append(f"{agents_path}: missing required routing pattern {pattern!r}")
        for pattern in rule["forbidden_patterns"]["readme"]:
            if pattern and re.search(pattern, readme_text, re.MULTILINE):
                errors.append(f"{readme_path}: found forbidden ownership pattern {pattern!r}")
        for pattern in rule["forbidden_patterns"]["agents"]:
            if pattern and re.search(pattern, agents_text, re.MULTILINE):
                errors.append(f"{agents_path}: found forbidden routing pattern {pattern!r}")

    validate_workspace_root_repo_coverage(repo_root / "workspace-root", active_repos, errors)
    validate_security_architecture_component_coverage(workspace_root, contracts, errors)
    validate_delivery_art_planning_workflow_contract(workspace_root, errors)
    validate_delivery_art_initiative_review_workflow_contract(workspace_root, errors)
    validate_delivery_art_blocker_workflow_contract(workspace_root, errors)
    validate_delivery_art_initiative_lineage_contract(workspace_root, errors)
    validate_delivery_art_operator_path_contract(workspace_root, repo_root, errors)

    for product_name, product in contracts["products"]["products"].items():
        if product["lifecycle"] not in {"platform-integrated", "fully-governed"}:
            continue
        product_readme = workspace_root / "platform-engineering" / "products" / product_name / "README.md"
        if not product_readme.exists():
            errors.append(f"platform-engineering product missing README for declared product {product_name}: {product_readme}")

    for component_name, payload in contracts["components"]["components"].items():
        interface_contract = payload.get("interface_contract")
        if not interface_contract:
            continue
        contract_path = workspace_root / payload["owner_repo"] / interface_contract["path"]
        if not contract_path.exists():
            errors.append(
                f"contracts/components.yaml: {component_name} interface contract path is missing in owner repo {payload['owner_repo']}: {contract_path}"
            )

    for skill_name, payload in contracts["skills"]["skills"].items():
        skill_path = workspace_root / payload["owner_repo"] / payload["source_path"]
        if not skill_path.exists():
            errors.append(
                f"contracts/skills.yaml: {skill_name} source path is missing in owner repo {payload['owner_repo']}: {skill_path}"
            )
            continue
        if not (skill_path / "SKILL.md").exists():
            errors.append(f"{skill_path}: missing SKILL.md for registered skill {skill_name}")

    compiled = build_generated_contracts(repo_root, contracts)
    paths = generated_paths(repo_root)

    if args.write_generated:
        write_generated_artifacts(repo_root, compiled, contracts=contracts)

    if args.check_generated:
        errors.extend(
            check_generated_artifacts(repo_root, compiled, contracts=contracts)
        )

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print(
        "cross-repo truth valid: "
        f"repos={len(active_repos)} "
        f"products={len(contracts['products']['products'])} "
        f"components={len(contracts['components']['components'])} "
        f"skills={len(contracts['skills']['skills'])}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
