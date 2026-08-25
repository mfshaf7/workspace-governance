from __future__ import annotations

import re
from typing import Any


ENVIRONMENT_VARIABLE_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]*$")
FORBIDDEN_CREDENTIAL_VALUE_KEYS = {
    "credential",
    "literal",
    "literal_value",
    "secret",
    "secret_value",
    "token",
    "value",
}


def _credential_value_paths(payload: Any, path: str = "") -> list[str]:
    paths: list[str] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            child_path = f"{path}.{key}" if path else key
            if key in FORBIDDEN_CREDENTIAL_VALUE_KEYS:
                paths.append(child_path)
            paths.extend(_credential_value_paths(value, child_path))
    elif isinstance(payload, list):
        for index, value in enumerate(payload):
            paths.extend(_credential_value_paths(value, f"{path}[{index}]"))
    return paths


def _cycle_path(graph: dict[str, set[str]]) -> list[str] | None:
    visiting: set[str] = set()
    visited: set[str] = set()
    path: list[str] = []

    def visit(node: str) -> list[str] | None:
        if node in visiting:
            start = path.index(node)
            return path[start:] + [node]
        if node in visited:
            return None
        visiting.add(node)
        path.append(node)
        for dependency in sorted(graph.get(node, set())):
            cycle = visit(dependency)
            if cycle:
                return cycle
        path.pop()
        visiting.remove(node)
        visited.add(node)
        return None

    for node in sorted(graph):
        cycle = visit(node)
        if cycle:
            return cycle
    return None


def runtime_composition_issues(
    registry: dict[str, Any],
    *,
    active_repos: set[str],
    allowed_lifecycles: set[str],
) -> list[str]:
    issues: list[str] = []
    profiles = registry.get("profiles") or {}
    compositions = registry.get("runtime_compositions") or {}

    if not compositions:
        return [
            "contracts/developer-integration-profiles.yaml: runtime_compositions must not be empty"
        ]

    for composition_id, composition in sorted(compositions.items()):
        label = (
            "contracts/developer-integration-profiles.yaml: "
            f"runtime_compositions.{composition_id}"
        )
        owner_repo = composition.get("owner_repo")
        if owner_repo not in active_repos:
            issues.append(f"{label}.owner_repo {owner_repo!r} is not an active repo")
        composition_lifecycle = composition.get("lifecycle")
        if composition_lifecycle not in allowed_lifecycles:
            issues.append(
                f"{label}.lifecycle {composition_lifecycle!r} is not declared"
            )

        participants = composition.get("profiles") or {}
        root_profile_id = composition.get("root_profile_id")
        if root_profile_id not in participants:
            issues.append(
                f"{label}.root_profile_id {root_profile_id!r} is not a declared composition profile"
            )

        for profile_id, requirement in sorted(participants.items()):
            profile = profiles.get(profile_id)
            if profile is None:
                issues.append(f"{label}.profiles references unknown profile {profile_id!r}")
                continue
            required_lifecycle = requirement.get("required_lifecycle")
            if required_lifecycle not in allowed_lifecycles:
                issues.append(
                    f"{label}.profiles.{profile_id}.required_lifecycle "
                    f"{required_lifecycle!r} is not declared"
                )
            elif (
                composition_lifecycle == "active"
                and profile.get("lifecycle") != required_lifecycle
            ):
                issues.append(
                    f"{label}.profiles.{profile_id} requires lifecycle "
                    f"{required_lifecycle!r}, got {profile.get('lifecycle')!r}"
                )
            runtime_owner = profile.get("runtime_owner")
            if runtime_owner != owner_repo:
                issues.append(
                    f"{label}.profiles.{profile_id} has ambiguous runtime ownership: "
                    f"composition owner {owner_repo!r}, profile runtime_owner {runtime_owner!r}"
                )

        graph = {profile_id: set() for profile_id in participants}
        edges: set[tuple[str, str]] = set()
        projection_targets: set[tuple[str, str]] = set()
        for dependency in composition.get("dependencies") or []:
            consumer = dependency.get("consumer_profile_id")
            provider = dependency.get("provider_profile_id")
            edge = (consumer, provider)
            if edge in edges:
                issues.append(
                    f"{label}.dependencies repeats dependency {consumer!r} -> {provider!r}"
                )
            edges.add(edge)
            if consumer not in participants:
                issues.append(
                    f"{label}.dependencies consumer {consumer!r} is not a declared composition profile"
                )
            if provider not in participants:
                issues.append(
                    f"{label}.dependencies provider {provider!r} is not a declared composition profile"
                )
            if consumer == provider:
                issues.append(f"{label}.dependencies contains self dependency {consumer!r}")
            if consumer in graph and provider in graph:
                graph[consumer].add(provider)

            for projection in dependency.get("endpoint_projections") or []:
                environment_variable = projection.get("environment_variable")
                target = (consumer, environment_variable)
                if target in projection_targets:
                    issues.append(
                        f"{label} repeats projection {consumer!r}:{environment_variable!r}"
                    )
                projection_targets.add(target)
                if not isinstance(environment_variable, str) or not ENVIRONMENT_VARIABLE_PATTERN.fullmatch(environment_variable):
                    issues.append(
                        f"{label} endpoint projection environment_variable "
                        f"{environment_variable!r} is invalid"
                    )

        execution = composition.get("execution") or {}
        cleanup_owner_repo = execution.get("cleanup_owner_repo")
        if cleanup_owner_repo != owner_repo:
            issues.append(
                f"{label}.execution.cleanup_owner_repo {cleanup_owner_repo!r} "
                f"does not match composition owner {owner_repo!r}"
            )
        for action_key in ("startup_action", "readiness_action", "teardown_action"):
            action = execution.get(action_key)
            for profile_id in sorted(participants):
                profile = profiles.get(profile_id) or {}
                if action not in (profile.get("actions") or []):
                    issues.append(
                        f"{label}.execution.{action_key} {action!r} is not available "
                        f"on profile {profile_id!r}"
                    )

        for binding_id, binding in sorted(
            (composition.get("caller_bindings") or {}).items()
        ):
            binding_label = f"{label}.caller_bindings.{binding_id}"
            binding_owner = binding.get("owner_repo")
            consumer = binding.get("consumer_profile_id")
            provider = binding.get("provider_profile_id")
            if binding_owner != owner_repo:
                issues.append(
                    f"{binding_label}.owner_repo {binding_owner!r} does not match "
                    f"composition owner {owner_repo!r}"
                )
            if consumer not in participants or provider not in participants:
                issues.append(
                    f"{binding_label} must reference declared consumer and provider profiles"
                )
            elif (consumer, provider) not in edges:
                issues.append(
                    f"{binding_label} does not match a declared dependency "
                    f"{consumer!r} -> {provider!r}"
                )
            for side in ("consumer", "provider"):
                profile_id = binding.get(f"{side}_profile_id")
                environment_variable = binding.get(
                    f"{side}_environment_variable"
                )
                target = (profile_id, environment_variable)
                if target in projection_targets:
                    issues.append(
                        f"{label} repeats projection {profile_id!r}:{environment_variable!r}"
                    )
                projection_targets.add(target)
                if (
                    not isinstance(environment_variable, str)
                    or not ENVIRONMENT_VARIABLE_PATTERN.fullmatch(
                        environment_variable
                    )
                ):
                    issues.append(
                        f"{binding_label}.{side}_environment_variable "
                        f"{environment_variable!r} is invalid"
                    )

        cycle = _cycle_path(graph)
        if cycle:
            issues.append(f"{label}.dependencies contains cycle {' -> '.join(cycle)}")

        if root_profile_id in graph:
            reachable: set[str] = set()
            pending = [root_profile_id]
            while pending:
                current = pending.pop()
                if current in reachable:
                    continue
                reachable.add(current)
                pending.extend(graph[current] - reachable)
            disconnected = sorted(set(participants) - reachable)
            if disconnected:
                issues.append(
                    f"{label}.profiles are not reachable from root {root_profile_id!r}: "
                    + ", ".join(disconnected)
                )

        for binding_id, binding in sorted(
            (composition.get("credential_bindings") or {}).items()
        ):
            binding_label = f"{label}.credential_bindings.{binding_id}"
            binding_owner = binding.get("owner_repo")
            if binding_owner != owner_repo:
                issues.append(
                    f"{binding_label}.owner_repo {binding_owner!r} does not match "
                    f"composition owner {owner_repo!r}"
                )
            if binding_owner not in active_repos:
                issues.append(
                    f"{binding_label}.owner_repo {binding_owner!r} is not an active repo"
                )
            for value_path in _credential_value_paths(binding):
                issues.append(
                    f"{binding_label} contains forbidden tracked credential value field {value_path!r}"
                )
            for projection in binding.get("projections") or []:
                profile_id = projection.get("profile_id")
                environment_variable = projection.get("environment_variable")
                if profile_id not in participants:
                    issues.append(
                        f"{binding_label}.projections profile {profile_id!r} is not a declared composition profile"
                    )
                target = (profile_id, environment_variable)
                if target in projection_targets:
                    issues.append(
                        f"{label} repeats projection {profile_id!r}:{environment_variable!r}"
                    )
                projection_targets.add(target)
                if not isinstance(environment_variable, str) or not ENVIRONMENT_VARIABLE_PATTERN.fullmatch(environment_variable):
                    issues.append(
                        f"{binding_label} projection environment_variable "
                        f"{environment_variable!r} is invalid"
                    )

        for binding_id, binding in sorted(
            (composition.get("profile_bindings") or {}).items()
        ):
            binding_label = f"{label}.profile_bindings.{binding_id}"
            binding_owner = binding.get("owner_repo")
            profile_id = binding.get("profile_id")
            environment_variable = binding.get("environment_variable")
            if binding_owner != owner_repo:
                issues.append(
                    f"{binding_label}.owner_repo {binding_owner!r} does not match "
                    f"composition owner {owner_repo!r}"
                )
            if profile_id not in participants:
                issues.append(
                    f"{binding_label}.profile_id {profile_id!r} is not a declared composition profile"
                )
            target = (profile_id, environment_variable)
            if target in projection_targets:
                issues.append(
                    f"{label} repeats projection {profile_id!r}:{environment_variable!r}"
                )
            projection_targets.add(target)
            if (
                not isinstance(environment_variable, str)
                or not ENVIRONMENT_VARIABLE_PATTERN.fullmatch(environment_variable)
            ):
                issues.append(
                    f"{binding_label}.environment_variable "
                    f"{environment_variable!r} is invalid"
                )

    return issues
