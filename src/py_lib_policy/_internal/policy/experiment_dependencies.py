"""Engineering Experiment dependency-isolation checks."""

from __future__ import annotations

import re
import tomllib
from collections.abc import Iterable
from pathlib import Path

from py_lib_policy._internal.config.assembly import _read_toml
from py_lib_policy._internal.config.models import ProjectPolicyConfig
from py_lib_policy._internal.policy.models import Violation


def _check_capsule_dependencies(
    capsule: Path,
    config: ProjectPolicyConfig,
) -> list[Violation]:
    """Reject dependencies that couple a capsule to the parent repository."""
    path = capsule / "pyproject.toml"
    if not path.is_file():
        return []
    try:
        data = _read_toml(path)
    except (OSError, tomllib.TOMLDecodeError):
        return []

    parent_names = {_canonical_name(name) for name in config.package_names}
    root_project = _read_root_project_name(capsule)
    if root_project:
        parent_names.add(_canonical_name(root_project))

    violations = _dependency_violations(path, data, parent_names)
    violations.extend(_uv_dependency_violations(path, data))
    return violations


def _dependency_violations(
    path: Path,
    data: dict[str, object],
    parent_names: set[str],
) -> list[Violation]:
    """Return violations for parent-package and filesystem dependency specs."""
    violations: list[Violation] = []
    for dependency in _dependency_specs(data):
        if _looks_like_local_reference(dependency.lower()):
            violations.append(
                Violation(
                    path,
                    f"experiment dependency must not use a local path: {dependency}",
                )
            )
        dependency_name = _requirement_name(dependency)
        if dependency_name and _canonical_name(dependency_name) in parent_names:
            message = (
                "experiment must not depend on the parent project package: "
                f"{dependency_name}"
            )
            violations.append(Violation(path, message))
    return violations


def _uv_dependency_violations(
    path: Path,
    data: dict[str, object],
) -> list[Violation]:
    """Return violations for uv workspace, path, and editable coupling."""
    tooling = data.get("tool", {})
    uv = tooling.get("uv", {}) if isinstance(tooling, dict) else {}
    if not isinstance(uv, dict):
        return []

    violations: list[Violation] = []
    if "workspace" in uv:
        violations.append(Violation(path, "experiment must be a standalone uv project"))
    sources = uv.get("sources", {})
    if not isinstance(sources, dict):
        return violations

    for name, source in sources.items():
        if not isinstance(source, dict):
            continue
        if (
            any(key in source for key in ("path", "workspace"))
            or source.get("editable") is True
        ):
            message = (
                f"uv source {name!r} must not use path/workspace/editable coupling"
            )
            violations.append(Violation(path, message))
    return violations


def _dependency_specs(data: dict[str, object]) -> Iterable[str]:
    """Yield dependency strings from PEP 621 and uv dependency groups."""
    project = data.get("project", {})
    if isinstance(project, dict):
        yield from _string_dependencies(project.get("dependencies"))
        yield from _dependency_table(project.get("optional-dependencies"))
    yield from _dependency_table(data.get("dependency-groups"))


def _dependency_table(value: object) -> Iterable[str]:
    """Yield dependency strings from a named dependency-group table."""
    if not isinstance(value, dict):
        return ()
    return (
        dependency
        for group in value.values()
        for dependency in _string_dependencies(group)
    )


def _string_dependencies(value: object) -> Iterable[str]:
    """Yield string dependency entries from one TOML array value."""
    if not isinstance(value, list):
        return ()
    return (dependency for dependency in value if isinstance(dependency, str))


def _looks_like_local_reference(value: str) -> bool:
    """Return whether one dependency spec contains a local filesystem reference."""
    compact = value.replace(" ", "")
    return "@file:" in compact or "@../" in compact or "@./" in compact


def _requirement_name(value: str) -> str | None:
    """Extract the leading distribution name from a PEP 508-like spec."""
    match = re.match(r"^[A-Za-z0-9][A-Za-z0-9._-]*", value.strip())
    return None if match is None else match.group(0)


def _canonical_name(value: str) -> str:
    """Normalize a distribution/import spelling for parent-package comparison."""
    return re.sub(r"[-_.]+", "-", value).lower()


def _read_root_project_name(capsule: Path) -> str | None:
    """Read the nearest parent repository distribution name."""
    for parent in capsule.parents:
        pyproject = parent / "pyproject.toml"
        if not pyproject.is_file():
            continue
        try:
            data = _read_toml(pyproject)
        except (OSError, tomllib.TOMLDecodeError):
            return None
        project = data.get("project", {})
        if isinstance(project, dict):
            name = project.get("name")
            if isinstance(name, str) and name.strip():
                return name.strip()
        return None
    return None
